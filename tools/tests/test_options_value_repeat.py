"""Exercise frame-rate independent held changes for numeric menu options."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class OptionsValueRepeatTests(unittest.TestCase):
    def run_haxe(self, main_source):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = FixturePath(folder)
            (base / "OptionsValueRepeat.hx").write_text(
                (ROOT / "source/OptionsValueRepeat.hx").read_text(),
                encoding="utf-8", newline="\n",
            )
            (base / "Main.hx").write_text(main_source, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_repeat_rate_edges_selection_release_and_hitch_bound(self):
        self.run_haxe('''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  for (rate in [10, 60, 480, 1440, 5000]) {
   var repeat = new OptionsValueRepeat();
   check(repeat.update(1, 0, 0, true)==1, "new hold did not change immediately at " + rate + " FPS");
   var changes = 0;
   for (frame in 0...rate)
    changes += repeat.update(1, 1.0/rate, 0, true);
   check(changes >= 59 && changes <= 60,
    "one second of hold produced " + changes + " repeats at " + rate + " FPS");
  }

  var quarterSecond = new OptionsValueRepeat();
  var repeatSteps = quarterSecond.update(1, 0, 0, true);
  for (frame in 0...15)
   repeatSteps += quarterSecond.update(1, 1.0/60, 0, true);
  check(repeatSteps >= 14 && repeatSteps <= 18,
   "a quarter-second hold produced " + repeatSteps + " total option changes");
  var fpsCap = 10 + repeatSteps * 10;
  var offset = repeatSteps * 0.1;
  check(fpsCap >= 150 && fpsCap <= 190 && Math.abs(offset - 1.6) <= 0.2,
   "FPS-cap or offset changes did not use the same repeat count");

  var variable = new OptionsValueRepeat();
  check(variable.update(1, 0, 4, true)==1, "variable-clock hold missed initial change");
  var irregular = [0.005, 0.025, 0.003, 0.067, 0.016, 0.001, 0.083,
   0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
  var variableChanges = 0;
  for (delta in irregular)
   variableChanges += variable.update(1, delta, 4, true);
  check(variableChanges >= 59 && variableChanges <= 61,
   "variable frame intervals produced " + variableChanges + " repeats over one second");

  var hitch = new OptionsValueRepeat();
  check(hitch.update(1, 0, 0, true)==1, "hitch scenario missed initial change");
  check(hitch.update(1, 1, 0, true)==OptionsValueRepeat.MAX_CHANGES_PER_FRAME,
   "long hitch was not bounded to the per-frame catch-up limit");
  check(hitch.update(1, 0, 0, true)==0,
   "long hitch left a repeat backlog for the next frame");
  check(hitch.update(1, OptionsValueRepeat.REPEAT_INTERVAL, 0, true)==1,
   "repeat timing did not recover after a hitch");
  var hugeCatchup = hitch.update(1, 1e100, 0, true);
  check(hugeCatchup==OptionsValueRepeat.MAX_CHANGES_PER_FRAME,
   "very large finite hitch produced " + hugeCatchup + " repeat changes");
  check(hitch.update(1, 0, 0, true)==0,
   "very large finite hitch left a repeat backlog for the next frame");

  var edges = new OptionsValueRepeat();
  check(edges.update(1, 0, 2, true)==1, "right press did not produce one initial change");
  check(edges.update(1, OptionsValueRepeat.REPEAT_INTERVAL/2, 2, true)==0,
   "held right repeated before its interval");
  check(edges.update(-1, 0.5, 2, true)==1,
   "direction reversal did not produce exactly one immediate change");
  check(edges.update(-1, OptionsValueRepeat.REPEAT_INTERVAL, 2, true)==1,
   "direction reversal retained stale timing");
  check(edges.update(0, 1, 2, true)==0, "vertical or neutral input changed the value");
  check(edges.update(-1, 0, 2, true)==1, "released key did not re-arm as one fresh press");

  var selection = new OptionsValueRepeat();
  check(selection.update(1, 0, 0, true)==1, "selection scenario missed initial change");
  check(selection.update(1, OptionsValueRepeat.REPEAT_INTERVAL/2, 0, true)==0,
   "selection scenario repeated too early");
  check(selection.update(1, OptionsValueRepeat.REPEAT_INTERVAL, 1, true)==0,
   "held direction changed the newly selected option immediately");
  check(selection.update(1, OptionsValueRepeat.REPEAT_INTERVAL/2, 1, true)==0,
   "selection change retained elapsed repeat time");
  check(selection.update(1, OptionsValueRepeat.REPEAT_INTERVAL/2, 1, true)==1,
   "selection change did not restart repeat timing");

  var freshSelection = new OptionsValueRepeat();
  check(freshSelection.update(0, 0, 0, false)==0,
   "inactive menu unexpectedly changed a value");
  check(freshSelection.update(1, 0, 1, true)==1,
   "fresh Ctrl press on a newly selected row was suppressed");

  var reversedSelection = new OptionsValueRepeat();
  check(reversedSelection.update(1, 0, 0, true)==1,
   "reversed-selection scenario missed initial change");
  check(reversedSelection.update(-1, OptionsValueRepeat.REPEAT_INTERVAL, 1, true)==1,
   "new direction on a newly selected row was suppressed");

  var blocked = new OptionsValueRepeat();
  check(blocked.update(1, 0, 0, true)==1, "blocked-menu scenario missed initial change");
  check(blocked.update(1, 1, 0, false)==0, "blocked menu changed an option");
  check(blocked.update(1, 0, 0, true)==1,
   "resuming after a blocked menu did not start with one fresh change");
 }
}
''')

    def test_save_data_state_routes_only_control_holds_through_repeat(self):
        source = (ROOT / "source/SaveDataState.hx").read_text()
        self.assertIn("var amountRepeat:OptionsValueRepeat", source)
        self.assertIn(
            "amountRepeat.update(repeatDirection, elapsed, optionsSelected, repeatAllowed)",
            source,
        )
        self.assertIn("if (!(inOptionsMenu && FlxG.keys.pressed.CONTROL))", source)
        self.assertIn("controls.RIGHT_MENU_H ? 1 : controls.LEFT_MENU_H ? -1 : 0", source)
        self.assertIn("amountRepeat.reset();", source)
        self.assertIn('(field == "offset" || field == "fpsCap") && FlxG.keys.pressed.SHIFT ? 20 : null', source)
        self.assertIn("changeAmount(increase, step)", source)


if __name__ == "__main__":
    unittest.main()
