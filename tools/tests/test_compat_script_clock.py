"""Pin rendering-independent, paired source-script timing."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CompatScriptClockTest(unittest.TestCase):
    def test_gameplay_brackets_native_work_with_same_source_batch(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        update = source[source.index("override public function update(elapsed:Float)"):]
        next_method = update.find("override public function", 20)
        if next_method >= 0:
            update = update[:next_method]
        self.assertIn("compatScriptClock.advance(paused ? 0 : elapsed)", update)
        self.assertIn("NightmareVisionFlxGView.captureSourceFrame(compatScriptClock)", update)
        self.assertIn("sourceBatch.dispatchUpdate(function(index, sourceElapsed)", update)
        self.assertNotIn("callNightmareVision('onUpdate', [elapsed])", update)
        self.assertNotIn("callNightmareVision('onUpdatePost', [elapsed])", update)
        helper = source[source.index("function dispatchNightmareVisionUpdatePost"):source.index("override public function update(elapsed:Float)")]
        self.assertIn("batch.dispatchUpdatePost", helper)
        self.assertIn("NightmareVisionFlxGView.finishSourceBatch", helper)

    def test_fixed_rate_pair_pause_resume_reset_and_uncapped_catchup(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Main {
 static function check(value:Bool, message:String):Void {
  if (!value) throw '[clock-test] ' + message;
 }

 static function countAtRate(hostHz:Int, seconds:Int):Int {
  var clock = new CompatScriptClock();
  var ticks = 0;
  for (_ in 0...(hostHz * seconds))
   ticks += clock.advance(1.0 / hostHz).tickCount;
  return ticks;
 }

 static function main():Void {
  check(CompatScriptClock.DEFAULT_SOURCE_HZ == 60,
   'source cadence is not 60 Hz');
  check(countAtRate(60, 20) == 1200
   && countAtRate(240, 20) == 1200
   && countAtRate(480, 20) == 1200,
   'script tick count depended on host update rate');

  var clock = new CompatScriptClock();
  var half = clock.tickElapsed * 0.5;
  check(clock.advance(half).tickCount == 0, 'half tick fired early');
  clock.pause();
  check(clock.isPaused && clock.advance(5).tickCount == 0,
   'paused wall time advanced script cadence');
  clock.resume();
  check(!clock.isPaused && clock.advance(half).tickCount == 1,
   'resume did not preserve the prior fractional phase');

  // One batch brackets all ordinary chart/native work. Both phases use the
  // exact same tick count, indices, and source elapsed value.
  var batch = clock.advance(clock.tickElapsed * 3);
  var order:Array<String> = [];
  var preDeltas:Array<Float> = [];
  var postDeltas:Array<Float> = [];
  batch.dispatchUpdate(function(index, elapsed) {
   order.push('update' + index);
   preDeltas.push(elapsed);
  });
  order.push('event');
  batch.dispatchUpdatePost(function(index, elapsed) {
   order.push('post' + index);
   postDeltas.push(elapsed);
  });
  check(batch.tickCount == 3
   && order.join(',') == 'update0,update1,update2,event,post0,post1,post2',
   'paired phases changed the host update/event ordering');
  check(preDeltas.length == postDeltas.length
   && preDeltas.length == batch.tickCount,
   'onUpdate and onUpdatePost received different tick counts');
  for (i in 0...preDeltas.length)
   check(preDeltas[i] == clock.tickElapsed
    && postDeltas[i] == preDeltas[i],
    'callback pair did not receive the same fixed source delta');

  var rejectedOrder = false;
  try batch.dispatchUpdatePost(function(_, _) {}) catch (_:Dynamic) rejectedOrder = true;
  check(rejectedOrder, 'batch allowed duplicate onUpdatePost dispatch');

  // No catch-up cap: a hitch's entire elapsed interval becomes due callbacks.
  var catchup = new CompatScriptClock();
  check(catchup.advance(2.5).tickCount == 150,
   'large elapsed interval was capped or lost');

  clock.advance(half);
  clock.reset();
  check(!clock.isPaused && clock.advance(half).tickCount == 0
   && clock.advance(half).tickCount == 1,
   'reset did not clear old phase or restore active state');

  var alternate = new CompatScriptClock(30);
  check(alternate.tickElapsed == 1.0 / 30 && alternate.advance(1).tickCount == 30,
   'generic clock did not honor an alternate source rate');
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="nmv-script-clock-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", scratch,
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
