"""Selected-owner resolution for imported Modding Plus and Codename stages."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
        index += 1
    raise AssertionError(f"unterminated method: {marker}")


class ImportedStageRegistryTest(unittest.TestCase):
    def test_selected_owner_collision_safety_and_path_validation(self):
        fixture = r'''import haxe.Json;

class Main {
  static var files:Map<String, String> = new Map();
  static var calls:Array<String> = [];

  static function exists(path:String):Bool {
    calls.push("exists:" + path);
    return files.exists(path);
  }
  static function read(path:String):String {
    calls.push("read:" + path);
    return files.get(path);
  }
  static function parse(raw:String):Dynamic return Json.parse(raw);
  static function check(ok:Bool, message:String):Void {
    if (!ok) throw message;
  }
  static function clear():Void {
    files = new Map();
    calls = [];
  }
  static function manifest(selected:String, roots:Array<Dynamic>):Void {
    files.set("assets/data/owner-song/compatScripts.json",
      Json.stringify({version:1, selectedRoot:selected, roots:roots}));
  }
  static function registry(root:String, contents:String, jsonc:Bool = false):Void {
    var extension = jsonc ? ".jsonc" : ".json";
    files.set(root + "/images/custom_stages/custom_stages" + extension, contents);
  }
  static function result(song:String, requested:String):Dynamic {
    return ImportedStageRegistry.resolve(song, requested, exists, read, parse);
  }

  static function main():Void {
    var ownerA = "assets/imported_mods/owner-a";
    var ownerB = "assets/imported_mods/owner-b";
    var global = "assets";

    // Both supported engines may own stages. The selected owner beats a
    // same-key foreign root and the global registry.
    clear();
    manifest(ownerA, [
      {engine:"Modding Plus", path:ownerA},
      {engine:"Codename Engine", path:ownerB}
    ]);
    registry(ownerA, '{"tank2":"owner-a-stage.hscript"}');
    registry(ownerB, '{"tank2":"owner-b-stage"}');
    registry(global, '{"tank2":"global-stage"}');
    files.set(ownerA + "/images/custom_stages/owner-a-stage.hscript", "owner-a");
    files.set(ownerB + "/images/custom_stages/owner-b-stage.hscript", "owner-b");
    files.set(global + "/images/custom_stages/global-stage.hscript", "global");
    var resolved:Dynamic = result("owner-song", "tank2");
    check(resolved != null && resolved.name == "tank2" && resolved.script == "owner-a-stage"
      && resolved.directory == ownerA + "/images/custom_stages/"
      && resolved.unavailable == false && resolved.reason == "",
      "selected Modding Plus owner did not win registry collision");

    // Codename is also an eligible selected owner.
    manifest(ownerB, [
      {engine:"Modding Plus", path:ownerA},
      {engine:"Codename Engine", path:ownerB}
    ]);
    resolved = result("owner-song", "tank2");
    check(resolved != null && resolved.script == "owner-b-stage"
      && resolved.directory == ownerB + "/images/custom_stages/"
      && resolved.unavailable == false,
      "selected Codename owner did not resolve its stage");

    // An owned row is authoritative even when its script is missing: callers
    // can reject it without loading the global/foreign registry collision.
    manifest(ownerA, [
      {engine:"Modding Plus", path:ownerA},
      {engine:"Codename Engine", path:ownerB}
    ]);
    registry(ownerA, '{"tank2":"missing-owner-stage.hscript"}');
    resolved = result("owner-song", "tank2");
    check(resolved != null && resolved.unavailable == true
      && resolved.reason == "script-unavailable"
      && resolved.script == "missing-owner-stage"
      && resolved.directory == ownerA + "/images/custom_stages/",
      "missing owned script fell through instead of returning unavailable");

    // Optional JSONC is used only when JSON is absent; JSON keeps precedence.
    registry(ownerA, '{"tank2":"from-json"}');
    files.set(ownerA + "/images/custom_stages/from-json.hscript", "json");
    registry(ownerA, '{"tank2":"from-jsonc"}', true);
    files.set(ownerA + "/images/custom_stages/from-jsonc.hscript", "jsonc");
    resolved = result("owner-song", "tank2");
    check(resolved.script == "from-json", "JSONC overrode the primary JSON registry");
    files.remove(ownerA + "/images/custom_stages/custom_stages.json");
    resolved = result("owner-song", "tank2");
    check(resolved.script == "from-jsonc", "JSONC fallback was not used when JSON was absent");

    // Exact keys win even with casefold duplicates. Without an exact key,
    // a single folded key is accepted and multiple folded keys are blocked.
    registry(ownerA, '{"tank2":"exact","TANK2":"upper"}');
    files.set(ownerA + "/images/custom_stages/exact.hscript", "exact");
    files.set(ownerA + "/images/custom_stages/upper.hscript", "upper");
    resolved = result("owner-song", "tank2");
    check(resolved.name == "tank2" && resolved.script == "exact",
      "exact-case registry key lost to casefold matching");
    registry(ownerA, '{"Tank2":"unique"}');
    files.set(ownerA + "/images/custom_stages/unique.hscript", "unique");
    resolved = result("owner-song", "tAnK2");
    check(resolved.name == "Tank2" && resolved.script == "unique",
      "unique casefold registry key was not resolved");
    registry(ownerA, '{"Tank2":"one","TANK2":"two"}');
    resolved = result("owner-song", "tank2");
    check(resolved != null && resolved.unavailable == true
      && resolved.reason == "registry-key-ambiguous",
      "ambiguous casefold owner keys did not block foreign fallback");

    // A present but malformed owner registry is still authoritative.
    registry(ownerA, "not-json");
    resolved = result("owner-song", "tank2");
    check(resolved != null && resolved.unavailable == true
      && resolved.reason == "registry-invalid",
      "malformed owner registry did not return an unavailable sentinel");

    registry(ownerA, '{"tank2":"../global-stage"}');
    var beforeUnsafeScript = calls.length;
    resolved = result("owner-song", "tank2");
    check(resolved != null && resolved.unavailable == true
      && resolved.reason == "script-id-invalid" && resolved.script == ""
      && calls.length == beforeUnsafeScript + 4
      && calls.slice(beforeUnsafeScript).join("|").indexOf("..") < 0,
      "unsafe owner script id did not stop before an out-of-root lookup");

    // A selected foreign engine cannot borrow a supported foreign root.
    manifest("assets/imported_mods/owner-psych", [
      {engine:"Psych Engine", path:"assets/imported_mods/owner-psych"},
      {engine:"Modding Plus", path:ownerA}
    ]);
    check(result("owner-song", "tank2") == null,
      "unsupported selected engine borrowed the foreign Modding Plus registry");

    // Invalid flat ids are rejected before any filesystem callback runs.
    clear();
    check(result("../owner-song", "tank2") == null && calls.length == 0,
      "unsafe song path reached a lookup callback");
    check(result("owner-song", "../tank2") == null && calls.length == 0,
      "unsafe requested stage path reached a lookup callback");
    check(result("owner-song", "folder\\tank2") == null && calls.length == 0,
      "backslash stage path reached a lookup callback");
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp", prefix="imported-stage-registry-") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(temp), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_stage_resolution_precedence_and_unavailable_swap(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(
            extract_method(play, marker)
            for marker in (
                "function manifestOwnedStage(",
                "function registeredStage(",
                "public function swapStage(",
            )
        )
        fixture = r'''import haxe.Json;
import Main.Extensions.Hscript;
using StringTools;

enum Extensions { Hscript; }
class FlxG { public static var camera:Dynamic = {filters:[]}; }
class StageHelper {
  public var name:String;
  public var interp:Dynamic;
  public function new(name:String) this.name = name;
  public function clearStage(_destroy:Bool):Void {}
}
class FNFAssets {
  public static var files:Map<String,String> = new Map();
  public static function exists(path:String, ?_extension:Extensions):Bool return files.exists(path);
  public static function getText(path:String):String {
    if (!files.exists(path)) throw 'missing fixture file: ' + path;
    return files.get(path);
  }
}
class Song {
  public static function storageFolder(chart:Dynamic):String {
    var stored:Dynamic = Reflect.field(chart, 'compatStorageFolder');
    var value = stored == null ? '' : StringTools.trim(Std.string(stored)).toLowerCase();
    if (value != '') return value;
    var title:Dynamic = Reflect.field(chart, 'song');
    return title == null ? '' : StringTools.trim(Std.string(title)).toLowerCase();
  }
}
class CoolUtil { public static function parseJson(raw:String):Dynamic return Json.parse(raw); }
class EngineCompat { public static function resolveStageAlias(name:String):String return name; }
class Main {
  public var SONG:Dynamic = {song:'Improbable Outset', compatStorageFolder:'improbable-outset--codename-engine-d97d25757d'};
  public var curStage:StageHelper = new StageHelper('original');
  public var nightmareVisionScripts:Dynamic=null;
  function swapNightmareVisionStage(name:String):Bool throw 'Unexpected NV route in native/Codename registry fixture';
  public var hscriptStates:Map<String,Dynamic> = new Map();
  public var cleanupCalls:Int = 0;
  public function new() {}
  static var staged = '';
''' + methods + r'''
  function clearRuntimeStage():Void cleanupCalls++;
  function releaseCodenameStageScripts():Void cleanupCalls++;
  function clearHxcStageScopes():Void cleanupCalls++;
  function callHscript(_name:String, _args:Array<Dynamic>, _module:String, _guard:Bool):Void cleanupCalls++;
  function makeHaxeState(_module:String, _directory:String, _script:String):Void {
    cleanupCalls++; hscriptStates.set(_module, {});
  }
  function loadHxcStageCompat():Bool { cleanupCalls++; return true; }
  function setAllHaxeVar(_name:String, _value:Dynamic):Void cleanupCalls++;
  function loadCodenameStageCompat(_name:String):Void cleanupCalls++;
  function reapplyCodenameActors():Void cleanupCalls++;
  function flushPendingHxcCharacterAdded():Void cleanupCalls++;
  function bindGameplayCameras():Void cleanupCalls++;
  function refreshCodenameStageAliases():Void cleanupCalls++;
  function applyCodenameStageStartCamera():Void {}

  static function main():Void {
    var owner = 'assets/imported_mods/owner-a';
    var foreign = 'assets/imported_mods/owner-b';
    var storage = 'improbable-outset--codename-engine-d97d25757d';
    FNFAssets.files.set('assets/data/' + storage + '/compatScripts.json', Json.stringify({
      version:1, selectedRoot:owner,
      roots:[{engine:'Modding Plus',path:owner},
        {engine:'Codename Engine',path:foreign}]
    }));
    // The display title has a separate decoy manifest. Resolution must follow
    // the chart's actual qualified storage folder and selected owner instead.
    FNFAssets.files.set('assets/data/improbable outset/compatScripts.json', Json.stringify({
      version:1, selectedRoot:foreign,
      roots:[{engine:'Codename Engine',path:foreign}, {engine:'Modding Plus',path:owner}]
    }));
    FNFAssets.files.set(owner + '/images/custom_stages/custom_stages.json',
      '{"collision":"owned-stage"}');
    FNFAssets.files.set(foreign + '/images/custom_stages/custom_stages.json',
      '{"collision":"foreign-stage"}');
    FNFAssets.files.set(foreign + '/images/custom_stages/foreign-stage.hscript', 'foreign');
    FNFAssets.files.set('assets/images/custom_stages/custom_stages.json',
      '{"collision":"global-stage"}');
    FNFAssets.files.set('assets/images/custom_stages/global-stage.hscript', 'global');

    var state = new Main();
    var ownedMissing = state.registeredStage('collision');
    if (ownedMissing == null || ownedMissing.name != 'collision'
      || ownedMissing.script != 'owned-stage' || ownedMissing.directory != owner + '/images/custom_stages/'
      || ownedMissing.unavailable != true)
      throw 'PlayState did not resolve the selected owner from the chart storage folder';
    var original = state.curStage;
    if (state.swapStage('collision') || state.curStage != original || state.cleanupCalls != 0)
      throw 'unavailable owned stage swap tore down or replaced the active stage';

    // An absent owner key permits the existing global fallback.
    FNFAssets.files.set(owner + '/images/custom_stages/custom_stages.json', '{"other":"owned-other"}');
    var global = state.registeredStage('collision');
    if (global == null || global.name != 'collision' || global.script != 'global-stage'
      || global.directory != 'assets/images/custom_stages/' || global.unavailable == true)
      throw 'an absent owner key blocked the native global registry fallback';

    // A present but malformed owner registry blocks fallback like a missing
    // owned script, since the owner may contain a collision the game cannot parse.
    FNFAssets.files.set(owner + '/images/custom_stages/custom_stages.json', 'not-json');
    var malformed = state.registeredStage('collision');
    if (malformed == null || malformed.unavailable != true || malformed.reason != 'registry-invalid')
      throw 'malformed owner registry allowed a foreign global fallback';
    if (state.swapStage('collision') || state.curStage != original || state.cleanupCalls != 0)
      throw 'malformed owner registry was not rejected before stage teardown';

    FNFAssets.files.set(owner + '/images/custom_stages/custom_stages.json',
      '{"Room":"Room","room":"room"}');
    FNFAssets.files.set(owner + '/images/custom_stages/Room.hscript','upper');
    FNFAssets.files.set(owner + '/images/custom_stages/room.hscript','lower');
    state.curStage = new StageHelper('Room');
    state.hscriptStates.set('stage', {});
    if (!state.swapStage('room') || state.curStage.name != 'room')
      throw 'case-distinct stage swap incorrectly returned without replacing stage';
    if (!state.swapStage('Room') || state.curStage.name != 'Room')
      throw 'return swap lost the exact owned identity';
    FNFAssets.files.set(owner + '/images/custom_stages/custom_stages.json', '{"Room":"Room"}');
    var swaps = state.cleanupCalls;
    var active = state.curStage;
    if (!state.swapStage('ROOM') || state.curStage != active || state.cleanupCalls != swaps)
      throw 'unique case alias unnecessarily recreated the canonical stage';
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp", prefix="imported-stage-wrapper-") as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            (temp / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
            (temp / "ImportedStageRegistry.hx").write_text(
                (ROOT / "source/ImportedStageRegistry.hx").read_text(encoding="utf-8"),
                encoding="utf-8",
             newline='\n')
            for module in ("CompatScriptManifest", "ImportSongOwnership", "ImportEngine"):
                (temp / (module + ".hx")).write_text(
                    (ROOT / "source" / (module + ".hx")).read_text(encoding="utf-8"),
                    encoding="utf-8",
                 newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(temp), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
