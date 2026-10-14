"""One statement that cannot be translated must not switch the whole script off."""
import unittest

from lua_translate_support import run_lua


class LuaPartialDisableTest(unittest.TestCase):
    def test_only_the_function_at_fault_is_stubbed(self):
        lua = ("made = 0\nfunction onCreate()\n made = made + 1\nend\n"
               + "function helper(s)\n return s @ 2\nend\n"
               + "onCreate()\nout(made, helper('x'))\n")
        record = run_lua([("partial", lua)])["partial"]
        self.assertFalse(record["supported"])
        self.assertIn("lua-generated-syntax", record["diagnostics"])
        self.assertIn("function helper", record["diagnostics"])
        self.assertIn("Lua line 5", record["diagnostics"])
        self.assertTrue(record["parses"])
        self.assertIn("made = made + 1;", record["hscript"])
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["out"], "1,nil")

    def test_a_bad_top_level_statement_is_commented_out_alone(self):
        record = run_lua([("statement", "local a = 1\nlocal b = a @ 2\nout(a)\n")])["statement"]
        self.assertIn("Disabled a statement at Lua line 2", record["diagnostics"])
        self.assertEqual(record["out"], "1")

    def test_local_and_table_functions_get_matching_stubs(self):
        lua = ("local box = {}\nlocal function broken(a)\n return a @ 1\nend\n"
               + "function box.alsoBroken()\n return 1 @ 1\nend\nout(broken(1), box.alsoBroken())\n")
        record = run_lua([("stubs", lua)])["stubs"]
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["out"], "nil,nil")


if __name__ == "__main__":
    unittest.main()
