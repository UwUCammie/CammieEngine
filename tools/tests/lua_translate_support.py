"""Translate small Lua snippets and run them in a Lua scope, for behaviour tests.

Each case is (name, lua source). The snippet reports through three functions:
``out(...)`` is an ordinary engine-style function (it sees one result of a
trailing call), ``all(...)`` takes every result the way a Lua function does,
and ``host(name)`` calls a script function from outside the script, the way
the engine calls a callback.
"""
import json
import subprocess
import tempfile

from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"

FIXTURE = r'''
class Fixture {
 static function show(value:Dynamic):String {
  if (value == null) return "nil";
  if (Std.isOfType(value, LuaValues)) return "<values " + Std.string(value) + ">";
  if (Std.isOfType(value, Array)) return "[" + [for (item in (cast value : Array<Dynamic>)) show(item)].join(",") + "]";
  return Std.string(value);
 }
 static function main() {
  var cases:Array<Array<String>> = __CASES__;
  for (entry in cases) {
   var seen:Array<String> = [];
   var status = "ok";
   var result = LuaCompat.translate(entry[1], entry[0] + ".lua");
   var parses = true;
   try new hscript.Parser().parseString(result.hscript) catch (error:Dynamic) parses = false;
   try {
    var interp = new LuaCompatInterp();
    var report = function(args:Array<Dynamic>):Dynamic {
     seen.push([for (value in args) show(value)].join(","));
     return null;
    };
    for (name => value in [
     "Std" => (Std : Dynamic), "Math" => (Math : Dynamic), "StringTools" => (StringTools : Dynamic),
     "luaNumber" => (EngineCompat.luaNumber : Dynamic), "luaString" => (EngineCompat.luaString : Dynamic),
     "luaStringSub" => (EngineCompat.luaStringSub : Dynamic), "luaStringLen" => (EngineCompat.luaStringLen : Dynamic),
     "luaStringLower" => (EngineCompat.luaStringLower : Dynamic), "luaStringUpper" => (EngineCompat.luaStringUpper : Dynamic),
     "luaStringGmatch" => (EngineCompat.luaStringGmatch : Dynamic), "luaType" => (EngineCompat.luaType : Dynamic),
     "luaTableValue" => (EngineCompat.luaTableValue : Dynamic)
    ]) interp.variables.set(name, value);
    interp.variables.set("makeRangeArray", function(max:Int, ?min:Int = 0):Array<Int> return [for (x in min...max) x]);
    interp.variables.set("Function_Stop", "Function_Stop");
    interp.variables.set("out", Reflect.makeVarArgs(report));
    interp.variables.set("all", interp.registerMultiValueFunction(Reflect.makeVarArgs(report)));
    interp.variables.set("host", function(name:String):Dynamic {
     return show(Reflect.callMethod(null, interp.variables.get(name), []));
    });
    interp.installTableHelpers();
    interp.execute(new hscript.Parser().parseString(result.hscript));
   } catch (error:Dynamic) status = "threw " + Std.string(error);
   Sys.println("CASE " + haxe.Json.stringify({name: entry[0], out: seen.join("|"), status: status,
    supported: result.supported, parses: parses, diagnostics: result.diagnostics.join(" || "), hscript: result.hscript}));
  }
 }
}
'''


def run_lua(cases):
    """Translate and run every case; return {name: record}."""
    source = FIXTURE.replace("__CASES__", json.dumps([[name, lua] for name, lua in cases]))
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "Fixture.hx").write_text(source, newline='\n', encoding='utf-8')
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
             "-main", "Fixture", "--interp"],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120,
        )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    records = {}
    for line in result.stdout.splitlines():
        if line.startswith("CASE "):
            record = json.loads(line[5:])
            records[record["name"]] = record
    return records


def check_outputs(test, cases):
    """cases: (name, lua, expected out). Every case must run cleanly with no diagnostics."""
    records = run_lua([(name, lua) for name, lua, _ in cases])
    for name, _, expected in cases:
        record = records[name]
        with test.subTest(name):
            test.assertEqual(record["status"], "ok", record["hscript"])
            test.assertEqual(record["diagnostics"], "", record["hscript"])
            test.assertTrue(record["supported"])
            test.assertEqual(record["out"], expected, record["hscript"])
    return records
