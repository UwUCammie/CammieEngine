"""repeat/until, the goto-continue idiom and varargs."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaControlFlowGapsTest(unittest.TestCase):
    def test_repeat_until(self):
        check_outputs(self, [
            ("counts_to_three", "local i = 0\nrepeat i = i + 1 until i >= 3\nout(i)", "3"),
            ("runs_at_least_once", "local n = 0\nrepeat n = n + 1 until true\nout(n)", "1"),
            ("condition_reads_body_locals", "local n = 0\nrepeat\n local done = n >= 2\n n = n + 1\nuntil done\nout(n)", "3"),
        ])

    def test_goto_continue(self):
        check_outputs(self, [
            ("numeric_loop", "local s = 0\nfor k = 1, 4 do\n  if k == 2 then goto continue end\n  s = s + k\n  ::continue::\nend\nout(s)", "8"),
            ("stepped_loop_still_advances",
             "local s = 0\nfor k = 1, 4, 1.5 do\n  if k == 1 then goto skip end\n  s = s + k\n  ::skip::\nend\nout(s)", "6.5"),
            ("while_loop",
             "local i, s = 0, 0\nwhile i < 4 do\n  i = i + 1\n  if i == 3 then goto next end\n  s = s + i\n  ::next::\nend\nout(s)", "7"),
            ("ipairs_loop",
             "local s = 0\nfor _, v in ipairs({1, 2, 3}) do\n  if v == 2 then goto continue end\n  s = s + v\n  ::continue::\nend\nout(s)", "4"),
        ])

    def test_other_goto_shapes_keep_their_diagnostic(self):
        records = run_lua([
            ("label_not_last", "for k = 1, 2 do\n  goto mid\n  ::mid::\n  out(k)\nend"),
            ("outside_a_loop", "goto done\nout(1)\n::done::"),
        ])
        for name in records:
            with self.subTest(name):
                self.assertIn("lua-goto", records[name]["diagnostics"])
                self.assertTrue(records[name]["parses"])

    def test_varargs(self):
        check_outputs(self, [
            ("collected_in_a_table", "local function f(...)\n  local args = {...}\n  return #args\nend\nout(f(1, 2, 3))", "3"),
            ("counted_with_select", "local function f(...)\n  return select('#', ...)\nend\nout(f(1, nil, 3))", "3"),
            ("passed_on", "local function g(a, b) return a + b end\nlocal function f(...) return g(...) end\nout(f(1, 2))", "3"),
            ("after_named_parameters",
             "function tail(first, ...)\n  local a, b = ...\n  return first .. a .. b\nend\nout(tail('x', 'y', 'z'))", "xyz"),
            ("anonymous_function", "local f = function(...) return select(2, ...) end\nout(f('a', 'b'))", "b"),
            ("statement_right_after_the_varargs",
             "local function second(...) local a, b = ... return b end\nout(second('x', 'y'))", "y"),
            ("unused_varargs_on_a_callback", "function onCreatePost( ... )\n  out('ran')\nend\nonCreatePost()", "ran"),
        ])

    def test_unused_varargs_leave_a_plain_function(self):
        record = run_lua([("plain", "function onCreatePost( ... ) end")])["plain"]
        self.assertTrue(record["supported"])
        self.assertIn("function onCreatePost() {", record["hscript"])
        self.assertNotIn("luaVarargFunction", record["hscript"])


if __name__ == "__main__":
    unittest.main()
