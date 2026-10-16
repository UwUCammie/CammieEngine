"""Psych 0.6 scripts drive camFollowPos, the point the camera locks onto.

Smooth Camera style scripts read camFollowPos, smooth it again and write it back
(and also write FlxG.camera.scroll). The engine's own camera eases its scroll
natively, so those writes stuck and fed the easing: the camera crawled after a
focus switch. A script that names camFollowPos now gets Psych's camera: the
point eases toward camFollow at 2.4 * cameraSpeed per second and the camera
locks onto it.
"""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'source/PlayState.hx'


def method(source, marker):
    start = source.index(marker)
    opening = source.index('{', start) if '{' in source[start:source.index('\n', start)] else None
    if opening is None:
        return source[start:source.index('\n', source.index('\n', start) + 1)]
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class PsychFollowPointTest(unittest.TestCase):
    def test_point_eases_like_psych_at_any_frame_rate(self):
        source = SOURCE.read_text()
        lerp = source[source.index('\tpublic static inline function psychFollowLerp'):]
        lerp = lerp[:lerp.index(';\n') + 2]
        update = method(source, '\tfunction updatePsychFollowPoint')
        fixture = '''class Point {
	public var x:Float = 0;
	public var y:Float = 0;
	public function new() {}
	public function setPosition(x:Float, y:Float):Void { this.x = x; this.y = y; }
}
class Camera {
	public var followed:Point;
	public var lerp:Float = -1;
	public function new() {}
	public function follow(target:Point, style:Int, value:Float):Void { followed = target; lerp = value; }
}
class FlxG { public static var camera:Camera = new Camera(); }
class Test {
	public static inline var LOCKON = 0;
	public var inCutscene:Bool = false;
	public var camSpeed:Float = 1;
	public var camFollow = new Point();
	public var camFollowPoint = new Point();
	public function new() {}
''' + lerp + '\n' + update + '''
	static function settle(fps:Float, speed:Float, fraction:Float):Float {
		var t = new Test();
		t.camSpeed = speed;
		t.camFollow.setPosition(1000, 0);
		var elapsed = 1 / fps;
		var time = 0.0;
		while (t.camFollowPoint.x < 1000 * fraction && time < 30) {
			t.updatePsychFollowPoint(elapsed);
			time += elapsed;
		}
		return time;
	}
	static function main() {
		// Psych: lerp = elapsed * 2.4 * speed, so 63 percent takes about 0.4 s at speed 1.
		var slow = settle(60, 1, 0.632);
		if (slow < 0.35 || slow > 0.5) throw "speed 1 time constant " + slow;
		// Twice the speed converges in half the time.
		if (Math.abs(settle(60, 2, 0.632) * 2 - slow) > 0.06) throw "speed scaling";
		// Psych's own lerp is per frame, so a high frame rate lands within a few percent.
		if (Math.abs(settle(240, 1, 0.632) - slow) > 0.08) throw "frame rate drift";
		// A countdown cut (1000) lands in one frame, speed 0 locks the camera.
		if (settle(60, 1000, 0.99) > 0.02) throw "snap";
		var locked = new Test();
		locked.camSpeed = 0;
		locked.camFollow.setPosition(500, 500);
		locked.updatePsychFollowPoint(1 / 60);
		if (locked.camFollowPoint.x != 0) throw "speed 0 must lock";
		// The camera is locked onto the point with no easing of its own, and cutscenes freeze the point.
		if (FlxG.camera.followed != locked.camFollowPoint || FlxG.camera.lerp != 1) throw "lock on point";
		var cut = new Test();
		cut.inCutscene = true;
		cut.camFollow.setPosition(500, 500);
		cut.updatePsychFollowPoint(1 / 60);
		if (cut.camFollowPoint.x != 0) throw "cutscene freezes the point";
	}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Test.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Test', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scripts_naming_the_point_switch_the_camera_over(self):
        source = SOURCE.read_text()
        getter = source[source.index('\tfunction get_camFollowPos():FlxObject {'):]
        self.assertIn('psychFollowPointActive = true;', getter[:120])
        self.assertIn('return camFollowPoint;', getter[:120])
        self.assertIn("case 'camfollowpos':\n\t\t\t\treturn camFollowPos;", source)
        update = source[source.index('\t\tensureGameplayCameraBinding();\n\t\tif (!codenameCameraControlled) {'):]
        self.assertLess(update.index('updatePsychFollowPoint(elapsed)'), update.index('camFollowLerp()'))
        compat = (ROOT / 'source/EngineCompat.hx').read_text()
        self.assertIn("case 'camfollowpos' | 'camerafollowpos':\n\t\t\t\treturn 'camFollowPos';", compat.replace('\r\n', '\n'))


if __name__ == '__main__':
    unittest.main()
