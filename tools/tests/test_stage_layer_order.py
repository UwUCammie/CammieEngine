from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class StageLayerOrderTest(unittest.TestCase):
    def test_hscript_layers_keep_backgrounds_in_script_order(self):
        """Repeated BEHIND_ALL calls must not fill actor null slots out of order."""
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tfunction addHscriptSprite(")
        end = source.index("\n\tfunction forgetCutsceneSprite(", start)
        helper = source[start:end]
        fixture = """
class FakeBasic {
 public var cameras:Array<Dynamic> = null;
 public function new() {}
}
class LayerOrderTest {
 var members:Array<FakeBasic> = [];
 var gf:FakeBasic;
 var dad:FakeBasic;
 var boyfriend:FakeBasic;
 var camGame:Dynamic;
 var BEHIND_GF:Int = 1;
 var BEHIND_BF:Int = 2;
 var BEHIND_DAD:Int = 4;
 public function new() {}
 function isScriptObject(value:Dynamic):Bool return value != null;
 function hasExplicitCameras(value:FakeBasic):Bool return value.cameras != null;
 function remove(value:FakeBasic, splice:Bool = false):FakeBasic {
  var index = members.indexOf(value);
  if (index >= 0) {
   if (splice) members.splice(index, 1); else members[index] = null;
  }
  return value;
 }
 function add(value:FakeBasic):FakeBasic {
  var index = members.indexOf(null);
  if (index >= 0) members[index] = value; else members.push(value);
  return value;
 }
 function insert(index:Int, value:FakeBasic):FakeBasic {
  if (index < members.length && members[index] == null) members[index] = value;
  else members.insert(index, value);
  return value;
 }
""" + helper.replace("FlxBasic", "FakeBasic") + """
 static function main() {
  var state = new LayerOrderTest();
  state.gf = new FakeBasic(); state.dad = new FakeBasic(); state.boyfriend = new FakeBasic();
  state.members = [state.gf, state.dad, state.boyfriend];
  var wall = new FakeBasic(); var floor = new FakeBasic(); var beam = new FakeBasic();
  state.addHscriptSprite(wall, 7);
  state.addHscriptSprite(floor, 7);
  state.addHscriptSprite(beam, 7);
  if (state.members[0] != wall || state.members[1] != floor || state.members[2] != beam)
   throw 'backgrounds were not kept in script order';
  if (state.members[3] != state.gf || state.members[4] != state.dad || state.members[5] != state.boyfriend)
   throw 'actor order was changed while layering backgrounds';
 }
}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "LayerOrderTest.hx"
            path.write_text(fixture)
            result = subprocess.run([
                str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                "-main", "LayerOrderTest", "--interp"
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_add_lua_sprite_maps_front_to_actor_relative_layer(self):
        """The live Psych bridge must honor addLuaSprite(tag, front)."""
        source = (ROOT / "source/PlayState.hx").read_text()
        add_start = source.index("\tfunction addHscriptSprite(")
        add_end = source.index("\n\tfunction forgetCutsceneSprite(", add_start)
        add_helper = source[add_start:add_end]
        compat_start = source.index("\tfunction compatAddLuaSprite(")
        compat_end = source.index("\n\tfunction compatRemoveLuaSprite(", compat_start)
        compat_helper = source[compat_start:compat_end]
        fixture = """
class FakeBasic {
 public var cameras:Array<Dynamic> = null;
 public function new() {}
}
class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(_phase:String):Void {}
}
class PsychSpriteLayerTest {
 var members:Array<FakeBasic> = [];
 var haxeSprites:Map<String, FakeBasic> = new Map<String, FakeBasic>();
 var psychGlobalProviderFirstSprite:FakeBasic = null;
 var gf:FakeBasic;
 var dad:FakeBasic;
 var boyfriend:FakeBasic;
 var camGame:Dynamic;
 var BEHIND_NONE:Int = 0;
 var BEHIND_GF:Int = 1;
 var BEHIND_BF:Int = 2;
 var BEHIND_DAD:Int = 4;
 var BEHIND_ALL:Int = 7;
 public function new() {}
 function markPsychGlobalProviderSpritePhase(_sprite:Dynamic, _phase:String, ?_detail:String):Void {}
 function isScriptObject(value:Dynamic):Bool return value != null;
 function hasExplicitCameras(value:FakeBasic):Bool return value.cameras != null;
 function remove(value:FakeBasic, splice:Bool = false):FakeBasic {
  var index = members.indexOf(value);
  if (index >= 0) {
   if (splice) members.splice(index, 1); else members[index] = null;
  }
  return value;
 }
 function add(value:FakeBasic):FakeBasic {
  var index = members.indexOf(null);
  if (index >= 0) members[index] = value; else members.push(value);
  return value;
 }
 function insert(index:Int, value:FakeBasic):FakeBasic {
  if (index < members.length && members[index] == null) members[index] = value;
  else members.insert(index, value);
  return value;
 }
""" + add_helper.replace("FlxBasic", "FakeBasic") + compat_helper + """
 static function main() {
  var state = new PsychSpriteLayerTest();
  state.gf = new FakeBasic(); state.dad = new FakeBasic(); state.boyfriend = new FakeBasic();
  state.members = [state.gf, state.dad, state.boyfriend];
  var background = new FakeBasic(); var foreground = new FakeBasic();
  state.haxeSprites.set("background", background);
  state.haxeSprites.set("foreground", foreground);
  state.compatAddLuaSprite("background", false);
  if (state.members[0] != background || state.members[1] != state.gf)
   throw 'addLuaSprite(tag, false) did not place the sprite behind actors';
  state.compatAddLuaSprite("foreground", true);
  if (state.members[state.members.length - 1] != foreground)
   throw 'addLuaSprite(tag, true) did not place the sprite in front';
 }
}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "PsychSpriteLayerTest.hx"
            path.write_text(fixture)
            result = subprocess.run([
                str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                "-main", "PsychSpriteLayerTest", "--interp"
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_remove_lua_sprite_preserves_non_destructive_tags(self):
        """Psych's destroy=false detaches a tag but allows a later re-add."""
        source = (ROOT / "source/PlayState.hx").read_text()
        add_start = source.index("\tfunction addHscriptSprite(")
        add_end = source.index("\n\tfunction forgetCutsceneSprite(", add_start)
        add_helper = source[add_start:add_end]
        compat_start = source.index("\tfunction compatAddLuaSprite(")
        compat_end = source.index("\n\tfunction compatRunTimer(", compat_start)
        compat_helper = source[compat_start:compat_end]
        fixture = """
class FakeBasic {
 public var cameras:Array<Dynamic> = null;
 public var destroyed:Bool = false;
 public function new() {}
 public function destroy():Void destroyed = true;
}
class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(_phase:String):Void {}
}
class PsychSpriteRemoveTest {
 var members:Array<FakeBasic> = [];
 var haxeSprites:Map<String, FakeBasic> = new Map<String, FakeBasic>();
 var psychGlobalProviderFirstSprite:FakeBasic = null;
 var haxeSpriteAtlasNames:Map<String, Array<String>> = new Map<String, Array<String>>();
 var haxeSpriteAtlasNamesByObject:Map<FakeBasic, Array<String>> = new Map<FakeBasic, Array<String>>();
 var gf:FakeBasic;
 var dad:FakeBasic;
 var boyfriend:FakeBasic;
 var camGame:Dynamic;
 var BEHIND_NONE:Int = 0;
 var BEHIND_GF:Int = 1;
 var BEHIND_BF:Int = 2;
 var BEHIND_DAD:Int = 4;
 var BEHIND_ALL:Int = 7;
 public function new() {}
 function markPsychGlobalProviderSpritePhase(_sprite:Dynamic, _phase:String, ?_detail:String):Void {}
 function compatForgetSpriteAtlas(sprite:Dynamic):Void {}
 function isScriptObject(value:Dynamic):Bool return value != null;
 function hasExplicitCameras(value:FakeBasic):Bool return value.cameras != null;
 function remove(value:FakeBasic, splice:Bool = false):FakeBasic {
  var index = members.indexOf(value);
  if (index >= 0) {
   if (splice) members.splice(index, 1); else members[index] = null;
  }
  return value;
 }
 function add(value:FakeBasic):FakeBasic {
  var index = members.indexOf(null);
  if (index >= 0) members[index] = value; else members.push(value);
  return value;
 }
 function insert(index:Int, value:FakeBasic):FakeBasic {
  if (index < members.length && members[index] == null) members[index] = value;
  else members.insert(index, value);
  return value;
 }
""" + add_helper.replace("FlxBasic", "FakeBasic") + compat_helper + """
 static function main() {
  var state = new PsychSpriteRemoveTest();
  state.gf = new FakeBasic(); state.dad = new FakeBasic(); state.boyfriend = new FakeBasic();
  state.members = [state.gf, state.dad, state.boyfriend];
  var reusable = new FakeBasic();
  state.haxeSprites.set("reusable", reusable);
  state.compatAddLuaSprite("reusable", false);
  state.compatRemoveLuaSprite("reusable", false);
  if (state.haxeSprites.get("reusable") != reusable || state.members.indexOf(reusable) >= 0 || reusable.destroyed)
   throw 'destroy=false did not preserve the tagged object';
  state.compatAddLuaSprite("reusable", true);
  if (state.members[state.members.length - 1] != reusable)
   throw 'preserved object was not re-added in front';
  state.compatRemoveLuaSprite("reusable", true);
  if (state.haxeSprites.exists("reusable") || !reusable.destroyed || state.members.indexOf(reusable) >= 0)
   throw 'destroy=true did not dispose the tagged object';
 }
}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "PsychSpriteRemoveTest.hx"
            path.write_text(fixture)
            result = subprocess.run([
                str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                "-main", "PsychSpriteRemoveTest", "--interp"
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_haven_uses_runtime_background_layer_route(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods/psych/PERFEXION Demo1/stages/Haven.lua")
        if not donor.is_file():
            self.skipTest(f"mounted PERFEXION Haven fixture unavailable: {donor}")
        chart = donor.parent.parent / "data/Resonance/resonance-hard.json"
        if not chart.is_file():
            self.skipTest(f"mounted Resonance chart unavailable: {chart}")
        self.assertIn('"stage": "Haven"', chart.read_text())
        donor_text = donor.read_text()
        for tag in ("CloudsLoop", "rock", "cloud1a", "cloud1b", "cloud2a", "cloud2b"):
            self.assertIn(f"addLuaSprite('{tag}', false)", donor_text)
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("addHscriptSprite(sprite, front ? BEHIND_NONE : BEHIND_ALL);", source)

    def test_chaos_stage_adds_and_primes_the_chamber_graphic(self):
        stage_fixture = ROOT / "assets/images/custom_stages/chamber.hscript"
        cutscene_fixture = ROOT / "assets/images/custom_cutscenes/fleetway.hscript"
        if not stage_fixture.is_file() or not cutscene_fixture.is_file():
            self.skipTest(f"mounted Chaos stage/cutscene fixtures unavailable: {stage_fixture}, {cutscene_fixture}")
        stage = stage_fixture.read_text()
        chaos = stage[:stage.index('if (curSong == "Powerless")')]
        self.assertIn("thechamber.animation.play('a');", chaos)
        self.assertIn("thechamber.animation.pause();", chaos)
        self.assertIn("addSprite(thechamber, BEHIND_ALL);", chaos)
        cutscene = cutscene_fixture.read_text()
        self.assertIn("thechamber.visible = true;", cutscene)
        self.assertIn("thechamber.animation.play('a', true);", cutscene)
        self.assertNotIn("removeSprite(thechamber);", cutscene)

    def test_chaos_intro_preloads_timed_sound_cues(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        fixture = ROOT / "assets/images/custom_cutscenes/fleetway.hscript"
        if not fixture.is_file():
            self.skipTest(f"mounted Chaos cutscene fixture unavailable: {fixture}")
        cutscene = fixture.read_text()
        self.assertIn('public static function preloadHscriptSound', source)
        self.assertIn('interp.variables.set("preloadSound", PlayState.preloadHscriptSound);', source)
        for cue in ('robot', 'sonic', 'beam'):
            self.assertIn(f"preloadSound('assets/sounds/{cue}');", cutscene)
            self.assertIn(f"soundPlaySafe('assets/sounds/{cue}');", cutscene)
