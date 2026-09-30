"""NMV interpreter error and control-flow behavior, executed with Iris."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
IRIS = ROOT / ".haxelib" / "hscript-iris" / "1,1,3"


class NightmareVisionScriptErrorsTest(unittest.TestCase):
    def test_unknown_variable_errors_loop_control_and_recovery(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(r'''
enum ForeignFlow {
 SBreak;
 SContinue;
 SReturn;
}
class Main {
 static var errors:Array<String> = [];
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) fail('expected ' + expected + ', got ' + actual);
 }
 static function throwForeign():Dynamic throw ForeignFlow.SReturn;
 static function configure(interp:NightmareVisionScriptInterp):Void {
  interp.variables.set('throwForeign', function():Dynamic { throw ForeignFlow.SReturn; });
 }
 static function group():NightmareVisionScriptGroup {
  return new NightmareVisionScriptGroup(null, function(name:String, phase:String, error:Dynamic):Void {
   errors.push(name + '#' + phase);
  });
 }
 static function assertCallbackError(group:NightmareVisionScriptGroup, name:String):Void {
  var oldCount = errors.length;
  eq(group.call(name), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(errors.length, oldCount + 1);
  eq(errors[errors.length - 1], 'errors.hx#' + name);
 }
 static function main() {
  var g = group();

  // Errors at module scope reject the script instead of registering a partial
  // module. This is the same path as ScriptModule.execute in the live host.
  eq(g.loadSource('top.hx', 'var value = unknownTop;'), null);
  eq(g.exists('top.hx'), false);
  eq(errors.pop(), 'top.hx#module');

  // Bare-variable errors from callbacks and every loop shape propagate to the
  // host reporter; they are not consumed as HScript return/break signals.
  var script = g.loadSource('errors.hx', '
   var attempts = 0;
   function functionError() return missingFunction;
   function whileError() {
    var index = 0;
    while (index < 1) { index++; var value = missingWhile; }
    return 10;
   }
   function doWhileError() {
    do { var value = missingDoWhile; } while (false);
    return 11;
   }
   function forError() {
    for (index in [1]) { var value = missingFor; }
    return 12;
   }
   function caughtError() {
    try { var value = missingCaught; }
    catch (error:Dynamic) { return 23; }
    return 0;
   }
   function loopControls() {
    var score = 0;
    for (index in [0, 1, 2, 3]) {
     try {
      if (index == 0) continue;
      if (index == 1) throw "caught string";
      if (index == 2) break;
      score += 100;
     } catch (error:Dynamic) { score += 10; }
     score += index;
    }
    return score;
   }
   function doWhileControls() {
    var index = 0;
    do {
     try { index++; if (index < 2) continue; break; }
     catch (error:Dynamic) { index = 99; }
    } while (true);
    return index + 10;
   }
   function returnThroughLoops() {
    var index = 0;
    while (true) {
     try { index++; return 40 + index; }
     catch (error:Dynamic) { return -1; }
    }
    return 0;
   }
   function recover() {
    attempts++;
    if (attempts == 1) { var value = missingOnce; }
    return attempts + 10;
   }
   function foreignTopLevelCallback() { throwForeign(); return 90; }
   function foreignWhile() { while (true) { throwForeign(); } return 91; }
   function foreignDoWhile() { do { throwForeign(); } while (false); return 92; }
   function foreignFor() { for (index in [1]) { throwForeign(); } return 93; }
   function good() return 17;
  ', configure);
  if (script == null) fail('valid error fixture failed to load: ' + errors.join(','));

  assertCallbackError(g, 'functionError');
  assertCallbackError(g, 'whileError');
  assertCallbackError(g, 'doWhileError');
  assertCallbackError(g, 'forError');

  // Script try/catch handles actual interpreter errors, while its internal
  // Stop enum still propagates through that same catch as loop control.
  eq(g.call('caughtError'), 23);
  eq(g.call('loopControls'), 11);
  eq(g.call('doWhileControls'), 12);
  eq(g.call('returnThroughLoops'), 41);

  // A callback that failed once can run again; later callbacks still execute.
  var beforeRecovery = errors.length;
  eq(g.call('recover'), NightmareVisionScriptGroup.CONTINUE_FUNC);
  eq(errors.length, beforeRecovery + 1);
  eq(errors[errors.length - 1], 'errors.hx#recover');
  eq(g.call('good'), 17);
  eq(g.call('recover'), 12);
  eq(errors.length, beforeRecovery + 1);

  // Match on the enum's type as well as the constructor: an unrelated host
  // enum also named SReturn is a real error, never an interpreter return.
  eq(g.loadSource('foreign-top.hx', 'throwForeign();', configure), null);
  eq(g.exists('foreign-top.hx'), false);
  eq(errors.pop(), 'foreign-top.hx#module');
  assertCallbackError(g, 'foreignTopLevelCallback');
  assertCallbackError(g, 'foreignWhile');
  assertCallbackError(g, 'foreignDoWhile');
  assertCallbackError(g, 'foreignFor');
  eq(g.call('good'), 17);
  g.destroy();
 }
}
''')
            for defines in ([], ["-D", "hscriptPos"]):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work)]
                        + defines + ["--main", "Main", "--interp"],
                        cwd=work,
                        capture_output=True,
                        text=True,
                        timeout=45,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
