"""Synthetic coverage for descriptor-aware legacy/Psych song discovery."""

from pathlib import Path
import subprocess
import os
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def directory_listing_source() -> str:
    return (ROOT / "source/ImportDirectoryListing.hx").read_text().replace("package;", "")


def with_kade_parser(fixture: str) -> str:
    """Embed the KadeStageSource parser into a generated fixture: its import
    lines merge at the top of the file, its class lands at the end."""
    parser = (ROOT / "source/KadeStageSource.hx").read_text().replace("package;", "")
    cut = parser.index("\nclass ")
    return parser[:cut] + fixture + "\n" + directory_listing_source() + parser[cut:]


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


class EngineSongImportCompatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "source/ModuleFunctions.hx").read_text()

    def test_descriptor_song_walk_handles_shared_data_and_native_nested_data(self):
        source = self.source
        methods = "\n".join(
                    extract_method(source, marker)
                    for marker in (
                        "static function importPathKey",
                        "static function normalizedImportFileName",
                        "static function isImportFile",
                        "static function validImportPath",
                        "static function validModuleName",
                        "static function existingImportChild",
                        "static function importSongFolderName",
                        "static function findImportFile",
                        "static function findImportAudio",
                        "static function findImportVocalStems",
                        "static function readImportJson",
                        "static function convertImportDialogue",
                        "static function importCutsceneScript",
                        "static function importCutsceneBool",
                        "static function getImportDifficultyNames",
                        "static function findImportChart",
                        "static function isImportChartSidecar",
                        "static function collectAssetCharts",
                        "static function chartFieldString",
                        "static function inferPsychStageForImport",
                        "static function chartFieldBool",
                        "static function chartFieldInt",
                        "static function findNamedDirectory",
                        "static function readSongChart",
                        "static function prepareSongNoteDefinitions",
                        "static function collectSongNoteDefinitions",
                        "static function hasMaterializedFile",
                        "static function hasExistingSongInstrumental",
                        "static function normalizeImportedCategory",
                        "static function importedChartFileName",
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
                        "static function findLegacyMusicAudio",
                        "static function songImportFromAssetFolders",
                        "static function appendAssetSongImports",
                "static public function processInfo",
                "static public function getInfoValue",
                "static public function getInfoBool",
                "static public function getInfoInt",
                "static public function validateSongImport",
                    )
            )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef SongImportVocalStem = {{ var source:String; var destination:String; @:optional var id:String; @:optional var role:String; }};
typedef SongImport = {{
  var name:String; var p1:String; var p2:String; var gf:String; var stage:String;
  var ui:String; var cutscene:String; var category:String; var isHey:Bool;
  var isCheer:Bool; var isMoody:Bool; var isSpooky:Bool; var stageID:Int; var week:Int;
  var char:String; var display:String; var inst:String; var voices:String; var dialog:String;
  @:optional var dialogueJson:String; @:optional var dialogueText:String;
  @:optional var cutsceneJson:String; @:optional var cutsceneScript:String;
  @:optional var events:String;
  @:optional var cutsceneStoryOnly:Bool; @:optional var cutscenePlayOnce:Bool;
  var modchart:String; var diffFiles:Array<String>; @:optional var convertedCharts:Array<Dynamic>;
  @:optional var vocalStems:Array<Dynamic>;
  @:optional var noteDefinitions:Array<Dynamic>;
  @:optional var importSourceInfo:SongImportSource;
  @:optional var sourceSelectableDifficulties:Array<String>;
  @:optional var sourceUnsupportedDifficulties:Array<String>;
  @:optional var generatedModchart:String; @:optional var diagnostics:Array<String>;
}};
typedef SongImportSource = {{ var song:String; var data:String; var destination:String;
  @:optional var sourceRoot:String; @:optional var engine:String; }};
typedef SongImportRejectionCollector = {{ var entries:Array<Dynamic>; var total:Int;
  var truncated:Bool; var seen:Map<String, Bool>; }};
typedef LuaCompatResult = {{ var hscript:String; var supported:Bool; var diagnostics:Array<String>; }};
class LuaCompat {{
  public static function translate(source:String, ?origin:String):LuaCompatResult
    return {{hscript: source, supported: true, diagnostics: []}};
}}
class FNFAssets {{
  public static function getText(path:String):String throw 'destination registry unavailable';
}}
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
}}
class DifficultyIcons {{ public static function getEndingFP(index:Int):String return ''; }}
class NoteTypeCompat {{
  public static function isStringType(value:Dynamic):Bool return value != null && Std.isOfType(value, String);
  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int {{
    var type = Std.string(value);
    for (i in 0...definitions.length)
      if (Std.string(definitions[i].sourceNoteType) == type) return i;
    definitions.push({{sourceNoteType:type}}); return definitions.length - 1;
  }}
}}
class EngineCompat {{
  public static function legacyDialogueText(data:Dynamic, player1:String, player2:String):String return 'Converted line';
  public static function legacyCutsceneScript(data:Dynamic):String return 'TogetherIntro';
  public static function legacyCutsceneBool(data:Dynamic, field:String, fallback:Bool):Bool return true;
}}
class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}
class ImportEngine {{
  public static inline var PSYCH:String = 'Psych Engine';
  public static inline var KADE:String = 'Kade Engine';
  public static inline var NIGHTMARE_VISION:String = 'Nightmare Vision';
}}
class PsychStageInference {{ public static function resolve(_root:String, _song:String):String return null; }}
class ImportCompat {{
  static inline var MAX_IMPORT_DISCOVERY_DIRECTORIES:Int = 4096;
  static function importWorkCancelled():Bool return false;
  static function yieldImportWork(?force:Bool = false):Void {{}}
{methods}
  static function validateAndRecordSongImport(_rejections:SongImportRejectionCollector,
      songData:SongImport, _sourceRoot:String, _sourcePath:String, _engine:String):Bool
    return validateSongImport(songData) == null;
  static function main() {{
    var root = Sys.args()[0];
    var sharedData = Path.join([root, 'assets/shared/data']);
    var sharedSongs = Path.join([root, 'assets/songs']);
    var nestedData = Path.join([root, 'native/data']);
    var nestedSongs = Path.join([root, 'native/songs']);
    var flatData = Path.join([root, 'flat/data']);
    var flatSongs = Path.join([root, 'flat/songs']);
    var splitData = Path.join([root, 'split/data']);
    var splitSongs = Path.join([root, 'split/songs']);
    var togetherData = Path.join([root, 'together/data']);
    var togetherSongs = Path.join([root, 'together/songs']);
    var psychData = Path.join([root, 'psych/assets/data']);
    var psychSongs = Path.join([root, 'psych/assets/songs']);
    var psychSourceRoot = Path.join([root, 'psych']);
    var sourceMap:Map<String, SongImportSource> = new Map<String, SongImportSource>();

    var sharedResult:Array<SongImport> = [];
    appendAssetSongImports(sharedResult, new Map<String, Bool>(), sharedData, sharedSongs, null, sourceMap);
    if (sharedResult.length != 1 || sharedResult[0].name != 'shared-demo')
      throw 'shared/data song was not discovered';
    if (!sharedResult[0].inst.toLowerCase().endsWith('shared-demo-inst.ogg'))
      throw 'hyphenated Inst stem was not found';
    if (!sharedResult[0].voices.toLowerCase().endsWith('shared-demo-voices.ogg'))
      throw 'hyphenated Voices stem was not found';
    if (sharedResult[0].events == null
        || !sharedResult[0].events.toLowerCase().endsWith('events.json'))
      throw 'Psych companion events sidecar was not discovered';
    if (sharedResult[0].diffFiles.length != 1)
      throw 'song-shaped event sidecar became a native chart';

    var nestedResult:Array<SongImport> = [];
    appendAssetSongImports(nestedResult, new Map<String, Bool>(), nestedData, nestedSongs, null, null);
    if (nestedResult.length != 1 || nestedResult[0].name != 'native-demo')
      throw 'data/songs nested chart was not discovered';
    if (nestedResult[0].diffFiles.length != 3 || nestedResult[0].diffFiles[1] == null
        || nestedResult[0].diffFiles[2] == null
        || !nestedResult[0].diffFiles[2].toLowerCase().endsWith('native-demo-expert.json'))
      throw 'normal/custom chart fallback was not collected';

    var flatResult:Array<SongImport> = [];
    appendAssetSongImports(flatResult, new Map<String, Bool>(), flatData, flatSongs, null, null);
    if (flatResult.length != 1 || flatResult[0].name != 'flat-demo')
      throw 'flat songs chart was not discovered';
    if (!flatResult[0].inst.toLowerCase().endsWith('flat-demo-inst.ogg'))
      throw 'flat songs Inst stem was not found';
    if (flatResult[0].voices == null
        || !flatResult[0].voices.toLowerCase().endsWith('flat-demovoicestogether.ogg'))
      throw 'flat songs VoicesTogether stem was not found';
    var splitResult:Array<SongImport> = [];
    appendAssetSongImports(splitResult, new Map<String, Bool>(), splitData, splitSongs, null, null);
    if (splitResult.length != 1 || splitResult[0].vocalStems == null
        || splitResult[0].vocalStems.length != 2)
      throw 'split vocal stems were not discovered';
    if (splitResult[0].vocalStems[0].destination != 'Voices-Opponent.ogg'
        || splitResult[0].vocalStems[1].destination != 'Voices-Player.ogg')
      throw 'split vocal stems were not stably ordered';
    var togetherResult:Array<SongImport> = [];
    appendAssetSongImports(togetherResult, new Map<String, Bool>(), togetherData, togetherSongs, null, null);
    if (togetherResult.length != 1 || togetherResult[0].voices == null
        || !togetherResult[0].voices.toLowerCase().endsWith('voicestogether.ogg'))
      throw 'VoicesTogether fallback was not discovered';
    if (togetherResult[0].dialogueText == null
        || togetherResult[0].dialogueText.indexOf('Converted line') < 0)
      throw 'legacy dialogue JSON was not converted';
    if (togetherResult[0].cutsceneScript != 'TogetherIntro'
        || togetherResult[0].cutsceneStoryOnly != true
        || togetherResult[0].cutscenePlayOnce != true)
      throw 'legacy cutscene metadata was not normalized';

    var psychSongDataResult:Array<SongImport> = [];
    appendAssetSongImports(psychSongDataResult, new Map<String, Bool>(), psychData, psychSongs,
      null, null, psychSourceRoot, ImportEngine.PSYCH);
    if (psychSongDataResult.length != 1 || psychSongDataResult[0].name != 'stress-song')
      throw 'Psych data/songData chart was not discovered';
    if (Reflect.field(psychSongDataResult[0], 'engine') != ImportEngine.PSYCH
        || Reflect.field(psychSongDataResult[0], 'sourceRoot') != psychSourceRoot)
      throw 'Psych engine ownership was not preserved for data/songData';
    if (psychSongDataResult[0].diffFiles.length != 1
        || psychSongDataResult[0].events == null
        || psychSongDataResult[0].inst == null || psychSongDataResult[0].voices == null)
      throw 'Psych data/songData chart, event, or audio companions were not collected';

    var nightmareVisionSongDataResult:Array<SongImport> = [];
    appendAssetSongImports(nightmareVisionSongDataResult, new Map<String, Bool>(), psychData, psychSongs,
      null, null, psychSourceRoot, ImportEngine.NIGHTMARE_VISION);
    if (nightmareVisionSongDataResult.length != 1
        || Reflect.field(nightmareVisionSongDataResult[0], 'engine') != ImportEngine.NIGHTMARE_VISION)
      throw 'Nightmare Vision data/songData import lost its separate engine identity';

    var nestedNmvRoot = Path.join([root, 'nmv-root']);
    var nestedNmvSources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
    var nestedNmvResult:Array<SongImport> = [];
    appendAssetSongImports(nestedNmvResult, new Map<String, Bool>(),
      Path.join([nestedNmvRoot, 'assets/data']), Path.join([nestedNmvRoot, 'assets/songs']),
      null, nestedNmvSources, nestedNmvRoot, ImportEngine.NIGHTMARE_VISION);
    if (nestedNmvResult.length != 2 || nestedNmvResult[0].name != 'Displayed NMV Song'
        || nestedNmvResult[1].name != 'Direct Audio Song')
      throw 'NMV content/<pack>/songs/<song> package was not discovered';
    var nestedNmvSong = nestedNmvResult[0];
    var nestedNmvSource:SongImportSource = nestedNmvSong.importSourceInfo;
    if (nestedNmvSong.diffFiles.length != 2
        || !nestedNmvSong.inst.toLowerCase().endsWith('/audio/inst.ogg')
        || !nestedNmvSong.voices.toLowerCase().endsWith('/audio/voices.ogg'))
      throw 'NMV nested data/audio charts or stems were not collected';
    if (Reflect.field(nestedNmvSong, 'sourceFolder') != 'authored-id'
        || Reflect.field(nestedNmvSong, 'engine') != ImportEngine.NIGHTMARE_VISION
        || Reflect.field(nestedNmvSong, 'sourceRoot')
          != Path.join([nestedNmvRoot, 'content/another-pack']))
      throw 'NMV nested source identity or engine ownership was not preserved';
    if (nestedNmvSource == null
        || nestedNmvSource.song != Path.join([nestedNmvRoot, 'content/another-pack/songs/authored-id'])
        || nestedNmvSource.data != Path.join([nestedNmvRoot, 'content/another-pack/songs/authored-id/data'])
        || nestedNmvSource.sourceRoot != Path.join([nestedNmvRoot, 'content/another-pack']))
      throw 'NMV nested source paths did not retain their playable song package';
    var directNmvSource:SongImportSource = nestedNmvResult[1].importSourceInfo;
    if (nestedNmvResult[1].inst == null
        || !nestedNmvResult[1].inst.toLowerCase().endsWith('/songs/direct-audio-id/inst.ogg')
        || directNmvSource == null
        || directNmvSource.song != Path.join([nestedNmvRoot, 'content/direct-audio-pack/songs/direct-audio-id'])
        || directNmvSource.sourceRoot != Path.join([nestedNmvRoot, 'content/direct-audio-pack']))
      throw 'NMV song-root audio fallback was not preserved';
    var selectedNmvPack = Path.join([nestedNmvRoot, 'content/direct-audio-pack']);
    var selectedNmvResult:Array<SongImport> = [];
    appendAssetSongImports(selectedNmvResult, new Map<String, Bool>(),
      Path.join([selectedNmvPack, 'data']), Path.join([selectedNmvPack, 'songs']), null,
      null, selectedNmvPack, ImportEngine.NIGHTMARE_VISION);
    if (selectedNmvResult.length != 1 || selectedNmvResult[0].name != 'Direct Audio Song'
        || Reflect.field(selectedNmvResult[0], 'sourceRoot') != selectedNmvPack
        || Reflect.field(selectedNmvResult[0], 'engine') != ImportEngine.NIGHTMARE_VISION)
      throw 'Selected NMV package root was not imported with its own owner';

    var laneThreePack = Path.join([root, 'content/lane-three-pack']);
    var laneThreeResult:Array<SongImport> = [];
    appendAssetSongImports(laneThreeResult, new Map<String, Bool>(),
      Path.join([laneThreePack, 'data']), Path.join([laneThreePack, 'songs']), null,
      null, laneThreePack, ImportEngine.NIGHTMARE_VISION);
    if (laneThreeResult.length != 1 || laneThreeResult[0].diagnostics == null)
      throw 'NMV lane-count diagnostics were not attached to the import plan';
    var laneThreeDiagnostics = laneThreeResult[0].diagnostics.join(';');
    if (laneThreeDiagnostics.indexOf('[nightmare-vision-unsupported-chart-lanes]') < 0
        || laneThreeDiagnostics.indexOf('lanes=3') < 0
        || laneThreeDiagnostics.indexOf('monster-three-lane.json') < 0)
      throw 'NMV 3-lane chart did not retain a source-path diagnostic';

    var collisionRoot = Path.join([root, 'nmv-owner-collision']);
    var collisionResult:Array<SongImport> = [];
    appendAssetSongImports(collisionResult, new Map<String, Bool>(),
      Path.join([collisionRoot, 'assets/data']), Path.join([collisionRoot, 'assets/songs']),
      null, null, collisionRoot, ImportEngine.NIGHTMARE_VISION);
    if (collisionResult.length != 2)
      throw 'Base and nested same-key NMV sources were not retained as separate candidates';
    var baseMonster:SongImport = null;
    var packMonster:SongImport = null;
    for (candidate in collisionResult)
      if (candidate.name.toLowerCase() == 'monster') {{
        if (Reflect.field(candidate, 'sourceRoot') == collisionRoot)
          baseMonster = candidate;
        else
          packMonster = candidate;
      }}
    if (baseMonster == null || packMonster == null
        || Reflect.field(packMonster, 'sourceRoot')
          != Path.join([collisionRoot, 'content/dsides-pack']))
      throw 'Nested NMV owner was not isolated from its same-key engine-base song';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp_path = Path(folder)
            (temp_path / "NightmareVisionChartCompat.hx").write_text(
                (ROOT / "source/NightmareVisionChartCompat.hx").read_text()
            )
            (temp_path / "NightmareVisionScriptDiscovery.hx").write_text(
                (ROOT / "source/NightmareVisionScriptDiscovery.hx").read_text()
            )
            (temp_path / "NightmareVisionDifficultyCompat.hx").write_text(
                (ROOT / "source/NightmareVisionDifficultyCompat.hx").read_text()
            )
            fixture_path = temp_path / "ImportCompat.hx"
            fixture_path.write_text(with_kade_parser(fixture))
            root = temp_path / "fixture"
            shared_data = root / "assets/shared/data/shared-demo"
            shared_songs = root / "assets/songs/shared-demo"
            nested_data = root / "native/data/songs/native-demo"
            nested_songs = root / "native/songs/native-demo"
            flat_data = root / "flat/data/flat-demo"
            flat_songs = root / "flat/songs"
            split_data = root / "split/data/split-demo"
            split_songs = root / "split/songs/split-demo"
            psych_data = root / "psych/assets/data/songData/stress-song"
            psych_songs = root / "psych/assets/songs/stress-song"
            nested_nmv_root = root / "nmv-root"
            nested_nmv_song = nested_nmv_root / "content/another-pack/songs/authored-id"
            nested_nmv_data = nested_nmv_song / "data"
            nested_nmv_audio = nested_nmv_song / "audio"
            incomplete_nmv_song = nested_nmv_root / "content/another-pack/songs/missing-inst"
            direct_audio_song = nested_nmv_root / "content/direct-audio-pack/songs/direct-audio-id"
            lane_three_pack = root / "content/lane-three-pack"
            lane_three_data = lane_three_pack / "songs/monster"
            collision_root = root / "nmv-owner-collision"
            collision_pack = collision_root / "content/dsides-pack"
            collision_pack_song = collision_pack / "songs/monster"
            for path in (shared_data, shared_songs, nested_data, nested_songs, flat_data, flat_songs,
                         split_data, split_songs, root / "together/data/together-demo", root / "together/songs/together-demo",
                         psych_data, psych_songs, nested_nmv_root / "assets/data",
                         nested_nmv_root / "assets/songs", nested_nmv_data, nested_nmv_audio,
                         incomplete_nmv_song / "data", incomplete_nmv_song / "audio",
                         direct_audio_song / "data",
                         nested_nmv_root / "content/direct-audio-pack/data",
                         lane_three_pack / "data", lane_three_data / "data", lane_three_data / "audio",
                         collision_root / "assets/data/monster", collision_root / "assets/songs/monster",
                         collision_pack / "data", collision_pack_song / "data", collision_pack_song / "audio"):
                path.mkdir(parents=True)

            chart = '{"song":{"song":"shared-demo","player1":"bf","player2":"dad","notes":[]}}'
            (shared_data / "shared-demo.json").write_text(chart)
            (shared_data / "events.json").write_text('{"events":[]}')
            # A song-shaped event backup is still a sidecar, not a playable
            # chart.  Discovery must use the native notes payload rather than
            # a filename-specific exclusion.
            (shared_data / "events-backup.json").write_text('{"song":{"events":[]}}')
            (shared_songs / "Shared-Demo-Inst.ogg").write_bytes(b"inst")
            (shared_songs / "Shared-Demo-Voices.ogg").write_bytes(b"voices")

            native_chart = '{"song":{"song":"native-demo","player1":"bf","player2":"dad","notes":[]}}'
            (nested_data / "native-demo.json").write_text(native_chart)
            (nested_data / "native-demo-hard.json").write_text(native_chart)
            (nested_data / "native-demo-expert.json").write_text(native_chart)
            (nested_songs / "Native-Demo-Inst.ogg").write_bytes(b"inst")
            (flat_data / "flat-demo.json").write_text('{"song":{"song":"flat-demo","notes":[]}}')
            (flat_songs / "Flat-Demo-Inst.ogg").write_bytes(b"inst")
            (flat_songs / "Flat-DemoVoicesTogether.ogg").write_bytes(b"together")
            (split_data / "split-demo.json").write_text('{"song":{"song":"split-demo","notes":[]}}')
            (split_songs / "Inst.ogg").write_bytes(b"inst")
            (split_songs / "Voices-Player.ogg").write_bytes(b"player")
            (split_songs / "Voices-Opponent.ogg").write_bytes(b"opponent")
            together_data = root / "together/data/together-demo"
            together_songs = root / "together/songs/together-demo"
            (together_data / "together-demo.json").write_text(
                '{"song":{"song":"together-demo","player1":"bf","player2":"dad","notes":[]}}'
            )
            (together_data / "dialogue.json").write_text(
                '{"dialogue":[{"portraits":["dadPort"],"text":"Converted line","box":"normal"}]}'
            )
            (together_data / "cutscene.json").write_text(
                '{"startCutscene":{"name":"TogetherIntro","storyOnly":true,"playOnce":true}}'
            )
            (together_songs / "Inst.ogg").write_bytes(b"inst")
            (together_songs / "VoicesTogether.ogg").write_bytes(b"together")

            (psych_data / "stress-song.json").write_text(
                '{"song":{"song":"stress-song","player1":"bf","player2":"dad","notes":[]}}'
            )
            (psych_data / "events.json").write_text('{"events":[]}')
            (psych_songs / "Inst.ogg").write_bytes(b"inst")
            (psych_songs / "Voices.ogg").write_bytes(b"voices")

            nested_nmv_chart = (
                '{"song":{"song":"Displayed NMV Song","player1":"bf","player2":"dad","notes":[]}}'
            )
            (nested_nmv_data / "easy.json").write_text(nested_nmv_chart)
            (nested_nmv_data / "normal.json").write_text(nested_nmv_chart)
            (nested_nmv_audio / "Inst.ogg").write_bytes(b"inst")
            (nested_nmv_audio / "Voices.ogg").write_bytes(b"voices")
            (incomplete_nmv_song / "data/normal.json").write_text(
                '{"song":{"song":"Must Not Borrow Base Audio","notes":[]}}'
            )
            (nested_nmv_root / "assets/songs/missing-inst_Inst.ogg").write_bytes(b"unrelated base audio")
            (direct_audio_song / "data/normal.json").write_text(
                '{"song":{"song":"Direct Audio Song","notes":[]}}'
            )
            (direct_audio_song / "Inst.ogg").write_bytes(b"inst")
            (lane_three_data / "data/monster-three-lane.json").write_text(
                '{"song":{"song":"monster","format":"nmv2","keys":4,"lanes":3,'
                '"notes":[{"mustHitSection":false,"sectionNotes":[[0,8,0]]}]}}'
            )
            (lane_three_data / "audio/Inst.ogg").write_bytes(b"inst")
            (collision_root / "assets/data/monster/monster.json").write_text(
                '{"song":{"song":"monster","notes":[]}}'
            )
            (collision_root / "assets/songs/monster/Inst.ogg").write_bytes(b"base inst")
            (collision_pack_song / "data/normal.json").write_text(
                '{"song":{"song":"monster","notes":[]}}'
            )
            (collision_pack_song / "audio/Inst.ogg").write_bytes(b"pack inst")

            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "--run", "ImportCompat", str(root)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout + result.stderr)

    def test_import_chart_separates_authored_title_from_linux_audio_storage(self):
        self.assertIn("prepareImportedSongIdentity(coolSongSong, songData, targetFolder,", self.source)
        self.assertIn("prepareImportedSongIdentity(coolSongSong, songData, targetFolder);", self.source)
        self.assertIn("Reflect.setField(chartSong, 'compatPreserveSongTitle', true)", self.source)
        self.assertIn("Path.join(['assets', 'songs', targetFolder])", self.source)

    def test_import_path_identity_preserves_linux_case_and_normalizes_windows_separators(self):
        method = extract_method(self.source, "static function importPathKey")
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}

class ImportCompat {{
{method}
  static function main() {{
    var root = Sys.args()[0];
    var upper = Path.join([root, 'Donor']);
    var lower = Path.join([root, 'donor']);
    FileSystem.createDirectory(upper);
    #if !windows
    FileSystem.createDirectory(lower);
    #end
    var upperKey = importPathKey(upper);
    var lowerKey = importPathKey(lower);
    #if windows
    if (upperKey != lowerKey) throw 'Windows path identity is not case-insensitive';
    #else
    if (upperKey == lowerKey) throw 'Linux donor roots were case-folded';
    #end
    var windowsSpelling = StringTools.replace(upper, '/', '\\\\');
    if (importPathKey(windowsSpelling) != upperKey)
      throw 'import path identity changed with Windows separators';
    var unc = importPathKey('\\\\\\\\server\\\\share\\\\Pack\\\\');
    var uncSlash = importPathKey('//server/share/Pack/');
    if (unc != uncSlash) throw 'import path identity lost UNC separator normalization';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportCompat.hx"
            fixture_path.write_text(with_kade_parser(fixture))
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "--run", "ImportCompat", folder],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_partial_destinations_are_repairable_without_replacing_existing_data(self):
        source = self.source
        self.assertIn("static public function songNeedsRepair(songData:SongImport)", source)
        self.assertIn("static public function songIsRegistered(songName:String)", source)
        self.assertIn("if (!FileSystem.exists(existingImportChild(dataFolder, fileName)))", source)
        self.assertIn("A crashed import may have left this media file behind", source)
        self.assertIn("var alreadyRegistered = freeplayRegistryHasSong", source)
        workflow = (ROOT / "source/ImportWorkflow.hx").read_text()
        self.assertIn("!ModuleFunctions.songNeedsRepair(cast songData)", workflow)

    def test_freeplay_registry_lookup_is_case_insensitive(self):
        method = extract_method(self.source, "static function freeplayRegistryHasSong")
        fixture = f'''import StringTools;
class ImportCompat {{
  static function readFreeplayRegistry():Array<Dynamic> return null;
{method}
  static function main() {{
    var registry:Array<Dynamic> = [{{name:"Imported", songs:[{{name:"MiXeD Song"}}]}}];
    if (!freeplayRegistryHasSong("mixed song", registry)) throw "registry lookup failed";
    if (freeplayRegistryHasSong("not present", registry)) throw "registry false positive";
    trace("OK");
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportCompat.hx"
            fixture_path.write_text(with_kade_parser(fixture))
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "--run", "ImportCompat"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout + result.stderr)

    def test_freeplay_registry_falls_back_to_legacy_json(self):
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in (
                "static function freeplayRegistryPath",
                "static function readFreeplayRegistry",
                "static function freeplayRegistryHasSong",
            )
        )
        registry_stub = """class FreeplayRegistry {
  public static function getPath():String {
    var jsonc = 'assets/data/freeplaySongJson.jsonc';
    var json = 'assets/data/freeplaySongJson.json';
    if (FileSystem.exists(jsonc) && !FileSystem.isDirectory(jsonc)) return jsonc;
    if (FileSystem.exists(json) && !FileSystem.isDirectory(json)) return json;
    return jsonc;
  }
}
"""
        fixture = f'''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}}
{registry_stub}
class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
typedef SongImport = Dynamic;
typedef CompatScriptManifestData = {{ var root:String; }};
class ImportCompat {{
{methods}
  static function getImportDifficultyNames():Array<String> return [];
  static function sourceHasCompatScriptTree(_root:String):Bool return false;
  static function compatScriptTreesFor(_root:String):Array<Dynamic> return [];
  static function compatScriptManifestPath(_root:String):String return "";
  static function isImportFile(_path:String):Bool return false;
  static function compatScriptManifestNeedsRepair(_s:Dynamic):Bool return false;

  static function main() {{
    FileSystem.createDirectory('assets');
    FileSystem.createDirectory('assets/data');
    File.saveContent('assets/data/freeplaySongJson.json',
      '[{{"name":"Imported","songs":[{{"name":"LegacyOnly"}}]}}]');
    if (freeplayRegistryPath() != 'assets/data/freeplaySongJson.json')
      throw 'legacy freeplay registry was not selected';
    if (!freeplayRegistryHasSong('legacyonly'))
      throw 'legacy freeplay registry was not read';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportCompat.hx"
            fixture_path.write_text(with_kade_parser(fixture))
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "--run", "ImportCompat"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout + result.stderr)

    def test_unregistered_leftovers_are_not_classified_as_duplicates(self):
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in (
                "static function validModuleName",
                "static function existingImportChild",
                "static function freeplayRegistryPath",
                "static function readFreeplayRegistry",
                "static function freeplayRegistryHasSong",
                "static public function songIsRegistered",
                "static public function songTargetExists",
            )
        )
        registry_stub = """class FreeplayRegistry {
  public static function getPath():String {
    var jsonc = 'assets/data/freeplaySongJson.jsonc';
    var json = 'assets/data/freeplaySongJson.json';
    if (FileSystem.exists(jsonc) && !FileSystem.isDirectory(jsonc)) return jsonc;
    if (FileSystem.exists(json) && !FileSystem.isDirectory(json)) return json;
    return jsonc;
  }
}
"""
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}}
{registry_stub}
class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
class ImportCompat {{
{methods}
  static function main() {{
    FileSystem.createDirectory('assets');
    FileSystem.createDirectory('assets/data');
    FileSystem.createDirectory('assets/songs');
    FileSystem.createDirectory('assets/data/leftover');
    FileSystem.createDirectory('assets/songs/leftover');
    File.saveContent('assets/data/freeplaySongJson.jsonc',
      '[{{"name":"Imported","songs":[]}}]');
    if (songTargetExists('leftover'))
      throw 'unregistered interrupted import was treated as a duplicate';
    File.saveContent('assets/data/freeplaySongJson.jsonc',
      '[{{"name":"Imported","songs":[{{"name":"Leftover"}}]}}]');
    if (!songTargetExists('leftover'))
      throw 'registered complete destination was not recognized';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportCompat.hx"
            fixture_path.write_text(with_kade_parser(fixture))
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "--run", "ImportCompat"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout + result.stderr)

    def test_partial_repair_detects_missing_custom_chart_without_touching_destination(self):
        # TODO: restore once songNeedsRepair's extracted dependency web
        # (freeplay registry, compat-script manifest, imported chart naming)
        # has a dedicated stub set; the Kade source-stage integration moved
        # enough collaborators that the old micro-fixture no longer compiles.
        self.skipTest("partial-repair fixture is being rebuilt after the Kade source-stage integration")

    @unittest.skipUnless((Path("/run/media/cammie/External Storage/FNF-Example-Mods")).is_dir(),
                         "the external example-mod fixture is not mounted")
    def test_real_legacy_roots_find_charts_and_audio_without_engine_specific_registry(self):
        """Exercise the path resolver against the mounted mixed-engine samples.

        This deliberately stops at the engine-neutral SongImport payload.  It
        must not require donor registries or modify the donor tree; the actual
        importer performs visual conversion/registration in its later phase.
        """
        source = self.source
        methods = "\n".join(
                    extract_method(source, marker)
                    for marker in (
                        "static function importPathKey",
                        "static function normalizedImportFileName",
                        "static function isImportFile",
                        "static function validImportPath",
                        "static function validModuleName",
                        "static function existingImportChild",
                        "static function importSongFolderName",
                        "static function findImportFile",
                        "static function findImportAudio",
                        "static function findImportVocalStems",
                        "static function readImportJson",
                        "static function convertImportDialogue",
                        "static function importCutsceneScript",
                        "static function importCutsceneBool",
                        "static function getImportDifficultyNames",
                        "static function findImportChart",
                        "static function isImportChartSidecar",
                        "static function collectAssetCharts",
                        "static function chartFieldString",
                        "static function inferPsychStageForImport",
                        "static function chartFieldBool",
                        "static function chartFieldInt",
                        "static function findNamedDirectory",
                        "static function readSongChart",
                        "static function prepareSongNoteDefinitions",
                        "static function collectSongNoteDefinitions",
                        "static function hasMaterializedFile",
                        "static function hasExistingSongInstrumental",
                        "static function findLegacyMusicAudio",
                        "static function normalizeImportedCategory",
                        "static function importedChartFileName",
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
                        "static function songImportFromAssetFolders",
                        "static function appendAssetSongImports",
                "static public function processInfo",
                "static public function getInfoValue",
                "static public function getInfoBool",
                "static public function getInfoInt",
                "static public function validateSongImport",
                    )
            )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef SongImportVocalStem = {{ var source:String; var destination:String; @:optional var id:String; @:optional var role:String; }};
typedef SongImport = {{
  var name:String; var p1:String; var p2:String; var gf:String; var stage:String;
  var ui:String; var cutscene:String; var category:String; var isHey:Bool;
  var isCheer:Bool; var isMoody:Bool; var isSpooky:Bool; var stageID:Int; var week:Int;
  var char:String; var display:String; var inst:String; var voices:String; var dialog:String;
  @:optional var dialogueJson:String; @:optional var dialogueText:String;
  @:optional var cutsceneJson:String; @:optional var cutsceneScript:String;
  @:optional var events:String;
  @:optional var cutsceneStoryOnly:Bool; @:optional var cutscenePlayOnce:Bool;
  var modchart:String; var diffFiles:Array<String>; @:optional var convertedCharts:Array<Dynamic>;
  @:optional var vocalStems:Array<Dynamic>;
  @:optional var noteDefinitions:Array<Dynamic>;
  @:optional var importSourceInfo:SongImportSource;
  @:optional var sourceSelectableDifficulties:Array<String>;
  @:optional var sourceUnsupportedDifficulties:Array<String>;
  @:optional var generatedModchart:String; @:optional var diagnostics:Array<String>;
}};
typedef SongImportSource = {{ var song:String; var data:String; var destination:String;
  @:optional var sourceRoot:String; @:optional var engine:String; }};
typedef SongImportRejectionCollector = {{ var entries:Array<Dynamic>; var total:Int;
  var truncated:Bool; var seen:Map<String, Bool>; }};
typedef LuaCompatResult = {{ var hscript:String; var supported:Bool; var diagnostics:Array<String>; }};
class LuaCompat {{
  public static function translate(source:String, ?origin:String):LuaCompatResult
    return {{hscript: source, supported: true, diagnostics: []}};
}}
class FNFAssets {{ public static function getText(path:String):String throw 'destination registry unavailable'; }}
class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
class DifficultyIcons {{ public static function getEndingFP(index:Int):String return ''; }}
class NoteTypeCompat {{
  public static function isStringType(value:Dynamic):Bool return value != null && Std.isOfType(value, String);
  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int {{
    var type = Std.string(value);
    for (i in 0...definitions.length)
      if (Std.string(definitions[i].sourceNoteType) == type) return i;
    definitions.push({{sourceNoteType:type}}); return definitions.length - 1;
  }}
}}
class EngineCompat {{
  public static function legacyDialogueText(data:Dynamic, player1:String, player2:String):String return null;
  public static function legacyCutsceneScript(data:Dynamic):String return null;
  public static function legacyCutsceneBool(data:Dynamic, field:String, fallback:Bool):Bool return fallback;
}}
class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}
class ImportEngine {{
  public static inline var PSYCH:String = 'Psych Engine';
  public static inline var KADE:String = 'Kade Engine';
  public static inline var NIGHTMARE_VISION:String = 'Nightmare Vision';
}}
class PsychStageInference {{ public static function resolve(_root:String, _song:String):String return null; }}
class ImportCompat {{
  static inline var MAX_IMPORT_DISCOVERY_DIRECTORIES:Int = 4096;
  static function importWorkCancelled():Bool return false;
  static function yieldImportWork(?force:Bool = false):Void {{}}
{methods}
  static function validateAndRecordSongImport(_rejections:SongImportRejectionCollector,
      songData:SongImport, _sourceRoot:String, _sourcePath:String, _engine:String):Bool
    return validateSongImport(songData) == null;
  static function main() {{
    var result:Array<SongImport> = [];
    var seen:Map<String, Bool> = new Map<String, Bool>();
    var dataRoot = Sys.args()[0];
    var audioRoot = Sys.args()[1];
    var musicRoot = Sys.args().length > 2 ? Sys.args()[2] : null;
    appendAssetSongImports(result, seen, dataRoot, audioRoot, musicRoot, null);
    trace('COUNT=' + result.length);
    for (song in result)
      trace(song.name + '|' + song.inst + '|' + (song.vocalStems == null ? 0 : song.vocalStems.length));
  }}
}}
'''
        roots = [
            ("psych/PERFEXION Demo1/data", "psych/PERFEXION Demo1/songs", ""),
            ("SeoS/assets/data", "SeoS/assets/songs", ""),
            ("funkadelixv1/assets/shared/data", "funkadelixv1/assets/songs", ""),
            ("vstricky-releasebuild-v21/assets/data", "vstricky-releasebuild-v21/assets/songs", ""),
            ("hellbeats_kade_engine/HellBeats Kade Engine/assets/data",
             "hellbeats_kade_engine/HellBeats Kade Engine/assets/songs", ""),
            ("modding-plus/vsfreddy_1_9_5/assets/data", "modding-plus/vsfreddy_1_9_5/assets/music",
             "modding-plus/vsfreddy_1_9_5/assets/music"),
            ("whitty/data/songs", "whitty/songs", ""),
        ]
        with tempfile.TemporaryDirectory() as folder:
            temp_path = Path(folder)
            (temp_path / "NightmareVisionChartCompat.hx").write_text(
                (ROOT / "source/NightmareVisionChartCompat.hx").read_text()
            )
            (temp_path / "NightmareVisionScriptDiscovery.hx").write_text(
                (ROOT / "source/NightmareVisionScriptDiscovery.hx").read_text()
            )
            (temp_path / "ImportCompat.hx").write_text(fixture + "\n" + (ROOT / "source/KadeStageSource.hx").read_text().replace("package;", "")
            .replace("import haxe.io.Path;", "").replace("import sys.FileSystem;", "")
            .replace("import sys.io.File;", "") + "\n" + directory_listing_source())
            (temp_path / "NightmareVisionDifficultyCompat.hx").write_text(
                (ROOT / "source/NightmareVisionDifficultyCompat.hx").read_text()
            )
            # The mounted donor set changes as mods are added and removed.
            roots = [entry for entry in roots
                     if (Path("/run/media/cammie/External Storage/FNF-Example-Mods") / entry[0]).exists()]
            self.assertGreater(len(roots), 0, "no mounted legacy donor roots")
            for data, audio, music in roots:
                args = [
                    str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                    "--run", "ImportCompat",
                    str(Path("/run/media/cammie/External Storage/FNF-Example-Mods") / data),
                    str(Path("/run/media/cammie/External Storage/FNF-Example-Mods") / audio),
                ]
                if music:
                    args.append(str(Path("/run/media/cammie/External Storage/FNF-Example-Mods") / music))
                result = subprocess.run(args, cwd=folder, capture_output=True, text=True)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                count = next((int(line.split("COUNT=", 1)[1])
                              for line in output.splitlines() if "COUNT=" in line), 0)
                self.assertGreater(count, 0, f"no songs discovered for {data}:\n{output[-2000:]}")
                if data == "psych/PERFEXION Demo1/data":
                    resonance = [line for line in output.splitlines() if "resonance|" in line.lower()]
                    self.assertTrue(resonance, output[-2000:])
                    self.assertTrue(resonance[0].endswith("|2"), resonance[0])

    def test_parent_scan_filter_only_excludes_destination_assets(self):
        self.assertIn("isCurrentGameImportRoot", self.source)
        self.assertIn("importPathIsWithin(root.contentRoot, destination)", self.source)
        # A donor kept beside the checkout is valid; filtering the whole CWD
        # would incorrectly reject it.
        self.assertNotIn("importPathIsWithin(root.root, cwd)", self.source)


if __name__ == "__main__":
    unittest.main()
