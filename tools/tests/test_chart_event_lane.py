"""Interpreter coverage for the chart editor's event timeline model."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class ChartEventLaneTest(unittest.TestCase):
    def test_imported_events_and_bpm_section_navigation(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''class ChartEventLaneFixture {
 static function main() {
  var song:Dynamic = {
   bpm: 120,
   events: haxe.Json.parse('[[2000, [["Native", "a"]]], {"t": 2500, "e": "Modern", "v": ["b"]}]'),
   notes: [
    {lengthInSteps: 16, changeBPM: false, bpm: 120,
     sectionNotes: haxe.Json.parse('[[1000, -1, "Legacy", "x"], [1200, 0, 0]]')},
    {lengthInSteps: 8, changeBPM: true, bpm: 60, sectionNotes: []},
    {lengthInSteps: 16, changeBPM: false, bpm: 60, sectionNotes: []}
   ]
  };
  ChartEventModel.normalizeSong(song);
  if(ChartEventModel.list(song.events).length != 3 || song.notes[0].sectionNotes.length != 1)
   throw "legacy or object events were not made editable";
  if(ChartEventModel.sectionStart(song.notes, song.bpm, 1) != 2000
   || ChartEventModel.sectionStart(song.notes, song.bpm, 2) != 4000
   || ChartEventModel.sectionStart(song.notes, song.bpm, 3) != 8000)
   throw "section starts ignored a BPM change or nonstandard length";
  if(ChartEventModel.sectionAtTime(song.notes, song.bpm, 1999) != 0
   || ChartEventModel.sectionAtTime(song.notes, song.bpm, 2000) != 1
   || ChartEventModel.sectionAtTime(song.notes, song.bpm, 4000) != 2)
   throw "exact section boundaries were assigned incorrectly";
  var companion:Dynamic = haxe.Json.parse('{"events":{"events":[[1,2000,0,"Native;a"],[1,2500,0,"Different;c"],[2,4000,0,"AtBoundary;d"]]}}');
  var before = SongEvents.collect(SongEvents.fromSong(song), SongEvents.fromSong(companion));
  ChartEventModel.mergeCompanion(song, companion);
  var entries = ChartEventModel.list(song.events);
  if(entries.length != 5 || entries[0].time != 1000 || entries[4].time != 4000)
   throw "companion events were not merged in timestamp order";
  var saved = haxe.Json.stringify({song: song});
  var reloaded = haxe.Json.parse(saved).song;
  var after = SongEvents.collect(SongEvents.fromSong(reloaded), SongEvents.fromSong(companion));
  if(before.length != after.length) throw "save/reload changed event dispatch count";
  for(i in 0...before.length)
   if(before[i].time != after[i].time || before[i].name != after[i].name
    || before[i].v1 != after[i].v1)
    throw "save/reload changed event dispatch order or values";

  var sidecar:Dynamic = haxe.Json.parse('{"events":{"events":[[1,3000,0,"Focus Camera;0.1;0.2"]]}}');
  var sidecarBefore = haxe.Json.stringify(sidecar);
  var owned:Dynamic = {song:"owner chart", bpm:120, compatStorageFolder:"owner-qualified-song",
   compatChartFileName:"owner-qualified-song-hard", events:[], notes:[]};
  ChartEventModel.normalizeSong(owned);
  ChartEventModel.mergeCompanion(owned, sidecar);
  var imported = ChartEventModel.list(owned.events);
  if(imported.length != 1 || SongEvents.editorSidecarSourceKey(imported[0].event) == null)
   throw "companion event did not retain its source identity";
  ChartEventModel.update(owned.events, imported[0], 3250, "Focus Camera", "0.9", "0.2", "");
  var editedSave = haxe.Json.stringify({song:owned});
  var editedReload:Dynamic = haxe.Json.parse(editedSave).song;
  ChartEventModel.normalizeSong(editedReload);
  ChartEventModel.mergeCompanion(editedReload, sidecar);
  var editedRows = ChartEventModel.list(editedReload.events);
  if(editedRows.length != 1 || editedRows[0].time != 3250 || editedRows[0].event[1] != "0.9")
   throw "edited sidecar row duplicated or reverted after editor reload";
  var editedRuntime = SongEvents.collect(SongEvents.fromSong(editedReload), SongEvents.fromSong(sidecar));
  if(editedRuntime.length != 1 || editedRuntime[0].time != 3250 || editedRuntime[0].v1 != "0.9")
   throw "runtime collection replayed the old sidecar row after an edit";
  if(editedReload.compatStorageFolder != "owner-qualified-song"
   || editedReload.compatChartFileName != "owner-qualified-song-hard")
   throw "event roundtrip changed owner or selected difficulty routing";

  var deleted:Dynamic = {song:"owner chart", compatStorageFolder:"owner-qualified-song",
   compatChartFileName:"owner-qualified-song-hard", events:[], notes:[]};
  ChartEventModel.normalizeSong(deleted);
  ChartEventModel.mergeCompanion(deleted, sidecar);
  var deleteRef = ChartEventModel.list(deleted.events)[0];
  if(!ChartEventModel.removeSongEvent(deleted, deleteRef)) throw "sidecar event deletion failed";
  var deletedSave = haxe.Json.stringify({song:deleted});
  var deletedReload:Dynamic = haxe.Json.parse(deletedSave).song;
  ChartEventModel.normalizeSong(deletedReload);
  ChartEventModel.mergeCompanion(deletedReload, sidecar);
  if(ChartEventModel.list(deletedReload.events).length != 0)
   throw "deleted sidecar event returned after editor reload";
  if(SongEvents.collect(SongEvents.fromSong(deletedReload), SongEvents.fromSong(sidecar)).length != 0)
   throw "runtime collection replayed a deleted sidecar event";
  if(haxe.Json.stringify(sidecar) != sidecarBefore)
   throw "editor roundtrip modified the source sidecar";
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "ChartEventLaneFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "ChartEventLaneFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
