"""Run production PlayState rating methods against mutable donor-style events."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    found = re.search(r'\t(?:@:keep )?(?:public )?function ' + name + r'\(', source)
    if found is None:
        raise AssertionError(name)
    start = found.start()
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameRatingRuntimeTest(unittest.TestCase):
    def test_accuracy_selection_mutation_cancellation_and_visit_isolation(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        methods = '\n'.join(method(source, name) for name in (
            'get_codenameAccuracy', 'set_codenameAccuracy',
            'syncCodenameAccuracyHud', 'updateRating', 'updateCodenameNoteAccuracy',
        ))
        fixture = r'''
class Main {
 public var accuracyPressedNotes:Float=0;
 public var totalAccuracyAmount:Float=0;
 public var codenameAccuracy(get,set):Float;
 public var comboRatings:Array<CodenameComboRating>=[
  new CodenameComboRating(0,'F',0xFF4444),
  new CodenameComboRating(.8,'C',0xFFFFFF)
 ];
 public var curRating:CodenameComboRating=null;
 public var misses=0;
 public var accuracy:Float=0;
 public var hudWrites=0;
 public var traceOrder:Array<String>=[];
 public var callback:CodenameRatingUpdateEvent->String->Void=null;
 public function new() {}
 function setAllHaxeVar(name:String,value:Dynamic):Void {
  if(name!='accuracy'||value!=accuracy)throw 'HUD sync field';hudWrites++;
 }
 function callCodenameEvent(name:String,event:CodenameGameEvent):Void {
  if(name!='onRatingUpdate')throw name;
  traceOrder.push('scene');
  if(callback!=null)callback(cast event,'scene');
  traceOrder.push('character');
  if(callback!=null)callback(cast event,'character');
 }
''' + methods + r'''
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function near(a:Float,b:Float,label:String):Void if(Math.abs(a-b)>.00001)throw label+':'+a;
 function run():Void {
  check(codenameAccuracy==-1,'no-notes donor accuracy');
  syncCodenameAccuracyHud();near(accuracy,0,'no-notes HUD clamp');
  var returned=set_codenameAccuracy(.8);
  near(returned,.8,'setter returns total amount');
  near(accuracyPressedNotes,1,'setter denominator minimum');
  near(codenameAccuracy,.8,'setter ratio');near(accuracy,80,'native HUD percent');
  var before=hudWrites;
  updateCodenameNoteAccuracy(.6);
  near(accuracyPressedNotes,2,'note denominator');
  near(totalAccuracyAmount,1.4,'note amount');
  near(codenameAccuracy,.7,'note ratio');near(accuracy,70,'native percent');
  check(hudWrites==before+1&&curRating.rating=='F','accuracy update rating/HUD');
  accuracyPressedNotes=3;
  near(set_codenameAccuracy(.25),.75,'setter return uses existing denominator');
  var low=new CodenameComboRating(0,'Low',0);
  var highLimited=new CodenameComboRating(.8,'Limited',0,0);
  var middle=new CodenameComboRating(.5,'Middle',0);
  var middleTie=new CodenameComboRating(.5,'Tie',0);
  comboRatings=[highLimited,middle,low,middleTie];
  set_codenameAccuracy(.7);misses=1;updateRating();
  check(curRating==middle,'unsorted thresholds/maxMisses/tie preference');
  misses=0;set_codenameAccuracy(.85);updateRating();
  check(curRating==highLimited,'eligible highest threshold');
  var custom=new CodenameComboRating(.2,'Custom',0);
  traceOrder=[];
  callback=function(event,scope) {
   check(event.oldRating==highLimited,'old rating snapshot');
   if(scope=='scene')event.rating=custom;
   else check(event.rating==custom,'character did not observe scene mutation');
  };
  updateRating();
  check(curRating==custom&&traceOrder.join(',')=='scene,character',
   'mutable scene/character event');
  callback=function(event,scope) if(scope=='scene') {event.rating=low;event.cancel();};
  updateRating();check(curRating==custom,'cancel replaced previous rating');
  callback=null;comboRatings=[];updateRating();
  check(curRating==null,'empty rating list should choose null');
  comboRatings=null;updateRating();check(curRating==null,'null list should choose null');
  var other=new Main();
  check(other.codenameAccuracy==-1&&other.curRating==null&&other.misses==0
   &&other.comboRatings!=comboRatings,'visit state leaked');
  other.updateCodenameNoteAccuracy(1);
  check(other.curRating.rating=='C'&&curRating==null&&accuracyPressedNotes==3,
   'second visit changed first visit');
 }
 public static function main():Void {new Main().run();Sys.println('rating runtime ok');}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            temp = Path(folder)
            for name in ('CodenameGameEvent', 'CodenameComboRating',
                         'CodenameRatingUpdateEvent'):
                (temp / (name + '.hx')).write_text((ROOT / 'source' / (name + '.hx')).read_text(), newline='\n')
            (temp / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp',
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('rating runtime ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
