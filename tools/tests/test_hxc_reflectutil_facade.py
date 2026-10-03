"""Focused coverage for imported HXC ReflectUtil calls."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class HxcReflectUtilFacadeTest(unittest.TestCase):
    def test_class_names_and_anonymous_fields_have_native_facade(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        source = r'''import fixture.nativeclasses.StoryMenuState;
import fixture.nativeclasses.FreeplayState;
class Main {
    static function fail(message:String):Void throw message;
    static function main() {
    var reflectUtil = HxcCompatRuntime.reflectUtilFacade();
    var getClassNameOf:Dynamic = Reflect.field(reflectUtil, "getClassNameOf");
    var getAnonymousField:Dynamic = Reflect.field(reflectUtil, "getAnonymousField");
    var storyName = Reflect.callMethod(null, getClassNameOf, [new StoryMenuState()]);
    var freeplayName = Reflect.callMethod(null, getClassNameOf, [new FreeplayState()]);
    if (storyName != "funkin.ui.story.StoryMenuState")
      fail("StoryMenuState compatibility name: " + storyName);
    if (freeplayName != "funkin.ui.freeplay.FreeplayState")
      fail("FreeplayState compatibility name: " + freeplayName);
    var easing = Reflect.callMethod(null, getAnonymousField, [{easeInQuad: 7}, "easeInQuad"]);
    if (easing != 7 || Reflect.callMethod(null, getAnonymousField, [null, "easeInQuad"]) != null
      || Reflect.callMethod(null, getClassNameOf, [null]) != null)
      fail("ReflectUtil facade changed null/field lookup semantics");
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture = Path(folder) / "fixture/nativeclasses"
            fixture.mkdir(parents=True)
            (fixture / "StoryMenuState.hx").write_text(
                "package fixture.nativeclasses; class StoryMenuState { public function new() {} }"
            , newline='\n')
            (fixture / "FreeplayState.hx").write_text(
                "package fixture.nativeclasses; class FreeplayState { public function new() {} }"
            , newline='\n')
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_translated_hxc_import_can_call_reflectutil_methods(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        donor = r'''import funkin.util.ReflectUtil;
class ReflectUtilProbe extends Song {
  function onUpdate(event) {
    if (ReflectUtil.getClassNameOf(FlxG.state) == "funkin.ui.story.StoryMenuState") {
      var easing = ReflectUtil.getAnonymousField(FlxEase, "linear");
      if (easing != 7) throw "anonymous field mismatch";
      trace("reflectutil-in-hxc-ok");
    }
  }
}'''
        source = f'''import hscript.Interp;
import hscript.Parser;
import fixture.nativeclasses.StoryMenuState;
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var result = HxcCompat.analyze({json.dumps(donor)}, "scripts/songs/reflect-util-probe.hxc");
    var interp = new Interp();
    interp.variables.set("FlxG", {{state: new StoryMenuState()}});
    interp.variables.set("FlxEase", {{linear: 7}});
    interp.variables.set("ReflectUtil", HxcCompatRuntime.reflectUtilFacade());
    interp.execute(new Parser().parseString(result.generatedHscript));
    var callback:Dynamic = interp.variables.get("update");
    if (callback == null) fail("HXC update callback was not generated");
    Reflect.callMethod(null, callback, [{{}}]);
  }}
}}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture = Path(folder) / "fixture/nativeclasses"
            fixture.mkdir(parents=True)
            (fixture / "StoryMenuState.hx").write_text(
                "package fixture.nativeclasses; class StoryMenuState { public function new() {} }"
            , newline='\n')
            (Path(folder) / "Main.hx").write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("reflectutil-in-hxc-ok", result.stdout)

    def test_playstate_seeds_facade_only_for_hxc_interpreters(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        branch = source[source.index("if (isHxcSource) {"):source.index("interp.variables.set(\"Conductor\"")]
        self.assertIn("interp.variables.set('ReflectUtil', HxcCompatRuntime.reflectUtilFacade());", branch)
        before_hxc = source[source.index("// set vars"):source.index("if (isHxcSource) {")]
        self.assertNotIn('interp.variables.set("ReflectUtil"', before_hxc)


if __name__ == "__main__":
    unittest.main()
