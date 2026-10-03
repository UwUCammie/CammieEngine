"""Existing NMV receipts gain menu metadata only for their exact source owner."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionProvenanceUpgradeTest(unittest.TestCase):
    def run_haxe(self, body, args=()):
        main = "class Main { static function main() {\n" + body + "\n} }\n"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            temp_path = Path(temp)
            (temp_path / "Main.hx").write_text(main, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", temp,
                 "--run", "Main", *map(str, args)],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_owner_upgrade_backs_up_raw_receipt_and_preserves_other_fields(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as fixture:
            self.run_haxe(r'''var root = Sys.args()[0];
var receipt = root + "/assets/data/fresh--nmv-owner/importProvenance.json";
var backupRoot = root + "/tmp/nmv-import-provenance-backups";
sys.FileSystem.createDirectory(root + "/assets");
sys.FileSystem.createDirectory(root + "/assets/data");
sys.FileSystem.createDirectory(root + "/assets/data/fresh--nmv-owner");
var original = '{"version":1,"sourceFolder":"fresh","sourceEngine":"Nightmare Vision",'
  + '"sourceOwner":"assets/imported_mods/dsides-owner",'
  + '"destinationFolder":"fresh--nmv-owner","display":"Fresh · D-Sides",'
  + '"userNote":{"keep":[3,true,"value"]}}';
sys.io.File.saveContent(receipt, original);
if (!NightmareVisionDifficultyCompat.needsProvenanceUpgrade(receipt,
  "assets/imported_mods/dsides-owner", "fresh--nmv-owner", ["Easy", "Normal", "Hard"], []))
  throw "exact owned legacy NMV receipt was not recognized";
var result = NightmareVisionDifficultyCompat.upgradeProvenance(receipt, backupRoot,
  "assets/imported_mods/dsides-owner", "fresh--nmv-owner", ["Easy", "Normal", "Hard"], []);
if (result.status != "upgraded") throw "receipt upgrade failed: " + result.status + " " + result.diagnostic;
if (sys.io.File.getContent(result.backup) != original)
  throw "backup did not preserve the exact original bytes";
var updated:Dynamic = haxe.Json.parse(sys.io.File.getContent(receipt));
if (Reflect.field(updated, "display") != "Fresh · D-Sides")
  throw "user-edited display field changed";
var userNote:Dynamic = Reflect.field(updated, "userNote");
if (Reflect.field(userNote, "keep").join(",") != "3,true,value")
  throw "custom receipt fields changed";
if (Reflect.field(updated, "sourceSelectableDifficulties").join(",") != "easy,normal,hard")
  throw "source selectable difficulties were not added";
if (Reflect.field(updated, "sourceUnsupportedDifficulties").length != 0)
  throw "empty unsupported-difficulty declaration was not added";
if (NightmareVisionDifficultyCompat.needsProvenanceUpgrade(receipt,
  "assets/imported_mods/dsides-owner", "fresh--nmv-owner", ["easy", "normal", "hard"], []))
  throw "upgraded receipt still appears to need repair";
''', [fixture])

    def test_owner_mismatch_existing_declaration_and_conflicting_backup_are_never_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as fixture:
            self.run_haxe(r'''var root = Sys.args()[0];
var folder = root + "/assets/data/song";
var receipt = folder + "/importProvenance.json";
var backupRoot = root + "/tmp/nmv-import-provenance-backups";
sys.FileSystem.createDirectory(root + "/assets");
sys.FileSystem.createDirectory(root + "/assets/data");
sys.FileSystem.createDirectory(folder);
var wrongOwner = '{"sourceEngine":"Nightmare Vision","sourceOwner":"foreign-owner",'
  + '"destinationFolder":"song","display":"User title"}';
sys.io.File.saveContent(receipt, wrongOwner);
var skipped = NightmareVisionDifficultyCompat.upgradeProvenance(receipt, backupRoot,
  "expected-owner", "song", ["easy", "normal", "hard"], []);
if (skipped.status != "not-needed" || sys.io.File.getContent(receipt) != wrongOwner)
  throw "foreign owner receipt was modified";
if (sys.FileSystem.exists(backupRoot)) throw "foreign receipt created an upgrade backup";

var declared = '{"sourceEngine":"Nightmare Vision","sourceOwner":"expected-owner",'
  + '"destinationFolder":"song","sourceSelectableDifficulties":["mania"],'
  + '"sourceUnsupportedDifficulties":[]}';
sys.io.File.saveContent(receipt, declared);
skipped = NightmareVisionDifficultyCompat.upgradeProvenance(receipt, backupRoot,
  "expected-owner", "song", ["easy", "normal", "hard"], []);
if (skipped.status != "not-needed" || sys.io.File.getContent(receipt) != declared)
  throw "existing user declaration was replaced";

var partial = '{"sourceEngine":"Nightmare Vision","sourceOwner":"expected-owner",'
  + '"destinationFolder":"song","sourceSelectableDifficulties":["mania"],'
  + '"display":"User title"}';
sys.io.File.saveContent(receipt, partial);
var partialUpgrade = NightmareVisionDifficultyCompat.upgradeProvenance(receipt, backupRoot,
  "expected-owner", "song", ["easy", "normal", "hard"], ["hard"]);
if (partialUpgrade.status != "upgraded") throw "missing unsupported list was not upgraded";
var partialRecord:Dynamic = haxe.Json.parse(sys.io.File.getContent(receipt));
if (Reflect.field(partialRecord, "sourceSelectableDifficulties").join(",") != "mania"
  || Reflect.field(partialRecord, "display") != "User title"
  || Reflect.field(partialRecord, "sourceUnsupportedDifficulties").join(",") != "hard")
  throw "partial upgrade overwrote existing receipt fields";

var legacy = '{"sourceEngine":"Nightmare Vision","sourceOwner":"expected-owner",'
  + '"destinationFolder":"song","display":"keep"}';
sys.io.File.saveContent(receipt, legacy);
sys.FileSystem.createDirectory(backupRoot);
sys.io.File.saveContent(backupRoot + "/song.json", "different prior backup");
var failed = NightmareVisionDifficultyCompat.upgradeProvenance(receipt, backupRoot,
  "expected-owner", "song", ["easy", "normal", "hard"], []);
if (failed.status != "failed" || sys.io.File.getContent(receipt) != legacy)
  throw "conflicting backup did not fail closed";
''', [fixture])

    def test_importer_repairs_only_same_owner_legacy_receipts(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
        repair = source[source.index("static public function songNeedsRepair(songData:SongImport)"):]
        repair = repair[:repair.index("\n\tstatic function findNamedDirectory")]
        self.assertIn("needsProvenanceUpgrade(receipt, expectedOwner", repair)
        writer = source[source.index("static function writeImportProvenance("):]
        writer = writer[:writer.index("\n\t/** Detect a missing/partial provenance write")]
        self.assertIn("tmp', 'nmv-import-provenance-backups", writer)
        self.assertIn("upgradeProvenance(existingProvenance", writer)
        self.assertIn("provenanceMerge.errors", source)


if __name__ == "__main__":
    unittest.main()
