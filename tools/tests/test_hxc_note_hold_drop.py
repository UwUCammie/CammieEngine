"""Letting go of a hold early reaches scripts as one cancelable event."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]

NOTE_KIND = '''
class StickyNote extends ScriptedNoteKind {
    function new() { super("sticky", "Sticky note"); }
    override function onNoteHoldDrop(event) {
        if (event.holdNote.strumTime < 2000) {
            event.cancel();
            return;
        }
        event.healthChange = event.healthChange * 3;
        event.score = -100;
    }
}
'''


class HxcNoteHoldDropTest(unittest.TestCase):
    def test_translated_hold_drop_handler_sees_and_changes_the_event(self):
        fixture = f'''import hscript.Interp;
import hscript.Parser;
class HoldDropFixture {{
    static function fail(message:String):Void throw message;
    static function head(time:Float):Dynamic
        return {{strumTime: time, noteData: 1, rating: "sick", isSustainNote: false,
            mustPress: true, alive: true, sustainLength: 400.0}};
    static function main() {{
        var result = HxcCompat.analyze({json.dumps(NOTE_KIND)}, "scripts/notes/sticky.hxc");
        if (result.canonicalCallbacks.indexOf("noteHoldDrop") < 0)
            fail("hold drop was not recognised as a callback: " + result.canonicalCallbacks);
        var adapted = false;
        for (adapter in (cast result.callbackAdapters:Array<Dynamic>))
            if (adapter.canonicalName == "noteHoldDrop" && adapter.safe) adapted = true;
        if (!adapted) fail("no callback adapter for the hold drop");
        if (EngineCompat.canonicalCallback("onNoteHoldDrop") != "noteHoldDrop")
            fail("canonical name");
        if (EngineCompat.callbackNames("noteHoldDrop").indexOf("onNoteHoldDrop") < 0)
            fail("script spelling is not looked up");

        var interp = new Interp();
        interp.execute(new Parser().parseString(result.generatedHscript));
        var handler = interp.variables.get("noteHoldDrop");
        if (handler == null) fail("generated handler missing: " + result.generatedHscript);

        // The interpreter gets the shared event object, not a copy.
        var early = NoteJudgementOutcome.miss(-0.04, -5, true, true, 12);
        var earlyEvent = EngineCompat.hxcHoldNotePayload(head(1000), true, 1, early);
        var passed = EngineCompat.callbackArguments("noteHoldDrop", "noteHoldDrop",
            [head(1000), true, 1, earlyEvent], true);
        if (passed.length != 1 || passed[0] != earlyEvent) fail("event object was not shared");
        if (earlyEvent.holdNote == null || earlyEvent.holdNote.strumTime != 1000) fail("holdNote view");
        if (earlyEvent.healthChange != -0.04 || earlyEvent.score != -5 || earlyEvent.isComboBreak != true)
            fail("seeded penalty");
        Reflect.callMethod(null, handler, [earlyEvent]);
        if (!EngineCompat.hxcPayloadCanceled(earlyEvent) || earlyEvent.eventCanceled != true)
            fail("cancel did not mark the event");

        var late = NoteJudgementOutcome.miss(-0.04, -5, true, true, 12);
        var lateEvent = EngineCompat.hxcHoldNotePayload(head(3000), true, 1, late);
        Reflect.callMethod(null, handler, [lateEvent]);
        EngineCompat.hxcApplyNoteOutcome(lateEvent, late);
        if (EngineCompat.hxcPayloadCanceled(lateEvent)) fail("later hold was cancelled");
        if (Math.abs(late.healthChange + 0.12) > 0.000001 || late.score != -100)
            fail("penalty writes: " + late.healthChange + " / " + late.score);

        // Without a tracked outcome the fields still read as plain values.
        var bare = EngineCompat.hxcHoldNotePayload(head(3000), true, 1);
        if (bare.healthChange != 0 || bare.score != 0 || bare.holdNote == null) fail("bare event");
        Sys.println("ok");
    }}
}}
'''
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "HoldDropFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "HoldDropFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_playstate_sends_the_drop_once_per_hold_from_the_sustain_miss_path(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        miss = source[source.index("function noteMissCore("):source.index("function badNoteCheck(")]
        hook = miss.index("onHoldDropped(note, playerOne, direction, missOutcome)")
        self.assertIn("note != null && note.isSustainNote && playerOne", miss[:hook])
        # The drop is announced before the per-piece miss event and its penalty.
        self.assertLess(hook, miss.index('callHxcNoteHScript("noteMiss"'))
        self.assertLess(hook, miss.index("misses += 1;"))

        dropped = source[source.index("function onHoldDropped("):source.index("var activeHitOutcome:")]
        # One event per hold: later pieces reuse the stored answer.
        # With no event-object script loaded nothing is looked up or stored.
        self.assertLess(dropped.index("if (!hasEventObjectScope())"),
            dropped.index("NoteHoldCoverCompat.resolveHead(piece)"))
        guard = dropped.index("if (droppedHolds.exists(head))")
        dispatch = dropped.index("callHxcNoteHScript('noteHoldDrop'")
        self.assertLess(guard, dispatch)
        self.assertLess(dropped.index("if (!head.wasGoodHit)"), dispatch)
        self.assertIn("NoteHoldCoverCompat.resolveHead(piece)", dropped)
        self.assertIn("droppedHolds.set(head, forgiven);", dropped)
        self.assertIn("var droppedHolds:haxe.ds.ObjectMap<Note, Bool> = new haxe.ds.ObjectMap<Note, Bool>();", source)


if __name__ == "__main__":
    unittest.main()
