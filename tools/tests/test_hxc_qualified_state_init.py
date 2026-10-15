"""ScriptedMusicBeatState/SubState.init accept V-Slice package-qualified class names."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


class HxcQualifiedStateInitTest(unittest.TestCase):
    def test_quoted_qualified_names_are_lowered(self):
        donor = r'''
class MenuModule extends Module {
    function onStateChangeBegin(event) {
        FlxG.switchState(ScriptedMusicBeatState.init('pack.states.CustomMenu'));
        FlxG.state.openSubState(ScriptedMusicBeatSubState.init("pack.substates.CustomPause"));
        FlxG.switchState(ScriptedMusicBeatState.init('PlainMenu'));
    }
}
'''
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var generated = HxcCompat.analyze(''' + json.dumps(donor) + ''', "scripts/modules/menu.hxc").generatedHscript;
    for (expected in ['hxcStateInit("pack.states.CustomMenu")', 'hxcSubStateInit("pack.substates.CustomPause")',
        'hxcStateInit("PlainMenu")'])
      if (generated.indexOf(expected) < 0) fail("missing " + expected + "\\n" + generated);
    if (generated.indexOf("ScriptedMusicBeat") >= 0) fail("an init call was left in place\\n" + generated);
    Sys.println("state-init-ok");
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                                     "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("state-init-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
