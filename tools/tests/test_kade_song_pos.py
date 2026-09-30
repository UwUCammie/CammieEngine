"""Regression coverage for the live Kade/FPS Plus ``songPos`` alias."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
KADE_MODCHART = (
    DONOR
    / "hellbeats_kade_engine/HellBeats Kade Engine/assets/data/tutorial/modchart.lua"
)


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class KadeSongPosTest(unittest.TestCase):
    def test_legacy_kade_clock_is_refreshed_for_every_script_scope(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(source, "function syncLegacyKadeGlobals")
        method = method.replace(
            "function syncLegacyKadeGlobals", "static function syncLegacyKadeGlobals", 1
        )
        fixture = """
class Conductor {{
  public static var songPosition:Float = 0;
  public static var bpm:Float = 120;
}}
class KadeClockCompat {{
  static var values:Map<String, Dynamic> = [];
  static function setAllHaxeVar(name:String, value:Dynamic):Void values.set(name, value);
{method}
  static function main() {{
    Conductor.songPosition = -625;
    syncLegacyKadeGlobals();
    if (values.get("songPos") != -625 || values.get("bpm") != 120)
      throw "initial Kade globals were not mirrored";
    Conductor.songPosition = 1480.5;
    Conductor.bpm = 175;
    syncLegacyKadeGlobals();
    if (values.get("songPos") != 1480.5 || values.get("bpm") != 175)
      throw "live Kade globals were not refreshed";
  }}
}}
""".format(method=method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "KadeClockCompat.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-main", "KadeClockCompat", "--interp"],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_kade_modchart_translates_with_the_live_clock_requirement(self):
        if not (KADE_MODCHART).exists():
            self.skipTest("mounted donor is unavailable")

        self.assertTrue(KADE_MODCHART.is_file())
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn('interp.variables.set("songPos", Conductor.songPosition);', source)
        self.assertGreaterEqual(source.count("syncLegacyKadeGlobals();"), 2)

        fixture = """
import sys.io.File;
import hscript.Parser;
class KadeCorpusCompat {{
  static function main() {{
    var path = "{path}";
    var result = LuaCompat.translate(File.getContent(path), path);
    if (!result.supported) throw result.diagnostics.join(" | ");
    if (result.hscript.indexOf("songPos") < 0) throw "Kade songPos reference was dropped";
    if (result.hscript.indexOf("luaGetDefaultStrum") < 0)
      throw "Kade defaultStrum dynamic-global route was dropped";
    new Parser().parseString(result.hscript);
  }}
}}
""".format(path=str(KADE_MODCHART).replace('\\', '\\\\').replace('"', '\\"'))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "KadeCorpusCompat.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [
                    str(HAXE),
                    "-cp",
                    folder,
                    "-cp",
                    str(ROOT / "source"),
                    "-cp",
                    str(HSCRIPT),
                    "-main",
                    "KadeCorpusCompat",
                    "--interp",
                ],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
