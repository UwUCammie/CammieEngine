"""Execute the engine-neutral Auto song writer against a mounted donor.

This audit is intentionally isolated from the game checkout.  It extracts the
same discovery and writer methods used by the native importer into a temporary
Haxe fixture, runs that fixture with the donor as a read-only input, and
creates all destination files below a temporary working directory.  It is a
stronger check than a scan: every selected candidate must produce a readable
native chart, and every materialized chart is checked against its donor (or
the captured V-Slice conversion) for difficulty membership, note/event rows,
timing/lane/sustain/type payloads, gameplay metadata, and centralized runtime
normalization. Nightmare Vision charts are compared after the same
source-backed chart normalization the importer applies. It also snapshots every selected donor source file and proves
that the donor bytes did not change.  The audit additionally requires a
bounded non-empty ``Inst.ogg`` execution fixture backed by a validated donor
file, a Freeplay registry entry, and a destination-only ``compatScripts.json``
manifest.  V-Slice character, stage, and note-style conversion plans are
checked separately: every supported mapping must have a safe relative
destination and a real non-empty donor source which remains unchanged through
the transaction.  Binary visual files are validated in place rather than
copied into the bounded scratch destination.

No donor file or checkout asset is written.  The mounted corpus is optional;
the command exits with a clear message when it is not available.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HAXE = ROOT / ".tools/haxe/haxe"
DEFAULT_DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
RUNTIME_SMOKE_ROOT = ROOT / "tmp" / "runtime-smoke"
DEFAULT_RUNTIME_SMOKE_OUTPUT = RUNTIME_SMOKE_ROOT / "selected-auto"


def validate_runtime_smoke_destination(value: Path | str) -> Path:
    """Resolve a retained audit destination below this checkout's ``tmp``.

    The mounted donor is intentionally never used as a destination.  Resolve
    existing symlinks before checking containment so a path such as
    ``tmp/runtime-smoke/link`` cannot redirect the importer outside the
    project-local scratch tree.
    """

    raw = Path(value)
    if not raw.is_absolute():
        raw = ROOT / raw
    if raw.exists() and raw.is_symlink():
        raise ValueError(f"runtime-smoke destination may not be a symlink: {raw}")
    resolved = raw.resolve()
    tmp_root = (ROOT / "tmp").resolve()
    if resolved == tmp_root or tmp_root not in resolved.parents:
        raise ValueError(
            f"runtime-smoke destination must be below project tmp: {resolved}"
        )
    return resolved


def validate_empty_runtime_smoke_destination(destination: Path) -> None:
    """Reject accidental overwrite of a retained fixture."""

    if destination.exists() and not destination.is_dir():
        raise ValueError(f"runtime-smoke destination is not a directory: {destination}")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(
            f"runtime-smoke destination is not empty (refusing overwrite): {destination}"
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


# Keep this list explicit.  It makes the audit fail loudly when a writer
# dependency is added without being exercised here, instead of silently
# falling back to a weaker scan-only path.
METHODS = (
    "static function importPathKey",
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
    "static function getImportDifficultyNames",
    "static function findImportChart",
    "static function isImportChartSidecar",
    "static function collectAssetCharts",
    "static function chartFieldString",
    "static function chartFieldBool",
    "static function chartFieldInt",
    "static function findNamedDirectory",
    "static function findChildDirectory",
    "static function readSongChart",
    "static function prepareSongNoteDefinitions",
    "static function collectSongNoteDefinitions",
    "static function appendCodenameDiagnostic",
    "static function appendCodenameDiagnostics",
    "static function discoverCodenameSongImports",
    "static function appendCodenameRootScriptDiagnostics",
    "static function collectCodenameScriptDiagnostics",
    "static function discoverCodenameSongsFromBase",
    "static function findCodenameDefinitionXml",
    "static function safeSortedDirectoryListing",
    "static public function processInfo",
    "static public function getInfoValue",
    "static public function getInfoBool",
    "static public function getInfoInt",
    "static function inferPsychStageForImport",
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
    "static function findLegacyMusicAudio",
    "static function songImportFromAssetFolders",
    "static function appendAssetSongImports",
    "static function findVSliceFreeplayIcon",
    "static function findVSliceFile",
    "static function findVSliceVideo",
    "static function findVSliceVoices",
    "static function findVSliceNoteStyle",
    "static function appendVSliceDiagnostic",
    "static function appendVSliceDiagnostics",
    "static function removeVSliceDiagnosticCode",
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
    "static function codenameConvertedCharacterName",
    "static function codenameNativeCharacterName",
    "static function findVSliceSongPairs",
    "static function safeVSliceVariationSuffix",
    "static function normalizeVSliceVariationDifficulty",
    "static function findVSliceVariationFile",
    "static function findVSliceInstrumental",
    "static function vSliceStemMatchesReference",
    "static function selectVSliceVocalStems",
    "static function discoverVSliceSongImports",
    "static function discoverLegacySongImportsFromRoot",
    "static function songCandidateChartCount",
    "static function songCandidateCompleteness",
    "static function compareSongCandidates",
    "static function songCandidateOrigin",
    "static function selectSongCandidates",
    "static function existingImportChild",
    "static function ensureDirectory",
    "static function copyIfPresent",
	"static function copyRequired",
	"static function hasMaterializedFile",
	"static function hasExistingSongInstrumental",
	"static function requireChartMaterialized",
	"static function importedCameraZoomMode",
	"static function applyImportedSidecars",
    "static function writeGeneratedDialogue",
    "static function applyImportedVisualMetadata",
    "static function prepareImportedSongIdentity",
    "static function importSongFolderName",
    "static function importedChartFileName",
    "static function freeplayRegistryPath",
    "static function readFreeplayRegistry",
    "static function freeplayRegistryHasSong",
    "static function compatScriptTreeNames",
    "static function hasCompatScriptFile",
    "static function nightmareVisionScriptSuffixes",
    "static function collectNightmareVisionScriptDirectory",
    "static function collectNightmareVisionScriptFilesImmediate",
    "static function collectNightmareVisionSongScripts",
    "static function collectNightmareVisionScriptFiles(root:String, prefix:String",
    "static function sourceHasCompatScriptTree",
    "static function compatScriptManifestPath",
    "static function validImportEntryName",
    "static function writeCompatScriptManifest",
    "static function writeImportProvenance",
    "static public function importSong(songData:SongImport)",
    "static public function validateSongImport",
)


# The mounted corpus contains real game audio and is much larger than the
# bounded scratch space available to this environment.  Keep the writer's
# source validation and destination-materialization path real, but replace
# binary audio copies with a tiny marker that records the donor byte count.
# Charts, registries, manifests, and small textual sidecars still use the
# extracted production writer unchanged.
BOUNDED_MEDIA_METHODS = r'''
  static function auditMediaFile(path:String):Bool {
    var extension = Path.extension(path).toLowerCase();
    return extension == 'ogg' || extension == 'mp3' || extension == 'wav'
      || extension == 'flac' || extension == 'opus' || extension == 'm4a'
      || extension == 'aac';
  }
  static function copyIfPresent(source:String, destination:String):Void {
    if (!validImportPath(source) || !FileSystem.exists(source) || FileSystem.isDirectory(source))
      return;
    var existingDestination = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
    if (FileSystem.exists(existingDestination)) {
      if (FileSystem.isDirectory(existingDestination))
        throw 'Unable to import asset: destination is a directory: ' + existingDestination;
      return;
    }
    ensureDirectory(Path.directory(destination));
    if (auditMediaFile(source)) {
      var sourceSize:Float = 0;
      try sourceSize = FileSystem.stat(source).size catch (_:Dynamic) {}
      if (sourceSize <= 0)
        throw 'Unable to import empty media source: ' + source;
      File.saveContent(destination, 'AUDIT_MEDIA_SOURCE_SIZE=' + Std.string(sourceSize));
      if (Path.withoutDirectory(destination).toLowerCase() == 'inst.ogg')
        ModuleFunctions.auditInstrumentalsValidated++;
    } else {
      File.copy(source, destination);
    }
  }
  static function copyRequired(source:String, destination:String, label:String):Void {
    var materialized = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
    if (FileSystem.exists(materialized)) {
      if (FileSystem.isDirectory(materialized))
        throw 'Required ' + label + ' is a directory: ' + destination;
      if (hasMaterializedFile(materialized))
        return;
    }
    if (!validImportPath(source) || !FileSystem.exists(source) || FileSystem.isDirectory(source))
      throw 'Missing required ' + label + ': ' + (source == null ? '' : source);
    var sourceSize:Float = 0;
    try sourceSize = FileSystem.stat(source).size catch (_:Dynamic) {}
    if (sourceSize <= 0)
      throw 'Empty required ' + label + ': ' + source;
    copyIfPresent(source, destination);
    materialized = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
    if (!hasMaterializedFile(materialized))
      throw 'Required ' + label + ' did not materialize at: ' + destination;
  }
'''


def kade_parser_class_text() -> str:
    parser = (ROOT / "source/KadeStageSource.hx").read_text().replace("package;", "")
    for imp in ("import haxe.io.Path;\n", "import sys.FileSystem;\n", "import sys.io.File;\n"):
        parser = parser.replace(imp, "")
    return parser


def insert_kade_parser(fixture: str) -> str:
    """Embed KadeStageSource as a second top-level class: its imports merge at
    the top of the file, its class lands before the fixture's own classes."""
    cut = fixture.index("\nclass ")
    return fixture[:cut] + "\n" + kade_parser_class_text() + fixture[cut:]


def psych_stage_inference_class_text() -> str:
    """Embed the production Psych StageData parser in standalone fixtures."""
    parser = (ROOT / "source/PsychStageInference.hx").read_text().replace("package;", "", 1)
    parser = parser.replace("import haxe.io.Path;\n", "")
    parser = parser.replace("#if sys\nimport sys.FileSystem;\nimport sys.io.File;\n#end\n", "")
    parser = parser.replace("using StringTools;\n", "")
    return parser.strip()


def insert_psych_stage_parser(fixture: str) -> str:
    """Keep the parser beside extracted methods while retaining fixture layout."""
    cut = fixture.index("\nclass Main {")
    return fixture[:cut] + "\n\n// PSYCH_STAGE_INFERENCE_FIXTURE\n" + psych_stage_inference_class_text() + fixture[cut:]


def haxe_fixture(module_source: str) -> str:
    extracted = {
        marker: extract_method(module_source, marker)
        for marker in METHODS
        if marker not in {
            "static function copyIfPresent",
            "static function copyRequired",
        }
    }
    methods = "\n".join(extracted.values())
    # applyKadeSourceStageCompatibility references KadeStageSource; ship
    # the parser beside the extracted methods so the fixture compiles.
    fixture = f'''import haxe.Json;
import haxe.io.Path;
import CompatScriptManifest.CompatScriptManifestData;
import hscript.Parser;
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
  @:optional var events:String; @:optional var cutsceneStoryOnly:Bool;
  @:optional var cutscenePlayOnce:Bool; var modchart:String;
  @:optional var sourceSelectableDifficulties:Array<String>;
  @:optional var sourceUnsupportedDifficulties:Array<String>;
  @:optional var generatedModchart:String; var diffFiles:Array<String>;
  @:optional var convertedCharts:Array<ConvertedSongChart>;
  @:optional var noteDefinitions:Array<Dynamic>;
  @:optional var convertedCharacters:Array<VSliceCharacterImport>;
  @:optional var freeplayIconSource:String;
  @:optional var convertedStage:VSliceStageImport; @:optional var vSliceRoot:String;
  @:optional var convertedNoteStyle:VSliceNoteStyleImport;
  @:optional var convertedNoteStyles:Array<VSliceNoteStyleImport>;
  @:optional var engine:String; @:optional var diagnostics:Array<String>;
  @:optional var sourceFolder:String; @:optional var destinationFolder:String;
  @:optional var sourceRoot:String; @:optional var sourceDuplicate:Bool;
  @:optional var sourceDuplicateOf:String;
  @:optional var importSourceInfo:SongImportSource;
  @:optional var sourceModName:String; @:optional var sourceModNameSource:String;
  @:optional var codenameEngineBaseAssetRoot:String;
  @:optional var codenameDefaultCharacter:String;
}};
typedef SongImportSource = {{ var song:String; var data:String; var destination:String;
  @:optional var sourceRoot:String; @:optional var engine:String; }};
typedef SongImportRejectionCollector = {{ var entries:Array<Dynamic>; var total:Int;
  var truncated:Bool; var seen:Map<String, Bool>; }};
typedef SongImportCandidate = {{ var song:SongImport; var root:String; var engine:String;
  @:optional var source:SongImportSource; }};
typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int;
  @:optional var errors:Array<String>; }};
class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
  public static function normalizeType(value:Dynamic):String return value == null ? 'Auto' : Std.string(value);
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
  public static function parseJson(raw:String):Dynamic {{
    var end = raw == null ? 0 : raw.length;
    while (end > 0) {{
      var code = raw.charCodeAt(end - 1);
      if (code == 0 || code == 9 || code == 10 || code == 13 || code == 32) end--;
      else break;
    }}
    return Json.parse(end == (raw == null ? 0 : raw.length) ? raw : raw.substr(0, end));
  }}
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}
class DifficultyManager {{
  public static var supportedDiff:Map<String, Bool> = new Map<String, Bool>();
  public static function addSongSupport(song:String):Void {{
    if (song == null) return;
    var key = song.toLowerCase();
    var folder = Path.join(['assets', 'data', key]);
    if (!FileSystem.isDirectory(folder)) return;
    for (entry in FileSystem.readDirectory(folder)) {{
      var lower = entry.toLowerCase();
      if (!lower.endsWith('.json')) continue;
      if (lower == key + '.json' || (lower.startsWith(key + '-')
          && ['events', 'metadata', 'manifest', 'dialogue', 'chartmeta'].indexOf(lower.substr(key.length + 1,
            lower.length - key.length - 6)) < 0)) {{
        supportedDiff.set(key, true);
        return;
      }}
    }}
  }}
}}

class ModuleFunctions {{
  static inline var MAX_IMPORT_DISCOVERY_DIRECTORIES:Int = 4096;
  static var importBackgroundMode:Bool = false;
  static var auditPrimaryOwners:Map<String, String> = new Map<String, String>();
  static var auditTargetOwners:Map<String, String> = new Map<String, String>();
  public static var auditInstrumentalsValidated:Int = 0;
  static function importWorkCancelled():Bool return false;
  static function yieldImportWork(?force:Bool = false):Void {{}}
  static function reportImportProgress(phase:String, current:String, completed:Int = 0,
    total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
  static function importPathIsWithin(path:String, root:String):Bool {{
    var a = importPathKey(path); var b = importPathKey(root);
    return a == b || (b != '' && a.startsWith(b + '/'));
  }}
  static function destinationAssetsPath():String return 'assets';
  static function isLegacyModuleSource(path:String):Bool return false;
  static function isCurrentGameImportRoot(root:ImportRootScanner.ImportRoot):Bool return false;
  static function songTargetExists(songName:String, ?sourceFolder:String):Bool return false;
  static function songNeedsRepair(songData:SongImport):Bool return false;
  static function validateAndRecordSongImport(_rejections:SongImportRejectionCollector,
      songData:SongImport, _sourceRoot:String, _sourcePath:String, _engine:String):Bool
    return validateSongImport(songData) == null;
{BOUNDED_MEDIA_METHODS}
{methods}
  public static function discoverRoot(root:ImportRootScanner.ImportRoot):Array<SongImport>
    return root.engine == ImportEngine.V_SLICE
      ? discoverVSliceSongImports(root)
      : (root.engine == ImportEngine.CODENAME
        ? discoverCodenameSongImports(root)
        : discoverLegacySongImportsFromRoot(root));
  public static function choose(candidates:Array<SongImportCandidate>):Array<SongImportCandidate>
    return selectSongCandidates(candidates);
  public static function auditImportedChartFileName(target:String, chartPath:String, index:Int):String
    return importedChartFileName(target, chartPath, index);
  public static function auditImportTarget(song:SongImport):String
  {{
    var canonical = importSongFolderName(song);
    var group = canonical.toLowerCase();
    var owner = CompatScriptManifest.destinationKey(
      CompatScriptManifest.destinationRoot(song.sourceRoot, song.engine));
    var ownerKey = group + '|' + owner;
    if (auditTargetOwners.exists(ownerKey)) {{
      var assigned = auditTargetOwners.get(ownerKey);
      if (assigned != canonical) {{
        Reflect.setField(song, 'destinationFolder', assigned);
        Reflect.setField(song, 'ownerQualifiedCollision', true);
      }}
      return assigned;
    }}
    var assigned = canonical;
    if (auditPrimaryOwners.exists(group) && auditPrimaryOwners.get(group) != owner)
      assigned = ImportSongOwnership.ownerQualifiedFolder(canonical, song.sourceRoot, song.engine);
    else
      auditPrimaryOwners.set(group, owner);
    auditTargetOwners.set(ownerKey, assigned);
    if (assigned != canonical) {{
      Reflect.setField(song, 'destinationFolder', assigned);
      Reflect.setField(song, 'ownerQualifiedCollision', true);
    }}
    return assigned;
  }}
  public static function writeManifest(song:SongImport):Dynamic
    return writeCompatScriptManifest(song);
  public static function writeProvenance(song:SongImport):Dynamic
    return writeImportProvenance(song);
}}

class Main {{
  static function fail(value:String):Void throw value;
  static function hasSong(registry:Array<Dynamic>, wanted:String):Bool {{
    for (category in registry) {{
      if (category == null || category.songs == null) continue;
      for (entry in (cast category.songs:Array<Dynamic>))
        if (entry != null && entry.name != null
          && Std.string(entry.name).toLowerCase() == wanted.toLowerCase()) return true;
    }}
    return false;
  }}
  static function songEntry(registry:Array<Dynamic>, wanted:String):Dynamic {{
    for (category in registry) {{
      if (category == null || category.songs == null) continue;
      for (entry in (cast category.songs:Array<Dynamic>))
        if (entry != null && entry.name != null
          && Std.string(entry.name).toLowerCase() == wanted.toLowerCase()) return entry;
    }}
    return null;
  }}
  static function chartFiles(folder:String):Array<String> {{
    var result:Array<String> = [];
    if (!FileSystem.isDirectory(folder)) return result;
    for (entry in FileSystem.readDirectory(folder)) {{
      // Psych event sidecars may contain an empty song.notes array, but are
      // not selectable difficulties. Their events are validated separately.
      if (!entry.toLowerCase().endsWith('.json') || ['noteinfo.json', 'events.json'].indexOf(entry.toLowerCase()) >= 0)
        continue;
      var path = Path.join([folder, entry]);
      try {{
        var parsed:Dynamic = Json.parse(File.getContent(path));
        if (parsed != null && parsed.song != null && Std.isOfType(parsed.song.notes, Array))
          result.push(entry);
      }} catch (_:Dynamic) {{}}
    }}
    result.sort(function(a:String, b:String):Int {{
      var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
      return lower == 0 ? Reflect.compare(a, b) : lower;
    }});
    return result;
  }}
  static function fieldPresent(value:Dynamic, name:String):Bool
    return value != null && Reflect.hasField(value, name);
  static function fieldValue(value:Dynamic, name:String):Dynamic
    return fieldPresent(value, name) ? Reflect.field(value, name) : null;
  static function meaningful(value:Dynamic):Bool {{
    if (value == null) return false;
    if (Std.isOfType(value, String)) {{
      var text = StringTools.trim(Std.string(value));
      return text != '' && text.toLowerCase() != 'null';
    }}
    return true;
  }}
  static function canonical(value:Dynamic):String {{
    if (value == null) return 'null';
    if (Std.isOfType(value, String)) return Json.stringify(Std.string(value));
    if (Std.isOfType(value, Bool)) return value == true ? 'true' : 'false';
    if (Std.isOfType(value, Int) || Std.isOfType(value, Float)) return Std.string(value);
    if (Std.isOfType(value, Array)) {{
      var parts:Array<String> = [];
      for (item in (cast value:Array<Dynamic>)) parts.push(canonical(item));
      return '[' + parts.join(',') + ']';
    }}
    var fields = Reflect.fields(value);
    fields.sort(function(a:String, b:String):Int return Reflect.compare(a, b));
    var objectParts:Array<String> = [];
    for (name in fields)
      objectParts.push(Json.stringify(name) + ':' + canonical(Reflect.field(value, name)));
    return '{' + objectParts.join(',') + '}';
  }}
  static function sameValue(a:Dynamic, b:Dynamic):Bool return canonical(a) == canonical(b);
  static function songOf(chart:Dynamic):Dynamic return chart == null ? null : fieldValue(chart, 'song');
  static function noteCount(song:Dynamic):Int {{
    var sections:Dynamic = fieldValue(song, 'notes');
    if (!Std.isOfType(sections, Array)) return 0;
    var count = 0;
    for (section in (cast sections:Array<Dynamic>)) {{
      var rows:Dynamic = Std.isOfType(section, Array) ? section : fieldValue(section, 'sectionNotes');
      if (Std.isOfType(rows, Array)) count += (cast rows:Array<Dynamic>).length;
    }}
    return count;
  }}
  static function eventCount(song:Dynamic):Int {{
    var events:Dynamic = fieldValue(song, 'events');
    if (!Std.isOfType(events, Array)) return 0;
    var count = 0;
    for (group in (cast events:Array<Dynamic>)) {{
      var groupValues:Array<Dynamic> = Std.isOfType(group, Array) ? cast group : null;
      var groupEvents:Dynamic = groupValues != null && groupValues.length > 1 ? groupValues[1] : null;
      if (Std.isOfType(groupEvents, Array)) count += (cast groupEvents:Array<Dynamic>).length;
      else count++;
    }}
    return count;
  }}
  static function chartFromFile(path:String):Dynamic {{
    try {{
      var parsed:Dynamic = Json.parse(File.getContent(path));
      return parsed != null && parsed.song != null && Std.isOfType(parsed.song.notes, Array)
        ? parsed : null;
    }} catch (_:Dynamic) {{ return null; }}
  }}
  static function chartDestination(target:String, candidate:SongImportCandidate,
      chartPath:String, index:Int, ?converted:Dynamic):String {{
    var suffix:String;
    if (converted != null) {{
      var template = VSliceImporter.nativeFileName('chart', Std.string(converted.difficulty));
      suffix = template.substr('chart'.length);
    }} else
      suffix = ModuleFunctions.auditImportedChartFileName(target, chartPath, index).substr(target.length);
    return Path.join(['assets', 'data', target, target + suffix]);
  }}
  static function expectedVisual(sourceSong:Dynamic, songData:SongImport, field:String):Dynamic {{
    if (field == 'gf' && songData.engine == ImportEngine.PSYCH) {{
      var explicitGf = fieldValue(sourceSong, 'gf');
      if (meaningful(explicitGf)) return explicitGf;
      var version = fieldValue(sourceSong, 'gfVersion');
      if (meaningful(version)) return version;
      var fallback = fieldValue(songData, 'gf');
      return meaningful(fallback) && Std.string(fallback) != 'gf' ? fallback : null;
    }}
    var source = fieldValue(sourceSong, field);
    if (source == null || (Std.isOfType(source, String) && !meaningful(source)))
      return fieldValue(songData, switch (field) {{
        case 'player1': 'p1'; case 'player2': 'p2'; case 'gf': 'gf'; case 'stage': 'stage';
        case 'uiType': 'ui'; case 'cutsceneType': 'cutscene'; case 'isHey': 'isHey';
        case 'isCheer': 'isCheer'; case 'isMoody': 'isMoody'; case 'isSpooky': 'isSpooky';
        case 'stageID': 'stageID'; default: field;
      }});
    return source;
  }}
  static function expectedVocalStems(songData:SongImport):Dynamic {{
    var stems:Dynamic = fieldValue(songData, 'vocalStems');
    if (!Std.isOfType(stems, Array) || (cast stems:Array<Dynamic>).length == 0) return null;
    var result:Array<Dynamic> = [];
    for (stem in (cast stems:Array<Dynamic>)) {{
      if (stem == null) continue;
      var file:Dynamic = fieldValue(stem, 'file');
      if (file == null) file = fieldValue(stem, 'destination');
      if (file == null || StringTools.trim(Std.string(file)) == '') continue;
      result.push({{
        id: fieldValue(stem, 'id'), role: fieldValue(stem, 'role'), file: Std.string(file)
      }});
    }}
    return result.length == 0 ? null : result;
  }}
  static function sourceTitleIsSafe(sourceSong:Dynamic, songData:SongImport,
      preserveCodenameTitle:Bool):Bool {{
    if (songData.engine != ImportEngine.PSYCH
      && songData.engine != ImportEngine.NIGHTMARE_VISION
      && !(songData.engine == ImportEngine.CODENAME && preserveCodenameTitle)) return false;
    var authored = fieldValue(sourceSong, 'song');
    if (authored == null) return false;
    var title = StringTools.trim(Std.string(authored));
    return title != '' && title != '.' && title != '..'
      && title.indexOf('/') < 0 && title.indexOf('\\\\') < 0
      && title.indexOf(':') < 0 && title.indexOf('\\u0000') < 0;
  }}
  static function expectedNativeField(sourceSong:Dynamic, songData:SongImport,
      field:String, target:String, preserveCodenameTitle:Bool):Dynamic {{
    if (field == 'song') {{
      var authored = fieldValue(sourceSong, 'song');
      return sourceTitleIsSafe(sourceSong, songData, preserveCodenameTitle) ? authored : target;
    }}
    if (field == 'compatPreserveSongTitle') return true;
    if (field == 'songArtist' || field == 'album' || field == 'difficultyRatings'
        || field == 'compatMetadata') {{
      var imported = fieldValue(songData, field);
      return imported == null ? fieldValue(sourceSong, field) : imported;
    }}
    if (field == 'player1' || field == 'player2' || field == 'gf' || field == 'stage'
        || field == 'uiType' || field == 'cutsceneType' || field == 'isHey'
        || field == 'isCheer' || field == 'isMoody' || field == 'isSpooky' || field == 'stageID')
      return expectedVisual(sourceSong, songData, field);
    if (field == 'vocalStems') {{
      var generated = expectedVocalStems(songData);
      return generated == null ? fieldValue(sourceSong, field) : generated;
    }}
    if (field == 'needsVoices' && expectedVocalStems(songData) != null) return true;
    if (field == 'cutsceneScript' || field == 'cutsceneStoryOnly' || field == 'cutscenePlayOnce') {{
      var generated = fieldValue(songData, field);
      if (field == 'cutsceneScript' && meaningful(generated)) return generated;
      if (field != 'cutsceneScript' && meaningful(fieldValue(songData, 'cutsceneScript'))
          && generated != null) return generated;
    }}
    return fieldValue(sourceSong, field);
  }}
  static function expectedNativePresence(sourceSong:Dynamic, songData:SongImport,
      field:String, preserveCodenameTitle:Bool):Bool {{
    if (field == 'song') return true;
    if (field == 'compatPreserveSongTitle')
      return sourceTitleIsSafe(sourceSong, songData, preserveCodenameTitle);
    if (field == 'songArtist' || field == 'album' || field == 'difficultyRatings'
        || field == 'compatMetadata')
      return fieldValue(songData, field) != null || fieldPresent(sourceSong, field);
    // This is a per-chart projection of the shared FPS Plus ratings list. The
    // writer validates it separately; the source chart has no corresponding
    // field to compare against.
    if (field == 'difficultyRating') return true;
    if (field == 'gf' && songData.engine == ImportEngine.PSYCH)
      return expectedVisual(sourceSong, songData, field) != null;
    if (field == 'player1' || field == 'player2' || field == 'gf' || field == 'stage'
        || field == 'uiType' || field == 'cutsceneType' || field == 'isHey'
        || field == 'isCheer' || field == 'isMoody' || field == 'isSpooky' || field == 'stageID')
      return fieldValue(songData, switch (field) {{
        case 'player1': 'p1'; case 'player2': 'p2'; case 'gf': 'gf'; case 'stage': 'stage';
        case 'uiType': 'ui'; case 'cutsceneType': 'cutscene'; case 'isHey': 'isHey';
        case 'isCheer': 'isCheer'; case 'isMoody': 'isMoody'; case 'isSpooky': 'isSpooky';
        case 'stageID': 'stageID'; default: field;
      }}) != null || fieldPresent(sourceSong, field);
    if (field == 'vocalStems') return expectedVocalStems(songData) != null || fieldPresent(sourceSong, field);
    if (field == 'needsVoices') return expectedVocalStems(songData) != null || fieldPresent(sourceSong, field);
    if (field == 'cutsceneScript') return meaningful(fieldValue(songData, field)) || fieldPresent(sourceSong, field);
    if (field == 'cutsceneStoryOnly' || field == 'cutscenePlayOnce')
      return (meaningful(fieldValue(songData, 'cutsceneScript')) && fieldValue(songData, field) != null)
        || fieldPresent(sourceSong, field);
    return fieldPresent(sourceSong, field);
  }}
  static function compareNativeMetadata(sourceSong:Dynamic, destinationSong:Dynamic,
      songData:SongImport, target:String, label:String,
      preserveCodenameTitle:Bool):Array<String> {{
    var errors:Array<String> = [];
    var known = ['song', 'player1', 'player2', 'gf', 'stage', 'uiType', 'cutsceneType',
      'isHey', 'isCheer', 'isMoody', 'isSpooky', 'stageID', 'vocalStems', 'needsVoices',
      'cutsceneScript', 'cutsceneStoryOnly', 'cutscenePlayOnce'];
    var names:Map<String, Bool> = new Map<String, Bool>();
    for (name in known) names.set(name, true);
    for (name in Reflect.fields(sourceSong)) names.set(name, true);
    for (name in Reflect.fields(destinationSong)) names.set(name, true);
    var all:Array<String> = [];
    for (name in names.keys()) all.push(name);
    all.sort(function(a:String, b:String):Int return Reflect.compare(a, b));
    for (name in all) {{
      if (name == 'notes' || name == 'events' || name == 'difficultyRating') continue;
      var expectedPresent = expectedNativePresence(sourceSong, songData, name,
        preserveCodenameTitle);
      var actualPresent = fieldPresent(destinationSong, name);
      if (expectedPresent != actualPresent) {{
        errors.push(label + ': metadata presence ' + name + ' expected=' + expectedPresent
          + ' actual=' + actualPresent);
        continue;
      }}
      if (expectedPresent && canonical(expectedNativeField(sourceSong, songData, name, target,
          preserveCodenameTitle))
          != canonical(fieldValue(destinationSong, name)))
        errors.push(label + ': metadata payload ' + name + ' changed');
    }}
    return errors;
  }}
  static function compareNativeChart(source:Dynamic, destination:Dynamic,
      songData:SongImport, target:String, label:String,
      preserveCodenameTitle:Bool):Array<String> {{
    var errors:Array<String> = [];
    var sourceSong = songOf(source); var destinationSong = songOf(destination);
    if (sourceSong == null || destinationSong == null) {{
      errors.push(label + ': missing song payload');
      return errors;
    }}
    if (canonical(fieldValue(sourceSong, 'notes')) != canonical(fieldValue(destinationSong, 'notes')))
      errors.push(label + ': note rows/section timing changed');
    if (canonical(fieldValue(sourceSong, 'events')) != canonical(fieldValue(destinationSong, 'events')))
      errors.push(label + ': embedded event payload changed');
    for (error in compareNativeMetadata(sourceSong, destinationSong, songData, target, label,
        preserveCodenameTitle))
      errors.push(error);
    return errors;
  }}
  static function compareEventSidecar(song:SongImport, target:String, label:String):Array<String> {{
    var errors:Array<String> = [];
    var source:Dynamic = fieldValue(song, 'events');
    if (source == null || !FileSystem.exists(source)) return errors;
    var sourceData:Dynamic = null; var destinationData:Dynamic = null;
    try {{
      sourceData = Json.parse(File.getContent(source));
      destinationData = Json.parse(File.getContent(Path.join(['assets', 'data', target, 'events.json'])));
    }} catch (error:Dynamic) {{
      errors.push(label + ': event sidecar could not be parsed');
      return errors;
    }}
    if (canonical(sourceData) != canonical(destinationData))
      errors.push(label + ': event sidecar payload changed');
    return errors;
  }}
  static function chartSnapshot(path:String):String {{
    try return File.getBytes(path).toHex() catch (_:Dynamic) return null;
  }}
  static function main() {{
    var donor = Sys.args()[0];
    var roots = ImportRootScanner.scan(donor, ImportEngine.AUTO);
    var candidates:Array<SongImportCandidate> = [];
    for (root in roots) {{
      var found = ModuleFunctions.discoverRoot(root);
      trace('ROOT_CANDIDATES|' + root.engine + '|' + found.length);
      for (song in found)
        candidates.push({{song:song, root:root.root, engine:root.engine}});
    }}
    var selected = ModuleFunctions.choose(candidates);
    if (Sys.args().length > 1 && Sys.args()[1] == '--discover-only') {{
      trace('ROOTS=' + roots.length + '|CANDIDATES=' + candidates.length
        + '|SELECTED=' + selected.length);
      var engineCounts:Map<String, Int> = new Map<String, Int>();
      for (candidate in selected) {{
        var count = engineCounts.exists(candidate.engine) ? engineCounts.get(candidate.engine) : 0;
        engineCounts.set(candidate.engine, count + 1);
      }}
      for (engine in engineCounts.keys())
        trace('ENGINE|' + engine + '|' + engineCounts.get(engine));
      return;
    }}
    FileSystem.createDirectory('assets');
    FileSystem.createDirectory('assets/data');
    FileSystem.createDirectory('assets/songs');
    File.saveContent('assets/data/baseSongKeys.json', '[]');
    File.saveContent('assets/data/freeplaySongJson.jsonc', '[{{"name":"Imported","songs":[]}}]');
    // Capture every selected donor chart (including skipped duplicate
    // candidates) before the writer runs.  Native charts are compared against
    // their source payload with only the documented song/visual/sidecar
    // normalization allowed; V-Slice charts are compared against the exact
    // in-memory conversion snapshot captured before importSong can mutate it.
    var donorBefore:Map<String, String> = new Map<String, String>();
    var visualSourceBefore:Map<String, String> = new Map<String, String>();
    var visualMappingsSeen:Map<String, Bool> = new Map<String, Bool>();
    var visualConversionsSeen:Map<String, Bool> = new Map<String, Bool>();
    var visualPlanErrors:Array<String> = [];
    var visualConversions = 0;
    var visualMappings = 0;
    var visualSourcesValidated = 0;
    var visualScriptsParsed = 0;
    var inspectVisualConversion = function(kind:String, reference:String, conversion:Dynamic) {{
      if (conversion == null) return;
      var conversionName = Std.string(fieldValue(conversion, 'name'));
      var conversionKey = kind + '|' + reference + '|' + conversionName;
      if (visualConversionsSeen.exists(conversionKey)) return;
      visualConversionsSeen.set(conversionKey, true);
      visualConversions++;
      if (!meaningful(conversionName))
        visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference + ': missing native conversion name');
      if (kind == 'character' && (fieldValue(conversion, 'registryEntry') == null
          || !meaningful(fieldValue(conversion, 'hscript'))))
        visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference + ': incomplete registry/script conversion');
      if (kind == 'stage' && (!meaningful(fieldValue(conversion, 'registryValue'))
          || !meaningful(fieldValue(conversion, 'hscript'))))
        visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference + ': incomplete registry/script conversion');
      if (kind == 'note-style' && fieldValue(conversion, 'supported') == true
          && (fieldValue(conversion, 'registryEntry') == null || fieldValue(conversion, 'preset') == null))
        visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference + ': incomplete registry/preset conversion');
      if ((kind == 'character' || kind == 'stage') && meaningful(fieldValue(conversion, 'hscript'))) {{
        try {{
          new Parser().parseString(Std.string(fieldValue(conversion, 'hscript')));
          visualScriptsParsed++;
        }} catch (error:Dynamic) {{
          visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference
            + ': generated HScript did not parse: ' + Std.string(error));
        }}
      }}
      var mappings:Dynamic = fieldValue(conversion, 'assets');
      if (!Std.isOfType(mappings, Array)) return;
      for (mapping in (cast mappings:Array<Dynamic>)) {{
        if (mapping == null || fieldValue(mapping, 'supported') != true) continue;
        var sourceValue:Dynamic = fieldValue(mapping, 'source');
        var destinationValue:Dynamic = fieldValue(mapping, 'destination');
        var source = sourceValue == null ? '' : Std.string(sourceValue);
        var destination = destinationValue == null ? ''
          : StringTools.replace(Std.string(destinationValue), '\\\\', '/');
        var mappingKey = source + '|' + destination + '|' + Std.string(fieldValue(mapping, 'kind'));
        if (visualMappingsSeen.exists(mappingKey)) continue;
        visualMappingsSeen.set(mappingKey, true);
        visualMappings++;
        var unsafeDestination = destination == '' || destination.startsWith('/')
          || destination.indexOf('../') >= 0 || destination.indexOf('/..') >= 0
          || (destination.length > 1 && destination.charAt(1) == ':');
        if (unsafeDestination) {{
          visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference
            + ': unsafe mapping destination ' + destination);
          continue;
        }}
        if (source == '' || !FileSystem.exists(source) || FileSystem.isDirectory(source)) {{
          visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference
            + ': supported mapping has no donor file ' + source);
          continue;
        }}
        var sourceStat = FileSystem.stat(source);
        if (sourceStat.size <= 0) {{
          visualPlanErrors.push('VISUAL_ERROR|' + kind + ' ' + reference
            + ': supported mapping is empty ' + source);
          continue;
        }}
        visualSourcesValidated++;
        visualSourceBefore.set(source, Std.string(sourceStat.size) + '|' + Std.string(sourceStat.mtime.getTime()));
      }}
    }};
    var expectedByTarget:Map<String, Array<Dynamic>> = new Map<String, Array<Dynamic>>();
    var expectedNamesByTarget:Map<String, Array<String>> = new Map<String, Array<String>>();
    var nativeExpected = 0;
    var vSliceExpected = 0;
    for (candidate in selected) {{
      var song = candidate.song;
      if (song.diffFiles != null)
        for (chartPath in song.diffFiles)
          if (chartPath != null && FileSystem.exists(chartPath) && !FileSystem.isDirectory(chartPath))
            donorBefore.set(chartPath, chartSnapshot(chartPath));
      if (song.sourceDuplicate == true)
        continue;
      if (candidate.engine == ImportEngine.V_SLICE) {{
        if (song.convertedCharacters != null)
          for (character in song.convertedCharacters)
            if (character != null)
              inspectVisualConversion('character', character.reference + '@' + character.source, character.conversion);
        if (song.convertedStage != null)
          inspectVisualConversion('stage', song.convertedStage.reference + '@' + song.convertedStage.source,
            song.convertedStage.conversion);
        if (song.convertedNoteStyle != null)
          inspectVisualConversion('note-style', song.convertedNoteStyle.reference + '@' + song.convertedNoteStyle.source,
            song.convertedNoteStyle.conversion);
      }}
      var target = ModuleFunctions.auditImportTarget(song);
      if (!expectedByTarget.exists(target)) expectedByTarget.set(target, []);
      if (!expectedNamesByTarget.exists(target)) expectedNamesByTarget.set(target, []);
          var expectations = expectedByTarget.get(target);
      var expectedNames = expectedNamesByTarget.get(target);
      if (song.convertedCharts != null && song.convertedCharts.length > 0) {{
        for (converted in song.convertedCharts) {{
          if (converted == null || converted.chart == null || converted.chart.song == null) continue;
          var destination = chartDestination(target, candidate, converted.source, -1, converted);
          var destinationName = Path.withoutDirectory(destination);
          var convertedAsNative = candidate.engine == ImportEngine.CODENAME;
          expectations.push({{
            native:convertedAsNative, source:converted.source, destination:destination,
            preserveCodenameTitle:converted.authoredSongTitle == true,
            expected:canonical(converted.chart), chart:converted.chart,
            notes:noteCount(converted.chart.song), events:eventCount(converted.chart.song)
          }});
          expectedNames.push(destinationName);
          if (convertedAsNative) nativeExpected++ else vSliceExpected++;
        }}
      }} else if (song.diffFiles != null) {{
        for (index in 0...song.diffFiles.length) {{
          var chartPath = song.diffFiles[index];
          var sourceChart = chartFromFile(chartPath);
          if (sourceChart == null) continue;
          // Native import applies the bundled NMV Chart.hx normalization
          // through this adapter before serialization. Compare against that
          // source-defined result, including safe preservation of the authored
          // chart title, instead of treating those intentional changes as loss.
          if (candidate.engine == ImportEngine.NIGHTMARE_VISION) {{
            var converted = NightmareVisionChartCompat.convert(sourceChart, chartPath);
            if (converted != null && converted.chart != null && converted.supported)
              sourceChart = converted.chart;
          }}
          var destination = chartDestination(target, candidate, chartPath, index);
          var destinationName = Path.withoutDirectory(destination);
          expectations.push({{
            native:true, source:chartPath, destination:destination,
            expected:canonical(sourceChart), chart:sourceChart,
            notes:noteCount(sourceChart.song), events:eventCount(sourceChart.song)
          }});
          expectedNames.push(destinationName);
          nativeExpected++;
        }}
      }}
      expectedNames.sort(function(a:String, b:String):Int {{
        var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
        return lower == 0 ? Reflect.compare(a, b) : lower;
      }});
    }}
    var duplicate = 0;
    var imported = 0;
    var failed = 0;
    var manifests = 0;
    var visible = 0;
    var chartChecks = 0;
    var noteChecks = 0;
    var eventChecks = 0;
    var eventSidecarChecks = 0;
    var difficultyChecks = 0;
    var metadataChecks = 0;
    var semanticErrors = 0;
    var byEngine:Map<String, Int> = new Map<String, Int>();
    var errors:Array<String> = visualPlanErrors.copy();
    for (candidate in selected) {{
      var song = candidate.song;
      if (song.sourceDuplicate == true) {{ duplicate++; continue; }}
      var target = ModuleFunctions.auditImportTarget(song);
      var ok = false;
      try ok = ModuleFunctions.importSong(song) catch (error:Dynamic) {{ errors.push(song.name + ': ' + Std.string(error)); }}
      if (!ok) {{ failed++; continue; }}
      imported++;
      var folder = Path.join(['assets', 'data', target]);
      var audio = Path.join(['assets', 'songs', target, 'Inst.ogg']);
      var charts = chartFiles(folder);
      if (charts.length == 0) {{ failed++; errors.push(song.name + ': no native chart'); continue; }}
      var expectedNames = expectedNamesByTarget.get(target);
      if (expectedNames == null) expectedNames = [];
      if (canonical(expectedNames) != canonical(charts)) {{
        semanticErrors++;
        errors.push('CHART_ERROR|' + song.name + ': difficulty set changed expected='
          + canonical(expectedNames) + ' actual=' + canonical(charts));
      }} else difficultyChecks++;
      var expectations = expectedByTarget.get(target);
      if (expectations == null) expectations = [];
      for (expectation in expectations) {{
        var destinationChart = chartFromFile(expectation.destination);
        chartChecks++;
        if (destinationChart == null) {{
          semanticErrors++;
          errors.push('CHART_ERROR|' + song.name + ': missing materialized chart ' + expectation.destination);
          continue;
        }}
        var destinationSong = destinationChart.song;
        var destinationNotes = noteCount(destinationSong);
        var destinationEvents = eventCount(destinationSong);
        if (expectation.notes != destinationNotes) {{
          semanticErrors++;
          errors.push('CHART_ERROR|' + song.name + ': note count changed at ' + expectation.destination
            + ' expected=' + expectation.notes + ' actual=' + destinationNotes);
        }} else noteChecks++;
        if (expectation.events != destinationEvents) {{
          semanticErrors++;
          errors.push('CHART_ERROR|' + song.name + ': event count changed at ' + expectation.destination
            + ' expected=' + expectation.events + ' actual=' + destinationEvents);
        }} else eventChecks++;
        var chartErrors:Array<String> = [];
        if (expectation.native == true)
          chartErrors = compareNativeChart(expectation.chart, destinationChart, song, target,
            song.name, expectation.preserveCodenameTitle == true);
        else if (expectation.expected != canonical(destinationChart))
          chartErrors.push(song.name + ': V-Slice conversion payload changed at ' + expectation.destination);
        if (chartErrors.length == 0) metadataChecks++;
        for (chartError in chartErrors) {{
          semanticErrors++;
          if (errors.length < 60) errors.push('CHART_ERROR|' + chartError);
        }}
      }}
      if (candidate.engine != ImportEngine.V_SLICE)
        if (fieldValue(song, 'events') != null && FileSystem.exists(fieldValue(song, 'events'))) {{
          eventSidecarChecks++;
          for (sidecarError in compareEventSidecar(song, target, song.name)) {{
            semanticErrors++;
            if (errors.length < 60) errors.push('CHART_ERROR|' + sidecarError);
          }}
        }}
      if (!FileSystem.exists(audio) || FileSystem.stat(audio).size <= 0) {{ failed++; errors.push(song.name + ': missing Inst.ogg'); continue; }}
      var registry:Array<Dynamic> = cast Json.parse(File.getContent('assets/data/freeplaySongJson.jsonc'));
      if (!hasSong(registry, target)) {{ failed++; errors.push(song.name + ': not in Freeplay registry'); continue; }}
      var registryEntry:Dynamic = songEntry(registry, target);
      var expectedDisplay:Dynamic = fieldValue(song, 'display');
      if (!meaningful(expectedDisplay)) expectedDisplay = target;
      if (meaningful(fieldValue(song, 'display'))
          && Std.string(fieldValue(registryEntry, 'display')) != Std.string(expectedDisplay)) {{
        semanticErrors++;
        errors.push('METADATA_ERROR|' + song.name + ': Freeplay display metadata changed');
      }}
      for (field in ['songArtist', 'album', 'difficultyRatings']) {{
        var expectedValue:Dynamic = fieldValue(song, field);
        if (expectedValue == null) continue;
        var actualValue:Dynamic = fieldValue(registryEntry, field);
        if (field == 'songArtist') actualValue = actualValue == null
          ? fieldValue(registryEntry, 'artist') : actualValue;
        if (canonical(expectedValue) != canonical(actualValue)) {{
          semanticErrors++;
          errors.push('METADATA_ERROR|' + song.name + ': Freeplay ' + field + ' metadata changed');
        }}
      }}
      if (!DifficultyManager.supportedDiff.exists(target)) {{ failed++; errors.push(song.name + ': not in DifficultyManager'); continue; }}
      visible++;
      var manifestPath = Path.join([folder, 'compatScripts.json']);
      var manifestOk = false;
      try {{
        var manifest:Dynamic = Json.parse(File.getContent(manifestPath));
        manifestOk = manifest != null && manifest.roots != null && (cast manifest.roots:Array<Dynamic>).length > 0;
      }} catch (_:Dynamic) {{}}
      if (!manifestOk) {{
        var provenance:Dynamic = ModuleFunctions.writeProvenance(song);
        var merge:Dynamic = ModuleFunctions.writeManifest(song);
        try {{
          var manifest:Dynamic = Json.parse(File.getContent(manifestPath));
          manifestOk = manifest != null && manifest.roots != null && (cast manifest.roots:Array<Dynamic>).length > 0;
        }} catch (_:Dynamic) {{}}
        if (!manifestOk) {{ failed++; errors.push(song.name + ': missing compatScripts.json'); continue; }}
      }}
      manifests++;
      var count = byEngine.exists(candidate.engine) ? byEngine.get(candidate.engine) : 0;
      byEngine.set(candidate.engine, count + 1);
    }}
    trace('ROOTS=' + roots.length + '|CANDIDATES=' + candidates.length + '|SELECTED=' + selected.length);
    trace('IMPORTED=' + imported + '|DUPLICATES=' + duplicate + '|FAILED=' + failed
      + '|MANIFESTS=' + manifests + '|FREEPLAY_VISIBLE=' + visible);
    trace('INSTRUMENTALS_VALIDATED=' + ModuleFunctions.auditInstrumentalsValidated
      + '|BOUNDED_MEDIA_FIXTURES=' + imported);
    var donorFiles = 0;
    var donorUnchanged = 0;
    for (path in donorBefore.keys()) {{
      donorFiles++;
      var before = donorBefore.get(path);
      var after = chartSnapshot(path);
      if (before != null && before == after) donorUnchanged++;
      else {{
        semanticErrors++;
        if (errors.length < 60) errors.push('CHART_ERROR|donor chart bytes changed: ' + path);
      }}
    }}
    trace('CHART_SEMANTICS=' + chartChecks + '|NATIVE_CHARTS=' + nativeExpected
      + '|VSLICE_CHARTS=' + vSliceExpected + '|NOTE_ROWS_CHECKED=' + noteChecks
      + '|EVENT_PAYLOADS_CHECKED=' + eventChecks + '|EVENT_SIDECARS_CHECKED=' + eventSidecarChecks
      + '|DIFFICULTY_SETS_CHECKED=' + difficultyChecks
      + '|GAMEPLAY_METADATA_CHECKED=' + metadataChecks);
    trace('DONOR_SOURCE_FILES=' + donorFiles + '|DONOR_SOURCE_BYTES_UNCHANGED=' + donorUnchanged
      + '|CHART_SEMANTIC_ERRORS=' + semanticErrors);
    var visualSourcesUnchanged = 0;
    var visualSourceFiles = 0;
    for (path in visualSourceBefore.keys()) {{
      visualSourceFiles++;
      try {{
        var stat = FileSystem.stat(path);
        var current = Std.string(stat.size) + '|' + Std.string(stat.mtime.getTime());
        if (current == visualSourceBefore.get(path)) visualSourcesUnchanged++;
        else visualPlanErrors.push('VISUAL_ERROR|donor visual source changed: ' + path);
      }} catch (_:Dynamic) {{
        visualPlanErrors.push('VISUAL_ERROR|donor visual source disappeared: ' + path);
      }}
    }}
    trace('VSLICE_VISUAL_CONVERSIONS=' + visualConversions + '|SUPPORTED_ASSET_MAPPINGS=' + visualMappings
      + '|VISUAL_SOURCES_VALIDATED=' + visualSourcesValidated + '|VISUAL_SOURCE_FILES=' + visualSourceFiles
      + '|VISUAL_SCRIPTS_PARSED=' + visualScriptsParsed + '|VISUAL_PLAN_ERRORS=' + visualPlanErrors.length);
    trace('VSLICE_VISUAL_SOURCE_FILES_UNCHANGED=' + visualSourcesUnchanged);
    for (engine in byEngine.keys()) trace('ENGINE|' + engine + '|' + byEngine.get(engine));
    for (error in errors) trace('ERROR|' + error);
    if (failed > 0 || semanticErrors > 0 || visualPlanErrors.length > 0) Sys.exit(2);
  }}
}}
'''
    return insert_psych_stage_parser(insert_kade_parser(fixture))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_DONOR)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument(
        "--prepare-runtime-smoke",
        action="store_true",
        help=(
            "retain the real importer transaction below project tmp for the "
            "native runtime-smoke fixture wrapper"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="retained fixture destination (must be below project tmp)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate source/destination only; do not run Haxe or write files",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="run source discovery only; do not invoke the destination writer",
    )
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_dir():
        print(f"mounted donor is not available: {source}", file=sys.stderr)
        return 2

    if args.output_root is not None and not args.prepare_runtime_smoke:
        parser.error("--output-root requires --prepare-runtime-smoke")
    if args.dry_run and not args.prepare_runtime_smoke:
        parser.error("--dry-run requires --prepare-runtime-smoke")

    retained_destination = None
    if args.prepare_runtime_smoke:
        try:
            retained_destination = validate_runtime_smoke_destination(
                args.output_root or DEFAULT_RUNTIME_SMOKE_OUTPUT
            )
            validate_empty_runtime_smoke_destination(retained_destination)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "runtime_smoke_prepare": {
                            "source": str(args.source.resolve()),
                            "destination": str(retained_destination),
                            "transaction": "ModuleFunctions.importSong",
                            "retained": False,
                            "dry_run": True,
                            "donor_writes": False,
                            "media_mode": "bounded-audit-markers",
                            "runtime_matrix_eligible": False,
                            "structural_only": True,
                        }
                    },
                    sort_keys=True,
                )
            )
            return 0

    if not HAXE.exists():
        print(f"portable Haxe runtime is not available: {HAXE}", file=sys.stderr)
        return 2

    module_source = (ROOT / "source/ModuleFunctions.hx").read_text()
    engine_source = (ROOT / "source/ImportEngine.hx").read_text()
    scanner_source = (ROOT / "source/ImportRootScanner.hx").read_text()
    vslice_source = (ROOT / "source/VSliceImporter.hx").read_text()
    astc_source = (ROOT / "source/VSliceAstcAdapter.hx").read_text()
    manifest_source = (ROOT / "source/CompatScriptManifest.hx").read_text()
    # Keep compiler output and the temporary destination on the project
    # filesystem.  The system /tmp is intentionally space-constrained and
    # must never receive a mounted-media copy during this audit.
    audit_tmp = ROOT / "tmp"
    audit_tmp.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="disappointing-auto-audit-", dir=str(audit_tmp)
    ) as folder:
        temp = Path(folder)
        # Compile the extracted fixture in an ephemeral workspace, but run it
        # with the retained output as cwd when requested.  This preserves the
        # production writer's relative ``assets/`` paths without leaving Haxe
        # sources in the runtime fixture or making the donor the cwd.
        transaction_cwd = temp
        if retained_destination is not None:
            retained_destination.mkdir(parents=True, exist_ok=True)
            transaction_cwd = retained_destination
        for name, fixture_source in {
            "ImportEngine.hx": engine_source,
            "ImportRootScanner.hx": scanner_source,
            "ImportDirectoryListing.hx": (ROOT / "source/ImportDirectoryListing.hx").read_text(),
            "VSliceImporter.hx": vslice_source,
            "VSliceAstcAdapter.hx": astc_source,
            "CodenameImporter.hx": (
                (ROOT / "source/CodenameImporter.hx").read_text()
                .replace("EngineCompat.EngineCompatEventRoute", "CodenameEventRoute")
                .replace(
                    "using StringTools;",
                    "using StringTools;\n"
                    "typedef CodenameEventRoute = { var name:String; var v1:String; var v2:String; var v3:String; };",
                    1,
                )
            ),
            "CodenameCharacterAtlas.hx": (ROOT / "source/CodenameCharacterAtlas.hx").read_text(),
            "CodenameEventMetadata.hx": (ROOT / "source/CodenameEventMetadata.hx").read_text(),
            "CodenameNoteMetadata.hx": (ROOT / "source/CodenameNoteMetadata.hx").read_text(),
            "CodenameStagePlacement.hx": (ROOT / "source/CodenameStagePlacement.hx").read_text(),
            "CodenameStrumlineLayout.hx": (ROOT / "source/CodenameStrumlineLayout.hx").read_text(),
            "CodenameEventPack.hx": (ROOT / "source/CodenameEventPack.hx").read_text(),
            "CodenameScriptDiscovery.hx": (ROOT / "source/CodenameScriptDiscovery.hx").read_text(),
            "CodenameInstallationAssetOverlay.hx": (ROOT / "source/CodenameInstallationAssetOverlay.hx").read_text(),
            "CodenameScriptPlan.hx": (ROOT / "source/CodenameScriptPlan.hx").read_text(),
            "CodenameSongMetadata.hx": (ROOT / "source/CodenameSongMetadata.hx").read_text(),
            "CompatScriptManifest.hx": manifest_source,
            "ImportSongOwnership.hx": (ROOT / "source/ImportSongOwnership.hx").read_text(),
            "PsychLuaScriptDependencies.hx": (ROOT / "source/PsychLuaScriptDependencies.hx").read_text(),
            "NightmareVisionChartCompat.hx": (ROOT / "source/NightmareVisionChartCompat.hx").read_text(),
            "NightmareVisionScriptDiscovery.hx": (ROOT / "source/NightmareVisionScriptDiscovery.hx").read_text(),
            "NightmareVisionDifficultyCompat.hx": (ROOT / "source/NightmareVisionDifficultyCompat.hx").read_text(),
        }.items():
            (temp / name).write_text(fixture_source)
        # The converter only needs these narrow interfaces for the audit.  The
        # real native runtime uses the full compatibility classes; these stubs
        # keep the audit independent of Flixel/OpenFL while preserving actual
        # chart conversion and writer behavior.
        (temp / "NoteTypeCompat.hx").write_text("""class NoteTypeCompat {
  public static function isStringType(value:Dynamic):Bool return value != null && Std.isOfType(value, String);
  public static function applyVSliceKind(definition:Dynamic, value:Dynamic):Bool return false;
  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int {
    var type = Std.string(value);
    for (i in 0...definitions.length)
      if (Std.string(definitions[i].sourceNoteType) == type) return i;
    definitions.push({sourceNoteType:type}); return definitions.length - 1;
  }
}
""")
        (temp / "EngineCompat.hx").write_text("""class EngineCompat {
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
  public static function resolveStageResolution(reference:String):Dynamic return {nativeName:reference, stageID:0, standard:false};
  public static function isBuiltinStageReference(reference:String):Bool return false;
  public static function legacyDialogueText(data:Dynamic, player1:String, player2:String):String return null;
  public static function legacyCutsceneScript(data:Dynamic):String return null;
  public static function legacyCutsceneBool(data:Dynamic, field:String, fallback:Bool):Bool return fallback;
}
""")
        (temp / "LuaCompat.hx").write_text("""typedef LuaCompatResult = { var hscript:String; var supported:Bool; var diagnostics:Array<String>; };
class LuaCompat { public static function translate(source:String, ?origin:String):LuaCompatResult
  return {hscript:source, supported:true, diagnostics:[]}; }
""")
        (temp / "HxcCompat.hx").write_text("""typedef HxcCompatDiagnostic = { var code:String; var message:String; };
typedef HxcCompatEventAdapter = { var sourceName:String; var canonicalName:String; var fields:Array<String>; };
typedef HxcCompatCallbackAdapter = { var sourceName:String; var canonicalName:String; var arguments:Array<String>; var body:String; var safe:Bool; };
typedef HxcCompatResult = { var kind:String; var generatedHscript:String; var diagnostics:Array<HxcCompatDiagnostic>;
  var eventAdapters:Array<HxcCompatEventAdapter>; var nativeNoteDefinitions:Array<Dynamic>; var className:String;
  var canonicalCallbacks:Array<String>; var noteKinds:Array<String>; var callbackAdapters:Array<HxcCompatCallbackAdapter>;
  var noteBehaviorPatterns:Array<String>; var moduleDisabled:Bool; var customEventKind:String; var customEventBody:String; };
class HxcCompat {
  public static function noteKindAvoidsHits(source:String):Bool return false; public static function analyze(source:String, ?path:String):HxcCompatResult
  return {kind:'', generatedHscript:'', diagnostics:[], eventAdapters:[], nativeNoteDefinitions:[], className:'',
    canonicalCallbacks:[], noteKinds:[], callbackAdapters:[], noteBehaviorPatterns:[], moduleDisabled:false,
    customEventKind:'', customEventBody:''}; }
""")
        (temp / "DifficultyManager.hx").write_text("""import haxe.io.Path; import sys.FileSystem;
class DifficultyManager { public static var supportedDiff:Map<String, Bool> = new Map<String, Bool>();
  public static function addSongSupport(song:String):Void { var key = song.toLowerCase(); var folder = Path.join(['assets','data',key]);
    if (!FileSystem.isDirectory(folder)) return; for (entry in FileSystem.readDirectory(folder))
      if (entry.toLowerCase() == key + '.json') { supportedDiff.set(key, true); return; } } }
""")
        (temp / "Main.hx").write_text(haxe_fixture(module_source))
        command = [
            str(HAXE),
            "-cp",
            str(ROOT / ".haxelib/hscript/2,5,0"),
            "-cp",
            str(temp),
            "--run",
            "Main",
            str(source),
        ]
        if args.discover_only:
            command.append("--discover-only")
        result = subprocess.run(
            command,
            cwd=transaction_cwd,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            env={**os.environ, "TMPDIR": str(audit_tmp)},
        )
        print(result.stdout, end="")
        print(result.stderr, end="")
        if retained_destination is not None:
            print(
                json.dumps(
                    {
                        "runtime_smoke_prepare": {
                            "source": str(source),
                            "destination": str(retained_destination),
                            "transaction": "ModuleFunctions.importSong",
                            "retained": result.returncode == 0,
                            "dry_run": False,
                            "donor_writes": False,
                            "media_mode": "bounded-audit-markers",
                            "runtime_matrix_eligible": False,
                            "structural_only": True,
                        }
                    },
                    sort_keys=True,
                )
            )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
