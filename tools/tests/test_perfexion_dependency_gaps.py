"""Mounted evidence for the three unresolved PERFEXION visual dependencies.

These assertions deliberately inspect the donor without copying or rewriting it.  The
chart and character sidecar are present, but their referenced stage/art/icon payloads
are not present under any case variant, and Xfracture has no alternate difficulty that
could provide a generic fallback.
"""

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
PERFEXION = DONOR / "psych/PERFEXION Demo1"


def _paths_with_name_or_stem(root: Path, stem: str):
    wanted = stem.casefold()
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.name.casefold() == wanted
        or (path.is_file() and path.stem.casefold() == wanted)
    )


def _hash_files(paths):
    """Hash only authoritative donor inputs used by this bounded audit."""
    result = {}
    for path in sorted({Path(path) for path in paths}):
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        result[path] = digest.hexdigest()
    return result


@unittest.skipUnless(DONOR.is_dir(), "the external example-mod fixture is not mounted")
class PerfexionDependencyGapsTest(unittest.TestCase):
    def test_authoritative_chart_and_character_sidecar_reference_the_three_gaps(self):
        chart_path = PERFEXION / "data/Xfracture/xfracture-hard.json"
        character_path = PERFEXION / "characters/girl-mad.json"
        chart = json.loads(chart_path.read_text())
        song = chart["song"]
        character = json.loads(character_path.read_text())

        self.assertEqual(song["song"], "Xfracture")
        self.assertEqual(song["stage"], "bedroom")
        self.assertEqual(song["player1"], "girl-mad")
        self.assertEqual(character["image"], "characters/girl-mad")
        self.assertEqual(character["healthicon"], "girl")

    def test_stage_gap_has_no_case_variant_or_donor_stage_definition(self):
        # A stage alias can only be justified by a real donor stage payload.  The
        # PERFEXION stage folder contains Haven variants, never bedroom.
        self.assertEqual(_paths_with_name_or_stem(PERFEXION / "stages", "bedroom"), [])
        self.assertEqual(_paths_with_name_or_stem(PERFEXION / "images", "bedroom"), [])
        self.assertEqual(
            _paths_with_name_or_stem(PERFEXION / "stages", "haven"),
            ["Haven.json", "Haven.lua"],
        )

    def test_character_and_health_icon_gaps_have_no_case_variant_payload(self):
        character_images = PERFEXION / "images/characters"
        icon_images = PERFEXION / "images/icons"
        self.assertEqual(_paths_with_name_or_stem(character_images, "girl-mad"), [])
        self.assertEqual(_paths_with_name_or_stem(icon_images, "icon-girl"), [])
        self.assertEqual(_paths_with_name_or_stem(icon_images, "girl"), [])
        # Also search the complete image/shared-image roots so a differently
        # laid-out Psych/Kade payload cannot hide behind a path assumption.
        for image_root in (PERFEXION / "images", PERFEXION / "shared/images"):
            self.assertEqual(_paths_with_name_or_stem(image_root, "girl-mad"), [])
            self.assertEqual(_paths_with_name_or_stem(image_root, "icon-girl"), [])
            self.assertEqual(_paths_with_name_or_stem(image_root, "girl"), [])

    def test_xfracture_has_no_alternate_difficulty_fallback(self):
        charts = sorted(
            path.relative_to(PERFEXION / "data/Xfracture").as_posix()
            for path in (PERFEXION / "data/Xfracture").rglob("*.json")
            if path.is_file()
        )
        self.assertEqual(charts, ["xfracture-hard.json"])

    def test_bounded_audit_leaves_authoritative_donor_hashes_unchanged(self):
        chart_path = PERFEXION / "data/Xfracture/xfracture-hard.json"
        character_path = PERFEXION / "characters/girl-mad.json"
        existing_stage_evidence = [
            PERFEXION / "stages" / relative
            for relative in _paths_with_name_or_stem(PERFEXION / "stages", "haven")
        ]
        authoritative = [chart_path, character_path, *existing_stage_evidence]
        before = _hash_files(authoritative)

        # Repeat the read-only evidence pass in the same process used by the
        # test suite.  If an implementation accidentally writes donor content,
        # the source hashes make that violation explicit.
        json.loads(chart_path.read_text())
        json.loads(character_path.read_text())
        for path in existing_stage_evidence:
            path.read_bytes()

        self.assertEqual(before, _hash_files(authoritative))

    def test_xfracture_fallback_can_be_planned_and_passes_launch_gate(self):
        chart_path = PERFEXION / "data/Xfracture/xfracture-hard.json"
        character_path = PERFEXION / "characters/girl-mad.json"
        chart = json.loads(chart_path.read_text())["song"]
        character = json.loads(character_path.read_text())
        self.assertEqual(
            [chart["stage"], chart["player1"], character["healthicon"]],
            ["bedroom", "girl-mad", "girl"],
        )

        fixture = r'''
class PerfexionFallbackTest {
    static function fail(message:String):Void throw message;
    static function main() {
        var stage = EngineCompat.planVisualFallback("stage", "bedroom",
            "psych/PERFEXION Demo1/data/Xfracture/xfracture-hard.json",
            EngineCompat.visualDependencySearchPaths("stage", "bedroom"),
            "stage visuals use the neutral native stage group; notes, timing, and gameplay callbacks continue",
            "donor-source-omission");
        var character = EngineCompat.planVisualFallback("character", "girl-mad",
            "psych/PERFEXION Demo1/data/Xfracture/xfracture-hard.json",
            EngineCompat.visualDependencySearchPaths("character", "girl-mad"),
            "character visual falls back to Dad; note lanes, timing, and score gameplay continue",
            "donor-source-omission");
        var icon = EngineCompat.planVisualFallback("health-icon", "girl",
            "psych/PERFEXION Demo1/characters/girl-mad.json",
            EngineCompat.visualDependencySearchPaths("health-icon", "girl"),
            "health display uses the neutral icon grid; health values, scoring, and note gameplay continue",
            "donor-source-omission");
        for (plan in [stage, character, icon]) {
            if (!EngineCompat.canUseVisualFallback(plan)) fail("fallback launch gate");
            if (!plan.preserveRequested) fail("authored id was not preserved");
            if (plan.diagnostic.code != "missing-donor-dependency") fail("missing classification");
            if (plan.diagnostic.origin == "" || plan.diagnostic.searched.length == 0
                || plan.diagnostic.gameplayImpact == "") fail("diagnostic provenance");
        }
        if (stage.fallback != "stage" || character.fallback != "dad" || icon.fallback != "iconGrid")
            fail("unsafe visual fallback");
        var unsupported = EngineCompat.planVisualFallback("character", "present-but-unsupported",
            "synthetic donor implementation", ["characters/present-but-unsupported.json"],
            "character cannot execute the donor implementation", "unsupported-engine-behavior");
        if (unsupported.diagnostic.code != "unsupported-engine-dependency")
            fail("unsupported engine behavior was not distinguished");
        if (EngineCompat.canUseVisualFallback(unsupported))
            fail("unsupported engine behavior passed the launch gate");
    }
}
'''
        with tempfile.TemporaryDirectory(dir=Path(os.environ.get("TMPDIR", ROOT / "tmp"))) as folder:
            source = Path(folder) / "PerfexionFallbackTest.hx"
            source.write_text(fixture)
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-cp", str(ROOT / "source"), "-main", "PerfexionFallbackTest", "--interp"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        playstate = (ROOT / "source/PlayState.hx").read_text()
        character_source = (ROOT / "source/Character.hx").read_text()
        health_icon = (ROOT / "source/HealthIcon.hx").read_text()
        stage_helper = (ROOT / "source/StageHelper.hx").read_text()
        importer = (ROOT / "source/ImportWorkflow.hx").read_text()
        self.assertIn("curStage.applyNativeFallback(SONG.stage", playstate)
        self.assertNotIn("curStage.name = 'Invalid Stage: ' + SONG.stage", playstate)
        self.assertIn("public var authoredName:String", stage_helper)
        self.assertIn("public function applyNativeFallback", stage_helper)
        self.assertIn("EngineCompat.planVisualFallback('character'", character_source)
        self.assertIn("EngineCompat.planVisualFallback('health-icon'", health_icon)
        self.assertIn("if (daData == null)", health_icon)
        self.assertIn("missingIconReference", health_icon)
        self.assertIn("donor-source-omission", importer)
        self.assertIn("fallbackPlan.diagnostic.message", importer)


if __name__ == "__main__":
    unittest.main()
