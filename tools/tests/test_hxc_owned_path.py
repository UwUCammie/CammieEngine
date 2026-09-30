from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HxcOwnedPathTest(unittest.TestCase):
    def test_owner_file_precedence_and_escape_rejection(self):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            base = Path(folder)
            owner = base / 'assets/imported_mods/owner'
            sibling = base / 'assets/imported_mods/sibling'
            owner.mkdir(parents=True)
            sibling.mkdir(parents=True)
            (owner / 'icon.png').write_bytes(b'owner')
            (sibling / 'icon.png').write_bytes(b'sibling')
            (base / 'assets/icon.png').write_bytes(b'global')
            (owner / 'linked.png').symlink_to(sibling / 'icon.png')
            fixture = '''class OwnedPathFixture {
 static function check(actual:Dynamic, expected:Dynamic):Void
  if (actual != expected) throw 'path mismatch: ' + actual + ' != ' + expected;
 static function main():Void {
  var root = '__OWNER__';
  check(HxcOwnedPath.existing(root, 'icon.png'), root + '/icon.png');
  check(HxcOwnedPath.existing(root, 'assets/icon.png'), root + '/icon.png');
  check(HxcOwnedPath.candidate(root, './new.png'), root + '/new.png');
  check(HxcOwnedPath.existing(root, 'new.png'), null);
  check(HxcOwnedPath.scoped(root, 'assets/dokicon.png'), root + '/dokicon.png');
  check(HxcOwnedPath.scoped(root, 'icon.png'), root + '/icon.png');
  for (key in ['../sibling/icon.png', 'assets/../../icon.png',
   '/assets/icon.png', 'C:/icon.png', 'a//icon.png', 'a/./icon.png',
   'a/../icon.png', 'bad' + String.fromCharCode(0) + '.png'])
   check(HxcOwnedPath.candidate(root, key), null);
  check(HxcOwnedPath.existing(root, 'linked.png'), null);
  check(HxcOwnedPath.scoped(root, 'linked.png'), null);
 }
}'''.replace('__OWNER__', owner.as_posix())
            (base / 'OwnedPathFixture.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                 '-cp', folder, '-main', 'OwnedPathFixture', '--interp'],
                cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_video_paths_stay_inside_the_selected_import(self):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            base = Path(folder)
            owner = base / 'assets/imported_mods/owner'
            sibling = base / 'assets/imported_mods/sibling'
            shared = base / 'assets/videos'
            (owner / 'videos').mkdir(parents=True)
            (sibling / 'videos').mkdir(parents=True)
            shared.mkdir(parents=True)
            (owner / 'videos/clip.mp4').write_bytes(b'owner')
            (owner / 'videos/videos').mkdir()
            (owner / 'videos/videos/rain.mp4').write_bytes(b'nested owner')
            (sibling / 'videos/clip.mp4').write_bytes(b'sibling')
            (owner / 'videos/linked.mp4').symlink_to(sibling / 'videos/clip.mp4')
            (shared / 'shared.webm').write_bytes(b'shared')
            fixture = '''class OwnedVideoPathFixture {
 static function check(actual:Dynamic, expected:Dynamic):Void
  if (actual != expected) throw 'video path mismatch: ' + actual + ' != ' + expected;
 static function path(owner:String, source:String):Dynamic
  return Reflect.field(HxcOwnedVideoPath.resolve(owner, source), 'path');
 static function error(owner:String, source:String):String
  return Reflect.field(HxcOwnedVideoPath.resolve(owner, source), 'error');
 static function main():Void {
  var owner = '__OWNER__';
  check(path(owner, owner + '/videos/clip.mp4'), owner + '/videos/clip.mp4');
  check(path(owner, 'videos/clip'), owner + '/videos/clip.mp4');
  check(path(owner, 'assets/videos/clip.mp4'), owner + '/videos/clip.mp4');
  check(path(owner, 'assets/videos/rain.mp4'), owner + '/videos/videos/rain.mp4');
  check(path(owner, 'rain'), owner + '/videos/videos/rain.mp4');
  check(path(owner, 'assets/videos/shared.webm'), 'assets/videos/shared.webm');
  check(path(owner, 'assets/imported_mods/sibling/videos/clip.mp4'), null);
  check(path(owner, '../sibling/videos/clip.mp4'), null);
  check(path(owner, 'videos/linked.mp4'), null);
  check(error(owner, 'videos/missing.mp4'), 'missing');
  check(error(owner, 'videos/clip.avi'), 'rejected');
 }
}'''.replace('__OWNER__', owner.as_posix())
            (base / 'OwnedVideoPathFixture.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                 '-cp', folder, '-main', 'OwnedVideoPathFixture', '--interp'],
                cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_proxy_rejects_unsafe_file_before_native_fallback(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        method = source[source.index('function makeHxcPathsProxy('):]
        file_api = method[method.index("Reflect.setField(proxy, 'file'"):]
        file_api = file_api[:file_api.index("Reflect.setField(proxy, 'xml'")]
        self.assertIn('HxcOwnedPath.candidate(root, file) == null', file_api)
        self.assertIn('HxcOwnedPath.scoped(root, file)', file_api)
        self.assertLess(file_api.index('HxcOwnedPath.candidate(root, file)'),
                        file_api.index('Paths.file(file)'))
        owner_branch = file_api[file_api.index("if (root != null && root != '')"):]
        owner_branch = owner_branch[:owner_branch.index("\n\t\t\treturn Paths.file(file);")]
        self.assertNotIn('Paths.file(file)', owner_branch)
        self.assertIn('HxcWindowCompat.setIcon(icon, hxcWindowOrigin)', source)

    def test_imported_window_icon_never_uses_a_global_or_sibling_file(self):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            base = Path(folder)
            owner = base / 'assets/imported_mods/owner'
            sibling = base / 'assets/imported_mods/sibling'
            owner.mkdir(parents=True)
            sibling.mkdir(parents=True)
            (sibling / 'dokicon.png').write_bytes(b'sibling icon')
            (base / 'assets').mkdir(exist_ok=True)
            (base / 'assets/dokicon.png').write_bytes(b'global icon')
            fixture = '''class OwnedWindowIconFixture {
 static function check(actual:Dynamic, expected:Dynamic):Void
  if (actual != expected) throw 'window icon path mismatch: ' + actual + ' != ' + expected;
 static function main():Void {
  var owner = '__OWNER__';
  check(HxcOwnedPath.scoped(owner, 'dokicon.png'), owner + '/dokicon.png');
  check(HxcOwnedPath.scoped(owner, 'assets/dokicon.png'), owner + '/dokicon.png');
  check(HxcOwnedPath.scoped(owner, '../sibling/dokicon.png'), null);
 }
}'''.replace('__OWNER__', owner.as_posix())
            (base / 'OwnedWindowIconFixture.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                 '-cp', folder, '-main', 'OwnedWindowIconFixture', '--interp'],
                cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
