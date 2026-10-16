"""A V-Slice atlas sprite plays frame labels and symbols by name, like the base game's FunkinSprite."""
import unittest

from haxe_test_support import FixturePath as Path
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]


def source(name):
    return (ROOT / "source" / name).read_text(encoding="utf-8")


class VSliceAtlasSpriteLabelsTest(unittest.TestCase):
    def test_controller_adds_a_missing_label_before_a_symbol_and_never_loops_it(self):
        controller = source("FunkinAtlasAnimationController.hx")
        add = extract_method(controller, "public function hasOrAddAnimation(")
        # Existing animations are left alone; labels win over symbols, both once-only at the document rate.
        self.assertLess(add.index("exists(name)"), add.index("addByFrameLabel(name, name, rate, false)"))
        self.assertLess(add.index("addByFrameLabel(name, name, rate, false)"), add.index("addBySymbol(name, name, rate, false)"))
        self.assertIn("_animate.library.frameRate", add)
        self.assertIn("labelInCollection(name)", add)
        play = extract_method(controller, "override public function play(")
        self.assertIn("if (!hasOrAddAnimation(animName))", play)
        self.assertLess(play.index("return;"), play.index("super.play("))
        # The base game's controller is the donor for this behaviour.
        donor = ROOT.parent / "fnf_sources/Funkin/source/funkin/graphics/FunkinAnimationController.hx"
        if donor.is_file():
            text = donor.read_text(encoding="utf-8")
            self.assertIn("hasAnimation(animName)", text)

    def test_loadtextureatlas_builds_the_sprite_with_that_controller(self):
        sprite = source("FunkinAtlasSprite.hx")
        self.assertIn("class FunkinAtlasSprite extends FlxAnimate", sprite)
        self.assertIn("anim = new FunkinAtlasAnimationController(this);", sprite)
        runtime = source("HxcCompatRuntime.hx")
        factory = extract_method(runtime, "public static function createFunkinSpriteTextureAtlas(")
        self.assertLess(factory.index("hxcNativeInstance('FunkinAtlasSprite'"), factory.index("hxcNativeInstance('animate.FlxAnimate'"))
        # Created by name, so the class has to be compiled into the game.
        self.assertIn("FunkinAtlasSprite;", source("Main.hx"))


if __name__ == "__main__":
    unittest.main()
