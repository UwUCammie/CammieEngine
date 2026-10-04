"""Regression coverage for the two-phase, non-blocking song importer."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


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


class ImportWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "source/ImportWorkflow.hx").read_text()

    def test_scan_plan_reports_duplicates_and_dependency_locations(self):
        source = self.source
        for field in (
            "songsFound:Int",
            "songsToImport:Int",
            "duplicateSongs:Int",
            "charactersFound:Int",
            "stagesFound:Int",
            "uiPacksFound:Int",
            "layoutsFound:Int",
            "cutscenesFound:Int",
            "missingDependencies:Int",
            "searched:Array<String>",
            "origin:String",
        ):
            self.assertIn(field, source)
        self.assertIn("DUPLICATE (not moved)", source)
        self.assertIn("[MISSING]", source)
        self.assertIn("Searched:", source)
        self.assertIn("ImportWorkflow.logPath()", source)

    def test_script_dependency_search_resolves_hscript_path_stem_folder(self):
        """`hscriptPath + 'asset.png'` points below the script's own folder."""
        source = self.source
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function normalized",
                "static function pathKey",
                "static function resolutionCacheKey",
                "static function uniquePush",
                "static function exists",
                "static function file",
                "static function caseInsensitiveFile",
                "static function caseInsensitivePath",
                "static function directory",
                "static function canonicalLegacyCharacter",
                "static function scriptCandidatesForToken",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}
class EngineCompat {{
  public static function stageLookupNames(value:String):Array<String> return [value];
  public static function resolveStageAlias(value:String):String return value;
  public static function resolveLegacyAssetPath(value:String):String return value;
}}

class HscriptPathFixture {{
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var script = Path.join([root, 'images/custom_stages/tank.hscript']);
    var candidates = scriptCandidatesForToken([root], script, 'tankSky.png', 'loadGraphic');
    var expected = Path.join([root, 'images/custom_stages/tank/tankSky.png']);
    if (candidates.indexOf(expected) < 0)
      throw 'hscriptPath stem folder was not searched';
    var driveCandidates = scriptCandidatesForToken([root], script, 'C:\\\\Mods\\\\asset.png', 'loadGraphic');
    if (driveCandidates.indexOf('C:/Mods/asset.png') < 0)
      throw 'drive-letter asset path was treated as relative';
    var slash = String.fromCharCode(92);
    var uncReference = slash + slash + 'server' + slash + 'share' + slash + 'asset.png';
    var uncCandidates = scriptCandidatesForToken([root], script, uncReference, 'loadGraphic');
    if (uncCandidates.indexOf('//server/share/asset.png') < 0)
      throw 'UNC asset path was treated as relative';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "HscriptPathFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            donor = Path(folder) / "donor"
            (donor / "images/custom_stages/tank").mkdir(parents=True)
            (donor / "images/custom_stages/tank/tankSky.png").write_bytes(b"png")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "HscriptPathFixture", str(donor)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_path_identity_preserves_linux_case_and_normalizes_windows_separators(self):
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in ("static function normalized", "static function pathKey")
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}

class ImportWorkflow {{
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var upper = Path.join([root, 'Donor']);
    var lower = Path.join([root, 'donor']);
    FileSystem.createDirectory(upper);
    #if !windows
    FileSystem.createDirectory(lower);
    #end
    var upperKey = pathKey(upper);
    var lowerKey = pathKey(lower);
    #if windows
    if (upperKey != lowerKey) throw 'Windows path identity is not case-insensitive';
    #else
    if (upperKey == lowerKey) throw 'Linux donor roots were case-folded';
    #end
    var windowsSpelling = StringTools.replace(upper, '/', '\\\\');
    if (pathKey(windowsSpelling) != upperKey)
      throw 'path identity changed with Windows separators';
    var unc = pathKey('\\\\\\\\server\\\\share\\\\Pack\\\\');
    var uncSlash = pathKey('//server/share/Pack/');
    if (unc != uncSlash) throw 'path identity lost UNC separator normalization';
    var missingA = pathKey(Path.join([root, 'missing', 'Freddy.hscript']));
    var missingB = pathKey(Path.join([root, 'missing', 'mom-car.hscript']));
    if (missingA == '' || missingB == '' || missingA == missingB)
      throw 'non-existent candidate paths collapsed to one empty identity';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportWorkflow.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportWorkflow", folder],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dependency_candidates_cover_shared_psych_and_hxc_layouts(self):
        """Dependency inspection follows the layouts consumed by import."""
        source = self.source
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function normalized",
                "static function pathKey",
                "static function resolutionCacheKey",
                "static function exists",
                "static function file",
                "static function caseInsensitiveFile",
                "static function caseInsensitivePath",
                "static function directory",
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
                "static function stageCandidates",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}
class CoolUtil {{
  public static var parseCount:Int = 0;
  public static function parseJson(raw:String):Dynamic {{
    parseCount++;
    return Json.parse(raw);
  }}
}}
class EngineCompat {{
  public static function stageLookupNames(value:String):Array<String> return [value];
  public static function resolveStageAlias(value:String):String return value;
  public static function resolveLegacyAssetPath(value:String):String return value;
}}
class DependencyFixture {{
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var dependencyCandidateCache:Map<String, Array<String>> = new Map<String, Array<String>>();
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var chars = charCandidates([root], 'Boyfriend-Vampire');
    var expectedChar = Path.join([root, 'shared/images/characters/boyfriend/vampire_boyfriend.PNG']);
    var charFound = false;
    for (candidate in chars) if (candidate.toLowerCase() == expectedChar.toLowerCase()) charFound = true;
    if (!charFound) throw 'Psych image field/shared asset was not resolved';
    var parsedAfterFirstLookup = CoolUtil.parseCount;
    chars.push('caller-mutation.png');
    var cachedChars = charCandidates([root], 'Boyfriend-Vampire');
    if (cachedChars.indexOf('caller-mutation.png') >= 0)
      throw 'character candidate cache returned a mutable shared array';
    if (CoolUtil.parseCount != parsedAfterFirstLookup)
      throw 'repeated character lookup reparsed its definition';
    var animateChars = charCandidates([root], 'gf-week2');
    var expectedAnimate = Path.join([root, 'shared/images/characters/girlfriend/gf_week2/Animation.json']);
    var animateFound = false;
    for (candidate in animateChars) if (candidate.toLowerCase() == expectedAnimate.toLowerCase()) animateFound = true;
    if (!animateFound) throw 'Psych Animate character atlas was not resolved';
    var stages = stageCandidates([root], 'Facility');
    var expectedStage = Path.join([root, 'data/stages/facility.HXC']);
    var stageFound = false;
    for (candidate in stages) if (candidate.toLowerCase() == expectedStage.toLowerCase()) stageFound = true;
    if (!stageFound) throw 'HXC stage path was not resolved';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "DependencyFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            donor = Path(folder) / "donor"
            (donor / "characters").mkdir(parents=True)
            (donor / "characters/Boyfriend-Vampire.json").write_text(
                '{"image":"characters/boyfriend/vampire_boyfriend"}'
            , newline='\n')
            (donor / "shared/images/characters/boyfriend").mkdir(parents=True)
            (donor / "shared/images/characters/boyfriend/vampire_boyfriend.PNG").write_bytes(b"png")
            (donor / "shared/characters").mkdir(parents=True)
            (donor / "shared/characters/gf-week2.json").write_text(
                '{"image":"characters/girlfriend/gf_week2"}'
            , newline='\n')
            (donor / "shared/images/characters/girlfriend/gf_week2").mkdir(parents=True)
            (donor / "shared/images/characters/girlfriend/gf_week2/Animation.json").write_text('{}', newline='\n')
            (donor / "data/stages").mkdir(parents=True)
            (donor / "data/stages/facility.HXC").write_bytes(b"hxc")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "DependencyFixture", str(donor)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_keyed_character_candidate_dedupe_preserves_order_and_first_spelling(self):
        char_candidates = extract_method(self.source, "static function charCandidates(")
        self.assertIn("var resultKeys:Map<String, Bool> = new Map()", char_candidates)
        self.assertIn("uniquePushKeyed(result, resultKeys", char_candidates)
        self.assertNotIn("uniquePush(result,", char_candidates)
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in (
                "static function normalized",
                "static function pathKey",
                "static function uniquePushKeyed",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}
class KeyedCandidateFixture {{
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var candidates:Array<String> = [];
    var keys:Map<String, Bool> = new Map();
    var first = root + '/folder/../images/custom_chars/bf/char.png';
    var normalizedDuplicate = root + '/images/custom_chars/bf/char.png';
    uniquePushKeyed(candidates, keys, first);
    uniquePushKeyed(candidates, keys, normalizedDuplicate);
    uniquePushKeyed(candidates, keys, '  ');
    if (candidates.length != 1 || candidates[0] != first)
      throw 'normalized duplicate changed order or first authored spelling';
    var next = root + '/images/custom_chars/dad/char.png';
    uniquePushKeyed(candidates, keys, next);
    if (candidates.length != 2 || candidates[1] != next)
      throw 'new candidate order changed';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "KeyedCandidateFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "--run", "KeyedCandidateFixture", folder],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(os.name == 'nt', 'requires a case-sensitive filesystem fixture')
    def test_mixed_case_parent_and_registry_paths_resolve_on_linux(self):
        """Windows-authored directory casing must not hide importer dependencies."""
        source = self.source
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function resolutionCacheKey",
                "static function exists",
                "static function file",
                "static function directory",
                "static function caseInsensitivePath",
                "static function caseInsensitiveFile",
                "static function registryDocument",
                "static function registryValue",
                "static function registryText",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(path:String):String return Path.normalize(path);
}}
class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
class MixedCaseFixture {{
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
{methods}
  static function main() {{
    var root = Sys.args()[0];
    FileSystem.createDirectory(Path.join([root, 'Data']));
    FileSystem.createDirectory(Path.join([root, 'Data', 'Characters']));
    var definition = Path.join([root, 'Data/Characters/ViCtIm.json']);
    File.saveContent(definition, '{{"name":"victim"}}');
    var resolvedDefinition = caseInsensitiveFile(
      Path.join([root, 'data', 'characters']), 'victim.JSON');
    if (Path.normalize(resolvedDefinition) != Path.normalize(definition))
      throw 'mixed-case parent did not resolve: ' + resolvedDefinition;

    FileSystem.createDirectory(Path.join([root, 'Images']));
    FileSystem.createDirectory(Path.join([root, 'Images', 'Custom_Chars']));
    var registry = Path.join([root, 'Images/Custom_Chars/custom_chars.jsonc']);
    File.saveContent(registry, '{{"Alias":{{"like":"victim"}}}}');
    var alias = registryText(
      registryValue(root, 'images/custom_chars/custom_chars.jsonc', 'alias'), 'like');
    if (alias != 'victim')
      throw 'mixed-case registry path did not resolve: ' + alias;
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "MixedCaseFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "--run", "MixedCaseFixture", folder],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_registry_documents_parse_once_per_scan_and_refresh_between_scans(self):
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in (
                "static function resolutionCacheKey",
                "static function clearResolutionCaches",
                "static function registryDocument",
                "static function registryValue",
                "static function findRegistryEntry",
            )
        )
        perform = extract_method(self.source, "public static function perform(sourcePath:String")
        self.assertIn("clearResolutionCaches();", perform)
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

class CoolUtil {{
  public static var parseCount:Int = 0;
  public static function parseJson(raw:String):Dynamic {{
    parseCount++;
    return Json.parse(raw);
  }}
}}
class RegistryCacheFixture {{
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var chartCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var dependencyCandidateCache:Map<String, Array<String>> = new Map<String, Array<String>>();
  static var luaDiagnosticCache:Map<String, Array<String>> = new Map<String, Array<String>>();
  static var luaDiagnosticCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static function caseInsensitivePath(path:String):String return path;
  static function file(path:String):Bool return FileSystem.exists(path) && !FileSystem.isDirectory(path);
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var registryPath = Path.join([root, 'custom_chars.jsonc']);
    File.saveContent(registryPath, '{{"Alpha":{{"like":"one"}},"Beta":{{"like":"two"}}}}');
    if (!findRegistryEntry(root, 'custom_chars.jsonc', 'alpha'))
      throw 'case-insensitive registry key was not found';
    var beta = registryValue(root, 'custom_chars.jsonc', 'Beta');
    if (Reflect.field(beta, 'like') != 'two')
      throw 'registry value lookup changed';
    if (CoolUtil.parseCount != 1)
      throw 'one scan parsed the same registry ' + CoolUtil.parseCount + ' times';

    File.saveContent(registryPath, '{{"Gamma":{{"like":"three"}}}}');
    clearResolutionCaches();
    if (!findRegistryEntry(root, 'custom_chars.jsonc', 'gamma'))
      throw 'next scan did not see the updated registry';
    if (findRegistryEntry(root, 'custom_chars.jsonc', 'alpha'))
      throw 'next scan retained a removed registry key';
    if (CoolUtil.parseCount != 2)
      throw 'updated scan did not parse the registry exactly once';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "RegistryCacheFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RegistryCacheFixture", folder],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dependency_candidate_cache_is_scan_scoped_and_returns_copies(self):
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in (
                "static function normalized",
                "static function pathKey",
                "static function resolutionCacheKey",
                "static function clearResolutionCaches",
                "static function dependencyCandidateCacheKey",
                "static function cachedDependencyCandidates",
                "static function rememberDependencyCandidates",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}
class CandidateCacheFixture {{
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var chartCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var dependencyCandidateCache:Map<String, Array<String>> = new Map<String, Array<String>>();
  static var luaDiagnosticCache:Map<String, Array<String>> = new Map<String, Array<String>>();
  static var luaDiagnosticCacheKnown:Map<String, Bool> = new Map<String, Bool>();
{methods}
  static function main() {{
    var root = Path.join([Sys.getCwd(), 'donor']);
    var original = ['donor/images/custom_chars/bf/char.json'];
    var remembered = rememberDependencyCandidates('character', [root], 'Boyfriend', original);
    remembered.push('caller-only-atlas.png');
    var firstRead = cachedDependencyCandidates('character', [root], 'Boyfriend');
    if (firstRead == null || firstRead.length != 1
      || firstRead[0] != 'donor/images/custom_chars/bf/char.json')
      throw 'cached paths were changed by the caller';
    firstRead.push('read-only-caller-mutation.png');
    var secondRead = cachedDependencyCandidates('character', [root], 'Boyfriend');
    if (secondRead == null || secondRead.length != 1)
      throw 'cache returned a shared mutable path list';
    if (cachedDependencyCandidates('character', [root], 'boyfriend') != null)
      throw 'case-distinct query reused another query result';
    if (cachedDependencyCandidates('stage', [root], 'Boyfriend') != null)
      throw 'candidate kinds shared a cache entry';
    clearResolutionCaches();
    if (cachedDependencyCandidates('character', [root], 'Boyfriend') != null)
      throw 'the next scan retained old candidate paths';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "CandidateCacheFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "CandidateCacheFixture"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        for kind in ("character", "stage", "ui", "cutscene", "layout"):
            marker = f"cachedDependencyCandidates('{kind}', sourceRoots, reference)"
            self.assertIn(marker, self.source)
        self.assertIn("LuaCompat.translate(File.getContent(entry.path), entry.path)", self.source)
        self.assertIn("luaDiagnosticCacheKnown", self.source)

    def test_hxc_data_families_copy_into_runtime_script_tree(self):
        """FPS Plus data modules enter the per-source compatibility namespace."""
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("static function mergeCompatScriptTrees", module)
        self.assertIn("static function mergeHxcScriptTree", module)
        self.assertIn("var familyDestination", module)
        self.assertIn("mergeHxcScriptTree(familyRoot, familyDestination, 0, result, skipPaths)", module)
        self.assertIn("CompatScriptManifest.destinationRoot", module)
        self.assertIn("assets/imported_mods", (ROOT / "source/CompatScriptManifest.hx").read_text())

    def test_scan_is_read_only_until_import_job_starts(self):
        source = self.source
        scan_body = source[source.index("public static function perform(sourcePath:String, ?importType:String)"):]
        scan_body = scan_body[:scan_body.index("class ImportImportJob")]
        self.assertNotIn("File.copy(", scan_body)
        self.assertNotIn("File.saveContent(", scan_body)
        self.assertIn("selectedType, descriptors);", scan_body)
        self.assertIn("ModuleFunctions.discoverSongImportsDetailed(source, null,", scan_body)
        self.assertIn("reportImportProgress('scan-songs', chart.path, discoveredIndex, discovered.length)", scan_body)
        self.assertIn("writeReport(result)", scan_body)

    def test_ui_facing_job_api_has_pollable_progress_and_background_worker(self):
        source = self.source
        for api in (
            "beginSongScan",
            "beginSongImport",
            "snapshot()",
            "isFinished()",
            "progress:Float",
            "completed:Int",
            "total:Int",
            "Thread.create",
        ):
            self.assertIn(api, source)
        # Import work is deliberately centralized in the existing duplicate-
        # safe importer, while the UI only polls immutable progress snapshots.
        self.assertIn("ModuleFunctions.importSongsFromPath(this.sourcePath, this.importType,", source)
        self.assertIn("scan == null ? null : scan.overlayMounts", source)
        self.assertIn("ModuleFunctions.setImportProgressCallback", source)
        self.assertIn("acceptProgress(payload)", source)
        self.assertIn("beginSongScan(sourcePath:String, ?importType:String)", source)
        self.assertIn("beginSongImport(sourcePath:String, scan:ImportScanResult, ?importType:String,", source)
        self.assertIn("public var importType(default, null):String", source)
        self.assertIn("importType: importType", source)
        self.assertIn("detectedRoots:Array<ImportScanRoot>", source)
        self.assertIn("detectedEngines:Array<String>", source)
        self.assertIn("ImportRootScanner.scanDetailed(source, selectedType, scannerCallbacks)", source)
        self.assertIn("descriptor.contentRoot", source)
        self.assertIn("descriptor.data", source)
        self.assertIn("dependencyRootsForChart(descriptors, chartPath)", source)
        self.assertIn("convertedCharts", source)
        self.assertIn("chartOverride", source)
        self.assertIn("V-Slice discovery already converted", source)
        self.assertNotIn("engine: selectedType == ImportSettings.AUTO ? 'Unknown'", source)

    def test_overlay_diagnostics_reach_report_and_import_settings_even_without_entries(self):
        workflow = self.source
        settings = (ROOT / "source/ImportSettingsState.hx").read_text()
        condition = "result.overlayDiagnostics != null && result.overlayDiagnostics.length > 0"
        self.assertIn(condition, workflow)
        self.assertIn(condition, settings)
        self.assertIn("Overlay diagnostics:", (ROOT / "source/ModuleFunctions.hx").read_text())

    def test_psych_lua_scan_diagnostics_include_external_event_sidecars(self):
        source = self.source
        self.assertIn("psychCompanionEvents(chartPath)", source)
        self.assertIn("inspectPsychLuaScripts(scanSong, chartPath, chart, roots)", source)
        self.assertIn("PsychScriptDiscovery.discover(root, songName, chart, companionEvents, chartPath)", source)
        self.assertIn("LuaCompat.translate(File.getContent(entry.path), entry.path)", source)

    def test_scan_worker_yields_reports_progress_and_supports_cooperative_cancel(self):
        source = self.source
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        for api in (
            "cancelRequested",
            "public function cancel():Void",
            "setImportCancelCallback",
            "isCancelRequested",
            "scan-songs",
        ):
            self.assertIn(api, source)
        self.assertIn("scan-discovery", module)
        self.assertIn("scan-assets", source)
        self.assertIn("scan-complete", source)
        self.assertIn("scanJob.cancel();", (ROOT / "source/ImportSettingsState.hx").read_text())
        self.assertIn("public static function yieldImportWork", module)
        self.assertIn("Sys.sleep(0.001)", module)
        self.assertIn("importWorkCancelled()", module)
        self.assertIn("ModuleFunctions.reportImportProgress('scan-assets'", source)

        import_job = source[source.index("class ImportImportJob"):]
        self.assertIn("ModuleFunctions.setImportCancelCallback(function():Bool", import_job)
        self.assertIn("ModuleFunctions.setImportCancelCallback(null)", import_job)
        cancel_body = extract_method(import_job, "public function cancel():Void")
        self.assertIn("cancelRequested = true", cancel_body)
        self.assertIn("phase: localDone ? (localPhase == 'import-cancelled'", import_job)
        merge_body = extract_method(module, "static function mergeTreeNonOverwriting")
        self.assertIn("importWorkCancelled()", merge_body)
        self.assertLess(merge_body.index("importWorkCancelled()"), merge_body.index("File.copy"))
        self.assertIn("static function mergeHxcScriptTree", module)
        self.assertIn("static function mergeCompatScriptTrees", module)
        self.assertIn("mergeCompatScriptTrees(sourceRoot", module)
        self.assertIn("['characters', 'stages', 'cutscenes', 'ui', 'events', 'notes', 'modules']", module)

    def test_completed_scan_handle_is_polled_during_done_handoff(self):
        """A worker can set done before the UI has consumed its result.

        The old outer update guard used hasActiveJob(), which becomes false
        at exactly that point.  This small Haxe model reproduces the state
        transition and makes sure a still-owned completed handle is consumed.
        The source assertions pin the production state to the same contract.
        """
        state = (ROOT / "source/ImportSettingsState.hx").read_text()
        update = extract_method(state, "override function update(elapsed:Float)")
        self.assertIn("if (hasJobHandle())", update)
        self.assertIn("pollJobs();", update)
        self.assertIn("function hasJobHandle():Bool", state)
        self.assertIn("return scanJob != null || importJob != null;", state)

        fixture = r'''class ScanHandoffFixture {
  static function main() {
    var handle:Dynamic = { done: true, result: "scan-result" };
    var scanResult:Dynamic = null;

    // This is the failed old guard: the worker is complete, but the handle
    // still owns a result which the main thread has not consumed yet.
    var active = handle != null && !handle.done;
    if (active) throw "fixture did not enter the completion handoff";
    if (handle == null) throw "completed handle was dropped before polling";

    var snapshot = handle;
    if (snapshot.done) {
      scanResult = snapshot.result;
      handle = null;
    }
    if (scanResult != "scan-result" || handle != null)
      throw "completed scan result was lost during handoff";
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ScanHandoffFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "ScanHandoffFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_completed_scan_summary_has_reserved_area_and_single_line_details(self):
        state = (ROOT / "source/ImportSettingsState.hx").read_text()
        self.assertIn("static inline var SUMMARY_HEIGHT:Int = 78", state)
        self.assertIn("scanSummary.fieldHeight = SUMMARY_HEIGHT", state)
        self.assertIn('"    Roots detected: " + detectedRootCount', state)
        self.assertIn('"    Engine types: " + rootEngines.length', state)
        self.assertIn("detailText.wordWrap = false", state)
        self.assertIn("detailText.fieldHeight / DETAIL_LINE_HEIGHT", state)
        self.assertIn("function wrapDetailLine", state)

    def test_scan_details_distinguish_evidence_from_actionable_failures(self):
        state = (ROOT / "source/ImportSettingsState.hx").read_text()
        show = extract_method(state, "function showScanResult(result:ImportScanResult)")
        classify = extract_method(state, "static function diagnosticDetailLabel(diagnostic:String)")
        shared = extract_method(
            (ROOT / "source/ImportDiagnostic.hx").read_text(),
            "public static function label(diagnostic:String)",
        )
        self.assertIn("diagnosticDetailLabel(diagnostic)", show)
        self.assertIn("informationalRows", show)
        self.assertIn("actionable findings are listed above", show)
        self.assertIn("ImportDiagnostic.label(diagnostic)", classify)
        # The persistent scan report must use the same engine-owned policy as
        # the UI, rather than unconditionally prefixing every line WARNING.
        self.assertIn("ImportDiagnostic.label(diagnostic)", self.source)

        fixture = f'''import StringTools;
class ImportDiagnostic {{
{shared}
}}
class ScanDiagnosticLabelFixture {{
{classify}
  static function main() {{
    if (diagnosticDetailLabel("[hxc-runtime-adapter] routed") != "[INFO]") throw "adapter label";
    if (diagnosticDetailLabel("[compatibility-alias] native") != "[INFO]") throw "alias label";
    if (diagnosticDetailLabel("[hxc-event-route] routed") != "[INFO]") throw "route label";
    if (diagnosticDetailLabel("[compatibility-fallback] native") != "[INFO]") throw "fallback label";
    if (diagnosticDetailLabel("[foreign-event-preserved] routed") != "[INFO]") throw "preserved label";
    if (diagnosticDetailLabel("[hxc-unsupported-hxc-module-body] body") != "[UNSUPPORTED]") throw "unsupported label";
    if (diagnosticDetailLabel("[unsupported] behavior") != "[UNSUPPORTED]") throw "bare unsupported label";
    if (diagnosticDetailLabel("[missing-asset] image") != "[MISSING]") throw "missing label";
    if (diagnosticDetailLabel("[missing] image") != "[MISSING]") throw "bare missing label";
    if (diagnosticDetailLabel("plain warning") != "[WARNING]") throw "warning label";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "ScanDiagnosticLabelFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "ScanDiagnosticLabelFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_completed_scan_handle_is_consumed_before_input_path_resumes(self):
        """A worker can finish between frames; that snapshot must reach the UI.

        The old update loop used ``hasActiveJob()`` as its outer guard.  A
        finished handle therefore made that guard false, skipped ``pollJobs``
        entirely, and left the screen showing ``scan-complete`` while still
        displaying "No completed scan."  Keep this regression test focused on
        the handoff contract rather than timing a native worker in CI.
        """
        ui = (ROOT / "source/ImportSettingsState.hx").read_text()
        update_body = extract_method(ui, "override function update(elapsed:Float)")
        self.assertIn("function hasJobHandle():Bool", ui)
        self.assertIn("if (hasJobHandle())", update_body)
        self.assertIn("pollJobs();", update_body)
        self.assertIn("if (hasJobHandle())\n\t\t\t\treturn;", update_body)

        poll_body = extract_method(ui, "function pollJobs():Void")
        self.assertIn("if (snapshot.complete)", poll_body)
        self.assertIn("scanJob = null", poll_body)
        self.assertIn("scanResult = completedResult", poll_body)
        self.assertIn("showScanResult(scanResult)", poll_body)
        # The completed handle is consumed before normal buttons are
        # refreshed, so the result is available to canImport() immediately.
        self.assertLess(poll_body.index("scanJob = null"), poll_body.index("refreshButtons();"))

    def test_scan_summary_is_compact_for_many_detected_roots(self):
        """The one-line summary must remain readable for a multi-root scan.

        Individual root paths belong in the paged details/report.  Putting a
        shortened path for every nested game folder in scanSummary makes the
        summary run off-screen before the song counts are even visible.
        """
        ui = (ROOT / "source/ImportSettingsState.hx").read_text()
        show_body = extract_method(ui, "function showScanResult(result:ImportScanResult)")
        summary_body = show_body[:show_body.index("detailLines = [];")]
        self.assertNotIn("shortenPath(root.path", summary_body)
        self.assertNotIn("root.path", summary_body)
        self.assertIn("detectedRoots.length", summary_body)
        self.assertIn("detectedEngines", summary_body)
        self.assertIn("rootEngines.length", summary_body)

    def test_scan_details_page_by_visual_lines_not_raw_entries(self):
        """Long diagnostics must not overflow a page of the detail panel."""
        ui = (ROOT / "source/ImportSettingsState.hx").read_text()
        details_per_page = extract_method(ui, "function detailsPerPage():Int")
        refresh = extract_method(ui, "function refreshDetails():Void")

        # Pagination needs a visual/wrapped-line budget.  A raw
        # ``detailLines.length / perPage`` calculation treats a 200-character
        # diagnostic as one line and can draw beyond detailText.fieldHeight.
        visual_markers = ("visual", "wrapped", "wrap", "lineCount", "lineHeight")
        self.assertTrue(
            any(marker in details_per_page.lower() or marker in refresh.lower() for marker in visual_markers),
            "details pagination must account for wrapped visual lines",
        )
        self.assertNotIn("start + perPage", refresh)
        self.assertNotIn("(detailLines.length - 1) / perPage", refresh)

    def test_source_duplicates_are_retained_with_winner_diagnostics(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        source = self.source
        settings = (ROOT / "source/ImportSettingsState.hx").read_text()
        for marker in (
            "sourceRoot:String",
            "sourceDuplicate:Bool",
            "sourceDuplicateOf:String",
            "var candidates:Array<SongImportCandidate>",
            "selectSongCandidates(candidates)",
            "songCandidateCompleteness",
            "skipped.song.sourceDuplicate = true",
            "[duplicate-source-candidate] Duplicate source candidate",
            "selected.push(winner)",
        ):
            self.assertIn(marker, module)
        self.assertIn("sourceDuplicate:Bool", source)
        self.assertIn("duplicate source candidate skipped; candidate from", source)
        self.assertIn("completeness comparison", source)
        self.assertIn("Candidate source:", source)
        self.assertIn("candidate source:", settings)

    def test_importer_info_diagnostics_have_stable_codes(self):
        """Informational scan lines must not collapse into `unclassified`."""
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        workflow = self.source
        self.assertIn("[vocal-stem-selection] Split V-Slice vocals were found", module)
        self.assertIn("[duplicate-source-candidate] Duplicate source candidate", module)
        self.assertIn("[compatibility-alias] Stage", workflow)
        self.assertIn("[compatibility-alias] Asset", workflow)

    def test_song_import_preflights_freeplay_registry_before_writing_targets(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        import_song = extract_method(module, "static public function importSong(songData:SongImport)")
        registry_read = import_song.index("FNFAssets.getText(freeplayPath)")
        target_setup = import_song.index("ensureDirectory(dataFolder)")
        chart_write = import_song.index("File.saveContent(chartDestination")
        self.assertLess(registry_read, target_setup)
        self.assertLess(target_setup, chart_write)
        self.assertIn("var freeplayPath = freeplayRegistryPath()", import_song)
        self.assertIn("if (FNFAssets.exists(freeplayPath))", import_song)
        self.assertIn("expected an array", import_song)
        # The only registry read is the preflight; malformed input therefore
        # returns before chart/audio folders can be created. The selected path
        # is centralized so legacy `.json` destinations are handled too.
        self.assertEqual(import_song.count("FNFAssets.getText(freeplayPath)"), 1)

    def test_dependency_scopes_are_selected_per_detected_root(self):
        source = self.source
        methods = "\n".join(
            extract_method(source, marker)
            for marker in ("static function pathWithin", "static function dependencyRootsForChart")
        )
        fixture = f'''import haxe.io.Path;
using StringTools;
typedef ImportRoot = {{ var root:String; var contentRoot:String; var data:String; }};
class ScopedDependencyFixture {{
  static function pathKey(path:String):String return Path.normalize(path).toLowerCase();
  static function uniquePush(items:Array<String>, value:String):Void {{
    for (item in items) if (pathKey(item) == pathKey(value)) return;
    items.push(value);
  }}
{methods}
  static function main() {{
    var roots:Array<ImportRoot> = [
      {{root:"/pack/one", contentRoot:"/pack/one/assets", data:"/pack/one/assets/data"}},
      {{root:"/pack/two", contentRoot:"/pack/two/assets", data:"/pack/two/assets/data"}}
    ];
    var one = dependencyRootsForChart(roots, "/pack/one/assets/data/demo/chart.json");
    if (one.length != 1 || one[0] != "/pack/one/assets") throw "wrong first root scope";
    var two = dependencyRootsForChart(roots, "/pack/two/assets/data/demo/chart.json");
    if (two.length != 1 || two[0] != "/pack/two/assets") throw "wrong second root scope";
    var none = dependencyRootsForChart(roots, "/pack/other/data/demo/chart.json");
    if (none.length != 0) throw "unrelated root leaked into dependency scope";
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ScopedDependencyFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "ScopedDependencyFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_progress_covers_asset_copy_phase_and_uses_mutex_snapshots(self):
        source = self.source
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("setImportProgressCallback", module)
        self.assertIn("setImportBackgroundMode", module)
        self.assertIn("completeImportOnMainThread", module)
        self.assertIn("reportImportProgress('assets'", module)
        self.assertIn("reportImportProgress('song-assets'", module)
        self.assertIn("reportImportProgress('registries'", module)
        self.assertIn("work:Int = 0", module)
        self.assertIn("var incomingWork", source)
        self.assertIn("workNow = incomingWork", source)
        self.assertIn("var assetFilesFound:Int", source)
        self.assertIn("addGenericAssetCounts(result, descriptors)", source)
        self.assertIn("import sys.thread.Mutex", source)
        self.assertGreaterEqual(source.count("stateMutex.acquire()"), 4)
        self.assertIn("if (!localDone && progress >= 1)", source)
        self.assertIn("runtimeCommitted", source)

    def test_runtime_commit_uses_only_successful_batch_songs_including_partial_cancel(self):
        """A completed worker may contain failed, skipped, and committed songs.

        The old handoff rebuilt the refresh list from every non-duplicate scan
        row, which could advertise failed songs to DifficultyManager and skipped
        cancellation results refreshed nothing.  The batch now carries the
        committed names so a partial import is playable immediately while
        failures remain absent.
        """
        source = self.source
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("@:optional var importedSongs:Array<String>", module)
        self.assertIn("importedSongs: []", module)
        self.assertIn("result.importedSongs.push(storageKey)", module)
        self.assertIn("var storageKey = importSongFolderName(songData)", module)
        poll = source[source.index("public function poll():ImportWorkflowProgress") :]
        commit_start = poll.index("if (!runtimeCommitted)")
        commit_end = poll.index("if (!reportWritten)", commit_start)
        commit = poll[commit_start:commit_end]
        self.assertIn("localResult.importedSongs", commit)
        self.assertIn("completeImportOnMainThread(importedNames)", commit)
        self.assertNotIn("scan.songs", commit)
        self.assertNotIn("localPhase != 'import-cancelled'", commit)

    def test_worker_does_not_invalidate_runtime_caches(self):
        """Cache mutation belongs to the completed main-thread handoff.

        The importer now runs visual/overlay writes on a native worker.  The
        resolver and Song registry maps are process-local mutable state, so a
        worker-side clear could race a render-thread asset read.  Keep the
        lower-level writer pure and make the handoff the sole invalidation
        boundary.
        """
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        handoff = extract_method(module, "public static function completeImportOnMainThread")
        self.assertIn("ImportOverlayResolver.invalidate()", handoff)
        self.assertIn("Song.invalidateVisualRegistryCache()", handoff)
        for marker in (
            "static function writeOverlayRetentionManifest",
            "static function importPsychCharacters",
            "static function importVSliceVisuals",
        ):
            self.assertNotIn("ImportOverlayResolver.invalidate()", extract_method(module, marker))
            self.assertNotIn("Song.invalidateVisualRegistryCache()", extract_method(module, marker))

    def test_freeplay_reloads_registry_from_runtime_disk_after_import(self):
        """The next category/freeplay state must observe the written registry."""
        category = (ROOT / "source/CategoryState.hx").read_text()
        main_menu = (ROOT / "source/MainMenuState.hx").read_text()
        assets = (ROOT / "source/FNFAssets.hx").read_text()
        freeplay = (ROOT / "source/FreeplayState.hx").read_text()
        self.assertIn("FreeplayRegistry.getJson()", category)
        self.assertIn("FreeplayRegistry.getJson()", main_menu)
        self.assertIn("FreeplayState.currentSongList = epicCategoryJs[0].songs", category)
        self.assertIn("getAmbigAsset([id], CoolUtil.JSON_EXT", assets)
        self.assertIn("for (songSnippet in currentSongList)", freeplay)
        # Import completion refreshes difficulty support for the committed
        # names; menu state creation then consumes the disk-backed registry.
        self.assertIn("completeImportOnMainThread(importedNames)", self.source)

    def test_auto_keeps_standalone_packages_alongside_detected_engine_roots(self):
        """Mixed parent selections must not drop package-shaped songs."""
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        discovery = extract_method(module, "static public function discoverSongImportsDetailed")
        self.assertIn("var legacySources:Map<String, SongImportSource>", discovery)
        self.assertIn("discoverLegacySongImportsDetailed(selectedPath, legacySources,", discovery)
        self.assertIn("rejectionCollector);", discovery)
        self.assertIn("candidates.push({song:song, root:candidateRoot", discovery)
        self.assertIn("Reflect.setField(songData, 'sourceRoot', packagePath)", module)
        self.assertIn("Reflect.setField(songData, 'engine', ImportEngine.MODDING_PLUS)", module)
        # The old implementation only returned package discovery when no
        # engine-shaped root was detected, losing valid songs in mixed parents.
        self.assertNotIn("roots.length == 0 && (selected == ImportEngine.AUTO", discovery)
        self.assertIn("?preScannedRoots:Array<ImportRootScanner.ImportRoot>", module)
        self.assertIn("preScannedRoots == null ? ImportRootScanner.scan", discovery)
        self.assertIn("}) : preScannedRoots.copy()", discovery)

    def test_asset_song_import_indexes_chart_and_audio_folders_once(self):
        """Large per-song trees should not rescan each parent for every song."""
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        discovery = extract_method(module, "static function appendAssetSongImports")
        self.assertIn(
            "var indexNamedDirectories = function(parent:String, names:Array<String>):Map<String, String>",
            discovery,
        )
        self.assertIn("if (!indexed.exists(key))", discovery)
        self.assertIn("FileSystem.isDirectory(candidate)", discovery)
        self.assertIn("audioSongFolders = indexNamedDirectories(audioRoot, audioFolderNames)", discovery)
        self.assertIn("var chartSongFolders = indexNamedDirectories(chartsRoot, songFolderNames)", discovery)
        self.assertIn("chartSongFolders.get(StringTools.trim(songFolderName).toLowerCase())", discovery)
        self.assertIn("audioSongFolders.get(StringTools.trim(songFolderName).toLowerCase())", discovery)
        self.assertNotIn("findNamedDirectory(chartsRoot, songFolderName)", discovery)
        self.assertNotIn("findNamedDirectory(audioRoot, songFolderName)", discovery)

    def test_registry_keys_are_not_themselves_dependency_successes(self):
        source = self.source
        self.assertIn("registryValue", source)
        self.assertIn("registryText", source)
        # A registry is consulted for aliases/implementation names, but no
        # dependency call passes the old registryFound shortcut anymore.
        self.assertIn("var p1Candidates = charCandidates(roots, p1)", source)
        self.assertIn("var stageCandidatesForChart = stageCandidates(roots, stage)", source)
        self.assertNotIn("cutsceneCandidates(roots, cutscene), cutsceneRegistry", source)
        self.assertIn("inspectImplementationScripts", source)
        self.assertIn("'/char.png'", source)
        self.assertIn("custom_stages", source)
        self.assertIn("Paths.image", source)
        self.assertIn("Paths.sound", source)
        self.assertIn("dependencyRootsForChart(descriptors, chartPath)", source)
        self.assertIn("descriptor.contentRoot", source)
        self.assertIn("descriptor.data", source)
        self.assertIn("for (suffix in ['/char.png', '/char.xml', '/char.txt', '.hscript', '.json', '.jsonc'])", source)
        self.assertIn("characterImplementationFound", source)
        self.assertIn("assetRelative", source)
        self.assertIn("Paths.music", source)
        self.assertIn("Paths.video", source)
        self.assertIn("for (suffix in ['.hscript'])", source)

    def test_psych_healthicon_is_a_logical_icon_dependency(self):
        """Psych healthicon ids are not reported as arbitrary JSON paths."""
        source = self.source
        self.assertIn("? 'health-icon' : 'json-asset'", source)
        self.assertIn("case 'health-icon'", source)
        self.assertIn("value == 'dad' || value == 'daddy'", source)
        self.assertNotIn("dependency(result, song, 'json-asset', reference, path,\n\t\t\t\t\tscriptCandidatesForToken", source)

    def test_destination_registries_and_legacy_character_aliases_satisfy_scan(self):
        """Donor charts keep their authored ids while native assets resolve."""
        source = self.source
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function normalized",
                "static function pathKey",
                "static function resolutionCacheKey",
                "static function uniquePush",
                "static function exists",
                "static function file",
                "static function directory",
                "static function caseInsensitivePath",
                "static function field(value",
                "static function caseInsensitiveFile",
                "static function registryDocument",
                "static function registryValue",
                "static function registryText",
                "static function canonicalLegacyCharacter",
                "static function dependencyRootsWithDestination",
                "static function destinationBuiltinDependency",
                "static function characterImplementationFound",
                "static function uniquePushKeyed",
                "static function dependencyCandidateCacheKey",
                "static function cachedDependencyCandidates",
                "static function rememberDependencyCandidates",
                "static function charCandidates",
                "static function stageCandidates",
                "static function uiCandidates",
                "static function cutsceneCandidates",
                "static function layoutCandidates",
                "static function addSongDiagnostic",
                "static function dependency(result",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef ImportScanDependency = {{
  var kind:String; var reference:String; var found:Bool;
  var searched:Array<String>; var origin:String;
}};
typedef ImportScanSong = {{
  var dependencies:Array<ImportScanDependency>; var missing:Array<ImportScanDependency>;
  @:optional var diagnostics:Array<String>;
}};
typedef ImportScanResult = {{ var missingDependencies:Int; }};
class ImportSettings {{
  public static function normalizeSourcePath(path:String):String return Path.normalize(path);
}}
class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
class EngineCompat {{
  public static function stageLookupNames(value:String):Array<String> return [value];
  public static function resolveStageAlias(value:String):String return value;
  public static function resolveLegacyAssetPath(value:String):String return value;
  public static function planVisualFallback(kind:String, reference:String, origin:String,
      searched:Array<String>, impact:String, ?classification:String):Dynamic
    return {{diagnostic: {{message: ''}}}};
}}
class ImportCompat {{
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var dependencyCandidateCache:Map<String, Array<String>> = new Map<String, Array<String>>();
{methods}
  static function main() {{
    var donor = Sys.args()[0];
    var roots = [donor];
    var searched = dependencyRootsWithDestination(roots);
    var destinationAssets = Path.join([Sys.getCwd(), 'assets']);
    if (searched.length != 2 || pathKey(searched[1]) != pathKey(destinationAssets))
      throw 'destination scope missing';
    var aliases = ['boyfriend' => 'bf', 'daddy' => 'dad', 'girlfriend' => 'gf'];
    for (alias in aliases.keys()) {{
      if (canonicalLegacyCharacter(alias) != aliases.get(alias)) throw 'alias not canonicalized: ' + alias;
      var candidates = charCandidates(searched, alias);
      if (!characterImplementationFound(candidates)) throw 'native alias unresolved: ' + alias;
      var scan:ImportScanResult = {{missingDependencies:0}};
      var song:ImportScanSong = {{dependencies:[], missing:[]}};
      dependency(scan, song, 'character', alias, 'donor/chart.json', candidates);
      if (song.dependencies.length != 1 || !song.dependencies[0].found
          || song.dependencies[0].reference != alias || scan.missingDependencies != 0)
        throw 'dependency changed or stayed missing: ' + alias;
    }}
    var stageScan:ImportScanResult = {{missingDependencies:0}};
    var stageSong:ImportScanSong = {{dependencies:[], missing:[]}};
    dependency(stageScan, stageSong, 'stage', 'stage', 'donor/chart.json',
      stageCandidates(searched, 'stage'));
    if (stageSong.missing.length != 0) throw 'native stage registry was missed';
    var uiScan:ImportScanResult = {{missingDependencies:0}};
    var uiSong:ImportScanSong = {{dependencies:[], missing:[]}};
    dependency(uiScan, uiSong, 'ui', 'normal', 'donor/chart.json', uiCandidates(searched, 'normal'));
    if (uiSong.missing.length != 0) throw 'native UI registry was missed';
    var pixelUiScan:ImportScanResult = {{missingDependencies:0}};
    var pixelUiSong:ImportScanSong = {{dependencies:[], missing:[]}};
    dependency(pixelUiScan, pixelUiSong, 'ui', 'pixel', 'donor/pixel-chart.json', uiCandidates(searched, 'pixel'));
    if (pixelUiSong.missing.length != 0) throw 'native pixel UI route was missed';
    var builtInScan:ImportScanResult = {{missingDependencies:0}};
    var builtInSong:ImportScanSong = {{dependencies:[], missing:[]}};
    dependency(builtInScan, builtInSong, 'cutscene', 'senpai', 'donor/chart.json', []);
    dependency(builtInScan, builtInSong, 'layout', 'normal', 'donor/chart.json', []);
    if (builtInSong.missing.length != 0) throw 'built-in dependency was missed';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp_path = Path(folder)
            (temp_path / "ImportCompat.hx").write_text(fixture, newline='\n')
            donor = temp_path / "donor/assets"
            for character in ("bf", "dad", "gf"):
                (temp_path / f"assets/images/custom_chars/{character}").mkdir(parents=True)
                (temp_path / f"assets/images/custom_chars/{character}/char.png").write_bytes(b"png")
                (temp_path / f"assets/images/custom_chars/{character}.hscript").write_text("function init(char) {}", newline='\n')
            (temp_path / "assets/images/custom_chars/custom_chars.jsonc").write_text(
                '{"bf":{"like":"bf"},"dad":{"like":"dad"},"gf":{"like":"gf"}}'
            , newline='\n')
            (temp_path / "assets/images/custom_stages").mkdir(parents=True)
            (temp_path / "assets/images/custom_stages/custom_stages.json").write_text('{"stage":"stage"}', newline='\n')
            (temp_path / "assets/images/custom_stages/stage.hscript").write_text("function start() {}", newline='\n')
            (temp_path / "assets/images/custom_ui/ui_packs/normal").mkdir(parents=True)
            (temp_path / "assets/images/custom_ui/ui_packs/ui.json").write_text(
                '{"normal":{"uses":"normal"}}'
            , newline='\n')
            (temp_path / "assets/images/custom_ui/ui_packs/normal/NOTE_assets.png").write_bytes(b"png")
            donor.mkdir(parents=True)
            chart = donor / "chart.json"
            original = '{"song":{"player1":"boyfriend","player2":"daddy","gf":"girlfriend"}}'
            chart.write_text(original, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportCompat", str(donor)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            self.assertEqual(chart.read_text(), original)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_native_character_definitions_bypass_legacy_atlas_fallback(self):
        """A valid registry/HXC character must not become a false atlas warning."""
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in (
                "static function normalized",
                "static function pathKey",
                "static function resolutionCacheKey",
                "static function uniquePush",
                "static function exists",
                "static function file",
                "static function directory",
                "static function caseInsensitivePath",
                "static function registryDocument",
                "static function registryValue",
                "static function registryText",
                "static function canonicalLegacyCharacter",
                "static function characterRegistryVisualFound",
                "static function characterImplementationFound",
                "static function destinationBuiltinDependency",
                "static function legacyCharacterAtlasNeeded",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(path:String):String return Path.normalize(path);
}}
class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
class AtlasFallbackCompat {{
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var nativeScript = Path.join([root, 'images/custom_chars/mom-car.hscript']);
    var nativeCandidates = [nativeScript];
    if (legacyCharacterAtlasNeeded([root], 'Freddy', nativeCandidates))
      throw 'registry-backed native character requested atlas fallback';
    if (legacyCharacterAtlasNeeded([root], 'Golden-freddy', nativeCandidates))
      throw 'registry-backed aliased character requested atlas fallback';
    var hxc = Path.join([root, 'data/characters/Whitty.hxc']);
    if (legacyCharacterAtlasNeeded([root], 'Whitty', [hxc]))
      throw 'HXC character requested atlas fallback';
    if (!legacyCharacterAtlasNeeded([root], 'MissingCharacter', []))
      throw 'missing character was incorrectly treated as native';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp_path = Path(folder)
            (temp_path / "AtlasFallbackCompat.hx").write_text(fixture, newline='\n')
            donor = temp_path / "donor"
            (donor / "images/custom_chars/mom-car").mkdir(parents=True)
            (donor / "data/characters").mkdir(parents=True)
            (donor / "images/custom_chars/custom_chars.jsonc").write_text(
                '{{"Freddy":{{"like":"mom-car"}},"Golden-freddy":{{"like":"mom-car"}}}}'
            , newline='\n')
            (donor / "images/custom_chars/mom-car/char.png").write_bytes(b"png")
            (donor / "images/custom_chars/mom-car/char.xml").write_text("<TextureAtlas/>", newline='\n')
            (donor / "images/custom_chars/mom-car.hscript").write_text("", newline='\n')
            (donor / "data/characters/Whitty.hxc").write_text("return null;", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "AtlasFallbackCompat", str(donor)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_phase_reuses_native_character_gate_before_atlas_inference(self):
        """Import-time atlas recovery must match scan-time native resolution."""
        module = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
        method = extract_method(module, "static function importLegacyCharacterAtlases")
        self.assertIn("var implementationRoots = roots.copy()", method)
        self.assertIn("implementationRoots.push('assets')", method)
        self.assertIn("ImportWorkflow.ImportScanJob.shouldInferLegacyCharacterAtlas(implementationRoots, reference.name)", method)
        self.assertNotIn("reference.name == 'Freddy'", method)
        self.assertNotIn("reference.name == 'Golden-freddy'", method)


if __name__ == "__main__":
    unittest.main()
