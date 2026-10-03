"""Smoke song-rate input shares PlayState's demo-rate lifecycle when botplaying."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / 'tmp'
TMP.mkdir(exist_ok=True)
HAXE = ROOT / '.tools/haxe/haxe'


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
    raise AssertionError(marker)


class RuntimeSmokeDemoSongRateTest(unittest.TestCase):
    @unittest.skipUnless(HAXE.is_file(), 'portable Haxe is unavailable')
    def test_botplay_uses_demo_setter_and_preserves_end_reset(self):
        harness = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text()
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        apply_rate = extract_method(harness, 'static function applySongRate(')
        demo_setter = extract_method(play_state, 'function setDemoPlaybackRate(')
        demo_apply = extract_method(play_state, 'function applyDemoPlaybackRate(')
        demo_reset = extract_method(play_state, 'function resetDemoPlaybackRate(')
        vocals_pitch = extract_method(play_state, 'function setVocalsPitch(')
        tick = extract_method(harness, 'public static function tick(')
        self.assertLess(tick.index('if (!enabled() || finished || !started)'), tick.index('applySongRate();'))
        self.assertIn('state.setDemoPlaybackRate(rate);', apply_rate)
        self.assertIn('if (!state.endingSong)', apply_rate)

        fixture = '''
class Music {
  public var pitch:Float = 1;
  public function new() {}
}
class SoundManager { public var music:Music = new Music(); public function new() {} }
class FlxG {
  public static var timeScale:Float = 1;
  public static var sound:SoundManager = new SoundManager();
}
class FlxMath {
  public static function bound(value:Float, min:Float, max:Float):Float
    return Math.max(min, Math.min(max, value));
}
class VocalTracks {
  public var pitch:Float = 1;
  public function new() {}
  public function setPitch(value:Float):Void pitch = value;
}
class Label { public var text:String = ''; public function new() {} }
class PlayState {
  public static var instance:PlayState;
  public var demoMode:Bool;
  public var demoPlaybackRate:Float = 1;
  public var paused:Bool = false;
  public var endingSong:Bool = false;
  public var startingSong:Bool = false;
  public var vocalTracks:Dynamic;
  public var vocals:Dynamic;
  public var demoSpeedTxt:Dynamic = new Label();
  public function new(demo:Bool) { demoMode = demo; instance = this; }
  public function resetDemoRate():Void resetDemoPlaybackRate();
''' + '\n'.join((demo_setter, demo_apply, demo_reset, vocals_pitch)) + '''
}
@:access(PlayState)
class RuntimeSmokeHarness {
  public static var request:Dynamic;
  static function config():Dynamic return request;
  public static function run():Void applySongRate();
''' + apply_rate + '''
}
class Main {
  static function check(ok:Bool, message:String):Void if (!ok) throw message;
  static function main():Void {
    RuntimeSmokeHarness.request = {songRate: 6.5};
    var demo = new PlayState(true);
    demo.vocalTracks = new VocalTracks();
    demo.vocals = {pitch: 1.0};
    RuntimeSmokeHarness.run();
    check(demo.demoPlaybackRate == 6.5, 'smoke rate did not use demo rate state');
    check(FlxG.timeScale == 6.5 && FlxG.sound.music.pitch == 6.5,
      'native demo helper did not apply time and instrumental rate');
    check(demo.vocalTracks.pitch == 6.5, 'native demo helper did not apply vocal-track rate');
    demo.resetDemoRate();
    check(FlxG.timeScale == 1 && FlxG.sound.music.pitch == 1
      && demo.vocalTracks.pitch == 1, 'natural end reset did not restore all rates');
    demo.endingSong = true;
    RuntimeSmokeHarness.run();
    check(FlxG.timeScale == 1 && FlxG.sound.music.pitch == 1
      && demo.vocalTracks.pitch == 1, 'smoke tick reapplied rate after ending reset');

    var ordinary = new PlayState(false);
    ordinary.vocals = {pitch: 1.0};
    FlxG.timeScale = 1;
    FlxG.sound.music.pitch = 1;
    RuntimeSmokeHarness.run();
    check(FlxG.timeScale == 6.5 && FlxG.sound.music.pitch == 6.5,
      'non-demo smoke rate path changed');
    check(ordinary.demoPlaybackRate == 1 && ordinary.vocals.pitch == 1,
      'non-demo smoke unexpectedly entered the demo path');
  }
}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
