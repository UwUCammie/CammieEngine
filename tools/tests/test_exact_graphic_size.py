"""Regression coverage for the imported-stage graphic-size compatibility API."""
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


class ExactGraphicSizeTest(unittest.TestCase):
    def test_helper_sets_render_scale_without_changing_hitbox(self):
        method = extract_method(
            (ROOT / "source/CoolUtil.hx").read_text(),
            "public static function exactSetGraphicSize",
        ).replace("FlxSprite", "FakeSprite")
        fixture = f"""
class FakeScale {{ public var x:Float = 1; public var y:Float = 1; public function new() {{}} public function set(x:Float, y:Float) {{ this.x = x; this.y = y; }} }}
class FakeSprite {{
    public var frameWidth:Float = 100;
    public var frameHeight:Float = 50;
    public var width:Float = 100;
    public var height:Float = 50;
    public var scale:FakeScale = new FakeScale();
    public function new() {{}}
}}
class CoolUtil {{
{method}
}}
class ExactGraphicSizeMain {{
    static function main() {{
        var sprite = new FakeSprite();
        CoolUtil.exactSetGraphicSize(sprite, 130, 65);
        if (sprite.scale.x != 1.3 || sprite.scale.y != 1.3) throw 'scale not applied';
        if (sprite.width != 100 || sprite.height != 50) throw 'helper changed hitbox dimensions';
    }}
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ExactGraphicSizeMain.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "ExactGraphicSizeMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
