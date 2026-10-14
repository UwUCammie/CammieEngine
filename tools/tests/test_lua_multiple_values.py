"""Functions may return several values, and an assignment sets all its names at once."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaMultipleValuesTest(unittest.TestCase):
    def test_several_results_follow_lua_rules(self):
        check_outputs(self, [
            ("return_two_and_swap",
             "local function f() return 1, 2 end\nlocal a, b = f()\na, b = b, a\nout(a, b)", "2,1"),
            ("fewer_results_than_names", "local function f() return 1, 2 end\nlocal a, b, c = f()\nout(a, b, c)", "1,2,nil"),
            ("globals_take_every_result", "function three() return 1, 2, 3 end\nx, y, z = three()\nout(x, y, z)", "1,2,3"),
            ("last_argument_expands_for_lua_functions",
             "local function f() return 1, 2 end\nlocal function sum(a, b, c) return a + b + c end\nout(sum(10, f()))", "13"),
            ("single_assignment_takes_the_first", "local function f() return 1, 2 end\nlocal x = f()\nout(x)", "1"),
            ("parentheses_keep_one_result",
             "local function f() return 1, 2 end\nlocal function count(...) return select('#', ...) end\n"
             + "out(count(f()), count((f())))", "2,1"),
            ("call_in_the_middle_gives_one",
             "local function f() return 1, 2 end\nlocal function count(...) return select('#', ...) end\nout(count(f(), 9))", "2"),
            ("tail_call_passes_results_on",
             "local function f() return 1, 2 end\nlocal function g() return f() end\nlocal a, b = g()\nout(a, b)", "1,2"),
            ("table_constructor_keeps_every_result", "local function f() return 1, 2 end\nlocal t = {0, f()}\nout(#t, t[3])", "3,2"),
            ("swap_of_table_slots", "local t = {1, 2}\nt[1], t[2] = t[2], t[1]\nout(t[1], t[2])", "2,1"),
            ("engine_style_function_sees_one_result", "local function f() return 1, 2 end\nout(f())", "1"),
            ("unpack_feeds_a_lua_function",
             "local t = {1, 2}\nlocal function add(a, b) return a + b end\nout(add(unpack(t)))", "3"),
        ])

    def test_the_engine_only_ever_gets_the_first_result(self):
        records = check_outputs(self, [
            ("callback_returning_two_values",
             "function onStartCountdown() return Function_Stop, 1 end\n"
             + "local function inner() return 'first', 'second' end\nfunction relay() return inner() end\n"
             + "out(host('onStartCountdown'), host('relay'))", "Function_Stop,first"),
        ])
        self.assertIn("return luaValues(Function_Stop, 1);", records["callback_returning_two_values"]["hscript"])

    def test_a_callback_run_by_an_engine_function_still_returns_one_value(self):
        # `host` stands for an engine function that runs a script callback. Being
        # called from a spot that reads several results must not change what the
        # callback hands to the engine.
        check_outputs(self, [
            ("engine_call_as_a_tail_call",
             "local function inner() return 'first', 'second' end\nfunction relay() return inner() end\n"
             + "local function viaEngine() return host('relay') end\nlocal a, b = viaEngine()\nout(a, b)", "first,nil"),
            ("engine_call_as_the_last_argument",
             "local function inner() return 'first', 'second' end\nfunction relay() return inner() end\n"
             + "all(host('relay'))\nlocal t = {host('relay')}\nout(#t, t[1])", "first|1,first"),
            ("engine_call_on_the_right_of_an_assignment",
             "local function inner() return 'first', 'second' end\nfunction relay() return inner() end\n"
             + "local a, b = host('relay')\nout(a, b)", "first,nil"),
        ])

    def test_method_calls_and_iterators_still_pass_every_result(self):
        check_outputs(self, [
            ("method_on_a_call_result",
             "local function make() return {pair = function(self) return 1, 2 end} end\n"
             + "local a, b = make():pair()\nout(a, b)", "1,2"),
            ("string_method_on_a_literal", "local a, b = ('hello world'):find('wor')\nout(a, b)", "7,9"),
            ("iterator_function_with_two_results",
             "local function each(list)\n local i = 0\n return function()\n  i = i + 1\n"
             + "  if list[i] then return i, list[i] end\n end\nend\n"
             + "for index, value in each({'a', 'b'}) do out(index, value) end", "1,a|2,b"),
        ])

    def test_simple_parallel_assignment_keeps_its_direct_form(self):
        record = run_lua([("plain", "local a, b = 1, 2\nout(a, b)")])["plain"]
        self.assertIn("var a = 1;\nvar b = 2;", record["hscript"])
        self.assertEqual(record["out"], "1,2")


if __name__ == "__main__":
    unittest.main()
