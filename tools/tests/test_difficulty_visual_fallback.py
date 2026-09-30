"""Focused coverage for cross-difficulty visual metadata fallback."""

from pathlib import Path
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


class DifficultyVisualFallbackTest(unittest.TestCase):
    def test_mixed_case_stage_is_validated_before_registry_normalization(self):
        source = (ROOT / "source/Song.hx").read_text()
        loader = source[source.index("\tpublic static function loadFromJson("):]
        self.assertLess(
            loader.index("!visualValueIsValid('stage', parsedJson.stage, validity)"),
            loader.index("normalizeVisualFields(parsedJson, folderLower);"),
            "normalizing auditorHell to auditorhell before checking the authored validity key discards the stage",
        )
        self.assertIn("compatibilityEngine(folderLower, requestedJson).toLowerCase().indexOf('psych') >= 0", loader)

        fields_start = source.index("\tstatic var gameplayFields")
        fields_end = source.index("\tstatic var registryCache", fields_start)
        fields = source[fields_start:fields_end]
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "\tstatic function chartHasValue(",
                "\tpublic static function resolveChartData(",
                "\tstatic function visualValueIsValid(",
                "\tstatic function registryKey(",
                "\tstatic function normalizeVisualFields(",
            )
        )
        fixture = """using StringTools;

class DifficultyVisualFallbackTest {
""" + fields + methods + """
  static function characterRootForSong(_folder:String):String return '';
  static function ownedStageEntry(_folder:String,_name:String):Dynamic return null;
  static function ownedCutsceneEntry(_folder:String,_name:String):Dynamic return null;
  static function readCharacterRegistryInManifest(_root:String):Dynamic return null;
  static function isValidVisualValue(field:String, value:Dynamic):Bool return false;
  static function readRegistry(path:String):Dynamic {
    return path.indexOf('custom_stages') >= 0 ? {auditorhell:'auditorhell'} : {};
  }
  static function main() {
    var requested:Dynamic = {song:'song', stage:'auditorHell'};
    var valid = new Map<String, Bool>();
    valid.set('stage=auditorHell', true);
    var resolved = resolveChartData(requested, [], null, valid);
    if (!visualValueIsValid('stage', resolved.stage, valid))
      throw 'authored mixed-case stage was rejected before normalization';
    normalizeVisualFields(resolved);
    var sibling:Dynamic = {codenameUnsupportedNotes:[{lineIndex:3,noteIndex:1}]};
    var own:Array<Dynamic> = [{lineIndex:4,noteIndex:0,note:{time:500}}];
    var selected = resolveChartData({codenameUnsupportedNotes:own}, [], sibling);
    if (selected.codenameUnsupportedNotes != own)
      throw 'selected difficulty lost its retained source notes';
    var absent = resolveChartData({}, [], sibling);
    if (Reflect.hasField(absent, 'codenameUnsupportedNotes'))
      throw 'retained source notes leaked from a sibling difficulty';
    var empty = resolveChartData({codenameUnsupportedNotes:[]}, [], {codenameUnsupportedNotes:own});
    if (empty.codenameUnsupportedNotes.length != 0)
      throw 'explicit empty source list was replaced';
    var standalone = resolveChartData({codenameUnsupportedNotes:own}, []);
    if (standalone.codenameUnsupportedNotes != own)
      throw 'standalone chart lost source notes';
    var vSliceBase:Dynamic = {vSliceUnroutedNotes:[{t:900,d:12}]};
    var vSliceOwn:Array<Dynamic> = [{t:100,d:8,authored:'selected'}];
    var vSliceSelected = resolveChartData({vSliceUnroutedNotes:vSliceOwn}, [], vSliceBase);
    if (vSliceSelected.vSliceUnroutedNotes != vSliceOwn)
      throw 'selected V-Slice difficulty lost raw unrouted notes';
    var vSliceAbsent = resolveChartData({}, [], vSliceBase);
    if (Reflect.hasField(vSliceAbsent, 'vSliceUnroutedNotes'))
      throw 'V-Slice raw notes leaked from a sibling difficulty';
    var vSliceEmpty = resolveChartData({vSliceUnroutedNotes:[]}, [], vSliceBase);
    if (vSliceEmpty.vSliceUnroutedNotes.length != 0)
      throw 'explicit empty V-Slice raw-note list was replaced';
    var vSliceStandalone = resolveChartData({vSliceUnroutedNotes:vSliceOwn}, []);
    if (vSliceStandalone.vSliceUnroutedNotes != vSliceOwn)
      throw 'standalone V-Slice chart lost raw unrouted notes';
    if (resolved.stage != 'auditorhell')
      throw 'registered stage spelling was not used for the runtime path';
    if (visualValueIsValid('stage', resolved.stage, valid))
      throw 'fixture failed to model the case-sensitive validity key';
    var sourceVisuals:Dynamic = {player1:'bf-santa',gf:'missing-gf',stage:'missing-stage'};
    var defaults:Dynamic = {player1:'bf',gf:'gf',stage:'stage'};
    var sourceResult = resolveChartData(sourceVisuals, [], defaults, valid, true);
    if (sourceResult.player1 != 'bf-santa' || sourceResult.gf != 'missing-gf'
        || sourceResult.stage != 'missing-stage')
      throw 'Psych difficulty silently borrowed graphics from its default chart';
    var legacy = resolveChartData(sourceVisuals, [],
      {player1:'bf',gf:'gf',stage:'stage'}, valid);
    if (legacy.player1 != 'bf' || legacy.gf != 'gf' || legacy.stage != 'stage')
      throw 'legacy invalid-visual fallback changed unexpectedly';
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "DifficultyVisualFallbackTest.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "DifficultyVisualFallbackTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_variant_does_not_leak_from_a_sibling_difficulty(self):
        source = (ROOT / "source/Song.hx").read_text()
        fields_start = source.index("\tstatic var gameplayFields")
        fields_end = source.index("\tstatic var registryCache", fields_start)
        fields = source[fields_start:fields_end]
        helpers = "\n".join(
            extract_method(source, marker)
            for marker in (
                "\tstatic function chartHasValue(",
                "\tpublic static function resolveChartData(",
                "\tstatic function visualValueIsValid(",
            )
        )
        fixture = """using StringTools;

class DifficultyVisualFallbackTest {
""" + fields + helpers + """
\tstatic function isValidVisualValue(field:String, value:Dynamic):Bool return true;

\tstatic function main() {
\t\tvar requested:Dynamic = {song:'ugh', notes:[], bpm:160};
\t\tvar normal:Dynamic = {stage:'tank'};
\t\tvar erect:Dynamic = {stage:'tank', stageID:1};
\t\tvar resolved = resolveChartData(requested, [normal, erect], normal);
\t\tif (Reflect.hasField(resolved, 'stageID'))
\t\t\tthrow 'the erect stage variant leaked into a difficulty with no stageID';

\t\tvar explicitLower:Dynamic = {song:'ugh', notes:[], bpm:160, stageID:0};
\t\tvar selected = resolveChartData(explicitLower, [normal, erect], normal);
\t\tif (selected.stageID != 0)
\t\t\tthrow 'an explicit lower-difficulty stage variant was replaced';
\t}
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "DifficultyVisualFallbackTest.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "DifficultyVisualFallbackTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_loader_checks_all_visual_siblings(self):
        source = (ROOT / "source/Song.hx").read_text()
        for field in ("player1", "player2", "gf", "stage", "uiType", "cutsceneType"):
            self.assertIn(f"'{field}'", source)
        # A complete character/stage quartet must not stop the search before a
        # later sibling supplies UI or cutscene metadata.
        self.assertNotIn("if (hasGraphicVisuals(candidateResult))", source)
        self.assertIn("normalizeVisualFields(parsedJson, folderLower);", source)

        scanner = (ROOT / "source/ImportWorkflow.hx").read_text()
        self.assertIn("A sibling visual donor must be a real chart envelope", scanner)
        self.assertIn("chartSongIdentity(peer.chart) == selectedIdentity", scanner)

    def test_import_writer_preserves_explicit_bad_visual_for_runtime_fallback(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        method = extract_method(source, "static function applyImportedVisualMetadata(")
        fixture = """import StringTools;

typedef SongImport = {
  var engine:String;
  var p1:String; var p2:String; var gf:String; var stage:String;
  var ui:String; var cutscene:String; var isMoody:Bool; var isHey:Bool;
  var isCheer:Bool; var isSpooky:Bool; var stageID:Int;
};
class ImportEngine { public static inline var PSYCH:String = 'Psych Engine'; }

class DifficultyVisualFallbackTest {
""" + method + """
  static function main() {
    var chart:Dynamic = {
      player1: 'explicit-but-missing', player2: null, gf: '', stage: 'authored-stage',
      uiType: 'normal', cutsceneType: 'none', stageID: 9
    };
    var metadata:SongImport = {
      engine:'Modding Plus',
      p1:'fallback-player', p2:'fallback-opponent', gf:'fallback-gf', stage:'fallback-stage',
      ui:'fallback-ui', cutscene:'fallback-cutscene', isMoody:false, isHey:false,
      isCheer:false, isSpooky:false, stageID:0
    };
    applyImportedVisualMetadata(chart, metadata);
    if (chart.player1 != 'explicit-but-missing')
      throw 'import writer erased an explicit invalid character reference';
    if (chart.player2 != 'fallback-opponent' || chart.gf != 'fallback-gf')
      throw 'missing imported visual metadata was not filled';
    if (chart.stage != 'authored-stage' || chart.stageID != 9)
      throw 'valid authored visual metadata was replaced';
    var psychMetadata:SongImport = {
      engine:ImportEngine.PSYCH,
      p1:'bf', p2:'dad', gf:'gf', stage:'stage',
      ui:'normal', cutscene:'none', isMoody:false, isHey:false,
      isCheer:false, isSpooky:false, stageID:0
    };
    var normal:Dynamic = {gfVersion:'gf_JUICY'};
    applyImportedVisualMetadata(normal, psychMetadata);
    if (normal.gf != 'gf_JUICY')
      throw 'Psych gfVersion lost to song-level default';
    var easy:Dynamic = {};
    applyImportedVisualMetadata(easy, psychMetadata);
    if (Reflect.hasField(easy, 'gf'))
      throw 'sparse Psych difficulty lost default-chart gf inheritance';
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "DifficultyVisualFallbackTest.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "DifficultyVisualFallbackTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scan_resolves_missing_visual_and_keeps_compatibility_diagnostic(self):
        source = (ROOT / "source/ImportWorkflow.hx").read_text()
        fields_start = source.index("\tstatic var visualFallbackFields")
        fields_end = source.index("\n\t/** Return the song payload", fields_start)
        fields = source[fields_start:fields_end]
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function chartPayload(",
                "static function rawChartValue(",
                "static function chartSongIdentity(",
                "static function visualDependencyKind(",
                "static function addVisualChartCandidate(",
                "static function collectSiblingVisualCharts(",
                "static function addSongDiagnostic(",
                "static function resolveVisualChartFallback(",
            )
        )
        fixture = """import haxe.io.Path;
import sys.FileSystem;
using StringTools;

typedef ImportVisualChart = { var path:String; var chart:Dynamic; };
typedef ImportScanSong = { @:optional var diagnostics:Array<String>; };

class DifficultyVisualFallbackTest {
""" + fields + """
""" + methods + """
  static function pathKey(path:String):String return path == null ? '' : Path.normalize(path).toLowerCase();
  static function directory(path:String):Bool return false;
  static function readChart(path:String):Dynamic return null;
  static function visualDependencyFound(fieldName:String, value:String, sourceRoots:Array<String>):Bool
    return value != null && value.toLowerCase() == 'valid';

  static function main() {
    var requested:Dynamic = {
      song:'song', player1:'valid', player2:'missing-definition', gf:'valid', stage:'valid',
      uiType:'valid', cutsceneType:'valid'
    };
    var sibling:Dynamic = {
      song:'SONG', player1:'valid', player2:'valid', gf:'valid', stage:'valid',
      uiType:'valid', cutsceneType:'valid'
    };
    var scan:ImportScanSong = {diagnostics:[]};
    var peers:Array<ImportVisualChart> = [{path:'C:/Donor/SONG-HARD.JSON', chart:sibling}];
    var resolved = resolveVisualChartFallback('C:/Donor/SONG.JSON', requested, [], scan, peers);
    if (resolved.player2 != 'valid')
      throw 'scanner did not reuse a valid sibling character';
    if (resolved.player1 != 'valid' || resolved.stage != 'valid')
      throw 'scanner replaced valid selected metadata';
    if (requested.player2 != 'missing-definition' || sibling.player2 != 'valid')
      throw 'scan fallback mutated a source chart object';
    if (scan.diagnostics == null || scan.diagnostics.length != 1
        || scan.diagnostics[0].indexOf('player2') < 0
        || scan.diagnostics[0].indexOf('SONG-HARD.JSON') < 0)
      throw 'compatibility fallback diagnostic was not retained';

    var unrelated:Dynamic = {song:'other-song', player2:'valid'};
    var unrelatedPeers:Array<ImportVisualChart> = [{path:'C:/Donor/OTHER-HARD.JSON', chart:unrelated}];
    var unrelatedScan:ImportScanSong = {diagnostics:[]};
    var unresolved = resolveVisualChartFallback('C:/Donor/SONG.JSON', requested, [], unrelatedScan, unrelatedPeers);
    if (unresolved.player2 != 'missing-definition' || unrelatedScan.diagnostics.length != 0)
      throw 'unrelated chart donated visual metadata';

    // Converted V-Slice peers arrive as {song:{...}} envelopes.  They must
    // still participate in same-song fallback after the selected envelope is
    // unwrapped by the scanner.
    var envelope:Dynamic = {song:{song:'song', player2:'valid'}};
    var envelopePeers:Array<ImportVisualChart> = [
      {path:'C:/Donor/SONG-ALT.JSON', chart:envelope}
    ];
    var envelopeScan:ImportScanSong = {diagnostics:[]};
    var envelopeResolved = resolveVisualChartFallback('C:/Donor/SONG.JSON', requested, [], envelopeScan,
      envelopePeers);
    if (envelopeResolved.player2 != 'valid')
      throw 'converted chart envelope did not donate same-song visual metadata';
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "DifficultyVisualFallbackTest.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "DifficultyVisualFallbackTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
