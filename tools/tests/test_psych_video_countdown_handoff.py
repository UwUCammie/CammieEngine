"""Extracted Psych video API preserves return values and guarded handoffs."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method
ROOT = Path(__file__).resolve().parents[2]

class PsychVideoCountdownHandoffTest(unittest.TestCase):
    def test_actual_video_api_and_handoff(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        paths = (ROOT / 'source/PsychOwnerPaths.hx').read_text()
        video_lookup = paths[paths.index("\t\tReflect.setField(proxy, 'video',"):paths.index("\t\tReflect.setField(proxy, 'getSparrowAtlas',")]
        gate = source[source.index('var countdownResults:Array<Dynamic> = [];', source.index('public function startCountdown():Void')):source.index('\n\t\tif (duoMode)', source.index('var countdownResults:Array<Dynamic> = [];', source.index('public function startCountdown():Void')))]
        fixture = r'''
class FlxG {public static var state:Dynamic;public static var width=1280;public static var height=720;}
class FlxTimer {
 public static var queue:Array<FlxTimer>=[];public var canceled=false;var callback:FlxTimer->Void;
 public function new() {} public function start(t:Float,cb:FlxTimer->Void):FlxTimer {callback=cb;queue.push(this);return this;}
 public function cancel():Void canceled=true;
 public static function tick():Void {var old=queue;queue=[];for(t in old)if(!t.canceled)t.callback(t);}
}
class FNFAssets {public static function exists(path:String):Bool return path=='owner/videos/intro.mp4';}
class PsychOwnerAssetPath {public static function resolve(owner:String,path:String):Dynamic return {path:path};}
class PsychOwnerPaths {
 static function cleanRelative(path:String):String {if(path.indexOf('..')>=0)throw 'unsafe';return path;}
 static function ownerAsset(owner:String,path:String,a:Dynamic,b:Dynamic):String return FNFAssets.exists(owner+'/'+path)?owner+'/'+path:null;
 public static function create(owner:String):Dynamic {var proxy:Dynamic={};var currentLevel:Dynamic=null;__LOOKUP__ return proxy;}
}
class NightmareVisionVideoSprite {
 public static var mode='normal';public static var made=0;public static var looping='loop';
 public var cameras:Array<Dynamic>;public var destroyed=false;public var starts=0;public var ended=false;
 var cb:Void->Void;
 public function new(a:Dynamic,b:Dynamic,x:Int,y:Int,once:Bool,skip:Bool){made++;ended=mode=='decoder';}
 public function setGraphicSize(w:Int,h:Int):Void {} public function updateHitbox():Void {} public function screenCenter():Void {}
 public function onFormat(cb:Void->Void):Void {} public function onEnd(f:Void->Void):Void {cb=f;if(ended)cb();}
 public function load(path:String,opts:Array<String>):Bool {if(mode=='loadfail'){finish();return false;}return true;}
 public function delayAndStart():Void starts++;
 public function finish():Void {ended=true;if(cb!=null)cb();}
 public function destroy():Void destroyed=true;
}
class RuntimeSmokeHarness {public static function markStep(s:String):Void {}}
class ScriptCallbackResult {public static var STOP=1;}
class EngineCompat {public static function anyFunctionStop(a:Array<Dynamic>):Bool return a.indexOf(1)>=0;}
class PsychRuntimeBindings {public static function dispatch(h:Dynamic,n:String,a:Array<Dynamic>):Dynamic {var cb:Dynamic=Reflect.field(h,'gateCallback');return cb==null?(Reflect.field(h,'allowCountdown')?0:1):cb();}}
class Main {
 var psychMissingIntroRequest:Null<Int>;var psychMissingIntroHandoffUsed=false;
 var isStoryMode=false;var alwaysDoCutscenes=false;var startedCountdown=false;public var gateCallback:Void->Dynamic;
 var psychVideoHostDestroyed=false;var psychVideoRequestSerial=0;var psychVideoHandoffTimer:FlxTimer;
 var psychSourceVideo:NightmareVisionVideoSprite;var hxcCountdownHookDispatching=false;
 var inCutscene=false;var endingSong=false;var camOther:Dynamic={};var members:Array<Dynamic>=[];
 var countdowns=0;var ends=0;var allowCountdown=false;var started=false;
 var nightmareVisionScripts:Dynamic=null;var genNotesBeforeCountdown=true;
 function generatePlayfields():Void throw "Psych video countdown entered NV receptor generation";
 public function new(){FlxG.state=this;}
 function add(v:Dynamic):Void members.push(v);function remove(v:Dynamic,b:Bool):Void members.remove(v);
 function callNightmareVision(n:String,a:Array<Dynamic>):Dynamic return 0;
 function callAllHScript(n:String,a:Array<Dynamic>,b:Bool,out:Array<Dynamic>,c:Dynamic,d:Bool):Void {}
 function startCountdown():Void {countdowns++;__GATE__ started=true;}
 function endForReal():Void ends++;
 __HANDOFF__
 __START__
 function teardown():Void {__TEARDOWN__}
 static function check(v:Bool,label:String):Void if(!v)throw label;
 static function main():Void {
  var h=new Main();var before=NightmareVisionVideoSprite.made;
  check(!h.psychStartVideo('owner','missing')&&!h.inCutscene&&h.countdowns==0&&NightmareVisionVideoSprite.made==before,'missing must returnfalse without transition');
  var p=PsychOwnerPaths.create('owner');check(Reflect.callMethod(p,Reflect.field(p,'video'),['intro'])=='owner/videos/intro.mp4','selected owner path');
  var unsafe=false;try Reflect.callMethod(p,Reflect.field(p,'video'),['../escape']) catch(e:Dynamic)unsafe=true;check(unsafe,'unsafe path validation');
  for(mode in ['decoder','loadfail']) {
   NightmareVisionVideoSprite.mode=mode;h=new Main();h.hxcCountdownHookDispatching=true;
   check(h.psychStartVideo('owner','intro'),'existing file accepted despite decoder/load failure');
   check(h.countdowns==0&&h.members.length==0&&h.inCutscene,'synchronous completion must queue and detach');
   FlxTimer.tick();check(h.countdowns==0,'callback dispatch still active');
   h.allowCountdown=true;h.hxcCountdownHookDispatching=false;FlxTimer.tick();
   check(h.countdowns==1&&h.started&&!h.inCutscene,'deferred source gate must see script local update');
   FlxTimer.tick();check(h.countdowns==1,'one completion only');
  }
  NightmareVisionVideoSprite.mode='normal';h=new Main();h.allowCountdown=false;
  check(h.psychStartVideo('owner','intro'),'load returns true');var v=h.psychSourceVideo;check(v.starts==1,'autostart');
  v.finish();v.finish();check(h.countdowns==1&&!h.started,'exact gate stop remains effective and completion dedup');
  h=new Main();h.endingSong=true;h.psychStartVideo('owner','intro');h.psychSourceVideo.finish();check(h.ends==1&&h.countdowns==0,'ending route');
  h=new Main();h.psychStartVideo('owner','intro',true,true,false,false);v=h.psychSourceVideo;check(v.starts==0&&!h.inCutscene,'mid-song manual play');v.finish();check(h.countdowns==0&&h.ends==0,'mid-song no handoff');
  h=new Main();h.hxcCountdownHookDispatching=true;h.psychStartVideo('owner','intro');v=h.psychSourceVideo;v.finish();
  h.psychStartVideo('owner','intro');h.hxcCountdownHookDispatching=false;FlxTimer.tick();check(h.countdowns==0,'replacement cancels queued old handoff');
  h=new Main();h.hxcCountdownHookDispatching=true;h.psychStartVideo('owner','intro');h.psychSourceVideo.finish();h.teardown();FlxTimer.tick();check(h.countdowns==0&&h.ends==0,'destroy cancels');
  h=new Main();h.hxcCountdownHookDispatching=true;h.psychStartVideo('owner','intro');h.psychSourceVideo.finish();h.hxcCountdownHookDispatching=false;FlxG.state={};FlxTimer.tick();check(h.countdowns==0,'state lifetime');
  h=new Main();h.alwaysDoCutscenes=true;
  h.gateCallback=function(){if(!h.allowCountdown){check(!h.psychStartVideo('owner','missing'),'forced missing still false');h.allowCountdown=true;return 1;}return 0;};
  h.startCountdown();check(h.countdowns==1&&!h.started&&FlxTimer.queue.length==1,'blocked forced gate must queue after dispatch');
  FlxTimer.tick();check(h.countdowns==2&&h.started,'script local release observed on deferred reentry');FlxTimer.tick();check(h.countdowns==2,'forced recovery once');
  h=new Main();h.alwaysDoCutscenes=true;
  h.gateCallback=function(){h.psychStartVideo('owner','missing');return 1;};h.startCountdown();FlxTimer.tick();
  check(h.countdowns==2&&!h.started&&FlxTimer.queue.length==0,'permanent source Stop must not retry forever');
  for(story in [false,true]) {
   h=new Main();h.isStoryMode=story;h.alwaysDoCutscenes=story;
   h.gateCallback=function(){h.psychStartVideo('owner','missing');return 1;};h.startCountdown();FlxTimer.tick();
   check(h.countdowns==1&&!h.started,'ordinary Freeplay and actual Story keep missing-video semantics');
  }
  for(mid in [false,true]){
   h=new Main();h.alwaysDoCutscenes=true;h.endingSong=!mid;
   h.gateCallback=function(){h.psychStartVideo('owner','missing',true,mid);return 1;};h.startCountdown();FlxTimer.tick();
   check(h.countdowns==1&&h.ends==0,'missing mid-song/end must not recover');
  }
  h=new Main();h.alwaysDoCutscenes=true;h.gateCallback=function(){h.psychStartVideo('owner','missing');return 0;};h.startCountdown();
  check(h.started&&FlxTimer.queue.length==0,'Continue gate needs no handoff');
  for(change in ['ending','started','story','preference','destroy','replacement']){
   h=new Main();h.alwaysDoCutscenes=true;h.gateCallback=function(){h.psychStartVideo('owner','missing');return 1;};h.startCountdown();
   switch(change){case 'ending':h.endingSong=true;case 'started':h.startedCountdown=true;case 'story':h.isStoryMode=true;case 'preference':h.alwaysDoCutscenes=false;case 'destroy':h.teardown();case 'replacement':h.psychStartVideo('owner','intro');}
   FlxTimer.tick();check(h.countdowns==1&&h.ends==0,'queued missing intro canceled after '+change);
  }
 }
}
'''
        prefix=source[source.index('override public function destroy() {')+len('override public function destroy() {'):]
        prefix=prefix[:prefix.index('psychSourceVideo = null;')+len('psychSourceVideo = null;')]
        fixture=fixture.replace('__GATE__',gate).replace('__LOOKUP__',video_lookup).replace('__HANDOFF__',method(source,'function psychVideoHandoff(')).replace('__START__',method(source,'public function psychStartVideo(')).replace('__TEARDOWN__',prefix)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory);(work/'Main.hx').write_text(fixture,newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',directory,'-main','Main','--interp'],capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
