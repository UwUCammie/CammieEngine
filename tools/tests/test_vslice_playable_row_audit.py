import sys
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from audit_vslice_playable_rows import annotate_matrix, source_counts


class VSlicePlayableRowAuditTest(unittest.TestCase):
    def test_two_source_strumlines_are_playable_and_extra_rows_remain_in_inventory(self):
        chart = {"generatedBy": "Friday Night Funkin' - v0.3.2", "notes": {
            "hard": [{"t": 100, "d": lane} for lane in range(16)]}}
        self.assertEqual(source_counts(chart, "hard"),
                         (16, 8, "Friday Night Funkin' - v0.3.2"))

    def test_mounted_madness_extra_rows_match_source_strumline_rule(self):
        source = (Path("/run/media/cammie/External Storage/FNF-Example-Mods")
                  / "v-slice/Vs Tricky/data/songs/madness/madness-chart.json")
        if not source.is_file():
            self.skipTest("mounted example donor is unavailable")
        import json
        chart = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(source_counts(chart, "easy")[:2], (656, 652))
        self.assertEqual(source_counts(chart, "normal")[:2], (840, 832))
        self.assertEqual(source_counts(chart, "hard")[:2], (1072, 1064))

    def test_annotation_keeps_raw_count_separate_from_gameplay_count(self):
        matrix = {"rows": [{"group": "V-Slice", "package": "package",
                            "sourceChart": "data/songs/example/example-chart.json",
                            "runtimeChart": "assets/data/example/example.json",
                            "difficulty": "normal", "sourceNoteCount": 16}]}
        detail = [{"package": "package", "sourceChart": "data/songs/example/example-chart.json",
                   "runtimeChart": "assets/data/example/example.json",
                   "difficulty": "normal", "sourceGameplayRows": 8,
                   "sourceUnroutedRows": 8, "sourceRawRows": 16,
                   "liveRows": 8, "liveGameplayCountMatches": True}]
        row = annotate_matrix(matrix, detail)["rows"][0]
        self.assertEqual(row["sourceNoteCount"], 16)
        self.assertEqual(row["sourceGameplayNoteCount"], 8)
        self.assertEqual(row["sourceUnroutedNoteCount"], 8)
        self.assertTrue(row["sourceGameplayNoteCountMatched"])
        self.assertFalse(row["sourceNoteCountMatched"])


if __name__ == "__main__":
    unittest.main()
