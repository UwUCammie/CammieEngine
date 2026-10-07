"""Exercise native Windows long paths and import retry pointers, beyond eval."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import patch_hxcpp_windows_file_paths as patcher
from haxe_test_support import HAXE, TEST_TMP
from test_import_refresh_manager import STUBS, FIXTURE
import test_import_refresh_manager as manager_fixtures

_NATIVE_BUILD_LOCK = threading.Lock()
_NATIVE_BUILD_CACHE = None
_SEQUENCE_CHECKPOINT = 'committed:view.committedOwnerRoots,revision:view.revision};'

MAIN = r'''import haxe.Json;
import sys.io.File;
import sys.FileSystem;
@:access(ImportRefreshManager)
@:access(ImportRefreshManagerFixture)
class NativeImportFilesystemFixture {
 static function main() {
  var args=Sys.args();
  try {
   switch(args[0]) {
    case "fresh", "auto-refresh", "auto-refresh-sequence":
     ImportRefreshManagerFixture.main();
    case "pointer":
     ImportRefreshManager.atomicText(args[1],args[2]);
     Sys.println(Json.stringify({ok:true,text:File.getContent(args[1])}));
    case "capture":
     var result=ImportSourceSnapshot.capture(args[1],args[2],"Nightmare Vision","0.0.9");
     if(!result.complete) throw result.error;
     ImportSourceSnapshot.verify(result.snapshotRoot,result.snapshotId);
     Sys.println(Json.stringify({ok:true,result:result}));
    case "verify":
     ImportSourceSnapshot.verify(args[1],args[2]);
     Sys.println(Json.stringify({ok:true}));
    case "io":
     var directory=args[1];
     FileSystem.createDirectory(directory);
     if(!FileSystem.exists(directory)||!FileSystem.isDirectory(directory)) throw "directory missing";
     var path=directory+"/雪.txt";
     File.saveContent(path,"long-path-bytes");
     if(File.getContent(path)!="long-path-bytes"||File.getBytes(path).length!=15||FileSystem.stat(path).size!=15)
      throw "incorrect long-path read or stat";
     var input=File.read(path,true);
     var text=input.readAll().toString(); input.close();
     if(text!="long-path-bytes") throw "incorrect streaming read";
     FileSystem.rename(path,path+".renamed");
     FileSystem.deleteFile(path+".renamed");
     FileSystem.deleteDirectory(directory);
     Sys.println(Json.stringify({ok:true}));
   }
  } catch(error:Dynamic) Sys.println(Json.stringify({ok:false,error:Std.string(error)}));
 }
}'''


def _native_fixture_source():
    if _SEQUENCE_CHECKPOINT not in FIXTURE:
        raise AssertionError('native refresh fixture lost its overlap checkpoint')
    return FIXTURE.replace(_SEQUENCE_CHECKPOINT,
        'committed:view.committedOwnerRoots,revision:view.revision,active:ImportRefreshManager.active};')


def _cleanup_native_build():
    global _NATIVE_BUILD_CACHE
    with _NATIVE_BUILD_LOCK:
        cache = _NATIVE_BUILD_CACHE
        _NATIVE_BUILD_CACHE = None
    if cache is not None:
        cache['build_temp'].cleanup()


atexit.register(_cleanup_native_build)


def _assert_native_handoff_overlap(test_case):
    test_case.install = test_case.base / 'install'
    registry = test_case.install / 'assets/data/freeplaySongJson.json'
    registry.parent.mkdir(parents=True)
    registry.write_text('{"base":{"keep":true},"owners":{}}', encoding='utf-8')

    donors = []
    for label, song in (("native-sequence-a", "queue-a"),
                         ("native-sequence-b", "queue-b")):
        donor = test_case.base / label
        donor.mkdir()
        (donor / 'package.json').write_text(json.dumps({
            'ownerKey': label, 'marker': 'retained:' + label,
            'initialVersion': 'v1-' + label, 'nextVersion': 'v2-' + label,
            'initialSongs': [song], 'nextSongs': [song, song + '-new']}), encoding='utf-8')
        imported = test_case.run_fixture('fresh', test_case.install, donor)
        test_case.assertEqual(imported['failed'], 0, imported)
        donors.append(donor)

    records = {record['label']: record for record in imported['records']}
    sequence_records = [records['native-sequence-a'], records['native-sequence-b']]
    for record in sequence_records:
        manager_fixtures.ImportRefreshManagerTest.mark_record_stale(
            test_case, record, common_revision=2)
    ordered = sorted(sequence_records, key=lambda record: record['id'])
    for donor in donors:
        shutil.rmtree(donor)

    result = test_case.run_fixture('auto-refresh-sequence', test_case.install, ordered[1]['label'])

    first_owner = 'assets/imported_mods/' + ordered[0]['roots'][0]['namespace']
    second_owner = 'assets/imported_mods/' + ordered[1]['roots'][0]['namespace']
    test_case.assertIsNotNone(result['split'], result)
    # The checkpoint is captured only inside the generation >= 1 &&
    # manager.active branch.
    test_case.assertTrue(result['split']['active'], result)
    test_case.assertEqual(result['split']['pending'], [second_owner], result)
    test_case.assertEqual(result['split']['handoff'], [], result)
    test_case.assertEqual(result['split']['committed'], sorted([first_owner, second_owner]), result)
    test_case.assertEqual(result['pending'], [], result)
    test_case.assertEqual(result['generation'], 2, result)
    test_case.assertEqual(result['handoffCalls'], 2, result)
    for song in ('queue-a-new', 'queue-b-new'):
        test_case.assertTrue((test_case.install / 'assets/songs' / song / 'Inst.ogg').is_file(), result)


class WindowsFilePathPatchTest(unittest.TestCase):
    def test_exact_patch_chain_is_idempotent_and_rejects_drift(self):
        for name, replacements, original_hash, patched_hash in (
            ('Sys.cpp', patcher.SYS_REPLACEMENTS, patcher.SYS_SOURCE_SHA256, patcher.SYS_PATCHED_SHA256),
            ('File.cpp', patcher.FILE_REPLACEMENTS, patcher.FILE_SOURCE_SHA256, patcher.FILE_PATCHED_SHA256),
        ):
            with self.subTest(name=name):
                source = (patcher.STD / name).read_bytes().replace(b'\r\n', b'\n')
                if hashlib.sha256(source).hexdigest() == patched_hash:
                    source = patcher.transform(source, replacements, reverse=True)
                self.assertEqual(hashlib.sha256(source).hexdigest(), original_hash)
                patched = patcher.patch_source(source, file=name == 'File.cpp')
                self.assertEqual(hashlib.sha256(patched).hexdigest(), patched_hash)
                self.assertEqual(patcher.patch_source(patched, file=name == 'File.cpp'), patched)
                with self.assertRaisesRegex(ValueError, 'differs from pinned'):
                    patcher.patch_source(source + b'// unexpected source drift\n', file=name == 'File.cpp')


@unittest.skipUnless(os.name == 'nt', 'native Windows filesystem regression')
class NativeWindowsImportFilesystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _NATIVE_BUILD_CACHE
        with _NATIVE_BUILD_LOCK:
            if _NATIVE_BUILD_CACHE is not None and _NATIVE_BUILD_CACHE['binary'].is_file():
                cls.build_temp = _NATIVE_BUILD_CACHE['build_temp']
                cls.work = _NATIVE_BUILD_CACHE['work']
                cls.environment = _NATIVE_BUILD_CACHE['environment']
                cls.binary = _NATIVE_BUILD_CACHE['binary']
                return

            compiler = ROOT / '.tools/llvm-mingw-windows'
            if not HAXE.exists() or not (compiler / 'bin/x86_64-w64-mingw32-clang++.exe').exists():
                raise unittest.SkipTest('portable native Windows toolchain is unavailable')

            Path(TEST_TMP).mkdir(parents=True, exist_ok=True)
            build_temp = tempfile.TemporaryDirectory(dir=TEST_TMP)
            work = Path(build_temp.name)
            try:
                native_fixture = _native_fixture_source()
                for name, content in {**STUBS, 'ImportRefreshManagerFixture.hx': native_fixture,
                                      'NativeImportFilesystemFixture.hx': MAIN}.items():
                    target = work / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding='utf-8', newline='\n')
                environment = {**os.environ, 'HAXEPATH': str(HAXE.parent),
                    'NEKOPATH': str(ROOT / '.tools/neko'), 'HAXELIB_PATH': str(ROOT / '.haxelib'),
                    'MINGW_ROOT': str(compiler), 'HXCPP_MINGW_EXE': 'x86_64-w64-mingw32-clang++.exe',
                    'HXCPP_AR': 'llvm-ar.exe', 'HXCPP_RANLIB': 'llvm-ranlib.exe',
                    'HXCPP_STRIP': 'llvm-strip.exe', 'HXCPP_RC': 'llvm-windres.exe',
                    'PATH': os.pathsep.join([str(HAXE.parent), str(ROOT / '.tools/neko'),
                                            str(compiler / 'bin'), os.environ['PATH']])}
                binary = work / 'cpp/NativeImportFilesystemFixture.exe'
                process = subprocess.run([str(HAXE), '-cp', str(ROOT / 'source'),
                    '-cp', str(ROOT / '.haxelib/tjson/1,4,0'), '-cp', str(work),
                    '-main', 'NativeImportFilesystemFixture', '-cpp', str(binary.parent),
                    '-D', 'windows', '-D', 'HXCPP_M64', '-D', 'HXCPP_MINGW', '-D', 'HXCPP_RC=llvm-windres.exe'],
                    cwd=ROOT, env=environment, capture_output=True, text=True, timeout=180)
                if process.returncode:
                    raise AssertionError(process.stdout + process.stderr)
            except BaseException:
                build_temp.cleanup()
                raise

            _NATIVE_BUILD_CACHE = {
                'build_temp': build_temp,
                'work': work,
                'environment': environment,
                'binary': binary,
            }
            cls.build_temp = build_temp
            cls.work = work
            cls.environment = environment
            cls.binary = binary

    @classmethod
    def tearDownClass(cls):
        _cleanup_native_build()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_TMP)
        self.base = Path(self.temp.name)

    def tearDown(self):
        # Python also needs the extended path spelling for deep test fixtures.
        shutil.rmtree('\\\\?\\' + str(self.base))
        self.temp.cleanup()

    def run_fixture(self, *args):
        process = subprocess.run([str(self.binary), *map(str, args)], env=self.environment,
                                 capture_output=True, text=True, timeout=45)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        return json.loads(process.stdout.strip().splitlines()[-1])

    def test_retry_reuses_pointer_and_preserves_conflicting_record(self):
        pointer = self.base / 'owner.json'
        text = '{"id":"immutable-owner"}'
        self.assertTrue(self.run_fixture('pointer', pointer, text)['ok'])
        temporary = pointer.with_suffix('.json.tmp')
        temporary.write_text(text, encoding='utf-8')
        self.assertTrue(self.run_fixture('pointer', pointer, text)['ok'])
        conflict = self.run_fixture('pointer', pointer, '{"id":"different-owner"}')
        self.assertFalse(conflict['ok'])
        self.assertIn('conflicts', conflict['error'])
        self.assertEqual(pointer.read_text(), text)

    def test_native_thread_refreshes_stale_record_after_donor_removal(self):
        self.install = self.base / 'install'
        registry = self.install / 'assets/data/freeplaySongJson.json'
        registry.parent.mkdir(parents=True)
        registry.write_text('{"base":{"keep":true},"owners":{}}', encoding='utf-8')
        donor = self.base / 'donor'
        donor.mkdir()
        (donor / 'package.json').write_text(json.dumps({
            'ownerKey': 'native-owner', 'marker': 'retained-native',
            'initialVersion': 'v1', 'nextVersion': 'v2',
            'initialSongs': ['original'], 'nextSongs': ['original', 'new-song']}), encoding='utf-8')
        imported = self.run_fixture('fresh', self.install, donor)
        self.assertEqual(imported['failed'], 0, imported)
        manager_fixtures.ImportRefreshManagerTest.mark_record_stale(self, imported['records'][0])
        shutil.rmtree(donor)
        refreshed = self.run_fixture('auto-refresh', self.install)
        self.assertFalse(refreshed['status']['busy'], refreshed)
        self.assertTrue(refreshed['status']['complete'], refreshed)
        self.assertFalse(refreshed['status']['blocked'], refreshed)
        self.assertEqual(refreshed['generation'], 1)
        self.assertTrue((self.install / 'assets/songs/new-song/Inst.ogg').exists())
        self.assertFalse(donor.exists())

    def test_native_handoff_overlap_route_is_preserved(self):
        native_fixture = _native_fixture_source()
        self.assertIn('case "fresh", "auto-refresh", "auto-refresh-sequence":', MAIN)
        self.assertIn('mode=="auto-refresh-sequence"&&ImportRefreshManager.generation>=1'
                      '&&ImportRefreshManager.active', FIXTURE)
        self.assertIn('active:ImportRefreshManager.active', native_fixture)
        self.assertIn('pending:view.pendingOwnerRoots,handoff:view.handoffPendingOwnerRoots',
                      native_fixture)

    def test_long_unicode_paths_support_stat_reads_writes_rename_and_cleanup(self):
        directory = self.base / ('parent-' + 'a' * 100) / ('nested-' + 'b' * 100) / ('leaf-' + 'c' * 70)
        self.assertGreater(len(str(directory)), 260)
        result = self.run_fixture('io', directory)
        self.assertTrue(result['ok'], result)

    def test_long_cached_snapshot_verifies_but_rejects_real_size_changes(self):
        donor = self.base / 'donor'
        relative = Path('content') / ('nested-' + 'a' * 85) / 'authored-雪-script.txt'
        authored = donor / relative
        authored.parent.mkdir(parents=True)
        authored.write_bytes(b'authored bytes\x00\xff')
        cache = self.base / ('cache-' + 'b' * 80)
        result = self.run_fixture('capture', donor, cache)
        self.assertTrue(result['ok'], result)
        snapshot = Path(result['result']['snapshotRoot'])
        retained = snapshot / 'content' / relative
        self.assertGreater(len(str(retained)), 260)
        extended = '\\\\?\\' + str(retained)
        self.assertEqual(Path(extended).read_bytes(), authored.read_bytes())
        Path(extended).write_bytes(b'real changed size')
        rejected = self.run_fixture('verify', snapshot, result['result']['snapshotId'])
        self.assertFalse(rejected['ok'])
        self.assertIn('Snapshot file size changed', rejected['error'])
        self.assertEqual(authored.read_bytes(), b'authored bytes\x00\xff')


def run_native_handoff_overlap_case():
    """Run the shared native overlap case with the fixture's normal lifecycle."""
    NativeWindowsImportFilesystemTest.setUpClass()
    test_case = NativeWindowsImportFilesystemTest('test_native_handoff_overlap_route_is_preserved')
    test_case.setUp()
    try:
        _assert_native_handoff_overlap(test_case)
    finally:
        test_case.tearDown()


if __name__ == '__main__':
    unittest.main()
