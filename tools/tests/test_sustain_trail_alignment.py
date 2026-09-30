"""Keep hold pieces centered on their own head through moving strumlines."""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(signature)


class SustainTrailAlignmentTest(unittest.TestCase):
    def test_hold_uses_its_head_canvas_and_tracks_receptor(self):
        note = (ROOT / "source/Note.hx").read_text()
        play = (ROOT / "source/PlayState.hx").read_text()
        graphic_center = method(note, "public function graphicCenterOffsetX():Float")
        head_anchor = method(note, "public function sustainHeadAnchorX():Float")
        align = method(play, "function alignCodenameNoteToReceptor(note:Note, line:Strumline):Void")
        self.assertIn("sustainHead = prevNote.isSustainNote ? prevNote.sustainHead : prevNote;", note)
        self.assertIn("daNote.x += daNote.sustainHeadAnchorX() - daNote.graphicCenterOffsetX();", play)
        self.assertIn("note.x += note.sustainHeadAnchorX() - note.graphicCenterOffsetX();", align)
        code = r'''
class Point { public var x:Float; public function new(x:Float) this.x=x; }
class Note {
  public static var NOTE_AMOUNT:Int=4;
  public var x:Float=0;
  public var width:Float;
  public var origin:Point;
  public var offset:Point;
  public var scale:Point;
  public var alive:Bool=true;
  public var sustainHead:Note=null;
  public var sustainHeadCenterX:Null<Float>=null;
  public var swagWidth:Float=112;
  public var isSustainNote:Bool=false;
  public var codenameInputLine:Dynamic={};
  public var codenameReceptorXOffset:Null<Float>=0;
  public var codenameGeneratedX:Null<Float>=null;
  public var noteData:Int=0;
  public function new(width:Float, origin:Float, offset:Float, scale:Float) {
    this.width=width; this.origin=new Point(origin); this.offset=new Point(offset);
    this.scale=new Point(scale);
  }
  GRAPHIC_CENTER
  HEAD_ANCHOR
}
class Receptor { public var x:Float; public function new(x:Float) this.x=x; }
class Strumline { public var members:Array<Receptor>;
  public function new(x:Float) members=[new Receptor(x)]; }
class Main {
  static function near(a:Float,b:Float):Void if (Math.abs(a-b)>0.0001) throw a+" != "+b;
  CODENAME_ALIGN
  static function codenameNoteLane(note:Note):Int return note.noteData;
  static function main():Void {
    var head=new Note(112,56,0,1);
    var tail=new Note(28,14,2,1);
    tail.isSustainNote=true; tail.sustainHead=head;
    tail.sustainHeadCenterX=head.graphicCenterOffsetX();
    var line=new Strumline(300);
    alignCodenameNoteToReceptor(tail,line);
    near(tail.x+tail.graphicCenterOffsetX(),300+head.graphicCenterOffsetX());
    line.members[0].x=475;
    alignCodenameNoteToReceptor(tail,line);
    near(tail.x+tail.graphicCenterOffsetX(),475+head.graphicCenterOffsetX());
    tail.scale.x=1.6; tail.width=44.8;
    alignCodenameNoteToReceptor(tail,line);
    near(tail.x+tail.graphicCenterOffsetX(),475+head.graphicCenterOffsetX());
    head.offset.x=9;
    alignCodenameNoteToReceptor(tail,line);
    near(tail.x+tail.graphicCenterOffsetX(),475+head.graphicCenterOffsetX());
    head.alive=false;
    head.offset.x=200;
    alignCodenameNoteToReceptor(tail,line);
    near(tail.x+tail.graphicCenterOffsetX(),475+47);
    var lateTail=new Note(28,14,2,1);
    lateTail.isSustainNote=true; lateTail.sustainHead=head;
    lateTail.sustainHeadCenterX=56;
    alignCodenameNoteToReceptor(lateTail,line);
    near(lateTail.x+lateTail.graphicCenterOffsetX(),475+47);
    var chartHead=new Note(112,56,0,1);
    chartHead.codenameGeneratedX=92;
    chartHead.codenameReceptorXOffset=0;
    var chartTail=new Note(28,14,2,1);
    chartTail.isSustainNote=true;chartTail.sustainHead=chartHead;
    chartTail.codenameGeneratedX=92;
    chartTail.codenameReceptorXOffset=0;
    alignCodenameNoteToReceptor(chartHead,line);
    alignCodenameNoteToReceptor(chartTail,line);
    near(chartHead.x+chartHead.graphicCenterOffsetX(),
      line.members[0].x+56);
    near(chartTail.x+chartTail.graphicCenterOffsetX(),
      chartHead.x+chartHead.graphicCenterOffsetX());
    line.members[0].x=525;
    alignCodenameNoteToReceptor(chartTail,line);
    near(chartTail.x+chartTail.graphicCenterOffsetX(),
      line.members[0].x+56);
    chartTail.codenameReceptorXOffset=12;
    alignCodenameNoteToReceptor(chartTail,line);
    near(chartTail.x+chartTail.graphicCenterOffsetX(),
      line.members[0].x+56+12);
  }
}
'''.replace("GRAPHIC_CENTER", graphic_center).replace("HEAD_ANCHOR", head_anchor).replace(
            "CODENAME_ALIGN", align.replace("function alignCodenameNoteToReceptor", "static function alignCodenameNoteToReceptor"))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(code)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
