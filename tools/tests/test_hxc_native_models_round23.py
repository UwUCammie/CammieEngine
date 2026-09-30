"""Focused source/Haxe coverage for the reusable Round 23 native HXC models."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_class(source: str, marker: str) -> str:
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
    raise AssertionError(f"unterminated class: {marker}")


class HxcNativeModelsRound23Test(unittest.TestCase):
    def test_strumline_aliases_and_splash_gate_are_native(self):
        strumline = (ROOT / "source/Strumline.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("strumlineNotes(get, never)", strumline)
        self.assertIn("strumlineScale(get, never)", strumline)
        self.assertIn("public var showNotesplash:Bool = true", strumline)
        self.assertIn("public function fadeInArrows", strumline)
        self.assertIn("public function setNoteSpacing", strumline)
        self.assertIn("strums.showNotesplash", play_state)

    def test_character_and_stage_models_keep_slot_and_other_roles_distinct(self):
        character = (ROOT / "source/Character.hx").read_text()
        stage = (ROOT / "source/StageHelper.hx").read_text()
        runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        compat = (ROOT / "source/HxcCompat.hx").read_text()
        self.assertIn("public var characterType:Dynamic", character)
        self.assertIn("public var ignoreExclusionPref:Dynamic", character)
        self.assertIn("public function getCharacterPosition", stage)
        self.assertIn("public function getDadPosition", stage)
        self.assertIn("public function addCharacter(character:Character", stage)
        self.assertIn("__hxc_character_", stage)
        self.assertIn("Reflect.field(stage, 'addCharacter')", runtime)
        self.assertIn("{source: 'OTHER', value: 'other'}", compat)

    def test_chart_metadata_is_opaque_and_difficulty_view_is_data_backed(self):
        song = (ROOT / "source/Song.hx").read_text()
        self.assertIn("@:optional var offsets:SongVocalOffsets", song)
        self.assertIn("@:optional var stickerPack:String", song)
        self.assertIn("attachCompatChartAccessors(parsedJson", song)
        self.assertIn("class SongVocalOffsets", song)
        self.assertIn("return Song.loadFromJson(input, folder)", song)
        compat = (ROOT / "source/HxcCompat.hx").read_text()
        self.assertIn("'offsets', 'stickerPack'", compat)

    def test_playstate_active_animation_reads_are_guarded(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        for old in (
            "singer.animation.curAnim.name.startsWith(singAnim)",
            "boyfriend.animation.curAnim.name.startsWith(singAnim)",
            "actingOn.animation.curAnim.name.startsWith('sing')",
            "onActing.animation.curAnim.name.startsWith('sing')",
            "spr.animation.curAnim.name != 'confirm'",
            "realActor.animation.curAnim.name.startsWith(singAnim)",
            "gf.animation.curAnim.name.startsWith(\"sing\")",
        ):
            self.assertNotIn(old, source)
        self.assertIn("Character.animationName(singer)", source)
        self.assertIn("Character.animationName(boyfriend)", source)
        self.assertIn("Character.animationName(realActor)", source)
        self.assertIn("var strumAnimationName = spr.animation != null", source)

    def test_vocal_offsets_fixture_executes_without_native_chart_graph(self):
        source = (ROOT / "source/Song.hx").read_text()
        offsets_class = extract_class(source, "class SongVocalOffsets")
        fixture = f'''{offsets_class}
class Test {{
\tstatic function main() {{
\t\tvar raw:Dynamic = {{bf: {{inst: 12.5}}}};
\t\tReflect.setField(raw, "default", 3);
\t\tvar offsets = new SongVocalOffsets(raw);
\t\tif (offsets.getVocalOffset("bf", "inst") != 12.5) throw "nested vocal offset";
\t\tif (offsets.getVocalOffset("unknown", "unknown") != 3) throw "default vocal offset";
\t\tif (new SongVocalOffsets().getVocalOffset("bf", "inst") != 0) throw "zero fallback";
\t}}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Test.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--main", "Test", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
