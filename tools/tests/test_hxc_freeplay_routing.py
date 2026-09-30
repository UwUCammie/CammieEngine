"""Focused isolation fixtures for native Freeplay HXC routing."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class HxcFreeplayRoutingTest(unittest.TestCase):
    def test_runtime_uses_native_song_metadata_field(self):
        source = (ROOT / "source/HxcFreeplayRuntime.hx").read_text()
        # FreeplayState.JsonMetadata exposes the registry id as `name`; the
        # separate SongMetadata runtime type is the one that has songName.
        self.assertIn("song.name", source)
        self.assertNotIn("song.songName", source)

    def test_manifest_roots_gate_callbacks_and_sibling_modules(self):
        main = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var rootSongs:Map<String, Array<String>> = new Map();
    var rootA = "assets/imported_mods/donor-a";
    var rootB = "assets/imported_mods/donor-b";
    HxcFreeplayRouting.associateSong(rootSongs, rootA, "Donor-A Song");
    HxcFreeplayRouting.associateSong(rootSongs, rootB, "Donor-B Song");

    // A selection payload from donor A can reach A, but never B. An omitted
    // capsule cannot accidentally broadcast into either imported namespace.
    if (!HxcFreeplayRouting.scopeMatches(false, rootSongs.get(rootA), "donor-a-song"))
      fail("donor A callback was filtered");
    if (HxcFreeplayRouting.scopeMatches(false, rootSongs.get(rootB), "donor-a-song"))
      fail("donor B callback leaked into donor A selection");
    if (HxcFreeplayRouting.scopeMatches(false, rootSongs.get(rootA), ""))
      fail("unidentified selection reached imported root");
    if (!HxcFreeplayRouting.scopeMatches(true, [], "donor-a-song"))
      fail("destination-global callback was filtered");

    var payload = {capsule:{name:"Donor-B Song"}};
    if (HxcFreeplayRouting.selectedSong(payload) != "donorbsong")
      fail("capsule song extraction");

    var modules:Map<String, Map<String, Dynamic>> = new Map();
    var modulesA:Map<String, Dynamic> = new Map();
    var modulesB:Map<String, Dynamic> = new Map();
    var globals:Map<String, Dynamic> = new Map();
    modulesA.set(HxcFreeplayRouting.normalizeSong("SharedModule"), "A");
    modulesB.set(HxcFreeplayRouting.normalizeSong("SharedModule"), "B");
    globals.set(HxcFreeplayRouting.normalizeSong("GlobalModule"), "global");
    modules.set(rootA, modulesA);
    modules.set(rootB, modulesB);
    modules.set("assets/scripts", globals);

    if (HxcFreeplayRouting.moduleLookup(modules, rootA, "assets/scripts", "SharedModule") != "A")
      fail("A sibling lookup");
    if (HxcFreeplayRouting.moduleLookup(modules, rootB, "assets/scripts", "SharedModule") != "B")
      fail("B sibling lookup");
    if (HxcFreeplayRouting.moduleLookup(modules, rootA, "assets/scripts", "OnlyB") != null)
      fail("cross-root sibling lookup leaked");
    if (HxcFreeplayRouting.moduleLookup(modules, rootA, "assets/scripts", "global:GlobalModule") != "global")
      fail("explicit global lookup");
    if (HxcFreeplayRouting.moduleLookup(modules, rootA, "assets/scripts", "GlobalModule") != null)
      fail("implicit global lookup bypassed explicit boundary");
  }
}'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(temp),
                "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_uses_manifest_root_routing(self):
        runtime = (ROOT / "source/HxcFreeplayRuntime.hx").read_text()
        self.assertIn("HxcFreeplayRouting.scopeMatches", runtime)
        self.assertIn("HxcFreeplayRouting.selectedSong", runtime)
        self.assertIn("HxcFreeplayRouting.moduleLookup", runtime)
        self.assertIn("associatedSongs", runtime)
        self.assertIn("addRoot(roots, destinationRoot, true)", runtime)
        self.assertIn("HxcFreeplayRouting.associateSong(rootSongs", runtime)
        # Translated V-Slice Freeplay modules call helpers with hxcAssetRoot
        # while their top-level body runs, before any song is selected.
        self.assertIn("seedInterpreter(interp, scope);\n\t\t\tinterp.execute(program);", runtime)
        self.assertIn("interp.variables.set('hxcAssetRoot', scope == null ? '' : scope.root);", runtime)

    def test_module_load_and_callback_see_their_manifest_asset_root(self):
        source = (ROOT / "source/HxcFreeplayRuntime.hx").read_text()
        seed = extract_method(source, "function seedInterpreter(interp:Interp, scope:HxcFreeplayScope):Void")
        fixture = '''import hscript.Interp;
import hscript.Parser;
typedef HxcFreeplayScope = { var root:String; };
class FreeplayState { public function new() {} }
class PlayState {}
class CreditsState {}
class SaveDataState {}
class HxcStateAssetScope {
  public static function paths(root:String):Dynamic return {assetRoot:root};
}
class HxcCompatRuntime {
  public static var freeplayPlaySound:Dynamic = function() {};
  public static var freeplayPlayMusic:Dynamic = function() {};
  public static function hxcCoalesce(a:Dynamic, b:Dynamic):Dynamic return a == null ? b : a;
  public static function hxcMap(entries:Array<Dynamic>):Dynamic return entries;
}
class HxcStateFactory {
  public static function stateInit(root:String, name:Dynamic):Dynamic return null;
  public static function subStateInit(root:String, name:Dynamic):Dynamic return null;
  public static function stateFactory(root:String, name:Dynamic, args:Array<Dynamic>):Dynamic return null;
  public static function switchStateScoped(root:String, target:Dynamic):Bool return false;
  public static function startExitState(root:String, target:Dynamic):Bool return false;
  public static function openSubStateScoped(root:String, host:Dynamic, target:Dynamic):Bool return false;
  public static function back(owner:Dynamic):Bool return false;
  public static var resetState:Dynamic = function() {};
}
class HxcDeferredValue { public function new(resolve:Void->Dynamic) {} }
class Main {
  static var HscriptGlobals:Dynamic = {};
  var owner:FreeplayState = new FreeplayState();
  public function new() {}
  function moduleProxy(caller:HxcFreeplayScope, name:Dynamic):Dynamic return null;
''' + seed + '''
  static function main():Void {
    var runtime = new Main();
    for (root in ["assets/imported_mods/wacky-world", "assets/imported_mods/other-donor"]) {
      var interp = new Interp();
      runtime.seedInterpreter(interp, {root:root});
      interp.execute(new Parser().parseString(
        "if (hxcAssetRoot != \\\"" + root + "\\\") throw 'module initializer lost its manifest asset root'; "
        + "function update(event) { return hxcAssetRoot; }"));
      var update:Dynamic = interp.variables.get("update");
      var callbackRoot:Dynamic = Reflect.callMethod(null, update, [null]);
      if (callbackRoot != root)
        throw "Freeplay callback lost its owner asset root: " + root;
      var paths:Dynamic = interp.variables.get("Paths");
      if (Reflect.field(paths, "assetRoot") != root)
        throw "Paths proxy did not use the same manifest owner: " + root;
    }
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder)
            (path / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(HSCRIPT), "-cp", str(path), "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_duplicate_module_identity_uses_selected_manifest_owner(self):
        runtime = (ROOT / "source/HxcFreeplayRuntime.hx").read_text()
        # A repaired song may retain an older compatibility namespace.  The
        # selected root must own a same-named Freeplay module; otherwise both
        # translated callbacks fire for one selection.
        self.assertIn("rootPriorityBySong", runtime)
        self.assertIn("CompatScriptManifest.rootsInPrecedence(manifest)", runtime)
        self.assertIn("function scopeOwnsIdentity", runtime)
        self.assertIn("if (!scopeOwnsIdentity(scope, selectedSong))", runtime)
        self.assertIn("candidate.identity != scope.identity", runtime)

if __name__ == "__main__":
    unittest.main()
