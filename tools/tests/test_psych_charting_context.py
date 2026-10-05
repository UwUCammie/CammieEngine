"""Exercise the owner-keyed Psych chart-editor mode store."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;

 static function main():Void {
  var ownerA = 'assets/imported_mods/ChartOwner/Pack';
  var ownerB = 'assets/imported_mods/OtherOwner';
  check(!PsychOwnerChartingMode.get(ownerA), 'owner default was not false');
  check(!PsychOwnerChartingMode.get(null) && !PsychOwnerChartingMode.get(''),
   'blank native/NV roots must have no enabled state');

  PsychOwnerChartingMode.set(ownerA + '/', true);
  check(PsychOwnerChartingMode.get('assets\\imported_mods\\ChartOwner\\Pack'),
   'slash direction or trailing slash produced a different owner key');
  check(!PsychOwnerChartingMode.get(ownerB), 'one owner leaked charting mode into another');

  // The store takes only explicit owner strings and retains no PlayState or
  // scene object, so replacing a current-state reference cannot pin an owner.
  var oldScene:Dynamic = {ownerRoot:ownerA};
  var newScene:Dynamic = {ownerRoot:ownerB};
  oldScene = newScene;
  check(PsychOwnerChartingMode.get(ownerA) && !PsychOwnerChartingMode.get(ownerB),
   'mode state depended on a stale scene reference');

  PsychOwnerChartingMode.set(ownerB, true);
  PsychOwnerChartingMode.set(ownerA, false);
  check(!PsychOwnerChartingMode.get(ownerA) && PsychOwnerChartingMode.get(ownerB),
   'setting false did not clear only the requested owner');
  PsychOwnerChartingMode.clear(ownerB + '/');
  check(!PsychOwnerChartingMode.get(ownerB), 'clear did not restore the false default');

  PsychOwnerChartingMode.set('', true);
  PsychOwnerChartingMode.set(null, true);
  PsychOwnerChartingMode.set('assets/imported_mods/../native', true);
  PsychOwnerChartingMode.set('mods/unowned', true);
  check(!PsychOwnerChartingMode.get('') && !PsychOwnerChartingMode.get(null)
   && !PsychOwnerChartingMode.get('assets/imported_mods/../native')
   && !PsychOwnerChartingMode.get('mods/unowned'),
   'invalid or non-Psych roots acquired charting state');
  check(PsychOwnerChartingMode.get(ownerA) == false,
   'blank/invalid writes changed a valid owner');
 }
}'''


class PsychChartingContextTest(unittest.TestCase):
    def test_owner_mode_store_executes_with_normalized_owner_keys(self):
        source = (ROOT / "source/PsychOwnerChartingMode.hx").read_text(encoding="utf-8")
        self.assertNotIn("PlayState.instance", source)
        self.assertNotIn("Dynamic", source)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
