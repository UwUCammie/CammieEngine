"""Regression coverage for Psych's static judgement-counter properties."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
COUNTER_SCRIPTS = (
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/noteMoveOnPress.lua",
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/Used later/noteMoveOnPress.lua",
)


def strip_lua_comments(source: str) -> str:
    source = re.sub(r"--\[\[.*?\]\]", "", source, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", source)


class PsychJudgementCountersTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PsychCounterCompat.hx"
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
                    "PsychCounterCompat",
                    "--interp",
                ],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_synthetic_counter_aliases_are_canonical(self):
        fixture = r'''
class PsychCounterCompat {
    static function main() {
        var expected = ["misses", "shits", "bads", "goods", "sicks"];
        for (name in expected) {
            if (EngineCompat.legacyCounterName(name.toUpperCase()) != name)
                throw "counter alias did not normalize: " + name;
        }
        if (EngineCompat.legacyCounterName("songScore") != "")
            throw "unrelated property was treated as a judgement counter";
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_note_move_scripts_translate_and_use_static_counters(self):
        for path in COUNTER_SCRIPTS:
            self.assertTrue(path.is_file(), path)
            source = strip_lua_comments(path.read_text(errors="ignore"))
            self.assertEqual(source.count('getProperty("sicks")'), 1, path)
            self.assertEqual(source.count('getProperty("goods")'), 1, path)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertGreaterEqual(play_state.count("EngineCompat.legacyCounterName(root)"), 2)
        for name in ["misses", "shits", "bads", "goods", "sicks"]:
            self.assertIn("case '%s': return PlayState.%s;" % (name, name), play_state)
            self.assertIn("case '%s': PlayState.%s = counterValue;" % (name, name), play_state)

        paths = [str(path).replace("\\", "\\\\").replace('"', '\\"') for path in COUNTER_SCRIPTS]
        fixture = r'''
import hscript.Parser;
import sys.io.File;
class PsychCounterCompat {
    static function main() {
        var paths = ["{first}", "{second}"];
        for (path in paths) {
            var converted = LuaCompat.translate(File.getContent(path), path);
            if (!converted.supported)
                throw "mounted judgement script was diagnosed: " + converted.diagnostics.join(" | ");
            if (converted.hscript.indexOf("sicks") < 0 || converted.hscript.indexOf("goods") < 0)
                throw "judgement counter references were dropped: " + path;
            new Parser().parseString(converted.hscript);
        }
    }
}
'''.replace("{first}", paths[0]).replace("{second}", paths[1])
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
