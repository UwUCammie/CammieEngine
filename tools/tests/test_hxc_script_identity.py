from haxe_test_support import HAXE_COMMAND
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def haxe_string(value):
    return json.dumps(value)


class HxcScriptIdentityTests(unittest.TestCase):
    def test_declared_character_identity_cache_and_owner_precedence(self):
        wrong_dir_source = r'''// class Fake extends MultiSparrowCharacter { function new() super('comment-fake'); }
var inert = "class StringFake extends MultiSparrowCharacter { function new() super('string-fake'); }";
class Helper extends Module { function new() { super('helper-id'); } }
class RenamedWrapper extends MultiSparrowCharacter {
  var openText = "{";
  var closeText = "}";
  function new() { super('renamed-id'); }
  function dance() { super.playAnimation('method-id'); }
}'''
        mixed_source = r'''class StageOwner extends Stage {
  function new() { super('mixed-stage-owner'); }
}
class CharacterHelper extends MultiSparrowCharacter {
  function new() { super('wrong-mixed-id'); }
}'''
        stage_source = r'''class DeclaredStage extends Stage {
  function new() { super('canonical-stage'); }
}'''
        misplaced_module_source = r'''class MisplacedModule extends Module {
  function new() { super('not-a-stage'); }
}'''
        multiple_stage_source = r'''class HelperStage extends Stage {
  function new() { super('helper-stage'); }
}
class RequestedStage extends BaseStage {
  function new() { super('declared-stage-id'); }
}'''
        constructor_matched_stage_source = r'''class HelperStage extends Stage {
  function new() { super('helper-stage'); }
}
class WrapperStage extends Stage {
  function new() { super('constructor-matched-stage'); }
}'''
        unmatched_multiple_stage_source = r'''class FirstStage extends Stage {
  function new() { super('first-stage-id'); }
}
class SecondStage extends Stage {
  function new() { super('second-stage-id'); }
}'''
        dynamic_stage_source = r'''class DynamicStage extends Stage {
  function new(stageName) { super(stageName); }
}'''
        owner_source = r'''class LiquidWrapper extends MultiSparrowCharacter {
  function new() { super('liquid'); }
}'''
        dynamic_character_source = r'''class WrapperWithoutLiteralId extends CharacterInfoBase {
  function new(characterInfo) { super(characterInfo); }
}'''
        initial_cache_source = r'''class CacheWrapper extends MultiSparrowCharacter {
  function new() { super('cache-id'); }
}'''
        changed_cache_source = r'''class CacheWrapper extends Stage {
  function new() { super('stage-only-id'); }
  function onCreate() { trace('changed to a longer stage implementation'); }
}'''

        main = f'''import sys.FileSystem;
import sys.io.File;
import haxe.io.Path;

class Main {{
  static function fail(message:String):Void throw message;

  static function ensureDirectory(path:String):Void {{
    if (path == null || path == "" || path == "/" || FileSystem.exists(path)) return;
    var parent = Path.directory(path);
    if (parent != path) ensureDirectory(parent);
    FileSystem.createDirectory(path);
  }}

  static function write(path:String, content:String):Void {{
    ensureDirectory(Path.directory(path));
    File.saveContent(path, content);
  }}

  static function main() {{
    var base = Sys.getCwd() + "/fixtures";
    var renamedPath = base + "/owner/data/stages/UnexpectedName.hxc";
    write(renamedPath, {haxe_string(wrong_dir_source)});
    if (HxcScriptDiscovery.familyForPath(renamedPath) != "character")
      fail("declared character in a stage directory was not classified as character");
            if (HxcScriptDiscovery.characterId(renamedPath) != "renamedid")
              fail("character id did not come from its selected constructor");
            if (!HxcScriptDiscovery.characterMatches(renamedPath, ["renamed-id"]))
              fail("renamed constructor id did not match the requested actor");
            if (HxcScriptDiscovery.stageMatches(renamedPath, ["renamed-id"]))
              fail("a character declaration in a stage directory was accepted as a stage");

            var dynamicCanonicalPath = base + "/owner/scripts/characters/wrapper-without-literal-id.hxc";
            write(dynamicCanonicalPath, {haxe_string(dynamic_character_source)});
            if (HxcScriptDiscovery.familyForPath(dynamicCanonicalPath) != "character"
              || HxcScriptDiscovery.characterId(dynamicCanonicalPath) != "wrapperwithoutliteralid")
              fail("canonical character wrapper without a literal id lost filename identity");

            var dynamicMisplacedPath = base + "/owner/scripts/stages/wrapper-without-literal-id.hxc";
            write(dynamicMisplacedPath, {haxe_string(dynamic_character_source)});
            if (HxcScriptDiscovery.familyForPath(dynamicMisplacedPath) != "character"
              || HxcScriptDiscovery.characterId(dynamicMisplacedPath) != "")
              fail("misplaced character wrapper guessed an id without a literal constructor id");

    var mixedPath = base + "/owner/data/stages/mixed.hxc";
    write(mixedPath, {haxe_string(mixed_source)});
    if (HxcScriptDiscovery.familyForPath(mixedPath) != "stage")
      fail("a declared Stage owner lost precedence to a helper character class");
    if (HxcScriptDiscovery.characterId(mixedPath) != "")
      fail("a helper character constructor was selected from a mixed stage file");
    if (HxcScriptDiscovery.stageId(mixedPath) != "mixedstageowner"
      || !HxcScriptDiscovery.stageMatches(mixedPath, ["mixed-stage-owner"])
      || HxcScriptDiscovery.stageMatches(mixedPath, ["wrong-mixed-id"]))
      fail("mixed-file stage identity did not preserve its declared owner");

    var renamedStagePath = base + "/owner/data/stages/UnexpectedStageName.hxc";
    write(renamedStagePath, {haxe_string(stage_source)});
    if (HxcScriptDiscovery.familyForPath(renamedStagePath) != "stage"
      || HxcScriptDiscovery.stageId(renamedStagePath) != "canonicalstage"
      || !HxcScriptDiscovery.stageMatches(renamedStagePath, ["canonical-stage"])
      || !HxcScriptDiscovery.stageMatches(renamedStagePath, ["UnexpectedStageName"])
      || HxcScriptDiscovery.stageMatches(renamedStagePath, ["unrelated-stage"]))
      fail("renamed Stage file did not match its declared id and filename aliases");

    var multipleStagePath = base + "/owner/scripts/stages/RequestedStage.hxc";
    write(multipleStagePath, {haxe_string(multiple_stage_source)});
    if (HxcScriptDiscovery.stageId(multipleStagePath) != "declaredstageid"
      || !HxcScriptDiscovery.stageMatches(multipleStagePath, ["declared-stage-id"])
      || HxcScriptDiscovery.stageMatches(multipleStagePath, ["helper-stage"]))
      fail("filename-matching Stage declaration did not own its helper file");

    var constructorMatchedStagePath = base + "/owner/scripts/stages/constructor-matched-stage.hxc";
    write(constructorMatchedStagePath, {haxe_string(constructor_matched_stage_source)});
    if (HxcScriptDiscovery.stageId(constructorMatchedStagePath) != "constructormatchedstage"
      || HxcScriptDiscovery.stageMatches(constructorMatchedStagePath, ["helper-stage"]))
      fail("constructor-id-matching Stage declaration did not own its helper file");

    var firstStageFallbackPath = base + "/owner/scripts/stages/no-matching-stage.hxc";
    write(firstStageFallbackPath, {haxe_string(unmatched_multiple_stage_source)});
    if (HxcScriptDiscovery.stageId(firstStageFallbackPath) != "firststageid")
      fail("unmatched multi-Stage file did not fall back to its first Stage");

    var dynamicStagePath = base + "/owner/scripts/stages/dynamic-stage-file.hxc";
    write(dynamicStagePath, {haxe_string(dynamic_stage_source)});
    if (HxcScriptDiscovery.stageId(dynamicStagePath) != "dynamicstagefile"
      || !HxcScriptDiscovery.stageMatches(dynamicStagePath, ["dynamic-stage-file"]))
      fail("nonliteral Stage constructor lost filename fallback");

    var legacyStagePath = base + "/owner/scripts/stages/legacy-stage.hxc";
    write(legacyStagePath, "function onUpdate(event) {{ trace(event); }}");
    if (HxcScriptDiscovery.familyForPath(legacyStagePath) != "stage"
      || HxcScriptDiscovery.stageId(legacyStagePath) != "legacystage"
      || !HxcScriptDiscovery.stageMatches(legacyStagePath, ["legacy-stage"]))
      fail("classless legacy stage did not retain filename fallback");

    var misplacedModuleStagePath = base + "/owner/scripts/stages/misplaced-stage-module.hxc";
    write(misplacedModuleStagePath, {haxe_string(misplaced_module_source)});
    if (HxcScriptDiscovery.familyForPath(misplacedModuleStagePath) != "module"
      || HxcScriptDiscovery.stageId(misplacedModuleStagePath) != ""
      || HxcScriptDiscovery.stageMatches(misplacedModuleStagePath, ["misplaced-stage-module"])
      || HxcScriptDiscovery.stageMatches(misplacedModuleStagePath, ["not-a-stage"]))
      fail("recognized Module declaration in a stage directory was accepted as a stage");

    var legacyPath = base + "/owner/scripts/characters/legacy-alias.hxc";
    write(legacyPath, "function onUpdate(event) {{ trace(event); }}");
    if (HxcScriptDiscovery.familyForPath(legacyPath) != "character"
      || HxcScriptDiscovery.characterId(legacyPath) != "legacyalias")
      fail("classless legacy character did not retain filename fallback");

    var ownerA = base + "/owner-a";
    var ownerB = base + "/owner-b";
    var ownerAPath = ownerA + "/scripts/stages/LiquidInstructions.hxc";
    var ownerBPath = ownerB + "/scripts/characters/liquid.hxc";
    write(ownerAPath, {haxe_string(owner_source)});
    write(ownerBPath, {haxe_string(owner_source)});
    var roots = ["assets/scripts", ownerA, ownerB];
    var selected = HxcScriptDiscovery.selectCharacterPaths(
      [ownerBPath, ownerAPath], ["liquid"], roots, ownerA);
    if (selected.length != 1 || selected[0] != ownerAPath)
      fail("selected manifest owner lost precedence for a constructor-derived id");

    var cachePath = base + "/owner/data/stages/cache.hxc";
    write(cachePath, {haxe_string(initial_cache_source)});
    if (HxcScriptDiscovery.familyForPath(cachePath) != "character"
      || HxcScriptDiscovery.characterId(cachePath) != "cacheid")
      fail("initial cached identity was not read");
    write(cachePath, {haxe_string(changed_cache_source)});
    if (HxcScriptDiscovery.familyForPath(cachePath) != "stage"
      || HxcScriptDiscovery.characterId(cachePath) != ""
      || HxcScriptDiscovery.stageId(cachePath) != "stageonlyid"
      || !HxcScriptDiscovery.stageMatches(cachePath, ["stage-only-id"])
      || HxcScriptDiscovery.stageMatches(cachePath, ["cache-id"]))
      fail("changed size/mtime did not invalidate source identity");

    if (HxcScriptDiscovery.familyForPath("fictional/scripts/stages/no-file.hxc") != "stage"
      || HxcScriptDiscovery.characterId("fictional/scripts/characters/bf-fixture.hxc") != "bffixture")
      fail("nonexistent fixture paths changed their path-only result");
  }}
}}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp), "--run", "Main"],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
