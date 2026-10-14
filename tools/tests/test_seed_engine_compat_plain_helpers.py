"""Every interpreter the gameplay host seeds gets the translated-callback helpers first."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
from lua_translate_support import HSCRIPT, ROOT


def method_body(source: str, marker: str) -> str:
    start = source.index(marker)
    depth = 0
    for index in range(source.index("{", start), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class SeedEngineCompatPlainHelpersTest(unittest.TestCase):
    def test_seed_runs_plain_helpers_before_any_other_binding(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        seed = method_body(play, "function seedEngineCompat(interp:Interp")
        first_statement = re.search(r"^\t\t(?!//)(\S.*)$", seed, re.M).group(1)
        self.assertEqual(first_statement, "LuaCompatInterp.seedPlainHelpers(interp);")
        # A Lua scope gets its result-list helpers back after the shared bindings.
        self.assertLess(seed.index("LuaCompatInterp.seedPlainHelpers(interp);"),
                        seed.index("(cast interp : LuaCompatInterp).installTableHelpers();"))

    def test_mixed_native_script_runs_translated_callback_and_lua_scope_keeps_its_helpers(self):
        fixture = r'''
class Fixture {
 static function main() {
  var lua = "function onBeatHit()\n"
   + " local a, b = 1, 2\n a, b = b, a\n"
   + " _G.beatLabel = ('beat ' .. a .. b):upper()\n"
   + "end\n";
  var translated = LuaCompat.translate(lua, 'stage.lua');
  if (!translated.supported) throw translated.diagnostics.join(' | ');
  // A native stage script: ordinary interpreter, its own code beside the translated callback.
  var stage = new hscript.Interp();
  stage.variables.set('luaString', function(value:Dynamic):String return value == null ? 'nil' : Std.string(value));
  LuaCompatInterp.seedPlainHelpers(stage);
  var parser = new hscript.Parser();
  stage.execute(parser.parseString('nativeReady = true;\n' + translated.hscript));
  Reflect.callMethod(null, stage.variables.get('onBeatHit'), []);
  if (stage.variables.get('beatLabel') != 'BEAT 21') throw 'mixed stage callback: ' + stage.variables.get('beatLabel');
  if (stage.variables.get('nativeReady') != true) throw 'native code beside the callback did not run';

  // The same seed on a Lua scope keeps the scope's result-list helpers.
  var luaScope = new LuaCompatInterp();
  var before:Dynamic = luaScope.variables.get('luaValues');
  var beforeCall:Dynamic = luaScope.variables.get('luaMethodCall');
  LuaCompatInterp.seedPlainHelpers(luaScope);
  if (luaScope.variables.get('luaValues') != before || luaScope.variables.get('luaMethodCall') != beforeCall)
   throw 'plain helpers replaced the Lua scope helpers';
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
