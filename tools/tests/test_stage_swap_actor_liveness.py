"""Regression guards for the fantasy-girl-01 end-of-song SIGSEGV and the
stage-switch background cleanup.

Two engine contracts are pinned here:

1. Character companion scopes are seeded once per script identity, so their
   captured actor must never be honored after Change Character destroyed that
   instance and installed a fresh one into the role slot.
2. Stage script scopes must bind the donor `members` display-list idiom so
   translated V-Slice Stage.contains()/remove() cleanup actually runs instead
   of dying on an unknown identifier and leaving toggled-in layers displayed.
"""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class StageSwapActorLivenessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()
        cls.character = (ROOT / "source/Character.hx").read_text()
        cls.run_sh = (ROOT / "run.sh").read_text()

    def test_role_resolution_never_honors_a_destroyed_override(self):
        source = self.play_state
        # The override is only trusted while it is being installed into an
        # empty slot, still equals the live slot actor, or is the bound
        # game-over actor; every other case resolves the role's live instance.
        self.assertIn("slotActor == null || actorOverride == slotActor", source)
        self.assertIn("actorOverride == hxcGameOverCharacter", source)
        self.assertIn("case 'boyfriend': boyfriend;", source)
        self.assertIn("case 'gf': gf;", source)
        self.assertIn("default: dad;", source)
        # The captured pointer must not short-circuit before the liveness
        # checks: the trust condition and the slot lookup share one guard.
        guard = source[source.index("function hxcCharacterForRole"):source.index("return switch (canonical)")]
        self.assertIn("slotActor", guard)
        self.assertIn("hxcCharacterRole(overrideRole) == canonical", guard)

    def test_destroyed_actor_note_calls_cannot_reach_native_animation(self):
        source = self.play_state
        # The seeds resolve their actor at call time through the guarded
        # resolver, not through a captured instance field.
        self.assertIn(
            "return EngineCompat.hxcPlayAnimation(actorForRole(), name, restart, ignoreOther, reversed));",
            source)
        self.assertIn("var actor = actorForRole();", source)

    def test_vslice_atlas_swap_rejects_unusable_collections(self):
        source = self.character
        self.assertIn("targetFrames.numFrames <= 0 || targetFrames.getByIndex(0) == null", source)
        self.assertIn("vslice-anim-asset", source)
        self.assertIn("vSliceBrokenAssetWarned", source)

    def test_stage_scopes_bind_the_donor_members_idiom(self):
        source = self.play_state
        # Donor Stage.contains() references the member array unqualified after
        # the translator strips `this.`; stage scopes need the live list bound
        # or the gated remove() cleanup never runs (backgrounds overlap).
        self.assertIn("if (isStageScriptScope(usehaxe))", source)
        self.assertIn('interp.variables.set("members", members);', source)

    def test_flixel_set_frame_null_guard_patch_is_wired(self):
        self.assertIn("dpui-null-frame-guard", self.run_sh)
        self.assertIn('grep -q "dpui-null-frame-guard"', self.run_sh)
        flx_sprite = ROOT / ".haxelib/flixel/6,1,2/flixel/FlxSprite.hx"
        if flx_sprite.exists():
            self.assertIn("dpui-null-frame-guard", flx_sprite.read_text())

    def test_smoke_harness_supports_song_rate_acceleration(self):
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        self.assertIn("'--smoke-song-rate'", harness)
        self.assertIn("applySongRate", harness)
        self.assertIn("FlxG.sound.music.pitch = rate;", harness)


if __name__ == "__main__":
    unittest.main()
