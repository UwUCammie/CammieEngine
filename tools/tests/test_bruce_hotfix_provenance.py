from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.audit_bruce_hotfix_provenance import audit_row, namespace_for, reconcile


class BruceHotfixProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.source = base / "donor" / "mods"
        self.runtime = base / "runtime"
        self.song = "Fixture-Song"
        self.source_chart = self.source / "data" / self.song / f"{self.song}.json"
        self.runtime_chart = self.runtime / "assets" / "data" / self.song.lower() / f"{self.song.lower()}.json"
        self.source_chart.parent.mkdir(parents=True)
        self.runtime_chart.parent.mkdir(parents=True)
        source_song = {
            "song": self.song,
            "needsVoices": True,
            "notes": [{"sectionNotes": [[0, 0, 0], [250, 1, 0]]}],
        }
        runtime_song = {**source_song, "song": self.song.lower(), "stageID": "nullspace"}
        self.source_chart.write_text(json.dumps({"song": source_song}), encoding="utf-8")
        self.runtime_chart.write_text(json.dumps({"song": runtime_song}), encoding="utf-8")

        source_audio = self.source / "songs" / self.song
        runtime_audio = self.runtime / "assets" / "songs" / self.song.lower()
        source_audio.mkdir(parents=True)
        runtime_audio.mkdir(parents=True)
        for name, payload in (("Inst.ogg", b"inst"), ("Voices.ogg", b"voices")):
            (source_audio / name).write_bytes(payload)
            (runtime_audio / name).write_bytes(payload)

        self.owner = namespace_for(self.source, "Psych Engine")
        manifest = {"selectedRoot": self.owner,
                    "roots": [{"engine": "Psych Engine", "path": self.owner}]}
        (self.runtime_chart.parent / "compatScripts.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.source / "stages").mkdir(parents=True)
        (self.source / "stages" / "nullspace.json").write_text(
            json.dumps({"defaultZoom": 0.9, "opponent": [100, 100]}), encoding="utf-8")
        (self.source / "stages" / "nullspace.lua").write_text("function onCreate() close(true); end\n", encoding="utf-8")
        owner_root = self.runtime / self.owner
        (owner_root / "stages").mkdir(parents=True)
        for name in ("nullspace.json", "nullspace.lua"):
            (owner_root / "stages" / name).write_bytes((self.source / "stages" / name).read_bytes())
        self.row = {
            "song": self.song,
            "difficulty": "normal",
            "sourceChart": f"data/{self.song}/{self.song}.json",
            "runtimeChart": f"assets/data/{self.song.lower()}/{self.song.lower()}.json",
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_owner_requires_chart_payload_and_required_audio_metadata(self):
        result = audit_row(self.row, self.source, self.runtime, self.owner)
        self.assertTrue(result["ownerManifestExact"])
        self.assertTrue(result["sourceNotePayloadMatch"])
        self.assertTrue(result["sourceAudioMetadataMatch"])
        self.assertTrue(result["ownerProvenanceVerified"])

    def test_same_basename_with_wrong_namespace_digest_is_not_owner_match(self):
        wrong = self.owner.rsplit("-", 1)[0] + "-0000000000"
        manifest_path = self.runtime_chart.parent / "compatScripts.json"
        manifest_path.write_text(json.dumps({
            "selectedRoot": wrong,
            "roots": [{"engine": "Psych Engine", "path": wrong}],
        }), encoding="utf-8")
        result = audit_row(self.row, self.source, self.runtime, self.owner)
        self.assertFalse(result["ownerManifestExact"])
        self.assertFalse(result["ownerProvenanceVerified"])

    def test_equal_row_count_with_changed_source_notes_is_not_provenance(self):
        chart = json.loads(self.runtime_chart.read_text(encoding="utf-8"))
        chart["song"]["notes"][0]["sectionNotes"][0][1] = 3
        self.runtime_chart.write_text(json.dumps(chart), encoding="utf-8")
        result = audit_row(self.row, self.source, self.runtime, self.owner)
        self.assertEqual(result["sourceNoteRows"], result["runtimeNoteRows"])
        self.assertFalse(result["sourceNotePayloadMatch"])
        self.assertFalse(result["ownerProvenanceVerified"])

    def test_audio_size_mismatch_is_not_provenance(self):
        runtime_voice = self.runtime / "assets" / "songs" / self.song.lower() / "Voices.ogg"
        runtime_voice.write_bytes(b"different length")
        result = audit_row(self.row, self.source, self.runtime, self.owner)
        self.assertFalse(result["sourceAudioMetadataMatch"])
        self.assertFalse(result["ownerProvenanceVerified"])

    def test_reconcile_records_stage_file_parity_without_claiming_screen_parity(self):
        inventory = {"packages": [{
            "name": "vs_brucedaworst_update_2_hotfix",
            "engine": "Psych Engine",
            "contentRoot": str(self.source),
            "stageMediaFiles": [],
            "songs": [{"id": self.song, "charts": [{"chartPath": self.row["sourceChart"]}]}],
        }]}
        matrix = {"rows": [{**self.row, "package": "vs_brucedaworst_update_2_hotfix"}]}
        result = reconcile(inventory, matrix, self.runtime)
        self.assertTrue(result["stageSourceParity"]["stageJsonEqual"])
        self.assertTrue(result["stageSourceParity"]["stageLuaEqual"])
        self.assertFalse(result["stageSourceParity"]["screenParityVerified"])


if __name__ == "__main__":
    unittest.main()
