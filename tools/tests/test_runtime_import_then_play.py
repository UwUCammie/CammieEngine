"""Focused contract tests for same-process import-to-chart smoke runs."""

from __future__ import annotations
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
HAXE = ROOT / ".tools" / "haxe" / "haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class RuntimeImportThenPlayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.import_harness = (SOURCE / "RuntimeImportSmokeHarness.hx").read_text()
        cls.import_state = (SOURCE / "RuntimeImportSmokeState.hx").read_text()
        cls.play_state = (SOURCE / "RuntimeSmokeState.hx").read_text()
        cls.freeplay_state = (SOURCE / "RuntimeSmokeFreeplayState.hx").read_text()
        cls.workflow = (SOURCE / "ImportWorkflow.hx").read_text()

    def test_opt_in_import_request_switches_after_main_thread_commit(self):
        self.assertIn("playAfterImport:Bool", self.import_harness)
        self.assertIn("case '--smoke-import-play-after-complete'", self.import_harness)
        self.assertIn("--smoke-import-play-after-complete cannot be combined with --smoke-import-scan-only",
                      self.import_state)
        self.assertIn("play-after-import requires --smoke-song and --smoke-chart", self.import_state)

        complete = self.import_state.index("if (RuntimeImportSmokeHarness.finish(result, error))")
        direct_switch = self.import_state.index("FlxG.switchState(new RuntimeSmokeState());", complete)
        freeplay_switch = self.import_state.index("FlxG.switchState(new RuntimeSmokeFreeplayState());", complete)
        self.assertLess(complete, direct_switch)
        self.assertLess(complete, freeplay_switch)
        self.assertIn("play-after-import Freeplay requires --smoke-freeplay-select", self.import_state)

        import_job = self.workflow[self.workflow.index("class ImportImportJob {"):]
        poll = extract_method(import_job, "public function poll():ImportWorkflowProgress {")
        handoff = poll.index("ImportRefreshManager.completeInitialImportHandoff(importedNames);")
        returned_snapshot = poll.index("runtimeCommitted: runtimeCommitted", handoff)
        self.assertLess(handoff, returned_snapshot)
        update = extract_method(self.import_state, "override public function update(elapsed:Float):Void")
        wait = update.index("waitForSuccessfulImportHandoff(result, error, snapshot.runtimeCommitted)")
        self.assertLess(update.index("if (error != null || result == null)"), wait)
        self.assertIn("RuntimeImportSmokeHarness.fail('timeout', 'import cancellation completed')", update)
        manager = (SOURCE / "ImportRefreshManager.hx").read_text()
        self.assertIn('"RuntimeImportSmokeState"', manager)

    def test_followup_play_reuses_services_initialized_before_import(self):
        consume = "RuntimeImportSmokeHarness.consumePreparedRuntimeForPlay()"
        self.assertIn(consume, self.play_state)
        self.assertLess(self.play_state.index(consume), self.play_state.index("PluginManager.init()"))
        self.assertIn(consume, self.freeplay_state)
        self.assertLess(self.freeplay_state.index(consume), self.freeplay_state.index("DifficultyManager.init()"))
        self.assertIn("preparedRuntimeForPlay = true;", self.import_harness)
        self.assertIn("public static function consumePreparedRuntimeForPlay():Bool", self.import_harness)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_play_waits_for_actual_deferred_import_handoff(self):
        """The real poll method reports worker completion separately from handoff."""
        import_job = self.workflow[self.workflow.index("class ImportImportJob {"):]
        poll = extract_method(import_job, "public function poll():ImportWorkflowProgress {")
        wait_for_handoff = extract_method(
            self.import_state,
            "static function waitForSuccessfulImportHandoff(result:Dynamic, error:Dynamic, runtimeCommitted:Bool):Bool"
        )
        fixture = r'''import sys.thread.Mutex;
typedef ImportWorkflowProgress = Dynamic;
class ImportScanJob {
  public static function writeReport(scan:Dynamic, summary:String):Void {}
}
class ModuleFunctions {
  public static function importBatchSummary(result:Dynamic, ?includeFailures:Bool = false):String return '';
}
class ImportRefreshManager {
  public static var handoffCalls:Int = 0;
  public static function completeInitialImportHandoff(names:Array<String>):Bool {
    handoffCalls++;
    return handoffCalls >= 2;
  }
}
class Main {
  var importType:String = 'Auto';
  var done:Bool = true;
  var result:Dynamic = {importedSongs: ['fixture-song']};
  var error:String = null;
  var phase:String = 'complete';
  var current:String = '';
  var completed:Int = 1;
  var total:Int = 1;
  var copied:Int = 0;
  var skipped:Int = 0;
  var failed:Int = 0;
  var stateMutex:Mutex = new Mutex();
  var runtimeCommitted:Bool = false;
  var reportWritten:Bool = false;
  var scan:Dynamic = {};
  public function new() {}
''' + poll + "\n" + wait_for_handoff + r'''
  static function main():Void {
    var job = new Main();
    var deferred = job.poll();
    if (!deferred.complete || deferred.runtimeCommitted)
      throw 'worker completion must remain distinct from deferred handoff';
    if (!waitForSuccessfulImportHandoff(deferred.result, deferred.error, deferred.runtimeCommitted))
      throw 'play should wait while handoff is deferred';
    var committed = job.poll();
    if (!committed.complete || !committed.runtimeCommitted)
      throw 'poll did not report successful retry';
    if (waitForSuccessfulImportHandoff(committed.result, committed.error, committed.runtimeCommitted))
      throw 'play should proceed after the handoff';
    if (waitForSuccessfulImportHandoff(null, 'worker error', false))
      throw 'worker errors must not wait for an unavailable handoff';
    if (ImportRefreshManager.handoffCalls != 2)
      throw 'handoff retry count';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--interp", "-main", "Main"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_import_success_returns_to_caller_without_ending_same_process(self):
        finish = extract_method(self.import_harness,
                                "public static function finish(result:Dynamic, error:Dynamic):Bool")
        consume = extract_method(self.import_harness,
                                 "public static function consumePreparedRuntimeForPlay():Bool")
        fixture = r'''class Main {
  static var finished = false;
  static var preparedRuntimeForPlay = false;
  static var request:Dynamic = {playAfterImport: true};
  static var events:Array<String> = [];
  static function enabled():Bool return true;
  static function config():Dynamic return request;
  static function emit(name:String, payload:Dynamic):Void events.push(name);
  static function fieldInt(value:Dynamic, key:String):Int {
    var result:Dynamic = Reflect.field(value, key);
    return result == null ? 0 : Std.int(result);
  }
  static function arrayLength(value:Dynamic):Int {
    return value == null ? 0 : (cast value:Array<Dynamic>).length;
  }
  static function boundedErrors(value:Dynamic):Array<String> return [];
  static function fail(kind:String, detail:String):Void throw kind + ':' + detail;
''' + finish + "\n" + consume + r'''
  static function main():Void {
    var result:Dynamic = {
      found: 1, imported: 1, skipped: 0, failed: 0,
      copiedAssets: 4, skippedAssets: 0, missingDependencies: 0, errors: []
    };
    if (!finish(result, null)) throw 'import did not continue';
    if (!finished || events.length != 1 || events[0] != 'import_complete')
      throw 'import completion marker/state';
    if (!consumePreparedRuntimeForPlay() || consumePreparedRuntimeForPlay())
      throw 'prepared setup was not consumed exactly once';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "Main.hx"
            path.write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--interp", "-main", "Main"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
