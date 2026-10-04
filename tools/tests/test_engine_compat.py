from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


class EngineCompatibilityTest(unittest.TestCase):
    def test_note_callback_reads_class_properties_instead_of_anonymous_field_presence(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            folder = Path(directory)
            (folder / "Main.hx").write_text(r'''class PropertyNote {
 public var ID = 97;
 public var noteData(get, never):Int;
 function get_noteData():Int return 0;
 public var isSustainNote(get, never):Bool;
 function get_isSustainNote():Bool return false;
 public var coolId(get, never):String;
 function get_coolId():String return "source-kind";
 public function new() {}
}
class Main {
 static function main() {
  var head = new PropertyNote();
  if (Reflect.hasField(head, "noteData")) throw "fixture must exercise property presence difference";
  var live:Array<Dynamic> = [{noteData:1,isSustainNote:true}, null, head];
  var args = EngineCompat.callbackArguments("goodNoteHit", "goodNoteHit", [head,true], false, live);
  if (args[0]!=2 || args[1]!=0 || args[2]!="source-kind" || args[3]!=false)
   throw "class note callback did not preserve index/direction/type/sustain: " + args;
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder),
                                     "--run", "Main"], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_window_icons_report_owner_scoped_source_dependencies(self):
        source = (ROOT / "source/HxcWindowCompat.hx").read_text()
        self.assertIn("EngineCompat.planVisualFallback('window-icon'", source)
        self.assertIn("'unresolved-source-dependency'", source)
        self.assertIn("EngineCompat.reportVisualFallback(diagnostic)", source)
        self.assertIn("HxcWindowCompat.setIcon(icon, hxcWindowOrigin)",
                      (ROOT / "source/PlayState.hx").read_text())

    def test_loaded_psych_flash_handler_owns_legacy_event_dispatch(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        discovery = source[source.index("function loadPsychCompatScripts(") : source.index(
            "function hxcScriptMatches(", source.index("function loadPsychCompatScripts(")
        )]
        self.assertIn("hscriptStates.get(scriptScope).variables.exists('onEvent')", discovery)
        self.assertIn("psychFlashEventScopes.set(scriptScope, true);", discovery)

        events = source[source.index("function fireSongEvent(") : source.index(
            "\n\tprivate function generateSong(", source.index("function fireSongEvent(")
        )]
        script_dispatch = events.index("callAllHScript('onEvent'")
        custom_owner_check = events.index("EngineCompat.psychFlashScriptOwnsLegacyEvent(")
        native_route = events.index("EngineCompat.routeLegacyEvent(")
        self.assertLess(script_dispatch, custom_owner_check)
        self.assertLess(custom_owner_check, native_route)
        self.assertIn("psychFlashEventScopes.keys().hasNext()", events)

    def test_psych_custom_event_callback_owner_requires_live_matching_function(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        method_start = source.index("function psychCustomEventHasCallback(")
        method_end = source.index("\n\tfunction fireNativeSongEvent(", method_start)
        method = source[method_start:method_end].strip()
        compat = (ROOT / "source/EngineCompat.hx").read_text()
        fallback_start = compat.index("public static function psychCustomEventOwnsNativeFallback(")
        fallback_end = compat.index("\npublic static function lyricActor(", fallback_start)
        fallback = compat[fallback_start:fallback_end].strip()
        event_dispatch = source[source.index("function fireNativeSongEvent("):source.index(
            "\n\tprivate function generateSong(", source.index("function fireNativeSongEvent(")
        )]
        script_dispatch = event_dispatch.index("callAllHScript('onEvent'")
        custom_owner_check = event_dispatch.index("EngineCompat.psychCustomEventOwnsNativeFallback(")
        native_route = event_dispatch.index("EngineCompat.routeLegacyEvent(")
        self.assertLess(script_dispatch, custom_owner_check)
        self.assertLess(custom_owner_check, native_route)
        self.assertIn("psychCustomEventHasCallback(e.name)", event_dispatch)
        fixture = f'''class MockInterp {{
 public var variables:Map<String, Dynamic> = [];
 public function new() {{}}
}}
class EngineCompat {{
 {fallback}
}}
class Main {{
 var psychCustomEventScopes:Map<String, String> = [];
 var hscriptStates:Map<String, MockInterp> = [];
 {method}
 public function new() {{}}
 static function fail(message:String):Void throw message;
 static function main():Void {{
  var builtinPsychEvents:Array<String> = ["Dadbattle Spotlight", "Hey!", "Set GF Speed",
   "Philly Glow", "Kill Henchmen", "Add Camera Zoom", "Trigger BG Ghouls",
   "Play Animation", "Camera Follow Pos", "Alt Idle Animation", "Screen Shake",
   "Change Character", "BG Freaks Expression", "Change Scroll Speed", "Set Property", "Play Sound"];
  for (eventName in builtinPsychEvents)
   if (EngineCompat.psychCustomEventOwnsNativeFallback(eventName, true))
    fail("canonical Psych event became custom-owned: " + eventName);
  if (!EngineCompat.psychCustomEventOwnsNativeFallback("Custom Glow", true)
   || EngineCompat.psychCustomEventOwnsNativeFallback("Custom Glow", false)
   || !EngineCompat.psychCustomEventOwnsNativeFallback("Goodbye Hud", true)
   || !EngineCompat.psychCustomEventOwnsNativeFallback("Flash", true))
   fail("loaded non-built-in custom event did not own its native fallback");
  if (!EngineCompat.psychCustomEventOwnsNativeFallback("Camera Follow Position", true)
   || !EngineCompat.psychCustomEventOwnsNativeFallback("SetProperty", true)
   || !EngineCompat.psychCustomEventOwnsNativeFallback("AddCamZoomPsych", true))
   fail("a noncanonical legacy alias did not remain custom-owned");

  var game = new Main();
  var live = new MockInterp();
  live.variables.set("onEvent", function() {{}});
  game.psychCustomEventScopes.set("custom-event:goodbye hud", "goodbye hud");
  game.hscriptStates.set("custom-event:goodbye hud", live);
  if (!game.psychCustomEventHasCallback(" Goodbye Hud ")
   || !game.psychCustomEventHasCallback("GOODBYE HUD"))
   fail("same-named live function handler did not own event");

  live.variables.set("__compatClosed", true);
  if (game.psychCustomEventHasCallback("Goodbye Hud"))
   fail("closed event interpreter still owned native fallback");
  live.variables.remove("__compatClosed");

  game.hscriptStates.remove("custom-event:goodbye hud");
  if (game.psychCustomEventHasCallback("Goodbye Hud"))
   fail("removed event interpreter still owned native fallback");

  live.variables.set("onEvent", "not a callback");
  game.hscriptStates.set("custom-event:goodbye hud", live);
  if (game.psychCustomEventHasCallback("Goodbye Hud"))
   fail("non-function event binding still owned native fallback");

  live.variables.set("onEvent", function() {{}});
  game.psychCustomEventScopes.clear();
  game.psychCustomEventScopes.set("custom-event:flash", "flash");
  if (game.psychCustomEventHasCallback("Goodbye Hud"))
   fail("unrelated custom-event scope claimed another event");
  if (game.psychCustomEventHasCallback(null))
   fail("null event name matched a custom handler");
  trace("psych-custom-event-callback-owner-ok");
 }}
}}'''
        with tempfile.TemporaryDirectory(prefix="psych-event-owner-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("psych-custom-event-callback-owner-ok", result.stdout)

    def test_alias_table_compiles_and_routes_donor_spellings(self):
        fixture = r'''
class EngineCompatTest {
	static function fail(message:String):Void throw message;
	static function main() {
		if (EngineCompat.resolveStageAlias("halloween") != "spooky") fail("halloween stage alias");
		if (EngineCompat.resolveStageAlias("schoolEvilErect") != "schoolEvil") fail("V-Slice erect stage alias");
		if (EngineCompat.stageVariantId("schoolEvilErect") != 1) fail("V-Slice erect stage variant");
		if (!EngineCompat.isBuiltinStageReference("schoolEvilErect")) fail("V-Slice erect built-in stage");
		if (EngineCompat.resolveStageAlias("schoolEvil") != "schoolEvil"
			|| EngineCompat.stageVariantId("schoolEvil") != 0)
			fail("normal school evil stage must remain unchanged");
		var psychSourceStage = EngineCompat.resolveStageResolution("phillyStreets");
		if (psychSourceStage.nativeName != "philly-streets" || psychSourceStage.stageID != 0
			|| psychSourceStage.standard)
			fail("Psych compiled phillyStreets may use only fallback visuals, not claim class compatibility");
		var psychSourceStageNames = EngineCompat.stageLookupNames("phillyStreets");
		if (psychSourceStageNames.length != 2 || psychSourceStageNames[0] != "phillyStreets"
			|| psychSourceStageNames[1] != "philly-streets")
			fail("Psych source stage lookup must retain the authored id and resolve its native implementation");
		if (EngineCompat.resolveStageResolution("phillyBlazin").standard)
			fail("a Psych source stage without a native implementation must stay unresolved");
		var psychStageFallback = EngineCompat.planVisualFallback("stage", "phillyStreets",
			"selected Psych compiled stage class PhillyStreets", ["source/states/stages/PhillyStreets.hx"],
			"compiled stage class behavior is unsupported", "unsupported-engine-behavior");
		if (psychStageFallback.fallback != "philly-streets"
			|| psychStageFallback.diagnostic.code != "unsupported-engine-dependency")
			fail("native Philly Streets visuals must be labeled as fallback for unsupported source behavior");
		var missingWindowIcon = EngineCompat.planVisualFallback("window-icon", "dokicon.png",
			"assets/imported_mods/ddto/scripts/modules/CustomTitleBar.hxc",
			["assets/imported_mods/ddto/dokicon.png"],
			"the window keeps its current icon; chart gameplay continues", "unresolved-source-dependency");
		if (missingWindowIcon.diagnostic.code != "missing-donor-dependency"
			|| missingWindowIcon.diagnostic.classification != "unresolved-source-dependency"
			|| missingWindowIcon.diagnostic.origin.indexOf("CustomTitleBar.hxc") < 0
			|| missingWindowIcon.diagnostic.searched[0].indexOf("/ddto/dokicon.png") < 0
			|| missingWindowIcon.fallback != "current-window-icon")
			fail("missing HXC window icon must retain owner provenance as a source dependency");
		var erectResolution = EngineCompat.resolveStageResolution("schoolEvilErect");
		if (erectResolution.nativeName != "schoolEvil" || erectResolution.stageID != 1 || !erectResolution.standard)
			fail("V-Slice stage resolution");
		var stageNames = EngineCompat.stageLookupNames("halloween");
		if (stageNames.length != 2 || stageNames[0] != "halloween" || stageNames[1] != "spooky")
			fail("stage lookup aliases");
		var erectNames = EngineCompat.stageLookupNames("schoolEvilErect");
		if (erectNames.length != 2 || erectNames[0] != "schoolEvilErect" || erectNames[1] != "schoolEvil")
			fail("V-Slice erect stage lookup aliases");
		if (EngineCompat.resolveLegacyAssetPath("assets/images/BOYFRIEND.png")
			!= "assets/images/custom_chars/bf/char.png") fail("legacy BF atlas alias");
		if (EngineCompat.resolveLegacyAssetPath("assets/shared/characters/BOYFRIEND.xml")
			!= "assets/images/custom_chars/bf/char.xml") fail("shared BF atlas alias");
		if (EngineCompat.resolveLegacyAssetPath("assets/images/custom_chars/foo/BOYFRIEND.png")
			!= "assets/images/custom_chars/foo/BOYFRIEND.png") fail("over-broad BF atlas alias");
		if (EngineCompat.resolveStageAlias("bedroom") != "bedroom"
			|| EngineCompat.resolveLegacyAssetPath("bedroom/dark") != "bedroom/dark")
			fail("unrelated donor data must remain unresolved");
		var rewritten = EngineCompat.rewriteLegacyAssetPaths(
			"FlxAtlasFrames.fromSparrow('assets/images/BOYFRIEND.png', 'assets/images/BOYFRIEND.xml');");
		if (rewritten.indexOf("assets/images/BOYFRIEND") >= 0
			|| rewritten.indexOf("assets/images/custom_chars/bf/char.png") < 0
			|| rewritten.indexOf("assets/images/custom_chars/bf/char.xml") < 0)
			fail("legacy BF source rewrite");
		var scoped = EngineCompat.rewriteScopedAssetPaths('Assets.getText(Paths.frag("blend"));');
		if (scoped.indexOf('hxcAssets.getText(hxcPaths.frag("blend"))') < 0)
			fail("HXC Paths/Assets scope rewrite");
		var update = EngineCompat.callbackNames("update");
		if (update[0] != "update" || update[1] != "onUpdate") fail("update callback alias");
		var create = EngineCompat.callbackNames("start");
		if (create[1] != "onCreate") fail("create callback alias");
		var pause = EngineCompat.callbackNames("onPause");
		if (pause[0] != "onPause" || pause[1] != "pause") fail("donor pause callback alias");
		var retry = EngineCompat.callbackNames("songRetry");
		if (retry[0] != "songRetry" || retry[1] != "onSongRetry") fail("retry callback alias");
		var countdownHook = EngineCompat.callbackNames("startCountdown");
		if (countdownHook.length != 1 || countdownHook[0] != "onStartCountdown")
			fail("engine startCountdown helper must not be broadcast as a callback");
		if (EngineCompat.callbackArguments("start", "onCreate", ["song"]).length != 0)
			fail("onCreate must receive its native zero-argument signature");
		if (EngineCompat.callbackArguments("countdownTick", "onCountdownTick", [3, null]).length != 1)
			fail("onCountdownTick argument adapter");
		var timerArgs = EngineCompat.callbackArguments("timerCompleted", "onTimerCompleted", ["tag", 2, 1]);
		if (timerArgs.length != 3 || timerArgs[1] != 2 || timerArgs[2] != 1)
			fail("onTimerCompleted donor signature adapter");
		if (EngineCompat.luaStringFormat("%02X:%02d:%.1f:%s:%%", 15, 3, 1.25, "ok") != "0F:03:1.3:ok:%")
			fail("Lua string.format adapter");
		var list:Array<Dynamic> = ["a", "b"];
		if (EngineCompat.luaTableLength(list) != 2 || EngineCompat.luaTableKey(list, 2) != 2
			|| EngineCompat.luaTableValue(list, 2) != "b")
			fail("Lua array iteration adapter");
		var object:Dynamic = {first: "x", second: "y"};
		var objectKey = Std.string(EngineCompat.luaTableKey(object, 1));
		if (EngineCompat.luaTableLength(object) != 2
			|| (objectKey != "first" && objectKey != "second")
			|| EngineCompat.luaTableValue(object, "first") != "x"
			|| EngineCompat.luaTableValue(object, "second") != "y")
			fail("Lua object iteration adapter");
		var parts = EngineCompat.luaStringGmatch("a,b,,c", "([^,]+)");
		if (parts.length != 3 || parts[0] != "a" || parts[2] != "c")
			fail("Lua string.gmatch adapter");
		if (EngineCompat.propertyPath("timeTxt.visible") != "timeBar.visible")
			fail("Psych timeTxt alias");
		if (EngineCompat.propertyPath("game.camOther.zoom") != "camOther.zoom") fail("camOther alias");
		if (EngineCompat.propertyPath("camFollowPos.x") != "camFollow.x") fail("follow alias");
		if (EngineCompat.propertyPath("game.opponentStrums") != "enemyStrums") fail("strum alias");
		if (EngineCompat.propertyPath("cameraSpeed") != "camSpeed") fail("camera speed alias");
		if (EngineCompat.propertyPath("camZoomingMult") != "camZoomIntensity") fail("zoom multiplier alias");
		if (EngineCompat.propertyPath("cameraBopMultiplier") != "camZoomIntensity") fail("camera bop property alias");
		if (EngineCompat.eventName("Camera Follow Position") != "Camera Follow Pos") fail("event alias");
		if (EngineCompat.eventName("SetProperty") != "Set Property") fail("property event alias");
		if (EngineCompat.eventName("ZoomCamera") != "Zoom Camera") fail("V-Slice zoom alias");
		if (EngineCompat.eventName("AddCamZoomPsych") != "Add Camera Zoom") fail("Psych zoom alias");
		if (EngineCompat.eventName("AddCameraZoom") != "Add Camera Zoom") fail("legacy add zoom alias");
		if (EngineCompat.eventName("Set Camera Zoom") != "Set Cam Zoom") fail("legacy set zoom alias");
		if (EngineCompat.eventName("charChange") != "Change Character") fail("V-Slice character alias");
		if (EngineCompat.eventName("ChangeCharacterCL") != "Change Character") fail("DDTO character alias");
		if (EngineCompat.eventName("ScrollSpeed") != "Change Scroll Speed") fail("V-Slice scroll alias");
		if (EngineCompat.eventName("SetCameraBop") != "Set Camera Bop") fail("V-Slice bop alias");
		if (EngineCompat.eventName("Flash Camera") != "Camera Flash") fail("V-Slice flash alias");
		if (EngineCompat.eventName("Flash") != "Camera Flash") fail("legacy flash alias");
		if (EngineCompat.eventName("PlayVideo") != "Play Video") fail("V-Slice video alias");
		if (EngineCompat.eventName("extra-events-cameraFadeEvent") != "Camera Fade") fail("V-Slice fade alias");
		if (EngineCompat.eventName("extra-events-addLyricsEvent") != "Lyrics") fail("V-Slice lyrics alias");
		if (EngineCompat.eventName("extra-events-vignEvent") != "Vignette") fail("V-Slice vignette alias");
		if (EngineCompat.eventName("EyePopup") != "Markov Popups") fail("TAKEOVER eye popup alias");
		var eventSource = "class OverlayCueEvent extends ScriptedSongEvent { function new() super('OverlayCue'); function handleEvent(data) { var cueX = data.value.x; var cueY = data.value.y; var cue = new FlxSprite(cueX, cueY); cue.frames = Paths.getSparrowAtlas('ui/overlay'); cue.animation.addByPrefix('pulse', 'Overlay Pulse', 18, false); cue.animation.play('pulse'); cue.scrollFactor.set(0, 0); cue.cameras = [PlayState.instance.camHUD]; cue.animation.finishCallback = function(s:String) { PlayState.instance.remove(cue); cue.kill(); cue = null; }; } }";
		var eventAssets = EngineCompat.eventAssetNamesInSource(eventSource);
		if (eventAssets.length != 1 || eventAssets[0] != "ui/overlay") fail("generic HXC event asset extraction");
		var eventDescriptor = EngineCompat.eventSpriteDescriptorFromSource(eventSource);
		if (eventDescriptor == null || eventDescriptor.canonicalName != "OverlayCue"
			|| eventDescriptor.animationName != "pulse" || eventDescriptor.framePrefix != "Overlay Pulse"
			|| eventDescriptor.xField != "x" || eventDescriptor.yField != "y")
			fail("generic HXC event descriptor extraction");
		if (EngineCompat.eventName("ChangeStage") != "Change Stage") fail("V-Slice stage alias");
		if (EngineCompat.eventName("camZoom") != "Legacy Camera Zoom") fail("FPS zoom alias");
		if (EngineCompat.eventName("camMove") != "Camera Follow Pos") fail("FPS camera move alias");
		if (EngineCompat.eventName("toggleCamMovement") != "Toggle Camera Movement") fail("FPS movement alias");
		if (EngineCompat.eventName("Camera Target") != "Camera Target") fail("camera target alias");
		if (EngineCompat.eventName("Camera Zoom Hold") != "Set Cam Zoom") fail("camera hold alias");
		if (EngineCompat.eventName("ClearLyrics") != "Clear Lyrics") fail("actor lyric clear alias");
		if (EngineCompat.eventName("SecondLyricLine") != "Second Lyric Line") fail("second lyric alias");
		if (EngineCompat.eventName("camBopBig") != "Add Camera Zoom") fail("FPS big bop alias");
		if (EngineCompat.eventName("CamBoomSpeed") != "Cam Boom Speed") fail("boom speed alias");
		var flashRoute = EngineCompat.routeLegacyEvent("Flash", "0.5", "2", "");
		if (flashRoute.name != "Camera Flash" || flashRoute.v1 != "FFFF0000" || flashRoute.v2 != "0.5")
			fail("PERFEXION flash payload route");
		if (EngineCompat.psychFlashScriptOwnsLegacyEvent("Flash", false)
			|| !EngineCompat.psychFlashScriptOwnsLegacyEvent(" Flash ", true)
			|| EngineCompat.psychFlashScriptOwnsLegacyEvent("Camera Flash", true))
			fail("Psych custom Flash ownership must be scoped to a loaded Flash handler");
		// Synthetic dispatch cases: preserve native fallback when no script owns
		// the event, suppress it when the selected custom handler owns `Flash`,
		// and keep canonical `Camera Flash` events native in either case.
		var nativeFallback:Dynamic = EngineCompat.psychFlashScriptOwnsLegacyEvent("Flash", false)
			? null : flashRoute;
		if (nativeFallback == null || nativeFallback.name != "Camera Flash")
			fail("native Flash fallback changed without a custom handler");
		var customOwnedNative:Dynamic = EngineCompat.psychFlashScriptOwnsLegacyEvent("Flash", true)
			? null : flashRoute;
		if (customOwnedNative != null)
			fail("loaded Psych Flash handler must own its legacy event");
		var hudFlashRoute = EngineCompat.routeLegacyEvent("Camera Flash", "hud", "1.0", "");
		if (hudFlashRoute.name != "Camera Flash" || hudFlashRoute.v1 != "hud" || hudFlashRoute.v2 != "1.0")
			fail("Funkadelix HUD flash payload route");
		var canonicalNative:Dynamic = EngineCompat.psychFlashScriptOwnsLegacyEvent("Camera Flash", true)
			? null : hudFlashRoute;
		if (canonicalNative == null || canonicalNative.name != "Camera Flash")
			fail("canonical Camera Flash must remain native with a custom Flash handler");
		var shakeRoute = EngineCompat.routeLegacyEvent("screenShakeSimple", "1", "", "");
		if (shakeRoute.name != "Screen Shake" || shakeRoute.v1 != "0.3,0.01" || shakeRoute.v2 != "0.3,0.01")
			fail("legacy shake payload route");
		var zoomRoute = EngineCompat.routeLegacyEvent("camZoom", "0.9", "2.2", "");
		if (zoomRoute.name != "Legacy Camera Zoom" || zoomRoute.v1 != "0.9" || zoomRoute.v2 != "2.2")
			fail("FPS zoom payload route");
		var bigBopRoute = EngineCompat.routeLegacyEvent("camBopBig", "", "", "");
		if (bigBopRoute.name != "Add Camera Zoom" || bigBopRoute.v1 != "0.03" || bigBopRoute.v2 != "0.06")
			fail("FPS big bop payload route");
		if (EngineCompat.lyricActor("boyfriend") != "bf"
			|| EngineCompat.lyricActor("player3") != "gf"
			|| EngineCompat.lyricActor("pump") != "pump")
			fail("actor lyric token route");
		var lyricMeta = EngineCompat.lyricDurationOrActor("skid");
		if (lyricMeta.duration != 0 || lyricMeta.actor != "skid") fail("actor lyric metadata route");
		var durationMeta = EngineCompat.lyricDurationOrActor("1.5");
		if (durationMeta.duration != 1.5 || durationMeta.actor != "") fail("legacy lyric duration route");
		if (EngineCompat.callbackNames("customSubstateUpdate")[1] != "onCustomSubstateUpdate")
			fail("custom substate callback alias");
		var songEventNames = EngineCompat.callbackNames("songEvent");
		if (songEventNames[0] != "songEvent" || songEventNames[1] != "onSongEvent")
			fail("HXC song event callback alias");
		var songEventArgs = EngineCompat.callbackArguments("songEvent", "songEvent",
			["ChangeCharacterCL", "dad", "yuri", ""]);
		if (songEventArgs.length != 1) fail("HXC song event payload arity");
		var songEvent:Dynamic = songEventArgs[0];
		if (songEvent.eventData.eventKind != "ChangeCharacterCL"
			|| songEvent.eventData.value.value1 != "dad"
			|| songEvent.eventData.value.value2 != "yuri"
			|| songEvent.eventCanceled != false)
			fail("HXC song event payload fields");
		songEvent.cancel();
		if (!songEvent.eventCanceled || !songEvent.eventData.activated)
			fail("HXC song event cancellation adapter");
		var shared = EngineCompat.hxcSongEventPayload(["ChangeStage", "pixel", "", ""]);
		var sharedArgs = EngineCompat.callbackArguments("songEvent", "songEvent", [shared]);
		if (sharedArgs.length != 1 || sharedArgs[0] != shared)
			fail("HXC song event payload must be shared");
		var timedVideo = EngineCompat.hxcSongEventPayload(["PlayVideo", "clip", "", "{}", 1234.5]);
		if (timedVideo.time != 1234.5 || timedVideo.eventData.time != 1234.5)
			fail("HXC video event timestamp payload");
		var vignettePayload = EngineCompat.hxcSongEventPayload(["Vignette", "3", "8",
			"{\"ease\":\"sine\",\"easeDir\":\"Out\"}"]);
		if (vignettePayload.eventData.value.intensity != "3"
			|| vignettePayload.eventData.value.duration != "8"
			|| vignettePayload.eventData.value.ease != "sine"
			|| vignettePayload.eventData.value.easeDir != "Out")
			fail("HXC vignette payload fields");
		var eyePopupPayload = EngineCompat.hxcSongEventPayload(["Markov Popups", "240", "96", ""]);
		if (eyePopupPayload.eventData.value.x != "240" || eyePopupPayload.eventData.value.y != "96")
			fail("HXC eye popup payload fields");
		var countdown = EngineCompat.hxcCountdownStartPayload();
		var countdownArgs = EngineCompat.callbackArguments("countdownStart", "onCountdownStart", [countdown]);
		if (countdownArgs.length != 1 || countdownArgs[0] != countdown
			|| countdown.eventData.eventKind != "countdownStart")
			fail("HXC countdown payload adapter");
		countdown.cancelEvent();
		if (!countdown.eventCanceled || !countdown.canceled || !countdown.cancelled
			|| !countdown.eventData.activated)
			fail("HXC countdown cancellation adapter");
		var pausePayload = EngineCompat.callbackArguments("onPause", "pause", [], true);
		if (pausePayload.length != 1 || pausePayload[0].eventData.eventKind != "pause")
			fail("HXC pause payload adapter");
		var destroyPayload = EngineCompat.callbackArguments("destroy", "destroy", [], true);
		if (destroyPayload.length != 1 || destroyPayload[0].eventData.eventKind != "destroy"
			|| EngineCompat.callbackArguments("destroy", "destroy", [], false).length != 0)
			fail("HXC destroy payload adapter");
		var incomingNote:Dynamic = {ID: 9, noteData: 1, isSustainNote: false};
		var incoming = EngineCompat.hxcNoteIncomingPayload(incomingNote);
		var incomingArgs = EngineCompat.callbackArguments("noteIncoming", "onNoteIncoming",
			[incomingNote, incoming]);
		if (incomingArgs.length != 1 || incomingArgs[0] != incoming || incoming.note == incomingNote
			|| incoming.eventData.value.note != incoming.note || incoming.nativeNote != incomingNote
			|| incoming.note.noteData.getDirection() != 1)
			fail("HXC note incoming payload adapter");
		incoming.cancel();
		if (!incoming.eventCanceled || !incoming.eventData.activated)
			fail("HXC note incoming cancellation adapter");
		var songEnd = EngineCompat.hxcSongEndPayload(123, 456);
		var songEndArgs = EngineCompat.callbackArguments("songEnd", "onSongEnd", [songEnd], true);
		if (songEndArgs.length != 1 || songEndArgs[0] != songEnd
			|| songEnd.eventData.value.songPosition != 123
			|| songEnd.eventData.value.songLength != 456)
			fail("HXC song end payload adapter");
		var typed = EngineCompat.hxcLifecyclePayload("typed", {
			duration: "1.5", enabled: "true", count: "7", label: 42
		});
		if (typed.getFloat("duration") != 1.5 || typed.getBool("enabled") != true
			|| typed.getInt("count") != 7 || typed.getString("label") != "42")
			fail("HXC typed payload getters");
		if (typed.getString("missing") != null || typed.getFloat("missing") != null)
			fail("HXC missing payload fields");
		var invalidFloats = EngineCompat.hxcLifecyclePayload("typed", {blank: "", invalid: "oops"});
		if (!Math.isNaN(invalidFloats.getFloat("blank"))
			|| !Math.isNaN(invalidFloats.getFloat("invalid")))
			fail("HXC supplied invalid floats must remain NaN for source defaults");
		typed.cancelEvent();
		if (!typed.eventCanceled || !typed.canceled || !typed.cancelled || !typed.eventData.activated)
			fail("HXC generic cancellation adapter");
		var rawNote:Dynamic = {ID: 7, noteData: 5, mustPress: true,
			coolId: "alt-anim", isSustainNote: false};
		var notePayloadArgs = EngineCompat.callbackArguments("noteHit", "onNoteHit",
			[true, rawNote, false], true);
		if (notePayloadArgs.length != 1 || notePayloadArgs[0].note.kind != "alt-anim"
			|| notePayloadArgs[0].note.noteData.kind != "alt-anim"
			|| notePayloadArgs[0].note.noteData.getDirection() != 1
			|| !notePayloadArgs[0].note.noteData.getMustHitNote()
			|| notePayloadArgs[0].note.noteData.getStrumlineIndex() != 0)
			fail("HXC note payload adapter");
		var liveState:Dynamic = null;
		liveState = {ID: 3, noteData: 2, isSustainNote: true,
			coolId: "markov", lowPriority: false, active: true, visible: true,
			x: 40.0, y: 20.0, alpha: 1.0, angle: 0.0, frames: "base",
			alive: true, destroyed: false,
			kill: function() { liveState.alive = false; },
			destroy: function() { liveState.destroyed = true; },
			updateHitbox: function() return null};
		var livePayload = EngineCompat.hxcNoteIncomingPayload(liveState);
		livePayload.note.lowPriority = true;
		livePayload.note.x = 36.0;
		livePayload.note.frames = "markov-atlas";
		livePayload.note.kill();
		EngineCompat.hxcApplyNoteCallbackPayload(livePayload);
		if (livePayload.note.kind != "markov" || liveState.lowPriority != true
			|| liveState.x != 36.0 || liveState.frames != "markov-atlas"
			|| liveState.alive != false)
			fail("HXC mutable note view adapter");
		liveState.alive = true;
		livePayload.note.destroy();
		if (liveState.alive || !liveState.destroyed)
			fail("HXC destroyed incoming note remained alive");
		var sharedNotePayload = EngineCompat.hxcNoteCallbackPayload([rawNote], "noteHit");
		var sharedNoteArgs = EngineCompat.callbackArguments("noteHit", "onNoteHit",
			[rawNote, sharedNotePayload], true);
		if (sharedNoteArgs.length != 1 || sharedNoteArgs[0] != sharedNotePayload)
			fail("HXC note callback payload must be shared");
		// A compiled Note can be missing from Reflect.hasField's hxcpp metadata.
		// Type-based discovery and typed field reads must still build its HXC view.
		var typedNote = new fixtures.Note(1234, 2, true, false, true, 2, "typed-kind");
		var typedPayload = EngineCompat.hxcNoteCallbackPayload([true, typedNote, false], "noteHit");
		if (typedPayload.nativeNote != typedNote || typedPayload.note == null
			|| typedPayload.note.noteData.kind != "typed-kind"
			|| typedPayload.note.noteData.getDirection() != 2
			|| typedPayload.note.shouldBeSung != true || typedPayload.note.altNum != 2
			|| typedPayload.note.noteData.getMustHitNote() != true)
			fail("typed native Note must produce a complete HXC view");
		if (typedPayload.note.offset == null || typedPayload.note.offset.x != 3
			|| typedPayload.note.offset.y != 4 || typedPayload.note.flipY != false)
			fail("typed native Note offset/flip view");
		typedPayload.note.offset.x = 45;
		typedPayload.note.offset.y = 150;
		typedPayload.note.offset.unrelated = 99;
		typedPayload.note.flipY = true;
		typedPayload.note.unrelated = "donor-only";
		EngineCompat.hxcApplyNoteCallbackPayload(typedPayload);
		if (typedNote.offset.x != 45 || typedNote.offset.y != 150 || !typedNote.flipY
			|| Reflect.hasField(typedNote.offset, "unrelated")
			|| Reflect.hasField(typedNote, "unrelated"))
			fail("bounded native Note offset/flip copyback");
		Reflect.setField(typedPayload.note.offset, "x", "bad");
		Reflect.setField(typedPayload.note.offset, "y", Math.NaN);
		Reflect.setField(typedPayload.note, "flipY", "bad");
		EngineCompat.hxcApplyNoteCallbackPayload(typedPayload);
		if (typedNote.offset.x != 45 || typedNote.offset.y != 150 || !typedNote.flipY)
			fail("invalid native Note coordinates/flip must be ignored");
		var sickRatedNote:Dynamic = {ID: 8, noteData: 2, rating: "sick"};
		var sickRatedPayload = EngineCompat.hxcNoteCallbackPayload([sickRatedNote], "noteHit");
		if (sickRatedPayload.judgement != "sick")
			fail("manually scored sick must remain distinct from a bot perfect hit");
		var goodRatedNote:Dynamic = {ID: 10, noteData: 3, rating: "good"};
		var goodRatedPayload = EngineCompat.hxcNoteCallbackPayload([goodRatedNote], "noteHit");
		if (goodRatedPayload.judgement != "good")
			fail("non-sick native ratings must remain unchanged for HXC");
		if (EngineCompat.callbackArguments("goodNoteHit", "onGoodNoteHit", [rawNote, true], false).length != 4)
			fail("ordinary note callback ABI changed");
		for (name in ["onCountdownStart", "onNoteIncoming", "onSongEnd"])
			if (!EngineCompat.knownScriptFunction(name)) fail("missing lifecycle API: " + name);
		var dad:Dynamic = {id: "dad"};
		var boyfriend:Dynamic = {id: "boyfriend"};
		var prop:Dynamic = {id: "prop"};
		var stage:Dynamic = {
			getDad: function() return dad,
			getBoyfriend: function() return boyfriend,
			getGirlfriend: function() return null,
			getNamedProp: function(name:String) return name == "light" ? prop : null
		};
		var state:Dynamic = {curStage: stage};
		if (EngineCompat.hxcGetDad(state) != dad
			|| EngineCompat.hxcGetBoyfriend(state) != boyfriend
			|| EngineCompat.hxcGetOpponent(state) != dad
			|| EngineCompat.hxcGetNamedProp(state, "light") != prop
			|| EngineCompat.hxcGetDad(stage) != dad)
			fail("HXC stage role adapter");
		var animation:Dynamic = {
			curAnim: {name: "singLEFT"},
			exists: function(name:String) return name == "hey"
		};
		var offsets:Array<Dynamic> = [];
		var character:Dynamic = {
			animation: animation,
			setAnimationOffsets: function(name:String, x:Float, y:Float) {
				offsets = [name, x, y];
				return null;
			}
		};
		if (EngineCompat.hxcCurrentAnimation(character) != "singLEFT"
			|| !EngineCompat.hxcHasAnimation(character, "hey")
			|| !EngineCompat.hxcIsSinging(character))
			fail("HXC character animation adapter");
		EngineCompat.hxcSetAnimationOffsets(character, "hey", 12, -4);
		if (offsets.length != 3 || offsets[0] != "hey" || offsets[1] != 12 || offsets[2] != -4)
			fail("HXC animation offset adapter");
		for (name in ["getDad", "getBoyfriend", "getGirlfriend", "getOpponent", "getNamedProp",
			"getCurrentAnimation", "setAnimationOffsets"])
			if (!EngineCompat.knownScriptFunction(name)) fail("missing HXC API: " + name);
		var adapted = EngineCompat.hxcApiNames("getDad(); getCurrentAnimation(); setAnimationOffsets('idle', 0, 0);");
		if (adapted.indexOf("getDad") < 0 || adapted.indexOf("getCurrentAnimation") < 0
			|| adapted.indexOf("setAnimationOffsets") < 0)
			fail("HXC API discovery");
		var routed = EngineCompat.routeVSliceEvent("ZoomCamera", {zoom: 1.25, duration: 8, ease: "expoOut", mode: "stage"});
		if (routed.name != "Zoom Camera" || routed.v1 != "1.25" || routed.v2 != "8" || routed.v3.indexOf("stage") < 0)
			fail("V-Slice payload route");
		var options = EngineCompat.eventOptions(routed.v3);
		if (options == null || options.mode != "stage") fail("V-Slice payload options");
		var stage = EngineCompat.routeVSliceEvent("ChangeStage", {stageid: "pixel"});
		if (stage.name != "Change Stage" || stage.v1 != "pixel") fail("V-Slice stage payload route");
		var video = EngineCompat.routeVSliceEvent("PlayVideo", {path: "intro", mute: true, resync: false});
		if (video.name != "Play Video" || video.v1 != "intro") fail("V-Slice video payload route");
		var videoOptions = EngineCompat.eventOptions(video.v2);
		if (videoOptions == null || videoOptions.mute != true || videoOptions.resync != false)
			fail("V-Slice video options");
		var fade = EngineCompat.routeVSliceEvent("extra-events-cameraFadeEvent",
			{color: "0xFF000000", duration: 2, shouldFadeIn: true, applyToHud: true});
		if (fade.name != "Camera Fade" || fade.v3.indexOf("shouldFadeIn") < 0)
			fail("V-Slice fade payload route");
		var lyrics = EngineCompat.routeVSliceEvent("extra-events-addLyricsEvent",
			{text: "line", duration: 3, text2nd: "second"});
		if (lyrics.name != "Lyrics" || lyrics.v1 != "line" || lyrics.v3.indexOf("text2nd") < 0)
			fail("V-Slice lyrics payload route");
		var vignette = EngineCompat.routeVSliceEvent("extra-events-vignEvent",
			{intensity: 3, duration: 8, ease: "sine", easeDir: "Out"});
		if (vignette.name != "Vignette" || vignette.v1 != "3" || vignette.v2 != "8")
			fail("V-Slice vignette payload route");
		var vignetteOptions = EngineCompat.eventOptions(vignette.v3);
		if (vignetteOptions == null || vignetteOptions.ease != "sine" || vignetteOptions.easeDir != "Out")
			fail("V-Slice vignette easing options");
		var characterByTarget = EngineCompat.routeVSliceEvent("ChangeCharacter",
			{target: "dad", char: "caine"});
		var characterByStandardFields = EngineCompat.routeVSliceEvent("charChange",
			{character: "bf", newchar: "pomni"});
		if (characterByTarget == null || characterByTarget.v1 != "dad" || characterByTarget.v2 != "caine"
			|| characterByStandardFields == null || characterByStandardFields.v1 != "bf"
			|| characterByStandardFields.v2 != "pomni")
			fail("character replacement routing must follow payload fields, not event spelling");
		var eyePopup = EngineCompat.routeVSliceEvent("EyePopup", {x: 240, y: 96});
		if (eyePopup.name != "Markov Popups" || eyePopup.v1 != "240" || eyePopup.v2 != "96")
			fail("TAKEOVER eye popup payload route");
		if (EngineCompat.routeVSliceEvent("Zoom Rabbit", {value1: "", value2: "0.55"}) != null)
			fail("custom HXC event was replaced by a native route");
		var noteSwap = EngineCompat.routeVSliceEvent("NoteSwapEvent",
			{strumline: "both", notestyle: "pixel"});
		if (noteSwap.name != "Note Swap" || noteSwap.v1 != "both" || noteSwap.v2 != "pixel")
			fail("V-Slice NoteSwap payload route");
		var psychZoom = EngineCompat.routeLegacyEvent("AddCamZoomPsych", "0.015", "0.03");
		if (psychZoom.name != "Add Camera Zoom" || psychZoom.v3 != "psych")
			fail("TAKEOVER AddCamZoomPsych semantic route");
		var rabbitPayload = EngineCompat.hxcSongEventPayload(["Zoom Rabbit", "", "0.55", ""]);
		if (rabbitPayload.eventData.value.value1 != "" || rabbitPayload.eventData.value.value2 != "0.55")
			fail("custom HXC payload fields");
		var notePayload = EngineCompat.hxcSongEventPayload(["Note Swap", "both", "pixel", ""]);
		if (notePayload.eventData.value.strumline != "both" || notePayload.eventData.value.notestyle != "pixel")
			fail("NoteSwap HXC payload aliases");
		if (EngineCompat.eventName("NoteSwapEvent") != "Note Swap") fail("NoteSwap event alias");
		if (EngineCompat.eventName("Zoom Rabbit") != "Zoom Rabbit") fail("Zoom Rabbit event identity");
		var note = {ID: 17, noteData: -2, coolId: "Hurt", isSustainNote: true};
		var psychArgs = EngineCompat.callbackArguments("goodNoteHit", "onGoodNoteHit", [note, false]);
		if (psychArgs.length != 4 || psychArgs[0] != 17 || psychArgs[1] != 2
			|| psychArgs[2] != "Hurt" || psychArgs[3] != true)
			fail("Psych note callback ABI: " + psychArgs);
		var earlierNote = {ID: 29, noteData: 1, coolId: "Earlier", isSustainNote: false};
		var livePsychNotes:Array<Dynamic> = [null, earlierNote, note, null];
		var livePsychArgs = EngineCompat.callbackArguments("goodNoteHit", "onGoodNoteHit",
			[note, false], false, livePsychNotes);
		if (livePsychArgs.length != 4 || livePsychArgs[0] != 2 || livePsychArgs[0] == note.ID
			|| livePsychArgs[1] != 2 || livePsychArgs[2] != "Hurt" || livePsychArgs[3] != true)
			fail("Psych callbacks must use the live notes.members index across holes: " + livePsychArgs);
		livePsychNotes.splice(2, 1);
		var removedPsychArgs = EngineCompat.callbackArguments("goodNoteHit", "goodNoteHit",
			[note, false], false, livePsychNotes);
		if (removedPsychArgs[0] != -1)
			fail("removed notes must use the live group's indexOf result");
		var liveMissArgs = EngineCompat.callbackArguments("noteMiss", "onNoteMiss",
			[note, true, 2], false, [null, earlierNote, note]);
		if (liveMissArgs.length != 4 || liveMissArgs[0] != 2 || liveMissArgs[1] != 2
			|| liveMissArgs[2] != "Hurt" || liveMissArgs[3] != true)
			fail("Psych onNoteMiss must use the live note index: " + liveMissArgs);
		var liveMissAlias = EngineCompat.callbackArguments("noteMiss", "onMissNote",
			[note, true, 2], false, [null, earlierNote, note]);
		if (liveMissAlias.length != 1 || liveMissAlias[0] != 2)
			fail("Psych onMissNote must use the live note index");
		var opponentMissArgs = EngineCompat.callbackArguments("opponentNoteMiss", "onOpponentNoteMiss",
			[note, false, 2], false, [null, earlierNote, note]);
		if (opponentMissArgs.length != 4 || opponentMissArgs[0] != 2
			|| opponentMissArgs[1] != 2 || opponentMissArgs[2] != "Hurt" || opponentMissArgs[3] != true)
			fail("Psych opponent miss must use the live note index: " + opponentMissArgs);
		var missArgs = EngineCompat.callbackArguments("noteMiss", "noteMiss", [null, true, 3]);
		if (missArgs.length != 4 || missArgs[1] != 3 || missArgs[2] != "" || missArgs[3] != false)
			fail("Psych miss callback ABI: " + missArgs);
		var ghostMissArgs = EngineCompat.callbackArguments("noteMiss", "noteMiss",
			[null, true, 3], false, livePsychNotes);
		if (ghostMissArgs.length != 4 || ghostMissArgs[0] != 0 || ghostMissArgs[1] != 3
			|| ghostMissArgs[2] != "" || ghostMissArgs[3] != false)
			fail("Psych ghost miss callback ABI with a live group: " + ghostMissArgs);
		var calls = EngineCompat.scriptFunctionNames("setProperty('x', 1); lerp(0, 1, 0.5); noteTweenX('x', 4, 1, 0.2); point.set(1, 2);");
		if (calls.indexOf("setProperty") < 0 || calls.indexOf("noteTweenX") < 0 || calls.indexOf("lerp") < 0
			|| calls.indexOf("set") >= 0)
			fail("script call scanner");
		var unknown = EngineCompat.unknownScriptFunctions("setProperty('x', 1); noteTweenX('x', 4, 1, 0.2); noteTweenAlpha('fade', 3, 0, 1); getMystery('x');");
		if (unknown.length != 1 || unknown[0] != "getMystery") fail("unknown API scanner");
		var local = EngineCompat.unknownScriptFunctions("function getMid(value) return value; getMid(1); point.set(1, 2);");
		if (local.length != 0) fail("local/member functions must not be diagnostics");
		for (name in ["setProperty", "getProperty", "setPropertyFromGroup", "getPropertyFromGroup",
			"setPropertyFromClass", "getPropertyFromClass", "doTweenX", "doTweenY", "doTweenAlpha",
			"doTweenAngle", "doTweenZoom", "runTimer", "makeLuaSprite", "makeLuaText", "addLuaSprite",
			"setObjectOrder", "getObjectOrder", "noteTweenX", "noteTweenY", "noteTweenAlpha", "noteTweenAngle",
			"cancelTween", "getRandomInt", "getRandomFloat", "keyboardJustPressed", "keyJustPressed",
				"getColorFromHex", "setBlendMode", "precacheImage", "triggerEvent", "cameraShake",
				"swapStage", "changeStage",
				"setShaderFloat", "setSpriteShader", "getSongPosition", "startTween",
				"setActorX", "setActorY", "tweenCameraZoom", "setTextAlignment", "getTextFont",
				"getRandomBool", "getMouseX", "getMouseY", "getMouseClicked", "mouseClicked",
				"playMusic", "loadSong", "restartSong", "exitSong", "close", "openCustomSubstate",
				"closeCustomSubstate", "callMethodFromClass", "setCameraShaderFilters",
				"clearCameraShaderFilters"])
			if (!EngineCompat.knownScriptFunction(name)) fail("missing API: " + name);
		Sys.println("ok");
	}
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "EngineCompatTest.hx").write_text(fixture, newline='\n')
            typed_package = Path(folder) / "fixtures"
            typed_package.mkdir()
            (typed_package / "Note.hx").write_text(r'''package fixtures;
class Note {
    final noteDataValue:Int;
    final strumTimeValue:Float;
    final mustPressValue:Bool;
    final sustainValue:Bool;
    final shouldSingValue:Bool;
    final altValue:Int;
    final kindValue:String;
    public var noteData(get, never):Int;
    public var strumTime(get, never):Float;
    public var mustPress(get, never):Bool;
    public var isSustainNote(get, never):Bool;
    public var shouldBeSung(get, never):Bool;
    public var altNum(get, never):Int;
    public var sourceKind(get, never):String;
    public var offset:NotePoint;
    public var flipY:Bool = false;
    function get_noteData():Int return noteDataValue;
    function get_strumTime():Float return strumTimeValue;
    function get_mustPress():Bool return mustPressValue;
    function get_isSustainNote():Bool return sustainValue;
    function get_shouldBeSung():Bool return shouldSingValue;
    function get_altNum():Int return altValue;
    function get_sourceKind():String return kindValue;
    public function new(strumTime:Float, noteData:Int, mustPress:Bool, sustain:Bool,
        shouldSing:Bool, altNum:Int, kind:String) {
        this.strumTimeValue = strumTime;
        this.noteDataValue = noteData;
        this.mustPressValue = mustPress;
        this.sustainValue = sustain;
        this.shouldSingValue = shouldSing;
        this.altValue = altNum;
        this.kindValue = kind;
        this.offset = new NotePoint(3, 4);
    }
}
class NotePoint {
    public var x:Float;
    public var y:Float;
    public function new(x:Float, y:Float) {
        this.x = x;
        this.y = y;
    }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-main", "EngineCompatTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_uses_the_central_router_and_property_bridge(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("EngineCompat.callbackNames(func_name)", source)
        self.assertIn("hxcCountdownHookDispatching", source)
        self.assertIn("if (hxcCountdownHookDispatching || codenameCountdownPreparationInProgress)", source)
        self.assertIn("EngineCompat.eventName(e.name)", source)
        self.assertIn("EngineCompat.routeLegacyEvent(e.name, e.v1, e.v2, e.v3)", source)
        self.assertIn("case 'Legacy Camera Zoom':", source)
        self.assertIn("case 'Toggle Camera Movement':", source)
        self.assertIn("case 'Camera Target':", source)
        self.assertIn("case 'Second Lyric Line':", source)
        self.assertIn("case 'Clear Lyrics':", source)
        self.assertIn("case 'Cam Boom Speed':", source)
        self.assertIn("camHUD.flash(flashColor, flashDuration);", source)
        self.assertIn("durationSteps", source)
        self.assertIn("Conductor.stepsToTime(flashDuration) / 1000", source)
        self.assertIn("nativeCamBoomPulse", source)
        self.assertIn("EngineCompat.lyricActor(actor)", source)
        self.assertIn("EngineCompat.lyricDurationOrActor(e.v2)", source)
        self.assertIn("case 'Play Video':", source)
        self.assertNotIn("case 'Zoom Rabbit':", source)
        self.assertIn("case 'Note Swap':", source)
        self.assertIn("applyCompatNoteSwap", source)
        self.assertIn("compatEventColor", source)
        self.assertIn("cameraBopMultiplier", source)
        self.assertIn("playCompatEventVideo(videoPath, videoOptions, videoOffset, eventTime);", source)
        self.assertIn("OptionsHandler.options.zoomCamera", source)
        self.assertIn("OptionsHandler.options.flashingLights", source)
        self.assertIn("OptionsHandler.options.vignetteEffects", source)
        self.assertIn("OptionsHandler.options.lyricsEnabled", source)
        self.assertIn("disableControl", source)
        self.assertIn("video.volumeAdjust = 0", (ROOT / "source/VideoCutscene.hx").read_text())
        self.assertIn("applyZIndex", (ROOT / "source/VideoCutscene.hx").read_text())
        self.assertIn("callAllHScript('songEvent'", source)
        self.assertIn("if (hxcEvent.eventCanceled == true)", source)
        self.assertIn("note.switchType(style);", source)
        note = (ROOT / "source/Note.hx").read_text()
        self.assertIn("currentKey.newKey(newType.uses, newType.isPixel);", note)
        self.assertIn("seedEngineCompat(interp);", source)
        for global_name in (
            "screenWidth", "screenHeight", "crochet", "shadersEnabled",
            "startCountdown", "luaStringFormat", "luaStringGmatch",
            "luaTableLength", "luaTableKey", "luaTableValue",
        ):
            self.assertIn("variables.set('" + global_name + "'", source)
        self.assertIn('variables.set("mustHitSection"', source)
        self.assertIn('variables.set("gfSection"', source)
        self.assertIn('variables.set("SONG", SONG);', source)
        self.assertIn("tmr.loops", source)
        self.assertIn("tmr.loopsLeft", source)
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("EngineCompat.knownScriptFunction(name)", module)
        self.assertIn("EngineCompat.unknownScriptFunctions(contents)", module)
        self.assertIn("[lua-runtime-adapter]", module)
        self.assertIn("[hxc-runtime-adapter]", module)
        for function in (
            "setProperty", "getProperty", "setPropertyFromGroup", "getPropertyFromGroup",
            "setPropertyFromClass", "getPropertyFromClass", "doTweenX", "doTweenY",
            "doTweenAlpha", "doTweenAngle", "doTweenZoom", "runTimer", "makeLuaSprite",
        ):
            self.assertIn("variables.set('" + function + "'", source)
        self.assertIn("callAllHScript('updatePost', [elapsed]);", source)
        self.assertIn("EngineCompat.hxcCountdownStartPayload()", source)
        self.assertIn("callAllHScript('countdownStart', [countdownEvent]);", source)
        self.assertIn("if (countdownEvent.eventCanceled == true", source)
        self.assertIn("EngineCompat.hxcNoteIncomingPayload(dunceNote)", source)
        self.assertIn('callAllHScript("noteIncoming", [dunceNote, incomingEvent], true);', source)
        self.assertIn('callHxcNoteHScript("noteIncoming", [dunceNote, incomingEvent]);', source)
        self.assertIn("function endSong(?force:Bool = false):Void", source)
        self.assertIn("EngineCompat.hxcSongEndPayload(Conductor.songPosition, songLength)", source)
        self.assertIn("callAllHScript('songEnd', [songEndEvent], false, songEndResults);", source)
        self.assertIn("var selectedEventCancelled = songEndEvent.eventCanceled == true", source)
        self.assertIn("PsychEndSongLifecycle.selectedDisposition(", source)
        self.assertIn("callAllHScript('destroy', []);", source)
        self.assertIn("public var currentSong(get, never):SwagSong;", source)
        self.assertIn("public var currentCameraZoom(get, set):Float;", source)
        self.assertIn("public var cameraFollowPoint(get, never):FlxObject;", source)
        self.assertIn("public var cameraZoomRate(get, set):Int;", source)
        self.assertIn("public var isMinimalMode(get, never):Bool;", source)
        self.assertIn("public var timeTxt(get, never):FlxText;", source)
        self.assertIn("return timeBar;", source)
        self.assertIn("public var needsReset(get, never):Bool;", source)
        self.assertIn("function get_needsReset():Bool", source)
        self.assertIn("public function cancelCameraFollowTween():Void", source)
        for function in (
            "setObjectOrder", "getObjectOrder", "noteTweenX", "noteTweenY", "noteTweenAngle",
            "cancelTween", "getRandomInt", "getRandomFloat", "keyboardJustPressed",
            "keyJustPressed", "getColorFromHex", "setBlendMode", "precacheImage",
            "triggerEvent", "cameraShake", "setShaderFloat", "setSpriteShader",
            "setCameraShaderFilters", "clearCameraShaderFilters",
        ):
            self.assertIn("variables.set('" + function + "'", source)
        self.assertIn("EngineCompat.eventOptions(e.v3)", source)
        self.assertIn("case 'Set Camera Bop':", source)
        self.assertIn("case 'Change Scroll Speed':", source)
        self.assertIn("case 'Change Stage':", source)
        self.assertIn("public function swapStage", source)

    def test_builtin_stage_and_asset_aliases_share_runtime_and_scan_resolvers(self):
        playstate = (ROOT / "source/PlayState.hx").read_text()
        importer = (ROOT / "source/ImportWorkflow.hx").read_text()
        character = (ROOT / "source/Character.hx").read_text()
        self.assertIn("EngineCompat.resolveStageAlias(requested)", playstate)
        self.assertIn("EngineCompat.rewriteLegacyAssetPaths(source)", playstate)
        self.assertIn("EngineCompat.stageLookupNames(reference)", importer)
        self.assertIn("EngineCompat.resolveLegacyAssetPath(raw)", importer)
        # Character resolution may select a case-correct sibling implementation
        # (for example Popipo's miku -> mikuv2 visual), so the shared asset-path
        # rewrite now runs on the resolved implementation text rather than a
        # second direct getHscript lookup by the authored id.
        self.assertIn("var scriptSource = FNFAssets.getText(implementationPath);", character)
        self.assertIn("EngineCompat.rewriteLegacyAssetPaths(scriptSource)", character)
        self.assertIn("program = cachedCharacterProgram('character:' + implementationPath,", character)
        self.assertTrue((ROOT / "assets/images/custom_stages/spooky.hscript").exists())
        self.assertTrue((ROOT / "assets/images/custom_stages/schoolEvil.hscript").exists())
        self.assertTrue((ROOT / "assets/images/custom_stages/philly-streets.hscript").exists())
        stage_registry = (ROOT / "assets/images/custom_stages/custom_stages.json").read_text()
        self.assertIn('"philly-streets": "philly-streets"', stage_registry)
        self.assertTrue((ROOT / "assets/images/custom_chars/bf/char.png").exists())
        self.assertTrue((ROOT / "assets/images/custom_chars/bf/char.xml").exists())
        halloween = DONOR / "hellbeats_kade_engine/HellBeats Kade Engine/assets/data/monster/monster-easy.json"
        school_evil_erect = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/too-slow-monika-mix/too-slow-monika-mix-metadata.json"
        boyfriend_script = DONOR / "modding-plus/vsfreddy_1_9_5/assets/images/custom_chars/bf-christmas.hscript"
        if not (halloween.exists() and school_evil_erect.exists() and boyfriend_script.exists()):
            self.skipTest("example donor evidence is not mounted")
        self.assertIn('"stage":"halloween"', halloween.read_text(errors="ignore"))
        self.assertIn('"stage": "schoolEvilErect"', school_evil_erect.read_text(errors="ignore"))
        self.assertIn("assets/images/BOYFRIEND.png", boyfriend_script.read_text(errors="ignore"))

    def test_donor_psych_surface_is_in_the_allow_list_when_examples_are_mounted(self):
        script = DONOR / "psych/PERFEXION Demo1/data/Resonance/modchart.lua"
        if not script.exists():
            self.skipTest("example donor is not mounted")
        source = "\n".join(
            path.read_text(errors="ignore")
            for path in DONOR.rglob("*.lua")
        )
        # These are the high-volume property/tween calls in the donor corpus;
        # they must remain routed through the native bridge rather than being
        # rejected as unsupported during a future script conversion.
        for token in ("setProperty", "getProperty", "setPropertyFromGroup",
                      "getPropertyFromGroup", "doTweenX", "doTweenY",
                      "doTweenAlpha", "doTweenAngle", "runTimer", "setObjectOrder",
                      "getObjectOrder", "noteTweenX", "noteTweenY", "noteTweenAngle",
                      "cancelTween", "getRandomInt", "getRandomFloat",
                      "keyboardJustPressed", "keyJustPressed", "getColorFromHex",
                      "setBlendMode", "precacheImage", "triggerEvent", "cameraShake"):
            self.assertIn(token + "(", source)
            self.assertIn("'" + token.lower() + "'", (ROOT / "source/EngineCompat.hx").read_text().lower())

    def test_legacy_stage_helpers_are_not_reported_as_unknown_engine_apis(self):
        stage_paths = [
            DONOR / "modding-plus/vsfreddy_1_9_5/assets/images/custom_stages/limo.hscript",
            DONOR / "modding-plus/vsfreddy_1_9_5/assets/images/custom_stages/school.hscript",
            DONOR / "modding-plus/vsfreddy_1_9_5/assets/images/custom_stages/tank.hscript",
        ]
        if not all(path.exists() for path in stage_paths):
            self.skipTest("example donor stage scripts are not mounted")
        donor_source = "\n".join(path.read_text(errors="ignore") for path in stage_paths)
        self.assertIn("setDefaultZoom(", donor_source)
        self.assertIn("getHaxeActor(", donor_source)
        playstate = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn('interp.variables.set("setDefaultZoom"', playstate)
        self.assertIn('interp.variables.set("getHaxeActor"', playstate)

        fixture = r'''
class EngineCompatStageTest {
    static function main() {
        if (!EngineCompat.knownScriptFunction("setDefaultZoom"))
            throw "setDefaultZoom is missing from the engine API allow-list";
        if (!EngineCompat.knownScriptFunction("getHaxeActor"))
            throw "getHaxeActor is missing from the engine API allow-list";
        var unknown = EngineCompat.unknownScriptFunctions(
            "function start(song) { setDefaultZoom(0.9); getHaxeActor('bf').x += 1; }");
        if (unknown.length != 0)
            throw "legacy stage API was diagnosed: " + unknown.join(",");
        trace("OK");
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "EngineCompatStageTest.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-main", "EngineCompatStageTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
