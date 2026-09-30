"""Execute NMV camera helpers extracted from both donor and local PlayState."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
DONOR = ROOT.parent / "FNF-Example-Mods/misc/nightmare_vision_source_code/source/funkin/states/PlayState.hx"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


class NightmareVisionCameraHelpersTest(unittest.TestCase):
    def test_helpers_match_donor_offsets_and_snap_lock_semantics(self):
        local_source = (ROOT / "source/PlayState.hx").read_text()
        donor_source = DONOR.read_text()
        work = Path(tempfile.mkdtemp(dir=ROOT / "tmp"))
        self.addCleanup(lambda: __import__("shutil").rmtree(work, ignore_errors=True))

        local_offset_methods = local_source[
            local_source.index("\t@:keep public var boyfriendCameraOffset(get, set):Array<Float>;"):
            local_source.index("\t/** NMV's explicit camera helper", local_source.index("\t@:keep public var boyfriendCameraOffset(get, set):Array<Float>;"))
        ]
        fields = re.findall(
            r"^\s*var psychStageCamera(?:Boyfriend|Opponent|Girlfriend):Array<Float> = \[0, 0\];$",
            local_source,
            re.MULTILINE,
        )
        self.assertEqual(len(fields), 3, "all three production camera offset backing arrays are present")
        local_methods = "\n".join([
            extract_method(local_source, "@:keep public function getCharacterCameraPos"),
            extract_method(local_source, "@:keep public function snapCamToPos"),
        ])
        donor_camera = extract_method(donor_source, "public function getCharacterCameraPos")
        donor_snap = extract_method(donor_source, "function snapCamToPos")
        donor_camera = donor_camera.replace("getCharacterCameraPos", "donorGetCharacterCameraPos", 1)
        donor_snap = donor_snap.replace("snapCamToPos", "donorSnapCamToPos", 1)
        donor_snap = donor_snap.replace("function donorSnapCamToPos", "public function donorSnapCamToPos", 1)

        (work / "Main.hx").write_text(r'''
class FlxPoint {
 public var x:Float;
 public var y:Float;
 public var isWeak:Bool;
 public function new(x:Float=0, y:Float=0, isWeak:Bool=false) {
  this.x=x; this.y=y; this.isWeak=isWeak;
 }
 public static function weak(x:Float=0, y:Float=0):FlxPoint return new FlxPoint(x, y, true);
 public static function get(x:Float=0, y:Float=0):FlxPoint return new FlxPoint(x, y, false);
}
class Character {
 public var name:String;
 public var isPlayer:Bool;
 public var cameraPosition:Array<Float>;
 public var midpointX:Float;
 public var midpointY:Float;
 public function new(name:String, isPlayer:Bool, x:Float, y:Float, cameraX:Float, cameraY:Float) {
  this.name=name; this.isPlayer=isPlayer; midpointX=x; midpointY=y;
  cameraPosition=[cameraX,cameraY];
 }
 public function getMidpoint():FlxPoint return FlxPoint.get(midpointX, midpointY);
}
class FollowTarget {
 public var x:Float=0;
 public var y:Float=0;
 public function new() {}
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class CameraStub {
 public var snapCount:Int=0;
 public function new() {}
 public function snapToTarget():Void snapCount++;
}
class FlxG { public static var camera:CameraStub = new CameraStub(); }

class ProductionCameraState {
 public var camFollow:FollowTarget = new FollowTarget();
 public var isCameraOnForcedPos:Bool = false;
 public function new() {}
 // Production camera-offset storage, live script properties, and helpers:
__LOCAL_FIELDS__
__LOCAL_OFFSET_METHODS__
__LOCAL_CAMERA_METHODS__
}
class DonorCameraState {
 public var camFollow:FollowTarget = new FollowTarget();
 public var isCameraOnForcedPos:Bool = false;
 public var boyfriendCameraOffset:Array<Float> = [0,0];
 public var opponentCameraOffset:Array<Float> = [0,0];
 public var girlfriendCameraOffset:Array<Float> = [0,0];
 public function new() {}
__DONOR_CAMERA__
__DONOR_SNAP__
}
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function close(a:Float,b:Float):Bool return Math.abs(a-b)<0.00001;
 static function samePoint(a:FlxPoint,b:FlxPoint,message:String):Void
  check(close(a.x,b.x)&&close(a.y,b.y),message+' expected ('+b.x+','+b.y+') got ('+a.x+','+a.y+')');
 static function compareCamera(local:ProductionCameraState, donor:DonorCameraState, actor:Character, label:String):FlxPoint {
  var actual=local.getCharacterCameraPos(actor);
  var expected=donor.donorGetCharacterCameraPos(actor);
  samePoint(actual,expected,label+' matches supplied donor formula');
  return actual;
 }
 static function main():Void {
  var local=new ProductionCameraState();
  var donor=new DonorCameraState();
  local.boyfriendCameraOffset=[11.0,13.0]; donor.boyfriendCameraOffset=[11.0,13.0];
  local.opponentCameraOffset=[-7.0,14.0]; donor.opponentCameraOffset=[-7.0,14.0];
  local.girlfriendCameraOffset=[500.0,700.0]; donor.girlfriendCameraOffset=[500.0,700.0];

  var player=new Character('bf',true,1000,400,8,9);
  var playerPoint=compareCamera(local,donor,player,'player camera position');
  check(close(playerPoint.x,903)&&close(playerPoint.y,322),'player uses boyfriend offset and source cameraPosition');
  var opponent=new Character('dad',false,500,600,2,3);
  var opponentPoint=compareCamera(local,donor,opponent,'opponent camera position');
  check(close(opponentPoint.x,595)&&close(opponentPoint.y,517),'non-player uses opponent offset');

  // GF helpers call getCharacterCameraPos with a non-player Character. The
  // source method intentionally branches on isPlayer, not the actor's name.
  var gf=new Character('gf',false,250,350,4,5);
  var gfPoint=compareCamera(local,donor,gf,'GF camera position');
  check(close(gfPoint.x,347)&&close(gfPoint.y,269),'GF uses opponent offset by isPlayer source rule');

  var replacement=[20.0,30.0];
  local.boyfriendCameraOffset=replacement;
  donor.boyfriendCameraOffset=replacement;
  check(local.boyfriendCameraOffset==replacement,'setter keeps replacement array identity');
  var changed=compareCamera(local,donor,player,'replaced offset array');
  check(close(changed.x,912)&&close(changed.y,339),'replacement offset affects the next camera query');
  replacement[0]=25.0; replacement[1]=35.0;
  donor.boyfriendCameraOffset=replacement;
  changed=compareCamera(local,donor,player,'mutated live offset array');
  check(close(changed.x,917)&&close(changed.y,344),'in-place array mutation affects the next camera query');

  var nullPosition=local.getCharacterCameraPos(null);
  check(nullPosition.isWeak&&nullPosition.x==0&&nullPosition.y==0,'null actor returns weak zero point');

  local.isCameraOnForcedPos=true; donor.isCameraOnForcedPos=true;
  local.snapCamToPos(18,29,false); donor.donorSnapCamToPos(18,29,false);
  check(local.camFollow.x==donor.camFollow.x&&local.camFollow.y==donor.camFollow.y,
   'snapCamToPos positions follow target like donor');
  check(local.isCameraOnForcedPos&&donor.isCameraOnForcedPos,
   'lockPosition=false preserves an existing camera lock');
  local.isCameraOnForcedPos=false; donor.isCameraOnForcedPos=false;
  local.snapCamToPos(-3,7,true); donor.donorSnapCamToPos(-3,7,true);
  check(local.isCameraOnForcedPos&&donor.isCameraOnForcedPos,'lockPosition=true enables camera lock');
  check(FlxG.camera.snapCount==4,'both helpers snap the normal camera target on every call');
  Sys.println('nightmare-vision-camera-helpers-ok');
 }
}
'''
            .replace("__LOCAL_FIELDS__", "\n".join(fields))
            .replace("__LOCAL_OFFSET_METHODS__", local_offset_methods)
            .replace("__LOCAL_CAMERA_METHODS__", local_methods)
            .replace("__DONOR_CAMERA__", donor_camera)
            .replace("__DONOR_SNAP__", donor_snap))

        result = subprocess.run(
            [str(HAXE), "-cp", str(work), "--run", "Main"],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nightmare-vision-camera-helpers-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
