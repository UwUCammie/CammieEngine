"""Numeric loops keep fractional bounds; generic loops accept any iterator."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaForLoopsTest(unittest.TestCase):
    def test_numeric_loops(self):
        check_outputs(self, [
            ("fractional_step", "local n = 0\nfor i = 0, 1, 0.25 do n = n + 1 end\nout(n)", "5"),
            ("fractional_bounds", "local s = 0\nfor i = 0.5, 2.5 do s = s + i end\nout(s)", "4.5"),
            ("call_with_commas_as_bound", "local n = 0\nfor i = 1, math.max(2, 3) do n = n + 1 end\nout(n)", "3"),
            ("counting_down", "local s = ''\nfor i = 3, 1, -1 do s = s .. i end\nout(s)", "321"),
            ("empty_range", "local n = 0\nfor i = 1, 0 do n = n + 1 end\nout(n)", "0"),
            ("variable_bounds", "local from, to = 2, 4\nlocal s = 0\nfor i = from, to do s = s + i end\nout(s)", "9"),
            ("loop_variable_stays_inside", "local i = 'outer'\nfor i = 1.5, 2 do end\nfor i = 1, 2 do end\nout(i)", "outer"),
            ("body_cannot_derail_the_counter", "local n = 0\nfor i = 1, 3, 1.0 do i = 10; n = n + 1 end\nout(n)", "3"),
        ])

    def test_generic_loops(self):
        check_outputs(self, [
            ("gmatch_with_two_captures",
             "local s = ''\nfor op, num in string.gmatch('+12-3', '(%p)(%w+)') do s = s .. op .. num .. ';' end\nout(s)", "+12;-3;"),
            ("gmatch_as_a_method_on_an_expression",
             "local n = 0\nlocal s = 'a,b'\nfor part in (s .. ','):gmatch('([^,%s]+)') do n = n + 1 end\nout(n)", "2"),
            ("next_and_table", "local t = {5, 6}\nlocal sum = 0\nfor i, v in next, t do sum = sum + v end\nout(sum)", "11"),
            ("script_iterator_function",
             "local function upto(n)\n local i = 0\n return function()\n  i = i + 1\n  if i <= n then return i end\n end\nend\n"
             + "local sum = 0\nfor v in upto(3) do sum = sum + v end\nout(sum)", "6"),
            ("pairs_with_keys", "local t = {a = 1}\nlocal seen = ''\nfor k, v in pairs(t) do seen = seen .. k .. v end\nout(seen)", "a1"),
            ("loop_names_stay_inside", "local k = 'outer'\nfor k, v in next, {1} do end\nout(k)", "outer"),
        ])

    def test_whole_number_literal_range_keeps_the_ready_made_range(self):
        record = run_lua([("range", "for i = 0, 3 do end")])["range"]
        self.assertIn("for (i in makeRangeArray(Std.int(3) + 1, Std.int(0))) {", record["hscript"])


if __name__ == "__main__":
    unittest.main()
