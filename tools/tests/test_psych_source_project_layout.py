"""Psych source projects expose their mapped base-game and shared asset roots."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
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
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychSourceProjectLayoutTest(unittest.TestCase):
    def test_full_project_resolves_base_game_and_retains_separate_shared_root(self):
        scanner = (ROOT / "source/ImportRootScanner.hx").read_text()
        engine = (ROOT / "source/ImportEngine.hx").read_text()
        module_functions = (ROOT / "source/ModuleFunctions.hx").read_text()
        selected_roots = extract_method(
            module_functions,
            "static function selectedAssetRootsForEngineRoot",
        )
        path_key = extract_method(module_functions, "static function importPathKey")
        merge_methods = "\n".join(
            extract_method(module_functions, marker)
            for marker in (
                "static function importPathIsWithin",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function compatScriptTreeNames",
                "static function validImportEntryName",
                "static function mergeTreeNonOverwriting",
                "static function copyImportFileNonOverwriting",
                "static function mergeMappedAssetRoot",
            )
        )
        fixture = r'''import sys.FileSystem;
import sys.io.File;
class Main {
  static function main():Void {
    var project = Sys.args()[0];
    var root = ImportRootScanner.inspectRoot(project);
    if (root == null) throw "Psych source project not discovered";
    if (root.engine != ImportEngine.PSYCH) throw "wrong engine: " + root.engine;
    var base = project + "/assets/base_game";
    var shared = project + "/assets/shared";
    if (root.root != project) throw "owner provenance moved off the project root";
    if (root.contentRoot != base) throw "base-game mapping unresolved: " + root.contentRoot;
    if (root.data != base + "/shared/data") throw "chart root unresolved: " + root.data;
    if (root.audio != base + "/songs") throw "song audio root unresolved: " + root.audio;
    if (root.images != base + "/shared/images") throw "visual root unresolved: " + root.images;
    if (root.shared != base + "/shared") throw "base-game shared root unresolved: " + root.shared;
    if (root.supplementalAssetRoots == null || root.supplementalAssetRoots.length != 1
        || root.supplementalAssetRoots[0].path != shared
        || root.supplementalAssetRoots[0].destinationPrefix != "shared")
      throw "separate project shared mapping missing";
    if (root.paths.supplementalAssetRoots == null
        || root.paths.supplementalAssetRoots[0].path != shared)
      throw "path descriptor lost separate project shared mapping";
    if (root.evidence.indexOf("Psych Engine Haxe source project: Project.xml + source/psychlua/*.hx") < 0)
      throw "Psych source evidence missing";
    root.supplementalAssetRoots.push({path:base, destinationPrefix:"shared"});
    var selected = ModuleFunctions.selected(root);
    if (selected.length != 2 || selected[0].path != base || selected[0].destinationPrefix != ""
        || selected[1].path != shared || selected[1].destinationPrefix != "shared")
      throw "importer asset roots lost order or duplicate filtering";
    FileSystem.createDirectory("assets");
    FileSystem.createDirectory("assets/shared");
    FileSystem.createDirectory("assets/shared/images");
    File.saveContent("assets/shared/images/conflict.png", "existing-owner");
    var merged = ModuleFunctions.map(shared, "shared", project, root.engine);
    if (merged.failed != 0 || merged.skipped != 1)
      throw "mapped shared import counters: " + merged.copied + "/" + merged.skipped + "/" + merged.failed;
    if (File.getContent("assets/shared/images/conflict.png") != "existing-owner")
      throw "mapped shared import replaced an existing owner";
    if (File.getContent("assets/shared/images/extra.png") != "supplemental")
      throw "mapped shared image was not copied under its logical prefix";
    if (File.getContent("assets/shared/data/characterList.txt") != "characters")
      throw "mapped shared data was not retained under its logical prefix";
    if (FileSystem.exists("assets/shared/stages/default.lua"))
      throw "mapped shared stage Lua escaped its owner namespace";
    if (ModuleFunctions.lastOwnerRoot != project || ModuleFunctions.lastEngine != ImportEngine.PSYCH)
      throw "mapped script root lost project owner provenance";
    var roots = ImportRootScanner.scan(project);
    if (roots.length != 1 || roots[0].root != project || roots[0].engine != ImportEngine.PSYCH)
      throw "project/base_game was reported as duplicate import roots: " + roots.length;
    trace("ROOT|" + root.engine + "|" + root.root + "|DATA=" + root.data
      + "|AUDIO=" + root.audio + "|EXTRA=" + root.supplementalAssetRoots[0].path);
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "ImportEngine.hx").write_text(engine, newline='\n')
            (work / "ImportRootScanner.hx").write_text(scanner, newline='\n')
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            (work / "PsychSongNameCompat.hx").write_text(
                (ROOT / "source/PsychSongNameCompat.hx").read_text()
            , newline='\n')
            (work / "ImportSettings.hx").write_text(r'''import haxe.io.Path;
using StringTools;
class ImportSettings {
  public static function normalizeSourcePath(path:String):String
    return path == null ? "" : Path.normalize(StringTools.replace(StringTools.trim(path), "\\", "/"));
}
''', newline='\n')
            (work / "ModuleFunctions.hx").write_text(
                """import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
typedef ImportAssetMergeResult = { var copied:Int; var skipped:Int; var failed:Int; @:optional var errors:Array<String>; };
typedef SourceMappedAssetPlan = { var failed:Bool; var cancelled:Bool; var diagnostics:Array<String>; };
typedef PreparedMappedAssetOwner = { var sourceRoot:String; var engine:String; var scope:String;
  var destinationRoot:String; var plan:SourceMappedAssetPlan; };
class ModuleFunctions {
  public static var lastOwnerRoot:String = "";
  public static var lastEngine:String = "";
""" + path_key + "\n" + selected_roots + "\n" + merge_methods + r'''
  static function importWorkCancelled():Bool return false;
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0,
      copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {}
  static function mergeCompatScriptTrees(sourceRoot:String, scriptSourceRoot:String, engine:String,
      result:ImportAssetMergeResult, ?skipPaths:Map<String, Bool>,
      ?modPlusCharacterIds:Array<String>, ?destinationSubpath:String,
      ?mappedAssetPlan:SourceMappedAssetPlan, ?nightmareVisionScope:String):String {
    lastOwnerRoot = scriptSourceRoot;
    lastEngine = engine;
    return scriptSourceRoot;
  }
  static function skipMappedGlobalFile(owner:PreparedMappedAssetOwner,
      _source:String, _destination:String):Bool {
    if (owner != null) throw "source-layout fixture is only for the profile-unavailable legacy path";
    return false;
  }
  static function skipMappedRawFile(owner:PreparedMappedAssetOwner,
      _source:String, _destination:String):Bool {
    if (owner != null) throw "source-layout fixture is only for the profile-unavailable legacy path";
    return false;
  }
  public static function selected(root:ImportRootScanner.ImportRoot):Array<ImportRootScanner.ImportRootAssetSource>
    return selectedAssetRootsForEngineRoot(root);
  public static function map(source:String, prefix:String, owner:String, engine:String):ImportAssetMergeResult
    return mergeMappedAssetRoot(source, prefix, owner, engine);
}
''', newline='\n')
            (work / "Main.hx").write_text(fixture, newline='\n')

            project = work / "psych-source"
            project.mkdir()
            (project / "Project.xml").write_text(
                '<project><assets path="assets/base_game" rename="assets" />'
                '<assets path="assets/shared" /></project>'
            , newline='\n')
            (project / "source/psychlua").mkdir(parents=True)
            (project / "source/psychlua/PsychLua.hx").write_text("class PsychLua {}", newline='\n')
            (project / "assets/base_game/shared/data/demo").mkdir(parents=True)
            (project / "assets/base_game/shared/images").mkdir(parents=True)
            (project / "assets/base_game/shared/characters").mkdir(parents=True)
            (project / "assets/base_game/shared/stages").mkdir(parents=True)
            (project / "assets/base_game/songs/demo").mkdir(parents=True)
            (project / "assets/shared/images").mkdir(parents=True)
            (project / "assets/shared/data").mkdir()
            (project / "assets/shared/stages").mkdir()
            (project / "assets/shared/images/conflict.png").write_text("supplemental", newline='\n')
            (project / "assets/shared/images/extra.png").write_text("supplemental", newline='\n')
            (project / "assets/shared/data/characterList.txt").write_text("characters", newline='\n')
            (project / "assets/shared/stages/default.lua").write_text("function onCreate() end", newline='\n')

            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main", str(project)],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ROOT|Psych Engine|", result.stdout)
        self.assertIn("|DATA=" + str(project / "assets/base_game/shared/data"), result.stdout)
        self.assertIn("|AUDIO=" + str(project / "assets/base_game/songs"), result.stdout)
        self.assertIn("|EXTRA=" + str(project / "assets/shared"), result.stdout)
        importer = (ROOT / "source/ModuleFunctions.hx").read_text()
        normalized_importer = " ".join(importer.split())
        self.assertIn("selectedAssetRootsForEngineRoot(engineRoot)", importer)
        self.assertIn("mergePsychRuntimeSounds(psychSourceRoot, ownerRuntimeRoot, ownerPlan);",
                      normalized_importer)
        self.assertIn("importPsychCharacters(supplemental", importer)


if __name__ == "__main__":
    unittest.main()
