"""Read-only reachability audit for the legacy Chaos intro graph.

Chaos's donor chart is one of the older malformed JSON files, so this test
repairs only the in-memory text.  It deliberately follows the chart's
registered cutscene instead of treating every neighbouring HScript as live
content.  Donor bytes are hashed around the audit to keep the test read-only.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DONOR = Path("/run/media/cammie/External Storage/modding-plus-fnf")
DONOR = Path(os.environ.get("REGRESSION_DONOR_ROOT", str(DEFAULT_DONOR)))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_legacy_json(path: Path):
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Match the importer's conservative separator repair: only insert a
        # comma between a complete JSON value and a newline-delimited property.
        repaired = re.sub(
            r'(true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|"(?:\\.|[^"\\])*"|\]|\})([ \t]*\r?\n[ \t]*"[^"\r\n]+"[ \t]*:)',
            r"\1,\2",
            raw,
        )
        # TJSON also accepts a trailing comma; Python's decoder does not.
        repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
        return json.loads(repaired)


class ChaosDonorReachabilityTest(unittest.TestCase):
    def _paths(self):
        paths = [
            DONOR / "assets/data/chaos/chaos.json",
            DONOR / "assets/images/custom_stages/custom_stages.json",
            DONOR / "assets/images/custom_stages/chamber.hscript",
            DONOR / "assets/images/custom_cutscenes/cutscenes.json",
            DONOR / "assets/images/custom_cutscenes/fleetway.hscript",
            DONOR / "assets/images/custom_cutscenes/chaos.hscript",
        ]
        for asset in (
            "Wall.png",
            "Wall.xml",
            "Floor.png",
            "Floor.xml",
            "FleetwayBGshit.png",
            "FleetwayBGshit.xml",
            "Emerald Beam.png",
            "Emerald Beam.xml",
            "Emerald Beam Charged.png",
            "Emerald Beam Charged.xml",
            "Emeralds.png",
            "Emeralds.xml",
            "pebles.png",
            "pebles.xml",
            "Porker Lewis.png",
            "Porker Lewis.xml",
            "The Chamber.png",
            "The Chamber.xml",
        ):
            paths.append(DONOR / "assets/images/custom_stages/chamber" / asset)
        for asset in ("black2.png", "The Chamber.png", "The Chamber.xml"):
            paths.append(DONOR / "assets/images/custom_cutscenes/fleetway" / asset)
        return paths

    def test_chart_reaches_fleetway_not_orphan_chaos_script(self):
        paths = self._paths()
        if not all(path.is_file() for path in paths):
            missing = next(path for path in paths if not path.is_file())
            self.skipTest(f"mounted Chaos donor unavailable: {missing}")
        before = {path: sha256(path) for path in paths}
        try:
            chart = parse_legacy_json(paths[0])["song"]
            self.assertEqual(chart["stage"], "chamber")
            self.assertEqual(chart["cutsceneType"], "fleetway")

            stages = parse_legacy_json(paths[1])
            cutscenes = parse_legacy_json(paths[3])
            self.assertNotIn("chamber", stages)
            self.assertEqual(cutscenes["fleetway"], "fleetway")
            self.assertNotIn("chaos", cutscenes)

            fleetway = paths[4].read_text(encoding="utf-8")
            orphan = paths[5].read_text(encoding="utf-8")
            self.assertNotIn("thechamber", fleetway)
            self.assertNotIn("floor.animation.play", fleetway)
            self.assertIn("thechamber.animation.play", orphan)
            self.assertIn("emeraldbeamyellow.visible", orphan)

            stage = paths[2].read_text(encoding="utf-8")
            self.assertTrue(
                (DONOR / "assets/images/custom_stages/chamber/The Chamber.png").is_file(),
                "donor stage does not carry the chamber atlas",
            )
            self.assertTrue(
                (DONOR / "assets/images/custom_cutscenes/fleetway/The Chamber.png").is_file(),
                "reachable fleetway cutscene does not carry its chamber atlas",
            )
            chaos_branch, powerless_branch = stage.split(
                'if (curSong == "Powerless")', 1
            )
            for name in (
                "wall",
                "floor",
                "fleetwaybgshit",
                "emeraldbeam",
                "emeraldbeamyellow",
                "emeralds",
                "pebles",
                "porker",
            ):
                self.assertRegex(
                    chaos_branch,
                    rf"(?m)^\s*(?:var\s+)?{re.escape(name)}\s*=\s*new\s+",
                    name,
                )
                self.assertRegex(
                    chaos_branch,
                    rf"addSprite\(\s*{re.escape(name)}\s*,",
                    name,
                )
            # The chamber overlay exists only in the later Powerless branch;
            # it is not a reachable Chaos stage export.
            self.assertNotRegex(chaos_branch, r"\bthechamber\s*=")
            self.assertRegex(powerless_branch, r"\bthechamber\s*=\s*new\s+")
        finally:
            self.assertEqual(
                {path: sha256(path) for path in paths},
                before,
                "Chaos donor bytes changed during read-only graph audit",
            )

    def test_direct_legacy_stage_script_fallback_is_generic(self):
        song = (ROOT / "source/Song.hx").read_text(encoding="utf-8")
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("Legacy Modding Plus packs", song)
        self.assertIn("assets/images/custom_stages/' + directName", song)
        self.assertIn("same bounded direct-script shape", play_state)
        self.assertIn("assets/images/custom_stages/' + requested", play_state)
        self.assertNotIn("chaos", song[song.index("static function validStage"):song.index("static function validUIType")])
        self.assertNotIn("chaos", play_state[play_state.index("function registeredStage"):play_state.index("function protectedStageObject")])


if __name__ == "__main__":
    unittest.main()
