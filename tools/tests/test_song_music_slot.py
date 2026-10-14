"""A song started without menu music still gives scripts a FlxG.sound.music object."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

FLXG = '''package flixel;
class SoundFront { public var music:flixel.sound.FlxSound; public function new() {} }
class FlxG { public static var sound = new SoundFront(); }
'''
FLX_SOUND = '''package flixel.sound;
class FlxSound {
 public var persist = false;
 public var volume = 1.0;
 public var playing = false;
 public function new() {}
}
'''
MAIN = '''class Main {
 static function main() {
  if (!SongMusicSlot.ensure()) throw 'a missing music object was not created';
  var music = flixel.FlxG.sound.music;
  if (music == null || !music.persist) throw 'the placeholder must exist and survive state switches';
  if (music.playing) throw 'the placeholder must be silent';
  music.volume = 0; // what scripts do in onCreate
  if (SongMusicSlot.ensure() || flixel.FlxG.sound.music != music) throw 'existing music must be kept';
 }
}
'''


class SongMusicSlotTest(unittest.TestCase):
    def test_placeholder_only_when_music_is_missing(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            (root / 'flixel/sound').mkdir(parents=True)
            (root / 'flixel/FlxG.hx').write_text(FLXG, newline=chr(10))
            (root / 'flixel/sound/FlxSound.hx').write_text(FLX_SOUND, newline=chr(10))
            (root / 'SongMusicSlot.hx').write_text((ROOT / 'source/SongMusicSlot.hx').read_text(encoding='utf-8'), newline=chr(10))
            (root / 'Main.hx').write_text(MAIN, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_play_state_creates_it_before_scripts_run(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        create = source.index('override public function create() {')
        self.assertLess(source.index('SongMusicSlot.ensure();', create), source.index('EngineMemory.enterSong(this);', create))


if __name__ == '__main__':
    unittest.main()
