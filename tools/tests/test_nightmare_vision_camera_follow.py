"""Execute shared NMV section following, callback order and render-rate independence."""
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
from test_nightmare_vision_camera_helpers import extract_method
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class NightmareVisionCameraFollowTest(unittest.TestCase):
    def test_source_actor_offsets_turn_callbacks_and_fixed_tick_order(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        methods = "\n".join(extract_method(source, marker) for marker in [
            "@:keep public function getCharacterCameraPos", "@:keep public function moveCameraSection",
            "function applyNightmareVisionSingDisplacement(", "@:keep public function moveCamera("])
        start = source.index("\t\tsourceBatch.dispatchUpdate(function(index, sourceElapsed)")
        end = source.index("\n\t\tif (smokeProfileAt", start)
        dispatch = source[start:end]
        fixture = r"""
class FlxPoint {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
 public static function weak():FlxPoint return new FlxPoint();
 public function put():Void {} public function putWeak():Void {} public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class Character {
 public var isPlayer:Bool; public var cameraPosition:Array<Float>=[0,0];
 public var x:Float; public var y:Float;
 public function new(player:Bool,x:Float,y:Float) {isPlayer=player;this.x=x;this.y=y;}
 public function getMidpoint():FlxPoint return new FlxPoint(x,y);
 public function getSingDisplacement():FlxPoint return FlxPoint.weak();
}
class Group {
 public var turn:String=''; public function new() {}
 public function set(name:String,value:String):Void turn=value;
}
class Scripts {public var group=new Group();public function new() {}}
class Batch {
 public var tickCount:Int; public function new(count:Int) tickCount=count;
 public function dispatchUpdate(fn:Int->Float->Void):Void for(i in 0...tickCount) fn(i,1/60);
}
class NightmareVisionFlxGView {
 public static function runSourceTick(clock:Dynamic,index:Int,count:Int,fn:Void->Void):Void fn();
}
class State {
 public var nightmareVisionScripts:Scripts=new Scripts();
 public var nightmareVisionPrefs:Dynamic={view:{camFollowsCharacters:true}};
 public var psychCameraCompatibilityActive:Bool=false;
 public var boyfriend=new Character(true,1000,500);
 public var dad=new Character(false,400,600);
 public var gf=new Character(false,600,300);
 public var camCurTarget:Character=null;
 public var boyfriendCameraOffset:Array<Float>=[11,12];
 public var opponentCameraOffset:Array<Float>=[21,22];
 public var girlfriendCameraOffset:Array<Float>=[31,32];
 public var camFollow=new FlxPoint();
 public var SONG:Dynamic={notes:[{mustHitSection:true,gfSection:false}]};
 public var curSection:Int=0;public var defaultCamZoom:Float=.55;
 public var generatedMusic=true;public var endingSong=false;public var forceCamera=false;
 public var isCameraOnForcedPos=false;public var compatScriptClock:Dynamic=null;
 public var calls:Array<String>=[]; public var callbackTurns:Array<String>=[];
 public var playerOwner:Character=null;public var opponentOwner:Character=null;
 public function new() {playerOwner=boyfriend;opponentOwner=dad;boyfriend.cameraPosition=[110,-10];dad.cameraPosition=[-200,-20];gf.cameraPosition=[5,6];}
 function getNightmareVisionField(id:Int):Dynamic return {owner:id==0?playerOwner:opponentOwner};
 function setCameraFollowActor(actor:Character,role:String):Void throw 'native camera used';
 function callAllHScript(name:String,args:Array<Dynamic>):Dynamic throw 'Psych callback leaked into NMV';
 function callNightmareVision(name:String,args:Array<Dynamic>):Dynamic {
  calls.push(name+':'+Std.string(args[0]));
  if(name=='onMoveCamera') {callbackTurns.push(nightmareVisionScripts.group.turn);defaultCamZoom=args[0]=='boyfriend' ? 0.75 : 0.6;}
  if(name=='onUpdate') camFollow.x+=7; // Callback must see the source target first.
  return null;
 }
__METHODS__
 public function tick(count:Int):Void {
  var sourceBatch=new Batch(count);
__DISPATCH__
 }
}
class Main {
 static function check(ok:Bool,msg:String):Void if(!ok)throw msg;
 static function close(a:Float,b:Float):Bool return Math.abs(a-b)<.00001;
 static function point(s:State,x:Float,y:Float,msg:String):Void check(close(s.camFollow.x,x)&&close(s.camFollow.y,y),msg);
 static function main():Void {
  var s=new State();s.moveCameraSection();point(s,801,402,'BF source position/sign/stage offset');
  check(s.defaultCamZoom==.75&&s.nightmareVisionScripts.group.turn=='boyfriend','authored BF callback zoom/turn');
  s.SONG.notes[0].mustHitSection=false;s.moveCameraSection();point(s,321,502,'opponent uses source 100, not Psych 150');
  check(s.calls[s.calls.length-1]=='onMoveCamera:dad'&&s.defaultCamZoom==.6,'dad callback');
  s.SONG.notes[0].gfSection=true;s.moveCameraSection();point(s,636,338,'GF source midpoint and its own stage offset');
  check(s.nightmareVisionScripts.group.turn=='gf'&&s.callbackTurns[2]=='dad','GF callback precedes turn change');
  check(s.callbackTurns[0]=='boyfriend'&&s.callbackTurns[1]=='dad','normal callback follows turn change');
  s.SONG.notes[0].gfSection=false;s.playerOwner=new Character(true,1200,700);
  s.SONG.notes[0].mustHitSection=true;s.moveCameraSection();point(s,1111,612,'field owner override');
  s.camCurTarget=new Character(false,700,800);s.moveCameraSection();point(s,821,722,'explicit actor override uses player flag');
  s.camCurTarget=null;s.playerOwner=s.boyfriend;s.calls=[];s.tick(0);check(s.calls.length==0,'uncapped render without source tick');
  s.tick(3);point(s,808,402,'follow precedes onUpdate on every source tick');
  check(s.calls.length==6&&s.calls[0]=='onMoveCamera:boyfriend'&&s.calls[1].indexOf('onUpdate:')==0,'source callback order/count');
  s.isCameraOnForcedPos=true;s.calls=[];s.tick(2);point(s,822,402,'forced target remains script owned');
  check(s.calls.length==2&&s.calls[0].indexOf('onUpdate:')==0,'forced camera skips follow callback');
  s.isCameraOnForcedPos=false;s.endingSong=true;s.calls=[];s.tick(1);check(s.calls.length==1,'ending does not follow');
  s.endingSong=false;s.forceCamera=true;s.calls=[];s.tick(1);check(s.calls.length==1,'explicit native forced camera preserved');
  s.moveCameraSection(-2);check(s.calls[s.calls.length-1]=='onMoveCamera:boyfriend','explicit section API');
  s.calls=[];s.moveCameraSection(100);check(s.calls.length==0,'invalid section no callback');
 }
}
""".replace("__METHODS__", methods).replace("__DISPATCH__", dispatch)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"], cwd=ROOT,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        update = source[source.index("if (generatedMusic && PlayState.SONG.notes[curSection] != null)"):]
        self.assertLess(update.index("else if (nightmareVisionScripts != null)"), update.index("switch(scriptableCamera)"))

if __name__ == "__main__": unittest.main()
