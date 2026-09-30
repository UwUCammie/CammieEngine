"""Selected-owner Codename splash XML and Sparrow atlas import closure."""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DSIDES = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/codename/"
    "D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX"
)
FNAS = Path("/run/media/cammie/External Storage/FNF-Example-Mods/fnas_after_hours")


class CodenameSplashDependencyTest(unittest.TestCase):
    def test_direct_and_legacy_layouts_are_selected_owner_scoped(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("CodenameSplashDependencies.filesFor(sourceRoot)", module)
        self.assertIn("appendResolvedAsset(dependency.source, dependency.relative)", module)
        fixture = r'''import sys.FileSystem;
class Main {
 static function fail(message:String):Void throw message;
 static function has(plan:Dynamic, relative:String):Bool {
  for (file in (cast Reflect.field(plan, "files"):Array<Dynamic>)) if (file.relative == relative) return true;
  return false;
 }
 static function main():Void {
  var selected = Sys.args()[0];
  var other = Sys.args()[1];
  var direct = CodenameSplashDependencies.filesFor(selected);
  var wanted = ["data/splashes/ourple.xml", "images/game/splashes/ourple.png",
   "images/game/splashes/ourple.xml"];
  for (relative in wanted) if (!has(direct, relative)) fail("direct layout omitted " + relative);
  for (file in direct.files) {
   if (!CodenameScriptDiscovery.withinRoot(selected, file.source)) fail("direct source escaped owner: " + file.source);
   if (file.source.indexOf(other + "/") == 0) fail("borrowed another owner: " + file.source);
  }
  if (has(direct, "images/game/splashes/unrelated.png")) fail("unreferenced atlas was copied");
  if (has(direct, "images/game/splashes/leak.png")) fail("symlinked atlas escaped selected owner");
  var leakReported = false;
  for (diagnostic in direct.diagnostics)
   if (diagnostic.indexOf("images/game/splashes/leak.png") >= 0) leakReported = true;
  if (!leakReported) fail("selected-owner symlink escape was not diagnosed");
  var legacy = CodenameSplashDependencies.filesFor(other);
  var legacyWanted = ["data/splashes/pixel-default.xml", "images/game/splashes/pixel.png",
   "images/game/splashes/pixel.xml"];
  for (relative in legacyWanted) if (!has(legacy, relative)) fail("legacy layout omitted " + relative);
  for (file in legacy.files)
   if (!CodenameScriptDiscovery.withinRoot(other, file.source)) fail("legacy source escaped owner: " + file.source);
  if (FileSystem.exists(other + "/assets/images/game/splashes/pixel-secret.png"))
   fail("fixture should model missing pixel secret atlas");
  var missing = false;
  for (diagnostic in legacy.diagnostics)
   if (diagnostic.indexOf("images/game/splashes/pixel-secret.png") >= 0) missing = true;
  if (!missing) fail("missing declared atlas was not diagnosed");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            selected, other = base / "direct-owner", base / "legacy-owner"
            direct_files = {
                "data/splashes/ourple.xml": '<splashes sprite="game/splashes/ourple"/>',
                "data/splashes/leak.xml": '<splashes sprite="game/splashes/leak"/>',
                "images/game/splashes/ourple.png": "direct png",
                "images/game/splashes/ourple.xml": "direct atlas xml",
                "images/game/splashes/unrelated.png": "ignore",
            }
            legacy_files = {
                "assets/data/splashes/pixel-default.xml": '<splashes sprite="game/splashes/pixel"/>',
                "assets/images/game/splashes/pixel.png": "legacy png",
                "assets/images/game/splashes/pixel.xml": "legacy atlas xml",
                "assets/data/splashes/pixel-secret.xml": '<splashes sprite="game/splashes/pixel-secret"/>',
            }
            for root, entries in ((selected, direct_files), (other, legacy_files)):
                for relative, content in entries.items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
            outside = base / "outside.png"
            outside.write_text("outside owner")
            escaped_atlas = selected / "images/game/splashes/leak.png"
            try:
                escaped_atlas.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            (base / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main",
                 str(selected), str(other)],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_d_sides_and_fnas_xml_are_read_only_parser_fixtures(self):
        if not DSIDES.is_dir() or not FNAS.is_dir():
            self.skipTest("mounted Codename donor fixtures are unavailable")
        fixture = r'''import sys.io.File;
class Main {
 static function fail(message:String):Void throw message;
 static function has(plan:Dynamic, relative:String):Bool {
  for (file in (cast Reflect.field(plan, "files"):Array<Dynamic>)) if (file.relative == relative) return true;
  return false;
 }
 static function main():Void {
  var dside = Sys.args()[0];
  var fnas = Sys.args()[1];
  for (name in ["default", "ourple"]) {
   var path = dside + "/data/splashes/" + name + ".xml";
   var data = CodenameSplashData.parse(File.getContent(path));
   if (data == null) fail("mounted D-Sides XML did not parse: " + path);
   var expectedSprite = name == "ourple" ? "game/splashes/ourple_splashes" : "game/splashes/default";
   if (data.sprite != expectedSprite) fail("mounted D-Sides sprite fixture changed: " + name);
  }
  var dsidePlan = CodenameSplashDependencies.filesFor(dside);
  for (relative in ["data/splashes/default.xml", "data/splashes/ourple.xml",
    "images/game/splashes/default.png", "images/game/splashes/default.xml",
    "images/game/splashes/ourple_splashes.png", "images/game/splashes/ourple_splashes.xml"])
   if (!has(dsidePlan, relative)) fail("D-Sides plan omitted " + relative);
  for (file in dsidePlan.files)
   if (!CodenameScriptDiscovery.withinRoot(dside, file.source)) fail("D-Sides source escaped selected owner");

  var fnasPlan = CodenameSplashDependencies.filesFor(fnas);
  for (name in ["default", "secret", "pixel-default", "pixel-secret"]) {
   var path = fnas + "/assets/data/splashes/" + name + ".xml";
   var data = CodenameSplashData.parse(File.getContent(path));
   if (data == null) fail("mounted FNAS XML did not parse: " + path);
   if (name == "pixel-default" && data.sprite != "stages/school/ui/pixel-splashes")
    fail("mounted FNAS pixel-default fixture changed");
   if (name == "pixel-secret" && data.sprite != "stages/school/ui/pixel-secret-splashes")
    fail("mounted FNAS pixel-secret fixture changed");
   if (!has(fnasPlan, "data/splashes/" + name + ".xml")) fail("FNAS plan omitted " + name + " definition");
  }
  for (relative in ["images/game/splashes/default.png", "images/game/splashes/default.xml",
    "images/game/splashes/secret.png", "images/game/splashes/secret.xml"])
   if (!has(fnasPlan, relative)) fail("FNAS available atlas omitted " + relative);
  var missingPixelDefault = false;
  var missingPixelSecret = false;
  for (diagnostic in fnasPlan.diagnostics) {
   if (diagnostic.indexOf("images/stages/school/ui/pixel-splashes.png") >= 0) missingPixelDefault = true;
   if (diagnostic.indexOf("images/stages/school/ui/pixel-secret-splashes.png") >= 0) missingPixelSecret = true;
  }
  if (!missingPixelDefault || !missingPixelSecret) fail("FNAS missing pixel atlas pair was not diagnosed");
  for (file in fnasPlan.files)
   if (!CodenameScriptDiscovery.withinRoot(fnas, file.source)) fail("FNAS source escaped selected owner");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main",
                 str(DSIDES), str(FNAS)],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
