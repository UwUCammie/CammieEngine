"""Exercise the actual HXC dispatch used by an autonomous opponent note hit."""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class HxcAutoHitRouteTest(unittest.TestCase):
    def test_opponent_hit_dispatches_without_input_and_respects_cancellation(self):
        state = (ROOT / "source/PlayState.hx").read_text()
        start = state.index("\tfunction dispatchHxcAutoNoteHit(")
        end = state.index("\n\tfunction goodNoteHit(", start)
        method = state[start:end]
        main = r'''
class Note {
  public var rating = "miss";
  public var alive = true;
  public var wasGoodHit = true;
  public var autoHitSuppressed = false;
  public var isSustainNote = false;
  public var destroyed = false;
  public function new() {}
  public function destroy():Void destroyed = true;
}
class FakeNotes {
  public var removed = 0;
  public function new() {}
  public function remove(note:Note, splice:Bool):Bool { removed++; return true; }
}
class EngineCompat {
  public static var applied = 0;
  public static function hxcNoteCallbackPayload(args:Array<Dynamic>, name:String):Dynamic {
    return {judgement: args[1].rating,
      playerOne: args[0], eventCanceled: false, canceled: false, cancelled: false};
  }
  public static function hxcApplyNoteCallbackPayload(event:Dynamic):Void applied++;
}
class TestState {
  public var notes = new FakeNotes();
  public var methods:Array<String> = [];
  public var cancel = false;
  public var kill = false;
  public var textCues = 0;
  public function new() {}
  function callHxcNoteHScript(name:String, args:Array<Dynamic>):Void {
    methods.push(name);
    if (name == "noteHit") {
      if (args[3].judgement == "perfect") textCues++;
      if (cancel) args[3].eventCanceled = true;
      if (kill) args[1].alive = false;
    }
  }
''' + method + r'''
  public function fire(note:Note, playerOne:Bool):Bool
    return dispatchHxcAutoNoteHit(note, playerOne);
}
class Main {
  static function check(ok:Bool, message:String):Void if (!ok) throw message;
  static function main():Void {
    var state = new TestState();
    var note = new Note();
    check(state.fire(note, false), "ordinary autonomous opponent hit should proceed");
    check(note.rating == "sick" && state.textCues == 1,
      "autonomous hit must supply perfect judgement to module");
    check(state.methods.join(",") == "noteHit,opponentNoteHit",
      "opponent route must dispatch both HXC callbacks once");
    check(EngineCompat.applied == 1 && state.notes.removed == 0,
      "normal hit should apply mutable payload without early removal");
    var hold = new TestState(); var segment = new Note(); segment.isSustainNote = true;
    check(hold.fire(segment, false) && hold.methods.length == 0,
      "legacy sustain pieces must not duplicate V-Slice head hit callbacks");
    var canceled = new TestState(); canceled.cancel = true;
    var canceledNote = new Note();
    check(!canceled.fire(canceledNote, false), "canceled hit must stop native branch");
    check(!canceledNote.wasGoodHit && canceledNote.autoHitSuppressed,
      "canceled autonomous hit must not retry next frame");
    check(canceled.notes.removed == 0 && !canceledNote.destroyed,
      "canceled, live note should remain owned by note lifecycle");
    var killed = new TestState(); killed.kill = true;
    var killedNote = new Note();
    check(!killed.fire(killedNote, false), "killed hit must stop native branch");
    check(killed.notes.removed == 1 && killedNote.destroyed,
      "script-killed note must be removed and destroyed");
    var ghost = new TestState();
    check(!ghost.fire(null, false) && ghost.methods.length == 0,
      "ghost input has no note-hit callback");
    var player = new TestState();
    check(player.fire(new Note(), true)
      && player.methods.join(",") == "noteHit,goodNoteHit",
      "owner callback reflects actual note side");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(main)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_live_opponent_branch_uses_shared_route_before_removal(self):
        state = (ROOT / "source/PlayState.hx").read_text()
        start = state.index("if (!daNote.mustPress && daNote.wasGoodHit")
        end = state.index("} else if (daNote.mustPress && daNote.wasGoodHit", start)
        opponent = state[start:end]
        self.assertLess(opponent.index("dispatchHxcAutoNoteHit(daNote, false)"),
                        opponent.index("daNote.kill()"))
        player_start = state.index("} else if (daNote.mustPress && daNote.wasGoodHit", end)
        player_end = state.index("var neg = downscroll", player_start)
        player_bot = state[player_start:player_end]
        self.assertLess(player_bot.index("dispatchHxcAutoNoteHit(daNote, true)"),
                        player_bot.index("applyDemoHealth(daNote)"))

    def test_manual_hit_skips_generated_sustain_segments(self):
        state = (ROOT / "source/PlayState.hx").read_text()
        start = state.index("function goodNoteHit(note:Note, playerOne:Bool)")
        gate = state.index("// V-Slice's authored hold uses a separate SustainTrail.", start)
        body = state[gate:state.index("EngineCompat.hxcApplyNoteCallbackPayload(hxcHitEvent);", gate)]
        self.assertIn("if (!note.isSustainNote) {", body)
        self.assertIn('callHxcNoteHScript("noteHit"', body)
        self.assertIn('callAllHScript(playerOne ? "goodNoteHit" : "opponentNoteHit", [note, playerOne], true);', state)


if __name__ == "__main__":
    unittest.main()
