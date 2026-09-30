"""Owner-scoped collection for Codename's composed Sparrow atlas paths."""

from pathlib import Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameDynamicAtlasAssetsTest(unittest.TestCase):
    def test_composed_prefix_collects_unbounded_direct_png_xml_assets(self):
        importer = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("CodenameDynamicAtlasAssets.filesFor(sourceRoot", importer)
        self.assertIn("appendResolvedAsset(asset.source, asset.relative)", importer)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            root = Path(temporary) / "owner"
            icons = root / "images/menus/freeplay/icons"
            nested = icons / "nested"
            nested.mkdir(parents=True)
            outside = Path(temporary) / "outside.png"
            outside.write_bytes(b"outside")

            for index in range(140):
                stem = f"icon-{index:03d}"
                (icons / f"{stem}.png").write_bytes(b"png")
                (icons / f"{stem}.xml").write_text("<TextureAtlas/>")
            for stem in ("GF", "gf"):
                (icons / f"{stem}.png").write_bytes(b"png")
                (icons / f"{stem}.xml").write_text("<TextureAtlas/>")
            (icons / "ignored.txt").write_text("not an atlas")
            (nested / "nested.png").write_bytes(b"not a direct child")
            try:
                (icons / "escape.png").symlink_to(outside)
            except OSError:
                pass

            script = Path(temporary) / "FreeplayState.hx"
            script.write_text(
                "var directory = 'menus/freeplay/';\n"
                "// Paths.getSparrowAtlas('ignored/' + song.icon);\n"
                "Paths.getSparrowAtlas(directory + 'icons/' + song.icon);\n"
            )
            fixture = r'''import sys.io.File;
class Main {
  static inline var OWNER = @@OWNER@@;
  static inline var SCRIPT = @@SCRIPT@@;
  static function main():Void {
    var plan = CodenameDynamicAtlasAssets.filesFor(OWNER, null, File.getContent(SCRIPT));
    if (plan.diagnostics.length != 0) throw plan.diagnostics.join("; ");
    if (plan.files.length != 284) throw "expected all 142 direct PNG/XML pairs, got " + plan.files.length;
    var names:Map<String, Bool> = new Map();
    for (file in plan.files) {
      if (!StringTools.startsWith(file.relative, "images/menus/freeplay/icons/"))
        throw "asset escaped its selected-owner atlas directory: " + file.relative;
      var extension = haxe.io.Path.extension(file.relative).toLowerCase();
      if (extension != "png" && extension != "xml") throw "non-atlas file included: " + file.relative;
      names.set(file.relative, true);
    }
    for (name in ["GF.png", "GF.xml", "gf.png", "gf.xml", "icon-139.png", "icon-139.xml"])
      if (!names.exists("images/menus/freeplay/icons/" + name))
        throw "missing case-preserved or over-128 atlas asset: " + name;
    if (names.exists("images/menus/freeplay/icons/ignored.txt")
      || names.exists("images/menus/freeplay/icons/nested.png")
      || names.exists("images/menus/freeplay/icons/escape.png"))
      throw "non-atlas or escaped asset was imported";

    var unresolved = CodenameDynamicAtlasAssets.filesFor(OWNER, null,
      "Paths.getSparrowAtlas(song.icon);");
    if (unresolved.files.length != 0 || unresolved.diagnostics.length != 1
      || unresolved.diagnostics[0].indexOf("no statically known directory prefix") < 0)
      throw "unresolved dynamic atlas path was not reported";

    var reassigned = CodenameDynamicAtlasAssets.filesFor(OWNER, null,
      "var directory = 'menus/freeplay/'; directory = other; "
      + "Paths.getSparrowAtlas(directory + 'icons/' + song.icon);");
    if (reassigned.files.length != 0 || reassigned.diagnostics.length != 1
      || reassigned.diagnostics[0].indexOf("no statically known directory prefix") < 0)
      throw "reassigned path prefix was incorrectly treated as constant";

    var missing = CodenameDynamicAtlasAssets.filesFor(OWNER, null,
      "var directory = 'missing/'; Paths.getSparrowAtlas(directory + song.icon);");
    if (missing.files.length != 0 || missing.diagnostics.length != 1
      || missing.diagnostics[0].indexOf("not found") < 0)
      throw "missing dynamic atlas directory was not reported";
  }
}'''
            fixture = fixture.replace("@@OWNER@@", json.dumps(str(root)))
            fixture = fixture.replace("@@SCRIPT@@", json.dumps(str(script)))
            (Path(temporary) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", temporary,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
