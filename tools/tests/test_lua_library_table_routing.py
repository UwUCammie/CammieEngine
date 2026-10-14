"""math.max/min, table.remove and script extensions of library tables reach the Lua scope's library."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaLibraryTableRoutingTest(unittest.TestCase):
    def test_library_calls(self):
        check_outputs(self, [
            ("max_and_min_take_any_number_of_values",
             "out(math.max(1, 5, 3), math.min(4, 2, 8), math.max(7))", "5,2,7"),
            ("max_and_min_take_every_result_of_a_trailing_call",
             "local t = {3, 9, 4}\nout(math.max(unpack(t)), math.min(table.unpack(t)))", "9,3"),
            ("a_spread_after_another_value_is_every_value",
             "local t = {3, 9, 4}\nout(math.max(1, unpack(t)), math.min(5, table.unpack(t)), math.max(0, select(2, 4, 7)))", "9,3,7"),
            ("an_alias_of_max_is_the_variadic_one",
             "local mx = math.max\nout(mx(4, 8, 2))", "8"),
            ("two_values_still_work",
             "out(math.max(1, 2), math.min(3, 4), math.max(-1, -2))", "2,3,-1"),
            ("remove_returns_the_removed_value",
             "local t = {10, 20, 30}\nlocal v = table.remove(t, 2)\nout(v, #t, t[2], table.remove(t))", "20,2,30,30"),
            ("remove_inside_an_expression",
             "local t = {'a', 'b'}\nout('got ' .. table.remove(t, 1) .. '!', #t)", "got a!,1"),
            ("remove_out_of_range_is_nil",
             "local t = {1}\nout(table.remove(t, 5), #t)", "nil,1"),
            ("script_assigned_math_field",
             "math.lerp2 = function(a, b, r) return a + (b - a) * r end\nout(math.lerp2(0, 10, 0.5))", "5"),
            ("script_declared_math_function",
             "function math.round(x) return math.floor(x + 0.5) end\nout(math.round(2.6))", "3"),
            ("script_replaces_a_routed_name",
             "function math.lerp(a, b, r) return 'own' end\nout(math.lerp(0, 10, 0.5))", "own"),
            ("script_declared_string_and_table_functions",
             "function string.startsWith(s, p) return s:sub(1, #p) == p end\nfunction table.count(t) return #t end\nout(string.startsWith('hello', 'he'), table.count({1, 2}))",
             "true,2"),
            ("library_names_inside_longer_names_are_left_alone",
             "local mymath = {pivot = 4, max = function(a, b) return 'own' end}\nlocal obj = {tostring = function() return 'obj' end}\nout(mymath.pivot, mymath.max(1, 2), obj.tostring())",
             "4,own,obj"),
        ])

    def test_two_value_max_keeps_the_spelling_every_interpreter_knows(self):
        record = run_lua([("plain", "local a = math.max(x, y)\nlocal b = math.max(x, y, z)")])["plain"]
        self.assertIn("var a = Math.max(x, y);", record["hscript"])
        self.assertIn("var b = math.max(x, y, z);", record["hscript"])

    def test_remove_is_no_longer_a_splice(self):
        record = run_lua([("remove", "local t = {1, 2}\ntable.remove(t, 1)")])["remove"]
        self.assertNotIn("splice", record["hscript"])
        self.assertIn("table.remove(t, 1)", record["hscript"])


if __name__ == "__main__":
    unittest.main()
