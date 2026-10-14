"""Full collections are asked for at quiet moments only, through one module."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class EngineMemoryPolicyTest(unittest.TestCase):
    def test_collects_are_spaced_out_and_tuning_applies_once(self):
        fixture = r'''class EngineMemoryFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var now = 1000.0;
  var collects:Array<Bool> = [];
  EngineMemory.clock = function() return now;
  EngineMemory.collector = function(major:Bool) { collects.push(major); now += 0.035; };
  EngineMemory.reset();

  if (!EngineMemory.collectNow(true, 'loading-handoff', true)) fail("the loading handoff did not collect");
  if (collects.length != 1 || collects[0] != true) fail("expected one full collection");
  if (Math.abs(EngineMemory.lastCollectSeconds - 0.035) > 0.0001) fail("pause time was not measured");
  if (EngineMemory.lastReason != 'loading-handoff') fail("reason was not recorded");

  // Pausing right after loading, or mashing pause, must not stack pauses.
  now += 1;
  if (EngineMemory.collectNow(true, 'pause')) fail("a collection ran moments after the last one");
  now += 1;
  if (EngineMemory.collectNow(true, 'pause')) fail("a second quick pause collected");
  if (collects.length != 1) fail("skipped requests reached the collector");

  // A pause later in the song does collect, once.
  now += EngineMemory.MIN_SECONDS_BETWEEN_COLLECTS;
  if (!EngineMemory.collectNow(true, 'pause')) fail("a pause well into the song did not collect");
  if (collects.length != 2 || EngineMemory.collectCount != 2) fail("collect count is off");

  // The next loading handoff always runs, however recent the last pause was.
  if (!EngineMemory.collectNow(true, 'loading-handoff', true)) fail("forced collect was skipped");

  // The diagnostic probe is a forced, timed collection.
  var report = EngineMemory.probe();
  if (collects.length != 4 || Math.abs(report.seconds - 0.035) > 0.0001) fail("probe did not time a collection");

  // Tuning is opt-in and applied once.
  var tuned:Array<String> = [];
  EngineMemory.tuner = function(mb:Int, percent:Int) tuned.push(mb + ":" + percent);
  EngineMemory.reset();
  if (EngineMemory.applyStartupTuning(["--smoke", "--other=3"])) fail("tuning ran without being asked for");
  if (tuned.length != 0) fail("defaults were changed");
  EngineMemory.reset();
  if (!EngineMemory.applyStartupTuning(["--gc-min-free-mb=256", "--gc-free-percent=150"])) fail("tuning was ignored");
  if (EngineMemory.applyStartupTuning(["--gc-min-free-mb=512"])) fail("tuning was applied twice");
  if (tuned.join(",") != "256:150") fail("wrong tuning values: " + tuned.join(","));
  // The byte count handed to the collector has to fit in 32 bits.
  EngineMemory.reset();
  tuned = [];
  EngineMemory.applyStartupTuning(["--gc-min-free-mb=4096"]);
  var askedMb = Std.parseInt(tuned[0].split(":")[0]);
  if (askedMb <= 0 || askedMb > 2047 || askedMb * 1024 * 1024 <= 0)
   fail("minimum free space would overflow the collector's byte count: " + tuned[0]);
  if (EngineMemory.argumentInt(["--gc-min-free-mb=999999"], "--gc-min-free-mb=", 0, 4096) != 4096) fail("no upper clamp");
  if (EngineMemory.argumentInt(["--gc-min-free-mb=-4"], "--gc-min-free-mb=", 0, 4096) != 0) fail("negative accepted");
  if (EngineMemory.argumentInt(["--gc-min-free-mb=abc"], "--gc-min-free-mb=", 7, 4096) != 7) fail("junk accepted");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "EngineMemoryFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", "EngineMemoryFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def run_fixture(self, name, body):
        fixture = 'class ' + name + ' {\n static function fail(message:String):Void throw message;\n static function main() {\n' + body + '\n  Sys.println("OK");\n }\n}'
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / (name + ".hx")).write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", name],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_song_free_space_is_applied_once_and_restored(self):
        self.run_fixture("EngineSongMemoryFixture", r'''
  var tuned:Array<String> = [];
  var env:Map<String, String> = [];
  EngineMemory.tuner = function(mb:Int, percent:Int) tuned.push(mb + ":" + percent);
  EngineMemory.environment = function(name:String) return env.get(name);
  EngineMemory.reset();
  var songA = {}, songB = {};

  // Plain launch: the song value goes in once and the default comes back.
  if (!EngineMemory.enterSong(songA)) fail("song free space was not applied");
  if (EngineMemory.enterSong(songA)) fail("song free space was applied twice");
  if (tuned.join(",") != EngineMemory.SONG_MIN_FREE_MB + ":0") fail("wrong song value: " + tuned.join(","));
  if (EngineMemory.SONG_MIN_FREE_MB > EngineMemory.MAX_MIN_FREE_MB) fail("song value overflows the collector");
  if (!EngineMemory.leaveSong(songA)) fail("song free space was not restored");
  if (EngineMemory.leaveSong(songA)) fail("restored twice");
  if (tuned.join(",") != EngineMemory.SONG_MIN_FREE_MB + ":0," + EngineMemory.DEFAULT_MIN_FREE_MB + ":0") fail("wrong restore: " + tuned.join(","));

  // A retry builds the next song before the old one is destroyed.
  tuned = [];
  EngineMemory.enterSong(songA);
  if (EngineMemory.enterSong(songB)) fail("a replacement song applied the value again");
  if (EngineMemory.leaveSong(songA)) fail("the old song restored the default under the new one");
  if (tuned.length != 1) fail("handover changed the tuning: " + tuned.join(","));
  if (!EngineMemory.leaveSong(songB)) fail("the replacement song did not restore");
  if (tuned.length != 2) fail("replacement restore missing");

  // An explicit command-line minimum wins and is never overwritten.
  EngineMemory.reset();
  tuned = [];
  EngineMemory.applyStartupTuning(["--gc-min-free-mb=128"]);
  if (EngineMemory.enterSong(songA) || EngineMemory.leaveSong(songA)) fail("song value overrode the command line");
  if (tuned.join(",") != "128:0") fail("command-line tuning changed: " + tuned.join(","));

  // So does the collector's own environment variable.
  EngineMemory.reset();
  tuned = [];
  env.set("HXCPP_MINIMUM_FREE_SPACE", "67108864");
  if (EngineMemory.enterSong(songA) || EngineMemory.leaveSong(songA) || tuned.length != 0) fail("song value overrode the environment");
  env.remove("HXCPP_MINIMUM_FREE_SPACE");

  // The song value itself can be changed or switched off for measurements.
  EngineMemory.reset();
  tuned = [];
  EngineMemory.applyStartupTuning(["--gc-song-min-free-mb=0"]);
  if (EngineMemory.enterSong(songA) || EngineMemory.leaveSong(songA) || tuned.length != 0) fail("song value could not be switched off");
  EngineMemory.reset();
  EngineMemory.applyStartupTuning(["--gc-song-min-free-mb=512"]);
  EngineMemory.enterSong(songA);
  if (tuned.join(",") != "512:0") fail("song override ignored: " + tuned.join(","));
  EngineMemory.reset();
  tuned = [];
  EngineMemory.applyStartupTuning(["--gc-song-min-free-mb=999999"]);
  EngineMemory.enterSong(songA);
  if (tuned.join(",") != EngineMemory.MAX_MIN_FREE_MB + ":0") fail("song override not clamped: " + tuned.join(","));
''')

    def test_probe_reports_large_heap_around_the_collection(self):
        self.run_fixture("EngineLargeMemoryFixture", r'''
  var large = 300.0;
  EngineMemory.collector = function(major:Bool) large = 120.0;
  EngineMemory.largeBytesProvider = function() return large;
  EngineMemory.reset();
  if (EngineMemory.largeBytes() != 300) fail("large bytes not read from the provider");
  var report = EngineMemory.probe();
  if (report.largeBefore != 300 || report.largeAfter != 120) fail("probe large figures: " + report.largeBefore + " -> " + report.largeAfter);
''')

    def test_song_states_enter_and_leave_the_song_policy(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        create = play[play.index("override public function create() {"):]
        self.assertIn("EngineMemory.enterSong(this);", create[:create.index("startTimestamp = consumeStartingPosition();")])
        destroy = play[play.index("override public function destroy() {"):]
        self.assertIn("EngineMemory.leaveSong(this);", destroy[:destroy.index('RuntimeSongExitProbe.mark("destroy-complete");')])
        self.assertEqual(play.count("EngineMemory.enterSong("), 1)
        self.assertEqual(play.count("EngineMemory.leaveSong("), 1)

    def test_collector_is_only_reached_through_the_module_at_quiet_points(self):
        loading = (ROOT / "source/SongLoadingScreen.hx").read_text(encoding="utf-8")
        handoff = loading[loading.index("if (progress.completed == 3) {"):]
        self.assertIn("EngineMemory.collectNow(true, 'loading-handoff', true);", handoff[:400])
        self.assertLess(handoff.index("EngineMemory.collectNow"), handoff.index("complete(4, progress.label)"))
        pause = (ROOT / "source/PauseSubState.hx").read_text(encoding="utf-8")
        constructor = pause[pause.index("public function new("):pause.index("function codenameInitPauseScript()")]
        self.assertIn("EngineMemory.collectNow(true, 'pause');", constructor)
        self.assertEqual(pause.count("EngineMemory.collectNow("), 1)
        main = (ROOT / "source/Main.hx").read_text(encoding="utf-8")
        self.assertEqual(main.count("EngineMemory.applyStartupTuning(Sys.args());"), 1)
        # Nothing else forces or tunes the collector, and no per-frame path asks.
        direct = re.compile(r"Gc\.(run|compact|setMinimumFreeSpace|setTargetFreeSpacePercentage)\(")
        for path in (ROOT / "source").glob("*.hx"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if path.name != "EngineMemory.hx":
                self.assertIsNone(direct.search(text), path.name + " talks to the collector directly")
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertNotIn("EngineMemory.collectNow(", play)
        self.assertNotIn("EngineMemory.probe(", play)


if __name__ == "__main__":
    unittest.main()
