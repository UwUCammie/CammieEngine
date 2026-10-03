"""Exercise the production indexed Camera Movement handler with camera/tween fakes."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    match = re.search(r'\t(?:public )?(?:static )?function ' + name + r'\(', source)
    if match is None:
        raise AssertionError(name)
    start = match.start()
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameIndexedCameraMovementTest(unittest.TestCase):
    def test_source_index_snap_tween_replacement_and_missing_runtime(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        names = (
            'codenameEventNumber', 'codenameEventBoolean', 'codenameEventText',
            'restoreCodenameCameraFollow', 'cancelCodenameCameraMovement',
            'cancelCodenameNativeEventTween', 'trackCodenameNativeEventTween',
            'finishCodenameNativeEventTween', 'applyCodenameCameraMovement',
        )
        helpers = '\n'.join(method(source, name) for name in names)
        fixture = r'''
using StringTools;
class Conductor { public static var stepCrochet:Float=125; }
class Point {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
}
class Camera {
 public var scroll=new Point(); public var width=800; public var height=600;
 public var followEnabled=true; public var target:Dynamic={}; public var snaps=0;
 public function new() {}
 public function snapToTarget():Void snaps++;
}
class FlxTween {
 public var active=true; public var cancelled=false;
 public var duration:Float; public var options:Dynamic; public var destination:Dynamic;
 public static function tween(target:Dynamic,destination:Dynamic,duration:Float,options:Dynamic):FlxTween {
  var t=new FlxTween();t.destination=destination;t.duration=duration;t.options=options;return t;
 }
 public function new() {}
 public function cancel():Void {active=false;cancelled=true;}
 public function finish():Void {active=false;options.onComplete(this);}
}
class Main {
 var camGame=new Camera(); var camFollow=new Point(250,180); var curCamPos:FlxTween=null;
 var codenameActors:Dynamic={}; var plan:Dynamic={lines:[{}, {}, {}, {}]};
 var codenameEventDiagnostics:Map<String,Bool>=[];
 var codenameNativeEventTweens:Map<String,FlxTween>=[];
 var codenameNativeEventResumeTweens:Map<String,FlxTween>=[];
 var codenameCameraFollowSuspended=false; var codenameCameraSavedFollow=true;
 var codenameCameraControlled=true; var focusCameraDrivesFollow=false;
 var scriptableCamera='true'; var curCameraTarget=-1; var paused=false;
 var moves:Array<Int>=[]; var callbackTarget:Null<Int>=null;
 public function new() {}
 function getCodenameActorPlan():Dynamic return plan;
 function moveCodenameCamera():Bool {
  moves.push(curCameraTarget);
  if (callbackTarget!=null) curCameraTarget=callbackTarget;
  // An empty authored line retains the previous follow point.
  if (curCameraTarget==3) camFollow.x=950;
  return true;
 }
 function codenameEventEase(name:String,direction:String):Dynamic return name+'-'+direction;
 static function check(ok:Bool,label:String):Void if(!ok) throw label;
 static function near(a:Float,b:Float,label:String):Void if(Math.abs(a-b)>0.00001) throw label+': '+a+' != '+b;
''' + helpers + r'''
 function run():Void {
  // Index 3 is an authored extra line, beyond the native BF/dad/GF slots.
  applyCodenameCameraMovement([3,false,4,'linear','Out']);
  check(curCameraTarget==3&&moves.length==1&&moves[0]==3,'extra source index projected to native role');
  check(camGame.snaps==1&&!codenameCameraControlled&&focusCameraDrivesFollow,'forced false did not snap source target');
  near(camFollow.x,950,'selected actor focus');
  applyCodenameCameraMovement([2,true,4,'CLASSIC','In']);
  check(curCameraTarget==2&&moves[1]==2&&!codenameNativeEventTweens.exists('cameraMovement'),
   'valid empty line should select without tween');
  near(camFollow.x,950,'empty line moved focus');
  applyCodenameCameraMovement([1,true,8,'linear','Out']);
  var first=codenameNativeEventTweens.get('cameraMovement');
  check(first!=null&&!camGame.followEnabled&&codenameCameraFollowSuspended,'indexed tween not started');
  near(first.duration,1,'step duration');
  near(first.destination.x,550,'scroll destination x');
  near(first.destination.y,-120,'scroll destination y');
  check(first.options.ease=='linear-Out','ease direction');
  applyCodenameCameraMovement([3,true,4,'linear','In']);
  var second=codenameNativeEventTweens.get('cameraMovement');
  check(first.cancelled&&second!=first&&!camGame.followEnabled,'replacement did not restore then suspend');
  first.finish();check(!camGame.followEnabled,'cancelled tween completed newer movement');
  second.finish();check(camGame.followEnabled&&!codenameCameraFollowSuspended
   &&!codenameNativeEventTweens.exists('cameraMovement'),'completion did not restore follow');
  var priorMoves=moves.length, priorSnaps=camGame.snaps;
  applyCodenameCameraMovement([99,false]);
  check(curCameraTarget==99&&moves.length==priorMoves&&camGame.snaps==priorSnaps,
   'invalid index should select only');
  plan=null;
  applyCodenameCameraMovement([0,false]);
  check(codenameEventDiagnostics.exists('Camera Movement needs a live selected-owner actor plan and runtime')
   &&moves.length==priorMoves&&camGame.snaps==priorSnaps,'missing actor plan silently consumed');
  plan={lines:[{}]};codenameActors=null;
  applyCodenameCameraMovement([0,false]);
  check(moves.length==priorMoves&&camGame.snaps==priorSnaps,'missing actor runtime used native fallback');
  plan={lines:[{}, {}, {}, {}]};codenameActors={};
  callbackTarget=99;
  applyCodenameCameraMovement([1,false]);
  check(moves.length==priorMoves+1&&curCameraTarget==99&&camGame.snaps==priorSnaps,
   'callback invalidation still snapped');
  applyCodenameCameraMovement([1,true,4,'linear','In']);
  check(!codenameNativeEventTweens.exists('cameraMovement'),
   'callback invalidation still tweened');
 }
 public static function main():Void {new Main().run();Sys.println('indexed camera movement ok');}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder) / 'Main.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('indexed camera movement ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
