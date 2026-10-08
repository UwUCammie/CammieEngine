"""Filesystem integration coverage for per-source foreign script isolation."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]


def install_directory_listing_helper(folder: str | Path) -> None:
    helper = ROOT / "source/ImportDirectoryListing.hx"
    (Path(folder) / helper.name).write_text(helper.read_text(), newline='\n')


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


class CompatScriptImportTest(unittest.TestCase):
    def test_script_trees_are_copied_below_the_manifest_namespace(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function destinationAssetsPath",
                "static function validImportEntryName",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function findChildDirectory",
                "static function mergeTreeNonOverwriting",
                "static function mergeHxcScriptTree",
                "static function nightmareVisionScriptSuffixes",
                "static function collectNightmareVisionScriptDirectory",
                "static function collectNightmareVisionScriptFilesImmediate",
                "static function collectNightmareVisionSongScripts",
                "static function collectNightmareVisionScriptFiles(",
                "static function copyImportFileNonOverwriting",
                "static function writeImportContentNonOverwriting",
                "static function normalizedImportFileName",
                "static function findImportFile",
                "static function isImportFile",
                "static function validModuleName",
                "static function readImportJson",
                "static function mergeModPlusCharacterAssets",
                "static function compatScriptTreeNames",
                "static function mergePsychLanguageDataScopes",
                "static function mergePsychLanguageFiles",
                "static function mergeCompatScriptTrees",
            )
        )
        manifest = (ROOT / "source/CompatScriptManifest.hx").read_text()
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import CompatScriptManifest.CompatScriptManifestData;
using StringTools;

typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int;
  @:optional var errors:Array<String>; }};
typedef SourceMappedAssetPlan = {{ var diagnostics:Array<String>; var cancelled:Bool;
  var failed:Bool; }};
typedef SourceMappedAssetPolicyView = {{ var diagnostics:Array<String>; var cancelled:Bool;
  var failed:Bool; var legacyAllowed:Bool; var blockAllLegacy:Bool; }};
typedef PreparedMappedAssetOwner = {{ var sourceRoot:String; var engine:String; var scope:String;
  var destinationRoot:String; var plan:SourceMappedAssetPlan; }};
typedef PsychLanguagePublicationPlan = {{ var diagnostics:Array<String>; var cancelled:Bool;
  var failed:Bool; var legacyAllowed:Bool; var blockAllLegacy:Bool; }};
class PsychLanguagePublisher {{
  public static function prepare(_source:String, _engine:String, _destination:String,
      ?_cancelled:Void->Bool):PsychLanguagePublicationPlan
    return {{diagnostics:[], cancelled:false, failed:false, legacyAllowed:true, blockAllLegacy:false}};
  public static function publish(_plan:PsychLanguagePublicationPlan,
      _copy:String->String->Void, ?_cancelled:Void->Bool):Void {{}}
  public static function skipLegacy(_plan:PsychLanguagePublicationPlan,
      _source:String, _destination:String):Bool return false;
}}
class SourceMappedMediaPublisher {{
  public static function prepare(_source:String, _engine:String, _destination:String,
      ?_scope:String, ?_cancelled:Void->Bool):SourceMappedAssetPlan
    return {{diagnostics:[], cancelled:false, failed:false}};
  public static function publish(_plan:SourceMappedAssetPlan,
      _copy:String->String->Void, ?_cancelled:Void->Bool,
      ?_writeText:String->String->Void):Void {{}}
  public static function languageView(_plan:SourceMappedAssetPlan):SourceMappedAssetPolicyView
    return {{diagnostics:[], cancelled:false, failed:false, legacyAllowed:true, blockAllLegacy:false}};
  public static function policyView(_plan:SourceMappedAssetPlan, _label:String):SourceMappedAssetPolicyView
    return languageView(_plan);
  public static function mediaLabel(_engine:String, _scope:String):String return '';
  public static function mediaPolicy(_engine:String, _scope:String):Dynamic return null;
  public static function skipLegacyOwner(_view:SourceMappedAssetPolicyView,
      _source:String, _destination:String):Bool return false;
}}
class ImportSettings {{
  public static function normalizeSourcePath(path:Dynamic):String
    return Path.normalize(Std.string(path));
}}
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return haxe.Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return haxe.Json.stringify(value);
}}
class CopyFixture {{
  static function importWorkCancelled():Bool return false;
  static function reportImportProgress(phase:String, current:String, completed:Int = 0,
      total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
{methods}
  static function main() {{
    var source = Sys.args()[0];
    var result:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0}};
    var destination = mergeCompatScriptTrees(source, source, 'Psych Engine', result);
    if (File.getContent(Path.join([destination, 'pack.json'])) != '{{"name":"Source Pack"}}')
      throw 'owned package metadata missing';
    if (!FileSystem.exists(Path.join([destination, 'scripts', 'global.lua']))) throw 'global script missing';
    if (!FileSystem.exists(Path.join([destination, 'epicScripts', 'first.lua']))
      || !FileSystem.exists(Path.join([destination, 'epicScripts', 'second.lua'])))
      throw 'literal Lua dependencies missing from namespace';
    if (!FileSystem.exists(Path.join([destination, 'stages', 'facility.json']))) throw 'stage metadata missing';
    if (!FileSystem.exists(Path.join([destination, 'shared', 'scripts', 'shared.lua']))) throw 'shared script missing';
    if (!FileSystem.exists(Path.join([destination, 'scripts', 'characters', 'vampire.hxc']))) throw 'HXC family missing';
    if (File.getContent(Path.join([destination, 'data', 'notestyles', 'fixture.json'])) != 'style metadata') throw 'scoped style metadata missing';
    if (File.getContent(Path.join([destination, 'data', 'package-lines.txt'])) != 'owned sidecar')
      throw 'root-level data sidecar missing from owner';
    if (FileSystem.exists(Path.join(['assets', 'data', 'package-lines.txt'])))
      throw 'root-level data sidecar flattened';
    File.saveContent(Path.join([source, 'data', 'package-lines.txt']), 'new donor revision');
    File.saveContent(Path.join([source, 'pack.json']), '{{"name":"Changed Donor"}}');
    mergeCompatScriptTrees(source, source, 'Psych Engine', result);
    if (File.getContent(Path.join([destination, 'pack.json'])) != '{{"name":"Source Pack"}}')
      throw 'owned package metadata overwritten';
    if (File.getContent(Path.join([destination, 'data', 'package-lines.txt'])) != 'owned sidecar')
      throw 'existing owner sidecar overwritten';
    if (FileSystem.exists(Path.join(['assets', 'data', 'notestyles', 'fixture.json']))) throw 'style metadata flattened';
    if (FileSystem.exists(Path.join(['assets', 'scripts', 'global.lua']))) throw 'foreign script flattened';
    if (FileSystem.exists(Path.join(['assets', 'epicScripts', 'first.lua'])))
      throw 'Lua dependency flattened';
    // Packaged Psych releases put their content root under assets/. Keep the
    // stage JSON beside the same owner namespace so PlayState can apply its
    // camera/start metadata after import.
    var packagedDestination = mergeCompatScriptTrees(Path.join([source, 'assets']), source,
      'Psych Engine', result);
    if (packagedDestination != destination
        || !FileSystem.exists(Path.join([destination, 'stages', 'packaged-stage.json'])))
      throw 'packaged assets/stages metadata was not retained under the owner';
    if (!FileSystem.exists(Path.join([destination, 'shared', 'stages', 'shared-stage.json'])))
      throw 'packaged assets/shared/stages metadata was not retained under the owner';
    if (FileSystem.exists(Path.join([destination, 'assets', 'stages', 'packaged-stage.json'])))
      throw 'packaged stage metadata retained the source assets prefix';
    var rootLanguage = Path.join([destination, 'data', 'en-US.lang']);
    if (File.getContent(rootLanguage) != 'English (US)\\r\\nhello: "Root"\\r\\n')
      throw 'root data language bytes were not retained exactly';
    if (File.getContent(Path.join([destination, 'data', 'languages', 'fr-FR.LANG']))
        != 'Francais\\nhello: "Nested"\\n')
      throw 'nested language file or case-insensitive extension was not retained';
    if (File.getContent(Path.join([destination, 'shared', 'data', 'en-US.lang']))
        != 'English (US)\\nhello: "Shared"\\n')
      throw 'shared-library language was flattened or omitted';
    if (File.getContent(Path.join([destination, 'week1', 'data', 'en-US.lang']))
        != 'English (US)\\nhello: "Current level"\\n')
      throw 'current-level language was not preserved in its library';
    if (File.getContent(Path.join([destination, 'base_game', 'week1', 'data', 'en-US.lang']))
        != 'English (US)\\nhello: "Base game level"\\n')
      throw 'base-game library language was not preserved';
    if (File.getContent(Path.join([destination, 'library', 'alternate', 'data', 'en-US.lang']))
        != 'English (US)\\nhello: "Named library"\\n')
      throw 'named library language was not preserved';
    if (FileSystem.exists(Path.join([destination, 'mods', 'untrusted', 'data', 'en-US.lang']))
        || FileSystem.exists(Path.join([destination, 'week1', 'data', 'languages', 'ignored.json'])))
      throw 'unrelated mods or non-language data was copied';
    File.saveContent(rootLanguage, 'user-owned language override');
    mergeCompatScriptTrees(Path.join([source, 'assets']), source, 'Psych Engine', result);
    if (File.getContent(rootLanguage) != 'user-owned language override')
      throw 'reimport replaced an existing owner language file';
    var modPlusRoot = Sys.args()[1];
    var modPlus = mergeCompatScriptTrees(modPlusRoot, modPlusRoot, 'Modding Plus', result);
    if (!FileSystem.exists(Path.join([modPlus, 'images', 'custom_stages', 'custom_stages.json'])))
      throw 'donor stage registry missing from its namespace';
    if (File.getContent(Path.join([modPlus, 'images', 'custom_stages', 'tank.hscript'])) != 'donor tank')
      throw 'colliding donor stage script was not preserved';
    if (File.getContent(Path.join([modPlus, 'images', 'custom_stages', 'tank2', 'sky.png'])) != 'donor sky')
      throw 'stage hscriptPath assets were not preserved';
    if (File.getContent(Path.join(['assets', 'images', 'custom_stages', 'tank.hscript'])) != 'native tank')
      throw 'the donor overwrote a native stage script';
    if (File.getContent(Path.join([modPlus, 'images', 'custom_cutscenes', 'cutscenes.json']))
        != '{{"monster":"owned-monster"}}') throw 'donor cutscene registry missing';
    if (File.getContent(Path.join([modPlus, 'images', 'custom_cutscenes', 'owned-monster.hscript']))
        != 'donor monster') throw 'colliding donor cutscene missing';
    if (File.getContent(Path.join([modPlus, 'images', 'custom_cutscenes', 'monster', 'room.png']))
        != 'donor room') throw 'cutscene relative media missing';
    if (File.getContent(Path.join(['assets', 'images', 'custom_cutscenes', 'monster.hscript']))
        != 'native monster') throw 'donor overwrote native cutscene';
    trace(destination + '|' + result.copied);
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            install_directory_listing_helper(temp)
            (temp / "CompatScriptManifest.hx").write_text(manifest, newline='\n')
            (temp / "ImportSongOwnership.hx").write_text((ROOT / "source/ImportSongOwnership.hx").read_text(), newline='\n')
            for helper in ("CodenameScriptPlan", "CodenameScriptDiscovery", "CodenameEventPack", "CodenameStagePlacement", "CodenameStrumlineLayout"):
                (temp / (helper + ".hx")).write_text((ROOT / "source" / (helper + ".hx")).read_text(), newline='\n')
            (temp / "ImportEngine.hx").write_text((ROOT / "source/ImportEngine.hx").read_text(), newline='\n')
            (temp / "PsychLuaScriptDependencies.hx").write_text(
                (ROOT / "source/PsychLuaScriptDependencies.hx").read_text(), newline='\n')
            (temp / "CopyFixture.hx").write_text(fixture, newline='\n')
            donor = temp / "donor"
            donor.mkdir()
            (donor / "pack.json").write_text('{"name":"Source Pack"}', newline='\n')
            (donor / "scripts").mkdir(parents=True)
            (donor / "scripts/global.lua").write_text("addLuaScript('epicScripts/first')", newline='\n')
            (donor / "epicScripts").mkdir()
            (donor / "epicScripts/first.lua").write_text("addLuaScript('epicScripts/second')", newline='\n')
            (donor / "epicScripts/second.lua").write_text("function onUpdate() end", newline='\n')
            (donor / "stages").mkdir()
            (donor / "stages/facility.json").write_text("{}", newline='\n')
            (donor / "stages/facility.lua").write_text("function onCreate() end", newline='\n')
            (donor / "assets/stages").mkdir(parents=True)
            (donor / "assets/stages/packaged-stage.json").write_text('{"defaultZoom":0.73}', newline='\n')
            (donor / "assets/shared/stages").mkdir(parents=True)
            (donor / "assets/shared/stages/shared-stage.json").write_text('{"defaultZoom":0.81}', newline='\n')
            language_bytes = {
                "assets/data/en-US.lang": b'English (US)\r\nhello: "Root"\r\n',
                "assets/data/languages/fr-FR.LANG": b'Francais\nhello: "Nested"\n',
                "assets/shared/data/en-US.lang": b'English (US)\nhello: "Shared"\n',
                "assets/week1/data/en-US.lang": b'English (US)\nhello: "Current level"\n',
                "assets/base_game/week1/data/en-US.lang": b'English (US)\nhello: "Base game level"\n',
                "assets/library/alternate/data/en-US.lang": b'English (US)\nhello: "Named library"\n',
                "assets/mods/untrusted/data/en-US.lang": b'English (US)\nhello: "Untrusted"\n',
            }
            for relative, contents in language_bytes.items():
                path = donor / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
            (donor / "assets/week1/data/languages").mkdir(parents=True)
            (donor / "assets/week1/data/languages/ignored.json").write_text('{"ignored":true}', newline='\n')
            (donor / "shared/scripts").mkdir(parents=True)
            (donor / "shared/scripts/shared.lua").write_text("function onUpdate() end", newline='\n')
            (donor / "data/characters").mkdir(parents=True)
            (donor / "data/characters/vampire.hxc").write_text("class Vampire {}", newline='\n')
            (donor / "data/notestyles").mkdir(parents=True)
            (donor / "data/notestyles/fixture.json").write_text("style metadata", newline='\n')
            (donor / "data/package-lines.txt").write_text("owned sidecar", newline='\n')
            (temp / "assets").mkdir()
            mod_plus = temp / "mod-plus"
            (mod_plus / "images/custom_stages/tank2").mkdir(parents=True)
            (mod_plus / "images/custom_stages/custom_stages.json").write_text('{"tank2":"tank"}', newline='\n')
            (mod_plus / "images/custom_stages/tank.hscript").write_text("donor tank", newline='\n')
            (mod_plus / "images/custom_stages/tank2/sky.png").write_text("donor sky", newline='\n')
            (mod_plus / "images/custom_cutscenes/monster").mkdir(parents=True)
            (mod_plus / "images/custom_cutscenes/cutscenes.json").write_text('{"monster":"owned-monster"}', newline='\n')
            (mod_plus / "images/custom_cutscenes/owned-monster.hscript").write_text("donor monster", newline='\n')
            (mod_plus / "images/custom_cutscenes/monster/room.png").write_text("donor room", newline='\n')
            (temp / "assets/images/custom_stages").mkdir(parents=True)
            (temp / "assets/images/custom_stages/tank.hscript").write_text("native tank", newline='\n')
            (temp / "assets/images/custom_cutscenes").mkdir(parents=True)
            (temp / "assets/images/custom_cutscenes/monster.hscript").write_text("native monster", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "CopyFixture", str(donor), str(mod_plus)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
            for relative, contents in language_bytes.items():
                self.assertEqual((donor / relative).read_bytes(), contents, relative)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("assets/imported_mods/psych-engine-donor-", result.stdout + result.stderr)

    def test_repair_accepts_existing_nonempty_instrumental_when_donor_is_gone(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function isImportFile",
                "static function validImportPath",
                "static function validModuleName",
                "static function importSongFolderName",
                "static function existingImportChild",
                "static function hasMaterializedFile",
                "static function hasExistingSongInstrumental",
                "static public function validateSongImport",
                "static function readSongChart",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef SongImport = {{
  var name:String;
  var inst:String;
  @:optional var sourceFolder:String;
  @:optional var convertedCharts:Array<Dynamic>;
  var diffFiles:Array<String>;
}};
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
}}
class RepairFixture {{
{methods}
  static function main() {{
    var chart = Path.join([Sys.getCwd(), 'donor', 'repair-key.json']);
    var song:SongImport = {{name:'Repair Song', inst:null, sourceFolder:'Repair-Key',
      convertedCharts:null, diffFiles:[chart]}};
    var accepted = validateSongImport(song);
    if (accepted != null) throw 'existing nonempty destination audio was not accepted: ' + accepted;

    var destination = Path.join([Sys.getCwd(), 'assets', 'songs', 'Repair-Key', 'Inst.ogg']);
    File.saveContent(destination, '');
    var rejected = validateSongImport(song);
    if (rejected != 'The song is missing Inst.ogg.')
      throw 'zero-byte destination audio was accepted: ' + rejected;
    FileSystem.deleteFile(destination);
    var missing = validateSongImport(song);
    if (missing != 'The song is missing Inst.ogg.')
      throw 'missing destination audio was accepted: ' + missing;
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            install_directory_listing_helper(temp)
            (temp / "RepairFixture.hx").write_text(fixture, newline='\n')
            (temp / "assets/songs/Repair-Key").mkdir(parents=True)
            (temp / "assets/songs/Repair-Key/Inst.ogg").write_bytes(b"existing-audio")
            (temp / "donor").mkdir()
            (temp / "donor/repair-key.json").write_text(
                '{"song":{"song":"repair-key","player1":"bf","player2":"dad","notes":[]}}'
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RepairFixture"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_repair_rechecks_manifest_namespace_after_interrupted_script_copy(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function isImportFile",
                "static function validModuleName",
                "static function existingImportChild",
                "static function findChildDirectory",
                "static function validImportEntryName",
                "static function compatScriptTreeNames",
                "static function hasCompatScriptFile",
                "static function collectCompatScriptFiles",
                "static function nightmareVisionScriptSuffixes",
                "static function collectNightmareVisionScriptDirectory",
                "static function collectNightmareVisionScriptFilesImmediate",
                "static function collectNightmareVisionSongScripts",
                "static function collectNightmareVisionScriptFiles(",
                "static function collectNightmareVisionStageDataFiles",
                "static function compatScriptNamespaceHasExpectedFiles",
                "static function importSongFolderName",
                "static function compatScriptManifestPath",
                "static function sourceHasCompatScriptTree",
                "static function compatScriptManifestNeedsRepair",
            )
        )
        manifest = (ROOT / "source/CompatScriptManifest.hx").read_text()
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import CompatScriptManifest.CompatScriptManifestData;
using StringTools;

typedef SongImport = {{
  var name:String;
  @:optional var sourceFolder:String;
  @:optional var engine:String;
  @:optional var sourceRoot:String;
}};
class RepairFixture {{
{methods}
  static function importPathKey(path:String):String return Path.normalize(path);
  static function importPathIsWithin(_path:String, _root:String):Bool return true;
  static function importWorkCancelled():Bool return false;
  static function codenameRuntimeFiles(_song:SongImport):Array<{{source:String, relative:String, ?content:String, ?family:String}}> return [];
  static function mkdir(path:String):Void {{
    if (path == null || path == '' || FileSystem.exists(path)) return;
    var parent = Path.directory(path);
    if (parent != path) mkdir(parent);
    FileSystem.createDirectory(path);
  }}
  static function main() {{
    var donor = Sys.args()[0];
    var song:SongImport = {{name:'Repair', sourceFolder:'repair', engine:'Psych Engine', sourceRoot:donor}};
    var destination = CompatScriptManifest.destinationRoot(donor, song.engine);
    mkdir(Path.join([destination, 'scripts']));
    File.saveContent(Path.join([destination, 'scripts', 'global.lua']), "addLuaScript('epicScripts/first')");
    File.saveContent(Path.join([destination, 'scripts', 'second.lua']), 'function onUpdate() end');
    mkdir(Path.join([destination, 'epicScripts']));
    File.saveContent(Path.join([destination, 'epicScripts', 'first.lua']), 'function onUpdate() end');
    mkdir(Path.join(['assets', 'data', 'repair']));
    File.saveContent(Path.join(['assets', 'data', 'repair', 'compatScripts.json']),
      CompatScriptManifest.stringify(CompatScriptManifest.create(donor, song.engine)));
    mkdir(Path.join([destination, 'data', 'notestyles']));
    File.saveContent(Path.join([destination, 'data', 'notestyles', 'fixture.json']), 'style metadata');
    if (compatScriptManifestNeedsRepair(song)) throw 'complete manifest namespace requested repair';
    FileSystem.deleteFile(Path.join([destination, 'data', 'notestyles', 'fixture.json']));
    if (!compatScriptManifestNeedsRepair(song)) throw 'missing scoped style metadata was treated as complete';
    File.saveContent(Path.join([destination, 'data', 'notestyles', 'fixture.json']), 'style metadata');

    FileSystem.deleteFile(Path.join([destination, 'epicScripts', 'first.lua']));
    if (!compatScriptManifestNeedsRepair(song)) throw 'missing literal Lua dependency was treated as complete';
    File.saveContent(Path.join([destination, 'epicScripts', 'first.lua']), 'function onUpdate() end');

    FileSystem.deleteFile(Path.join([destination, 'scripts', 'second.lua']));
    if (!compatScriptManifestNeedsRepair(song)) throw 'partial namespace was treated as complete';

    var loose = donor + '-loose';
    var looseDestination = 'assets/imported_mods/loose-stage';
    mkdir(loose + '/images/custom_stages');
    mkdir(looseDestination + '/images/custom_stages');
    File.saveContent(loose + '/images/custom_stages/room.hscript', 'function start() {{}}');
    File.saveContent(looseDestination + '/images/custom_stages/room.hscript', 'function start() {{}}');
    if (!compatScriptNamespaceHasExpectedFiles(loose, looseDestination, 'Modding Plus'))
      throw 'registry-less complete stage repeatedly requested repair';
    File.saveContent(loose + '/images/custom_stages/custom_stages.jsonc', '{{}}');
    if (compatScriptNamespaceHasExpectedFiles(loose, looseDestination, 'Modding Plus'))
      throw 'supplied JSONC registry omitted';
    File.saveContent(looseDestination + '/images/custom_stages/custom_stages.jsonc', '{{}}');
    if (!compatScriptNamespaceHasExpectedFiles(loose, looseDestination, 'Modding Plus'))
      throw 'copied JSONC registry not accepted';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            install_directory_listing_helper(temp)
            (temp / "CompatScriptManifest.hx").write_text(manifest, newline='\n')
            (temp / "ImportSongOwnership.hx").write_text((ROOT / "source/ImportSongOwnership.hx").read_text(), newline='\n')
            for helper in ("CodenameScriptPlan", "CodenameScriptDiscovery", "CodenameEventPack", "CodenameStagePlacement", "CodenameModCatalog", "CodenameStrumlineLayout"):
                (temp / (helper + ".hx")).write_text((ROOT / "source" / (helper + ".hx")).read_text(), newline='\n')
            (temp / "ImportEngine.hx").write_text((ROOT / "source/ImportEngine.hx").read_text(), newline='\n')
            (temp / "PsychLuaScriptDependencies.hx").write_text(
                (ROOT / "source/PsychLuaScriptDependencies.hx").read_text(), newline='\n')
            (temp / "RepairFixture.hx").write_text(fixture, newline='\n')
            donor = temp / "donor"
            (donor / "scripts").mkdir(parents=True)
            # An entry rejected by the destination path policy must be skipped;
            # it must not stop verification of later, valid executable files.
            (donor / "scripts/00:invalid.lua").write_text("function ignored() end", newline='\n')
            (donor / "scripts/global.lua").write_text("addLuaScript('epicScripts/first')", newline='\n')
            (donor / "scripts/second.lua").write_text("function onUpdate() end", newline='\n')
            (donor / "epicScripts").mkdir()
            (donor / "epicScripts/first.lua").write_text("function onUpdate() end", newline='\n')
            (donor / "data/notestyles").mkdir(parents=True)
            (donor / "data/notestyles/fixture.json").write_text("style metadata", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RepairFixture", str(donor)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_hxc_asset_lookup_resolves_mixed_case_nested_directories(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function normalizedImportFileName",
                "static function isImportFile",
                "static function findImportFile",
                "static function findChildDirectory",
                "static function findVSliceHxcAssetByBasename",
                "static function findVSliceHxcAsset(sourceRoot",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class LookupFixture {{
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var found = findVSliceHxcAsset(root, 'stage/tb/teto_idle', 'images', ['.png']);
    if (found == null || !found.toLowerCase().endsWith('teto_idle.png'))
      throw 'mixed-case nested HXC asset was not found: ' + found;
    var boyfriend = findVSliceHxcAsset(root, 'characters/DDLCBoyFriend_Assets', 'images', ['.png']);
    if (boyfriend == null || !boyfriend.toLowerCase().endsWith('ddlcboyfriend_assets.png'))
      throw 'nested boyfriend alias was not found: ' + boyfriend;
    var staticShock = findVSliceHxcAsset(root, 'staticshock', 'images', ['.png']);
    if (staticShock == null || !staticShock.toLowerCase().endsWith('staticshock.png'))
      throw 'nested staticshock alias was not found: ' + staticShock;
    var noteHold = findVSliceHxcAsset(root, 'NOTE_hold_assets', 'images', ['.png']);
    if (noteHold == null || !noteHold.toLowerCase().endsWith('note_hold_assets.png'))
      throw 'shared note-hold alias was not found: ' + noteHold;
    var sharedMusic = findVSliceHxcAsset(root, 'breakfast-doki', 'music', ['.ogg']);
    if (sharedMusic == null
        || !sharedMusic.toLowerCase().endsWith('/shared/music/breakfast-doki/breakfast-doki.ogg'))
      throw 'nested V-Slice shared music track was not found: ' + sharedMusic;
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            install_directory_listing_helper(temp)
            (temp / "LookupFixture.hx").write_text(fixture, newline='\n')
            donor = temp / "donor"
            (donor / "IMAGES/Stage/TB").mkdir(parents=True)
            (donor / "IMAGES/Stage/TB/Teto_Idle.PNG").write_bytes(b"png")
            (donor / "IMAGES/Characters/Boyfriend").mkdir(parents=True)
            (donor / "IMAGES/Characters/Boyfriend/DDLCBoyFriend_Assets.PNG").write_bytes(b"png")
            (donor / "IMAGES/Clubroom").mkdir(parents=True)
            (donor / "IMAGES/Clubroom/staticshock.PNG").write_bytes(b"png")
            (donor / "Shared/IMAGES/NoteSkins").mkdir(parents=True)
            (donor / "Shared/IMAGES/NoteSkins/NOTE_hold_assets.PNG").write_bytes(b"png")
            (donor / "Shared/Music/breakfast-doki").mkdir(parents=True)
            (donor / "Shared/Music/breakfast-doki/breakfast-doki.ogg").write_bytes(b"ogg")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "LookupFixture", str(donor)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_repair_checks_nested_assets_even_with_direct_metadata(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function isImportFile",
                "static function validModuleName",
                "static function existingImportChild",
                "static function findChildDirectory",
                "static function validImportEntryName",
                "static function compatScriptTreeNames",
                "static function hasCompatScriptFile",
                "static function collectCompatScriptFiles",
                "static function nightmareVisionScriptSuffixes",
                "static function collectNightmareVisionScriptDirectory",
                "static function collectNightmareVisionScriptFilesImmediate",
                "static function collectNightmareVisionSongScripts",
                "static function collectNightmareVisionScriptFiles(",
                "static function collectNightmareVisionStageDataFiles",
                "static function compatScriptNamespaceHasExpectedFiles",
                "static function importSongFolderName",
                "static function compatScriptManifestPath",
                "static function sourceHasCompatScriptTree",
                "static function compatScriptManifestNeedsRepair",
            )
        )
        manifest = (ROOT / "source/CompatScriptManifest.hx").read_text()
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import CompatScriptManifest.CompatScriptManifestData;
using StringTools;

typedef SongImport = {{
  var name:String;
  @:optional var sourceFolder:String;
  @:optional var engine:String;
  @:optional var sourceRoot:String;
}};
class RepairFixture {{
{methods}
  static function importPathKey(path:String):String return Path.normalize(path);
  static function importPathIsWithin(_path:String, _root:String):Bool return true;
  static function importWorkCancelled():Bool return false;
  static function codenameRuntimeFiles(_song:SongImport):Array<{{source:String, relative:String, ?content:String, ?family:String}}> return [];
  static function mkdir(path:String):Void {{
    if (path == null || path == '' || FileSystem.exists(path)) return;
    var parent = Path.directory(path);
    if (parent != path) mkdir(parent);
    FileSystem.createDirectory(path);
  }}
  static function main() {{
    var donor = Sys.args()[0];
    var song:SongImport = {{name:'Repair', sourceFolder:'repair', engine:'Psych Engine', sourceRoot:donor}};
    var destination = CompatScriptManifest.destinationRoot(donor, song.engine);
    mkdir(Path.join([destination, 'scripts']));
    File.saveContent(Path.join([destination, 'scripts', 'global.lua']), 'function onCreate() end');
    mkdir(Path.join(['assets', 'data', 'repair']));
    File.saveContent(Path.join(['assets', 'data', 'repair', 'compatScripts.json']),
      CompatScriptManifest.stringify(CompatScriptManifest.create(donor, song.engine)));
    if (compatScriptManifestNeedsRepair(song)) throw 'nested assets namespace requested repair';
    FileSystem.deleteFile(Path.join([destination, 'scripts', 'global.lua']));
    if (!compatScriptManifestNeedsRepair(song)) throw 'nested assets partial namespace was treated as complete';

    var dataOnly = Sys.args()[1];
    var childSong:SongImport = {{name:'Data-Only', sourceFolder:'data-only',
      engine:'Psych Engine', sourceRoot:dataOnly}};
    var childDestination = CompatScriptManifest.destinationRoot(dataOnly, childSong.engine);
    mkdir(Path.join([childDestination, 'epicScripts']));
    File.saveContent(Path.join([childDestination, 'epicScripts', 'only.lua']),
      'function onUpdate() end');
    mkdir(Path.join(['assets', 'data', 'data-only']));
    File.saveContent(Path.join(['assets', 'data', 'data-only', 'compatScripts.json']),
      CompatScriptManifest.stringify(CompatScriptManifest.create(dataOnly, childSong.engine)));
    if (compatScriptManifestNeedsRepair(childSong))
      throw 'complete data-only literal namespace requested repair';
    FileSystem.deleteFile(Path.join([childDestination, 'epicScripts', 'only.lua']));
    if (!compatScriptManifestNeedsRepair(childSong))
      throw 'missing data-only literal dependency was treated as complete';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            install_directory_listing_helper(temp)
            (temp / "CompatScriptManifest.hx").write_text(manifest, newline='\n')
            (temp / "ImportSongOwnership.hx").write_text((ROOT / "source/ImportSongOwnership.hx").read_text(), newline='\n')
            for helper in ("CodenameScriptPlan", "CodenameScriptDiscovery", "CodenameEventPack", "CodenameStagePlacement", "CodenameModCatalog", "CodenameStrumlineLayout"):
                (temp / (helper + ".hx")).write_text((ROOT / "source" / (helper + ".hx")).read_text(), newline='\n')
            (temp / "ImportEngine.hx").write_text((ROOT / "source/ImportEngine.hx").read_text(), newline='\n')
            (temp / "PsychLuaScriptDependencies.hx").write_text(
                (ROOT / "source/PsychLuaScriptDependencies.hx").read_text(), newline='\n')
            (temp / "RepairFixture.hx").write_text(fixture, newline='\n')
            donor = temp / "donor"
            (donor / "assets/scripts").mkdir(parents=True)
            (donor / "assets/scripts/global.lua").write_text("function onCreate() end", newline='\n')
            (donor / "data").mkdir()
            (donor / "data/metadata.txt").write_text("direct metadata", newline='\n')
            data_only = temp / "data-only-donor"
            (data_only / "data/song").mkdir(parents=True)
            (data_only / "data/song/script.lua").write_text("addLuaScript('epicScripts/only')", newline='\n')
            (data_only / "epicScripts").mkdir()
            (data_only / "epicScripts/only.lua").write_text("function onUpdate() end", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RepairFixture", str(donor), str(data_only)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nightmare_vision_hx_generic_tree_copy_and_repair(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function destinationAssetsPath",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function findChildDirectory",
                "static function validImportEntryName",
                "static function normalizedImportFileName",
                "static function findImportFile",
                "static function copyImportFileNonOverwriting",
                "static function mergeTreeNonOverwriting",
                "static function mergeHxcScriptTree",
                "static function compatScriptTreeNames",
                "static function hasCompatScriptFile",
                "static function collectCompatScriptFiles",
                "static function nightmareVisionScriptSuffixes",
                "static function collectNightmareVisionScriptDirectory",
                "static function collectNightmareVisionScriptFilesImmediate",
                "static function collectNightmareVisionSongScripts",
                "static function collectNightmareVisionScriptFiles(",
                "static function collectNightmareVisionStageDataFiles",
                "static function mergeNightmareVisionStageDataFiles",
                "static function mergeNightmareVisionAssetFiles",
                "static function writeImportContentNonOverwriting",
                "static function compatScriptNamespaceHasExpectedFiles",
                "static function sourceHasCompatScriptTree",
                "static function mergePsychLanguageDataScopes",
                "static function mergePsychLanguageFiles",
                "static function isImportFile",
                "static function validModuleName",
                "static function importSongFolderName",
                "static function compatScriptManifestPath",
                "static function compatScriptManifestNeedsRepair",
                "static function mergeCompatScriptTrees",
                "static function mergeSelectedNightmareVisionScriptOwners",
                "static function canonicalNightmareVisionPackageRoot",
                "static function retainNightmareVisionPackageNamespace",
                "public static function publishNightmareVisionFamilyMemberRoots",
            )
        )
        manifest = (ROOT / "source/CompatScriptManifest.hx").read_text()
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import CompatScriptManifest.CompatScriptManifestData;
using StringTools;

class ImportSettings {{
  public static function normalizeSourcePath(path:String):String return Path.normalize(path);
}}
class ImportPackageFamilyCatalog {{
  public static function isAuthenticatedNightmareVisionContainer(path:String):Bool {{
    var root = ImportRootScanner.inspectRoot(path, ImportEngine.AUTO);
    if (root == null || root.engine != ImportEngine.NIGHTMARE_VISION || root.evidence == null)
      return false;
    for (item in root.evidence)
      if (StringTools.startsWith(item, 'Nightmare Vision executable package marker:')
          || StringTools.startsWith(item, 'Nightmare Vision Haxe project package:')
          || StringTools.startsWith(item, 'Nightmare Vision chart metadata: format=nmv2'))
        return true;
    return false;
  }}
  public static function bindCoreAssetHandoffs(_snapshotRoot:String, _record:Dynamic,
      _io:Dynamic):Null<Array<Dynamic>> return null;
}}
class SourceMappedMediaPolicy {{
  public static inline var PACKAGE_SCOPE:String = "package";
  public static inline var CORE_SCOPE:String = "core";
}}
typedef SongImport = {{
  var name:String;
  @:optional var sourceFolder:String;
  @:optional var engine:String;
  @:optional var sourceRoot:String;
}};
typedef SongImportSource = {{
  var song:String;
  var data:String;
  var destination:String;
  @:optional var sourceRoot:String;
  @:optional var engine:String;
}};
typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int;
  @:optional var errors:Array<String>; }};
typedef SourceMappedAssetPlan = {{ var diagnostics:Array<String>; var cancelled:Bool;
  var failed:Bool; }};
typedef SourceMappedAssetPolicyView = {{ var diagnostics:Array<String>; var cancelled:Bool;
  var failed:Bool; var legacyAllowed:Bool; var blockAllLegacy:Bool; }};
typedef PreparedMappedAssetOwner = {{ var sourceRoot:String; var engine:String; var scope:String;
  var destinationRoot:String; var plan:SourceMappedAssetPlan; }};
typedef PsychLanguagePublicationPlan = {{ var diagnostics:Array<String>; var cancelled:Bool;
  var failed:Bool; var legacyAllowed:Bool; var blockAllLegacy:Bool; }};
class PsychLanguagePublisher {{
  public static function prepare(_source:String, _engine:String, _destination:String,
      ?_cancelled:Void->Bool):PsychLanguagePublicationPlan
    return {{diagnostics:[], cancelled:false, failed:false, legacyAllowed:true, blockAllLegacy:false}};
  public static function publish(_plan:PsychLanguagePublicationPlan,
      _copy:String->String->Void, ?_cancelled:Void->Bool):Void {{}}
  public static function skipLegacy(_plan:PsychLanguagePublicationPlan,
      _source:String, _destination:String):Bool return false;
}}
class SourceMappedMediaPublisher {{
  public static function prepare(_source:String, _engine:String, _destination:String,
      ?_scope:String, ?_cancelled:Void->Bool):SourceMappedAssetPlan
    return {{diagnostics:[], cancelled:false, failed:false}};
  public static function publish(_plan:SourceMappedAssetPlan,
      _copy:String->String->Void, ?_cancelled:Void->Bool,
      ?_writeText:String->String->Void):Void {{}}
  public static function languageView(_plan:SourceMappedAssetPlan):SourceMappedAssetPolicyView
    return {{diagnostics:[], cancelled:false, failed:false, legacyAllowed:true, blockAllLegacy:false}};
  public static function policyView(_plan:SourceMappedAssetPlan, _label:String):SourceMappedAssetPolicyView
    return languageView(_plan);
  public static function mediaLabel(_engine:String, _scope:String):String return '';
  public static function mediaPolicy(_engine:String, _scope:String):Dynamic return null;
  public static function skipLegacyOwner(_view:SourceMappedAssetPolicyView,
      _source:String, _destination:String):Bool return false;
}}
class RepairFixture {{
{methods}
  static function mappedAssetOwnerKey(sourceRoot:String, engine:String):String return engine + '|' + sourceRoot;
  static function mappedOwnerPlan(_plans:Map<String, PreparedMappedAssetOwner>,
      _sourceRoot:String, _engine:String):PreparedMappedAssetOwner return null;
  static function mappedOwnerMediaView(_owner:PreparedMappedAssetOwner):SourceMappedAssetPolicyView return null;
  static function skipMappedOwnerMediaFile(_owner:PreparedMappedAssetOwner,
      _source:String, _destination:String):Bool return false;
  static function authenticatedNightmareVisionScope(_sourceRoot:String,
      _contentRoot:String):String return '';
  static function importWorkCancelled():Bool return false;
  static function mergeModPlusCharacterAssets(_root:String, _destination:String,
      _ids:Array<String>, _result:ImportAssetMergeResult):Void {{}}
  static function reportImportProgress(_phase:String, _current:String, _completed:Int = 0,
      _total:Int = 0, _copied:Int = 0, _skipped:Int = 0, _failed:Int = 0, _work:Int = 0):Void {{}}
  static function codenameRuntimeFiles(_song:SongImport):Array<{{source:String, relative:String, ?content:String, ?family:String}}> return [];
  static function main() {{
    var donor = Sys.args()[0];
    var song:SongImport = {{name:'NMV', sourceFolder:'nmv', engine:ImportEngine.NIGHTMARE_VISION,
      sourceRoot:donor}};
    var destination = CompatScriptManifest.destinationRoot(donor, song.engine);
    var sourceScripts = Path.join([donor, 'scripts']);
    var destinationScripts = Path.join([destination, 'scripts']);
    ensureDirectory(destinationScripts);
    var ownerFile = Path.join([destinationScripts, 'owner-not-script.txt']);
    File.saveContent(ownerFile, 'keep owner file');
    var ownerStageScript = Path.join([destination, 'data', 'stages', 'stage.hx']);
    ensureDirectory(Path.directory(ownerStageScript));
    File.saveContent(ownerStageScript, 'owner stage override');
    var ownerSongScript = Path.join([destination, 'songs', 'title', 'owner.hx']);
    ensureDirectory(Path.directory(ownerSongScript));
    File.saveContent(ownerSongScript, 'owner song override');

    var manifestPath = Path.join(['assets', 'data', 'nmv', CompatScriptManifest.FILE_NAME]);
    ensureDirectory(Path.directory(manifestPath));
    File.saveContent(manifestPath,
      CompatScriptManifest.stringify(CompatScriptManifest.create(donor, song.engine)));
    if (!compatScriptManifestNeedsRepair(song))
      throw 'missing copied NMV .hx namespace was treated as complete';

    var result:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0}};
    var mergedDestination = mergeCompatScriptTrees(donor, donor, ImportEngine.NIGHTMARE_VISION, result);
    if (mergedDestination != destination || result.failed != 0)
      throw 'NMV owner copy failed: ' + Std.string(result.errors);
    if (File.getContent(Path.join([destination, 'meta.json'])) != '{{"name":"single package"}}')
      throw 'package-local Nightmare Vision config was not copied byte-for-byte';
    var importedHx = Path.join([destinationScripts, 'global.hx']);
    if (!FileSystem.exists(importedHx)
        || File.getContent(importedHx) != 'function onLoad() {{}}')
      throw 'generic .hx script was not copied';
    if (File.getContent(ownerFile) != 'keep owner file')
      throw 'existing owner file was changed by the generic tree copy';
    if (File.getContent(ownerStageScript) != 'owner stage override')
      throw 'existing owner data-family script was overwritten';
    if (File.getContent(ownerSongScript) != 'owner song override')
      throw 'existing owner song script was overwritten';
    if (File.getContent(Path.join([destination, 'data', 'stages', 'nested', 'extra.hscript']))
        != 'function create() {{}}') throw 'nested stage HScript was not kept in source layout';
    if (File.getContent(Path.join([destination, 'data', 'notetypes', 'custom.hxs']))
        != 'function onNote() {{}}') throw 'NMV note type script was not kept in source layout';
    if (File.getContent(Path.join([destination, 'characters', 'vampire.hscript']))
        != 'function onLoad() {{}}') throw 'NMV character fallback was not retained';
    if (File.getContent(Path.join([destination, 'songs', 'title', 'scripts', 'modchart.hxs']))
        != 'function onCreate() {{}}') throw 'NMV song scripts/ file was not retained';
    if (File.getContent(Path.join([destination, 'songs', 'title', 'events.hx']))
        != 'function onEvent() {{}}') throw 'NMV direct song script was not copied';
    if (FileSystem.exists(Path.join([destination, 'songs', 'title', 'scripts', 'nested', 'not-direct.hx'])))
      throw 'nested song script outside the source lookup directories was copied';
    if (FileSystem.exists(Path.join([destination, 'songs', 'title', 'audio', 'Inst.ogg']))
        || FileSystem.exists(Path.join([destination, 'songs', 'title', 'chart.json'])))
      throw 'song audio/chart content was copied through the script-only path';

    // The executable's base assets and a selected content package have separate
    // owner roots. Staging one package must not flatten base files into it.
    var engineRoot = donor + '-engine-root';
    var baseScript = Path.join([engineRoot, 'assets', 'scripts', 'base.hx']);
    ensureDirectory(Path.directory(baseScript));
    File.saveContent(baseScript, 'function baseGlobal() {{}}');
    var packageRoot = Path.join([engineRoot, 'content', 'new-dsides']);
    var packageGlobal = Path.join([packageRoot, 'scripts', 'global.hx']);
    ensureDirectory(Path.directory(packageGlobal));
    File.saveContent(packageGlobal, 'function packageGlobal() {{}}');
    var packageStage = Path.join([packageRoot, 'data', 'stages', 'keep.hx']);
    ensureDirectory(Path.directory(packageStage));
    File.saveContent(packageStage, 'function donorStage() {{}}');
    var packageSongScript = Path.join([packageRoot, 'songs', 'pack-song', 'scripts', 'modchart.hxs']);
    ensureDirectory(Path.directory(packageSongScript));
    File.saveContent(packageSongScript, 'function onCreate() {{}}');
    var engineRootB = engineRoot + '-second';
    var packageRootB = Path.join([engineRootB, 'content', 'old-dsides']);
    var packageBScript = Path.join([packageRootB, 'scripts', 'second-root.hx']);
    ensureDirectory(Path.directory(packageBScript));
    File.saveContent(packageBScript, 'function secondPackage() {{}}');
    var baseOwner = mergeCompatScriptTrees(Path.join([engineRoot, 'assets']), engineRoot,
      ImportEngine.NIGHTMARE_VISION, result);
    var packageOwner = CompatScriptManifest.destinationRoot(packageRoot, ImportEngine.NIGHTMARE_VISION);
    var existingPackageStage = Path.join([packageOwner, 'data', 'stages', 'keep.hx']);
    ensureDirectory(Path.directory(existingPackageStage));
    File.saveContent(existingPackageStage, 'owner edited stage');
    var selectedNames:Map<String, Bool> = new Map<String, Bool>();
    selectedNames.set('song-one', true);
    selectedNames.set('song-two', true);
    selectedNames.set('song-three', true);
    var selectedSources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
    var packageInfo:SongImportSource = {{song:'pack-song', data:packageRoot, destination:'pack-song',
      sourceRoot:packageRoot, engine:ImportEngine.NIGHTMARE_VISION}};
    var packageInfoB:SongImportSource = {{song:'second-song', data:packageRootB, destination:'second-song',
      sourceRoot:packageRootB, engine:ImportEngine.NIGHTMARE_VISION}};
    selectedSources.set('song-one', packageInfo);
    selectedSources.set('song-two', packageInfo);
    selectedSources.set('song-three', packageInfoB);
    var stagedOwners:Map<String, Bool> = new Map<String, Bool>();
    mergeSelectedNightmareVisionScriptOwners(selectedNames, selectedSources, engineRoot,
      result, stagedOwners);
    if (result.failed != 0)
      throw 'first NMV installation reported another installation as a failure: ' + Std.string(result.errors);
    var copiedAfterFirstOwnerStage = result.copied;
    var skippedAfterFirstOwnerStage = result.skipped;
    mergeSelectedNightmareVisionScriptOwners(selectedNames, selectedSources, engineRoot,
      result, stagedOwners);
    if (result.copied != copiedAfterFirstOwnerStage || result.skipped != skippedAfterFirstOwnerStage)
      throw 'same NMV package was rescanned for each selected song';
    mergeSelectedNightmareVisionScriptOwners(selectedNames, selectedSources, engineRootB,
      result, stagedOwners);
    if (result.failed != 0)
      throw 'second NMV installation reported the first installation as a failure: ' + Std.string(result.errors);
    var copiedAfterSecondOwnerStage = result.copied;
    var skippedAfterSecondOwnerStage = result.skipped;
    mergeSelectedNightmareVisionScriptOwners(selectedNames, selectedSources, engineRootB,
      result, stagedOwners);
    if (result.copied != copiedAfterSecondOwnerStage || result.skipped != skippedAfterSecondOwnerStage)
      throw 'second NMV package was rescanned within its import transaction';
    if (baseOwner != CompatScriptManifest.destinationRoot(engineRoot, ImportEngine.NIGHTMARE_VISION)
        || File.getContent(Path.join([baseOwner, 'scripts', 'base.hx'])) != 'function baseGlobal() {{}}')
      throw 'outer executable assets were not kept in their own owner';
    if (File.getContent(Path.join([packageOwner, 'scripts', 'global.hx']))
        != 'function packageGlobal() {{}}')
      throw 'selected content package script tree was not retained';
    if (File.getContent(existingPackageStage) != 'owner edited stage')
      throw 'selected package copy overwrote an existing owner script';
    if (File.getContent(packageSongScript.replace(packageRoot, packageOwner))
        != 'function onCreate() {{}}')
      throw 'selected package song script was not kept under its owner';
    if (FileSystem.exists(Path.join([packageOwner, 'scripts', 'base.hx'])))
      throw 'base assets were flattened into the selected content owner';
    var packageOwnerB = CompatScriptManifest.destinationRoot(packageRootB, ImportEngine.NIGHTMARE_VISION);
    if (File.getContent(Path.join([packageOwnerB, 'scripts', 'second-root.hx']))
        != 'function secondPackage() {{}}')
      throw 'second NMV installation package was not staged by its matching root';
    if (FileSystem.exists(Path.join([packageOwner, 'scripts', 'second-root.hx']))
        || FileSystem.exists(Path.join([packageOwnerB, 'scripts', 'global.hx'])))
      throw 'separate NMV installation owners were cross-copied';

    // A chart discovered directly under the game assets root has only a core
    // layer. Keep its scripts and generic Paths files under __nmv_core so the
    // runtime's core fallback does not execute a duplicate owner-layer copy.
    var coreAssetsRoot = Path.join([donor + '-core-only', 'assets']);
    var coreScript = Path.join([coreAssetsRoot, 'scripts', 'base-core.hx']);
    ensureDirectory(Path.directory(coreScript));
    File.saveContent(coreScript, 'function baseCore() {{}}');
    var coreImage = Path.join([coreAssetsRoot, 'images', 'core-only.png']);
    ensureDirectory(Path.directory(coreImage));
    File.saveContent(coreImage, 'core image');
    var coreNamespace = CompatScriptManifest.destinationRoot(coreAssetsRoot,
      ImportEngine.NIGHTMARE_VISION);
    var coreNames:Map<String, Bool> = new Map<String, Bool>();
    coreNames.set('core-song', true);
    var coreSources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
    coreSources.set('core-song', {{song:'core-song', data:coreAssetsRoot, destination:'core-song',
      sourceRoot:coreAssetsRoot, engine:ImportEngine.NIGHTMARE_VISION}});
    mergeSelectedNightmareVisionScriptOwners(coreNames, coreSources, coreAssetsRoot,
      result, new Map());
    if (result.failed != 0)
      throw 'core-only NMV root staging failed: ' + Std.string(result.errors);
    if (File.getContent(Path.join([coreNamespace, '__nmv_core', 'scripts', 'base-core.hx']))
        != 'function baseCore() {{}}'
        || FileSystem.exists(Path.join([coreNamespace, 'scripts', 'base-core.hx'])))
      throw 'core-only NMV scripts were duplicated into the owner layer';
    if (File.getContent(Path.join([coreNamespace, '__nmv_core', 'images', 'core-only.png']))
        != 'core image')
      throw 'core-only generic Paths asset was not staged under __nmv_core';

    var copiedScopeDestination = Path.join([destination, 'data', 'stages', 'stage.hx']);
    var copiedSongDestination = Path.join([destination, 'songs', 'title', 'scripts', 'modchart.hxs']);
    if (!FileSystem.exists(copiedScopeDestination) || !FileSystem.exists(copiedSongDestination))
      throw 'NMV scoped script paths were not materialized';
    if (compatScriptManifestNeedsRepair(song))
      throw 'complete copied NMV .hx namespace requested repair';

    FileSystem.deleteFile(Path.join([destination, 'data', 'stages', 'nested', 'extra.hscript']));
    if (!compatScriptManifestNeedsRepair(song))
      throw 'missing NMV data-family script was treated as complete';
    mergeCompatScriptTrees(donor, donor, ImportEngine.NIGHTMARE_VISION, result);
    if (File.getContent(Path.join([destination, 'data', 'stages', 'nested', 'extra.hscript']))
        != 'function create() {{}}') throw 'repair did not restore the NMV data-family script';
    if (File.getContent(ownerFile) != 'keep owner file')
      throw 'repair copy overwrote an existing owner file';
    if (File.getContent(ownerStageScript) != 'owner stage override'
        || File.getContent(ownerSongScript) != 'owner song override')
      throw 'repair overwrote an existing owner script';
    if (compatScriptManifestNeedsRepair(song))
      throw 'repair did not clear after restoring the generic .hx script';

    // Chartless siblings still receive a real runtime namespace when their
    // package-local config and assets are present. A shared-container config
    // cannot enroll a child package.
    var chartlessGame = donor + '-chartless-game';
    ensureDirectory(Path.join([chartlessGame, 'content']));
    ensureDirectory(Path.join([chartlessGame, 'assets']));
    File.saveContent(Path.join([chartlessGame, 'Project.xml']),
      '<project><app package="com.nmvTeam.nightmareEngine" /></project>');
    var chartlessRoot = Path.join([chartlessGame, 'content', 'chartless-family-member']);
    ensureDirectory(Path.join([chartlessRoot, 'assets', 'images']));
    ensureDirectory(Path.join([chartlessRoot, 'assets', 'scripts']));
    File.saveContent(Path.join([chartlessRoot, 'meta.json']), '{{"name":"chartless"}}');
    File.saveContent(Path.join([chartlessRoot, 'assets', 'images', 'menu.png']), 'menu asset');
    File.saveContent(Path.join([chartlessRoot, 'assets', 'scripts', 'mod.hx']), 'function onLoad() {{}}');
    var chartlessResult = publishNightmareVisionFamilyMemberRoots([chartlessRoot]);
    var chartlessOwner = CompatScriptManifest.destinationRoot(chartlessRoot, ImportEngine.NIGHTMARE_VISION);
    if (chartlessResult.failed != 0
        || !FileSystem.exists(Path.join([chartlessOwner, 'meta.json']))
        || !FileSystem.exists(Path.join([chartlessOwner, 'images', 'menu.png']))
        || !FileSystem.exists(Path.join([chartlessOwner, 'scripts', 'mod.hx']))
        || File.getContent(Path.join([chartlessOwner, 'meta.json'])) != '{{"name":"chartless"}}'
        || File.getContent(Path.join([chartlessOwner, 'images', 'menu.png'])) != 'menu asset'
        || File.getContent(Path.join([chartlessOwner, 'scripts', 'mod.hx'])) != 'function onLoad() {{}}')
      throw 'chartless configured Nightmare Vision package was not fully published: copied='
        + chartlessResult.copied + ' failed=' + chartlessResult.failed + ' errors='
        + Std.string(chartlessResult.errors) + ' owner=' + chartlessOwner;
    var unconfiguredRoot = Path.join([chartlessGame, 'content', 'unconfigured-family-member']);
    ensureDirectory(Path.join([unconfiguredRoot, 'assets', 'images']));
    File.saveContent(Path.join([unconfiguredRoot, 'assets', 'images', 'menu.png']), 'unconfigured asset');
    var unconfiguredOwner = CompatScriptManifest.destinationRoot(unconfiguredRoot,
      ImportEngine.NIGHTMARE_VISION);
    var unconfiguredResult = publishNightmareVisionFamilyMemberRoots([unconfiguredRoot]);
    if (unconfiguredResult.failed != 0 || FileSystem.exists(unconfiguredOwner))
      throw 'family publication substituted a missing package config';

    FileSystem.deleteFile(copiedSongDestination);
    if (!compatScriptManifestNeedsRepair(song))
      throw 'missing NMV song script was treated as complete';
    mergeCompatScriptTrees(donor, donor, ImportEngine.NIGHTMARE_VISION, result);
    if (File.getContent(copiedSongDestination) != 'function onCreate() {{}}'
        || compatScriptManifestNeedsRepair(song))
      throw 'repair did not restore and verify the NMV song script';

    var psychOnlyHx = donor + '-psych';
    ensureDirectory(Path.join([psychOnlyHx, 'scripts']));
    File.saveContent(Path.join([psychOnlyHx, 'scripts', 'global.hx']), 'function onLoad() {{}}');
    if (sourceHasCompatScriptTree(psychOnlyHx, ImportEngine.PSYCH))
      throw 'Psych .hx file changed the non-NMV executable-script rule';
    var modPlusOnlyHx = donor + '-modplus';
    ensureDirectory(Path.join([modPlusOnlyHx, 'images', 'custom_stages']));
    File.saveContent(Path.join([modPlusOnlyHx, 'images', 'custom_stages', 'room.hx']),
      'function start() {{}}');
    if (sourceHasCompatScriptTree(modPlusOnlyHx, ImportEngine.MODDING_PLUS))
      throw 'Modding Plus stage .hx file changed the existing rule';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            install_directory_listing_helper(temp)
            (temp / "ImportRootScanner.hx").write_text('''
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
            (temp / "CompatScriptManifest.hx").write_text(manifest, newline='\n')
            (temp / "ImportGeneratedOutput.hx").write_text(
                (ROOT / "source/ImportGeneratedOutput.hx").read_text(), newline='\n')
            (temp / "ImportSongOwnership.hx").write_text((ROOT / "source/ImportSongOwnership.hx").read_text(), newline='\n')
            for helper in (
                "CodenameScriptPlan", "CodenameScriptDiscovery", "CodenameEventPack",
                "CodenameStagePlacement", "CodenameModCatalog", "CodenameStrumlineLayout",
            ):
                (temp / (helper + ".hx")).write_text((ROOT / "source" / (helper + ".hx")).read_text(), newline='\n')
            for helper in ("ImportEngine", "PsychLuaScriptDependencies", "NightmareVisionAssetCollector"):
                (temp / (helper + ".hx")).write_text((ROOT / "source" / (helper + ".hx")).read_text(), newline='\n')
            (temp / "RepairFixture.hx").write_text(fixture, newline='\n')
            donor = temp / "donor"
            (donor / "scripts").mkdir(parents=True)
            (donor / "scripts/global.hx").write_text("function onLoad() {}", newline='\n')
            (donor / "meta.json").write_text('{"name":"single package"}', newline='\n')
            (donor / "data/stages").mkdir(parents=True)
            (donor / "data/stages/stage.hx").write_text("function create() {}", newline='\n')
            (donor / "data/stages/nested").mkdir(parents=True)
            (donor / "data/stages/nested/extra.hscript").write_text("function create() {}", newline='\n')
            (donor / "data/notetypes").mkdir(parents=True)
            (donor / "data/notetypes/custom.hxs").write_text("function onNote() {}", newline='\n')
            (donor / "events").mkdir()
            (donor / "events/flash.hscript").write_text("function onEvent() {}", newline='\n')
            (donor / "characters").mkdir()
            (donor / "characters/vampire.hscript").write_text("function onLoad() {}", newline='\n')
            (donor / "songs/title/scripts/nested").mkdir(parents=True)
            (donor / "songs/title/events.hx").write_text("function onEvent() {}", newline='\n')
            (donor / "songs/title/scripts/modchart.hxs").write_text("function onCreate() {}", newline='\n')
            (donor / "songs/title/scripts/nested/not-direct.hx").write_text("function onCreate() {}", newline='\n')
            (donor / "songs/title/audio").mkdir()
            (donor / "songs/title/audio/Inst.ogg").write_text("audio", newline='\n')
            (donor / "songs/title/chart.json").write_text("{{}}", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "RepairFixture", str(donor)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
