from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class StrumlineCompatTest(unittest.TestCase):
    def test_legacy_script_switches_each_side_and_replaces_all_receptors(self):
        fixture = ROOT / 'assets/data/instigation/modchart.hscript'
        if not fixture.is_file():
            self.skipTest(f'mounted Instigation modchart fixture unavailable: {fixture}')
        source = (ROOT / 'source/Strumline.hx').read_text()
        change = source[source.index('\tpublic function changeType('):source.index('\n\tpublic function transIn(')]
        play = (ROOT / 'source/PlayState.hx').read_text()
        api = play[play.index('\t@:keep public function generateStaticArrows('):play.index('\n\t/*private function generateStaticArrows(')]
        fixture = '''class FlxTween {public static var cancelled=0;public static function cancelTweensOf(s:Dynamic){cancelled++;}}
class Judgement {public static var uiJson:Dynamic={normal:{uses:'normal'},fatal:{uses:'fatal'}};}
class Note {public static var NOTE_AMOUNT=4;public static var swagWidth=112;}
class NoteKeys {public function new(s:String){} public function newKey(s:String){}}
class StrumNote {
 public var parentLine:Dynamic;public var destroyed=false;public var pack:String;
 public function new(x:Float,y:Float,id:Int,type:String,key:NoteKeys){pack=type;}
 public function destroy(){destroyed=true;}
}
class NoteSplash {public var destroyed=false;public function new(x:Int,y:Int,n:Int,t:String){}public function destroy(){destroyed=true;}}
class FlxTypedGroup<T> {
 public var members:Array<T>=[];public function new(){}public function add(s:T){members.push(s);} public function clear(){members=[];}
}
class Line {
 public var type='normal';public var currentKey:NoteKeys;public var noteSplashes:FlxTypedGroup<NoteSplash>;
 public var members:Array<StrumNote>=[];public var length(get,never):Int;public var transitions=0;
 function get_length(){return members.length;}public function new(){changeType();}
 function add(s:StrumNote){members.push(s);}function remove(s:StrumNote,splice:Bool){members.remove(s);}
 function transIn(){transitions++;}
''' + change + '''
}
class CompatTest {
 var playerStrums=new Line();var enemyStrums=new Line();public function new(){}
''' + api + '''
 static function main(){
  var state=new CompatTest();var old=state.enemyStrums.members.copy();var splashes=state.enemyStrums.noteSplashes;
  state.generateStaticArrows(0,'fatal',true);
  if(state.enemyStrums.type!='fatal'||state.playerStrums.type!='normal'||state.enemyStrums.members.length!=4)throw 'Wrong side or duplicate receptors';
  for(s in old)if(!s.destroyed)throw 'Old receptor survived';
  if(FlxTween.cancelled!=4||state.enemyStrums.noteSplashes!=splashes||state.enemyStrums.transitions!=1)throw 'Unsafe replacement';
  state.generateStaticArrows(1,'fatal',false);
  if(state.playerStrums.type!='fatal'||state.playerStrums.transitions!=0)throw 'Later player switch failed';
  state.generateStaticArrows(0,'missing',true);
  if(state.enemyStrums.type!='fatal')throw 'Unknown pack damaged strumline';
 }
}
'''
        script = fixture.read_text()
        self.assertIn('currentPlayState.generateStaticArrows(0, "fatal", true)', script)
        self.assertIn('currentPlayState.generateStaticArrows(1, "fatal", false)', script)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'CompatTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'CompatTest', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hold_timer_handles_replaced_or_unanimated_receptors(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        method = play[play.index('\tfunction sustain2('):play.index('\n\tfunction promoteCompatEndingOverlay(')]
        method = method.replace('Strumline.StrumNote', 'Dynamic').replace('note:Note', 'note:Dynamic')
        strumline = (ROOT / 'source/Strumline.hx').read_text()
        self.assertIn("if (anim == 'confirm' || anim == 'confirmHold')\n\t\t\tconfirmationGeneration++", strumline)
        helper_start = play.index('\tpublic static inline var SUSTAIN_LENGTH_EPSILON:')
        helper_end = play.index('\n\t// Keep chart/tween speed intact', helper_start)
        sustain_helper = play[helper_start:helper_end]
        fixture = '''class Conductor {public static var bpm=120.;public static var crochet=500.;public static var stepCrochet=125.;}
class FlxTimer {
 public static var last:FlxTimer;public var callback:FlxTimer->Void;public var resets=0;public var delay=0.;
 public function new(){}
 public function start(t:Float,f:FlxTimer->Void){delay=t;callback=f;last=this;return this;}
 public function reset(t:Float){resets++;delay=t;}
 public function fire():Void if(callback!=null)callback(this);
}
class TimerTest {
 function isPsychReceptorNote(_note:Dynamic):Bool return false;
 var playbackRate:Float=1;
 public function new(){}
 function getNightmareVisionField(_strum:Int):Dynamic
  return {autoPlayed:false,holdDropLeniency:0.15};
 function nightmareVisionFieldForNote(note:Dynamic):Dynamic
  return note == null ? null : getNightmareVisionField(note.sourcePlayfieldIndex);
''' + sustain_helper + method + '''
 static function main(){
  var state=new TimerTest();var note:Dynamic={sustainLength:500.,isSustainNote:false,
   nightmareVisionTypeRuntime:null,nightmareVisionSustainEnd:false};
  var restored=0;
  var spr:Dynamic={exists:true,resetAnim:0.,coyoteTime:0.,holding:false,confirmationGeneration:0,
   animation:{curAnim:{name:'confirm',finished:false}},playAnim:function(n:String,f:Bool){restored++;}};
  state.sustain2(0,spr,note);var timer=FlxTimer.last;
  timer.fire();
  if(timer.resets!=1||restored!=0)throw 'Must wait for confirmation animation';
  spr.animation.curAnim.finished=true;timer.fire();
  if(restored!=1)throw 'Must restore static after confirmation';
  spr.animation.curAnim=null;timer.fire();
  spr.animation=null;timer.fire();
  spr.exists=false;timer.fire();
  if(timer.resets!=1||restored!=1)throw 'Invalid receptor must end timer';

  // A fractional hold may generate its final tail after the head's authored
  // duration. Keep the head deadline past its rounded last segment.
  var holdState=new TimerTest();var holdRestored=0;
  var holdSpr:Dynamic={exists:true,resetAnim:0.,coyoteTime:0.,holding:false,confirmationGeneration:1,
   animation:{curAnim:{name:'confirm',finished:false}},playAnim:function(n:String,f:Bool){holdRestored++;}};
  var head:Dynamic={sustainLength:385.,isSustainNote:false,strumTime:0.,prevNote:null,
   nightmareVisionTypeRuntime:null,nightmareVisionSustainEnd:false};
  holdState.sustain2(0,holdSpr,head);var headTimer=FlxTimer.last;
  if(headTimer.delay<=0.5)throw 'Head timer ended before the rounded final piece';
  holdSpr.confirmationGeneration++;
  holdSpr.animation.curAnim={name:'confirmHold',finished:false}; // final tail confirms
  var tail:Dynamic={sustainLength:0.,isSustainNote:true,strumTime:500.,prevNote:{strumTime:375.},
   nightmareVisionTypeRuntime:null,nightmareVisionSustainEnd:false};
  holdState.sustain2(0,holdSpr,tail);var tailTimer=FlxTimer.last;
  if(tailTimer.delay<0.2)throw 'Tail reset must wait through its next-piece interval';
  headTimer.fire();
  if(holdRestored!=0)throw 'Stale head timer reset the newer tail confirm';
  tailTimer.fire();
  if(tailTimer.resets!=1||holdRestored!=0)throw 'Tail reset ran before confirmHold finished';
  holdSpr.animation.curAnim.finished=true;tailTimer.fire();
  if(holdRestored!=1)throw 'Final sustain confirmation stayed glowing';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'TimerTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'TimerTest', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
