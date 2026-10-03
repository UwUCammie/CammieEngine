"""Behavior tests for the bounded Freeplay row window."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class FreeplayListWindowTest(unittest.TestCase):
    def test_large_and_filtered_windows_keep_original_registry_indexes(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''class FreeplayListWindowFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var all = FreeplayListWindow.visibleIndices(1300, function(_index) return true);
  var center = FreeplayListWindow.window(all, 650, 12);
  if(center.length != 25 || center[0] != 638 || center[12] != 650 || center[24] != 662)
   fail("1300-song center window was not bounded around the selected registry index");
  var first = FreeplayListWindow.window(all, 0, 12);
  if(first.length != 13 || first[0] != 0 || first[12] != 12)
   fail("first-song window did not clamp at the list boundary");
  var last = FreeplayListWindow.window(all, 1299, 12);
  if(last.length != 13 || last[0] != 1287 || last[12] != 1299)
   fail("last-song window did not clamp at the list boundary");

  var filtered = FreeplayListWindow.visibleIndices(1300, function(index) return index % 100 == 3);
  var filteredWindow = FreeplayListWindow.window(filtered, 503, 1);
  if(filteredWindow.length != 3 || filteredWindow[0] != 403
   || filteredWindow[1] != 503 || filteredWindow[2] != 603)
   fail("filtered rows lost their original song indexes or visible order");
  if(FreeplayListWindow.window(filtered, 504, 12).length != 0)
   fail("a selection hidden by the filter produced live rows");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "FreeplayListWindowFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "FreeplayListWindowFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_freeplay_rows_are_built_from_the_bounded_window(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        self.assertIn("FreeplayListWindow.window(visible, curSelected, ROW_WINDOW_RADIUS)", source)
        self.assertIn("songRows:Array<Alphabet>", source)
        self.assertIn("icon.sprTracker = songRows[i]", source)
        self.assertIn("rowSongIndices", source)


if __name__ == "__main__":
    unittest.main()
