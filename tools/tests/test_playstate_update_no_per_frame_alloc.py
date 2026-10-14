"""The gameplay update loop does not allocate for its hit rate, input or misses label."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PlayStateUpdateAllocationTest(unittest.TestCase):
    def test_hit_rate_window_matches_the_date_based_readout(self):
        fixture = r'''class HitRateFixture {
 static function fail(message:String):Void throw message;
 // The readout as it was written with Date objects, kept here as the reference.
 static function legacy(hits:Array<Date>, now:Float):Int {
  var joe = hits.length - 1;
  while (joe >= 0) {
   var mama:Date = hits[joe];
   if (mama != null && mama.getTime() + 1000 < now) hits.remove(mama);
   else joe = 0;
   joe--;
  }
  return hits.length;
 }
 static function main() {
  var dates:Array<Date> = [];
  var times:Array<Float> = [];
  var base = 1700000000000.0;
  var seed = 12345;
  function roll(limit:Int):Int { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed % limit; }
  var now = base;
  for (frame in 0...4000) {
   // Streams, gaps longer than the window and several hits on one frame.
   now += roll(40) == 0 ? 900 + roll(700) : 4 + roll(30);
   for (hit in 0...(roll(5) == 0 ? 1 + roll(3) : 0)) {
    dates.push(Date.fromTime(now));
    times.push(now);
   }
   var expected = legacy(dates, now);
   var actual = HitRateWindow.prune(times, now);
   if (expected != actual) fail("frame " + frame + ": expected " + expected + " hits, got " + actual);
  }
  var hits = [1000.0, 1500.0];
  if (HitRateWindow.prune(hits, 2400) != 2) fail("a hit inside the window was dropped");
  if (HitRateWindow.prune(hits, 2501) != 0) fail("hits older than a second were kept");
  if (HitRateWindow.prune([], 5000) != 0) fail("empty window");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "HitRateFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", "HitRateFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_update_loop_reuses_its_scratch_values(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("var notesHitArray:Array<Float> = [];", play)
        self.assertIn("nps = HitRateWindow.prune(notesHitArray, Sys.time() * 1000);", play)
        self.assertIn("notesHitArray.push(Sys.time() * 1000);", play)
        self.assertNotIn("notesHitArray.push(Date.now())", play)
        self.assertNotIn("Date.now().getTime())\n\t\t\t\tnotesHitArray.remove", play)
        # Source input edges are copied into two arrays kept on the state.
        self.assertNotIn("[for (key in 0...sourceInput.justPressedActions.length)", play)
        self.assertNotIn("[for (key in 0...sourceInput.justReleasedActions.length)", play)
        start = play.index("var pressed = sourceJustPressedScratch;")
        block = play[start:start + 700]
        self.assertIn("pressed.resize(0);", block)
        self.assertIn("released.resize(0);", block)
        self.assertLess(block.index("pressed.push(sourceInput.inputJustPressed(key))"),
                        block.index("released.push(sourceInput.inputJustReleased(key))"))
        # The misses label is only rebuilt when it changes but is still enforced each frame.
        label = play[play.index("if (missesLabel == null || missesLabelCount != misses"):]
        label = label[:500]
        self.assertIn("missesLabel = (comboBreaks ? 'Combo Breaks: ' : 'Misses: ') + misses;", label)
        self.assertIn("if (missesTxt.text != missesLabel)", label)
        self.assertEqual(play.count("(comboBreaks ? 'Combo Breaks: ' : 'Misses: ') + misses"), 1)


if __name__ == "__main__":
    unittest.main()
