"""Regression coverage for campaign week images that have no Sparrow XML."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError("unterminated method: " + marker)


class MenuItemPngFallbackTest(unittest.TestCase):
    def test_png_only_week_creates_sprite_before_loading_graphic(self):
        source = (ROOT / "source/MenuItem.hx").read_text()
        constructor = source[source.index("public function new"):]
        xml_branch = constructor.index('if (rawXml != "")')
        fallback_branch = constructor.index("} else {", xml_branch)
        fallback_end = constructor.index("week.updateHitbox();", fallback_branch)
        self.assertIn("week = createWeekSpriteFromGraphic(rawPic);",
                      constructor[fallback_branch:fallback_end])

        helper = extract_method(source, "static function createWeekSpriteFromGraphic")
        main = f'''class BitmapData {{ public function new() {{}} }}
class FlxSprite {{
  public var loaded:Bool = false;
  public function new() {{}}
  public function loadGraphic(rawPic:Dynamic):FlxSprite {{
    loaded = rawPic != null;
    return this;
  }}
}}
class Main {{
  {helper}
  static function main() {{
    var sprite = createWeekSpriteFromGraphic(new BitmapData());
    if (sprite == null || !sprite.loaded)
      throw "PNG-only week fallback did not construct and populate its sprite";
  }}
}}'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(temp), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
