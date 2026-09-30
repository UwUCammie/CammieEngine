"""Semantic coverage for chart-event editing and one-shot menu prompt ownership."""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class EngineEditorAndSelectionGateTest(unittest.TestCase):
    def test_chart_event_edits_preserve_groups_and_prompt_gate_rejects_stale_selection(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''class EditorAndSelectionGateFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var groups:Array<Dynamic> = [
   [100, [["Camera Flash", "0.5", "1"]]],
   [50, [["Focus Camera", "0", ""]]]
  ];
  var entries = ChartEventModel.list(groups);
  if(entries.length != 2 || entries[0].time != 50 || entries[1].time != 100)
   fail("event editor list was not timestamp sorted");

  var created = ChartEventModel.add(groups, 50, "Add Camera Zoom", "0.03", "0.06", "");
  groups = created.groups;
  if(groups.length != 2 || groups[0][1].length != 2)
   fail("event at an existing time did not share its timestamp group");
  var selected:Dynamic = null;
  for(entry in ChartEventModel.list(groups))
   if(entry.event == created.event) selected = entry;
  if(!ChartEventModel.update(groups, selected, 25, "Add Camera Zoom", "0.04", "0.08", "x"))
   fail("selected event could not be updated");
  entries = ChartEventModel.list(groups);
  selected = null;
  for(entry in entries) if(entry.event == created.event) selected = entry;
  if(selected == null || selected.time != 25 || selected.event[1] != "0.04" || selected.event[3] != "x")
   fail("updated event data was not retained");
  var originalTimeRetained = false;
  for(entry in entries) if(entry.event[0] == "Focus Camera" && entry.time == 50) originalTimeRetained = true;
  if(!originalTimeRetained) fail("editing one event moved its timestamp-group siblings");
  if(!ChartEventModel.remove(groups, selected) || ChartEventModel.list(groups).length != 2)
   fail("event deletion did not remove only the selected event");

  var gate = new SelectionActionGate();
  var token = gate.armFor("selected-a", 4);
  if(token == 0 || gate.consumeFor("selected-b", 4, token))
   fail("prompt from one selection was accepted for another selection");
  token = gate.armFor("selected-a", 4);
  if(gate.consumeFor("selected-a", 5, token))
   fail("prompt from an old selection generation was accepted");
  token = gate.armFor("selected-a", 4);
  if(gate.consumeFor("selected-a", 4, token + 1))
   fail("a stale callback token was accepted");
  token = gate.armFor("selected-a", 4);
  if(!gate.consumeFor("SELECTED-A", 4, token)
    || gate.consumeFor("selected-a", 4, token))
   fail("matching prompt was not consumed exactly once");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "EditorAndSelectionGateFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "EditorAndSelectionGateFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_chart_editor_exposes_events_before_notes_and_uses_dynamic_tab_count(self):
        source = (ROOT / "source/ChartingState.hx").read_text()
        self.assertLess(source.index('{name: "Events"'), source.index('{name: "Note"'))
        self.assertIn("function addEventUI()", source)
        self.assertIn("ChartEventModel.add(_song.events", source)
        self.assertIn("UI_box.numTabs", source)


if __name__ == "__main__":
    unittest.main()
