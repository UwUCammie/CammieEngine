"""string.format rounds like C, refuses unknown options, and tonumber/tostring know inf and nan."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaFormatRoundingTest(unittest.TestCase):
    def test_format_and_special_numbers(self):
        check_outputs(self, [
            ("exact_halves_go_to_the_even_digit",
             "out(string.format('%.1f|%.0f|%.0f|%.0f|%05.1f|%.2f', 1.25, 0.5, 1.5, 2.5, 2.25, 0.125))",
             "1.2|0|2|2|002.2|0.12"),
            # These print the binary value's real digits: 2.675 is stored as 2.67499...
            ("near_halves_follow_the_stored_value",
             "out(string.format('%.2f|%.2f|%.1f|%.1f|%.3g', 2.675, 1.005, 0.35, 0.05, 2.675))",
             "2.67|1.00|0.3|0.1|2.67"),
            ("ordinary_rounding_is_unchanged",
             "out(string.format('%.2f|%.1f|%d|%.3f', 3.14159, 2.96, 42, 1 / 3))",
             "3.14|3.0|42|0.333"),
            ("percent_sign_still_prints",
             "out(string.format('%d%%', 50))", "50%"),
            ("tonumber_reads_inf_and_nan",
             "local nan = tonumber('nan')\nout(tostring(tonumber('inf')), tostring(tonumber(' -Infinity ')), nan ~= nan, tonumber('info'))",
             "inf,-inf,true,nil"),
            ("tostring_of_infinities",
             "out(tostring(math.huge), tostring(-math.huge))", "inf,-inf"),
        ])

    def test_unknown_format_option_is_an_error_like_lua(self):
        record = run_lua([("bad", "out(string.format('%5%'))")])["bad"]
        self.assertTrue(record["status"].startswith("threw"), record["status"])
        self.assertIn("invalid option", record["status"])
        caught = run_lua([("caught", "out(pcall(string.format, '%y', 1))")])["caught"]
        self.assertEqual(caught["status"], "ok", caught["hscript"])
        self.assertTrue(caught["out"].startswith("false"), caught["out"])


if __name__ == "__main__":
    unittest.main()
