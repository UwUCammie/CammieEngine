"""FPS Plus HXC character/stage converter coverage (data-only recovery).

The importer must translate compiled FPS Plus `data/characters/*.hxc`
CharacterInfo modules and `data/stages/*.hxc` BaseStage modules into native
custom_chars/custom_stages implementations without executing donor code.
These fixtures exercise the pure parsing/generation halves of that conversion
against a synthetic module and the mounted whitty donor.
"""

from __future__ import annotations
from haxe_test_support import HAXE_COMMAND

import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods/whitty")
HAXE = ROOT / ".tools/haxe/haxe"

SYNTHETIC_STAGE_HXC = """import flixel.FlxSprite;
import objects.BGSprite;

class alleyBalls extends BaseStage
{
    public function new(){
\t\tsuper();

        name = "alleyBalls";
\t\tstartingZoom = 0.8;
\t\tbfStart.x += 230;
\t\tbfStart.y += 0;
\t\tgfStart.x += 110;
\t\tgfStart.y += 0;
\t\tdadStart.x += 200;
\t\tdadStart.y += 0;

\t\tuseStartPoints = true;

\t\tvar bg:BGSprite = new BGSprite('alley/BallisticBackground', -200, -100, 1.0, 1.0, ['Background Whitty Moving'], true);
\t\tbg.antialiasing = true;
\t\taddToBackground(bg);

\t\tvar front:FlxSprite = new FlxSprite(-300, 670).loadGraphic(Paths.image("alley/whittyFront"));
\t\tfront.antialiasing = true;
\t\taddToBackground(front);
    }
}"""

SYNTHETIC_CHARACTER_HXC = """class WhitBonkers extends CharacterInfoBase
{
    public function new(){
        super();

        info.name = "whitbonkers";
        info.spritePath = "characters/WhittyCrazy";
        info.frameLoadType = setSparrow();
        info.focusOffset.set(0, -430);
        info.iconName = "angor";

        addByPrefix('idle', offset(181, 412), 'Whitty idle dance', 24, loop(true, -4));
        addByPrefix('singUP', offset(190, 513), 'Whitty Sing Note UP', 24, loop(true, -4));
        addExtraData("reposition", [150, 420]);
    }
}"""


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


def extract_typedef(source: str, name: str) -> str:
    start = source.index(f"typedef {name} =")
    depth = 0
    body_start = source.index("{", start)
    end = body_start
    for index in range(body_start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    return source[start:end]


def make_fixture(folder: Path) -> Path:
    """Compile the converter's pure halves beside a stub of HxcCompat's
    data-only CharacterInfo reader (the same methods the real class uses)."""
    module_source = (ROOT / "source/ModuleFunctions.hx").read_text()
    methods = "\n".join(
        extract_method(module_source, marker)
        for marker in (
            "static function fpsPlusCharacterDefinition",
            "static function fpsPlusQuote",
            "static function fpsPlusNumber",
            "static function generateFpsPlusCharacterHScript",
            "static function parseFpsPlusStage",
            "static function generateFpsPlusStageHScript",
            "static function readPngHorizontalFrames",
        )
    )
    typedefs = "\n".join(
        extract_typedef(module_source, name)
        for name in ("FpsPlusStageSprite", "FpsPlusStageSpec")
    )
    hxc_source = (ROOT / "source/HxcCompat.hx").read_text()
    hxc_methods = "\n".join(
        extract_method(hxc_source, marker)
        for marker in (
            "static function detectCharacterInfoDefinition",
            "static function collectCharacterPrefixAnimations",
            "static function collectCharacterIndexAnimations",
            "static function appendCharacterAnimation",
            "static function validNumeric",
            "static function literalNumberPair",
            "static function literalNumberArray",
            "static function literalIntArray",
            "static function firstString",
            "static function matchGroups",
        )
    )
    source = f"""import haxe.Json;
import sys.FileSystem;
import sys.io.File;
using StringTools;

{typedefs}

class HxcCompat {{
{hxc_methods}
  public static function analyze(source:String, ?path:String):Dynamic {{
    var definition = detectCharacterInfoDefinition(source == null ? '' : source);
    return definition == null ? null : {{kind:'character', characterDefinition:definition}};
  }}
}}

class ConverterFixture {{
{methods}
  static function field(value:Dynamic, name:String):Dynamic
    return value == null ? null : Reflect.field(value, name);

  static function main() {{
    var stageHxc = File.getContent(Sys.args()[0]);
    var characterHxc = File.getContent(Sys.args()[1]);
    var definition = fpsPlusCharacterDefinition(characterHxc, 'characters/WhitBonkers.hxc');
    var animations:Array<Dynamic> = definition == null ? [] : Reflect.field(definition, 'animations');
    var characterScript = definition == null ? '' : generateFpsPlusCharacterHScript('WhitBonkers', definition);
    var spec = parseFpsPlusStage(stageHxc);
    var stageScript = spec == null ? '' : generateFpsPlusStageHScript(spec);
    var spriteNames:Array<String> = [];
    var spriteImages:Array<String> = [];
    var spriteAnimations:Int = 0;
    if (spec != null) {{
      for (sprite in spec.sprites) {{
        spriteNames.push(sprite.variable);
        spriteImages.push(sprite.image);
        spriteAnimations += sprite.animations.length;
      }}
    }}
    var offsets:Array<String> = [];
    if (spec != null)
      for (offset in spec.offsets)
        offsets.push(offset.char + ':' + offset.x + ':' + offset.y);
    Sys.println(Json.stringify({{
      characterFound: definition != null,
      characterName: definition == null ? null : field(definition, 'name'),
      spritePath: definition == null ? null : field(definition, 'spritePath'),
      iconName: definition == null ? null : field(definition, 'iconName'),
      animationCount: animations.length,
      firstAnimation: animations.length == 0 ? null : animations[0],
      characterScript: characterScript,
      stageFound: spec != null,
      defaultZoom: spec == null ? null : spec.defaultZoom,
      useStartPoints: spec == null ? null : spec.useStartPoints,
      offsets: offsets,
      spriteNames: spriteNames,
      spriteImages: spriteImages,
      spriteAnimations: spriteAnimations,
      stageScript: stageScript
    }}));
  }}
}}
"""
    path = folder / "ConverterFixture.hx"
    path.write_text(source, newline='\n')
    return path


class FpsPlusCharacterStageConversionTest(unittest.TestCase):
    def run_fixture(self, stage_path: Path, character_path: Path) -> dict:
        with tempfile.TemporaryDirectory(prefix="fps-conv-", dir=ROOT / "tmp") as folder:
            folder_path = Path(folder)
            make_fixture(folder_path)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(folder_path), "--run", "ConverterFixture",
                 str(stage_path), str(character_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            lines = [line for line in result.stdout.splitlines()
                     if line.strip().startswith("{")]
            self.assertTrue(lines, result.stdout + result.stderr)
            return json.loads(lines[-1])

    def test_synthetic_stage_and_character_convert_with_authored_data(self):
        with tempfile.TemporaryDirectory(prefix="fps-conv-synthetic-", dir=ROOT / "tmp") as folder:
            root = Path(folder)
            stage_path = root / "alleyBalls.hxc"
            stage_path.write_text(SYNTHETIC_STAGE_HXC, newline='\n')
            character_path = root / "WhitBonkers.hxc"
            character_path.write_text(SYNTHETIC_CHARACTER_HXC, newline='\n')
            parsed = self.run_fixture(stage_path, character_path)

            self.assertTrue(parsed["characterFound"])
            self.assertEqual(parsed["characterName"], "whitbonkers")
            self.assertEqual(parsed["spritePath"], "characters/WhittyCrazy")
            self.assertEqual(parsed["iconName"], "angor")
            self.assertEqual(parsed["animationCount"], 2)
            self.assertEqual(parsed["firstAnimation"]["name"], "idle")
            self.assertEqual(parsed["firstAnimation"]["prefix"], "Whitty idle dance")
            # The generated native script carries the authored atlas, like-id,
            # animation prefixes and offsets so the registry entry is playable.
            script = parsed["characterScript"]
            self.assertIn("char.like = 'WhitBonkers';", script)
            self.assertIn("hscriptPath + 'char.png'", script)
            self.assertIn("addByPrefix('idle', 'Whitty idle dance', 24, true);", script)
            self.assertIn("char.addOffset('idle', 181, 412);", script)
            self.assertIn("char.playAnim('idle');", script)

            self.assertTrue(parsed["stageFound"])
            self.assertEqual(parsed["defaultZoom"], 0.8)
            self.assertTrue(parsed["useStartPoints"])
            self.assertEqual(parsed["offsets"],
                             ["bf:230:0", "gf:110:0", "dad:200:0"])
            self.assertEqual(parsed["spriteNames"], ["bg", "front"])
            self.assertEqual(parsed["spriteImages"],
                             ["alley/BallisticBackground", "alley/whittyFront"])
            self.assertEqual(parsed["spriteAnimations"], 1)
            stage_script = parsed["stageScript"]
            self.assertIn("setDefaultZoom(0.8);", stage_script)
            self.assertIn("stage.setOffsets('bf', 230, 0);", stage_script)
            self.assertIn("FlxAtlasFrames.fromSparrow('assets/images/alley/BallisticBackground.png', "
                          "'assets/images/alley/BallisticBackground.xml');", stage_script)
            self.assertIn("addByPrefix('Background Whitty Moving', "
                          "'Background Whitty Moving', 24, true);", stage_script)
            self.assertIn("addSprite(bg, BEHIND_ALL);", stage_script)
            self.assertIn("loadGraphic('assets/images/alley/whittyFront.png');", stage_script)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_whitty_donor_modules_recover_authored_data(self):
        parsed = self.run_fixture(
            DONOR / "data/stages/alleyBalls.hxc",
            DONOR / "data/characters/WhitBonkers.hxc",
        )
        self.assertTrue(parsed["characterFound"])
        self.assertEqual(parsed["animationCount"], 5)
        self.assertEqual(parsed["firstAnimation"]["prefix"], "Whitty idle dance")
        self.assertEqual(parsed["spritePath"], "characters/WhittyCrazy")
        self.assertEqual(parsed["iconName"], "angor")
        self.assertTrue(parsed["stageFound"])
        self.assertEqual(parsed["defaultZoom"], 0.8)
        self.assertEqual(parsed["offsets"], ["bf:230:0", "gf:110:0", "dad:200:0"])
        self.assertEqual(parsed["spriteImages"], ["alley/BallisticBackground"])

    def test_png_frame_counter_and_malformed_stage_reject_safely(self):
        with tempfile.TemporaryDirectory(prefix="fps-conv-png-", dir=ROOT / "tmp") as folder:
            root = Path(folder)
            module_source = (ROOT / "source/ModuleFunctions.hx").read_text()
            counter = extract_method(module_source, "static function readPngHorizontalFrames")
            fixture = """import haxe.Json;
import sys.io.File;
import haxe.io.Bytes;

class PngCounterFixture {
""" + counter + """
  static function writeHeader(path:String, width:Int, height:Int, ihdr:Bool):Void {
    var bytes = Bytes.alloc(24);
    bytes.set(0, 0x89); bytes.set(1, 0x50); bytes.set(2, 0x4E); bytes.set(3, 0x47);
    bytes.set(4, 0x0D); bytes.set(5, 0x0A); bytes.set(6, 0x1A); bytes.set(7, 0x0A);
    bytes.set(12, ihdr ? 0x49 : 0x58); bytes.set(13, 0x48); bytes.set(14, 0x44); bytes.set(15, 0x52);
    bytes.set(16, (width >> 24) & 0xFF); bytes.set(17, (width >> 16) & 0xFF);
    bytes.set(18, (width >> 8) & 0xFF); bytes.set(19, width & 0xFF);
    bytes.set(20, (height >> 24) & 0xFF); bytes.set(21, (height >> 16) & 0xFF);
    bytes.set(22, (height >> 8) & 0xFF); bytes.set(23, height & 0xFF);
    File.saveBytes(path, bytes);
  }

  static function main() {
    writeHeader('strip3.png', 450, 150, true);
    writeHeader('strip4.png', 600, 150, true);
    writeHeader('single.png', 150, 150, true);
    writeHeader('wrongheight.png', 450, 200, true);
    writeHeader('notihdr.png', 450, 150, false);
    Sys.println(Json.stringify({
      strip3: readPngHorizontalFrames('strip3.png', 150),
      strip4: readPngHorizontalFrames('strip4.png', 150),
      single: readPngHorizontalFrames('single.png', 150),
      wrongHeight: readPngHorizontalFrames('wrongheight.png', 150),
      notIhdr: readPngHorizontalFrames('notihdr.png', 150),
      missing: readPngHorizontalFrames('does-not-exist.png', 150)
    }));
  }
}
"""
            fixture_path = root / "PngCounterFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(root), "--run", "PngCounterFixture"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            lines = [line for line in result.stdout.splitlines()
                     if line.strip().startswith("{")]
            self.assertTrue(lines, result.stdout + result.stderr)
            parsed = json.loads(lines[-1])
            self.assertEqual(parsed["strip3"], 3)
            self.assertEqual(parsed["strip4"], 4)
            self.assertEqual(parsed["single"], 1)
            self.assertEqual(parsed["wrongHeight"], 0)
            self.assertEqual(parsed["notIhdr"], 0)
            self.assertEqual(parsed["missing"], 0)


if __name__ == "__main__":
    unittest.main()
