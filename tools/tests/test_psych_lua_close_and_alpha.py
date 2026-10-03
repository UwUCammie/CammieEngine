"""Execute the production Psych close and receptor-alpha bindings in isolation."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class PsychLuaCloseAndAlphaTest(unittest.TestCase):
    def test_close_stops_later_callbacks_and_alpha_tweens_the_selected_receptor(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/PlayState.hx").read_text()
        seed_start = source.index("\t\tif (Std.isOfType(interp, LuaCompatInterp)) {", source.index("function seedEngineCompat("))
        seed_end = source.index("\t\t// Psych exposes these globals", seed_start)
        close_seed = source[seed_start:seed_end]
        closed_guard = "if (interp != null && interp.variables.get('__compatClosed') == true)"
        self.assertIn(closed_guard, source)
        alpha = next(line for line in source.splitlines()
                     if "interp.variables.set('noteTweenAlpha'" in line)
        fixture = r'''
class Interp {
 public var variables:Map<String,Dynamic>=[];
 public function new() {}
}
class RuntimeSmokeHarness {
 static var diagnosticsEnabled:Bool = true;
 public static function enabled():Bool return diagnosticsEnabled;
}
class PsychModSettingCompat {
 public static function ownerForScript(origin:String, root:String):String return null;
 public static function create(origin:String, root:String, report:String->Void):Dynamic
  return function(?name:Dynamic, ?packageName:Dynamic):Dynamic return null;
}
class LuaCompatInterp extends Interp {
 public var smokeDiagnosticsEnabled:Bool = false;
}
class Main {
 static var SONG:Dynamic = {song:'fixture-song'};
 static var storyDifficultyText='authored-difficulty';
 static var tween:Array<Dynamic>=[];
 static function compatNoteTween(tag:String,note:Dynamic,property:String,value:Float,
  duration:Float,?ease:String):Void tween=[tag,note,property,value,duration,ease];
 static function seed(interp:Interp):Void {
  var origin:String = null;
  var psychScriptOwner:String = null;
''' + close_seed + alpha + r'''
 }
 static function canCall(interp:Interp):Bool {
  if (interp != null && interp.variables.get('__compatClosed') == true) return false;
  return true;
 }
 static function main():Void {
  var lua=new LuaCompatInterp(); seed(lua);
  if (!lua.smokeDiagnosticsEnabled) throw 'Lua compatibility scope lost smoke diagnostics setting';
  if (!canCall(lua)) throw 'new script closed';
  if (lua.variables.get('difficultyName')!='authored-difficulty') throw 'missing difficulty name';
  Reflect.callMethod(null,lua.variables.get('noteTweenAlpha'),['fade',7,0.25,1.5,'quartInOut']);
  if (tween[0]!='fade' || tween[1]!=7 || tween[2]!='alpha' || tween[3]!=0.25
   || tween[4]!=1.5 || tween[5]!='quartInOut') throw 'alpha tween contract';
  Reflect.callMethod(null,lua.variables.get('close'),[true]);
  if (canCall(lua)) throw 'closed script still called';
  var other=new Interp(); seed(other);
  if (!canCall(other) || other.variables.exists('close')) throw 'non-Lua scope changed';
  other.variables.set('__compatClosed',true);
  if (canCall(other)) throw 'removed static Lua stage still called';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", scratch, "--run", "Main"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
