"""Psych RGB toggles must reach native/accessor-backed receptor properties."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PsychStrumRGBToggleTest(unittest.TestCase):
    def test_property_toggle_calls_setter_and_preserves_unrelated_receptors(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        method = source.split('\tfunction compatSetStrumLineRGBShader(', 1)[1].split(
            '\n\tfunction compatUpdateCameraAngle(', 1)[0]
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text('''
class Receptor {
 public var useRGBShader(get,set):Bool;
 var enabled:Bool = true;
 public var refreshes:Int = 0;
 public function new() {}
 function get_useRGBShader():Bool return enabled;
 function set_useRGBShader(value:Bool):Bool {
  refreshes++;
  return enabled = value;
 }
}
class Host {
 public var enemyStrums:{members:Array<Dynamic>};
 public var playerStrums:{members:Array<Dynamic>};
 public var strumLineNotes:{members:Array<Dynamic>};
 public function new() {}
 public function compatSetStrumLineRGBShader(''' + method + '''
}
class Main {
 static function main() {
  var host = new Host();
  host.compatSetStrumLineRGBShader(false); // Missing group is permitted.
  var first = new Receptor();
  var second = new Receptor();
  second.useRGBShader = false;
  var unrelated = {visible:true};
  var legacy = new Receptor();
  host.strumLineNotes = {members:[cast legacy]};
  host.enemyStrums = {members:[cast first, null, cast unrelated]};
  host.playerStrums = {members:[cast second]};
  if (Reflect.hasField(first, 'useRGBShader')) throw 'fixture needs an accessor property';
  host.compatSetStrumLineRGBShader(false);
  if (first.useRGBShader || second.useRGBShader || first.refreshes != 1 || second.refreshes != 2)
   throw 'RGB disable did not reach both setters';
  host.compatSetStrumLineRGBShader(true);
  if (!first.useRGBShader || !second.useRGBShader || first.refreshes != 2 || second.refreshes != 3)
   throw 'RGB re-enable lost false property values';
  if (Reflect.hasField(unrelated, 'useRGBShader') || !unrelated.visible)
   throw 'unrelated receptor acquired a foreign field';
  if (legacy.refreshes != 0) throw 'unused legacy group was toggled';
  host.enemyStrums = null;
  host.compatSetStrumLineRGBShader(false);
  if (second.useRGBShader || second.refreshes != 4)
   throw 'missing opponent group prevented player toggle';
 }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work),
                                     '--main', 'Main', '--interp'], cwd=work,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
