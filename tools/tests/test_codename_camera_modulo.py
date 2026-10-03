"""Exercise Codename camera cadence against synthetic conductor data."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'


class CodenameCameraModuloTest(unittest.TestCase):
    def test_event_config_grid_and_conductor_timeline(self):
        fixture = r'''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function near(actual:Float, expected:Float, message:String):Void {
  if (Math.abs(actual - expected) > 0.00001) throw message + ": " + actual + " != " + expected;
 }
 static function main():Void {
  var ordinary = CodenameCameraModulo.songDefaults(
   {bpm:120, beatsPerMeasure:4, stepsPerBeat:4}, []);
  check(ordinary.interval == 4 && ordinary.strength == 1
   && ordinary.every == "BEAT" && ordinary.offset == 0, "ordinary 4/4 defaults");
  var nonstandard = CodenameCameraModulo.songDefaults(
   {bpm:120, beatsPerMeasure:3, stepsPerBeat:4}, []);
  check(nonstandard.interval == 1 && nonstandard.every == "MEASURE",
   "non-4/4 measure defaults");
  var signatureEvent = {name:"Time Signature Change", time:500,
   params:([4, 8, false]:Array<Dynamic>)};
  check(CodenameCameraModulo.songDefaults(
   {bpm:120, beatsPerMeasure:4, stepsPerBeat:4}, [signatureEvent]).every == "MEASURE",
   "signature event defaults");

  var config = CodenameCameraModulo.defaults();
  config = CodenameCameraModulo.apply(config, [2, 1.75, "sTeP", -0.25]);
  check(config.interval == 2 && config.strength == 1.75
   && config.every == "STEP" && config.offset == -0.25, "parameter slots");
  CodenameCameraModulo.apply(config, [null, null, null, null]);
  check(config.interval == 2 && config.strength == 1.75
   && config.every == "STEP" && config.offset == -0.25, "nullable slots preserve state");
  CodenameCameraModulo.apply(config, [1, 1, "unknown", 0]);
  check(config.every == "BEAT", "unknown axis falls back to BEAT");
  check(CodenameCameraModulo.axis(config, 12, 3, 1) == 3, "axis selection");

  near(CodenameCameraModulo.bucket(0, 2, 0.5), -2, "negative initial bucket");
  near(CodenameCameraModulo.bucket(0.499, 2, 0.5), -2, "before offset boundary");
  near(CodenameCameraModulo.bucket(0.5, 2, 0.5), 0, "at offset boundary");
  near(CodenameCameraModulo.bucket(2.499, 2, 0.5), 0, "before next boundary");
  near(CodenameCameraModulo.bucket(2.5, 2, 0.5), 2, "next interval boundary");
  near(CodenameCameraModulo.bucket(3.25, 0, 0.5), 2.75, "nonpositive interval");

  var bpmAndMeter = CodenameCameraModulo.buildTimeline(
   {bpm:120, beatsPerMeasure:4, stepsPerBeat:4}, [
    {name:"BPM Change", time:1000, params:([60]:Array<Dynamic>)},
    {name:"Time Signature Change", time:2500, params:([3, 4, false]:Array<Dynamic>)}
   ]);
  var beforeTempo = CodenameCameraModulo.positionAt(bpmAndMeter, 1000);
  near(beforeTempo.step, 8, "step continuity at BPM change");
  near(beforeTempo.beat, 2, "beat continuity at BPM change");
  near(beforeTempo.measure, 0.5, "measure continuity at BPM change");
  var afterTempo = CodenameCameraModulo.positionAt(bpmAndMeter, 2000);
  near(afterTempo.beat, 3, "new BPM advances beats");
  var afterSignature = CodenameCameraModulo.positionAt(bpmAndMeter, 3000);
  near(afterSignature.step, 16, "step continuity at signature change");
  near(afterSignature.beat, 4.5, "signature retains cumulative beats");
  near(afterSignature.measure, 1 + 1.0 / 6.0,
   "new three-beat measure uses cumulative signature position");

  var eighthNoteMeter = CodenameCameraModulo.buildTimeline(
   {bpm:120, beatsPerMeasure:4, stepsPerBeat:4}, [
    {name:"Time Signature Change", time:1000, params:([6, 8, false]:Array<Dynamic>)}
   ]);
  var afterEighth = CodenameCameraModulo.positionAt(eighthNoteMeter, 1125);
  near(afterEighth.step, 9, "eighth-note signature step axis");
  near(afterEighth.beat, 2.5, "eighth-note denominator beat axis");
  near(afterEighth.measure, 1 + 1.0 / 12.0,
   "six-eight signature measure axis");

  var continuous = CodenameCameraModulo.buildTimeline(
   {bpm:120, beatsPerMeasure:4, stepsPerBeat:4}, [
    {name:"Continuous BPM Change", time:0, params:([60, 4]:Array<Dynamic>)}
   ]);
  var rampEnd = continuous[1].endSongTime;
  near(CodenameCameraModulo.positionAt(continuous, rampEnd).step, 4,
   "continuous BPM reaches authored step duration");
  near(CodenameCameraModulo.positionAt(continuous, rampEnd + 250).step, 5,
   "continuous BPM settles to target tempo");
  check(CodenameCameraModulo.positionAt(continuous, rampEnd + 250).bpm == 60,
   "continuous BPM target");
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
            run = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                  '--run', 'Main'], cwd=ROOT, capture_output=True, text=True,
                                 timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
