"""Translated callbacks inside a script that keeps an ordinary interpreter still find their helpers."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
from lua_translate_support import HSCRIPT, ROOT


class LuaPlainInterpHelpersTest(unittest.TestCase):
    def test_ordinary_interpreter_runs_translated_callbacks_after_seeding(self):
        fixture = r'''
class Fixture {
 static function main() {
  var lua = "function describe(name, count)\n"
   + " local label = name .. ' x' .. count + 1\n"
   + " local a, b = 1, 2\n a, b = b, a\n"
   + " local first, second = pair()\n"
   + " _G.shared = label\n"
   + " return (label .. '!'):upper() .. a .. b .. first .. tostring(second) .. _G.shared\n"
   + "end\n"
   + "function pair() return 'p', 'q' end\n";
  var translated = LuaCompat.translate(lua, 'callbacks.lua');
  if (!translated.supported) throw translated.diagnostics.join(' | ');
  var plain = new hscript.Interp();
  plain.variables.set('luaString', function(value:Dynamic):String return value == null ? 'nil' : Std.string(value));
  LuaCompatInterp.seedPlainHelpers(plain);
  plain.execute(new hscript.Parser().parseString(translated.hscript));
  var result:String = Reflect.callMethod(null, plain.variables.get('describe'), ['tag', 2]);
  // No result lists outside a Lua scope: a call has one result there.
  if (result != 'TAG X3!21pniltag x3') throw 'plain interpreter result: ' + result;
  if (plain.variables.get('shared') != 'tag x3') throw 'script global was not stored';
  // Seeding never replaces a binding the interpreter already has.
  var kept = new hscript.Interp();
  kept.variables.set('luaValues', 'mine');
  LuaCompatInterp.seedPlainHelpers(kept);
  if (kept.variables.get('luaValues') != 'mine') throw 'existing binding was replaced';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Fixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-main", "Fixture", "--interp"], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
