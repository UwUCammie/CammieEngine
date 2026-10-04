"""Gameplay pause uses the configured control action, including Escape and P."""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PlayStatePauseInputTest(unittest.TestCase):
    def test_gameplay_uses_pause_action_and_keeps_script_cancellation(self):
        controls = (ROOT / "source/Controls.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("bindKeys(Control.PAUSE, [P, ENTER, ESCAPE])", controls)
        pause_gate = "if ((psychControls == null ? controls.PAUSE : psychControls.PAUSE) && startedCountdown && canPause"
        self.assertTrue(pause_gate in play_state, "Configured gameplay pause gate missing")
        self.assertIn("callNightmareVision('onPause', []) != NightmareVisionScriptGroup.STOP_FUNC", play_state)
        callback = "callAllHScript('onPause', [], false, pauseResults, [pauseEvent])"
        self.assertLess(play_state.index(pause_gate), play_state.index(callback))
        self.assertIn("EngineCompat.anyFunctionStop(pauseResults)", play_state)


if __name__ == "__main__":
    unittest.main()
