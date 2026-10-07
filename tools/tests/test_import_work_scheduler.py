"""Exercise the shared foreground/import-work gate with real Haxe threads."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"

MAIN = r'''import sys.thread.Lock;
import sys.thread.Mutex;
import sys.thread.Thread;
import sys.io.File;
import sys.FileSystem;

class ImportWorkSchedulerFixture {
 static function require(value:Bool, message:String):Void {
  if (!value) throw message;
 }

 static function main():Void {
  ImportWorkScheduler.bindForegroundThread();

  var first = ImportWorkScheduler.beginGameplay();
  var second = ImportWorkScheduler.beginGameplay();
  require(first > 0 && second > 0 && first != second, "gameplay leases must be distinct");
  require(ImportWorkScheduler.gameplayActive(), "gameplay lease should activate the gate");

  // The foreground must remain able to process state changes and release these leases.
  var foregroundStart = Sys.time();
  ImportWorkScheduler.cooperate();
  require(Sys.time() - foregroundStart < 0.05, "foreground cooperate must never wait");
  require(!ImportWorkScheduler.backgroundWorkPaused(), "foreground must never report a worker wait");
  require(ImportWorkScheduler.beginUninterruptedPublication() == 0,
   "foreground publication acquisition must never wait");

  ImportWorkScheduler.endGameplay(first);
  ImportWorkScheduler.endGameplay(first);
  require(ImportWorkScheduler.gameplayActive(), "overlapping lease must keep the gate active");
  ImportWorkScheduler.endGameplay(second);
  require(!ImportWorkScheduler.gameplayActive(), "final lease release should clear the gate");

  // ETA time excludes only the interval when background work is actually paused.
  var workStart = ImportWorkScheduler.workStamp();
  var clockLease = ImportWorkScheduler.beginGameplay();
  Sys.sleep(0.08);
  var pausedWorkTime = ImportWorkScheduler.workStamp();
  require(pausedWorkTime - workStart < 0.04, "paused gameplay time should not advance work time");
  ImportWorkScheduler.endGameplay(clockLease);
  Sys.sleep(0.04);
  require(ImportWorkScheduler.workStamp() - pausedWorkTime >= 0.02,
   "work time should resume after the last gameplay lease ends");

  // A worker blocks at a checkpoint until the last gameplay lease exits.
  var pauseLease = ImportWorkScheduler.beginGameplay();
  var workerStarted = new Lock();
  var workerFinished = new Lock();
  Thread.create(function() {
   workerStarted.release();
   ImportWorkScheduler.cooperate();
   workerFinished.release();
  });
  require(workerStarted.wait(2), "worker did not start");
  Sys.sleep(0.08);
  require(!workerFinished.wait(0.01), "background worker should pause during gameplay");
  ImportWorkScheduler.endGameplay(pauseLease);
  require(workerFinished.wait(1), "background worker did not resume after gameplay");

  // Cooperative waits and publication acquisition can observe cancellation.
  var cancelLease = ImportWorkScheduler.beginGameplay();
  var cancellationMutex = new Mutex();
  var cancelRequested = false;
  var cancelWorkerStarted = new Lock();
  var cooperativeCancelDone = new Lock();
  var publicationCancelDone = new Lock();
  var cooperativeResult = true;
  var publicationResult = 0;
  Thread.create(function() {
   cancelWorkerStarted.release();
   cooperativeResult = ImportWorkScheduler.cooperate(function() {
    cancellationMutex.acquire();
    var value = cancelRequested;
    cancellationMutex.release();
    return value;
   });
   cooperativeCancelDone.release();
   publicationResult = ImportWorkScheduler.beginUninterruptedPublication(function() {
    cancellationMutex.acquire();
    var value = cancelRequested;
    cancellationMutex.release();
    return value;
   });
   publicationCancelDone.release();
  });
  require(cancelWorkerStarted.wait(2), "cancellation worker did not start");
  Sys.sleep(0.08);
  require(!cooperativeCancelDone.wait(0.01), "cooperate should remain paused before cancellation");
  cancellationMutex.acquire();
  cancelRequested = true;
  cancellationMutex.release();
  require(cooperativeCancelDone.wait(1), "cooperate did not wake for cancellation");
  require(!cooperativeResult, "cooperate should report cancellation");
  require(publicationCancelDone.wait(1), "publication gate did not wake for cancellation");
  require(publicationResult == -1, "cancelled publication should not acquire the gate");
  ImportWorkScheduler.endGameplay(cancelLease);

  // Cancellation must also win when the publication gate is already idle.
  var idleCancelStarted = new Lock();
  var idleCancelDone = new Lock();
  var idlePublicationResult = 0;
  Thread.create(function() {
   idleCancelStarted.release();
   idlePublicationResult = ImportWorkScheduler.beginUninterruptedPublication(function() return true);
   idleCancelDone.release();
  });
  require(idleCancelStarted.wait(2), "idle publication cancellation worker did not start");
  require(idleCancelDone.wait(1), "idle publication cancellation did not return promptly");
  require(idlePublicationResult == -1, "already-cancelled idle publication must not acquire the gate");
  require(!ImportWorkScheduler.gameplayActive(), "idle cancellation must leave gameplay state unchanged");

  // File hashing uses the same cancellation-aware safe point for long reads.
  var hashPath = Sys.getCwd() + "/tmp/import-work-scheduler-hash.tmp";
  File.saveContent(hashPath, "hash cancellation fixture");
  var hashLease = ImportWorkScheduler.beginGameplay();
  var hashStarted = new Lock();
  var hashDone = new Lock();
  var hashCancelMutex = new Mutex();
  var hashCancelRequested = false;
  var hashCancelled = false;
  Thread.create(function() {
   hashStarted.release();
   try {
    ImportSourceSnapshot.sha256File(hashPath, 4096, function() {
     hashCancelMutex.acquire();
     var value = hashCancelRequested;
     hashCancelMutex.release();
     return value;
    });
   } catch (error:Dynamic) {
    hashCancelled = Std.isOfType(error, ImportWorkCancelled);
   }
   hashDone.release();
  });
  require(hashStarted.wait(2), "hash worker did not start");
  Sys.sleep(0.08);
  require(!hashDone.wait(0.01), "hash should wait while gameplay is active");
  hashCancelMutex.acquire();
  hashCancelRequested = true;
  hashCancelMutex.release();
  require(hashDone.wait(1), "hash did not wake for cancellation");
  require(hashCancelled, "cancelled hash should report the internal cancellation signal");
  ImportWorkScheduler.endGameplay(hashLease);
  FileSystem.deleteFile(hashPath);

  // Only the publication owner may continue while a new gameplay lease keeps
  // unrelated workers paused.
  var waitingLease = ImportWorkScheduler.beginGameplay();
  var waiting = new Lock();
  var publicationEntered = new Lock();
  var publicationContinued = new Lock();
  var publicationReleased = new Lock();
  var allowOwnerContinue = new Lock();
  var allowPublicationRelease = new Lock();
  var ownerPauseStateReady = new Lock();
  var ownerPaused = true;
  Thread.create(function() {
   waiting.release();
   var token = ImportWorkScheduler.beginUninterruptedPublication();
   publicationEntered.release();
   allowOwnerContinue.wait();
   ownerPaused = ImportWorkScheduler.backgroundWorkPaused();
   ownerPauseStateReady.release();
   ImportWorkScheduler.cooperate();
   publicationContinued.release();
   allowPublicationRelease.wait();
   ImportWorkScheduler.endUninterruptedPublication(token);
   publicationReleased.release();
  });
  require(waiting.wait(2), "publication worker did not start");
  Sys.sleep(0.08);
  require(!publicationEntered.wait(0.01), "publication must wait for active gameplay");
  ImportWorkScheduler.endGameplay(waitingLease);
  require(publicationEntered.wait(1), "publication did not resume after gameplay");
  var newlyStartedLease = ImportWorkScheduler.beginGameplay();
  allowOwnerContinue.release();
  require(ownerPauseStateReady.wait(1), "publication owner did not inspect its gate state");
  require(!ownerPaused, "publication owner should be exempt from the gameplay gate");
  require(publicationContinued.wait(0.2), "active publication should finish without pausing");
  var unrelatedStarted = new Lock();
  var unrelatedFinished = new Lock();
  Thread.create(function() {
   unrelatedStarted.release();
   ImportWorkScheduler.cooperate();
   unrelatedFinished.release();
  });
  require(unrelatedStarted.wait(2), "unrelated worker did not start");
  Sys.sleep(0.08);
  require(!unrelatedFinished.wait(0.01), "unrelated worker must remain paused during publication");
  allowPublicationRelease.release();
  require(publicationReleased.wait(1), "publication lease was not released");
  Sys.sleep(0.08);
  require(!unrelatedFinished.wait(0.01), "unrelated worker must remain paused after publication until gameplay ends");
  ImportWorkScheduler.endGameplay(newlyStartedLease);
  require(unrelatedFinished.wait(1), "unrelated worker did not resume after gameplay");
  require(!ImportWorkScheduler.gameplayActive(), "all gameplay leases should be released");

  Sys.println("scheduler-ok");
 }
}'''


class ImportWorkSchedulerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE_COMMAND:
            raise unittest.SkipTest("portable Haxe interpreter is unavailable")

    def test_foreground_leases_worker_pause_and_publication_gate(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        temp_root = (str(TEST_TMP) if os.environ.get("CAMMIE_TEST_TMP")
                     else (os.environ.get("TEMP") if os.name == "nt" else str(TEST_TMP)))
        with tempfile.TemporaryDirectory(dir=temp_root) as temporary:
            scratch = Path(temporary)
            (scratch / "ImportWorkSchedulerFixture.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "-cp", str(SOURCE), "--run", "ImportWorkSchedulerFixture"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("scheduler-ok", result.stdout)

    def test_native_state_probe_verification_avoids_foreground_child_pool(self):
        source = (ROOT / "source/RuntimeNvStateProbe.hx").read_text(encoding="utf-8")
        start = source.index("static function verifyRetainedCandidate(")
        opening = source.index("{", start)
        depth = 1
        end = opening + 1
        while depth:
            if source[end] == "{":
                depth += 1
            elif source[end] == "}":
                depth -= 1
            end += 1
        method = source[start:end]
        self.assertIn(
            "ImportSourceSnapshot.verify(snapshotRoot, snapshotId, null, null, 1);",
            method,
            "the opt-in probe runs on the game thread and must not wait for paused child workers",
        )


if __name__ == "__main__":
    unittest.main()
