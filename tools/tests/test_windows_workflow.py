"""Exercise Windows batch failure propagation and portable test setup."""

import importlib.util
import io
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from haxe_test_support import haxe_command
from tools import file_lock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('workflow_runner', ROOT / 'tools/run_tests.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class WindowsWorkflowTest(unittest.TestCase):
    def test_eval_platform_is_explicit_and_posix_probe_can_opt_out(self):
        self.assertEqual(haxe_command(windows=True)[1:], ['-D', 'windows'])
        self.assertEqual(haxe_command(windows=False)[1:], [])

    def test_fixture_paths_preserve_native_equality_hashing_and_parents(self):
        from pathlib import Path as NativePath
        fixture = Path(ROOT / 'tmp' / 'path with spaces')
        native = NativePath(str(fixture))
        self.assertEqual(fixture, native)
        self.assertEqual(hash(fixture), hash(native))
        self.assertIn(NativePath(str(ROOT)), fixture.parents)
        self.assertNotIn('\\', str(fixture))

    def test_only_missing_symlink_privilege_is_a_fixture_skip(self):
        case = unittest.FunctionTestCase(lambda: None)
        result = RUNNER.FixtureResult(unittest.runner._WritelnDecorator(io.StringIO()), True, 1)
        missing = OSError('symlink unavailable')
        missing.winerror = 1314
        broken = OSError('broken executable')
        broken.winerror = 193
        with patch.object(RUNNER.os, 'name', 'nt'):
            result.addError(case, (OSError, missing, None))
            result.addError(case, (OSError, broken, None))
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(len(result.errors), 1)

    def test_exclusive_file_lock_blocks_then_releases_a_second_process(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            lock_path = Path(directory) / 'runtime.lock'
            script = '''import sys
sys.path.insert(0, sys.argv[2])
from tools import file_lock
with open(sys.argv[1], 'a+b') as handle:
 try: file_lock.flock(handle, file_lock.LOCK_EX | file_lock.LOCK_NB)
 except BlockingIOError: sys.exit(17)
'''
            with lock_path.open('a+b') as handle:
                file_lock.flock(handle, file_lock.LOCK_EX)
                locked = subprocess.run([sys.executable, '-c', script, str(lock_path), str(ROOT)], cwd=ROOT)
                self.assertEqual(locked.returncode, 17)
                file_lock.flock(handle, file_lock.LOCK_UN)
            released = subprocess.run([sys.executable, '-c', script, str(lock_path), str(ROOT)], cwd=ROOT)
            self.assertEqual(released.returncode, 0)

    @unittest.skipUnless(os.name == 'nt', 'native Windows batch workflow')
    def test_package_stops_at_build_or_test_failure_and_handles_spaces(self):
        for build_code, test_code, expected in ((7, 0, ['build']), (0, 8, ['build', 'updater', 'tests']), (0, 0, ['build', 'updater', 'tests', 'package'])):
            with self.subTest(build_code=build_code, test_code=test_code):
                with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
                    project = Path(directory) / 'project with spaces'
                    project.mkdir()
                    (project / 'tools').mkdir()
                    original = (ROOT / 'run.bat').read_text(encoding='utf-8')
                    main = original[:original.index('\n:build_update_helper')]
                    stubs = '\n:ensure_toolchain\nset PYTHON_COMMAND="' + sys.executable + '"\nexit /b 0\n'
                    for label in ('ensure_astc_decoder', 'ensure_haxelibs', 'ensure_shared_haxelib_patches', 'patch_haxelibs', 'ensure_asset_scaffolding', 'ensure_native_compiler', 'sync_astc_decoder', 'sync_compiler_runtime'):
                        stubs += '\n:' + label + '\nexit /b 0\n'
                    stubs += '\n:build_update_helper\necho updater>>events.txt\nexit /b 0\n'
                    (project / 'run.bat').write_bytes((main + stubs).replace('\n', '\r\n').encode())
                    build = '@echo off\necho build>>events.txt\nif not exist export\\release\\windows\\bin mkdir export\\release\\windows\\bin\ncopy /Y nul export\\release\\windows\\bin\\Funkin.exe >nul\nexit /b ' + str(build_code) + '\n'
                    (project / 'haxelib.cmd').write_bytes(build.replace('\n', '\r\n').encode())
                    (project / 'tools/run_tests.py').write_text("from pathlib import Path\nwith Path('events.txt').open('a') as output: output.write('tests\\n')\nraise SystemExit(" + str(test_code) + ')\n', encoding='utf-8', newline='\n')
                    (project / 'tools/package_windows_release.py').write_text("from pathlib import Path\nwith Path('events.txt').open('a') as output: output.write('package\\n')\n", encoding='utf-8', newline='\n')
                    (project / 'tools/sync_windows_audio.py').write_text('pass\n', encoding='utf-8', newline='\n')
                    environment = {**os.environ, 'PATH': str(project) + os.pathsep + os.environ['PATH']}
                    result = subprocess.run(['cmd', '/c', str(project / 'run.bat'), 'package'], cwd=ROOT, env=environment, capture_output=True, text=True)
                    self.assertEqual((project / 'events.txt').read_text().splitlines(), expected, result.stdout + result.stderr)
                    self.assertEqual(result.returncode == 0, build_code == 0 and test_code == 0)


if __name__ == '__main__':
    unittest.main()
