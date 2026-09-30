"""Scoped mixed-owner import reset keeps unrelated runtime assets intact."""

import fcntl
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import reset_mixed_imports as reset


ROOT = Path(__file__).resolve().parents[2]
OWNER = "assets/imported_mods/selected-owner"
OTHER = "assets/imported_mods/foreign-owner"


class ResetMixedImportsTest(unittest.TestCase):
    def setUp(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "tmp")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "repo"
        self.runtime = self.base / "runtime"
        (self.repo / ".tools").mkdir(parents=True)
        (self.runtime / OWNER).mkdir(parents=True)
        (self.runtime / OTHER).mkdir(parents=True)
        (self.runtime / "assets/data").mkdir(parents=True)
        (self.runtime / "assets/songs").mkdir(parents=True)
        self.registry = self.runtime / "assets/data/freeplaySongJson.jsonc"
        self.registry.write_text(json.dumps([
            {"name": "One", "songs": [{"name": "mixed", "character": "bf"},
                                      {"name": "owned", "character": "bf"}]},
            {"name": "Two", "songs": [{"name": "foreign", "character": "dad"}]},
        ]))
        self.registry_before = self.registry.read_bytes()
        self.song("mixed", OWNER, [OTHER, OWNER])
        self.song("owned", OWNER, [OWNER])
        self.song("foreign", OTHER, [OTHER, OWNER])
        (self.runtime / "assets/data/options.json").write_text('{"offset":33}')
        (self.runtime / OWNER / "image.png").write_bytes(b"shared media")

    def song(self, name, selected, roots):
        data = self.runtime / "assets/data" / name
        audio = self.runtime / "assets/songs" / name
        data.mkdir()
        audio.mkdir()
        (data / "compatScripts.json").write_text(json.dumps({
            "selectedRoot": selected,
            "roots": [{"engine": "V-Slice", "path": root} for root in roots],
        }))
        (data / f"{name}.json").write_text('{"song":{"song":"' + name + '"}}')
        (audio / "Inst.ogg").write_bytes(b"audio")

    def test_plan_and_apply_move_only_mixed_selected_song(self):
        plan = reset.plan_reset(self.runtime, OWNER)
        self.assertEqual([item["song"] for item in plan["candidates"]], ["mixed"])
        self.assertEqual(self.registry.read_bytes(), self.registry_before)
        self.assertTrue((self.runtime / "assets/data/mixed").exists())
        with patch.object(reset, "running_funkin", return_value=False):
            backup = reset.apply_reset(plan, repo_root=self.repo)
        self.assertIsNotNone(backup)
        self.assertFalse((self.runtime / "assets/data/mixed").exists())
        self.assertFalse((self.runtime / "assets/songs/mixed").exists())
        self.assertTrue((backup / "assets/data/mixed/mixed.json").exists())
        self.assertTrue((backup / "assets/songs/mixed/Inst.ogg").exists())
        self.assertEqual((backup / "freeplaySongJson.jsonc").read_bytes(), self.registry_before)
        self.assertEqual([entry["name"] for category in json.loads(self.registry.read_text())
                          for entry in category["songs"]], ["owned", "foreign"])
        self.assertTrue((self.runtime / "assets/data/owned").exists())
        self.assertTrue((self.runtime / "assets/data/foreign").exists())
        self.assertEqual((self.runtime / "assets/data/options.json").read_text(), '{"offset":33}')
        self.assertEqual((self.runtime / OWNER / "image.png").read_bytes(), b"shared media")

    def test_changed_plan_and_held_lock_leave_runtime_untouched(self):
        plan = reset.plan_reset(self.runtime, OWNER)
        (self.runtime / "assets/data/mixed/mixed.json").write_text('{"song":{"song":"mixed","bpm":140}}')
        with patch.object(reset, "running_funkin", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "plan changed"):
                reset.apply_reset(plan, repo_root=self.repo)
        self.assertEqual(self.registry.read_bytes(), self.registry_before)
        lock_path = self.repo / ".tools/runtime-0.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                reset.apply_reset(reset.plan_reset(self.runtime, OWNER), repo_root=self.repo)
        self.assertTrue((self.runtime / "assets/data/mixed").exists())

    def test_registry_failure_rolls_back_both_song_directories(self):
        plan = reset.plan_reset(self.runtime, OWNER)
        with patch.object(reset, "running_funkin", return_value=False), \
             patch.object(reset.os, "replace", side_effect=OSError("write failed")):
            with self.assertRaisesRegex(OSError, "write failed"):
                reset.apply_reset(plan, repo_root=self.repo)
        self.assertTrue((self.runtime / "assets/data/mixed/mixed.json").exists())
        self.assertTrue((self.runtime / "assets/songs/mixed/Inst.ogg").exists())
        self.assertEqual(self.registry.read_bytes(), self.registry_before)

    def test_symlink_in_selected_song_is_rejected(self):
        (self.runtime / "assets/data/mixed/escape").symlink_to(self.base)
        with self.assertRaisesRegex(ValueError, "symlink"):
            reset.plan_reset(self.runtime, OWNER)


if __name__ == "__main__":
    unittest.main()
