"""Regression inventory for the mounted V-Slice chart/event boundary.

This test is intentionally data-only.  It does not import, rewrite, build, or
launch donor content; it pins the selected mounted corpus and the source-level
contract which preserves foreign event names for the stage HXC callback.
"""

import json
import unittest
from collections import Counter
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


EXPECTED_COUNTS = {
    "FocusCamera": 1710,
    "Zoom Rabbit": 443,
    "ZoomCamera": 403,
    "lightsBeat": 118,
    "ChangeCharacterCL": 74,
    "AddCamZoomPsych": 67,
    "PlayAnimation": 63,
    "EyePopup": 43,
    "SetCameraBop": 37,
    "spotlight": 30,
    "NoteSwapEvent": 16,
    "Flash": 8,
    "charChange": 8,
    "ChangeCharacter": 7,
    "camera": 5,
    "extra-events-cameraFlashEvent": 5,
    "ChangeStage": 4,
    "TWIM-ON/OFF": 3,
    "Fade": 2,
    "Play Animation": 2,
    "ending": 2,
    "extra-events-addLyricsEvent": 2,
    "fixstuff": 2,
    "tweenScreenR": 2,
    "Alt Idle Rabbit": 1,
    "Baka": 1,
    "Crowd-Appears": 1,
    "Flash Camera": 1,
    "PlayVideo": 1,
    "ROLLING-TIME": 1,
    "ScrollSpeed": 1,
    "SetHealthIcon": 1,
    "TWIM-SCREAM": 1,
    "bye": 1,
    "extra-events-cameraFadeEvent": 1,
    "fixFinal": 1,
    "screenScream": 1,
    # Vs Tricky joined the mounted corpus with its own event vocabulary.
    "tricky.ExpurgationGremlinEvent": 1,
    "tricky.ExpurgationSignEvent": 47,
    # Singstar Challenges PC joined the mounted corpus with Virgin Rage.
    "redMenaceAlpha": 1,
    "redMenaceAlphaOut": 1,
    "screenShake": 2,
    "setSuffix": 1,
    "zoomCameraPsych": 3,
}


STAGE_HXC_ONLY = {
    "concert": {
        "Crowd-Appears",
        "camera",
        "Fade",
        "TWIM-SCREAM",
        "TWIM-ON/OFF",
        "ROLLING-TIME",
        "fixstuff",
        "Baka",
        "fixFinal",
        "ending",
    },
    "concert2": {"screenScream", "tweenScreenR", "bye", "Fade", "ending"},
    "miku": {"spotlight", "lightsBeat", "Alt Idle Rabbit"},
}


STAGE_SCRIPTS = {
    "concert": DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/stages/concert.hxc",
    "concert2": DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/stages/concert2.hxc",
    "miku": DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/stages/miku.hxc",
}


def selected_chart_pairs():
    pairs = []
    if not DONOR.is_dir():
        return pairs
    for chart in sorted(DONOR.rglob("*-chart.json")):
        metadata = chart.with_name(chart.name.replace("-chart.json", "-metadata.json"))
        if metadata.is_file():
            pairs.append((chart, metadata))
    return pairs


class VSliceEventInventoryTest(unittest.TestCase):
    def test_selected_corpus_counts_and_foreign_event_contract(self):
        pairs = selected_chart_pairs()
        if not pairs:
            self.skipTest("mounted V-Slice corpus is unavailable")

        self.assertEqual(len(pairs), 59)
        counts = Counter()
        payload_keys = {}
        for chart_path, _metadata_path in pairs:
            chart = json.loads(chart_path.read_text())
            for event in chart.get("events", []):
                name = event.get("e")
                counts[name] += 1
                payload_keys.setdefault(name, set()).update((event.get("v") or {}).keys())

        self.assertEqual(sum(counts.values()), 3125)
        self.assertEqual(dict(counts), EXPECTED_COUNTS)
        self.assertEqual(len(counts), 44)

        foreign_names = set().union(*STAGE_HXC_ONLY.values())
        self.assertEqual(len(foreign_names), 16)
        self.assertEqual(foreign_names, set(EXPECTED_COUNTS) - {
            "FocusCamera", "Zoom Rabbit", "ZoomCamera", "ChangeCharacterCL",
            "AddCamZoomPsych", "PlayAnimation", "EyePopup", "SetCameraBop",
            "NoteSwapEvent", "Flash", "charChange", "ChangeCharacter",
            "extra-events-cameraFlashEvent", "ChangeStage", "Play Animation",
            "extra-events-addLyricsEvent", "ScrollSpeed", "SetHealthIcon",
            "PlayVideo", "Flash Camera", "extra-events-cameraFadeEvent",
            "tricky.ExpurgationGremlinEvent", "tricky.ExpurgationSignEvent",
            "redMenaceAlpha", "redMenaceAlphaOut", "screenShake", "setSuffix",
            "zoomCameraPsych",
        })
        self.assertEqual(sum(counts[name] for name in foreign_names), 172)
        self.assertEqual(sum(counts.values()) - sum(counts[name] for name in foreign_names), 2953)

        for name in foreign_names:
            self.assertEqual(payload_keys[name], {"value1", "value2"}, name)

        importer = (ROOT / "source/VSliceImporter.hx").read_text()
        self.assertIn("Json.stringify(values)", importer)
        self.assertIn("foreign-event-preserved", importer)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        hxc_dispatch = play_state.index("callAllHScript('songEvent', [hxcEvent]);")
        native_route = play_state.index("EngineCompat.routeLegacyEvent", hxc_dispatch)
        self.assertLess(hxc_dispatch, native_route)
        self.assertIn("hxcEvent.nativeHandled", play_state)

        for stage, names in STAGE_HXC_ONLY.items():
            source = STAGE_SCRIPTS[stage].read_text(errors="ignore")
            self.assertIn("onSongEvent", source, stage)
            self.assertIn("event.eventData", source, stage)
            self.assertIn("eventKind", source, stage)
            for name in names:
                self.assertIn(name, source, f"{stage}: {name}")


if __name__ == "__main__":
    unittest.main()
