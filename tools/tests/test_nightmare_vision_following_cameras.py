"""Exercise the actual NV camera-follow helper with native Flixel cameras."""
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_nightmare_vision_character_runtime import function_body
from test_source_camera_reflection import FLIXEL_ARGS

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionFollowingCamerasTest(unittest.TestCase):
    def test_followers_copy_view_but_preserve_authored_effects(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        method = function_body(source, "syncNightmareVisionFollowingCameras")
        self.assertIn("@:keep public var followingCams:Array<FlxCamera>", source)
        self.assertIn("followingCams.resize(0);", source)
        self.assertIn("callCodenameScripts('postUpdate', [elapsed]);\n\t\tsyncNightmareVisionFollowingCameras();", source)
        fixture = '''import flixel.FlxCamera;
import flixel.FlxG;
class CameraOwner {
 public var nightmareVisionScripts:Dynamic = {};
 public var camGame:FlxCamera;
 public var followingCams:Array<FlxCamera> = [];
 public function new() {}
 public METHOD
}
class FollowingCameraProbe {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function main():Void {
  var owner = new CameraOwner();
  owner.camGame = new FlxCamera(0,0,1280,720,0.75);
  FlxG.camera = owner.camGame;
  owner.camGame.scroll.set(-73,241);
  var first = new FlxCamera(0,0,1280,720,1);
  var second = new FlxCamera(0,0,640,480,2);
  first.angle = 7; first.alpha = 0.4; second.visible = false;
  owner.followingCams.push(first);
  owner.followingCams.push(null);
  owner.followingCams.push(owner.camGame);
  owner.followingCams.push(second);
  owner.syncNightmareVisionFollowingCameras();
  check(first.zoom==0.75 && second.zoom==0.75,'registered cameras missed source zoom');
  check(first.scroll.x==-73 && second.scroll.y==241,'registered cameras missed source scroll');
  check(first.scroll!=owner.camGame.scroll,'source and follower scroll points were aliased');
  check(first.angle==7 && first.alpha==0.4 && !second.visible,'authored camera effects were overwritten');
  owner.camGame.zoom=1.3; owner.camGame.scroll.set(350,-40);
  owner.syncNightmareVisionFollowingCameras();
  check(first.zoom==1.3 && second.scroll.y==-40,'live camera changes were not copied');
  owner.followingCams.remove(first); first.zoom=2.2;
  owner.syncNightmareVisionFollowingCameras();
  check(first.zoom==2.2,'unregistered follower kept receiving writes');
  var replacement = new FlxCamera(0,0,1280,720,0.6);
  replacement.scroll.set(9,15); FlxG.camera = replacement;
  owner.syncNightmareVisionFollowingCameras();
  check(second.zoom==0.6 && second.scroll.x==9,'followers ignored the live default camera');
  owner.nightmareVisionScripts=null; second.zoom=3;
  owner.syncNightmareVisionFollowingCameras();
  check(second.zoom==3,'non-NV owner received follower writes');
  FlxG.camera=null; owner.nightmareVisionScripts={};
  owner.syncNightmareVisionFollowingCameras();
 }
}'''.replace('METHOD', method)
        with tempfile.TemporaryDirectory(prefix="nv-following-cameras-", dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "FollowingCameraProbe.hx").write_text(fixture, encoding="utf-8")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["PATH"] = os.pathsep.join([str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")])
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), *FLIXEL_ARGS,
                "--run", "FollowingCameraProbe"], cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
