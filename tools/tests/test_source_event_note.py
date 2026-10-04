"""Exercise the live Psych view over native source event rows."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''package;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;

 static function main():Void {
  var row:Dynamic = {time:100.0, name:"Camera Flash", v1:"#FF0000", v2:"0.5", v3:"keep"};
  var view = new SourceEventNote(row, 25.0);
  var held = view;
  check(row.time == 125.0 && view.strumTime == 125.0,
   "the constructor should apply the note offset once to the native time");
  for (_ in 0...4)
   check(held.strumTime == 125.0, "reading the view must not add the offset again");

  held.event = "Changed Event";
  held.value1 = "blue";
  row.v2 = "1.25";
  check(row.name == "Changed Event" && row.v1 == "blue" && held.value2 == "1.25",
   "view writes and native writes must stay visible through the same row");
  held.strumTime = 180.0;
  check(row.time == 180.0 && view.strumTime == 180.0,
   "strumTime writes should target the native event time");
  row.name = "Native Rename";
  check(held.event == "Native Rename" && row.v3 == "keep",
   "retained views must observe later native changes without changing extension fields");

  var unshifted:Dynamic = {time:42.0, name:"Unshifted", v1:"a", v2:"b"};
  var noOffset = new SourceEventNote(unshifted);
  check(noOffset.strumTime == 42.0 && unshifted.time == 42.0,
   "the default offset must preserve native time");

  var nullableRow:Dynamic = {time:64.0, name:"Nullable Event", v1:null};
  var nullableView = new SourceEventNote(nullableRow);
  check(nullableView.value1 == null && nullableView.value2 == null,
   "explicit-null and missing source values should remain null in the live view");
  nullableRow.v1 = "filled natively";
  check(nullableView.value1 == "filled natively",
   "the live nullable view should continue to observe native mutations");
  nullableView.value2 = "filled through view";
  check(nullableRow.v2 == "filled through view",
   "setting an initially missing value should write through to the native row");
 }
}
'''


class SourceEventNoteTest(unittest.TestCase):
    def test_live_row_mapping_and_one_time_offset(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
