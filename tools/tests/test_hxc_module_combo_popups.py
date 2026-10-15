"""A module helper that moves PlayState.comboPopUps stays executable.

The native PlayState provides a writable comboPopUps.offsets holder, so the
module safety gate must not drop a HUD setup helper (and the state-change
callback that calls it) only because it repositions the combo popups.
"""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"

MODULE = '''import funkin.Preferences;

class ExampleHudModule extends Module
{
    function new() {
        super("ExampleHudModule");
    }

    override function onStateChangeEnd(event:StateChangeScriptEvent) {
        if (PlayState.instance == null) return;
        setupHud();
    }

    function setupHud() {
        var state = PlayState.instance;
        state.healthBarBG.visible = false;
        if (!Preferences.downscroll) PlayState.instance.comboPopUps.offsets = [480, 300];
        else state.comboPopUps.offsets = [480, -150];
        state.refresh();
    }
}
'''

DONOR_ONLY = MODULE.replace('state.comboPopUps.offsets', 'state.donorOnlyPopups.offsets')


class HxcModuleComboPopupsTest(unittest.TestCase):
    def analyze(self, module):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='hxc-combo-popups-', dir=TEST_TMP) as folder:
            path = Path(folder)
            (path / 'module.hxc').write_text(module, newline='\n')
            (path / 'Main.hx').write_text(
                'class Main { static function main() {\n'
                '  var file = ' + repr(str(path / 'module.hxc').replace('\\', '/')).replace("'", '"') + ';\n'
                '  var result = HxcCompat.analyze(sys.io.File.getContent(file), "scripts/modules/ExampleHudModule.hxc");\n'
                '  Sys.println("REASONS=" + result.moduleSafetyReasons.join("|"));\n'
                '} }\n', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT),
                                     '-cp', str(path), '-main', 'Main', '--interp'],
                                    cwd=ROOT, text=True, capture_output=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        line = [l for l in result.stdout.splitlines() if l.startswith('REASONS=')]
        self.assertTrue(line, result.stdout)
        return line[-1][len('REASONS='):]

    def test_combo_popup_offsets_keep_the_helper_safe(self):
        reasons = self.analyze(MODULE)
        self.assertNotIn('unsafe helper setupHud', reasons)

    def test_unknown_playstate_member_still_marks_the_helper_unsafe(self):
        reasons = self.analyze(DONOR_ONLY)
        self.assertIn('unsafe helper setupHud', reasons)


if __name__ == '__main__':
    unittest.main()
