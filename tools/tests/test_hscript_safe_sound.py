"""HScript sound cache must not reuse destroyed FlxSound objects."""
from pathlib import Path
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
            path.write_text(fixture)
            result = subprocess.run([str(HAXE), '-cp', tmp, '--main', 'Test', '--interp'],
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
            path.write_text(fixture)
            result = subprocess.run([str(HAXE), '-cp', tmp, '--main', 'Test', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
