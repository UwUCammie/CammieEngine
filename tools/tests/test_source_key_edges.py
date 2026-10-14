"""Psych and Nightmare Vision key presses share one admission check."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
class State {
 public var demoMode = false; public var paused = false; public var generatedMusic = true; public var endingSong = false;
 public var startedCountdown = true; public var disableKeys = false;
 public var compatEventVideoControlsDisabled = false; public var hxcVideoControlsDisabled = false;
 public function new() {}
 @@METHOD@@
 public function admitted(countdown:Bool, locks:Bool):Bool return sourceKeyPressAdmitted(countdown, locks);
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  for (flags in [[false, false], [true, true]]) {
   var countdown = flags[0], locks = flags[1];
   var s = new State(); check(s.admitted(countdown, locks), 'ready state admits');
   s = new State(); s.demoMode = true; check(!s.admitted(countdown, locks), 'demo');
   s = new State(); s.paused = true; check(!s.admitted(countdown, locks), 'paused');
   s = new State(); s.generatedMusic = false; check(!s.admitted(countdown, locks), 'no chart');
   s = new State(); s.endingSong = true; check(!s.admitted(countdown, locks), 'ending');
  }
  // Psych's edge dispatcher owns the locks and does not wait for the countdown.
  var psych = new State(); psych.startedCountdown = false; psych.disableKeys = true;
  psych.compatEventVideoControlsDisabled = true; psych.hxcVideoControlsDisabled = true;
  check(psych.admitted(false, false), 'Psych profile leaves countdown and locks to its caller');
  var nv = new State(); nv.startedCountdown = false; check(!nv.admitted(true, true), 'NV waits for the countdown');
  nv = new State(); nv.disableKeys = true; check(!nv.admitted(true, true), 'NV key lock');
  nv = new State(); nv.compatEventVideoControlsDisabled = true; check(!nv.admitted(true, true), 'NV event video lock');
  nv = new State(); nv.hxcVideoControlsDisabled = true; check(!nv.admitted(true, true), 'NV script video lock');
 }
}
'''


class SourceKeyEdgesTest(unittest.TestCase):
	def test_admission_matrix_for_both_profiles(self):
		play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
		helper = method(play, 'function sourceKeyPressAdmitted(')
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			Path(folder, 'Main.hx').write_text(FIXTURE.replace('@@METHOD@@', helper), encoding='utf-8', newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
					cwd=ROOT, capture_output=True, text=True, timeout=120)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_both_handlers_use_the_shared_admission(self):
		play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
		psych = method(play, 'function psychSourceKeyPressed(')
		nv = method(play, 'function nightmareVisionSourceKeyPressed(')
		self.assertIn('!sourceKeyPressAdmitted(false, false) || inCutscene', psych)
		self.assertIn('actor.stunned', psych)
		self.assertIn('if (sourceKeyPressAdmitted(true, true)) {', nv)
		# NV's clock rewind keeps its own narrower gate; the admission rules live in the helper.
		for handler in (psych, nv):
			self.assertNotIn('generatedMusic', handler)
			self.assertNotIn('endingSong', handler)
			self.assertNotIn('hxcVideoControlsDisabled', handler)


if __name__ == '__main__':
	unittest.main()
