"""Mounted end-to-end coverage for the selected Modding Plus donor root.

The mounted ``modding-plus/vsfreddy_1_9_5`` root is used as a read-only donor.  The Haxe
fixture extracts the production discovery/chart writer and asset/compatibility
tree merge methods, then runs them in a project-local temporary destination.
This keeps the test independent of a game build while exercising the same
native materialization boundaries used by ``importSongsFromPath``.
"""
from haxe_test_support import HAXE_COMMAND

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]
DONOR_ROOT = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/modding-plus/vsfreddy_1_9_5"
)
HAXE = ROOT / ".tools/haxe/haxe"


def _audit_module():
    spec = importlib.util.spec_from_file_location(
        "mounted_auto_audit", ROOT / "tools/audit_mounted_auto_import.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(module_source: str) -> str:
    """Build a bounded Haxe fixture around production ModuleFunctions methods."""

    audit = _audit_module()
    base = audit.haxe_fixture(module_source)
    extra_markers = (
        "static function mergeTreeNonOverwriting",
        "static function mergeHxcScriptTree",
        "static function registryArrayContains",
        "static function isImportStageMapRegistry",
        "static function recoverImportStageMapRegistry",
        "static function parseImportRegistryJson",
        "static function mergeObjectRegistry",
        "static function mergeFreeplayRegistry",
        "static function mergeStoryRegistry",
        "static function importJsonValuesEqual",
        "static function supportedAssetTrees",
        "static function mergeCompatScriptTrees",
        "static function collectNightmareVisionStageDataFiles",
        "static function mergeNightmareVisionStageDataFiles",
        "static function mergeNightmareVisionAssetFiles",
        "static function mergeSelectedNightmareVisionScriptOwners",
        "static function copyImportFileNonOverwriting",
        "static function writeImportContentNonOverwriting",
        "static function modPlusCharactersUsedByImportedSongs",
        "static function mergeModPlusCharacterAssets",
        "static function mergeSupportedAssets",
    )
    extra = "\n".join(
        audit.extract_method(module_source, marker) for marker in extra_markers
    )
    stage_parser_marker = base.index("// PSYCH_STAGE_INFERENCE_FIXTURE")
    module_close = base.rfind("\n}", 0, stage_parser_marker)
    if module_close < 0:
        raise AssertionError("could not locate extracted ModuleFunctions close")
    wrappers = r'''
  public static function discoverModPlus(data:String, audio:String, music:String,
      sourceRoot:String, output:Map<String, SongImportSource>):Array<SongImport> {
    var result:Array<SongImport> = [];
    var seen:Map<String, Bool> = new Map<String, Bool>();
    appendAssetSongImports(result, seen, data, audio, music, output, sourceRoot,
      ImportEngine.MODDING_PLUS);
    return result;
  }
  public static function mergeAssets(sourceRoot:String, importedNames:Map<String, Bool>,
      sources:Map<String, SongImportSource>, scriptRoot:String, engine:String,
      ?stagedCompatOwnerRoots:Map<String, Bool>):ImportAssetMergeResult
    return mergeSupportedAssets(sourceRoot, importedNames, sources, scriptRoot, engine,
      stagedCompatOwnerRoots);
'''
    base = base[:module_close] + "\n" + extra + wrappers + base[module_close:]
    main_start = base.index("class Main {")
    main = r'''class Main {
  static function fail(message:String):Void throw message;
  static function requireFile(path:String):Void {
    if (!FileSystem.exists(path) || FileSystem.isDirectory(path)
        || FileSystem.stat(path).size <= 0)
      fail("missing file: " + path);
  }
  static function hasRegistrySong(path:String, wanted:String):Bool {
    var registry:Dynamic = Json.parse(File.getContent(path));
    if (!Std.isOfType(registry, Array)) return false;
    for (category in (cast registry:Array<Dynamic>)) {
      if (category == null || category.songs == null || !Std.isOfType(category.songs, Array))
        continue;
      for (entry in (cast category.songs:Array<Dynamic>))
        if (entry != null && entry.name != null
            && Std.string(entry.name).toLowerCase() == wanted.toLowerCase())
          return true;
    }
    return false;
  }
  static function registrySongCount(path:String, categoryName:String, wanted:String):Int {
    var registry:Dynamic = Json.parse(File.getContent(path));
    var count = 0;
    if (!Std.isOfType(registry, Array)) return count;
    for (category in (cast registry:Array<Dynamic>)) {
      if (category == null || category.name == null || category.songs == null
          || Std.string(category.name).toLowerCase() != categoryName.toLowerCase()) continue;
      for (entry in (cast category.songs:Array<Dynamic>))
        if (entry != null && entry.name != null
            && Std.string(entry.name).toLowerCase() == wanted.toLowerCase()) count++;
    }
    return count;
  }
  static function main() {
    var root = Sys.args()[0];
    var data = Path.join([root, "assets", "data"]);
    var music = Path.join([root, "assets", "music"]);
    var sources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
    var songs = ModuleFunctions.discoverModPlus(data, music, music, root, sources);
    if (songs.length != 3) fail("Modding Plus discovery count=" + songs.length);

    FileSystem.createDirectory("assets");
    FileSystem.createDirectory("assets/data");
    FileSystem.createDirectory("assets/songs");
    File.saveContent("assets/data/baseSongKeys.json", "[]");
    File.saveContent("assets/data/freeplaySongJson.jsonc",
      "[{\"name\":\"Imported\",\"songs\":[]}]");
    var imported:Map<String, Bool> = new Map<String, Bool>();
    for (song in songs) {
      var target = song.name.toLowerCase();
      imported.set(target, true);
      if (!ModuleFunctions.importSong(song)) fail("song writer failed: " + song.name);
      ModuleFunctions.writeProvenance(song);
      ModuleFunctions.writeManifest(song);
      requireFile(Path.join(["assets", "data", target, target + ".json"]));
      requireFile(Path.join(["assets", "songs", target, "Inst.ogg"]));
      requireFile(Path.join(["assets", "songs", target, "Voices.ogg"]));
      requireFile(Path.join(["assets", "data", target, "compatScripts.json"]));
      if (target == "let-us-in")
        requireFile(Path.join(["assets", "data", target, "dialog.txt"]));
      if (FileSystem.exists(Path.join(["assets", "data", target, "modchart.hscript"])))
        fail("unobserved song modchart was materialized: " + target);
    }

    var merged = ModuleFunctions.mergeAssets(Path.join([root, "assets"]), imported,
      sources, root, ImportEngine.MODDING_PLUS);
    if (merged.failed != 0) fail("asset merge failures=" + merged.failed);
    for (target in ["fired", "let-us-in", "slaughter"]) {
      if (!hasRegistrySong("assets/data/freeplaySongJson.jsonc", target))
        fail("song is not Freeplay-visible: " + target);
      if (registrySongCount("assets/data/freeplaySongJson.jsonc", "Imported", target) != 1
          || registrySongCount("assets/data/freeplaySongJson.jsonc", "Base Game", target) != 0)
        fail("donor-local Base Game category was not normalized: " + target);
      requireFile(Path.join(["assets", "data", target, target + ".json"]));
      requireFile(Path.join(["assets", "songs", target, "Inst.ogg"]));
      requireFile(Path.join(["assets", "songs", target, "Voices.ogg"]));
    }
    requireFile("assets/data/storySonglist.json");

    // These are actual donor-backed native registry/assets used by the three
    // selected charts, not synthetic package conventions.
    requireFile("assets/images/custom_chars/custom_chars.jsonc");
    requireFile("assets/images/custom_chars/bf-fire/char.png");
    requireFile("assets/images/custom_chars/bf-dark/char.png");
    requireFile("assets/images/custom_chars/Freddy/char.png");
    requireFile("assets/images/custom_chars/Freddy-angry/char.png");
    requireFile("assets/images/custom_chars/Golden-freddy/char.png");
    requireFile("assets/images/custom_stages/custom_stages.json");
    requireFile("assets/images/custom_stages/tank2.hscript");
    requireFile("assets/images/custom_stages/stage.hscript");
    requireFile("assets/images/custom_cutscenes/cutscenes.json");
    requireFile("assets/images/custom_cutscenes/monster.hscript");
    requireFile("assets/images/custom_cutscenes/Fired.hscript");
    requireFile("assets/images/custom_difficulties/difficulties.json");
    // This donor has no ui_packs/ui.json; its real UI payload is the ordinary
    // custom_ui asset tree, while all three charts request native `normal`.
    requireFile("assets/images/custom_ui/ui_packs/template/NOTE_assets.png");

    var manifest:Dynamic = Json.parse(
      File.getContent("assets/data/fired/compatScripts.json"));
    if (manifest == null || manifest.selectedRoot == null
        || Std.string(manifest.selectedRoot) == "")
      fail("compatibility manifest owner missing");
    var owner = Std.string(manifest.selectedRoot);
    requireFile(Path.join([owner, "scripts", "plugin_classes", "RunningTankman.hx"]));
    for (character in ["bf-fire", "bf-dark", "gf-dark", "Freddy",
        "Freddy-angry", "Golden-freddy"])
      requireFile(Path.join([owner, "images", "custom_chars", character, "char.png"]));
    requireFile(Path.join([owner, "images", "custom_chars", "bf.hscript"]));
    requireFile(Path.join([owner, "images", "custom_chars", "gf.hscript"]));
    var scopedCharacters:Dynamic = Json.parse(
      File.getContent(Path.join([owner, "images", "custom_chars", "custom_chars.jsonc"])));
    for (character in ["bf-fire", "bf-dark", "gf-dark", "Freddy",
        "Freddy-angry", "Golden-freddy"])
      if (!Reflect.hasField(scopedCharacters, character))
        fail("selected owner character registry row missing: " + character);
    if (FileSystem.exists("assets/data/fired/modchart.hscript")
        || FileSystem.exists("assets/data/let-us-in/modchart.hscript")
        || FileSystem.exists("assets/data/slaughter/modchart.hscript"))
      fail("unexpected per-song modchart materialized");
    // The donor's unassociated legacy script is not a selected song module;
    // do not silently make it execute for all three songs.
    if (FileSystem.exists("assets/data/zavodilla.hscript"))
      fail("orphan root script was exposed as a selected song module");
    trace("MODPLUS=" + songs.length + "|MERGED=" + merged.copied
      + "|OWNER=" + owner);
  }
}
'''
    return base[:main_start] + main


def _snapshot(paths):
    return {str(path): sha256(path.read_bytes()).hexdigest() for path in paths}


@unittest.skipUnless(
    DONOR_ROOT.is_dir() and HAXE.is_file(),
    "mounted Modding Plus donor or portable Haxe is unavailable",
)
class MountedModPlusEndToEndTest(unittest.TestCase):
    def test_donor_inventory_and_native_materialization(self):
        songs = {
            "fired": {
                "display": "Fired",
                "p1": "bf-fire",
                "p2": "Golden-freddy",
                "stage": "tank2",
                "cutscene": "none",
            },
            "let-us-in": {
                "display": "Let-us-in",
                "p1": "bf-dark",
                "p2": "Freddy",
                "stage": "stage",
                "cutscene": "none",
            },
            "slaughter": {
                "display": "Slaughter",
                "p1": "bf-dark",
                "p2": "Freddy-angry",
                "stage": "tank",
                "cutscene": "monster",
            },
        }
        snapshot_paths = [
            DONOR_ROOT / "assets/images/custom_chars/custom_chars.jsonc",
            DONOR_ROOT / "assets/images/custom_stages/custom_stages.json",
            DONOR_ROOT / "assets/images/custom_cutscenes/cutscenes.json",
            DONOR_ROOT / "assets/images/custom_ui/ui_packs/template/NOTE_assets.png",
            DONOR_ROOT / "assets/scripts/plugin_classes/RunningTankman.hx",
            DONOR_ROOT / "assets/data/zavodilla.hscript",
        ]
        for key, expected in songs.items():
            folder = DONOR_ROOT / "assets/data" / key
            charts = sorted(folder.glob("*.json"))
            self.assertEqual(
                [path.name for path in charts],
                [f"{key}-easy.json", f"{key}-hard.json", f"{key}.json"],
            )
            for chart in charts:
                payload = json.loads(chart.read_text())
                song = payload["song"]
                self.assertEqual(song["song"], expected["display"])
                self.assertEqual(song["player1"], expected["p1"])
                self.assertEqual(song["player2"], expected["p2"])
                self.assertEqual(song["stage"], expected["stage"])
                self.assertEqual(song["cutsceneType"], expected["cutscene"])
                self.assertGreater(len(song["notes"]), 0)
                self.assertNotIn("events", song)
                self.assertNotIn("modchart", song)
            for suffix in ("_Inst.ogg", "_Voices.ogg"):
                audio = DONOR_ROOT / "assets/music" / f"{expected['display']}{suffix}"
                self.assertTrue(audio.is_file(), audio)
                self.assertGreater(audio.stat().st_size, 0)
            self.assertFalse((folder / "events.json").exists())
            self.assertFalse((folder / "noteInfo.json").exists())
            self.assertFalse((folder / "modchart.hscript").exists())
        self.assertTrue((DONOR_ROOT / "assets/data/let-us-in/dialog.txt").is_file())
        self.assertFalse((DONOR_ROOT / "assets/data/fired/dialog.txt").exists())
        self.assertFalse((DONOR_ROOT / "assets/data/slaughter/dialog.txt").exists())

        chars = json.loads(
            (DONOR_ROOT / "assets/images/custom_chars/custom_chars.jsonc").read_text()
        )
        for name in ("bf-fire", "bf-dark", "Freddy", "Freddy-angry", "Golden-freddy"):
            self.assertIn(name, chars)
            self.assertTrue(
                (DONOR_ROOT / "assets/images/custom_chars" / name / "char.png").is_file()
            )
        stages = json.loads(
            (DONOR_ROOT / "assets/images/custom_stages/custom_stages.json").read_text()
        )
        self.assertEqual(stages["tank2"], "tank")
        self.assertEqual(stages["stage"], "stage")
        cuts = json.loads(
            (DONOR_ROOT / "assets/images/custom_cutscenes/cutscenes.json").read_text()
        )
        self.assertEqual(cuts["monster"], "monster")
        self.assertFalse(
            (DONOR_ROOT / "assets/images/custom_ui/ui_packs/ui.json").exists()
        )
        self.assertEqual(
            (DONOR_ROOT / "assets/scripts/plugin_classes/classes.txt").read_text(), ""
        )
        self.assertNotIn(
            "zavodilla",
            {path.name.rsplit(".", 1)[0].lower() for path in (DONOR_ROOT / "assets/data").glob("*/")},
        )
        before = _snapshot(snapshot_paths)

        module_source = (ROOT / "source/ModuleFunctions.hx").read_text()
        fixture = _fixture(module_source)
        with tempfile.TemporaryDirectory(prefix="modplus-e2e-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            for name in (
                "ImportSongOwnership.hx",
                "PsychLuaScriptDependencies.hx",
                "ImportEngine.hx",
                "ImportRootScanner.hx",
                "VSliceImporter.hx",
                "VSliceAstcAdapter.hx",
                "HxcScriptIdentity.hx",
                "HxcScriptDiscovery.hx",
                "CodenameEventMetadata.hx",
                "CodenameNoteMetadata.hx",
                "CodenameEventPack.hx",
                "CodenameStagePlacement.hx",
                "CodenameStrumlineLayout.hx",
                "CodenameScriptDiscovery.hx",
                "CodenameInstallationAssetOverlay.hx",
                "CodenameSongMetadata.hx",
                "NightmareVisionChartCompat.hx",
                "NightmareVisionScriptDiscovery.hx",
                "NightmareVisionDifficultyCompat.hx",
                "NightmareVisionVocalRole.hx",
                "NightmareVisionAssetCollector.hx",
                "ImportDirectoryListing.hx",
            ):
                (temp / name).write_text((ROOT / "source" / name).read_text(), newline='\n')
            codename_importer = (ROOT / "source/CodenameImporter.hx").read_text()
            codename_importer = codename_importer.replace(
                "EngineCompat.EngineCompatEventRoute", "CodenameEventRoute"
            ).replace(
                "using StringTools;",
                "using StringTools;\ntypedef CodenameEventRoute = { var name:String; var v1:String; var v2:String; var v3:String; };",
                1,
            )
            (temp / "CodenameImporter.hx").write_text(codename_importer, newline='\n')
            (temp / "CodenameCharacterAtlas.hx").write_text(
                (ROOT / "source/CodenameCharacterAtlas.hx").read_text()
            , newline='\n')
            (temp / "CompatScriptManifest.hx").write_text(
                (ROOT / "source/CompatScriptManifest.hx").read_text()
            , newline='\n')
            (temp / "NoteTypeCompat.hx").write_text(
                """class NoteTypeCompat {
  public static function isStringType(value:Dynamic):Bool return value != null && Std.isOfType(value, String);
  public static function applyVSliceKind(definition:Dynamic, value:Dynamic):Bool return false;
  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int {
    definitions.push({sourceNoteType:Std.string(value)}); return definitions.length - 1;
  }
}
"""
            , newline='\n')
            (temp / "EngineCompat.hx").write_text(
                """class EngineCompat {
  public static function eventName(name:Dynamic):String {
    if (name == null) return "";
    var original = StringTools.trim(Std.string(name));
    switch (original.toLowerCase()) {
      case 'changecharacter' | 'change character cl' | 'charchange': return 'Change Character';
      case 'focuscamera' | 'focus camera': return 'Focus Camera';
      default: return original;
    }
  }
  public static function scriptFunctionNames(contents:String):Array<String> return [];
  public static function knownScriptFunction(name:String):Bool return false;
  public static function unknownScriptFunctions(contents:String):Array<String> return [];
  public static function routeVSliceEvent(name:String, values:Dynamic):Dynamic return null;
  public static function vSliceNativeCharacterCandidates(path:String):Array<String> return [];
  public static function resolveStageResolution(reference:String):Dynamic return {nativeName:reference,stageID:0,standard:false};
  public static function isBuiltinStageReference(reference:String):Bool return false;
  public static function legacyDialogueText(data:Dynamic,player1:String,player2:String):String return null;
  public static function legacyCutsceneScript(data:Dynamic):String return null;
  public static function legacyCutsceneBool(data:Dynamic,field:String,fallback:Bool):Bool return fallback;
}
"""
            , newline='\n')
            (temp / "LuaCompat.hx").write_text(
                """typedef LuaCompatResult = { var hscript:String; var supported:Bool; var diagnostics:Array<String>; };
class LuaCompat { public static function translate(source:String,?origin:String):LuaCompatResult
  return {hscript:source,supported:true,diagnostics:[]}; }
"""
            , newline='\n')
            (temp / "HxcCompat.hx").write_text(
                """typedef HxcCompatDiagnostic = { var code:String; var message:String; };
typedef HxcCompatEventAdapter = { var sourceName:String; var canonicalName:String; var fields:Array<String>; };
typedef HxcCompatCallbackAdapter = { var sourceName:String; var canonicalName:String; var arguments:Array<String>; var body:String; var safe:Bool; };
typedef HxcCompatResult = { var kind:String; var generatedHscript:String; var diagnostics:Array<HxcCompatDiagnostic>;
  var eventAdapters:Array<HxcCompatEventAdapter>; var nativeNoteDefinitions:Array<Dynamic>; var className:String;
  var canonicalCallbacks:Array<String>; var noteKinds:Array<String>; var callbackAdapters:Array<HxcCompatCallbackAdapter>;
  var noteBehaviorPatterns:Array<String>; var moduleDisabled:Bool; var customEventKind:String; var customEventBody:String; };
class HxcCompat {
  public static function noteKindAvoidsHits(source:String):Bool return false; public static function analyze(source:String,?path:String):HxcCompatResult
  return {kind:'',generatedHscript:'',diagnostics:[],eventAdapters:[],nativeNoteDefinitions:[],className:'',canonicalCallbacks:[],noteKinds:[],callbackAdapters:[],noteBehaviorPatterns:[],moduleDisabled:false,customEventKind:'',customEventBody:''}; }
"""
            , newline='\n')
            (temp / "DifficultyManager.hx").write_text(
                """import haxe.io.Path; import sys.FileSystem;
class DifficultyManager { public static var supportedDiff:Map<String,Bool>=new Map<String,Bool>();
  public static function addSongSupport(song:String):Void { var key=song.toLowerCase();
    if (FileSystem.exists(Path.join(["assets","data",key,key+".json"]))) supportedDiff.set(key,true); } }
"""
            , newline='\n')
            (temp / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", str(temp),
                 "--run", "Main", str(DONOR_ROOT)],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=240,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
            )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertRegex(output, r"MODPLUS=3\|MERGED=[1-9][0-9]*\|OWNER=assets/imported_mods/")
        self.assertEqual(before, _snapshot(snapshot_paths))


if __name__ == "__main__":
    unittest.main()
