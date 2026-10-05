"""NMV chart normalization follows the bundled generic engine schema."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionChartCompatTest(unittest.TestCase):
    def test_positive_field_counts_and_invalid_declarations(self):
        self.run_haxe(r'''for (lanes in [1, 3, 4]) {
  var result = NightmareVisionChartCompat.convert({song:{keys:4, lanes:lanes, notes:[]}});
  if (!result.supported || result.chart.song.lanes != lanes) throw "positive field count rejected";
}
for (lanes in ([0, -1, 1.5, "bogus", "3junk"]:Array<Dynamic>)) {
  var result = NightmareVisionChartCompat.convert({song:{keys:4, lanes:lanes, notes:[]}});
  if (result.supported) throw "invalid field count accepted";
}''')

    def run_haxe(self, body):
        main = "class Main { static function main() {\n" + body + "\n} }\n"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            (Path(temp) / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", temp, "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nmv2_fields_and_dynamic_absolute_lane_ownership(self):
        self.run_haxe(r'''var chart:Dynamic = {song:{format:"nmv2", keys:6, lanes:2, preferredNoteAmount:4,
  gfVersion:"gf-alt", needsVoices:false, speed:1.25,
  notes:[{mustHitSection:false, sectionBeats:3, sectionNotes:[[0,0,0],[100,6,0]]}]}};
var result = NightmareVisionChartCompat.convert(chart, "normal.json");
if (!result.supported) throw result.diagnostics.join(";");
var song = chart.song;
if (song.preferredNoteAmount != 6) throw "NMV keys were not mapped to the native key count";
if (song.gf != "gf-alt") throw "NMV gfVersion was not mapped";
if (song.format != "nmv2") throw "normalized NMV format was changed";
if (song.notes[0].lengthInSteps != 12) throw "sectionBeats were not mapped to native steps";
if (song.notes[0].sectionNotes[0][1] != 0 || song.notes[0].sectionNotes[1][1] != 6)
  throw "already-normalized NMV lanes were rewritten";
if (!ChartNoteOwnership.mustPress("nmv2", 0, false, 6)
  || ChartNoteOwnership.mustPress("nmv2", 6, true, 6))
  throw "NMV absolute field ids did not use the authored key count";
''')

    def test_source_layout_defaults_are_explicit_on_each_imported_chart(self):
        self.run_haxe(r'''var chart:Dynamic = {song:{format:"nmv2", notes:[]}};
var result = NightmareVisionChartCompat.convert(chart);
if (!result.supported || chart.song.keys != 4 || chart.song.lanes != 2
  || chart.song.preferredNoteAmount != 4 || chart.song.arrowSkins.join(",") != "default,default"
  || chart.song.trackSwap != false)
  throw "missing layout did not receive the source chart defaults";
''')

    def test_legacy_nmv_chart_lane_swap_matches_source_chart_loader(self):
        self.run_haxe(r'''var chart:Dynamic = {song:{keys:4, lanes:2, bpm:120,
  notes:[
    {mustHitSection:false, sectionNotes:[[0,0,0],[100,5,0]]},
    {mustHitSection:true, sectionNotes:[[200,2,0]]}
  ]}};
var result = NightmareVisionChartCompat.convert(chart, "legacy.json");
if (!result.supported) throw result.diagnostics.join(";");
if (chart.song.format != "nmv2") throw "legacy chart did not receive NMV's normalized marker";
if (chart.song.preferredNoteAmount != 4) throw "default NMV key count was not mapped";
if (chart.song.notes[0].sectionNotes[0][1] != 4
  || chart.song.notes[0].sectionNotes[1][1] != 1
  || chart.song.notes[1].sectionNotes[0][1] != 2)
  throw "legacy lane blocks do not match NMV Chart.correctFormat";
''')

    def test_psych_v1_convert_uses_source_family_legacy_normalization(self):
        self.run_haxe(r'''var chart:Dynamic = {song:{format:"psych_v1_convert", keys:4, lanes:2,
  notes:[
    {mustHitSection:false, sectionNotes:[[0,0,0],[100,5,0]]},
    {mustHitSection:true, sectionNotes:[[200,2,0]]}
  ]}};
var result = NightmareVisionChartCompat.convert(chart, "converted.json");
if (!result.supported) throw result.diagnostics.join(";");
if (chart.song.format != "nmv2") throw "psych_v1_convert did not receive NMV's normalized marker";
if (chart.song.notes[0].sectionNotes[0][1] != 4
  || chart.song.notes[0].sectionNotes[1][1] != 1
  || chart.song.notes[1].sectionNotes[0][1] != 2)
  throw "psych_v1_convert lanes do not match NMV Chart.correctFormat";
''')

    def test_unsupported_engine_features_are_reported_without_guessing(self):
        self.run_haxe(r'''var chart:Dynamic = {song:{format:"codenameChart", keys:4, lanes:3,
  arrowSkins:["one", "two"], trackSwap:true,
  notes:[{mustHitSection:false, sectionNotes:[[0,8,0]]}]}};
var result = NightmareVisionChartCompat.convert(chart, "custom.json");
if (result.supported) throw "unsupported format/lanes were accepted";
var joined = result.diagnostics.join(";");
for (code in ["nightmare-vision-unsupported-chart-format",
  "nightmare-vision-unsupported-track-swap"])
  if (joined.indexOf("[" + code + "]") < 0) throw "missing diagnostic " + code;
if (chart.song.format != "codenameChart") throw "unsupported chart was rewritten";
if (chart.song.notes[0].sectionNotes[0][1] != 8)
  throw "unsupported third-field note lane was reassigned";
''')

    def test_authored_per_field_skins_are_retained(self):
        self.run_haxe(r'''var chart:Dynamic = {song:{format:"nmv2", keys:4, lanes:2,
  arrowSkins:["first", "second"], notes:[]}};
var result = NightmareVisionChartCompat.convert(chart, "skins.json");
if (!result.supported || chart.song.arrowSkins.join(",") != "first,second")
  throw "source playfield note skins were not retained";
for (diagnostic in result.diagnostics)
  if (diagnostic.indexOf("unsupported-arrow-skins") >= 0)
    throw "supported source skins were diagnosed as unsupported";
''')


if __name__ == "__main__":
    unittest.main()
