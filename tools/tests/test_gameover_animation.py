"""Game-over update tolerates a missing current animation."""
from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class GameOverAnimationTest(unittest.TestCase):
    def test_update_guards_current_animation_and_falls_back_once(self):
        source = (ROOT / 'source/GameOverSubstate.hx').read_text()
        start = source.index('\toverride function update(elapsed:Float)')
        update = source[start:source.index('\n\tfunction playGameoverMusic(', start)]
        self.assertIn('var currentAnim = bf.animation != null ? bf.animation.curAnim : null;', update)
        self.assertIn('if (currentAnim == null)', update)
        self.assertIn('startGameoverLoop();', update)
        self.assertNotIn('bf.animation.curAnim.name', update)
        self.assertNotIn('bf.animation.curAnim.curFrame', update)
        self.assertNotIn('bf.animation.curAnim.finished', update)

    def test_gameover_loop_is_idempotent(self):
        source = (ROOT / 'source/GameOverSubstate.hx').read_text()
        start = source.index('\tfunction startGameoverLoop()')
        helper = source[start:source.index('\n\t}', start) + 3]
        self.assertIn('if (gameoverStarted) return;', helper)
        self.assertIn('gameoverStarted = true;', helper)
        self.assertIn('FlxG.camera.follow(camFollow, LOCKON, 0.01);', helper)
        self.assertIn('playGameoverMusic();', helper)


if __name__ == '__main__':
    unittest.main()
