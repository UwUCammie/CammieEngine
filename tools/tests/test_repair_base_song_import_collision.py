"""Guard scoped cleanup of generated note registries on base songs."""

from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "repair_base_song_import_collision",
    ROOT / "tools/repair_base_song_import_collision.py",
)
REPAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPAIR)


class GeneratedNoteSubsetTest(unittest.TestCase):
    def test_only_generated_subset_without_authored_base_registry_is_removable(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)
            old, qualified, source = (root / name for name in
                                      ("old.json", "qualified.json", "source.json"))
            old.write_text(json.dumps([{"id": "a"}]))
            qualified.write_text(json.dumps([{"id": "a"}, {"id": "b"}]))
            self.assertTrue(REPAIR.generated_note_subset(old, qualified, source))
            source.write_text("[]")
            self.assertFalse(REPAIR.generated_note_subset(old, qualified, source))
            source.unlink()
            old.write_text(json.dumps([{"id": "other"}]))
            self.assertFalse(REPAIR.generated_note_subset(old, qualified, source))
            old.write_text(json.dumps([{"id": "codename:GF:0",
                                        "sourceEngine": "Codename Engine", "sourceKind": "GF"}]))
            qualified.write_text(json.dumps([{"id": "codename:GF:2",
                                              "sourceEngine": "Codename Engine", "sourceKind": "GF"}]))
            self.assertTrue(REPAIR.generated_note_subset(old, qualified, source))
            qualified.write_text(json.dumps([{"id": "codename:GF:2",
                                              "sourceEngine": "Codename Engine", "sourceKind": "Other"}]))
            self.assertFalse(REPAIR.generated_note_subset(old, qualified, source))
            old.write_text("not json")
            self.assertFalse(REPAIR.generated_note_subset(old, qualified, source))


if __name__ == "__main__":
    unittest.main()
