"""`text:method(...)` calls the Lua string library, whatever the receiver looks like."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaStringMethodCallsTest(unittest.TestCase):
    def test_string_receivers_use_the_string_library(self):
        check_outputs(self, [
            ("variable_receiver", "local s = 'Hello'\nout(s:len(), s:sub(2, 3), s:upper(), s:lower())", "5|el|HELLO|hello".replace("|", ",")),
            ("chained_calls", "local songName = 'My-Song'\nout(songName:gsub('-', ' '):lower())", "my song"),
            ("three_links", "local songName = 'My-Demon'\nout(songName:gsub('-', ' '):lower():upper())", "MY DEMON"),
            ("parenthesised_literal", "out(('My-Song'):gsub('-', ' '):lower(), ('x'):rep(3))", "my song,xxx"),
            ("parenthesised_concatenation", "local s = 'ab'\nout((s .. ','):len())", "3"),
            ("method_result_in_arithmetic", "local s = 'abc'\nlocal n = s:len() + ('de'):len()\nout(n)", "5"),
            ("pattern_match", "local s = 'abc123'\nout(s:match('%d+'))", "123"),
            ("every_result_reaches_a_lua_function", "local s = 'hello world'\nall(s:find('wor'))", "7,9"),
            ("method_call_inside_arguments", "local s = 'a-b'\nout(#s:gsub('-', ''), 'x' .. s:upper())", "2,xA-B"),
        ])

    def test_table_receivers_still_call_their_own_functions(self):
        check_outputs(self, [
            ("chained_user_methods",
             "local obj = {n = 1}\nobj.inc = function(self, by) self.n = self.n + by; return self end\n"
             + "obj:inc(2):inc(3)\nout(obj.n)", "6"),
            ("receiver_is_evaluated_once",
             "local made = 0\nlocal function make() made = made + 1; return {get = function(self) return 7 end} end\n"
             + "out(make():get(), made)", "7,1"),
            ("method_declared_with_colon",
             "local obj = {v = 5}\nfunction obj:get(extra) return self.v + extra end\nout(obj:get(1))", "6"),
            ("field_named_like_a_string_method",
             "local box = {}\nbox.upper = function(self) return 'table wins' end\nout(box:upper())", "table wins"),
        ])

    def test_plain_name_receiver_keeps_its_direct_spelling(self):
        record = run_lua([("direct", "local obj = {}\nobj:run(1)")])["direct"]
        self.assertIn("obj.run(obj, 1);", record["hscript"])
        self.assertEqual(record["diagnostics"], "")


if __name__ == "__main__":
    unittest.main()
