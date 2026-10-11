"""Directory metadata must preserve script discovery and filesystem behavior."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, ROOT, TEST_TMP
from windows_native_import_fixture import NativeFixtureUnavailable, get_native_fixture


class PortableDirectoryListingTest(unittest.TestCase):
    def test_portable_fallback_observes_new_entries_and_errors(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            (root / 'Main.hx').write_text(r'''
import sys.FileSystem;
import sys.io.File;
class Main {
 static function main() {
  var root=Sys.args()[0];
  function read() {var rows=[for(entry in NativeDirectoryListing.read(root)){name:entry.name,isDirectory:entry.isDirectory==null?FileSystem.isDirectory(root+"/"+entry.name):entry.isDirectory}];rows.sort(function(a,b)return Reflect.compare(a.name,b.name));return rows;}
  if(read().length!=0)throw "empty";
  File.saveContent(root+"/note.hxc","file");FileSystem.createDirectory(root+"/folder.hxc");
  var first=read();if(first.length!=2 || !first[0].isDirectory || first[1].isDirectory)throw "types";
  FileSystem.deleteFile(root+"/note.hxc");File.saveContent(root+"/next.txt","new");
  if(read()[1].name!="next.txt")throw "stale metadata";
  var failed=false;try NativeDirectoryListing.read(root+"/missing") catch(_:Dynamic)failed=true;
  if(!failed)throw "missing directory must fail";
  Sys.println("passed");
 }
}''', encoding='utf-8')
            data = root / 'data'
            data.mkdir()
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(root),
                                     '--run', 'Main', str(data)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('passed', result.stdout)


@unittest.skipUnless(os.name == 'nt', 'native Windows directory metadata')
class NativeDirectoryListingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.fixture = get_native_fixture()
        except NativeFixtureUnavailable as error:
            raise unittest.SkipTest(str(error)) from error

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_TMP)
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def run_fixture(self, *args):
        run = subprocess.run([str(self.fixture.executable), *map(str, args)],
                             env=self.fixture.environment, capture_output=True, encoding='utf-8',
                             timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        result = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertNotEqual(result.get('ok'), False, result)
        return result

    def test_entries_match_portable_unicode_empty_and_mutation(self):
        self.assertEqual(self.run_fixture('directory-listing', self.root)['entries'], [])
        names = ['plain', '.hidden.hxc', 'UPPER.HXC', 'é_日本_🧙.hxc', 'with space.txt']
        for name in names:
            (self.root / name).write_text('text', encoding='utf-8')
        (self.root / 'folder.hxc').mkdir()
        expected = {name: False for name in names}
        expected['folder.hxc'] = True
        actual = self.run_fixture('directory-listing', self.root)['entries']
        self.assertEqual({v['name']: v['isDirectory'] for v in actual}, expected)
        (self.root / 'plain').unlink()
        (self.root / 'plain').mkdir()
        actual = self.run_fixture('directory-listing', self.root)['entries']
        self.assertTrue(next(v['isDirectory'] for v in actual if v['name'] == 'plain'))

    def test_missing_and_file_roots_preserve_errors(self):
        file = self.root / 'file'
        file.write_text('x')
        for path in (file, self.root / 'absent', ''):
            self.assertEqual(self.run_fixture('directory-errors', path), {'portable': True, 'native': True})

    def test_relative_and_drive_rooted_paths_match_portable(self):
        (self.root / 'child').mkdir()
        (self.root / 'note.hxc').write_text('class N extends Module {}')
        for spelling in (os.path.relpath(self.root), str(self.root)[2:], str(self.root).replace('\\', '/')):
            entries = self.run_fixture('directory-listing', spelling)['entries']
            self.assertEqual({v['name']: v['isDirectory'] for v in entries}, {'child': True, 'note.hxc': False})

    def test_long_paths_and_directory_named_like_script(self):
        deep = self.root / ('a' * 100) / ('b' * 100) / ('c' * 70)
        extended = Path('\\\\?\\' + str(deep))
        extended.mkdir(parents=True)
        (extended / 'stage.hxc').write_text('class LongStage extends Stage {}')
        entries = self.run_fixture('directory-listing', deep)['entries']
        self.assertEqual(entries, [{'name': 'stage.hxc', 'isDirectory': False}])
        plan = self.run_fixture('script-discovery', deep, 4096)
        self.assertEqual(len(plan['all']), 1)
        self.assertTrue(plan['all'][0].replace('\\', '/').endswith('/stage.hxc'))

    def test_discovery_order_budget_depth_and_family(self):
        (self.root / 'A.hxc').write_text('class A extends Stage {}')
        (self.root / 'b.HXC').write_text('class B extends Module {}')
        folder = self.root / 'c.hxc'
        folder.mkdir()
        (folder / 'nested.hxc').write_text('class C extends Character {}')
        (self.root / 'other.lua').write_text('ignored')
        for budget, count in ((0, 1), (1, 1), (2, 2), (4096, 3)):
            plan = self.run_fixture('script-discovery', self.root, budget)
            self.assertEqual(len(plan['all']), count)
            self.assertEqual([Path(p).name for p in plan['all']], ['A.hxc', 'b.HXC', 'nested.hxc'][:count])
        plan = self.run_fixture('script-discovery', self.root, 4096)
        self.assertEqual(len(plan['families']['unknown']), 2)
        self.assertEqual(len(plan['families']['character']), 1)
        cursor = self.root
        for depth in range(1, 14):
            cursor = cursor / 'x'
            cursor.mkdir()
            if depth in (12, 13):
                (cursor / f'depth{depth}.hxc').write_text('class Depth extends Module {}')
        plan = self.run_fixture('script-discovery', self.root, 4096)
        self.assertEqual(len(plan['all']), 4)
        self.assertTrue(any(Path(p).name == 'depth12.hxc' for p in plan['all']))
        self.assertFalse(any(Path(p).name == 'depth13.hxc' for p in plan['all']))
        for directory, family in (('stages', 'stage'), ('modules', 'module')):
            path = self.root / directory
            path.mkdir()
            (path / 'owner.hxc').write_text('function onCreate() {}')
            plan = self.run_fixture('script-discovery', path, 4096)
            self.assertEqual(len(plan['families'][family]), 1)

    def test_junction_target_uses_live_directory_semantics(self):
        target = self.root / 'target'
        target.mkdir()
        (target / 'nested.hxc').write_text('class Nested extends Module {}')
        link = self.root / 'link'
        # Both endpoints belong to this private fixture; no external tree is touched.
        script = "New-Item -ItemType Junction -Path $env:CAMMIE_TEST_LINK -Target $env:CAMMIE_TEST_TARGET | Out-Null"
        env = dict(os.environ, CAMMIE_TEST_LINK=str(link), CAMMIE_TEST_TARGET=str(target))
        result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script], env=env, capture_output=True, text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(link.is_junction())
        # Remove only the link itself before ordinary fixture cleanup.
        self.addCleanup(lambda: os.rmdir(link) if link.is_junction() else None)
        rows = self.run_fixture('directory-listing', self.root)['entries']
        self.assertTrue(next(v['isDirectory'] for v in rows if v['name'] == 'link'))
        plan = self.run_fixture('script-discovery', link, 4096)
        self.assertEqual(len(plan['all']), 1)
