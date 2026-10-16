"""Owner-scoped source planning for Codename Paths.getFrames references."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class CodenameFrameAtlasAssetsTest(unittest.TestCase):
    def test_direct_page_animate_and_missing_frame_assets_are_scoped(self):
        with tempfile.TemporaryDirectory(prefix="codename-frame-atlas-", dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            other = base / "other"
            (owner / "images/main").mkdir(parents=True)
            (owner / "images/sheets").mkdir(parents=True)
            (owner / "images/packed").mkdir(parents=True)
            (owner / "images/animated/nested").mkdir(parents=True)
            (owner / "images/broken").mkdir(parents=True)
            (other / "images").mkdir(parents=True)
            (owner / "images/main/sonic.png").write_bytes(b"owner image")
            (owner / "images/main/sonic.xml").write_text("<TextureAtlas/>", newline='\n')
            for page in (1, 2):
                (owner / f"images/sheets/{page}.png").write_bytes(f"page {page}".encode())
                (owner / f"images/sheets/{page}.xml").write_text(f"<TextureAtlas page='{page}'/>", newline='\n')
            (owner / "images/packed.png").write_bytes(b"packed")
            (owner / "images/packed.txt").write_text("frame rect\n", newline='\n')
            (owner / "images/animated/Animation.json").write_text("{}", newline='\n')
            (owner / "images/animated/spritemap1.png").write_bytes(b"animate page")
            (owner / "images/animated/nested/spritemap1.json").write_text("{}", newline='\n')
            (owner / "images/broken/1.png").write_bytes(b"incomplete page")
            (other / "images/escape.png").write_bytes(b"foreign image")
            try:
                (owner / "images/escape.png").symlink_to(other / "images/escape.png")
            except OSError:
                pass

            (base / "Main.hx").write_text(
                """class Main {
 static function require(plan:CodenameFrameAtlasAssets.CodenameFrameAtlasPlan, mode:String, count:Int):Void {
  if (plan.mode != mode || plan.files.length != count)
   throw mode + " plan mismatch: " + plan.mode + "/" + plan.files.length;
 }
 static function main():Void {
  var root = Sys.args()[0];
  var direct = CodenameFrameAtlasAssets.plan(root, "main/sonic");
  require(direct, "sparrow", 2);
  if (direct.files[0].relative != "images/main/sonic.png"
      || direct.files[1].relative != "images/main/sonic.xml"
      || sys.io.File.getContent(direct.files[0].source) != "owner image")
   throw "direct Sparrow dependency or owner provenance";
  require(CodenameFrameAtlasAssets.plan(root, "sheets"), "pages", 4);
  require(CodenameFrameAtlasAssets.plan(root, "packed"), "packer", 2);
  var animate = CodenameFrameAtlasAssets.plan(root, "animated");
  require(animate, "animate", 3);
  if (animate.files[0].relative != "images/animated/Animation.json"
      || animate.files[1].relative != "images/animated/nested/spritemap1.json")
   throw "Animate folder contents were not preserved";
  var incomplete = CodenameFrameAtlasAssets.plan(root, "broken");
  if (incomplete.files.length != 0 || incomplete.diagnostics.length == 0)
   throw "incomplete numbered Sparrow page was not diagnosed";
  var missing = CodenameFrameAtlasAssets.plan(root, "not-present");
  if (missing.files.length != 0 || missing.diagnostics.length == 0)
   throw "missing key was not diagnosed";
  var traversal = CodenameFrameAtlasAssets.plan(root, "../other/images/escape");
  if (traversal.files.length != 0 || traversal.diagnostics.length == 0)
   throw "traversal key escaped source root";
  var symlink = CodenameFrameAtlasAssets.plan(root, "escape");
  if (symlink.files.length != 0) throw "symlink asset escaped source root";
 }
}"""
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main", str(owner)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_v_slice_shared_library_art_is_found_with_its_images_destination(self):
        with tempfile.TemporaryDirectory(prefix="vslice-frame-atlas-", dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            (owner / "images/props/local").mkdir(parents=True)
            (owner / "shared/images/props/gremlin").mkdir(parents=True)
            (owner / "shared/images/props/flat").mkdir(parents=True)
            (owner / "images/props/local/Animation.json").write_text("{}", newline='\n')
            (owner / "shared/images/props/gremlin/Animation.json").write_text("{}", newline='\n')
            (owner / "shared/images/props/gremlin/spritemap1.png").write_bytes(b"page")
            (owner / "shared/images/props/flat.png").write_bytes(b"flat")
            (owner / "shared/images/props/flat.xml").write_text("<TextureAtlas/>", newline='\n')
            (base / "Main.hx").write_text(
                """class Main {
 static function main():Void {
  var root = Sys.args()[0];
  var local = CodenameFrameAtlasAssets.planWithSharedLibrary(root, "props/local");
  if (local.mode != "animate" || local.files.length != 1 || local.files[0].source.indexOf("shared") >= 0)
   throw "an art folder under images was not preferred: " + local.mode;
  var shared = CodenameFrameAtlasAssets.planWithSharedLibrary(root, "props/gremlin");
  if (shared.mode != "animate" || shared.files.length != 2
      || shared.files[0].relative != "images/props/gremlin/Animation.json"
      || shared.files[1].relative != "images/props/gremlin/spritemap1.png"
      || shared.files[0].source.indexOf("shared") < 0)
   throw "shared Animate folder was not planned: " + shared.mode + "/" + shared.files.length;
  var flat = CodenameFrameAtlasAssets.planWithSharedLibrary(root, "props/flat");
  if (flat.mode != "sparrow" || flat.files.length != 2 || flat.files[0].relative != "images/props/flat.png")
   throw "shared Sparrow atlas was not planned";
  var missing = CodenameFrameAtlasAssets.planWithSharedLibrary(root, "props/none");
  if (missing.files.length != 0 || missing.diagnostics.length == 0)
   throw "a missing key was not diagnosed";
  if (CodenameFrameAtlasAssets.plan(root, "props/gremlin").files.length != 0)
   throw "plain planning must stay scoped to the given root";
 }
}"""
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main", str(owner)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("CodenameFrameAtlasAssets.planWithSharedLibrary(sourceRoot, stem)", module)


if __name__ == "__main__":
    unittest.main()
