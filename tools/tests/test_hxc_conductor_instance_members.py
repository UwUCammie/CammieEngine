"""V-Slice Conductor.instance tempo members reach the native Conductor.

Scripts call Conductor.instance.getBeatTimeInMs, getStepTimeInMs and
getTypeLengthAtMs and read bpm, measureLengthMs, currentBeatTime and
currentStepTime. The native Conductor is static and has no instance, so these
went to a null object before.
"""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

DONOR = r'''
class TimedStage extends Stage {
    var endBeat:Float = 0;
    function onSongStart(event) {
        var hit = Conductor.instance.getBeatTimeInMs(8) + Conductor.instance.getStepTimeInMs(4);
        endBeat = Conductor.instance.getTypeLengthAtMs(hit, 'step') + Conductor.instance.getTypeLengthAtMs(hit);
    }
    function onUpdate(event) {
        var t = Conductor.instance.currentBeatTime + Conductor.instance.currentStepTime;
        var m = Conductor.instance.measureLengthMs / Conductor.instance.bpm;
    }
}
'''

# Stands in for source/Conductor.hx, whose Flixel imports the interpreter
# cannot load; same static names and the same tempo maths at one BPM.
CONDUCTOR = '''class Conductor {
  public static var bpm:Float = 100;
  public static var crochet:Float = 600;
  public static var stepCrochet:Float = 150;
  public static var songPosition:Float = 0;
  public static function stepToSeconds(step:Float):Float return step * stepCrochet;
  public static function beatToSeconds(beat:Float):Float return stepToSeconds(beat * 4);
  public static function getCrotchetAtTime(time:Float):Float return crochet;
  public static function getStep(time:Float, noteOffset:Float = 0):Float return (time - noteOffset) / stepCrochet;
  public static function getBeat(time:Float, noteOffset:Float = 0):Float return getStep(time, noteOffset) / 4;
}
'''

MAIN = '''class Main {
  static function fail(value:String):Void throw value;
  static function near(a:Float, b:Float):Bool return Math.abs(a - b) < 0.001;
  static function main() {
    var result = HxcCompat.analyze(%s, "scripts/stages/timed.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("Conductor.instance") >= 0) fail("a Conductor.instance member was left for a null object: " + generated);
    for (call in ["HxcCompatRuntime.conductorGetBeatTimeInMs(8)", "HxcCompatRuntime.conductorGetStepTimeInMs(4)",
        "HxcCompatRuntime.conductorGetTypeLengthAtMs(hit, 'step')", "HxcCompatRuntime.conductorCurrentBeatTime",
        "HxcCompatRuntime.conductorCurrentStepTime", "HxcCompatRuntime.conductorMeasureLengthMs", "HxcCompatRuntime.conductorBpm"])
      if (generated.indexOf(call) < 0) fail("missing " + call + " in " + generated);
    // The stub below is the native Conductor's surface at 100 BPM: a beat is
    // 600 ms and a step 150 ms.
    if (!near(HxcCompatRuntime.conductorGetBeatTimeInMs(8), 4800)) fail("beat 8 at " + HxcCompatRuntime.conductorGetBeatTimeInMs(8));
    if (!near(HxcCompatRuntime.conductorGetStepTimeInMs(4), 600)) fail("step 4 at " + HxcCompatRuntime.conductorGetStepTimeInMs(4));
    if (!near(HxcCompatRuntime.conductorGetTypeLengthAtMs(0), 600)) fail("beat length");
    if (!near(HxcCompatRuntime.conductorGetTypeLengthAtMs(0, "s"), 150)) fail("step length");
    if (!near(HxcCompatRuntime.conductorGetTypeLengthAtMs(0, "measure"), 2400)) fail("measure length");
    if (!near(HxcCompatRuntime.conductorMeasureLengthMs, 2400) || !near(HxcCompatRuntime.conductorBpm, 100)) fail("bpm or measure");
    Conductor.songPosition = 1500;
    if (!near(HxcCompatRuntime.conductorCurrentStepTime, 10) || !near(HxcCompatRuntime.conductorCurrentBeatTime, 2.5))
      fail("song position in steps/beats " + HxcCompatRuntime.conductorCurrentStepTime);
    Sys.println("conductor-ok");
  }
}
'''


class HxcConductorInstanceMembersTest(unittest.TestCase):
    def test_tempo_members_are_lowered_to_the_native_conductor(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps(DONOR), newline=chr(10))
            (Path(folder) / 'Conductor.hx').write_text(CONDUCTOR, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('conductor-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
