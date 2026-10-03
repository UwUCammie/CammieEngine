"""Psych Lua sprites play their first registered animation immediately."""
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


class PsychFirstAnimationTest(unittest.TestCase):
    def test_first_animation_replaces_unrelated_atlas_frame_and_preserves_playback(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        method = extract_method(source, "public static function compatStartFirstAnimation")
        fixture = f"""
class FakeAnimation {{
    public var curAnim:String = null;
    public var frameName:String = 'BF Dead Loop0000';
    public var played:Int = 0;
    var names:Map<String, String> = [];
    public function new() {{}}
    public function addByPrefix(name:String, prefix:String):Void names.set(name, prefix);
    public function exists(name:String):Bool return names.exists(name);
    public function play(name:String, force:Bool):Void {{
        if (!exists(name)) throw 'missing animation';
        curAnim = name;
        frameName = names.get(name);
        played++;
    }}
}}
class Character {{
    public var animation = new FakeAnimation();
    public var characterPlays:Int = 0;
    public function new() {{}}
    public function playAnim(name:String, force:Bool):Void {{
        characterPlays++;
        animation.play(name, force);
    }}
}}
class PsychFirstAnimationFixture {{
{method}
    static function main() {{
        var sprite = {{animation: new FakeAnimation()}};
        sprite.animation.addByPrefix('stuff', 'BF idle dance0007');
        compatStartFirstAnimation(sprite, 'stuff');
        if (sprite.animation.frameName != 'BF idle dance0007' || sprite.animation.played != 1)
            throw 'first animation stayed on death atlas frame';
        sprite.animation.addByPrefix('later', 'BF NOTE LEFT0000');
        compatStartFirstAnimation(sprite, 'later');
        if (sprite.animation.curAnim != 'stuff' || sprite.animation.played != 1)
            throw 'new registration interrupted active animation';
        var missing = {{animation: new FakeAnimation()}};
        compatStartFirstAnimation(missing, 'absent');
        if (missing.animation.played != 0)
            throw 'missing animation was played';
        var character = new Character();
        character.animation.addByPrefix('idle', 'BF idle dance0000');
        compatStartFirstAnimation(character, 'idle');
        if (character.characterPlays != 1)
            throw 'character playback skipped playAnim';
        Sys.println('ok');
    }}
}}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "PsychFirstAnimationFixture.hx"
            path.write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "PsychFirstAnimationFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_both_psych_lua_registration_paths_use_first_animation_playback(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        for marker in ("function compatAddAnimationByPrefix", "function compatAddAnimationByIndices"):
            method = extract_method(source, marker)
            self.assertIn("compatStartFirstAnimation(object, animation)", method)


if __name__ == "__main__":
    unittest.main()
