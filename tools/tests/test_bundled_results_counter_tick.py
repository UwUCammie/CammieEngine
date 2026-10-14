from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"
SCRIPT = ROOT / "assets/imported_mods/bundled-vslice-results/scripts/results.lua"


class BundledResultsCounterTickTest(unittest.TestCase):
    def test_clear_percent_ticks_at_most_once_per_frame(self):
        # The bundled results screen counts the clear percent up with one timer
        # per percent on an eased schedule, so most timers finish in the first
        # frames. Each frame must start at most one tick sound; stacking one per
        # timer summed dozens of identical sounds into a very loud first burst.
        fixture = r'''
class BundledResultsCounterTickTest {
 static function main() {
  var source = sys.io.File.getContent('SCRIPT_PATH');
  var converted = LuaCompat.translate(source, 'results.lua');
  if (!converted.supported) throw converted.diagnostics.join(' | ');
  var interp = new LuaCompatInterp();
  var sounds:Array<String> = [];
  var noop = Reflect.makeVarArgs(function(_) return null);
  interp.variables.set('getProperty', Reflect.makeVarArgs(function(_) return 0));
  interp.variables.set('playSound', Reflect.makeVarArgs(function(args) {
   sounds.push(Std.string(args[0]));
   return null;
  }));
  interp.variables.set('Math', Math);
  interp.variables.set('Std', Std);
  interp.variables.set('makeRangeArray', function(max:Int, ?min:Int = 0):Array<Int> return [for (x in min...max) x]);
  interp.variables.set('luaNumber', EngineCompat.luaNumber);
  interp.variables.set('luaString', EngineCompat.luaString);
  interp.variables.set('luaStringSub', EngineCompat.luaStringSub);
  interp.variables.set('luaStringLen', EngineCompat.luaStringLen);
  interp.variables.set('luaStringFind', EngineCompat.luaStringFind);
  interp.variables.set('luaStringLower', EngineCompat.luaStringLower);
  interp.variables.set('luaStringUpper', EngineCompat.luaStringUpper);
  interp.variables.set('luaStringGsub', EngineCompat.luaStringGsub);
  interp.variables.set('luaType', EngineCompat.luaType);
  interp.variables.set('luaTableLength', EngineCompat.luaTableLength);
  interp.installTableHelpers();
  LuaStdlib.installScopedStringHelpers(interp);
  // Every other engine call the script makes is presentation: answer it with
  // nothing. The script's own functions replace these when it runs.
  var program = new hscript.Parser().parseString(converted.hscript);
  for (name in calledNames(program))
   if (!interp.variables.exists(name)) interp.variables.set(name, noop);
  interp.execute(program);
  // The rank animations that follow the count are outside this check.
  interp.variables.set('startAnims', noop);

  var accuracy = 95;
  interp.variables.set('accuracyNum', accuracy);
  interp.variables.set('riseAccuracy', 0);
  interp.variables.set('char', 'bf');
  var onTimer = interp.variables.get('onTimerCompleted');
  var onUpdatePost = interp.variables.get('onUpdatePost');
  // The script's own schedule: riseAcc i fires 0.03 + (i / n)^12 * 2.47 s in.
  var due = [for (i in 1...accuracy + 1) 0.03 + Math.pow(i / accuracy, 12) * 2.47];
  var next = 0, frame = 0, mostTimersInFrame = 0, ticks = 0;
  while (next < accuracy) {
   frame++;
   var now = frame / 60;
   var before = sounds.length, fired = 0;
   while (next < accuracy && due[next] <= now) {
    Reflect.callMethod(null, onTimer, ['riseAcc' + (next + 1), 1, 0]);
    next++;
    fired++;
   }
   if (fired > mostTimersInFrame) mostTimersInFrame = fired;
   var tickSounds = [for (i in before...sounds.length) if (sounds[i] == 'scrollMenu') i].length;
   if (tickSounds > 1) throw 'frame ' + frame + ' started ' + tickSounds + ' tick sounds';
   ticks += tickSounds;
   Reflect.callMethod(null, onUpdatePost, [1 / 60]);
  }
  if (mostTimersInFrame < 10) throw 'schedule no longer bunches timers: ' + mostTimersInFrame;
  if (ticks < 10) throw 'counter stopped ticking: ' + ticks;
  if (interp.variables.get('riseAccuracy') != accuracy) throw 'counter did not reach the target';
  if (sounds.indexOf('confirmMenu') < 0) throw 'final confirm sound missing';
  Sys.println('ok');
 }

 static function calledNames(program:hscript.Expr):Array<String> {
  var names:Array<String> = [];
  function walk(e:hscript.Expr) {
   switch (hscript.Tools.expr(e)) {
    case ECall(target, _):
     switch (hscript.Tools.expr(target)) {
      case EIdent(name): if (names.indexOf(name) < 0) names.push(name);
      default:
     }
    default:
   }
   hscript.Tools.iter(e, walk);
  }
  walk(program);
  return names;
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "BundledResultsCounterTickTest.hx").write_text(
                fixture.replace("SCRIPT_PATH", SCRIPT.as_posix()), newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HAXESCRIPT),
                 "-main", "BundledResultsCounterTickTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
