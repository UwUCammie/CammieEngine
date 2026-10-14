"""The Lua scope's per-call and per-loop work stays cheap without changing results.

Translated Lua functions run in their captured scope instead of copying it on
every call, and a `return` closing a function body hands its value back
without a throw. Numeric and pairs loops walk their range without building a
list, while loops test their condition in place, identifiers are one lookup per
map, the `_G` name checks are hand scans, and the tables a script drops are not
kept alive by the scope's own bookkeeping on native builds.
"""
import json
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND
from lua_translate_support import HSCRIPT, ROOT, Path, check_outputs, run_lua


class LuaReturnTest(unittest.TestCase):
    def test_returns_keep_their_values(self):
        check_outputs(self, [
            ("tail_call_passes_every_result",
             "local function two() return 1, 2 end\nlocal function pass() return two() end\nall(pass())\nout(pass())",
             "1,2|1"),
            ("tail_call_cut_to_one_inside_an_expression",
             "local function two() return 1, 2 end\nlocal function pass() return two() end\nall(pass(), 'x')",
             "1,x"),
            ("bare_return_is_nil", "local function f() return end\nout(f(), 'after')", "nil,after"),
            ("early_returns_in_ifs",
             "local function sign(x)\n if x < 0 then return -1 end\n if x == 0 then return 0 end\n return 1\nend\n"
             "out(sign(-5), sign(0), sign(3))", "-1,0,1"),
            ("return_inside_a_numeric_loop",
             "local function find(t, v)\n for i = 1, #t do if t[i] == v then return i end end\n return nil\nend\n"
             "out(find({4, 5, 6}, 5), find({4}, 9))", "2,nil"),
            ("return_inside_a_while_loop",
             "local function firstOver(limit)\n local n = 0\n while true do n = n + 1 if n * n > limit then return n end end\nend\n"
             "out(firstOver(10))", "4"),
            ("callback_returns_function_stop",
             "function onCheck() return Function_Stop end\nfunction onNothing() end\nout(host('onCheck'), host('onNothing'))",
             "Function_Stop,nil"),
            ("assignment_from_several_results",
             "function pair() return 3, 4 end\nlocal a, b = pair()\nout(a, b)", "3,4"),
            ("return_of_a_table_literal",
             "local function make() return {1, 2} end\nlocal t = make()\nout(#t, t[2])", "2,2"),
        ])


class LuaCapturedScopeTest(unittest.TestCase):
    def test_calls_share_the_captured_scope_safely(self):
        check_outputs(self, [
            ("local_recursion",
             "local function fib(n) if n < 2 then return n end return fib(n - 1) + fib(n - 2) end\nout(fib(15))", "610"),
            ("global_recursion",
             "function fact(n) if n <= 1 then return 1 end return n * fact(n - 1) end\nout(fact(6))", "720"),
            ("closures_keep_their_own_upvalues",
             "local function counter(start)\n local n = start\n return function() n = n + 1 return n end\nend\n"
             "local a, b = counter(10), counter(20)\nout(a(), a(), b(), a())", "11,12,21,13"),
            ("closures_capture_parameters",
             "local function adder(x) return function(y) return x + y end end\n"
             "local add2, add5 = adder(2), adder(5)\nout(add2(1), add5(1), add2(10))", "3,6,12"),
            ("closures_made_during_recursion",
             "local fs = {}\nlocal function make(n) if n > 0 then fs[#fs + 1] = function() return n end make(n - 1) end end\n"
             "make(3)\nout(fs[1](), fs[2](), fs[3]())", "3,2,1"),
            ("parameter_shadows_a_top_level_local",
             "local x = 'top'\nlocal function f(x) return x end\nout(f('param'), x, f('again'))", "param,top,again"),
            ("body_local_stays_inside",
             "local y = 'top'\nlocal function f() local y = 'inner' return y end\nout(f(), y, f())", "inner,top,inner"),
            ("upvalue_writes_are_shared",
             "local total = 0\nlocal function add(n) total = total + n end\nadd(2)\nadd(3)\nout(total)", "5"),
            ("missing_arguments_are_nil",
             "local function f(a, b) return b == nil end\nout(f(1))", "true"),
            ("error_mid_call_then_more_calls",
             "local x = 'top'\nlocal function boom(x) local z = 'z' error('bad') end\nlocal function ok(v) return v end\n"
             "local good = pcall(boom, 'param')\nout(good, x, ok('fine'), x, z)", "false,top,fine,top,nil"),
            ("caller_scope_survives_a_caught_error",
             "local function inner(a) local b = 'inner' error('x') end\n"
             "local function outer(a)\n local mine = 'outer'\n pcall(inner, 'z')\n return a .. mine\nend\nout(outer('A'), outer('B'))",
             "Aouter,Bouter"),
            ("unknown_global_is_nil", "out(neverSet, type(neverSet))", "nil,nil"),
        ])


class LuaLoopTest(unittest.TestCase):
    def test_range_loops(self):
        check_outputs(self, [
            ("break_in_a_numeric_loop",
             "local s = 0\nfor i = 1, 10 do if i > 3 then break end s = s + i end\nout(s)", "6"),
            ("goto_continue_in_a_numeric_loop",
             "local s = 0\nfor i = 1, 5 do\n if i % 2 == 0 then goto continue end\n s = s + i\n ::continue::\nend\nout(s)", "9"),
            ("bounds_are_read_once",
             "local n = 3\nlocal c = 0\nfor i = 1, n do n = 10 c = c + 1 end\nout(c)", "3"),
            ("each_step_has_its_own_variable",
             "local fs = {}\nfor i = 1, 3 do fs[i] = function() return i end end\nout(fs[1](), fs[2](), fs[3]())", "1,2,3"),
            ("nested_loops", "local s = ''\nfor i = 1, 2 do for j = 1, 2 do s = s .. i .. j end end\nout(s)", "11122122"),
            ("long_loop", "local s = 0\nfor i = 1, 100000 do s = s + 1 end\nout(s)", "100000"),
            ("loop_variable_does_not_leak", "local i = 'outer'\nfor i = 1, 2 do end\nout(i)", "outer"),
            ("ipairs", "local s = 0\nfor i, v in ipairs({5, 6, 7}) do s = s + i * v end\nout(s)", "38"),
            ("pairs_order",
             "local t = {10, 20}\nt.name = 'n'\nlocal s = ''\nfor k, v in pairs(t) do s = s .. k .. '=' .. v .. ';' end\nout(s)",
             "1=10;2=20;name=n;"),
            ("table_concat", "out(table.concat({1, 2, 3}, '-'))", "1-2-3"),
        ])

    def test_while_and_repeat(self):
        check_outputs(self, [
            ("while_with_break",
             "local i, s = 0, 0\nwhile i < 5 do i = i + 1 if i == 4 then break end s = s + i end\nout(s)", "6"),
            ("zero_is_true_in_a_condition",
             "local n = 0\nlocal v = 0\nwhile v do n = n + 1 if n == 3 then v = nil end end\nout(n)", "3"),
            ("repeat_with_break",
             "local n = 0\nrepeat n = n + 1 if n == 2 then break end until false\nout(n)", "2"),
            ("repeat_until_a_value", "local n = 0\nrepeat n = n + 1 until n >= 4\nout(n)", "4"),
        ])

    def test_numeric_loops_still_use_the_range_helper_spelling(self):
        # The interpreter recognises this exact helper call; the translator must keep it.
        record = run_lua([("range", "for i = 0, 3 do end")])["range"]
        self.assertIn("makeRangeArray(", record["hscript"])


class LuaTableBookkeepingTest(unittest.TestCase):
    def test_kept_tables_keep_fields_order_and_metatables_after_many_dropped_ones(self):
        check_outputs(self, [
            ("kept_table_survives",
             "local keep = {}\nkeep.name = 'kept'\nkeep[10] = 'sparse'\n"
             "setmetatable(keep, {__index = function(t, k) return 'meta:' .. k end})\n"
             "for i = 1, 10000 do local t = {i, x = i} t.extra = i setmetatable(t, {}) end\n"
             "local order = ''\nfor k, v in pairs(keep) do order = order .. tostring(k) .. ';' end\n"
             "out(keep.name, keep[10], keep.missing, order)",
             "kept,sparse,meta:missing,name;10;"),
        ])

    def test_table_maps_hold_keys_weakly_on_native_builds(self):
        source = (ROOT / "source" / "LuaCompatInterp.hx").read_text(encoding="utf-8")
        self.assertRegex(source, r"#if cpp\s+typedef LuaTableMap<V> = haxe\.ds\.WeakMap<Dynamic, V>;\s+#else\s+"
                                 r"typedef LuaTableMap<V> = ObjectMap<Dynamic, V>;\s+#end")
        for field in ("luaTables", "extraFields", "objectFields", "extraOrder", "metatables", "multiCallees"):
            self.assertRegex(source, r"\tvar " + field + r":LuaTableMap<", field)
        self.assertNotIn("new ObjectMap()", source.split("function snapshotSourceArray")[0].split("class LuaCompatInterp")[1])


class LuaRuntimeSourceTest(unittest.TestCase):
    def test_no_regex_on_lua_runtime_paths(self):
        for name in ("LuaCompatInterp.hx", "LuaStdlib.hx", "LuaValues.hx", "LuaPattern.hx"):
            source = (ROOT / "source" / name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"~/|new EReg|EReg\(", source), name)
        engine = (ROOT / "source" / "EngineCompat.hx").read_text(encoding="utf-8")
        start = engine.index("public static function luaDynamicGlobalAllowed(")
        end = engine.index("public static function luaGetScriptGlobal(", start)
        self.assertIsNone(re.search(r"~/|EReg", engine[start:end]))

    def test_calls_and_loops_build_nothing_per_run(self):
        source = (ROOT / "source" / "LuaCompatInterp.hx").read_text(encoding="utf-8")
        start = source.index("function luaFunction(")
        body = source[start:source.index("function luaFunctionBody(", start)]
        call = body[body.index("Reflect.makeVarArgs("):body.index("if (name != null) {")]
        self.assertNotIn("duplicate(", call)
        self.assertIn("me.locals = capturedLocals;", call)
        self.assertNotIn("Tools.mk(EWhile", source)
        self.assertNotIn("Tools.mk(EDoWhile", source)
        self.assertNotIn("boolCondition", source)
        self.assertNotIn("STRING_NAMES.indexOf", source)


FIXTURE = r'''
@:access(LuaCompatInterp)
class Fixture {
 static function main() {
  var keys:Array<String> = __KEYS__;
  var lua = ~/^default(?:Player|Opponent)?Strum(?:[XY][0-9]+|[0-9]+[XY])$/;
  var engine = ~/^default(?:Player|Opponent)Strum[XY][0-3]$/;
  var rows = [];
  for (key in keys)
   rows.push({key: key, lua: LuaCompatInterp.readOnlyGlobal(key), luaRegex: lua.match(key),
    engine: EngineCompat.luaDynamicGlobalAllowed(key), engineRegex: key == 'objects' || engine.match(key)});
  Sys.println("ROWS " + haxe.Json.stringify(rows));
 }
}
'''

KEYS = [
    "defaultStrum0X", "defaultStrumX0", "defaultStrumX12", "defaultStrum12Y", "defaultPlayerStrumX12",
    "defaultOpponentStrum3Y", "defaultPlayerStrumX", "defaultStrum", "defaultStrumXY", "defaultStrum0",
    "defaultStrum0X1", "defaultStrumX0Y", "default", "defaultplayerStrumX0", "defaultPlayerOpponentStrumX0",
    "defaultStrumX0\n", "defaultStrumX0\n\n", "defaultPlayerStrumY3\n", "xdefaultStrumX0", "defaultPlayerStrumX0",
    "defaultOpponentStrumY3", "defaultOpponentStrumY4", "defaultStrumX0 ", "defaultPlayerStrumZ0",
    "defaultPlayerStrumX00", "", "objects", "defaultOpponentStrum", "defaultPlayerStrum0Y", "defaultStrumx0",
]


class LuaGlobalNameScanTest(unittest.TestCase):
    def test_hand_scans_match_the_patterns_they_replace(self):
        source = FIXTURE.replace("__KEYS__", json.dumps(KEYS))
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Fixture.hx").write_text(source, newline='\n', encoding='utf-8')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-main", "Fixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        line = next(line for line in result.stdout.splitlines() if line.startswith("ROWS "))
        rows = json.loads(line[5:])
        self.assertEqual(len(rows), len(KEYS))
        for row in rows:
            with self.subTest(row["key"]):
                self.assertEqual(row["lua"], row["luaRegex"])
                self.assertEqual(row["engine"], row["engineRegex"])
        self.assertTrue(any(row["lua"] for row in rows))
        self.assertTrue(any(row["engine"] for row in rows))


PROBE_FIXTURE = r'''
import hscript.Expr;

@:access(hscript.Interp)
class Probe extends LuaCompatInterp {
 public var returnNodes = 0;
 override public function expr(expression:Expr):Dynamic {
  switch (hscript.Tools.expr(expression)) {
   case EReturn(_): returnNodes++;
   default:
  }
  return super.expr(expression);
 }
}

@:access(hscript.Interp)
class Fixture {
 static function main() {
  var cases:Array<Array<String>> = __CASES__;
  for (entry in cases) {
   var seen:Array<String> = [];
   var status = "ok";
   var rangeCalls = 0;
   var interp = new Probe();
   var after = "";
   var returnNodes = -1;
   try {
    var result = LuaCompat.translate(entry[1], entry[0] + ".lua");
    var report = function(args:Array<Dynamic>):Dynamic {
     seen.push([for (value in args) value == null ? "nil" : Std.string(value)].join(","));
     return null;
    };
    for (name => value in [
     "Std" => (Std : Dynamic), "Math" => (Math : Dynamic), "StringTools" => (StringTools : Dynamic),
     "luaNumber" => (EngineCompat.luaNumber : Dynamic), "luaString" => (EngineCompat.luaString : Dynamic),
     "luaType" => (EngineCompat.luaType : Dynamic), "luaTableValue" => (EngineCompat.luaTableValue : Dynamic)
    ]) interp.variables.set(name, value);
    interp.variables.set("makeRangeArray", function(max:Int, ?min:Int = 0):Array<Int> {
     rangeCalls++;
     return [for (x in min...max) x];
    });
    interp.variables.set("out", Reflect.makeVarArgs(report));
    interp.installTableHelpers();
    interp.execute(new hscript.Parser().parseString(result.hscript));
    returnNodes = interp.returnNodes;
    var boom:Dynamic = interp.variables.get("boom");
    if (boom != null) {
     var locals = interp.locals;
     var declared = interp.declared.length;
     var depth = interp.depth;
     try Reflect.callMethod(null, boom, ["arg"]) catch (_:Dynamic) {}
     after = (interp.locals == locals) + "," + (interp.declared.length == declared) + "," + (interp.depth == depth);
    }
   } catch (error:Dynamic) status = "threw " + Std.string(error);
   Sys.println("CASE " + haxe.Json.stringify({name: entry[0], out: seen.join("|"), status: status,
    rangeCalls: rangeCalls, returnNodes: returnNodes, after: after}));
  }
 }
}
'''


def run_probe(cases):
    source = PROBE_FIXTURE.replace("__CASES__", json.dumps([[name, lua] for name, lua in cases]))
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "Fixture.hx").write_text(source, newline='\n', encoding='utf-8')
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
             "-main", "Fixture", "--interp"],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    records = {}
    for line in result.stdout.splitlines():
        if line.startswith("CASE "):
            record = json.loads(line[5:])
            records[record["name"]] = record
    return records


class LuaFastPathProbeTest(unittest.TestCase):
    """The fast paths are really taken, so the cheaper code is what runs."""

    def test_fast_paths_are_taken(self):
        records = run_probe([
            ("tail_returns",
             "local function a(x) return x + 1 end\nlocal function b() return a(1) end\n"
             "local function c() local t = {} return t end\nout(a(1), b(), #c())"),
            ("nested_return",
             "local function f(x) if x then return 1 end return 2 end\nout(f(true), f(false))"),
            ("range_loops",
             "local s = 0\nfor i = 1, 4 do s = s + i end\nfor k, v in pairs({5, 6}) do s = s + v end\n"
             "for i, v in ipairs({7}) do s = s + v end\nout(s)"),
            ("script_range_helper",
             "function makeRangeArray(high, low) out('own', high, low) return {} end\nfor i = 1, 2 do out(i) end\nout('end')"),
            ("error_escaping_a_call",
             "local x = 'top'\nfunction boom(x) local inner = 1 error('bad') end\nout(x)"),
        ])
        for name, record in records.items():
            with self.subTest(name):
                self.assertEqual(record["status"], "ok")
        self.assertEqual(records["tail_returns"]["out"], "2,2,0")
        # No return node is run as a node: each ends its body and hands its value back.
        self.assertEqual(records["tail_returns"]["returnNodes"], 0)
        self.assertEqual(records["nested_return"]["out"], "1,2")
        # Only the return inside the if is run (and thrown); the closing one is not.
        self.assertEqual(records["nested_return"]["returnNodes"], 1)
        self.assertEqual(records["range_loops"]["out"], "28")
        self.assertEqual(records["range_loops"]["rangeCalls"], 0)
        # A script's own function of that name is still the one called.
        self.assertEqual(records["script_range_helper"]["out"], "own,3,1|end")
        self.assertEqual(records["script_range_helper"]["rangeCalls"], 0)
        # An error leaving a call outside pcall puts the caller's scope back.
        self.assertEqual(records["error_escaping_a_call"]["out"], "top")
        self.assertEqual(records["error_escaping_a_call"]["after"], "true,true,true")

    def test_range_helper_is_called_for_bounds_that_are_not_whole_numbers(self):
        source = (ROOT / "source" / "LuaCompatInterp.hx").read_text(encoding="utf-8")
        start = source.index("function luaRangeLoop(")
        body = source[start:source.index("override public function expr(", start)]
        self.assertIn("!Std.isOfType(high, Int) || !Std.isOfType(low, Int)", body)
        self.assertIn("call(null, helper,", body)


if __name__ == "__main__":
    unittest.main()
