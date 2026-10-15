"""A script that imports the V-Slice options menu can name it bare.

`import funkin.ui.options.OptionsState;` followed by
`Std.isOfType(FlxG.state, OptionsState)` used to leave the bare name unbound,
so every update threw EUnknownVariable(OptionsState).
"""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

DONOR = r'''import funkin.ui.options.OptionsState;
import funkin.modding.module.Module;

class Taunts extends Module {
    public function new() { super('Taunts'); }
    override function onUpdate(event) {
        if (Std.isOfType(FlxG.state, OptionsState)) return;
    }
}
'''

PLAIN = r'''class Other extends Module {
    public function new() { super('Other'); }
    override function onUpdate(event) { var OptionsStateLabel = 1; }
}
'''

MAIN = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var generated = HxcCompat.analyze(%s, "scripts/modules/Taunts.hxc").generatedHscript;
    if (generated.indexOf("OptionsState") >= 0) fail("bare OptionsState left unbound: " + generated);
    if (generated.indexOf("Std.isOfType(FlxG.state, SaveDataState)") < 0) fail("type test not mapped: " + generated);
    var other = HxcCompat.analyze(%s, "scripts/modules/Other.hxc").generatedHscript;
    if (other.indexOf("SaveDataState") >= 0) fail("a script without the import was rewritten: " + other);
    Sys.println("options-ok");
  }
}
'''


class HxcImportedOptionsStateTest(unittest.TestCase):
    def test_bare_options_state_after_its_import_maps_to_the_native_menu(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % (json.dumps(DONOR), json.dumps(PLAIN)), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('options-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
