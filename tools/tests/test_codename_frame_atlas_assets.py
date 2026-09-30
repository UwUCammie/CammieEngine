"""Owner-scoped source planning for Codename Paths.getFrames references."""

from pathlib import Path
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
            (owner / "images/main/sonic.xml").write_text("<TextureAtlas/>")
            for page in (1, 2):
                (owner / f"images/sheets/{page}.png").write_bytes(f"page {page}".encode())
                (owner / f"images/sheets/{page}.xml").write_text(f"<TextureAtlas page='{page}'/>")
            (owner / "images/packed.png").write_bytes(b"packed")
            (owner / "images/packed.txt").write_text("frame rect\n")
            (owner / "images/animated/Animation.json").write_text("{}")
            (owner / "images/animated/spritemap1.png").write_bytes(b"animate page")
            (owner / "images/animated/nested/spritemap1.json").write_text("{}")
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
            )
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main", str(owner)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
