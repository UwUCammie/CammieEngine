"""Psych numeric atlas animations must not dereference unnamed frames."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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


class PsychAnimationIndicesTest(unittest.TestCase):
    def test_native_adapter_resolves_only_named_frames(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        method = extract_method(source, "public static function compatAnimationFrameIndices")
        names_method = extract_method(source, "public static function compatAnimationNameIndices")
        normalize_method = extract_method(source, "public static function compatNormalizeAnimationIndices")
        fixture = f"""
class PsychAnimationIndicesFixture {{
{method}
{names_method}
{normalize_method}
    static function fail(message:String):Void throw message;
    static function main() {{
        var frames:Array<Dynamic> = [
            {{name: 'Universe Idle0000'}},
            {{name: null}},
            null,
            {{name: 'Universe Idle0002'}},
            {{name: 'Other0001'}},
            {{name: 'Universe Idle0005'}}
        ];
        var resolved = compatAnimationFrameIndices(frames, 'Universe Idle', [0, 2, 5, 9]);
        if (resolved.length != 3 || resolved[0] != 0 || resolved[1] != 3 || resolved[2] != 5)
            fail('named atlas lookup: ' + resolved);
        var indexOnly:Array<Dynamic> = [{{name: '0'}}, {{name: null}}, {{name: '2'}}];
        var bare = compatAnimationFrameIndices(indexOnly, '', [0, 2]);
        if (bare.length != 2 || bare[0] != 0 || bare[1] != 2)
            fail('index-only atlas lookup: ' + bare);
        var unnamed:Array<Dynamic> = [{{name: null}}, null, {{name: null}}, {{name: null}}];
        var positional = compatAnimationFrameIndices(unnamed, 'Universe Idle', [0, 2, 9]);
        if (positional.length != 2 || positional[0] != 0 || positional[1] != 2)
            fail('unnamed atlas positional lookup: ' + positional);
        var authored = compatAnimationNameIndices([
            'Universe Idle0000', 'Universe Idle0001', 'Universe Idle0002',
            'Other0000'
        ], 'Universe Idle', [0, 2, 9]);
        if (authored.length != 2 || authored[0] != 0 || authored[1] != 2)
            fail('authored XML lookup: ' + authored);
        if (compatAnimationFrameIndices(frames, 'Missing', [0]).length != 0)
            fail('missing prefix was accepted');
        var csv = compatNormalizeAnimationIndices('0, 2,5');
        if (csv.length != 3 || csv[0] != 0 || csv[1] != 2 || csv[2] != 5)
            fail('Psych CSV indices were not normalized: ' + csv);
        var bracketed = compatNormalizeAnimationIndices('[1, 3]');
        if (bracketed.length != 2 || bracketed[0] != 1 || bracketed[1] != 3)
            fail('bracketed indices were not normalized: ' + bracketed);
        Sys.println('ok');
    }}
}}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "PsychAnimationIndicesFixture.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "PsychAnimationIndicesFixture"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_adapter_avoids_flixel_add_by_indices(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = source.index("\tfunction compatAddAnimationByIndices")
        end = source.index("\n\t}", start) + 3
        method = source[start:end]
        self.assertIn("compatAnimationFrameIndices", method)
        self.assertIn("compatAnimationNameIndices", method)
        self.assertIn("compatNormalizeAnimationIndices", method)
        self.assertIn("object.animation.add(animation, frameIndices, fps, looped)", method)
        self.assertNotIn("object.animation.addByIndices", method)
        self.assertIn("object.frames", method)
        self.assertIn("frameCollection.frames", method)
        self.assertIn("frameNameValue == null", source)

    def test_lua_creation_to_alias_lookup_keeps_atlas_metadata_on_object(self):
        """Mirror makeAnimatedLuaSprite -> dynamic lookup -> addByIndices.

        The translated callback normally passes the original tag, but imported
        scripts can reach the same sprite through a property alias.  The
        production adapter therefore keeps XML names on the live object as
        well as on the string tag; this fixture exercises that call sequence
        without constructing a full PlayState/Flixel window.
        """
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        names_method = extract_method(source, "public static function compatAnimationNameIndices")
        normalize_method = extract_method(source, "public static function compatNormalizeAnimationIndices")
        self.assertIn("haxeSpriteAtlasNamesByObject:Map<FlxSprite, Array<String>>", source)
        self.assertIn("haxeSpriteAtlasNamesByObject.set(sprite, names)", source)
        self.assertIn("compatSpriteAtlasNames(name, object)", source)
        fixture = f"""
class FakeSprite {{ public function new() {{}} }}
class PsychAnimationCallSequenceFixture {{
{names_method}
{normalize_method}
    static function fail(message:String):Void throw message;
    static function main() {{
        var byTag:Map<String, Array<String>> = [];
        var byObject:Map<FakeSprite, Array<String>> = [];
        var aliases:Map<String, Dynamic> = [];
        var sprite = new FakeSprite();
        var names:Array<String> = [
            'Universe Idle0000', 'Universe Idle0001', 'Universe Idle0002',
            'Universe Idle0003', 'Universe Idle0004', 'Universe Idle0005'
        ];
        // makeAnimatedLuaSprite stores both the authored tag and live object.
        byTag.set('Universe', names);
        byObject.set(sprite, names);
        // A later dynamic/property route resolves the same object under a
        // different name; the tag-only lookup intentionally misses here.
        aliases.set('UniverseAlias', sprite);
        var object = aliases.get('UniverseAlias');
        var authored:Array<String> = byTag.get('UniverseAlias');
        if (authored == null)
            authored = byObject.get(object);
        var requested = compatNormalizeAnimationIndices('0,2,5');
        var resolved = compatAnimationNameIndices(authored, 'Universe Idle', requested);
        if (resolved.length != 3 || resolved[0] != 0 || resolved[1] != 2 || resolved[2] != 5)
            fail('object metadata was not propagated: ' + resolved);
        Sys.println('ok');
    }}
}}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "PsychAnimationCallSequenceFixture.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "PsychAnimationCallSequenceFixture"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_positional_fallback_is_limited_to_unnamed_atlases(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        method = extract_method(source, "public static function compatAnimationFrameIndices")
        names_method = extract_method(source, "public static function compatAnimationNameIndices")
        self.assertIn("!hasNamedFrame", method)
        self.assertIn("wanted >= 0 && wanted < frames.length", method)
        self.assertIn("frame.name", method)
        self.assertIn("Reflect.field(frame, 'name')", method)
        self.assertIn("StringTools.startsWith(frameName, cleanPrefix)", names_method)
        self.assertIn("StringTools.endsWith(frameName, cleanPostfix)", names_method)


if __name__ == "__main__":
    unittest.main()
