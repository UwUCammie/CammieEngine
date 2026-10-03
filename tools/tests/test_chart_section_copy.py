"""The chart editor copies full JSON note rows when duplicating sections."""
from haxe_test_support import HAXE_COMMAND

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class ChartSectionCopyTest(unittest.TestCase):
    def test_timestamp_copy_preserves_optional_columns_and_is_deep_independent(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        source = (ROOT / "source/ChartingState.hx").read_text()
        self.assertIn("ChartNoteRowCopy.withTimestamp(note, strum)", source)

        fixture = r'''class ChartSectionCopyFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var eventParams:Array<Dynamic> = [0.04, 0.08, {curve:"out"}];
  var codenamePayload:Array<Dynamic> = [1, {tag:"keep"}];
  var row:Array<Dynamic> = [1000, 6, 375, 2, false, 0.25, 1.5, true,
   2.5, false, true, "altSuffix",
   {events:[{name:"Camera Zoom", params:eventParams}]},
   {codename:{strumlineIndex:3, character:"Extra", payload:codenamePayload}}];
  var copy = ChartNoteRowCopy.withTimestamp(row, 2500);
  if(copy.length != row.length || copy[0] != 2500)
   fail("timestamp copy changed row shape or time");
  if(copy[1] != 6 || copy[2] != 375 || copy[3] != 2 || copy[4] != false
   || copy[5] != 0.25 || copy[6] != 1.5 || copy[7] != true
   || copy[8] != 2.5 || copy[9] != false || copy[10] != true
   || copy[11] != "altSuffix")
   fail("legacy optional note fields were dropped or changed");
  if(copy[12].events[0].name != "Camera Zoom"
   || copy[12].events[0].params[2].curve != "out"
   || copy[13].codename.strumlineIndex != 3
   || copy[13].codename.payload[1].tag != "keep")
   fail("nested event or Codename metadata was dropped");

  copy[12].events[0].params[2].curve = "mutated";
  copy[13].codename.payload[1].tag = "mutated";
  copy[13].codename.payload.push(4);
  if(row[12].events[0].params[2].curve != "out"
   || row[13].codename.payload[1].tag != "keep"
   || row[13].codename.payload.length != 2)
   fail("editing the copied row mutated the source row's nested metadata");
  if(row[0] != 1000)
   fail("timestamp edit mutated the source row");

  var short = ChartNoteRowCopy.withTimestamp([30, 1, 0], 60);
  if(short.length != 3 || short[0] != 60 || short[1] != 1 || short[2] != 0)
   fail("ordinary three-column note rows changed");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "ChartSectionCopyFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "ChartSectionCopyFixture"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
