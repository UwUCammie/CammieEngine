"""Camera/HUD event arguments and handles compared with pinned NV source."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
EVENTS=['Game Flash','Add Camera Zoom','Camera Zoom','HUD Fade','Camera Follow Pos','Screen Shake','Set Cam Zoom','Set Cam Pos']

HOST=r'''import flixel.FlxG;import flixel.FlxCamera;import flixel.tweens.FlxTween;import flixel.tweens.FlxEase;import flixel.util.FlxColor;using StringTools;
class PlayState {
 public var camGame=new FlxCamera('game');public var camHUD=new FlxCamera('hud');
 public var camFollow:Dynamic={x:12.,y:34.};public var isCameraOnForcedPos=true;
 public var defaultCamZoom=0.8;public var camTween:FlxTween;public var camHUDAlphaTween:FlxTween;
 public var boyfriendCameraOffset:Array<Float>=[3,4];public var girlfriendCameraOffset:Array<Float>=[5,6];public var opponentCameraOffset:Array<Float>=[7,8];
 public var nightmareVisionPrefs:Dynamic={view:{camZooms:true}};public var registry=new Registry();
 public function new(){}
 public function legacyScriptRegistry()return registry;
 function setOnHScripts(n:String,v:Dynamic):Void registry.setOnScripts(n,v,registry.hscriptArray);
 __HELPERS__
 __REFERENCE__
 public function snapshot():String return [Std.string(defaultCamZoom),Std.string(FlxG.camera.zoom),Std.string(camGame.zoom),Std.string(camHUD.zoom),Std.string(camHUD.alpha),Std.string(camFollow.x),Std.string(camFollow.y),Std.string(isCameraOnForcedPos),boyfriendCameraOffset.join(','),girlfriendCameraOffset.join(','),opponentCameraOffset.join(','),camTween==null?'null':camTween.name,camHUDAlphaTween==null?'null':camHUDAlphaTween.name,registry.log.join('|'),FlxTween.log.join('|'),FlxCamera.log.join('|')].join('#');
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
 static function main(){
  var values:Array<String>=[null,'','bad','0','-1','1','2.5','0.4,linear','1,0.2','0.2,0.1,extra','bf',' dad ','#FF0000'];
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
  trace(count+' pinned camera/HUD event cases verified');
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
  play=(ROOT/'source/PlayState.hx').read_text()
  helpers='\n'.join(extract_method(play,'function '+n+'(') for n in ['sourceHudFade','sourceCameraFollowPosition'])
  files={
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
if __name__=='__main__':unittest.main()
