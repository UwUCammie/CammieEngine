"""Freeplay labels imported rows from their exact destination provenance."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class FreeplaySourceDisplayTest(unittest.TestCase):
    def test_verified_provenance_labels_unqualified_imports(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        ownership_stub = '''
class ImportSongOwnership {
  public static function displayWithEngine(name:String, engine:String):String {
    var modName = name == null ? "" : StringTools.trim(name);
    var engineName = engine == null ? "" : StringTools.trim(engine);
    if (modName == "") return engineName;
    if (engineName == "") return modName;
    var suffixAt = modName.length - engineName.length;
    if (suffixAt >= 0 && modName.substr(suffixAt).toLowerCase() == engineName.toLowerCase()
        && (suffixAt == 0 || " :·-".indexOf(modName.charAt(suffixAt - 1)) >= 0))
      return modName;
    return modName + " · " + engineName;
  }
}
'''
        fixture = '''
class FreeplaySourceDisplayFixture {
  static function check(condition:Bool, message:String):Void {
    if (!condition) throw message;
  }
  static function main():Void {
    var provenance = {
      destinationFolder:"better-clone", display:"Better Clone",
      modName:"FNAS After Hours", sourceEngine:"Codename Engine"
    };
    var imported = FreeplaySourceDisplay.resolve("Better Clone", "", "better-clone", provenance);
    check(imported.title == "Better Clone", "ordinary chart title changed");
    check(imported.source == "FNAS After Hours · Codename Engine",
      "unqualified imported row missed its source label");

    var collision = FreeplaySourceDisplay.resolve(
      "Tutorial · D-Sides · Codename Engine", "", "tutorial--codename-engine-a1b2c3d4e5",
      {destinationFolder:"tutorial--codename-engine-a1b2c3d4e5",
       display:"Tutorial · D-Sides · Codename Engine", modName:"D-Sides",
       sourceEngine:"Codename Engine"});
    check(collision.title == "Tutorial", "collision suffix was not separated");
    check(collision.source == "D-Sides · Codename Engine", "collision source changed");

    var mismatched = FreeplaySourceDisplay.resolve("Better Clone", "", "better-clone",
      {destinationFolder:"some-other-song", modName:"Wrong Owner", sourceEngine:"Psych Engine"});
    check(mismatched.title == "Better Clone" && mismatched.source == "",
      "a different folder's receipt claimed this row");

    var partialReceipt = FreeplaySourceDisplay.resolve("Better Clone", "", "better-clone",
      {destinationFolder:"better-clone", modName:"FNAS After Hours", sourceEngine:7});
    check(partialReceipt.source == "FNAS After Hours",
      "a malformed optional engine field blocked a valid package name");

    var base = FreeplaySourceDisplay.resolve("Tutorial", "", "tutorial", null);
    check(base.title == "Tutorial" && base.source == "", "base row acquired a source label");

    var explicit = FreeplaySourceDisplay.resolve("Custom title", "Chosen label", "better-clone",
      {destinationFolder:"other", modName:"Wrong Owner", sourceEngine:"Psych Engine"});
    check(explicit.title == "Custom title" && explicit.source == "Chosen label",
      "explicit registry label did not take precedence");

    var repaired = FreeplaySourceDisplay.resolve(
      "Philly Nice · content · Psych Engine", "fnf_fnia · Psych Engine",
      "philly-nice--psych-engine-68fb3cd061",
      {destinationFolder:"philly-nice--psych-engine-68fb3cd061",
       modName:"content", sourceEngine:"Psych Engine"}, "",
      "content · Psych Engine");
    check(repaired.title == "Philly Nice", "validated generic display suffix remained in title");
    check(repaired.source == "fnf_fnia · Psych Engine", "validated inferred source label was lost");

    var repairedCaptionOnly = FreeplaySourceDisplay.resolve(
      "Philly Nice", "fnf_fnia · Psych Engine",
      "philly-nice--psych-engine-68fb3cd061",
      {destinationFolder:"philly-nice--psych-engine-68fb3cd061",
       modName:"content", sourceEngine:"Psych Engine"});
    check(repairedCaptionOnly.title == "Philly Nice",
      "caption repair changed a title without the validated stale suffix");

    var authored = FreeplaySourceDisplay.resolve(
      "A title · content · Psych Engine", "User Pack", "authored-song",
      {destinationFolder:"authored-song", modName:"content", sourceEngine:"Psych Engine"});
    check(authored.title == "A title · content · Psych Engine" && authored.source == "User Pack",
      "authored title suffix was stripped without a validated stale label");
    Sys.println("OK");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            shutil.copy2(ROOT / "source/FreeplaySourceDisplay.hx", folder)
            (Path(folder) / "ImportSongOwnership.hx").write_text(ownership_stub, encoding="utf-8", newline='\n')
            (Path(folder) / "FreeplaySourceDisplayFixture.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "--run", "FreeplaySourceDisplayFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_freeplay_reads_receipts_for_unlabeled_or_legacy_generic_rows(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        start = source.index("function sourceDisplayFor(song:SongMetadata)")
        end = source.index("\n\t/** Read only the selected owner's bounded chart directory", start)
        method = source[start:end]
        self.assertLess(method.index("if (song.sourceResolved)"),
                        method.index("FNFAssets.exists(path)"))
        self.assertIn("looksLikeGenericSourceLabel(existingSourceLabel)", method)
        self.assertIn("songKey.indexOf('/') < 0", method)
        self.assertIn("songKey.indexOf('\\\\') < 0", method)
        self.assertIn("importProvenance.json", method)
        self.assertIn("inferredGenericLabelFromReceipt(", method)
        self.assertIn("provenance, song.songName, song.ownerRoot, expectedEngine", method)
        self.assertIn("currentLabel == receiptGenericLabel", method)
        self.assertIn("&& currentLabel == receiptGenericLabel);", method)
        self.assertIn("StringTools.endsWith(song.display, staleDisplaySuffix)", method)
        self.assertLess(method.index("inferredGenericLabelFromReceipt("),
                        method.index("FreeplaySourceDisplay.resolve("))
        self.assertIn("if (mayRepair && !song.ownerResolved)", method)
        self.assertIn("chartTitle, staleGenericLabel", method)


if __name__ == "__main__":
    unittest.main()
