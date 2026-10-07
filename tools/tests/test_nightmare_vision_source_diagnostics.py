"""Owner-scoped diagnostics on the real NMV script interpreter."""
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / ".haxelib" / "hscript-iris" / "1,1,3"


class NightmareVisionSourceDiagnosticsTest(unittest.TestCase):
    def test_unknown_function_reaches_owner_debug_and_console(self):
        haxe = ROOT / ".tools" / "haxe" / ("haxe.exe" if os.name == "nt" else "haxe")
        if not haxe.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        main = r'''
import NightmareVisionScriptInterp;
import NightmareVisionScriptParser;
import NightmareVisionSourceDiagnostics;
import flixel.util.FlxColor;

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var messages:Array<String> = [];
  var colours:Array<FlxColor> = [];
  var diagnostics = new NightmareVisionSourceDiagnostics('assets/imported_mods/selected',
   'assets/imported_mods/selected/__nmv_core');
  diagnostics.bindDebugText(function(message:String, colour:FlxColor) {
   messages.push(message); colours.push(colour);
  });
  var interp = new NightmareVisionScriptInterp();
  diagnostics.bindIris(interp);
  interp.variables.set('diagnosticReceiver', {});
  var parsed = new NightmareVisionScriptParser().parseString('diagnosticReceiver.missingRuntimeTarget()',
   'assets/imported_mods/selected/__nmv_core/scripts/runtime-error.hx');
  interp.execute(parsed);
  check(messages.length == 1, 'unknown function did not reach the owner DebugText sink');
  check(messages[0].indexOf('Unknown function: missingRuntimeTarget') >= 0,
   'unknown function DebugText lost its source error message');
  check(colours[0] == FlxColor.fromRGB(255, 64, 64),
   'unknown function did not use donor error red');
  diagnostics.release();
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            point_dir = work / "flixel" / "math"
            point_dir.mkdir(parents=True)
            (point_dir / "FlxPoint.hx").write_text(r'''package flixel.math;
class FlxPoint {
 public var x:Float;
 public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public static function weak(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function set(x:Float=0,y:Float=0):FlxPoint { this.x=x; this.y=y; return this; }
 public function copyFrom(point:FlxPoint):FlxPoint return set(point.x,point.y);
}
class FlxCallbackPoint extends FlxPoint {
 final callback:FlxPoint->Void;
 public function new(setXCallback:FlxPoint->Void, ?setYCallback:FlxPoint->Void,
  ?setXYCallback:FlxPoint->Void) { super(); callback = setXYCallback != null ? setXYCallback : setXCallback; }
 override public function set(x:Float=0,y:Float=0):FlxCallbackPoint { super.set(x,y); callback(this); return this; }
}
''', encoding="utf-8", newline="\n")
            color_dir = work / "flixel" / "util"
            color_dir.mkdir(parents=True)
            (color_dir / "FlxColor.hx").write_text(r'''package flixel.util;
@:forward
abstract FlxColor(Int) from Int to Int {
 public static var WHITE:FlxColor = cast 0xffffffff;
 public static var YELLOW:FlxColor = cast 0xffffff00;
 public static inline function fromRGB(red:Int, green:Int, blue:Int):FlxColor
  return cast (red << 16) | (green << 8) | blue;
}
''', encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["HAXEPATH"] = str(ROOT / ".tools/haxe")
            env["NEKOPATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join((env["HAXEPATH"], env["NEKOPATH"], env.get("PATH", "")))
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work),
                 "--interp", "-main", "Main"],
                cwd=work, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Unknown function: missingRuntimeTarget", result.stdout)


if __name__ == "__main__":
    unittest.main()
