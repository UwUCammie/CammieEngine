"""FPS Plus song-meta.json mapping and mounted donor immutability coverage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods/whitty")
HAXE = ROOT / ".tools/haxe/haxe"


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


def make_fixture(module_source: str, folder: Path) -> Path:
    # applyKadeSourceStageCompatibility references KadeStageSource; ship the
    # parser beside the extracted methods so the fixture compiles.
    methods = "\n".join(
        extract_method(module_source, marker)
        for marker in (
            "static function normalizedImportFileName",
            "static function isImportFile",
            "static function validImportPath",
            "static function validModuleName",
            "static function findImportFile",
            "static function findImportAudio",
            "static function findImportVocalStems",
            "static function readImportJson",
            "static function convertImportDialogue",
            "static function importCutsceneScript",
            "static function importCutsceneBool",
            "static public function processInfo",
            "static public function getInfoValue",
            "static public function getInfoBool",
            "static public function getInfoInt",
            "static function chartFieldString",
            "static function chartFieldBool",
            "static function chartFieldInt",
            "static function readSongChart",
            "static function collectSongNoteDefinitions",
            "static function prepareSongNoteDefinitions",
            "static function normalizeImportedCategory",
            "static function songImportFromRoots",
    "static function applyKadeSourceStageCompatibility",
            "static function applyKadeSourceCharacterCompatibility",
            "static function prepareKadeSourceCharacter",
            "static function generateKadeCharacterHScript",
            "static function nativeCharacterComplete",
            "static function placedActorPoint",
            "static function injectAfterActorPlacement",
            "static function chooseVSliceRegistry",
            "static function findVSliceVideo",
            "static function applyImportedVisualMetadata",
            "public static function importedCameraZoomMode",
            "static function applyImportedSidecars",
        )
    )
    source = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef SongImport = {{
  @:optional var engine:String;
  var name:String; var p1:String; var p2:String; var gf:String; var stage:String;
  var ui:String; var cutscene:String; var category:String; var isHey:Bool;
  var isCheer:Bool; var isMoody:Bool; var isSpooky:Bool; var stageID:Int; var week:Int;
  var char:String; var display:String; var inst:String; var voices:String; var dialog:String;
  @:optional var dialogueJson:String; @:optional var dialogueText:String;
  @:optional var cutsceneJson:String; @:optional var cutsceneScript:String;
  @:optional var events:String; @:optional var cutsceneStoryOnly:Bool;
  @:optional var cutscenePlayOnce:Bool; var modchart:String;
  @:optional var generatedModchart:String; var diffFiles:Array<String>;
  @:optional var noteDefinitions:Array<Dynamic>; @:optional var diagnostics:Array<String>;
  @:optional var compatMetadata:Dynamic; @:optional var songArtist:String;
  @:optional var album:String; @:optional var difficultyRatings:Array<Dynamic>;
}};
class ImportEngine {{ public static inline var PSYCH:String = 'Psych Engine'; }}
typedef SongImportVocalStem = {{ var source:String; var destination:String;
  @:optional var id:String; @:optional var role:String; }};

class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
typedef LuaCompatResult = {{ var hscript:String; var supported:Bool; var diagnostics:Array<String>; }};
class LuaCompat {{ public static function translate(source:String, ?origin:String):LuaCompatResult
  return {{hscript:'', supported:false, diagnostics:[]}}; }}
class EngineCompat {{
  public static function legacyDialogueText(data:Dynamic, player1:String, player2:String):String return null;
  public static function legacyCutsceneScript(data:Dynamic):String return null;
  public static function legacyCutsceneBool(data:Dynamic, field:String, fallback:Bool):Bool return fallback;
}}
class NoteTypeCompat {{
  public static function isStringType(value:Dynamic):Bool return value != null && Std.isOfType(value, String);
  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int return 0;
}}
class MetaFixture {{
{methods}
  static function field(value:Dynamic, name:String):Dynamic
    return value == null ? null : Reflect.field(value, name);
  static function main() {{
    var root = Sys.args()[0];
    var charts:Array<String> = [];
    for (entry in FileSystem.readDirectory(root)) {{
      var lower = entry.toLowerCase();
      if (lower.endsWith('.json') && lower != 'meta.json' && lower != 'events.json'
          && lower != 'dialogue.json' && lower != 'cutscene.json')
        charts.push(Path.join([root, entry]));
    }}
    charts.sort(function(a:String, b:String):Int return Reflect.compare(a, b));
    var song = songImportFromRoots(root, root, Path.withoutDirectory(Path.normalize(root)), charts);
    var metadata = field(song, 'compatMetadata');
    var raw = field(metadata, 'raw');
    var rawFields:Array<String> = raw == null ? [] : Reflect.fields(raw);
    rawFields.sort(function(a:String, b:String):Int return Reflect.compare(a, b));
    var diagnostics:Array<String> = song.diagnostics == null ? [] : song.diagnostics;
    var materialized:Dynamic = {{}};
    applyImportedVisualMetadata(materialized, song);
    applyImportedSidecars(materialized, song, 0);
    Sys.println(Json.stringify({{
      name:song.name,
      display:song.display,
      artist:field(song, 'songArtist'),
      album:field(song, 'album'),
      ratings:field(song, 'difficultyRatings'),
      format:field(metadata, 'format'),
      sourceFile:field(metadata, 'sourceFile'),
      rawFields:rawFields,
      materializedArtist:field(materialized, 'songArtist'),
      materializedAlbum:field(materialized, 'album'),
      materializedRatings:field(materialized, 'difficultyRatings'),
      materializedRating:field(materialized, 'difficultyRating'),
      materializedMetadata:field(materialized, 'compatMetadata'),
      chartCount:charts.length,
      diagnostics:diagnostics
    }}));
  }}
}}
'''
    path = folder / "MetaFixture.hx"
    path.write_text(source + "\n" + (ROOT / "source/KadeStageSource.hx").read_text().replace("package;", "").replace("import haxe.io.Path;", "").replace("import sys.FileSystem;", "").replace("import sys.io.File;", ""))
    return path


class FpsPlusSongMetadataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = (ROOT / "source/ModuleFunctions.hx").read_text()

    def run_fixture(self, root: Path) -> dict:
        with tempfile.TemporaryDirectory(prefix="fps-meta-fixture-", dir=ROOT / "tmp") as folder:
            folder_path = Path(folder)
            make_fixture(self.module, folder_path)
            result = subprocess.run(
                [str(HAXE), "-cp", str(folder_path), "--run", "MetaFixture", str(root)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
            self.assertTrue(lines, result.stdout + result.stderr)
            return json.loads(lines[-1])

    def test_song_loader_inherits_fps_metadata_from_a_sibling_difficulty(self):
        source = (ROOT / "source/Song.hx").read_text()
        fields_start = source.index("\tstatic var gameplayFields")
        fields_end = source.index("\n\tstatic var registryCache", fields_start)
        fields = source[fields_start:fields_end]
        chart_has_value = extract_method(source, "\tstatic function chartHasValue(")
        resolve = extract_method(source, "\tpublic static function resolveChartData(")
        visual_valid = extract_method(source, "\tstatic function visualValueIsValid(")
        fixture = """import haxe.Json;
using StringTools;

class SongMetadataInheritanceTest {
""" + fields + """
""" + chart_has_value + """
	static function isValidVisualValue(field:String, value:Dynamic):Bool return true;
""" + resolve + """
""" + visual_valid + """
	static function main() {
		var requested:Dynamic = {song:'fps-song', notes:[], bpm:120};
		var sibling:Dynamic = {
			songArtist:'sock.clip', album:'vol2', difficultyRatings:[7, 9, 12],
			difficultyRating:9, compatMetadata:{format:'fps-plus-song-meta', raw:{future:42}}
		};
		var resolved = resolveChartData(requested, [sibling], sibling);
		if (resolved.songArtist != 'sock.clip' || resolved.album != 'vol2')
			throw 'artist/album metadata did not inherit from the sibling difficulty';
		if (resolved.difficultyRatings[2] != 12 || resolved.difficultyRating != 9)
			throw 'difficulty metadata did not inherit from the sibling difficulty';
		if (resolved.compatMetadata.raw.future != 42)
			throw 'unknown compatibility metadata was not inherited';
	}
}
"""
        with tempfile.TemporaryDirectory(prefix="fps-meta-song-", dir=ROOT / "tmp") as folder:
            path = Path(folder) / "SongMetadataInheritanceTest.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-main", "SongMetadataInheritanceTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_known_unknown_and_malformed_metadata(self):
        with tempfile.TemporaryDirectory(prefix="fps-meta-synthetic-", dir=ROOT / "tmp") as folder:
            root = Path(folder)
            (root / "meta.json").write_text(json.dumps({
                "name": "Synthetic Display", "artist": "Synthetic Artist",
                "album": "Synthetic Album", "difficulties": [1, 2.5, 4],
                "futureKey": {"preserve": [True, False]},
            }))
            chart = {"song": {"song": "synthetic", "notes": [], "bpm": 120,
                               "player1": "bf", "player2": "dad", "gf": "gf",
                               "stage": "stage"}}
            (root / "synthetic.json").write_text(json.dumps(chart))
            (root / "Inst.ogg").write_bytes(b"fixture")
            parsed = self.run_fixture(root)
            self.assertEqual(parsed["display"], "Synthetic Display")
            self.assertEqual(parsed["artist"], "Synthetic Artist")
            self.assertEqual(parsed["album"], "Synthetic Album")
            self.assertEqual(parsed["ratings"], [1, 2.5, 4])
            self.assertEqual(parsed["materializedArtist"], "Synthetic Artist")
            self.assertEqual(parsed["materializedAlbum"], "Synthetic Album")
            self.assertEqual(parsed["materializedRatings"], [1, 2.5, 4])
            self.assertEqual(parsed["materializedRating"], 1)
            self.assertEqual(parsed["materializedMetadata"]["raw"]["futureKey"],
                             {"preserve": [True, False]})
            self.assertEqual(parsed["format"], "fps-plus-song-meta")
            self.assertEqual(parsed["sourceFile"], "meta.json")
            self.assertIn("futureKey", parsed["rawFields"])
            self.assertEqual(parsed["diagnostics"], [])

            (root / "meta.json").write_text('{"name":"Safe", "artist":"A", "album":"B", "difficulties":["bad"], "future":7}')
            malformed = self.run_fixture(root)
            self.assertEqual(malformed["display"], "Safe")
            self.assertEqual(malformed["artist"], "A")
            self.assertIsNone(malformed["ratings"])
            self.assertIsNone(malformed["materializedRatings"])
            self.assertTrue(any("[fps-meta-invalid]" in item for item in malformed["diagnostics"]))

            (root / "meta.json").write_text('[]')
            non_object = self.run_fixture(root)
            self.assertEqual(non_object["display"], "null")
            self.assertIsNone(non_object["artist"])
            self.assertTrue(any("[fps-meta-invalid]" in item for item in non_object["diagnostics"]))

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_whitty_four_songs_and_donor_immutability(self):
        songs = {"ballistic": ["Ballistic", "sock.clip", "vol2", [7, 9, 12], 3],
                 "lo-fight": ["Lo Fight", "sock.clip", "vol2", [1, 2, 2], 3],
                 "overhead": ["Overhead", "sock.clip", "vol2", [2, 3, 5], 3],
                 "remorse": ["Remorse", "sock.clip", "vol2", [3, 3, 3], 1]}
        roots = {name: DONOR / "data/songs" / name for name in songs}
        selected_files = [path for root in roots.values() for path in root.iterdir() if path.is_file()]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in selected_files}
        try:
            for name, expected in songs.items():
                parsed = self.run_fixture(roots[name])
                self.assertEqual(parsed["name"], expected[0] if name != "lo-fight" else "Lo-Fight")
                self.assertEqual(parsed["display"], expected[0])
                self.assertEqual(parsed["artist"], expected[1])
                self.assertEqual(parsed["album"], expected[2])
                self.assertEqual(parsed["ratings"], expected[3])
                self.assertEqual(parsed["chartCount"], expected[4])
                self.assertEqual(parsed["sourceFile"], "meta.json")
                self.assertEqual(parsed["diagnostics"], [])
                self.assertEqual(set(parsed["rawFields"]), {"name", "artist", "album", "difficulties"})
        finally:
            after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in selected_files}
            self.assertEqual(before, after, "FPS Plus donor chart/meta bytes changed during metadata discovery")


if __name__ == "__main__":
    unittest.main()
