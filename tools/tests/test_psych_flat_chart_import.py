"""Charts saved without the {"song": ...} wrapper are read like wrapped ones."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

SECTIONS = [{'sectionNotes': [[0, 0, 0], [500, 5, 0]], 'mustHitSection': True, 'sectionBeats': 4}]
PAYLOAD = {'song': 'Test', 'bpm': 150, 'speed': 2.5, 'player1': 'bf', 'player2': 'dad',
           'gfVersion': 'gf', 'stage': 'stage', 'needsVoices': True, 'format': 'psych_v1',
           'notes': SECTIONS, 'events': []}


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('unterminated method: ' + marker)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value if isinstance(value, str) else json.dumps(value), newline='\n')


def build_mod(root):
    write(root / 'data/test/test.json', PAYLOAD)
    write(root / 'data/test/test-hard.json', {'song': PAYLOAD})
    # Psych 1.0 saves its event file flat as well. It has no sections.
    write(root / 'data/test/events.json', {'events': [[0, [['Hey!', '', '']]]], 'format': 'psych_v1'})
    write(root / 'songs/test/Inst.ogg', b'fixture')


class PsychFlatChartImportTest(unittest.TestCase):
    def run_haxe(self, folder, main, *args):
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(folder), '--run', main,
                                 *[str(arg).replace('\\', '/') for arg in args]],
                                cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_both_shapes_give_the_same_song_payload(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            write(base / 'Main.hx', '''class Main { static function main() {
var flat:Dynamic = haxe.Json.parse(Sys.args()[0]);
var wrapped:Dynamic = {song: haxe.Json.parse(Sys.args()[0])};
var fromFlat = PsychFamilyChartFields.envelope(flat);
var fromWrapped = PsychFamilyChartFields.envelope(wrapped);
if (fromWrapped != wrapped) throw "a wrapped chart was not handed back as it is";
if (PsychFamilyChartFields.wasFlat(fromWrapped)) throw "a wrapped chart was reported flat";
if (fromFlat == null || fromFlat.song != flat) throw "a flat chart did not become the payload of a wrapper";
if (!PsychFamilyChartFields.wasFlat(fromFlat)) throw "the added wrapper is not marked";
if (haxe.Json.stringify(fromFlat.song) != haxe.Json.stringify(fromWrapped.song)) throw "the two shapes read differently";
if (fromFlat.song.song != "Test" || fromFlat.song.notes.length != 1) throw "payload fields were lost";

// Files that only look like charts.
var sidecars:Array<Dynamic> = [
 haxe.Json.parse('{"song":"Test","events":[]}'),
 haxe.Json.parse('{"song":"Test","notes":["intro","verse"]}'),
 haxe.Json.parse('{"song":"Test","notes":[{"text":"hello"}]}'),
 haxe.Json.parse('{"song":"Test","notes":[]}'),
 haxe.Json.parse('{"events":[[0,[["Hey!","",""]]]],"format":"psych_v1"}'),
 haxe.Json.parse('{"song":{"bpm":100}}'),
 haxe.Json.parse('[1,2,3]')
];
for (sidecar in sidecars)
 if (PsychFamilyChartFields.envelope(sidecar) != null) throw "not a chart, but accepted: " + haxe.Json.stringify(sidecar);
if (PsychFamilyChartFields.envelope(null) != null) throw "null accepted";
// An empty section list is fine next to a tempo.
if (PsychFamilyChartFields.envelope(haxe.Json.parse('{"song":"Test","bpm":100,"notes":[]}')) == null)
 throw "an empty flat chart with a tempo was rejected";
}}
''')
            self.run_haxe(base, 'Main', json.dumps(PAYLOAD))

    def test_importer_reader_counts_flat_and_wrapped_charts_of_one_song(self):
        source = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8')
        methods = '\n'.join(extract_method(source, marker) for marker in (
            'static function isImportFile', 'static function validImportPath', 'static function readSongChart',
            'static function normalizedImportFileName', 'static function importChartNames',
            'static function findImportChartInEntries', 'static function collectAssetCharts',
            'static function isImportChartSidecar', 'static function collectSongNoteDefinitions'))
        fixture = '''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class CoolUtil {
  public static function parseJson(text:String):Dynamic return haxe.Json.parse(text);
}

class NoteTypeCompat {
  public static function isStringType(value:Dynamic):Bool return Std.isOfType(value, String);
  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int return 0;
}

class FlatImport {
  static function getImportDifficultyNames():Array<String> return ["easy", "normal", "hard"];
''' + methods + '''
  static function main():Void {
    var folder = Sys.args()[0] + "/data/test";
    var charts = collectAssetCharts(folder, "test", []);
    if (charts.length != 2) throw "expected the flat and the wrapped chart, got " + charts.length;
    var flat:Dynamic = readSongChart(folder + "/test.json");
    var wrapped:Dynamic = readSongChart(folder + "/test-hard.json");
    if (flat == null || wrapped == null) throw "a chart was rejected";
    if (haxe.Json.stringify(flat.song) != haxe.Json.stringify(wrapped.song)) throw "the two shapes read differently";
    if (!Std.isOfType(flat.song.notes, Array) || flat.song.song != "Test") throw "the flat chart has no song payload";
    if (readSongChart(folder + "/events.json") != null) throw "the event file became a chart";
    // The fork's own loader refuses a chart without the wrapper.
    var forked = NightmareVisionChartCompat.convert(flat, "test.json");
    if (forked.supported) throw "a flat chart was accepted for an engine that requires the wrapper";
    if (forked.diagnostics.join(";").indexOf("[nightmare-vision-chart-invalid]") < 0) throw "missing diagnostic";
    if (!NightmareVisionChartCompat.convert(wrapped, "test-hard.json").supported) throw "the wrapped chart was refused";
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            build_mod(base / 'mod')
            write(base / 'code/FlatImport.hx', fixture)
            self.run_haxe(base / 'code', 'FlatImport', base / 'mod')

    def test_flat_psych_chart_identifies_the_root(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            base = Path(temp)
            build_mod(base / 'mod')
            # The same song with only wrapped, unmarked charts proves nothing.
            write(base / 'plain/data/test/test.json', {'song': {key: value for key, value in PAYLOAD.items() if key != 'format'}})
            write(base / 'plain/songs/test/Inst.ogg', b'fixture')
            write(base / 'code/Main.hx', '''class Main { static function main() {
var base = Sys.args()[0];
var found = ImportRootScanner.scan(base + "/mod", ImportEngine.AUTO);
if (found.length != 1 || found[0].engine != ImportEngine.PSYCH) throw "flat chart root was not classified as Psych";
if (found[0].evidence.join(";").indexOf("Psych Engine flat chart: format=psych_v1 without a song wrapper") < 0)
 throw "flat chart evidence missing: " + found[0].evidence.join(";");
if (ImportRootScanner.scan(base + "/plain", ImportEngine.AUTO).length != 0) throw "an unmarked wrapped chart was treated as engine evidence";
}}
''')
            self.run_haxe(base / 'code', 'Main', base)

    def test_runtime_and_workflow_readers_use_the_shared_check(self):
        song = (ROOT / 'source/Song.hx').read_text(encoding='utf-8')
        self.assertIn('return PsychFamilyChartFields.envelope(parsed);', extract_method(song, 'public static function chartEnvelope'))
        self.assertIn('PsychFamilyChartFields.isFlat(parsed) ? parsed : parsed.song',
                      extract_method(song, 'public static function parseJSONshit'))
        workflow = (ROOT / 'source/ImportWorkflow.hx').read_text(encoding='utf-8')
        self.assertIn('else if (PsychFamilyChartFields.isFlat(parsed))', extract_method(workflow, 'static function readChart'))
        pack = (ROOT / 'source/PsychGlobalPackImporter.hx').read_text(encoding='utf-8')
        self.assertIn('PsychFamilyChartFields.payload(chart)', pack[pack.index('static function chartEnvelopeAtDirectory'):])


if __name__ == '__main__':
    unittest.main()
