"""Exercise Windows batch failure propagation and portable test setup."""

import importlib.util
import io
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
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
                    shutil.copy2(ROOT / 'tools/launch_cache.py', project / 'tools/launch_cache.py')
                    original = (ROOT / 'run.bat').read_text(encoding='utf-8')
                    (project / 'tools/is_explorer_parent.ps1').write_text(
                        (ROOT / 'tools/is_explorer_parent.ps1').read_text(encoding='utf-8'),
                        encoding='utf-8', newline='\n')
                    main = original[:original.index('\n:build_update_helper')]
                    stubs = '\n:ensure_python\nset PYTHON_COMMAND="' + sys.executable + '"\nexit /b 0\n'
                    stubs += '\n:ensure_toolchain\nset PYTHON_COMMAND="' + sys.executable + '"\nexit /b 0\n'
                    for label in ('ensure_git', 'ensure_astc_decoder', 'ensure_haxelibs', 'ensure_shared_haxelib_patches', 'patch_haxelibs', 'ensure_asset_scaffolding', 'ensure_native_compiler', 'probe_native_compiler', 'configure_mingw_environment', 'ensure_lime_uncapped', 'sync_astc_decoder', 'sync_compiler_runtime'):
                        stubs += '\n:' + label + '\nexit /b 0\n'
                    stubs += '\n:build_update_helper\necho updater>>events.txt\nexit /b 0\n'
                    (project / 'run.bat').write_bytes((main + stubs).replace('\n', '\r\n').encode())
                    build = ('@echo off\necho build>>events.txt\n'
                             'if not exist export\\release\\windows\\bin\\assets mkdir export\\release\\windows\\bin\\assets\n'
                             'if not exist export\\release\\windows\\bin\\tools mkdir export\\release\\windows\\bin\\tools\n'
                             'if not exist export\\release\\windows\\bin\\manifest mkdir export\\release\\windows\\bin\\manifest\n'
                             'copy /Y nul export\\release\\windows\\bin\\Funkin.exe >nul\n'
                             'copy /Y nul export\\release\\windows\\bin\\lime.ndll >nul\n'
                             'copy /Y nul export\\release\\windows\\bin\\CammieUpdateHelper.exe >nul\n'
                             'copy /Y nul export\\release\\windows\\bin\\tools\\astcenc.exe >nul\n'
                             'copy /Y nul export\\release\\windows\\bin\\manifest\\default.json >nul\n'
                             'copy /Y nul export\\release\\windows\\bin\\manifest\\libvlc.json >nul\n'
                             'exit /b ' + str(build_code) + '\n')
                    (project / 'haxelib.cmd').write_bytes(build.replace('\n', '\r\n').encode())
                    (project / 'tools/run_tests.py').write_text("from pathlib import Path\nwith Path('events.txt').open('a') as output: output.write('tests\\n')\nraise SystemExit(" + str(test_code) + ')\n', encoding='utf-8', newline='\n')
                    (project / 'tools/package_windows_release.py').write_text("from pathlib import Path\nwith Path('events.txt').open('a') as output: output.write('package\\n')\n", encoding='utf-8', newline='\n')
                    (project / 'tools/sync_windows_audio.py').write_text('pass\n', encoding='utf-8', newline='\n')
                    environment = {**os.environ, 'PATH': str(project) + os.pathsep + os.environ['PATH']}
                    result = subprocess.run(['cmd', '/c', str(project / 'run.bat'), 'package'], cwd=ROOT, env=environment, capture_output=True, text=True)
                    self.assertEqual((project / 'events.txt').read_text().splitlines(), expected, result.stdout + result.stderr)
                    self.assertEqual(result.returncode == 0, build_code == 0 and test_code == 0)
                    self.assertNotIn('Press any key to close this window', result.stdout)

    @unittest.skipUnless(os.name == 'nt', 'native Windows batch workflow')
    def test_cached_build_still_runs_tests_and_rebuild_is_explicit(self):
        import shutil
        from tools import launch_cache
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            project = Path(directory) / 'cached project with spaces'
            (project / 'tools').mkdir(parents=True)
            (project / 'tools/is_explorer_parent.ps1').write_text(
                (ROOT / 'tools/is_explorer_parent.ps1').read_text(encoding='utf-8'),
                encoding='utf-8', newline='\n')
            shutil.copy2(ROOT / 'tools/launch_cache.py', project / 'tools/launch_cache.py')
            original = (ROOT / 'run.bat').read_text(encoding='utf-8')
            main = original[:original.index('\n:build_update_helper')]
            stubs = '\n:ensure_python\nset PYTHON_COMMAND="' + sys.executable + '"\nexit /b 0\n'
            stubs += '\n:ensure_toolchain\nset PYTHON_COMMAND="' + sys.executable + '"\nexit /b 0\n'
            for label in ('ensure_git', 'ensure_astc_decoder', 'ensure_shared_haxelib_patches', 'patch_haxelibs', 'ensure_asset_scaffolding', 'ensure_native_compiler', 'probe_native_compiler', 'configure_mingw_environment', 'ensure_lime_uncapped', 'sync_astc_decoder', 'sync_compiler_runtime'):
                stubs += '\n:' + label + '\nexit /b 0\n'
            stubs += '\n:ensure_haxelibs\necho haxelibs>>events.txt\nexit /b 0\n'
            stubs += '\n:build_update_helper\necho updater>>events.txt\nexit /b 0\n'
            (project / 'run.bat').write_bytes((main + stubs).replace('\n', '\r\n').encode())
            runtime = project / 'export/release/windows/bin'
            (runtime / 'assets').mkdir(parents=True)
            (runtime / 'tools').mkdir()
            (runtime / 'manifest').mkdir()
            for name in ('Funkin.exe', 'lime.ndll', 'CammieUpdateHelper.exe', 'tools/astcenc.exe',
                         'manifest/default.json', 'manifest/libvlc.json'):
                (runtime / name).write_text('native fixture')
            (project / 'haxelib.cmd').write_bytes(b'@echo off\r\necho build>>events.txt\r\nexit /b 0\r\n')
            (project / 'tools/run_tests.py').write_text("from pathlib import Path\nwith Path('events.txt').open('a') as output: output.write('tests\\n')\n", newline='\n')
            (project / 'tools/sync_windows_audio.py').write_text('pass\n', newline='\n')
            environment = {**os.environ, 'PATH': str(project) + os.pathsep + os.environ['PATH']}
            # Batch `set VAR=` removes these variables, so exclude them from the
            # fixture fingerprint just as the entry point does before checking it.
            for key in ('HAXE_DEBUG_FLAG', 'LIME_ARCH_FLAGS', 'LIME_COMPILER_FLAGS',
                        'HAXE_COMPILER_FLAGS', 'HXCPP_COMPILER_FLAGS'):
                environment.pop(key, None)
            with patch.dict(os.environ, environment, clear=True):
                before = launch_cache.capture(project, project / 'export/release', 'windows')
                launch_cache.record(project, project / 'export/release', before, 'windows')
            cache_check = subprocess.run(
                [sys.executable, str(project / 'tools/launch_cache.py'), 'check',
                 str(project / 'export/release'), '--platform', 'windows'],
                cwd=project, env=environment, capture_output=True, text=True)
            self.assertEqual(cache_check.returncode, 0, cache_check.stdout + cache_check.stderr)
            for mode in ('build', 'test', 'test', 'rebuild'):
                result = subprocess.run(['cmd', '/c', str(project / 'run.bat'), mode], cwd=ROOT, env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if mode in ('build', 'test'):
                    self.assertIn('build is up to date', result.stdout)
            self.assertEqual((project / 'events.txt').read_text().splitlines(),
                             ['tests', 'tests', 'haxelibs', 'build', 'updater'])
            self.assertNotIn('Press any key to close this window', result.stdout)

    @unittest.skipUnless(os.name == 'nt', 'PowerShell CIM process-tree probe')
    def test_explorer_detector_walks_cmd_ancestors_but_not_shell_or_python_parents(self):
        helper = (ROOT / 'tools/is_explorer_parent.ps1').resolve()

        def detect(parent_names):
            processes = [{'Name': 'powershell.exe', 'ParentProcessId': 100}]
            for index, name in enumerate(parent_names):
                processes.append({'Name': name, 'ParentProcessId': 101 + index})
            mock_rows = ',\n'.join(
                "[pscustomobject]@{Name='%s'; ParentProcessId=%d}" %
                (row['Name'], row['ParentProcessId']) for row in processes
            )
            harness = f"""$script:rows = @(
{mock_rows}
)
$script:index = 0
function Get-CimInstance {{
    param([string]$ClassName, [string]$Filter)
    if ($script:index -ge $script:rows.Count) {{ return $null }}
    $row = $script:rows[$script:index]
    $script:index++
    return $row
}}
. '{str(helper).replace("'", "''")}'
"""
            with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
                script = Path(folder) / 'mock-process-tree.ps1'
                script.write_text(harness, encoding='utf-8', newline='\n')
                return subprocess.run(
                    ['powershell.exe', '-NoProfile', '-NonInteractive',
                     '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                    cwd=ROOT, capture_output=True, text=True, timeout=15,
                )

        explorer = detect(['cmd.exe', 'cmd.exe', 'explorer.exe'])
        self.assertEqual(explorer.returncode, 0, explorer.stderr)
        self.assertEqual(explorer.stdout.strip(), '1')
        powershell = detect(['cmd.exe', 'cmd.exe', 'powershell.exe'])
        self.assertEqual(powershell.returncode, 0, powershell.stderr)
        self.assertEqual(powershell.stdout.strip(), '')
        python = detect(['cmd.exe', 'cmd.exe', 'python.exe'])
        self.assertEqual(python.returncode, 0, python.stderr)
        self.assertEqual(python.stdout.strip(), '')

    def test_explorer_wrapper_pauses_only_after_the_child_and_returns_its_code(self):
        batch = (ROOT / 'run.bat').read_text(encoding='utf-8')
        self.assertIn('tools\\is_explorer_parent.ps1', batch)
        self.assertIn('if defined CAMMIE_RUNBAT_EXPLORER_WRAPPER goto run_bat_body', batch)
        self.assertLess(batch.index('call "%~f0" %*'), batch.index('pause >nul'))
        self.assertIn('exit /b !RUN_BAT_RESULT!', batch)


if __name__ == '__main__':
    unittest.main()
