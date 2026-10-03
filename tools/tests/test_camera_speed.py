"""camSpeed is a script-facing speed multiplier, not a raw flixel follow lerp.

officeourple's stage sets currentPlayState.camSpeed = 1000 during the
countdown (cut the camera to place) and restores 1 ("normal"), and psych
"Set Property: cameraSpeed" events in this library use 0.75-4. Feeding those
straight into HaxeFlixel's follow lerp turned 1 into "no easing at all",
so Golden's camera hard-cut to every sing offset. The engine maps the
multiplier onto its own smoothing instead.
"""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'
SOURCE = ROOT / 'source/PlayState.hx'


def cam_speed_block(source):
    start = source.index('\tstatic inline var CAMERA_LERP_NORMAL')
    end = source.index('\n\t}\n', source.index('function camFollowLerp')) + len('\n\t}\n')
    return source[start:end].replace('function camFollowLerp', 'public function camFollowLerp')


class CameraSpeedTest(unittest.TestCase):
    def test_speed_maps_onto_engine_smoothing(self):
        block = cam_speed_block(SOURCE.read_text())
        fixture = '''class Camera {
	public var camSpeed:Float;
	public var focusCameraDrivesFollow:Bool = false;
''' + block + '''
	public function new(camSpeed:Float) {
		this.camSpeed = camSpeed;
	}
}
class Test {
	static function closeEnough(a:Float, b:Float):Bool {
		return Math.abs(a - b) < 0.0000001;
	}
	static function main() {
		if (!closeEnough(new Camera(1).camFollowLerp(), 0.08))
			throw "camSpeed 1 must stay the engine's normal lag";
		if (!closeEnough(new Camera(0.5).camFollowLerp(), 1 - Math.pow(0.92, 0.5)))
			throw "fractional speeds must ease proportionally";
		if (!closeEnough(new Camera(4).camFollowLerp(), 1 - Math.pow(0.92, 4)))
			throw "faster speeds must stay eased, not snap";
		if (new Camera(1000).camFollowLerp() < 0.999999)
			throw "countdown values (officeourple's 1000) must still cut instantly";
		if (new Camera(0).camFollowLerp() != 0)
			throw "camSpeed 0 must lock the camera";
		if (new Camera(-5).camFollowLerp() != 0)
			throw "negative camSpeed must not explode";
		// the countdown snap must be strictly faster than the song's 1
		if (!(new Camera(1000).camFollowLerp() > new Camera(1).camFollowLerp()))
			throw "mapping must grow with the requested speed";
	}
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'Test.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-main', 'Test', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_follow_calls_use_the_mapping(self):
        source = SOURCE.read_text()
        self.assertNotIn('FlxG.camera.follow(camFollow, LOCKON, camSpeed)', source)
        self.assertEqual(source.count('FlxG.camera.follow(camFollow, LOCKON, camFollowLerp())'), 2)


if __name__ == '__main__':
    unittest.main()
