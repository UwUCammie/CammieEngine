"""Regression coverage for the shared import settings and song importer."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


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


class SongImporterTest(unittest.TestCase):
    def test_import_settings_has_accurate_engine_types_and_is_reachable(self):
        settings = (ROOT / "source/ImportSettings.hx").read_text()
        engines = (ROOT / "source/ImportEngine.hx").read_text()
        state = (ROOT / "source/ImportSettingsState.hx").read_text()
        save_data = (ROOT / "source/SaveDataState.hx").read_text()
        self.assertIn('AUTO:String = ImportEngine.AUTO', settings)
        self.assertIn('V_SLICE:String = ImportEngine.V_SLICE', settings)
        self.assertIn('KADE_ENGINE:String = ImportEngine.KADE', settings)
        self.assertIn('MODDING_PLUS:String = ImportEngine.MODDING_PLUS', settings)
        self.assertIn('PSYCH_ENGINE:String = ImportEngine.PSYCH', settings)
        self.assertIn('FPS_PLUS:String = ImportEngine.FPS_PLUS', settings)
        self.assertIn('LEGACY_POLYMOD:String = ImportEngine.LEGACY_POLYMOD', settings)
        self.assertIn('MODDING_POOP:String = "Modding Poop"', settings)
        self.assertIn('IMPORT_TYPES:Array<String> = ImportEngine.names()', settings)
        self.assertNotIn('Kate Engine', engines)
        self.assertIn('"Import Type"', state)
        self.assertIn('"< " + importTypes[importTypeIndex] + " >"', state)
        self.assertIn('name:"Import Settings..."', save_data)
        self.assertIn('new ImportSettingsState()', save_data)
        self.assertIn('FlxG.mouse.visible = true', state)
        self.assertIn('ImportSettings.sourceDialogTitle(currentImportType())', state)
        self.assertIn('beginSongScan(sourcePath, importTypeAtScan)', state)
        self.assertIn('beginSongImport(sourcePath, scanResult, currentImportType(), packageNames)', state)
        self.assertIn('ImportPackageNamePrompt.collectUnnamedRoots', state)
        self.assertIn('controls.UP_MENU', state)
        self.assertIn('controls.DOWN_MENU', state)
        self.assertIn('chooseSourceFolder();', state)
        self.assertIn('startScan();', state)
        self.assertIn('startImport();', state)
        self.assertIn('ImportWorkflow.beginSongScan', state)
        self.assertIn('ImportWorkflow.beginSongImport', state)
        self.assertIn('scanResult.songsFound > 0 || scanResult.assetsToImport > 0', state)
        self.assertIn('scanResult.overlayPlanned != null', state)
        self.assertIn('DUPLICATE SONG', state)
        self.assertIn('MISSING', state)
        self.assertIn('progressPresentation', state)
        self.assertIn('new ImportRefreshProgressBar(this, progressPresentationStatus, true)', state)
        self.assertNotIn('new FlxBar(', state)
        self.assertIn('snapshot()', state)
        self.assertIn('cancelActiveJob();', state)
        self.assertIn('FileDialogType.OPEN_DIRECTORY', state)

        # FileDialog callbacks must be attached before browse() opens the
        # native picker, otherwise the selected path is lost on some Lime
        # backends.
        self.assertLess(state.index('dialog.onSelect.add'), state.index('dialog.browse'))

    def test_import_type_normalization_defaults_to_auto_and_migrates_legacy_label(self):
        source = (ROOT / "source/ImportSettings.hx").read_text()
        method = extract_method(source, "public static function normalizeType")
        fixture = f'''using StringTools;
class ImportTypeFixture {{
  static inline var AUTO:String = "Auto";
  static inline var V_SLICE:String = "V-Slice";
  static inline var KADE_ENGINE:String = "Kade Engine";
  static inline var MODDING_PLUS:String = "Modding Plus";
  static inline var PSYCH_ENGINE:String = "Psych Engine";
  static inline var NIGHTMARE_VISION:String = "Nightmare Vision";
  static inline var FPS_PLUS:String = "FPS Plus";
  static inline var LEGACY_POLYMOD:String = "Legacy FNF/Polymod";
  static final IMPORT_TYPES:Array<String> = [AUTO, V_SLICE, KADE_ENGINE, MODDING_PLUS, PSYCH_ENGINE, NIGHTMARE_VISION, FPS_PLUS, LEGACY_POLYMOD];
{method}
  static function main() {{
    if (normalizeType(null) != AUTO) throw "null did not default to Auto";
    if (normalizeType("Modding Poop") != MODDING_PLUS) throw "legacy label did not migrate";
    if (normalizeType("psych") != PSYCH_ENGINE) throw "psych alias did not normalize";
    if (normalizeType("fpsplus") != FPS_PLUS) throw "FPS Plus alias did not normalize";
    if (normalizeType("Kade Engine") != KADE_ENGINE) throw "engine label was rejected";
    if (normalizeType("not-an-engine") != AUTO) throw "unknown label did not fall back to Auto";
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportTypeFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "ImportTypeFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scan_completion_handoff_polls_finished_job_handle(self):
        """A worker can finish between frames; the UI must consume that result."""
        state = (ROOT / "source/ImportSettingsState.hx").read_text()
        update_start = state.index("override function update(elapsed:Float)")
        update_end = state.index("\n\toverride function destroy()", update_start)
        update = state[update_start:update_end]

        # hasActiveJob() is false as soon as the worker sets done=true.  The
        # update loop therefore needs to enter polling based on the handle's
        # presence, then let pollJobs() consume the completed snapshot.
        self.assertIn("if (hasJobHandle())", update)
        self.assertIn("pollJobs();", update)
        self.assertIn("function hasJobHandle():Bool", state)
        self.assertIn("return scanJob != null || importJob != null;", state)
        self.assertIn("if (completedResult != null)", state)
        self.assertIn("scanResult = completedResult;", state)
        self.assertIn("var completedSource = ImportSettings.normalizeSourcePath(completedResult.source);", state)
        self.assertIn("sourcePathAtScan = completedSource;", state)
        self.assertNotIn("sourcePathAtScan = currentSourcePath();", state)

    def test_completed_scan_summary_and_details_are_bounded(self):
        state = (ROOT / "source/ImportSettingsState.hx").read_text()
        show = extract_method(state, "function showScanResult(result:ImportScanResult)")
        self.assertIn("Engine types:", show)
        self.assertIn("Report:", show)
        # Root paths are detail rows, never part of the fixed-height summary.
        summary_end = show.index("detailLines = [];")
        self.assertNotIn("root.path", show[:summary_end])
        self.assertIn('detailLines.push("  path: "', show)
        self.assertIn("wrappedDetailLines()", state)
        self.assertIn("wrapDetailLine(line, maxChars)", state)
        self.assertIn("maxDetailPage(perPage)", state)
        self.assertIn("detailText.wordWrap = false", state)

    def test_detail_wrap_splits_long_paths_without_losing_text(self):
        state = (ROOT / "source/ImportSettingsState.hx").read_text()
        method = extract_method(state, "static function wrapDetailLine(line:String, maxChars:Int)")
        fixture = f'''import StringTools;
class DetailWrapFixture {{
{method}
  static function main() {{
    var original = "  path: /a/very/long/source/folder/with/no/spaces/inside/the/name/song/chart.json";
    var rows = wrapDetailLine(original, 18);
    if (rows.length < 3) throw "long path was not split";
    if (rows.join("").indexOf("/a/very/long/source") < 0) throw "wrapped path lost its prefix";
    if (rows.join("").indexOf("song/chart.json") < 0) throw "wrapped path lost its suffix";
    for (row in rows) if (row.length > 18) throw "wrapped row exceeds its bound";
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "DetailWrapFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "DetailWrapFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_custom_character_registry_normalization_defaults_missing_colors(self):
        """A legacy/imported entry without colors must not crash native builds."""
        source = (ROOT / "source/CoolUtil.hx").read_text()
        # The method contains a JSON string with a literal `}`; use the next
        # method declaration as the boundary instead of the test helper's
        # brace counter.
        method_start = source.index("public static function formatCustomChars()")
        method_end = source.index("\n\tpublic static function getSongFile", method_start)
        method = source[method_start:method_end]
        method = method.replace("CoolUtil.parseJson", "parseJson")
        fixture = f'''import haxe.Json;
import sys.io.File;
using StringTools;

class FNFAssets {{
  public static function getJson(path:String):String
    return '{{"abot":{{"like":"abot","icons":"face"}}}}';
}}

class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
{method}
}}

class CustomCharacterRegistryFixture {{
  static function main() {{
    sys.FileSystem.createDirectory("assets");
    sys.FileSystem.createDirectory("assets/images");
    sys.FileSystem.createDirectory("assets/images/custom_chars");
    CoolUtil.formatCustomChars();
    var normalized:String = File.getContent("assets/images/custom_chars/custom_chars.jsonc");
    if (normalized.indexOf('"colors": ["#FFFFFF"]') < 0)
      throw "missing colors were not defaulted";
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "CustomCharacterRegistryFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "CustomCharacterRegistryFixture", "--interp"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_json_parser_accepts_trailing_nul_padding(self):
        """Kade-era fixed-size chart buffers must parse without donor edits."""
        source = (ROOT / "source/CoolUtil.hx").read_text()
        method = extract_method(source, "public static function parseJson(json:String):Dynamic")
        method = method.replace("TJSON.parse", "Json.parse")
        fixture = """import haxe.Json;

class ParseJsonFixture {
""" + method + """
  static function main() {
    var raw:String = '{"song":{"notes":[]}}' + String.fromCharCode(0) + String.fromCharCode(0) + "\n";
    var parsed:Dynamic = parseJson(raw);
    if (parsed.song == null || parsed.song.notes == null || parsed.song.notes.length != 0)
      throw "trailing NUL padding was not removed";
  }
}
"""
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ParseJsonFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "ParseJsonFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_visual_registry_cache_invalidation_refreshes_in_session(self):
        song_source = (ROOT / "source/Song.hx").read_text()
        cache_start = song_source.index("\tstatic var registryCache")
        api_start = song_source.index("\n\tpublic static function invalidateVisualRegistryCache", cache_start)
        api_end = song_source.index("\n\tpublic var song", api_start)
        read_start = song_source.index("\n\tstatic function readRegistry", api_end)
        read_end = song_source.index("\n\tstatic function registryKey", read_start)
        cache_helpers = (
            song_source[cache_start:api_start]
            + song_source[api_start:api_end]
            + song_source[read_start:read_end]
        )
        module_source = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("public static function invalidateVisualRegistryCache():Void", cache_helpers)
        self.assertIn("Song.invalidateVisualRegistryCache();", module_source)
        self.assertGreaterEqual(module_source.count("Song.invalidateVisualRegistryCache();"), 4)

        fixture = f'''import haxe.Json;
class FNFAssets {{
  public static var source:String;
  public static function getJson(path:String):String return source;
}}
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
}}
class Song {{
{cache_helpers}
  static function main() {{
    FNFAssets.source = '{{"oldVisual":true}}';
    var initial = readRegistry('registry');
    if (initial.oldVisual != true) throw 'initial registry was not read';

    // A registry write during this process must not remain hidden behind the
    // cache populated by a chart loaded before the import.
    FNFAssets.source = '{{"newVisual":true}}';
    if (readRegistry('registry').newVisual == true) throw 'stale registry was unexpectedly refreshed';
    invalidateVisualRegistryCache();
    if (readRegistry('registry').newVisual != true) throw 'registry invalidation did not refresh data';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "Song.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Song", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_info_parser_preserves_windows_drive_colons(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        method = extract_method(source, "static public function processInfo")
        fixture = f'''import sys.io.File;
using StringTools;
class ImportInfoTest {{
{method}
 static function main() {{
  var path = "import-info-fixture.txt";
  File.saveContent(path, "# comment\\r\\nmalformed\\r\\npath:C:/mods/song\\r\\nname: Song\\r\\n");
  var info = processInfo(path);
  if (info.get("path") != "C:/mods/song") throw "drive colon was split";
  if (info.get("name") != "Song") throw "value was not trimmed";
  if (info.get("malformed") != null) throw "malformed line was accepted";
  sys.FileSystem.deleteFile(path);
 }}
}}'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportInfoTest.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "ImportInfoTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_song_import_guards_optional_files_and_easy_preview(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        module_state = (ROOT / "source/ModuleState.hx").read_text()
        settings = (ROOT / "source/ImportSettings.hx").read_text()
        self.assertIn("if (!validImportPath(songData.inst) && !hasExistingSongInstrumental(songData))", source)
        self.assertIn("copyIfPresent(songData.voices", source)
        self.assertIn("songData.char = songData.p2", source)
        self.assertNotIn("songData.char == songData.p2", source)
        self.assertIn("['hard', 'normal', 'easy']", module_state)
        self.assertIn("infoLines.join('\\n')", source)
        self.assertIn("importSongsPath()", module_state)
        self.assertIn("ensureImportDirectories", settings)
        self.assertIn("ImportSettings.ensureImportDirectories();", module_state)
        self.assertIn("static public function importSongsFromPath", source)
        self.assertIn("static public function importBatchSummary", source)
        self.assertIn("?compact:Bool = false", source)
        self.assertIn("diagnostic(s); see the details and import-report.txt", source)

    def test_import_gate_allows_asset_only_overlay_and_repair_passes(self):
        """A scan with duplicate charts can still have useful import work.

        The reported all-duplicate scan (158 duplicate songs, 292 new assets)
        must not strand those assets behind the Import button.  The same gate
        must allow an overlay-only plan and a repair plan, while stale scan
        identity, a missing source, and either job handle keep importing
        disabled until the main-thread handoff consumes the handle.
        """
        source = (ROOT / "source/ImportSettingsState.hx").read_text()
        gate = extract_method(source, "function canImport():Bool")
        self.assertIn("scanResult.assetsToImport > 0", gate)
        self.assertIn("scanResult.overlayPlanned != null", gate)
        self.assertIn("sourcePathAtScan", gate)
        self.assertIn("importTypeAtScan", gate)
        self.assertIn("scanJob == null && importJob == null", gate)

        fixture = f'''import StringTools;
typedef ScanResult = {{
  var songsFound:Int;
  var assetsToImport:Int;
  @:optional var globalPacksToImport:Int;
  @:optional var overlayPlanned:Int;
}};
class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String
    return value == null ? "" : StringTools.replace(StringTools.trim(Std.string(value)), "\\\\", "/");
  public static function normalizeType(value:Dynamic):String
    return value == null ? "Auto" : StringTools.trim(Std.string(value));
}}
class ImportGateFixture {{
  var scanJob:Dynamic;
  var importJob:Dynamic;
  var scanResult:ScanResult;
  var sourcePathAtScan:String = "";
  var importTypeAtScan:String = "";
  var currentPath:String = "";
  var currentType:String = "";
  var sourceValid:Bool = true;

  public function new() {{}}

  function sourcePathIsValid():Bool return sourceValid;
  function currentSourcePath():String return currentPath;
  function currentImportType():String return currentType;
{gate}

  function check(result:ScanResult, sourceAt:String, typeAt:String, path:String,
      type:String, valid:Bool, scanActive:Bool, importActive:Bool):Bool {{
    scanResult = result;
    sourcePathAtScan = sourceAt;
    importTypeAtScan = typeAt;
    currentPath = path;
    currentType = type;
    sourceValid = valid;
    scanJob = scanActive ? {{}} : null;
    importJob = importActive ? {{}} : null;
    return canImport();
  }}

  static function main() {{
    var fixture = new ImportGateFixture();
    var assetOnly:ScanResult = {{songsFound:158, assetsToImport:292, overlayPlanned:0}};
    if (!fixture.check(assetOnly, "/donor", "Auto", "/donor", "Auto", true, false, false))
      throw "all-duplicate song scan with new assets was blocked";

    var overlayOnly:ScanResult = {{songsFound:0, assetsToImport:0, overlayPlanned:4}};
    if (!fixture.check(overlayOnly, "/donor", "Auto", "/donor", "Auto", true, false, false))
      throw "overlay-only import was blocked";

    var repair:ScanResult = {{songsFound:1, assetsToImport:0, overlayPlanned:0}};
    if (!fixture.check(repair, "/donor", "Psych Engine", "/donor", "Psych Engine", true, false, false))
      throw "repair import was blocked";

    if (fixture.check(assetOnly, "/old", "Auto", "/donor", "Auto", true, false, false))
      throw "stale source scan was accepted";
    if (fixture.check(assetOnly, "/donor", "Psych Engine", "/donor", "Auto", true, false, false))
      throw "stale type scan was accepted";
    if (fixture.check(assetOnly, "/donor", "Auto", "/donor", "Auto", false, false, false))
      throw "invalid source was accepted";
    if (fixture.check(assetOnly, "/donor", "Auto", "/donor", "Auto", true, true, false))
      throw "active scan was accepted";
    if (fixture.check(assetOnly, "/donor", "Auto", "/donor", "Auto", true, false, true))
      throw "active import was accepted";
    var empty:ScanResult = {{songsFound:0, assetsToImport:0, overlayPlanned:0}};
    if (fixture.check(empty, "/donor", "Auto", "/donor", "Auto", true, false, false))
      throw "empty scan was accepted";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "ImportGateFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "ImportGateFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_compact_import_summary_hides_raw_diagnostics_but_report_summary_does_not(self):
        """The status line must stay short while import-report.txt stays exact."""
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        workflow = (ROOT / "source/ImportWorkflow.hx").read_text()
        summary = extract_method(source, "static public function importBatchSummary")
        self.assertIn("if (compact)", summary)
        self.assertIn("overlay diagnostic(s); see the details and import-report.txt.", summary)
        self.assertIn("Overlay diagnostics: " , summary)
        # The worker's persistent report deliberately uses the full summary;
        # only ImportSettingsState asks for the compact status-line form.
        self.assertIn("ModuleFunctions.importBatchSummary(localResult)", workflow)
        self.assertNotIn("writeReport(scan, ModuleFunctions.importBatchSummary(localResult, true))", workflow)

        fixture = f'''typedef SongImportBatchResult = {{
  var found:Int;
  var imported:Int;
  var skipped:Int;
  var failed:Int;
  var copiedAssets:Int;
  var skippedAssets:Int;
  var errors:Array<String>;
  @:optional var globalPacksImported:Int;
  @:optional var overlayPlanned:Int;
  @:optional var overlayApplied:Int;
  @:optional var overlayRetained:Int;
  @:optional var overlaySkipped:Int;
  @:optional var overlayProvenance:Array<String>;
  @:optional var overlayDiagnostics:Array<String>;
}};
class ImportSummaryFixture {{
{summary}
  static function main() {{
    var rawError = "[missing-asset] a very long diagnostic that belongs in the report";
    var rawOverlay = "[overlay-retained] /donor/path/with/details";
    var result:SongImportBatchResult = {{
      found:158, imported:0, skipped:158, failed:0, copiedAssets:292,
      skippedAssets:0, errors:[rawError], overlayPlanned:2, overlayApplied:1,
      overlayRetained:1, overlaySkipped:0, overlayProvenance:["donor-root"],
      overlayDiagnostics:[rawOverlay]
    }};
    var compact = importBatchSummary(result, true);
    var full = importBatchSummary(result);
    if (compact.indexOf(rawError) >= 0 || compact.indexOf(rawOverlay) >= 0)
      throw "compact summary leaked raw diagnostics";
    if (compact.indexOf("diagnostic(s); see the details and import-report.txt.") < 0)
      throw "compact error summary was not actionable";
    if (compact.indexOf("overlay diagnostic(s); see the details and import-report.txt.") < 0)
      throw "compact overlay summary was not actionable";
    if (full.indexOf(rawError) < 0 || full.indexOf(rawOverlay) < 0)
      throw "full summary dropped report diagnostics";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "ImportSummaryFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "ImportSummaryFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_required_song_assets_cannot_silently_register_after_source_loss(self):
        """Optional sidecars may disappear; Inst must either already exist or copy."""
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function importPathKey",
                "static function isImportFile",
                "static function validImportPath",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function copyIfPresent",
                "static function copyRequired",
                "static function hasMaterializedFile",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(path:Dynamic):String {{
    if (path == null) return "";
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(path)), "\\\\", "/"));
  }}
}}

class RequiredCopyFixture {{
{methods}
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0,
      copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}

  static function main() {{
    var destination = Path.join(["assets", "songs", "demo", "Inst.ogg"]);
    var missing = "missing-Inst.ogg";
    var threw = false;
    try copyRequired(missing, destination, "instrumental audio") catch (_:Dynamic) threw = true;
    if (!threw) throw "missing required audio was silently accepted";

    File.saveContent("source-Inst.ogg", "inst");
    copyRequired("source-Inst.ogg", destination, "instrumental audio");
    if (!FileSystem.exists(destination)) throw "required audio was not copied";

    // A repair can keep valid destination bytes even when the donor is gone.
    FileSystem.deleteFile("source-Inst.ogg");
    copyRequired("source-Inst.ogg", destination, "instrumental audio");

    // A zero-byte interrupted copy is not playable and must not count as
    // materialized required audio.
    FileSystem.createDirectory(Path.join(["assets", "songs", "empty"]));
    File.saveContent(Path.join(["assets", "songs", "empty", "Inst.ogg"]), "");
    threw = false;
    try copyRequired("source-Inst.ogg", Path.join(["assets", "songs", "empty", "Inst.ogg"]),
      "instrumental audio") catch (_:Dynamic) threw = true;
    if (!threw) throw "zero-byte required audio was accepted";

    // Optional sidecars retain their best-effort behavior.
    copyIfPresent("missing-dialog.txt", Path.join(["assets", "data", "demo", "dialog.txt"]));
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "RequiredCopyFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RequiredCopyFixture"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        # The required copy and chart verification must precede registry write.
        self.assertLess(source.index("copyRequired(songData.inst"), source.index("File.saveContent(freeplayPath"))
        self.assertIn("requireChartMaterialized(chartDestination)", source)

    def test_stage_import_uses_registered_custom_stage_tree(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        module_state = (ROOT / "source/ModuleState.hx").read_text()
        self.assertIn("function importStage(path:String", module_state)
        self.assertIn(
            "Path.join(['assets', 'images', 'custom_stages', StringTools.trim(stageData.name)])",
            source,
        )
        self.assertIn("custom_stages/custom_stages.json'))", source)
        self.assertIn("assets/images/custom_stages/custom_stages.json", source)

    def test_recursive_import_accepts_assets_game_nested_and_module_roots(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function destinationAssetsPath",
                "static function isLegacyModuleSource",
                "static public function isSafeImportSource",
                "static public function discoverSongPackageFolders",
                "static public function discoverSongPackageFoldersDetailed",
                "static public function discoverSongPackageFoldersBounded",
                "static function findChildDirectory",
                "static function isAssetsRoot",
                "static function isAssetRootSearchName",
                "static function findSelectedAssetsRoots",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef SongPackageDiscoveryDiagnostic = {{
  var code:String;
  var severity:String;
  var message:String;
  var scannedDirectories:Int;
  var directoryLimit:Int;
  var queuedDirectories:Int;
}};
typedef SongPackageDiscoveryResult = {{
  var folders:Array<String>;
  var diagnostics:Array<SongPackageDiscoveryDiagnostic>;
  var truncated:Bool;
  var cancelled:Bool;
  var scannedDirectories:Int;
  var directoryLimit:Int;
  var queuedDirectories:Int;
}};

class ImportSettings {{
  public static function normalizeSourcePath(path:Dynamic):String {{
    if (path == null) return "";
    var value = StringTools.trim(Std.string(path));
    return value == "" ? "" : Path.normalize(StringTools.replace(value, "\\\\", "/"));
  }}
  public static function getImportRoot():String return Path.join(["assets", "module", "import"]);
}}

class RecursiveImportFixture {{
  static inline var MAX_IMPORT_DISCOVERY_DEPTH:Int = 8;
  static inline var MAX_IMPORT_DISCOVERY_DIRECTORIES:Int = 4096;
  static inline var MAX_ASSETS_ROOT_DEPTH:Int = 8;
  static inline var MAX_ASSETS_ROOT_DIRECTORIES:Int = 512;
  static function importWorkCancelled():Bool return false;
  static function yieldImportWork(?force:Bool = false):Void {{}}
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0):Void {{}}
{methods}
  static function main() {{
    var args = Sys.args();
    var mode = args[0];
    if (mode == "roots") {{
      var roots = findSelectedAssetsRoots(args[1]);
      if (roots.length != Std.parseInt(args[2])) throw "unexpected assets root count: " + roots.length;
    }} else if (mode == "packages") {{
      var packages = discoverSongPackageFolders(args[1]);
      if (packages.length != Std.parseInt(args[2])) throw "unexpected package count: " + packages.length;
    }} else if (mode == "safe") {{
      var allowed = isSafeImportSource(args[1]);
      if (allowed != (args[2] == "true")) throw "unexpected source safety result";
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "RecursiveImportFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            assets = Path(folder) / "assets-root" / "assets"
            (assets / "data" / "fixture-song").mkdir(parents=True)
            (assets / "songs" / "fixture-song").mkdir(parents=True)
            (assets / "data" / "fixture-song" / "fixture-song.json").write_text("{{}}", newline='\n')
            (assets / "songs" / "fixture-song" / "Inst.ogg").write_bytes(b"inst")
            game_assets = Path(folder) / "game" / "assets"
            (game_assets / "data").mkdir(parents=True)
            (game_assets / "songs").mkdir()
            nested_assets = Path(folder) / "outer" / "pack" / "game" / "assets"
            (nested_assets / "data").mkdir(parents=True)
            (nested_assets / "songs").mkdir()
            package = Path(folder) / "module-song"
            package.mkdir()
            (package / "Inst.ogg").write_bytes(b"inst")
            (package / "hard.json").write_text("{{\"song\":{{\"song\":\"module-song\"}}}}", newline='\n')

            def run(mode, path, expected):
                result = subprocess.run(
                    [*HAXE_COMMAND, "-cp", folder, "--run", "RecursiveImportFixture", mode, str(path), str(expected)],
                    cwd=folder,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            run("roots", assets, 1)
            run("roots", Path(folder) / "game", 1)
            run("roots", Path(folder) / "outer", 1)
            run("packages", package, 1)

    def test_package_discovery_reports_synthetic_truncation_without_large_fixture(self):
        """The package walk exposes its cap through a low-limit test seam."""
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function destinationAssetsPath",
                "static function isLegacyModuleSource",
                "static public function isSafeImportSource",
                "static public function discoverSongPackageFoldersDetailed",
                "static public function discoverSongPackageFoldersBounded",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;
typedef SongPackageDiscoveryDiagnostic = {{ var code:String; var severity:String; var message:String; var scannedDirectories:Int; var directoryLimit:Int; var queuedDirectories:Int; }};
typedef SongPackageDiscoveryResult = {{ var folders:Array<String>; var diagnostics:Array<SongPackageDiscoveryDiagnostic>; var truncated:Bool; var cancelled:Bool; var scannedDirectories:Int; var directoryLimit:Int; var queuedDirectories:Int; }};
class ImportSettings {{
  public static function normalizeSourcePath(path:Dynamic):String {{
    if (path == null) return "";
    var value = StringTools.trim(Std.string(path));
    return value == "" ? "" : Path.normalize(StringTools.replace(value, "\\\\", "/"));
  }}
  public static function getImportRoot():String return Path.join(["assets", "module", "import"]);
}}
class PackageDiscoveryFixture {{
  static inline var MAX_IMPORT_DISCOVERY_DEPTH:Int = 8;
  static inline var MAX_IMPORT_DISCOVERY_DIRECTORIES:Int = 4096;
  static var cancelled:Bool = false;
  static function importWorkCancelled():Bool return cancelled;
  static function yieldImportWork(?force:Bool = false):Void {{}}
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0):Void {{}}
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var bounded = discoverSongPackageFoldersBounded(root, 2);
    if (!bounded.truncated) throw "package walk did not report truncation";
    if (bounded.scannedDirectories != 2 || bounded.directoryLimit != 2) throw "unexpected package counts";
    if (bounded.queuedDirectories <= 0) throw "package truncation lost queued count";
    if (bounded.diagnostics.length != 1 || bounded.diagnostics[0].code != "package-scan-truncated") throw "package diagnostic missing";
    cancelled = true;
    var stopped = discoverSongPackageFoldersDetailed(root, 2);
    if (!stopped.cancelled || stopped.truncated || stopped.diagnostics.length != 0) throw "cancellation was reported as truncation";
    trace("TRUNCATED=" + bounded.truncated + "|SCANNED=" + bounded.scannedDirectories + "|QUEUED=" + bounded.queuedDirectories);
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "PackageDiscoveryFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            root = Path(folder) / "root"
            root.mkdir()
            for index in range(4):
                (root / f"candidate-{index}").mkdir()
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "PackageDiscoveryFixture", str(root)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("TRUNCATED=true|SCANNED=2", result.stdout + result.stderr)

    def test_recursive_import_skips_existing_files_and_rejects_own_assets(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function destinationAssetsPath",
                "static function isLegacyModuleSource",
                "static public function isSafeImportSource",
                "static function existingImportChild",
                "static function validImportEntryName",
                "static function ensureDirectory",
                "static function mergeTreeNonOverwriting",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class ImportSettings {{
  public static function normalizeSourcePath(path:Dynamic):String {{
    if (path == null) return "";
    var value = StringTools.trim(Std.string(path));
    return value == "" ? "" : Path.normalize(StringTools.replace(value, "\\\\", "/"));
  }}
  public static function getImportRoot():String return Path.join(["assets", "module", "import"]);
}}
typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int; }};
class RecursiveMergeFixture {{
{methods}
  static function importWorkCancelled():Bool return false;
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
  static function main() {{
    var args = Sys.args();
    var source = args[0];
    var destination = args[1];
    if (isSafeImportSource(Path.join([Sys.getCwd(), "assets"]))) throw "own assets accepted as source";
    var result:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0}};
    mergeTreeNonOverwriting(source, destination, 0, result);
    if (result.copied != 1 || result.skipped != 1 || result.failed != 0)
      throw "unexpected merge counts: " + result.copied + "/" + result.skipped + "/" + result.failed;
    if (File.getContent(Path.join([destination, "existing.txt"])) != "old") throw "duplicate was overwritten";
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "RecursiveMergeFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            source_root = Path(folder) / "source"
            destination_root = Path(folder) / "destination"
            source_root.mkdir()
            destination_root.mkdir()
            (Path(folder) / "assets").mkdir()
            (source_root / "existing.txt").write_text("new", newline='\n')
            (source_root / "new.txt").write_text("new", newline='\n')
            (destination_root / "existing.txt").write_text("old", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RecursiveMergeFixture", str(source_root), str(destination_root)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_recursive_import_copies_arbitrary_asset_dependencies_and_music(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function validImportEntryName",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function mergeTreeNonOverwriting",
                "static function supportedAssetTrees",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int; }};
class ImportSettings {{
  public static function normalizeSourcePath(path:Dynamic):String {{
    if (path == null) return "";
    var value = StringTools.trim(Std.string(path));
    return value == "" ? "" : Path.normalize(StringTools.replace(value, "\\\\", "/"));
  }}
}}
class ArbitraryAssetFixture {{
{methods}
  static function importWorkCancelled():Bool return false;
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
  static function main() {{
    var args = Sys.args();
    var sourceRoot = args[0];
    var destinationRoot = args[1];
    var result:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0}};
    for (relative in supportedAssetTrees(sourceRoot)) {{
      var source = Path.join([sourceRoot, relative]);
      if (FileSystem.isDirectory(source))
        mergeTreeNonOverwriting(source, Path.join([destinationRoot, relative]), 0, result);
    }}
    if (result.copied != 3 || result.skipped != 0 || result.failed != 0)
      throw "unexpected arbitrary asset counts: " + result.copied + "/" + result.skipped + "/" + result.failed;
    if (!FileSystem.exists(Path.join([destinationRoot, "images", "shared.png"]))) throw "image dependency missing";
    if (!FileSystem.exists(Path.join([destinationRoot, "videos", "cutscene.mp4"]))) throw "video dependency missing";
    if (!FileSystem.exists(Path.join([destinationRoot, "music", "ignored.ogg"]))) throw "music dependency missing";
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ArbitraryAssetFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            source_root = Path(folder) / "source-assets"
            destination_root = Path(folder) / "destination-assets"
            (source_root / "images").mkdir(parents=True)
            (source_root / "videos").mkdir()
            (source_root / "music").mkdir()
            (source_root / "images" / "shared.png").write_bytes(b"image")
            (source_root / "videos" / "cutscene.mp4").write_bytes(b"video")
            (source_root / "music" / "ignored.ogg").write_bytes(b"large")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ArbitraryAssetFixture", str(source_root), str(destination_root)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
