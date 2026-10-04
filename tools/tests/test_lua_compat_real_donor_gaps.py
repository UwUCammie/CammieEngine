from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class LuaCompatRealDonorGapsTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "LuaCompatRealDonorGapsTest.hx").write_text(source, newline="\n")
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HAXESCRIPT), "-main", "LuaCompatRealDonorGapsTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_inline_branches_and_table_insert_execute(self):
        fixture = r'''
class LuaCompatRealDonorGapsTest {
 static function main() {
  var source = "function select(a, b, output)\n"
   + " if a then for i = 1,2 do table.insert(output, 'loop'..i); end; elseif b then table.insert(output, 'second'); else table.insert(output, 'fallback'); end\n"
   + "end\n";
  var converted = LuaCompat.translate(source, "psych-ratings-shape.lua");
  if (!converted.supported) throw converted.diagnostics.join(" | ");
  var interp = new LuaCompatInterp();
  interp.variables.set("select", null);
  interp.variables.set("Std", Std);
  interp.variables.set("makeRangeArray", function(end:Int, start:Int):Array<Int> {
   var values:Array<Int> = [];
   for (index in start...end) values.push(index);
   return values;
  });
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  var output:Array<Dynamic> = [];
  Reflect.callMethod(null, interp.variables.get("select"), [true, false, output]);
  if (output.length != 2 || output[0] != "loop1" || output[1] != "loop2")
   throw "inline for/body did not lower to an executable loop: " + output;
  output = [];
  Reflect.callMethod(null, interp.variables.get("select"), [false, true, output]);
  if (output.length != 1 || output[0] != "second")
   throw "inline elseif/table.insert was not executed: " + output;
  output = [];
  Reflect.callMethod(null, interp.variables.get("select"), [false, false, output]);
  if (output.length != 1 || output[0] != "fallback")
   throw "inline else/table.insert was not executed: " + output;
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_corpus_math_string_match_and_table_concat_helpers_execute(self):
        fixture = r'''
class LuaCompatRealDonorGapsTest {
 static function main() {
  var source = "function inspectString(input)\n"
   + " local left, right = string.match(input, '(.*),(%a+)')\n"
   + " capturedLeft = left\n"
   + " capturedRight = right\n"
   + " local ratingIds = { ['sick'] = 1, ['good'] = 2 }\n"
   + " lookedUpRating = ratingIds['sick']\n"
   + "end\n"
   + "function inspectTable(parts)\n"
   + " staticJoin = table.concat{'A', 'B', 'C'}\n"
   + " dynamicJoin = table.concat(parts, '-')\n"
   + "end\n"
   + "function inspectMath()\n"
   + " mathName = 'math.fmod(7,4)'\n"
   + " sine = math.asin(0)\n"
   + " interpolated = math.lerp(10, 20, 0.25)\n"
   + " remainder = math.fmod(7, 4)\n"
   + "end\n";
  var converted = LuaCompat.translate(source, "psych-library-shapes.lua");
  if (!converted.supported) throw converted.diagnostics.join(" | ");
  if (converted.hscript.indexOf("new EReg") < 0 || converted.hscript.indexOf("FlxMath.lerp") < 0
   || converted.hscript.indexOf("luaSequenceLength") < 0
   || converted.hscript.indexOf("'math.fmod(7,4)'") < 0)
   throw "the expected generic helper lowering was not emitted: " + converted.hscript;
  var interp = new LuaCompatInterp();
  interp.variables.set("Math", Math);
  interp.variables.set("FlxMath", {lerp:function(a:Float, b:Float, t:Float):Float return a + (b - a) * t});
  interp.variables.set("EReg", EReg);
  interp.variables.set("luaString", EngineCompat.luaString);
  interp.variables.set("luaSequenceLength", EngineCompat.luaTableLength);
  interp.variables.set("luaTableValue", EngineCompat.luaTableValue);
  interp.variables.set("makeRangeArray", function(end:Int, start:Int):Array<Int> {
   var values:Array<Int> = [];
   for (index in start...end) values.push(index);
   return values;
  });
  interp.variables.set("capturedLeft", "");
  interp.variables.set("capturedRight", "");
  interp.variables.set("lookedUpRating", 0);
  interp.variables.set("staticJoin", "");
  interp.variables.set("dynamicJoin", "");
  interp.variables.set("sine", -1.0);
  interp.variables.set("interpolated", -1.0);
  interp.variables.set("remainder", -1.0);
  interp.variables.set("mathName", "");
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  try Reflect.callMethod(null, interp.variables.get("inspectString"), ["name,word"])
   catch (error:Dynamic) throw "string.match failed: " + Std.string(error);
  try Reflect.callMethod(null, interp.variables.get("inspectTable"), [["x", "y", "z"]])
   catch (error:Dynamic) throw "table.concat failed: " + Std.string(error);
  try Reflect.callMethod(null, interp.variables.get("inspectMath"), [])
   catch (error:Dynamic) throw "math helpers failed: " + Std.string(error);
  if (interp.variables.get("capturedLeft") != "name"
   || interp.variables.get("capturedRight") != "word"
   || interp.variables.get("lookedUpRating") != 1
   || interp.variables.get("staticJoin") != "ABC"
   || interp.variables.get("dynamicJoin") != "x-y-z"
   || Math.abs(interp.variables.get("sine")) > 0.000001
   || Math.abs(interp.variables.get("interpolated") - 12.5) > 0.000001
   || interp.variables.get("remainder") != 3
   || interp.variables.get("mathName") != "math.fmod(7,4)")
   throw "wrong routed values: " + interp.variables.get("capturedLeft") + ", "
    + interp.variables.get("capturedRight") + ", " + interp.variables.get("staticJoin") + ", "
    + interp.variables.get("dynamicJoin") + ", " + interp.variables.get("sine") + ", "
    + interp.variables.get("interpolated") + ", " + interp.variables.get("remainder");
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tvcrt_haxe_blocks_route_only_as_complete_allowlisted_shapes(self):
        fixture = r'''
class LuaCompatRealDonorGapsTest {
 static function main() {
  var source = "local shaderName = 'tvcrt'\n"
   + "function setup()\n"
   + " runHaxeCode([[\n"
   + " var shaderName = \"]] .. shaderName .. [[\";\n"
   + " game.initLuaShader(shaderName);\n"
   + " var shader0 = game.createRuntimeShader(shaderName);\n"
   + " game.camGame.setFilters([new ShaderFilter(shader0)]);\n"
   + " game.getLuaObject('tvcrt').shader = shader0;\n"
   + " game.camHUD.setFilters([new ShaderFilter(game.getLuaObject('tvcrt').shader)]);\n"
   + " return;\n"
   + " ]])\n"
   + "end\n"
   + "function install()\n"
   + " runHaxeCode([[\n"
   + " resetCamCache = function(?spr) { if (spr == null || spr.filters == null) return; spr.__cacheBitmap = null; spr.__cacheBitmapData = null; }\n"
   + " fixShaderCoordFix = function(?_) { resetCamCache(game.camGame.flashSprite); resetCamCache(game.camHUD.flashSprite); resetCamCache(game.camOther.flashSprite); }\n"
   + " FlxG.signals.gameResized.add(fixShaderCoordFix);\n"
   + " fixShaderCoordFix();\n"
   + " return;\n"
   + " ]])\n"
   + "end\n"
   + "function uninstall()\n"
   + " runHaxeCode([[ FlxG.signals.gameResized.remove(fixShaderCoordFix); return; ]])\n"
   + "end\n";
  var converted = LuaCompat.translate(source, "tvcrt.lua");
  if (!converted.supported) throw converted.diagnostics.join(" | ");
  if (converted.hscript.indexOf('createRuntimeShaderAndStore("tvcrt", shaderName, "__psychRunHaxeShader0")') < 0
   || converted.hscript.indexOf('setCameraShaderFiltersFromStored("camGame", "__psychRunHaxeShader0")') < 0
   || converted.hscript.indexOf('setCameraShaderFiltersFromStored("camHUD", "__psychRunHaxeShader0")') < 0
   || converted.hscript.indexOf("installShaderCoordFix()") < 0
   || converted.hscript.indexOf("removeShaderCoordFix()") < 0)
   throw "complete TV CRT blocks did not lower to the seeded adapters: " + converted.hscript;

  var unsafe = LuaCompat.translate("function unsafe()\n runHaxeCode([[trace('unsafe'); return;]])\nend", "unsafe-haxe.lua");
  if (unsafe.supported || unsafe.diagnostics.join(" | ").indexOf("lua-raw-haxe") < 0)
   throw "unknown raw Haxe escaped the structural whitelist";
  var nearMatchSource = StringTools.replace(source, "game.initLuaShader(shaderName);",
   "game.initLuaShader(shaderName); trace('unsafe');");
  var nearMatch = LuaCompat.translate(nearMatchSource, "tvcrt-near-match.lua");
  if (nearMatch.supported || nearMatch.diagnostics.join(" | ").indexOf("lua-raw-haxe") < 0
   || nearMatch.hscript.indexOf("createRuntimeShaderAndStore") >= 0)
   throw "a composite shader block with an extra operation was partially lowered";
 }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nested_named_functions_preserve_lua_scope_and_callback_registration(self):
        fixture = r'''
class LuaCompatRealDonorGapsTest {
 static function main() {
  var source = "local function topLocal(n)\n return n + 1\nend\n"
   + "topLocalResult = topLocal(7)\n"
   + "if true then\n"
   + " local function branchLocal(n)\n"
   + "  return n + 2\n"
   + " end\n"
   + " branchLocalResult = branchLocal(5)\n"
   + "end\n"
   + "function registerTimer(value)\n"
   + " function onTimerCompleted(tag)\n"
   + "  callbackResult = value .. tag\n"
   + " end\n"
   + "end\n"
   + "function registerInline()\n"
   + " function onUpdatePost(elapsed) inlineResult = elapsed end\n"
   + "end\n"
   + "function registerShadow()\n"
   + " local onTimerCompleted = 'private'\n"
   + " function onTimerCompleted(tag) shadowResult = tag end\n"
   + " shadowCallback = onTimerCompleted\n"
   + "end\n"
   + "function installCleanup()\n"
   + " function onDestroy()\n"
   + "  cleanupCount = cleanupCount + 1\n"
   + " end\n"
   + "end\n"
   + "function calculate(n)\n"
   + " local function factorial(k)\n"
   + "  if k <= 1 then return 1 end\n"
   + "  return k * factorial(k - 1)\n"
   + " end\n"
   + " factorialResult = factorial(n)\n"
   + "end\n";
  var translated = LuaCompat.translate(source, "nested-callbacks.lua");
  if (!translated.supported) throw translated.diagnostics.join(" | ");
  if (translated.hscript.indexOf("function registerTimer(") < 0
    || translated.hscript.indexOf("onTimerCompleted = function(") < 0
    || translated.hscript.indexOf("onUpdatePost = function(") < 0
    || translated.hscript.indexOf("onDestroy = function(") < 0
    || translated.hscript.indexOf("var factorial; factorial = function(") < 0
    || translated.hscript.indexOf("var topLocal; topLocal = function(") < 0
    || translated.hscript.indexOf("var branchLocal; branchLocal = function(") < 0)
    throw "nested named functions used the wrong HScript declaration form: " + translated.hscript;

  var interp = new LuaCompatInterp();
  interp.variables.set("callbackResult", "");
  interp.variables.set("shadowResult", "");
  interp.variables.set("inlineResult", 0.0);
  interp.variables.set("cleanupCount", 0);
  interp.variables.set("topLocalResult", 0);
  interp.variables.set("branchLocalResult", 0);
  interp.variables.set("factorialResult", 0);
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  if (interp.variables.get("topLocalResult") != 8 || interp.variables.get("branchLocalResult") != 7
   || interp.variables.exists("topLocal") || interp.variables.exists("branchLocal"))
   throw "top-level or branch-local Lua functions leaked out of their lexical scopes";

  Reflect.callMethod(null, interp.variables.get("registerTimer"), ["first-"]);
  var firstCallback:Dynamic = interp.variables.get("onTimerCompleted");
  Reflect.callMethod(null, interp.variables.get("registerTimer"), ["second-"]);
  var secondCallback:Dynamic = interp.variables.get("onTimerCompleted");
  Reflect.callMethod(null, firstCallback, ["done"]);
  if (interp.variables.get("callbackResult") != "first-done")
   throw "the first nested global callback lost its captured parameter";
  Reflect.callMethod(null, secondCallback, ["done"]);
  if (interp.variables.get("callbackResult") != "second-done")
   throw "redefining a nested global callback did not replace it with its new closure";
  Reflect.callMethod(null, interp.variables.get("registerShadow"), []);
  if (interp.variables.get("onTimerCompleted") != secondCallback)
   throw "nested function assignment ignored an existing local shadow";
  Reflect.callMethod(null, interp.variables.get("shadowCallback"), ["local"]);
  if (interp.variables.get("shadowResult") != "local")
   throw "a locally shadowed named function did not keep its local assignment";

  Reflect.callMethod(null, interp.variables.get("registerInline"), []);
  Reflect.callMethod(null, interp.variables.get("onUpdatePost"), [0.25]);
  if (interp.variables.get("inlineResult") != 0.25)
   throw "one-line nested callback declaration was not registered globally";
  Reflect.callMethod(null, interp.variables.get("installCleanup"), []);
  Reflect.callMethod(null, interp.variables.get("onDestroy"), []);
  if (interp.variables.get("cleanupCount") != 1)
   throw "nested onDestroy cleanup callback was not registered";

  Reflect.callMethod(null, interp.variables.get("calculate"), [5]);
  if (interp.variables.get("factorialResult") != 120 || interp.variables.exists("factorial"))
   throw "local function recursion leaked or returned the wrong value";
 }
}
        '''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
