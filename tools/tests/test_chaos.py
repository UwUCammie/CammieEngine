from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def ownership_helper_slice(source: str, end_marker: str) -> str:
    """Keep the ownership methods without adjacent StageHelper display adapters."""
    start = source.index('\tfunction isScriptObject(')
    end = source.index(end_marker, start)
    helper = source[start:end]
    attach = helper.find('\n\tpublic function attachStageMember(')
    if attach >= 0:
        following = helper.index('\n\tfunction isStageOwnedSprite(', attach)
        helper = helper[:attach] + helper[following:]
    return helper


class ChaosTest(unittest.TestCase):
    def test_intro_reaches_countdown(self):
        fixture = ROOT / 'assets/images/custom_stages/chamber.hscript'
        if not fixture.is_file():
            self.skipTest(f'mounted Chaos stage fixture unavailable: {fixture}')
        result = subprocess.run([
            *HAXE_COMMAND, '-cp', str(ROOT / 'tools/tests/fixtures'),
            '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-main', 'ChaosIntroTest', '--interp'
        ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_intro_retains_donor_cues_and_uses_engine_handoff(self):
        fixture = ROOT / 'assets/images/custom_cutscenes/fleetway.hscript'
        if not fixture.is_file():
            self.skipTest(f'mounted Chaos cutscene fixture unavailable: {fixture}')
        script = fixture.read_text()
        self.assertIn('currentPlayState.camFollow.x -= 800;', script)
        self.assertIn('currentPlayState.camFollow.y -= 250;', script)
        self.assertIn("ZoomCamera({zoom: 1, durationSeconds: 0.9", script)
        self.assertIn('new FlxTimer().start(0.9', script)
        self.assertIn('FlxG.camera.fade(0xFFFF0000, 0.2, true);', script)
        self.assertIn("preloadSound('assets/sounds/robot');", script)
        self.assertIn("soundPlaySafe('assets/sounds/robot');", script)
        self.assertIn('new FlxTimer().start(2', script)
        self.assertIn("thechamber.animation.play('a', true);", script)
        self.assertIn('new FlxTimer().start(4.2', script)
        self.assertIn('FlxG.camera.shake(0.003, 1);', script)
        self.assertIn("ZoomCamera({zoom: 0.7, durationSeconds: 0.4", script)
        self.assertIn("floor.animation.play('b');", script)
        self.assertIn("fleetwaybgshit.animation.play('b');", script)
        self.assertIn("pebles.animation.play('b');", script)
        self.assertIn('emeraldbeamyellow.visible = true;', script)
        self.assertIn('emeraldbeam.visible = false;', script)
        self.assertNotIn('removeSprite(thechamber);', script)
        self.assertIn('new FlxTimer().start(4.5', script)
        self.assertIn('handoffCutsceneSprite(bar1, true, 0.5);', script)
        self.assertIn('handoffCutsceneSprite(bar2, true, 0.5);', script)
        self.assertIn('function playerTwoSing()', script)
        self.assertIn('handoffCutsceneSprite', (ROOT / 'source/PlayState.hx').read_text())

    def test_stage_globals_are_shared_with_cutscene(self):
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn("if (usehaxe == 'cutscene')\n\t\t\tinheritHscriptVariables('stage', interp);", play_state)
        self.assertLess(
            play_state.index("inheritHscriptVariables('stage', interp);"),
            play_state.index('interp.execute(program);'),
        )
        fixture = ROOT / 'assets/images/custom_stages/chamber.hscript'
        if not fixture.is_file():
            self.skipTest(f'mounted Chaos stage fixture unavailable: {fixture}')
        stage = fixture.read_text()
        chaos_stage = stage[:stage.index('if (curSong == "Powerless")')]
        for name in ('floor', 'fleetwaybgshit', 'emeraldbeam', 'emeraldbeamyellow', 'pebles', 'thechamber'):
            self.assertRegex(chaos_stage, rf'(?m)^\s*{name}\s*=\s*new FlxSprite')
            self.assertNotRegex(chaos_stage, rf'(?m)^\s*var {name}\s*=')

    def test_cutscene_cleanup_preserves_inherited_stage_objects(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('var stageSprites:Array<FlxBasic> = [];', source)
        self.assertIn('var cutsceneSprites:Array<FlxBasic> = [];', source)
        self.assertIn('var stageSeededVariables:Map<String, Dynamic> = [];', source)
        self.assertIn('snapshotStageVariables(interp);', source)
        self.assertIn('registerStageSprites(interp);', source)
        self.assertIn('registerStageSprite(value);', source)
        self.assertIn("if (isStageScriptScope(usehaxe)) {\n\t\t\t\tregisterStageSprite(spr);\n\t\t\t\ttrackImportedStageHudProp(spr, usehaxe);\n\t\t\t}", source)
        self.assertIn('if (script != \'cutscene\' || isStageOwnedSprite(sprite))', source)
        self.assertIn('trackHscriptSprite(sprite, usehaxe);', source)

        # Execute the production ownership helpers in isolation. This covers
        # both paths that matter at the hand-off: an inherited stage object
        # must not enter the cleanup list, while a cutscene-only overlay must.
        helpers = ownership_helper_slice(source, '\n\tfunction registerStageSprites(').replace('FlxBasic', 'FakeBasic').replace('Interp', 'FakeInterp').replace('FlxTimer', 'FakeTimer').replace('FlxTween', 'FakeTween')
        fixture = '''
class FakeBasic { public function new() {} }
class FakeTimer {
 public function new() {}
 public function start(delay:Float, callback:Dynamic->Void):FakeTimer return this;
 public function cancel():Void {}
}
class FakeTween { public function cancel():Void {} }
class FakeInterp {
 public var variables:Map<String,Dynamic> = [];
 public function new() {}
}
class OwnershipTest {
 var stageSprites:Array<FakeBasic> = [];
 var cutsceneSprites:Array<FakeBasic> = [];
 var cutsceneHandoffSprites:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseOnOpponentSing:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseDelays:Array<Float> = [];
 var cutsceneHandoffOpponentSing:Dynamic = null;
 var cutsceneHandoffOpponentSingTriggered:Bool = false;
 var compatTimers:Map<String,FakeTimer> = [];
 var compatTweens:Map<String,FakeTween> = [];
 var haxeSprites:Map<String,FakeBasic> = [];
 var haxeSpriteAtlasNames:Map<String,Array<String>> = [];
 var haxeSpriteAtlasNamesByObject:Map<FakeBasic,Array<String>> = [];
 var psychGlobalProviderFirstSprite:FakeBasic = null;
 var psychGlobalProviderFirstSpriteTag:String = null;
 var psychGlobalProviderSpriteMarked:Bool = false;
 var hscriptStates:Map<String,FakeInterp> = [];
 public function new() {}
 function remove(sprite:Dynamic):Void {}
 function removeGlobalSpriteReferences(sprite:FakeBasic):Void {}
''' + helpers + '''
 static function main() {
  var state = new OwnershipTest();
  var chamber = new FakeBasic();
  var bars = new FakeBasic();
  state.trackHscriptSprite(chamber, 'stage');
  state.trackHscriptSprite(chamber, 'cutscene');
  state.trackHscriptSprite(bars, 'cutscene');
  if (state.stageSprites.length != 1 || state.cutsceneSprites.length != 1)
   throw 'stage-owned object was scheduled for cleanup';
  if (state.cutsceneSprites[0] != bars)
   throw 'cutscene overlay was not scheduled for cleanup';
  state.registerStageSprite(bars);
  if (state.cutsceneSprites.length != 0)
   throw 'ownership correction did not remove the stale cleanup entry';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / 'OwnershipTest.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder,
                '-main', 'OwnershipTest', '--interp'
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        # Exercise the generalized hand-off path separately: a cutscene-only
        # sprite is retained through the countdown, its one-shot hook fires
        # on the first opponent sing, and delayed cleanup removes it.
        handoff_start = source.index('\tfunction forgetCutsceneSprite(')
        handoff_end = source.index('\n\tinline function dispatchNoteStrumCallback(', handoff_start)
        handoff_helpers = source[handoff_start:handoff_end].replace('FlxBasic', 'FakeBasic').replace('FlxTimer', 'FakeTimer')
        handoff_fixture = '''
class FakeBasic { public function new() {} }
class FakeTimer {
 public function new() {}
 public function start(delay:Float, callback:Dynamic->Void) { callback(this); return this; }
}
class HandoffTest {
 var stageSprites:Array<FakeBasic> = [];
 var cutsceneSprites:Array<FakeBasic> = [];
 var cutsceneHandoffSprites:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseOnOpponentSing:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseDelays:Array<Float> = [];
 var cutsceneHandoffOpponentSing:Dynamic = null;
 var cutsceneHandoffOpponentSingTriggered:Bool = false;
 var removed:Array<FakeBasic> = [];
 public function new() {}
 function isScriptObject(value:Dynamic):Bool return value != null;
 function isStageOwnedSprite(sprite:Dynamic):Bool return stageSprites.indexOf(cast sprite) != -1;
 function remove(sprite:Dynamic):Void removed.push(cast sprite);
 function removeGlobalSpriteReferences(sprite:FakeBasic):Void {}
''' + handoff_helpers + '''
 static function main() {
  var state = new HandoffTest();
  var bar = new FakeBasic();
  var chamber = new FakeBasic();
  state.stageSprites.push(chamber);
  state.cutsceneSprites.push(bar);
  state.handoffCutsceneSprite(bar, true, 0.5);
  state.handoffCutsceneSprite(chamber, true, 0.5);
  if (state.cutsceneSprites.length != 0 || state.cutsceneHandoffSprites.length != 1
      || state.cutsceneHandoffReleaseOnOpponentSing.length != 1)
   throw 'handoff did not separate retained cutscene ownership';
  var hookCalls = 0;
  state.cutsceneHandoffOpponentSing = function() hookCalls++;
  state.callCutsceneOpponentSing();
  if (hookCalls != 1 || state.removed.length != 1 || state.cutsceneHandoffSprites.length != 0
      || !state.cutsceneHandoffOpponentSingTriggered)
   throw 'handoff opponent-sing release did not complete';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / 'HandoffTest.hx'
            path.write_text(handoff_fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder,
                '-main', 'HandoffTest', '--interp'
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_snapshot_excludes_seeded_objects_and_keeps_unadded_exports(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        helpers = ownership_helper_slice(source, '\n\tfunction inheritHscriptVariables(').replace('FlxBasic', 'FakeBasic').replace('Interp', 'FakeInterp').replace('FlxTimer', 'FakeTimer').replace('FlxTween', 'FakeTween')
        fixture = '''
class FakeBasic { public function new() {} }
class FakeTimer {
 public function new() {}
 public function start(delay:Float, callback:Dynamic->Void):FakeTimer return this;
 public function cancel():Void {}
}
class FakeTween { public function cancel():Void {} }
class FakeInterp {
 public var variables:Map<String,Dynamic> = [];
 public function new() {}
}
class OwnershipSnapshotTest {
 var stageSprites:Array<FakeBasic> = [];
 var cutsceneSprites:Array<FakeBasic> = [];
 var cutsceneHandoffSprites:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseOnOpponentSing:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseDelays:Array<Float> = [];
 var cutsceneHandoffOpponentSing:Dynamic = null;
 var cutsceneHandoffOpponentSingTriggered:Bool = false;
 var stageSeededVariables:Map<String,Dynamic> = [];
 var compatTimers:Map<String,FakeTimer> = [];
 var compatTweens:Map<String,FakeTween> = [];
 var haxeSprites:Map<String,FakeBasic> = [];
 var haxeSpriteAtlasNames:Map<String,Array<String>> = [];
 var haxeSpriteAtlasNamesByObject:Map<FakeBasic,Array<String>> = [];
 var psychGlobalProviderFirstSprite:FakeBasic = null;
 var psychGlobalProviderFirstSpriteTag:String = null;
 var psychGlobalProviderSpriteMarked:Bool = false;
 var hscriptStates:Map<String,FakeInterp> = [];
 public function new() {}
 function remove(sprite:Dynamic):Void {}
 function removeGlobalSpriteReferences(sprite:FakeBasic):Void {}
''' + helpers + '''
 static function main() {
  var state = new OwnershipSnapshotTest();
  var boyfriend = new FakeBasic();
  var chamber = new FakeBasic();
  var interp = new FakeInterp();
  interp.variables.set('boyfriend', boyfriend);
  state.snapshotStageVariables(interp);
  // This is the un-added global exported by Chaos's stage start hook.
  interp.variables.set('thechamber', chamber);
  state.registerStageSprites(interp);
  if (state.stageSprites.length != 1 || state.stageSprites[0] != chamber)
   throw 'seeded object was incorrectly claimed or new export was missed';
  if (state.stageSprites.indexOf(boyfriend) != -1)
   throw 'shared preseeded object became stage-owned';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / 'OwnershipSnapshotTest.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder,
                '-main', 'OwnershipSnapshotTest', '--interp'
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_early_countdown_cleans_late_cutscene_additions(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        helper_start = source.index('\tfunction removeGlobalSpriteReferences(')
        helper_end = source.index('\n\tpublic function startCountdown():Void {', helper_start)
        helper = source[helper_start:helper_end].replace('FlxBasic', 'FakeBasic').replace('FlxTimer', 'FakeTimer')
        start = source.index('public function startCountdown():Void {')
        # Keep the production preamble and cutscene handoff under test, then
        # stop before the unrelated countdown setup. The setup now includes a
        # Codename try/catch block, so truncating at the first strum tween left
        # the extracted fixture inside an open try statement.
        end = source.index('\n\t\tdiagnoseLegacyKadeOffset();', start)
        countdown = source[start:end]
        fixture = '''
class FakeBasic { public function new() {} }
class FakeTimer {
 public var active:Bool = true;
 public function new() {}
 public function start(delay:Float, callback:Dynamic->Void):FakeTimer return this;
 public function cancel():Void { active = false; }
}
class FakeTimeline {
 public function new() {}
 public function isDone():Bool return false;
 public function cancel(?handoff:Bool = true):Void {}
}
class Conductor {
 public static var songPosition:Float = 0;
 public static var crochet:Float = 100;
}
class RuntimeSmokeHarness {
 public static function markStep(_phase:String):Void {}
}
class PsychRuntimeBindings {
 public static var calls:Array<String> = [];
 public static function dispatch(host:Dynamic, name:String, args:Array<Dynamic>,
   family:String = 'Scripts', ignoreStops:Bool = false,
   ?hscriptArgs:Array<Dynamic>):Dynamic {
  calls.push(name);
  return null;
 }
}
class PlayState { public static var globalSprites:Map<String,FakeBasic> = []; }
class EarlyHandoffTest {
 var stageSprites:Array<FakeBasic> = [];
 var cutsceneSprites:Array<FakeBasic> = [];
 var cutsceneHandoffSprites:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseOnOpponentSing:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseDelays:Array<Float> = [];
 var cutsceneHandoffOpponentSing:Dynamic = null;
 var cutsceneHandoffOpponentSingTriggered:Bool = false;
 var cutsceneStartInProgress:Bool = false;
 var pendingCutsceneHandoff:Bool = false;
 var skipCountdown:Bool = false;
 var hxcCountdownStopRequested:Bool = false;
 var hxcCountdownHookDispatching:Bool = false;
 var codenameCountdownPreparationInProgress:Bool = false;
 var sourceEventPreparationInProgress:Bool = false;
 var psychSourceCreationReady:Bool = true;
 var startedCountdown:Bool = false;
 var startTimer:FakeTimer = null;
 var hxcCutsceneTimelineRuntime:FakeTimeline = null;
 var inCutscene:Bool = false;
 var hxcScriptInCutscene:Bool = false;
 var curStage:Dynamic = null;
 var watchedCutscene:Bool = false;
 var SONG:Dynamic = {cutsceneType:'chaos'};
 var hscriptStates:Map<String,Dynamic> = [];
 var removed:Array<FakeBasic> = [];
 var nightmareCalls:Array<String> = [];
 public function new() { hscriptStates.set('cutscene', {}); }
 function importedCutsceneScript():String return '';
 function diagnoseLegacyKadeOffset():Void {}
 function remove(sprite:Dynamic):Void removed.push(cast sprite);
 function callNightmareVision(name:String, args:Array<Dynamic>):Dynamic {
  nightmareCalls.push(name);
  return null;
 }
''' + helper + '''
 public function startCountdown():Void {
''' + countdown.replace('public function startCountdown():Void {\n', '') + '''
  return;
 }
 static function main() {
  var state = new EarlyHandoffTest();
  var first = new FakeBasic();
  var late = new FakeBasic();
  PlayState.globalSprites.set('first', first);
  PlayState.globalSprites.set('late', late);
  state.cutsceneSprites.push(first);
  state.inCutscene = true;
  state.cutsceneStartInProgress = true;
  state.startCountdown();
  if (!state.pendingCutsceneHandoff || state.removed.length != 0)
   throw 'early countdown did not defer cleanup';
  // Simulate a later addSprite statement in the same cutscene start() hook.
  state.cutsceneSprites.push(late);
  state.cutsceneStartInProgress = false;
  state.pendingCutsceneHandoff = false;
  state.startCountdown();
  if (state.removed.length != 2 || state.inCutscene || state.cutsceneSprites.length != 0)
   throw 'late cutscene addition escaped cleanup';
  if (PlayState.globalSprites.exists('first') || PlayState.globalSprites.exists('late'))
   throw 'cutscene globals survived handoff';

  var creating = new EarlyHandoffTest();
  creating.psychSourceCreationReady = false;
  creating.inCutscene = true;
  PsychRuntimeBindings.calls = [];
  creating.startCountdown();
  if (!creating.inCutscene || PsychRuntimeBindings.calls.length != 0
    || creating.nightmareCalls.length != 0)
   throw 'source creation should finish event/script preparation before countdown';

  var preparing = new EarlyHandoffTest();
  preparing.sourceEventPreparationInProgress = true;
  preparing.inCutscene = true;
  PsychRuntimeBindings.calls = [];
  preparing.startCountdown();
  if (!preparing.inCutscene || PsychRuntimeBindings.calls.length != 0
    || preparing.nightmareCalls.length != 0)
   throw 'event preparation re-entry should not start countdown or dispatch lifecycle callbacks';

  var repeated = new EarlyHandoffTest();
  repeated.startedCountdown = true;
  repeated.inCutscene = true;
  repeated.cutsceneSprites.push(first);
  repeated.startTimer = new FakeTimer();
  var timerBefore = repeated.startTimer;
  Conductor.songPosition = 777;
  PsychRuntimeBindings.calls = [];
  repeated.startCountdown();
  if (Conductor.songPosition != 777 || repeated.startTimer != timerBefore
    || !repeated.startTimer.active || !repeated.inCutscene
    || repeated.cutsceneSprites.length != 1 || repeated.removed.length != 0)
   throw 'repeated started countdown rewound or handed off active state';
  if (PsychRuntimeBindings.calls.join(',') != 'onStartCountdown'
    || repeated.nightmareCalls.join(',') != 'onStartCountdown'
    || repeated.hxcCountdownHookDispatching)
   throw 'repeated started countdown must only re-notify its start gate';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / 'EarlyHandoffTest.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder,
                '-main', 'EarlyHandoffTest', '--interp'
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_script_global_registry_clears_with_state_ownership(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\tfunction clearScriptOwnership():Void {')
        end = source.index('\n\tfunction isScriptObject(', start)
        helper = source[start:end].replace('FlxBasic', 'FakeBasic').replace('FlxTimer', 'FakeTimer')
        fixture = '''
class FakeBasic { public function new() {} }
class FakeTimer {
 public function new() {}
 public function start(delay:Float, callback:Dynamic->Void):FakeTimer return this;
}
class FakeTimeline {
 public function new() {}
 public function cancel(?handoff:Bool = true):Void {}
}
class PlayState { public static var globalSprites:Map<String,FakeBasic> = []; }
class RegistryResetTest {
 var pendingHxcCharacterVisuals:Map<String,Bool> = [];
 var stageSprites:Array<FakeBasic> = [];
 var cutsceneSprites:Array<FakeBasic> = [];
 var cutsceneHandoffSprites:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseOnOpponentSing:Array<FakeBasic> = [];
 var cutsceneHandoffReleaseDelays:Array<Float> = [];
 var cutsceneHandoffOpponentSing:Dynamic = null;
 var cutsceneHandoffOpponentSingTriggered:Bool = false;
 var stageSeededVariables:Map<String,Dynamic> = [];
 var hxcPayloadStates:Map<String,Bool> = [];
 var hxcNoteKindScopes:Map<String,String> = [];
 var hxcModuleScopes:Map<String,String> = [];
 var hxcModulePaths:Map<String,String> = [];
 var hxcStageScopes:Array<String> = [];
 var hxcStageScopeIndex:Int = 0;
 var hxcCharacterScopeNames:Map<String,String> = [];
 var hxcCharacterScopeRoles:Map<String,Array<String>> = [];
 var hxcCharacterDispatchDepth:Int = 0;
 var hxcCharacterCallbackActor:FakeBasic = null;
 var hxcCharacterCallbackRole:String = '';
 var hxcGameOverCharacter:FakeBasic = null;
 var hxcSongLoadedDispatched:Bool = false;
 var loadedCompatScriptPaths:Map<String,Bool> = [];
 var compatScriptScopes:Map<String,Array<{scope:String,interp:Dynamic,path:String}>> = [];
 var loadingPsychLuaScriptPaths:Map<String,Bool> = [];
 var psychCompatScriptsLoaded:Bool = false;
 var hxcCompatScriptsLoaded:Bool = false;
 var psychCompatScriptIndex:Int = 0;
 var cachedHxcScriptPlan:Dynamic = null;
 var cachedCompatScriptManifest:Dynamic = null;
 var cachedHxcEventSpriteCatalogs:Map<String,Array<Dynamic>> = new Map<String,Array<Dynamic>>();
 var cutsceneStartInProgress:Bool = false;
 var pendingCutsceneHandoff:Bool = false;
 var hxcCountdownEndDispatched:Bool = false;
 var hxcCountdownStopRequested:Bool = false;
 var hxcScriptInCutscene:Bool = false;
 var psychStageStartCallback:Dynamic = null;
 var psychStageEndCallback:Dynamic = null;
 var psychStageCutsceneEnding:Bool = false;
 var psychFlashEventScopes:Map<String,Bool> = [];
 var psychCustomEventScopes:Map<String,String> = ["custom" => "some event"];
 var hxcCutsceneTimelineRuntime:FakeTimeline = null;
 var compatCustomSubstateName:String = '';
 var compatCustomSubstateOpen:Bool = false;
 var compatCustomSubstate:Dynamic = {};
 var compatCustomSubstatePausesGame:Bool = true;
 var vSliceCameraHoldsFocus:Bool = true;
 function clearHxcCutsceneTimelineNativeObjects():Void {}
 public function new() {}
''' + helper + '''
 static function main() {
  var state = new RegistryResetTest();
  PlayState.globalSprites.set('stale', new FakeBasic());
  state.stageSprites.push(new FakeBasic());
  state.cutsceneSprites.push(new FakeBasic());
  state.hxcCharacterCallbackActor = new FakeBasic();
  state.hxcCharacterCallbackRole = 'bf';
  state.hxcNoteKindScopes.set('stale-kind', 'trickyhell');
  state.loadingPsychLuaScriptPaths.set('scripts/pending.lua', true);
  state.compatScriptScopes.set('scripts/pending.lua', [{scope:'pending',interp:null,path:'scripts/pending.lua'}]);
  state.clearScriptOwnership();
  if (state.compatCustomSubstate != null || state.compatCustomSubstatePausesGame || state.vSliceCameraHoldsFocus)
   throw 'custom substate owner survived cleanup';
  if (PlayState.globalSprites.exists('stale') || state.stageSprites.length != 0 || state.cutsceneSprites.length != 0)
   throw 'song-local ownership or global registry was not cleared';
  if (state.hxcCharacterCallbackActor != null || state.hxcCharacterCallbackRole != '')
   throw 'temporary character callback binding survived state cleanup';
  if (state.hxcNoteKindScopes.exists('stale-kind'))
   throw 'note-kind scope ownership survived state cleanup';
  if (state.loadingPsychLuaScriptPaths.exists('scripts/pending.lua'))
   throw 'Lua dependency recursion guard survived state cleanup';
  if (state.compatScriptScopes.exists('scripts/pending.lua'))
   throw 'Lua scope ownership survived state cleanup';
  if (state.psychCustomEventScopes.keys().hasNext())
   throw 'custom event ownership survived state cleanup';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / 'RegistryResetTest.hx'
            path.write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, '-cp', folder,
                '-main', 'RegistryResetTest', '--interp'
            ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_first_laser_is_live(self):
        fixture = ROOT / 'assets/data/chaos/modchart.hscript'
        if not fixture.is_file():
            self.skipTest(f'mounted Chaos modchart fixture unavailable: {fixture}')
        script = fixture.read_text()
        warning = re.search(r'if \(step == 256\)(.*?)if \(step == 264\)', script, re.S)
        self.assertIsNotNone(warning)
        self.assertIn('killable = true;', warning.group(1))
        self.assertIn('warning.alpha = 1;', warning.group(1))

    def test_registered_dependencies_exist_with_exact_case(self):
        stages = json.loads((ROOT / 'assets/images/custom_stages/custom_stages.json').read_text())
        cutscenes = json.loads((ROOT / 'assets/images/custom_cutscenes/cutscenes.json').read_text())
        registry = (ROOT / 'assets/images/custom_chars/custom_chars.jsonc').read_text()
        for chart in (ROOT / 'assets/data/chaos').glob('chaos*.json'):
            song = json.loads(chart.read_text())['song']
            self.assertRegex(registry, r'"' + song['player2'] + r'"\s*:\s*\{')
            scripts = {
                f"assets/images/custom_stages/{stages[song['stage']]}.hscript": f"assets/images/custom_stages/{song['stage']}",
                f"assets/images/custom_cutscenes/{cutscenes[song['cutsceneType']]}.hscript": f"assets/images/custom_cutscenes/{song['cutsceneType']}",
                f"assets/images/custom_chars/{song['player2']}.hscript": f"assets/images/custom_chars/{song['player2']}",
                'assets/data/chaos/modchart.hscript': 'assets/data/chaos',
            }
            for script, base in scripts.items():
                text = (ROOT / script).read_text()
                for asset in re.findall(r"hscriptPath\s*\+\s*'([^']+)'", text):
                    self.assertTrue((ROOT / base / asset).is_file(), f'{script}: {asset}')
