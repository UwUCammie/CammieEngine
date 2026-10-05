"""Keep the Psych Iris FlxG/camera facade live through reflective reads and writes."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


MAIN = r'''package;
import flixel.FlxCamera;
import flixel.FlxG;
import PsychFlxCameraCompat.PsychFlxGCompat;
import crowplexus.hscript.Parser;

class SourceCameraReflectionProbe {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function main():Void {
  var camera=new FlxCamera(0,0,640,480,1);
  FlxG.camera=camera;
  var interp=new NightmareVisionScriptInterp();
  interp.variables.set('FlxG',PsychFlxGCompat);
  var parser=new Parser();
  var initialLerp=camera.followLerp;
  var oldPause=FlxG.autoPause;
  var oldFilters=camera.filters;
  var oldEnabled=camera.filtersEnabled;
  interp.variables.set('oldFilters',oldFilters);
  interp.variables.set('oldEnabled',oldEnabled);
  interp.variables.set('oldPause',oldPause);

  interp.execute(parser.parseString(
   'cameraRateRead=FlxG.camera.followLerp; FlxG.camera.followLerp=0.01; '
   + 'savedCamera=FlxG.camera; FlxG.camera=null; nullCameraWasNull=(FlxG.camera==null); FlxG.camera=savedCamera; '
   + 'FlxG.camera.alpha=0.4; FlxG.camera.setScrollBounds(5,15,25,35); '
   + 'autoPauseRead=FlxG.autoPause; FlxG.autoPause=!FlxG.autoPause;'));
  check(interp.variables.get('cameraRateRead')==initialLerp,
   'Psych HScript could not read the live camera follow rate');
  check(camera.followLerp==0.01,
   'Psych HScript camera follow-rate write did not reach the native camera');
  check(FlxG.camera==camera,
   'saving and restoring the Psych camera facade did not preserve the native camera');
  check(interp.variables.get('nullCameraWasNull')==true,
   'a null native camera read fell through to a stale facade camera');
  check(camera.alpha==0.4,
   'generic camera assignment did not use the native setter');
  check(camera.minScrollX==5 && camera.maxScrollX==15
   && camera.minScrollY==25 && camera.maxScrollY==35,
   'delegated camera method lost its native receiver');
  check(interp.variables.get('autoPauseRead')==oldPause && FlxG.autoPause==!oldPause,
   'Psych HScript could not read an unlisted native FlxG property');

  interp.execute(parser.parseString('FlxG.camera.filters=null;'));
  check(!camera.filtersEnabled,
   'facade filters setter stopped disabling filters');
  // The previous statement deliberately exercises null through HScript. Restore
  // both native fields through the interpreter so this fixture leaves no state.
  interp.execute(parser.parseString('FlxG.camera.filters=oldFilters; FlxG.camera.filtersEnabled=oldEnabled; FlxG.autoPause=oldPause;'));
  check(camera.filtersEnabled==oldEnabled,
   'generic camera delegation did not preserve filter state restoration');
 }
}'''


FIXTURES = {
    "Character.hx": '''package;
class Character { public var animation:CameraProbeAnimation=new CameraProbeAnimation(); }
class CameraProbeAnimation {
 public var onFrameChange:Dynamic=null;
 public var onFinish:Dynamic=null;
 public var onLoop:Dynamic=null;
 public function new() {}
}
''',
    "NightmareVisionPlayableSongOwner.hx": '''package;
interface NightmareVisionPlayableSongOwner { public function nightmareVisionAudioView():Dynamic; }
''',
    "PsychBaseStageActorGroupCompat.hx": '''package;
class PsychBaseStageActorGroupCompat { public var zIndex:Int=0; public function new() {} }
''',
    "HxcCompatRuntime.hx": '''package;
class HxcCompatRuntime {
 public static function getZIndex(_object:Dynamic):Dynamic return 0;
 public static function setZIndex(_object:Dynamic,value:Dynamic):Dynamic return value;
}
''',
    "NightmareVisionFlxGView.hx": '''package;
class NightmareVisionFlxGView {
 public function getField(_field:String):Dynamic return null;
 public function setField(_field:String,value:Dynamic):Dynamic return value;
}
''',
    "NightmareVisionSaveData.hx": '''package;
class NightmareVisionSaveData {
 public function getField(_field:String):Dynamic return null;
 public function setField(_field:String,value:Dynamic):Dynamic return value;
}
''',
    "NightmareVisionSaveFacade.hx": '''package;
class NightmareVisionSaveFacade {
 public function new(_ownerRoot:String,_storage:Dynamic) {}
 public function release():Void {}
}
''',
}


class SourceCameraReflectionTest(unittest.TestCase):
    def test_actual_iris_property_boundary_delegates_flxg_and_camera(self):
        interp_source = (ROOT / "source/NightmareVisionScriptInterp.hx").read_text(encoding="utf-8")
        camera_source = (ROOT / "source/PsychFlxCameraCompat.hx").read_text(encoding="utf-8")
        self.assertIn("if (object == PsychFlxGCompat) return PsychFlxGCompat.getField(field);", interp_source)
        self.assertIn("return (cast object:PsychFlxCameraCompat).getField(field);", interp_source)
        self.assertIn("Reflect.getProperty(nativeCamera, field)", camera_source)
        self.assertIn("Reflect.getProperty(FlxG, field)", camera_source)

        with tempfile.TemporaryDirectory(prefix="source-camera-reflection-", dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "SourceCameraReflectionProbe.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            for name, contents in FIXTURES.items():
                (work / name).write_text(contents, encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "flixel", "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(work), *FLIXEL_ARGS,
                 "--run", "SourceCameraReflectionProbe"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
