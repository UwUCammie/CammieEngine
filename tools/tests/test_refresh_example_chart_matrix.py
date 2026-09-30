"""Current-state matrix refresh checks donor identity and installed ownership."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import refresh_example_chart_matrix as matrix


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RefreshExampleChartMatrixTest(unittest.TestCase):
    def test_empty_undeclared_keys_are_diagnostics_not_playable_chart_rows(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            examples = base / "examples"
            donor = examples / "generic-package"
            empty_source = donor / "data/source/raw-key.json"
            nonempty_source = donor / "data/source/authored-chart.json"
            empty_source.parent.mkdir(parents=True)
            empty_bytes = b'{"rawKey":[]}'
            nonempty_bytes = b'{"rawKey":[1]}'
            empty_source.write_bytes(empty_bytes)
            nonempty_source.write_bytes(nonempty_bytes)

            runtime = base / "runtime"
            owner = "assets/imported_mods/generic-owner"
            live_chart = runtime / "assets/data/live/live.json"
            live_chart.parent.mkdir(parents=True)
            live_chart.write_text(
                '{"song":{"notes":[{"sectionNotes":[[1,2,3]]}]}}',
                encoding="utf-8",
            )
            (live_chart.parent / "compatScripts.json").write_text(
                json.dumps({"selectedRoot": owner}), encoding="utf-8")
            (runtime / owner).mkdir(parents=True)

            baseline = {"schema": 1, "rows": [
                {
                    "group": "Generic format", "package": "generic-package",
                    "song": "unrelated-song", "variant": "alternate",
                    "difficulty": "empty-key", "sourceChart": "data/source/raw-key.json",
                    "sourceNoteCount": 0, "declaredDifficulty": False,
                    "sourceChartSha256": digest(empty_bytes),
                    "runtimeChart": "assets/data/wrong-candidate/wrong-candidate.json",
                    "runtimeOwner": owner, "sourceVariantImported": False,
                    "inventoryDiagnostic": "raw source key is empty and undeclared",
                },
                {
                    "group": "Generic format", "package": "generic-package",
                    "song": "another-song", "variant": "alternate",
                    "difficulty": "authored", "sourceChart": "data/source/authored-chart.json",
                    "sourceNoteCount": 1, "declaredDifficulty": True,
                    "sourceChartSha256": digest(nonempty_bytes),
                    "runtimeChart": "assets/data/live/live.json",
                    "runtimeOwner": owner, "sourceVariantImported": True,
                },
            ]}
            inventory = {"packages": [{
                "name": "generic-package", "sourceRoot": str(donor),
            }]}

            result = matrix.refresh(baseline, inventory, examples, runtime)

            self.assertEqual(len(result["rows"]), 1)
            playable = result["rows"][0]
            self.assertEqual(playable["song"], "another-song")
            self.assertTrue(playable["playable"])
            self.assertTrue(playable["structurallyCovered"])
            self.assertEqual(playable["matrixIndex"], 1)

            self.assertEqual(len(result["nonPlayableDiagnostics"]), 1)
            diagnostic = result["nonPlayableDiagnostics"][0]
            self.assertEqual(diagnostic["song"], "unrelated-song")
            self.assertEqual(diagnostic["sourceChart"], "data/source/raw-key.json")
            self.assertEqual(diagnostic["sourceNoteCount"], 0)
            self.assertFalse(diagnostic["declaredDifficulty"])
            self.assertFalse(diagnostic["playable"])
            self.assertEqual(diagnostic["nonPlayableReason"], "empty-undeclared-raw-key")
            self.assertEqual(diagnostic["coverageStatus"], "nonplayable-empty-undeclared-key")
            self.assertIsNone(diagnostic["sourceVariantImported"])
            self.assertIsNone(diagnostic["structurallyCovered"])
            self.assertTrue(diagnostic["sourceChartPresent"])
            self.assertEqual(diagnostic["sourceChartSha256"], digest(empty_bytes))
            self.assertEqual(diagnostic["inventoryDiagnostic"],
                             "raw source key is empty and undeclared")
            self.assertNotIn("runtimeChart", diagnostic)
            self.assertEqual(diagnostic["rejectedRuntimeCandidate"], {
                "chart": "assets/data/wrong-candidate/wrong-candidate.json",
                "owner": owner,
            })
            self.assertEqual(result["refresh"]["problems"], [])
            self.assertEqual(result["refresh"]["baselineRows"], 2)
            self.assertEqual(result["refresh"]["refreshedRows"], 1)
            self.assertEqual(result["refresh"]["nonPlayableDiagnosticRows"], 1)
            self.assertEqual(result["refresh"]["totalProcessedRows"], 2)

    def test_moved_package_and_nested_mod_keep_selected_chart_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            examples = base / "examples"
            donor = examples / "codename" / "moved"
            source = donor / "mods" / "inner" / "songs" / "demo" / "charts" / "normal.json"
            source.parent.mkdir(parents=True)
            source_bytes = b'{"notes":[1,2,3]}'
            source.write_bytes(source_bytes)
            runtime = base / "runtime"
            chart = runtime / "assets/data/demo/demo.json"
            chart.parent.mkdir(parents=True)
            chart.write_text('{"song":{"notes":[{"sectionNotes":[[1],[2]]}]}}', encoding="utf-8")
            owner = "assets/imported_mods/moved-owner"
            (runtime / owner).mkdir(parents=True)
            (chart.parent / "compatScripts.json").write_text(json.dumps({"selectedRoot": owner}), encoding="utf-8")
            old = {"schema": 1, "rows": [{
                "group": "Generic package", "package": "moved", "song": "demo",
                "variant": "default", "difficulty": "normal", "referenceOnly": False,
                "sourceChart": "songs/demo/charts/normal.json", "sourceNoteCount": 3,
                "sourceGameplayNoteCount": 2, "sourceUnroutedNoteCount": 1,
                "sourceChartSha256": digest(source_bytes),
                "runtimeChart": "assets/data/demo/demo.json", "runtimeOwner": owner,
                "sourceVariantImported": True,
            }]}
            inventory = {"packages": [{"name": "moved", "sourceRoot": str(examples / "moved")}]}
            result = matrix.refresh(old, inventory, examples, runtime)
            row = result["rows"][0]
            self.assertTrue(row["structurallyCovered"])
            self.assertTrue(row["sourceGameplayNoteCountMatched"])
            self.assertFalse(row["sourceNoteCountMatched"])
            self.assertEqual(row["sourceChartResolved"], str(source))
            self.assertEqual(row["runtimeNoteCount"], 2)
            self.assertEqual(result["refresh"]["problems"], [])

            no_prior_hash = {"schema": 1, "rows": [{key: value for key, value in old["rows"][0].items()
                                                     if key != "sourceChartSha256"}]}
            newly_hashed = matrix.refresh(no_prior_hash, inventory, examples, runtime)["rows"][0]
            self.assertIsNone(newly_hashed["sourceHashMatchesBaseline"])
            self.assertTrue(newly_hashed["structurallyCovered"])

            source.write_bytes(b"changed")
            drift = matrix.refresh(old, inventory, examples, runtime)
            self.assertFalse(drift["rows"][0]["structurallyCovered"])
            self.assertEqual(drift["refresh"]["problems"][0]["kind"], "source-hash-drift")

    def test_vslice_metadata_derives_difficulties_and_keeps_undeclared_keys_diagnosed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            examples = base / "examples"
            donor = examples / "v-slice-package"
            source_folder = donor / "data/songs/example"
            source_folder.mkdir(parents=True)
            chart_path = source_folder / "example-chart-alt.json"
            metadata_path = source_folder / "example-metadata-alt.json"
            chart_bytes = json.dumps({
                "notes": {"normal": [], "alt": [[1]], "hard": [[2], [3]]},
            }).encode("utf-8")
            chart_path.write_bytes(chart_bytes)
            metadata_path.write_text(json.dumps({
                "playData": {"difficulties": ["alt"]},
            }), encoding="utf-8")

            runtime = base / "runtime"
            owner = "assets/imported_mods/example-owner"
            live_chart = runtime / "assets/data/example-alt/example-alt.json"
            live_chart.parent.mkdir(parents=True)
            live_chart.write_text(
                '{"song":{"notes":[{"sectionNotes":[[1,2,3]]}]}}',
                encoding="utf-8",
            )
            (live_chart.parent / "compatScripts.json").write_text(
                json.dumps({"selectedRoot": owner}), encoding="utf-8")
            (runtime / owner).mkdir(parents=True)

            baseline = {"schema": 1, "rows": [
                {
                    "group": "V-Slice", "package": "v-slice-package",
                    "song": "example", "variant": "alt", "difficulty": "alt",
                    "sourceChart": "data/songs/example/example-chart-alt.json",
                    "sourceNoteCount": 1, "sourceChartSha256": digest(chart_bytes),
                    "runtimeChart": "assets/data/example-alt/example-alt.json",
                    "runtimeOwner": owner, "sourceVariantImported": True,
                },
                {
                    "group": "V-Slice", "package": "v-slice-package",
                    "song": "example", "variant": "alt", "difficulty": "normal",
                    "sourceChart": "data/songs/example/example-chart-alt.json",
                    "sourceNoteCount": 0, "sourceChartSha256": digest(chart_bytes),
                    "runtimeChart": "assets/data/example/example.json",
                    "runtimeOwner": owner, "sourceVariantImported": False,
                },
                {
                    "group": "V-Slice", "package": "v-slice-package",
                    "song": "example", "variant": "alt", "difficulty": "hard",
                    "sourceChart": "data/songs/example/example-chart-alt.json",
                    "sourceNoteCount": 2, "sourceChartSha256": digest(chart_bytes),
                    "runtimeChart": "assets/data/example-hard/example-hard.json",
                    "runtimeOwner": owner, "sourceVariantImported": False,
                },
            ]}
            inventory = {"packages": [{
                "name": "v-slice-package", "sourceRoot": str(donor),
            }]}

            result = matrix.refresh(baseline, inventory, examples, runtime)

            self.assertEqual(len(result["rows"]), 1)
            declared = result["rows"][0]
            self.assertEqual(declared["difficulty"], "alt")
            self.assertTrue(declared["declaredDifficulty"])
            self.assertEqual(declared["declaredDifficultySource"], "source-metadata")
            self.assertEqual(declared["declaredDifficultySourceFile"], str(metadata_path))
            self.assertTrue(declared["structurallyCovered"])

            diagnostics = result["nonPlayableDiagnostics"]
            self.assertEqual(len(diagnostics), 2)
            empty, nonempty = diagnostics
            self.assertFalse(empty["declaredDifficulty"])
            self.assertEqual(empty["sourceNoteCount"], 0)
            self.assertEqual(empty["nonPlayableReason"], "empty-undeclared-raw-key")
            self.assertEqual(empty["declaredDifficultySource"], "source-metadata")
            self.assertFalse(nonempty["declaredDifficulty"])
            self.assertEqual(nonempty["sourceNoteCount"], 2)
            self.assertEqual(nonempty["nonPlayableReason"], "nonempty-undeclared-raw-key")
            self.assertEqual(nonempty["coverageStatus"], "nonplayable-nonempty-undeclared-key")
            self.assertIn("nonempty source note-map key", nonempty["inventoryDiagnostic"])
            self.assertTrue(all("runtimeChart" not in row for row in diagnostics))
            self.assertEqual(result["refresh"]["problems"], [])

    def test_vslice_empty_metadata_list_falls_back_to_chart_note_keys(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            donor = Path(directory) / "donor"
            source_folder = donor / "data/songs/example"
            source_folder.mkdir(parents=True)
            chart_path = source_folder / "example-chart.json"
            metadata_path = source_folder / "example-metadata.json"
            chart_bytes = json.dumps({
                "notes": {"normal": [], "alt": [[1]]},
            }).encode("utf-8")
            chart_path.write_bytes(chart_bytes)
            metadata_path.write_text(json.dumps({
                "playData": {"difficulties": []},
            }), encoding="utf-8")

            declared = matrix.derive_vslice_declared_difficulty(
                donor, "data/songs/example/example-chart.json", "alt", chart_bytes,
            )
            undeclared = matrix.derive_vslice_declared_difficulty(
                donor, "data/songs/example/example-chart.json", "hard", chart_bytes,
            )

            self.assertEqual(declared, (
                True, "source-chart-fallback", str(metadata_path), None,
            ))
            self.assertEqual(undeclared, (
                False, "source-chart-fallback", str(metadata_path), None,
            ))

    def test_archive_source_and_missing_installed_chart_are_explicit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            examples = base / "examples"
            examples.mkdir()
            archive = examples / "package.zip"
            source_bytes = b'{"song":{}}'
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("package/assets/data/demo/demo.json", source_bytes)
            old = {"schema": 1, "rows": [{
                "group": "Psych source archive", "package": "package.zip",
                "song": "demo", "variant": "default", "difficulty": "normal",
                "referenceOnly": False, "sourceChart": "package/assets/data/demo/demo.json",
                "sourceNoteCount": 1, "sourceChartSha256": digest(source_bytes),
                "runtimeChart": None, "runtimeOwner": None,
                "sourceVariantImported": False,
            }]}
            old["rows"].append({**old["rows"][0], "difficulty": "easy",
                                "runtimeChart": "assets/data/demo/demo-easy.json"})
            inventory = {"packages": [{"name": "package.zip", "sourceRoot": str(archive)}]}
            result = matrix.refresh(old, inventory, examples, base / "runtime")
            row = result["rows"][0]
            self.assertTrue(row["sourceChartPresent"])
            self.assertFalse(row["runtimeChartPresent"])
            self.assertFalse(row["structurallyCovered"])
            self.assertEqual(result["refresh"]["problems"][0]["kind"], "runtime-unavailable")
            self.assertIn("no installed chart candidate", result["refresh"]["problems"][0]["detail"])
            self.assertIn("installed chart candidate is absent", result["refresh"]["problems"][1]["detail"])

    def test_paths_cannot_escape_source_or_runtime(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "unsafe relative"):
                matrix.safe_child(root, "../outside")
            with self.assertRaisesRegex(ValueError, "not text"):
                matrix.safe_child(root, None)
            donor = root / "donor"
            outside = root / "outside"
            donor.mkdir()
            (outside / "charts").mkdir(parents=True)
            (outside / "charts/demo.json").write_text("{}", encoding="utf-8")
            (donor / "linked").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(FileNotFoundError):
                matrix.source_bytes(donor, "charts/demo.json")


if __name__ == "__main__":
    unittest.main()
