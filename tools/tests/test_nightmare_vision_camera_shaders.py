"""The Nightmare Vision camera macro's shader API, including ownership cleanup."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionCameraShadersTest(unittest.TestCase):
    def test_add_remove_identity_order_and_owner_cleanup(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe unavailable")
        files = {
            "flixel/FlxCamera.hx": '''package flixel;
import openfl.filters.BitmapFilter;
class FlxCamera {
 public var filters:Null<Array<BitmapFilter>> = null;
 public function new() {}
}
''',
            "flixel/graphics/tile/FlxGraphicsShader.hx": '''package flixel.graphics.tile;
class FlxGraphicsShader { public function new() {} }
''',
            "openfl/filters/BitmapFilter.hx": '''package openfl.filters;
class BitmapFilter { public function new() {} }
''',
            "openfl/filters/ShaderFilter.hx": '''package openfl.filters;
class ShaderFilter extends BitmapFilter {
 public var shader:flixel.graphics.tile.FlxGraphicsShader;
 public function new(shader:flixel.graphics.tile.FlxGraphicsShader) {
  super(); this.shader = shader;
 }
}
''',
            "Main.hx": '''import flixel.FlxCamera;
import flixel.graphics.tile.FlxGraphicsShader;
import openfl.filters.ShaderFilter;
class Main {
 static function check(ok:Bool, message:String) if (!ok) throw message;
 static function main() {
  var camera = new FlxCamera();
  var shader = new FlxGraphicsShader();
  var other = new FlxGraphicsShader();
  var outside = new ShaderFilter(other);
  camera.filters = [outside];
  var first = new NightmareVisionCameraShaders();
  var second = new NightmareVisionCameraShaders();
  first.add(camera, shader);
  first.add(camera, shader);
  second.add(camera, other);
  check(camera.filters.length == 4, 'filters were not appended');
  check(camera.filters[0] == outside, 'existing filter order changed');
  check(first.remove(camera, shader), 'first matching shader was not removed');
  check(camera.filters.length == 3, 'remove did not remove one filter');
  check(!first.remove(camera, new FlxGraphicsShader()), 'unknown shader returned true');
  first.release();
  check(camera.filters.length == 2, 'owner cleanup missed one filter');
  check(camera.filters[0] == outside, 'cleanup removed a foreign filter');
  second.release();
  check(camera.filters.length == 1 && camera.filters[0] == outside,
   'second owner cleanup damaged an external filter');
  check(!first.remove(camera, shader), 'released shader was still attached');
  first.add(camera, null);
  check(camera.filters.length == 1, 'null shader should be a no-op');
 }
}
''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, source in files.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
