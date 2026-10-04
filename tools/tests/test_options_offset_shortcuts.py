"""Exercise the native numeric display used by offset keyboard shortcuts."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class OptionsOffsetShortcutTests(unittest.TestCase):
    def test_twenty_millisecond_steps_preserve_precision_and_clamp(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = FixturePath(folder)
            files = {
                "NumberDisplay.hx": (ROOT / "source/NumberDisplay.hx").read_text(),
                "flixel/math/FlxMath.hx": """package flixel.math;
class FlxMath {
 public static function bound(value:Float, low:Float, high:Float):Float
  return Math.max(low, Math.min(high, value));
}
""",
                "flixel/util/FlxColor.hx": """package flixel.util;
class FlxColor { public static inline var WHITE:Int=-1; public static inline var BLACK:Int=0; }
""",
                "flixel/text/FlxText.hx": """package flixel.text;
enum abstract FlxTextAlign(Int) { var RIGHT; }
enum abstract FlxTextBorderStyle(Int) { var OUTLINE; }
class FlxText {
 public var text:String='';
 public function new(x:Float, y:Float) {}
 public function setFormat(font:String, size:Int, color:Int, align:FlxTextAlign,
  border:FlxTextBorderStyle, borderColor:Int):Void {}
}
""",
                "HelperFunctions.hx": """class HelperFunctions {
 public static function truncateFloat(value:Float, places:Int):Float {
  var scale = Math.pow(10, places); return Math.floor(value * scale) / scale;
 }
}
""",
                "Main.hx": """class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function near(a:Float,b:Float):Bool return Math.abs(a-b)<0.000001;
 static function main():Void {
  var display = new NumberDisplay(0, 0, 0, 0.1, -1000, 1000);
  display.value = 1.3;
  display.changeAmount(true, 20);
  check(near(display.value,21.3), 'Shift right lost fractional offset or wrong step');
  display.changeAmount(false, 20);
  check(near(display.value,1.3), 'Shift left did not subtract 20');
  display.changeAmount(true);
  check(near(display.value,1.4) && display.precision==0.1, 'normal precision changed after Shift');
  display.value=995.3;
  display.changeAmount(true,20);
  check(display.value==1000, 'upper offset boundary not clamped');
  display.changeAmount(true,20);
  check(display.value==1000, 'step at upper boundary escaped');
  display.value=-995.3;
  display.changeAmount(false,20);
  check(display.value==-1000, 'lower offset boundary not clamped');
  display.resetValues();
  check(display.value==0 && display.precision==0.1, 'reset changed normal offset precision');
 }
}
""",
            }
            for name, content in files.items():
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "-main", "Main", "--interp"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_keyboard_shortcut_is_scoped_to_offset_and_fps_in_both_menus(self):
        native = (ROOT / "source/SaveDataState.hx").read_text()
        model = (ROOT / "source/CodenameOptionsMenuModel.hx").read_text()
        compat = (ROOT / "source/CodenameOptionsMenuCompat.hx").read_text()
        self.assertIn('(field == "offset" || field == "fpsCap") && FlxG.keys.pressed.SHIFT ? 20 : null', native)
        self.assertIn('changeAmount(increase, step)', native)
        self.assertIn("(name == 'offset' || name == 'fpsCap') && shiftHeld ? 20.0 : step", model)
        self.assertIn('direction, FlxG.keys.pressed.SHIFT)', compat)


if __name__ == "__main__":
    unittest.main()
