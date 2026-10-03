"""Window-resize framing contract.

Pins the fixed 1280x720 design-space behavior the engine promises on any OS
window size: RatioScaleMode keeps FlxG at the design size, computes a uniform
fit scale, and centers the letterbox.  The real vendored flixel scale mode
sources are extracted and interpreted so the math (not a copy of it) is what
gets pinned, and source contracts keep Main.hx wiring explicit.
"""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FLIXEL = ROOT / ".haxelib/flixel/6,1,2"

# Minimal flixel stand-ins: the vendored BaseScaleMode/RatioScaleMode only
# touch FlxG size statics, FlxPoint and the align enums.  FlxG.game stays null
# (updateGamePosition null-guards it) because there is no display tree here.
STUB_FILES = {
    "flixel/FlxG.hx": """\
package flixel;
class FlxG {
	public static var initialWidth:Int = 1280;
	public static var initialHeight:Int = 720;
	public static var width:Int = 1280;
	public static var height:Int = 720;
	public static var game:Dynamic = null;
}
""",
    "flixel/math/FlxPoint.hx": """\
package flixel.math;
class FlxPoint {
	public var x:Float;
	public var y:Float;
	public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; }
	public static function get(x:Float = 0, y:Float = 0):FlxPoint { return new FlxPoint(x, y); }
	public function set(x:Float = 0, y:Float = 0):FlxPoint { this.x = x; this.y = y; return this; }
}
""",
    "flixel/util/FlxHorizontalAlign.hx": """\
package flixel.util;
enum FlxHorizontalAlign { LEFT; CENTER; RIGHT; }
""",
    "flixel/util/FlxVerticalAlign.hx": """\
package flixel.util;
enum FlxVerticalAlign { TOP; CENTER; BOTTOM; }
""",
}

MAIN = """\
class ScaleModeContractTest {
	static function main() {
		var sm = new flixel.system.scaleModes.RatioScaleMode();

		// The 1280x720 reference window: identity, no letterbox.
		check(sm, 1280, 720, 1280, 720, 1, 1, 0, 0);

		// 16:9 enlargement (the harness/user case 1792x1008): uniform 1.4 fit,
		// design size untouched, no bars.
		check(sm, 1792, 1008, 1792, 1008, 1.4, 1.4, 0, 0);

		// Wider-than-16:9 (2560x1080): fit height, vertical bars centered.
		check(sm, 2560, 1080, 1920, 1080, 1.5, 1.5, 320, 0);

		// 4:3 window (1440x1080): fit width, horizontal bars centered.
		check(sm, 1440, 1080, 1440, 810, 1.125, 1.125, 0, 135);

		// Taller window (1024x1365): fit width, bars top and bottom.
		check(sm, 1024, 1365, 1024, 576, 0.8, 0.8, 0, 395);

		// Portrait window: fit height, horizontal bars centered.
		check(sm, 800, 1280, 800, 450, 0.625, 0.625, 0, 415);

		// Downscaled 16:9 window (854x480): uniform shrink; gameSize.x floors
		// to 853 (0.26% scale skew) and the spare pixel lands left of center.
		check(sm, 854, 480, 853, 480, 0.66640625, 0.6666666666666666, 1, 0);

		// The design size reported by FlxG must never drift from the initial
		// 1280x720 game size, whatever the window does.
		if (flixel.FlxG.width != 1280 || flixel.FlxG.height != 720)
			throw "FlxG width/height must stay at the 1280x720 design size";
	}

	static function check(sm:flixel.system.scaleModes.RatioScaleMode, windowW:Int, windowH:Int,
			gameW:Float, gameH:Float, scaleX:Float, scaleY:Float, offsetX:Float, offsetY:Float):Void {
		sm.onMeasure(windowW, windowH);
		if (!close(sm.gameSize.x, gameW) || !close(sm.gameSize.y, gameH))
			throw 'window ${windowW}x${windowH}: gameSize ${sm.gameSize.x}x${sm.gameSize.y}, expected ${gameW}x${gameH}';
		if (!close(sm.scale.x, scaleX) || !close(sm.scale.y, scaleY))
			throw 'window ${windowW}x${windowH}: scale ${sm.scale.x}x${sm.scale.y}, expected ${scaleX}x${scaleY}';
		if (!close(sm.offset.x, offsetX) || !close(sm.offset.y, offsetY))
			throw 'window ${windowW}x${windowH}: offset ${sm.offset.x},${sm.offset.y}, expected ${offsetX},${offsetY}';
		if (Math.abs(sm.scale.x - sm.scale.y) > 0.01)
			throw 'window ${windowW}x${windowH}: scale must stay uniform, got ${sm.scale.x}x${sm.scale.y}';
	}

	static function close(a:Float, b:Float):Bool {
		return Math.abs(a - b) < 0.6;
	}
}
"""


class WindowResizeFramingTest(unittest.TestCase):
    def setUp(self):
        if not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable haxe toolchain missing (run ./run.sh once)")

    def test_main_installs_fixed_design_space_and_letterbox_scale_mode(self):
        main = (ROOT / "source/Main.hx").read_text()
        self.assertIn("new FlxGame(1280, 720", main,
                      "the design space must stay fixed at 1280x720, not window-sized")
        self.assertIn("flixel.system.scaleModes.RatioScaleMode()", main,
                      "the uniform-fit letterbox scale mode must be installed explicitly")
        self.assertNotIn("new FlxGame(0, 0", main,
                         "a window-sized game space reintroduces the framing drift")

    def test_engine_does_not_reassign_scale_mode_elsewhere(self):
        # The scale mode is engine policy owned by Main; scripts may flip it via
        # the HxcCompatRuntime adapter, but engine code must not fight Main.
        offenders = []
        for path in (ROOT / "source").rglob("*.hx"):
            if path.name == "Main.hx":
                continue
            if "FlxG.scaleMode =" in path.read_text():
                offenders.append(str(path))
        self.assertEqual(offenders, [], "engine scale-mode assignments outside Main.hx")

    def test_ratio_scale_mode_math(self):
        scale_mode_dir = FLIXEL / "flixel/system/scaleModes"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, text in STUB_FILES.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, newline='\n')
            shutil_copy(scale_mode_dir / "BaseScaleMode.hx", root / "flixel/system/scaleModes/BaseScaleMode.hx")
            shutil_copy(scale_mode_dir / "RatioScaleMode.hx", root / "flixel/system/scaleModes/RatioScaleMode.hx")
            (root / "ScaleModeContractTest.hx").write_text(MAIN, newline='\n')
            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(root),
                    "-main", "ScaleModeContractTest",
                    "--interp",
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def shutil_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(), newline='\n')


if __name__ == "__main__":
    unittest.main()
