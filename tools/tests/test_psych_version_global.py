"""Regression coverage for Psych's legacy ``version`` compatibility global."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
VERSION_SCRIPTS = (
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/20changeNote.lua",
    DONOR / "psych/PERFEXION Demo1/data/Xfracture/Used later/changeNote.lua",
)


class PsychVersionGlobalTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PsychVersionCompat.hx"
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
                    "PsychVersionCompat",
                    "--interp",
                ],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_synthetic_psych_generation_is_modern_and_orderable(self):
        fixture = r'''
class PsychVersionCompat {
    static function main() {
        var version = EngineCompat.psychCompatibilityVersion();
        if (version != "0.7.0") throw "unexpected Psych compatibility generation: " + version;
        if (!(version >= "0.7") || !(version > "0.6.3") || version < "0.7")
            throw "Psych version checks do not select the modern API route";
        var components = version.split('.');
        if (components.length != 3 || Std.parseInt(components.join('')) < 51)
            throw "legacy dotted-release comparisons lost the compatibility generation";
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_release_gate_accepts_current_generation_and_rejects_older_one(self):
        fixture = r''' 
class PsychVersionCompat {
    static function main() {
        var source = "curver = 0\nfunction onCreate()\n"
            + "curver = tonumber(string.gsub(version, '%.' , ''))\nend\n"
            + "function onStartCountdown()\nif curver < 51 then\n"
            + "return Function_Stop\nend\nreturn Function_Continue\nend";
        var translated = LuaCompat.translate(source, "release-gate.lua");
        if (!translated.supported) throw translated.diagnostics.join(" | ");
        for (version in ["0.5.0", EngineCompat.psychCompatibilityVersion()]) {
            var interp = new LuaCompatInterp();
            interp.variables.set("version", version);
            interp.variables.set("luaStringGsub", EngineCompat.luaStringGsub);
            interp.variables.set("luaNumber", EngineCompat.luaNumber);
            interp.variables.set("Function_Stop", true);
            interp.variables.set("Function_Continue", false);
            interp.execute(new hscript.Parser().parseString(translated.hscript));
            Reflect.callMethod(null, interp.variables.get("onCreate"), []);
            var result = Reflect.callMethod(null, interp.variables.get("onStartCountdown"), []);
            if (EngineCompat.functionStop(result) != (version == "0.5.0"))
                throw "release gate did not honor version " + version;
        }
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_version_scripts_translate_and_playstate_seeds_global(self):
        for path in VERSION_SCRIPTS:
            self.assertTrue(path.is_file(), path)
        self.assertEqual(
            sum(path.read_text(errors="ignore").count("version") for path in VERSION_SCRIPTS),
            8,
        )
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn(
            'interp.variables.set("version", EngineCompat.psychCompatibilityVersion());',
            play_state,
        )

        paths = [str(path).replace("\\", "\\\\").replace('"', '\\"') for path in VERSION_SCRIPTS]
        fixture = r'''
import hscript.Parser;
import sys.io.File;
class PsychVersionCompat {
    static function main() {
        var paths = ["{first}", "{second}"];
        for (path in paths) {
            var converted = LuaCompat.translate(File.getContent(path), path);
            if (!converted.supported)
                throw "mounted Psych version script was diagnosed: " + converted.diagnostics.join(" | ");
            if (converted.hscript.indexOf("version") < 0)
                throw "version branch was dropped from " + path;
            new Parser().parseString(converted.hscript);
        }
    }
}
'''.replace("{first}", paths[0]).replace("{second}", paths[1])
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
