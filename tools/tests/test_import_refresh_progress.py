"""Deterministic timing and progress measurements for retained-source refreshes."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var progress = new ImportRefreshProgress(10);
  progress.update({phase:"scan-roots",current:"assets",completed:42,total:0},11);
  var unknown = progress.snapshot(13,2);
  check(unknown.total == 0 && unknown.etaSeconds == -1, "Discovery must not invent an ETA");
  check(unknown.elapsedSeconds == 3 && unknown.activityAgeSeconds == 2, "elapsed/activity timing");
  check(unknown.queueRemaining == 2, "queued imports");
  progress.update({phase:"checking-output",current:"first.png",completed:0,total:100},14);
  progress.update({phase:"checking-output",current:"next.png",completed:10,total:100},16);
  var measured = progress.snapshot(16,1);
  check(measured.etaSeconds == 18, "phase ETA from measured throughput");
  progress.update({phase:"checking-output",current:"next.png",completed:10,total:100},20);
  var unchanged = progress.snapshot(20,1);
  check(unchanged.activityAgeSeconds == 4, "Repeated callbacks must not fake activity");
  check(unchanged.etaSeconds == 54, "a pause must be reflected in ETA");
  progress.update({phase:"publishing-import",current:"next.png",completed:0,total:12},21);
  check(progress.snapshot(21,0).etaSeconds == -1, "new phase discards previous rate");
  progress.update({phase:"publishing-import",current:"done.png",completed:12,total:12},24);
  check(progress.snapshot(24,0).etaSeconds == 0, "completed phase");
  progress.update({phase:"scan-roots",completed:-10,total:"NaN"},25);
  check(progress.completed == 0 && progress.total == 0, "invalid counts normalized");
  progress.update({phase:"checking-output",completed:999,total:3},26);
  check(progress.completed == 3, "completed cannot exceed total");
  progress.update({phase:"checking-output",completed:0,total:3},27);
  check(progress.snapshot(30,0).etaSeconds == -1, "restarted counter resets rate");
  progress.update({phase:"songs",current:"first",completed:0,total:20},31);
  progress.update({phase:"songs",current:"second",completed:2,total:20},33);
  progress.update({phase:"charts",current:"second-hard.json",completed:1,total:3},34);
  check(progress.phase == "songs" && progress.completed == 2 && progress.total == 20,
   "Nested charts keep measurable song-batch progress");
  check(progress.snapshot(34,0).etaSeconds == 27, "nested files retain song-batch throughput");
  progress.update({phase:"chart-serialize-start",current:"second-hard.json",completed:1,total:3},34);
  check(progress.phase == "songs" && progress.total == 20, "chart serialization retains batch counters");
  progress.update({phase:"assets",current:"assets",completed:0,total:2},35);
  progress.update({phase:"assets",current:"a.png",completed:0,total:0},36);
  check(progress.total == 2, "per-file activity keeps the known asset folder total");
  progress.update({phase:"scan-discovery",current:"root",completed:40,total:10000},37);
  check(progress.total == 0 && progress.snapshot(40,0).etaSeconds == -1,
   "a traversal safety limit must not become a work total");
  Sys.println("OK");
 }
}'''


class ImportRefreshProgressTest(unittest.TestCase):
    def test_phase_rates_and_activity_are_measured_without_fabricated_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            (fixture / "Main.hx").write_text(MAIN, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(fixture),
                 "--run", "Main"], cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout)
