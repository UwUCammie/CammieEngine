"""Compile the production Codename rating value and update-event models."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameComboRatingTest(unittest.TestCase):
    def test_constructor_threshold_translation_and_event_recycle(self):
        fixture = r'''
class Main {
 static function check(ok:Bool,label:String):Void if(!ok) throw label;
 static function main():Void {
  var low=new CodenameComboRating(.5,'E',0xFF22AA44);
  check(low.percent==.5&&low.rating=='E'&&low.color==0xFF22AA44,
   'constructor field order');
  check(low.maxMisses==Math.POSITIVE_INFINITY,'default misses');
  var capped=new CodenameComboRating(.9,'A',0xFF123456,2);
  check(capped.maxMisses==2,'explicit max misses');
  var nan=new CodenameComboRating(1,'S',0xFF000000,Math.NaN);
  check(nan.maxMisses==Math.POSITIVE_INFINITY,'NaN misses must be unbounded');
  var zero=new CodenameComboRating(0,'F',0,0);
  check(zero.maxMisses==0,'zero misses should remain zero');
  var evt=new CodenameRatingUpdateEvent(capped,low);
  check(evt.rating==capped&&evt.oldRating==low&&!evt.cancelled,'event field order');
  evt.rating=zero;evt.cancel(false);evt.data={previous:true};
  check(evt.stopsPropagation()&&evt.rating==zero,'mutable rating/cancel');
  check(evt.recycle(null,capped)==evt&&evt.rating==null&&evt.oldRating==capped
   &&!evt.cancelled&&!evt.stopsPropagation()&&evt.data.previous==null,
   'recycle must reset inherited cancellation and data');
  Sys.println('combo rating models ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name in ('CodenameGameEvent', 'CodenameComboRating',
                         'CodenameRatingUpdateEvent'):
                (Path(folder) / (name + '.hx')).write_text(
                    (ROOT / 'source' / (name + '.hx')).read_text()
                , newline='\n')
            (Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp',
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('combo rating models ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
