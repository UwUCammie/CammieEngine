"""Codename song audio callbacks use the live Flixel music sound."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameInstrumentalFacadeTest(unittest.TestCase):
    def test_live_length_time_callback_and_release(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            base = Path(work)
            flxg = base / 'flixel/FlxG.hx'
            flxg.parent.mkdir(parents=True)
            flxg.write_text('''package flixel;
class FlxG { public static var sound:Dynamic={music:null}; }
''', newline='\n')
            (base / 'Main.hx').write_text('''import flixel.FlxG;
class Main {
 static function main():Void {
  var facade=new CodenameInstrumentalFacade({length:1200.0});
  if(facade.length!=1200 || facade.time!=0) throw "source sound fallback";
  FlxG.sound.music={length:2400.0,time:100.0};
  if(facade.length!=2400 || facade.time!=100) throw "live music view";
  facade.time=900;
  if(FlxG.sound.music.time!=900) throw "seek did not update live sound";
  var calls=0;
  facade.onComplete=function():Void calls++;
  if(!facade.complete() || calls!=1) throw "authored callback not invoked";
  facade.release();
  if(facade.complete() || calls!=1) throw "released callback survived";
 }
}''', newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', work, '--run', 'Main'
            ], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
