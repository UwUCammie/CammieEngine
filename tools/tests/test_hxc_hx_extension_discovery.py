"""Scripted classes in `.hx` files and import.hx(c) package defaults are discovered like `.hxc`."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]

# A generated scripts tree in the shape newer V-Slice packages ship: class
# files in both extensions, import defaults at the root and in one package,
# and classless HScript of the kind Psych-family mods keep in `.hx`.
FILES = {
    "scripts/import.hx": "// shared imports\nimport flixel.FlxG;\nimport flixel.tweens.FlxTween;\n#if mobile\nimport touch.Pad;\n#end\nusing StringTools;\n",
    "scripts/modules/import.hx": "import funkin.modding.module.Module;\nimport flixel.FlxG; /* repeated */\nimport funkin.play.PlayState as Play;\n",
    "scripts/modules/ClassModule.hx": "class ClassModule extends Module {\n  public function new() { super('ClassModule'); }\n}\n",
    "scripts/modules/OldModule.hxc": "class OldModule extends Module {\n  public function new() { super('OldModule'); }\n}\n",
    "scripts/modules/Helper.hx": "function onCreate() { trace('classless'); }\n",
    "scripts/modules/Mobile.hx": "#if mobile\nclass Mobile extends Module {}\n#end\n",
    "scripts/songs/test-song.hx": "class TestSong extends Song {\n  public function new() { super('test-song'); }\n}\n",
    "scripts/stages/import.hxc": "import funkin.play.stage.Stage;\n",
    "scripts/stages/Plain.hx": "class Plain extends FlxSprite {}\n",
    "data/notescripts/Outside.hx": "class Outside extends Module {}\n",
}


class HxExtensionDiscoveryTest(unittest.TestCase):
    def test_hx_classes_import_defaults_and_classless_scripts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder) / "pack"
            for relative, text in FILES.items():
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, newline="\n")
            root = str(base / "scripts").replace("\\", "/")
            main = '''class Main {
  static function fail(value:String):Void throw value;
  static function names(paths:Array<String>):String {
    var result = [for (path in paths) haxe.io.Path.withoutDirectory(path)];
    result.sort(Reflect.compare);
    return result.join(",");
  }
  static function main() {
    var root = "%ROOT%";
    var plan = HxcScriptDiscovery.discoverRoot(root, "test-song");
    if (names(plan.all) != "ClassModule.hx,OldModule.hxc,test-song.hx") fail("all " + names(plan.all));
    if (names(plan.families.get("module")) != "ClassModule.hx,OldModule.hxc") fail("modules");
    if (names(plan.chart) != "test-song.hx") fail("song script");
    if (HxcScriptDiscovery.familyForPath(root + "/modules/Helper.hx") != "unknown") fail("classless hx");
    if (HxcScriptDiscovery.familyForPath(root + "/modules/import.hx") != "unknown") fail("import defaults file");
    if (HxcScriptDiscovery.familyForPath(root + "/stages/import.hxc") != "unknown") fail("hxc import defaults file");
    if (HxcScriptDiscovery.familyForPath(root + "/stages/Plain.hx") != "unknown") fail("unknown base");
    if (HxcScriptDiscovery.isScriptedClassFile(root + "/modules/Mobile.hx")) fail("inactive branch class");
    if (HxcScriptDiscovery.isScriptedClassFile("%BASE%/data/notescripts/Outside.hx")) fail("outside scripts tree");
    if (!HxcScriptDiscovery.isScriptedClassFile("x/scripts/a.hx", "class A extends Stage {}")) fail("source text");
    // The word pre-check must not change the answer either way.
    if (!HxcScriptDiscovery.isScriptedClassFile("x/scripts/a.hx", "class\\tA\\n\\textends Song {}")) fail("split declaration");
    if (HxcScriptDiscovery.isScriptedClassFile("x/scripts/b.hx", "// class notes\\nfunction f() {}")) fail("class word only");
    if (HxcScriptDiscovery.isScriptedClassFile("x/scripts/c.hx", "var s = 'extends';\\nfunction f() {}")) fail("extends word only");

    var defaults = HxcScriptDiscovery.importDefaults(root + "/modules/ClassModule.hx").join("|");
    var expected = "import flixel.FlxG;|import flixel.tweens.FlxTween;|using StringTools;"
      + "|import funkin.modding.module.Module;|import funkin.play.PlayState as Play;";
    if (defaults != expected) fail("module defaults " + defaults);
    var stage = HxcScriptDiscovery.importDefaults(root + "/stages/Any.hxc").join("|");
    if (stage != "import flixel.FlxG;|import flixel.tweens.FlxTween;|using StringTools;|import funkin.play.stage.Stage;")
      fail("stage defaults " + stage);
    if (HxcScriptDiscovery.importStatements("import a.b.*; import 1bad.X; importer.thing(); import a b c;").join("|") != "import a.b.*;")
      fail("statement filter");
  }
}
'''.replace("%ROOT%", root).replace("%BASE%", str(base).replace("\\", "/"))
            (Path(folder) / "Main.hx").write_text(main, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "--run", "Main"],
                cwd=folder, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
