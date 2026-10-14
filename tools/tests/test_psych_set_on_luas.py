"""Psych HScript calls game.setOnLuas after swapping a character by hand, so
the Lua scripts see the new dadName. PlayState has to offer that method and
write only to Lua scopes.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_hit_order import extract_method

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r"""
class Interp {
 public var variables:Map<String, Dynamic> = [];
 public function new() {}
}
class LuaCompatInterp extends Interp {}
class PlayState {
 public var hscriptStates:Map<String, Interp> = [];
 public function new() {}
 __METHOD__
}
class Main {
 static function check(b:Bool, s:String) if (!b) throw s;
 static function main() {
  var game = new PlayState();
  var luaA = new LuaCompatInterp(), luaB = new LuaCompatInterp(), haxe = new Interp();
  game.hscriptStates.set('scripts/a.lua', luaA);
  game.hscriptStates.set('scripts/b.lua', luaB);
  game.hscriptStates.set('scripts/c.hx', haxe);
  // Scripts reach it by name through the game object, as runHaxeCode does.
  Reflect.callMethod(game, Reflect.field(game, 'setOnLuas'), ['dadName', 'Glitchy-Red-Mad']);
  check(luaA.variables.get('dadName') == 'Glitchy-Red-Mad' && luaB.variables.get('dadName') == 'Glitchy-Red-Mad', 'Lua scopes missed the value');
  check(!haxe.variables.exists('dadName'), 'an HScript scope got a Lua-only value');
  game.setOnLuas('boyfriendName', 'bf-alt', ['scripts/b.lua']);
  check(luaA.variables.get('boyfriendName') == 'bf-alt' && !luaB.variables.exists('boyfriendName'), 'exclusions were not honoured');
  Sys.println('OK');
 }
}
"""


class PsychSetOnLuasTest(unittest.TestCase):
    def test_set_on_luas_writes_only_lua_scopes(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8").replace("\r\n", "\n")
        method = extract_method(play, "@:keep public function setOnLuas(")
        fixture = FIXTURE.replace("__METHOD__", method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = FixturePath(folder)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
