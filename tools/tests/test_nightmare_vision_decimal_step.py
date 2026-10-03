"""NMV decimal-step calculation across countdowns, tempo changes and frame rates."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionDecimalStepTest(unittest.TestCase):
    def test_tempo_segments_offset_boundaries_seek_and_frame_rate_callbacks(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function near(actual:Float, expected:Float, message:String, epsilon:Float=0.00001):Void {
  if (Math.isNaN(actual) || Math.abs(actual - expected) > epsilon)
   fail(message + ': expected ' + expected + ', got ' + actual);
 }

 static function main() {
  var map:Array<Dynamic> = [
   {stepTime:8, songTime:1000.0, bpm:60.0},
   {stepTime:10, songTime:1500.0, bpm:240.0}
  ];
  // Initial 120 BPM uses 125 ms per step, including negative count-in.
  near(NightmareVisionDecimalStep.getStep(-500, 120, map), -4, 'negative countdown');
  near(NightmareVisionDecimalStep.getStep(0, 120, map), 0, 'song start');
  near(NightmareVisionDecimalStep.getStep(62.5, 120, map), 0.5, 'fractional initial step');
  near(NightmareVisionDecimalStep.getStep(999.99, 120, map), 7.99992, 'pre-change step');
  // At the exact boundary the new segment applies, as Conductor.getBPMFromSeconds uses >=.
  near(NightmareVisionDecimalStep.getStep(1000, 120, map), 8, 'exact BPM boundary');
  near(NightmareVisionDecimalStep.getStep(1125, 120, map), 8.5, 'fractional step after BPM change');
  near(NightmareVisionDecimalStep.getStep(1500, 120, map), 10, 'second exact BPM boundary');
  near(NightmareVisionDecimalStep.getStep(1562.5, 120, map), 11, 'second segment step duration');

  // NMV selects a BPM segment from raw song time, then subtracts noteOffset
  // inside that segment when it calculates MusicBeatState.curDecStep.
  near(NightmareVisionDecimalStep.getStep(1000, 120, map, 100), 7.6,
   'note offset at boundary uses newly selected BPM');
  near(NightmareVisionDecimalStep.getStep(999.99, 120, map, 100), 7.19992,
   'note offset before boundary uses previous BPM');

  // The source map includes a precomputed stepCrotchet; the fork's map does not.
  var sourceMap:Array<Dynamic> = [
   {stepTime:0, songTime:0.0, bpm:120.0, stepCrotchet:125.0},
   {stepTime:8, songTime:1000.0, bpm:60.0, stepCrotchet:250.0}
  ];
  near(NightmareVisionDecimalStep.getStep(1125, 180, sourceMap), 8.5,
   'source stepCrotchet overrides initial fallback');

  // The helper is stateless: a seek backward recomputes the earlier segment.
  near(NightmareVisionDecimalStep.getStep(1750, 120, map), 14, 'forward seek');
  near(NightmareVisionDecimalStep.getStep(500, 120, map), 4, 'backward seek');

  // Exercise manager scheduling at rates that bracket low and very high FPS.
  // Events around a tempo boundary may share a frame, but every one-shot must
  // fire once, in step order, with at most one frame of decimal-step lateness.
  for (fps in [60, 240, 480]) {
   var fired:Array<String> = [];
   var firedSteps:Map<String, Float> = new Map();
   var manager = new NightmareVisionModManager();
   for (entry in [
    {name:'before', step:7.99},
    {name:'boundary', step:8.0},
    {name:'within-a-frame-a', step:8.1},
    {name:'within-a-frame-b', step:8.2},
    {name:'after', step:10.5}
   ]) {
    var name = entry.name;
    var dueStep = entry.step;
    manager.queueFuncOnce(dueStep, function(event, currentStep):Void {
     fired.push(name);
     firedSteps.set(name, currentStep);
    });
   }
   var frame = 0;
   var time = -500.0;
   while (time <= 1700.0) {
    manager.updateTimeline(NightmareVisionDecimalStep.getStep(time, 120, map));
    frame++;
    time = -500.0 + frame * (1000.0 / fps);
   }
   eq(fired.join(','), 'before,boundary,within-a-frame-a,within-a-frame-b,after',
    'missed, repeated, or reordered callback at ' + fps + ' FPS');
   for (entry in [
    {name:'before', step:7.99}, {name:'boundary', step:8.0},
    {name:'within-a-frame-a', step:8.1}, {name:'within-a-frame-b', step:8.2},
    {name:'after', step:10.5}
   ]) {
    var duration = entry.step < 8 ? 125.0 : (entry.step < 10 ? 250.0 : 62.5);
    var maxLate = (1000.0 / fps) / duration + 0.0001;
    var observed = firedSteps.get(entry.name);
    check(observed >= entry.step && observed - entry.step <= maxLate,
     'callback lateness exceeded one frame at ' + fps + ' FPS for ' + entry.name
      + ': step=' + observed + ', due=' + entry.step + ', maxLate=' + maxLate);
   }
   manager.destroy();
  }
 }

 static function eq(actual:String, expected:String, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/flixel/6,1,2"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_uses_raw_time_for_segment_and_note_offset_for_decimal_step(self):
        source_root = ROOT.parent / "FNF-Example-Mods/misc/nightmare_vision_source_code/source/funkin/backend"
        if not source_root.is_dir():
            self.skipTest("supplied Nightmare Vision Conductor source unavailable")
        conductor = (source_root / "Conductor.hx").read_text()
        beat_state = (source_root / "MusicBeatState.hx").read_text()
        play_state = (ROOT.parent / "FNF-Example-Mods/misc/nightmare_vision_source_code/source/funkin/states/PlayState.hx").read_text()
        self.assertIn("if (time >= change.songTime)", conductor)
        self.assertIn("lastChange.stepTime + (time - lastChange.songTime) / lastChange.stepCrotchet", conductor)
        self.assertIn("(Conductor.songPosition - ClientPrefs.noteOffset) - lastChange.songTime", beat_state)
        self.assertIn("modManager.updateTimeline(curDecStep);", play_state)
        update_start = play_state.index("override public function update(elapsed:Float):Void")
        update_body = play_state[update_start:]
        self.assertLess(update_body.index("modManager.updateTimeline(curDecStep);"),
            update_body.index("while (queueNotes.length > 0"))


if __name__ == "__main__":
    unittest.main()
