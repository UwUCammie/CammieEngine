"""Pause UI owns a camera even when authored HUD state is hidden/transformed."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PauseCameraIsolationTest(unittest.TestCase):
    def test_owned_overlay_preserves_hud_and_releases_on_repeated_pause(self):
        source = (ROOT / "source/PauseSubState.hx").read_text()
        setup = source[source.index("pauseCamera = new FlxCamera();"):source.index("cameras = [pauseCamera];") + len("cameras = [pauseCamera];")]
        cleanup = source[source.index("if (pauseCamera != null) {"):source.index("\n\tfunction changeSelection")]
        # Strip only the enclosing destroy method's closing brace.
        cleanup = cleanup.rsplit("}", 1)[0]
        main = """
class FlxCamera {
 public var alpha:Float=1; public var zoom:Float=1; public var bgColor:Int=1;
 public var visible=true; public var dead=false; public function new() {}
}
class FlxColor { public static var TRANSPARENT=0; }
class CameraList {
 public var list:Array<FlxCamera>=[]; public var defaults:Array<FlxCamera>=[];
 public function new() {}
 public function add(c:FlxCamera, defaultDraw:Bool) {list.push(c); if(defaultDraw)defaults.push(c);}
 public function remove(c:FlxCamera, destroy:Bool) {list.remove(c);defaults.remove(c);if(destroy)c.dead=true;}
}
class FlxG { public static var cameras=new CameraList(); }
class Main {
 var pauseCamera:FlxCamera; var cameras:Array<FlxCamera>;
 function new() {}
 function setup() { SETUP }
 function cleanup() { CLEANUP }
 static function main() {
  var hud=new FlxCamera();hud.alpha=0;hud.visible=false;hud.zoom=3;
  FlxG.cameras.add(hud,true);
  for(i in 0...3) {
   var pause=new Main();pause.setup();var overlay=pause.cameras[0];
   if(overlay==hud||overlay.alpha!=1||!overlay.visible||overlay.zoom!=1||overlay.bgColor!=0)
    throw 'pause inherits authored HUD state';
   if(FlxG.cameras.list.length!=2||FlxG.cameras.defaults.length!=1)
    throw 'overlay changed default gameplay render targets';
   pause.cleanup();pause.cleanup();
   if(!overlay.dead||FlxG.cameras.list.length!=1||hud.dead||hud.alpha!=0||hud.visible||hud.zoom!=3)
    throw 'pause cleanup leaked a camera or changed authored HUD';
  }
 }
}
""".replace("SETUP", setup).replace("CLEANUP", cleanup)
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder,
                                     "--main", "Main", "--interp"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
