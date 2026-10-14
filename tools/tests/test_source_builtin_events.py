"""Psych-family built-in chart events share one body per event across Psych and both Nightmare Vision revisions."""
from pathlib import Path
import re, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method

ROOT = Path(__file__).resolve().parents[2]

# Members SourceBuiltinEvents reaches on PlayState. Fixtures that compile the
# shared class around their own host call builtin_host_stubs() to fill in the
# ones they do not exercise; a stub that runs anyway throws so a wrong route shows.
BUILTIN_STUBS = {
	'SONG': 'public static var SONG:Dynamic={speed:1.};',
	'gfSpeed': 'public var gfSpeed:Int=1;',
	'songSpeedType': "public var songSpeedType:String='multiplicative';",
	'playbackRate': 'public var playbackRate:Float=1;',
	'sourceHeyEvent': "function sourceHeyEvent(t:Int,d:Float,strict:Bool=false):Void throw 'unexpected sourceHeyEvent';",
	'sourceAnimationEventActor': "function sourceAnimationEventActor(v:String,trim:Bool,strict:Bool=false):Dynamic throw 'unexpected sourceAnimationEventActor';",
	'playSourceEventAnimation': "function playSourceEventAnimation(a:Dynamic,n:String,s:Bool):Void throw 'unexpected playSourceEventAnimation';",
	'applySourceAltIdleAnimation': "function applySourceAltIdleAnimation(a:String,b:String,strict:Bool=false):Bool throw 'unexpected applySourceAltIdleAnimation';",
	'sourceCameraFollowPosition': "function sourceCameraFollowPosition(a:String,b:String):Void throw 'unexpected sourceCameraFollowPosition';",
	'sourceCameraZoomsEnabled': "function sourceCameraZoomsEnabled():Bool throw 'unexpected sourceCameraZoomsEnabled';",
	'pulseCameraZoom': "function pulseCameraZoom(g:Float,h:Float,m:Float=0,r:Bool=false):Void throw 'unexpected pulseCameraZoom';",
	'shakeCamerasFromEvent': "function shakeCamerasFromEvent(a:String,b:String):Void throw 'unexpected shakeCamerasFromEvent';",
	'sourceScrollSpeedSetting': "function sourceScrollSpeedSetting():Float throw 'unexpected sourceScrollSpeedSetting';",
	'setSongSpeed': "function setSongSpeed(t:Float,s:Float):Void throw 'unexpected setSongSpeed';",
	'historicalSetProperty': "function historicalSetProperty(p:String,v:String):Void throw 'unexpected historicalSetProperty';",
	'setEventProperty': "function setEventProperty(p:String,v:Dynamic):Void throw 'unexpected setEventProperty';",
	'playEventSound': "function playEventSound(p:String,v:Float):Void throw 'unexpected playEventSound';",
}


def builtin_host_stubs(host: str) -> str:
	"""Stub declarations for every shared-event member the host does not declare itself."""
	return '\n '.join(stub for name, stub in BUILTIN_STUBS.items()
		if not re.search(r'\b(?:function|var)\s+' + name + r'\b', host))


def builtin_sources() -> dict:
	return {name + '.hx': (ROOT / ('source/' + name + '.hx')).read_text()
		for name in ['SourceBuiltinEvents', 'CameraEventValues', 'PsychHeyEventCompat']}


TWEEN = r'''package flixel.tweens;
class FlxTween {
 public static var log:Array<String>=[];public static var zooming:Array<Dynamic>=[];public static var globalManager=new Manager();
 public var options:Dynamic;public function new(o:Dynamic)options=o;
 public static function tween(t:Dynamic,v:Dynamic,d:Float,?o:Dynamic):FlxTween {log.push('tween:'+Reflect.fields(v).join(',')+':'+d);return new FlxTween(o);}
}
class Manager {public function new(){}public function containsTweensOf(o:Dynamic,f:Array<String>):Bool return FlxTween.zooming.indexOf(o)>=0;}
'''

HOST = r'''import flixel.FlxG;import flixel.FlxCamera;import flixel.tweens.FlxTween;import flixel.tweens.FlxEase;
class NightmareVisionLegacyCameraEvents {
 var s:PlayState;public function new(s:PlayState)this.s=s;
 public function tweenSongSpeed(t:Float,d:Float):Void s.log.push('owned-tween:'+t+':'+d);
}
class PlayState {
 public static var SONG:Dynamic={speed:2.};
 public var camGame:FlxCamera=new FlxCamera('game');public var camHUD:FlxCamera=new FlxCamera('hud');
 public var songSpeed:Float=2;public var songSpeedType:String='multiplicative';public var songSpeedTween:FlxTween;public var playbackRate:Float=1;
 public var zoomsOn=true;public var gfSpeed:Int=1;public var log:Array<String>=[];
 public var nightmareVisionScripts:Dynamic=null;public var nightmareVisionLegacyFieldCameras=false;
 public var nightmareVisionCameraEvents:NightmareVisionLegacyCameraEvents;public var nightmareVisionPrefs:Dynamic;
 public function new(){FlxG.camera=camGame;}
 function sourceCameraZoomsEnabled():Bool return zoomsOn;
 function setGameCameraZoom(z:Float):Void {camGame.zoom=z;log.push('game-zoom:'+z);}
 function sourceHeyEvent(t:Int,d:Float,strict:Bool=false):Void log.push('hey:'+t+':'+d+':'+strict);
 function sourceAnimationEventActor(v:String,trim:Bool,strict:Bool=false):Dynamic return v+'/'+trim+'/'+strict;
 function playSourceEventAnimation(a:Dynamic,n:String,s:Bool):Void log.push('anim:'+a+':'+n+':'+s);
 function applySourceAltIdleAnimation(a:String,b:String,strict:Bool=false):Bool {log.push('alt:'+a+':'+b+':'+strict);return true;}
 function sourceCameraFollowPosition(a:String,b:String):Void log.push('follow:'+a+':'+b);
 function historicalSetProperty(p:String,v:String):Void log.push('historical:'+p+':'+v);
 function setEventProperty(p:String,v:Dynamic):Void log.push('property:'+p+':'+(Std.isOfType(v,Bool)?'bool':Std.isOfType(v,String)?'text':'number')+':'+v);
 function playEventSound(p:String,v:Float):Void log.push('sound:'+p+':'+v);
 __METHODS__
}
'''

MAIN = r'''import flixel.FlxG;import flixel.FlxCamera;import flixel.tweens.FlxTween;
@:access(PlayState) class Main {
 static function check(v:Bool,m:String) if(!v)throw m;
 static function near(a:Float,b:Float,m:String) if(Math.abs(a-b)>0.000001)throw m+': '+a+' != '+b;
 static function host(profile:Int):PlayState {
  FlxTween.log=[];FlxTween.zooming=[];var s=new PlayState();
  if(profile==SourceBuiltinEvents.NIGHTMARE_LEGACY){s.nightmareVisionScripts={};s.nightmareVisionLegacyFieldCameras=true;s.nightmareVisionPrefs={getGameplaySetting:function(n:String,d:Dynamic):Dynamic return 1.5};}
  if(profile==SourceBuiltinEvents.NIGHTMARE)s.nightmareVisionScripts={};
  return s;
 }
 static function main() {
  // Pure value parsing.
  var shake=CameraEventValues.shake('0.5,0.02,extra');check(shake!=null,'extra fields still shake');near(shake[0],0.5,'duration');near(shake[1],0.02,'intensity');
  for(v in ['0.5','','x,y','0,0.01','0.5,0',' 0.2 , bad'])check(CameraEventValues.shake(v)==null,'no shake for '+v);
  near(CameraEventValues.amount('',0.015),0.015,'empty zoom default');near(CameraEventValues.amount('0.1',0.015),0.1,'zoom amount');
  check(SourceBuiltinEvents.propertyValue(' false ')==false,'trimmed false');check(SourceBuiltinEvents.propertyValue('true')==true,'true');
  check(Std.isOfType(SourceBuiltinEvents.propertyValue('1.5'),Float),'number');check(SourceBuiltinEvents.propertyValue('abc ')=='abc ','text kept as written');
  check(SourceBuiltinEvents.gfSpeed('2.6',true)==3&&SourceBuiltinEvents.gfSpeed('0',true)==1&&SourceBuiltinEvents.gfSpeed('x',true)==1,'Psych rounds');
  check(SourceBuiltinEvents.gfSpeed('2.6',false)==2&&SourceBuiltinEvents.gfSpeed('-3',false)==1,'Nightmare Vision truncates');

  for(profile in [SourceBuiltinEvents.PSYCH,SourceBuiltinEvents.NIGHTMARE,SourceBuiltinEvents.NIGHTMARE_LEGACY]) {
   var tag='profile '+profile+' ';
   var s=host(profile);
   check(SourceBuiltinEvents.apply(s,profile,'Add Camera Zoom','','')==SourceBuiltinEvents.HANDLED,tag+'zoom handled');
   near(s.camGame.zoom,1.015,tag+'default game bump');near(s.camHUD.zoom,1.03,tag+'default HUD bump');
   s.camGame.zoom=1.35;SourceBuiltinEvents.apply(s,profile,'Add Camera Zoom','0.1','0.2');near(s.camGame.zoom,1.35,tag+'cap');near(s.camHUD.zoom,1.03,tag+'cap skips HUD too');
   s.camGame.zoom=1;s.zoomsOn=false;SourceBuiltinEvents.apply(s,profile,'Add Camera Zoom','0.1','0.2');near(s.camGame.zoom,1,tag+'zooms off');
   s.zoomsOn=true;FlxG.camera=new FlxCamera('swapped');SourceBuiltinEvents.apply(s,profile,'Add Camera Zoom','0.1','');near(FlxG.camera.zoom,1.1,tag+'live FlxG camera');near(s.camGame.zoom,1,tag+'swapped camera leaves game camera');

   s=host(profile);
   SourceBuiltinEvents.apply(s,profile,'Screen Shake','0.5, 0.01','0.5');
   check(s.camGame.log.join('|')=='shake:0.01:0.5'&&s.camHUD.log.length==0,tag+'per camera shake '+s.camGame.log+s.camHUD.log);
   SourceBuiltinEvents.apply(s,profile,'Screen Shake','0,0.01','0.3,0.02,0.9');
   check(s.camGame.log.length==1&&s.camHUD.log.join('|')=='shake:0.02:0.3',tag+'zero duration skipped, extra field tolerated');

   s=host(profile);
   var r=SourceBuiltinEvents.apply(s,profile,'Change Scroll Speed','2','');
   var scale=profile==SourceBuiltinEvents.NIGHTMARE_LEGACY?1.5:1;
   check(r==SourceBuiltinEvents.HANDLED,tag+'scroll handled');near(s.songSpeed,2*scale*2,tag+'empty duration is instant');check(FlxTween.log.length==0&&s.log.length==0,tag+'no tween for instant');
   SourceBuiltinEvents.apply(s,profile,'Change Scroll Speed','0.5','1.5');
   if(profile==SourceBuiltinEvents.NIGHTMARE_LEGACY)check(s.log.join('|')=='owned-tween:'+(2*scale*0.5)+':1.5',tag+'historical tween owned '+s.log);
   else check(FlxTween.log.join('|')=='tween:songSpeed:1.5'&&s.songSpeedTween!=null,tag+'linear song speed tween '+FlxTween.log);
   s=host(profile);s.songSpeedType='constant';
   r=SourceBuiltinEvents.apply(s,profile,'Change Scroll Speed','3','0');near(s.songSpeed,2,tag+'constant speed untouched');
   check(r==(profile==SourceBuiltinEvents.PSYCH?SourceBuiltinEvents.HANDLED:SourceBuiltinEvents.STOPPED),tag+'constant result');

   s=host(profile);SourceBuiltinEvents.apply(s,profile,'Set GF Speed','2.6','');
   check(s.gfSpeed==(profile==SourceBuiltinEvents.PSYCH?3:2),tag+'gf speed');
   SourceBuiltinEvents.apply(s,profile,'Hey!','BF','');
   SourceBuiltinEvents.apply(s,profile,'Play Animation','hey',' bf ');
   SourceBuiltinEvents.apply(s,profile,'Alt Idle Animation','gf','-alt');
   SourceBuiltinEvents.apply(s,profile,'Camera Follow Pos','10','');
   var strict=profile==SourceBuiltinEvents.NIGHTMARE_LEGACY;
   check(s.log.join('|')=='hey:0:0.6:'+strict+'|anim: bf /true/'+strict+':hey:true|alt:gf:-alt:'+strict+'|follow:10:',tag+'actor events '+s.log);

   s=host(profile);SourceBuiltinEvents.apply(s,profile,'Set Property','boyfriend.visible','false');SourceBuiltinEvents.apply(s,profile,'Set Property','camHUD.alpha','0.5');
   SourceBuiltinEvents.apply(s,profile,'Set Property','cameraSpeed','fast');
   if(strict)check(s.log.join('|')=='historical:boyfriend.visible:false|historical:camHUD.alpha:0.5|historical:cameraSpeed:fast',tag+'historical property rules');
   else check(s.log.join('|')=='property:boyfriend.visible:bool:false|property:camHUD.alpha:number:0.5|property:cameraSpeed:text:fast',tag+'typed property values '+s.log);

   s=host(profile);r=SourceBuiltinEvents.apply(s,profile,'Play Sound','blip','0.5');var r2=SourceBuiltinEvents.apply(s,profile,'Play Sound','blip','');
   if(profile==SourceBuiltinEvents.PSYCH)check(r==SourceBuiltinEvents.HANDLED&&s.log.join('|')=='sound:blip:0.5|sound:blip:1',tag+'Play Sound plays '+s.log);
   else check(r==SourceBuiltinEvents.UNHANDLED&&r2==SourceBuiltinEvents.UNHANDLED&&s.log.length==0,tag+'Play Sound is Psych only');
   check(SourceBuiltinEvents.apply(s,profile,'add camera zoom','','')==SourceBuiltinEvents.UNHANDLED,tag+'names are exact');
  }

  // Tween-aware beat bumps leave a tweened camera alone and still bump the other.
  var s=host(SourceBuiltinEvents.NIGHTMARE);FlxTween.zooming=[s.camGame];
  s.pulseCameraZoom(0.1,0.2,0,true);near(s.camGame.zoom,1,'tweened game camera untouched');near(s.camHUD.zoom,1.2,'HUD still bumped');
  s.pulseCameraZoom(0.1,0.2);near(s.camGame.zoom,1.1,'unguarded bump');check(s.log.indexOf('game-zoom:1.1')>=0,'game camera goes through the base zoom setter');

  // Native beat pulses always meant the gameplay camera, even after a script swapped FlxG.camera.
  s=host(SourceBuiltinEvents.PSYCH);var swapped=new FlxCamera('swapped');FlxG.camera=swapped;
  s.pulseCameraZoom(0.1,0.2,1.35,false,true);near(s.camGame.zoom,1.1,'native pulse bumps camGame');near(swapped.zoom,1,'native pulse leaves the swapped camera');
  swapped.zoom=2;s.pulseCameraZoom(0.1,0.2,1.35,false,true);near(s.camGame.zoom,1.2,'native cap reads camGame');
  s.camGame.zoom=1.35;s.pulseCameraZoom(0.1,0.2,1.35,false,true);near(s.camGame.zoom,1.35,'native cap');near(s.camHUD.zoom,1.4,'native cap skips HUD');
  trace('ok');
 }
}
'''


class SourceBuiltinEventsTest(unittest.TestCase):
	def test_one_body_per_event_for_every_source_profile(self):
		play = (ROOT / 'source/PlayState.hx').read_text()
		methods = '\n'.join(extract_method(play, 'function ' + name + '(')
			for name in ['pulseCameraZoom', 'shakeCamerasFromEvent', 'setSongSpeed', 'sourceScrollSpeedSetting'])
		files = builtin_sources()
		files.update({
			'PlayState.hx': HOST.replace('__METHODS__', methods),
			'Main.hx': MAIN,
			'flixel/FlxG.hx': 'package flixel;class FlxG {public static var camera:FlxCamera;}',
			'flixel/FlxCamera.hx': "package flixel;class FlxCamera {public var name:String;public var zoom=1.;public var log:Array<String>=[];public function new(n:String)name=n;public function shake(i:Float,d:Float)log.push('shake:'+i+':'+d);}",
			'flixel/tweens/FlxTween.hx': TWEEN,
			'flixel/tweens/FlxEase.hx': 'package flixel.tweens;class FlxEase {public static function linear(t:Float)return t;}',
		})
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = FixturePath(folder)
			for name, content in files.items():
				path = work / name
				path.parent.mkdir(parents=True, exist_ok=True)
				path.write_text(content, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
				cwd=ROOT, text=True, capture_output=True, timeout=120)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_set_property_event_writes_through_the_script_property_aliases(self):
		play = (ROOT / 'source/PlayState.hx').read_text()
		aliases = []
		for name in ['camZoomingMult', 'camZoomingDecay', 'cameraSpeed']:
			start = play.index('@:keep public var ' + name + '(get, set):Float;')
			setter = play.index('function set_' + name + '(', start)
			aliases.append(play[start:play.index('\n', setter)])
		host = r'''class PlayState {
 public var camZoomIntensity:Float=1;public var camZoomDecay:Float=1;public var camSpeed:Float=1;public var defaultCamZoom:Float=1.05;
 public var visibleFlag:Bool=true;public var label:String='';
 public function new(){}
 // Root-only paths are fields on the state, the way the script writer resolves them.
 function compatSetProperty(path:Dynamic,value:Dynamic):Void {
  var name=Std.string(path);
  if(Reflect.getProperty(this,name)==null)throw 'no field '+name;
  Reflect.setProperty(this,name,value);
 }
 __ALIASES__
 __METHODS__
}
'''.replace('__ALIASES__', '\n '.join(aliases)).replace('__METHODS__', extract_method(play, 'public function setEventProperty('))
		main = r'''class Main {
 static function check(v:Bool,m:String) if(!v)throw m;
 static function fire(s:PlayState,path:String,value:String) s.setEventProperty(path,SourceBuiltinEvents.propertyValue(value));
 static function main() {
  var s=new PlayState();
  fire(s,'defaultCamZoom','0.7');check(s.defaultCamZoom==0.7,'defaultCamZoom');
  fire(s,'camZoomingMult','2');check(s.camZoomIntensity==2,'camZoomingMult reaches the beat bump size');
  fire(s,'camZoomingDecay','3.5');check(s.camZoomDecay==3.5,'camZoomingDecay reaches the return speed');
  fire(s,'cameraSpeed','1.5');check(s.camSpeed==1.5,'cameraSpeed reaches the follow speed');
  fire(s,'visibleFlag',' false ');check(s.visibleFlag==false,'booleans are written as booleans');
  fire(s,'label','hello there');check(s.label=='hello there','text is written as text');
  fire(s,'missingThing','1');check(s.defaultCamZoom==0.7,'a failed write is caught and leaves the state alone');
  trace('ok');
 }
}
'''
		files = builtin_sources()
		host = host.replace('\n}\n', '\n ' + builtin_host_stubs(host) + '\n}\n')
		files.update({'PlayState.hx': host, 'Main.hx': main})
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = FixturePath(folder)
			for name, content in files.items():
				(work / name).write_text(content, newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
				cwd=ROOT, text=True, capture_output=True, timeout=120)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_play_state_routes_source_songs_through_the_shared_events(self):
		play = (ROOT / 'source/PlayState.hx').read_text()
		native = extract_method(play, 'function fireNativeSongEvent(')
		route = native.index('applySourceBuiltinEvent(e, psychStageEvent, suppressHistoricalNotification)')
		self.assertLess(native.index('if (hxcEvent.nativeHandled == true'), route)
		self.assertLess(route, native.index('EngineCompat.routeLegacyEvent('))
		self.assertNotIn('NightmareVisionLegacyActorEvents', play)
		self.assertNotIn('changeScrollSpeed(', play)
		profile = extract_method(play, 'function sourceBuiltinEventProfile(')
		self.assertIn('case 1: SourceBuiltinEvents.PSYCH;', profile)
		self.assertIn('nightmareVisionLegacyFieldCameras ? SourceBuiltinEvents.NIGHTMARE_LEGACY : SourceBuiltinEvents.NIGHTMARE', profile)
		# The host switch keeps serving other charts, through the same base functions.
		switch = native[native.index('switch (EngineCompat.eventName(e.name))'):]
		shake = switch[switch.index("case 'Screen Shake':"):switch.index("case 'Focus Camera':")]
		self.assertIn('shakeCamerasFromEvent(e.v1, e.v2);', shake)
		prop = switch[switch.index("case 'Set Property':"):switch.index('\t\t\tdefault:', switch.index("case 'Set Property':"))]
		self.assertIn('setEventProperty(', prop)
		self.assertIn('SourceBuiltinEvents.propertyValue(e.v2)', prop)
		self.assertNotIn('switch', prop)
		wrapper = extract_method(play, 'function fireSongEvent(')
		self.assertIn('if (nightmareVisionScripts != null || nightmareVisionLegacyFieldCameras)', wrapper)

	def test_every_camera_bump_goes_through_the_base_pulse(self):
		play = (ROOT / 'source/PlayState.hx').read_text()
		bumps = [line for line in play.splitlines() if '0.015 *' in line]
		self.assertGreaterEqual(len(bumps), 4)
		for line in bumps:
			self.assertIn('pulseCameraZoom(', line)
		beat = extract_method(play, 'function applyNightmareVisionBeatZoom(')
		self.assertIn('pulseCameraZoom(0.015 * camZoomingMult, 0.03 * camZoomingMult, 0, !nightmareVisionLegacyFieldCameras);', beat)
		self.assertIn('sourceCameraZoomsEnabled()', beat)


if __name__ == '__main__':
	unittest.main()
