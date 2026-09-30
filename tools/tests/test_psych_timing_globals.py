"""Regression coverage for Psych's live ``curBpm``/``stepCrochet`` globals."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
TIMING_SCRIPTS = (
    DONOR / "psych/PERFEXION Demo1/custom_events/Kaboom.lua",
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/10scriptnote.lua",
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/Used later/scriptnote.lua",
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/noteMoveOnPress.lua",
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/Used later/noteMoveOnPress.lua",
)


def strip_lua_comments(source: str) -> str:
    source = re.sub(r"--\[\[.*?\]\]", "", source, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", source)


class PsychTimingGlobalsTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PsychTimingCompat.hx"
            path.write_text(source)
            return subprocess.run(
                [
                    str(HAXE),
                    "-cp",
                    folder,
                    "-cp",
                    str(ROOT / "source"),
                    "-cp",
                    str(HSCRIPT),
                    "-main",
                    "PsychTimingCompat",
                    "--interp",
                ],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_synthetic_timing_globals_follow_conductor(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        marker = "function syncPsychTimingGlobals"
        start = source.index(marker)
        brace = source.index("{", start)
        depth = 0
        for index in range(brace, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    method = source[start : index + 1]
                    break
        else:
            self.fail("unterminated syncPsychTimingGlobals method")
        method = method.replace(
            "function syncPsychTimingGlobals", "static function syncPsychTimingGlobals", 1
        )
        fixture = """
class Conductor {
    public static var bpm:Float = 120;
    public static var crochet:Float = 500;
    public static var stepCrochet:Float = 125;
}
class PsychTimingCompat {
    static var values:Map<String, Dynamic> = [];
    static function setAllHaxeVar(name:String, value:Dynamic):Void values.set(name, value);
{method}
    static function main() {
        syncPsychTimingGlobals();
        if (values.get("curBpm") != 120 || values.get("bpm") != 120
            || values.get("crochet") != 500
            || values.get("stepCrochet") != 125)
            throw "initial Psych timing globals were not mirrored";
        Conductor.bpm = 175;
        Conductor.crochet = 342.857142857;
        Conductor.stepCrochet = 85.714285714;
        syncPsychTimingGlobals();
        if (values.get("curBpm") != 175 || values.get("bpm") != 175
            || values.get("crochet") != 342.857142857
            || values.get("stepCrochet") != 85.714285714)
            throw "BPM-change timing globals were not refreshed";
    }
}
""".replace("{method}", method)
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_psych_timing_scripts_translate_and_have_live_seed(self):
        for path in TIMING_SCRIPTS:
            self.assertTrue(path.is_file(), path)
        self.assertEqual(
            sum(
                len(re.findall(r"\bstepCrochet\b", strip_lua_comments(path.read_text(errors="ignore"))))
                for path in TIMING_SCRIPTS[:3]
            ),
            6,
        )
        self.assertEqual(
            sum(
                len(re.findall(r"\bcurBpm\b", strip_lua_comments(path.read_text(errors="ignore"))))
                for path in TIMING_SCRIPTS[3:]
            ),
            4,
        )
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertGreaterEqual(play_state.count('interp.variables.set("curBpm", Conductor.bpm);'), 2)
        self.assertGreaterEqual(play_state.count('interp.variables.set("stepCrochet", Conductor.stepCrochet);'), 2)
        self.assertGreaterEqual(play_state.count("syncPsychTimingGlobals();"), 3)

        paths = [str(path).replace("\\", "\\\\").replace('"', '\\"') for path in TIMING_SCRIPTS]
        fixture = r'''
import hscript.Parser;
import sys.io.File;
class PsychTimingCompat {
    static function main() {
        var paths = ["{p0}", "{p1}", "{p2}", "{p3}", "{p4}"];
        for (path in paths) {
            var converted = LuaCompat.translate(File.getContent(path), path);
            if (!converted.supported)
                throw "mounted Psych timing script was diagnosed: " + converted.diagnostics.join(" | ");
            new Parser().parseString(converted.hscript);
        }
    }
}
'''.replace("{p0}", paths[0]).replace("{p1}", paths[1]).replace("{p2}", paths[2]) \
            .replace("{p3}", paths[3]).replace("{p4}", paths[4])
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
