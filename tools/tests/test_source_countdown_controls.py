"""Scripts can tune the countdown and the reset key through PlayState fields."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('Unclosed source method: ' + marker)


class SourceCountdownControlsTest(unittest.TestCase):
    def setUp(self):
        self.play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')

    def test_intro_sound_names_and_reset_gate(self):
        fixture = r'''class Main {
 static function same(names:Array<String>, expected:String, why:String):Void
  if (names.join(',') != expected) throw why + ': ' + names.join(',');
 static function main():Void {
  // Untouched songs look for exactly what they always did.
  same(SongFlow.introSoundNames('intro3', '', '', true), 'intro3', 'stock');
  same(SongFlow.introSoundNames('intro3', null, '-pixel', true), 'intro3-pixel', 'pixel UI');
  // A script suffix is tried first and the usual sound stays as the fallback.
  same(SongFlow.introSoundNames('introGo', '-custom', '', true), 'introGo-custom,introGo', 'scripted');
  same(SongFlow.introSoundNames('introGo', '-custom', '-pixel', true), 'introGo-custom,introGo-pixel', 'scripted on pixel UI');
  // A script asking for the suffix the UI already uses must not double it.
  same(SongFlow.introSoundNames('intro1', '-pixel', '-pixel', true), 'intro1-pixel', 'same suffix twice');
  // A silent countdown needs no sound at all.
  same(SongFlow.introSoundNames('intro2', '-custom', '-pixel', false), '', 'muted');

  if (!SongFlow.resetKeyAllowed(true, false, false, false, false)) throw 'reset blocked by default';
  if (SongFlow.resetKeyAllowed(false, false, false, false, false)) throw 'canReset = false did not block reset';
  if (SongFlow.resetKeyAllowed(true, true, false, false, false)) throw 'two player mode';
  if (SongFlow.resetKeyAllowed(true, false, true, false, false)) throw 'cutscene';
  if (SongFlow.resetKeyAllowed(true, false, false, true, false)) throw 'locked controls';
  if (SongFlow.resetKeyAllowed(true, false, false, false, true)) throw 'preference';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                     '--main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fields_exist_with_defaults_that_change_nothing(self):
        for declaration in (
            "@:keep public var introSoundsSuffix:String = '';",
            '@:keep public var countdownSounds:Bool = true;',
            '@:keep public var countdownDelay:Float = 0;',
            '@:keep public var countdownReady:FlxSprite = null;',
            '@:keep public var countdownSet:FlxSprite = null;',
            '@:keep public var countdownGo:FlxSprite = null;',
            '@:keep public var canReset:Bool = true;',
            '@:keep public var canAccessEditors:Bool = true;',
        ):
            self.assertEqual(self.play.count(declaration), 1, declaration)

    def test_countdown_reads_the_options(self):
        countdown = method(self.play, 'public function startCountdown():Void')
        # The wait sits between the scripts allowing the countdown and it starting.
        clock = countdown.index('var beginCountdownClock = function():Void {')
        delay = countdown.index('if (countdownDelay > 0) {')
        self.assertLess(countdown.index('if (sourceCountdownStopped)'), clock)
        self.assertLess(clock, countdown.index('startedCountdown = true;'))
        self.assertLess(countdown.index('startedCountdown = true;'), delay)
        waiting = countdown[delay:]
        self.assertIn('new FlxTimer().start(countdownDelay,', waiting)
        self.assertIn('if (!startedCountdown) beginCountdownClock();', waiting)
        # Asking again during the wait stops before anything is set up twice.
        waiting_guard = countdown.index('if (countdownDelayTimer != null && !countdownDelayTimer.finished) return;')
        self.assertLess(waiting_guard, countdown.index('var countdownResults:Array<Dynamic> = [];'))
        self.assertLess(waiting_guard, countdown.index('generatePlayfields();'))
        # Like Nightmare Vision, the notes are on the field before the wait begins.
        self.assertLess(countdown.index('generatePlayfields();'), clock)
        self.assertTrue(waiting.rstrip().endswith('beginCountdownClock();\n\t}'), 'no delay must start at once')

        for name, variable in (('intro3', 'intro3Sound'), ('intro2', 'intro2Sound'),
                               ('intro1', 'intro1Sound'), ('introGo', 'introGoSound')):
            self.assertIn("%s = countdownIntroSound('%s', altSuffix, uipackPath);" % (variable, name), countdown)
            self.assertIn('if (%s != null) FlxG.sound.play(%s, 0.6);' % (variable, variable), countdown)
        sound = method(self.play, 'function countdownIntroSound(')
        self.assertIn('SongFlow.introSoundNames(name, introSoundsSuffix, uiSuffix, countdownSounds)', sound)
        self.assertIn("FNFAssets.getAssetWithBackup(uiPackPath + name + uiSuffix + '.ogg', 'assets/sounds/' + name + uiSuffix + '.ogg', SOUND)", sound)

    def test_reset_and_editor_keys_respect_the_script_switches(self):
        self.assertIn('&& SongFlow.resetKeyAllowed(canReset, duoMode, inCutscene,', self.play)
        self.assertIn('FlxG.keys.justPressed.SEVEN && !OptionsHandler.options.danceMode && canAccessEditors', self.play)
        self.assertIn('FlxG.keys.justPressed.EIGHT && !OptionsHandler.options.danceMode && canAccessEditors', self.play)


if __name__ == '__main__':
    unittest.main()
