"""Focused interpreter tests for the shared Codename transition adapters."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameMusicBeatTransitionTest(unittest.TestCase):
    def test_substate_open_close_do_not_synthesize_state_transitions(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        transition = (ROOT / "source/CodenameMusicBeatTransition.hx").read_text()
        open_state = play_state.index("override function openSubState(SubState:FlxSubState)")
        close_end = play_state.index("function resyncVocals()", open_state)
        lifecycle = play_state[open_state:close_end]
        self.assertNotIn("openLifecycleSubstate", lifecycle)
        self.assertNotIn("openLifecycleResume", lifecycle)
        self.assertIn("super.openSubState(SubState)", lifecycle)
        self.assertIn("super.closeSubState()", lifecycle)
        # Explicit transitions still choose a willing substate as their host.
        self.assertIn("Reflect.field(candidate, 'canOpenCustomTransition') == true", transition)
        self.assertIn("public static function startOwnerOutro", transition)

    def test_transition_song_metadata_is_one_shot_and_owner_scoped(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''class Main {
 static function main() {
  var lease = new CodenameTransitionSongLease();
  var chart:Dynamic = {song: "fixture"};
  var meta:Dynamic = {customValues: {stickerPack: "authored"}};
  lease.capture("owner", chart, meta);
  var view = lease.take("owner", chart);
  if (view == null || view.getField("meta") != meta || view.getField("song") != "fixture")
   throw "metadata/chart lost across handoff";
  if (lease.take("owner", chart) != null) throw "lease reused";
  // The returned view survives clearing the lease, without a gameplay host.
  if (view.getField("song") != "fixture") throw "chart closure retained cleared lease";
  lease.capture("owner", chart, meta);
  if (lease.take("foreign", chart) != null) throw "cross-owner leak";
  lease.capture("owner", chart, meta);
  if (lease.take("owner", {song: "replacement"}) != null) throw "stale chart leak";
  lease.capture("owner", chart, meta);
  lease.clear("foreign");
  if (lease.take("owner", chart) == null) throw "unrelated owner cleared lease";
  lease.capture("owner", chart, meta);
  lease.clear("owner");
  if (lease.take("owner", chart) != null) throw "abandoned lease survived";
 }
}''')
            result = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                     "--run", "Main"], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_selector_incoming_pair_and_static_scope(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''class Main {
 static function main() {
  var a = '/mods/d-sides';
  var b = '/mods/other';
  if (CodenameTransitionScope.setScript(a, 'data/stickerTransition.hx') != 'data/stickerTransition.hx')
   throw 'setter result';
  if (CodenameTransitionScope.script(a) != 'data/stickerTransition.hx') throw 'owner selector';
  if (CodenameTransitionScope.script(b) != '') throw 'selector crossed owner';
  var destination:Dynamic = {name:'destination'};
  if (!CodenameTransitionScope.queueStateTarget(a, destination)) throw 'state target was rejected';
  if (CodenameTransitionScope.takeStateTarget(b) != null) throw 'state target crossed owner';
  if (CodenameTransitionScope.takeStateTarget(a) != destination) throw 'state target was not handed off';
  if (CodenameTransitionScope.takeStateTarget(a) != null) throw 'state target was not one-shot';
  if (CodenameTransitionScope.resolveOwner(a, b) != a
   || CodenameTransitionScope.resolveOwner('', b) != b) throw 'chart owner precedence/fallback';
  CodenameTransitionScope.pushExecutingTransition(a);
  if (CodenameTransitionScope.executingTransitionOwner() != a) throw 'transition execution owner missing';
  CodenameTransitionScope.pushExecutingTransition(b);
  if (CodenameTransitionScope.executingTransitionOwner() != b) throw 'nested transition owner missing';
  CodenameTransitionScope.popExecutingTransition(b);
  if (CodenameTransitionScope.executingTransitionOwner() != a) throw 'transition owner stack was not restored';
  CodenameTransitionScope.popExecutingTransition(a);
  if (CodenameTransitionScope.executingTransitionOwner() != '') throw 'transition owner context leaked';
  if (CodenameTransitionScope.resolveStickerOwner(a, b, b) != a
   || CodenameTransitionScope.resolveStickerOwner('', b, a) != b
   || CodenameTransitionScope.resolveStickerOwner('', '', a) != a)
   throw 'sticker owner precedence';
  if (!CodenameTransitionScope.canRun(a, a) || CodenameTransitionScope.canRun(a, b))
   throw 'lifecycle owner gate';
  var outgoing:Map<String, Dynamic> = new Map();
  outgoing.set('lastStickers', [1, 2, 3]);
  CodenameTransitionScope.captureStaticVariables(a, 'data/stickerTransition.hx', ['lastStickers'], outgoing);
  CodenameTransitionScope.markOutgoingFinished(a);
  if (CodenameTransitionScope.consumeIncoming(b) != '') throw 'cross-owner incoming transition';
  if (CodenameTransitionScope.consumeIncoming(a) != 'data/stickerTransition.hx') throw 'missing incoming half';
  if (CodenameTransitionScope.consumeIncoming(a) != '') throw 'incoming was not one-shot';
  var pauseOwner = '/mods/pause-resume';
  CodenameTransitionScope.setScript(pauseOwner, 'data/stickerTransition.hx');
  CodenameTransitionScope.markOutgoingFinished(pauseOwner, false, 'data/stickerTransition.hx');
  CodenameTransitionScope.setScript(pauseOwner, 'data/states/Dsides/StickerTransition.hx');
  if (CodenameTransitionScope.consumeLifecycleResumeScript(pauseOwner)
   != 'data/stickerTransition.hx') throw 'pause resume did not retain its outgoing script';
  if (CodenameTransitionScope.consumeLifecycleResumeScript(pauseOwner)
   != 'data/states/Dsides/StickerTransition.hx') throw 'resume without an outgoing half ignored the current selector';
  CodenameTransitionScope.clearOwner(pauseOwner);
  var handoffOwner = '/mods/state-handoff';
  CodenameTransitionScope.setScript(handoffOwner, 'data/outgoing.hx');
  CodenameTransitionScope.setScript(handoffOwner, 'data/incoming.hx');
  CodenameTransitionScope.markOutgoingFinished(handoffOwner, true, 'data/outgoing.hx');
  if (CodenameTransitionScope.pendingIncomingOwner() != handoffOwner)
   throw 'state handoff no longer follows the live incoming selector';
  if (CodenameTransitionScope.consumeIncoming(handoffOwner) != 'data/incoming.hx')
   throw 'state handoff incoming script changed';
  CodenameTransitionScope.clearOwner(handoffOwner);
  var c = '/mods/chart-only';
  CodenameTransitionScope.setScript(c, 'data/chartTransition.hx');
  CodenameTransitionScope.markOutgoingFinished(c, true);
  if (CodenameTransitionScope.pendingIncomingOwner() != c
   || !CodenameTransitionScope.canRunOwner(c, '', '') || !CodenameTransitionScope.hasStateHandoff(c))
   throw 'chart owner was not carried across a state switch';
  if (CodenameTransitionScope.consumeIncoming(c) != 'data/chartTransition.hx')
   throw 'chart incoming script missing';
  if (!CodenameTransitionScope.hasStateHandoff(c)) throw 'incoming lease ended before callback';
  if (CodenameTransitionScope.stateHandoffOwner() != c) throw 'handoff owner unavailable to assets';
  CodenameTransitionScope.completeIncoming(c);
  if (CodenameTransitionScope.hasStateHandoff(c)
   || CodenameTransitionScope.canRunOwner(c, '', '')
   || CodenameTransitionScope.stateHandoffOwner() != '') throw 'completed chart owner lease survived';
  CodenameTransitionScope.clearOwner(c);
  var failed = '/mods/failed-incoming';
  CodenameTransitionScope.setScript(failed, 'data/transition.hx');
  CodenameTransitionScope.markOutgoingFinished(failed, true);
  if (!CodenameTransitionScope.shouldAbandonIncoming(false, false))
   throw 'non-MusicBeat destination was not identified as unconsumable';
  if (CodenameTransitionScope.shouldAbandonIncoming(false, true)
   || CodenameTransitionScope.shouldAbandonIncoming(true, false))
   throw 'transient loading or MusicBeat destination was incorrectly abandoned';
  CodenameTransitionScope.abandonIncoming(failed);
  if (CodenameTransitionScope.hasStateHandoff(failed)
   || CodenameTransitionScope.stateHandoffOwner() != '') throw 'failed incoming lease survived abandonment';
  CodenameTransitionScope.clearOwner(failed);
  var incoming:Map<String, Dynamic> = new Map();
  incoming.set('lastStickers', []);
  CodenameTransitionScope.restoreStaticVariables(a, 'data/stickerTransition.hx', ['lastStickers'], incoming);
  if ((cast incoming.get('lastStickers'):Array<Int>).join(',') != '1,2,3') throw 'static array was not restored';
  CodenameTransitionScope.setScript(a, 'data/other.hx');
  CodenameTransitionScope.markOutgoingFinished(a);
  CodenameTransitionScope.setScript(a, '');
  if (CodenameTransitionScope.canRun(a, a)) throw 'empty selector ran a lifecycle transition';
  if (CodenameTransitionScope.consumeIncoming(a) != '') throw 'stale incoming script survived selector change';
  CodenameTransitionScope.clearOwner(a);
  if (CodenameTransitionScope.script(a) != '') throw 'owner selector was not cleared';
  CodenameTransitionScope.queueStateTarget(a, destination);
  CodenameTransitionScope.clearOwner(a);
  if (CodenameTransitionScope.takeStateTarget(a) != null) throw 'owner target survived clear';
  var cleared:Map<String, Dynamic> = new Map();
  CodenameTransitionScope.restoreStaticVariables(a, 'data/stickerTransition.hx', ['lastStickers'], cleared);
  if (cleared.exists('lastStickers')) throw 'owner static state survived clear';
 }
}''')
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_sticker_pack_is_owner_scoped_with_donor_fallback_and_random_api(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "CodenameStickerPack.hx").write_text(
                (ROOT / "source/CodenameStickerPack.hx").read_text()
            )
            stubs = {
                "CodenamePaths.hx": '''class CodenamePaths {
 public var root:String;
 public function new(root:String) this.root = root;
 public function json(key:String):String return root + '/data/' + key + '.json';
}''',
                "CodenameModRuntime.hx": '''class CodenameModRuntime {
 public static var root:String = '/mods/owned';
 public static function activeRoot():String return root;
}''',
                "CodenameMusicBeatTransition.hx": '''class CodenameMusicBeatTransition {
 public static var root:String = '/mods/owned';
 public static function currentOwnerRoot():String return root;
}''',
                "CodenameScriptDiscovery.hx": '''class CodenameScriptDiscovery {
 public static function safeName(value:String):Bool return value != null && value != ''
  && value.indexOf('/') < 0 && value.indexOf('\\\\') < 0 && value.indexOf('..') < 0;
}''',
                "FNFAssets.hx": '''class FNFAssets {
 public static var texts:Map<String, String> = new Map();
 public static function exists(path:String):Bool return texts.exists(path);
 public static function getText(path:String):String return texts.get(path);
}''',
                "flixel/FlxG.hx": '''package flixel;
class FlxG {
 public static var random:Dynamic = {int:function(min:Int, max:Int):Int return min};
}''',
            }
            for name, source in stubs.items():
                dest = base / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(source)
            (base / "Main.hx").write_text(r'''class Main {
 static function main() {
  var root = CodenameModRuntime.activeRoot();
  var defaultPath = root + '/data/stickerpacks/default.json';
  var chosenPath = root + '/data/stickerpacks/known.json';
  FNFAssets.texts.set(defaultPath, '{"name":"Default","artist":"D-Sides","stickers":["default/a","default/b"]}');
  FNFAssets.texts.set(chosenPath, '{"name":"Known","artist":"D-Sides","stickers":["known/a","known/b"]}');
  var chosen = new CodenameStickerPack('known');
  if (chosen.id != 'known' || chosen.getStickerPackName() != 'Known'
   || chosen.getStickerPackArtist() != 'D-Sides') throw 'pack metadata';
  if (chosen.getRandomStickerPath(false) != 'known/a'
   || chosen.getRandomStickerPath(true) != 'known/a') throw 'extra boolean changed donor random behavior';
  var fallback = new CodenameStickerPack('missing');
  if (fallback.id != 'missing' || fallback.getStickerPackName() != 'Default')
   throw 'default fallback or donor id behavior';
  CodenameModRuntime.root = '/mods/foreign';
  CodenameMusicBeatTransition.root = '/mods/foreign';
  var foreignPath = '/mods/foreign/data/stickerpacks/default.json';
  FNFAssets.texts.set(foreignPath, '{"name":"Foreign","artist":"Other","stickers":["foreign"]}');
  if (new CodenameStickerPack('default').getStickerPackName() != 'Foreign') throw 'owner path';
  CodenameMusicBeatTransition.root = '/mods/chart-b';
  var transitionA = '/mods/transition-a/data/stickerpacks/default.json';
  var chartB = '/mods/chart-b/data/stickerpacks/default.json';
  FNFAssets.texts.set(transitionA, '{"name":"Transition A","artist":"A","stickers":["a"]}');
  FNFAssets.texts.set(chartB, '{"name":"Chart B","artist":"B","stickers":["b"]}');
  CodenameTransitionScope.pushExecutingTransition('/mods/transition-a');
  if (new CodenameStickerPack('default').getStickerPackName() != 'Transition A')
   throw 'A transition did not retain its asset owner while chart B was live';
  CodenameTransitionScope.popExecutingTransition('/mods/transition-a');
  if (new CodenameStickerPack('default').getStickerPackName() != 'Chart B')
   throw 'live chart owner did not win outside transition callbacks';
  CodenameMusicBeatTransition.root = '';
  CodenameTransitionScope.setScript('/mods/foreign', 'data/transition.hx');
  CodenameTransitionScope.markOutgoingFinished('/mods/foreign', true);
  if (new CodenameStickerPack('default').getStickerPackName() != 'Foreign')
   throw 'outgoing/incoming chart owner was not used for sticker assets';
  FNFAssets.texts = new Map();
  var error = '';
  try new CodenameStickerPack('missing') catch (caught:Dynamic) error = Std.string(caught);
  if (error.indexOf('Default sticker pack') < 0) throw 'missing default did not fail clearly: ' + error;
  CodenameTransitionScope.clearOwner('/mods/foreign');
 }
}''')
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_transition_lifecycle_and_bindings_include_callbacks_and_cleanup(self):
        transition = (ROOT / "source/CodenameMusicBeatTransition.hx").read_text()
        runtime = (ROOT / "source/CodenameMusicBeatTransitionRuntime.hx").read_text()
        state = (ROOT / "source/MusicBeatState.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        camera = (ROOT / "source/CodenameTransitionCamera.hx").read_text()
        for callback in ("create", "postCreate", "update", "postUpdate", "onSkip",
                         "onFinish", "onPostFinish", "onResize", "destroy"):
            self.assertIn("'" + callback + "'", runtime)
        self.assertIn("CodenameTransitionScope.markOutgoingFinished(ownerRoot, stateHandoff, scriptPath)", transition)
        self.assertLess(transition.index("runtime.captureStaticVariables();"),
                        transition.index("CodenameTransitionScope.markOutgoingFinished(ownerRoot, stateHandoff, scriptPath)"))
        self.assertIn("public function captureStaticVariables():Void", runtime)
        self.assertIn("parentDisabler.reset()", transition)
        self.assertIn("parentDisabler != null && (newState != null || outroComplete != null)", transition)
        self.assertIn("FlxG.cameras.remove(transitionCamera, true)", transition)
        self.assertIn("CodenameMusicBeatTransition.completeTransitionSwitch", state)
        self.assertIn("CodenameMusicBeatTransition.startPendingIncoming(this)", state)
        self.assertIn("CodenameMusicBeatTransition.currentOwnerRoot()", state)
        self.assertNotIn("CodenameMusicBeatTransition.openLifecycleSubstate", play_state)
        self.assertNotIn("CodenameMusicBeatTransition.openLifecycleResume", play_state)
        self.assertIn("consumeLifecycleResumeScript(ownerRoot)", transition)
        self.assertIn("null, false, null, incomingScript", transition)
        self.assertIn("?scriptPathOverride:String", transition)
        self.assertIn("? CodenameTransitionScope.script(ownerRoot) : scriptPathOverride", transition)
        self.assertIn("codenameTransitionOwnerRoot():String return codenameSelectedRoot()", play_state)
        self.assertIn("CodenameMusicBeatTransition.releaseChartOwner(codenameTransitionOwner)", play_state)
        self.assertIn("CodenameMusicBeatTransition.canRunOwner(ownerRoot)", runtime)
        self.assertIn("CodenameTransitionScope.pendingIncomingOwner()", transition)
        self.assertIn("CodenameTransitionScope.completeIncoming(ownerRoot)", transition)
        self.assertIn("play.codenameTransitionOwnerRoot()", transition)
        self.assertIn("CodenameTransitionScope.resolveOwner(chartOwner", transition)
        self.assertIn("FlxG.signals.preStateCreate.add(incomingStateHandler)", transition)
        self.assertIn("shouldAbandonIncoming(isMusicBeatState,", transition)
        self.assertIn("isLoadingWrapper))", transition)
        self.assertIn("if (!openForOwner(owner, null, false, null, null, null, null, songView))", transition)
        self.assertIn("CodenameTransitionScope.takeStateTarget(owner)", transition)
        self.assertIn("transition.scriptNewState = cast scriptStateTarget", transition)
        self.assertIn("new CodenameMusicBeatTransitionEvent(transOut, scriptNewState)", transition)
        self.assertIn("CodenameTransitionScope.abandonIncoming(ownerRoot)", transition)
        self.assertIn("CodenameTransitionScope.canRun(ownerRoot", transition)
        self.assertIn("transOut,", transition)
        self.assertIn("new CodenameTransitionCamera()", transition)
        self.assertIn("public var transitionCamera:CodenameTransitionCamera", transition)
        self.assertIn("public var flipY:Bool = false", camera)
        self.assertIn("CodenameMusicBeatTransition", bindings)
        self.assertIn("CodenameStickerPack", bindings)
        self.assertIn("flixel.util.FlxTimerManager", bindings)
        self.assertIn("haxe.io.Path", bindings)
        self.assertIn("interp.variables.set('newState', host.scriptNewState)", runtime)
        mod_runtime = (ROOT / "source/CodenameModRuntime.hx").read_text()
        self.assertIn("CodenameTransitionScope.queueStateTarget(root, target)", mod_runtime)
        self.assertIn("CodenameTransitionScope.clearPendingStateTarget(root)", mod_runtime)
        self.assertIn("switchStateForCurrentOwner(target:FlxState)", transition)
        loading = (ROOT / "source/LoadingState.hx").read_text()
        self.assertIn("CodenameMusicBeatTransition.switchStateForCurrentOwner(target)", loading)
        self.assertIn("switchState(new LoadingState())", loading)


if __name__ == "__main__":
    unittest.main()
