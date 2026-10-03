"""Exercise the actual HXC dispatch used by an autonomous opponent note hit."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class HxcAutoHitRouteTest(unittest.TestCase):
    def test_opponent_hit_dispatches_without_input_and_respects_cancellation(self):
        state = (ROOT / "source/PlayState.hx").read_text()
        start = state.index("\tfunction dispatchHxcAutoNoteHit(")
        end = state.index("\n\tfunction goodNoteHit(", start)
        method = state[start:end]
        pre_start = state.index("\tfunction dispatchNightmareVisionNoteHitPre(")
        pre_end = state.index("\n\tfunction dispatchNightmareVisionNoteHit(", pre_start)
        pre_method = state[pre_start:pre_end]
        main = r'''
class Note {
  public var rating = "miss";
  public var alive = true;
  public var wasGoodHit = true;
  public var autoHitSuppressed = false;
  public var isSustainNote = false;
  public var sourcePlayfieldIndex = 1;
  public var sourceDirection = 0;
  public var nightmareVisionTypeRuntime:Dynamic = {};
  public var nightmareVisionSustainEnd = false;
  public var nightmareVisionTailState:Dynamic;
  public var destroyed = false;
  public function new() nightmareVisionTailState = {active:false, missed:false, notes:[]};
  public function destroy():Void destroyed = true;
}
class FakeStrum {
  public var ID:Int;
  public var lastNote:Note;
  public var playConfirms = 0;
  public var resetAnim = 0.0;
  public var coyoteTime = 0.0;
  var order:Array<String>;
  public function new(id:Int, order:Array<String>) { ID=id; this.order=order; }
  public function playConfirm(sustain:Bool, force:Bool):Void {
    playConfirms++;
    order.push("confirm");
  }
}
class FakeLine { public var members:Array<FakeStrum>; public function new(strum:FakeStrum) members=[strum]; }
class FakeField {
  public var ID:Int;
  public var playerControls:Bool;
  public var playAnims = true;
  public var autoPlayed:Bool;
  public var holdDropLeniency = 1 / 3;
  public function new(id:Int, player:Bool, autoplay:Bool) {
    ID=id; playerControls=player; autoPlayed=autoplay;
  }
}
class FakeScripts {
  public var calls:Array<String> = [];
  var order:Array<String>;
  public function new(order:Array<String>) this.order=order;
  public function call(name:String, args:Array<Dynamic>):Dynamic {
    calls.push(name); order.push("source:" + name); return null;
  }
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
  public var order:Array<String> = [];
  public var sourceScripts:FakeScripts;
  public var nightmareVisionScripts:FakeScripts;
  public var fields:Array<FakeField>;
  public var lines:Array<FakeLine>;
  public var playbackRate = 2.0;
  public var cancel = false;
  public var kill = false;
  public var textCues = 0;
  public function new() {
    sourceScripts = new FakeScripts(order);
    nightmareVisionScripts = sourceScripts;
    fields = [new FakeField(0, true, false), new FakeField(1, false, true)];
    lines = [new FakeLine(new FakeStrum(0, order)), new FakeLine(new FakeStrum(0, order))];
  }
  function getNightmareVisionField(id:Int):FakeField return fields[id];
  function getNoteStrumline(note:Note):FakeLine return lines[note.sourcePlayfieldIndex];
  function sustain2(strum:Int, spr:FakeStrum, note:Note):Void {
    order.push("bookkeeping");
    var field = getNightmareVisionField(note.sourcePlayfieldIndex);
    if (note.nightmareVisionTypeRuntime != null) {
      if (field.autoPlayed) spr.resetAnim = (0.15
        + (note.isSustainNote && !note.nightmareVisionSustainEnd ? 0.15 : 0)) / playbackRate;
      if (note.isSustainNote) spr.coyoteTime = field.holdDropLeniency;
      else if (note.nightmareVisionTailState != null) note.nightmareVisionTailState.active = true;
    }
  }
''' + pre_method + r'''
  function callHxcNoteHScript(name:String, args:Array<Dynamic>):Void {
    methods.push(name);
    order.push("hxc:" + name);
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
    check(state.sourceScripts.calls.join(",") == "opponentNoteHitPre",
      "source Pre callback runs before an autonomous opponent hit");
    var opponentStrum = state.lines[1].members[0];
    check(opponentStrum.lastNote == note && opponentStrum.playConfirms == 1
      && note.nightmareVisionTailState.active,
      "source hit Pre applies receptor and tail bookkeeping");
    check(state.order.join(",") == "source:opponentNoteHitPre,confirm,bookkeeping,hxc:noteHit,hxc:opponentNoteHit",
      "source callback and receptor bookkeeping precede HXC hit callbacks");
    check(EngineCompat.applied == 1 && state.notes.removed == 0,
      "normal hit should apply mutable payload without early removal");
    var hold = new TestState(); var segment = new Note(); segment.isSustainNote = true;
    check(hold.fire(segment, false) && hold.methods.length == 0,
      "legacy sustain pieces must not duplicate V-Slice head hit callbacks");
    check(hold.lines[1].members[0].coyoteTime == 1 / 3
      && hold.lines[1].members[0].resetAnim == 0.15,
      "source sustain Pre refreshes hold grace and playback-rate-adjusted reset time");
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
            Path(folder, "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
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
        start = state.index("function goodNoteHit(note:Note, playerOne:Bool")
        gate = state.index("// V-Slice's authored hold uses a separate SustainTrail.", start)
        body = state[gate:state.index("EngineCompat.hxcApplyNoteCallbackPayload(hxcHitEvent);", gate)]
        self.assertIn("if (!note.isSustainNote) {", body)
        self.assertIn('callHxcNoteHScript("noteHit"', body)
        self.assertIn('callAllHScript(playerOne ? "goodNoteHit" : "opponentNoteHit", [note, playerOne], true);', state)


if __name__ == "__main__":
    unittest.main()
