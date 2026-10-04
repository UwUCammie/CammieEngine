"""Execute production NMV sing offsets through the shared camera helpers."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
from test_nightmare_vision_camera_helpers import extract_method
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionCameraDisplacementTest(unittest.TestCase):
    def test_character_offsets_fresh_camera_targets_and_source_clock(self):
        character_source = (ROOT / "source/Character.hx").read_text(encoding="utf-8")
        play_source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        character_methods = "\n".join([
            extract_method(character_source, "public static function animationName("),
            extract_method(character_source, "@:keep public function getSingDisplacement()"),
        ])
        play_methods = "\n".join([
            extract_method(play_source, "@:keep public function getCharacterCameraPos("),
            extract_method(play_source, "@:keep public function moveCameraSection("),
            extract_method(play_source, "function applyNightmareVisionSingDisplacement("),
            extract_method(play_source, "@:keep public function moveCamera("),
        ])

        dispatch_start = play_source.index("\t\tsourceBatch.dispatchUpdate(function(index, sourceElapsed)")
        dispatch_end = play_source.index("\n\t\tif (smokeProfileAt", dispatch_start)
        source_dispatch = play_source[dispatch_start:dispatch_end]

        fixture = r'''
class FlxPoint {
 public var x:Float;
 public var y:Float;
 public var isWeak:Bool;
 public static var weakCreated:Int = 0;
 public static var weakReleased:Int = 0;
 public static var regularReleased:Int = 0;
 public function new(x:Float=0, y:Float=0, weak:Bool=false) {
  this.x=x; this.y=y; isWeak=weak;
 }
 public static function weak(x:Float=0, y:Float=0):FlxPoint {
  weakCreated++;
  return new FlxPoint(x,y,true);
 }
 public static function get(x:Float=0, y:Float=0):FlxPoint return new FlxPoint(x,y,false);
 public function put():Void if (!isWeak) regularReleased++;
 public function putWeak():Void if (isWeak) weakReleased++;
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}

class Character {
 public var name:String;
 public var isPlayer:Bool;
 public var cameraPosition:Array<Float>=[0,0];
 public var camDisplacement:Float=20;
 public var x:Float;
 public var y:Float;
 public var animation:Dynamic;
 public function new(name:String, player:Bool, x:Float, y:Float, ?animationName:String) {
  this.name=name; isPlayer=player; this.x=x; this.y=y;
  play(animationName);
 }
 public function play(name:String):Void {
  animation = name == null ? null : {curAnim:{name:name}};
 }
 public function getMidpoint():FlxPoint return FlxPoint.get(x,y);
__CHARACTER_METHODS__
}

class FollowTarget {
 public var x:Float=0;
 public var y:Float=0;
 public function new() {}
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}

class Group {
 public var turn:String='';
 public function new() {}
 public function set(name:String,value:String):Void turn=value;
}
class Scripts {
 public var group:Group=new Group();
 public function new() {}
}

class NightmareVisionFlxGView {
 public static function runSourceTick(clock:Dynamic,index:Int,count:Int,fn:Void->Void):Void fn();
}

class State {
 public var nightmareVisionScripts:Scripts=new Scripts();
 public var nightmareVisionPrefs:Dynamic={view:{camFollowsCharacters:true}};
 public var boyfriend:Character;
 public var dad:Character;
 public var gf:Character;
 public var camCurTarget:Character=null;
 public var boyfriendCameraOffset:Array<Float>=[11,12];
 public var opponentCameraOffset:Array<Float>=[21,22];
 public var girlfriendCameraOffset:Array<Float>=[31,32];
 public var camFollow:FollowTarget=new FollowTarget();
 public var SONG:Dynamic;
 public var curSection:Int=0;
 public var playerOwner:Character=null;
 public var opponentOwner:Character=null;
 public var psychCameraCompatibilityActive:Bool=false;
 public var compatScriptClock:CompatScriptClock=new CompatScriptClock();
 public var paused:Bool=false;
 public var generatedMusic:Bool=true;
 public var endingSong:Bool=false;
 public var isCameraOnForcedPos:Bool=false;
 public var forceCamera:Bool=false;
 public var moveCameraCallbacks:Int=0;
 public var updateCallbacks:Int=0;
 public var moveTargets:Array<Array<Float>>=[];
 public var updateElapsed:Array<Float>=[];
 public var overrideOnMove:Bool=false;
 public var overrideOnUpdate:Bool=false;
 public var scriptX:Float=9000;
 public var scriptY:Float=8000;
 public function new() {
  boyfriend=new Character('boyfriend',true,1000,500,'singLEFT');
  boyfriend.cameraPosition=[10,20];
  dad=new Character('dad',false,400,600,'singDOWN');
  dad.cameraPosition=[-200,-20];
  gf=new Character('gf',false,600,300,'singRIGHT');
  gf.cameraPosition=[5,6];
  SONG={notes:[{mustHitSection:true,gfSection:false}]};
 }
 function getNightmareVisionField(id:Int):Dynamic
  return {owner:id==0 ? playerOwner : opponentOwner};
 function setCameraFollowActor(actor:Character,role:String):Void {
  var point=getCharacterCameraPos(actor);
  camFollow.setPosition(point.x,point.y);
  point.put();
 }
 function callAllHScript(name:String,args:Array<Dynamic>):Dynamic return null;
 function callNightmareVision(name:String,args:Array<Dynamic>):Dynamic {
  if (name=='onMoveCamera') {
   moveCameraCallbacks++;
   moveTargets.push([camFollow.x,camFollow.y]);
   if (overrideOnMove) camFollow.setPosition(scriptX,scriptY);
  } else if (name=='onUpdate') {
   updateCallbacks++;
   updateElapsed.push(args[0]);
   if (overrideOnUpdate) camFollow.setPosition(scriptX,scriptY);
  }
  return null;
 }
__PLAY_METHODS__
 public function applyDisplacementForTest(actor:Character):Void
  applyNightmareVisionSingDisplacement(actor);
 public function tickFrame(elapsed:Float):Void {
  var sourceBatch=compatScriptClock.advance(paused ? 0 : elapsed);
__SOURCE_DISPATCH__
 }
}

class Main {
 static function fail(message:String):Void throw '[camera-displacement-test] '+message;
 static function check(value:Bool,message:String):Void if (!value) fail(message);
 static function close(a:Float,b:Float):Bool return Math.abs(a-b)<0.00001;
 static function point(actual:Dynamic,x:Float,y:Float,message:String):Void
  check(close(actual.x,x)&&close(actual.y,y),message+' expected ('+x+','+y+') got ('+actual.x+','+actual.y+')');
 static function displacement(actor:Character,name:String,x:Float,y:Float,message:String):Void {
  actor.play(name);
  var value=actor.getSingDisplacement();
  check(value.isWeak,message+' must use a pooled FlxPoint');
  point(value,x,y,message);
  value.putWeak();
 }
 static function runAtHostRate(rate:Int):State {
  var state=new State();
  state.boyfriend.play('singLEFT-hold');
  for (_ in 0...(rate)) state.tickFrame(1.0/rate);
  return state;
 }
 static function main():Void {
  var actor=new Character('test',true,0,0);
  check(actor.camDisplacement==20,'Character camera displacement default changed');
  displacement(actor,'singLEFT',-20,0,'left direction');
  displacement(actor,'singDOWN',0,20,'down direction');
  displacement(actor,'singUP',0,-20,'up direction');
  displacement(actor,'singRIGHT',20,0,'right direction');
  displacement(actor,'singLEFT-alt',-20,0,'direction before alternate suffix');
  displacement(actor,'singDOWN-hold',0,20,'sustained current animation');
  displacement(actor,'singLEFTmiss',0,0,'miss animation without a direction delimiter');
  displacement(actor,'idle',0,0,'idle animation');
  actor.animation=null;
  check(Character.animationName(actor)=='','null animation name is not empty');
  displacement(actor,'singRIGHT-alt2',20,0,'case-insensitive alternate suffix');
  actor.camDisplacement=0;
  displacement(actor,'singUP',0,0,'zero configured displacement');
  actor.camDisplacement=-7;
  displacement(actor,'singLEFT',7,0,'negative configured left displacement');
  displacement(actor,'singDOWN',0,-7,'negative configured down displacement');
  displacement(actor,'singUP',0,7,'negative configured up displacement');
  displacement(actor,'singRIGHT',-7,0,'negative configured right displacement');
  check(FlxPoint.weakReleased==FlxPoint.weakCreated,
   'all direct Character offsets release their weak points');

  var state=new State();
  // Fresh native camera position plus the current singer direction is applied
  // on every move, even while a sustain keeps the same animation active.
  state.moveCamera(false);
  point(state.camFollow,881,432,'boyfriend left sing target');
  state.moveCamera(false);
  point(state.camFollow,881,432,'repeated follow does not accumulate displacement');
  state.boyfriend.play('singRIGHT-hold');
  state.moveCamera(false);
  point(state.camFollow,921,432,'sustain reads the current right animation');
  state.moveCamera(false);
  point(state.camFollow,921,432,'repeated sustain follow starts from a fresh base');
  state.boyfriend.play('singLEFTmiss');
  state.moveCamera(false);
  point(state.camFollow,901,432,'miss animation does not move the camera');
  state.boyfriend.play('singLEFT-alt');
  state.moveCamera(false);
  point(state.camFollow,881,432,'alternate singer suffix still moves left');

  state.nightmareVisionPrefs.view.camFollowsCharacters=false;
  state.moveCamera(false);
  point(state.camFollow,901,432,'disabled camera-follow preference skips displacement');
  state.camFollow.setPosition(12,13);
  state.applyDisplacementForTest(state.boyfriend);
  point(state.camFollow,12,13,'disabled preference leaves an existing target untouched');
  state.nightmareVisionPrefs=null;
  state.applyDisplacementForTest(state.boyfriend);
  point(state.camFollow,12,13,'missing preferences leave an existing target untouched');
  state.applyDisplacementForTest(null);
  point(state.camFollow,12,13,'null actor leaves an existing target untouched');

  // Role selection, manifest-owned field overrides, and explicit targets all
  // use each selected Character's own animation and isPlayer camera convention.
  state=new State();
  state.moveCamera(true);
  point(state.camFollow,321,522,'dad down sing target');
  state.dad.play('singUP');
  state.moveCamera(true);
  point(state.camFollow,321,482,'dad up sing target');
  state.playerOwner=new Character('field-player-owner',true,1200,700,'singUP');
  state.playerOwner.cameraPosition=[30,40];
  state.moveCamera(false);
  point(state.camFollow,1081,632,'player field owner target');
  state.opponentOwner=new Character('field-opponent-owner',false,800,850,'singRIGHT');
  state.opponentOwner.cameraPosition=[14,15];
  state.moveCamera(true);
  point(state.camFollow,955,787,'opponent field owner target');
  state.camCurTarget=new Character('explicit-player-target',true,700,900,'singRIGHT-alt');
  state.camCurTarget.cameraPosition=[5,6];
  state.moveCamera(true);
  point(state.camFollow,626,818,'camCurTarget overrides the selected owner');

  // GF section targeting retains its own base formula before the same singer
  // offset is applied. A script callback may still claim the final target.
  state=new State();
  state.SONG.notes[0].gfSection=true;
  state.gf.play('singUP');
  state.moveCameraSection();
  point(state.camFollow,636,318,'GF source base plus up displacement');
  check(state.moveCameraCallbacks==1 && state.nightmareVisionScripts.group.turn=='gf',
   'GF camera callback and turn assignment still run');
  point({x:state.moveTargets[0][0],y:state.moveTargets[0][1]},636,318,
   'onMoveCamera observes the displaced target');
  state.overrideOnMove=true;
  state.moveCameraSection();
  point(state.camFollow,state.scriptX,state.scriptY,'onMoveCamera script retains final camera ownership');
  point({x:state.moveTargets[1][0],y:state.moveTargets[1][1]},636,318,
   'the callback receives a fresh GF base before script override');

  state=new State();
  state.overrideOnUpdate=true;
  state.tickFrame(1.0/60);
  point(state.camFollow,state.scriptX,state.scriptY,'onUpdate script can replace the singer target');
  check(state.moveCameraCallbacks==1 && state.updateCallbacks==1,
   'source onMoveCamera then onUpdate both run');

  // Execute the production source-batch dispatch with the real compatibility
  // clock: host refresh cadence must not change the 60 Hz camera follow path.
  var at30=runAtHostRate(30);
  var at60=runAtHostRate(60);
  var at240=runAtHostRate(240);
  for (sample in [at30,at60,at240]) {
   check(sample.moveCameraCallbacks==60 && sample.updateCallbacks==60,
    'one second of render time must produce 60 follow/update pairs');
   point(sample.camFollow,881,432,'source-clock camera position is host-rate independent');
   for (elapsed in sample.updateElapsed)
    check(close(elapsed,1.0/60),'source update delta depends on render frame rate');
  }
 }
}
'''.replace("__CHARACTER_METHODS__", character_methods).replace("__PLAY_METHODS__", play_methods).replace("__SOURCE_DISPATCH__", source_dispatch)

        with tempfile.TemporaryDirectory(prefix="nmv-camera-displacement-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", scratch, "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
