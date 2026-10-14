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
        self.assertLess(asked, opening.index("FlxG.sound.music.pause();"))
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


if __name__ == "__main__":
    unittest.main()
