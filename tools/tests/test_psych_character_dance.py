"""Psych dance-pair rendering and provenance-checked refresh."""
from haxe_test_support import HAXE_COMMAND

import base64
import hashlib
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.refresh_psych_character_dance import apply_plan, make_plan, namespace_for, render_scripts


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"


def character_json(name):
    return {"image": name, "healthicon": name, "healthbar_colors": [1, 2, 3],
            "animations": [
                {"anim": "danceLeft", "name": "left", "indices": [0, 1], "fps": 24,
                 "loop": False, "offsets": [0, 0]},
                {"anim": "danceRight", "name": "right", "indices": [2, 3], "fps": 24,
                 "loop": False, "offsets": [0, 0]}],
            "flip_x": False, "scale": 1, "no_antialiasing": False, "sing_duration": 4}


class PsychCharacterDanceTest(unittest.TestCase):
    def test_standard_renderer_treats_missing_or_malformed_indices_as_prefix(self):
        fixture = '''class Main {
  static function main() {
    var malformedIndices:Array<Dynamic> = [1];
    malformedIndices.push('bad');
    var data:Dynamic = {animations:[
      {anim:'danceLeft-alt', name:'left', fps:24, loop:false, offsets:[-110,21]},
      {anim:'danceRight-alt', name:'right', indices:null, fps:24, loop:false, offsets:[-110,21]},
      {anim:'singUP', name:'up', indices:'not-an-array', fps:24, loop:false, offsets:[0,0]},
      {anim:'singLEFT', name:'left', indices:[0,2], fps:30, loop:true, offsets:[1,2]},
      {anim:'idle', name:'idle', indices:[], fps:24, loop:false, offsets:[0,0]},
      {anim:'singDOWN', name:'down', indices:malformedIndices, fps:24, loop:false, offsets:[0,0]}],
      flip_x:false, scale:1, no_antialiasing:false, sing_duration:4};
    var script = PsychCharacterDanceCompat.renderStandardScript(data, false, false, false);
    for (name in ['danceLeft-alt', 'danceRight-alt', 'singUP', 'idle', 'singDOWN'])
      if (script.indexOf("char.animation.addByPrefix('" + name + "'") < 0)
        throw 'missing prefix animation fallback for ' + name + ': ' + script;
    if (script.indexOf("char.animation.addByIndices('singLEFT', 'left', [0,2]") < 0)
      throw 'valid indices animation changed: ' + script;
    if (script.split('char.animation.addByIndices(').length != 2)
      throw 'malformed index lists should not be emitted: ' + script;
  }
}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            (work / "PsychCharacterDanceCompat.hx").write_bytes(
                (ROOT / "source/PsychCharacterDanceCompat.hx").read_bytes())
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_animate_importer_generates_dance_from_authored_animations(self):
        importer = (ROOT / "source/ModuleFunctions.hx").read_text()
        start = importer.index("static function psychToDisAnimateChar(")
        end = importer.index("\n\tstatic function legacyAtlasEngine", start)
        generated = importer[start:end]
        self.assertIn("PsychCharacterDanceCompat.renderAnimateDance(charJson)", generated)
        self.assertNotIn("danced = !danced", generated)

        fixture = '''import hscript.Parser;
import hscript.Interp;
class Animations {
  public var names:Array<String>;
  public function new(names:Array<String>) this.names = names;
  public function exists(name:String):Bool return names.indexOf(name) >= 0;
}
class Actor {
  public var idleSuffix:String = '';
  public var animation:Animations;
  public var played:Array<String> = [];
  public function new(names:Array<String>) animation = new Animations(names);
  public function playAnim(name:String):Void played.push(name);
}
class Main {
  static function runDance(source:String, actor:Actor):Void {
    var interp = new Interp();
    interp.execute(new Parser().parseString(source));
    Reflect.callMethod(null, interp.variables.get('dance'), [actor]);
  }
  static function main() {
    var pair:Dynamic = {animations:[{anim:'danceLeft'}, {anim:'danceRight'}]};
    var pairScript = PsychCharacterDanceCompat.renderAnimateDance(pair);
    if (pairScript.indexOf('var danced = false;') < 0)
      throw 'paired dances need initialized toggle state';
    var pairActor = new Actor(['danceLeft', 'danceRight']);
    var pairInterp = new Interp();
    pairInterp.execute(new Parser().parseString(pairScript));
    var pairDance = pairInterp.variables.get('dance');
    Reflect.callMethod(null, pairDance, [pairActor]);
    Reflect.callMethod(null, pairDance, [pairActor]);
    if (pairActor.played.join(',') != 'danceRight,danceLeft')
      throw 'paired dance order: ' + pairActor.played.join(',');

    var idle:Dynamic = {animations:[{anim:'idle'}, {anim:'idle-alt'}]};
    var idleScript = PsychCharacterDanceCompat.renderAnimateDance(idle);
    if (idleScript.indexOf('danced') >= 0 || idleScript.indexOf('danceLeft') >= 0
      || idleScript.indexOf('danceRight') >= 0)
      throw 'idle-only character references absent dance state/anims';
    var idleActor = new Actor(['idle-alt']);
    idleActor.idleSuffix = '-alt';
    runDance(idleScript, idleActor);
    if (idleActor.played.join(',') != 'idle-alt')
      throw 'idle fallback: ' + idleActor.played.join(',');

    var combat:Dynamic = {animations:[{anim:'singLEFT'}, {anim:'attack'}]};
    var combatScript = PsychCharacterDanceCompat.renderAnimateDance(combat);
    if (combatScript.indexOf('danced') >= 0 || combatScript.indexOf('idle') >= 0
      || combatScript.indexOf('danceLeft') >= 0 || combatScript.indexOf('danceRight') >= 0)
      throw 'no-idle character references absent dance/idle anims';
    var combatActor = new Actor(['singLEFT', 'attack']);
    runDance(combatScript, combatActor);
    if (combatActor.played.length != 0)
      throw 'no-idle dance callback should be a no-op';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            (work / "PsychCharacterDanceCompat.hx").write_bytes(
                (ROOT / "source/PsychCharacterDanceCompat.hx").read_bytes())
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work),
                                     "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                     "--run", "Main"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scaled_character_hitbox_matches_psych_camera_midpoint(self):
        source = (ROOT / "source/Character.hx").read_text()
        start = source.index('try callInterp("init", [this])')
        init = source[start:source.index('dance();', start) + len('dance();')]
        self.assertLess(init.index("needsOwnedLegacyHitbox"), init.index("dance();"))
        self.assertIn("visualResolution.implementationPath", init)
        fixture = '''class Main {
  static function main() {
    var data:Dynamic = {animations:[], flip_x:false, scale:6,
      no_antialiasing:false, sing_duration:4};
    var script = PsychCharacterDanceCompat.renderStandardScript(data, false, false, false);
    var scale = script.indexOf('char.scale.y = 6;');
    var hitbox = script.indexOf('char.updateHitbox();');
    if (scale < 0 || hitbox <= scale) throw 'Psych scale did not update hitbox';
    if (!PsychCharacterDanceCompat.needsScaledHitbox(6, 6, 720, 720, 720, 720))
      throw 'older imported phone must refresh scaled hitbox';
    if (PsychCharacterDanceCompat.needsScaledHitbox(6, 6, 720, 720, 4320, 4320))
      throw 'already corrected hitbox must remain intact';
    if (PsychCharacterDanceCompat.needsScaledHitbox(1, 1, 720, 720, 720, 720))
      throw 'native size must remain intact';
    var owner = 'assets/imported_mods/psych-owner';
    var generated = StringTools.replace(script, '\\n    char.updateHitbox();', '');
    var metadata = haxe.Json.stringify(data);
    var sources:Map<String, String> = [
      owner + '/characters/Champ-Huge.json' => metadata,
      'assets/images/custom_chars/Champ-Huge.hscript' => generated
    ];
    var read = function(path:String):Null<String> return sources.get(path);
    if (!PsychCharacterDanceCompat.needsOwnedLegacyHitbox('Champ-Huge', owner,
      'assets/images/custom_chars/Champ-Huge.hscript', 6, 6, 720, 720, 720, 720, read))
      throw 'selected owner and exact global generated script rejected';
    sources.set('assets/images/custom_chars/Champ-Huge.hscript', generated + '\\n// edited');
    if (PsychCharacterDanceCompat.needsOwnedLegacyHitbox('Champ-Huge', owner,
      'assets/images/custom_chars/Champ-Huge.hscript', 6, 6, 720, 720, 720, 720, read))
      throw 'edited lookalike script accepted';
    sources.set('assets/images/custom_chars/Champ-Huge.hscript', generated);
    sources.remove(owner + '/characters/Champ-Huge.json');
    if (PsychCharacterDanceCompat.needsOwnedLegacyHitbox('Champ-Huge', owner,
      'assets/images/custom_chars/Champ-Huge.hscript', 6, 6, 720, 720, 720, 720, read))
      throw 'global native fallback without selected metadata accepted';
    sources.set(owner + '/characters/Champ-Huge.json', metadata);
    if (PsychCharacterDanceCompat.needsOwnedLegacyHitbox('Champ-Huge', owner,
      'assets/images/custom_chars/other.hscript', 6, 6, 720, 720, 720, 720, read))
      throw 'unrelated implementation accepted';
    var donorMidpoint = -1250 + 4320 / 2;
    var staleMidpoint = -1250 + 720 / 2;
    if (donorMidpoint != 910 || staleMidpoint != -890)
      throw 'fixture failed to capture 1800-pixel camera focus gap';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            (work / "PsychCharacterDanceCompat.hx").write_text(
                (ROOT / "source/PsychCharacterDanceCompat.hx").read_text(), newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rendered_script_plays_right_then_left_and_recalculates_suffix(self):
        fixture = '''import hscript.Parser;
import hscript.Interp;
class Animations {
  public var names:Array<String> = ['danceLeft','danceRight','danceLeft-alt','danceRight-alt','idle-alt','idle-sad'];
  public function new() {}
  public function exists(name:String):Bool return names.indexOf(name) >= 0;
}
class Actor {
  public var idleSuffix:String = '';
  public var animation:Animations = new Animations();
  public var played:Array<String> = [];
  public function new() {}
  public function playAnim(name:String):Void played.push(name);
}
class Main {
  static function main() {
    var data:Dynamic = {animations:[
      {anim:'danceLeft', name:'left', indices:[0], fps:24, loop:false, offsets:[0,0]},
      {anim:'danceRight', name:'right', indices:[1], fps:24, loop:false, offsets:[0,0]}],
      flip_x:false, scale:1, no_antialiasing:false, sing_duration:4};
    if (!PsychCharacterDanceCompat.hasDancePair(data)) throw 'pair not detected';
    var script = PsychCharacterDanceCompat.renderStandardScript(data, false, false, false);
    var legacy = PsychCharacterDanceCompat.renderStandardScript(data, false, false, false, true);
    if (legacy.indexOf("char.playAnim('idle')") < 0) throw 'legacy renderer changed';
    var interp = new Interp();
    interp.execute(new Parser().parseString(script));
    var dance = interp.variables.get('dance');
    var actor = new Actor();
    Reflect.callMethod(null, dance, [actor]);
    Reflect.callMethod(null, dance, [actor]);
    actor.idleSuffix = '-alt';
    Reflect.callMethod(null, dance, [actor]);
    actor.idleSuffix = '-sad';
    Reflect.callMethod(null, dance, [actor]);
    if (actor.played.join(',') != 'danceRight,danceLeft,danceRight-alt,idle-sad')
      throw 'dance order/suffix: ' + actor.played.join(',');
    var suffixOnly:Dynamic = {animations:[
      {anim:'danceLeft-alt', name:'left', indices:[0], fps:24, loop:false, offsets:[0,0]},
      {anim:'danceRight-alt', name:'right', indices:[1], fps:24, loop:false, offsets:[0,0]}],
      flip_x:false, scale:1, no_antialiasing:false, sing_duration:4};
    if (!PsychCharacterDanceCompat.hasDancePair(suffixOnly)) throw 'suffix pair not detected';
    var suffixInterp = new Interp();
    suffixInterp.execute(new Parser().parseString(
      PsychCharacterDanceCompat.renderStandardScript(suffixOnly, false, false, false)));
    var suffixActor = new Actor();
    suffixActor.idleSuffix = '-alt';
    var suffixDance = suffixInterp.variables.get('dance');
    Reflect.callMethod(null, suffixDance, [suffixActor]);
    Reflect.callMethod(null, suffixDance, [suffixActor]);
    if (suffixActor.played.join(',') != 'danceRight-alt,danceLeft-alt')
      throw 'suffix-only pair: ' + suffixActor.played.join(',');
    var idle:Dynamic = {animations:[
      {anim:'idle', name:'idle', indices:[], fps:24, loop:false, offsets:[0,0]},
      {anim:'idle-alt', name:'idle alt', indices:[], fps:24, loop:false, offsets:[0,0]}],
      flip_x:false, scale:1,
      no_antialiasing:false, sing_duration:4};
    if (PsychCharacterDanceCompat.hasDancePair(idle)) throw 'false pair';
    var idleInterp = new Interp();
    idleInterp.execute(new Parser().parseString(
      PsychCharacterDanceCompat.renderStandardScript(idle, false, false, false)));
    var idleActor = new Actor();
    idleActor.idleSuffix = '-alt';
    idleActor.animation.names = ['idle', 'idle-alt'];
    Reflect.callMethod(null, idleInterp.variables.get('dance'), [idleActor]);
    if (idleActor.played.join(',') != 'idle-alt')
      throw 'idle suffix: ' + idleActor.played.join(',');
  }
}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            (work / "PsychCharacterDanceCompat.hx").write_bytes(
                (ROOT / "source/PsychCharacterDanceCompat.hx").read_bytes())
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work),
                                     "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                     "--run", "Main"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_refresh_preserves_custom_script_and_backs_up_generated_bytes(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            donor = work / "donor"
            runtime = work / "runtime"
            characters = donor / "characters"
            characters.mkdir(parents=True)
            sources = []
            for name in ("paired", "custom", "idle"):
                source = characters / (name + ".json")
                data = character_json(name)
                if name == "idle":
                    data["animations"] = [{"anim": "idle", "name": "idle", "indices": [],
                        "fps": 24, "loop": False, "offsets": [0, 0]}]
                source.write_text(json.dumps(data), newline='\n')
                sources.append(source)
            namespace = namespace_for(donor)
            song = runtime / "assets/data/song"
            song.mkdir(parents=True)
            (song / "compatScripts.json").write_text(json.dumps({"selectedRoot": namespace,
                "roots": [{"path": namespace, "engine": "Psych Engine"}]}), newline='\n')
            target_dir = runtime / namespace / "images/custom_chars"
            target_dir.mkdir(parents=True)
            rendered = render_scripts(sources)
            generated = target_dir / "paired.hscript"
            generated.write_text(rendered[sources[0]]["legacy"], newline='\n')
            custom = target_dir / "custom.hscript"
            custom.write_text(rendered[sources[1]]["legacy"] + "\n// hand edited", newline='\n')
            idle = target_dir / "idle.hscript"
            idle.write_text(rendered[sources[2]]["legacy"], newline='\n')
            plan = make_plan(donor, runtime)
            self.assertEqual([item["name"] for item in plan["candidates"]], ["idle", "paired"])
            self.assertEqual(plan["skipped"], [{"name": "custom",
                "reason": "script differs from legacy generated bytes"}])
            plan_path = work / "plan.json"
            plan_path.write_text(json.dumps(plan), newline='\n')
            tampered = json.loads(json.dumps(plan))
            tampered["candidates"][0]["afterBase64"] = base64.b64encode(b"tampered").decode()
            tampered["candidates"][0]["afterSha256"] = hashlib.sha256(b"tampered").hexdigest()
            with patch("tools.refresh_psych_character_dance.fcntl.flock"):
                with self.assertRaisesRegex(ValueError, "differs from current renderer"):
                    apply_plan(tampered, plan_path)
            customized_bytes = b"customized after planning"
            idle.write_bytes(customized_bytes)
            tampered = json.loads(json.dumps(plan))
            tampered["candidates"][0]["beforeSha256"] = hashlib.sha256(customized_bytes).hexdigest()
            with patch("tools.refresh_psych_character_dance.fcntl.flock"):
                with self.assertRaisesRegex(ValueError, "not the exact legacy"):
                    apply_plan(tampered, plan_path)
            idle.write_text(rendered[sources[2]]["legacy"], newline='\n')
            with patch("tools.refresh_psych_character_dance.fcntl.flock"):
                backup = apply_plan(plan, plan_path)
            try:
                self.assertEqual(generated.read_text(), rendered[sources[0]]["current"])
                self.assertEqual(idle.read_text(), rendered[sources[2]]["current"])
                self.assertTrue(custom.read_text().endswith("// hand edited"))
                self.assertEqual((backup / generated.relative_to(runtime)).read_text(),
                                 rendered[sources[0]]["legacy"])
                self.assertEqual((backup / idle.relative_to(runtime)).read_text(),
                                 rendered[sources[2]]["legacy"])
            finally:
                shutil.rmtree(backup)


if __name__ == "__main__":
    unittest.main()
