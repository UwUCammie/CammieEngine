"""NMV package/core asset collection preserves paths and rejects escapes."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionAssetCollectorTest(unittest.TestCase):
    def run_haxe(self, work: Path, *args: str) -> subprocess.CompletedProcess[str]:
        (work / "Main.hx").write_text(r'''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  var args = Sys.args();
  var collection = NightmareVisionAssetCollector.collect(args[0]);
  check(collection.complete, 'collector incomplete: ' + collection.errors);
  var hasSymlinks = args[3] == 'true';
  check(collection.cycles == (hasSymlinks ? 1 : 0), 'ancestor cycle count mismatch');
  var paths:Array<String> = [];
  for (file in (cast collection.files:Array<Dynamic>)) paths.push(file.relative);
  paths.sort(Reflect.compare);
  check(paths.join('|') == 'characters/bf/bf.json'
    + '|data/d0/d1/d2/d3/d4/d5/d6/d7/d8/d9/d10/d11/d12/file.json'
    + '|images/aliasTarget/pixel.png'
    + (hasSymlinks ? '|images/atlas/alias/pixel.png' : '')
    + '|images/atlas/pixel.png|images/collision.png|noteskins/skin.json'
    + '|songs/track/Inst.ogg|stages/legacy/room.json',
    'unexpected collected paths: ' + paths.join('|'));
  var owner = args[1];
  check(NightmareVisionAssetCollector.resolveCoreAssetsRoot(owner) == args[2], 'sibling core root mismatch');
  check(NightmareVisionAssetCollector.resolveCoreAssetsRoot(args[2]) == args[2], 'assets root core mismatch');
 }
}''', newline='\n')
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main", *args],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=45,
        )

    def run_core_resolution_haxe(self, work: Path, *args: str) -> subprocess.CompletedProcess[str]:
        (work / "Main.hx").write_text(r'''
import haxe.io.Path;
import sys.FileSystem;
class Main {
 static function samePath(left:String, right:String):Bool {
  if (left == '' || right == '') return left == right;
  var a = Path.normalize(FileSystem.fullPath(left));
  var b = Path.normalize(FileSystem.fullPath(right));
  #if windows
  return a.toLowerCase() == b.toLowerCase();
  #else
  return a == b;
  #end
 }
 static function main() {
  var args = Sys.args();
  if (args.length % 2 != 0) throw 'expected path pairs';
  var index = 0;
  while (index < args.length) {
   var actual = NightmareVisionAssetCollector.resolveCoreAssetsRoot(args[index]);
   if (!samePath(actual, args[index + 1]))
    throw 'core root mismatch for ' + args[index] + ': got ' + actual + ', expected ' + args[index + 1];
   index += 2;
  }
 }
}''', newline='\n')
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main", *args],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=45,
        )

    def test_uncapped_tree_alias_cycle_and_separate_core_root(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            owner = work / "game/content/owner"
            core = work / "game/assets"
            (work / "game").mkdir()
            (work / "game/Project.xml").write_text(
                '<project><app package="com.nmvTeam.nightmareEngine" /></project>', newline='\n')
            deep = owner / "data"
            for index in range(13):
                deep /= f"d{index}"
            deep.mkdir(parents=True)
            (deep / "file.json").write_text("{}", newline='\n')
            (owner / "images/atlas").mkdir(parents=True)
            (owner / "images/atlas/pixel.png").write_bytes(b"pixel")
            (owner / "images/collision.png").write_bytes(b"owner")
            (owner / "images/aliasTarget").mkdir()
            (owner / "images/aliasTarget/pixel.png").write_bytes(b"aliased")
            symlinks_available = True
            try:
                (owner / "images/atlas/alias").symlink_to(owner / "images/aliasTarget", target_is_directory=True)
                (owner / "images/atlas/loop").symlink_to(owner / "images/atlas", target_is_directory=True)
            except (OSError, NotImplementedError):
                symlinks_available = False
                for link in (owner / "images/atlas/alias", owner / "images/atlas/loop"):
                    if link.is_symlink():
                        link.unlink()
            (owner / "characters/bf").mkdir(parents=True)
            (owner / "characters/bf/bf.json").write_text("{}", newline='\n')
            (owner / "noteskins").mkdir()
            (owner / "noteskins/skin.json").write_text("{}", newline='\n')
            (owner / "stages/legacy").mkdir(parents=True)
            (owner / "stages/legacy/room.json").write_text("{}", newline='\n')
            song = owner / "songs/track"
            song.mkdir(parents=True)
            (song / "Inst.ogg").write_bytes(b"audio")
            (core / "images").mkdir(parents=True)
            (core / "images/collision.png").write_bytes(b"core")
            result = self.run_haxe(work, str(owner), str(owner), str(core), str(symlinks_available).lower())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_core_resolution_requires_authenticated_content_container(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            game = work / 'engine'
            package = game / 'content' / 'package'
            package_assets = package / 'assets'
            engine_assets = game / 'assets'
            package_assets.mkdir(parents=True)
            engine_assets.mkdir()
            (game / 'Project.xml').write_text(
                '<project><app package="com.nmvTeam.nightmareEngine" /></project>', newline='\n')

            ordinary = work / 'ordinary-package'
            ordinary_assets = ordinary / 'assets'
            ordinary_assets.mkdir(parents=True)
            standalone_assets = work / 'standalone-assets' / 'assets'
            standalone_assets.mkdir(parents=True)

            unrelated = work / 'unmarked-game'
            unrelated_assets = unrelated / 'assets'
            unrelated_package = unrelated / 'content' / 'package'
            unrelated_assets.mkdir(parents=True)
            unrelated_package.mkdir(parents=True)
            (unrelated_package / 'assets').mkdir()

            malformed = work / 'malformed-game'
            (malformed / 'assets').mkdir(parents=True)
            (malformed / 'content' / 'package').mkdir(parents=True)
            (malformed / 'Project.xml').write_text('<project><app package="unterminated"', newline='\n')

            cases = [
                str(package), str(engine_assets),
                str(ordinary), str(ordinary_assets),
                str(standalone_assets), str(standalone_assets),
                str(unrelated_package), '',
                str(malformed / 'content' / 'package'), '',
            ]

            # A canonicalized content symlink is not a direct child of the game
            # root, even when a valid marker and sibling assets directory exist.
            symlink_game = work / 'symlink-game'
            (symlink_game / 'assets').mkdir(parents=True)
            (symlink_game / 'Project.xml').write_text(
                '<project><app package="com.nmvTeam.nightmareEngine" /></project>', newline='\n')
            external_content = work / 'external-content'
            (external_content / 'package').mkdir(parents=True)
            try:
                (symlink_game / 'content').symlink_to(external_content, target_is_directory=True)
                cases.extend([str(external_content / 'package'), ''])
            except (OSError, NotImplementedError):
                pass

            result = self.run_core_resolution_haxe(work, *cases)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_external_symlink_is_incomplete(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            root = work / "owner"
            external = work / "outside"
            (root / "images").mkdir(parents=True)
            (external / "nested").mkdir(parents=True)
            (external / "nested/file.png").write_bytes(b"outside")
            try:
                (root / "images/escape").symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks are unavailable in this environment')
            (work / "Main.hx").write_text(r'''
class Main {
 static function main() {
  var result = NightmareVisionAssetCollector.collect(Sys.args()[0]);
  if (result.complete) throw 'external symlink did not make collection incomplete';
  if (result.errors.length == 0) throw 'missing containment diagnostic';
  if (result.files.length != 0) throw 'external file was collected';
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main", str(root)],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
