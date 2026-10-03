"""Regression coverage for imported, donor-defined difficulty suffixes."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


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


class DiscoveredDifficultyTest(unittest.TestCase):
    def test_registry_seed_is_valid_json(self):
        registry = ROOT / "assets/images/custom_difficulties/difficulties.json"
        parsed = json.loads(registry.read_text(encoding="utf-8"))
        self.assertEqual(parsed["difficulties"][1]["name"], "normal")

    def test_unknown_chart_suffix_is_discovered_without_renaming(self):
        source = (ROOT / "source/DifficultyManager.hx").read_text(encoding="utf-8")
        start = source.index("\tpublic static function difficultySuffixFromChartFile(")
        end = source.index("\n\t#if sys", start)
        method = source[start:end]
        fixture = """using StringTools;
import haxe.io.Path;
class DifficultySuffixTest {
""" + method + """
\tstatic function check(actual:String, expected:String):Void {
\t\tif (actual != expected) throw 'expected ' + expected + ', got ' + actual;
\t}
\tstatic function main():Void {
\t\tcheck(difficultySuffixFromChartFile('cycles-encore-springless',
\t\t\t'cycles-encore-springless-encore.json'), 'encore');
\t\tcheck(difficultySuffixFromChartFile('song', 'song-hard.json'), 'hard');
\t\tcheck(difficultySuffixFromChartFile('song', 'song.json'), '');
\t\tif (difficultySuffixFromChartFile('song', 'events.json') != null)
\t\t\tthrow 'events sidecar became a difficulty';
\t\tif (difficultySuffixFromChartFile('song', 'other-encore.json') != null)
\t\t\tthrow 'unrelated chart became a difficulty';
\t}
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "DifficultySuffixTest.hx"
            path.write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp",
                    folder,
                    "-main",
                    "DifficultySuffixTest",
                    "--interp",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_discovers_suffixes_before_support_maps(self):
        source = (ROOT / "source/DifficultyManager.hx").read_text(encoding="utf-8")
        add_support = extract_method(source, "public static function addSongSupport(")
        discover = add_support.index("discoverSongDifficulties(key);")
        support = add_support.index("supportedDiff.set(key, []);")
        self.assertLess(discover, support)
        self.assertIn("ensureDifficultyDefinition(suffix);", source)

    def test_nmv_source_menu_metadata_hides_unselectable_but_retains_chart_files(self):
        source = (ROOT / "source/DifficultyManager.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "public static function difficultySuffixFromChartFile(",
                "static function readSourceSelectableDifficulties(",
                "static function readSourceUnsupportedDifficulties(",
                "static function discoverSongDifficulties(",
                "static function ensureDifficultyDefinition(",
                "public static function addSongSupport(",
                "public static function getDiffEnding(",
            )
        )
        fixture = '''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class FNFAssets {
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}
class CoolUtil { public static function parseJson(raw:String):Dynamic return Json.parse(raw); }
class DifficultyFilterTest {
  static var diffJson:Dynamic;
  static var supportedDiff:Map<String,Array<Int>> = new Map();
''' + methods + '''
  static function chart(folder:String, name:String):Void
    File.saveContent("assets/data/" + folder + "/" + name + ".json", "{}");
  static function fail(message:String):Void throw message;
  static function main():Void {
    for (folder in ["alpha", "beta", "gamma"]) FileSystem.createDirectory("assets/data/" + folder);
    File.saveContent("assets/data/alpha/importProvenance.json", Json.stringify({
      sourceEngine:"Nightmare Vision", sourceSelectableDifficulties:["easy", "normal", "hard"],
      sourceUnsupportedDifficulties:["hard"]
    }));
    File.saveContent("assets/data/beta/importProvenance.json", Json.stringify({
      sourceEngine:"Nightmare Vision", sourceSelectableDifficulties:["normal", "mania"]
    }));
    chart("alpha", "alpha-easy"); chart("alpha", "alpha");
    chart("alpha", "alpha-hard"); chart("alpha", "alpha-crowd");
    chart("beta", "beta"); chart("beta", "beta-mania");
    diffJson = {defaultDiff:1, difficulties:[
      {name:"easy"}, {name:"normal"}, {name:"hard"}
    ]};
    discoverSongDifficulties("alpha");
    if (diffJson.difficulties.length != 3)
      fail("unlisted alpha chart created a global difficulty definition");
    discoverSongDifficulties("beta");
    if (diffJson.difficulties.length != 4 || diffJson.difficulties[3].name != "mania")
      fail("beta owner menu declaration was not used");
    addSongSupport("alpha"); addSongSupport("beta");
    if (supportedDiff.get("alpha").indexOf(3) >= 0)
      fail("unselectable crowd chart appeared in Freeplay support");
    if (supportedDiff.get("alpha").indexOf(2) >= 0)
      fail("source-declared but schema-unsupported chart appeared in Freeplay support");
    if (supportedDiff.get("beta").indexOf(3) < 0)
      fail("owner-declared mania chart was hidden");
    if (!FileSystem.exists("assets/data/alpha/alpha-crowd.json"))
      fail("source chart was removed instead of retained");
    // This song appears after the startup registry scan. The import callback
    // must add its new suffix before Freeplay asks for supported difficulties.
    chart("gamma", "gamma-buck");
    addSongSupport("gamma");
    if (diffJson.difficulties.length != 5 || diffJson.difficulties[4].name != "buck")
      fail("late import did not define its authored difficulty");
    if (supportedDiff.get("gamma").length != 1 || supportedDiff.get("gamma")[0] != 4)
      fail("late import could not select its only chart difficulty");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder)
            (path / "DifficultyFilterTest.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "DifficultyFilterTest", "--interp"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_late_import_support_lookup_is_null_safe_and_lazy(self):
        manager = (ROOT / "source/DifficultyManager.hx").read_text(encoding="utf-8")
        freeplay = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        self.assertIn("public static function getSupportedDiffs(song:String):Array<Int>", manager)
        self.assertIn("addSongSupport(key);", manager)
        self.assertIn("return supported == null ? [] : supported;", manager)
        self.assertIn("var supported = getSupportedDiffs(song);", manager)
        self.assertIn("var daThing = getSupportedDiffs(song);", manager)
        self.assertNotIn("supportedDiff.get(song.toLowerCase()).contains", manager)
        self.assertIn("DifficultyManager.getSupportedDiffs(songs[curSelected].songName)", freeplay)
        self.assertIn("DifficultyManager.getSupportedDiffs(songs[i].songName)", freeplay)

    def test_missing_or_empty_support_list_is_runtime_safe(self):
        """Exercise the production lookup/change path in the Haxe interpreter.

        The native crash occurred when Freeplay called changeDifficultySans for
        a song that was present in the registry but absent from supportedDiff.
        Static source checks would not catch a future null dereference, so this
        fixture extracts the actual helper methods and invokes both the missing
        key and explicitly empty-list cases.
        """
        source = (ROOT / "source/DifficultyManager.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "public static function difficultySuffixFromChartFile(",
                "public static function addSongSupport(",
                "static function readSourceSelectableDifficulties(",
                "static function readSourceUnsupportedDifficulties(",
                "static function discoverSongDifficulties(",
                "static function ensureDifficultyDefinition(",
                "public static function getSupportedDiffs(",
                "public static function getDiffEnding(",
                "public static function changeDifficulty(",
                "public static function changeDifficultySans(",
            )
        )
        fixture = """using StringTools;
import haxe.io.Path;
import sys.FileSystem;

typedef DiffInfo = { var difficulty:Int; var text:String; };

class FNFAssets {
  public static function exists(path:String):Bool return false;
  public static function getText(path:String):String return "";
}
class CoolUtil { public static function parseJson(raw:String):Dynamic return null; }

class FlxMath {
  public static function wrap(value:Int, min:Int, max:Int):Int {
    var range = max - min + 1;
    var wrapped = (value - min) % range;
    if (wrapped < 0) wrapped += range;
    return wrapped + min;
  }
}

class MissingDifficultyRuntimeTest {
  static var diffJson:Dynamic;
  static var supportedDiff:Map<String,Array<Int>> = new Map();
""" + methods + """
  static function fail(message:String):Void throw message;

  static function main():Void {
    diffJson = {
      defaultDiff: 0,
      difficulties: [
        {name:'easy'}, {name:'normal'}, {name:'hard'}
      ]
    };

    // This is the coredump shape: Freeplay has a song, but the startup scan
    // did not create a supportedDiff entry for it yet.
    var missing = changeDifficultySans(1, 0, 'late-imported-song');
    if (missing == null || missing.difficulty != 1 || missing.text != 'NORMAL')
      fail('missing song did not return the current difficulty safely');
    if (supportedDiff.get('late-imported-song') == null)
      fail('missing-song lookup did not lazily seed an empty support list');

    // An entry may exist but still have no discovered chart files.  It must
    // take the same safe fallback path instead of calling contains on null.
    supportedDiff.set('empty-chart', []);
    var empty = changeDifficultySans(2, 1, 'empty-chart');
    if (empty == null || empty.difficulty != 0 || empty.text != 'EASY')
      fail('empty support list did not return the wrapped fallback');

    // Preserve normal behavior for a genuinely supported song as a control.
    supportedDiff.set('charted-song', [0, 2]);
    var charted = changeDifficultySans(0, 1, 'charted-song');
    if (charted == null || charted.difficulty != 2 || charted.text != 'HARD')
      fail('supported song difficulty selection regressed');
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "MissingDifficultyRuntimeTest.hx"
            path.write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp",
                    str(ROOT / "source"),
                    "-cp",
                    folder,
                    "-main",
                    "MissingDifficultyRuntimeTest",
                    "--interp",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pause_difficulty_menu_uses_null_safe_support_lookup(self):
        pause = (ROOT / "source/PauseSubState.hx").read_text(encoding="utf-8")
        self.assertIn(
            "diffs = DifficultyManager.getSupportedDiffs(PlayState.SONG.song);",
            pause,
        )
        self.assertNotIn(
            "diffs = DifficultyManager.supportedDiff.get(PlayState.SONG.song.toLowerCase());",
            pause,
        )


if __name__ == "__main__":
    unittest.main()
