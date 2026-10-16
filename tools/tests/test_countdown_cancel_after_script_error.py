"""A countdownStart callback that cancels the countdown and then fails must not leave the song waiting forever."""
import unittest

from haxe_test_support import FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


class CountdownCancelAfterScriptErrorTest(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')

    def test_only_a_callback_that_cancelled_and_failed_is_counted(self):
        catch = self.source.index("trace(errorLine);")
        counted = self.source.rindex("countdownStartErrors++;", 0, catch)
        self.assertLess(catch - counted, 600, 'the counter must sit in the script error handler')
        # The counter needs the shared payload to have become cancelled during this very call:
        # a broken callback in another script must not override a working script's cancel.
        condition = self.source[self.source.rindex('if (', 0, counted):counted]
        for part in ('countdownPayload != null', '!countdownCancelledBefore',
                     'EngineCompat.hxcPayloadCanceled(countdownPayload)'):
            self.assertIn(part, condition)
        self.assertNotIn('||', condition)
        # The state before the call is read before the callback runs, from the arguments it receives.
        capture = self.source.rindex('countdownCancelledBefore = EngineCompat.hxcPayloadCanceled(countdownPayload);', 0, counted)
        invoke = self.source.index('returned = method(callArgs[0]);', capture)
        self.assertLess(capture, invoke)
        self.assertLess(self.source.rindex('countdownPayload = EngineCompat.hxcPayloadIn(callArgs);', 0, capture),
                        capture)
        self.assertIn("if (func_name == 'countdownStart' || func_name == 'onCountdownStart') {",
                      self.source[capture - 300:capture])

    def test_cancel_is_honoured_only_without_a_failure(self):
        start = self.source.index("var countdownErrorsBefore = countdownStartErrors;")
        block = self.source[start:start + 2600]
        dispatch = block.index("callAllHScript('countdownStart', [countdownEvent]);")
        guard = block.index("if (countdownStartErrors == countdownErrorsBefore) {")
        honoured = block.index("RuntimeSmokeHarness.markStep('countdown:cancelled-by-countdownStart');")
        ignored = block.index("RuntimeSmokeHarness.markStep('countdown:cancel-ignored-after-script-error');")
        self.assertLess(dispatch, guard)
        self.assertLess(guard, honoured)
        self.assertLess(honoured, block.index('return;', honoured) + 1)
        self.assertLess(block.index('return;', honoured), ignored, 'a failed cancel must fall through to the normal countdown')


if __name__ == '__main__':
    unittest.main()
