"""`#` measures whatever expression follows it, not just a plain name."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaLengthOperatorTest(unittest.TestCase):
    def test_length_of_any_operand(self):
        check_outputs(self, [
            ("names_and_literals", "local t = {1,2,3}\nlocal s = 'hello'\nout(#t, #s, #'abc', #t + 1)", "3,5,3,4"),
            ("parenthesised", "local lists = {a={1,2,3}}\nout(#(lists.a), #lists['a'], #'abc')", "3,3,3"),
            ("indexed", "local o = {{1,2,3},{4}}\nout(#o[1], #o[2])", "3,1"),
            ("call_result", "local function f() return {1,2} end\nout(#f())", "2"),
            ("as_a_call_argument", "local words = {x = {'a', 'b', 'c'}}\nlocal key = 'x'\nout(math.max(1, #words[key]) + 1)", "4"),
            ("hash_inside_strings_is_text", "local colour = '#FF0000'\nlocal t = {1}\nout(colour, '#t', #t)", "#FF0000,#t,1"),
        ])

    def test_operand_is_wrapped_whole(self):
        record = run_lua([("text", "local n = #t[k] + #(t) + #f() + #a.b[c].d + #'abc'")])["text"]
        for expected in ("luaSequenceLength(t[k])", "luaSequenceLength((t))", "luaSequenceLength(f())",
                         "luaSequenceLength(a.b[c].d)", "luaSequenceLength('abc')"):
            self.assertIn(expected, record["hscript"])
        self.assertEqual(record["diagnostics"], "")


if __name__ == "__main__":
    unittest.main()
