"""Focused Codename strum and note travel-angle compatibility coverage."""
from haxe_test_support import HAXE_COMMAND

import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    match = re.search(r"\t(?:@:keep )?(?:public )?function " + re.escape(name) + r"\(", source)
    if match is None:
        raise AssertionError(f"missing production method {name}")
    start = match.start()
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated production method {name}")


class CodenameNoteAngleTest(unittest.TestCase):
    def test_note_angle_fields_and_live_presentation_route_are_shared(self):
        note = (ROOT / "source/Note.hx").read_text()
        strumline = (ROOT / "source/Strumline.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()

        self.assertIn("@:keep public var noteAngle:Null<Float> = null;", note)
        self.assertIn("@:keep public var noteAngle:Null<Float> = null;", strumline)
        self.assertIn("CodenameNoteAngleCompat.resolve(note == null ? null : note.noteAngle, noteAngle, angle)", strumline)
        update = play_state[play_state.index("var noteScrollSpeed ="):]
        update = update[:update.index("RuntimeSmokeHarness.markLiveCustomNoteVisual")]
        self.assertIn("if (daNote.codenameInputLine != null)", update)
        self.assertIn("applyCodenameNotePresentation(daNote, daNoteStrums, travelDistance);", update)

    def test_source_angle_precedence_and_note_motion(self):
        strumline = (ROOT / "source/Strumline.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        getter = re.sub(r"\bNote\b", "TestNote", method(strumline, "getNotesAngle"))
        lane = re.sub(r"\bNote\b", "TestNote", method(play_state, "codenameNoteLane"))
        presentation = method(play_state, "applyCodenameNotePresentation")
        presentation = presentation.replace("Strumline.StrumNote", "TestReceptor")
        presentation = presentation.replace("Strumline", "TestLine")
        presentation = re.sub(r"\bNote\b", "TestNote", presentation)

        main = r'''class TestNote {
  public static var NOTE_AMOUNT:Int = 4;
  public var noteAngle:Null<Float> = null;
  public var noteData:Int = 0;
  public var codenameInputLine:Dynamic = null;
  public var isSustainNote:Bool = false;
  public var x:Float = 0;
  public var y:Float = 0;
  public var angle:Float = 0;
  public function new() {}
}
class TestReceptor {
  public var x:Float;
  public var y:Float;
  public var angle:Float;
  public var noteAngle:Null<Float> = null;
  public function new(x:Float, y:Float, angle:Float) {
    this.x=x; this.y=y; this.angle=angle;
  }
''' + getter + r'''
}
class TestLine {
  public var members:Array<TestReceptor>;
  public function new(receptor:TestReceptor) members=[receptor];
}
class Main {
  public var downscroll:Bool = false;
  public function new() {}
  static function check(value:Bool, label:String):Void if (!value) throw label;
  static function near(value:Float, expected:Float, label:String):Void
    if (Math.abs(value-expected) > 0.0001) throw label + ": " + value + " != " + expected;
''' + lane + "\n" + presentation + r'''
  public static function main():Void {
    var receptor = new TestReceptor(100, 200, 45);
    var line = new TestLine(receptor);
    var state = new Main();

    // With no direction override, notes follow the receptor's visual angle.
    near(receptor.getNotesAngle(null), 45, "visual-angle fallback");
    var tap = new TestNote(); tap.codenameInputLine={}; tap.x=100; tap.y=250;
    state.applyCodenameNotePresentation(tap, line, 50);
    near(tap.x, 100-35.35533906, "angled note horizontal travel");
    near(tap.y, 200+35.35533906, "angled note vertical travel");
    near(tap.angle, 45, "tap copies receptor visual angle");

    // A strum override of zero keeps the travel vertical while the tap still
    // displays the receptor's independently rotated graphic.
    receptor.noteAngle=0;
    var straightTap = new TestNote(); straightTap.codenameInputLine={};
    straightTap.x=100; straightTap.y=250;
    state.applyCodenameNotePresentation(straightTap, line, 50);
    near(straightTap.x, 100, "zero strum noteAngle keeps X fixed");
    near(straightTap.y, 250, "zero strum noteAngle keeps vertical travel");
    near(straightTap.angle, 45, "tap remains rotated with receptor");

    // A per-note direction overrides the strum direction; sustains render in
    // that direction and keep any existing hold-head vertical padding.
    receptor.noteAngle=60;
    var sustain = new TestNote(); sustain.codenameInputLine={}; sustain.isSustainNote=true;
    sustain.noteAngle=0; sustain.x=100; sustain.y=260;
    state.applyCodenameNotePresentation(sustain, line, 50);
    near(sustain.x, 100, "per-note override keeps vertical path");
    near(sustain.y, 260, "sustain padding survives angle adjustment");
    near(sustain.angle, 0, "sustain follows resolved travel angle");

    // Up/down scroll reverse the travel vector without changing angle priority.
    receptor.noteAngle=0;
    state.downscroll=true;
    var downscrollNote = new TestNote(); downscrollNote.codenameInputLine={};
    downscrollNote.x=100; downscrollNote.y=150;
    state.applyCodenameNotePresentation(downscrollNote, line, 50);
    near(downscrollNote.y, 150, "downscroll keeps the vertical approach");

    var nativeNote = new TestNote(); nativeNote.x=15; nativeNote.y=25; nativeNote.angle=7;
    state.applyCodenameNotePresentation(nativeNote, line, 50);
    near(nativeNote.x, 15, "unowned native note X unchanged");
    near(nativeNote.y, 25, "unowned native note Y unchanged");
    near(nativeNote.angle, 7, "unowned native note angle unchanged");
  }
}'''

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main_file = Path(folder) / "Main.hx"
            main_file.write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", folder, "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
