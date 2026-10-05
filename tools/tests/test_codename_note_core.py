"""Run production bound-note effect helpers with mutable source callbacks."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    match = re.search(r'\t(?:@:keep )?(?:public )?function ' + name + r'\(', source)
    if match is None:
        raise AssertionError(name)
    start = match.start()
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameNoteCoreTest(unittest.TestCase):
    def test_mutated_hit_miss_and_cancel_change_real_effects(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        helpers = '\n'.join(method(source, name) for name in (
            'callCodenameSceneNoteEvent', 'applyCodenameNoteHealth',
            'get_codenameAccuracy', 'set_codenameAccuracy',
            'syncCodenameAccuracyHud', 'updateRating',
            'updateCodenameNoteAccuracy', 'updateCodenameNoteLifetime',
            'getNoteStrumline', 'sustain2', 'hitCodenameNote', 'missCodenameNote'))
        sustain_helpers_start = source.index('\tpublic static inline var SUSTAIN_LENGTH_EPSILON:')
        sustain_helpers_end = source.index('\n\t// Keep chart/tween speed intact', sustain_helpers_start)
        helpers += '\n' + source[sustain_helpers_start:sustain_helpers_end]
        self.assertIn('if (hitCodenameNote(note)) return;', source)
        self.assertIn('if (missCodenameNote(direction, note, playMissSound, authoredLine)) return;', source)
        fixture = r'''import CodenameRatingManager.CodenameWindowPreset;

class Judge {public static var wayoffJudge:Float=200;}
class Conductor {
 public static var songPosition:Float=1000;public static var bpm:Float=120;
 public static var crochet:Float=500;public static var stepCrochet:Float=125;
}
class TitleState {public static var soundExt='.ogg';}
class FlxTimer {
 public static var pending:FlxTimer;var callback:FlxTimer->Void;public var resets=0;
 public function new() {}
 public function start(time:Float,callback:FlxTimer->Void):FlxTimer {
  this.callback=callback;FlxTimer.pending=this;return this;
 }
 public function reset(time:Float):Void {resets++;FlxTimer.pending=this;}
 public static function tick():Void {
  var timer=pending;pending=null;if(timer!=null&&timer.callback!=null)timer.callback(timer);
 }
}
class FlxG {
 public static var random={int:function(a:Int,b:Int):Int return 1,
  float:function(a:Float,b:Float):Float return .15};
 public static var sound={play:function(asset:Dynamic,volume:Float):Void {}};
}
class CodenamePaths {
 public function new(root:String) {}
 public function sound(key:String):Dynamic return key;
}
class RuntimeSmokeHarness {
 public static function codenameVisualsEnabled():Bool return false;
 public static function markCodenameHitActorSnapshot(position:Float,line:Int,
  cancelled:Bool,animationCancelled:Bool,actors:Array<Dynamic>):Void {}
}
class NoteGroup {
 public var removed=0;public function new() {}
 public function remove(n:Note,splice:Bool):Void removed++;
}
class Main {
 var nightmareVisionScripts:Dynamic=null;
 var codenameScriptScopes:Array<Dynamic>=[{}];
 var callback:CodenameGameEvent->String->Void;
 var events:Array<String>=[];
 var observed:Array<Dynamic>=[];
 function traceCompatNoteObserver(note:Note,event:CodenameNoteHitEvent,player:Bool):Void {}
 function callAllHScript(name:String,args:Array<Dynamic>,skip:Bool):Void {
  var note:Note=cast args[0];
  if(note!=null&&!note.alive)throw 'observer received dead note';
  observed.push({name:name,rating:note==null?null:note.rating,combo:combo,score:songScore});
 }
 var missCalls=0;
 var playbackRate:Float=1;
 var health:Float=1;var songScore=0;var songScoreDef=0;var trueScore=0;
 var combo=0;var misses=0;var ratingNum=0;var accuracy:Float=0;
 var accuracyPressedNotes:Float=0;var totalAccuracyAmount:Float=0;
 public var codenameAccuracy(get,set):Float;
 var comboRatings:Array<CodenameComboRating>=[new CodenameComboRating(0,'F',0xFF0000)];
 var curRating:CodenameComboRating=null;
 var ratingManager=new CodenameRatingManager();
 var defaultDisplayRating=true;var defaultDisplayCombo=false;var useNoteSplashes=true;
 var muteVocalsOnMiss=true;var camZooming=false;var vocalsVolume:Float=.4;
 var iconP1=new HealthIcon();var iconP2=new HealthIcon();
 var playerStrums=new Strumline();var enemyStrums=new Strumline();var notes=new NoteGroup();
 var codenameStrumlines:Array<Strumline>=[];
 var codenameActors:{bindings:Array<Dynamic>}=null;
 var gf:Character=null;var grpNoteSplashes={add:function(v:Dynamic):Void {}};
 public function new() {codenameStrumlines=[enemyStrums,playerStrums];}
 function getNightmareVisionField(id:Int):Dynamic return null;
 function getCodenameLineStrumline(index:Int):Strumline
  return index < 0 || index >= codenameStrumlines.length ? null : codenameStrumlines[index];
 function callCodenameScript(scope:Dynamic,name:String,args:Array<Dynamic>):Bool {
  events.push('scene:'+name);if(callback!=null)callback(cast args[0],name);return true;
 }
 function callCodenameEvent(name:String,event:CodenameGameEvent):Void {
  if(name!='onRatingUpdate') events.push('all:'+name);
  if(callback!=null)callback(event,name);
 }
 function displayCodenameNoteRating(event:CodenameNoteHitEvent):Void events.push('rating');
 function setAllHaxeVar(name:String,value:Dynamic):Void {}
 function setVocalsVolume(value:Float):Void vocalsVolume=value;
 function spawnCrossFade(actor:Character,note:Note):Void {}
 function codenameSelectedRoot():String return 'selected';
 // Splash selection is exercised against its production helper in the focused
 // test_codename_note_splash suite; this note-core fixture isolates judgement.
 function showCodenameNoteSplash(note:Note,strums:Strumline,direction:Int):Void {}
 function noteMiss(direction:Int,playerOne:Bool,note:Note,playSound:Bool):Void {
  missCalls++;missCodenameNote(direction,note,playSound,note.codenameInputLine);
 }
''' + helpers + r'''
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function near(a:Float,b:Float,label:String):Void if(Math.abs(a-b)>.00001)throw label+':'+a;
 function run():Void {
  ratingManager=new CodenameRatingManager(CodenameWindowPreset.CNE_CLASSIC);
  ratingManager.addRating({name:'epic',window:37.8,accuracy:1,score:350,splash:true});
  check(ratingManager.psychJudgement('epic',1)=='sick','custom highest tier disappeared');
  check(ratingManager.psychJudgement('unfamiliar',.8)=='good','custom middle tier');
  check(ratingManager.psychJudgement('unfamiliar',.5)=='bad','custom low tier');
  check(ratingManager.psychJudgement('unfamiliar',.1)=='shit','custom lowest tier');
  check(ratingManager.psychJudgement('sick',.5)=='sick','authored standard name changed');
  check(ratingManager.psychJudgement('epic',null)=='sick','unscored source observer lookup');
  check(ratingManager.psychJudgement('absent',null)=='unknown','missing rating invented');
  var altered=new CodenameRatingManager();
  altered.addRating({name:'good',accuracy:.6,window:100,score:150});
  check(altered.psychJudgement('custom',.65)=='good','source canonical weights ignored');
  altered.removeRating('sick');
  check(altered.psychJudgement('custom',1)=='sick','removed canonical tier fallback');
  var a=new Character(1), b=new Character(2);
  var line=new CodenameInputLine<Character>(1,1,false,false,false,{},null,null,function(_)return [a,a]);
  var note=new Note(line);note.strumTime=1000;
  line.onHit.add(function(e:Dynamic) {events.push('line:hit');});
  callback=function(e,name) {
   if(name=='onPlayerHit') {var h:CodenameNoteHitEvent=cast e;
    check(h.rating=='epic'&&h.score==350&&h.showSplash&&!h.misses,
     'source rating did not reach mutable hit callback');
    h.score=123;h.accuracy=.5;h.healthGain=.07;h.characters=[b];h.direction=3;
    h.forceAnim=false;h.showRating=false;h.unmuteVocals=false;h.showSplash=false;
    h.strumGlowCancelled=true;
   }
  };
  check(hitCodenameNote(note),'bound hit fell through');
  check(note.wasGoodHit&&note.codenameHitDispatched&&!note.alive&&notes.removed==1,
   'hit mark/delete');
  check(events.join(',')=='scene:onPlayerHit,line:hit,all:onNoteHit,all:onPostNoteHit',
   'hit callback order');
  check(songScore==123&&combo==1&&accuracyPressedNotes==1,'mutated scoring');
  check(observed.length==1&&observed[0].name=='goodNoteHit'&&observed[0].rating=='bad'
   &&observed[0].combo==1&&observed[0].score==123,'post-judgement observer data');
  near(health,1.07,'mutated health');near(accuracy,50,'mutated accuracy');
  check(b.sings==1&&a.sings==0&&b.lastDirection==3&&b.lastForce==false,
   'mutated actor/direction/force');
  near(vocalsVolume,.4,'prevent vocals unmute');
  check(playerStrums.receptor.confirms==0&&playerStrums.splashes==0&&FlxTimer.pending==null,
   'prevent visuals and receptor reset');
  events=[];var cancelled=new Note(line);
  callback=function(e,name) if(name=='onNoteHit') { e.cancel(); (cast e:CodenameNoteHitEvent).preventSustainClip(); }
  check(hitCodenameNote(cancelled)&&songScore==123&&combo==1&&cancelled.destroyed,
   'cancelled hit default effects or deletion');
  check(events[events.length-1]=='all:onPostNoteHit','cancelled hit lost post callback');
  check(cancelled.noSustainClip,'cancelled event lost sustain-clip mutation');
  check(!note.noSustainClip,'ordinary hit disabled sustain clipping');
  check(observed.length==1,'cancelled hit reported as scored');
  var missed=new Note(line);missed.tooLate=true;events=[];
  line.onMiss.add(function(e:Dynamic) events.push('line:miss'));
  callback=function(e,name) if(name=='onPlayerMiss') {
   var m:CodenameNoteMissEvent=cast e;m.score=-17;m.misses=2;
   m.healthGain=-.09;m.preventAnim();m.preventMissSound();m.preventVocalsMute();
   m.preventDeletion();
  };
  check(missCodenameNote(2,missed,true,line),'bound miss fell through');
  check(events.join(',')=='all:onPlayerMiss,line:miss','miss callback order');
  check(songScore==106&&misses==2&&combo==0&&missed.alive,
   'mutated miss bookkeeping/deletion');
  check(observed[1].name=='noteMiss'&&observed[1].combo==0
   &&observed[1].score==106,'miss observer saw stale score');
  near(health,.98,'mutated miss health');near(vocalsVolume,1,'prevent mute');
  check(b.sings==1&&a.sings==0,'prevent miss animation');
  events=[];var cpu=new CodenameInputLine<Character>(0,0,false,false,false,{},null,null,
   function(_)return [a]);
  var cpuNote=new Note(cpu);cpuNote.mustPress=false;
  callback=null;check(hitCodenameNote(cpuNote),'CPU hit');
  check(songScore==106&&combo==0&&events[0]=='scene:onDadHit','CPU score or hook');
  check(observed[2].name=='opponentNoteHit','CPU hit reported to player observer');
  events=[];var canceledMiss=new Note(line);
  callback=function(e,name) if(name=='onPlayerMiss') e.cancel();
  check(missCodenameNote(1,canceledMiss,true,line)&&misses==2&&canceledMiss.alive,
   'cancelled miss default effects');
  var retained=new Note(line);retained.tooLate=true;events=[];missCalls=0;
  check(!updateCodenameNoteLifetime(retained)&&!updateCodenameNoteLifetime(retained)
   &&retained.alive&&missCalls==2,
   'cancelled tooLate miss should repeat on each update');
  var held=new Note(line);held.wasGoodHit=true;held.codenameHitDispatched=true;
  held.isSustainNote=true;held.strumTime=500;held.sustainLength=100;
  check(updateCodenameNoteLifetime(held)&&held.destroyed&&notes.removed==4,
   'accepted sustain was not retired after end time');
  var freshAutoTail=new Note(line);freshAutoTail.wasGoodHit=true;
  freshAutoTail.isSustainNote=true;freshAutoTail.strumTime=500;freshAutoTail.sustainLength=100;
  check(!updateCodenameNoteLifetime(freshAutoTail)&&freshAutoTail.alive,
   'autoplay sustain retired before hit callback');
  callback=null;check(hitCodenameNote(freshAutoTail,true)&&freshAutoTail.codenameHitDispatched,
   'autoplay sustain did not dispatch once');
  check(observed[observed.length-1].rating=='unknown','sustain counted as a judged head');
  check(updateCodenameNoteLifetime(freshAutoTail)&&freshAutoTail.destroyed,
   'autoplay sustain did not retire after callback');
  var keptTap=new Note(line);keptTap.wasGoodHit=true;keptTap.tooLate=true;
  check(!updateCodenameNoteLifetime(keptTap)&&keptTap.alive&&missCalls==2,
   'retained accepted tap was missed again');
  ratingManager.addRating({name:'break',window:5,score:100,breaksCombo:true});
  var breaking=new Note(line);callback=null;
  check(hitCodenameNote(breaking)&&combo==0&&misses==3,
   'source breaksCombo rating did not reset combo and count a miss');
  FlxTimer.pending=null;var glowing=new Note(line);glowing.noteData=3;callback=null;
  check(hitCodenameNote(glowing),'Codename glow hit');
  check(playerStrums.receptor.confirms==1&&FlxTimer.pending!=null,
   'Codename confirm did not schedule the shared receptor reset');
  var timer=FlxTimer.pending;FlxTimer.tick();
  check(timer.resets==1&&playerStrums.receptor.staticRestores==0,
   'confirm reset ran before its animation finished');
  playerStrums.receptor.animation.curAnim.finished=true;FlxTimer.tick();
  check(playerStrums.receptor.staticRestores==1
   &&playerStrums.receptor.lastAnimation=='static'&&FlxTimer.pending==null,
   'finished Codename confirm did not return to static');
 }
 public static function main():Void {new Main().run();Sys.println('note core ok');}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            temp = Path(folder)
            for name in ('CodenameGameEvent', 'CodenameNoteHitEvent',
                         'CodenameNoteMissEvent', 'CodenameInputLine',
                         'CodenameStrumlineNoteCollection',
                         'CodenameLineNoteQuery', 'CodenameLineNoteIndex',
                         'CodenameStrumlineLayout', 'CodenameComboRating', 'CodenameRatingUpdateEvent',
                         'CodenameNoteTypeCompat', 'CodenameRatingManager'):
                (temp / (name + '.hx')).write_text((ROOT / 'source' / (name + '.hx')).read_text(), newline='\n')
            (temp / 'Main.hx').write_text(fixture, newline='\n')
            (temp / 'Character.hx').write_text('''class Character {
 public var id:Int; public var sings=0; public var lastDirection=-1;
 public var lastForce:Null<Bool>=null; public var codenameLiveDefinition:Dynamic={};
 public var stunned=false; public var animation={exists:function(name:String):Bool return false};
 public var visible=true;
 public function new(id:Int) this.id=id;
 public function codenamePlayAnim(n:String,f:Bool,c:Dynamic):Void {}
 public function playAnim(n:String,f:Bool):Void {}
 public function codenamePlaySingAnim(d:Int,s:String,c:Dynamic,f:Null<Bool>):Void
  {sings++;lastDirection=d;lastForce=f;}
 public function sing(d:Int,m:Bool):Void {sings++;lastDirection=d;}
}''', newline='\n')
            (temp / 'Note.hx').write_text('''class Note {
 public var codenameInputLine:CodenameInputLine<Character>;public var alive=true;
 public var nightmareVisionTypeRuntime:Dynamic=null;
 public var nightmareVisionSustainEnd=false;public var sourcePlayfieldIndex=-1;
 public var wasGoodHit=false;public var codenameHitDispatched=false;
 public var canBeHit=true;public var tooLate=false;public var rating='miss';
 public var isSustainNote=false;public var sourceKind:String=null;
 public var animSuffix:String='';public var codenameAuthoredAnimSuffix:String='';
 public var noteData=0;public var strumTime:Float=1000;public var prevNote:Note=null;
 public var nightmareVisionTailState:Dynamic=null;
 public var sustainLength:Float=0;
 public var mustPress=true;public var dontStrum=false;public var destroyed=false;
 public var noSustainClip=false;
 public function new(line:CodenameInputLine<Character>) codenameInputLine=line;
 public function kill():Void alive=false;public function destroy():Void destroyed=true;
}''', newline='\n')
            (temp / 'HealthIcon.hx').write_text('class HealthIcon {public function new() {}}', newline='\n')
            (temp / 'Strumline.hx').write_text('''class Strumline {
 public var receptor=new Strumline.StrumNote(3);public var splashes=0;
 public function new() {}
 public function forEachReceptor(f:Strumline.StrumNote->Void):Void f(receptor);
 public function doSplash(direction:Int):Dynamic {splashes++;return {};}
}
class StrumNote {public var ID:Int;public var confirms=0;public var confirmationGeneration:Int=0;
 public var resetAnim:Float=0;public var coyoteTime:Float=0;
 public var exists=true;public var animation:Dynamic={curAnim:{name:'static',finished:false}};
 public var staticRestores=0;public var lastAnimation:String='static';
 public function new(id:Int) ID=id;
 public function playConfirm(sustain:Bool,force:Bool):Void {
  confirms++;confirmationGeneration++;animation.curAnim.name='confirm';animation.curAnim.finished=false;lastAnimation='confirm';
 }
 public function playAnim(name:String,force:Bool):Void {
  lastAnimation=name;animation.curAnim.name=name;animation.curAnim.finished=false;
  if(name=='static')staticRestores++;
 }
}''', newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', str(ROOT / 'tools/tests/haxe_stubs'),
                '-cp', folder, '-main', 'Main', '--interp',
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('note core ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
