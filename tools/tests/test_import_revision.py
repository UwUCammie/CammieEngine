"""Compatibility receipts use importer revisions, not app release numbers."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class ImportRevisionTest(unittest.TestCase):
    def test_legacy_current_stale_future_and_engine_mismatch_assessments(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var legacy = ImportRevision.assess({applicationVersion:"0.0.8"}, "Psych Engine");
  check(legacy.status == ImportRevision.UNKNOWN, "legacy app version was mistaken for a compatibility receipt");

  var current = ImportRevision.current("psychengine", "0.0.8");
  check(current.engineRevision == 10
   && ImportRevision.assess({schemaVersion:1, commonRevision:3, sourceEngine:"Psych Engine", engineRevision:8},
    "Psych Engine").status == ImportRevision.OUTDATED,
   "older Psych receipts did not request source-profile republishing");
  check(ImportRevision.current("V-Slice").engineRevision == 2
    && ImportRevision.assess({schemaVersion:1, commonRevision:3, sourceEngine:"V-Slice", engineRevision:1},
      "V-Slice").status == ImportRevision.OUTDATED,
    "V-Slice variation-discovery changes did not schedule retained-source refresh");
  check(current.sourceEngine == "Psych Engine" && current.commonRevision > 0 && current.engineRevision > 0,
   "explicit common and engine revisions were not recorded");
  check(current.commonRevision == 3
   && ImportRevision.assess({schemaVersion:1, commonRevision:2, sourceEngine:"Psych Engine",
    engineRevision:1}, "Psych Engine").status == ImportRevision.OUTDATED,
   "shared display metadata changes do not trigger retained-source refresh");
	 var priorNmv = {schemaVersion:1, commonRevision:3, sourceEngine:"Nightmare Vision",
	 engineRevision:10};
  check(ImportRevision.assess(priorNmv, "Nightmare Vision").status == ImportRevision.OUTDATED,
	 "Nightmare Vision revision-10 receipts were not scheduled for legacy-content refresh");
  check(ImportRevision.current("Nightmare Vision").engineRevision == 11,
	 "Nightmare Vision legacy content discovery did not advance the engine revision");
  current.applicationVersion = "0.0.1-alpha.8";
  check(ImportRevision.assess(current, "Psych Engine").status == ImportRevision.CURRENT,
   "app release number incorrectly determined importer compatibility");

  var oldCommon = ImportRevision.current("Psych Engine");
  oldCommon.commonRevision--;
  check(ImportRevision.assess(oldCommon, "Psych Engine").status == ImportRevision.OUTDATED,
   "older common compatibility revision was not detected");
  var oldSchema = ImportRevision.current("Psych Engine");
  oldSchema.schemaVersion--;
  check(ImportRevision.assess(oldSchema, "Psych Engine").status == ImportRevision.OUTDATED,
   "older revision schema was not detected");
  var futureSchema = ImportRevision.current("Psych Engine");
  futureSchema.schemaVersion++;
  check(ImportRevision.assess(futureSchema, "Psych Engine").status == ImportRevision.FUTURE,
   "newer revision schema was not preserved as future");
  var oldEngine = ImportRevision.current("Psych Engine");
  oldEngine.engineRevision--;
  check(ImportRevision.assess(oldEngine, "Psych Engine").status == ImportRevision.OUTDATED,
   "older engine compatibility revision was not detected");
  var future = ImportRevision.current("Psych Engine");
  future.engineRevision++;
  check(ImportRevision.assess(future, "Psych Engine").status == ImportRevision.FUTURE,
   "newer engine compatibility revision was not preserved as future");
  check(ImportRevision.assess(ImportRevision.current("Codename Engine"), "Psych Engine").status == ImportRevision.UNKNOWN,
   "engine mismatch claimed current compatibility");
  check(ImportRevision.assess({schemaVersion:1, commonRevision:1, sourceEngine:"Unrecognized", engineRevision:1},
   "Psych Engine").status == ImportRevision.UNKNOWN, "unrecognized source engine claimed current compatibility");
 }
}''', newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=base, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
