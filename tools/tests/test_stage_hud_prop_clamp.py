"""Coverage for imported stage prop layering vs the native HUD.

Kade/v-slice source mods letterbox camHUD with authored-z cinema bars and
other props.  The engine follows the mod's z-order among the props and layers
the native gameplay HUD above the imported prop layer (as v-slice draws its UI
over stage props), so the bars stay visible while the strumlines, health bar
and score text draw on top.
"""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class StageHudLayerTest(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "source/PlayState.hx").read_text()

    def test_imported_props_keep_authored_z_and_hud_layers_above(self):
        self.assertIn("function layerNativeStageHudOverProps():Void", self.source)
        # props keep their authored z: the rule reads it and never writes it
        self.assertIn("var z:Float = HxcCompatRuntime.getZIndex(sprite);", self.source)
        self.assertNotIn("setZIndex(sprite,", self.source.split(
            "function layerNativeStageHudOverProps")[1].split("nativeStageHudMembers")[0])
        # only camHUD-attached props participate; camGame props (crowds, fades)
        # are untouched
        self.assertIn('sprite.cameras.indexOf(camHUD) == -1', self.source)
        # The note and receptor ordering is exercised with an interpreted
        # state fixture in test_stage_hud_note_order.py.

    def test_native_hud_members_cover_the_full_hud(self):
        for member in ("songPosBG", "playerStrums", "enemyStrums", "healthBarBG",
                       "healthBar", "iconP1", "iconP2", "scoreTxt"):
            self.assertIn(member, self.source.split("function nativeStageHudMembers")[1]
                          .split("]")[0])

    def test_layer_rule_runs_after_the_stage_script(self):
        self.assertIn("layerNativeStageHudOverProps();", self.source)


if __name__ == "__main__":
    unittest.main()
