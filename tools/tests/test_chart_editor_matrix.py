"""Offline checks for resumable, owner-preserving chart-editor matrix runs."""

from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_chart_editor_matrix as matrix_runner
import run_runtime_smoke_matrix as smoke_matrix


class ChartEditorMatrixTest(unittest.TestCase):
    def make_runtime(self, root: Path, folder: str = "sample-song",
                     chart: str = "sample-song-hard") -> tuple[Path, dict]:
        data_folder = root / "assets" / "data" / folder
        owner_folder = root / "assets" / "imported_mods" / "sample-owner"
        data_folder.mkdir(parents=True)
        owner_folder.mkdir(parents=True)
        (data_folder / f"{chart}.json").write_text('{"song":{}}', encoding="utf-8")
        (data_folder / "compatScripts.json").write_text(json.dumps({
            "selectedRoot": "assets/imported_mods/sample-owner",
            "roots": [{"path": "assets/imported_mods/sample-owner"}],
        }), encoding="utf-8")
        row = {
            "group": "Psych Engine",
            "package": "sample-pack",
            "song": folder,
            "variant": "default",
            "difficulty": "hard",
            "sourceChart": "data/sample-song/sample-song-hard.json",
            "runtimeChart": f"assets/data/{folder}/{chart}.json",
            "runtimeOwner": "assets/imported_mods/sample-owner",
            "runtimeChartPresent": True,
            "runtimeOwnerRootPresent": True,
            "coverageStatus": "installed-structural",
        }
        return root, row

    def test_dry_run_preflights_owner_and_never_launches_or_locks(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime, installed = self.make_runtime(Path(folder) / "runtime")
            (runtime / "assets").mkdir(exist_ok=True)
            binary = Path(folder) / "missing-game"
            archive_only = {
                "group": "Psych source archive",
                "package": "archive",
                "song": "reference-song",
                "variant": "reference",
                "difficulty": "normal",
                "runtimeChart": None,
                "runtimeOwner": None,
                "referenceOnly": True,
            }

            with patch.object(matrix_runner.chart_editor_smoke,
                              "run_chart_editor_case") as launch, \
                 patch.object(matrix_runner, "runtime_lock") as lock:
                results = matrix_runner.run_rows(
                    [(3, installed), (4, archive_only)], binary, runtime,
                    5000, 30, dry_run=True,
                )

            self.assertEqual([item["status"] for item in results], ["ready", "skipped"])
            self.assertTrue(results[0]["owner_verified"])
            self.assertEqual(results[0]["case"]["folder"], "sample-song")
            self.assertEqual(results[0]["case"]["chart"], "sample-song-hard")
            self.assertIn("reference-only", results[1]["reason"])
            launch.assert_not_called()
            lock.assert_not_called()

    def test_preflight_reports_missing_and_mismatched_owner_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime, row = self.make_runtime(Path(folder) / "runtime")
            missing = dict(row, runtimeChartPresent=False,
                           runtimeChart="assets/data/absent/absent-hard.json")
            absent_result = matrix_runner.inspect_row(8, missing, runtime)
            self.assertEqual(absent_result["status"], "skipped")
            self.assertIn("not installed", absent_result["reason"])

            mismatch = dict(row, runtimeOwner="assets/imported_mods/other-owner")
            mismatch_result = matrix_runner.inspect_row(9, mismatch, runtime)
            self.assertEqual(mismatch_result["status"], "failed")
            self.assertIn("owner directory is absent", mismatch_result["reason"])

            unimported_variant = dict(row, sourceVariantImported=False)
            variant_result = matrix_runner.inspect_row(10, unimported_variant, runtime)
            self.assertEqual(variant_result["status"], "skipped")
            self.assertIn("variant is not imported", variant_result["reason"])

            manifest_path = runtime / "assets/data/sample-song/compatScripts.json"
            manifest_path.write_text(json.dumps({
                "selectedRoot": "assets/imported_mods/another-owner",
                "roots": [{"path": "assets/imported_mods/sample-owner"}],
            }), encoding="utf-8")
            selected_mismatch = matrix_runner.inspect_row(11, row, runtime)
            self.assertEqual(selected_mismatch["status"], "failed")
            self.assertIn("selectedRoot", selected_mismatch["reason"])

            malicious = dict(row, runtimeChart="assets/data/../outside/chart.json")
            malicious_result = matrix_runner.inspect_row(12, malicious, runtime)
            self.assertEqual(malicious_result["status"], "failed")
            self.assertIn("safe relative path", malicious_result["reason"])

    def test_parenthesized_import_chart_names_round_trip_through_fixture(self):
        folder_name = "sample-song-(hq)"
        chart_name = "sample-song-(hq)-hard"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp_root = Path(folder)
            source_root = temp_root / "runtime"
            source_song = source_root / "assets" / "data" / folder_name
            source_song.mkdir(parents=True)
            (source_song / f"{chart_name}.json").write_text('{"song":{}}', encoding="utf-8")
            (source_root / "assets" / "imported_mods").mkdir()
            overlay_root = temp_root / "overlay"
            overlay_root.mkdir()

            case = matrix_runner.case_for_row(16, {
                "group": "Psych Engine",
                "difficulty": "hard",
                "runtimeChart": f"assets/data/{folder_name}/{chart_name}.json",
            })
            smoke_matrix._prepare_case_overlay(source_root, overlay_root, case)
            sidecar, fixture = smoke_matrix.prepare_chart_editor_fixture(
                overlay_root, source_root, case.folder, case.chart,
            )

            self.assertEqual(case.folder, folder_name)
            self.assertEqual(case.chart, chart_name)
            self.assertTrue(sidecar.is_file())
            self.assertIn("__dp_chart_editor_smoke_edit__", fixture.decode("utf-8"))
            self.assertTrue((source_song / f"{chart_name}.json").is_file())

    def test_fixture_token_expansion_still_rejects_absolute_and_traversal(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            source_root = root / "runtime"
            source_data = source_root / "assets" / "data"
            source_data.mkdir(parents=True)
            overlay_root = root / "overlay"
            overlay_root.mkdir()

            for folder_name in ("../outside", "/absolute-song"):
                with self.subTest(folder=folder_name):
                    with self.assertRaises(ValueError):
                        smoke_matrix.prepare_chart_editor_fixture(
                            overlay_root, source_root, folder_name, "chart",
                        )

            for raw in ("assets/data/../outside/chart.json",
                        "/assets/data/song/chart.json"):
                with self.subTest(runtime_chart=raw):
                    with self.assertRaises(ValueError):
                        matrix_runner.case_for_row(0, {
                            "runtimeChart": raw,
                            "difficulty": "hard",
                        })

    def test_runtime_run_uses_chart_editor_helper_while_holding_shared_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime, row = self.make_runtime(Path(folder) / "runtime")
            binary = Path(folder) / "Funkin"
            binary.write_bytes(b"offline test placeholder")
            events = []

            @contextmanager
            def fake_lock(_binary):
                events.append("lock-enter")
                try:
                    yield
                finally:
                    events.append("lock-exit")

            def fake_run(_binary, song, chart, difficulty, **kwargs):
                events.append((song, chart, difficulty, kwargs["case_id"], kwargs["duration_ms"]))
                return {"id": kwargs["case_id"], "status": "passed", "events": ["success"]}

            with patch.object(matrix_runner, "runtime_lock", fake_lock), \
                 patch.object(matrix_runner.chart_editor_smoke,
                              "run_chart_editor_case", side_effect=fake_run):
                results = matrix_runner.run_rows(
                    [(11, row)], binary, runtime, 6500, 25,
                )

            self.assertEqual(results[0]["status"], "passed")
            self.assertEqual(events[0], "lock-enter")
            self.assertEqual(events[1][:3], ("sample-song", "sample-song-hard", "hard"))
            self.assertEqual(events[1][4], 6500)
            self.assertEqual(events[-1], "lock-exit")

    def test_parallel_editor_visits_keep_one_build_lock_and_complete_each_row(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime, row = self.make_runtime(Path(folder) / "runtime")
            binary = Path(folder) / "Funkin"
            binary.write_bytes(b"offline test placeholder")
            both_started = threading.Barrier(2)
            observed = []

            @contextmanager
            def fake_lock(_binary):
                observed.append("lock-enter")
                try:
                    yield
                finally:
                    observed.append("lock-exit")

            def fake_run(_binary, song, chart, difficulty, **kwargs):
                both_started.wait(timeout=2)
                return {"id": kwargs["case_id"], "status": "passed", "events": ["success"]}

            with patch.object(matrix_runner, "runtime_lock", fake_lock), \
                 patch.object(matrix_runner.chart_editor_smoke,
                              "run_chart_editor_case", side_effect=fake_run):
                results = matrix_runner.run_rows(
                    [(12, row), (11, row)], binary, runtime, 20000, 60,
                    jobs=2, on_result=lambda result: observed.append(result["row_index"]),
                )

            self.assertEqual([result["row_index"] for result in results], [11, 12])
            self.assertEqual([result["status"] for result in results], ["passed", "passed"])
            self.assertEqual(observed[0], "lock-enter")
            self.assertEqual(observed[-1], "lock-exit")
            self.assertEqual(set(observed[1:-1]), {11, 12})

    def test_report_upserts_slices_and_refuses_a_different_matrix(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            matrix_path = root / "matrix.json"
            matrix_path.write_text('{"schema":1,"rows":[]}', encoding="utf-8")
            digest = "a" * 64
            report = matrix_runner.MatrixReport(root / "report.json", matrix_path, digest)
            report.upsert({"row_index": 1, "status": "passed"})
            report.upsert({"row_index": 4, "status": "skipped"})
            payload = json.loads((root / "report.json").read_text(encoding="utf-8"))
            self.assertEqual([row["row_index"] for row in payload["rows"]], [1, 4])
            self.assertEqual(payload["summary"]["passed"], 1)
            self.assertEqual(payload["summary"]["skipped"], 1)
            with self.assertRaisesRegex(ValueError, "different matrix"):
                matrix_runner.MatrixReport(root / "report.json", matrix_path, "b" * 64)

    def test_start_and_limit_select_stable_zero_based_row_indices(self):
        rows = [{"song": str(index)} for index in range(6)]
        selection = matrix_runner.selected_rows(rows, start=2, limit=3)
        self.assertEqual([index for index, _ in selection], [2, 3, 4])
        self.assertEqual([row["song"] for _, row in selection], ["2", "3", "4"])

    def test_requested_runtime_matrix_paths_map_without_per_row_exceptions(self):
        matrix_path = ROOT / "tmp" / "example_mods_chart_matrix_runtime_20260929.json"
        if not matrix_path.is_file():
            self.skipTest("requested chart matrix is unavailable")
        manifest, _, _ = matrix_runner.load_matrix(matrix_path)
        installed = [row for row in manifest["rows"] if row.get("runtimeChartPresent")]
        candidates = [row for row in manifest["rows"] if row.get("runtimeChart")]
        cases = [matrix_runner.case_for_row(index, row)
                 for index, row in enumerate(manifest["rows"]) if row.get("runtimeChart")]
        self.assertEqual(len(installed), 251)
        self.assertEqual(len(candidates), 254)
        self.assertEqual(len(cases), len(candidates))
        self.assertTrue(any("(" in case.folder for case in cases))
        self.assertTrue(all(case.folder and case.chart and case.difficulty for case in cases))


if __name__ == "__main__":
    unittest.main()
