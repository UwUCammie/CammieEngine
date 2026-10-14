"""Lua block keywords may sit anywhere on a line; the translation must not care."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaBlockLayoutTest(unittest.TestCase):
    def test_blocks_written_across_or_within_lines_run_the_same(self):
        check_outputs(self, [
            ("if_statement_then_else_on_next_line",
             "local a = 1\nlocal r\nif a == 1 then r = 'one'\nelse r = 'other' end\nout(r)", "one"),
            ("if_statement_then_elseif_on_next_line",
             "local a = 2\nlocal r\nif a == 1 then r = 'one'\nelseif a == 2 then r = 'two' end\nout(r)", "two"),
            ("else_if_as_two_words",
             "local a = 2\nlocal r = 'none'\nif a == 1 then\n  r = 'one'\nelse if a == 2 then\n  r = 'two'\nend\nend\nout(r)",
             "two"),
            ("one_line_function_with_if",
             "function f(x) if x == 1 then return 'one' end end\nout(f(1))", "one"),
            ("one_line_function_with_if_else",
             "function f(x) if x == 1 then return 'one' else return 'other' end end\nout(f(2))", "other"),
            ("nested_if_on_one_line",
             "local a, b = 1, 2\nif a == 1 then if b == 2 then out('both') end end", "both"),
            ("while_on_one_line", "local i = 0\nwhile i < 3 do i = i + 1 end\nout(i)", "3"),
            ("statement_after_end_on_the_same_line", "local i = 0\nwhile i < 3 do i = i + 1 end out(i)", "3"),
            ("bare_do_block_scopes_its_locals", "local x = 1\ndo\n  local x = 2\n  out(x)\nend\nout(x)", "2|1"),
            ("while_body_on_header_line", "local i = 0\nwhile i < 2 do i = i + 1\nend\nout(i)", "2"),
            ("for_body_on_header_line", "local s = 0\nfor i = 1, 3 do s = s + i\nend\nout(s)", "6"),
            ("several_statements_per_branch_line",
             "local a = 2\nlocal r = ''\nif a == 1 then r = 'x' out('one')\nelseif a == 2 then r = 'y' out('two')\n"
             + "else r = 'z' end\nout(r)", "two|y"),
            ("two_if_blocks_on_one_line",
             "local n = 0\nif true then n = 1 end if n == 1 then n = 2 end\nout(n)", "2"),
            ("one_line_local_function_with_else",
             "local function sel(c) if c then return 'T' else return 'F' end end\nout(sel(true), sel(false))", "T,F"),
            ("then_on_the_line_after_the_condition",
             "local a = 3\nif a == 3\nthen out('late then') end", "late then"),
            ("keywords_inside_strings_and_names_are_text",
             "local friend = 'if x then y else z end'\nlocal ending = 2\nlocal t = {done = 'do it'}\n"
             + "out(friend, ending, t.done)", "if x then y else z end,2,do it"),
        ])

    def test_blocks_already_on_their_own_lines_translate_exactly_as_before(self):
        lua = ("function onCreate()\n\tlocal total = 0\n\tfor i = 0, 3 do\n\t\tif i == 2 then\n\t\t\ttotal = total + 10\n"
               + "\t\telseif i == 3 then\n\t\t\ttotal = total + 100\n\t\telse\n\t\t\ttotal = total + 1\n\t\tend\n\tend\n"
               + "\treturn total\nend\n")
        expected = "\n".join([
            "// lua-compat-translated:v1",
            "function onCreate() {",
            "var total = 0;",
            "for (i in makeRangeArray(Std.int(3) + 1, Std.int(0))) {",
            "if (i == 2 ) {",
            "total = total + 10;",
            "} else if (i == 3 ) {",
            "total = total + 100;",
            "} else {",
            "total = total + 1;",
            "}",
            "}",
            "return total;",
            "return null;",
            "}",
            "",
        ])
        record = run_lua([("canonical", lua)])["canonical"]
        self.assertEqual(record["hscript"], expected)
        self.assertTrue(record["supported"])

    def test_one_line_block_gives_the_same_program_as_its_spread_out_form(self):
        records = run_lua([
            ("compact", "function f(a) if a then return 1 else return 2 end end"),
            ("spread", "function f(a)\nif a then\nreturn 1\nelse\nreturn 2\nend\nend"),
        ])
        self.assertEqual(records["compact"]["hscript"].strip(), records["spread"]["hscript"].strip())


if __name__ == "__main__":
    unittest.main()
