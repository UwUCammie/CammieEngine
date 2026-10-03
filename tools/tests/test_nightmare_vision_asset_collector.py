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
  check(collection.cycles == 1, 'ancestor cycle was not stopped');
  var paths:Array<String> = [];
  for (file in (cast collection.files:Array<Dynamic>)) paths.push(file.relative);
  paths.sort(Reflect.compare);
  check(paths.join('|') == 'characters/bf/bf.json'
    + '|data/d0/d1/d2/d3/d4/d5/d6/d7/d8/d9/d10/d11/d12/file.json'
    + '|images/aliasTarget/pixel.png|images/atlas/alias/pixel.png'
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

    def test_uncapped_tree_alias_cycle_and_separate_core_root(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            owner = work / "game/content/owner"
            core = work / "game/assets"
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
            (owner / "images/atlas/alias").symlink_to(owner / "images/aliasTarget", target_is_directory=True)
            (owner / "images/atlas/loop").symlink_to(owner / "images/atlas", target_is_directory=True)
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
            result = self.run_haxe(work, str(owner), str(owner), str(core))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_external_symlink_is_incomplete(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            root = work / "owner"
            external = work / "outside"
            (root / "images").mkdir(parents=True)
            (external / "nested").mkdir(parents=True)
            (external / "nested/file.png").write_bytes(b"outside")
            (root / "images/escape").symlink_to(external, target_is_directory=True)
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
