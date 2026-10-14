"""Cancelable V-Slice lifecycle events reach the game through one helper."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]

MODULE = '''
class HoldTheScreen extends Module {
    function new() { super("hold-the-screen"); }
    override function onGameOver(event) { event.cancel(); }
    override function onCountdownStep(event) { if (event.step == "TWO") event.cancel(); }
    override function onResume(event) { event.cancelEvent(); }
    override function onPause(event) { event.eventCanceled = true; }
    override function onCountdownStart(event) { Countdown.pauseCountdown(); Countdown.resumeCountdown(); }
}
'''


class HxcLifecycleCancellationTest(unittest.TestCase):
    def run_fixture(self, fixture):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "LifecycleCancelFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "LifecycleCancelFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_translated_handlers_cancel_the_shared_payload(self):
        self.run_fixture(f'''import hscript.Interp;
import hscript.Parser;
class LifecycleCancelFixture {{
    static function fail(message:String):Void throw message;
    static function main() {{
        var result = HxcCompat.analyze({json.dumps(MODULE)}, "scripts/modules/hold.hxc");
        var generated:String = result.generatedHscript;
        for (name in ["gameOver", "countdownStep", "resume", "pause"])
            if (result.canonicalCallbacks.indexOf(name) < 0) fail("callback not routed: " + name);
        if (generated.indexOf("HxcCompatRuntime.pauseCountdown(PlayState.instance)") < 0
            || generated.indexOf("HxcCompatRuntime.resumeCountdown(PlayState.instance)") < 0)
            fail("countdown hold facade was not lowered: " + generated);
        // Only the plain handlers are run here; the countdown facade needs a live game.
        var handlers = generated.substr(0, generated.indexOf("function countdownStart("));
        if (handlers.indexOf("function gameOver(") < 0) fail("fixture order changed: " + generated);
        var interp = new Interp();
        interp.execute(new Parser().parseString(handlers));
        function call(name:String, payload:Dynamic):Dynamic {{
            Reflect.callMethod(null, interp.variables.get(name), [payload]);
            return payload;
        }}

        var untouched = EngineCompat.hxcLifecyclePayload("gameOver", {{targetState: null}});
        if (EngineCompat.hxcPayloadCanceled(untouched)) fail("a fresh event must not be cancelled");
        if (EngineCompat.hxcPayloadCanceled(null)) fail("no event, nothing cancelled");

        if (!EngineCompat.hxcPayloadCanceled(call("gameOver", untouched))) fail("game over cancel");
        if (!EngineCompat.hxcPayloadCanceled(call("resume", EngineCompat.hxcLifecyclePayload("resume"))))
            fail("resume cancelEvent");
        // A handler may write the flag instead of calling cancel().
        if (!EngineCompat.hxcPayloadCanceled(call("pause", EngineCompat.hxcLifecyclePayload("pause"))))
            fail("direct flag write");
        if (EngineCompat.hxcPayloadCanceled(call("countdownStep", EngineCompat.hxcCountdownStepPayload(0))))
            fail("step three was not cancelled by the script");
        if (!EngineCompat.hxcPayloadCanceled(call("countdownStep", EngineCompat.hxcCountdownStepPayload(1))))
            fail("step two cancel");
        for (spelling in ["canceled", "cancelled"]) {{
            var payload = EngineCompat.hxcLifecyclePayload("gameOver");
            Reflect.setField(payload, spelling, true);
            if (!EngineCompat.hxcPayloadCanceled(payload)) fail("alias " + spelling);
        }}
        Sys.println("ok");
    }}
}}
''')

    def test_countdown_hold_facade_calls_only_the_owner(self):
        self.run_fixture('''class FakeOwner {
    public function new() {}
    public var held:Bool = false;
    public function hxcPauseCountdown():Bool { held = true; return true; }
    public function hxcResumeCountdown():Bool { if (!held) return false; held = false; return true; }
}
class LifecycleCancelFixture {
    static function fail(message:String):Void throw message;
    static function main() {
        var owner = new FakeOwner();
        if (HxcCompatRuntime.resumeCountdown(owner)) fail("nothing was held yet");
        if (!HxcCompatRuntime.pauseCountdown(owner) || !owner.held) fail("pause facade");
        if (!HxcCompatRuntime.resumeCountdown(owner) || owner.held) fail("resume facade");
        if (HxcCompatRuntime.pauseCountdown({})) fail("an owner without the method must refuse");
        Sys.println("ok");
    }
}
''')

    def test_playstate_routes_cancelable_events_through_the_helper(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        helper = source[source.index("function dispatchCancelableLifecycle("):
            source.index("function callCountdownTick(")]
        self.assertIn("return EngineCompat.hxcPayloadCanceled(payload);", helper)

        # Game over: a cancel skips the game over screen and un-stages the death.
        game_over = source[source.index("function runPsychGameOverTransition("):
            source.index("function cancelPendingGameOver(")]
        dispatch = game_over.index("if (dispatchCancelableLifecycle('gameOver',")
        self.assertLess(dispatch, game_over.index("cancelPendingGameOver();"))
        self.assertLess(game_over.index("cancelPendingGameOver();"),
            game_over.index("openSubState(new GameOverSubstate("))
        # The song is only paused while scripts are asked; stopping it would
        # rewind it and leave a cancelled game over with nothing to resume.
        paused = game_over.index("FlxG.sound.music.pause();")
        stopped = game_over.index("FlxG.sound.music.stop();")
        self.assertLess(paused, dispatch)
        self.assertLess(game_over.index("cancelPendingGameOver();"), stopped)
        self.assertLess(stopped, game_over.index("openSubState(new GameOverSubstate("))
        undo = source[source.index("function cancelPendingGameOver("):
            source.index("public function psychGameOverSoundPath(")]
        for line in ["psychGameOverTransitionPending = false;", "paused = false;",
                     "persistentUpdate = true;"]:
            self.assertIn(line, undo)

        # Countdown step: a cancel holds the timer on that step.
        tick = source[source.index("function callCountdownTick("):
            source.index("function removeGlobalSpriteReferences(")]
        self.assertIn("dispatchCancelableLifecycle('countdownStep', "
            "EngineCompat.hxcCountdownStepPayload(tick))", tick)
        self.assertIn("hxcPauseCountdown();", tick)
        hold = source[source.index("public function hxcPauseCountdown("):
            source.index("public function startCountdown(")]
        self.assertIn("startTimer.active = false;", hold)
        self.assertIn("public function hxcResumeCountdown(", hold)

        # Resume: asked before anything is un-paused, and a cancel keeps the menu.
        close = source[source.index("override function closeSubState("):]
        asked = close.index("dispatchCancelableHxcLifecycle('onResume', "
            "EngineCompat.hxcLifecyclePayload('resume'))")
        self.assertLess(asked, close.index("paused = false;"))
        self.assertLess(asked, close.index("super.closeSubState();"))
        # The other script families are still told once, without a second HXC call.
        self.assertIn("callAllHScript('onResume', [], hxcResumeDispatched);", close)

        # The older inline flag tests are gone in favour of the one helper.
        self.assertNotIn("countdownEvent.eventCanceled == true", source)
        self.assertNotIn("pauseEvent.eventCanceled == true", source)
        self.assertIn("EngineCompat.hxcPayloadCanceled(countdownEvent)", source)
        self.assertIn("EngineCompat.hxcPayloadCanceled(pauseEvent)", source)


if __name__ == "__main__":
    unittest.main()
