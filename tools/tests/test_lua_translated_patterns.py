"""Translated Lua string calls reach the one Lua pattern engine with every result."""
from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"

FIXTURE = r'''
class LuaTranslatedPatterns {
 static function show(value:Dynamic):String return value == null ? 'nil' : Std.string(value);
 static function main() {
  var source = "function onCreate()\n"
   + " local speed, zoom, extra = string.match('1.5, 20', '([^,]+),%s*([^,]*),?%s*([^,]*)')\n"
   + " first = speed\n second = zoom\n third = extra\n"
   + " local s, e = string.find('ab cd', ' ', 0, true)\n"
   + " findStart = s\n findEnd = e\n"
   + " swapped = string.gsub('john smith', '(%w+) (%w+)', '%2 %1')\n"
   + " word = string.match('a_b', '%w+')\n"
   + " single = string.match('speed=2', '=(%d+)')\n"
   + " repeated = string.rep('ab', 3)\n"
   + " reversed = string.reverse('abc')\n"
   + "end\n";
  var translated = LuaCompat.translate(source, "patterns.lua");
  if (!translated.supported) throw translated.diagnostics.join(" | ");
  if (translated.hscript.indexOf("new EReg") >= 0) throw "translator still builds its own regular expression";
  var interp = new LuaCompatInterp();
  // The game seeds its single-result helpers after the scope exists, then
  // hands the scope its own result-list versions back.
  interp.variables.set("luaStringFind", EngineCompat.luaStringFind);
  interp.variables.set("luaStringMatch", EngineCompat.luaStringMatch);
  interp.variables.set("luaStringGsub", EngineCompat.luaStringGsub);
  interp.variables.set("luaStringRep", EngineCompat.luaStringRep);
  interp.variables.set("luaStringReverse", EngineCompat.luaStringReverse);
  LuaStdlib.installScopedStringHelpers(interp);
  interp.execute(new hscript.Parser().parseString(translated.hscript));
  Reflect.callMethod(null, interp.variables.get("onCreate"), []);
  var got = [for (name in ["first", "second", "third", "findStart", "findEnd", "swapped", "word", "single", "repeated", "reversed"])
   name + '=' + show(interp.variables.get(name))].join(' ');
  var want = "first=1.5 second=20 third= findStart=3 findEnd=3 swapped=smith john word=a single=2 repeated=ababab reversed=cba";
  if (got != want) throw 'got ' + got + '\nwant ' + want;
  Sys.println("ok");
 }
}
'''


class LuaTranslatedPatternsTest(unittest.TestCase):
    def test_translated_string_calls_return_every_lua_result(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "LuaTranslatedPatterns.hx").write_text(FIXTURE, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HAXESCRIPT),
                 "-main", "LuaTranslatedPatterns", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_translator_keeps_no_pattern_subset_and_game_restores_scoped_helpers(self):
        lua = (ROOT / "source/LuaCompat.hx").read_text(encoding="utf-8")
        for name in ("parseLuaStringMatch", "luaCapturePattern", "routeLiteralGsub", "supportedGsubPattern"):
            self.assertNotIn(name, lua)
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        table = play.index("(cast interp : LuaCompatInterp).installTableHelpers();")
        self.assertLess(play.index("interp.variables.set('luaStringFind', EngineCompat.luaStringFind);"), table)
        self.assertIn("LuaStdlib.installScopedStringHelpers(cast interp);", play[table:table + 400])


if __name__ == "__main__":
    unittest.main()
