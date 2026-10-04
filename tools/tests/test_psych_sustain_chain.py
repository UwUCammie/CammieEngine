"""Exercise the Psych GH-sustain chain helpers and donor quirks."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
DONOR_PLAY_STATE = ROOT.parent / "fnf_sources/FNF-PsychEngine/source/states/PlayState.hx"

MAIN = r'''package;
class FakeNote {
 public var parent:FakeNote;
 public var isSustainNote:Bool;
 public var wasGoodHit:Bool;
 public var tail:Array<FakeNote>;
 public var alpha:Float=1.0;
 public var missed:Bool=false;
 public var ignoreNote:Bool=false;
 public var tooLate:Bool=false;
 public var cachedCanBeHit:Bool=true;
 public var canBeHit(get, set):Bool;
 function get_canBeHit():Bool return cachedCanBeHit;
 function set_canBeHit(value:Bool):Bool { cachedCanBeHit=value; return value; }
 public function new(?parent:FakeNote, ?sustain:Bool=false, ?good:Bool=false, ?tail:Array<FakeNote>) {
  this.parent=parent; this.isSustainNote=sustain; this.wasGoodHit=good;
  this.tail=tail == null ? [] : tail;
 }
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) throw message + ': expected ' + Std.string(expected) + ', got ' + Std.string(actual);
 static function note(?parent:FakeNote, ?sustain:Bool=false, ?good:Bool=false, ?tail:Array<FakeNote>):FakeNote
  return new FakeNote(parent, sustain, good, tail);
 static function main():Void {
  var unmatched = note(null, true);
  check(!PsychSustainChain.canHitSustain(unmatched, true), 'GH sustain with no parent must be rejected');
  check(PsychSustainChain.canHitSustain(unmatched, false), 'disabled GH mode must leave sustain unrestricted');
  check(PsychSustainChain.canHitSustain(note(), true), 'ordinary note must not require a parent');
  var notHitParent = note();
  check(!PsychSustainChain.canHitSustain(note(notHitParent, true), true), 'sustain must wait for parent hit');
  var hitParent = note(null, false, true);
  check(PsychSustainChain.canHitSustain(note(hitParent, true), true), 'sustain can hit after parent succeeds');
  check(!PsychSustainChain.canHitSustain(null, true), 'null note is not hittable in GH mode');
  check(PsychSustainChain.canHitSustain(null, false), 'disabled GH mode does not add a hit restriction');

  var first = note(); var second = note();
  var head = note(null, false, false, [first, second]);
  check(!PsychSustainChain.prepareMiss(head, true), 'head miss marks chain then takes donor early return');
  eq(head.alpha, 0.35, 'missed head alpha');
  eq(head.missed, true, 'missed head flag');
  eq(head.canBeHit, false, 'missed head hit flag');
  eq(head.cachedCanBeHit, false, 'head setter updates cached canBeHit');
  for (child in [first, second]) {
   eq(child.alpha, 0.35, 'head miss copies alpha to each tail child');
   eq(child.missed, true, 'head miss marks each tail child missed');
   eq(child.canBeHit, false, 'head miss makes child unhittable');
   eq(child.cachedCanBeHit, false, 'head miss updates each canBeHit accessor');
   eq(child.ignoreNote, true, 'head miss ignores each child');
   eq(child.tooLate, true, 'head miss marks each child late');
  }

  var previouslyMissedHead = note(); previouslyMissedHead.missed = true;
  check(!PsychSustainChain.prepareMiss(previouslyMissedHead, true), 'already missed head early returns without a tail');
  check(PsychSustainChain.prepareMiss(note(), true), 'unmissed head without a tail continues normal miss accounting');
  var disabledHead = note(null, false, false, [note()]);
  check(PsychSustainChain.prepareMiss(disabledHead, false) && !disabledHead.missed,
   'disabled GH mode skips chain mutation and continues miss accounting');
  check(PsychSustainChain.prepareMiss(null, true), 'null note has no sustain-chain early return');

  var missedChildParent = note(); missedChildParent.wasGoodHit = true;
  var alreadyMissedChild = note(missedChildParent, true); alreadyMissedChild.missed = true;
  var untouchedSibling = note(); missedChildParent.tail = [alreadyMissedChild, untouchedSibling];
  check(!PsychSustainChain.prepareMiss(alreadyMissedChild, true), 'already missed child early returns');
  eq(untouchedSibling.missed, false, 'child early return precedes sibling updates');

  var headSibling = note(); var current = note(null, true); var tailSibling = note();
  var successfulHead = note(null, false, true, [headSibling, current, tailSibling]);
  current.parent = successfulHead;
  check(PsychSustainChain.prepareMiss(current, true), 'first child miss continues normal miss accounting');
  for (sibling in [headSibling, tailSibling]) {
   eq(sibling.missed, true, 'parent hit marks all other tail entries missed');
   eq(sibling.canBeHit, false, 'parent hit blocks every other tail entry');
   eq(sibling.cachedCanBeHit, false, 'sibling marks update cached canBeHit accessors');
   eq(sibling.ignoreNote, true, 'parent hit ignores every other tail entry');
   eq(sibling.tooLate, true, 'parent hit marks every other tail entry late');
  }
  eq(current.missed, false, 'current sustain remains unmarked by sibling loop');
  eq(current.canBeHit, true, 'current sustain remains hittable by sibling loop');
  eq(current.cachedCanBeHit, true, 'current sustain accessor cache remains unchanged');
  eq(current.ignoreNote, false, 'current sustain remains non-ignored by sibling loop');
  eq(current.tooLate, false, 'current sustain remains non-late by sibling loop');

  var unhitParent = note(null, false, false, [note(), note()]);
  var ordinaryChild = note(unhitParent, true);
  check(PsychSustainChain.prepareMiss(ordinaryChild, true), 'unhit parent does not mark siblings');
  eq(unhitParent.tail[0].missed, false, 'unhit parent leaves siblings alone');
 }
}'''


class PsychSustainChainTest(unittest.TestCase):
    def test_chain_hit_and_miss_transitions(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_helper_matches_pinned_psych_note_miss_quirks(self):
        play = DONOR_PLAY_STATE.read_text(encoding="utf-8")
        miss = play[play.index("function noteMissCommon("):play.index("function opponentNoteHit(")]
        self.assertIn("canHit = canHit && n.parent != null && n.parent.wasGoodHit;", play)
        self.assertIn("if (note != null && guitarHeroSustains && note.parent == null)", miss)
        self.assertIn("note.alpha = 0.35;", miss)
        self.assertIn("childNote.missed = true;", miss)
        self.assertIn("note.missed = true;", miss)
        self.assertIn("if (note.missed)\n\t\t\t\treturn;", miss)
        self.assertIn("if (note != null && guitarHeroSustains && note.parent != null && note.isSustainNote)", miss)
        self.assertIn("if (parentNote.wasGoodHit && parentNote.tail.length > 0)", miss)
        self.assertIn("for (child in parentNote.tail) if (child != note)", miss)


if __name__ == "__main__":
    unittest.main()
