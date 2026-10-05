"""Codename note placement must survive the legacy primary-bank snap pass."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    match = re.search(r"\t(?:@:keep )?(?:public )?function " + re.escape(name) + r"\(", source)
    if match is None:
        raise AssertionError(f"missing production method {name}")
    start = match.start()
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated production method {name}")


def block(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated production block {signature}")


class CodenameSnapGeometryTest(unittest.TestCase):
    def test_angled_extra_line_head_and_sustain_keep_source_geometry(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        note = (ROOT / "source/Note.hx").read_text()
        strumline = (ROOT / "source/Strumline.hx").read_text()

        snap = block(play, "\t\tif (snapToStrumline) {")
        engine_owned_skip = snap.index(
            "if (daNote.codenameInputLine != null || nightmareVisionScripts != null || isPsychReceptorNote(daNote))")
        legacy_x_write = snap.index("daNote.x = strums.members[noteData].x;")
        self.assertLess(engine_owned_skip, legacy_x_write)
        self.assertIn("daNote.codenameInputLine != null", snap[engine_owned_skip:legacy_x_write])
        self.assertIn("nightmareVisionScripts != null", snap[engine_owned_skip:legacy_x_write])
        self.assertIn("\n\t\t\t\t\treturn;", snap[engine_owned_skip:legacy_x_write])
        snap_reassignment = snap[engine_owned_skip:snap.index(";", legacy_x_write) + 1]

        psych_guard = re.sub(r"\bNote\b", "TestNote", method(play, "isPsychReceptorNote"))
        lane = method(play, "codenameNoteLane").replace(
            "function codenameNoteLane", "static function codenameNoteLane")
        lane = re.sub(r"\bNote\b", "TestNote", lane)
        align = method(play, "alignCodenameNoteToReceptor")
        align = align.replace("Strumline.StrumNote", "TestReceptor")
        align = align.replace("Strumline", "TestLine")
        align = re.sub(r"\bNote\b", "TestNote", align)
        align = align.replace("function alignCodenameNoteToReceptor", "static function alignCodenameNoteToReceptor")
        presentation = method(play, "applyCodenameNotePresentation")
        presentation = presentation.replace("Strumline.StrumNote", "TestReceptor")
        presentation = presentation.replace("Strumline", "TestLine")
        presentation = re.sub(r"\bNote\b", "TestNote", presentation)
        angle_getter = method(strumline, "getNotesAngle")
        angle_getter = re.sub(r"\bNote\b", "TestNote", angle_getter)
        anchor = method(note, "sustainHeadAnchorX")
        anchor = re.sub(r"\bNote\b", "TestNote", anchor)
        center = method(note, "graphicCenterOffsetX")

        fixture = r'''class Point { public var x:Float; public function new(x:Float) this.x=x; }
class TestNote {
  public static var NOTE_AMOUNT:Int=4;
  public static var swagWidth:Float=112;
  public var sourceTimingMode:Int=0;
  public var noteData:Int=0;
  public var codenameInputLine:Dynamic={};
  public var codenameReceptorXOffset:Null<Float>=7;
  public var noteAngle:Null<Float>=null;
  public var isSustainNote:Bool=false;
  public var mustPress:Bool=true;
  public var sustainHead:TestNote=null;
  public var sustainHeadCenterX:Null<Float>=null;
  public var alive:Bool=true;
  public var exists:Bool=true;
  public var origin:Point;
  public var offset:Point;
  public var scale:Point;
  public var width:Float;
  public var x:Float=0;
  public var y:Float=0;
  public var angle:Float=0;
  public function new(width:Float, origin:Float, offset:Float) {
    this.width=width; this.origin=new Point(origin); this.offset=new Point(offset);
    scale=new Point(1);
  }
''' + center + "\n" + anchor + r'''
}
class TestReceptor {
  public var x:Float; public var y:Float; public var angle:Float;
  public var noteAngle:Null<Float>=null;
  public function new(x:Float,y:Float,angle:Float) {this.x=x;this.y=y;this.angle=angle;}
''' + angle_getter + r'''
}
class TestLine { public var members:Array<TestReceptor>; public function new(m:Array<TestReceptor>) members=m; }
class Main {
  public var downscroll:Bool=false;
  public var nightmareVisionScripts:Dynamic=null;
  public var playerStrums:TestLine;
  public var enemyStrums:TestLine;
  public function new() {}
''' + psych_guard + "\n" + lane + "\n" + align + "\n" + presentation + r'''
  function legacySnap(daNote:TestNote):Void {
SNAP_REASSIGNMENT
  }
  static function check(ok:Bool,label:String):Void if(!ok)throw label;
  static function near(a:Float,b:Float,label:String):Void
    if(Math.abs(a-b)>.0001)throw label+': '+a+' != '+b;
  static function main():Void {
    var primary=new TestLine([for (lane in 0...4) new TestReceptor(80+lane*112,200,0)]);
    var extra=new TestLine([for (lane in 0...4) new TestReceptor(300+lane*112,200,30)]);
    var head=new TestNote(112,56,0); head.noteData=5;
    var tail=new TestNote(28,14,2); tail.noteData=5; tail.isSustainNote=true;
    tail.sustainHead=head;

    // Source lane five is lane one on this four-key line. The head and the
    // narrower tail keep their authored x shift while following its 30° path.
    Main.alignCodenameNoteToReceptor(head,extra);
    Main.alignCodenameNoteToReceptor(tail,extra);
    var state=new Main();
    state.applyCodenameNotePresentation(head,extra,80);
    state.applyCodenameNotePresentation(tail,extra,40);
    near(head.x+head.graphicCenterOffsetX(),475-40,'angled head on extra source line');
    near(tail.x+tail.graphicCenterOffsetX(),475-20,'centered hold tail on extra source line');
    check(primary.members[1].x!=extra.members[1].x,'fixture requires distinct primary/extra lines');
    state.playerStrums=primary; state.enemyStrums=primary;
    var headX=head.x, tailX=tail.x;
    state.legacySnap(head);
    state.legacySnap(tail);
    near(head.x,headX,'legacy snap preserves angled head geometry');
    near(tail.x,tailX,'legacy snap preserves centered hold geometry');
    check(Main.codenameNoteLane(tail)==1,'normalized lane');
  }
}'''.replace("SNAP_REASSIGNMENT", snap_reassignment)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "Main.hx"
            path.write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", folder, "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
