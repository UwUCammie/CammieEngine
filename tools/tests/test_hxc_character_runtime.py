"""Donor-backed guards for actor-local V-Slice/HXC character runtime routing."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


class HxcCharacterRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()
        cls.character = (ROOT / "source/Character.hx").read_text()
        cls.runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        cls.discovery = (ROOT / "source/HxcScriptDiscovery.hx").read_text()
        cls.asset_scope = (ROOT / "source/HxcStateAssetScope.hx").read_text()

    def test_selection_is_character_family_and_actor_local(self):
        source = self.play_state
        self.assertIn("selectedCharacterPaths = hxcCharacterPaths(plan, characterNames)", source)
        self.assertIn("function loadHxcCharacterCompat(characterName:String, characterRole:String,", source)
        self.assertIn("?characterOverride:Character", source)
        self.assertIn("loadedCompatScriptPaths.exists(compatibleScriptIdentity(scriptPath))", source)
        self.assertIn("hxcCharacterScopeNames:Map<String, String>", source)
        self.assertIn("hxcCharacterScopeRoles:Map<String, Array<String>>", source)
        self.assertIn("hxcCharacterScopeIsActive", source)
        self.assertIn("hxcCharacterScopeOwnsNote", source)
        self.assertIn("mustPress", source)
        self.assertIn("hxcCharacterDispatchDepth", source)
        self.assertIn("func_name != 'destroy'", source)
        self.assertIn("interp.variables.set('playSingAnimation'", source)
        self.assertIn("interp.variables.set('isAnimationFinished'", source)
        self.assertIn("var keys:Array<String> = [];", source)
        self.assertIn("var scopes:Array<String> = [];", source)

    def test_character_lifecycle_and_swap_bindings_are_routed(self):
        source = self.play_state
        for token in (
            "callHxcCharacterAdded",
            "dispatchHxcCharacterMethod",
            "loadHxcCharacterCompat(boyfriend.curCharacter, 'boyfriend', boyfriend)",
            "loadHxcCharacterCompat(dad.curCharacter, 'dad', dad)",
            "loadHxcCharacterCompat(gf.curCharacter, 'gf', gf)",
            "setAllHaxeVar('boyfriend', boyfriend)",
            "setAllHaxeVar('dad', dad)",
            "setAllHaxeVar('gf', gf)",
        ):
            self.assertIn(token, source)
        self.assertIn("loadHxcCharacterCompat(newChar.curCharacter, charState, newChar)", source)
        self.assertIn("callHxcCharacterAdded(newChar, charState, newChar)", source)
        self.assertIn("callHxcCharacterAdded(daCharacter, charState, daCharacter)", source)
        self.assertIn("function hxcCharacterForRole(role:String, ?actorOverride:Character", source)
        self.assertIn("var actorForRole = function():Character return hxcCharacterForRole(role);", source)
        self.assertIn("hxcCharacterCallbackActor = actorOverride == null ? actor : actorOverride;", source)
        self.assertIn("hxcCharacterCallbackActor = previousActor;", source)
        self.assertIn("hxcCharacterRole(hxcCharacterCallbackRole) == canonical", source)
        self.assertIn("hxcCharacterScopeNames.clear();", source)
        self.assertIn("hxcCharacterScopeRoles.clear();", source)
        self.assertIn("cachedHxcScriptPlan = null;", source)
        self.assertIn("cachedCompatScriptManifest = null;", source)
        self.assertIn('callAllHScript("noteIncoming", [dunceNote, incomingEvent], true);', source)
        self.assertIn('callHxcNoteHScript("noteIncoming", [dunceNote, incomingEvent]);', source)
        self.assertIn('callHxcNoteHScript("opponentNoteMiss", [note, playerOne, direction, hxcMissEvent]);', source)
        self.assertIn('callHxcNoteHScript(playerOne ? "goodNoteHit" : "opponentNoteHit"', source)

    def test_character_native_operations_dispatch_companion_methods(self):
        source = self.character
        self.assertIn("@:keep public function playSingAnimation(", source)
        self.assertIn("dispatchHxcCharacterMethod(this, 'playAnimation'", source)
        self.assertIn("dispatchHxcCharacterMethod(this, 'playSingAnimation'", source)
        self.assertIn("dispatchHxcCharacterMethod(this, 'dance'", source)
        self.assertIn("dispatchHxcCharacterMethod(this, 'onAnimationFinished'", source)
        self.assertIn("hxcFinishedAnimation", source)

    def test_character_screen_and_gameover_hooks_use_native_runtime_boundaries(self):
        self.assertIn("hxcBaseScreenPosition", self.character)
        self.assertIn("dispatchHxcCharacterScreenPosition", self.character)
        self.assertIn("getCurrentAnimationOffset", self.character)
        self.assertIn("addHxcAtlasAnimations", self.character)
        self.assertIn("characterBaseScreenPosition", self.runtime)
        self.assertIn("characterAnimationOffset", self.runtime)
        self.assertIn("addCharacterAtlasAnimations", self.runtime)
        self.assertIn("dispatchHxcCharacterScreenPosition", self.play_state)

    def test_character_info_scripts_load_before_countdown_and_native_media_fallback_is_explicit(self):
        # FPS Plus CharacterInfo scripts are discovered while each actor is
        # constructed. Waiting for startCountdown leaves the opening with the
        # emergency Dad visual even though the imported HXC definition is
        # present. The loader remains identity-deduplicated when the full
        # compatibility pass runs later.
        loader = self.play_state[self.play_state.index("function loadHxcCharacterCompat"):
                                 self.play_state.index("function getHxcScriptPlan")]
        self.assertNotIn("!hxcCompatScriptsLoaded", loader)
        self.assertIn("loadHxcCompatScripts() skips its identity", loader)
        # The importer namespaces HXC code, but shared donor media is often
        # copied into assets/images. The selected manifest is tried first and
        # the native asset resolver is an explicit, bounded second source.
        self.assertIn("nativeAssetPath('images/' + clean + '.png')", self.asset_scope)
        self.assertIn("nativeAssetPath('images/' + clean + '.xml')", self.asset_scope)
        self.assertIn("FNFAssets.exists(candidate)", self.asset_scope)

    def test_early_character_hxc_load_does_not_dereference_strum_line(self):
        # addCharacter() loads HXC CharacterInfo before PlayState.create() has
        # constructed strumLine.  The shared script ABI must therefore expose
        # a safe initial value and let the normal live value take over later.
        self.assertGreaterEqual(
            self.play_state.count('strumLine == null ? 0 : strumLine.y'), 2,
        )

    def test_complete_manifest_character_info_does_not_report_transient_registry_miss(self):
        # The native Character is constructed before the selected HXC companion
        # runs its generated onAdd bridge.  Only a complete CharacterInfo atlas
        # may defer the diagnostic; a script name by itself must not turn a
        # genuinely missing dependency into a playable character.
        self.assertIn("hasPendingHxcCharacterVisual", self.character)
        self.assertIn("PlayState.instance.hasPendingHxcCharacterVisual", self.character)
        self.assertIn("hxcCharacterDefinitionHasAtlas", self.play_state)
        self.assertIn("HxcCompat.analyze(source, scriptPath)", self.play_state)
        self.assertIn("definition.characterDefinition == null", self.play_state)
        self.assertIn("HxcStateAssetScope.scopedAssetPath(root, 'images/' + clean + '.png')", self.play_state)
        self.assertIn("HxcStateAssetScope.scopedAssetPath(root, 'images/' + clean + '.xml')", self.play_state)
        self.assertIn("return scopedImage != null && scopedMetadata != null", self.play_state)
        self.assertIn("pendingHxcCharacterVisuals.set(key, true)", self.play_state)
        self.assertIn("pendingHxcCharacterVisuals.clear()", self.play_state)

    def test_role_helpers_follow_swaps_and_scope_pending_on_add_actor(self):
        """Execute production role routing across initial load, swap, and onAdd.

        addCharacter() intentionally loads the companion before assigning the
        new Character to gf/dad/boyfriend. The extracted production methods
        verify that normal helpers follow the live slot while the pending
        actor is exposed only during onAdd, then restored even if dispatch
        throws. Game-over's temporary boyfriend keeps its existing precedence.
        """
        def extract_method(source, marker):
            start = source.index(marker)
            opening = source.index("{", start)
            depth = 0
            for index in range(opening, len(source)):
                if source[index] == "{":
                    depth += 1
                elif source[index] == "}":
                    depth -= 1
                    if depth == 0:
                        return source[start:index + 1]
            raise AssertionError("unterminated method: " + marker)

        role_method = extract_method(self.play_state, "function hxcCharacterRole(role:String):String")
        resolver_method = extract_method(
            self.play_state,
            "function hxcCharacterForRole(role:String, ?actorOverride:Character",
        )
        # Character is deliberately erased only for this interpreter fixture;
        # the extracted control flow and pending override are production code.
        role_method = re.sub(r"\bCharacter\b", "Dynamic", role_method)
        resolver_method = re.sub(r"\bCharacter\b", "Dynamic", resolver_method)
        callback_method = extract_method(
            self.play_state,
            "function callHxcCharacterAdded(actor:Character, role:String",
        )
        dispatch_added_method = extract_method(
            self.play_state,
            "function dispatchHxcCharacterAdded(actor:Character, role:String",
        )
        flush_added_method = extract_method(
            self.play_state,
            "function flushPendingHxcCharacterAdded():Void",
        )
        callback_method = re.sub(r"\bCharacter\b", "Dynamic", callback_method)
        dispatch_added_method = re.sub(r"\bCharacter\b", "Dynamic", dispatch_added_method)
        main = f'''import HxcCharacterLifecycleQueue.HxcCharacterLifecycleCall;
class EngineCompat {{
  public static function hxcLifecyclePayload(kind:String, values:Dynamic):Dynamic return values;
}}
class Actor {{
  public var id:String;
  public var frames:Dynamic;
  public function new(id:String) this.id = id;
}}
class Main {{
  public function new() {{}}
  var boyfriend:Dynamic;
  var gf:Dynamic;
  var dad:Dynamic;
  var hxcGameOverCharacter:Dynamic;
  var hxcCharacterCallbackActor:Dynamic;
  var hxcCharacterCallbackRole:String = "";
  var hxcCharacterScopeNames:Map<String, String> = new Map();
  var curStage:Dynamic;
  var pendingHxcCharacterAdds:HxcCharacterLifecycleQueue = new HxcCharacterLifecycleQueue();
  var callbackActor:Dynamic;
  var throwOnAdd:Bool = false;
{role_method}
{resolver_method}
  function hxcCharacterScopeIsActive(scope:String, ?actorOverride:Dynamic, ?overrideRole:String):Bool return true;
  function hxcCharacterForScope(scope:String, ?actorOverride:Dynamic, ?overrideRole:String):Array<Dynamic>
    return actorOverride == null ? [] : [actorOverride];
  function callHscript(name:String, args:Array<Dynamic>, scope:String, optional:Bool):Bool {{
    callbackActor = hxcCharacterForRole("boyfriend");
    if (throwOnAdd) throw "onAdd failed";
    return true;
  }}
{callback_method}
{dispatch_added_method}
{flush_added_method}
  static function fail(value:String):Void throw value;
  function run():Void {{
    var first = new Actor("first-bf");
    first.frames = new Actor("sheet");
    boyfriend = first;
    // Generated helper closures capture the role, not the actor instance.
    var hxcCharacter = function():Dynamic return hxcCharacterForRole("boyfriend");
    if (hxcCharacter() != first) fail("initial actor binding");

    hxcCharacterScopeNames.set("bf-scope", "bf");
    var pending = new Actor("pending-bf");
    pending.frames = new Actor("sheet");
    callHxcCharacterAdded(pending, "boyfriend", pending);
    callHxcCharacterAdded(pending, "boyfriend", null);
    if (pendingHxcCharacterAdds.length != 1) fail("initial actor onAdd was not queued once");
    if (callbackActor != null) fail("onAdd ran before stage setup");
    curStage = {{}};
    flushPendingHxcCharacterAdded();
    if (callbackActor != pending) fail("onAdd did not bind the pending actor");
    if (pendingHxcCharacterAdds.length != 0) fail("stage-ready flush retained pending callbacks");
    if (hxcCharacterCallbackActor != null || hxcCharacterCallbackRole != "")
      fail("onAdd callback binding was not restored");

    boyfriend = pending;
    if (hxcCharacter() != pending) fail("live slot did not follow the installed actor");
    var replacement = new Actor("replacement-bf");
    replacement.frames = new Actor("sheet");
    boyfriend = replacement;
    if (hxcCharacter() != replacement) fail("stale captured actor survived replacement");

    hxcGameOverCharacter = new Actor("game-over-bf");
    hxcGameOverCharacter.frames = new Actor("sheet");
    if (hxcCharacter() != hxcGameOverCharacter) fail("game-over actor binding");

    throwOnAdd = true;
    var didThrow = false;
    try callHxcCharacterAdded(pending, "boyfriend", pending) catch (_:Dynamic) didThrow = true;
    if (!didThrow) fail("onAdd failure fixture did not throw");
    if (hxcCharacterCallbackActor != null || hxcCharacterCallbackRole != "")
      fail("onAdd failure leaked its temporary actor binding");
    if (hxcCharacter() != hxcGameOverCharacter) fail("failure changed game-over binding");
  }}
  static function main() new Main().run();
}}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(temp), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_fps_plus_character_definitions_keep_their_native_visual_metadata(self):
        paths = [
            DONOR / "whitty/data/characters/WhitBonkers.hxc",
            DONOR / "whitty/data/characters/GfStandingScared.hxc",
        ]
        if not all(path.is_file() for path in paths):
            self.skipTest("mounted ballistic HXC character donors are unavailable")
        encoded = ",\n".join(
            'sys.io.File.getContent("' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '")'
            for path in paths
        )
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var paths = [{encoded}];
    var names = ["WhitBonkers", "GfStandingScared"];
    var sprites = ["characters/WhittyCrazy", "characters/GF_Standing_Sway"];
    for (index in 0...paths.length) {{
      var result = HxcCompat.analyze(paths[index], "scripts/characters/" + names[index] + ".hxc");
      if (result.kind != "character" || result.characterDefinition == null)
        fail("missing CharacterInfo metadata for " + names[index]);
      if (result.characterDefinition.spritePath != sprites[index])
        fail("wrong sprite path for " + names[index] + ": " + result.characterDefinition.spritePath);
      if (result.generatedHscript.indexOf("HxcCompatRuntime.applyCharacterInfo") < 0)
        fail("missing native CharacterInfo bridge for " + names[index]);
    }}
  }}
}}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(temp), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_discovery_exposes_stable_character_matching(self):
        source = self.discovery
        self.assertIn("public static function characterId(path:String):String", source)
        self.assertIn("public static function characterMatches(path:String, names:Array<String>):Bool", source)
        self.assertIn("familyForPath(path) != 'character'", source)
        self.assertIn("public static function selectCharacterPaths", source)
        self.assertIn("selectedRoot:String", source)

    def test_same_id_uses_one_manifest_owner_across_swaps(self):
        main = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var roots = [
      "assets/scripts",
      "assets/imported_mods/pack-a",
      "assets/imported_mods/pack-b"
    ];
    // Deliberately put pack B first to prove selection does not depend on
    // discovery/filesystem enumeration order.
    var paths = [
      "assets/imported_mods/pack-b/scripts/characters/bf.hxc",
      "assets/imported_mods/pack-a/scripts/characters/bf.hxc",
      "assets/imported_mods/pack-b/scripts/characters/unique-b.hxc",
      "assets/imported_mods/pack-a/scripts/characters/unique-a.hxc"
    ];
    var selected = HxcScriptDiscovery.selectCharacterPaths(paths,
      ["bf", "unique-a", "unique-b"], roots, "assets/imported_mods/pack-a");
    if (selected.length != 3) fail("expected one path per character id: " + selected.length);
    if (selected.indexOf("assets/imported_mods/pack-a/scripts/characters/bf.hxc") < 0)
      fail("selected owner did not win duplicate bf");
    if (selected.indexOf("assets/imported_mods/pack-b/scripts/characters/bf.hxc") >= 0)
      fail("duplicate bf crossed manifest roots");
    if (selected.indexOf("assets/imported_mods/pack-b/scripts/characters/unique-b.hxc") < 0
      || selected.indexOf("assets/imported_mods/pack-a/scripts/characters/unique-a.hxc") < 0)
      fail("unique companion was lost during selection");

    // A character swap reuses the same owner rule; loading the id again can
    // never introduce the sibling-root duplicate.
    var swapped = HxcScriptDiscovery.selectCharacterPaths(paths, ["bf"], roots,
      "assets/imported_mods/pack-a");
    if (swapped.length != 1 || swapped[0] != "assets/imported_mods/pack-a/scripts/characters/bf.hxc")
      fail("character swap changed manifest ownership");

    // Runtime discovery returns FileSystem.fullPath() values; manifests keep
    // safe destination-relative roots. The same owner must win there too.
    var absolutePaths = [for (path in paths) Sys.getCwd() + "/" + path];
    var absoluteSelected = HxcScriptDiscovery.selectCharacterPaths(absolutePaths,
      ["bf"], roots, "assets/imported_mods/pack-a");
    if (absoluteSelected.length != 1
      || absoluteSelected[0].indexOf("/assets/imported_mods/pack-a/") < 0)
      fail("absolute discovery path lost manifest ownership");
  }
}'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            (temp / "HxcScriptDiscovery.hx").write_text(self.discovery)
            (temp / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(temp), "--run", "Main"],
                cwd=temp,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_character_donors_cover_note_and_lifecycle_hooks(self):
        rabbit = DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/characters/bf-rabbit.hxc"
        bf_tb = DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/characters/bf_tb.hxc"
        doki = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/bf-doki.hxc"
        if not all(path.is_file() for path in (rabbit, bf_tb, doki)):
            self.skipTest("mounted HXC character donors are unavailable")
        rabbit_text = rabbit.read_text(errors="ignore")
        bf_tb_text = bf_tb.read_text(errors="ignore")
        doki_text = doki.read_text(errors="ignore")
        self.assertIn("class BFRabbit", rabbit_text)
        self.assertIn("function onNoteHit", rabbit_text)
        self.assertIn("class BFTB", bf_tb_text)
        self.assertIn("function onNoteHit", bf_tb_text)
        self.assertIn("function onCreate", doki_text)
        self.assertIn("function playAnimation", doki_text)
        self.assertIn("onAnimationFinished", doki_text)


if __name__ == "__main__":
    unittest.main()
