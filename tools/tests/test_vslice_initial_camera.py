"""Run the production V-Slice opening-camera methods with synthetic stage data."""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'source/PlayState.hx'


def method(source, name):
    start = source.index('\tfunction ' + name + '(')
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f'unclosed method {name}')


class VSliceInitialCameraTest(unittest.TestCase):
    def test_current_camera_zoom_is_resting_target_not_live_pulse(self):
        source = SOURCE.read_text()
        camera_alias = source[source.index('\tpublic var currentCameraZoom(get, set):Float;'):
                              source.index('\tpublic var cameraFollowPoint(get, never):FlxObject;')]
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as scratch:
            folder = Path(scratch)
            fixture = '''
class Camera { public var zoom:Float; public function new(zoom:Float) this.zoom=zoom; }
class CameraHarness {
 public var camGame:Camera=new Camera(1.3);
 public var defaultCamZoom:Float=1.3;
__ALIAS__
 function setGameCameraZoom(zoom:Float):Void camGame.zoom=zoom;
 public function new() {}
}
class Main {
 static function check(ok:Bool, why:String):Void if(!ok) throw why;
 static function main():Void {
  var camera=new CameraHarness();
  check(camera.currentCameraZoom==1.3,'initial stage target');
  camera.camGame.zoom=1.345;
  check(camera.currentCameraZoom==1.3,'temporary event pulse changed donor resting zoom');
  camera.currentCameraZoom=.55;
  check(camera.camGame.zoom==.55 && camera.currentCameraZoom==.55,'authored default change');
  camera.camGame.zoom=.595;
  check(camera.currentCameraZoom==.55,'new resting zoom must survive event pulse');
 }
}
'''.replace('__ALIAS__', camera_alias)
            (folder / 'Main.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(folder), '--run', 'Main'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_selected_owner_initial_opponent_focus_hold_and_authored_retarget(self):
        source = SOURCE.read_text()
        selected = method(source, 'selectedVSliceCameraSource')
        initialize = method(source, 'initializeVSliceCameraFocus')
        hold_start = source.index('\tfunction holdVSliceSectionCamera()')
        hold = source[hold_start:source.index(';', hold_start) + 1]
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as scratch:
            folder = Path(scratch)
            owner = folder / 'selected-owner'
            owner.mkdir()
            fixture = r'''
import sys.FileSystem;
typedef RootEntry = {engine:String,path:String};
typedef Manifest = {roots:Array<RootEntry>,selectedRoot:String};
class CompatScriptManifest {
 public static function selectedRoot(m:Manifest):String return m.selectedRoot;
 public static function destinationKey(v:String):String return v;
}
class ImportEngine { public static inline var V_SLICE='V-Slice'; }
class Character {
 public var x:Float;public var y:Float;
 public var charCamX:Float;public var charCamY:Float;
 public var stageCamX:Float;public var stageCamY:Float;
 public function new(x:Float,y:Float,cx:Float,cy:Float,sx:Float,sy:Float) {
  this.x=x;this.y=y;charCamX=cx;charCamY=cy;stageCamX=sx;stageCamY=sy;
 }
}
class Follow {
 public var x:Float=0;public var y:Float=0;
 public function new() {}
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
 public function getPosition():Follow return this;
}
class Camera {
 public var followCalls:Int=0;public var snapCalls:Int=0;
 public var lastLerp:Float=0;public var snappedX:Float=0;
 public function new() {}
 public function follow(f:Follow,lock:String,lerp:Float):Void {followCalls++;lastLerp=lerp;}
 public function focusOn(f:Follow):Void {snapCalls++;snappedX=f.x;}
}
class CameraHarness {
 public static inline var LOCKON='lockon';
 public var manifest:Manifest;
 public var dad:Character;
 public var camFollow:Follow=new Follow();
 public var camGame:Camera=new Camera();
 public var forceCamera:Bool=false;
 public var scriptableCamera:String='false';
 public var focusCameraDrivesFollow:Bool=false;
 public var vSliceCameraHoldsFocus:Bool=false;
 public function new(m:Manifest) manifest=m;
 function getCompatScriptManifest():Manifest return manifest;
 function camFollowLerp():Float return focusCameraDrivesFollow ? .04 : .08;
 function cameraTargetForActor(a:Character,role:String,x:Float,y:Float,turn:Bool):Array<Float>
  return [a.x+a.charCamX+a.stageCamX+x,a.y+a.charCamY+a.stageCamY+y];
__SELECTED__
__INITIALIZE__
__HOLD__
 public function init(?beforeX:Float=0,?beforeY:Float=0):Void initializeVSliceCameraFocus(beforeX,beforeY);
 public function held():Bool return holdVSliceSectionCamera();
 public function sourceSelected():Bool return selectedVSliceCameraSource();
}
class Main {
 static function check(ok:Bool,why:String):Void if(!ok) throw why;
 static function main():Void {
  var path='__OWNER__';
  var v:Manifest={selectedRoot:path,roots:[{engine:'V-Slice',path:path}]};
  var camera=new CameraHarness(v);
  camera.dad=new Character(500,300,10,-4,170,-10);
  check(camera.sourceSelected(),'positive selected source not recognized');
  camera.init();
  check(camera.camFollow.x==680 && camera.camFollow.y==286,'initial target lacks character/stage offsets');
  check(camera.camGame.snapCalls==1 && camera.camGame.snappedX==680
   && camera.camGame.lastLerp==.04,'opening did not snap at donor follow rate');
  check(camera.held(),'native mustHitSection could retarget source camera');
  // A later authored FocusCamera CLASSIC supplies a static target. It must
  // override the initial hold and remain stable through subsequent sections.
  camera.scriptableCamera='static';camera.camFollow.setPosition(1200,450);
  check(!camera.held() && camera.camFollow.x==1200,'authored camera event blocked');
  camera.dad=new Character(60,70,0,0,450,0); // stage swap
  check(!camera.held() && camera.camFollow.x==1200,'stage swap reset authored focus');
  camera.scriptableCamera='false';
  check(camera.held() && camera.camFollow.x==1200,'released event fell into native section follow');
  var script=new CameraHarness(v);script.dad=camera.dad;
  script.forceCamera=true;script.camFollow.setPosition(77,88);script.init();
  check(script.held() && script.camFollow.x==77 && script.camGame.snapCalls==0,
   'explicit script camera ownership overwritten');
  var stageScript=new CameraHarness(v);stageScript.dad=camera.dad;
  stageScript.camFollow.setPosition(333,444);stageScript.init();
  check(stageScript.held() && stageScript.camFollow.x==333 && stageScript.camGame.snapCalls==0,
   'stage script camera mutation overwritten');
  var other=new CameraHarness({selectedRoot:path,roots:[{engine:'Psych',path:path}]});
  other.dad=camera.dad;other.init();
  check(!other.held() && other.camGame.snapCalls==0,'non-V-Slice chart affected');
  var mixed=new CameraHarness({selectedRoot:path,roots:[{engine:'Psych',path:path},
   {engine:'V-Slice',path:path+'/other'}]});
  mixed.dad=camera.dad;mixed.init();check(!mixed.held(),'unselected root activated camera');
  var absent=new CameraHarness({selectedRoot:path+'/missing',roots:[{engine:'V-Slice',path:path+'/missing'}]});
  absent.dad=camera.dad;absent.init();check(!absent.held(),'missing selected source activated camera');
  // A new PlayState instance begins with its own unheld policy.
  check(!new CameraHarness({selectedRoot:'',roots:[]}).held(),'focus state leaked to next visit');
 }
}
'''.replace('__OWNER__', str(owner)).replace('__SELECTED__', selected).replace('__INITIALIZE__', initialize).replace('__HOLD__', hold)
            (folder / 'Main.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(folder), '--run', 'Main'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_wires_stage_completion_and_excludes_native_section_follow(self):
        source = SOURCE.read_text()
        stage = source[source.index("setAllHaxeVar('stage', curStage);"):source.index("RuntimeSmokeHarness.markLoadPhase('stage_loaded')")]
        self.assertLess(stage.index('flushPendingHxcCharacterAdded();'),
                        stage.index('initializeVSliceCameraFocus(beforeStageCameraX, beforeStageCameraY);'))
        self.assertIn("else if (holdVSliceSectionCamera())", source)
        focus = source[source.index('function FocusCamera('):source.index('function ZoomCamera(')]
        self.assertIn("scriptableCamera = 'static';", focus)
        self.assertIn('focusCameraDrivesFollow = true;', focus)


if __name__ == '__main__':
    unittest.main()
