"""A private beat clock (V-Slice `new Conductor()`) follows its own tempo map."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def hx_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


class ConductorTimelineTest(unittest.TestCase):
    def run_main(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(source, newline='\n')
            return subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder),
                                   "-main", "Main", "--interp"],
                                  cwd=ROOT, capture_output=True, text=True, timeout=180)

    def test_timeline_maps_changes_and_fires_signals(self):
        main = r'''class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function near(a:Float, b:Float):Bool return Math.abs(a - b) < 0.0001;
  static function main() {
    var clock = HxcCompatRuntime.newConductor();
    var beats = 0; var steps = 0; var measures = 0;
    var onBeat = function() beats++;
    clock.onBeatHit.add(onBeat);
    clock.onStepHit.add(function() steps++);
    clock.onMeasureHit.add(function() measures++);
    // Stored chart form, as a song's music metadata writes it.
    clock.mapTimeChanges([{t: 0, bpm: 120, n: 4, d: 4, bt: [4, 4, 4, 4]}]);
    check(beats == 0 && clock.currentBeat == 0, "mapping alone must not fire beats");
    check(near(clock.beatLengthMs, 500) && near(clock.stepLengthMs, 125), "120 bpm lengths");
    clock.update(1250);
    check(clock.currentBeat == 2 && clock.currentStep == 10, "beat and step at 1250 ms");
    check(beats == 1 && steps == 1 && measures == 0, "one change fires each signal once");
    clock.update(1300);
    check(beats == 1 && steps == 1, "no change no signal");
    clock.update(2000);
    check(clock.currentMeasure == 1 && measures == 1 && beats == 2, "measure after four beats");
    clock.update(null);
    check(clock.songPosition == 2000, "a missing sound time leaves the clock alone");
    clock.onBeatHit.remove(onBeat);
    clock.update(2600);
    check(beats == 2 && steps == 3, "a removed listener is not called");

    // Long form with a later tempo change.
    clock.mapTimeChanges([{timeStamp: 2000, bpm: 60}, {timeStamp: 0, bpm: 120}]);
    check(near(clock.getTimeInSteps(2000), 16), "first change covers four beats");
    check(near(clock.getTimeInSteps(3000), 20), "60 bpm after the change");
    check(near(clock.getStepTimeInMs(20), 3000), "steps convert back");
    clock.update(3000);
    check(clock.bpm == 60 && clock.currentBeat == 5, "current change follows the position");
    clock.forceBPM(240);
    check(near(clock.getTimeInSteps(1000), 16), "forced tempo ignores the map");
    clock.mapTimeChanges(null);
    clock.forceBPM(null);
    check(clock.bpm == 100, "an empty map uses the default tempo");
    HxcCompatRuntime.conductorMapTimeChanges([{t: 0, bpm: 10}]);
    Sys.println("timeline-ok");
  }
}'''
        result = self.run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("timeline-ok", result.stdout)

    def test_conductor_construction_and_restore_are_lowered(self):
        donor = r'''
class ClockSong extends Song {
    var conduct;
    function onCountdownStart(event) {
        Conductor.instance.mapTimeChanges(PlayState.instance.currentChart.timeChanges);
        conduct = new Conductor();
        conduct.mapTimeChanges([{t: 0, bpm: 130}]);
        conduct.onBeatHit.add(bop);
    }
    function bop() {}
    function onUpdate(event) { if (conduct != null) conduct.update(event.elapsed); }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/clock.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("HxcCompatRuntime.newConductor()") < 0) fail("construction not lowered: " + generated);
    if (generated.indexOf("new Conductor") >= 0) fail("native Conductor still constructed: " + generated);
    if (generated.indexOf("HxcCompatRuntime.conductorMapTimeChanges(") < 0) fail("restore not lowered: " + generated);
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-api" && finding.message.indexOf("Conductor") >= 0)
        fail("conductor use diagnosed: " + finding.message);
    Sys.println("lowering-ok");
  }}
}}'''
        result = self.run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("lowering-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
