"""Psych and Nightmare Vision charts name the girlfriend the same way."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


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


class PsychFamilyChartFieldsTest(unittest.TestCase):
    def run_haxe(self, source, main='Main'):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            (Path(temp) / (main + '.hx')).write_text(source, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', main],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_girlfriend_resolution_order_and_blank_values(self):
        self.run_haxe('''class Main { static function main() {
function expect(song:Dynamic, wanted:String) {
 var found = PsychFamilyChartFields.girlfriend(song);
 if (found != wanted) throw haxe.Json.stringify(song) + " resolved to '" + found + "', expected '" + wanted + "'";
}
expect({gf:"native"}, "native");
expect({gfVersion:"modern"}, "modern");
expect({player3:"legacy"}, "legacy");
expect({gf:"native", gfVersion:"modern", player3:"legacy"}, "native");
expect({gfVersion:"modern", player3:"legacy"}, "modern");
expect({gf:"", gfVersion:" ", player3:"legacy"}, "legacy");
expect({gf:"null", gfVersion:"modern"}, "modern");
expect({player1:"bf"}, "");
expect(null, "");
// Outside the family player3 can be a third singer.
if (PsychFamilyChartFields.girlfriend({player3:"legacy"}, false) != "") throw "player3 was read for an unknown engine";
if (PsychFamilyChartFields.girlfriend({gfVersion:"modern", player3:"legacy"}, false) != "modern") throw "gfVersion lost";

var song:Dynamic = {player3:"legacy"};
if (!PsychFamilyChartFields.normalizeGirlfriend(song) || song.gf != "legacy") throw "player3 was not written to gf";
song = {gf:"native", gfVersion:"modern"};
if (!PsychFamilyChartFields.normalizeGirlfriend(song) || song.gf != "native") throw "an authored gf was replaced";
song = {player1:"bf"};
if (PsychFamilyChartFields.normalizeGirlfriend(song) || Reflect.hasField(song, "gf")) throw "a girlfriend was invented";

song = {needsVoices:false, speed:2.5};
PsychFamilyChartFields.fillSharedDefaults(song);
if (song.needsVoices != false || song.speed != 2.5) throw "authored values were replaced by defaults";
song = {};
PsychFamilyChartFields.fillSharedDefaults(song);
if (song.needsVoices != true || song.speed != 1) throw "defaults were not filled";
}}
''')

    def test_both_engines_import_the_same_girlfriend(self):
        source = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8')
        method = extract_method(source, 'static function applyImportedVisualMetadata(')
        self.run_haxe('''typedef SongImport = Dynamic;

class ImportEngine {
 public static inline var PSYCH:String = "Psych Engine";
 public static inline var NIGHTMARE_VISION:String = "Nightmare Vision";
}

class Fields {
''' + method + '''
 static function psych(song:Dynamic):Dynamic {
  applyImportedVisualMetadata(song, {engine:ImportEngine.PSYCH, gf:"gf", p1:"bf", p2:"dad"});
  return song.gf;
 }
 static function fork(song:Dynamic):Dynamic {
  song.notes = [];
  var result = NightmareVisionChartCompat.convert({song:song});
  if (!result.supported) throw result.diagnostics.join(";");
  return song.gf;
 }
 static function main() {
  var cases:Array<{chart:String, wanted:Null<String>}> = [
   {chart:'{"gf":"native"}', wanted:"native"},
   {chart:'{"gfVersion":"modern"}', wanted:"modern"},
   {chart:'{"player3":"legacy"}', wanted:"legacy"},
   {chart:'{"gf":"native","gfVersion":"modern","player3":"legacy"}', wanted:"native"},
   {chart:'{"player1":"bf"}', wanted:null}
  ];
  for (item in cases) {
   var fromPsych = psych(haxe.Json.parse(item.chart));
   var fromFork = fork(haxe.Json.parse(item.chart));
   if (fromPsych != item.wanted) throw "Psych import of " + item.chart + " gave " + fromPsych;
   if (fromFork != item.wanted) throw "Nightmare Vision import of " + item.chart + " gave " + fromFork;
  }
  // A song-level girlfriend still fills a Psych chart that names none.
  var inherited:Dynamic = {};
  applyImportedVisualMetadata(inherited, {engine:ImportEngine.PSYCH, gf:"custom", p1:"bf", p2:"dad"});
  if (inherited.gf != "custom") throw "song-level girlfriend was not applied";
 }
}
''', main='Fields')

    def test_every_reader_calls_the_shared_resolver(self):
        module = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8')
        self.assertIn('PsychFamilyChartFields.normalizeGirlfriend(chartSong)',
                      extract_method(module, 'static function applyImportedVisualMetadata('))
        self.assertIn('PsychFamilyChartFields.girlfriend(chartSong, false)', module)
        fork = (ROOT / 'source/NightmareVisionChartCompat.hx').read_text(encoding='utf-8')
        self.assertIn('PsychFamilyChartFields.normalizeGirlfriend(song);', fork)
        self.assertNotIn("'player3'", fork)
        roots = (ROOT / 'source/ImportInstalledDependencyRoots.hx').read_text(encoding='utf-8')
        self.assertIn('var girlfriend = PsychFamilyChartFields.girlfriend(song);', roots)
        self.assertNotIn("'player3'", roots)


if __name__ == '__main__':
    unittest.main()
