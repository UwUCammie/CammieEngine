"""A partial Psych character import can repair its registry entry safely."""

from pathlib import Path
import os
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


class PsychRegistryRepairTest(unittest.TestCase):
    def test_existing_generated_files_repair_a_missing_registry_key(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("hasNativeCharacterFiles(creation.name, assetRoot)", module)
        self.assertIn("ensurePsychCharacterRegistryEntry(creation.name, creation.charjson, assetRoot", module)

        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function validModuleName",
                "static function psychDestinationAssetRoot",
                "static function ensureDirectory",
                "static function chooseVSliceRegistry",
                "static function registryHasVSliceKey",
                "static function ensurePsychCharacterRegistryEntry",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class CoolUtil {{
  public static function parseJson(value:String):Dynamic return Json.parse(value);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}
class FlxColor {{
  var value:Int;
  public function new(value:Int) this.value = value;
  public static function fromRGB(red:Int, green:Int, blue:Int):FlxColor
    return new FlxColor((red << 16) | (green << 8) | blue);
  public function toWebString():String return StringTools.hex(value, 6);
}}
class Song {{
  public static function invalidateVisualRegistryCache():Void {{}}
}}
class CompatScriptManifest {{
  public static inline var ROOT_PREFIX:String = 'assets/imported_mods';
}}
class Main {{
  static var importBackgroundMode:Bool = false;
{methods}
  static function main() {{
    var root = Sys.args()[0];
    ensureDirectory(root);
    Sys.setCwd(root);
    var folder = Path.join(['assets', 'images', 'custom_chars', 'Champ-Huge']);
    ensureDirectory(folder);
    File.saveContent(Path.join([folder, 'char.png']), 'existing-atlas');
    File.saveContent(Path.join([folder, 'char.xml']), 'existing-xml');
    File.saveContent(Path.join(['assets', 'images', 'custom_chars', 'Champ-Huge.hscript']), 'existing-script');
    File.saveContent(Path.join(['assets', 'images', 'custom_chars', 'custom_chars.jsonc']),
      '{{"existing":{{"like":"existing","icons":[0,0,0,0],"colors":["#FFFFFF"]}}}}');
    if (!ensurePsychCharacterRegistryEntry('Champ-Huge', {{healthbar_colors:[1, 2, 3]}}))
      throw 'missing character registry key was not repaired';
    var registry:Dynamic = Json.parse(File.getContent(
      Path.join(['assets', 'images', 'custom_chars', 'custom_chars.jsonc'])));
    var repaired:Dynamic = Reflect.field(registry, 'Champ-Huge');
    if (registry.existing == null || repaired == null)
      throw 'repair replaced or omitted registry entries';
    if (repaired.like != 'Champ-Huge')
      throw 'repair wrote the wrong character alias';
    if (ensurePsychCharacterRegistryEntry('Champ-Huge', {{healthbar_colors:[9, 9, 9]}}))
      throw 'existing registry entry was not idempotent';
    if (File.getContent(Path.join([folder, 'char.png'])) != 'existing-atlas')
      throw 'repair overwrote generated character bytes';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(temp), "--run", "Main", str(temp / "runtime")],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
