"""Focused coverage for bounded validation rejections in song discovery."""

from pathlib import Path
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


class SongImportRejectionDiagnosticsTest(unittest.TestCase):
    def test_rejections_are_structured_bounded_and_not_candidates(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function newSongImportRejectionCollector",
                "static function songImportValidationCode",
                "static function recordSongImportValidationRejection",
                "static function validateAndRecordSongImport",
            )
        )
        fixture = f'''import haxe.io.Path;
using StringTools;

typedef SongImport = {{
  var name:String;
  var inst:String;
  var diffFiles:Array<String>;
  @:optional var convertedCharts:Array<Dynamic>;
  @:optional var engine:String;
}};
typedef SongImportDiscoveryRejection = {{
  var code:String; var song:String; var engine:String; var sourceRoot:String;
  var sourcePath:String; var reason:String; var charts:Array<String>;
  var chartsTruncated:Bool;
}};
typedef SongImportRejectionCollector = {{
  var entries:Array<SongImportDiscoveryRejection>; var total:Int;
  var truncated:Bool; var seen:Map<String, Bool>;
}};
class ModuleFunctions {{
  static inline var MAX_SONG_IMPORT_REJECTIONS:Int = 64;
  static inline var MAX_SONG_IMPORT_REJECTION_CHARTS:Int = 8;
{methods}
  public static function collector():SongImportRejectionCollector
    return newSongImportRejectionCollector();
  public static function checked(rejections:SongImportRejectionCollector, song:SongImport,
      sourceRoot:String, sourcePath:String, engine:String):Bool
    return validateAndRecordSongImport(rejections, song, sourceRoot, sourcePath, engine);
  static function validateSongImport(song:SongImport):String {{
    if (song == null) return 'No song data was provided.';
    if (song.inst == null || song.inst == '') return 'The song is missing Inst.ogg.';
    if (song.name == 'Bad Name') return 'The song name is not valid.';
    if (song.diffFiles == null || song.diffFiles.length == 0)
      return 'The song is missing a difficulty chart.';
    return null;
  }}
}}
class SongImportRejectionFixture {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var collector = ModuleFunctions.collector();
    var selectable:Array<SongImport> = [];
    var missingInstrumental:SongImport = {{
      name: 'No Audio', inst: null, diffFiles: ['donor/data/no-audio-hard.json'],
      engine: 'Psych Engine'
    }};
    if (ModuleFunctions.checked(collector, missingInstrumental,
      'donor', 'donor/data/no-audio', 'Psych Engine')) selectable.push(missingInstrumental);
    if (selectable.length != 0) fail('rejected candidate was made selectable');
    if (collector.total != 1 || collector.entries.length != 1)
      fail('missing instrumental rejection was not retained');
    var first = collector.entries[0];
    if (first.code != 'missing-required-instrumental') fail('wrong rejection code');
    if (first.reason != 'The song is missing Inst.ogg.') fail('validation reason was lost');
    if (first.song != 'No Audio' || first.sourcePath != 'donor/data/no-audio')
      fail('source identity was lost');
    if (first.charts.length != 1 || first.charts[0] != 'donor/data/no-audio-hard.json')
      fail('source chart evidence was lost');
    ModuleFunctions.checked(collector, missingInstrumental,
      'donor', 'donor/data/no-audio', 'Psych Engine');
    if (collector.total != 1) fail('duplicate rejection was counted twice');

    var missingChart:SongImport = {{
      name: 'No Chart', inst: 'donor/songs/no-chart/Inst.ogg', diffFiles: [],
      engine: 'Kade Engine'
    }};
    if (ModuleFunctions.checked(collector, missingChart,
      'donor', 'donor/data/no-chart', 'Kade Engine')) selectable.push(missingChart);
    if (collector.entries[1].code != 'missing-difficulty-chart')
      fail('other validation reasons were not classified');

    var invalidName:SongImport = {{
      name: 'Bad Name', inst: 'donor/songs/bad-name/Inst.ogg',
      diffFiles: ['donor/data/bad-name/normal.json'], engine: 'Generic'
    }};
    if (ModuleFunctions.checked(collector, invalidName,
      'donor', 'donor/data/bad-name', 'Generic')) selectable.push(invalidName);
    if (collector.entries[2].code != 'invalid-song-import'
      || collector.entries[2].reason != 'The song name is not valid.')
      fail('generic validation reason was not retained');

    var manyCharts:Array<String> = [];
    for (i in 0...10) manyCharts.push('donor/data/bad-name/chart-' + i + '.json');
    var tooManyCharts:SongImport = {{
      name: 'Too Many Charts', inst: null, diffFiles: manyCharts, engine: 'Generic'
    }};
    ModuleFunctions.checked(collector, tooManyCharts,
      'donor', 'donor/data/too-many', 'Generic');
    if (collector.entries[3].charts.length != 8 || !collector.entries[3].chartsTruncated)
      fail('per-rejection chart evidence was not bounded');

    for (i in 0...65) {{
      var candidate:SongImport = {{
        name: 'Missing ' + i, inst: null, diffFiles: ['donor/data/missing-' + i + '/hard.json'],
        engine: 'Generic'
      }};
      ModuleFunctions.checked(collector, candidate,
        'donor', 'donor/data/missing-' + i, 'Generic');
    }}
    if (collector.entries.length != 64) fail('global rejection cap was not enforced');
    if (collector.total != 69 || !collector.truncated)
      fail('truncation count was not retained');
    if (selectable.length != 0) fail('a rejected row entered the candidate list');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "SongImportRejectionFixture.hx"
            fixture_path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "--run", "SongImportRejectionFixture"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_discovery_paths_forward_rejections_to_the_preview_and_report(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        workflow = (ROOT / "source/ImportWorkflow.hx").read_text()
        settings = (ROOT / "source/ImportSettingsState.hx").read_text()
        for marker in (
            "static function appendAssetSongImports",
            "static function discoverLegacySongImportsDetailed",
            "static function discoverVSliceSongImports",
            "static function discoverCodenameSongsFromBase",
        ):
            self.assertIn("validateAndRecordSongImport", extract_method(module, marker))
        detailed = extract_method(module, "static public function discoverSongImportsDetailed")
        self.assertIn("rejectedSongs: rejectionCollector.entries", detailed)
        self.assertIn("rejectedSongCount: rejectionCollector.total", detailed)
        self.assertIn("rejectedSongsTruncated: rejectionCollector.truncated", detailed)
        self.assertIn("discovery.rejectedSongs", workflow)
        self.assertIn("[SONG REJECTED ", workflow)
        self.assertIn("[REJECTED SONG ", settings)
        self.assertIn("MAX_SONG_IMPORT_REJECTIONS:Int = 64", module)
        self.assertIn("MAX_SONG_IMPORT_REJECTION_CHARTS:Int = 8", module)


if __name__ == "__main__":
    unittest.main()
