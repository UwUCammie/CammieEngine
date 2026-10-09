"""The native runner must reject a playing install before writing any files."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

@unittest.skipUnless(os.name == 'nt', 'Windows private desktop runner')
class PrivateVideoRunnerTest(unittest.TestCase):
    def test_outside_runtime_is_untouched(self):
        with tempfile.TemporaryDirectory(dir=Path(os.environ['LOCALAPPDATA'])/'Temp') as directory:
            runtime = Path(directory) / 'playing-install'
            options = runtime / 'assets/data/options.json'
            options.parent.mkdir(parents=True)
            options.write_bytes(b'{"volume":0.5}')
            executable = runtime / 'Funkin.exe'
            executable.write_bytes(b'protected executable')
            before = {p.relative_to(runtime):p.read_bytes() for p in runtime.rglob('*') if p.is_file()}
            result = subprocess.run([sys.executable, str(ROOT/'tools/check_legacy_video_native.py'),
                '--runtime', str(runtime), '--clip', str(executable)], cwd=ROOT,
                capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('disposable game below this checkout tmp directory', result.stderr)
            after = {p.relative_to(runtime):p.read_bytes() for p in runtime.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

if __name__ == '__main__':
    unittest.main()
