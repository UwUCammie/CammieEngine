"""Modchart rendering must retain arrow cameras outside their native group draw."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ModchartCameraCompatTest(unittest.TestCase):
    def test_camera_precedence_does_not_take_global_draw_default(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            work = Path(work)
            (work / 'flixel').mkdir()
            (work / 'flixel/FlxCamera.hx').write_text('package flixel; class FlxCamera { public function new() {} }')
            (work / 'flixel/FlxBasic.hx').write_text('''package flixel;
class FlxBasic {
 var _cameras:Array<FlxCamera>;
 public var container:FlxBasic;
 public function new(?cameras:Array<FlxCamera>, ?parent:FlxBasic) {
  _cameras = cameras; container = parent;
 }
 public function getCameras():Array<FlxCamera> {
  throw "Global draw defaults must not be mistaken for an authored camera";
 }
}''')
            (work / 'Main.hx').write_text('''import flixel.FlxBasic;
import flixel.FlxCamera;
class Main {
 static function check(value:Bool, label:String) { if (!value) throw label; }
 static function main() {
  var hud = [new FlxCamera()];
  var custom = [new FlxCamera(), new FlxCamera()];
  var field = [new FlxCamera()];
  var calls = 0;
  var fallback = function() { calls++; return hud; };
  var plainNote = new FlxBasic();
  var plainField = new FlxBasic();
  check(ModchartCameraCompat.resolve(plainNote, plainField, fallback) == hud,
   "unassigned note outside group draw must retain HUD fallback");
  check(calls == 1, "fallback called once");
  check(ModchartCameraCompat.resolve(new FlxBasic(custom), new FlxBasic(field), fallback) == custom,
   "explicit sprite cameras must win");
  var container = new FlxBasic(custom);
  check(ModchartCameraCompat.resolve(new FlxBasic(null, new FlxBasic(null, container)),
   new FlxBasic(field), fallback) == custom, "nested container cameras must win");
  check(ModchartCameraCompat.resolve(plainNote, new FlxBasic(field), fallback) == field,
   "authored playfield camera must precede fallback");
  check(calls == 1, "explicit cameras must avoid evaluating fallback");
  check(ModchartCameraCompat.resolve(new FlxBasic([]), plainField, fallback) == hud,
   "empty cameras retain upstream fallback behavior");
  check(ModchartCameraCompat.explicitCameras(null) == null, "null group has no camera");
 }
}''')
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT/'source'),
                                     '-cp', str(work), '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_adapter_retains_note_group_camera(self):
        adapter = (ROOT/'source/modchart/backend/standalone/adapters/cammie/Cammie.hx').read_text()
        self.assertIn('ModchartCameraCompat.explicitCameras(ps.notes)', adapter)
        self.assertIn('return cameras == null ? [ps.camHUD] : cameras', adapter)


if __name__ == '__main__':
    unittest.main()
