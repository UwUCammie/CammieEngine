"""V-Slice time signatures set the native section (measure) length."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def convert_and_check(time_changes: list, notes: list, checks: str) -> subprocess.CompletedProcess:
    metadata = {
        "version": "2.2.4",
        "songName": "Meter Song",
        "playData": {"difficulties": ["normal"], "characters": {"player": "bf", "opponent": "dad"}, "stage": "mainStage"},
        "timeChanges": time_changes,
    }
    chart = {"version": "2.0.0", "scrollSpeed": {"normal": 1}, "notes": {"normal": notes}}
    main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertJson({json.dumps(json.dumps(metadata))}, {json.dumps(json.dumps(chart))}, "fixture");
    var song:Dynamic = result.charts[0].chart.song;
    var sections:Array<Dynamic> = cast song.notes;
    var codes = [for (finding in result.diagnostics) finding.code];
{checks}
  }}
}}
'''
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        (Path(folder) / "Main.hx").write_text(main, newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
            cwd=ROOT, capture_output=True, text=True,
        )


class VSliceTimeSignatureTest(unittest.TestCase):
    def test_three_four_sections_are_twelve_steps_and_notes_follow_the_measures(self):
        # 120 bpm: a step is 125 ms, so a 3/4 measure is 1500 ms.
        notes = [{"t": 0, "d": 0}, {"t": 1400, "d": 1}, {"t": 1500, "d": 2}, {"t": 2900, "d": 3}, {"t": 4400, "d": 4}]
        result = convert_and_check([{"t": 0, "bpm": 120, "n": 3, "d": 4}], notes, '''
    if (sections.length != 3) fail("section count " + sections.length);
    for (section in sections) {
      if (section.lengthInSteps != 12) fail("section length " + section.lengthInSteps);
      var signature:Array<Int> = cast section.timeSignature;
      if (signature == null || signature[0] != 3 || signature[1] != 4) fail("time signature kept");
    }
    var counts = [for (section in sections) (cast section.sectionNotes:Array<Dynamic>).length];
    if (counts[0] != 2 || counts[1] != 2 || counts[2] != 1) fail("notes per measure " + counts);
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_eighth_note_meters_use_quarter_note_steps(self):
        result = convert_and_check([{"t": 0, "bpm": 120, "n": 7, "d": 8}], [{"t": 3000, "d": 0}], '''
    if (sections[0].lengthInSteps != 14) fail("7/8 length " + sections[0].lengthInSteps);
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_meter_change_mid_song_switches_section_length(self):
        result = convert_and_check(
            [{"t": 0, "bpm": 120, "n": 4, "d": 4}, {"t": 4000, "bpm": 120, "n": 6, "d": 8}],
            [{"t": 7000, "d": 0}], '''
    if (sections[0].lengthInSteps != 16 || sections[1].lengthInSteps != 16) fail("4/4 part");
    if (Reflect.hasField(sections[0], "timeSignature")) fail("4/4 section marked");
    if (sections[2].lengthInSteps != 12) fail("6/8 part " + sections[2].lengthInSteps);
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_four_four_and_absent_signatures_keep_sixteen_step_sections(self):
        for changes in ([{"t": 0, "bpm": 150}], [{"t": 0, "bpm": 150, "n": 4, "d": 4}]):
            result = convert_and_check(changes, [{"t": 0, "d": 0}, {"t": 5000, "d": 1}], '''
    if (sections.length != 4) fail("section count " + sections.length);
    for (section in sections) {
      if (section.lengthInSteps != 16) fail("length");
      if (Reflect.hasField(section, "timeSignature")) fail("4/4 marked");
    }
''')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unusable_signature_falls_back_to_four_four_with_a_warning(self):
        result = convert_and_check([{"t": 0, "bpm": 120, "n": 0, "d": 4}], [{"t": 0, "d": 0}], '''
    if (sections[0].lengthInSteps != 16) fail("fallback length");
    if (codes.indexOf("invalid-time-signature") < 0) fail("warning");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
