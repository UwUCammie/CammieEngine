from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
HAVEN = DONOR / "psych/PERFEXION Demo1/stages/Haven.lua"
WHITTY_ALLEY = DONOR / "psych/vswhitty/stages/alley.lua"
WHITTY_4CHAN = DONOR / "psych/vswhitty/stages/4chan.lua"
WHITTY_ALLEY_BALLS = DONOR / "psych/vswhitty/stages/alley-balls-hqr.lua"
WHITTY_BETTER_HQR3 = DONOR / "psych/vswhitty/stages/better-hqr3.lua"
WEINER_STAGE = DONOR / "psych/Hey kid do you wanna weiner/stages/weiner.lua"


class PsychStageCompatibilityTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "PsychStageCompatTest.hx").write_text(source, newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HAXESCRIPT), "-main", "PsychStageCompatTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_stage_class_property_routes_gameover_actor_and_audio_to_song_state(self):
        fixture = r'''
class PsychStageCompatTest {
 static function main() {
  var source = "function onCreate()\n"
   + " setPropertyFromClass('GameOverSubstate', 'characterName', 'death-actor')\n"
   + " setPropertyFromClass('GameOverSubstate', 'deathSoundName', 'custom-loss')\n"
   + "end\n";
  var converted = PsychStageCompat.translate(source, 'fixture.lua');
  if (!converted.supported || converted.hscript.indexOf(
   'currentPlayState.setPsychClassProperty("GameOverSubstate", "deathSoundName", "custom-loss");') < 0
   || converted.hscript.indexOf(
   'currentPlayState.setPsychClassProperty("GameOverSubstate", "characterName", "death-actor");') < 0)
   throw converted.hscript + " diagnostics=" + converted.diagnostics.length;
  var captured = '';
  var interp = new hscript.Interp();
  interp.variables.set('currentPlayState', {setPsychClassProperty:function(cls:String,path:String,value:String) {
   captured = cls + ':' + path + ':' + value;
  }});
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  Reflect.callMethod(null, interp.variables.get('start'), ['fixture']);
  if (captured != 'GameOverSubstate:deathSoundName:custom-loss') throw captured;
  var dynamicResult = PsychStageCompat.translate("function onCreate()\n"
   + " setPropertyFromClass('GameOverSubstate', 'deathSoundName', customName)\nend\n");
  if (dynamicResult.supported) throw 'dynamic class value silently accepted';
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state = (ROOT / 'source/PlayState.hx').read_text()
        gameover = (ROOT / 'source/GameOverSubstate.hx').read_text()
        self.assertIn("public function psychGameOverSoundPath", state)
        self.assertIn("public function psychGameOverCharacterName", state)
        self.assertIn("var activePlayState = PlayState.instance;", gameover)
        self.assertIn("sourceOwner = activeSourceMode == 0 ? null : activePlayState;", gameover)
        self.assertIn("var psychCharacter = activePlayState == null ? null : activePlayState.psychGameOverCharacterName();", gameover)
        self.assertEqual(gameover.count("var playState = sourceOwner == null ? PlayState.instance : sourceOwner;"), 2,
                         "native setup and loop audio retain their owning PlayState")
        self.assertIn("playState.psychGameOverSoundPath('deathSoundName', true)", gameover)
        self.assertIn("playState.psychGameOverSoundPath('loopSoundName', false)", gameover)
        self.assertIn("playState.psychGameOverSoundPath('endSoundName', false)", gameover)
        self.assertIn("sourceOwner.sourceGameOverSound('deathSoundName', true)", gameover)
        self.assertIn("sourceOwner.sourceGameOverSound('loopSoundName', false)", gameover)
        self.assertIn("sourceOwner.sourceGameOverSound('endSoundName', false)", gameover)
        for key in ("deathSoundName", "loopSoundName", "endSoundName"):
            self.assertIn(f"playState.psychGameOverSoundPath('{key}'", gameover)

    def test_static_stage_sprite_alpha_retains_literal_and_diagnoses_dynamic_values(self):
        if not WHITTY_BETTER_HQR3.exists():
            self.skipTest("example donor is not mounted")
        fixture = r'''
class PsychStageCompatTest {
 static function main() {
  var stage = PsychStageCompat.translateFile(
   "/run/media/cammie/External Storage/FNF-Example-Mods/psych/vswhitty/stages/better-hqr3.lua");
  if (stage.hscript.indexOf('setProperty("moonlight2.alpha", 0.4);') < 0)
   throw 'authored moonlight opacity was lost: ' + stage.hscript;
  for (diagnostic in stage.diagnostics)
   if (diagnostic.code == 'unsupported-stage-property') throw diagnostic.message;
  var dynamicResult = PsychStageCompat.translate("function onCreate()\n"
   + " makeLuaSprite('fog', 'fog', 0, 0)\n"
   + " setProperty('fog.alpha', liveValue)\nend\n");
  if (dynamicResult.supported) throw 'dynamic opacity silently accepted';
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_static_psych_stage_helpers_and_metadata(self):
        fixture = r'''
class PsychStageCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "local gap = 15000\n"
            + "function onCreate()\n"
            + "  setProperty('defaultCamZoom', 0.85)\n"
            + "  setProperty('camGame.bgColor', getColorFromHex('FFA0D1'))\n"
            + "  makeLuaSprite('rock', 'Haven/EternityRock', 600, 600)\n"
            + "  scaleObject('rock', 1.5, 1.5)\n"
            + "  setScrollFactor('rock', 0.8, 0.7)\n"
            + "  setObjectCamera('rock', 'camGame')\n"
            + "  addLuaSprite('rock', false)\n"
            + "  makeAnimatedLuaSprite('cloud', 'Haven/CloudsLoop', -10 - gap, -3000)\n"
            + "  addAnimationByPrefix('cloud', 'loop', 'Loop', 25, true)\n"
            + "  objectPlayAnimation('cloud', 'loop', true)\n"
            + "  addLuaSprite('cloud', true)\n"
            + "end\n"
            + "function onUpdate(elapsed)\n"
            + "  doTweenX('cloud', 'cloud', 5, 1, 'linear')\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'fixture.lua');
        if (converted.defaultZoom == null || Math.abs(converted.defaultZoom - 0.85) > 0.0001)
            fail('default zoom metadata');
        if (converted.sprites.length != 2)
            fail('sprite count: ' + converted.sprites.length);
        if (converted.assets.length != 2 || converted.assets[0].destination != 'assets/images/Haven/EternityRock.png'
            || converted.assets[1].xmlDestination != 'assets/images/Haven/CloudsLoop.xml')
            fail('asset mapping');
        var rock = converted.sprites[0];
        if (rock.tag != 'rock' || rock.x != 600 || rock.scaleX != 1.5 || rock.scrollY != 0.7 || rock.front)
            fail('rock metadata');
        var cloud = converted.sprites[1];
        if (cloud.x != -15010 || !cloud.animated || !cloud.front || cloud.animations.length != 1) {
            var findings = [];
            for (diagnostic in converted.diagnostics) findings.push(diagnostic.code + ':' + diagnostic.message);
            fail('cloud metadata: ' + cloud.x + '/' + cloud.animations.length + '\\n' + findings.join('\\n') + '\\n' + converted.hscript);
        }
        if (converted.hscript.indexOf('setDefaultZoom(0.85);') < 0)
            fail('zoom route');
        if (converted.hscript.indexOf('makeLuaSprite("rock", "Haven/EternityRock", 600, 600)') < 0
            || converted.hscript.indexOf('addAnimationByPrefix("cloud", "loop", "Loop", 25, true);') < 0
            || converted.hscript.indexOf('objectPlayAnimation("cloud", "loop", true);') < 0)
            fail('asset/animation route: ' + converted.hscript);
        if (converted.hscript.indexOf('addLuaSprite("rock", false);') < 0
            || converted.hscript.indexOf('addLuaSprite("cloud", true);') < 0)
            fail('layer route: ' + converted.hscript);
        if (converted.hscript.indexOf('setScrollFactor("rock", 0.8, 0.7);') < 0)
            fail('scroll route');
        if (converted.runtimeCallbacks.length != 1 || converted.runtimeCallbacks[0] != 'onUpdate'
            || converted.hscript.indexOf('function onUpdate(?elapsed)') < 0 || !converted.supported)
            fail('runtime callback was not preserved: ' + converted.hscript);
        new hscript.Parser().parseString(converted.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_static_geometry_blend_and_visibility_helpers_use_shared_bindings(self):
        fixture = r'''
class PsychStageCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "function onCreate()\n"
            + "  makeLuaSprite('eff', 'thefunnyeffect', 0, 0)\n"
            + "  setGraphicSize('eff', 1280, 720)\n"
            + "  updateHitbox('eff')\n"
            + "  setBlendMode('eff', 'multiply')\n"
            + "  setProperty('eff.visible', false)\n"
            + "  setProperty('eff.flipX', true)\n"
            + "  addLuaSprite('eff', false)\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'static-helpers.lua');
        if (!converted.supported) {
            var messages = [];
            for (diagnostic in converted.diagnostics) messages.push(diagnostic.code + ':' + diagnostic.message);
            fail('supported static API was diagnosed: ' + messages.join(' | '));
        }
        for (expected in [
            'setGraphicSize("eff", 1280, 720);',
            'updateHitbox("eff");',
            'setBlendMode("eff", "multiply");',
            'setProperty("eff.visible", false);',
            'setProperty("eff.flipX", true);'
        ])
            if (converted.hscript.indexOf(expected) < 0) fail('missing generated binding ' + expected + '\n' + converted.hscript);

        var program = new hscript.Parser().parseString(converted.hscript);
        var objects:Map<String, Dynamic> = new Map<String, Dynamic>();
        var interp = new hscript.Interp();
        interp.variables.set('makeLuaSprite', function(tag:String, image:String, x:Float, y:Float):Dynamic {
            var sprite:Dynamic = {x:x, y:y, visible:true, flipX:false, width:0, height:0, hitboxUpdates:0, blendMode:''};
            objects.set(tag, sprite);
            return sprite;
        });
        interp.variables.set('setGraphicSize', function(tag:String, width:Int, ?height:Int):Void {
            var sprite = objects.get(tag);
            sprite.width = width;
            sprite.height = height == null ? width : height;
        });
        interp.variables.set('updateHitbox', function(tag:String):Void objects.get(tag).hitboxUpdates++);
        interp.variables.set('setBlendMode', function(tag:String, mode:String):Void objects.get(tag).blendMode = mode);
        interp.variables.set('setProperty', function(path:String, value:Dynamic):Void {
            var parts = path.split('.');
            Reflect.setField(objects.get(parts[0]), parts[1], value);
        });
        interp.variables.set('addLuaSprite', function(tag:String, front:Bool = false):Void {});
        interp.execute(program);
        var start:Dynamic = interp.variables.get('start');
        start('alley-balls');
        var sprite = objects.get('eff');
        if (sprite.width != 1280 || sprite.height != 720 || sprite.hitboxUpdates != 1
            || sprite.blendMode != 'multiply' || sprite.visible != false || sprite.flipX != true)
            fail('static helper behavior did not reach the shared bindings');
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        playstate = (ROOT / "source/PlayState.hx").read_text()
        for helper in ("setGraphicSize", "updateHitbox", "setBlendMode", "setProperty"):
            self.assertIn("interp.variables.set('" + helper + "'", playstate)

    def test_mounted_psych_stage_mirror_uses_shared_flip_property(self):
        if not WEINER_STAGE.is_file():
            self.skipTest("Psych example stage is not mounted")
        fixture = '''
class PsychStageCompatTest {
  static function main() {
    var converted = PsychStageCompat.translate(__SOURCE__, 'stages/weiner.lua');
    if (!converted.supported) {
      var messages = [];
      for (diagnostic in converted.diagnostics)
        messages.push(diagnostic.code + ':' + diagnostic.message);
      throw messages.join(' | ');
    }
    if (converted.hscript.indexOf('setProperty("stagelight_right.flipX", true);') < 0)
      throw 'stage light mirror was not emitted';
    new hscript.Parser().parseString(converted.hscript);
  }
}
'''.replace("__SOURCE__", json.dumps(WEINER_STAGE.read_text()))
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_whitty_stage_static_helpers_are_translated_and_class_properties_stay_explicit(self):
        if not WHITTY_ALLEY_BALLS.exists():
            self.skipTest("example donor is not mounted")
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var converted = PsychStageCompat.translateFile("/run/media/cammie/External Storage/FNF-Example-Mods/psych/vswhitty/stages/alley-balls-hqr.lua");
        for (expected in [
            'setGraphicSize("eff", 1280, 720);',
            'updateHitbox("eff");',
            'setBlendMode("eff", "multiply");'
        ])
            if (converted.hscript.indexOf(expected) < 0) throw 'missing translated helper: ' + expected;
        var classPropertyDiagnostic = 0;
        for (diagnostic in converted.diagnostics)
            if (diagnostic.code == 'unsupported-stage-api' && diagnostic.message.indexOf('setPropertyFromClass') >= 0)
                classPropertyDiagnostic++;
        if (classPropertyDiagnostic != 0 || converted.hscript.indexOf(
            'currentPlayState.setPsychClassProperty("GameOverSubstate", "deathSoundName", "fnf_loss_sfx-hqr");') < 0)
            throw 'GameOverSubstate death sound was not routed: ' + converted.hscript;
        new hscript.Parser().parseString(converted.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_terminal_close_and_add_sprite_layer_literals_are_safe(self):
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "  makeLuaSprite('nilLayer', 'nil-layer', 0, 0)\n"
            + "  addLuaSprite('nilLayer', nil)\n"
            + "  makeLuaSprite('dynamicLayer', 'dynamic-layer', 0, 0)\n"
            + "  addLuaSprite('dynamicLayer', selectedLayer)\n"
            + "  close(true)\n"
            + "end\n"
            + "function onCreatePost()\n"
            + "  setProperty('nilLayer.visible', false)\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'generic-stage.lua');
        var foundDynamicLayer = false;
        var closeDiagnostic = false;
        for (diagnostic in converted.diagnostics) {
            if (diagnostic.code == 'dynamic-stage-layer') foundDynamicLayer = true;
            if (diagnostic.code == 'unsupported-stage-api' && diagnostic.message.indexOf('close') >= 0)
                closeDiagnostic = true;
        }
        if (!foundDynamicLayer || closeDiagnostic) throw 'layer/close diagnostics: ' + converted.hscript;
        if (converted.hscript.indexOf('addLuaSprite("nilLayer", false);') < 0
            || converted.hscript.indexOf('addLuaSprite("dynamicLayer", false);') < 0)
            throw 'layer fallback was not emitted: ' + converted.hscript;
        if (converted.runtimeCallbacks.length != 1 || converted.runtimeCallbacks[0] != 'onCreatePost'
            || converted.hscript.indexOf('function onCreatePost()') < 0)
            throw 'onCreatePost was not retained: ' + converted.hscript;
        new hscript.Parser().parseString(converted.hscript);

        var nonTerminal = PsychStageCompat.translate(
            "function onCreate()\n  close(true)\n  makeLuaSprite('later', 'later', 0, 0)\nend\n",
            'non-terminal-close.lua');
        var rejectedClose = false;
        for (diagnostic in nonTerminal.diagnostics)
            if (diagnostic.code == 'unsupported-stage-api' && diagnostic.message.indexOf('close') >= 0)
                rejectedClose = true;
        if (!rejectedClose) throw 'non-terminal close was silently discarded';
        new hscript.Parser().parseString(nonTerminal.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_whitty_close_nil_and_dynamic_layer_behaviors(self):
        if not WHITTY_ALLEY.exists() or not WHITTY_4CHAN.exists():
            self.skipTest("Whitty example donor stages are not mounted")
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var alley = PsychStageCompat.translateFile("/run/media/cammie/External Storage/FNF-Example-Mods/psych/vswhitty/stages/alley.lua");
        if (alley.hscript.indexOf('addLuaSprite("stageback", false);') < 0
            || alley.hscript.indexOf('addLuaSprite("stagefront", false);') < 0)
            throw 'Whitty alley sprite setup was lost: ' + alley.hscript;
        if (alley.hscript.indexOf('close(') >= 0)
            throw 'terminal state cleanup leaked into HScript: ' + alley.hscript;
        for (diagnostic in alley.diagnostics)
            if (diagnostic.code == 'unsupported-stage-api' && diagnostic.message.indexOf('close') >= 0)
                throw 'terminal close was diagnosed: ' + diagnostic.message;
        new hscript.Parser().parseString(alley.hscript);

        var fourChan = PsychStageCompat.translateFile("/run/media/cammie/External Storage/FNF-Example-Mods/psych/vswhitty/stages/4chan.lua");
        var foundDynamicLayer = false;
        var closeDiagnostic = false;
        var classPropertyCalls = 0;
        for (diagnostic in fourChan.diagnostics) {
            if (diagnostic.code == 'dynamic-stage-layer') foundDynamicLayer = true;
            if (diagnostic.code == 'unsupported-stage-api' && diagnostic.message.indexOf('close') >= 0)
                closeDiagnostic = true;
            if (diagnostic.code == 'unsupported-stage-api' && diagnostic.message.indexOf('setPropertyFromClass') >= 0)
                classPropertyCalls++;
        }
        if (!foundDynamicLayer || closeDiagnostic || classPropertyCalls != 0)
            throw 'Whitty 4chan diagnostics layer=' + foundDynamicLayer + ' close=' + closeDiagnostic
                + ' classPropertyCalls=' + classPropertyCalls;
        for (field in ['characterName', 'deathSoundName', 'loopSoundName', 'endSoundName'])
            if (fourChan.hscript.indexOf('currentPlayState.setPsychClassProperty("GameOverSubstate", "'
                + field + '"') < 0) throw 'missing song-owned game-over audio ' + field;
        if (fourChan.hscript.indexOf('addLuaSprite("stageback", false);') < 0
            || fourChan.hscript.indexOf('close(') >= 0)
            throw 'Whitty 4chan static fallback: ' + fourChan.hscript;
        if (fourChan.runtimeCallbacks.indexOf('onCreatePost') < 0
            || fourChan.hscript.indexOf('function onCreatePost()') < 0)
            throw 'Whitty 4chan onCreatePost was not preserved: ' + fourChan.hscript;
        new hscript.Parser().parseString(fourChan.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_static_helper_calls_keep_dynamic_and_unresolved_arguments_diagnostic(self):
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "  makeLuaSprite('eff', 'effect', 0, 0)\n"
            + "  setGraphicSize('eff', screenWidth, 720)\n"
            + "  updateHitbox(dynamicTag)\n"
            + "  setBlendMode('eff', selectedMode)\n"
            + "  setProperty('eff.visible', shouldShow)\n"
            + "  setGraphicSize('missing', 320)\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'dynamic-helpers.lua');
        var found = new Map<String, Bool>();
        for (diagnostic in converted.diagnostics) found.set(diagnostic.code, true);
        for (code in ['dynamic-stage-graphic-size', 'dynamic-stage-target', 'dynamic-stage-blend-mode',
            'dynamic-stage-property', 'unknown-stage-sprite'])
            if (!found.exists(code)) throw 'missing diagnostic ' + code;
        for (unsupported in ['setGraphicSize("eff"', 'updateHitbox("', 'setBlendMode("eff"', 'setProperty("eff.visible"'])
            if (converted.hscript.indexOf(unsupported) >= 0) throw 'dynamic call was emitted: ' + unsupported;
        new hscript.Parser().parseString(converted.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_perfexion_haven_is_staticly_recovered_without_editing_donor(self):
        if not HAVEN.exists():
            self.skipTest("example donor is not mounted")
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var path = "/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/stages/Haven.lua";
        var converted = PsychStageCompat.translateFile(path);
        if (converted.sprites.length < 6) throw 'Haven sprite count: ' + converted.sprites.length;
        var rock:Dynamic = null;
        var cloud:Dynamic = null;
        for (sprite in converted.sprites) {
            if (sprite.tag == 'rock') rock = sprite;
            if (sprite.tag == 'cloud1b') cloud = sprite;
        }
        if (rock == null || rock.image != 'Haven/EternityRock' || rock.scaleX != 1.5)
            throw 'Haven rock metadata';
        if (cloud == null || cloud.x != -15010 || cloud.scaleY != -5)
            throw 'Haven cloud metadata: ' + (cloud == null ? 'missing' : cloud.x + '/' + cloud.scaleY);
        if (converted.hscript.indexOf('makeAnimatedLuaSprite("CloudsLoop", "Haven/CloudsLoop"') < 0
            || converted.hscript.indexOf('addAnimationByPrefix("CloudsLoop", "loop", "Loop", 25, true);') < 0
            || converted.hscript.indexOf('addLuaSprite("rock", false);') < 0)
            throw 'Haven generated stage setup';
        if (converted.runtimeCallbacks.length != 2
            || converted.runtimeCallbacks[0] != 'onUpdate'
            || converted.runtimeCallbacks[1] != 'onTweenCompleted'
            || converted.hscript.indexOf('function onUpdate(?elapsed)') < 0
            || converted.hscript.indexOf('function onTweenCompleted(?tag)') < 0)
            throw 'Haven runtime callbacks were not preserved';
        new hscript.Parser().parseString(converted.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_haven_runtime_cloud_motion_and_reset_route_execute(self):
        if not HAVEN.exists():
            self.skipTest("example donor is not mounted")
        fixture = r'''
class PsychStageCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var converted = PsychStageCompat.translateFile("/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/stages/Haven.lua");
        var program = new hscript.Parser().parseString(converted.hscript);
        var objects:Map<String, Dynamic> = new Map<String, Dynamic>();
        var tweens:Array<String> = [];
        var interp = new hscript.Interp();
        var make = function(tag:String, image:String, x:Float, y:Float):Dynamic {
            var object:Dynamic = {x: x, y: y, scaleX: 1.0, scaleY: 1.0};
            objects.set(tag, object);
            return object;
        };
        interp.variables.set('makeLuaSprite', make);
        interp.variables.set('makeAnimatedLuaSprite', make);
        interp.variables.set('addLuaSprite', function(tag:String, front:Bool = false) {});
        interp.variables.set('addAnimationByPrefix', function(tag:String, name:String, prefix:String, fps:Float = 24, looped:Bool = true) {});
        interp.variables.set('objectPlayAnimation', function(tag:String, name:String, force:Bool = false) {});
        interp.variables.set('scaleObject', function(tag:String, x:Float, y:Float = 0) {});
        interp.variables.set('setScrollFactor', function(tag:String, x:Float, y:Float = 0) {});
        interp.variables.set('setObjectCamera', function(tag:String, camera:String) {});
        interp.variables.set('setDefaultZoom', function(zoom:Float) {});
        interp.variables.set('getColorFromHex', function(value:String):Int return 0);
        interp.variables.set('getProperty', function(path:String):Dynamic {
            var parts = path.split('.');
            return Reflect.field(objects.get(parts[0]), parts[1]);
        });
        interp.variables.set('setProperty', function(path:String, value:Dynamic) {
            var parts = path.split('.');
            Reflect.setField(objects.get(parts[0]), parts[1], value);
        });
        interp.variables.set('doTweenX', function(tag:String, object:String, value:Float, duration:Float, ease:String) {
            tweens.push(tag + ':' + object + ':' + value);
        });
        interp.variables.set('camGame', {bgColor: 0});
        interp.execute(program);
        var start:Dynamic = interp.variables.get('start');
        start('Haven');
        var update:Dynamic = interp.variables.get('onUpdate');
        update(0.033);
        if (Math.abs(objects.get('cloud1a').x - (-1.75)) > 0.0001
            || Math.abs(objects.get('cloud1b').x - (-15001.75)) > 0.0001)
            fail('Haven cloud motion was not preserved');
        objects.get('cloud1a').x = 4001;
        update(0.033);
        if (tweens.length != 2 || tweens[0].indexOf('cloud1aReset:cloud1a:-10') < 0
            || tweens[1].indexOf('cloud1bReset:cloud1b:-15010') < 0)
            fail('Haven cloud reset tweens were not preserved: ' + tweens.join('|'));
        var completed:Dynamic = interp.variables.get('onTweenCompleted');
        completed('cloud1aReset');
        objects.get('cloud1a').x = 0;
        update(0.033);
        if (Math.abs(objects.get('cloud1a').x - 8.25) > 0.0001)
            fail('Haven tween completion did not release cloud motion');
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unsupported_static_calls_are_explicit(self):
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "  makeLuaSprite('bg', 'bg', 0, 0)\n"
            + "  mysteryStageHelper('bg')\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'unsupported.lua');
        var found = false;
        for (diagnostic in converted.diagnostics)
            if (diagnostic.code == 'unsupported-stage-api' && diagnostic.message.indexOf('mysteryStageHelper') >= 0)
                found = true;
        if (!found || converted.supported) throw 'unsupported stage API was hidden';
        new hscript.Parser().parseString(converted.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_image_keys_use_global_assets_images_resolution(self):
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "  makeLuaSprite('bg', 'stage/bg', 0, 0)\n"
            + "  addLuaSprite('bg', false)\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'assets/stages/foo.lua');
        if (converted.hscript.indexOf('makeLuaSprite("bg", "stage/bg", 0, 0)') < 0)
            throw 'Psych image key was made relative to the stage script: ' + converted.hscript;
        if (converted.hscript.indexOf('hscriptPath + "stage/bg') >= 0)
            throw 'stage-local image path leaked into generated HScript';
        new hscript.Parser().parseString(converted.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_static_order_and_reuse_flags_route_through_tag_helpers(self):
        fixture = r'''
class PsychStageCompatTest {
    static function main() {
        var source = "function onCreate()\n"
            + "  makeLuaSprite('back', 'back', 0, 0)\n"
            + "  addLuaSprite('back', false)\n"
            + "  makeLuaSprite('front', 'front', 0, 0)\n"
            + "  addLuaSprite('front', true)\n"
            + "  setObjectOrder('front', getObjectOrder('back') + 1)\n"
            + "  removeLuaSprite('back', false)\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'order.lua');
        if (converted.hscript.indexOf('setObjectOrder("front", (getObjectOrder("back") + 1), false);') < 0)
            throw 'order helper route: ' + converted.hscript;
        if (converted.hscript.indexOf('removeLuaSprite("back", false);') < 0)
            throw 'non-destructive remove route: ' + converted.hscript;
        var back = converted.sprites[0];
        var front = converted.sprites[1];
        if (!back.added || !back.removed || !front.added || front.order != null)
            throw 'order/removal metadata';
        new hscript.Parser().parseString(converted.hscript);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_callbacks_execute_through_centralized_helpers(self):
        fixture = r'''
class PsychStageCompatTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var source = "function onCreate()\n"
            + "  makeLuaSprite('cloud', 'cloud', 0, 0)\n"
            + "  addLuaSprite('cloud', false)\n"
            + "end\n"
            + "function onCreatePost()\n"
            + "  setObjectOrder('cloud', 2)\n"
            + "end\n"
            + "function onUpdate(elapsed)\n"
            + "  setProperty('cloud.x', getProperty('cloud.x') + 10 * elapsed)\n"
            + "end\n"
            + "function onBeatHit()\n"
            + "  setProperty('cloud.x', getProperty('cloud.x') + 1)\n"
            + "end\n"
            + "function onStepHit()\n"
            + "  setProperty('cloud.x', getProperty('cloud.x') + 2)\n"
            + "end\n"
            + "function onEvent(name, value1, value2)\n"
            + "  if name == 'Move' then setProperty('cloud.x', value1) end\n"
            + "end\n";
        var converted = PsychStageCompat.translate(source, 'runtime.lua');
        if (converted.runtimeCallbacks.length != 5)
            fail('callback count: ' + converted.runtimeCallbacks.length);
        var program = new hscript.Parser().parseString(converted.hscript);
        var objects:Map<String, Dynamic> = new Map<String, Dynamic>();
        var order:Int = -1;
        var interp = new hscript.Interp();
        interp.variables.set('makeLuaSprite', function(tag:String, image:String, x:Float, y:Float) {
            var object:Dynamic = {x: x, visible: true};
            objects.set(tag, object);
            return object;
        });
        interp.variables.set('addLuaSprite', function(tag:String, front:Bool = false) {});
        interp.variables.set('setObjectOrder', function(tag:String, value:Dynamic, front:Bool = false) {
            order = Std.int(Std.parseFloat(Std.string(value)));
        });
        interp.variables.set('getObjectOrder', function(tag:String):Int return 1);
        interp.variables.set('getProperty', function(path:String):Dynamic {
            var parts = path.split('.');
            return objects.get(parts[0]).x;
        });
        interp.variables.set('setProperty', function(path:String, value:Dynamic) {
            var number = Std.parseFloat(Std.string(value));
            objects.get(path.split('.')[0]).x = Math.isNaN(number) ? value : number;
        });
        interp.execute(program);
        var start:Dynamic = interp.variables.get('start');
        start('runtime');
        var createPost:Dynamic = interp.variables.get('onCreatePost');
        createPost();
        if (order != 2)
            fail('createPost order: ' + order);
        var update:Dynamic = interp.variables.get('onUpdate');
        update(0.5);
        if (objects.get('cloud').x != 5)
            fail('onUpdate execution x=' + objects.get('cloud').x);
        var beat:Dynamic = interp.variables.get('onBeatHit');
        var step:Dynamic = interp.variables.get('onStepHit');
        beat(); step();
        if (objects.get('cloud').x != 8)
            fail('beat/step execution: ' + objects.get('cloud').x);
        var event:Dynamic = interp.variables.get('onEvent');
        event('Move', 42, '');
        if (objects.get('cloud').x != 42)
            fail('event execution: ' + objects.get('cloud').x);
        Sys.println('ok');
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
