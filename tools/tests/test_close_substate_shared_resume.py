"""closeSubState resumes gameplay through the shared resumeGameplayFromSubstate.

The fixture runs the real closeSubState twice per scenario: once as it ships,
and once with its resume block put back to the inline copy it replaced. Every
script-visible call must see the same state in both, and both must end in the
same state.
"""
from pathlib import Path
import itertools, re, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_camera_alias import extract_method

ROOT = Path(__file__).resolve().parents[2]

SHARED_BLOCK = '''			resumeGameplayFromSubstate(!psychSourcePause || canResync, false);
			if (!opponentPlayer && !duoMode)
				controls.setKeyboardScheme(Solo(Note.NOTE_AMOUNT));
			if (duoMode)
				controls.setKeyboardScheme(Duo(true));
			if (psychSourcePause) SourcePauseTasks.setActive(true);
			if (!psychSourcePause && !resumePsychCustom && startTimer != null && !startTimer.finished
				&& !hxcCountdownHeld())
				startTimer.active = true;
			applyDemoPlaybackRate();
'''

INLINE_BLOCK = '''			if (FlxG.sound.music != null && !startingSong && (!psychSourcePause || canResync))
				resyncVocals();
			if (!opponentPlayer && !duoMode)
				controls.setKeyboardScheme(Solo(Note.NOTE_AMOUNT));
			if (duoMode)
				controls.setKeyboardScheme(Duo(true));
			if (psychSourcePause) SourcePauseTasks.setActive(true);
			if (!psychSourcePause && !resumePsychCustom && startTimer != null && !startTimer.finished
				&& !hxcCountdownHeld())
				startTimer.active = true;
			paused = false;
			applyDemoPlaybackRate();
			setAllHaxeVar("paused", paused);
'''


def strip_platform_blocks(text):
	return re.sub(r'#if (windows|cpp)\b.*?#end', '', text, flags=re.S)


class CloseSubstateSharedResumeTest(unittest.TestCase):
	def setUp(self):
		self.source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
		self.close = extract_method(self.source, 'override function closeSubState(')

	def test_close_uses_the_shared_resume(self):
		self.assertIn(SHARED_BLOCK, self.close)
		self.assertNotIn('resyncVocals()', self.close)
		self.assertNotIn('paused = false;', self.close)
		self.assertNotIn('setAllHaxeVar("paused"', self.close)

	def test_shipped_close_matches_the_inline_resume(self):
		shipped = strip_platform_blocks(self.close).replace('override function closeSubState()', 'function closeShipped()')
		inline = shipped.replace('function closeShipped()', 'function closeInline()').replace(SHARED_BLOCK, INLINE_BLOCK)
		self.assertNotEqual(shipped, inline)
		resume = extract_method(self.source, 'function resumeGameplayFromSubstate(')
		shipped = shipped.replace('super.closeSubState()', 'baseClose()')
		inline = inline.replace('super.closeSubState()', 'baseClose()')
		fixture = r'''
enum KeyboardScheme {Solo(n:Int); Duo(b:Bool);}
class Note {public static var NOTE_AMOUNT=4;}
class PauseSubState {public function new(){}}
class Custom {public var sourceLifecycle=false;public function new(){}}
class CodenameGameEvent {public function new(){}}
class Sound {public var playing=false;public function new(){}}
class FlxG {public static var sound:{music:Sound}={music:null};}
class Timer {public var finished=false;public var active=false;public function new(){}}
class Log {public static var lines:Array<String>=[];}
class EngineCompat {public static function hxcLifecyclePayload(n:String,?o:Dynamic):Dynamic return n;}
class SourcePauseTasks {public static var active=false;public static function setActive(a:Bool){active=a;Log.lines.push('tasks:'+a);}}
class PsychRuntimeBindings {public static function dispatch(h:Main,n:String,a:Array<Dynamic>){h.observe('psych:'+n);}}
class CoolUtil {public static function resumeTween(t:Dynamic){Log.lines.push('tween:'+t);}}
class RuntimeSmokeHarness {public static function markPauseTransition(n:String){Log.lines.push('smoke:'+n);}}
class HxcCompatRuntime {public static function resumeFunkinVideos(h:Main){h.observe('videos');}}
class Controls {public var scheme:KeyboardScheme;public function new(){}public function setKeyboardScheme(s:KeyboardScheme)scheme=s;}
class CamEvents {public var active=false;public function new(){}public function setActive(a:Bool)active=a;}
class Main {
 var subState:Dynamic;var paused=false;var persistentUpdate=false;var startingSong=false;var canResync=true;
 var opponentPlayer=false;var duoMode=false;var controls=new Controls();var startTimer:Timer;
 var compatCustomSubstatePausesGame=false;var compatCustomSubstate:Custom;var nightmareVisionCameraEvents=new CamEvents();
 var curCamPos='pos';var curCamZoom='zoom';var vSliceScrollTweens=['scroll'];var poisonTimes=0;
 var hxcHeld=false;var cancelResume=false;var psychSource=false;var resyncs=0;var demoRate=0;var vars:Map<String,Dynamic>=[];
 var timeline=0;var codenamePaused:Null<Bool>=null;
 public function new(){}
 function psychSourceSubstateSemantics(s:Dynamic):Bool return psychSource;
 function dispatchCancelableHxcLifecycle(n:String,p:Dynamic):Bool {observe('cancelable:'+n);return cancelResume;}
 function callCodenameScripts(n:String,a:Array<Dynamic>)observe('codename:'+n);
 function callNightmareVision(n:String,a:Array<Dynamic>)observe('nv:'+n);
 function dispatchPsychCompiledStage(n:String,a:Array<Dynamic>)observe('stage:'+n);
 function callAllHScript(n:String,a:Array<Dynamic>,?force:Bool)observe('hscript:'+n+':'+force);
 function baseClose(){observe('baseClose');subState=null;}
 function resyncVocals(){resyncs++;FlxG.sound.music.playing=true;}
 function hxcCountdownHeld():Bool return hxcHeld;
 function applyDemoPlaybackRate(){demoRate=paused?1:2;}
 function setAllHaxeVar(n:String,v:Dynamic)vars.set(n,v);
 function sourceHUDHealthPercent():Float return 50;
 function resumePsychCustomTimeline()timeline++;
 function setCodenameScriptsPaused(v:Bool)codenamePaused=v;
 // The V-Slice justUnpaused flag sits outside the resume block both copies share.
 function markJustUnpaused()observe('justUnpaused');
 public function observe(what:String)
  Log.lines.push(what+'|'+paused+'|'+vars.get('paused')+'|'+resyncs+'|'+SourcePauseTasks.active+'|'+(startTimer==null?'-':''+startTimer.active)+'|'+demoRate+'|'+controls.scheme);
 function finalState():String
  return ([paused,persistentUpdate,vars.get('paused'),resyncs,SourcePauseTasks.active,startTimer==null?null:startTimer.active,demoRate,
   controls.scheme,nightmareVisionCameraEvents.active,timeline,codenamePaused,subState==null]:Array<Dynamic>).join(',');
 RESUME
 SHIPPED
 INLINE
 static function run(flags:Array<Bool>,shipped:Bool):String {
  Log.lines=[];SourcePauseTasks.active=false;
  var s=new Main();
  s.paused=flags[0];s.psychSource=flags[1];s.canResync=flags[2];s.startingSong=flags[3];
  FlxG.sound.music=flags[4]?new Sound():null;s.duoMode=flags[5];s.opponentPlayer=flags[6];
  s.startTimer=flags[7]?new Timer():null;s.hxcHeld=flags[8];s.cancelResume=flags[9];
  var custom=new Custom();s.compatCustomSubstate=custom;s.compatCustomSubstatePausesGame=flags[10];
  s.subState=flags[11]?(new PauseSubState():Dynamic):(custom:Dynamic);
  s.vars.set('paused',s.paused);
  if(shipped)s.closeShipped();else s.closeInline();
  return Log.lines.join(';')+'#'+s.finalState();
 }
 static function main(){
  var cases=0;
  for(mask in 0...(1<<12)){
   var flags=[for(bit in 0...12)(mask&(1<<bit))!=0];
   var a=run(flags,true),b=run(flags,false);
   if(a!=b)throw 'mismatch '+flags+'\nshipped '+a+'\ninline  '+b;
   cases++;
  }
  if(cases!=4096)throw 'cases';
 }
}
'''.replace('RESUME', resume).replace('SHIPPED', shipped).replace('INLINE', inline)
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			(Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--run', 'Main'], cwd=ROOT,
									capture_output=True, text=True, timeout=120)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_closing_keeps_persistent_update_but_custom_close_restores_it(self):
		resume = extract_method(self.source, 'function resumeGameplayFromSubstate(')
		fixture = r'''
class Main {
 var paused=true;var persistentUpdate=false;var startingSong=false;var resyncs=0;var vars:Map<String,Dynamic>=[];
 public function new(){}
 function setAllHaxeVar(n:String,v:Dynamic)vars.set(n,v);
 function resyncVocals()resyncs++;
 RESUME
 static function main(){
  FlxG.sound.music={};
  var s=new Main();s.resumeGameplayFromSubstate(true,false);
  if(s.paused||s.persistentUpdate||s.vars.get('paused')!=false||s.resyncs!=1)throw 'close resume';
  s=new Main();s.resumeGameplayFromSubstate(true);
  if(s.paused||!s.persistentUpdate||s.resyncs!=1)throw 'custom resume';
  s=new Main();s.startingSong=true;s.resumeGameplayFromSubstate(true);
  if(s.resyncs!=0)throw 'resynced before the song started';
 }
}
class FlxG {public static var sound:{music:Dynamic}={music:null};}
'''.replace('RESUME', resume)
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			(Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--run', 'Main'], cwd=ROOT,
									capture_output=True, text=True, timeout=60)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
	unittest.main()
