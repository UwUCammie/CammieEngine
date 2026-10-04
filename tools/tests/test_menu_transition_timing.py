"""Keep menu-position and score-count lerps consistent at any frame rate."""

from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class MenuTransitionTimingTest(unittest.TestCase):
    def test_elapsed_factor_preserves_reference_trajectory_at_uncapped_rates(self):
        helper = extract_method(
            (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8"),
            "public static function timeAdjustedLerpAlpha",
        )
        fixture = f"""
class CoolUtil {{
{helper}
}}
class MenuTransitionTimingMain {{
    static function runFor(alpha:Float, fps:Int, duration:Float):Float {{
        var value = 0.0;
        var frameCount = Std.int(fps * duration);
        for (_ in 0...frameCount) {{
            var elapsed = 1.0 / fps;
            var amount = CoolUtil.timeAdjustedLerpAlpha(alpha, elapsed);
            value += (1.0 - value) * amount;
        }}
        return value;
    }}

    static function main() {{
        var rates = [60, 480, 1440, 5000];
        var durations = [0.1, 0.25, 1.0];
        var menuAlphas = [0.16, 0.17, 0.4, 0.5];
        for (baseAlpha in menuAlphas) {{
            if (Math.abs(CoolUtil.timeAdjustedLerpAlpha(baseAlpha, 1.0 / 60) - baseAlpha) > 1e-12)
                throw '60 Hz reference alpha changed';
            for (duration in durations) {{
                var expected = runFor(baseAlpha, 60, duration);
                for (fps in rates) {{
                    var actual = runFor(baseAlpha, fps, duration);
                    if (Math.abs(actual - expected) > 1e-8)
                        throw 'frame-rate dependent trajectory at ' + fps + ' fps';
                }}
            }}
        }}
        if (CoolUtil.timeAdjustedLerpAlpha(0.16, 0) != 0)
            throw 'zero elapsed time advanced the transition';
    }}
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MenuTransitionTimingMain.hx"
            path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "MenuTransitionTimingMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_negative_c_shape_keeps_its_original_two_step_trajectory(self):
        cool_util = (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8")
        alphabet = (ROOT / "source/Alphabet.hx").read_text(encoding="utf-8")
        helpers = "\n".join(
            extract_method(cool_util, marker)
            for marker in (
                "public static function timeAdjustedLerpAlpha",
                "public static function timeAdjustedTwoTargetLerp",
            )
        )
        c_shape_update = extract_method(alphabet, "function updateCShapeX")
        fixture = f"""
class FlxG {{ public static var width:Float = 1280; }}
class FlxMath {{
    public static function lerp(a:Float, b:Float, amount:Float):Float
        return a + (b - a) * amount;
}}
class CoolUtil {{
{helpers}
}}
class Alphabet {{
    public var x:Float;
    public var menuMotionRate:Float = 1;
    public function new(x:Float) this.x = x;
{c_shape_update}
    public function advance(y:Float, elapsed:Float, alpha:Float):Void
        updateCShapeX(y, elapsed, alpha);
}}
class NegativeCShapeMain {{
    static function actualAtRate(scaledY:Float, fps:Int, duration:Float):Float {{
        var row = new Alphabet(100);
        var elapsed = 1.0 / fps;
        for (_ in 0...Std.int(fps * duration))
            row.advance(scaledY, elapsed, CoolUtil.timeAdjustedLerpAlpha(0.16, elapsed));
        return row.x;
    }}

    static function originalAt60(scaledY:Float, duration:Float):Float {{
        var x = 100.0;
        var firstTarget = Math.exp(scaledY * 0.8) * 70 + (FlxG.width * 0.1);
        var secondTarget = Math.exp(scaledY * -0.8) * 70 + (FlxG.width * 0.1);
        for (_ in 0...Std.int(60 * duration)) {{
            x = FlxMath.lerp(x, firstTarget, 0.16);
            x = FlxMath.lerp(x, secondTarget, 0.16);
        }}
        return x;
    }}

    static function main() {{
        var rates = [60, 480, 1440, 5000];
        var durations = [0.1, 0.25, 1.0];
        var positions = [-0.5, -1.2];
        for (scaledY in positions) {{
            for (duration in durations) {{
                var expected = originalAt60(scaledY, duration);
                for (fps in rates) {{
                    var actual = actualAtRate(scaledY, fps, duration);
                    if (Math.abs(actual - expected) > 1e-8)
                        throw 'negative C-Shape path differs at ' + fps + ' fps';
                }}
            }}
        }}
    }}
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "NegativeCShapeMain.hx"
            path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "NegativeCShapeMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_alphabet_motion_rate_is_per_instance_and_elapsed_time_based(self):
        alphabet = (ROOT / "source/Alphabet.hx").read_text(encoding="utf-8")
        cool_util = (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8")
        self.assertIn("public var menuMotionRate:Float = 1;", alphabet)
        self.assertIn("elapsed * menuMotionRate", alphabet)
        freeplay = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        self.assertIn("static inline var SONG_ROW_SCALE:Float = 0.85;", freeplay)
        self.assertIn("static inline var SONG_ROW_MOTION_RATE:Float = 2;", freeplay)
        self.assertIn("row.setMenuTextScale(SONG_ROW_SCALE);", freeplay)
        self.assertIn("row.menuMotionRate = SONG_ROW_MOTION_RATE;", freeplay)
        alpha_helper = extract_method(
            cool_util,
            "public static function timeAdjustedLerpAlpha",
        )
        menu_helper = extract_method(alphabet, "function menuLerpAlpha")
        fixture = f"""
class CoolUtil {{
{alpha_helper}
}}
class Alphabet {{
    public var menuMotionRate:Float = 1;
    public function new(rate:Float) menuMotionRate = rate;
{menu_helper}
    public function alpha(elapsed:Float):Float return menuLerpAlpha(elapsed);
}}
class AlphabetMenuMotionMain {{
    static function run(rate:Float, fps:Int, duration:Float):Float {{
        var row = new Alphabet(rate);
        var value = 0.0;
        for (_ in 0...Std.int(fps * duration)) {{
            var amount = row.alpha(1.0 / fps);
            value += (1.0 - value) * amount;
        }}
        return value;
    }}
    static function main() {{
        var expected = run(2, 60, 0.05);
        for (fps in [60, 480, 1440, 5000]) {{
            var actual = run(2, fps, 0.05);
            if (Math.abs(actual - expected) > 1e-8)
                throw 'Alphabet motion changed at ' + fps + ' fps';
        }}
        if (Math.abs(expected - run(1, 60, 0.1)) > 1e-8)
            throw 'per-row 2x motion did not match twice the elapsed time';
        if (Math.abs(run(1, 60, 0.05) - run(2, 60, 0.05)) < 1e-4)
            throw 'menuMotionRate did not affect only the configured row';
    }}
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AlphabetMenuMotionMain.hx"
            path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "AlphabetMenuMotionMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fractional_score_accumulator_can_raise_above_zero_at_5000_fps(self):
        helper = extract_method(
            (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8"),
            "public static function timeAdjustedLerpAlpha",
        )
        fixture = f"""
class CoolUtil {{
{helper}
}}
class FlxMath {{
    public static function lerp(a:Float, b:Float, amount:Float):Float
        return a + (b - a) * amount;
}}
class RisingScoreMain {{
    static function main() {{
        var intendedScore = 50;
        var integerScore = 0;
        var floatScore = 0.0;
        var elapsed = 1.0 / 5000;
        for (_ in 0...5000) {{
            var alpha = CoolUtil.timeAdjustedLerpAlpha(0.4, elapsed);
            integerScore = Std.int(Math.floor(FlxMath.lerp(integerScore, intendedScore, alpha)));
            floatScore = FlxMath.lerp(floatScore, intendedScore, alpha);
        }}
        if (integerScore != 0)
            throw 'integer-state fixture no longer reproduces the stuck counter';
        if (Math.floor(floatScore) <= 0)
            throw 'fractional score did not advance the displayed counter';
    }}
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "RisingScoreMain.hx"
            path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "RisingScoreMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_menu_rows_and_score_counters_use_elapsed_time(self):
        for name in (
            "Alphabet.hx",
            "MenuItem.hx",
            "SaveFile.hx",
            "FreeplayState.hx",
            "StoryMenuState.hx",
            "SelectSongsState.hx",
            "SortState.hx",
        ):
            with self.subTest(source=name):
                source = (ROOT / "source" / name).read_text(encoding="utf-8")
                self.assertIn("CoolUtil.timeAdjustedLerpAlpha", source)
                self.assertNotIn("CoolUtil.fps / 60", source)

        alphabet = (ROOT / "source/Alphabet.hx").read_text(encoding="utf-8")
        self.assertIn("CoolUtil.timeAdjustedTwoTargetLerp", alphabet)
        for name in ("FreeplayState.hx", "StoryMenuState.hx", "SelectSongsState.hx", "SortState.hx"):
            with self.subTest(score_source=name):
                source = (ROOT / "source" / name).read_text(encoding="utf-8")
                self.assertRegex(source, r"var lerpScore:Float = 0;")
                self.assertNotRegex(source, r"lerpScore\s*=\s*Math\.floor")
                self.assertRegex(
                    source,
                    r"lerpScore\s*=\s*FlxMath\.lerp\(lerpScore, intendedScore, CoolUtil\.timeAdjustedLerpAlpha",
                )
                if name in ("FreeplayState.hx", "StoryMenuState.hx"):
                    self.assertIn("Math.floor(lerpScore)", source)


if __name__ == "__main__":
    unittest.main()
