"""Owner-scoped retention and repair checks for NMV StageData JSON."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
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
typedef SourceMappedAssetPlan = {{ var failed:Bool; var cancelled:Bool; var diagnostics:Array<String>; }};
typedef PreparedMappedAssetOwner = {{ var sourceRoot:String; var engine:String; var scope:String;
  var destinationRoot:String; var plan:SourceMappedAssetPlan; }};
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
      ?modPlusCharacterIds:Array<String>, ?destinationSubpath:String,
      ?mappedAssetPlan:SourceMappedAssetPlan, ?nightmareVisionScope:String):String
    return selectedNamespace;
  static function mappedOwnerPlan(_plans:Map<String, PreparedMappedAssetOwner>,
      _sourceRoot:String, _engine:String):PreparedMappedAssetOwner return null;
  static function skipMappedOwnerMediaFile(owner:PreparedMappedAssetOwner,
      _source:String, _destination:String):Bool {{
    if (owner != null) throw "stage fixture is only for the profile-unavailable legacy path";
    return false;
  }}
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
    var gameRoot = Path.directory(Path.directory(donor));
    if (NightmareVisionAssetCollector.retentionRoot(donor) != Path.normalize(FileSystem.fullPath(gameRoot)))
      throw 'selected package retention omitted authenticated parent core';
    var untrusted = Path.join([Path.directory(gameRoot), 'untrusted/content/package']);
    FileSystem.createDirectory(untrusted);
    FileSystem.createDirectory(Path.join([Path.directory(Path.directory(untrusted)), 'assets']));
    if (NightmareVisionAssetCollector.retentionRoot(untrusted) != Path.normalize(FileSystem.fullPath(untrusted)))
      throw 'unproven content parent widened retention';
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
    , newline='\n')
    (temp / "ImportRootScanner.hx").write_text(r'''
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
class ImportRootScanner {
  public static function inspectRoot(root:String, _engine:String):{var engine:String; var evidence:Array<String>;} {
    var marker = Path.join([root, 'Project.xml']);
    if (!FileSystem.exists(marker) || !FileSystem.isDirectory(Path.join([root, 'content']))) return null;
    var raw = File.getContent(marker).toLowerCase();
    if (raw.indexOf('com.nmvteam.nightmareengine') < 0) return null;
    return {engine:'Nightmare Vision',
      evidence:['Nightmare Vision Haxe project package: com.nmvTeam.nightmareEngine']};
  }
}''', newline='\n')
    scanner = (ROOT / "source/ImportRootScanner.hx").read_text()
    proof = scanner[scanner.index("public static function hasNightmareVisionContainerProof"):scanner.index("static function hasNightmareVisionExecutable")]
    scanner_stub = temp / "ImportRootScanner.hx"
    scanner_stub.write_text(scanner_stub.read_text().replace("class ImportRootScanner {", "class ImportRootScanner {\n" + proof), newline="\n")
    (temp / "StageImportFixture.hx").write_text(fixture_source(), newline='\n')
    (temp / "ImportEngine.hx").write_text((ROOT / "source/ImportEngine.hx").read_text(), newline='\n')
    (temp / "NightmareVisionAssetCollector.hx").write_text(
        (ROOT / "source/NightmareVisionAssetCollector.hx").read_text()
    , newline='\n')
    return subprocess.run(
        [*HAXE_COMMAND, "-cp", str(temp), "--run", "StageImportFixture", *args],
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
            , newline='\n')
            (content / "data/stages/flat.json").write_text('{"flat":1}', newline='\n')
            (content / "data/stages/nested/id.json").write_text('{"nested":2}', newline='\n')
            (content / "stages/fallback/room/data.json").write_text('{"fallback":3}', newline='\n')
            (content / "stages/root-stage.json").write_text('{"root":4}', newline='\n')
            (deep / "data.json").write_text('{"deep":12}', newline='\n')
            (content / "data/stages/nope.jsonc").write_text("ignored JSONC", newline='\n')
            (content / "stages/ignored.png").write_bytes(b"not JSON")
            (content / "images").mkdir()
            (content / "images/collision.png").write_bytes(b"owner image")
            (core / "images").mkdir(parents=True)
            (core / "images/collision.png").write_bytes(b"core image")
            (core / "images/core-only.png").write_bytes(b"core only")
            (core.parent / "Project.xml").write_text(
                '<project><app package="com.nmvTeam.nightmareEngine" /></project>', newline='\n')
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
