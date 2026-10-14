"""Floor division, numeric string addition, trailing calls into method calls and table walks."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaOperatorExtrasTest(unittest.TestCase):
    def test_operators_and_walks(self):
        check_outputs(self, [
            ("floor_division",
             "out(7 // 2, -7 // 2, 7.5 // 2, 9 // 3)", "3,-4,3,3"),
            ("floor_division_precedence",
             "local a = 7\nout(1 + a // 2 * 3, a // 2 ^ 2, -a // 2, (a + 1) // 3, a / 2 // 1)", "10,1,-4,2,3"),
            ("two_numeric_strings_add",
             "local a, b = '5', '5'\nout(a + b, a .. b, a + 1, 'x' .. a + b)", "10,55,6,x10"),
            ("event_values_add",
             "local value1, value2 = '0.5', '1.25'\nout(value1 + value2)", "1.75"),
            ("text_that_is_not_a_number_still_joins",
             "local a, b = 'x', 'y'\nlocal c = a .. b\nout(c, a .. 1 .. b)", "xy,x1y"),
            ("trailing_call_into_a_worked_out_receiver",
             "local function pick() return {sum = function(self, a, b, c) return a + b + c end} end\nlocal function three() return 1, 2, 3 end\nout(pick():sum(three()))",
             "6"),
            ("trailing_call_into_a_string_method",
             "local function two() return 1, 2 end\nlocal s = '%d-%d'\nout(s:format(two()), ('%d+%d'):format(two()))",
             "1-2,1+2"),
            ("trailing_call_into_a_dotted_method",
             "local o = {}\nfunction o:sum(a, b, c) return a + b + c end\nlocal function three() return 1, 2, 3 end\nout(o:sum(three()))",
             "6"),
            ("next_walk_clearing_the_current_key",
             "local t = {a = 1, b = 2, c = 3}\nlocal n = 0\nfor k, v in next, t do t[k] = nil n = n + 1 end\nout(n, next(t))",
             "3,nil"),
            ("next_by_hand_clearing_as_it_goes",
             "local t = {a = 1, b = 2, c = 3}\nlocal n = 0\nlocal k = next(t)\nwhile k do t[k] = nil n = n + 1 k = next(t, k) end\nout(n)",
             "3"),
            ("next_skips_fields_cleared_ahead",
             "local t = {a = 1, b = 2, c = 3}\nlocal n = 0\nfor k in next, t do\n  n = n + 1\n  if n == 1 then for _, other in ipairs({'a', 'b', 'c'}) do if other ~= k then t[other] = nil end end end\nend\nout(n)",
             "1"),
            # Lua leaves the order of a walk open, so only the visits are counted.
            ("pairs_clearing_visits_every_key_once",
             "local t = {a = 1, b = 2, c = 3}\nlocal seen = ''\nfor k, v in pairs(t) do t[k] = nil seen = seen .. k end\nout(#seen, seen:find('a') ~= nil, seen:find('b') ~= nil, seen:find('c') ~= nil, next(t))",
             "3,true,true,true,nil"),
            ("nested_pairs_over_two_tables",
             "local outer = {x = {1, 2}, y = {3}}\nlocal total = 0\nfor name, list in pairs(outer) do for i, v in pairs(list) do total = total + v end end\nout(total)",
             "6"),
            # The inner loop over another table must not make the outer walk
            # take its keys again, or clearing the current key skips the next one.
            ("clearing_inside_a_loop_with_a_nested_walk",
             "local t = {a = 1, b = 2, c = 3}\nlocal other = {x = 1}\nlocal seen = ''\nfor k, v in pairs(t) do\n  for _, w in pairs(other) do end\n  t[k] = nil\n  seen = seen .. tostring(k) .. tostring(v)\nend\nout(#seen, seen:find('a1') ~= nil, seen:find('b2') ~= nil, seen:find('c3') ~= nil, next(t))",
             "6,true,true,true,nil"),
        ])

    def test_floor_division_keeps_the_division_operator(self):
        record = run_lua([("spelling", "local q = a // b")])["spelling"]
        self.assertIn("var q = a / __luaFloorDivisor(b);", record["hscript"])


if __name__ == "__main__":
    unittest.main()
