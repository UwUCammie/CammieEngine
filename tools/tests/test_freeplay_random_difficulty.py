"""Tests for difficulty fallback when Freeplay's random entry chooses a song."""

from pathlib import Path
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


class FreeplayRandomDifficultyTest(unittest.TestCase):
    @unittest.skipUnless(HAXE.is_file(), "portable Haxe interpreter is unavailable")
    def test_valid_difficulty_resolution_uses_selected_songs_supported_charts(self):
        method = extract_method(
            (ROOT / "source/DifficultyManager.hx").read_text(),
            "public static function getValidDiff(",
        )
        fixture = f'''class DifficultyManager {{
  static var diffJson:Dynamic = {{defaultDiff: 1}};
  public static var supported:Map<String, Array<Int>> = new Map();
  static function getSupportedDiffs(song:String):Array<Int> {{
    return supported.exists(song) ? supported.get(song) : [];
  }}
  static function changeDifficulty(diff:Int):Dynamic {{ return {{difficulty: diffJson.defaultDiff}}; }}
{method}
}}
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    DifficultyManager.supported.set("default-available", [0, 1]);
    DifficultyManager.supported.set("hardest-only", [3]);
    DifficultyManager.supported.set("selected-present", [1, 2, 3]);
    if (DifficultyManager.getValidDiff(3, "default-available") != 1)
      fail("unsupported random-song difficulty did not prefer the configured default");
    if (DifficultyManager.getValidDiff(0, "hardest-only") != 3)
      fail("song without the default difficulty did not select a supported fallback");
    if (DifficultyManager.getValidDiff(2, "selected-present") != 2)
      fail("valid selected difficulty was changed");
    if (DifficultyManager.getValidDiff(3, "missing-support") != 1)
      fail("empty chart support did not use the manager fallback");
    Sys.println("freeplay-random-difficulty-ok");
  }}
}}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("freeplay-random-difficulty-ok", result.stdout + result.stderr)

    def test_random_entry_has_no_song_named_difficulty_branches(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        start = source.index("var randomValue:Int = FlxG.random.int")
        end = source.index("daSelection = randomValue;", start)
        branch = source[start:end].lower()
        self.assertIn("difficultymanager.getvaliddiff(curdifficulty", branch)
        self.assertNotIn("expurgation", branch)
        self.assertNotIn("case 'test'", branch)


if __name__ == "__main__":
    unittest.main()
