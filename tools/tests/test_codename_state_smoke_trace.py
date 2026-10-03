"""Opt-in Codename state smoke breadcrumbs remain scoped and inspectable."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class CodenameStateSmokeTraceTest(unittest.TestCase):
    def test_trace_helper_is_opt_in_and_sanitizes_scope_fields(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            scratch_path = Path(scratch)
            shutil.copy2(ROOT / "source" / "CodenameStateSmokeTrace.hx", scratch_path)
            (scratch_path / "Main.hx").write_text(r'''
class Main {
 static function main():Void {
  CodenameStateSmokeTrace.mark('timer-fired', 'owner|one', 'states/final:room',
   [CodenameStateSmokeTrace.field('seconds', 1.6), CodenameStateSmokeTrace.field('loops', 1)]);
  if (CodenameStateSmokeTrace.stateName(null) != 'null') throw 'null state label';
 }
}
''', newline='\n')
            quiet = subprocess.run([*HAXE_COMMAND, "-cp", scratch, "--run", "Main"],
                                   cwd=ROOT, capture_output=True, text=True, timeout=30)
            traced = subprocess.run([*HAXE_COMMAND, "-cp", scratch, "--run", "Main",
                                     "--codename-state-trace"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(quiet.returncode, 0, quiet.stdout + quiet.stderr)
        self.assertEqual(traced.returncode, 0, traced.stdout + traced.stderr)
        self.assertNotIn("CODENAME_STATE_TRACE|", quiet.stdout)
        self.assertIn("CODENAME_STATE_TRACE|codename-timer-fired:owner=owner_one:"
                      "script=states/final_room:seconds=1.6:loops=1", traced.stdout)

    def test_timer_switch_redirect_and_state_creation_are_instrumented(self):
        interp = (ROOT / "source" / "CodenameScriptInterp.hx").read_text()
        state_runtime = (ROOT / "source" / "CodenameModStateRuntime.hx").read_text()
        mod_runtime = (ROOT / "source" / "CodenameModRuntime.hx").read_text()
        imported_state = (ROOT / "source" / "CodenameImportedState.hx").read_text()

        timer = interp[interp.index("// Keep the selected script context while an asynchronous timer callback"):
                       interp.index("// Codename chart-event parameters")]
        self.assertIn("CodenameStateSmokeTrace.enabled()", timer)
        self.assertIn("runtimeSmokeOwnerRoot != ''", timer)
        self.assertIn("state-timer-start", timer)
        self.assertIn("state-timer-fired", timer)
        self.assertIn("callAsyncCallbackWithDiagnosticContext(callback, [timer], callbackSource, callbackName)", timer)
        self.assertIn("function callAsyncCallbackWithDiagnosticContext(", interp)

        switch = state_runtime[state_runtime.index("function switchState(target:Dynamic)"):
                              state_runtime.index("public function update(elapsed:Float)")]
        self.assertIn("state-switch-request", switch)
        self.assertIn("state-switch-accepted", switch)
        self.assertIn("state-switch-refused", switch)
        self.assertIn("CodenameModRuntime.switchTarget(ownerRoot, target)", switch)
        self.assertNotIn("FlxG.switchState(cast target)", switch)

        self.assertIn("global-pre-switch-before", mod_runtime)
        self.assertIn("global-pre-switch-after", mod_runtime)
        self.assertIn("pendingStateName('_nextState')", mod_runtime)
        self.assertIn("pendingStateName('_requestedState')", mod_runtime)
        self.assertIn("pre-state-create", mod_runtime)
        self.assertIn("preStateCreate.remove(preStateCreateSmokeHandler)", mod_runtime)
        transition = (ROOT / "source" / "CodenameMusicBeatTransition.hx").read_text()
        self.assertIn("transition-target", transition)
        self.assertIn("scriptTarget", transition)
        self.assertIn("hostTarget", transition)
        self.assertIn("imported-create-enter", imported_state)
        self.assertIn("imported-create-ready", imported_state)


if __name__ == "__main__":
    unittest.main()
