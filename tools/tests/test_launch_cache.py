import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

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
        target.write_text(text)
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

    def test_same_size_edit_with_restored_mtime_is_detected(self):
        self.record()
        target = self.root / 'assets/data/chart.json'
        original = target.stat()
        target.write_text('[]')
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
            source.write_text('before')
            self.record()
            source.write_text('after')
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

    def run_launcher(self, *args):
        return subprocess.run(['bash', 'run.sh', *args], cwd=self.root,
                              capture_output=True, text=True, timeout=10)

    def test_unchanged_default_launch_and_build_skip_toolchain_setup(self):
        # There is no Haxe or Neko installed in this fixture: any attempt to
        # enter the setup path would fail instead of producing these outputs.
        self.record()
        for args, launches in [((), True), (('build',), False)]:
            result = self.run_launcher(*args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('build is up to date', result.stdout)
            self.assertEqual('game-started' in result.stdout, launches)

    def test_nobuild_launches_without_cache_or_toolchain(self):
        result = self.run_launcher('nobuild')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('game-started', result.stdout)


if __name__ == '__main__':
    unittest.main()
