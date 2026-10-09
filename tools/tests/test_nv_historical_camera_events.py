"""Camera/HUD event arguments and handles compared with pinned NV source."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
EVENTS=['Game Flash','Add Camera Zoom','Camera Zoom','HUD Fade','Camera Follow Pos','Screen Shake','Set Cam Zoom','Set Cam Pos','Camera Zoom Chain','Screen Shake Chain']

HOST=r'''import flixel.FlxG;import flixel.FlxCamera;import flixel.tweens.FlxTween;import flixel.tweens.FlxEase;import flixel.util.FlxColor;using StringTools;
class PlayState {
 public static var SONG={speed:2.};public var songSpeed=2.;public var songSpeedType='multiplicative';public var songSpeedTween:FlxTween;
 public var camGame=new FlxCamera('game');public var camHUD=new FlxCamera('hud');
 public var camFollow:Dynamic={x:12.,y:34.};public var isCameraOnForcedPos=true;
 public var defaultCamZoom=0.8;public var camTween:FlxTween;public var camHUDAlphaTween:FlxTween;
 public var boyfriendCameraOffset:Array<Float>=[3,4];public var girlfriendCameraOffset:Array<Float>=[5,6];public var opponentCameraOffset:Array<Float>=[7,8];
 public var nightmareVisionPrefs:Dynamic={view:{camZooms:true}};public var registry=new Registry();
 public var totalBeat:Int=0;public var totalShake:Int=0;public var timeBeat:Float=1;
 public var gameZ:Float=.015;public var hudZ:Float=.03;public var gameShake:Float=.003;public var hudShake:Float=.003;public var shakeTime=false;public var curBeat=0;
 public var actual=false;public var mode=0;public var events:Array<String>=[];public var altered=false;
 public function triggerEventNote(n:String,a:String,b:String) {
  events.push(n+':'+a+':'+b+':remaining='+totalBeat);
  if(actual)new NightmareVisionLegacyCameraEvents(this).apply(n,a,b);else source(n,a,b);
  if(n=='Add Camera Zoom'&&!altered) {
   altered=true;
   switch(mode) {
    case 1:totalBeat=0;
    case 2:totalBeat=5;timeBeat=2;gameShake=.7;hudShake=.8;
    case 3:shakeTime=false;
    case 4:triggerEventNote('Camera Zoom Chain','bad,bad,0.4,0.5','3,0.5');
   }
  }
 }
 public function new(){}
 public function legacyScriptRegistry()return registry;
 function setOnHScripts(n:String,v:Dynamic):Void registry.setOnScripts(n,v,registry.hscriptArray);
 __HELPERS__
 __REFERENCE__
 public function snapshot():String return [Std.string(totalBeat),Std.string(totalShake),Std.string(timeBeat),Std.string(gameZ),Std.string(hudZ),Std.string(gameShake),Std.string(hudShake),Std.string(shakeTime),events.join("~"),Std.string(defaultCamZoom),Std.string(FlxG.camera.zoom),Std.string(camGame.zoom),Std.string(camHUD.zoom),Std.string(camHUD.alpha),Std.string(camFollow.x),Std.string(camFollow.y),Std.string(isCameraOnForcedPos),boyfriendCameraOffset.join(','),girlfriendCameraOffset.join(','),opponentCameraOffset.join(','),camTween==null?'null':camTween.name,camHUDAlphaTween==null?'null':camHUDAlphaTween.name,registry.log.join('|'),FlxTween.log.join('|'),FlxCamera.log.join('|')].join('#');
}
class Registry {
 public var hscriptArray:Array<Dynamic>=[];public var log:Array<String>=[];public function new(){}
 public function setOnScripts(n:String,v:Dynamic,a:Array<Dynamic>){if(a!=hscriptArray)throw 'wrong language';log.push(n+':'+v);}
}
class ClientPrefs {public static var camZooms=true;}
'''
MAIN=r'''import PlayState.ClientPrefs;import flixel.FlxG;import flixel.FlxCamera;import flixel.tweens.FlxTween;
class Main {
 static function run(actual:Bool,name:String,a:String,b:String,enabled:Bool,zoom:Float):String {
  FlxTween.reset();FlxCamera.log=[];FlxG.camera=new FlxCamera('primary');FlxG.camera.zoom=zoom;
  var s=new PlayState();s.nightmareVisionPrefs.view.camZooms=enabled;ClientPrefs.camZooms=enabled;
  s.camTween=FlxTween.tween(FlxG.camera,{zoom:1.2},5);s.camHUDAlphaTween=FlxTween.tween(s.camHUD,{alpha:.2},5);
  var unrelated=FlxTween.tween(s.camHUD,{alpha:.5},10);FlxTween.log=[];
  var error=false;var adapter=new NightmareVisionLegacyCameraEvents(s);
  try {if(actual)adapter.apply(name,a,b);else s.source(name,a,b);}catch(_:Dynamic)error=true;
  var before=s.snapshot()+'#'+error;
  for(t in FlxTween.all.copy())t.complete();
  return before+'@@'+s.snapshot();
 }
 static function chain(actual:Bool,mode:Int,interval:Float,bpm:Float,enabled:Bool):String {
  FlxTween.reset();FlxCamera.log=[];var s=new PlayState();FlxG.camera=s.camGame;Conductor.bpm=bpm;
  s.actual=actual;s.mode=mode;s.totalBeat=3;s.totalShake=7;s.shakeTime=true;s.timeBeat=interval;
  s.gameZ=.04;s.hudZ=.05;s.gameShake=.006;s.hudShake=.008;s.nightmareVisionPrefs.view.camZooms=enabled;ClientPrefs.camZooms=enabled;
  var result=[];
  for(beat in [0,1,2,3,4,8,12]) {s.curBeat=beat;if(actual)NightmareVisionLegacyCameraEvents.consumeBeat(s);else s.sourceBeat();result.push(s.snapshot());}
  return result.join('@@');
 }
 static function main(){
  var values:Array<String>=[null,'','bad','0','-1','1','2.5','0.4,linear','1,0.2','0.2,0.1,extra','bf',' dad ','#FF0000','3,2','3,2,0.01,0.02'];
  var count=0;
  for(n in __EVENTS__)for(a in values)for(b in values)for(enabled in [false,true])for(z in [.8,1.35,2.]) {
   var expected=run(false,n,a,b,enabled,z);var actual=run(true,n,a,b,enabled,z);
   if(expected!=actual)throw n+':'+a+':'+b+':'+enabled+':'+z+'\n'+expected+'\n'+actual;count++;
  }
  FlxTween.reset();var s=new PlayState();FlxG.camera=s.camGame;var owner=new NightmareVisionLegacyCameraEvents(s);
  owner.apply('HUD Fade','0','2');var first=s.camHUDAlphaTween;
  var foreign=FlxTween.tween(s.camHUD,{alpha:.5},3);
  s.camHUDAlphaTween=null;owner.setActive(false);
  if(first.active||!foreign.active)throw 'captured ownership must survive public handle replacement';
  owner.setActive(true);if(!first.active)throw 'resume owned tween';
  first.cancel();owner.setActive(true);if(first.active)throw 'cancelled tween revived';
  owner.apply('Camera Zoom','2','1');var zoom=s.camTween;
  owner.destroy();if(zoom.active||!foreign.active||s.camTween!=null||s.camHUDAlphaTween!=null)throw 'owner cleanup';
  var chains=0;
  for(mode in 0...5)for(interval in [0.,.5,1.,2.,-1.,Math.NaN])for(bpm in [60.,120.,180.])for(enabled in [true,false]) {
   var expected=chain(false,mode,interval,bpm,enabled);var actual=chain(true,mode,interval,bpm,enabled);
   if(expected!=actual)throw 'chain '+mode+':'+interval+':'+bpm+':'+enabled+'\n'+expected+'\n'+actual;chains++;
  }
  trace(count+' pinned camera/HUD event cases and '+chains+' live chain sequences verified');
 }
}'''
TWEEN=r'''package flixel.tweens;
class FlxTween {
 public static var all:Array<FlxTween>=[];public static var log:Array<String>=[];public static var globalManager=new Manager();
 public var active=true;public var finished=false;public var name:String;public var target:Dynamic;public var values:Dynamic;public var options:Dynamic;
 public function new(n:String,t:Dynamic,v:Dynamic,o:Dynamic){name=n;target=t;values=v;options=o;}
 public static function reset(){all=[];log=[];}
 public static function tween(t:Dynamic,v:Dynamic,d:Float,?o:Dynamic):FlxTween {
  var fields=Reflect.fields(v);fields.sort(Reflect.compare);var props=[for(f in fields)f+':'+Reflect.field(v,f)];
  var ease=o==null?'default':Std.string(Reflect.callMethod(null,o.ease,[.5]));
  var n=t.name+':'+props.join(',')+':'+d+':'+ease;log.push('start:'+n);var result=new FlxTween(n,t,v,o);all.push(result);return result;
 }
 public static function cancelTweensOf(t:Dynamic,f:Array<String>):Void {for(x in all.copy())if(x.target==t)x.cancel();}
 public function cancel(){active=false;all.remove(this);log.push('cancel:'+name);}
 public function complete(){finished=true;active=false;for(f in Reflect.fields(values))Reflect.setField(target,f,Reflect.field(values,f));all.remove(this);if(options!=null&&options.onComplete!=null)Reflect.callMethod(null,options.onComplete,[this]);}
}
class Manager {public function new(){}public function forEach(f:FlxTween->Void)for(t in FlxTween.all)f(t);}
'''
class HistoricalCameraEventsTest(unittest.TestCase):
 def test_arguments_handles_and_owner_lifetime_match_pinned_source(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  src=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  method=extract_method(src,'function triggerEventNote(')
  cases=re.split(r'(?=^\t\t\tcase )',method,flags=re.M)
  selected=[]
  for case in cases:
   match=re.match(r"\t\t\tcase '([^']+)':",case)
   if match and match[1] in EVENTS:selected.append(case)
  reference='public function source(eventName:String,value1:String,value2:String){switch(eventName){'+''.join(selected)+'}}'
  beat=extract_method(src,'function beatHit(')
  reference+='public function sourceBeat(){'+beat[beat.index('if(totalBeat > 0)'):beat.index("setOnScripts('curBeat'")]+ '}'
  play=(ROOT/'source/PlayState.hx').read_text()
  helpers='\n'.join(extract_method(play,'function '+n+'(') for n in ['sourceHudFade','sourceCameraFollowPosition'])
  files={
   'Conductor.hx':'class Conductor {public static var bpm:Float=120;}',
   'PlayState.hx':HOST.replace('__HELPERS__',helpers).replace('__REFERENCE__',reference),
   'Main.hx':MAIN.replace('__EVENTS__',str(EVENTS)),
   'NightmareVisionLegacyCameraEvents.hx':(ROOT/'source/NightmareVisionLegacyCameraEvents.hx').read_text(),
   'flixel/FlxG.hx':'package flixel;class FlxG {public static var camera:FlxCamera;}',
   'flixel/FlxCamera.hx':'''package flixel;class FlxCamera {public static var log:Array<String>=[];public var name:String;public var zoom=1.;public var alpha=1.;public function new(n:String)name=n;public function flash(c:Dynamic,d:Float){log.push('flash:'+name+':'+c+':'+d);}public function shake(i:Float,d:Float){log.push('shake:'+name+':'+i+':'+d);}}''',
   'flixel/util/FlxColor.hx':'''package flixel.util;class FlxColor {public static function fromString(v:String):Dynamic return v;}''',
   'flixel/tweens/FlxTween.hx':TWEEN,
   'flixel/tweens/FlxEase.hx':'package flixel.tweens;class FlxEase {public static function linear(t:Float)return t;public static function circOut(t:Float)return Math.sqrt(1-(t-1)*(t-1));}'
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   for name,content in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  host_beat=extract_method(play,'function beatHit(')
  self.assertLess(host_beat.index('super.beatHit();'),host_beat.index('lastBeatHit >= curBeat'))
  self.assertLess(host_beat.index('lastBeatHit >= curBeat'),host_beat.index('dispatchPsychCompiledStage'))
  self.assertIn('if (endingSong && !nightmareVisionLegacyFieldCameras) return;',host_beat)
  self.assertLess(host_beat.index('applyNightmareVisionBeatZoom();'),host_beat.index('finishHistoricalNightmareBeat();'))
  self.assertIn("callAllHScript('beatHit', [curBeat], false, null, null, false, nightmareVisionLegacyFieldCameras)",host_beat)
  finish=extract_method(play,'function finishHistoricalNightmareBeat(')
  order=['lastBeatHit = curBeat','consumeBeat(this)',"setAllHaxeVar('curBeat'","setOnScripts('curBeat'","broadcastHistoricalNightmareScripts('onBeatHit'"]
  self.assertEqual(sorted(finish.index(x) for x in order),[finish.index(x) for x in order])
  death=extract_method(play,'function doDeathCheck(')
  self.assertIn('if (nightmareVisionLegacyFieldCameras) totalBeat = 0;',death)
  self.assertLess(death.index('isDead = true'),death.index('totalBeat = 0'))
if __name__=='__main__':unittest.main()
