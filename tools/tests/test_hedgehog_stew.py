from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HedgehogStewTest(unittest.TestCase):
    def test_fear_gauge_is_bounded_and_scaled_to_the_asset(self):
        fixture = ROOT / 'assets/data/hedgehog-stew/modchart.hscript'
        if not fixture.is_file():
            self.skipTest(f'mounted Hedgehog Stew modchart fixture unavailable: {fixture}')
        script = fixture.read_text()
        helpers = script[:script.index('function start')]
        callbacks = script[script.index('function update'):]
        fixture = '''import hscript.Interp;
import hscript.Parser;
class Scale {
 public var y:Float = 0;
 public function new() {}
}
class Bar {
 public var scale:Scale = new Scale();
 public function new() {}
}
class Test {
 static function main() {
  var interp = new Interp();
  var bar = new Bar();
  var state:Dynamic = {health: 1.0};
  interp.variables.set('Math', Math);
  interp.variables.set('barObject', bar);
  interp.variables.set('currentPlayState', state);
  interp.execute(new Parser().parseString(''' + json.dumps(helpers + callbacks +
   "\nfunction getFear() { return totalFear; }\nbar = barObject; fearBarMaxScale = 264 / 50; setFear(50);") + '''));
  if (Math.abs(bar.scale.y - 2.64) > 0.00001)
   throw '50 fear must fill half of the 264px gauge';
  interp.variables.get('playerTwoSing')();
  if (Math.abs(interp.variables.get('getFear')() - 50.15) > 0.00001)
   throw 'an opponent sing must increase fear by the chart amount';
  interp.variables.get('playerOneSing')();
  if (Math.abs(interp.variables.get('getFear')() - 50.05) > 0.00001)
   throw 'a player sing must reduce fear by the chart amount';
  state.health = 1;
  interp.variables.get('setFear')(150);
  if (interp.variables.get('getFear')() != 100 || Math.abs(bar.scale.y - 5.28) > 0.00001)
   throw 'fear must clamp at 100 and the fill must stop at the gauge boundary';
  state.health = 1;
  interp.variables.get('setFear')(95);
  interp.variables.get('playerOneMiss')();
  if (state.health != 0 || interp.variables.get('getFear')() != 100)
   throw 'a miss reaching 100 fear must end the song';
  interp.variables.get('setFear')(-10);
  if (interp.variables.get('getFear')() != 0 || bar.scale.y != 0)
   throw 'fear must clamp at zero';
  state.health = 1;
  interp.variables.get('setFear')(50);
  interp.variables.get('update')(1);
  if (Math.abs(state.health - 0.9) > 0.00001)
   throw 'fear drain must use the chart threshold rate';
 }
}
'''
        self.assertIn('currentPlayState.iconsVertical = true;', script)
        self.assertIn('bar.origin.y = bar.height;', script)
        self.assertIn('bar.y = fearbg.y + 279 - bar.height;', script)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Test.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder,
                 '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-main', 'Test', '--interp'],
                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
