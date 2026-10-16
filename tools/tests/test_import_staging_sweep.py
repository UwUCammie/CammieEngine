"""Staging folders left by a refresh that was killed mid-way are removed on the next launch."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]
MANAGER = (ROOT / "source/ImportRefreshManager.hx").read_text(encoding="utf-8")

FIXTURE = r"""import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
class ImportWorkScheduler { public static function cooperate():Bool return true; }
class Main {
 static inline var CACHE_ROOT:String = "import-cache";
 __AGE__
 __CREATED__
 __RELATIVE__
 __DELETE__
 __SWEEP__
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function make(root:String, name:String):String {
  var folder = Path.join([root, "import-cache", "staging", name]);
  FileSystem.createDirectory(folder + "/nested/deeper");
  File.saveContent(folder + "/nested/deeper/file.bin", "converted copy");
  File.saveContent(folder + "/top.json", "{}");
  return folder;
 }
 static function main():Void {
  var root = FileSystem.fullPath(Sys.args()[0]);
  var id = [for (i in 0...64) "a"].join("");
  // now is 1792000000000: the folders are 3605 s, 20 h, 60 s and 3595 s old.
  var now = 1792000000000.0;
  check(stagingCreatedAt(id + "-1792000000000") == 1792000000000.0, "generated name not read");
  check(stagingCreatedAt("notes") < 0 && stagingCreatedAt(id) < 0 && stagingCreatedAt(id + "-12") < 0
   && stagingCreatedAt("short-1792000000000") < 0, "foreign names were treated as generated");
  check(sweepAbandonedStaging(root, now) == 0, "a missing staging folder reported work");
  var old = make(root, id + "-" + "1791996395000");
  var older = make(root, id + "-" + "1791928000000");
  var fresh = make(root, id + "-" + "1791999940000");
  var edge = make(root, id + "-" + "1791996405000");
  var foreign = make(root, "keep-me");
  File.saveContent(root + "/import-cache/staging/loose-file.txt", "not a folder");
  var removed = sweepAbandonedStaging(root, now);
  check(removed == 2, "expected two abandoned folders, removed " + removed);
  check(!FileSystem.exists(old) && !FileSystem.exists(older), "an abandoned staging folder survived");
  check(FileSystem.exists(fresh + "/nested/deeper/file.bin"), "a recent staging folder (maybe in use) was removed");
  check(FileSystem.exists(edge + "/top.json"), "a folder just under the age limit was removed");
  check(FileSystem.exists(foreign + "/top.json") && FileSystem.exists(root + "/import-cache/staging/loose-file.txt"),
   "something that is not a generated staging folder was removed");
  check(sweepAbandonedStaging(root, now) == 0, "a second sweep found more to remove");
  Sys.println("staging sweep passed");
 }
}
"""


class StagingSweepTest(unittest.TestCase):
    def test_only_old_generated_staging_folders_are_removed(self):
        age = re.search(r"static inline var ABANDONED_STAGING_SECONDS:Float = [0-9.]+;", MANAGER)
        self.assertIsNotNone(age)
        fixture = (FIXTURE
                   .replace("__AGE__", age.group())
                   .replace("__CREATED__", extract_method(MANAGER, "static function stagingCreatedAt("))
                   .replace("__RELATIVE__", extract_method(MANAGER, "static function relativeTo("))
                   .replace("__DELETE__", extract_method(MANAGER, "static function deleteStage("))
                   .replace("__SWEEP__", extract_method(MANAGER, "static function sweepAbandonedStaging(")))
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            install = work / "install"
            install.mkdir()
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main", str(install)],
                                    cwd=work, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("staging sweep passed", result.stdout)

    def test_inspection_sweeps_before_it_reads_receipts(self):
        thread = extract_method(MANAGER, "static function ensureQueueInspection(")
        self.assertIn("sweepAbandonedStaging(install, Date.now().getTime());", thread)
        self.assertLess(thread.index("sweepAbandonedStaging("), thread.index("loadQueue(install)"))
        # The sweep is disposable cleanup: it records a failure and never blocks inspection.
        sweep = extract_method(MANAGER, "static function sweepAbandonedStaging(")
        self.assertIn("[import-refresh-cleanup-error]", sweep)


if __name__ == "__main__":
    unittest.main()
