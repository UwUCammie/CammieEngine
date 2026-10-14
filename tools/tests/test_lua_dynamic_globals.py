"""`_G` reads and writes reach the script's own globals; library names in text are just text."""
import unittest

from lua_translate_support import check_outputs, run_lua


class LuaDynamicGlobalsTest(unittest.TestCase):
    def test_library_names_inside_strings_and_longer_names_do_not_drop_the_statement(self):
        check_outputs(self, [
            ("underscore_g_in_a_string",
             "local made = {}\nlocal function makeSprite(tag, path) made[#made + 1] = path end\n"
             + "makeSprite('endScreen', 'stage/BG_GameOver')\nout(#made, made[1])", "1,stage/BG_GameOver"),
            ("library_words_in_a_string",
             "local msg = 'please require(this) or loadstring it; coroutine.wrap setfenv'\nout(#msg > 0)", "true"),
            ("library_words_inside_identifiers",
             "local my_Gate = 1\nlocal requireCount = 2\nlocal loadstrings = 3\nout(my_Gate + requireCount + loadstrings)", "6"),
        ])

    def test_computed_and_dotted_global_keys_share_one_store_with_bare_names(self):
        check_outputs(self, [
            ("computed_key_round_trip",
             "local tag = 'bf'\n_G[tag .. 'GhostData.frameName'] = 'idle'\nout(_G[tag .. 'GhostData.frameName'])", "idle"),
            ("dotted_bracketed_and_bare_agree", "_G.myCounter = 3\nout(myCounter, _G.myCounter, _G['myCounter'])", "3,3,3"),
            ("bare_write_is_seen_through_the_table", "score = 12\nlocal key = 'score'\nout(_G[key], _G.missing)", "12,nil"),
            ("value_side_may_read_other_globals", "first = 4\n_G.second = _G.first + 1\nout(second)", "5"),
            ("engine_functions_cannot_be_replaced", "_G['out'] = 5\nout(type(out))", "function"),
        ])

    def test_default_strum_slots_stay_read_only(self):
        records = run_lua([
            ("literal_slot_write", "_G['defaultPlayerStrumX0'] = 1"),
            ("computed_slot_write", "local i = 0\n_G['defaultStrum' .. i .. 'X'] = 1"),
            ("whole_table", "local everything = _G"),
        ])
        for name in ("literal_slot_write", "computed_slot_write", "whole_table"):
            with self.subTest(name):
                self.assertFalse(records[name]["supported"])
                self.assertIn("lua-global-table", records[name]["diagnostics"])
                self.assertNotIn("luaGlobalSet", records[name]["hscript"])
                self.assertTrue(records[name]["parses"])


if __name__ == "__main__":
    unittest.main()
