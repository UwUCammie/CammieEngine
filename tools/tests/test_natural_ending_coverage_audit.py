"""Regression tests for historical natural-ending coverage accounting."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from audit_natural_ending_coverage import audit_matrix


def ended_record(runtime_chart, difficulty, **fields):
    return {
        "runtimeChart": runtime_chart,
        "difficulty": difficulty,
        "status": "passed",
        "naturalSongEnd": {
            "count": 1,
            "totalEvents": 12,
            "dueEvents": 10,
            "dispatchedEvents": 10,
            "positionMs": 1000,
            "songLengthMs": 1000,
            "time": 1234.5,
            "valid": True,
        },
        **fields,
    }


class NaturalEndingCoverageAuditTest(unittest.TestCase):
    def audit_rows(self, matrix_rows, receipt_records, current_build="current-build"):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            receipt_path = Path(temporary) / "rows.jsonl"
            receipt_path.write_text(
                "".join(json.dumps(row) + "\n" for row in receipt_records),
                encoding="utf-8",
             newline='\n')
            return audit_matrix(
                {"schema": 1, "rows": matrix_rows}, [receipt_path], current_build)

    def test_moved_row_order_uses_runtime_chart_and_difficulty_not_matrix_index(self):
        matrix_rows = [
            {"matrixIndex": 70, "song": "second", "difficulty": "normal",
             "runtimeChart": "assets/data/second/second.json"},
            {"matrixIndex": 13, "song": "first", "difficulty": "hard",
             "runtimeChart": "assets/data/first/first-hard.json"},
        ]
        receipt = ended_record(
            "assets/data/first/first-hard.json", "hard", matrixIndex=70)

        result = self.audit_rows(matrix_rows, [receipt])

        self.assertEqual(result["summary"]["historicalNaturalEndingRows"], 1)
        self.assertEqual(result["rows"][0]["matrixIndex"], 70)
        self.assertEqual(result["rows"][0]["historicalNaturalEnding"], "missing")
        self.assertEqual(result["rows"][1]["matrixIndex"], 13)
        self.assertEqual(result["rows"][1]["historicalNaturalEnding"], "covered")

    def test_failed_receipt_that_ended_covers_history_but_keeps_diagnostic_failure(self):
        matrix_rows = [{"matrixIndex": 4, "song": "example", "difficulty": "normal",
                        "runtimeChart": "assets/data/example/example.json"}]
        receipt = ended_record(
            "assets/data/example/example.json", "normal", status="failed",
            strictRuntimeGatePassed=False,
            strictDiagnostics=["native runtime diagnostic"],
        )

        result = self.audit_rows(matrix_rows, [receipt])
        row = result["rows"][0]

        self.assertEqual(row["historicalNaturalEnding"], "covered")
        self.assertEqual(row["diagnosticStatus"], "failed")
        self.assertEqual(row["endingEvidenceCount"], 1)
        self.assertEqual(result["summary"]["diagnosticStatusCounts"]["failed"], 1)

    def test_build_provenance_unknown_and_mismatch_stay_out_of_current_validation(self):
        matrix_rows = [
            {"matrixIndex": 0, "song": "unknown", "difficulty": "normal",
             "runtimeChart": "assets/data/unknown/unknown.json",
             "runtimeChartSha256": "expected-unknown-chart"},
            {"matrixIndex": 1, "song": "different", "difficulty": "hard",
             "runtimeChart": "assets/data/different/different-hard.json",
             "runtimeChartSha256": "expected-different-chart"},
        ]
        records = [
            ended_record("assets/data/unknown/unknown.json", "normal"),
            ended_record(
                "assets/data/different/different-hard.json", "hard",
                provenance={"binarySha256": "older-build",
                            "runtimeChartSha256": "older-chart"}),
        ]

        result = self.audit_rows(matrix_rows, records, current_build="current-build")

        unknown, mismatch = result["rows"]
        self.assertEqual(unknown["historicalNaturalEnding"], "covered")
        self.assertEqual(unknown["buildProvenanceStatus"], "unknown")
        self.assertEqual(unknown["currentBuildNaturalEndingValidation"], "unknown")
        self.assertEqual(mismatch["buildProvenanceStatus"], "mismatch")
        self.assertEqual(mismatch["runtimeChartProvenanceStatus"], "mismatch")
        self.assertEqual(mismatch["currentBuildNaturalEndingValidation"], "mismatch")
        self.assertEqual(result["summary"]["currentBuildNaturalEndingValidatedRows"], 0)

    def test_row_provenance_overrides_conflicting_wrapper_hashes(self):
        matrix_rows = [{"matrixIndex": 2, "song": "example", "difficulty": "normal",
                        "runtimeChart": "assets/data/example/example.json",
                        "runtimeChartSha256": "current-chart"}]
        row = ended_record(
            "assets/data/example/example.json", "normal",
            provenance={"binarySha256": "current-build",
                        "runtimeChartSha256": "current-chart"})

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            receipt_path = Path(temporary) / "sweep.json"
            receipt_path.write_text(json.dumps({
                "binarySha256": "older-wrapper-build",
                "runtimeChartSha256": "older-wrapper-chart",
                "rows": [row],
            }), encoding="utf-8", newline='\n')
            result = audit_matrix(
                {"rows": matrix_rows}, [receipt_path], "current-build")

        self.assertEqual(result["rows"][0]["buildProvenanceStatus"], "matched")
        self.assertEqual(result["rows"][0]["runtimeChartProvenanceStatus"], "matched")
        self.assertEqual(
            result["rows"][0]["currentBuildNaturalEndingValidation"], "matched")

    def test_duplicate_records_do_not_inflate_attempt_or_ending_counts(self):
        matrix_rows = [{"matrixIndex": 3, "song": "example", "difficulty": "hard",
                        "runtimeChart": "assets/data/example/example-hard.json"}]
        receipt = ended_record(
            "assets/data/example/example-hard.json", "hard", matrixIndex=3)
        duplicate = {**receipt, "matrixIndex": 98}

        result = self.audit_rows(matrix_rows, [receipt, duplicate])
        row = result["rows"][0]

        self.assertEqual(row["uniqueAttemptCount"], 1)
        self.assertEqual(row["endingEvidenceCount"], 1)
        self.assertEqual(result["summary"]["duplicateMatchedRecordsIgnored"], 1)

    def test_current_ending_is_kept_alongside_old_failed_build(self):
        key = "assets/data/example/example.json"
        rows = [{"runtimeChart": key, "difficulty": "normal",
                 "runtimeChartSha256": "current-chart"}]
        records = [
            ended_record(key, "normal", status="failed", provenance={
                "binarySha256": "old-build", "runtimeChartSha256": "old-chart"}),
            ended_record(key, "normal", provenance={
                "binarySha256": "current-build", "runtimeChartSha256": "current-chart"}),
        ]
        result = self.audit_rows(rows, records)
        self.assertEqual(result["summary"]["currentBuildNaturalEndingValidatedRows"], 1)
        self.assertEqual(result["rows"][0]["diagnosticStatus"], "mixed")
        self.assertEqual(result["rows"][0]["endingEvidenceCount"], 2)

    def test_missing_and_skipped_rows_are_not_promoted_to_coverage(self):
        matrix_rows = [
            {"matrixIndex": 0, "song": "stopped", "difficulty": "easy",
             "runtimeChart": "assets/data/stopped/stopped-easy.json"},
            {"matrixIndex": 1, "song": "unavailable", "difficulty": "normal",
             "runtimeChart": None},
        ]
        skipped = {"runtimeChart": "assets/data/stopped/stopped-easy.json",
                   "difficulty": "easy", "status": "blocked"}

        result = self.audit_rows(matrix_rows, [skipped])

        self.assertEqual(result["summary"]["historicalNaturalEndingRows"], 0)
        self.assertEqual(result["summary"]["missingNaturalEndingRows"], 2)
        self.assertEqual(result["rows"][0]["diagnosticStatus"], "skipped")
        self.assertEqual(result["rows"][1]["keyStatus"], "unkeyed")

    def test_nonfinite_or_nonpositive_end_positions_are_not_valid_endings(self):
        matrix_rows = [{"matrixIndex": 0, "song": "invalid", "difficulty": "normal",
                        "runtimeChart": "assets/data/invalid/invalid.json"}]
        record = ended_record(
            "assets/data/invalid/invalid.json", "normal",
            naturalSongEnd={"count": 1, "totalEvents": 2, "dueEvents": 1,
                            "dispatchedEvents": 1, "positionMs": float("inf"),
                            "songLengthMs": 0, "valid": True})

        result = self.audit_rows(matrix_rows, [record])

        self.assertEqual(result["rows"][0]["historicalNaturalEnding"], "missing")


if __name__ == "__main__":
    unittest.main()
