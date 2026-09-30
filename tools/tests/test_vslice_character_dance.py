"""Generated V-Slice character dance ticks mirror the donor Bopper.dance rule.

The donor engine alternates the authored danceLeft/danceRight pair on every
dance tick (hasDanced flip-flop, force-restarted like the donor's beat bop), so
a donor idle authored as the pair plays both halves in order and holds a
finished half until the next tick.  Replaying one fixed animation instead
looped a single half mid-swing, which read as too fast / cut off.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def haxe_string(value: str) -> str:
    return json.dumps(str(value))


class VSliceCharacterDanceTest(unittest.TestCase):
    def convert(self, character: dict, missing_secondary: bool = False) -> str:
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/pairhero.png").write_bytes(b"png")
            (fixture / "images/characters/pairhero.xml").write_text("<TextureAtlas/>")
            (fixture / "images/icons/icon-pairhero.png").write_bytes(b"icon")
            character_path = fixture / "character.json"
            character_path.write_text(json.dumps(character))
            output_path = fixture / "out.txt"
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var converted = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(str(character_path))})), {haxe_string(str(fixture))});
    sys.io.File.saveContent({haxe_string(str(output_path))}, converted.hscript);
  }}
}}
'''
            with tempfile.TemporaryDirectory() as build:
                Path(build, "Main.hx").write_text(main)
                result = subprocess.run(
                    [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                     "-cp", build, "-main", "Main", "--interp"],
                    cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return output_path.read_text()

    def run_interpreted(self, generated_tail: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "Generated.hscript").write_text(generated_tail)
            Path(folder, "Main.hx").write_text(f'''class MockChar {{
  public function new() {{}}
  public var calls:Array<Dynamic> = [];
  public function playAnim(name:String, ?force:Null<Bool>) {{
    calls.push({{name: name, force: force == true}});
  }}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var parser = new hscript.Parser();
    var program = parser.parseString(sys.io.File.getContent({haxe_string(str(Path(folder, 'Generated.hscript')))}));
    var interp = new hscript.Interp();
    var mock = new MockChar();
    interp.variables.set("char", mock);
    interp.execute(program);
    var dance = interp.variables.get("dance");
    if (dance == null) fail("generated dance missing");
    dance(mock);
    dance(mock);
    dance(mock);
    dance(mock);
    if (mock.calls.length != 4) fail("expected 4 dance ticks, got " + mock.calls.length);
    var expected = ["danceLeft", "danceRight", "danceLeft", "danceRight"];
    for (index in 0...4) {{
      if (mock.calls[index].name != expected[index])
        fail("tick " + index + " played " + mock.calls[index].name);
      if (mock.calls[index].force != true)
        fail("tick " + index + " did not force-restart like the donor beat bop");
    }}
    trace("dance ticks OK");
  }}
}}
''')
            return subprocess.run(
                [str(HAXE), "-cp", str(HSCRIPT), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_dance_pair_alternates_halves_like_donor(self):
        generated = self.convert({
            "version": "1.0.0",
            "name": "Pair Hero",
            "assetPath": "characters/pairhero",
            "startingAnimation": "danceRight",
            "healthIcon": {"id": "pairhero"},
            "animations": [
                {"name": "danceLeft", "prefix": "Pair Idle", "frameIndices": [30, 0, 1, 2]},
                {"name": "danceRight", "prefix": "Pair Idle", "frameIndices": [3, 4, 5]},
            ],
        })
        # The flip state must survive across dance ticks, so it lives at the
        # top level of the generated script, before init().
        self.assertIn("vSliceHasDanced = false;", generated)
        self.assertLess(generated.index("vSliceHasDanced = false;"),
                        generated.index("function init(char)"))
        self.assertIn('char.playAnim("danceRight", true);', generated)
        self.assertIn('char.playAnim("danceLeft", true);', generated)
        # Both halves must stop on their final frame until the next beat.
        # V-Slice AnimationData defaults looped to false, regardless of name.
        self.assertIn('"Pair Idle", [30, 0, 1, 2], "", 24, false)', generated)
        self.assertIn('"Pair Idle", [3, 4, 5], "", 24, false)', generated)

        result = self.run_interpreted(generated)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("dance ticks OK", result.stdout)

    def test_character_without_the_pair_keeps_fixed_dance_tick(self):
        generated = self.convert({
            "version": "1.0.0",
            "name": "Solo Hero",
            "assetPath": "characters/pairhero",
            "healthIcon": {"id": "pairhero"},
            "animations": [
                {"name": "idle", "prefix": "Pair Idle", "frameIndices": [0, 1, 2]},
                {"name": "singLEFT", "prefix": "Pair Left", "frameIndices": []},
            ],
        })
        self.assertNotIn("vSliceHasDanced", generated)
        self.assertIn('function dance(char) {\n    char.playAnim("idle");\n}', generated)

    def test_explicit_animation_loop_modes_survive_conversion(self):
        generated = self.convert({
            "version": "1.0.0", "name": "Loop Hero",
            "assetPath": "characters/pairhero",
            "healthIcon": {"id": "pairhero"},
            "animations": [
                {"name": "idle", "prefix": "Idle", "looped": True},
                {"name": "danceLeft", "prefix": "Left", "looped": False},
                {"name": "danceRight", "prefix": "Right", "loop": True},
                {"name": "special", "prefix": "Special"},
            ],
        })
        self.assertIn('addByPrefix("idle", "Idle", 24, true)', generated)
        self.assertIn('addByPrefix("danceLeft", "Left", 24, false)', generated)
        self.assertIn('addByPrefix("danceRight", "Right", 24, true)', generated)
        self.assertIn('addByPrefix("special", "Special", 24, false)', generated)

    def test_unavailable_pair_half_does_not_alternate(self):
        generated = self.convert({
            "version": "1.0.0",
            "name": "Broken Pair Hero",
            "assetPath": "characters/pairhero",
            "healthIcon": {"id": "pairhero"},
            "animations": [
                {"name": "danceLeft", "prefix": "Pair Idle", "frameIndices": [30, 0, 1]},
                {"name": "danceRight", "prefix": "Pair Missing", "frameIndices": [3, 4],
                 "assetPath": "characters/does-not-exist"},
            ],
        })
        self.assertNotIn("vSliceHasDanced", generated)
        self.assertNotIn('char.playAnim("danceLeft", true);', generated)


if __name__ == "__main__":
    unittest.main()
