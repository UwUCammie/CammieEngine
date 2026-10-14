"""V-Slice note params survive import and are readable from the native note."""
from haxe_test_support import HAXE_COMMAND

import json
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def run_main(main_source: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        (Path(folder) / "Main.hx").write_text(main_source, newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
            cwd=ROOT, capture_output=True, text=True,
        )


def note_param_api() -> str:
    """The params field and getParam method, copied out of Note.hx."""
    source = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
    start = source.index("@:keep public var params:Array<Dynamic>")
    end = source.index("return null;\n\t}", start) + len("return null;\n\t}")
    return source[start:end]


class VSliceNoteParamsTest(unittest.TestCase):
    def test_params_are_kept_on_the_row_and_rows_without_params_are_unchanged(self):
        metadata = {
            "version": "2.2.4", "songName": "Param Song",
            "playData": {"difficulties": ["normal"], "characters": {"player": "bf", "opponent": "dad"}, "stage": "mainStage"},
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {"version": "2.0.0", "scrollSpeed": {"normal": 1}, "notes": {"normal": [
            {"t": 100, "d": 1, "k": "custom-kind", "p": [{"n": "speed", "v": 2}, {"n": "", "v": 9}, {"n": "label", "v": "fast"}]},
            {"t": 200, "d": 2},
            {"t": 300, "d": 3, "k": "alt", "p": [{"n": "tag", "v": {"x": 1}}]},
        ]}}
        result = run_main(f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertJson({json.dumps(json.dumps(metadata))}, {json.dumps(json.dumps(chart))}, "fixture");
    var rows:Array<Array<Dynamic>> = [];
    for (section in (cast result.charts[0].chart.song.notes:Array<Dynamic>))
      for (row in (cast section.sectionNotes:Array<Dynamic>)) rows.push(cast row);
    if (rows.length != 3) fail("row count");
    var params = NoteRowParams.read(rows[0]);
    if (params == null || params.length != 2) fail("params kept, blank names dropped");
    if (params[0].name != "speed" || params[0].value != 2 || params[1].name != "label" || params[1].value != "fast") fail("param values");
    if (rows[1].length != 3) fail("plain row grew to " + rows[1].length);
    if (NoteRowParams.read(rows[1]) != null) fail("plain row has params");
    // The alt marker keeps column 3 and the params sit in their own column.
    if (rows[2][3] != 1) fail("alt marker moved");
    var altParams = NoteRowParams.read(rows[2]);
    if (altParams == null || altParams[0].value.x != 1) fail("alt row params");
    for (index in 4...NoteRowParams.SLOT) if (rows[2][index] != null) fail("padding at " + index);
    if (CodenameNoteMetadata.read(rows[2]) != null) fail("params read as a Codename tag");
  }}
}}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_note_exposes_params_and_get_param(self):
        result = run_main('''class FakeNote {
  public function new() {}
  ''' + note_param_api() + '''
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var row:Array<Dynamic> = NoteRowParams.apply([100, 1, 0], [{name: "speed", value: 2}]);
    var note = new FakeNote();
    note.params = NoteRowParams.read(row);
    if (note.params[0].name != "speed") fail("params view");
    if (note.getParam("speed") != 2) fail("getParam");
    if (note.getParam("missing") != null) fail("missing param");
    if (new FakeNote().getParam("speed") != null) fail("note without params");
    if (NoteRowParams.apply([1, 2, 3], null).length != 3) fail("no params, no column");
  }
}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_chart_loader_hands_row_params_to_head_and_hold_notes(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("swagNote.params = NoteRowParams.read(songNotes);", source)
        self.assertIn("sustainNote.params = swagNote.params;", source)


if __name__ == "__main__":
    unittest.main()
