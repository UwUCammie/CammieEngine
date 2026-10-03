"""FocusCamera must reproduce the donor engine's camera glide, not the classic one.

Matched-timestamp A/B against the donor build (Vs Tricky Expurgation, 230 BPM)
showed the compat adapter kept tracking the character's live midpoint with the
classic 0.08 section-follow rate, while the donor snaps its follow point once
(cameraFocusPoint is anim-independent) and glides at
Constants.DEFAULT_CAMERA_FOLLOW_RATE (0.04). At this song's event cadence the
old behavior left the framing up to ~200 screen pixels away from the donor at
matched moments - characters appeared pushed aside relative to the stage.
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


def cam_follow_lerp_block(source):
    start = source.index('\tstatic inline var CAMERA_LERP_NORMAL')
    end = source.index('\n\t}\n', source.index('function camFollowLerp')) + len('\n\t}\n')
    return source[start:end].replace('function camFollowLerp', 'public function camFollowLerp')


def focus_camera_classic_block(source):
    start = source.index("\t\t\tcase 'classic':\n", source.index('function FocusCamera'))
    end = source.index("\t\t\tcase 'instant':", start)
    return source[start:end]


class FocusCameraDonorParityTest(unittest.TestCase):
    def setUp(self):
        self.source = SOURCE.read_text()

    def test_donor_follow_rate_is_pinned(self):
        self.assertIn('static inline var DONOR_CAMERA_FOLLOW_RATE:Float = 0.04;', self.source)

    def test_classic_focus_snaps_a_static_point(self):
        block = focus_camera_classic_block(self.source)
        # Donor's cameraFollowPoint is a one-time capture; the adapter must not
        # switch to the live-tracking bf/dad/gf modes anymore.
        for mode in ("scriptableCamera = 'bf';", "scriptableCamera = 'dad';", "scriptableCamera = 'gf';"):
            self.assertNotIn(mode, block)
        self.assertIn("scriptableCamera = 'static';", block)
        self.assertIn('scriptCamPos[0] = targetPos;', block)

    def test_adapter_flags_the_donor_rate(self):
        # FocusCamera (any ease) hands the camera to the compat follow rate.
        focus_start = self.source.index('function FocusCamera(')
        focus_end = self.source.index('function ZoomCamera(', focus_start)
        self.assertIn('focusCameraDrivesFollow = true;', self.source[focus_start:focus_end])

    def test_glide_uses_donor_rate_when_flagged(self):
        block = cam_follow_lerp_block(self.source)
        fixture = '''class Camera {
	public var camSpeed:Float;
	public var focusCameraDrivesFollow:Bool;
''' + block + '''
	public function new(camSpeed:Float, donor:Bool) {
		this.camSpeed = camSpeed;
		this.focusCameraDrivesFollow = donor;
	}
}
class Test {
	static function closeEnough(a:Float, b:Float):Bool {
		return Math.abs(a - b) < 0.0000001;
	}
	static function main() {
		// donor glide: Constants.DEFAULT_CAMERA_FOLLOW_RATE (0.04) per frame
		if (!closeEnough(new Camera(1, true).camFollowLerp(), 1 - Math.pow(0.96, 1)))
			throw "FocusCamera follow must glide at the donor's 0.04 rate";
		if (!closeEnough(new Camera(1, false).camFollowLerp(), 0.08))
			throw "classic section-follow must keep the fork's 0.08 rate";
		// script speed multipliers keep working on top of either base
		if (!closeEnough(new Camera(2, true).camFollowLerp(), 1 - Math.pow(0.96, 2)))
			throw "camSpeed must still ease proportionally on the donor path";
		if (new Camera(1000, true).camFollowLerp() < 0.999999)
			throw "countdown-style speeds must still cut instantly";
		if (new Camera(0, true).camFollowLerp() != 0)
			throw "camSpeed 0 must still lock the camera";
		// the donor path must glide slower than the classic path at speed 1
		if (!(new Camera(1, true).camFollowLerp() < new Camera(1, false).camFollowLerp()))
			throw "donor rate must be the gentler glide";
	}
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'Test.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-main', 'Test', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
