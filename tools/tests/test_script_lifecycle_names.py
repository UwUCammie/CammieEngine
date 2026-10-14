"""The two lifecycle name tables agree, and the newer hooks are dispatched."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]

MODULE = '''
class DoorKeeper extends Module {
    function new() { super("door-keeper"); }
    override function onSubStateOpenBegin(event) { if (event.targetState != null) event.cancel(); }
    override function onFocusLost(event) { trace("away"); }
    override function onNoteHoldDrop(event) { event.cancel(); }
}
'''

# Script spellings both tables must resolve to the same game-side hook.
SHARED_SPELLINGS = [
    "onNoteHit", "onNoteMiss", "onNoteGhostMiss", "onNoteHoldDrop", "onNoteIncoming",
    "onSongEnd", "onSongRetry", "onSongEvent", "onPause", "onResume",
    "onSubStateOpenBegin", "onSubStateOpenEnd", "onSubStateCloseBegin", "onSubStateCloseEnd",
    "onStateChangeBegin", "onStateChangeEnd", "onFocusGained", "onFocusLost",
    "onGameOver", "onDestroy", "onDifficultySwitch", "onCapsuleSelected",
]


class ScriptLifecycleNamesTest(unittest.TestCase):
    def test_tables_agree_and_new_hooks_are_recognised(self):
        fixture = f'''import hscript.Interp;
import hscript.Parser;
class LifecycleNamesFixture {{
    static function fail(message:String):Void throw message;
    static function main() {{
        var spellings:Array<String> = {json.dumps(SHARED_SPELLINGS)};
        for (spelling in spellings) {{
            var canonical = EngineCompat.canonicalCallback(spelling);
            if (canonical == spelling) fail("game table does not know " + spelling);
            var translated:String = @:privateAccess HxcCompat.lifecycleCallback(spelling);
            if (translated != canonical)
                fail(spelling + " maps to " + translated + " in the translator but " + canonical + " in the game");
            if (EngineCompat.callbackNames(canonical).indexOf(spelling) < 0)
                fail(canonical + " does not look up the script spelling " + spelling);
        }}
        var result = HxcCompat.analyze({json.dumps(MODULE)}, "scripts/modules/door.hxc");
        for (name in ["subStateOpenBegin", "focusLost", "noteHoldDrop"])
            if (result.canonicalCallbacks.indexOf(name) < 0)
                fail("not routed: " + name + " in " + result.canonicalCallbacks);
        for (finding in (cast result.diagnostics:Array<Dynamic>))
            if (finding.code == "unsupported-hxc-payload-field")
                fail("substate target was diagnosed: " + finding.message);
        var interp = new Interp();
        interp.variables.set("trace", function(value:Dynamic) {{}});
        interp.execute(new Parser().parseString(result.generatedHscript));
        var opening = EngineCompat.hxcLifecyclePayload("subStateOpenBegin", {{targetState: {{}}}});
        Reflect.callMethod(null, interp.variables.get("subStateOpenBegin"), [opening]);
        if (!EngineCompat.hxcPayloadCanceled(opening)) fail("substate open was not cancelled");
        var nothing = EngineCompat.hxcLifecyclePayload("subStateOpenBegin", {{targetState: null}});
        Reflect.callMethod(null, interp.variables.get("subStateOpenBegin"), [nothing]);
        if (EngineCompat.hxcPayloadCanceled(nothing)) fail("handler cancelled without a target");
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "LifecycleNamesFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "LifecycleNamesFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_playstate_asks_before_opening_a_substate_and_reports_focus_loss(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        opening = source[source.index("override function openSubState("):
            source.index("override function closeSubState(")]
        asked = opening.index("dispatchCancelableHxcLifecycle('subStateOpenBegin',")
        self.assertLess(asked, opening.index("super.openSubState(SubState);"))
        # Nothing is paused or announced for a substate a script refused.
        self.assertLess(asked, opening.index("dispatchPsychCompiledStage('openSubState'"))
        self.assertLess(asked, opening.index("pauseGameplayAudio();"))
        refused = opening[asked:opening.index("subStateOpensAccepted++;")]
        self.assertIn("subStateOpenRefused();", refused)
        self.assertIn("return;", refused)
        undo = source[source.index("function subStateOpenRefused("):
            source.index("function psychSourceSubstateSemantics(")]
        self.assertIn("cancelPendingGameOver();", undo)
        # The pause menu freezes the camera tweens before it asks to open.
        self.assertIn("CoolUtil.resumeTween(curCamPos);", undo)
        self.assertIn("paused = false;", undo)

        focus = source[source.index("override public function onFocusLost("):
            source.index("function subStateOpenRefused(")]
        self.assertIn("callAllHScript('focusLost', "
            "[EngineCompat.hxcLifecyclePayload('focusLost', {targetState: this})]);", focus)

    def test_one_table_feeds_the_game_and_the_translator(self):
        module = '''
class Watcher extends Module {
    function new() { super("watcher", 3); }
    override function onStateCreate(event) { trace("made"); }
    override function onScriptEvent(event) { trace("any"); }
    override function onSongSelected(event) { trace("picked"); }
    override function onDialogueEnd(event) { trace("done"); }
    function start() { trace("plain helper"); }
}
'''
        fixture = f'''class LifecycleTableFixture {{
    static function fail(message:String):Void throw message;
    static function main() {{
        for (entry in ScriptLifecycleNames.ENTRIES) {{
            if (EngineCompat.canonicalCallback(entry.canonical) != entry.canonical) fail("canonical " + entry.canonical);
            var names = EngineCompat.callbackNames(entry.canonical);
            for (spelling in entry.broadcast) {{
                if (EngineCompat.canonicalCallback(spelling) != entry.canonical) fail("broadcast " + spelling);
                if (names.indexOf(spelling) < 0) fail(entry.canonical + " does not try " + spelling);
            }}
            for (alias in entry.aliases)
                if (EngineCompat.canonicalCallback(alias) != entry.canonical) fail("alias " + alias);
            // Every V-Slice onX spelling means the same hook to the translator and the game.
            for (spelling in entry.vslice)
                if (StringTools.startsWith(spelling, "on")) {{
                    var translated:String = @:privateAccess HxcCompat.lifecycleCallback(spelling);
                    if (translated != entry.canonical || EngineCompat.canonicalCallback(spelling) != entry.canonical)
                        fail("tables disagree on " + spelling);
                }}
        }}
        // Spellings each side kept before the merge.
        if (EngineCompat.canonicalCallback("missNote") != "noteMiss") fail("missNote");
        if (EngineCompat.canonicalCallback("gameOverStart") != "gameOver") fail("gameOverStart");
        if (EngineCompat.canonicalCallback("onTimerCompleted") != "timerCompleted") fail("timer");
        if (@:privateAccess HxcCompat.lifecycleCallback("step") != "stepHit") fail("step");
        if (@:privateAccess HxcCompat.lifecycleCallback("create") != "start") fail("create");
        if (@:privateAccess HxcCompat.lifecycleCallback("start") != "") fail("start is a helper in a V-Slice class");
        if (@:privateAccess HxcCompat.lifecycleCallback("onTimerCompleted") != "") fail("Psych hook taken as V-Slice");
        if (@:privateAccess HxcCompat.lifecycleCallback("new") != "") fail("constructor");
        if (EngineCompat.canonicalCallback("myOwnHook") != "myOwnHook") fail("unknown name changed");
        var names = EngineCompat.callbackNames("subStateOpenEnd");
        if (names.join(",") != "subStateOpenEnd,onSubStateOpenEnd,onPauseSubstateOpen") fail("order " + names.join(","));
        var hooks = @:privateAccess HxcCompat.lifecycleNames;
        for (name in ["onCreate", "onEndSong", "onPauseSubstateOpen", "onStateOpenEnd", "onFocusLost", "onStateCreate", "onDialogueEnd"])
            if (hooks.indexOf(name) < 0) fail("hook list misses " + name);
        var result = HxcCompat.analyze({json.dumps(module)}, "scripts/modules/watcher.hxc");
        for (name in ["stateCreate", "scriptEvent", "songSelected", "dialogueEnd"])
            if (result.canonicalCallbacks.indexOf(name) < 0) fail("not routed: " + name + " in " + result.canonicalCallbacks);
        if (result.canonicalCallbacks.indexOf("start") >= 0) fail("helper routed as a hook");
        if (result.modulePriority != 3) fail("priority " + result.modulePriority);
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "LifecycleTableFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-main", "LifecycleTableFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_modules_hear_state_create_before_song_loaded(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        loaded = source[source.index("if (!hxcSongLoadedDispatched) {"):]
        loaded = loaded[:loaded.index("countdown:song-loaded-callbacks-complete")]
        self.assertLess(loaded.index("callAllHScript('stateCreate',"), loaded.index("callAllHScript('songLoaded',"))
        # The script load that creates the modules runs before both.
        countdown = source[source.index("public function startCountdown():Void {"):]
        self.assertLess(countdown.index("loadHxcCompatScripts();"), countdown.index("callAllHScript('stateCreate',"))


if __name__ == "__main__":
    unittest.main()
