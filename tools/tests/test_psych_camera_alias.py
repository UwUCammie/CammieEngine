"""Regression coverage for Psych's separate camHUD and camOther layers."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychCameraAliasTest(unittest.TestCase):
    def test_psych_camera_routes_keep_overlay_independent_from_hidden_hud(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        layer = extract_method(source, "public static function psychCameraLayerName")
        camera = extract_method(source, "function compatCameraForName")
        camera = camera.replace(":FlxCamera", ":FixtureCamera")
        fixture = """
class FixtureCamera {
  public var alpha:Float;
  public function new(alpha:Float) this.alpha = alpha;
}
class PsychCameraLayerCompat {
  var camGame:FixtureCamera;
  var camHUD:FixtureCamera;
  var camOther:FixtureCamera;
  public function new() {
    camGame = new FixtureCamera(1);
    camHUD = new FixtureCamera(1);
    camOther = new FixtureCamera(1);
  }
{layer}
{camera}
  static function main() {
    var state = new PsychCameraLayerCompat();
    state.camHUD.alpha = 0;
    if (state.compatCameraForName("camOther") != state.camOther)
      throw "camOther route collapsed into the HUD camera";
    if (state.compatCameraForName("other") != state.camOther)
      throw "other alias did not select the overlay camera";
    if (state.compatCameraForName("camHUD") != state.camHUD)
      throw "camHUD route changed";
    if (state.compatCameraForName("camGame") != state.camGame)
      throw "camGame route changed";
    if (state.camOther.alpha != 1 || state.compatCameraForName("camOther").alpha == 0)
      throw "overlay camera inherited HUD alpha";
    if (psychCameraLayerName("camGameHud") != "hud"
      || psychCameraLayerName(null) != "game")
      throw "camera alias normalization changed";
  }
}
""".replace("{layer}", layer).replace("{camera}", camera)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PsychCameraLayerCompat.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "PsychCameraLayerCompat", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_camera_stack_and_property_routes_expose_camother_above_hud(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        init_start = play_state.index("camGame = new CompatCamera();")
        init_end = play_state.index("//dynamicMouse = true;", init_start)
        init = play_state[init_start:init_end]
        self.assertLess(init.index("FlxG.cameras.reset(camGame);"), init.index("FlxG.cameras.add(camHUD, false);"))
        self.assertLess(init.index("FlxG.cameras.add(camHUD, false);"), init.index("FlxG.cameras.add(camOther, false);"))
        self.assertIn("camOther.bgColor.alpha = 0;", init)

        set_camera = extract_method(play_state, "function compatSetObjectCamera")
        self.assertIn("(cast object : FlxBasic).cameras = cameras;", set_camera)
        self.assertIn("Reflect.setProperty(object, 'cameras', cameras);", set_camera)
        property_root = extract_method(play_state, "function compatPropertyRoot")
        self.assertIn("case 'camother' | 'other':\n\t\t\t\treturn camOther;", property_root)

        engine = (ROOT / "source/EngineCompat.hx").read_text()
        root = extract_method(engine, "public static function propertyRoot")
        self.assertIn("case 'camother' | 'other':\n\t\t\t\treturn 'camOther';", root)
        self.assertIn("interp.variables.set(\"camOther\", camOther);", play_state)
        self.assertIn("if (camOther != null)\n\t\t\tcompatResetShaderCache(camOther.flashSprite);", play_state)

        fade = play_state[play_state.index("case 'Camera Fade':") : play_state.index("case 'Lyrics':", play_state.index("case 'Camera Fade':"))]
        self.assertIn("Reflect.field(fadeOptions, 'applyToOther')", fade)
        self.assertIn("fadeApplyOther ? 'other' : (fadeApplyHud ? 'hud' : 'game')", fade)

    def test_camera_assignment_calls_native_basic_setter(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        layer = extract_method(source, "public static function psychCameraLayerName")
        camera = extract_method(source, "function compatCameraForName").replace(":FlxCamera", ":FixtureCamera")
        setter = extract_method(source, "function compatSetObjectCamera")
        fixture = r'''class FixtureCamera { public function new() {} }
class FlxBasic {
 public var cameras(get,set):Array<FixtureCamera>;
 var assigned:Array<FixtureCamera> = null;
 public var writes:Int = 0;
 public function new() {}
 function get_cameras():Array<FixtureCamera> return assigned;
 function set_cameras(value:Array<FixtureCamera>):Array<FixtureCamera> {
  writes++; assigned = value; return value;
 }
}
class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(_phase:String):Void {}
}
class PsychCameraSetterFixture {
 var camGame = new FixtureCamera();
 var camHUD = new FixtureCamera();
 var camOther = new FixtureCamera();
 var sprite = new FlxBasic();
 var psychGlobalProviderFirstSprite:FlxBasic = null;
 public function new() {}
 function markPsychGlobalProviderSpritePhase(_sprite:Dynamic, _phase:String, ?_detail:String):Void {}
 function compatFindObject(_name:Dynamic):Dynamic return sprite;
 __LAYER__
 __CAMERA__
 __SETTER__
 static function main() {
  var state = new PsychCameraSetterFixture();
  state.compatSetObjectCamera('flash', 'camOther');
  if(state.sprite.writes != 1 || state.sprite.cameras[0] != state.camOther)
   throw 'camOther assignment did not invoke FlxBasic.cameras setter';
 }
}'''.replace("__LAYER__", layer).replace("__CAMERA__", camera).replace("__SETTER__", setter)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PsychCameraSetterFixture.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "PsychCameraSetterFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_corpus_camother_calls_route_to_distinct_overlay(self):
        calls = []
        for path in DONOR.rglob("*.lua"):
            text = path.read_text(errors="ignore")
            calls.extend(re.findall(r"\bsetObjectCamera\s*\(([^\n]*)\)", text))
        self.assertGreaterEqual(len(calls), 37)
        cam_other_calls = [call for call in calls if re.search(r"['\"]camOther['\"]", call, re.IGNORECASE)]
        self.assertGreaterEqual(len(cam_other_calls), 9)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("case 'other' | 'camother': 'other';", play_state)
        self.assertIn("case 'other': camOther;", play_state)


if __name__ == "__main__":
    unittest.main()
