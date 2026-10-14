"""Regression coverage for Psych's side-specific default receptor globals."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
OPPONENT_SCRIPT = DONOR / "psych/PERFEXION Demo1/data/Xfracture/FuckSake.lua"
PLAYER_SCRIPT = DONOR / "psych/PERFEXION Demo1/data/Resonance/Recolor2.lua"


class PsychDefaultStrumAliasTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PsychDefaultStrumCompat.hx"
            path.write_text(source, newline='\n')
            return subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp",
                    folder,
                    "-cp",
                    str(ROOT / "source"),
                    "-cp",
                    str(HSCRIPT),
                    "-main",
                    "PsychDefaultStrumCompat",
                    "--interp",
                ],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_synthetic_side_defaults_select_the_requested_receptor_pack(self):
        fixture = r'''
class PsychDefaultStrumCompat {
    static function main() {
        var opponentX = [10.0, 20.0];
        var opponentY = [30.0, 40.0];
        var playerX = [50.0, 60.0];
        var playerY = [70.0, 80.0];
        if (EngineCompat.luaGetSideDefaultStrum(opponentX, opponentY, playerX, playerY,
                "opponent", 1, "x") != 20) throw "opponent X route";
        if (EngineCompat.luaGetSideDefaultStrum(opponentX, opponentY, playerX, playerY,
                "dad", 0, "y") != 30) throw "dad Y route";
        if (EngineCompat.luaGetSideDefaultStrum(opponentX, opponentY, playerX, playerY,
                "player", 1, "x") != 60) throw "player X route";
        if (EngineCompat.luaGetSideDefaultStrum(opponentX, opponentY, playerX, playerY,
                "bf", 0, "y") != 70) throw "player Y route";
        if (EngineCompat.luaGetSideDefaultStrum(opponentX, opponentY, playerX, playerY,
                "player", 4, "x") != 0) throw "out-of-range route";
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_computed_opponent_global_is_whitelisted(self):
        fixture = r'''
class PsychDefaultStrumCompat {
    static function main() {
        var source = "function onCreate()\n"
            + "  local i = 0\n"
            + "  local x = _G['defaultOpponentStrumX' .. i]\n"
            + "end";
        var converted = LuaCompat.translate(source, "opponent-global.lua");
        if (!converted.supported)
            throw converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("luaGetScriptGlobal") < 0)
            throw "computed opponent global route";
        new hscript.Parser().parseString(converted.hscript);
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_script_owned_side_default_writes_shadow_later_reads(self):
        # Psych gives every Lua script its own copy of these globals: a script
        # that moves its baseline reads its own number back, comparisons are
        # not mistaken for writes, and the untouched slots keep the receptor.
        fixture = r"""
class PsychDefaultStrumCompat {
    static function main() {
        var source = "function onStepHit()\n"
            + "  if curStep >= 3 then\n"
            + "    defaultOpponentStrumX0 = -412\n"
            + "    defaultPlayerStrumY1 = defaultPlayerStrumY1 + 5;\n"
            + "  end\n"
            + "  if defaultOpponentStrumX0 == -412 then out('moved') end\n"
            + "  out(defaultOpponentStrumX0 + 1, defaultPlayerStrumY1, defaultOpponentStrumX1)\n"
            + "end";
        var converted = LuaCompat.translate(source, "own-strum.lua");
        if (!converted.supported)
            throw converted.diagnostics.join(" | ");
        var interp = new LuaCompatInterp();
        var globals:Map<String, Dynamic> = [];
        var own:Array<Dynamic> = [];
        var lines:Array<String> = [];
        interp.variables.set("out", Reflect.makeVarArgs(function(a:Array<Dynamic>) {
            lines.push(a.join(","));
            return null;
        }));
        interp.variables.set("luaSetScriptGlobal", function(name:Dynamic, value:Dynamic) {
            if (!EngineCompat.luaSetScriptGlobal(globals, name, value)) return false;
            var slot = EngineCompat.luaSideStrumSlot(Std.string(name));
            if (slot >= 0) own[slot] = value;
            return true;
        });
        interp.variables.set("luaGetSideDefaultStrum", function(side:Dynamic, index:Dynamic, axis:Dynamic)
            return EngineCompat.luaGetSideDefaultStrum([100.0, 110.0], [200.0, 210.0],
                [300.0, 310.0], [400.0, 410.0], side, index, axis, own));
        interp.variables.set("curStep", 0);
        interp.execute(new hscript.Parser().parseString(converted.hscript));
        var step:Dynamic = interp.variables.get("onStepHit");
        step();
        interp.variables.set("curStep", 4);
        step();
        var got = lines.join("|");
        if (got != "101,410,110|moved|-411,415,110")
            throw "own strum values: " + got;
        if (EngineCompat.luaSideStrumSlot("defaultPlayerStrumY3") != 15
            || EngineCompat.luaSideStrumSlot("defaultOpponentStrumX0") != 0
            || EngineCompat.luaSideStrumSlot("defaultStrum0X") != -1)
            throw "slot layout";
    }
}
"""
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_bare_side_globals_translate_to_the_native_adapter(self):
        self.assertTrue(OPPONENT_SCRIPT.is_file(), OPPONENT_SCRIPT)
        self.assertTrue(PLAYER_SCRIPT.is_file(), PLAYER_SCRIPT)
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("luaDefaultOpponentStrumX", play_state)
        self.assertIn("luaDefaultPlayerStrumX", play_state)
        self.assertIn("luaGetSideDefaultStrum", play_state)

        opponent = OPPONENT_SCRIPT.read_text(errors="ignore")
        self.assertEqual(opponent.count("defaultOpponentStrumX0"), 1)
        self.assertEqual(opponent.count("defaultOpponentStrumY0"), 1)
        player = PLAYER_SCRIPT.read_text(errors="ignore")
        for index in range(4):
            self.assertEqual(player.count(f"defaultPlayerStrumX{index}"), 1)

        paths = [
            str(OPPONENT_SCRIPT).replace("\\", "\\\\").replace('"', '\\"'),
            str(PLAYER_SCRIPT).replace("\\", "\\\\").replace('"', '\\"'),
        ]
        fixture = r'''
import hscript.Parser;
import sys.io.File;
class PsychDefaultStrumCompat {
    static function main() {
        var paths = ["{opponent}", "{player}"];
        for (path in paths) {
            var converted = LuaCompat.translate(File.getContent(path), path);
            if (!converted.supported)
                throw "mounted side-default script was diagnosed: " + converted.diagnostics.join(" | ");
            if (converted.hscript.indexOf("luaGetSideDefaultStrum") < 0)
                throw "side-default helper route was dropped: " + path;
            new Parser().parseString(converted.hscript);
        }
    }
}
'''.replace("{opponent}", paths[0]).replace("{player}", paths[1])
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
