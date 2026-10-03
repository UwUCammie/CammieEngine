"""Codename scripts see the live native receptor animation."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameReceptorAnimationTest(unittest.TestCase):
    def test_get_anim_tracks_native_animation_changes(self):
        source = (ROOT / 'source/Strumline.hx').read_text()
        method = re.search(r'\tpublic function getAnim\(\):String\s+return [^;]+;', source)
        self.assertIsNotNone(method)
        fixture = '''class StrumNote {
 public var animation:Dynamic={curAnim:null};
 public function new() {}
''' + method.group() + '''
}
class Main {
 static function main() {
  var receptor=new StrumNote();
  if(receptor.getAnim()!=null) throw 'missing animation should be null';
  receptor.animation.curAnim={name:'pressed'};
  if(receptor.getAnim()!='pressed') throw 'press was not exposed';
  receptor.animation.curAnim={name:'confirm'};
  if(receptor.getAnim()!='confirm') throw 'confirm was not exposed';
  receptor.animation.curAnim={name:'static'};
  if(receptor.getAnim()!='static') throw 'reset was not exposed';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '-main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
