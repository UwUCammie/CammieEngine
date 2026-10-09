"""Historical scroll events compare source defaults, notification exits and overlapping handles."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
from test_nv_historical_camera_events import TWEEN
ROOT=Path(__file__).resolve().parents[2]
class HistoricalScrollEventsTest(unittest.TestCase):
 def test_source_event_and_generation_contract(self):
  src=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/NightmareVision'),'show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],text=True)
  source_generation=extract_method(src,'private function generateSong(')
  source_init=source_generation[source_generation.index('{')+1:source_generation.index('var songData = SONG;')]
  event=extract_method(src,'function triggerEventNote(')
  case=event[event.index("case 'Change Scroll Speed':"):event.index("case 'Camera Zoom Chain':")]
  reference='function sourceEvent(eventName:String,value1:String,value2:String){switch(eventName){'+case+'}registry.notifyEvent(eventName,value1,value2);}'
  play=(ROOT/'source/PlayState.hx').read_text()
  wrapper=extract_method(play,'function fireSongEvent(')
  native=extract_method(play,"if (nightmareVisionLegacyFieldCameras && e.name == 'Change Scroll Speed')")
  init=extract_method(play,'function initializeHistoricalSongSpeed(')
  controller=(ROOT/'source/NightmareVisionLegacyCameraEvents.hx').read_text()
  methods='\n'.join(extract_method(controller,m) for m in ['function cancel(', 'function tween(', 'public function setActive(', 'public function destroy(', 'public function changeScrollSpeed('])
  owner='import flixel.tweens.FlxTween;import flixel.tweens.FlxEase;class NightmareVisionLegacyCameraEvents {var state:PlayState;var owned:Array<FlxTween>=[];public function new(s:PlayState)state=s;'+methods+'}'
  host=r'''import flixel.tweens.FlxTween;import flixel.tweens.FlxEase;
class Prefs {
 var s:PlayState;public var multiplier:Float;public var mode=0;public var touched=false;
 public function new(s:PlayState,m:Float){this.s=s;multiplier=m;}
 public function getGameplaySetting(n:String,d:Dynamic):Dynamic {
  if(n=='scrolltype')return s.initialType;
  s.events.push('pref');if(!touched){touched=true;if(mode==1)throw 'pref';if(mode==2){var old=s.songSpeedType;s.songSpeedType='constant';s.fire('2','0');s.songSpeedType=old;}}
  return multiplier;
 }
}
class Registry {var s:PlayState;public function new(s:PlayState)this.s=s;public function notifyEvent(n:String,a:String,b:String){s.events.push('notify:'+s.songSpeed+':'+(s.songSpeedTween==null?'null':s.songSpeedTween.name));}}
class ClientPrefs {public static var current:Prefs;public static function getGameplaySetting(n:String,d:Dynamic):Dynamic return current.getGameplaySetting(n,d);}
class CodenameEventDispatch {public static function fromNative(e:Dynamic):Dynamic return null;}
class PlayState {
 public static var SONG={speed:2.};public var name='state';public var songSpeed=3.;public var songSpeedType:String='multiplicative';public var initialType:String;
 public var camTween:FlxTween;public var camHUDAlphaTween:FlxTween;public var songSpeedTween:FlxTween;
 public var nightmareVisionPrefs:Prefs;public var nightmareVisionLegacyFieldCameras=true;public var nightmareVisionScripts:Dynamic={};
 public var nightmareVisionCameraEvents:NightmareVisionLegacyCameraEvents;public var registry:Registry;public var events:Array<String>=[];var actual:Bool;
 public function new(a:Bool,t:String,m:Float,mode:Int){actual=a;initialType=t;songSpeedType=t;registry=new Registry(this);nightmareVisionPrefs=new Prefs(this,m);nightmareVisionPrefs.mode=mode;ClientPrefs.current=nightmareVisionPrefs;}
 function codenameSelectedRoot():String return '';function executeCodenameEvent(e:Dynamic):Void throw 'unexpected';
 function callNightmareVision(n:String,a:Array<Dynamic>):Dynamic return 0;
 function legacyScriptRegistry():Registry return registry;
 function dispatchPsychCompiledStageEvent(e:Dynamic):Void {}
 function fireNativeSongEvent(e:Dynamic,?suppressHistoricalNotification:Void->Void):Void {var psychStageEvent=e; __NATIVE__ }
 public function fire(a:String,b:String):Void {if(actual)fireSongEvent({name:'Change Scroll Speed',v1:a,v2:b});else sourceEvent('Change Scroll Speed',a,b);}
 public function initialize(){if(actual)initializeHistoricalSongSpeed();else {__SOURCE_INIT__}}
 public function snapshot():String return songSpeed+'#'+songSpeedType+'#'+(songSpeedTween==null?'null':songSpeedTween.name)+'#'+events.join('|')+'#'+FlxTween.log.join('|');
 __METHODS__
}
'''.replace('__NATIVE__',native).replace('__METHODS__',wrapper+'\n'+reference+'\n'+init).replace('__SOURCE_INIT__',source_init)
  main=r'''import PlayState;import flixel.tweens.FlxTween;
class Main {
 static function run(actual:Bool,t:String,p:Float,mode:Int,a:String,b:String):String {
  FlxTween.reset();var s=new PlayState(actual,t,p,mode);s.initialize();var failed=false;
  try{s.fire(a,b);s.fire('3','2');}catch(_:Dynamic)failed=true;
  var result=s.snapshot()+'#'+failed;
  for(tween in FlxTween.all.copy()){tween.complete();result+='@@'+s.snapshot();}
  return result;
 }
 static function main(){var count=0;
 for(t in [null,'constant','multiplicative','Constant',''])for(p in [0.,-1.,1.,1.5,Math.NaN])for(mode in 0...3)
 for(a in [null,'','bad','0','-1','1','2.5'])for(b in [null,'','bad','-1','0','0.5','2']){
  var expected=run(false,t,p,mode,a,b);var actual=run(true,t,p,mode,a,b);
  if(expected!=actual)throw t+':'+p+':'+mode+':'+a+':'+b+'\n'+expected+'\n'+actual;count++;
 }trace(count+' scroll event/notification sequences');
 }}'''
  files={'Main.hx':main,'PlayState.hx':host,'NightmareVisionLegacyCameraEvents.hx':owner,'flixel/tweens/FlxTween.hx':TWEEN,'flixel/tweens/FlxEase.hx':'package flixel.tweens;class FlxEase {public static function linear(t:Float)return t;}'}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   for name,content in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  generation=extract_method(play,'private function generateSong(')
  self.assertLess(generation.index('initializeHistoricalSongSpeed();'),generation.index('SongEvents.collect('))
if __name__=='__main__':unittest.main()
