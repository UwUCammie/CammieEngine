"""Destroyed notes let go of the song's earlier notes without changing chords."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_hit_order import extract_method

ROOT = Path(__file__).resolve().parents[2]


def note_release_members() -> str:
    source = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
    start = source.index("@:allow(PlayState) var nightmareVisionLegacyRow")
    fields = source[start:source.index(";", source.index("static var retiredLegacyRows", start)) + 1]
    flush = extract_method(source, "public static function flushRetiredLegacyRows()")
    release = extract_method(source, "function releaseLegacyRowMembership()")
    destroy = extract_method(source, "override public function destroy():Void {")
    head = destroy[:destroy.index("if (nightmareVisionTypeRuntime != null)")]
    return "\n".join([
        fields.replace("@:allow(PlayState) ", "public "),
        flush,
        release,
        head.replace("override public", "public") + " exists = false; }",
    ])


FIXTURE = r"""
class Note {
 public var id:Int;
 public var noteData:Int;
 public var row:Int;
 public var mustPress:Bool;
 public var forceGfSing = false;
 public var noAnimation = false;
 public var isSustainNote = false;
 public var noteType = '';
 public var exists = true;
 public var prevNote:Note;
 public var nextNote:Note;
 public function new(id:Int, noteData:Int, row:Int, mustPress:Bool, ?prevNote:Note, sustain:Bool = false) {
  this.id = id; this.noteData = noteData; this.row = row; this.mustPress = mustPress;
  this.prevNote = prevNote == null ? this : prevNote; isSustainNote = sustain;
 }
 __MEMBERS__
}
class Character {
 public var animOffsets:Map<String, Array<Float>> = [];
 public var animTimer = 0.; public var voicelining = false; public var holdTimer = 0.;
 public var specialAnim = false; public var heyTimer = 0.; public var mostRecentRow = -1;
 public var log:Array<String> = [];
 public function new() {}
 public function playAnim(n:String, f:Bool) log.push('anim:' + n);
 public function playGhostAnim(i:Int, n:String, f:Bool) log.push('ghost:' + i + ':' + n);
}
class Main {
 static function check(b:Bool, s:String) if (!b) throw s;
 static var animations = ['singLEFT', 'singDOWN', 'singUP', 'singRIGHT'];
 static function sing(note:Note, actor:Character, rows:Array<Array<Array<Note>>>):String {
  actor.log = [];
  actor.mostRecentRow = -1;
  NightmareVisionLegacySinging.sing(note, actor, null, true, animations, rows, true, null, function(_, _) return 0);
  return actor.log.join(',');
 }
 static function group(rows:Array<Array<Array<Note>>>, note:Note):Void {
  var side = rows[note.mustPress ? 0 : 1];
  if (side[note.row] == null) side[note.row] = [];
  side[note.row].push(note);
  note.nightmareVisionLegacyRow = side[note.row];
 }
 static function main() {
  // Chart order: a single, a three note jump, a held note and a later jump.
  var rows:Array<Array<Array<Note>>> = [[], []];
  var single = new Note(0, 0, 4, true);
  var jumpA = new Note(1, 0, 8, true, single), jumpB = new Note(2, 2, 8, true, jumpA), jumpC = new Note(3, 3, 8, true, jumpB);
  var hold = new Note(4, 1, 12, true, jumpC);
  var holdPiece = new Note(5, 1, 12, true, hold, true), holdEnd = new Note(6, 1, 12, true, holdPiece, true);
  var lateA = new Note(7, 0, 16, true, holdEnd), lateB = new Note(8, 3, 16, true, lateA);
  for (note in [single, jumpA, jumpB, jumpC, hold, lateA, lateB]) group(rows, note);

  // Reference chord behaviour, before anything is destroyed.
  var actor = new Character();
  var expectedB = sing(jumpB, actor, rows);
  var expectedC = sing(jumpC, actor, rows);
  var expectedLate = sing(lateB, actor, rows);
  check(expectedB.indexOf('ghost:1') >= 0 && expectedC.indexOf('ghost:2') >= 0, 'reference chord ghosts: ' + expectedB + ' / ' + expectedC);

  // Earlier notes, then part of the jump, are hit and destroyed.
  single.destroy();
  jumpA.destroy();
  Note.flushRetiredLegacyRows();
  check(sing(jumpB, actor, rows) == expectedB, 'jump lost its chord after its first note was destroyed');
  jumpB.destroy();
  Note.flushRetiredLegacyRows();
  check(sing(jumpC, actor, rows) == expectedC, 'jump lost its chord after two of its notes were destroyed');
  check(rows[0][8].length == 3, 'a row with a live head was emptied');

  // The last head of the row is destroyed in the same frame it sings.
  jumpC.destroy();
  check(rows[0][8].length == 3, 'a row was emptied in the frame its last head was destroyed');
  Note.flushRetiredLegacyRows();
  check(rows[0][4].length == 0 && rows[0][8].length == 0, 'retired rows still hold their notes');
  check(sing(lateB, actor, rows) == expectedLate, 'a later chord changed');

  // Destroyed heads stop chaining back through the chart.
  check(jumpC.prevNote == jumpC && jumpA.prevNote == jumpA && single.prevNote == single, 'destroyed heads still link to earlier notes');
  // The held note's head is destroyed while its sustain is still on screen.
  hold.destroy();
  check(holdPiece.prevNote == hold && holdEnd.prevNote == holdPiece, 'live sustain pieces lost their predecessor');
  check(hold.prevNote == hold, 'held head still links to the previous chord');
  // A destroyed sustain piece keeps its predecessor for pieces walking back to the head.
  holdPiece.destroy();
  check(holdPiece.prevNote == hold && holdEnd.prevNote == holdPiece, 'sustain chain was cut');
  // Live heads and destroying twice are untouched.
  check(lateA.prevNote == holdEnd && lateB.prevNote == lateA, 'live heads lost their links');
  hold.destroy();
  Note.flushRetiredLegacyRows();
  check(rows[0][16].length == 2, 'live chord row changed');
  Sys.println('OK');
 }
}
"""


class NoteRowsReleaseTest(unittest.TestCase):
    def test_destroyed_notes_release_rows_and_links_but_keep_chords(self):
        fixture = FIXTURE.replace("__MEMBERS__", note_release_members())
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = FixturePath(folder)
            # One type per module so the real singing helper resolves them.
            for name in ("Note", "Character", "Main"):
                start = fixture.index("class " + name + " {")
                end = fixture.find("\nclass ", start + 1)
                text = fixture[start:] if end < 0 else fixture[start:end]
                (work / (name + ".hx")).write_text(text, encoding="utf-8", newline="\n")
            (work / "NightmareVisionLegacySinging.hx").write_text(
                (ROOT / "source/NightmareVisionLegacySinging.hx").read_text(encoding="utf-8"),
                encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_play_state_groups_flushes_and_tears_down_rows(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        grouping = play[play.index("rows[swagNote.row].push(swagNote);"):][:200]
        self.assertIn("swagNote.nightmareVisionLegacyRow = rows[swagNote.row];", grouping)
        update = play[play.index("override public function update(elapsed:Float) {"):][:200]
        self.assertIn("Note.flushRetiredLegacyRows();", update)
        destroy = play[play.index("override public function destroy() {"):]
        self.assertIn("Note.flushRetiredLegacyRows();", destroy[:destroy.index("CodenameMusicBeatTransition.releaseChartOwner")])


if __name__ == "__main__":
    unittest.main()
