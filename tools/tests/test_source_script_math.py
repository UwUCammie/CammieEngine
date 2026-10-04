"""Shared source-compatible arithmetic used by imported script APIs."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class SourceScriptMathTest(unittest.TestCase):
    def test_source_functions_and_nightmare_vision_facade(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function near(actual:Float, expected:Float, message:String):Void
  if (Math.abs(actual - expected) > 0.000001) fail(message + ': expected ' + expected + ', got ' + actual);
 static function main() {
  near(NightmareVisionMathUtil.logBase(2, 8), 3, 'logBase');
  near(NightmareVisionMathUtil.scale(5, 0, 10, 0, 100), 50, 'scale');
  near(NightmareVisionMathUtil.clamp(12, 0, 10), 10, 'upper clamp');
  near(NightmareVisionMathUtil.clamp(-2, 0, 10), 0, 'lower clamp');
  near(NightmareVisionMathUtil.quantize(0.6, 1), 1, 'quantize');
  near(NightmareVisionMathUtil.quantizeAlpha(0.6, 1), 1, 'quantizeAlpha');
  near(NightmareVisionMathUtil.decayLerp(10, 2, 1, 1), 2 + 8 * Math.exp(-1), 'decayLerp');
  near(NightmareVisionMathUtil.euclideanMod(-5, 3), 1, 'euclideanMod');
  near(NightmareVisionMathUtil.wrap(-1, 0, 3), 3, 'wrap');
  near(NightmareVisionMathUtil.floorDecimal(-1.231, 2), -1.24, 'floorDecimal');
  check(NightmareVisionMathUtil.numberArray(2, 5).join(',') == '2,3,4', 'numberArray bounds');
  near(NightmareVisionMathUtil.fastTan(Math.PI / 4), 1, 'fastTan');
  var supplied = new flixel.math.FlxPoint();
  var rotated = NightmareVisionMathUtil.rotate(1, 0, Math.PI / 2, supplied);
  check(rotated == supplied, 'rotate must reuse the supplied FlxPoint');
  near(rotated.x, 0, 'rotate x');
  near(rotated.y, 1, 'rotate y');
  near(NightmareVisionMathUtil.fpsLerp(0, 1, 0.1),
    1 - Math.pow(0.9, 30), 'fpsLerp elapsed scaling');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / "flixel" / "FlxG.hx").write_text(
                "package flixel; class FlxG { public static var elapsed:Float = 0.5; }\n",
                encoding="utf-8",
            )
            (work / "flixel" / "math" / "FlxMath.hx").write_text(
                """package flixel.math;
class FlxMath {
 public static function lerp(a:Float,b:Float,ratio:Float):Float return a+(b-a)*ratio;
 public static function getElapsedLerp(ratio:Float,elapsed:Float):Float return 1-Math.pow(1-ratio,elapsed*60);
 public static function fastSin(value:Float):Float return Math.sin(value);
 public static function fastCos(value:Float):Float return Math.cos(value);
}
""",
                encoding="utf-8",
            )
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
