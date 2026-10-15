"""Psych indexed property paths on a missing parent raise Psych's error instead of crashing.

During a Psych game over, getProperty reads from the game-over substate, which
has none of PlayState's camera offset arrays. `getProperty('opponentCameraOffset[0]')`
then indexed null, which is a native access violation on hxcpp and closed the
game on the first game-over frame. Psych itself is built with null checks and
throws a catchable "Null Object Reference" there, which the Lua call reports.
"""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''
class Substate { public var bf:Dynamic = null; public function new() {} }
class Play { public var opponentCameraOffset:Array<Float> = [12, 34]; public var nested:Dynamic = {list: [[5]]}; public function new() {} }
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 // The error must be the one Psych reports, not whatever the interpreter
 // happens to raise for indexing null, which native code does not raise at all.
 static function thrown(run:Void->Dynamic):Bool {
  try run() catch (e:Dynamic) return Std.string(e) == 'Null Object Reference';
  return false;
 }
 static function main():Void {
  var registry = new Map<String, Dynamic>();
  var isState = function(o:Dynamic):Bool return false;
  var reg = function():Dynamic return registry;
  var read = function(o:Dynamic, k:String):Dynamic return o == null ? null : Reflect.getProperty(o, k);
  var write = function(o:Dynamic, k:String, v:Dynamic):Void Reflect.setProperty(o, k, v);
  // Live indexing itself is unchanged; the interpreter used here cannot index an
  // array with the string key hxcpp accepts, so only missing parents are run.
  var play = new Play();
  check(SourceScriptReflection.readPsychInstancePart(play, 'opponentCameraOffset', isState, reg, read) == play.opponentCameraOffset,
   'plain read on a live field');
  var dead = new Substate();
  check(thrown(function():Dynamic return SourceScriptReflection.readPsychInstancePart(dead, 'opponentCameraOffset[0]', isState, reg, read)),
   'indexed read through a missing field');
  check(thrown(function():Dynamic return SourceScriptReflection.readPsychInstancePart(dead, 'missing[0][1]', isState, reg, read)),
   'nested index through a missing field');
  check(thrown(function():Dynamic return SourceScriptReflection.writePsychPathPart(dead, 'opponentCameraOffset[0]', 5, isState, reg, read, write)),
   'indexed write through a missing field');
  check(thrown(function():Dynamic return SourceScriptReflection.isPsychMap(null)), 'map test on null');
  check(SourceScriptReflection.readPsychInstancePart(dead, 'missing', isState, reg, read) == null, 'plain missing field reads as nil');
 }
}
'''


class PsychIndexNullTargetTest(unittest.TestCase):
    def test_missing_index_parents_raise_the_psych_error(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            (Path(directory) / 'Main.hx').write_text(MAIN, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory,
                                     '-main', 'Main', '--interp'], text=True, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
