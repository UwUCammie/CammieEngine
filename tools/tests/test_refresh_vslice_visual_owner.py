import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/refresh_vslice_visual_owner.py"
SPEC = importlib.util.spec_from_file_location("refresh_vslice_visual_owner_test", MODULE_PATH)
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")


class VSliceVisualOwnerRefreshTest(unittest.TestCase):
    def setUp(self):
        ROOT.joinpath("tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tmp")
        self.scratch = Path(self.temp.name)
        self.project = self.scratch / "project"
        self.project.mkdir()
        self.runtime = self.project / "export/release/linux/bin"
        self.runtime.mkdir(parents=True)
        self.binary = self.runtime / "Funkin"
        self.binary.write_bytes(b"test binary placeholder")
        self.source = self.scratch / "donor"
        self.source.mkdir()
        self.source_content = self.source / "assets"
        self.source_content.mkdir()
        write_json(self.source / "pack.json", {"name": "Fixture Pack"})
        songs = self.source_content / "data/songs/Alpha"
        self.metadata = {"songName": "Base Audio", "playData": {"songVariations": ["alt"]}}
        self.base_chart = {"notes": [{"t": 0, "l": 0, "d": 1}]}
        self.alt_metadata = {"songName": "Variant Audio", "playData": {}}
        self.alt_chart = {"notes": [{"t": 300, "l": 1, "d": 1}]}
        write_json(songs / "Alpha-metadata.json", self.metadata)
        write_json(songs / "Alpha-chart.json", self.base_chart)
        write_json(songs / "Alpha-metadata-alt.json", self.alt_metadata)
        write_json(songs / "Alpha-chart-alt.json", self.alt_chart)
        for folder in ("Base Audio", "Variant Audio"):
            audio = self.source_content / "songs" / folder
            audio.mkdir(parents=True)
            (audio / "Inst.ogg").write_bytes(b"audio marker")

        self.owner = refresh._path_namespace(self.source)
        self.other_owner = "assets/imported_mods/psych-fixture"
        owner_dir = self.runtime / self.owner / "images/custom_chars"
        owner_dir.mkdir(parents=True)
        (owner_dir / "existing.json").write_text("keep owner bytes\n", encoding="utf-8")
        self.source_songs = refresh._v_slice_source_pairs(
            self.source, self.source_content / "data/songs", self.source_content / "songs")
        self.fingerprint = refresh._source_fingerprint(self.source_songs)
        identity = "v-slice|package-name|fixture pack"
        for name in ("alpha", "alpha-alt"):
            folder = self.runtime / "assets/data" / name
            folder.mkdir(parents=True)
            chart = folder / (name + ".json")
            chart.write_text('{"song":{"song":"' + name + '"}}\n', encoding="utf-8")
            write_json(folder / "compatScripts.json", {
                "version": 1, "selectedRoot": self.owner,
                "roots": [
                    {"engine": "V-Slice", "path": self.owner},
                    {"engine": "Psych Engine", "path": self.other_owner},
                ], "overlays": None,
            })
            write_json(folder / "importProvenance.json", {
                "sourceEngine": "V-Slice", "sourceOwner": self.owner,
                "destinationFolder": name, "sourceFingerprint": self.fingerprint,
                "sourceIdentity": identity, "modName": "Fixture Pack", "nameSource": "metadata",
            })
            audio_target = self.runtime / "assets/songs" / name
            audio_target.mkdir(parents=True)
            (audio_target / "Inst.ogg").write_bytes(b"original installed audio")
        self._seed_shared_files(self.runtime)
        self._seed_shared_files(self.project)
        write_json(self.project / "assets/data/options.json", {"testDefaults": True})
        write_json(self.runtime / "assets/data/options.json", {"personalSetting": "preserve"})
        self.runtime_ui = self.runtime / "assets/images/custom_ui/ui_packs"
        self.runtime_ui.mkdir(parents=True)
        write_json(self.runtime_ui / "ui.json", {})
        repo_ui = self.project / "assets/images/custom_ui/ui_packs"
        repo_ui.mkdir(parents=True)
        write_json(repo_ui / "ui.json", {})

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _seed_shared_files(root: Path) -> None:
        data = root / "assets/data"
        data.mkdir(parents=True, exist_ok=True)
        write_json(data / "freeplaySongJson.jsonc", {})
        write_json(data / "options.json", {"personal": True})
        chars = root / "assets/images/custom_chars"
        chars.mkdir(parents=True, exist_ok=True)
        write_json(chars / "custom_chars.jsonc", {})
        stages = root / "assets/images/custom_stages"
        stages.mkdir(parents=True, exist_ok=True)
        write_json(stages / "custom_stages.json", {})

    def make_plan(self):
        return refresh.make_plan(
            self.source, self.runtime, repository_root=self.project, binary=self.binary)

    def test_plan_fingerprints_all_variations_and_resolves_their_audio(self):
        self.assertEqual([song["destinationFolder"] for song in self.source_songs],
                         ["alpha", "alpha-alt"])
        self.assertEqual([song["audioFolder"] for song in self.source_songs],
                         ["assets/songs/Base Audio", "assets/songs/Variant Audio"])
        plan = self.make_plan()
        self.assertTrue(plan["preflight"]["visualOnlyBranchExpectedForEveryChart"])
        self.assertTrue(plan["preflight"]["sourceFingerprintPersistedInChartProvenance"])
        self.assertEqual(plan["selectedRoot"], self.owner)
        self.assertEqual(plan["sourceFingerprint"], self.fingerprint)
        self.assertEqual(len(plan["selectedCharts"]), 2)
        self.assertTrue(all(chart["ownerCount"] == 2 for chart in plan["selectedCharts"]))
        self.assertFalse(plan["packageNamePromptRequired"])

    def test_legacy_manifests_require_exact_path_owner_and_do_not_claim_fingerprint(self):
        for name in ("alpha", "alpha-alt"):
            folder = self.runtime / "assets/data" / name
            manifest_path = folder / "compatScripts.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["roots"] = [{"engine": "V-Slice", "path": self.owner}]
            write_json(manifest_path, manifest)
            (folder / "importProvenance.json").unlink()

        plan = self.make_plan()
        self.assertEqual(plan["selectedRoot"], self.owner)
        self.assertEqual(plan["ownerAssociationMethod"],
                         "legacy-path-derived-owner-and-selectedRoot-manifests")
        self.assertFalse(plan["preflight"]["sourceFingerprintPersistedInChartProvenance"])
        self.assertFalse(plan["preflight"]["visualOnlyBranchExpectedForEveryChart"])
        self.assertTrue(all(chart["provenance"] is None for chart in plan["selectedCharts"]))
        self.assertTrue(all(chart["ownerCount"] == 1 for chart in plan["selectedCharts"]))

    def test_apply_adds_owner_files_without_touching_charts_or_settings(self):
        plan = self.make_plan()
        plan_path = self.project / "tmp/reviewed-plan.json"
        refresh._write_json(plan_path, plan)

        def fake_native(_plan, report_root):
            report_root.mkdir(parents=True)
            self.assertEqual(json.loads((self.runtime / "assets/data/options.json").read_text()),
                             {"testDefaults": True})
            owner_file = self.runtime / self.owner / "images/custom_chars/converted.json"
            owner_file.write_text("converted visual\n", encoding="utf-8")
            (self.runtime / "assets/data/alpha/alpha.json").write_text("temporary chart mutation\n",
                                                                          encoding="utf-8")
            (self.runtime / "assets/songs/alpha/Inst.ogg").write_bytes(b"temporary audio mutation")
            return {"status": "passed", "events": ["success"], "returncode": 0}

        receipt = refresh.apply_plan(plan, plan_path, runner=fake_native)
        self.assertEqual(receipt["status"], "applied")
        self.assertEqual(receipt["postflight"]["newOwnerFiles"], ["images/custom_chars/converted.json"])
        self.assertEqual((self.runtime / "assets/data/alpha/alpha.json").read_text(encoding="utf-8"),
                         '{"song":{"song":"alpha"}}\n')
        self.assertEqual(json.loads((self.runtime / "assets/data/options.json").read_text()),
                         {"personalSetting": "preserve"})
        self.assertEqual((self.runtime / "assets/songs/alpha/Inst.ogg").read_bytes(),
                         b"original installed audio")
        self.assertTrue(receipt["postflight"]["attemptedProtectedFileChanges"])
        self.assertTrue(Path(receipt["backup"]).joinpath("receipt.json").is_file())

    def test_changed_preexisting_bytes_and_global_additions_roll_back(self):
        plan = self.make_plan()
        plan_path = self.project / "tmp/reviewed-plan.json"
        refresh._write_json(plan_path, plan)
        chart = self.runtime / "assets/data/alpha/alpha.json"
        owner_existing = self.runtime / self.owner / "images/custom_chars/existing.json"
        ui_addition = self.runtime_ui / "new-style/preset.json"

        def fake_native(_plan, report_root):
            report_root.mkdir(parents=True)
            self.assertEqual(json.loads((self.runtime / "assets/data/options.json").read_text()),
                             {"testDefaults": True})
            chart.write_text("mutated chart\n", encoding="utf-8")
            owner_existing.write_text("mutated owner\n", encoding="utf-8")
            ui_addition.parent.mkdir()
            ui_addition.write_text("unexpected global output\n", encoding="utf-8")
            return {"status": "passed", "events": ["success"], "returncode": 0}

        receipt = refresh.apply_plan(plan, plan_path, runner=fake_native)
        self.assertEqual(receipt["status"], "rolled-back")
        self.assertTrue(receipt["postflight"]["violations"])
        self.assertEqual(chart.read_text(encoding="utf-8"), '{"song":{"song":"alpha"}}\n')
        self.assertEqual(owner_existing.read_text(encoding="utf-8"), "keep owner bytes\n")
        self.assertEqual(json.loads((self.runtime / "assets/data/options.json").read_text()),
                         {"personalSetting": "preserve"})
        self.assertFalse(ui_addition.exists())
        self.assertFalse(ui_addition.parent.exists())
        self.assertEqual(receipt["rollbackErrors"], [])

    def test_postflight_exception_still_restores_options_and_chart_bytes(self):
        plan = self.make_plan()
        plan_path = self.project / "tmp/reviewed-plan.json"
        refresh._write_json(plan_path, plan)
        chart = self.runtime / "assets/data/alpha/alpha.json"
        owner_file = self.runtime / self.owner / "images/custom_chars/exception-probe.json"
        original_postflight = refresh._postflight
        calls = 0

        def failing_first_postflight(current_plan, native_result):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("injected postflight failure")
            return original_postflight(current_plan, native_result)

        def fake_native(_plan, report_root):
            report_root.mkdir(parents=True)
            chart.write_text("modified chart before exception\n", encoding="utf-8")
            (self.runtime / "assets/data/options.json").write_text("modified options before exception\n",
                                                                     encoding="utf-8")
            owner_file.write_text("new visual\n", encoding="utf-8")
            return {"status": "passed", "events": ["success"], "returncode": 0}

        with patch.object(refresh, "_postflight", side_effect=failing_first_postflight):
            receipt = refresh.apply_plan(plan, plan_path, runner=fake_native)

        self.assertEqual(receipt["status"], "rolled-back")
        self.assertIn("injected postflight failure",
                      receipt["postflight"]["preRestorationPostflightError"])
        self.assertTrue(receipt["protectedFilesRestoredAfterImport"])
        self.assertEqual(chart.read_text(encoding="utf-8"), '{"song":{"song":"alpha"}}\n')
        self.assertEqual(json.loads((self.runtime / "assets/data/options.json").read_text()),
                         {"personalSetting": "preserve"})
        self.assertFalse(owner_file.exists())
        self.assertEqual(receipt["rollbackErrors"], [])

    def test_legacy_refresh_removes_new_chart_provenance_and_surfaces_importer_errors(self):
        for name in ("alpha", "alpha-alt"):
            folder = self.runtime / "assets/data" / name
            manifest_path = folder / "compatScripts.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["roots"] = [{"engine": "V-Slice", "path": self.owner}]
            write_json(manifest_path, manifest)
            (folder / "importProvenance.json").unlink()

        plan = self.make_plan()
        plan_path = self.project / "tmp/reviewed-plan.json"
        refresh._write_json(plan_path, plan)
        provenance = self.runtime / "assets/data/alpha/importProvenance.json"
        owner_file = self.runtime / self.owner / "images/custom_chars/converted.json"
        missing_assets = [
            "HXC static asset missing: mechanics/Sign_Post_Mechanic",
            "HXC static asset missing: mechanics/HP GREMLIN",
            "HXC static asset missing: notes/NOTE_death",
        ]

        def fake_native(_plan, report_root):
            report_root.mkdir(parents=True)
            # A current importer can add provenance to only some one-root charts.
            # That must not invalidate the donor fingerprint check or survive the
            # backed-up visual-only refresh outside its selected owner namespace.
            write_json(provenance, {"sourceEngine": "V-Slice", "sourceFingerprint": self.fingerprint})
            owner_file.write_text("converted visual\n", encoding="utf-8")
            return {
                "status": "passed", "events": ["success"], "returncode": 0,
                "markers": [{"event": "success", "errors": 3, "errorDetails": missing_assets}],
            }

        receipt = refresh.apply_plan(plan, plan_path, runner=fake_native)

        self.assertEqual(receipt["status"], "applied")
        self.assertFalse(provenance.exists())
        self.assertEqual(owner_file.read_text(encoding="utf-8"), "converted visual\n")
        self.assertIn("runtime:assets/data/alpha/importProvenance.json",
                      receipt["postflight"]["removedOutsideOwnerAdditions"])
        self.assertTrue(receipt["protectedFilesRestoredAfterImport"])
        diagnostics = receipt["compatibilityDiagnostics"]
        self.assertFalse(diagnostics["evaluatedGameplayCompatibility"])
        self.assertEqual(diagnostics["reportedErrorCount"], 3)
        self.assertEqual(diagnostics["unresolvedSourceDependencies"], sorted(missing_assets))

    def test_cleanup_preserves_unrelated_new_song_directories(self):
        plan = self.make_plan()
        plan_path = self.project / "tmp/reviewed-plan.json"
        refresh._write_json(plan_path, plan)
        allowed_names = refresh._transaction_song_folder_names(plan)
        qualified = next(name for name in allowed_names if "--v-slice-" in name)
        qualified_folder = self.runtime / "assets/data" / qualified
        unrelated_folder = self.runtime / "assets/data/concurrent-user-song"
        unrelated_marker = unrelated_folder / "keep.txt"
        owner_file = self.runtime / self.owner / "images/custom_chars/temporary.json"

        def fake_native(_plan, report_root):
            report_root.mkdir(parents=True)
            qualified_folder.mkdir()
            unrelated_folder.mkdir()
            unrelated_marker.write_text("user content\n", encoding="utf-8")
            owner_file.write_text("temporary conversion\n", encoding="utf-8")
            return {"status": "passed", "events": ["success"], "returncode": 0}

        receipt = refresh.apply_plan(plan, plan_path, runner=fake_native)

        self.assertEqual(receipt["status"], "rollback-incomplete")
        self.assertTrue(unrelated_marker.is_file())
        self.assertEqual(unrelated_marker.read_text(encoding="utf-8"), "user content\n")
        self.assertFalse(qualified_folder.exists())
        self.assertFalse(owner_file.exists())
        self.assertTrue(any("preserved unrelated new entry" in error
                            for error in receipt["postflight"]["outsideOwnerCleanupErrors"]))
        self.assertTrue(any("preserved unrelated new entry" in error
                            for error in receipt["rollbackErrors"]))


if __name__ == "__main__":
    unittest.main()
