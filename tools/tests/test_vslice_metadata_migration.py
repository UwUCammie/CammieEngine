"""Older V-Slice metadata (2.0.x, 2.1.x) is read with the current field names."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
CHART = {"version": "2.0.0", "scrollSpeed": {"normal": 1}, "notes": {"normal": [{"t": 0, "d": 0}]}}


def convert_and_check(metadata: dict, checks: str) -> subprocess.CompletedProcess:
    main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var metadata:Dynamic = haxe.Json.parse({json.dumps(json.dumps(metadata))});
    var before = haxe.Json.stringify(metadata);
    var result = VSliceImporter.convert(metadata, haxe.Json.parse({json.dumps(json.dumps(CHART))}), "fixture");
    if (haxe.Json.stringify(metadata) != before) fail("caller metadata rewritten");
    var song:Dynamic = result.charts[0].chart.song;
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


def base(version: str, play_data: dict) -> dict:
    data = {"difficulties": ["normal"], "stage": "mainStage"}
    data.update(play_data)
    return {"version": version, "songName": "Old Song", "playData": data, "timeChanges": [{"t": 0, "bpm": 100}]}


class VSliceMetadataMigrationTest(unittest.TestCase):
    def test_v2_0_playable_characters_and_note_skin_are_migrated(self):
        meta = base("2.0.0", {"playableChars": {"pico": {"g": "nene", "o": "darnell", "i": "pico"}}, "noteSkin": "pixel"})
        result = convert_and_check(meta, '''
    if (song.player1 != "pico" || song.player2 != "darnell" || song.gf != "nene") fail("characters " + song.player1 + "/" + song.player2 + "/" + song.gf);
    if (song.uiType != "pixel") fail("note style " + song.uiType);
    if (codes.indexOf("metadata-migrated") < 0) fail("migration diagnostic");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_v2_0_long_names_and_blank_girlfriend(self):
        meta = base("2.0.0", {"playableChars": {"bf": {"girlfriend": "", "opponent": "spooky"}}})
        result = convert_and_check(meta, '''
    if (song.player1 != "bf" || song.player2 != "spooky" || song.gf != "no-gf") fail("characters");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_v2_1_note_skin_maps_to_note_style(self):
        meta = base("2.1.0", {"characters": {"player": "bf", "opponent": "senpai", "girlfriend": "gf"}, "noteSkin": "pixel"})
        result = convert_and_check(meta, '''
    if (song.uiType != "pixel" || song.player2 != "senpai") fail("note skin");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_metadata_is_not_migrated(self):
        meta = base("2.2.4", {"characters": {"player": "bf", "opponent": "dad", "girlfriend": "gf"},
                              "noteStyle": "funkin", "noteSkin": "pixel",
                              "playableChars": {"pico": {"o": "darnell"}}})
        result = convert_and_check(meta, '''
    if (song.player1 != "bf" || song.player2 != "dad" || song.uiType != "normal") fail("current fields win");
    if (codes.indexOf("metadata-migrated") >= 0) fail("no migration expected");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
