"""The dependency report finds characters and stages in per-library V-Slice builds.

Some V-Slice builds split their assets into library folders and keep each
definition in its own folder beside its sprites, for example
`gameplay/characters/<id>/<id>.json` with `assetPath: gameplay/characters/<id>/<id>`
and a DDS texture. The importer converts those, but the dependency scan only
probed flat definition folders, so every converted character was reported as a
missing donor dependency and the missing count was wrong.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND
from test_import_workflow import extract_method

ROOT = Path(__file__).resolve().parents[2]

METHODS = (
    "static function normalized",
    "static function pathKey",
    "static function resolutionCacheKey",
    "static function directoryCaseCandidates",
    "static function exists",
    "static function file",
    "static function caseInsensitiveFile",
    "static function caseInsensitivePath",
    "static function directory(",
    "static function uniquePush",
    "static function uniquePushKeyed",
    "static function field",
    "static function registryDocument",
    "static function registryValue",
    "static function registryText",
    "static function canonicalLegacyCharacter",
    "static function dependencyCandidateCacheKey",
    "static function cachedDependencyCandidates",
    "static function rememberDependencyCandidates",
    "static function charCandidates",
    "static function libraryAssetParent(",
    "static function stageCandidates",
    "static function characterImplementationFound(",
)


def fixture_methods():
    source = (ROOT / "source/ImportWorkflow.hx").read_text(encoding="utf-8")
    return "\n".join(extract_method(source, marker) for marker in METHODS)


class ImportLibraryLayoutDependenciesTest(unittest.TestCase):
    def run_fixture(self, body, layout):
        fixture = '''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class ImportSettings {
  public static function normalizeSourcePath(value:Dynamic):String {
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }
}
class CoolUtil {
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
}
class EngineCompat {
  public static function stageLookupNames(value:String):Array<String> return [value];
  public static function resolveStageAlias(value:String):String return value;
  public static function resolveLegacyAssetPath(value:String):String return value;
}
class LayoutFixture {
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var directoryCaseIndex:Map<String, Map<String, Array<String>>> = new Map();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var dependencyCandidateCache:Map<String, Array<String>> = new Map<String, Array<String>>();
METHODS
  static function fail(message:String):Void throw message;
  static function main() {
    var root = Sys.args()[0];
BODY
    Sys.println('layout-ok');
  }
}
'''.replace('METHODS', fixture_methods()).replace('BODY', body)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "LayoutFixture.hx").write_text(fixture, newline='\n')
            donor = Path(folder) / "mod"
            for relative, content in layout.items():
                target = donor / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "--run", "LayoutFixture",
                                     str(donor / "gameplay").replace('\\', '/')],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('layout-ok', result.stdout)

    def test_colocated_character_with_library_asset_path_is_found(self):
        self.run_fixture('''
    var candidates = charCandidates([root], 'hexa');
    if (!characterImplementationFound(candidates)) fail('per-library character reported missing: ' + candidates.join(', '));
    var stages = stageCandidates([root], 'court');
    var stageFound = false;
    for (candidate in stages) if (FileSystem.exists(candidate)) stageFound = true;
    if (!stageFound) fail('per-library stage reported missing: ' + stages.join(', '));
''', {
            'gameplay/characters/hexa/hexa.json': '{"assetPath": "gameplay/characters/hexa/hexa"}',
            'gameplay/characters/hexa/hexa.dds': 'dds',
            'gameplay/characters/hexa/hexa.xml': '<TextureAtlas/>',
            'gameplay/stages/court/court.json': '{"props": []}',
        })

    def test_definition_without_sprite_stays_missing(self):
        self.run_fixture('''
    var candidates = charCandidates([root], 'hexa');
    if (characterImplementationFound(candidates)) fail('a definition with no sprite was accepted');
    // An assetPath that does not start with the library folder is not re-rooted.
    if (libraryAssetParent(root, 'characters/hexa/hexa') != null) fail('plain assetPath was re-rooted');
    if (libraryAssetParent(root, 'gameplay/characters/hexa/hexa') == null) fail('library assetPath was not re-rooted');
''', {
            'gameplay/characters/hexa/hexa.json': '{"assetPath": "gameplay/characters/hexa/hexa"}',
            'gameplay/characters/hexa/hexa.xml': '<TextureAtlas/>',
        })


if __name__ == '__main__':
    unittest.main()
