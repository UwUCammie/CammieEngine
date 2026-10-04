import contextlib
import importlib.util
import io
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cache', ROOT / 'tools/launch_cache.py')
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


class LaunchCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root / 'export/release'
        for folder in ('source', 'assets/data', '.haxelib', 'tools', '.tools',
                       'export/release/linux/bin/assets'):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        for file in ('run.sh', 'tools/launch_cache.py', 'tools/runtime_lock.sh'):
            shutil.copy2(ROOT / file, self.root / file)
        self.write('source/Main.hx', 'class Main {}')
        self.write('assets/data/chart.json', '{}')
        self.write('export/release/linux/bin/lime.ndll', 'library')
        self.write('export/release/linux/bin/Funkin', '#!/bin/sh\necho game-started\n')
        (self.build / 'linux/bin/Funkin').chmod(0o755)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, newline='\n')
        return target

    def record(self):
        before = cache.capture(self.root, self.build)
        cache.record(self.root, self.build, before)
        self.assertTrue(cache.fresh(self.root, self.build))

    def test_source_asset_dependency_edits_and_removals_invalidate(self):
        for path in ('source/Main.hx', 'assets/data/chart.json', '.haxelib/lib/.current'):
            self.record()
            target = self.write(path, 'changed')
            self.assertFalse(cache.fresh(self.root, self.build), path)
            self.record()
            target.unlink()
            self.assertFalse(cache.fresh(self.root, self.build), path)

    @unittest.skipIf(os.name == 'nt', 'Linux launch shell and metadata semantics fixture')
    def test_same_size_edit_with_restored_mtime_is_detected(self):
        self.record()
        target = self.root / 'assets/data/chart.json'
        original = target.stat()
        target.write_text('[]', newline='\n')
        os.utime(target, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.assertFalse(cache.fresh(self.root, self.build))

    def test_asset_rename_invalidates(self):
        self.record()
        (self.root / 'assets/data/chart.json').rename(self.root / 'assets/data/renamed.json')
        self.assertFalse(cache.fresh(self.root, self.build))

    def test_dev_library_outside_checkout_is_tracked(self):
        with tempfile.TemporaryDirectory() as external:
            self.write('.haxelib/library/.dev', external)
            source = Path(external) / 'Library.hx'
            source.write_text('before', newline='\n')
            self.record()
            source.write_text('after', newline='\n')
            self.assertFalse(cache.fresh(self.root, self.build))

    def test_live_settings_do_not_invalidate_but_missing_native_library_does(self):
        self.record()
        self.write('export/release/linux/bin/assets/data/options.json', '{"volume":0.5}')
        self.assertTrue(cache.fresh(self.root, self.build))
        (self.build / 'linux/bin/lime.ndll').unlink()
        self.assertFalse(cache.fresh(self.root, self.build))

    def test_readme_edits_do_not_rebuild_but_project_config_does(self):
        self.write('README.md', 'before')
        self.record()
        self.write('README.md', 'after')
        self.assertTrue(cache.fresh(self.root, self.build))
        self.write('Project.xml', '<project/>')
        self.assertFalse(cache.fresh(self.root, self.build))

    def test_failed_or_concurrently_edited_build_is_not_cached(self):
        self.record()
        before = cache.capture(self.root, self.build)
        self.assertFalse(cache.fresh(self.root, self.build))
        self.write('source/Main.hx', 'edited during build')
        with contextlib.redirect_stdout(io.StringIO()):
            cache.record(self.root, self.build, before)
        self.assertFalse(cache.fresh(self.root, self.build))

    def test_debug_build_has_separate_cache(self):
        self.record()
        self.assertFalse(cache.fresh(self.root, self.root / 'export/debug'))

    def make_windows_runtime(self):
        for name in ('Funkin.exe', 'lime.ndll', 'CammieUpdateHelper.exe', 'tools/astcenc.exe',
                     'manifest/default.json', 'manifest/libvlc.json'):
            self.write('export/release/windows/bin/' + name, 'native fixture')
        (self.build / 'windows/bin/assets').mkdir(parents=True, exist_ok=True)

    def test_windows_tracks_tools_outputs_and_platform_independently(self):
        self.make_windows_runtime()
        before = cache.capture(self.root, self.build, 'windows')
        cache.record(self.root, self.build, before, 'windows')
        self.assertTrue(cache.fresh(self.root, self.build, 'windows'))
        self.assertFalse(cache.fresh(self.root, self.build, 'linux'))
        self.write('export/release/windows/bin/assets/data/options.json', '{"volume":0}')
        self.assertTrue(cache.fresh(self.root, self.build, 'windows'))
        for changed in ('run.bat', 'tools/updater/CammieUpdateHelper.hx',
                        'tools/patch_windows_mingw.py', 'tools/is_explorer_parent.ps1',
                        '.tools/git/cmd/git.exe', '.tools/astcenc/astcenc.exe'):
            before = cache.capture(self.root, self.build, 'windows')
            cache.record(self.root, self.build, before, 'windows')
            self.write(changed, 'changed')
            self.assertFalse(cache.fresh(self.root, self.build, 'windows'), changed)
        before = cache.capture(self.root, self.build, 'windows')
        cache.record(self.root, self.build, before, 'windows')
        (self.build / 'windows/bin/CammieUpdateHelper.exe').unlink()
        self.assertFalse(cache.fresh(self.root, self.build, 'windows'))

    def test_windows_missing_asset_manifest_invalidates_build(self):
        self.make_windows_runtime()
        before = cache.capture(self.root, self.build, 'windows')
        cache.record(self.root, self.build, before, 'windows')
        (self.build / 'windows/bin/manifest/default.json').unlink()
        self.assertFalse(cache.fresh(self.root, self.build, 'windows'))

    def test_windows_debug_and_arch_flags_invalidate_shared_output(self):
        self.make_windows_runtime()
        before = cache.capture(self.root, self.build, 'windows')
        cache.record(self.root, self.build, before, 'windows')
        for key, value in (('HAXE_DEBUG_FLAG', '-debug'), ('LIME_ARCH_FLAGS', '-D32bit -32')):
            with patch.dict(os.environ, {key: value}):
                self.assertFalse(cache.fresh(self.root, self.build, 'windows'))

    def test_windows_concurrent_input_edits_are_never_cached(self):
        self.make_windows_runtime()
        before = cache.capture(self.root, self.build, 'windows')
        self.write('source/Main.hx', 'changed during native build')
        with contextlib.redirect_stdout(io.StringIO()):
            cache.record(self.root, self.build, before, 'windows')
        self.assertFalse(cache.fresh(self.root, self.build, 'windows'))

    def run_launcher(self, *args):
        return subprocess.run(['bash', 'run.sh', *args], cwd=self.root,
                              capture_output=True, text=True, timeout=10)

    @unittest.skipIf(os.name == 'nt', 'Linux launch shell and metadata semantics fixture')
    def test_unchanged_default_launch_and_build_skip_toolchain_setup(self):
        # There is no Haxe or Neko installed in this fixture: any attempt to
        # enter the setup path would fail instead of producing these outputs.
        self.record()
        for args, launches in [((), True), (('build',), False)]:
            result = self.run_launcher(*args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('build is up to date', result.stdout)
            self.assertEqual('game-started' in result.stdout, launches)

    @unittest.skipIf(os.name == 'nt', 'Linux launch shell and metadata semantics fixture')
    def test_nobuild_launches_without_cache_or_toolchain(self):
        result = self.run_launcher('nobuild')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('game-started', result.stdout)


if __name__ == '__main__':
    unittest.main()
