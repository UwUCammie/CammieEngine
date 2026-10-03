"""Checks for scoped Codename note provenance refresh safety."""

import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import refresh_codename_notes as refresh  # noqa: E402


def current_row(time, lane, sustain, note_index):
    return [time, lane, sustain, *([None] * 10),
            {"engine": "codename", "version": 1, "lineIndex": 1,
             "noteIndex": note_index, "lineType": 1, "nativeSide": 0}]


def section(rows):
    return {"sectionNotes": rows, "lengthInSteps": 16, "mustHitSection": True,
            "bpm": 100, "changeBPM": False, "altAnim": False, "altAnimNum": 0}


class CodenameNoteRefreshTest(unittest.TestCase):
    def setUp(self):
        self.donor = {"strumLines": [{"notes": []}, {"notes": [
            {"id": 0, "time": 277.777, "sLen": 416.999, "type": 0},
            {"id": 1, "time": 277.777, "sLen": 0, "type": 0},
        ]}]}
        self.current = [section([current_row(277.777, 0, 416.999, 0),
                                 current_row(277.777, 1, 0, 1)])]

    def test_matches_legacy_numbers_and_preserves_all_other_bytes(self):
        chart = {"song": {"notes": [section([[277, 0, 416], [277.777, 1, 0]])],
                          "events": [[0, [["Camera Follow Pos", "", "", ""]]]],
                          "speed": 1.25}}
        before = json.dumps(chart, indent=2)
        present, layout = refresh.notes_layout(before)
        assignments, complete = refresh.match_note_rows(present, self.current, self.donor)
        self.assertFalse(complete)
        self.assertEqual([a["origin"]["noteIndex"] for a in assignments], [0, 1])
        after = refresh.append_metadata(before, layout, assignments)
        parsed = json.loads(after)
        self.assertEqual(parsed["song"]["events"], chart["song"]["events"])
        self.assertEqual(parsed["song"]["speed"], 1.25)
        self.assertEqual([row[:3] for row in parsed["song"]["notes"][0]["sectionNotes"]],
                         [[277, 0, 416], [277.777, 1, 0]])
        _, complete = refresh.match_note_rows(parsed["song"]["notes"], self.current,
                                               self.donor)
        self.assertTrue(complete)

    def test_rejects_edited_note_and_ambiguous_duplicate(self):
        with self.assertRaisesRegex(ValueError, "multiset differs"):
            refresh.match_note_rows([section([[277, 3, 416], [277, 1, 0]])],
                                    self.current, self.donor)
        duplicate_current = [section([current_row(277.777, 0, 0, 0),
                                      current_row(277.777, 0, 0, 1)])]
        with self.assertRaisesRegex(ValueError, "ambiguous duplicate"):
            refresh.match_note_rows([section([[277, 0, 0], [277, 0, 0]])],
                                    duplicate_current, self.donor)


if __name__ == "__main__":
    unittest.main()
