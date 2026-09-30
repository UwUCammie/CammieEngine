"""Owner-scoped retention and repair checks for NMV StageData JSON."""

from pathlib import Path
import json
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
    raise AssertionError(marker)


def fixture_source() -> str:
    source = (ROOT / "source/ModuleFunctions.hx").read_text()
    markers = (
        "static function importPathKey",
        "static function importPathIsWithin",
        "static function validImportEntryName",
        "static function ensureDirectory",
        "static function findChildDirectory",
        "static function compatScriptTreeNames",
        "static function collectNightmareVisionStageDataFiles",
        "static function mergeNightmareVisionStageDataFiles",
        "static function mergeNightmareVisionAssetFiles",
        "static function isImportFile",
        "static function copyImportFileNonOverwriting",
        "static function compatScriptNamespaceHasExpectedFiles",
        "static function mergeSelectedNightmareVisionScriptOwners",
    )
    methods = "\n".join(extract_method(source, marker) for marker in markers)
    return f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int;
  @:optional var errors:Array<String>; }};
typedef SongImportSource = {{ var engine:String; var sourceRoot:String; }};
class ImportSettings {{
  public static function normalizeSourcePath(path:Dynamic):String return Path.normalize(Std.string(path));
}}
class CompatScriptManifest {{ public static inline var ROOT_PREFIX:String = 'assets/imported_mods'; }}
class PsychLuaScriptDependencies {{
  public static function discover(root:String):Dynamic return {{files:[], complete:true}};
}}
class StageImportFixture {{
  static var selectedNamespace:String;
  static function importWorkCancelled():Bool return false;
  static function mergeCompatScriptTrees(contentRoot:String, sourceRoot:String, engine:String,
      result:ImportAssetMergeResult, ?skipPaths:Map<String, Bool>,
      ?modPlusCharacterIds:Array<String>, ?destinationSubpath:String):String
    return selectedNamespace;
  static function collectCompatScriptFiles(source:String, relative:String, hxcOnly:Bool,
      output:Array<Dynamic>, depth:Int, budget:Array<Int>, ?suffixes:Array<String>,
      ?includeHaxe:Bool = false):Void {{}}
  static function collectNightmareVisionScriptFiles(root:String, prefix:String,
      output:Array<Dynamic>):Bool return true;
{methods}
  static function main() {{
    var args = Sys.args();
    if (args.length > 0 && args[0] == '--collect') {{
      var files:Array<Dynamic> = [];
      if (!collectNightmareVisionStageDataFiles(args[1], files)) throw 'collector incomplete';
      Sys.println(haxe.Json.stringify(files));
      return;
    }}
    var donor = args[0];
    var destination = args[1];
    selectedNamespace = destination;
    var contentRoot = donor;
    if (importPathKey(donor) == importPathKey(destination)
        || importPathIsWithin(destination, donor)) throw 'fixture donor and installed owner must be distinct';
    var expected = compatScriptNamespaceHasExpectedFiles(donor, destination,
      ImportEngine.NIGHTMARE_VISION);
    if (expected) throw 'missing destination was marked complete';
    var result:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0}};
    var names:Map<String, Bool> = new Map();
    names.set('fixture', true);
    var sources:Map<String, SongImportSource> = new Map();
    sources.set('fixture', {{engine:ImportEngine.NIGHTMARE_VISION, sourceRoot:donor}});
    mergeSelectedNightmareVisionScriptOwners(names, sources, donor, result, new Map());
    if (result.failed != 0) throw 'copy failures: ' + result.errors;
    var city = Path.join([destination, 'data/stages/city/data.json']);
    if (File.getContent(city) != '{{ "defaultZoom" : 0.73, // authored spacing\\n "hide_girlfriend": true }}')
      throw 'source stage JSON was not preserved byte-for-byte';
    if (File.getContent(Path.join([contentRoot, 'data/stages/city/data.json']))
        != '{{ "defaultZoom" : 0.73, // authored spacing\\n "hide_girlfriend": true }}')
      throw 'stage metadata import modified the donor';
    if (File.getContent(Path.join([destination, 'data/stages/flat.json'])) != '{{"flat":1}}')
      throw 'flat data/stages JSON missing';
    if (File.getContent(Path.join([destination, 'data/stages/nested/id.json'])) != '{{"nested":2}}')
      throw 'nested flat stage id missing';
    if (File.getContent(Path.join([destination, 'stages/fallback/room/data.json'])) != '{{"fallback":3}}')
      throw 'stages directory-form metadata missing';
    if (File.getContent(Path.join([destination, 'stages/root-stage.json'])) != '{{"root":4}}')
      throw 'stages flat metadata missing';
    if (File.getContent(Path.join([destination, 'images/collision.png'])) != 'owner image')
      throw 'selected package image was not kept in its owner layer';
    if (File.getContent(Path.join([destination, '__nmv_core/images/collision.png'])) != 'core image'
        || File.getContent(Path.join([destination, '__nmv_core/images/core-only.png'])) != 'core only')
      throw 'engine core images were not kept in the explicit core layer';
    if (File.getContent(Path.join([destination, 'data/stages/deep/' + [for (i in 0...12) 'd' + i].join('/') + '/data.json'])) != '{{"deep":12}}')
      throw 'deep nested StageData file was omitted';
    if (File.getContent(Path.join([destination, 'data/stages/nope.jsonc'])) != 'ignored JSONC'
        || File.getContent(Path.join([destination, 'stages/ignored.png'])) != 'not JSON')
      throw 'generic package-relative stage assets were not retained';
    if (!compatScriptNamespaceHasExpectedFiles(donor, destination,
      ImportEngine.NIGHTMARE_VISION)) throw 'complete owner failed stage JSON verification';

    // Existing owner edits stay authoritative even when the donor changes.
    File.saveContent(city, 'owner edit');
    File.saveContent(Path.join([contentRoot, 'data/stages/city/data.json']), '{{"donorRevision":2}}');
    mergeSelectedNightmareVisionScriptOwners(names, sources, donor, result, new Map());
    if (File.getContent(city) != 'owner edit')
      throw 'owner stage metadata was overwritten';
    if (result.skipped < 1) throw 'existing owner file was not recorded as skipped';

    var repair = Path.join([destination, 'stages/root-stage.json']);
    FileSystem.deleteFile(repair);
    if (compatScriptNamespaceHasExpectedFiles(donor, destination,
      ImportEngine.NIGHTMARE_VISION)) throw 'missing owner metadata passed repair check';
    mergeSelectedNightmareVisionScriptOwners(names, sources, donor, result, new Map());
    if (!compatScriptNamespaceHasExpectedFiles(donor, destination,
      ImportEngine.NIGHTMARE_VISION)) throw 'missing stage metadata was not repaired';
    if (FileSystem.exists(Path.join(['assets', 'data/stages/flat.json'])))
      throw 'owner stage metadata was flattened into the global assets tree';
  }}
}}
'''


def run_fixture(temp: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (temp / "ImportDirectoryListing.hx").write_text(
        (ROOT / "source/ImportDirectoryListing.hx").read_text()
    )
    (temp / "StageImportFixture.hx").write_text(fixture_source())
    (temp / "ImportEngine.hx").write_text((ROOT / "source/ImportEngine.hx").read_text())
    (temp / "NightmareVisionAssetCollector.hx").write_text(
        (ROOT / "source/NightmareVisionAssetCollector.hx").read_text()
    )
    return subprocess.run(
        [str(ROOT / ".tools/haxe/haxe"), "-cp", str(temp), "--run", "StageImportFixture", *args],
        cwd=temp,
        capture_output=True,
        text=True,
    )


class NightmareVisionStageImportTest(unittest.TestCase):
    def test_owner_stage_json_retention_repair_and_no_flattening(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            donor = temp / "donor/game/content/package"
            content = donor
            core = temp / "donor/game/assets"
            destination = temp / "assets/imported_mods/nightmare-vision-owner"
            deep = content / "data/stages/deep"
            for index in range(12):
                deep /= f"d{index}"
            (content / "data/stages/city").mkdir(parents=True)
            (content / "data/stages/nested").mkdir(parents=True)
            (content / "stages/fallback/room").mkdir(parents=True)
            deep.mkdir(parents=True)
            (content / "stages").mkdir(parents=True, exist_ok=True)
            (content / "data/stages/city/data.json").write_text(
                '{ "defaultZoom" : 0.73, // authored spacing\n "hide_girlfriend": true }'
            )
            (content / "data/stages/flat.json").write_text('{"flat":1}')
            (content / "data/stages/nested/id.json").write_text('{"nested":2}')
            (content / "stages/fallback/room/data.json").write_text('{"fallback":3}')
            (content / "stages/root-stage.json").write_text('{"root":4}')
            (deep / "data.json").write_text('{"deep":12}')
            (content / "data/stages/nope.jsonc").write_text("ignored JSONC")
            (content / "stages/ignored.png").write_bytes(b"not JSON")
            (content / "images").mkdir()
            (content / "images/collision.png").write_bytes(b"owner image")
            (core / "images").mkdir(parents=True)
            (core / "images/collision.png").write_bytes(b"core image")
            (core / "images/core-only.png").write_bytes(b"core only")
            destination.mkdir(parents=True)
            result = run_fixture(temp, str(donor), str(destination))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    if args.preview:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            result = run_fixture(Path(folder), "--collect", str(args.preview))
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)
        print(result.stdout.strip())
    else:
        unittest.main(argv=[__file__])
