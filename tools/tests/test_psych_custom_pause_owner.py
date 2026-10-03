"""Execute production custom-pause owner methods with deferred substate opens."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from test_psych_camera_alias import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychCustomPauseOwnerTest(unittest.TestCase):
    def test_cancelled_pause_preserves_script_opened_substate(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\t\tif (controls.PAUSE && startedCountdown && canPause')
        end = source.index('\n\t\tvar canShowKeys', start)
        gate = source[start:end]
        fixture = r'''
class NightmareVisionScriptGroup {public static inline var STOP_FUNC:Int=1;}
class EngineCompat {
 public static function hxcLifecyclePayload(s:String):Dynamic return {};
 public static function anyFunctionStop(values:Array<Dynamic>)return values.indexOf("stop")>=0;
}
class CoolUtil {public static function pauseTween(x:Dynamic){} public static function resumeTween(x:Dynamic){}}
class Actor {public function new(){}public function getScreenPosition()return {x:0,y:0};}
class PauseSubState {public function new(x:Int,y:Int,camera:Dynamic){}}
class CodenameGameEvent {public function new(){}}
class Main {
 var controls={PAUSE:true};var startedCountdown=true;var canPause=true;
 var persistentUpdate=true;var persistentDraw=true;var paused=false;
 var compatCustomSubstateOpen=false;var compatCustomSubstatePausesGame=false;
 var curCamPos:Dynamic;var curCamZoom:Dynamic;var camHUD:Dynamic;var boyfriend=new Actor();
 var vSliceScrollTweens:Array<Dynamic>=[];
 var behavior=0;var nativeOpens=0;var nmvStop=false;
 var sourceBatch:Dynamic = {};var postDispatches=0;
 function dispatchNightmareVisionUpdatePost(batch:Dynamic){postDispatches++;}
 function callNightmareVision(name:String,args:Array<Dynamic>):Int return nmvStop ? 1 : 0;
 public function new(){}
 function setAllHaxeVar(s:String,v:Dynamic){}
 function callCodenameEvent(name:String,e:CodenameGameEvent){}
 function openSubState(s:PauseSubState){nativeOpens++;}
 function callAllHScript(name:String,args:Array<Dynamic>,skip:Bool,results:Array<Dynamic>,events:Array<Dynamic>){
  if(behavior==0)return;
  results.push("stop");
  if(behavior>=2){compatCustomSubstateOpen=true;compatCustomSubstatePausesGame=behavior==2;
   paused=compatCustomSubstatePausesGame;persistentUpdate=!paused;persistentDraw=true;}
 }
 function run(){ GATE }
 static function check(ok:Bool,why:String)if(!ok)throw why;
 static function main(){
  var s=new Main();s.nmvStop=true;s.run();check(s.nativeOpens==0&&!s.paused&&s.persistentUpdate,'NMV cancellation changed pause state');
  s=new Main();s.run();check(s.nativeOpens==1&&s.paused&&!s.persistentUpdate,'native pause');
  s=new Main();s.behavior=1;s.run();check(s.nativeOpens==0&&!s.paused&&s.persistentUpdate,'consumed press');
  s=new Main();s.behavior=2;s.run();check(s.nativeOpens==0&&s.paused&&!s.persistentUpdate&&s.persistentDraw,'custom pause overwritten');check(s.postDispatches==1,'custom pause lost paired source post');
  s=new Main();s.behavior=3;s.run();check(s.nativeOpens==0&&!s.paused&&s.persistentUpdate&&s.persistentDraw,'nonpausing overlay hidden');check(s.postDispatches==1,'overlay lost paired source post');
 }
}
'''.replace('GATE', gate)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '--run', 'Main'], cwd=ROOT, capture_output=True,
                                    text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pause_resume_pending_cancel_and_task_ownership(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        methods = '\n'.join(extract_method(source, 'function ' + name + '(') for name in (
            'pausePsychCustomTimeline', 'resumePsychCustomTimeline',
            'compatOpenCustomSubstate', 'compatCloseCustomSubstate',
            'psychCustomSubstateCreate', 'psychCustomSubstateCreatePost',
            'psychCustomSubstateUpdate', 'psychCustomSubstateUpdatePost',
            'psychCustomSubstateDestroy'))
        fixture = r'''
class Task {public var active=true; public var finished=false; public function new() {}}
class Manager<T> {public var tasks:Array<T>=[]; public function new() {}
 public function forEach(f:T->Void) for(t in tasks)f(t);}
class FlxTimer extends Task {public static var globalManager=new Manager<FlxTimer>();}
class FlxTween extends Task {public static var globalManager=new Manager<FlxTween>();}
class Sound {public var paused=false;public function new(){}public function pause()paused=true;}
class FlxG {public static var sound={music:new Sound()};}
class PsychCustomSubstate {
 public var lifecycleCreated=false;public var pausesGame:Bool;public var customName:String;
 public var canceled=false;
 public function new(owner:Main,name:String,pauseGame:Bool){customName=name;pausesGame=pauseGame;}
 public function cancelBeforeCreate(){canceled=true;}
}
class HostBase {
 public var subState:PsychCustomSubstate;
 public var requested:PsychCustomSubstate;
 public function new(){}
 public function openSubState(s:PsychCustomSubstate){requested=s;}
}
class Main extends HostBase {
 var compatCustomSubstate:PsychCustomSubstate;
 var compatCustomSubstateOpen=false;
 var compatCustomSubstateName='';
 var compatCustomSubstatePausesGame=false;
 var compatCustomPausedTimers:Array<FlxTimer>=[];
 var compatCustomPausedTweens:Array<FlxTween>=[];
 var vSliceScrollTweens:Array<FlxTween>=[];
 var compatCustomPausedSnapshot=false;
 var paused=false; var persistentUpdate=true;var persistentDraw=true;var startingSong=false;
 var resumes=0;var calls:Array<String>=[];var globals:Map<String,Dynamic>=[];
 function setAllHaxeVar(key:String,value:Dynamic){globals.set(key,value);}
 function callAllHScript(name:String,args:Array<Dynamic>){calls.push(name+':'+args[0]);}
 function pauseVocals(){}
 function resyncVocals(){resumes++;FlxG.sound.music.paused=false;}
 function closeSubState(){throw 'unexpected native close in queued-open test';}
 METHODS
 static function check(ok:Bool,why:String)if(!ok)throw why;
 static function main(){
  var s=new Main();
  var timer=new FlxTimer();var idle=new FlxTimer();idle.active=false;
  var tween=new FlxTween();var done=new FlxTween();done.finished=true;
  FlxTimer.globalManager.tasks=[timer,idle];FlxTween.globalManager.tasks=[tween,done];
  s.compatOpenCustomSubstate('menu',true);
  check(s.paused&&!s.persistentUpdate&&s.persistentDraw,'parent not paused/drawn');
  check(FlxG.sound.music.paused&&!timer.active&&!tween.active&&!idle.active,'timeline not paused');
  check(done.active,'finished task changed');
  check(s.calls.length==0,'callbacks before Flixel create');
  var pending=s.requested;
  var menuTimer=new FlxTimer();FlxTimer.globalManager.tasks.push(menuTimer);
  check(s.compatCloseCustomSubstate(),'queued close failed');
  check(pending.canceled&&s.requested==null,'queued instance not canceled');
  check(!s.paused&&s.persistentUpdate&&s.resumes==1,'audio/parent not resumed');
  check(timer.active&&tween.active&&!idle.active&&menuTimer.active,'task state restore');
  check(!s.compatCloseCustomSubstate(),'closed twice');
  s.compatOpenCustomSubstate('first',true);var first=s.requested;
  var firstMenuTimer=new FlxTimer();FlxTimer.globalManager.tasks.push(firstMenuTimer);
  s.compatOpenCustomSubstate('second',true);var second=s.requested;
  check(first.canceled&&second!=first,'queued replacement');
  check(!firstMenuTimer.active,'replacement left previous menu task running');
  second.lifecycleCreated=true;s.subState=second;
  s.psychCustomSubstateCreate(second);s.psychCustomSubstateCreatePost(second);
  s.psychCustomSubstateUpdate(second,.1);s.psychCustomSubstateUpdatePost(second,.1);
  check(s.calls.join(',')=='customSubstateCreate:second,customSubstateCreatePost:second,customSubstateUpdate:second,customSubstateUpdatePost:second','callback ownership');
  s.calls=[];s.psychCustomSubstateUpdate(first,.1);
  check(s.calls.length==0,'stale owner updated');
  s.compatOpenCustomSubstate('overlay',false);
  check(!s.paused&&s.persistentUpdate&&s.persistentDraw&&timer.active,'nonpaused replacement');
  s.psychCustomSubstateDestroy(second);
  check(s.compatCustomSubstateName=='overlay'&&s.compatCustomSubstateOpen,'old destroy cleared replacement');
  s.compatCloseCustomSubstate();
 }
}
'''.replace('METHODS', methods)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '--run', 'Main'], cwd=ROOT, capture_output=True,
                                    text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
