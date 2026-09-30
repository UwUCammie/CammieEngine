"""Focused checks for the isolated native chart-editor round-trip smoke."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
TOOLS = ROOT / "tools"
HAXE = ROOT / ".tools/haxe/haxe"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_runtime_smoke_matrix as smoke_matrix


class ChartEditorSmokeTest(unittest.TestCase):
    def test_fixture_is_private_and_preserves_installed_chart_and_sidecar(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp_root = Path(folder)
            source_root = temp_root / "runtime"
            source_data = source_root / "assets" / "data"
            selected = source_data / "owned-song"
            other = source_data / "other-song"
            selected.mkdir(parents=True)
            other.mkdir()
            chart_bytes = b'{"song":{"song":"Owned Name","notes":[]}}\n'
            sidecar_bytes = b'{"events":[[250,[ ["Existing", "kept"] ]]]}\n'
            (selected / "owned-song-hard.json").write_bytes(chart_bytes)
            (selected / "events.json").write_bytes(sidecar_bytes)
            (other / "other-song.json").write_text('{"song":{}}', encoding="utf-8")
            (source_data / "options.json").write_text("{}", encoding="utf-8")

            overlay_root = temp_root / "overlay"
            overlay_root.mkdir()
            case = smoke_matrix.SmokeCase(
                "chart-editor", "editor round-trip", "owned-song", "owned-song-hard", "hard"
            )
            smoke_matrix._prepare_case_overlay(source_root, overlay_root, case)
            overlay_sidecar, expected_bytes = smoke_matrix.prepare_chart_editor_fixture(
                overlay_root, source_root, case.folder, case.chart
            )

            self.assertFalse((overlay_root / "assets/data/owned-song").is_symlink())
            self.assertTrue((overlay_root / "assets/data/other-song").is_symlink())
            self.assertEqual((overlay_root / "assets/data/owned-song/owned-song-hard.json").read_bytes(),
                             chart_bytes)
            self.assertEqual(overlay_sidecar.read_bytes(), expected_bytes)
            self.assertEqual(json.loads(expected_bytes), smoke_matrix.CHART_EDITOR_FIXTURE)
            self.assertEqual((selected / "owned-song-hard.json").read_bytes(), chart_bytes)
            self.assertEqual((selected / "events.json").read_bytes(), sidecar_bytes)

    def test_editor_smoke_enters_editor_and_runs_real_edit_delete_autosave_reload(self):
        main = (SOURCE / "Main.hx").read_text(encoding="utf-8")
        state = (SOURCE / "RuntimeSmokeState.hx").read_text(encoding="utf-8")
        harness = (SOURCE / "RuntimeSmokeHarness.hx").read_text(encoding="utf-8")
        charting = (SOURCE / "ChartingState.hx").read_text(encoding="utf-8")
        runner = (TOOLS / "run_runtime_smoke_matrix.py").read_text(encoding="utf-8")
        self.assertIn("initialState = RuntimeSmokeChartingState", main)
        self.assertIn("case '--smoke-chart-editor'", harness)
        self.assertIn("FlxG.switchState(new ChartingState())", state)
        self.assertIn("saveSelectedChartEvent();", charting)
        self.assertIn("deleteSelectedChartEvent();", charting)
        self.assertIn("autosaveSong();", charting)
        self.assertIn("loadAutosave();", charting)
        self.assertIn("chartEditorSidecarBytes.compare(File.getBytes(sidecarPath))", harness)
        self.assertIn("editor_source_unchanged", runner)
        self.assertIn("source_options_snapshot", runner)
        self.assertIn("SongEvents.collect(SongEvents.fromSong(song)",
                      (SOURCE / "RuntimeSmokeChartEditorCheck.hx").read_text(encoding="utf-8"))

    def test_editor_create_phase_markers_are_opt_in_and_cover_post_bpm_setup(self):
        harness = (SOURCE / "RuntimeSmokeHarness.hx").read_text(encoding="utf-8")
        charting = (SOURCE / "ChartingState.hx").read_text(encoding="utf-8")
        marker = harness[harness.index("public static function markChartEditorCreatePhase("):
                         harness.index("\n\t/** True on the ChartingState creation", harness.index(
                             "public static function markChartEditorCreatePhase("))]
        self.assertIn("if (chartEditorSmokeEnabled() && !finished)", marker)
        self.assertIn("emit('chart_editor_create_phase', {phase: phase})", marker)

        phases = ["after_bpm_map", "after_grid_controls", "after_song_panel",
                  "after_section_panel", "after_event_panel", "after_note_panel",
                  "after_char_panel", "before_change_section", "after_change_section",
                  "after_super_create"]
        positions = [charting.index("markChartEditorCreatePhase('%s')" % phase)
                     for phase in phases]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(charting.index("Conductor.mapBPMChanges(_song)"), positions[0])
        self.assertLess(positions[-1], charting.index(
            "chartEditorSmokePending = RuntimeSmokeHarness.chartEditorSmokeEnabled();"))
        self.assertIn("if (chartEditorSmokePending) {", charting)
        self.assertLess(charting.index("override function update(elapsed:Float)"),
                        charting.index("runChartEditorRoundTripSmoke();"))

    def test_event_helper_exercises_companion_edit_delete_reload_and_runtime_collection(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''class ChartEditorSmokeFixture {
 static function main() {
  var companion:Dynamic = haxe.Json.parse('{"events":[[1000,[["__dp_chart_editor_smoke_edit__","source-v1","source-v2","source-v3"]]],[2000,[["__dp_chart_editor_smoke_delete__","delete-v1","delete-v2","delete-v3"]]]]}');
  var companionBefore = haxe.Json.stringify(companion);
  var song:Dynamic = {song:"owner chart", compatStorageFolder:"owner-qualified-song",
   compatChartFileName:"owner-qualified-song-hard", bpm:120, events:[], notes:[]};
  ChartEventModel.normalizeSong(song);
  ChartEventModel.mergeCompanion(song, companion);
  var loaded = RuntimeSmokeChartEditorCheck.validateLoaded(song.events);
  if(loaded != "") throw loaded;
  var editRef = RuntimeSmokeChartEditorCheck.uniqueEditorEvent(song.events,
   RuntimeSmokeChartEditorCheck.SOURCE_EDIT);
  var deleteRef = RuntimeSmokeChartEditorCheck.uniqueEditorEvent(song.events,
   RuntimeSmokeChartEditorCheck.SOURCE_DELETE);
  if(!ChartEventModel.update(song.events, editRef, RuntimeSmokeChartEditorCheck.EDITED_TIME,
   RuntimeSmokeChartEditorCheck.EDITED_NAME, RuntimeSmokeChartEditorCheck.EDITED_VALUE_1,
   RuntimeSmokeChartEditorCheck.EDITED_VALUE_2, RuntimeSmokeChartEditorCheck.EDITED_VALUE_3))
   throw "edit failed";
  if(!ChartEventModel.removeSongEvent(song, deleteRef)) throw "delete failed";
  var current = RuntimeSmokeChartEditorCheck.validateRoundTrip(song, companion);
  if(current != "") throw current;
  var reloaded:Dynamic = haxe.Json.parse(haxe.Json.stringify({song:song})).song;
  ChartEventModel.normalizeSong(reloaded);
  ChartEventModel.mergeCompanion(reloaded, companion);
  var afterReload = RuntimeSmokeChartEditorCheck.validateRoundTrip(reloaded, companion);
  if(afterReload != "") throw afterReload;
  if(reloaded.compatStorageFolder != "owner-qualified-song"
   || reloaded.compatChartFileName != "owner-qualified-song-hard")
   throw "owner or difficulty path changed";
  if(haxe.Json.stringify(companion) != companionBefore) throw "source sidecar changed";
  Sys.println("OK");
 }
}'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "ChartEditorSmokeFixture.hx"
            fixture_path.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(SOURCE), "--run", "ChartEditorSmokeFixture"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
