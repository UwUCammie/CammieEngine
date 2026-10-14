"""Numeric strings in Lua arithmetic are read by a hand scanner, never a regex per call.

Every `x .. n` in a translated script passes its `"" + n` half through the
numeric string check, so the check runs thousands of times a second. A regex
literal there built a fresh native pattern on each call, and the pile of
finalizers made later garbage collections stall for many seconds mid-song.
"""
import re
import unittest

from lua_translate_support import ROOT, check_outputs, run_lua


class LuaNumericStringScanTest(unittest.TestCase):
    def test_numeric_strings_keep_their_lua_values(self):
        check_outputs(self, [
            ("hex", "local s = ' 0x1F '\nout(s + 1, '-0x10' + 0, '+0X0a' + 0)", "32,-16,10"),
            ("signed_and_partial_decimals",
             "out('+7' + 1, '-7' + 1, '.5' + 1, '5.' + 1, ' 3 ' * 2)", "8,-6,1.5,6,6"),
            ("exponents", "out('1e2' + 0, '2.5E-1' + 0, '1E+1' - 0)", "100,0.25,10"),
            ("long_integer_is_read_as_a_float", "out('12345678901' + 0)", "12345678901"),
            ("joining_numbers_still_joins", "local i, j = 3, 2.5\nout('tag' .. i .. j, '' .. i)", "tag32.5,3"),
        ])

    def test_text_that_only_looks_numeric_is_not_a_number(self):
        cases = [(name, "local v = %r\nout(v * 2)" % text) for name, text in [
            ("empty", ""), ("sign_only", "+"), ("dot_only", "."), ("hex_without_digits", "0x"),
            ("bad_hex_digit", "0x1g"), ("exponent_without_digits", "1e"), ("two_dots", "1.2.3"),
            ("inner_space", "1 2"), ("word", "lossScrollMoveX")]]
        records = run_lua(cases)
        for name, _ in cases:
            self.assertTrue(records[name]["status"].startswith("threw"), (name, records[name]["status"]))

    def test_the_check_builds_no_regex(self):
        source = (ROOT / "source" / "LuaCompatInterp.hx").read_text(encoding="utf-8")
        start = source.index("static function luaNumericString(")
        end = source.index("\n\t}\n", start)
        body = source[start:end]
        self.assertIsNone(re.search(r"~/|EReg", body), body)


if __name__ == "__main__":
    unittest.main()
