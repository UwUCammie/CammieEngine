from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DemoBeatTest(unittest.TestCase):
    def test_demo_delivers_every_crossed_step(self):
        source = (ROOT / 'source/MusicBeatState.hx').read_text()
        method = source[source.index('\toverride function update('):source.index('\tprivate function updateBeat')]
        fixture = '''
class Base { public function new() {} public function update(elapsed:Float) {} }
class FlxG {
 public static var keys={justPressed:{ESCAPE:false},pressed:{SHIFT:false}};
 public static function resetGame() {}
}
class TitleState { public static var initialized=true; }
class BeatTest extends Base {
 var curStep=0; var maxStepCatchUp=32; var targetStep=200;
 var steps:Array<Int>=[]; var beats:Array<Int>=[];
 function updateCurStep() {curStep=targetStep;}
 function updateBeat() {}
 function stepHit() {steps.push(curStep); if(curStep%4==0) beats.push(Std.int(curStep/4));}
''' + method + '''
 static function main() {
  var demo=new BeatTest(); demo.maxStepCatchUp=0;
  demo.update(0);
  if(demo.steps.length!=200 || demo.beats.length!=50) throw "Accelerated demo dropped beat hooks";
  for(i in 0...200) if(demo.steps[i]!=i+1) throw "Steps must stay ordered";
  demo.update(0);
  if(demo.steps.length!=200) throw "Stationary audio must not repeat hooks";
  var normal=new BeatTest(); normal.update(0);
  if(normal.steps.length!=33) throw "Normal gameplay stall protection changed";
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'BeatTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '-main', 'BeatTest', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
