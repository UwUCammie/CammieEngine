"""Execute the Codename position controller with deterministic camera boundaries."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class CodenameCameraPositionTest(unittest.TestCase):
    def test_relative_snap_classic_tween_and_follow_ownership(self):
        source=(ROOT/'source/PlayState.hx').read_text()
        def method(name):
            match=re.search(r'\t(?:public )?(?:static )?function '+name+r'\(',source)
            self.assertIsNotNone(match,name)
            begin=match.start();brace=source.index('{',begin);depth=0
            for at in range(brace,len(source)):
                depth+=(source[at]=='{')-(source[at]=='}')
                if depth==0:return source[begin:at+1]
            raise AssertionError(name)
        methods='\n'.join(method(name) for name in (
            'applyCodenameCameraPosition','restoreCodenameCameraFollow',
            'cancelCodenameCameraMovement','releaseCodenameCameraControl',
            'codenameEventNumber','codenameEventBoolean','codenameEventText',
            'codenameEventEase','resolveFocusCameraEase',
            'trackCodenameNativeEventTween','finishCodenameNativeEventTween',
            'cancelCodenameNativeEventTween','clearCodenameNativeEventTweens',
            'setCodenameScriptsPaused'))
        fixture=r'''
class FlxObject {
 public var x:Float=0;public var y:Float=0;
 public function new() {}
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class Camera {
 public var target:FlxObject;
 public var scroll=new FlxObject();
 public var width:Float=1280;public var height:Float=720;
 public var snaps=0;public var followEnabled=true;public var followLerp:Float=.08;
 public function new(target:FlxObject) this.target=target;
 public function snapToTarget():Void {snaps++;scroll.setPosition(target.x-width/2,target.y-height/2);}
}
class Conductor {public static var stepCrochet:Float=125;}
@:keep class FlxEase {
 public static function linear(x:Float):Float return x;
 public static function quadOut(x:Float):Float return 1-(1-x)*(1-x);
}
class FlxTween {
 public var active=true;public var finished=false;public var cancelled=false;
 public var duration:Float;public var opts:Dynamic;public var fields:Dynamic;
 var obj:Dynamic;
 public function new() {}
 public function cancel():Void {active=false;cancelled=true;}
 public static function tween(obj:Dynamic,fields:Dynamic,duration:Float,opts:Dynamic):FlxTween {
  var t=new FlxTween();t.obj=obj;t.fields=fields;t.duration=duration;t.opts=opts;return t;
 }
 public function complete():Void {
  if(!active)return;
  for(k in Reflect.fields(fields))Reflect.setProperty(obj,k,Reflect.field(fields,k));
  finished=true;active=false;if(opts.onComplete!=null)opts.onComplete(this);
 }
}
class Main {
 public function new() {}
 var camFollow=new FlxObject();var camGame:Camera;
 var curCamPos:FlxTween=null;
 var curCameraTarget=7;var codenameCameraControlled=false;
 var codenameCameraFollowSuspended=false;
 var codenameCameraSavedFollow=true;
 static inline var DONOR_CAMERA_FOLLOW_RATE:Float=.04;
 var focusCameraDrivesFollow=false;var paused=false;
 var codenameScriptScopes:Array<Dynamic>=[];
 var codenameCharacterScopes:Array<Dynamic>=[];
 var comboGroup:Dynamic=null;
 var codenameNativeEventTweens:Map<String,FlxTween>=[];
 var codenameNativeEventResumeTweens:Map<String,FlxTween>=[];
 static function check(v:Bool,msg:String):Void if(!v)throw msg;
 static function near(a:Float,b:Float,msg:String):Void if(Math.abs(a-b)>.00001)throw msg+": "+a+" != "+b;
''' + methods + r'''
 function run():Void {
  camGame=new Camera(camFollow);camFollow.setPosition(300,400);
  applyCodenameCameraPosition([20,-30,false,4,"CLASSIC","In",true]);
  near(camFollow.x,320,"relative x");near(camFollow.y,370,"relative y");
  near(camGame.scroll.x,-320,"snap viewport x");near(camGame.scroll.y,10,"snap viewport y");
  check(camGame.snaps==1 && curCameraTarget == -1 && codenameCameraControlled,"fixed mode/snap");
  applyCodenameCameraPosition([700,500]);
  near(camFollow.x,700,"absolute x");near(camGame.scroll.x,-320,"default CLASSIC glides");
  check(!codenameNativeEventTweens.exists("cameraMovement") && focusCameraDrivesFollow,"classic tween/default rate");
  curCamPos=new FlxTween();
  applyCodenameCameraPosition([900,700,true,8,"quad","Out",false]);
  var old=codenameNativeEventTweens.get("cameraMovement");
  check(curCamPos.cancelled && !camGame.followEnabled && codenameCameraFollowSuspended,"legacy tween cancelled and follow suspended");
  near(old.duration,1,"steps duration");near(old.opts.ease(.5),.75,"direction ease");
  near(old.fields.x,260,"target x");near(old.fields.y,340,"target y");
  // The next relative event must use the authored follow point, not scroll.
  applyCodenameCameraPosition([10,20,true,2,"linear","In",true]);
  var replacement=codenameNativeEventTweens.get("cameraMovement");
  check(old.cancelled && !camGame.followEnabled,"replacement suspension");
  near(camFollow.x,910,"replacement relative x");near(camFollow.y,720,"replacement relative y");
  // A late callback from an old tween must not restore a newer lease.
  old.opts.onComplete(old);check(!camGame.followEnabled,"stale completion restored follow");
  paused=true;setCodenameScriptsPaused(true);replacement.complete();
  check(!replacement.finished && !camGame.followEnabled,"pause lost tween/follow");
  paused=false;setCodenameScriptsPaused(false);replacement.complete();
  check(camGame.target==camFollow && camGame.followEnabled && !codenameCameraFollowSuspended,"completion restores follow");
  near(camGame.scroll.x,270,"completed x");
  applyCodenameCameraPosition([100,200,true,4,"linear","In",false]);
  var interrupted=codenameNativeEventTweens.get("cameraMovement");
  applyCodenameCameraPosition([3,4,false,4,"CLASSIC","In",true]);
  check(interrupted.cancelled && camGame.target==camFollow && camGame.followEnabled && camGame.snaps==2,"snap interrupted tween/restored follow");
  near(camFollow.x,103,"snap relative to previous target");
  // A script-disabled follow state survives an event tween.
  camGame.followEnabled=false;
  applyCodenameCameraPosition([10,20,true,4,"linear","In",false]);
  codenameNativeEventTweens.get("cameraMovement").complete();
  check(!camGame.followEnabled && camGame.target==camFollow,"prior disabled flag lost");
  camGame.followEnabled=true;
  applyCodenameCameraPosition([10,20,true,4,"linear","In",false]);
  var destroyed=codenameNativeEventTweens.get("cameraMovement");
  clearCodenameNativeEventTweens();
  check(destroyed.cancelled && camGame.target==camFollow && camGame.followEnabled && !codenameCameraControlled,"teardown releases follow");
 }
 static function main():Void new Main().run();
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as work:
            path=Path(work);(path/'Main.hx').write_text(fixture, newline='\n')
            r=subprocess.run([*HAXE_COMMAND,'-cp',str(path),'--run','Main'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

if __name__=='__main__':unittest.main()
