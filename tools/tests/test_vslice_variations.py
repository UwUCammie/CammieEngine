"""V-Slice sibling variations resolve as independent chart/audio/vocal plans."""

from __future__ import annotations
from haxe_test_support import HAXE_COMMAND

import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def haxe_string(value: str) -> str:
    return json.dumps(str(value))


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
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class VSliceVariationsTest(unittest.TestCase):
    def test_declared_pairs_select_matching_instrumentals_and_vocal_stems(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function normalizedImportFileName",
                "static function isImportFile",
                "static function findImportFile",
                "static function findImportAudio",
                "static function chartFieldString",
                "static function findVSliceSongPairs",
                "static function safeVSliceVariationSuffix",
                "static function findVSliceVariationFile",
                "static function findVSliceInstrumental",
                "static function normalizeVSliceVariationDifficulty",
                "static function findVSliceVoices",
                "static function vSliceStemMatchesReference",
                "static function selectVSliceVocalStems",
            )
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            data = root / "data/songs/bundle-song"
            audio = root / "songs/bundle-song"
            data.mkdir(parents=True)
            audio.mkdir(parents=True)
            base_metadata = {
                "version": "2.2.0",
                "songName": "Bundle Song",
                "playData": {
                    "songVariations": ["alt", "lyrics"],
                    "characters": {"player": "bf-doki", "opponent": "natsuki"},
                },
            }
            alt_metadata = {
                "version": "2.2.0",
                "songName": "Bundle Song Mix",
                "playData": {
                    "songVariations": [],
                    "characters": {
                        "player": "tankman-doki",
                        "opponent": "natsuki",
                        "instrumental": "alt",
                    },
                },
            }
            (data / "bundle-song-metadata.json").write_text(json.dumps(base_metadata), newline='\n')
            (data / "bundle-song-chart.json").write_text(json.dumps({"version": "2.0.0", "notes": {"normal": []}}), newline='\n')
            (data / "bundle-song-metadata-alt.json").write_text(json.dumps(alt_metadata), newline='\n')
            (data / "bundle-song-chart-alt.json").write_text(json.dumps({"version": "2.0.0", "notes": {"alt": []}}), newline='\n')
            (audio / "Inst.ogg").write_bytes(b"base-inst")
            (audio / "Inst-alt.ogg").write_bytes(b"alt-inst")
            for name in ("Voices-bf-doki.ogg", "Voices-natsuki.ogg", "Voices-natsuki-alt.ogg", "Voices-tankman-doki.ogg"):
                (audio / name).write_bytes(name.encode())

            main = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
}}
typedef ConvertedSongChart = {{
  var difficulty:String; var fileName:String; var source:String; var chart:Dynamic;
  @:optional var sourceDifficulty:String;
  @:optional var authoredSongTitle:Bool;
}}
class ModuleFunctions {{
{methods}
  public static function testPairs(dataFolder:String, folder:String, metadata:String, chart:String,
    diagnostics:Array<String>):Array<Dynamic>
    return findVSliceSongPairs(dataFolder, folder, metadata, chart, diagnostics);
  public static function testInstrumental(folder:String, metadata:Dynamic, diagnostics:Array<String>):String
    return findVSliceInstrumental(folder, metadata, diagnostics);
  public static function testUnifiedVoices(folder:String, diagnostics:Array<String>):String
    return findVSliceVoices(folder, diagnostics);
  public static function testVocals(metadata:Dynamic, available:Array<Dynamic>, diagnostics:Array<String>,
    ?variation:String):Array<Dynamic>
    return selectVSliceVocalStems(metadata, available, diagnostics, variation);
  public static function testDifficulty(charts:Array<ConvertedSongChart>, songName:String,
    nativeDifficulties:Array<String>, diagnostics:Array<String>):Void
    normalizeVSliceVariationDifficulty(charts, songName, nativeDifficulties, diagnostics);
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main():Void {{
    var data = {haxe_string(str(data))};
    var audio = {haxe_string(str(audio))};
    var metadataPath = Path.join([data, "bundle-song-metadata.json"]);
    var chartPath = Path.join([data, "bundle-song-chart.json"]);
    var diagnostics:Array<String> = [];
    var pairs = ModuleFunctions.testPairs(data, "bundle-song", metadataPath, chartPath, diagnostics);
    if (pairs.length != 2 || pairs[1].variation != "alt") fail("declared variation pair resolution");
    if (Path.withoutDirectory(pairs[1].metadataPath) != "bundle-song-metadata-alt.json"
      || Path.withoutDirectory(pairs[1].chartPath) != "bundle-song-chart-alt.json")
      fail("variation metadata/chart identity was mismatched");
    var baseMetadata = Json.parse(File.getContent(metadataPath));
    var altMetadata = Json.parse(File.getContent(pairs[1].metadataPath));
    if (ModuleFunctions.testInstrumental(audio, baseMetadata, diagnostics)
      != Path.join([audio, "Inst.ogg"])) fail("base instrumental selection");
    if (ModuleFunctions.testInstrumental(audio, altMetadata, diagnostics)
      != Path.join([audio, "Inst-alt.ogg"])) fail("variation instrumental selection");
    if (ModuleFunctions.testUnifiedVoices(audio, diagnostics) != null)
      fail("an unrelated split voice stem was selected as the mixed vocal track");
    File.saveContent(Path.join([audio, "Voices.ogg"]), "mixed");
    if (ModuleFunctions.testUnifiedVoices(audio, diagnostics) != Path.join([audio, "Voices.ogg"]))
      fail("unified vocal track fallback");
    var singleton:Array<ConvertedSongChart> = [{{difficulty:"lyrics", fileName:"source-lyrics.json",
      source:"source-chart.json", chart:{{song:{{}}}}}}];
    ModuleFunctions.testDifficulty(singleton, "bundle-song-lyrics", ["easy", "normal", "hard"], diagnostics);
    if (singleton[0].difficulty != "normal" || singleton[0].sourceDifficulty != "lyrics"
      || singleton[0].fileName != "bundle-song-lyrics.json")
      fail("unregistered singleton variation difficulty was not made natively selectable");
    var supported:Array<ConvertedSongChart> = [{{difficulty:"hard", fileName:"song-hard.json",
      source:"chart.json", chart:{{song:{{}}}}}}];
    ModuleFunctions.testDifficulty(supported, "song-hard", ["easy", "normal", "hard"], diagnostics);
    if (supported[0].difficulty != "hard" || supported[0].sourceDifficulty != null)
      fail("registered native difficulty was rewritten");
    var stems:Array<Dynamic> = [
      {{id:"bf-doki", source:"bf", destination:"Voices-bf-doki.ogg", role:"shared"}},
      {{id:"natsuki", source:"n", destination:"Voices-natsuki.ogg", role:"shared"}},
      {{id:"natsuki-alt", source:"na", destination:"Voices-natsuki-alt.ogg", role:"shared"}},
      {{id:"tankman-doki", source:"td", destination:"Voices-tankman-doki.ogg", role:"shared"}}
    ];
    var baseStems = ModuleFunctions.testVocals(baseMetadata, stems, diagnostics);
    var altStems = ModuleFunctions.testVocals(altMetadata, stems, diagnostics, "alt");
    if (baseStems.length != 2 || baseStems[0].id != "bf-doki" || baseStems[1].id != "natsuki")
      fail("base vocals included stems from another variation");
    if (altStems.length != 2 || altStems[0].id != "natsuki-alt" || altStems[1].id != "tankman-doki")
      fail("alt vocals did not include the suffixed opponent and variant player stems");
    var diagnosedMissing = false;
    var diagnosedDifficultyMapping = false;
    for (diagnostic in diagnostics) {{
      if (diagnostic.indexOf("variation \\"lyrics\\"") >= 0) diagnosedMissing = true;
      if (diagnostic.indexOf("variation-difficulty-normalized") >= 0) diagnosedDifficultyMapping = true;
    }}
    if (!diagnosedMissing || !diagnosedDifficultyMapping)
      fail("missing declared sibling was not diagnosed");
  }}
}}
'''
            with tempfile.TemporaryDirectory() as build:
                Path(build, "Main.hx").write_text(main, newline='\n')
                result = subprocess.run(
                    [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                     "-cp", build, "-main", "Main", "--interp"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
