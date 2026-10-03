"""Native note judgement is ready before imported pre-hit callbacks run."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HitRatingPreCallbackTest(unittest.TestCase):
    def test_smoke_driver_hits_due_player_notes_through_normal_route(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tfunction runtimeSmokePlayerHits():Void {")
        end = source.index("\n\t// keeps the highway", start)
        method = source[start:end]
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        flag = harness[harness.index("case '--smoke-player-hits':"):]
        self.assertIn("result.practice = true;", flag[:200])
        self.assertIn("if (RuntimeSmokeHarness.playerHitsEnabled())", source)
        fixture = r'''
class Note {
 public var strumTime:Float = 100;
 public var alive:Bool = true;
 public var mustPress:Bool = true;
 public var wasGoodHit:Bool = false;
 public var canBeHit:Bool = true;
 public var tooLate:Bool = false;
 public var autoHit:Bool = true;
 public function new() {}
 public function canAutoHit():Bool return autoHit;
}
class Conductor { public static var songPosition:Float = 100; }
class RuntimeSmokeHarness {
 public static var delay:Float = 0;
 public static function playerHitDelayMs():Float return delay;
}
class SmokeHitFixture {
 var startingSong:Bool = false;
 var paused:Bool = false;
 var generatedMusic:Bool = true;
 var notes:{members:Array<Note>} = {members: []};
 var hits:Array<Note> = [];
 function new() {}
 function goodNoteHit(note:Note, player:Bool):Void {
  if (!player) throw 'wrong hit owner';
  hits.push(note); notes.members.remove(note);
 }
''' + method + r'''
 static function main() {
  var state = new SmokeHitFixture();
  var first = new Note(); var second = new Note();
  var future = new Note(); future.strumTime = 101;
  var opponent = new Note(); opponent.mustPress = false;
  var avoid = new Note(); avoid.autoHit = false;
  var late = new Note(); late.tooLate = true;
  var dead = new Note(); dead.alive = false;
  state.notes.members = [first, future, opponent, avoid, late, dead, second];
  state.paused = true; state.runtimeSmokePlayerHits();
  if (state.hits.length != 0) throw 'hit while paused';
  state.paused = false; state.runtimeSmokePlayerHits();
  if (state.hits.length != 2 || state.hits[0] != first || state.hits[1] != second)
   throw 'smoke hit filtering or mutation snapshot failed';
  state.notes.members = [new Note()];
  RuntimeSmokeHarness.delay = 185;
  state.runtimeSmokePlayerHits();
  if (state.hits.length != 2) throw 'delayed hit fired immediately';
  Conductor.songPosition = 284.999;
  state.runtimeSmokePlayerHits();
  if (state.hits.length != 2) throw 'delayed hit fired before due time';
  Conductor.songPosition = 285;
  state.runtimeSmokePlayerHits();
  if (state.hits.length != 3) throw 'delayed hit did not reach the normal route';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "SmokeHitFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "SmokeHitFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rating_and_score_share_timing_before_hxc_payload(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tstatic function adjustedNoteDiff(note:Note):Float {")
        end = source.index("\n\tfunction goodNoteHit(", start)
        methods = source[start:source.index("\n\t/** Match the pre-judgement HXC route", start)]
        good_hit = source[end:source.index("\n\tvar sectionSteps:", end)]
        self.assertLess(good_hit.index("note.rating = noteRatingAtHit(note);"),
                        good_hit.index("EngineCompat.hxcNoteCallbackPayload("))
        score_start = source.index("\tprivate function popUpScore(")
        score = source[score_start:score_start + 900]
        self.assertIn("var noteDiff:Float = adjustedNoteDiff(daNote);", score)
        self.assertIn("daNote.rating = noteRatingAtHit(daNote);", score)

        fixture = r'''
class Note {
 public var strumTime:Float;
 public var mineNote:Bool;
 public var nukeNote:Bool;
 public function new(time:Float, mine:Bool = false, nuke:Bool = false) {
  strumTime = time; mineNote = mine; nukeNote = nuke;
 }
}
class Conductor { public static var songPosition:Float = 100; }
class Ratings {
 public static function CalculateRating(diff:Float):String
  return diff <= 10 ? 'sick' : 'good';
}
class HitRatingFixture {
''' + methods + r'''
 static function main() {
  var plain = new Note(108);
  var mine = new Note(108, true);
  var nuke = new Note(108, false, true);
  if (adjustedNoteDiff(plain) != 8 || noteRatingAtHit(plain) != 'sick')
   throw 'ordinary timing changed';
  if (adjustedNoteDiff(mine) <= 15 || noteRatingAtHit(mine) != 'good')
   throw 'mine window was not shared';
  if (adjustedNoteDiff(nuke) != 24 || noteRatingAtHit(nuke) != 'good')
   throw 'nuke window was not shared';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "HitRatingFixture.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "HitRatingFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
