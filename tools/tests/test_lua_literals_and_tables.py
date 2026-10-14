"""Table constructors and literal spellings Lua accepts beyond the simple forms."""
import unittest

from lua_translate_support import check_outputs


class LuaLiteralsAndTablesTest(unittest.TestCase):
    def test_table_constructors(self):
        check_outputs(self, [
            ("mixed_sequence_and_fields", "local t = { 1, 2, name = 'n', [10] = 'x' }\nout(#t, t.name, t[10], t[2])", "2,n,x,2"),
            ("bracketed_keys", "local k = 'dyn'\nlocal t = {[1] = 'a', [k] = 2, [k .. 'X'] = 3, ['my key'] = 4}\n"
             + "out(t[1], t.dyn, t.dynX, t['my key'])", "a,2,3,4"),
            ("semicolon_separators", "local t = {1; 2; 3}\nlocal named = {a = 1; b = 2}\nout(#t, named.a + named.b)", "3,3"),
            ("function_under_a_computed_key", "local key = 'x'\nlocal values = {[key] = function() return 7 end}\nout(values.x())", "7"),
            ("plain_forms_are_unchanged", "local list = {1, 2}\nlocal record = {a = 1}\nout(#list, record.a)", "2,1"),
        ])

    def test_literal_spellings(self):
        check_outputs(self, [
            ("long_string", "local s = [[two\nlines]]\nout(#s, s == 'two\\nlines')", "9,true"),
            ("long_string_with_level", "local s = [==[x]]y]==]\nout(s)", "x]]y"),
            ("long_string_keeps_the_next_statement", "local s = [[abc]]\nout(#s)\nout('next')", "3|next"),
            ("decimal_and_hex_escapes", "out('\\65\\066', '\\x41', #'\\65\\066')", "AB,A,2"),
            ("exponent_without_decimal_point", "out(1e2, 1E-1, 2.5e1, 0x10)", "100,0.1,25,16"),
            ("call_with_a_bare_string", "local function f(s) return s .. '!' end\nout(f'hi', f \"yo\")", "hi!,yo!"),
            ("brackets_in_quoted_strings_are_text", "local s = 'a[[b]]c'\nout(s)", "a[[b]]c"),
            ("block_comments_with_and_without_level",
             "--[[ one\nout('hidden') ]]\n--[==[ two ]] still comment\nout('hidden') ]==]\nout('shown') -- tail", "shown"),
        ])


if __name__ == "__main__":
    unittest.main()
