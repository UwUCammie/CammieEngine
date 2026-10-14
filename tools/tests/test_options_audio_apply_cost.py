"""Reading OptionsHandler.options must not touch every sound's gain when nothing changed.

The getter applies the audio options on every read, and engine code reads the
options many times per frame. A group volume assignment refreshes every sound
in the group, so the production applyAudioOptions is run here against counting
stand-ins to show it only assigns a value that differs.
"""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def section(text, start, end):
    pos = text.index(start)
    return text[pos:text.index(end, pos)]


class OptionsAudioApplyCostTest(unittest.TestCase):
    def test_unchanged_volumes_are_not_reassigned(self):
        options = (ROOT / 'source/OptionsHandler.hx').read_text(encoding='utf-8')
        apply = section(options, '    public static function applyAudioOptions', '    static function get_options')
        self.assertIn('applyAudioOptions(lastOptions);', options, 'the getter still applies audio options on every read')
        fixture = '''
class Group {
	public var assignments = 0;
	public var refreshedSounds = 0;
	public var sounds = 12;
	public var volume(default, set):Float = 1;
	public function new() {}
	function set_volume(value:Float):Float {
		assignments++;
		refreshedSounds += sounds;
		return volume = value;
	}
}
class SoundFront {
	public var defaultMusicGroup = new Group();
	public var defaultSoundGroup = new Group();
	public function new() {}
}
class FlxG { public static var sound:SoundFront = new SoundFront(); }
typedef TOptions = {volumeMusic:Float, volumeSFX:Float};
class Main {
''' + apply + '''
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function main() {
		var music = FlxG.sound.defaultMusicGroup;
		var effects = FlxG.sound.defaultSoundGroup;
		var opt:TOptions = {volumeMusic: 0.4, volumeSFX: 0.8};
		applyAudioOptions(opt);
		check(music.volume == 0.4 && effects.volume == 0.8, 'first apply sets both groups');
		check(music.assignments == 1 && effects.assignments == 1, 'first apply assigns once each');
		// A frame of option reads with nothing changed.
		for (i in 0...500) applyAudioOptions(opt);
		check(music.assignments == 1 && effects.assignments == 1, 'unchanged reads must not reassign');
		check(music.refreshedSounds == 12 && effects.refreshedSounds == 12, 'unchanged reads must not refresh sounds');
		// Something else changed a group: the next read still restores the option value.
		music.volume = 0.1;
		applyAudioOptions(opt);
		check(music.volume == 0.4, 'a changed group is restored to the option value');
		opt.volumeSFX = 0.25;
		applyAudioOptions(opt);
		check(effects.volume == 0.25 && effects.assignments == 2, 'a changed option is applied once');
		applyAudioOptions(null);
		Sys.println('ok');
	}
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
