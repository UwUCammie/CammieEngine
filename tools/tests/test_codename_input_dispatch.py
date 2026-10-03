"""Execute the real input selector with independent authored line ownership."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    start = source.index('function ' + name + '(')
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if not depth:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameInputDispatchTest(unittest.TestCase):
    def test_input_candidates_are_owned_and_callbacks_control_real_hits(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        methods = '\n'.join(method(source, name) for name in (
            'noteBelongsToInputLine', 'getInputStrumline', 'keyShit'))
        fixture = r'''
using StringTools;
class Character {
 public var stunned=false; public var holdTimer:Float=0;
 public var singPriority:Array<String>=[]; public var locks=0;
 public function new() {}
 public function lockCodenameAnimationForInput():Void locks++;
 public static function animationName(c:Character):String return "idle";
 public function dance():Void {} public function playAnim(n:String,f:Bool):Void {}
 public function sing(n:Int):Void {}
}
class Note {
 public var codenameInputLine:CodenameInputLine<Character>;
 public var mustPress=true; public var canBeHit=true; public var tooLate=false;
 public var wasGoodHit=false; public var isLiftNote=false; public var isSustainNote=false;
 public var blockHit=false;
 public var alive=true; public var destroyed=false; public var noteData=0;
 public var strumTime:Float=1000;
 public function new(line:CodenameInputLine<Character>,time:Float=1000) {codenameInputLine=line;strumTime=time;}
 public function kill():Void alive=false; public function destroy():Void destroyed=true;
}
class Notes {
 public var members:Array<Note>=[]; public function new() {}
 public function forEachAlive(f:Note->Void):Void for(n in members.copy()) if(n.alive) f(n);
 public function remove(n:Note,splice:Bool):Void members.remove(n);
}
class FlxG { public static var log={add:function(s:String):Void {}}; }
class FlxColor { public static var WHITE=0; public static var RED=1; }
class Conductor { public static var stepCrochet:Float=125; public static var songPosition:Float=1000; }
class Ratings { public static function CalculateRating(t:Float):String return 'sick'; }
class OptionsHandler { public static var options={useCustomInput:true,singYourHeartOut:false}; }
class Main {
 var controls:Dynamic; var controlsPlayerTwo:Dynamic;
 var codenameInputLines:Array<CodenameInputLine<Character>>=[];
 var nightmareVisionScripts:Dynamic=null;
 var boyfriend=new Character(); var dad=new Character();
 var notes=new Notes(); var soloMode=false; var generatedMusic=true; var demoMode=false;
 var mashViolations=0; var scoreTxt={color:0}; var useCustomInput=true; public var ghostTapping=true;
 var currentKey={getSing:function(i:Int):String return 'singLEFT'};
 var playerStrums=new Strumline(); var enemyStrums=new Strumline();
 var codenameStrumlines:Array<Strumline>=[];
 var codenameCharacterScopes:Array<Dynamic>=[];
 var callback:CodenameInputEvent->Void; var posts=0; var hits:Array<Note>=[]; var misses:Array<Dynamic>=[];
 function new() {
  codenameStrumlines=[playerStrums,enemyStrums];
  controls={};
  for(letter in ['A','B','C','D','E','F','G','H','I']) for(suffix in ['','_P','_R'])
   Reflect.setField(controls,'CTRL'+letter+suffix,false);
  controlsPlayerTwo=controls;
 }
 function getOpponentSinger():Character return dad;
 function getNightmareVisionField(index:Int):Dynamic return {canInput:function() return true};
 function getCodenameLineStrumline(index:Int):Strumline
  return index < 0 || index >= codenameStrumlines.length ? null : codenameStrumlines[index];
 function codenameVisualInputOwner(line:CodenameInputLine<Character>):Bool return false;
 function callCodenameEvent(name:String,e:CodenameGameEvent):Void callback(cast e);
 function callCodenameScripts(name:String,args:Array<Dynamic>):Void {if(name!='onPostInputUpdate')throw name;posts++;}
 function goodNoteHit(n:Note,side:Bool):Void {if(!n.alive||n.wasGoodHit)throw 'double hit';hits.push(n);n.wasGoodHit=true;n.alive=false;}
 function noteMiss(d:Int,side:Bool,?n:Note,?sound:Bool=true,?line:CodenameInputLine<Character>):Void misses.push({lane:d,line:line});
 static function check(ok:Bool,s:String):Void if(!ok)throw s;
''' + methods + r'''
 static function main():Void {
  var state=new Main(); var actorA=new Character(), actorB=new Character();
  var inherited=function() return state.ghostTapping;
  var a=new CodenameInputLine<Character>(0,1,false,false,false,state.controls,null,null,function(_)return [actorA],inherited);
  var b=new CodenameInputLine<Character>(1,1,false,false,false,state.controls,null,null,function(_)return [actorB],inherited);
  state.codenameInputLines=[a,b];
  var first=new Note(a),other=new Note(b),duplicate=new Note(a,1002),later=new Note(a,1005);
  state.notes.members=[first,other,duplicate,later];
  state.callback=function(e) {check(e.pressed.length==4,'native nine-key array leaked'); e.pressed=[true];e.justPressed=[true];};
  state.keyShit(true,a);
  check(state.hits.length==1&&state.hits[0]==first,'first line hit');
  check(duplicate.destroyed&&!other.destroyed&&!later.destroyed,'cross-line duplicate or wide tolerance');
  check(actorA.locks==1&&actorB.locks==0,'lock leaked actor line');
  state.keyShit(true,b);
  check(state.hits.length==2&&state.hits[1]==other,'simultaneous second line lost');
  check(state.posts==2,'post-input dispatch');
  var cancelled=new Note(b);state.notes.members=[cancelled];
  state.callback=function(e){e.pressed=[true];e.justPressed=[true];e.cancel();};
  state.keyShit(true,b);
  check(state.hits.length==2&&actorB.locks==1&&state.posts==2,'cancelled input acted');
  state.callback=function(e){e.pressed=null;e.justPressed=null;e.justReleased=null;};
  state.keyShit(true,b);check(state.posts==3&&state.hits.length==2,'null arrays not empty');
  OptionsHandler.options.useCustomInput=false;
  state.ghostTapping=false;
  state.callback=function(e){e.pressed=[true,true];e.justPressed=[true,true];};
  state.keyShit(true,b);
  check(state.hits.length==3&&state.hits[2]==cancelled,'empty extra lane suppressed valid hit');
  check(state.misses.length==1&&state.misses[0].lane==1&&state.misses[0].line==b,'ghost miss not per line/lane');
  // The same empty lane is judged independently for each authored line.
  a.ghostTapping=true;
  var validB=new Note(b);state.notes.members=[validB];
  state.callback=function(e){e.pressed=[true,true];e.justPressed=[true,true];};
  state.keyShit(true,a);
  state.keyShit(true,b);
  check(validB.wasGoodHit&&state.misses.length==2&&state.misses[1].line==b
   &&state.misses[1].lane==1,'line override suppressed sibling hit or ghost miss');
  state.notes.members=[];
  state.callback=function(e){e.pressed=[false,true];e.justPressed=[false,true];};
  b.ghostTapping=true;
  state.keyShit(true,b);
  check(state.misses.length==2,'enabled line still ghost missed');
  OptionsHandler.options.useCustomInput=true;
  state.ghostTapping=true;
  b.ghostTapping=false;
  state.keyShit(true,b);
  check(state.misses.length==3&&state.misses[2].line==b,
   'line override did not beat inherited enabled setting');
  b.ghostTapping=null;
  state.keyShit(true,b);
  check(state.misses.length==3,'cleared override did not inherit setting');
  var heldA=new Note(a),heldB=new Note(b);heldA.isSustainNote=true;heldB.isSustainNote=true;
  state.notes.members=[heldA,heldB];
  state.callback=function(e){e.pressed=[true];e.justPressed=[];};
  state.keyShit(true,a);
  check(heldA.wasGoodHit&&!heldB.wasGoodHit,'sustain ownership');
  var liftA=new Note(a),liftB=new Note(b);liftA.isLiftNote=true;liftB.isLiftNote=true;
  state.notes.members=[liftA,liftB];
  state.callback=function(e){e.pressed=[];e.justPressed=[];e.justReleased=[true];};
  state.keyShit(true,b);check(!liftA.wasGoodHit&&liftB.wasGoodHit,'release ownership');
  var blocked=new Note(a);blocked.blockHit=true;state.notes.members=[blocked];
  state.callback=function(e){e.pressed=[true];e.justPressed=[true];e.justReleased=[];};
  state.keyShit(true,a);
  check(!blocked.wasGoodHit,'Psych blockHit was ignored by player input');
  blocked.blockHit=false;
  state.keyShit(true,a);
  check(blocked.wasGoodHit,'unblocked note did not become hittable');
  var native=new Note(null);var bound=new Note(a);state.notes.members=[native,bound];
  Reflect.setField(state.controls,'CTRLA_P',true);
  state.keyShit(true);check(native.wasGoodHit&&!bound.wasGoodHit,'native fallback consumed bound note');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            folder = Path(work)
            (folder / 'Main.hx').write_text(fixture, newline='\n')
            (folder / 'Strumline.hx').write_text('''class StrumNote {
 public var ID=0; public var animation:Dynamic=null;
 public function playAnim(s:String):Void {}
}
class Strumline {
 public function new() {}
 public function endNoteHoldCoverAtLane(i:Int):Void {}
 public function forEachReceptor(f:StrumNote->Void):Void {}
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'tools/tests/haxe_stubs'), '-cp', str(ROOT / 'source'),
                                     '-cp', str(folder), '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
