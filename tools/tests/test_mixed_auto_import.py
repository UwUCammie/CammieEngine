"""End-to-end Auto discovery coverage for a mixed engine parent folder.

The fixture deliberately combines the six layouts supported by the importer.
It stops at the engine-neutral SongImport payload: no donor chart is edited and
the destination writer is covered by the existing non-overwrite tests.
"""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import shutil
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]


def with_kade_parser(fixture: str) -> str:
    """Embed the KadeStageSource parser into a generated fixture: its import
    lines merge at the top of the file, its class lands at the end."""
    parser = (ROOT / "source/KadeStageSource.hx").read_text().replace("package;", "")
    cut = parser.index("\nclass ")
    fixture = parser[:cut] + fixture + parser[cut:]
    stage_parser = (ROOT / "source/PsychStageInference.hx").read_text().replace("package;", "", 1)
    stage_parser = stage_parser.replace("import haxe.io.Path;\n", "")
    stage_parser = stage_parser.replace("#if sys\nimport sys.FileSystem;\nimport sys.io.File;\n#end\n", "")
    stage_parser = stage_parser.replace("using StringTools;\n", "")
    cut = fixture.index("\nclass Main {")
    return fixture[:cut] + "\n\n" + stage_parser.strip() + fixture[cut:]
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
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class MixedAutoImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = (ROOT / "source/ModuleFunctions.hx").read_text()
        cls.engine = (ROOT / "source/ImportEngine.hx").read_text()
        cls.scanner = (ROOT / "source/ImportRootScanner.hx").read_text()
        cls.vslice = (ROOT / "source/VSliceImporter.hx").read_text()
        cls.astc = (ROOT / "source/VSliceAstcAdapter.hx").read_text()

    def test_auto_discovers_all_six_engine_layouts_and_produces_importable_songs(self):
        methods = "\n".join(
            extract_method(self.module, marker)
            for marker in (
                "static function importPathKey",
                "static function normalizedImportFileName",
                "static function isImportFile",
                "static function validImportPath",
                "static function validModuleName",
                "static function findImportFile",
                "static function findImportAudio",
                "static function findImportVocalStems",
                "static function normalizeNightmareVisionVocalRoles",
                "static function vocalStemMetadataMatches",
                "static function updateChartVocalStemMetadata",
                "static function readImportJson",
                "static function convertImportDialogue",
                "static function importCutsceneScript",
                "static function importCutsceneBool",
                "static function getImportDifficultyNames",
                "static function findImportChart",
                "static function importChartNames",
                "static function findImportChartInEntries",
                "static function isImportChartSidecar",
                "static function collectAssetCharts",
                "static function chartFieldString",
                "static function chartFieldBool",
                "static function chartFieldInt",
                "static function findNamedDirectory",
                "static function readSongChart",
                "static function prepareInstalledDependencyRoots",
                "static function prepareSongNoteDefinitions",
                "static function collectSongNoteDefinitions",
                "static function normalizeImportedCategory",
                "static public function processInfo",
                "static public function getInfoValue",
                "static public function getInfoBool",
                "static public function getInfoInt",
                "static function inferPsychStageForImport",
                "static function songImportFromRoots",
    "static function applyKadeSourceStageCompatibility",
                "static function applyKadeSourceCharacterCompatibility",
                "static function prepareKadeSourceCharacter",
                "static function generateKadeCharacterHScript",
                "static function nativeCharacterComplete",
                "static function placedActorPoint",
                "static function injectAfterActorPlacement",
                "static function findLegacyMusicAudio",
                "static function songImportFromAssetFolders",
                "static function songImportValidationCode",
                "static function recordSongImportValidationRejection",
                "static function validateAndRecordSongImport",
                "static function appendAssetSongImports",
                "static function canonicalNightmareVisionPackageRoot",
                "static function retainNightmareVisionPackageNamespace",
                "static function findVSliceFile",
                "static function findVSliceFreeplayIcon",
    "static function findVSliceVideo",
                "static function findVSliceNoteStyle",
                "static function findVSliceVoices",
                "static function removeVSliceDiagnosticCode",
                "static function appendVSliceDiagnostic",
                "static function appendVSliceDiagnostics",
                "static function vSliceDefinitionFolders",
                "static function vSliceDefinitionStem",
                "static function findVSliceDefinition",
                "static function readVSliceDefinition",
                "static function appendVSliceFolderAssetDiagnostics",
                "static function appendVSliceScriptDiagnostics",
                "static function appendUniqueScriptDiagnostic",
                "static function collectVSliceScriptDiagnostics",
                "static function vSliceNativeCharacterName",
                "static function vSliceNativeCharacterReference",
                "static function findVSliceSongPairs",
                "static function safeVSliceVariationSuffix",
                "static function findVSliceVariationFile",
                "static function findVSliceInstrumental",
                "static function normalizeVSliceVariationDifficulty",
                "static function vSliceStemMatchesReference",
                "static function selectVSliceVocalStems",
                "static function discoverVSliceSongImports",
                "static function discoverLegacySongImportsFromRoot",
                "static function importSongFolderName",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function vSliceMappingDestination",
                "static function mergeVSliceMapping",
                "static function chooseVSliceRegistry",
                "static function registryHasVSliceKey",
                "static function mergeVSliceRegistryEntry",
                "static function importVSliceNoteStyleConversion",
                "static function copyIfPresent",
                "static function copyRequired",
                "static function hasMaterializedFile",
                "static function hasExistingSongInstrumental",
                "static function requireChartMaterialized",
                "public static function importedCameraZoomMode",
                "static function applyImportedSidecars",
                "static function applyImportedVisualMetadata",
                "static function prepareImportedSongIdentity",
                "static function writeGeneratedDialogue",
	                "static function importedChartFileName",
	                "static function freeplayRegistryPath",
	                "static function readFreeplayRegistry",
                "static function freeplayRegistryHasSong",
                "static public function importSong(songData:SongImport)",
                "static public function validateSongImport",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef VSliceCharacterImport = {{
  var reference:String; var source:String; var conversion:VSliceImporter.VSliceCharacterConversion;
}};
typedef VSliceStageImport = {{
  var reference:String; var source:String; var conversion:VSliceImporter.VSliceStageConversion;
}};
typedef VSliceNoteStyleImport = {{
  var reference:String; var source:String; var conversion:VSliceImporter.VSliceNoteStyleConversion;
}};
typedef ConvertedSongChart = {{
  var difficulty:String; var fileName:String; var source:String; var chart:Dynamic;
  @:optional var noteTypes:Array<Dynamic>;
  @:optional var sourceDifficulty:String;
  @:optional var cameraLines:Array<Dynamic>;
  @:optional var authoredSongTitle:Bool;
}};
typedef SongImportVocalStem = {{
  var source:String; var destination:String; @:optional var id:String; @:optional var role:String;
}};
typedef SongImport = {{
  var name:String; var p1:String; var p2:String; var gf:String; var stage:String;
  var ui:String; var cutscene:String; var category:String; var isHey:Bool;
  var isCheer:Bool; var isMoody:Bool; var isSpooky:Bool; var stageID:Int; var week:Int;
  var char:String; var display:String; var inst:String; var voices:String; var dialog:String;
  @:optional var vocalStems:Array<SongImportVocalStem>;
  @:optional var dialogueJson:String; @:optional var dialogueText:String;
  @:optional var cutsceneJson:String; @:optional var cutsceneScript:String;
  @:optional var events:String;
  @:optional var cutsceneStoryOnly:Bool; @:optional var cutscenePlayOnce:Bool;
  var modchart:String; var diffFiles:Array<String>;
  @:optional var convertedCharts:Array<ConvertedSongChart>;
  @:optional var noteDefinitions:Array<Dynamic>;
  @:optional var convertedCharacters:Array<VSliceCharacterImport>;
  @:optional var freeplayIconSource:String;
  @:optional var convertedStage:VSliceStageImport;
  @:optional var convertedNoteStyle:VSliceNoteStyleImport;
  @:optional var convertedNoteStyles:Array<VSliceNoteStyleImport>;
  @:optional var vSliceRoot:String; @:optional var engine:String; @:optional var sourceRoot:String;
  @:optional var codenameEngineBaseAssetRoot:String;
  @:optional var codenameDefaultCharacter:String;
  @:optional var importSourceInfo:SongImportSource;
  @:optional var diagnostics:Array<String>;
  @:optional var generatedModchart:String;
  @:optional var sourceSelectableDifficulties:Array<String>;
  @:optional var sourceUnsupportedDifficulties:Array<String>;
}};
typedef SongImportSource = {{ var song:String; var data:String; var destination:String;
  @:optional var sourceRoot:String; @:optional var engine:String; }};
typedef SongImportDiscoveryRejection = {{
  var code:String; var song:String; var engine:String; var sourceRoot:String;
  var sourcePath:String; var reason:String; var charts:Array<String>;
  var chartsTruncated:Bool;
}};
typedef SongImportRejectionCollector = {{
  var entries:Array<SongImportDiscoveryRejection>; var total:Int;
  var truncated:Bool; var seen:Map<String, Bool>;
}};
typedef ImportAssetMergeResult = {{
  var copied:Int; var skipped:Int; var failed:Int; @:optional var errors:Array<String>;
}};

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    var result = StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/');
    return Path.normalize(result);
  }}
  public static function getImportRoot(?kind:String):String return 'assets/module/import';
}}
class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}}
class FreeplayRegistry {{
  public static function getPath():String {{
    var jsonc = 'assets/data/freeplaySongJson.jsonc';
    var json = 'assets/data/freeplaySongJson.json';
    if (FileSystem.exists(jsonc) && !FileSystem.isDirectory(jsonc)) return jsonc;
    if (FileSystem.exists(json) && !FileSystem.isDirectory(json)) return json;
    return jsonc;
  }}
  public static function getPathInRoot(root:String):String return Path.join([root, 'data/freeplaySongJson.jsonc']);
}}
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}
class ImportPackageFamilyCatalog {{
  public static function isAuthenticatedNightmareVisionContainer(path:String):Bool {{
    var root = ImportRootScanner.inspectRoot(path, ImportEngine.AUTO);
    if (root == null || root.engine != ImportEngine.NIGHTMARE_VISION || root.evidence == null)
      return false;
    for (item in root.evidence)
      if (StringTools.startsWith(item, 'Nightmare Vision executable package marker:')
          || StringTools.startsWith(item, 'Nightmare Vision Haxe project package:')
          || StringTools.startsWith(item, 'Nightmare Vision chart metadata: format=nmv2'))
        return true;
    return false;
  }}
}}
class ModuleFunctions {{
  static inline var MAX_SONG_IMPORT_REJECTIONS:Int = 64;
  static inline var MAX_SONG_IMPORT_REJECTION_CHARTS:Int = 8;
  static inline var MAX_IMPORT_DISCOVERY_DIRECTORIES:Int = 4096;
  static var importBackgroundMode:Bool = false;
  static function importWorkCancelled():Bool return false;
  static function yieldImportWork(?force:Bool = false):Void {{}}
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0,
    copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
  static function songTargetExists(songName:String, ?sourceFolder:String):Bool return false;
  static function songNeedsRepair(songData:SongImport):Bool return false;
  static function importPathIsWithin(path:String, root:String):Bool {{
    var a = importPathKey(path); var b = importPathKey(root);
    return a == b || (b != '' && a.startsWith(b + '/'));
  }}
{methods}
  public static function commitCustomStyle(importData:VSliceNoteStyleImport, result:ImportAssetMergeResult):Void
    importVSliceNoteStyleConversion(importData, result);
  public static function commitOneStyleMapping(mapping:VSliceImporter.VSliceAssetMapping, base:String, result:ImportAssetMergeResult):Void
    mergeVSliceMapping(mapping, base, result);
  public static function discoverRoot(root:ImportRootScanner.ImportRoot):Array<SongImport> {{
    return root.engine == ImportEngine.V_SLICE
      ? discoverVSliceSongImports(root)
      : discoverLegacySongImportsFromRoot(root);
  }}
}}

class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var roots = ImportRootScanner.scan(Sys.args()[0], ImportEngine.AUTO);
    if (roots.length != 6) fail('expected six roots, got ' + roots.length);
    var seenEngines:Map<String, Bool> = new Map<String, Bool>();
    FileSystem.createDirectory('assets');
    FileSystem.createDirectory('assets/data');
    FileSystem.createDirectory('assets/songs');
    File.saveContent('assets/data/baseSongKeys.json', '[]');
    File.saveContent('assets/data/freeplaySongJson.jsonc', '[{{"name":"Imported","songs":[]}}]');
    // A previous attempt may have left this destination behind.  Import must
    // register it without replacing the existing chart/audio bytes.
    FileSystem.createDirectory('assets/data/kade-song');
    FileSystem.createDirectory('assets/songs/kade-song');
    // Existing destination bytes are retained, but they still need to be a
    // readable chart: the importer now validates every required chart before
    // exposing the song through the freeplay registry.
    File.saveContent('assets/data/kade-song/kade-song.json',
      '{{"song":{{"song":"kade-song","player1":"bf","player2":"dad","notes":[]}}}}');
    File.saveContent('assets/songs/kade-song/Inst.ogg', 'existing-audio');
    var songs = 0;
    for (root in roots) {{
      seenEngines.set(root.engine, true);
      var found = ModuleFunctions.discoverRoot(root);
      var expectedFound = root.engine == ImportEngine.V_SLICE ? 2 : 1;
      if (found.length != expectedFound) fail(root.engine + ' discovered ' + found.length + ' songs');
      var song = found[0];
      if (song.inst == null || !FileSystem.exists(song.inst)) fail(root.engine + ' has no Inst audio');
      if (song.diffFiles == null || song.diffFiles.length == 0) fail(root.engine + ' has no source chart');
      if (song.convertedCharts != null && song.convertedCharts.length == 0) fail(root.engine + ' has no converted chart');
      if (song.name.toLowerCase() == 'kade-song')
        File.saveContent('assets/data/kade-song/compatScripts.json', CompatScriptManifest.stringify(
          CompatScriptManifest.create(song.sourceRoot, song.engine)));
      if (!ModuleFunctions.importSong(song)) fail(root.engine + ' failed to import ' + song.name);
      var target = song.name.toLowerCase();
      if (!FileSystem.exists(Path.join(['assets', 'data', target, target + '.json'])))
        fail(root.engine + ' did not write a native chart');
      if (!FileSystem.exists(Path.join(['assets', 'songs', target, 'Inst.ogg'])))
        fail(root.engine + ' did not copy Inst audio');
      if (target == 'vslice-song') {{
        if (song.convertedNoteStyle == null)
          fail('V-Slice custom note style was not discovered');
        for (converted in (cast song.convertedCharts:Array<Dynamic>))
          if (converted.chart.song.uiType != 'vslice-teststyle')
            fail('V-Slice difficulty did not receive generated UI type');
        var styleMerge:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0}};
        var oneMerge:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0}};
        ModuleFunctions.commitOneStyleMapping(song.convertedNoteStyle.conversion.assets[0],
          'assets/images/custom_ui/ui_packs/vslice-teststyle', oneMerge);
        ModuleFunctions.commitCustomStyle(song.convertedNoteStyle, styleMerge);
        if (styleMerge.failed != 0 || styleMerge.copied == 0)
          fail('V-Slice custom UI pack was not materialized');
        var styleFolder = 'assets/images/custom_ui/ui_packs/vslice-teststyle';
        if (!FileSystem.exists(Path.join([styleFolder, 'NOTE_assets.png']))
          || !FileSystem.exists(Path.join([styleFolder, 'strumline.xml']))
          || !FileSystem.exists(Path.join([styleFolder, 'holdCoverLeft.png']))
          || !FileSystem.exists(Path.join([styleFolder, 'holdCoverRight.xml']))
          || !FileSystem.exists(Path.join([styleFolder, 'multiNotePresets.json'])))
          fail('V-Slice generated UI files are incomplete: ' + FileSystem.readDirectory(styleFolder).join('|'));
        var uiRegistry:Dynamic = Json.parse(File.getContent('assets/images/custom_ui/ui_packs/ui.json'));
        if (Reflect.field(uiRegistry, 'vslice-teststyle') == null)
          fail('V-Slice generated UI registry entry missing');
        if (Reflect.field(Reflect.field(uiRegistry, 'vslice-teststyle'), 'holdCoverEnabled') != true)
          fail('V-Slice generated hold-cover registry entry missing');
        var imported:Dynamic = Json.parse(File.getContent(Path.join(['assets', 'data', target, target + '.json']))).song;
        if (imported.needsVoices != true) fail('V-Slice split stems did not enable voices');
        var stems:Array<Dynamic> = cast imported.vocalStems;
        if (stems == null || stems.length != 3) fail('V-Slice stem metadata count');
        var destinations:Array<String> = [];
        for (stem in stems) {{
          var destination = Std.string(stem.file);
          destinations.push(destination);
          if (!FileSystem.exists(Path.join(['assets', 'songs', target, destination])))
            fail('missing copied V-Slice stem ' + destination);
        }}
        if (destinations.join('|') != 'Voices-ada.mp3|Voices-zed.ogg|Voices-bf.wav')
          fail('V-Slice stem destinations were not deterministic: ' + destinations.join('|'));
        if (FileSystem.exists(Path.join(['assets', 'songs', target, 'Voices.ogg'])))
          fail('split V-Slice import created an ambiguous Voices.ogg alias');
        var donorMetadata = File.getContent(Path.join([song.vSliceRoot, 'data', 'songs', 'vslice-song', 'vslice-song-metadata.json']));
        if (donorMetadata.indexOf('vocalStems') >= 0)
          fail('donor V-Slice metadata was modified');
      }}
      if (target == 'kade-song') {{
        if (File.getContent('assets/data/kade-song/kade-song.json')
            != '{{"song":{{"song":"kade-song","player1":"bf","player2":"dad","notes":[]}}}}'
            || File.getContent('assets/songs/kade-song/Inst.ogg') != 'existing-audio')
          fail('existing Kade destination bytes were overwritten');
      }}
      songs++;
      trace(root.engine + '|' + song.name);
      if (root.engine == ImportEngine.V_SLICE) {{
        var variant = found[1];
        var variantTarget = variant.name.toLowerCase();
        if (variantTarget != 'vslice-song-alt' || Reflect.field(variant, 'destinationFolder') != variantTarget)
          fail('V-Slice variation did not receive a unique native song key');
        if (variant.display != 'VSlice Alt Display' || variant.inst == null
          || File.getContent(variant.inst) != 'alt-inst')
          fail('V-Slice variation display/instrumental did not follow its metadata');
        if (variant.convertedCharts.length != 1 || variant.convertedCharts[0].difficulty != 'normal'
          || variant.convertedCharts[0].sourceDifficulty != 'alt'
          || variant.convertedCharts[0].fileName != variantTarget + '.json')
          fail('V-Slice singleton variation difficulty was not mapped into a selectable native chart slot');
        var plannedVariant = variant.convertedCharts[0].chart.song;
        if (plannedVariant.player1 != 'dad' || plannedVariant.player2 != 'bf'
          || plannedVariant.stage != 'mall' || plannedVariant.uiType != 'pixel')
          fail('V-Slice variation chart lost its characters, stage, or UI');
        if (plannedVariant.events.length != 1 || plannedVariant.events[0][0] != 700)
          fail('V-Slice variation chart lost its own events');
        var plannedStems:Array<Dynamic> = cast plannedVariant.vocalStems;
        if (plannedStems == null || plannedStems.length != 2
          || plannedStems[0].id != 'alt-opponent' || plannedStems[1].id != 'alt-player')
          fail('V-Slice variation selected unrelated vocal stems');
        if (!ModuleFunctions.importSong(variant)) fail('V-Slice variation import failed');
        var variantChartPath = Path.join(['assets', 'data', variantTarget, variantTarget + '.json']);
        if (!FileSystem.exists(variantChartPath)) fail('V-Slice variation chart was not written');
        var writtenVariant:Dynamic = Json.parse(File.getContent(variantChartPath)).song;
        if (writtenVariant.song != variantTarget || writtenVariant.notes[0].sectionNotes[0][0] != 600)
          fail('written variation chart does not contain its authored identity/notes');
        if (writtenVariant.vocalStems.length != 2
          || writtenVariant.vocalStems[0].id != 'alt-opponent'
          || writtenVariant.vocalStems[1].id != 'alt-player')
          fail('written variation chart has the wrong vocal stem selection');
        if (File.getContent(Path.join(['assets', 'songs', variantTarget, 'Inst.ogg'])) != 'alt-inst')
          fail('variation instrumental was not copied to its song folder');
        for (stem in plannedStems)
          if (!FileSystem.exists(Path.join(['assets', 'songs', variantTarget, Std.string(stem.file)])))
            fail('variation vocal stem was not copied: ' + stem.file);
        songs++;
        trace(root.engine + '|' + variant.name);
      }}
    }}
    for (engine in [ImportEngine.PSYCH, ImportEngine.V_SLICE, ImportEngine.KADE,
      ImportEngine.FPS_PLUS, ImportEngine.MODDING_PLUS, ImportEngine.LEGACY_POLYMOD])
      if (!seenEngines.exists(engine)) fail('missing engine ' + engine);
    if (songs != 7) fail('expected seven importable songs');
    var registry:Array<Dynamic> = cast Json.parse(File.getContent('assets/data/freeplaySongJson.jsonc'));
    var registered = 0;
    for (category in registry)
      for (entry in (cast category.songs:Array<Dynamic>))
        registered++;
    if (registered != 7) fail('expected seven registered songs, got ' + registered);
    var visible = 0;
    for (_ in DifficultyManager.supportedDiff.keys()) visible++;
    if (visible != 7)
      fail('expected seven visible songs, got ' + visible);
    trace('SONGS=' + songs);
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp_path = Path(folder)
            install_import_io_dependencies(temp_path)
            for dependency in ("ImportSongOwnership.hx", "CompatScriptManifest.hx",
                               "ImportInstalledDependencyRoots.hx", "CompatCanonicalPath.hx"):
                (temp_path / dependency).write_text((ROOT / "source" / dependency).read_text(), newline='\n')
            (temp_path / "NightmareVisionVocalRole.hx").write_text(
                (ROOT / "source/NightmareVisionVocalRole.hx").read_text(), newline='\n'
            )
            (temp_path / "NightmareVisionChartCompat.hx").write_text(
                (ROOT / "source/NightmareVisionChartCompat.hx").read_text()
            , newline='\n')
            (temp_path / "NightmareVisionScriptDiscovery.hx").write_text(
                (ROOT / "source/NightmareVisionScriptDiscovery.hx").read_text()
            , newline='\n')
            (temp_path / "NightmareVisionDifficultyCompat.hx").write_text(
                (ROOT / "source/NightmareVisionDifficultyCompat.hx").read_text()
            , newline='\n')
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            (temp_path / "ImportRootScanner.hx").write_text(self.scanner, newline='\n')
            (temp_path / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            (temp_path / "PsychSongNameCompat.hx").write_text(
                (ROOT / "source/PsychSongNameCompat.hx").read_text()
            , newline='\n')
            (temp_path / "VSliceAstcAdapter.hx").write_text(self.astc, newline='\n')
            (temp_path / "VSliceImporter.hx").write_text(self.vslice, newline='\n')
            (temp_path / "HxcScriptIdentity.hx").write_text(
                (ROOT / "source/HxcScriptIdentity.hx").read_text()
            , newline='\n')
            (temp_path / "HxcScriptDiscovery.hx").write_text(
                (ROOT / "source/HxcScriptDiscovery.hx").read_text()
            , newline='\n')
            # VSliceImporter bounds Codename character definitions through this
            # shared helper. The fixture exercises its filesystem boundary but
            # otherwise keeps the discovery implementation out of this extract.
            (temp_path / "CodenameScriptDiscovery.hx").write_text("""import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class CodenameScriptDiscovery {
  public static function withinRoot(root:String, path:String):Bool {
    if (root == null || path == null || !FileSystem.exists(root) || !FileSystem.exists(path))
      return false;
    try {
      var base = Path.normalize(FileSystem.fullPath(root));
      var candidate = Path.normalize(FileSystem.fullPath(path));
      return candidate.startsWith(base + '/');
    } catch (_:Dynamic) {
      return false;
    }
  }
}
""", newline='\n')
            (temp_path / "NoteTypeCompat.hx").write_text("""class NoteTypeCompat {
  public static function isStringType(value:Dynamic):Bool return value != null && Std.isOfType(value, String);
  public static function applyVSliceKind(definition:Dynamic, value:Dynamic):Bool return false;
  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int {
    var type = Std.string(value);
    for (i in 0...definitions.length)
      if (Std.string(definitions[i].sourceNoteType) == type) return i;
    definitions.push({sourceNoteType:type}); return definitions.length - 1;
  }
}
""", newline='\n')
            (temp_path / "EngineCompat.hx").write_text("""class EngineCompat {
  public static function eventName(name:Dynamic):String {
    if (name == null) return "";
    var original = StringTools.trim(Std.string(name));
    switch (original.toLowerCase()) {
      case 'changecharacter' | 'change character cl' | 'charchange': return 'Change Character';
      case 'focuscamera' | 'focus camera': return 'Focus Camera';
      default: return original;
    }
  }
  public static function scriptFunctionNames(contents:String):Array<String> return [];
  public static function knownScriptFunction(name:String):Bool return false;
  public static function unknownScriptFunctions(contents:String):Array<String> return [];
  public static function routeVSliceEvent(name:String, values:Dynamic):Dynamic return null;
  public static function vSliceNativeCharacterCandidates(path:String):Array<String> return [];
  public static function resolveStageResolution(reference:String):Dynamic return {nativeName: reference, stageID: 0, standard: false};
  public static function isBuiltinStageReference(reference:String):Bool return false;
  public static function legacyDialogueText(data:Dynamic, player1:String, player2:String):String return null;
  public static function legacyCutsceneScript(data:Dynamic):String return null;
  public static function legacyCutsceneBool(data:Dynamic, field:String, fallback:Bool):Bool return fallback;
}
""", newline='\n')
            (temp_path / "LuaCompat.hx").write_text("""typedef LuaCompatResult = {
  var hscript:String;
  var supported:Bool;
  var diagnostics:Array<String>;
};
class LuaCompat {
  public static function translate(source:String, ?origin:String):LuaCompatResult
    return {hscript: source, supported: true, diagnostics: []};
}
""", newline='\n')
            (temp_path / "HxcCompat.hx").write_text("""typedef HxcCompatDiagnostic = { var code:String; var message:String; };
typedef HxcCompatEventAdapter = { var sourceName:String; var canonicalName:String; var fields:Array<String>; };
typedef HxcCompatCallbackAdapter = {
  var sourceName:String;
  var canonicalName:String;
  var arguments:Array<String>;
  var body:String;
  var safe:Bool;
};
typedef HxcCompatResult = {
  var kind:String;
  var generatedHscript:String;
  var diagnostics:Array<HxcCompatDiagnostic>;
  var eventAdapters:Array<HxcCompatEventAdapter>;
  var nativeNoteDefinitions:Array<Dynamic>;
  var className:String;
  var canonicalCallbacks:Array<String>;
  var noteKinds:Array<String>;
  var callbackAdapters:Array<HxcCompatCallbackAdapter>;
  var noteBehaviorPatterns:Array<String>;
  var moduleDisabled:Bool;
  var customEventKind:String;
  var customEventBody:String;
};
class HxcCompat {
  public static function noteKindAvoidsHits(source:String):Bool return false;
  public static function analyze(source:String, ?path:String):HxcCompatResult
    return {kind: '', generatedHscript: '', diagnostics: [], eventAdapters: [], nativeNoteDefinitions: [], className: '',
      canonicalCallbacks: [], noteKinds: [], callbackAdapters: [], noteBehaviorPatterns: [], moduleDisabled: false,
      customEventKind: '', customEventBody: ''};
}
""", newline='\n')
            (temp_path / "DifficultyManager.hx").write_text("""import sys.FileSystem;
class DifficultyManager {
  public static var supportedDiff:Map<String, Bool> = new Map<String, Bool>();
  public static function addSongSupport(song:String):Void {
    var key = song.toLowerCase();
    if (FileSystem.exists('assets/data/' + key + '/' + key + '.json'))
      supportedDiff.set(key, true);
  }
}
""", newline='\n')
            (temp_path / "Main.hx").write_text(with_kade_parser(fixture), newline='\n')
            parent = temp_path / "mixed-parent"
            self._make_legacy_root(parent / "psych", "psych-song", direct=True,
                                    marker=("pack.json", "custom_events"))
            self._make_vslice_root(parent / "vslice", "vslice-song")
            self._make_legacy_root(parent / "kade", "kade-song", assets=True,
                                    marker=("manifest/default.json", "Kade Engine.exe"))
            self._make_legacy_root(parent / "fps", "fps-song", nested=True,
                                    marker=("meta.json",))
            (parent / "fps/meta.json").write_text('{{"description":"FPS Plus"}}', newline='\n')
            self._make_legacy_root(parent / "modplus", "mod-song", assets=True,
                                    marker=("images/custom_chars", "images/custom_stages"))
            self._make_legacy_root(parent / "legacy", "legacy-song", assets=True,
                                    marker=("manifest/default.json",))
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main", str(parent)],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("SONGS=7", output)

    @staticmethod
    def _make_legacy_root(root: Path, song: str, *, direct=False, assets=False,
                          nested=False, marker=()):
        content = root / ("assets" if assets else "")
        data = content / "data"
        audio = content / "songs"
        if nested:
            chart_dir = data / "songs" / song
        else:
            chart_dir = data / song
        audio_dir = audio / song
        chart_dir.mkdir(parents=True)
        audio_dir.mkdir(parents=True)
        chart = {"song": {"song": song, "player1": "bf", "player2": "dad", "notes": []}}
        (chart_dir / f"{song}.json").write_text(json.dumps(chart), newline='\n')
        (audio_dir / "Inst.ogg").write_bytes(b"inst")
        if direct:
            for directory in ("images", "characters", "stages", "scripts"):
                (root / directory).mkdir(parents=True, exist_ok=True)
        if not assets and not direct:
            (root / "images").mkdir(parents=True, exist_ok=True)
        for item in marker:
            path = root / item if item.lower().endswith('.exe') else content / item
            if path.suffix:
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.name == "Kade Engine.exe":
                    path.write_bytes(b"KadeDev")
                else:
                    path.write_text("{}", newline='\n')
            else:
                path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _make_vslice_root(root: Path, song: str):
        data = root / "data/songs" / song
        audio = root / "songs" / song
        data.mkdir(parents=True)
        audio.mkdir(parents=True)
        metadata = {
            "version": "2.2.0", "songName": "VSlice Display",
            "playData": {"difficulties": ["normal"], "songVariations": ["alt"], "characters": {
                "player": "bf", "opponent": "dad", "girlfriend": "gf",
                "opponentVocals": ["zed"], "playerVocals": ["ada", "bf"]},
                "stage": "stage", "noteStyle": "TestStyle"},
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {"version": "2.0.0", "notes": {"normal": [{"t": 100, "d": 0}]}}
        (data / f"{song}-metadata.json").write_text(json.dumps(metadata), newline='\n')
        (data / f"{song}-chart.json").write_text(json.dumps(chart), newline='\n')
        variation_metadata = {
            "version": "2.2.0", "songName": "VSlice Alt Display",
            "playData": {"difficulties": ["alt"], "songVariations": [], "characters": {
                "player": "dad", "opponent": "bf", "girlfriend": "nogf",
                "opponentVocals": ["alt-opponent"], "playerVocals": ["alt-player"],
                "instrumental": "alt"}, "stage": "mall", "noteStyle": "pixel"},
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        variation_chart = {"version": "2.0.0", "notes": {"alt": [{"t": 600, "d": 3}]},
                           "events": [{"t": 700, "e": "FocusCamera", "v": {"x": 5, "y": 7}}]}
        (data / f"{song}-metadata-alt.json").write_text(json.dumps(variation_metadata), newline='\n')
        (data / f"{song}-chart-alt.json").write_text(json.dumps(variation_chart), newline='\n')
        styles = root / "data/notestyles"
        styles.mkdir(parents=True)
        (styles / "TestStyle.json").write_text(json.dumps({
            "version": "1.1.0", "name": "TestStyle", "assets": {
                "note": {"assetPath": "shared:notes/test", "data": {
                    "left": {"prefix": "purple0"}, "down": {"prefix": "blue0"},
                    "up": {"prefix": "green0"}, "right": {"prefix": "red0"}}},
                "noteStrumline": {"assetPath": "shared:receptors/test", "data": {
                    "leftStatic": {"prefix": "arrowLEFT0"}, "leftPress": {"prefix": "left press0"},
                    "leftConfirm": {"prefix": "left confirm0"}, "downStatic": {"prefix": "arrowDOWN0"},
                    "downPress": {"prefix": "down press0"}, "downConfirm": {"prefix": "down confirm0"},
                    "upStatic": {"prefix": "arrowUP0"}, "upPress": {"prefix": "up press0"},
                    "upConfirm": {"prefix": "up confirm0"}, "rightStatic": {"prefix": "arrowRIGHT0"},
                    "rightPress": {"prefix": "right press0"}, "rightConfirm": {"prefix": "right confirm0"}}},
                "holdNote": {"assetPath": "shared:holds/test"},
                "noteSplash": {"assetPath": "shared:splashes/test", "data": {"enabled": True,
                    "leftSplashes": [{"prefix": "note impact 1 purple0"}],
                    "downSplashes": [{"prefix": "note impact 1 blue0"}],
                    "upSplashes": [{"prefix": "note impact 1 green0"}],
                    "rightSplashes": [{"prefix": "note impact 1 red0"}]}},
                "holdNoteCover": {"data": {"enabled": True,
                    "left": {"assetPath": "shared:holdCovers/left", "start": {"prefix": "coverStartLeft"}, "hold": {"prefix": "coverHoldLeft"}, "end": {"prefix": "coverEndLeft"}},
                    "down": {"assetPath": "shared:holdCovers/down", "start": {"prefix": "coverStartDown"}, "hold": {"prefix": "coverHoldDown"}, "end": {"prefix": "coverEndDown"}},
                    "up": {"assetPath": "shared:holdCovers/up", "start": {"prefix": "coverStartUp"}, "hold": {"prefix": "coverHoldUp"}, "end": {"prefix": "coverEndUp"}},
                    "right": {"assetPath": "shared:holdCovers/right", "start": {"prefix": "coverStartRight"}, "hold": {"prefix": "coverHoldRight"}, "end": {"prefix": "coverEndRight"}}}}
            }}), newline='\n')
        for stem in ("notes/test", "receptors/test", "splashes/test"):
            asset = root / ("shared/images/" + stem)
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.with_suffix(".png").write_bytes(b"png")
            asset.with_suffix(".xml").write_text("<TextureAtlas />", newline='\n')
        hold = root / "shared/images/holds/test.png"
        hold.parent.mkdir(parents=True, exist_ok=True)
        hold.write_bytes(b"png")
        for direction in ("left", "down", "up", "right"):
            cover = root / ("shared/images/holdCovers/" + direction + ".png")
            cover.parent.mkdir(parents=True, exist_ok=True)
            cover.write_bytes(b"png")
            cover.with_suffix(".xml").write_text("<TextureAtlas />", newline='\n')
        (audio / "Inst.ogg").write_bytes(b"inst")
        (audio / "Inst-alt.ogg").write_bytes(b"alt-inst")
        (audio / "Voices-Zed.ogg").write_bytes(b"zed")
        (audio / "Voices_bf.wav").write_bytes(b"bf")
        (audio / "Voices-Ada.mp3").write_bytes(b"ada")
        (audio / "Voices-alt-opponent.ogg").write_bytes(b"alt-opponent")
        (audio / "Voices-alt-player.ogg").write_bytes(b"alt-player")
        (root / "shared").mkdir(exist_ok=True)
        (root / "_polymod_meta.json").write_text("{}", newline='\n')


if __name__ == "__main__":
    unittest.main()
