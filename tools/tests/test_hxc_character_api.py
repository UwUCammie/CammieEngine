"""Source-level coverage for the shared HXC character/stage API aliases."""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HxcCharacterApiTest(unittest.TestCase):
    def test_character_exposes_donor_animation_methods(self):
        source = (ROOT / "source/Character.hx").read_text()
        for method in (
            "getCurrentAnimation", "setAnimationOffsets", "hasAnimation",
            "isSinging", "isAnimationFinished", "playAnimation", "playSingAnimation", "getDataFlipX",
        ):
            self.assertIn("public function " + method + "(", source)
        self.assertIn("Character.animationName(this)", source)
        self.assertIn("addOffset(name, x, y)", source)

    def test_stage_and_playstate_expose_shared_role_access(self):
        stage = (ROOT / "source/StageHelper.hx").read_text()
        playstate = (ROOT / "source/PlayState.hx").read_text()
        engine = (ROOT / "source/EngineCompat.hx").read_text()
        for method in ("getDad", "getBoyfriend", "getGirlfriend", "getOpponent", "getNamedProp"):
            self.assertIn("public function " + method + "(", stage)
            self.assertIn("public function " + method + "(", playstate)
        self.assertIn("public var currentStage(get, never):StageHelper;", playstate)
        self.assertIn("seedHxcCharacterCompat(interp, path + filename);", playstate)
        for alias in (
            "getDad", "getBoyfriend", "getGirlfriend", "getOpponent", "getNamedProp",
            "getCurrentAnimation", "setAnimationOffsets", "playSingAnimation", "isAnimationFinished",
        ):
            self.assertIn("variables.set('" + alias + "'", playstate)
        self.assertIn("'playSingAnimation'", engine)
        self.assertIn("'isAnimationFinished'", engine)


if __name__ == "__main__":
    unittest.main()
