"""Pin source character special, return, and held-animation transitions."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


class SourceCharacterAnimationLifecycleTest(unittest.TestCase):
    def test_source_transition_policy_and_character_wiring(self):
        helper = (ROOT / 'source/SourceCharacterAnimationLifecycle.hx').read_text(encoding='utf-8')
        character = (ROOT / 'source/Character.hx').read_text(encoding='utf-8')
        self.assertIn('SourceCharacterAnimationLifecycle.specialAfterPlay', character)
        self.assertIn('SourceCharacterAnimationLifecycle.returnAnimation', character)
        self.assertIn('SourceCharacterAnimationLifecycle.finishesReturn', character)
        self.assertIn('SourceCharacterAnimationLifecycle.mayFinishSpecial', character)
        self.assertIn('SourceCharacterAnimationLifecycle.mayAdvanceSingDance', character)
        self.assertIn('SourceCharacterAnimationLifecycle.usesSingDurationFallback', character)
        self.assertIn('SourceCharacterAnimationLifecycle.shouldAccumulateSingDuration', character)
        self.assertIn('sourceDanceNightmare ? singDuration', character)
        self.assertIn('if (interp != null && !sourceDanceNightmare)', character)
        self.assertLess(character.index('if (!canPlayAnimations) return;'),
                        character.index('SourceCharacterAnimationLifecycle.specialAfterPlay'))

        fixture = '''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  check(!SourceCharacterAnimationLifecycle.specialAfterPlay(true, 1, false, false),
   'Psych playback must clear a special latch before a new animation');
  check(!SourceCharacterAnimationLifecycle.specialAfterPlay(true, 2, false, false),
   'Nightmare Vision playback must clear a special latch before a new animation');
  check(!SourceCharacterAnimationLifecycle.specialAfterPlay(true, 0, true, false),
   'an NV-owned actor must clear a special latch in an otherwise native context');
  check(SourceCharacterAnimationLifecycle.specialAfterPlay(true, 0, false, false),
   'native playback must preserve its special latch');
  check(SourceCharacterAnimationLifecycle.specialAfterPlay(true, 2, true, true),
   'Codename keeps its separate special-animation contract');
  check(!SourceCharacterAnimationLifecycle.mayFinishSpecial(true, true)
   && SourceCharacterAnimationLifecycle.mayFinishSpecial(true, false),
   'NV cutscene/special animation stays held until input release');
  check(SourceCharacterAnimationLifecycle.mayFinishSpecial(false, true),
   'Psych special completion does not inherit NV holding semantics');

  check(SourceCharacterAnimationLifecycle.returnAnimation('singLEFT', true, true, false, false)
   == 'singLEFT-return', 'NV enters the authored return animation');
  check(SourceCharacterAnimationLifecycle.returnAnimation('singLEFT', false, true, false, false)
   == null, 'missing return animation falls back to idle');
  check(SourceCharacterAnimationLifecycle.returnAnimation('singLEFT', true, false, false, false)
   == null, 'Psych does not gain NV return behavior');
  check(SourceCharacterAnimationLifecycle.returnAnimation('singLEFT', true, true, true, false)
   == null, 'debug animation is not replaced by return');
  check(SourceCharacterAnimationLifecycle.returnAnimation('Grab', true, true, false, true)
   == null, 'cutscene special animation is not replaced by a return');
  check(SourceCharacterAnimationLifecycle.finishesReturn(true, 'singLEFT-return', true)
   && !SourceCharacterAnimationLifecycle.finishesReturn(true, 'singLEFT-return', false)
   && !SourceCharacterAnimationLifecycle.finishesReturn(false, 'singLEFT-return', true),
   'only a completed NV return leaves the return state');
  check(!SourceCharacterAnimationLifecycle.mayAdvanceSingDance(true, true)
   && SourceCharacterAnimationLifecycle.mayAdvanceSingDance(true, false)
   && SourceCharacterAnimationLifecycle.mayAdvanceSingDance(false, true),
   'NV sing-duration fallback respects held input without changing Psych');
  check(SourceCharacterAnimationLifecycle.usesSingDurationFallback(true, true)
   && SourceCharacterAnimationLifecycle.usesSingDurationFallback(true, false)
   && !SourceCharacterAnimationLifecycle.usesSingDurationFallback(false, true)
   && SourceCharacterAnimationLifecycle.usesSingDurationFallback(false, false),
   'NV sing-duration fallback covers every actor role while native keeps its controlled split');
  check(SourceCharacterAnimationLifecycle.shouldAccumulateSingDuration(true, 'singLEFT', [], false)
   && SourceCharacterAnimationLifecycle.shouldAccumulateSingDuration(true, 'hey', [], true)
   && !SourceCharacterAnimationLifecycle.shouldAccumulateSingDuration(true, 'hey', [], false)
   && SourceCharacterAnimationLifecycle.shouldAccumulateSingDuration(false, 'hey', ['hey'], false)
   && !SourceCharacterAnimationLifecycle.shouldAccumulateSingDuration(false, 'hey', [], true),
   'NV hold time includes a live hold while native keeps its sing-priority rule');
  check(!SourceCharacterAnimationLifecycle.shouldPlayNightmareVisionNoteAnimation(true, true, true)
   && SourceCharacterAnimationLifecycle.shouldPlayNightmareVisionNoteAnimation(true, true, false)
   && SourceCharacterAnimationLifecycle.shouldPlayNightmareVisionNoteAnimation(true, false, true)
   && SourceCharacterAnimationLifecycle.shouldPlayNightmareVisionNoteAnimation(false, true, true),
   'only opted-in NV sustains suppress note animation, never taps or other dialects');

 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            (work / 'SourceCharacterAnimationLifecycle.hx').write_text(
                helper, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
