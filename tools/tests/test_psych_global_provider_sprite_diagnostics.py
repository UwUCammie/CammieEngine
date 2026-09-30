"""Keep native smoke diagnostics around global Psych sprite setup bounded."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychGlobalProviderSpriteDiagnosticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def test_lifecycle_markers_are_smoke_only_and_track_one_object(self):
        helper = extract_method(
            self.source, "function markPsychGlobalProviderSpritePhase"
        )
        self.assertIn("!RuntimeSmokeHarness.enabled()", helper)
        self.assertIn("sprite == null", helper)
        self.assertIn("sprite != psychGlobalProviderFirstSprite", helper)

        constructor = extract_method(
            self.source, "function compatMakeLuaSpriteForOwner"
        )
        self.assertIn("psychGlobalProviderFirstSpriteTag = tag", constructor)
        self.assertIn("sprite-constructor-begin", constructor)
        self.assertIn("markPsychGlobalProviderSpritePhase(sprite, 'constructor-complete')", constructor)
        self.assertIn("markPsychGlobalProviderSpritePhase(sprite, 'registry-complete')", constructor)
        self.assertLess(
            constructor.index("sprite-constructor-begin"),
            constructor.index("var sprite = new FlxSprite(x, y)"),
        )

        cleanup = extract_method(self.source, "function clearEngineCompatObjects")
        self.assertIn("psychGlobalProviderFirstSprite = null", cleanup)
        self.assertIn("psychGlobalProviderFirstSpriteTag = null", cleanup)

    def test_graphic_camera_property_and_add_boundaries_are_marked(self):
        make_graphic = extract_method(self.source, "function compatMakeGraphic")
        begin = make_graphic.index("'makeGraphic-begin'")
        call = make_graphic.index("'makeGraphic-call'")
        native_call = make_graphic.index(".makeGraphic(width, height, parsedColor)")
        complete = make_graphic.index("'makeGraphic-complete'")
        self.assertLess(begin, call)
        self.assertLess(call, native_call)
        self.assertLess(native_call, complete)

        camera = extract_method(self.source, "function compatSetObjectCamera")
        self.assertIn("'camera-begin'", camera)
        self.assertIn("'camera-complete'", camera)
        self.assertIn("'camera-error'", camera)

        property_write = extract_method(self.source, "function compatSetProperty")
        self.assertIn("'property-begin'", property_write)
        self.assertIn("'property-complete'", property_write)
        self.assertIn("field=' + (suffix == '' ? root : suffix)", property_write)

        add_sprite = extract_method(self.source, "function compatAddLuaSprite")
        self.assertLess(
            add_sprite.index("'add-begin'"),
            add_sprite.index("addHscriptSprite(sprite"),
        )
        self.assertLess(
            add_sprite.index("addHscriptSprite(sprite"),
            add_sprite.index("'add-complete'"),
        )


if __name__ == "__main__":
    unittest.main()
