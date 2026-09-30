"""Execute the actual Psych mouse bridge against the pinned Flixel transform."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_psych_camera_alias import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychMouseCoordinatesTest(unittest.TestCase):
    def test_requested_camera_coordinates_and_pool_return(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        pointer = (ROOT / '.haxelib/flixel/6,1,2/flixel/input/FlxPointer.hx').read_text()
        methods = '\n'.join(extract_method(source, name) for name in (
            'public static function psychCameraLayerName',
            'function compatCameraForName', 'function compatMouseX', 'function compatMouseY'))
        transform = extract_method(pointer, 'public function getScreenPosition(')
        fixture = '''
class FlxPoint {
 public var x:Float=0; public var y:Float=0; public static var returned=0;
 public function new() {} public static function get() return new FlxPoint();
 public function put() {returned++; x=-999; y=-999;}
}
class FlxCamera {
 public var x:Float; public var y:Float; public var zoom:Float;
 public var initialZoom:Float=1; public var width:Float=1280; public var height:Float=720;
 public function new(x:Float,y:Float,zoom:Float) {this.x=x;this.y=y;this.zoom=zoom;}
}
class Mouse {
 public var gameX:Float=500; public var gameY:Float=300;
 // Deliberately different world coordinates, which the bridge must not use.
 public var x:Float=9999; public var y:Float=8888;
 public function new() {}
 TRANSFORM
}
class FlxG {public static var mouse=new Mouse(); public static var camera:FlxCamera;}
class Main {
 var camGame=new FlxCamera(10,20,2);
 var camHUD=new FlxCamera(20,30,1);
 var camOther=new FlxCamera(40,50,.5);
 public function new() {FlxG.camera=camGame;}
 METHODS
 static function equal(actual:Float,expected:Float) {
  if(Math.abs(actual-expected)>.000001)throw actual+' != '+expected;
 }
 static function main() {
  var s=new Main();
  equal(s.compatMouseX(),565); equal(s.compatMouseY('game'),320);
  equal(s.compatMouseX('hud'),480); equal(s.compatMouseY('camHUD'),270);
  equal(s.compatMouseX('other'),280); equal(s.compatMouseY('camOther'),140);
  s.camGame.x=999; s.camGame.zoom=8;
  equal(s.compatMouseX('other'),280); equal(s.compatMouseY('other'),140);
  equal(s.compatMouseX('unknown'),s.compatMouseX('game'));
  if(FlxPoint.returned!=10)throw 'pooled mouse points leaked';
 }
}
'''.replace('TRANSFORM', transform).replace('METHODS', methods)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder,
                                     '-main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
