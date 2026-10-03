"""Beat animation handling tolerates imported characters with no active animation."""
from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PlayStateBeatAnimationTest(unittest.TestCase):
    def test_beat_uses_safe_character_animation_names(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\toverride function beatHit()')
        beat = source[start:source.index('\n\tfunction updatePresence()', start)]
        self.assertIn('var dadAnim = Character.animationName(dad);', beat)
        self.assertIn('var boyfriendAnim = Character.animationName(boyfriend);', beat)
        self.assertNotIn('dad.animation.curAnim.name', beat)
        self.assertNotIn('boyfriend.animation.curAnim.name', beat)


if __name__ == '__main__':
    unittest.main()
