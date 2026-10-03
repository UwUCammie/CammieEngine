"""Focused coverage for Freeplay registry path precedence and writes."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class FreeplayRegistryTest(unittest.TestCase):
    def test_runtime_resolver_keeps_one_authoritative_existing_file(self):
        registry_source = (ROOT / "source/FreeplayRegistry.hx").read_text().replace("package;\n", "", 1)
        fixture = f'''import haxe.Json;
import sys.FileSystem;
import sys.io.File;

{registry_source}

class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
  public static function saveContent(path:String, data:String):Void File.saveContent(path, data);
}}
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}

class RegistryFixture {{
  static function remove(path:String):Void {{
    if (FileSystem.exists(path) && !FileSystem.isDirectory(path)) FileSystem.deleteFile(path);
  }}
  static function write(path:String, value:String):Void File.saveContent(path, value);
  static function main():Void {{
    FileSystem.createDirectory('assets');
    FileSystem.createDirectory('assets/data');
    FileSystem.createDirectory('assets/images');
    var jsonc = FreeplayRegistry.JSONC_PATH;
    var json = FreeplayRegistry.JSON_PATH;
    var imageJsonc = FreeplayRegistry.IMAGE_JSONC_PATH;
    var imageJson = FreeplayRegistry.IMAGE_JSON_PATH;
    remove(jsonc); remove(json); remove(imageJsonc); remove(imageJson);

    // Conflicting dual files must always expose and overwrite JSONC.
    write(json, '[{{"name":"legacy"}}]');
    write(jsonc, '[{{"name":"seed"}}]');
    if (FreeplayRegistry.getPath() != jsonc) throw 'JSONC did not win dual precedence';
    if (Reflect.field(FreeplayRegistry.getJson()[0], 'name') != 'seed') throw 'JSONC was not read';
    FreeplayRegistry.saveContent('[{{"name":"updated"}}]');
    if (File.getContent(json) != '[{{"name":"legacy"}}]') throw 'legacy file was overwritten';
    if (File.getContent(jsonc) != '[{{"name":"updated"}}]') throw 'JSONC write missed selected file';

    // A JSON-only destination is retained; no competing JSONC is created.
    remove(jsonc);
    if (FreeplayRegistry.getPath() != json) throw 'JSON-only destination was not selected';
    if (Reflect.field(FreeplayRegistry.getJson()[0], 'name') != 'legacy') throw 'JSON-only file was not read';
    FreeplayRegistry.saveContent('[{{"name":"legacy-updated"}}]');
    if (FileSystem.exists(jsonc)) throw 'JSON-only write created a competing JSONC';
    if (File.getContent(json) != '[{{"name":"legacy-updated"}}]') throw 'JSON-only write missed selected file';

    // An old image-tree pack is still readable when no data-tree registry exists.
    remove(json);
    write(imageJson, '[{{"name":"image-legacy"}}]');
    write(imageJsonc, '[{{"name":"image-seed"}}]');
    if (FreeplayRegistry.getPath() != imageJsonc) throw 'image-tree JSONC did not win';
    remove(imageJsonc);
    if (FreeplayRegistry.getPath() != imageJson) throw 'image-tree JSON fallback failed';

    // Donor roots use the same precedence without reading the destination.
    FileSystem.createDirectory('donor');
    FileSystem.createDirectory('donor/data');
    FileSystem.createDirectory('donor/images');
    var donorJson = 'donor/data/freeplaySongJson.json';
    var donorImageJsonc = 'donor/images/freeplaySongJson.jsonc';
    write(donorJson, '[{{"name":"donor"}}]');
    write(donorImageJsonc, '[{{"name":"donor-image"}}]');
    if (FreeplayRegistry.getPathInRoot('donor') != donorJson) throw 'donor data registry precedence failed';
    remove(donorJson);
    if (FreeplayRegistry.getPathInRoot('donor') != donorImageJsonc) throw 'donor image registry fallback failed';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "RegistryFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RegistryFixture"],
                cwd=folder,
                capture_output=True,
                text=True,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_freeplay_consumers_do_not_bypass_the_shared_resolver(self):
        consumers = (
            "CategoryState.hx",
            "MainMenuState.hx",
            "FreeplayState.hx",
            "DifficultyManager.hx",
            "NewSongState.hx",
            "SelectSongsState.hx",
            "SelectSortState.hx",
            "SortState.hx",
            "ModPlusCarryState.hx",
        )
        for name in consumers:
            source = (ROOT / "source" / name).read_text()
            self.assertNotIn("freeplaySongJson.jsonc", source, name)
            self.assertNotIn("FNFAssets.getJson('assets/data/freeplaySongJson')", source, name)
            self.assertNotIn('FNFAssets.getJson("assets/data/freeplaySongJson")', source, name)
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("return FreeplayRegistry.getPath();", module)
        self.assertIn("destination:freeplayRegistryPath()", module)

    def test_shared_layout_merge_uses_the_registry_source_it_enumerated(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("static function mergeFreeplayRegistry(sourcePath:String", module)
        self.assertIn("mergeFreeplayRegistry(registry.source, importedNames)", module)
        self.assertIn("Do not recompute it from", module)
        self.assertIn("sourceRoot: shared", module)

    def test_python_validator_mirrors_the_same_precedence(self):
        validator = (ROOT / "tools/validate_ported_songs.py").read_text()
        self.assertIn("def freeplay_registry_path():", validator)
        self.assertIn("fp = rj(freeplay_registry_path())", validator)
        self.assertIn("AT('images', 'freeplaySongJson.jsonc')", validator)
