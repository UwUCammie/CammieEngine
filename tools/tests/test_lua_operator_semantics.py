"""Power, modulo, concatenation and numeric strings behave as Lua defines them."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
from lua_translate_support import HSCRIPT, ROOT, check_outputs, run_lua


class LuaOperatorSemanticsTest(unittest.TestCase):
    def test_operators(self):
        check_outputs(self, [
            ("overview", "out(2 ^ 10, -1 % 5, 1 .. 2, 'n' .. 1 + 1, '10' + 5)", "1024,4,12,n2,15"),
            ("power_precedence", "out(2 * 3 ^ 2, 2 ^ 3 ^ 2, -2 ^ 2, 2 ^ -1, (1 + 1) ^ 2)", "18,512,-4,0.5,4"),
            ("power_in_digit_extraction",
             "local combo = 345\nlocal d = {}\nfor i = 0, 2 do d[#d + 1] = math.floor(combo / (10 ^ i)) % 10 end\nout(d[1], d[2], d[3])",
             "5,4,3"),
            ("modulo_follows_the_divisor", "local sel, n = 0, 4\nout((sel - 1) % n, 7 % -3, -7 % 3, 5.5 % 2, 6 % 3)", "3,-2,2,1.5,0"),
            ("fmod_follows_the_dividend", "out(math.fmod(-7, 3), math.fmod(7, 3), math.fmod(5.5, 2))", "-1,1,1.5"),
            ("concat_binds_looser_than_arithmetic", "local i = 3\nout('a' .. i * 2 .. 'b', 'n' .. i - 1, 'a' .. 1 + 2)", "a6b,n2,a3"),
            ("concat_never_adds", "local a, b = 1, 2\nlocal zero, seconds = '0', 5\nout(a .. b, zero .. seconds, '10' .. '5')", "12,05,105"),
            ("concat_inside_comparison", "out('a' .. 'b' == 'ab' and 'ab' == 'a' .. 'b')", "true"),
            ("numeric_strings_in_arithmetic",
             "local value1, value2 = '2', '0.5'\nout(value1 + 1, value1 * value2, value1 - 1, value1 / 4, -value1, value1 % 2)",
             "3,1,1,0.5,-2,0"),
            ("text_joined_with_text", "local a, b = 'x', 'y'\nout(a .. b)", "xy"),
        ])

    def test_non_numeric_string_arithmetic_still_fails_loudly(self):
        record = run_lua([("bad", "local v = 'abc'\nout(v * 2)")])["bad"]
        self.assertTrue(record["status"].startswith("threw"), record["status"])

    def test_concatenation_needs_no_helper_so_it_also_runs_in_an_ordinary_interpreter(self):
        record = run_lua([("spelling", "local tag = 'a' .. i + 1 .. name")])["spelling"]
        self.assertIn("""var tag = 'a' + ("" + (i + 1)) + ("" + name);""", record["hscript"])

    def test_native_scripts_keep_haxe_operators(self):
        fixture = r'''
class Fixture {
 static function main() {
  var native = new hscript.Interp();
  var run = function(code:String):Dynamic return native.execute(new hscript.Parser().parseString(code));
  if (run('-1 % 5;') != -1) throw 'native modulo changed';
  if (run('"10" + 5;') != "105") throw 'native string plus number changed';
  if (run('6 ^ 3;') != 5) throw 'native xor changed';
  if (run('var i = 2; var name = "z"; "a" + ("" + (i + 1)) + ("" + name);') != "a3z") throw 'translated concatenation spelling';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Fixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-main", "Fixture", "--interp"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
