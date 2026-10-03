"""Execute production Codename handlers with deterministic tween boundaries."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameNativeEventTest(unittest.TestCase):
    def test_camera_speed_replacement_and_pause_contracts(self):
        source = (ROOT/'source/PlayState.hx').read_text()
        def method(name):
            match = re.search(r'\t(?:public )?(?:static )?function '+name+r'\(', source)
            self.assertIsNotNone(match, name)
            start = match.start(); brace = source.index('{', start); depth = 0
            for i in range(brace, len(source)):
                depth += (source[i]=='{')-(source[i]=='}')
                if depth == 0:
                    return source[start:i+1]
            raise AssertionError(name)
        helpers = '\n'.join(method(name) for name in (
            'codenameEventNumber', 'codenameEventBoolean', 'codenameEventText',
            'codenameEventEase', 'resolveFocusCameraEase', 'cancelCodenameNativeEventTween',
            'trackCodenameNativeEventTween', 'finishCodenameNativeEventTween',
            'clearCodenameNativeEventTweens', 'setCodenameCameraZoomDefault',
            'applyCodenameNativeEvent', 'setCodenameScriptsPaused'))
        dispatch_source = (ROOT/'source/CodenameEventDispatch.hx').read_text()
        dispatch_start = dispatch_source.index('\tpublic static function applyPlayAnimation<')
        dispatch_brace = dispatch_source.index('{', dispatch_start)
        dispatch_depth = 0
        for index in range(dispatch_brace, len(dispatch_source)):
            dispatch_depth += (dispatch_source[index]=='{')-(dispatch_source[index]=='}')
            if dispatch_depth == 0:
                play_animation_helper = dispatch_source[dispatch_start:index+1]
                break
        else:
            self.fail('could not extract CodenameEventDispatch.applyPlayAnimation')
        fixture = r'''
class FlxCamera {
 public static var defaultZoom:Float=1;
 public var zoom:Float=1;
 public function new() {}
}
class Conductor {
 public static var stepCrochet:Float=125;
 public static var bpm:Float=120;
 public static function changeBPM(value:Float):Void bpm=value;
}
class CodenameCameraModulo {
 public static function defaults():Dynamic return {interval:4,strength:1,every:'BEAT',offset:0};
 public static function apply(config:Dynamic,params:Array<Dynamic>):Dynamic return config;
}
class CharacterAnimation {
 public function new() {}
 public function exists(name:String):Bool return name=='locked' || name=='plain';
}
class Character {
 public var idleSuffix='';
 public var animation=new CharacterAnimation();
 public var playedName:String='';
 public var playedForce:Null<Bool>=null;
 public var playedContext:Dynamic=null;
 public function new() {}
 public function codenamePlayAnim(name:String,force:Null<Bool>,context:Dynamic):Void {
  playedName=name;playedForce=force;playedContext=context;
 }
}
class Line {
 public var altAnim:Bool=false;
 public var defaultAnimSuffix='-alt';
 public var characters:Array<Character>=[new Character()];
 public var actorSlots:Array<Character>;
 public function new() {actorSlots=characters;}
}
@:keep class FlxEase {
 public static function linear(t:Float):Float return t;
 public static function quadOut(t:Float):Float return 1-(1-t)*(1-t);
}
class FlxTween {
 public var active=true;
 public var finished=false;
 public var cancelled=false;
 public var duration:Float;
 public var options:Dynamic;
 var target:Dynamic;
 var fields:Dynamic;
 var initial:Map<String,Float>=[];
 public static function tween(target:Dynamic,fields:Dynamic,duration:Float,options:Dynamic):FlxTween {
  var t=new FlxTween();t.target=target;t.fields=fields;t.duration=duration;t.options=options;
  for(k in Reflect.fields(fields)) t.initial.set(k,Reflect.getProperty(target,k));
  return t;
 }
 public function new() {}
 public function cancel():Void {active=false;cancelled=true;}
 public function advance(fraction:Float):Void {
  if(!active)return;
  var factor:Float=options.ease(fraction);
  // FlxTween.update invokes onUpdate before VarTween writes properties.
  if(fraction<1 && options.onUpdate!=null)options.onUpdate(this);
  for(k in Reflect.fields(fields))Reflect.setProperty(target,k,initial.get(k)+(Reflect.field(fields,k)-initial.get(k))*factor);
  if(fraction==1){finished=true;active=false;if(options.onComplete!=null)options.onComplete(this);}
 }
}
class CodenameEventDispatch {
''' + play_animation_helper + r'''
}
class Main {
 var codenameScriptScopes:Array<Dynamic>=[];
 var codenameCharacterScopes:Array<Dynamic>=[];
 var comboGroup:Dynamic=null;
 var codenameNativeEventTweens:Map<String,FlxTween>=[];
 var codenameNativeEventResumeTweens:Map<String,FlxTween>=[];
 var paused=false;
 var camGame=new FlxCamera();
 var camHUD=new FlxCamera();
 var curStage:Dynamic={defaultZoom:0.6};
 var defaultCamZoom:Float=1;
 var defaultHudZoom:Float=1;
 var baseCameraZoom:Null<Float>=null;
 var codenameCameraModuloActive=false;
 var codenameCameraModuloConfig:Dynamic=CodenameCameraModulo.defaults();
 var line=new Line();
 var calledName="";
 var calledArgs:Array<Dynamic>=[];
 public var scrollSpeed:Float=2;
 public function new() {}
 function callCodenameScripts(name:String,args:Array<Dynamic>):Void {calledName=name;calledArgs=args;}
 function setGameCameraZoom(value:Float):Void camGame.zoom=value;
 function applyCodenameCameraPosition(_params:Array<Dynamic>):Void throw "unexpected position route";
 function applyCodenameCameraMovement(_params:Array<Dynamic>):Void throw "unexpected movement route";
 function releaseCodenameCameraControl():Void {}
 function getCodenameInputLine(index:Int):Line return index==1?line:null;
 static function near(a:Float,b:Float,label:String):Void if(Math.abs(a-b)>0.00001)throw label+": "+a+" != "+b;
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 function event(name:String,params:Array<Dynamic>):Bool return applyCodenameNativeEvent({name:name,params:params});
''' + helpers + r'''
 function run():Void {
  check(!event("camera zoom",[false,9]) && !event(" Camera Zoom",[false,9]),"custom name triggered builtin");
  check(!event("Change Scroll Speed",[false,9]),"legacy name triggered builtin");
  event("HScript Call",["songEvents","white, red"]);
  check(calledName=="songEvents" && calledArgs.length==2 && calledArgs[0]=="white"
   && calledArgs[1]==" red","HScript argument strings retain source spacing");
  event("HScript Call",["blackOut",""]);
  check(calledName=="blackOut" && calledArgs.length==1 && calledArgs[0]=="",
   "HScript empty argument follows source split");
  event("Alt Animation Toggle",[true,true,1]);
  check(line.altAnim && line.characters[0].idleSuffix=='-alt',"alt sing and idle toggle");
  event("Alt Animation Toggle",[false,false,1]);
  check(!line.altAnim && line.characters[0].idleSuffix=='',"alt sing and idle reset");
  check(event("Alt Animation Toggle",[true,true,8]),"absent source line should be consumed");
  var actor=line.characters[0];
  check(event("Play Animation",[1,"locked",false,"LOCK"]),"Play Animation should be handled");
  check(actor.playedName=="locked" && actor.playedForce==false && actor.playedContext=="LOCK",
   "Play Animation force and LOCK context");
  event("Play Animation",[1,"plain",null,"NONE"]);
  check(actor.playedName=="plain" && actor.playedForce==null && actor.playedContext==null,
   "Play Animation NONE context and nullable force");
  event("Add Camera Zoom",[.04,"camGame"]);near(camGame.zoom,1.04,"CNE game zoom pulse");
  event("Add Camera Zoom",[.02,"camHUD"]);near(camHUD.zoom,1.02,"CNE HUD zoom pulse");
  camGame.zoom=1;camHUD.zoom=1;
  event("Camera Zoom",[false,1.4,"camGame",4,"CLASSIC","In","direct",false]);
  near(camGame.zoom,1.4,"false precedes CLASSIC");near(defaultCamZoom,1.4,"immediate default");
  event("Camera Zoom",[true,2,"camGame",4,"CLASSIC","In","direct",false]);
  near(camGame.zoom,1.4,"classic retains current");near(defaultCamZoom,2,"classic default");
  event("Camera Zoom",[false,2,"camHUD",4,"linear","In","stage",true]);
  near(camHUD.zoom,1.2,"stage baseline HUD multiplication");near(defaultHudZoom,1.2,"HUD default");
  FlxCamera.defaultZoom=.5;
  event("Camera Zoom",[false,2,"camGame",4,"linear","In","direct",true]);
  near(camGame.zoom,1.4,"direct baseline times live zoom");FlxCamera.defaultZoom=1;
  event("Camera Zoom",[true,3,"camGame",4,"quad","Out","direct",false]);
  var old=codenameNativeEventTweens.get("camGame.zoom");
  near(old.duration,.5,"steps duration");old.advance(.5);
  near(camGame.zoom,2.6,"direction ease");near(defaultCamZoom,1.4,"default samples camera at onUpdate");
  event("Camera Zoom",[true,.8,"camHUD",8,"linear","In","direct",false]);
  var hud=codenameNativeEventTweens.get("camHUD.zoom");
  event("Camera Zoom",[false,1.1,"camGame",4,"linear","In","direct",false]);
  check(old.cancelled && hud.active,"replacement cancels only chosen camera");
  old.advance(1);near(camGame.zoom,1.1,"cancelled action stayed stopped");
  near(defaultCamZoom,1.1,"cancelled completion stayed stopped");
  hud.advance(1);near(defaultHudZoom,.8,"HUD completion");
  check(!codenameNativeEventTweens.exists("camHUD.zoom"),"completed tween retained");
  event("Scroll Speed Change",[false,3,4,"linear","In",false]);
  event("Scroll Speed Change",[false,.5,4,"linear","In",true]);near(scrollSpeed,1.5,"live multiplicative speed");
  event("Scroll Speed Change",[true,3,2,"quad","Out",false]);
  var speed=codenameNativeEventTweens.get("scrollSpeedTween");near(speed.duration,.25,"speed step duration");
  speed.advance(.5);near(scrollSpeed,2.625,"speed easing");
  event("Scroll Speed Change",[true,.5,2,"linear","In",true]);
  check(speed.cancelled,"speed replacement");
  var replacement=codenameNativeEventTweens.get("scrollSpeedTween");
  paused=true;setCodenameScriptsPaused(true);setCodenameScriptsPaused(true);
  check(!replacement.active,"paused tween active");replacement.advance(1);near(scrollSpeed,2.625,"paused advanced");
  paused=false;setCodenameScriptsPaused(false);replacement.advance(1);near(scrollSpeed,1.3125,"replacement samples live speed");
  event("Camera Zoom",[true,2,"camGame",4,"linear","In","direct",false]);
  var inactive=codenameNativeEventTweens.get("camGame.zoom");inactive.active=false;
  paused=true;setCodenameScriptsPaused(true);paused=false;setCodenameScriptsPaused(false);
  check(!inactive.active,"pre-inactive tween revived");
  paused=true;
  event("Scroll Speed Change",[true,4,4,"linear","In",false]);
  var bornPaused=codenameNativeEventTweens.get("scrollSpeedTween");check(!bornPaused.active,"new tween escaped pause");
  event("Scroll Speed Change",[false,2,4,"linear","In",false]);
  paused=false;setCodenameScriptsPaused(false);check(!bornPaused.active && bornPaused.cancelled,"replaced paused tween revived");
  clearCodenameNativeEventTweens();check(inactive.cancelled,"teardown retained tween");
  check(!codenameNativeEventTweens.iterator().hasNext(),"teardown map retained");
 }
 static function main():Void new Main().run();
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as scratch:
            path=Path(scratch); (path/'Main.hx').write_text(fixture, newline='\n')
            result=subprocess.run([*HAXE_COMMAND, '-cp', str(path), '--run', 'Main'],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':
    unittest.main()
