"""Regression coverage for donor Modding Plus visual effects.

Cycles Wrath stores crossfade on section metadata (rather than on a note
type), while several imported scripts use the same effect classes that the
donor exposed to HScript.  These checks keep the compatibility contract
engine-wide so a future chart importer change cannot silently discard it.
"""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CrossfadeCompatibilityTest(unittest.TestCase):
    def test_cycles_wrath_section_flags_are_consumed_by_engine(self):
        fixture = ROOT / "assets/data/cycles-wrath/cycles-wrath-hard.json"
        if not fixture.is_file():
            self.skipTest(f"mounted Cycles Wrath chart fixture unavailable: {fixture}")
        chart = json.loads(
            fixture.read_text(
                encoding="utf-8"
            )
        )["song"]
        sections = chart["notes"]
        self.assertTrue(any(section.get("crossfadeDad") is True for section in sections))
        self.assertTrue(any(section.get("crossfadeBf") is True for section in sections))

        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        for field in ("crossfadeBf", "crossfadeDad", "crossFade"):
            self.assertIn(field, source)
        self.assertIn("sectionHasCrossFade(section, gottaHitNote)", source)
        self.assertIn("spawnCrossFade(realActor, note)", source)
        self.assertIn("spawnCrossFade(singer, daNote)", source)

    def test_crossfade_uses_character_tint_and_is_recycled(self):
        sprite = (ROOT / "source/CrossFade.hx").read_text(encoding="utf-8")
        character = (ROOT / "source/Character.hx").read_text(encoding="utf-8")
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("character.crossFadeColor", sprite)
        self.assertIn("loadGraphicFromSprite(character)", sprite)
        self.assertIn("group.recycle(CrossFade)", play_state)
        self.assertIn("public var crossFadeColor", character)

    def test_springless_effect_classes_are_available_before_camera_fade(self):
        fixture = ROOT / "assets/data/cycles-encore-springless/modchart.hscript"
        if not fixture.is_file():
            self.skipTest(f"mounted springless Cycles modchart fixture unavailable: {fixture}")
        modchart = fixture.read_text(encoding="utf-8")
        plugin = (ROOT / "source/PluginManager.hx").read_text(encoding="utf-8")
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("new FlxGlitchEffect", modchart)
        self.assertIn("new FlxEffectSprite", modchart)
        self.assertIn('interp.variables.set("FlxGlitchEffect", FlxGlitchEffect)', plugin)
        self.assertIn('interp.variables.set("FlxEffectSprite", FlxEffectSprite)', plugin)
        self.assertIn("var startSucceeded = callHscript(\"start\"", play_state)
        self.assertIn("if (!startSucceeded)", play_state)
        self.assertIn("camGame.alpha = startGameAlpha", play_state)


if __name__ == "__main__":
    unittest.main()
