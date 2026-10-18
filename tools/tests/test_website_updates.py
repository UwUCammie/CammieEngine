"""Website release publication and file-only Windows update regressions."""
import hashlib
import json
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
import zipfile

from haxe_test_support import HAXE_COMMAND, TEST_TMP
from prepare_website_release import prepare, safe_path, SITE_ROOT
from activate_website_release import activate

ROOT = Path(__file__).resolve().parents[2]
TAG = 'v0.0.46'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class WebsiteUpdatesTest(unittest.TestCase):
    def make_release(self, folder):
        files = {'Funkin.exe': b'new-game', 'lime.ndll': b'same-library',
                 'CammieUpdateHelper.exe': b'new-helper', 'RELEASE_TAG': (TAG + '\n').encode(),
                 'assets/data/options.json': b'default-options',
                 'assets/official.txt': b'new-official', 'assets/edited.txt': b'new-official',
                 'assets/unchanged.txt': b'unchanged-asset', 'new-runtime.txt': b'new-file',
                 'duplicate-runtime.txt': b'new-file'}
        files['BUNDLED_ASSETS.json'] = json.dumps({'version': 1, 'files': {
            'assets/official.txt': [digest(b'old-official'), digest(b'new-official')],
            'assets/edited.txt': [digest(b'old-official'), digest(b'new-official')],
            'assets/unchanged.txt': [digest(b'unchanged-asset')]}}).encode()
        archive = folder / f'CammieEngine-{TAG}-windows-x64.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
            for path, data in files.items():
                package.writestr('CammieEngine-windows-x64/' + path, data)
        site = folder / 'site'
        metadata = prepare(archive, site, TAG, TAG + ' alpha\n- Website updates.\n')
        return site, metadata, files

    def test_prepare_deduplicates_objects_and_activation_verifies_before_switch(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temporary:
            site, metadata, files = self.make_release(Path(temporary))
            manifest = json.loads((site / 'releases' / TAG / 'manifest.json').read_text())
            self.assertEqual(len(manifest['files']), len(files))
            self.assertEqual(len(list((site / 'objects').iterdir())), len({digest(data) for data in files.values()}))
            blob = site / 'objects' / digest(b'new-game')
            blob.write_bytes(b'corrupt!')
            with self.assertRaisesRegex(ValueError, 'Object verification failed'):
                activate(site, TAG)
            self.assertFalse((site / 'latest.json').exists())
            blob.write_bytes(b'new-game')
            activate(site, TAG)
            self.assertEqual(json.loads((site / 'latest.json').read_text()), metadata)
            self.assertEqual(json.loads((site / 'history.json').read_text())['releases'], [metadata])
            self.assertEqual((site / 'download.zip').resolve(), site / 'releases' / TAG / metadata['archive']['name'])
            activate(site, TAG)
            self.assertEqual(len(json.loads((site / 'history.json').read_text())['releases']), 1)

    def test_windows_manifest_paths_reject_unsafe_and_reserved_names(self):
        for name in ['../escape', '/escape', 'assets//x', 'C:/x', 'foo\\x', 'NUL.txt',
                     'x./file', 'file ', 'assets/x\x00', 'com1/file', 'x|y']:
            self.assertFalse(safe_path(name), name)
        self.assertTrue(safe_path('assets/images/normal-file.png'))

    def run_haxe(self, mode):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temporary:
            folder = Path(temporary)
            site, metadata, files = self.make_release(folder)
            installed = folder / 'installed'
            (installed / 'assets/data').mkdir(parents=True)
            (installed / 'Funkin.exe').write_bytes(b'old-game')
            (installed / 'CammieUpdateHelper.exe').write_bytes(b'old-helper')
            (installed / 'lime.ndll').write_bytes(b'same-library')
            (installed / 'RELEASE_TAG').write_text('v0.0.45\n')
            (installed / 'assets/data/options.json').write_bytes(b'my-settings')
            (installed / 'assets/official.txt').write_bytes(b'old-official')
            (installed / 'assets/edited.txt').write_bytes(b'my-edit')
            (installed / 'assets/unchanged.txt').write_bytes(b'unchanged-asset')
            (installed / 'obsolete.dll').write_bytes(b'old-library')
            (installed / 'modified-old.dll').write_bytes(b'my-runtime-edit')
            old_manifest = json.loads((site / 'releases' / TAG / 'manifest.json').read_text())
            old_manifest['tag'] = 'v0.0.45'
            for name in ('obsolete.dll', 'modified-old.dll'):
                old_manifest['files'].append({'path': name, 'sha256': digest(b'old-library'), 'size': 11})
            (installed / 'RELEASE_FILES.json').write_text(json.dumps(old_manifest))
            if mode == 'corrupt':
                (site / 'objects' / digest(b'new-game')).write_bytes(b'bad-game')
            if mode == 'manifest':
                with (site / 'releases' / TAG / 'manifest.json').open('a') as stream:
                    stream.write(' ')
            work = folder / 'work'
            work.mkdir()
            args = [str(work / 'status.txt'), str(installed / 'Funkin.exe'), str(installed),
                    metadata['archive']['url'], metadata['checksumUrl'], metadata['archive']['name'],
                    metadata['archive']['sha256'], TAG, '0', metadata['manifest']['url'], metadata['manifest']['sha256']]
            (folder / 'args.json').write_text(json.dumps(args))
            fixture = r'''
import sys.io.File;
import sys.FileSystem;
import CammieUpdateHelper;
import UpdateChecker;
@:access(CammieUpdateHelper)
class Main {
 static function main() {
  var root = Sys.getEnv('WEBSITE_FIXTURE');
  var mode = Sys.getEnv('WEBSITE_MODE');
  var urls:Array<String> = [];
  var prefix = WebsiteUpdateManifest.ROOT;
  var metadata = File.getContent(root + '/site/releases/v0.0.46/release.json');
  var release = UpdateChecker.parseWebsiteRelease(metadata);
  if (release.manifestUrl != prefix + 'releases/v0.0.46/manifest.json') throw 'Manifest URL lost';
  var invalid:Dynamic = haxe.Json.parse(metadata);
  invalid.manifest.url = 'https://evil.invalid/manifest.json';
  var rejected = false;
  try UpdateChecker.parseWebsiteRelease(haxe.Json.stringify(invalid)) catch (_:Dynamic) rejected = true;
  if (!rejected) throw 'Foreign manifest URL accepted';
  var source = File.getContent(root + '/site/releases/v0.0.46/manifest.json');
  var manifest:Dynamic = haxe.Json.parse(source);
  manifest.files.push(manifest.files[0]);
  rejected = false;
  try WebsiteUpdateManifest.parse(haxe.Json.stringify(manifest), 'v0.0.46') catch (_:Dynamic) rejected = true;
  if (!rejected) throw 'Duplicate paths accepted';
  for (path in ['../escape', 'assets//x', 'NUL.txt', 'bad./x', 'C:/escape', 'foo\\bar'])
   if (WebsiteUpdateManifest.safePath(path)) throw 'Unsafe path accepted: ' + path;
  CammieUpdateHelper.testDownload = function(url, destination) {
   if (!StringTools.startsWith(url, prefix)) throw 'Foreign download URL';
   urls.push(url);
   File.copy(root + '/site/' + url.substr(prefix.length), destination);
  };
  if (mode == 'rollback') CammieUpdateHelper.testFailAfter = 3;
  if (mode == 'rollback-delete') CammieUpdateHelper.testFailBeforeCommit = true;
  var args:Array<String> = cast haxe.Json.parse(File.getContent(root + '/args.json'));
  var failed = false;
  try CammieUpdateHelper.run(args) catch (_:Dynamic) failed = true;
  File.saveContent(root + '/requests.json', haxe.Json.stringify(urls));
  if (failed != (mode != 'success')) throw 'Unexpected transaction result: ' + mode;
 }
}'''
            (folder / 'Main.hx').write_text(fixture)
            env = {**os.environ, 'WEBSITE_FIXTURE': folder.as_posix(), 'WEBSITE_MODE': mode}
            result = subprocess.run([*HAXE_COMMAND, '-D', 'updater_test', '-cp', str(ROOT / 'source'),
                                     '-cp', str(ROOT / 'tools/updater'), '-cp', str(folder),
                                     '-main', 'Main', '--interp'], env=env, cwd=ROOT,
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            urls = json.loads((folder / 'requests.json').read_text())
            for unchanged in (b'same-library', b'unchanged-asset', b'default-options'):
                self.assertNotIn(SITE_ROOT + 'objects/' + digest(unchanged), urls)
            self.assertFalse(any(url.endswith('.zip') for url in urls), 'Incremental update downloaded the full ZIP')
            self.assertEqual((installed / 'assets/data/options.json').read_bytes(), b'my-settings')
            self.assertEqual((installed / 'assets/edited.txt').read_bytes(), b'my-edit')
            self.assertEqual((installed / 'modified-old.dll').read_bytes(), b'my-runtime-edit')
            if mode == 'success':
                self.assertEqual(urls.count(SITE_ROOT + 'objects/' + digest(b'new-file')), 1)
                self.assertEqual((installed / 'Funkin.exe').read_bytes(), b'new-game')
                self.assertEqual((installed / 'CammieUpdateHelper.exe').read_bytes(), b'new-helper')
                self.assertEqual((installed / 'assets/official.txt').read_bytes(), b'new-official')
                self.assertFalse((installed / 'obsolete.dll').exists())
                self.assertEqual((installed / 'RELEASE_TAG').read_text().strip(), TAG)
            else:
                self.assertEqual((installed / 'Funkin.exe').read_bytes(), b'old-game')
                self.assertEqual((installed / 'CammieUpdateHelper.exe').read_bytes(), b'old-helper')
                self.assertEqual((installed / 'obsolete.dll').read_bytes(), b'old-library')
                self.assertEqual((installed / 'RELEASE_TAG').read_text().strip(), 'v0.0.45')
                self.assertEqual(json.loads((installed / 'RELEASE_FILES.json').read_text())['tag'], 'v0.0.45')

    def test_file_only_update_preserves_custom_content_and_removes_unmodified_old_runtime(self):
        self.run_haxe('success')

    def test_corrupt_changed_file_leaves_installation_untouched(self):
        self.run_haxe('corrupt')

    def test_changed_manifest_is_rejected_before_installation(self):
        self.run_haxe('manifest')

    def test_failed_install_rolls_back_helper_game_and_inventory(self):
        self.run_haxe('rollback')

    def test_failed_commit_restores_deleted_runtime_files(self):
        self.run_haxe('rollback-delete')


if __name__ == '__main__':
    unittest.main()
