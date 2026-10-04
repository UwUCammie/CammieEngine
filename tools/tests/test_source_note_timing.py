"""Pure and donor-extracted contracts for Psych/NV note timing windows."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from tools.tests.test_playstate_source_scoring import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
PSYCH_SOURCE = Path(
    "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/FNF-PsychEngine/source"
)
NV_SOURCE = Path(
    "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/NightmareVision/source"
)


class SourceNoteTimingTest(unittest.TestCase):
    def run_haxe(self, fixture: str, main: str) -> None:
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(prefix="source-note-timing-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / f"{main}.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", main, "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pure_windows_and_rating_diff(self):
        fixture = r'''
import SourceNoteTiming;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function near(actual:Float, expected:Float, message:String):Void
  if (Math.abs(actual - expected) > 0.0001)
   fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  near(SourceNoteTiming.safeWindow(10), 1000 / 6,
   'ten safe frames are converted to milliseconds');
  near(SourceNoteTiming.safeWindow(10, 2), 1000 / 3,
   'playback rate scales the source safe window');

  var pos = 100.0;
  var zone = 60.0;
  var early = 0.5;
  var late = 1.5;
  check(!SourceNoteTiming.psychCanBeHit(pos - zone * late, pos, zone, early, late),
   'Psych excludes its late canBeHit boundary');
  check(SourceNoteTiming.psychCanBeHit(pos - zone * late + 0.001, pos, zone, early, late),
   'Psych accepts a note just inside the late canBeHit boundary');
  check(SourceNoteTiming.psychCanBeHit(pos + zone * early - 0.001, pos, zone, early, late),
   'Psych accepts a note just inside the early canBeHit boundary');
  check(!SourceNoteTiming.psychCanBeHit(pos + zone * early, pos, zone, early, late),
   'Psych excludes its early canBeHit boundary');
  check(SourceNoteTiming.isLate(pos - zone - 0.001, pos, zone, false),
   'Psych late cutoff uses the unscaled safe zone');
  check(!SourceNoteTiming.isLate(pos - zone, pos, zone, false),
   'Psych late cutoff excludes exact equality');
  check(!SourceNoteTiming.isLate(pos - zone - 1, pos, zone, true),
   'already-hit notes do not become too late');

  var hitbox = 75.0;
  var earlyNV = 0.5;
  check(SourceNoteTiming.nightmareCanBeHit(pos - hitbox * earlyNV, pos, hitbox, earlyNV),
   'NV includes the early edge of its symmetric window');
  check(SourceNoteTiming.nightmareCanBeHit(pos + hitbox * earlyNV, pos, hitbox, earlyNV),
   'NV includes the late edge of its symmetric window');
  check(!SourceNoteTiming.nightmareCanBeHit(pos - hitbox * earlyNV - 0.001, pos, hitbox, earlyNV),
   'NV excludes points beyond the early edge');
  check(!SourceNoteTiming.nightmareCanBeHit(pos + hitbox * earlyNV + 0.001, pos, hitbox, earlyNV),
   'NV excludes points beyond the late edge');
  check(!SourceNoteTiming.isLate(pos - hitbox, pos, hitbox, false),
   'NV tooLate cutoff is strict at the safe-zone edge');
  check(SourceNoteTiming.isLate(pos - hitbox - 0.001, pos, hitbox, false),
   'NV marks a note late only beyond the safe-zone edge');
  check(!SourceNoteTiming.isLate(pos - hitbox - 10, pos, hitbox, true),
   'NV already-hit notes do not become late');

  near(SourceNoteTiming.ratingDiff(150, 100, 10, 2), 30,
   'rating offset is added before absolute difference and playback scaling');
  near(SourceNoteTiming.ratingDiff(90, 100, 10, 2), 0,
   'rating offset can cancel the signed raw note difference');
  near(SourceNoteTiming.ratingDiff(150, 100, 10), 60,
   'rating difference defaults to playback rate one');
 }
}
'''
        self.run_haxe(fixture, "Main")

    def test_donor_note_methods_match_windows_and_selection_contract(self):
        psych_note_path = PSYCH_SOURCE / "objects/Note.hx"
        psych_play_path = PSYCH_SOURCE / "states/PlayState.hx"
        nv_note_path = NV_SOURCE / "funkin/objects/note/Note.hx"
        nv_play_path = NV_SOURCE / "funkin/states/PlayState.hx"
        nv_field_path = NV_SOURCE / "funkin/objects/note/PlayField.hx"
        donor_paths = (psych_note_path, psych_play_path, nv_note_path, nv_play_path, nv_field_path)
        if not all(path.is_file() for path in donor_paths):
            self.skipTest("local Psych/Nightmare Vision donor sources are not mounted")
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        psych_note_source = psych_note_path.read_text()
        nv_note_source = nv_note_path.read_text()
        psych_update = extract_method(psych_note_source, "override function update(elapsed:Float)")
        nv_methods = "\n".join(
            extract_method(nv_note_source, marker)
            for marker in (
                "public inline function get_noteDiff()",
                "public inline function get_canBeHit()",
                "public inline function isLate()",
            )
        )
        fixture = r'''
import SourceNoteTiming;

class Conductor {
 public static var songPosition:Float = 0;
 public static var safeZoneOffset:Float = 0;
}
class FakeSprite {
 public var alpha:Float = 1;
 public function update(elapsed:Float):Void {}
}
class PsychNote extends FakeSprite {
 public var mustPress:Bool = true;
 public var canBeHit:Bool = false;
 public var tooLate:Bool = false;
 public var wasGoodHit:Bool = false;
 public var strumTime:Float = 0;
 public var earlyHitMult:Float = 1;
 public var lateHitMult:Float = 1;
 public var isSustainNote:Bool = false;
 public var prevNote:PsychNote;
 public var ignoreNote:Bool = false;
 public var inEditor:Bool = false;
 public function new() {}
 __PSYCH_UPDATE__
}
class Note {
 public var strumTime:Float = 0;
 public var hitbox:Float = 0;
 public var earlyHitMult:Float = 1;
 public var wasGoodHit:Bool = false;
 public var noteDiff(get, never):Float;
 public var canBeHit(get, never):Bool;
 public function new() {}
 __NV_METHODS__
}
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);

 static function main():Void {
  Conductor.songPosition = 100;
  Conductor.safeZoneOffset = 60;
  var psych = new PsychNote();
  psych.earlyHitMult = 0.5;
  psych.lateHitMult = 1.5;
  psych.strumTime = 10;
  psych.update(0);
  check(!psych.canBeHit && psych.tooLate,
   'Psych lower can-hit edge is strict while tooLate uses the unscaled window');
  psych = new PsychNote();
  psych.earlyHitMult = 0.5;
  psych.lateHitMult = 1.5;
  psych.strumTime = 10.001;
  psych.update(0);
  check(psych.canBeHit && psych.tooLate,
   'Psych extended late multiplier canBeHit can overlap its unscaled tooLate flag');
  psych = new PsychNote();
  psych.earlyHitMult = 0.5;
  psych.lateHitMult = 1.5;
  psych.strumTime = 40;
  psych.update(0);
  check(psych.canBeHit && !psych.tooLate,
   'Psych exact unscaled late cutoff is not tooLate');
  psych = new PsychNote();
  psych.earlyHitMult = 0.5;
  psych.lateHitMult = 1.5;
  psych.strumTime = 130;
  psych.update(0);
  check(!psych.canBeHit && !psych.tooLate,
   'Psych early can-hit edge is excluded');
  psych = new PsychNote();
  psych.isSustainNote = true;
  psych.earlyHitMult = 0;
  psych.lateHitMult = 1;
  psych.strumTime = 100;
  psych.update(0);
  check(!psych.canBeHit, 'Psych sustain earlyHitMult zero excludes exact note time');
  psych = new PsychNote();
  psych.isSustainNote = true;
  psych.earlyHitMult = 0;
  psych.lateHitMult = 1;
  psych.strumTime = 99.999;
  psych.update(0);
  check(psych.canBeHit, 'Psych sustain canBeHit opens just after its note time');

  var nv = new Note();
  nv.hitbox = 75;
  nv.earlyHitMult = 0.5;
  nv.strumTime = 62.5;
  check(nv.noteDiff == -37.5 && nv.canBeHit,
   'NV signed noteDiff and inclusive early boundary match donor getters');
  nv.strumTime = 137.5;
  check(nv.noteDiff == 37.5 && nv.canBeHit,
   'NV inclusive late boundary uses the symmetric hitbox');
  nv.strumTime = 62.499;
  check(!nv.canBeHit, 'NV rejects a note just outside its captured hitbox');
  nv.strumTime = 39.999;
  check(nv.isLate(), 'NV isLate uses the raw strict safe-zone cutoff');
  nv.strumTime = 40;
  check(!nv.isLate(), 'NV isLate excludes equality at the safe-zone edge');
  nv.wasGoodHit = true;
  nv.strumTime = 39.999;
  check(!nv.isLate(), 'NV already-hit note is not late');

  // Note.hitbox is initialized from safeZoneOffset once at construction.
  // Changing the global window later does not update this captured value.
  nv = new Note();
  nv.hitbox = SourceNoteTiming.safeWindow(4.5, 1);
  Conductor.safeZoneOffset = 1;
  nv.earlyHitMult = 1;
  nv.strumTime = 100 + nv.hitbox;
  check(nv.canBeHit, 'NV canBeHit keeps the note-local hitbox after the global window changes');
 }
}
'''
        fixture = fixture.replace("__PSYCH_UPDATE__", psych_update).replace("__NV_METHODS__", nv_methods)
        with tempfile.TemporaryDirectory(prefix="source-note-donor-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        psych_play = psych_play_path.read_text()
        nv_play = nv_play_path.read_text()
        nv_field = nv_field_path.read_text()
        self.assertIn("var noteDiff:Float = Math.abs(note.strumTime - Conductor.songPosition + ClientPrefs.data.ratingOffset);", psych_play)
        self.assertIn("Conductor.judgeNote(ratingsData, noteDiff / playbackRate)", psych_play)
        self.assertIn("Conductor.safeZoneOffset = (ClientPrefs.data.safeFrames / 60) * 1000 * value;", psych_play)
        self.assertIn("return canHit && !n.isSustainNote && n.noteData == key;", psych_play)
        self.assertIn("if (canHit && n.isSustainNote)", psych_play)
        self.assertIn("if (!released)", psych_play)
        self.assertIn("goodNoteHit(n);", psych_play)
        self.assertIn("earlyHitMult = 0;", psych_note_source)
        self.assertIn("var noteDiff:Float = Math.abs(note.strumTime - Conductor.songPosition + ClientPrefs.ratingOffset);", nv_play)
        self.assertIn("Rating.judgeNote(note, noteDiff / playbackRate)", nv_play)
        self.assertIn("Conductor.safeZoneOffset = (ClientPrefs.safeFrames / 60) * 1000 * value;", nv_play)
        self.assertIn("if (!field.canInput()) continue;", nv_play)
        self.assertIn("note.hitPriority > topNote.hitPriority", nv_play)
        self.assertIn("public var hitbox:Float = Conductor.safeZoneOffset;", nv_note_source)
        self.assertIn("note.alive && note.noteData == dir && !note.wasGoodHit && !note.tooLate && note.canBeHit", nv_field)
        self.assertIn("public function getTapNotes(dir:Int):Array<Note> return getNotes(dir, (note:Note) -> !note.isSustainNote);", nv_field)
        self.assertIn("public function getHoldNotes(dir:Int):Array<Note> return getNotes(dir, (note:Note) -> note.isSustainNote);", nv_field)
        self.assertIn("return (playerControls && inControl && !autoPlayed && (owner == null || !owner.stunned));", nv_field)


if __name__ == "__main__":
    unittest.main()
