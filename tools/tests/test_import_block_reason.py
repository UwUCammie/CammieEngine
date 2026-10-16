"""A new import that cannot start says why, and the coordinator reports its own state."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]
MANAGER = (ROOT / "source/ImportRefreshManager.hx").read_text(encoding="utf-8")


class ImportBlockReasonTest(unittest.TestCase):
    def test_each_cause_has_its_own_sentence_and_clear_means_empty(self):
        reason = extract_method(MANAGER, "static function importBlockReasonLocked(")
        fixture = """class Main {
 static var removalToken:String = '';
 static var inspectionPending:Bool = false;
 static var inspectionRunning:Bool = false;
 static var active:Bool = false;
 static var queue:Array<Dynamic> = [];
 static var unresolvedRecovery:Bool = false;
 static var leased:Bool = false;
 static function runtimeOwnersBusyLocked(roots:Array<String>):Bool return leased;
 __REASON__
 static function reset():Void {
  removalToken = ''; inspectionPending = false; inspectionRunning = false; active = false;
  queue = []; unresolvedRecovery = false; leased = false;
 }
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  check(importBlockReasonLocked([]) == '', 'an idle coordinator blocked an import');
  var seen:Map<String, String> = new Map();
  function expect(label:String, setup:Void->Void, needle:String):Void {
   reset(); setup();
   var text = importBlockReasonLocked(['assets/imported_mods/x']);
   check(text != '' && text.indexOf(needle) >= 0, label + ' gave: ' + text);
   check(text.indexOf('Another import refresh is already running') < 0 || needle == 'Another import refresh', label + ' used the generic sentence');
   for (other in seen.keys()) check(other == needle || seen.get(other) != text, label + ' repeated the sentence of ' + other);
   seen.set(needle, text);
  }
  expect('removal', function() removalToken = 'removal-1', 'removal');
  expect('loaded song', function() leased = true, 'song');
  expect('inspection pending', function() inspectionPending = true, 'still being checked');
  expect('inspection running', function() inspectionRunning = true, 'still being checked');
  expect('refresh active', function() active = true, 'Another import refresh');
  expect('queued refresh', function() queue = [{}], 'Another import refresh');
  expect('unresolved recovery', function() unresolvedRecovery = true, 'interrupted');
  // A removal still running outranks the saved-import check it also raises.
  reset(); removalToken = 'removal-1'; inspectionPending = true;
  check(importBlockReasonLocked([]).indexOf('removal') >= 0, 'the removal reason was hidden by the generic check');
  reset();
  check(importBlockReasonLocked([]) == '', 'reset left a block behind');
 }
}
""".replace("__REASON__", reason)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_start_uses_the_reason_and_the_harness_reports_the_state(self):
        scoped = extract_method(MANAGER, "static function importOnceScoped(")
        self.assertIn("importBlockReasonLocked(importRoots)", scoped)
        self.assertIn("throw blockedBy;", scoped)
        self.assertNotIn('throw "Another import refresh is already running.";', scoped)
        state = extract_method(MANAGER, "static function debugStateLocked(")
        for field in ("removal=", "unresolved=", "pending=", "running=", "active=", "queue="):
            self.assertIn(field, state)
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text(encoding="utf-8")
        self.assertIn("coordinator:ImportRefreshManager.debugState()", harness)

    def test_import_smoke_can_remove_a_package_first_through_the_library_flow(self):
        state = (ROOT / "source/RuntimeImportSmokeState.hx").read_text(encoding="utf-8")
        harness = (ROOT / "source/RuntimeImportSmokeHarness.hx").read_text(encoding="utf-8")
        self.assertIn("--smoke-import-remove-owner", state)
        step = extract_method(state, "function stepRemoval(")
        for call in ("ImportRemovalManager.beginPreview(removalOwner)", "ImportRemovalManager.confirm()"):
            self.assertIn(call, step)
        # The scan only starts once the removal has published, never in parallel with it.
        self.assertEqual(state.count("ImportWorkflow.beginScan("), 2)
        self.assertLess(step.index("ImportRemovalManager.confirm()"), step.index("ImportWorkflow.beginScan("))
        self.assertIn("public static function argumentValue(", harness)


if __name__ == "__main__":
    unittest.main()
