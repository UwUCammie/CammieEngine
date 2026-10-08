"""HScript sound cache must not reuse destroyed FlxSound objects."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'
SOURCE = ROOT / 'source/PlayState.hx'


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f'unterminated method: {marker}')


class HscriptSafeSoundTest(unittest.TestCase):
    def test_cached_script_sfx_uses_saved_default_group_before_first_play(self):
        source = SOURCE.read_text()
        methods = "\n".join(
            extract_method(source, marker).replace("public static function", "static function")
            for marker in (
                "public static function hscriptSoundNeedsRebuild(",
                "public static function resolveHscriptSoundPath(",
                "public static function preloadHscriptSound(",
                "public static function hscriptSafePlay(",
            )
        )
        fixture = f'''using StringTools;
class Sound {{
  public function new() {{}}
  public static function fromFile(_path:String):Sound return new Sound();
}}
class FNFAssets {{
  public static function exists(path:String):Bool return path.endsWith('.ogg');
}}
class FlxSoundGroup {{
  public var volume:Float;
  public var sounds:Array<FlxSound> = [];
  public function new(volume:Float) this.volume = volume;
  public function add(sound:FlxSound):Bool {{
    if (sound.group != null) sound.group.sounds.remove(sound);
    if (!sounds.contains(sound)) sounds.push(sound);
    sound.group = this;
    return true;
  }}
  public function remove(sound:FlxSound):Bool {{
    sound.group = null;
    return sounds.remove(sound);
  }}
  public function getVolume():Float return volume;
}}
class FlxSound {{
  public var exists:Bool = true;
  public var volume:Float = 1;
  public var group:FlxSoundGroup;
  public var plays:Int = 0;
  public var groupVolumeAtPlay:Float = -1;
  public var globalVolumeAtPlay:Float = -1;
  public var effectiveVolumeAtPlay:Float = -1;
  public function new() {{}}
  public function loadEmbedded(_sound:Sound, _looped:Bool, _autoDestroy:Bool):FlxSound return this;
  public function play(_forceRestart:Bool = false):FlxSound {{
    plays++;
    groupVolumeAtPlay = group == null ? 1 : group.getVolume();
    globalVolumeAtPlay = FlxG.sound.volume;
    effectiveVolumeAtPlay = volume * groupVolumeAtPlay * globalVolumeAtPlay;
    return this;
  }}
}}
class FlxSoundList {{
  public var sounds:Array<FlxSound> = [];
  public function new() {{}}
  public function add(sound:FlxSound):Bool {{ sounds.push(sound); return true; }}
}}
class SoundFrontEnd {{
  public var list:FlxSoundList = new FlxSoundList();
  public var defaultSoundGroup:FlxSoundGroup = new FlxSoundGroup(0.25);
  public var volume:Float = 0.5;
  public function new() {{}}
  public function play(_sound:Dynamic, _volume:Float, _looped:Bool):FlxSound return new FlxSound();
}}
class FlxG {{ public static var sound:SoundFrontEnd = new SoundFrontEnd(); }}
class Test {{
  static var hscriptSoundCache:Map<String,Sound> = new Map();
  static var hscriptSoundLastPlay:Map<String,Float> = new Map();
  static var hscriptFlxSounds:Map<String,FlxSound> = new Map();
  static var hscriptFlxSoundLooped:Map<String,Bool> = new Map();
{methods}
  static function main():Void {{
    var sound = hscriptSafePlay('scrollMenu', 0.8, false);
    if (sound == null || sound.group != FlxG.sound.defaultSoundGroup
        || sound.groupVolumeAtPlay != 0.25 || sound.globalVolumeAtPlay != 0.5
        || sound.volume != 0.8 || Math.abs(sound.effectiveVolumeAtPlay - 0.1) > 0.0001)
      throw 'first cached script SFX bypassed the saved SFX or master volume';
    if (FlxG.sound.list.sounds.length != 1 || FlxG.sound.defaultSoundGroup.sounds.length != 1)
      throw 'cached script SFX was not registered exactly once in both update and volume groups';

    hscriptSoundLastPlay.set('scrollMenu.ogg', Sys.time() - 0.1);
    FlxG.sound.defaultSoundGroup.volume = 0.4;
    FlxG.sound.volume = 0.75;
    var repeated = hscriptSafePlay('scrollMenu', 0.4, false);
    if (repeated != sound || repeated.plays != 2 || repeated.group != FlxG.sound.defaultSoundGroup
        || repeated.groupVolumeAtPlay != 0.4 || repeated.globalVolumeAtPlay != 0.75
        || repeated.volume != 0.4 || Math.abs(repeated.effectiveVolumeAtPlay - 0.12) > 0.0001)
      throw 'reused script SFX lost its updated group, master, or authored volume';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
            path = Path(tmp) / 'Test.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '--run', 'Test'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_destroyed_cached_sound_is_rebuilt(self):
        source = SOURCE.read_text()
        start = source.index('\tpublic static function hscriptSoundNeedsRebuild(')
        end = source.index('\n\tpublic static function resolveHscriptSoundPath(', start)
        helper = source[start:end].replace('public static function', 'static function')
        fixture = f'''class FlxSound {{
\tpublic var exists:Bool;
\tpublic function new(exists:Bool) this.exists = exists;
}}
class Test {{
{helper}
\tstatic function main() {{
\t\tif (!hscriptSoundNeedsRebuild(null, false, false)) throw "null cache reused";
\t\tif (!hscriptSoundNeedsRebuild(new FlxSound(false), false, false)) throw "destroyed cache reused";
\t\tif (!hscriptSoundNeedsRebuild(new FlxSound(true), false, true)) throw "loop mode mismatch reused";
\t\tif (hscriptSoundNeedsRebuild(new FlxSound(true), false, false)) throw "live matching sound rebuilt";
\t}}
}}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Test.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '--main', 'Test', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_state_cleanup_releases_only_owned_hscript_sounds(self):
        source = SOURCE.read_text()
        clear_method = extract_method(source, '\tpublic static function clearHscriptSoundCache():Void')
        clear_method = clear_method.replace('public static function', 'static function', 1)
        destroy_method = extract_method(source, '\toverride public function destroy()')
        self.assertLess(destroy_method.index('clearScriptOwnership();'),
                        destroy_method.index('clearHscriptSoundCache();'))
        self.assertLess(destroy_method.index('clearHscriptSoundCache();'),
                        destroy_method.index('super.destroy();'))
        fixture = f'''class FlxSound {{
  public static var group:Array<FlxSound> = [];
  public var exists:Bool;
  public var destroyCalls:Int = 0;
  public function new(exists:Bool) this.exists = exists;
  public function destroy():Void {{
    destroyCalls++;
    exists = false;
    FlxSound.group.remove(this);
  }}
}}
class Test {{
  static var hscriptFlxSounds:Map<String,FlxSound> = [];
  static var hscriptFlxSoundLooped:Map<String,Bool> = [];
  static var hscriptSoundCache:Map<String,Dynamic> = [];
  static var hscriptSoundLastPlay:Map<String,Float> = [];
{clear_method}
  static function main():Void {{
    var owned = new FlxSound(true);
    var deadOwned = new FlxSound(false);
    var unrelated = new FlxSound(true);
    FlxSound.group = [owned, deadOwned, unrelated];
    hscriptFlxSounds.set('owned.ogg', owned);
    hscriptFlxSounds.set('dead.ogg', deadOwned);
    hscriptFlxSoundLooped.set('owned.ogg', true);
    hscriptSoundCache.set('owned.ogg', {{}});
    hscriptSoundLastPlay.set('owned.ogg', 1.0);

    clearHscriptSoundCache();

    if (owned.destroyCalls != 1 || owned.exists || FlxSound.group.indexOf(owned) >= 0)
      throw 'live PlayState-owned FlxSound was not destroyed and detached once';
    if (deadOwned.destroyCalls != 0)
      throw 'already-dead FlxSound was destroyed twice';
    if (!unrelated.exists || unrelated.destroyCalls != 0
        || FlxSound.group.indexOf(unrelated) < 0)
      throw 'unowned sound in the global sound group was changed';
    if (hscriptFlxSounds.keys().hasNext() || hscriptFlxSoundLooped.keys().hasNext()
        || hscriptSoundCache.keys().hasNext() || hscriptSoundLastPlay.keys().hasNext())
      throw 'per-song HScript sound cache maps were retained';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
            path = Path(tmp) / 'Test.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '--main', 'Test', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
