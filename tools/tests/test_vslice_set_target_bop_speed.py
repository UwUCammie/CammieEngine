"""The built-in dance rate event is routed to one base-game function."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


class VSliceSetTargetBopSpeedTest(unittest.TestCase):
    def run_fixture(self, body):
        fixture = f'''import haxe.Json;
class BopSpeedFixture {{
    static function fail(message:String):Void throw message;
    static function main() {{
        {body}
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "BopSpeedFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-main", "BopSpeedFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_event_routes_target_and_rate_into_the_value_slots(self):
        self.run_fixture('''
        var route = EngineCompat.routeVSliceEvent("SetTargetBopSpeed", {target: "dad", rate: 2});
        if (route == null || route.name != "Set Target Bop Speed" || route.v1 != "dad" || route.v2 != "2")
            fail("object payload route");
        var defaults = EngineCompat.routeVSliceEvent("SetTargetBopSpeed", {});
        if (defaults.v1 != "boyfriend" || defaults.v2 != "1") fail("default target and rate");
        if (EngineCompat.eventName("Set Target Bop Speed") != "Set Target Bop Speed") fail("display name");
        // A converted chart keeps the authored name with its payload in the first slot.
        var row = EngineCompat.routeLegacyEvent("SetTargetBopSpeed",
            Json.stringify({target: "gf", rate: 0.5}), "", "");
        if (row.name != "Set Target Bop Speed" || row.v1 != "gf" || row.v2 != "0.5") fail("chart row route");
        var payload = EngineCompat.hxcSongEventPayload(["Set Target Bop Speed", "dad", "4", ""]);
        if (payload.eventData.value.target != "dad" || payload.eventData.value.rate != "4")
            fail("script payload field names");
        ''')

    def test_rate_is_turned_into_whole_beats(self):
        self.run_fixture('''
        if (EngineCompat.danceIntervalBeats(1) != 1 || EngineCompat.danceIntervalBeats(2) != 2
            || EngineCompat.danceIntervalBeats(4) != 4)
            fail("whole beat rates");
        // Faster than once a beat is capped at every beat; zero stops the dance.
        if (EngineCompat.danceIntervalBeats(0.5) != 1) fail("sub-beat rate");
        if (EngineCompat.danceIntervalBeats(0) != 0 || EngineCompat.danceIntervalBeats(-3) != 0)
            fail("zero means never");
        if (EngineCompat.danceIntervalBeats(Math.NaN) != 1) fail("unreadable rate keeps the default");
        ''')

    def test_importer_no_longer_reports_the_event_as_unknown(self):
        metadata = {
            "version": "2.2.0", "songName": "Bop Fixture",
            "playData": {"difficulties": ["normal"],
                         "characters": {"player": "bf", "opponent": "dad"}, "stage": "stage"},
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {
            "version": "2.0.0", "scrollSpeed": {"normal": 1.0},
            "notes": {"normal": [{"t": 100, "d": 0}]},
            "events": [{"t": 100, "e": "SetTargetBopSpeed", "v": {"target": "dad", "rate": 2}}],
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            metadata_path = Path(folder) / "bop-metadata.json"
            chart_path = Path(folder) / "bop-chart.json"
            metadata_path.write_text(json.dumps(metadata), newline="\n")
            chart_path.write_text(json.dumps(chart), newline="\n")
            self.run_fixture(f'''
        var result = VSliceImporter.convertFiles({json.dumps(metadata_path.as_posix())},
            {json.dumps(chart_path.as_posix())});
        for (finding in result.diagnostics)
            if (finding.code == "foreign-event-preserved") fail("still reported: " + finding.message);
        ''')

    def test_playstate_event_switch_calls_the_base_function(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        case = source.index("case 'Set Target Bop Speed':")
        self.assertIn("setTargetDanceRate(e.v1,", source[case:case + 200])
        method = source[source.index("public function setTargetDanceRate("):
            source.index("function characterDanceDue(")]
        # Props keep whole beats; characters keep the authored fraction.
        self.assertIn("EngineCompat.danceIntervalBeats(rate)", method)
        self.assertIn("actor.danceEvery = Character.danceRate(rate);", method)
        for name in ["'boyfriend' | 'bf' | 'player'", "'dad' | 'opponent'", "'girlfriend' | 'gf'"]:
            self.assertIn(name, method)
        self.assertIn("PlayState.globalSprites.get(name)", method)


if __name__ == "__main__":
    unittest.main()
