"""Owner-qualified chart paths keep their source title and editor destination separate."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    depth = 0
    begin = source.index("{", start)
    for index in range(begin, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated {marker}")


class SongStorageFolderTest(unittest.TestCase):
    def test_storage_folder_keeps_selected_owner_key(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/Song.hx").read_text()
        fixture = "\n".join([
            "using StringTools;",
            "class Main {",
            method(source, "public static function storageFolder("),
            method(source, "static function validStorageKey("),
            "static function main():Void {",
            "  var chart:Dynamic = {song:'Improbable Outset', compatStorageFolder:'improbable-outset--codename-engine-1234'};",
            "  if (storageFolder(chart) != 'improbable-outset--codename-engine-1234') throw 'selected folder lost';",
            "  Reflect.setField(chart, 'compatStorageFolder', '../foreign');",
            "  if (storageFolder(chart) != 'improbable outset') throw 'unsafe folder accepted';",
            "}",
            "}",
        ])
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            completed = subprocess.run([*HAXE_COMMAND, "-cp", scratch, "--run", "Main"],
                                       cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_editor_routes_sidecars_reload_audio_and_save_through_storage_key(self):
        source = (ROOT / "source/ChartingState.hx").read_text()
        self.assertIn("Song.loadFromJson(song.toLowerCase(), Song.storageFolder(_song))", source)
        self.assertIn("File.saveContent('assets/data/' + Song.storageFolder(_song) + '/' + editorChartFileName()", source)
        self.assertIn("var audioFolder = Song.storageFolder(_song)", source)
        self.assertIn("Reflect.deleteField(data, 'compatStorageFolder')", source)
        self.assertIn("Reflect.deleteField(data, 'compatChartFileName')", source)
        self.assertIn("Reflect.deleteField(data, 'compatStageAuthored')", source)
        self.assertIn("Song.parseJSONshit(FlxG.save.data.autosave, true)", source)
        self.assertIn("Reflect.setField(_song, 'compatStageAuthored', true)", source)
        self.assertIn('FlxG.save.data.autosave = Json.stringify({\n\t\t\t"song": _song', source)

    def test_editor_reads_authored_rows_before_normalizing_events(self):
        source = (ROOT / "source/ChartingState.hx").read_text()
        self.assertLess(source.index("loadRawEditorNotes();"),
                        source.index("ChartEventModel.normalizeSong(_song);"))
        self.assertIn("Reflect.setField(editorCopy, 'notes', sourceNotes)", source)
        chart = ROOT / "export/release/linux/bin/assets/data/slaughter/slaughter-easy.json"
        if not chart.is_file():
            self.skipTest("mounted Modding Plus editor fixture unavailable")
        song = json.loads(chart.read_text())["song"]
        self.assertTrue(any(isinstance(row, list) and len(row) >= 5 and row[4] is True
                            and row[1] < 16
                            for section in song["notes"] for row in section["sectionNotes"]))

    def test_editor_selected_file_round_trip_keeps_lift_note_and_authored_song(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/ChartingState.hx").read_text()
        methods = "\n".join(method(source, marker) for marker in (
            "function loadRawEditorNotes(", "function editorChartFileName(",
            "function editorSongData("))
        fixture = r'''
using StringTools;
class Song {
 public static function storageFolder(song:Dynamic):String
  return Reflect.field(song,"compatStorageFolder");
}
class FNFAssets {
 public static function exists(path:String):Bool
  return path=="assets/data/slaughter/slaughter-easy.json";
 public static function getText(_:String):String
  return '{"song":{"song":"Slaughter","notes":[{"sectionNotes":[[100,3,0,"Lift",true]]}]}}';
}
class CoolUtil {public static function parseJson(raw:String):Dynamic return haxe.Json.parse(raw);}
class DifficultyIcons {public static function getEndingFP(_:Int):String return "-easy";}
class PlayState {public static var storyDifficulty=0;}
class Main {
 var _song:Dynamic;
 public function new() {
  var normalized:Array<Dynamic>=[100,19,0,"Lift",false];
  _song={song:"Slaughter",compatStorageFolder:"slaughter",
   compatChartFileName:"slaughter-easy",notes:[{sectionNotes:[normalized]}]};
 }
''' + methods + r'''
 static function main():Void {
  var editor=new Main();
  editor.loadRawEditorNotes();
  var saved=editor.editorSongData();
  if(saved.song!="Slaughter") throw "authored title changed";
  var row:Array<Dynamic>=cast saved.notes[0].sectionNotes[0];
  if(row[1]!=3 || row[4]!=true)
   throw "authored lift note was rewritten";
  if(Reflect.hasField(saved,"compatStorageFolder") || Reflect.hasField(saved,"compatChartFileName")
   || Reflect.hasField(saved,"compatStageAuthored"))
   throw "runtime owner routing leaked into chart";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            completed = subprocess.run([*HAXE_COMMAND, "-cp", scratch, "--run", "Main"],
                                       cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
