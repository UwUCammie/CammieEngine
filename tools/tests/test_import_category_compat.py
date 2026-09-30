"""Regression coverage for donor-local Freeplay categories during imports."""

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


class ImportCategoryCompatTest(unittest.TestCase):
    def test_base_game_rows_from_donor_are_moved_to_imported(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        helper = extract_method(module, "static function normalizeImportedCategory")
        json_equal = extract_method(module, "static function importJsonValuesEqual")
        merge = extract_method(module, "static function mergeFreeplayRegistry")
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int; }};
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}
class ImportCategoryFixture {{
  static function freeplayRegistryPath():String return 'assets/data/freeplaySongJson.jsonc';
  static function importPathKey(path:String):String return Path.normalize(path);
  static function isImportFile(path:String):Bool
    return path != null && FileSystem.exists(path) && !FileSystem.isDirectory(path);
  static function ensureDirectory(path:String):Void {{
    if (path == null || path == '' || FileSystem.exists(path)) return;
    var parent = Path.directory(path);
    if (parent != null && parent != '' && parent != path) ensureDirectory(parent);
    FileSystem.createDirectory(path);
  }}
{helper}
{json_equal}
{merge}
  static function countSong(registry:Dynamic, categoryName:String, songName:String):Int {{
    var count = 0;
    for (category in (cast registry:Array<Dynamic>)) {{
      if (category == null || category.name == null || category.songs == null
          || Std.string(category.name).toLowerCase() != categoryName.toLowerCase()) continue;
      for (song in (cast category.songs:Array<Dynamic>))
        if (song != null && song.name != null
            && Std.string(song.name).toLowerCase() == songName.toLowerCase()) count++;
    }}
    return count;
  }}
  static function main():Void {{
    FileSystem.createDirectory('donor');
    FileSystem.createDirectory('donor/data');
    FileSystem.createDirectory('assets');
    FileSystem.createDirectory('assets/data');
    File.saveContent('donor/data/freeplaySongJson.json',
      '[{{"name":"Base Game","songs":[{{"name":"fnaf-song","character":"freddy"}},'
      + '{{"name":"fnaf-bonus"}},{{"name":"donor-only"}}]}}]');
    File.saveContent(freeplayRegistryPath(),
      '[{{"name":"Imported","songs":[{{"name":"fnaf-song","character":"freddy"}}]}},'
      + '{{"name":"Base Game","songs":[{{"name":"fnaf-song"}},{{"name":"native-song"}}]}}]');
    var imported:Map<String, Bool> = new Map<String, Bool>();
    imported.set('fnaf-song', true);
    imported.set('fnaf-bonus', true);
    var result = mergeFreeplayRegistry('donor/data/freeplaySongJson.json', imported);
    if (result.failed != 0) throw 'registry merge failed';
    var merged:Dynamic = Json.parse(File.getContent(freeplayRegistryPath()));
    if (countSong(merged, 'Imported', 'fnaf-song') != 1)
      throw 'existing imported row was lost or duplicated';
    if (countSong(merged, 'Imported', 'fnaf-bonus') != 1)
      throw 'new donor Base Game row was not added to Imported';
    if (countSong(merged, 'Base Game', 'fnaf-song') != 0
        || countSong(merged, 'Base Game', 'fnaf-bonus') != 0)
      throw 'selected imported rows remain in the donor-local Base Game category';
    if (countSong(merged, 'Base Game', 'native-song') != 1)
      throw 'unrelated destination Base Game row was removed';
    if (countSong(merged, 'Imported', 'donor-only') != 0)
      throw 'a donor song outside the import selection was copied';
    if (normalizeImportedCategory(' Base Game ') != 'Imported'
        || normalizeImportedCategory('Custom Pack') != 'Custom Pack'
        || normalizeImportedCategory(null) != 'Imported')
      throw 'import category normalization changed';
    var formatted = '[\n  {{"name":"Imported", "songs":[{{"name":"fnaf-song", "character":"freddy"}},'
      + '{{"name":"fnaf-bonus"}}]}},\n  {{"name":"Base Game", "songs":[{{"name":"native-song"}}]}}\n]';
    File.saveContent(freeplayRegistryPath(), formatted);
    var repeated = mergeFreeplayRegistry('donor/data/freeplaySongJson.json', imported);
    if (repeated.failed != 0 || repeated.copied != 0
        || File.getContent(freeplayRegistryPath()) != formatted)
      throw 'logical no-op merge reserialized the destination registry';
    if (!importJsonValuesEqual(Json.parse('{{"a":1,"nested":[{{"ok":true,"n":2}}]}}'),
        Json.parse('{{"nested":[{{"n":2.0,"ok":true}}],"a":1.0}}')))
      throw 'JSON comparison treated object order or equivalent number spelling as a change';
    if (importJsonValuesEqual(Json.parse('[1,2]'), Json.parse('[2,1]')))
      throw 'JSON comparison ignored array order';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportCategoryFixture.hx"
            fixture_path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "ImportCategoryFixture"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_malformed_modding_plus_stage_map_recovers_only_for_stage_registry(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        helpers = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function registryArrayContains",
                "static function isImportStageMapRegistry",
                "static function recoverImportStageMapRegistry",
                "static function parseImportRegistryJson",
                "static function mergeObjectRegistry",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int; }};
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}
class StageRegistryFixture {{
  static function importPathKey(path:String):String return Path.normalize(path);
  static function isImportFile(path:String):Bool
    return path != null && FileSystem.exists(path) && !FileSystem.isDirectory(path);
  static function ensureDirectory(path:String):Void {{
    if (path == null || path == '' || FileSystem.exists(path)) return;
    var parent = Path.directory(path);
    if (parent != null && parent != '' && parent != path) ensureDirectory(parent);
    FileSystem.createDirectory(path);
  }}
{helpers}
  static function main():Void {{
    var malformed = '{{"fnaf2":"fnaf2"\\n  "fnaf-street":"fnaf-street",}}';
    FileSystem.createDirectory('donor/assets/images/custom_stages');
    File.saveContent('donor/assets/images/custom_stages/custom_stages.json', malformed);
    var result = mergeObjectRegistry('donor/assets/images/custom_stages/custom_stages.json',
      'assets/images/custom_stages/custom_stages.json');
    if (result.failed != 0 || result.copied != 1) throw 'stage registry merge failed';
    var copied = File.getContent('assets/images/custom_stages/custom_stages.json');
    var recovered:Dynamic = parseImportRegistryJson(copied,
      'assets/images/custom_stages/custom_stages.json');
    if (recovered == null || Reflect.field(recovered, 'fnaf2') != 'fnaf2'
        || Reflect.field(recovered, 'fnaf-street') != 'fnaf-street')
      throw 'simple stage registry recovery lost entries';
    if (parseImportRegistryJson(malformed, 'donor/assets/data/other.json') != null)
      throw 'recovery escaped the stage registry boundary';
    if (recoverImportStageMapRegistry('{{"a":"b" "c":3}}') != null)
      throw 'non-string map values were accepted';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "StageRegistryFixture.hx"
            fixture_path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "StageRegistryFixture"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_legacy_import_metadata_uses_category_normalization(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn(
            "category: normalizeImportedCategory(getInfoValue(info, 'category', 'Imported'))",
            module,
        )


if __name__ == "__main__":
    unittest.main()
