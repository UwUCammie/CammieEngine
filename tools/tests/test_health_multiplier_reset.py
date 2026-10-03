"""Song-specific health multipliers must not leak into the next PlayState."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'source/PlayState.hx'


def reset_method(source):
    start = source.index('\tstatic function resetSongHealthMultipliers()')
    end = source.index('\n\t}', start) + len('\n\t}')
    return source[start:end]


class HealthMultiplierResetTest(unittest.TestCase):
    def test_reset_restores_defaults(self):
        method = reset_method(SOURCE.read_text())
        fixture = '''class Probe {
\tpublic static var healthLossMultiplier:Float = 0;
\tpublic static var healthGainMultiplier:Float = 0;
''' + method + '''
\tstatic function main() {
\t\tresetSongHealthMultipliers();
\t\tif (healthLossMultiplier != 1) throw "health loss leaked";
\t\tif (healthGainMultiplier != 1) throw "health gain leaked";
\t}
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'Probe.hx').write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder,
                '-main', 'Probe', '--interp'
            ], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reset_precedes_current_song_modifiers(self):
        source = SOURCE.read_text()
        create = source[source.index('override public function create()'):]
        reset = create.index('resetSongHealthMultipliers();')
        modifiers = create.index('ModifierState.namedModifiers.healthgain')
        self.assertLess(reset, modifiers)

    def test_control_loaded_contains_the_regression_trigger(self):
        fixture = ROOT / 'assets/data/control-loaded/modchart.hscript'
        if not fixture.is_file():
            self.skipTest(f'mounted Control Loaded modchart fixture unavailable: {fixture}')
        script = fixture.read_text()
        self.assertIn('PlayState.healthGainMultiplier = 0;', script)


if __name__ == '__main__':
    unittest.main()
