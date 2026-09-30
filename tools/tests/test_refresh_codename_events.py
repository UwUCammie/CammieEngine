"""Synthetic, executable checks for the Codename event refresh safety gate."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("refresh_codename_events", ROOT / "tools/refresh_codename_events.py")
REFRESH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFRESH)


class CodenameEventRefreshTest(unittest.TestCase):
    def fixture(self, work):
        donor = work / "donor"
        runtime = work / "runtime"
        song = donor / "songs/SourceSong"
        (song / "charts").mkdir(parents=True)
        (runtime / "assets/data/sourcesong").mkdir(parents=True)
        (song / "meta.json").write_text('{"displayName":"Alias","difficulties":["normal"],"bpm":120,"stepsPerBeat":4}')
        (song / "charts/normal.json").write_text(json.dumps({"codenameChart": True,
            "events": [
                {"name": "Set GF Speed", "time": 100.00005, "params": [3]},
                {"name": "Set GF Speed", "time": 100.0, "params": [2]},
                {"name": "Set GF Speed", "time": 50.0, "params": [1]},
                {"name": "Set GF Speed", "time": 300.0, "params": [4]},
            ]}))
        (song / "events.json").write_text(json.dumps({"events": [
            {"name": "Set GF Speed", "time": 300.0, "params": [5]}
        ]}))
        owner = REFRESH.render(donor.resolve(), [])["namespace"]
        data = runtime / "assets/data/sourcesong"
        (data / "compatScripts.json").write_text(json.dumps({"version": 1,
            "roots": [{"engine": "Codename Engine", "path": owner}], "selectedRoot": owner}))
        plan = runtime / owner / "songs/SourceSong/__cammie_compat_scripts.json"
        plan.parent.mkdir(parents=True)
        plan.write_text(json.dumps({"version": 1, "song": "SourceSong", "stages": {}}))
        request = [{"id": "sourcesong/normal", "chart": str(song / "charts/normal.json"),
                    "sidecar": str(song / "events.json"), "difficulty": "normal"}]
        rendered = REFRESH.render(donor.resolve(), request)["charts"][0]
        old = rendered["legacy"]
        native = data / "sourcesong.json"
        # Keep intentional whitespace and an unrelated user-authored note edit.
        before = '{ "song" : {"song":"sourcesong", "notes" : [{"custom":"keep me"}], "events" : ' + \
                 json.dumps(old, separators=(",", ":")) + ', "extra": 123}, "other": "preserve" }\n'
        native.write_text(before)
        return donor, runtime, native, rendered, before

    def test_legacy_match_updates_only_events_and_preserves_source_timing(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            donor, runtime, native, rendered, before = self.fixture(Path(scratch))
            plan = REFRESH.make_plan(donor, runtime)
            self.assertEqual(len(plan["candidates"]), 1, plan["skipped"])
            candidate = plan["candidates"][0]
            self.assertEqual(candidate["oldTimes"], [50, 100.00005, 300])
            self.assertEqual(candidate["newTimes"], [50, 100, 100.00005, 300])
            self.assertEqual(candidate["oldRows"], candidate["newRows"])
            plan_file = Path(scratch) / "reviewed-plan.json"
            plan_file.write_text(json.dumps(plan))
            # This fixture checks event bytes, while the transaction suite tests
            # real flock behavior in isolated lock files. Avoid contending with
            # a canonical build or live native run during the parallel suite.
            with patch.object(REFRESH.fcntl, "flock"):
                backup = REFRESH.apply_plan(plan, plan_file)
            try:
                self.assertTrue(backup.is_dir())
                self.assertEqual((backup / native.relative_to(runtime)).read_text(), before)
            finally:
                shutil.rmtree(backup)
            after = native.read_text()
            old_span, _ = REFRESH.events_span(before)
            new_span, events = REFRESH.events_span(after)
            self.assertEqual(before[:old_span[0]], after[:new_span[0]])
            self.assertEqual(before[old_span[1]:], after[new_span[1]:])
            self.assertEqual(events, rendered["current"])
            repeated = REFRESH.make_plan(donor, runtime)
            self.assertEqual(repeated["candidates"], [])
            self.assertEqual(repeated["skipped"], [])

    def test_changed_events_and_donor_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            donor, runtime, native, _, _ = self.fixture(Path(scratch))
            plan = REFRESH.make_plan(donor, runtime)
            plan_file = Path(scratch) / "reviewed-plan.json"
            plan_file.write_text(json.dumps(plan))
            native.write_text(native.read_text().replace('"Set GF Speed"', '"Edited Event"', 1))
            self.assertEqual(len(REFRESH.make_plan(donor, runtime)["candidates"]), 0)
            with patch.object(REFRESH.fcntl, "flock"), self.assertRaises(ValueError):
                REFRESH.apply_plan(plan, plan_file)
            self.assertIn("Edited Event", native.read_text())
            donor, runtime, native, _, before = self.fixture(Path(scratch) / "second")
            plan = REFRESH.make_plan(donor, runtime)
            plan_file.write_text(json.dumps(plan))
            (donor / "songs/SourceSong/charts/normal.json").write_text('{"events":[]}')
            with patch.object(REFRESH.fcntl, "flock"), self.assertRaises(ValueError):
                REFRESH.apply_plan(plan, plan_file)
            self.assertEqual(native.read_text(), before)

    def test_owner_and_ambiguous_difficulty_do_not_refresh(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            donor, runtime, native, _, _ = self.fixture(Path(scratch))
            manifest = native.parent / "compatScripts.json"
            data = json.loads(manifest.read_text())
            data["selectedRoot"] = "assets/imported_mods/foreign"
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "no song selects"):
                REFRESH.make_plan(donor, runtime)
            data["selectedRoot"] = data["roots"][0]["path"]
            manifest.write_text(json.dumps(data))
            second = donor / "songs/SourceSong/charts/Normal.json"
            second.write_bytes((donor / "songs/SourceSong/charts/normal.json").read_bytes())
            plan = REFRESH.make_plan(donor, runtime)
            self.assertEqual(plan["candidates"], [])
            self.assertTrue(any("multiple donor difficulties" in item["reason"] for item in plan["skipped"]))

    def test_duplicate_keys_are_not_patched(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            REFRESH.events_span('{"song":{"events":[],"events":[]}}')

    def test_only_generated_focus_options_allow_serializer_order_drift(self):
        expected = [[0, [["Focus Camera", "650", "450",
                         '{"duration":16,"cancelMovement":false,"char":"-1","codenameParams":[650,450,false,16],"ease":"cube"}']]]]
        reordered = [[0, [["Focus Camera", "650", "450",
                          '{"ease":"cube","codenameParams":[650,450,false,16],"char":"-1","cancelMovement":false,"duration":16}']]]]
        self.assertEqual(REFRESH.legacy_matches(reordered, expected), (True, 1))
        changed = [[0, [["Focus Camera", "650", "450",
                        reordered[0][1][0][3].replace('"duration":16', '"duration":17')]]]]
        self.assertEqual(REFRESH.legacy_matches(changed, expected), (False, 0))
        duplicate = [[0, [["Focus Camera", "650", "450",
                          reordered[0][1][0][3].replace('"duration":16', '"duration":16,"duration":16')]]]]
        self.assertEqual(REFRESH.legacy_matches(duplicate, expected), (False, 0))
        other = [[0, [["Custom Event", "650", "450", reordered[0][1][0][3]]]]]
        self.assertEqual(REFRESH.legacy_matches(other, expected), (False, 0))
        boolean_time = [[False, expected[0][1]]]
        self.assertEqual(REFRESH.legacy_matches(boolean_time, expected), (False, 0))

    def test_generated_foreign_payload_accepts_key_order_only(self):
        expected = [[0, [["Camera Follow Pos",
                         '{"name":"Camera Follow Pos","engine":"codename","params":[1030,270,false]}',
                         "", ""]]]]
        reordered = [[0, [["Camera Follow Pos",
                          '{"params":[1030,270,false],"engine":"codename","name":"Camera Follow Pos"}',
                          "", ""]]]]
        self.assertEqual(REFRESH.legacy_matches(reordered, expected), (True, 1))
        changed = [[0, [["Camera Follow Pos",
                        reordered[0][1][0][1].replace('1030', '1031'), "", ""]]]]
        self.assertEqual(REFRESH.legacy_matches(changed, expected), (False, 0))
        duplicate = [[0, [["Camera Follow Pos",
                          reordered[0][1][0][1].replace('"engine":"codename"',
                                                       '"engine":"codename","engine":"codename"'),
                          "", ""]]]]
        self.assertEqual(REFRESH.legacy_matches(duplicate, expected), (False, 0))

    def test_compiled_release_child_mod_and_duplicate_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            donor, runtime, _, _, _ = self.fixture(Path(scratch))
            source = donor / "songs/SourceSong"
            compiled = donor / "mods/HL17/songs/SourceSong"
            compiled.parent.mkdir(parents=True)
            shutil.move(str(source), compiled)
            plan = REFRESH.make_plan(donor, runtime)
            self.assertEqual(len(plan["candidates"]), 1, plan["skipped"])
            duplicate = donor / "mods/Other/songs/SourceSong"
            duplicate.parent.mkdir(parents=True)
            shutil.copytree(compiled, duplicate)
            plan = REFRESH.make_plan(donor, runtime)
            self.assertEqual(plan["candidates"], [])
            self.assertTrue(any("donor song/meta/charts missing" in issue["reason"]
                                for issue in plan["skipped"]))

    def test_importer_valid_spaces_and_unicode_are_not_excluded(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            donor, runtime, native, _, _ = self.fixture(Path(scratch))
            owner = REFRESH.render(donor.resolve(), [])["namespace"]
            (donor / "songs/SourceSong").rename(donor / "songs/Source Mélodie")
            (donor / "songs/Source Mélodie/charts/normal.json").rename(
                donor / "songs/Source Mélodie/charts/Hard Mode.json")
            data = native.parent
            data.rename(data.parent / "source mélodie")
            (data.parent / "source mélodie/sourcesong.json").rename(
                data.parent / "source mélodie/source mélodie-hard-mode.json")
            source = runtime / owner / "songs/SourceSong"
            source.rename(source.parent / "Source Mélodie")
            metadata = source.parent / "Source Mélodie/__cammie_compat_scripts.json"
            value = json.loads(metadata.read_text())
            value["song"] = "Source Mélodie"
            metadata.write_text(json.dumps(value))
            plan = REFRESH.make_plan(donor, runtime)
            self.assertEqual(len(plan["candidates"]), 1, plan["skipped"])
            self.assertEqual(plan["candidates"][0]["id"], "source mélodie/Hard Mode")


if __name__ == "__main__":
    unittest.main()
