"""The smoke harness can dump the scene at exact song positions, not only once per second."""
import unittest

from haxe_test_support import FixturePath as Path
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]
HARNESS = (ROOT / "source/RuntimeSmokeHarness.hx").read_text(encoding="utf-8")


class SceneSampleTest(unittest.TestCase):
    def test_targets_come_from_the_environment_and_each_fires_once_in_order(self):
        sample = extract_method(HARNESS, "static function sampleSceneAtCues(")
        self.assertIn("Sys.getEnv('CAMMIE_SMOKE_SCENE_AT_MS')", sample)
        self.assertIn("sceneSampleTargets.sort(", sample)
        # One dump per target: the index moves before the dump and the dump waits for the song to reach it.
        self.assertLess(sample.index("sceneSampleIndex++;"), sample.index("emit('scene_visual_sample', scene);"))
        self.assertIn("Conductor.songPosition < sceneSampleTargets[sceneSampleIndex]", sample)
        self.assertIn("!songStartObserved", sample)

    def test_it_runs_every_frame_before_drawing_and_stays_off_without_the_variable(self):
        pre_draw = extract_method(HARNESS, "static function onFramePreDraw(")
        self.assertIn("sampleSceneAtCues();", pre_draw)
        # With no variable the target list is empty and the call returns before touching the scene.
        sample = extract_method(HARNESS, "static function sampleSceneAtCues(")
        self.assertLess(sample.index("sceneSampleIndex >= sceneSampleTargets.length"), sample.index("RuntimeSmokeVisuals.stage("))


if __name__ == "__main__":
    unittest.main()
