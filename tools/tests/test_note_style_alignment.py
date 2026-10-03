"""Offscreen geometry checks for scoped imported note-style atlases."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NoteStyleAlignmentTest(unittest.TestCase):
    @staticmethod
    def extract_method(source: str, signature: str) -> str:
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
        raise AssertionError(f"Unclosed method: {signature}")

    def test_large_and_trimmed_sparrow_frames_center_after_every_hitbox_update(self):
        source = r'''
class Main {
  static function fail(message:String):Void throw message;
  static function near(actual:Float, expected:Float, label:String):Void {
    if (Math.abs(actual - expected) > 0.00001) fail(label + ": " + actual + " != " + expected);
  }
  // FlxSprite.getGraphicBounds().x with the exact native Flixel formula.
  static function graphicCenter(x:Float, width:Float, origin:Float,
    scale:Float, offset:Float):Float {
    return x + origin - offset - origin * scale + width / 2;
  }
  static function graphicCenterY(y:Float, height:Float, origin:Float,
    scale:Float, offset:Float):Float {
    return y + origin - offset - origin * scale + height / 2;
  }
  static function main() {
    var laneX = 300.0;
    var laneWidth = 112.0;
    var frameWidth = 635.0; // Sparrow frameWidth, not the trimmed subtexture width.
    var trimmedWidth = 343.0;
    var frameX = -146.0;
    var scale = 0.7;
    var width = frameWidth * scale;
    var origin = frameWidth / 2; // super.updateHitbox centers the unscaled frame.
    var defaultOffset = (frameWidth - width) / 2;
    if (Math.abs(graphicCenter(laneX, width, origin, scale, defaultOffset)
      - (laneX + laneWidth / 2)) < 100)
      fail("fixture no longer reproduces the oversized-frame drift");
    for (update in 0...3) {
      // super.updateHitbox resets offset every time, including each
      // snap-to-strumline update. The correction must therefore be stable.
      var offset = NoteStyleAlignment.centeredOffsetX(width, origin, scale, laneWidth, 0);
      near(graphicCenter(laneX, width, origin, scale, offset),
        laneX + laneWidth / 2, "full frame center");
      near(offset, NoteStyleAlignment.centeredOffsetX(width, origin, scale, laneWidth, 0),
        "repeated update");
    }
    var authored = NoteStyleAlignment.centeredOffsetX(width, origin, scale, laneWidth, 12);
    near(graphicCenter(laneX, width, origin, scale, authored),
      laneX + laneWidth / 2 - 12, "authored positive offset keeps Flixel sign");
    // An asymmetric trim changes visible ink inside the frame, but must not
    // change the authored frame canvas or our lane-centering calculation.
    if (trimmedWidth == frameWidth || frameX == 0) fail("trim fixture invalid");
    near(NoteStyleAlignment.centeredOffsetX(width, origin, scale, laneWidth, 0),
      NoteStyleAlignment.centeredOffsetX(frameWidth * scale, origin, scale, laneWidth, 0),
      "trim-independent frame canvas");
    var smallWidth = 157.0 * 0.7;
    var smallOrigin = 157.0 / 2;
    var small = NoteStyleAlignment.centeredOffsetX(smallWidth, smallOrigin, 0.7, laneWidth, 0);
    near(graphicCenter(laneX, smallWidth, smallOrigin, 0.7, small),
      laneX + laneWidth / 2, "ordinary sized custom style");

    // V-Slice receptor prefixes can use different source canvases. Pomni's
    // press frame is 146x148 while its static/confirm frame is 232x236; the
    // origin can still be the previous frame's center when the animation
    // changes, so the current source canvas must be used explicitly.
    var receptorX = 92.0;
    var receptorY = 50.0;
    var authoredX = 20.0;
    var authoredY = 24.0;
    var staleOriginX = 116.0;
    var staleOriginY = 118.0;
    for (frame in [{w:232.0, h:236.0}, {w:146.0, h:148.0}, {w:232.0, h:236.0}]) {
      var receptorWidth = frame.w * scale;
      var receptorHeight = frame.h * scale;
      var receptorOffsetX = NoteStyleAlignment.vSliceReceptorOffsetX(receptorWidth,
        staleOriginX, scale, laneWidth, authoredX, 232.0 * scale);
      var receptorOffsetY = NoteStyleAlignment.vSliceReceptorOffsetY(receptorHeight,
        staleOriginY, scale, laneWidth, authoredY, 236.0 * scale);
      near(graphicCenter(receptorX, receptorWidth, staleOriginX, scale, receptorOffsetX),
        receptorX + laneWidth / 2 -28.6 + authoredX + 232.0*scale/2 - 50,
        "receptor source-frame center x");
      near(graphicCenterY(receptorY, receptorHeight, staleOriginY, scale, receptorOffsetY),
        receptorY -28.6 + authoredY + 236.0*scale/2,
        "receptor source-frame center y");
    }
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_note_hitbox_path_keeps_kind_alignment_and_native_style_isolation(self):
        note_source = (ROOT / "source/Note.hx").read_text()
        method = self.extract_method(note_source,
                                     "override public function updateHitbox():Void")
        center_method = self.extract_method(note_source,
                                            "public function graphicCenterOffsetX():Float")
        style_method = self.extract_method(note_source,
                                           "function setVSliceNoteOffsets(style:TUI):Void")
        receptor_method = self.extract_method((ROOT / "source/Strumline.hx").read_text(),
                                              "function alignVSliceFrame():Void")
        source = r'''
typedef TUI = { ?vSliceAlias:String, ?noteOffsetX:Float, ?noteOffsetY:Float }
class Point { public var x:Float; public var y:Float;
  public function new(x:Float, y:Float) { this.x=x; this.y=y; }
  public function set(x:Float, y:Float):Void { this.x=x; this.y=y; }
}
class BaseSprite {
  public var width:Float=0; public var height:Float=0;
  public var sourceWidth:Float=0; public var sourceHeight:Float=0;
  public var origin:Point=new Point(0,0);
  public var offset:Point=new Point(0,0);
  public var scale:Point=new Point(0.7,0.7);
  public function new() {}
  public function updateHitbox():Void {
    width=sourceWidth*scale.x; height=sourceHeight*scale.y;
    origin.set(sourceWidth/2,sourceHeight/2);
    offset.set((sourceWidth-width)/2,(sourceHeight-height)/2);
  }
}
class NoteProbe extends BaseSprite {
  public static var swagWidth:Float=112;
  public var psychSkinOwner:String=null;
  public var isSustainNote:Bool=false;
  public var customNotePath:String=null;
  public var specialNoteInfo:Dynamic=null;
  public var offsetState:NoteOffsetState;
  public var offsetWritesReady:Bool=false;
  public var vSliceNoteOffsetX:Null<Float>=null;
  public var vSliceNoteOffsetY:Float=0;
  public var sustainHeadCenterX:Null<Float>=null;
  public function new() { super(); }
  METHOD
  CENTER_METHOD
  STYLE_METHOD
  public function setStyle(style:TUI):Void setVSliceNoteOffsets(style);
}
class Note { public static var swagWidth:Float=112; }
class ReceptorProbe {
  public var frameWidth:Float=0; public var frameHeight:Float=0;
  public var vSliceSourceFrameWidth:Float=168;
  public var vSliceSourceFrameHeight:Float=152;
  public var vSliceAnchorWidth:Float=0;
  public var vSliceAnchorHeight:Float=0;
  public var origin:Point=new Point(84,76);
  public var offset:Point=new Point(0,0);
  public var scale:Point=new Point(0.7,0.7);
  public var authoredStyleOffsetX:Float=20;
  public var authoredStyleOffsetY:Float=24;
  public function new() {}
  RECEPTOR_METHOD
  public function align():Void alignVSliceFrame();
}
class Main {
  static function near(actual:Float, expected:Float, label:String):Void
    if (Math.abs(actual-expected)>0.00001) throw label+": "+actual+" != "+expected;
  static function center(position:Float, width:Float, origin:Float,
    scale:Float, offset:Float):Float
    return position + origin - offset - origin * scale + width / 2;
  static function main() {
    var note=new NoteProbe(); note.sourceWidth=167; note.sourceHeight=151;
    note.setStyle({vSliceAlias:"HatsuneMiku",noteOffsetX:0,noteOffsetY:0});
    note.updateHitbox(); note.offsetWritesReady=true;
    var receptor=new ReceptorProbe();
    // Actual snapToStrumline gives the note and receptor the same x=300.
    // The note and receptor methods must reproduce donor's relative anchor.
    for (i in 0...3) {
      note.updateHitbox();
      near(center(300,note.width,note.origin.x,note.scale.x,note.offset.x),
        300+112/2,"Miku note centered in host lane");
      for (frame in [168.0,248.0]) {
        receptor.frameWidth=frame; receptor.frameHeight=152;
        receptor.align();
        var receptorCenter=center(300,frame*.7,receptor.origin.x,.7,receptor.offset.x);
        var noteCenter=center(300,note.width,note.origin.x,.7,note.offset.x);
        near(receptorCenter-noteCenter,
          -28.6+20+168*.7/2-(104/2-2),"actual paired donor anchor");
      }
    }
    // A second V-Slice style may have its own note offset, which must stay
    // independent of the receptor's authored offset.
    note.setStyle({vSliceAlias:"other",noteOffsetX:4,noteOffsetY:3});
    note.sourceWidth=182; note.sourceHeight=155;
    note.updateHitbox();
    receptor.authoredStyleOffsetX=10; receptor.frameWidth=200;
    receptor.vSliceSourceFrameWidth=200;
    receptor.align();
    near(center(300,note.width,note.origin.x,.7,note.offset.x),
      300+112/2-4,"second style own note X offset");
    near(note.offset.y-(note.sourceHeight-note.height)/2,3,
      "second style own note Y offset");
    near(center(300,receptor.frameWidth*.7,receptor.origin.x,.7,receptor.offset.x)
      -center(300,note.width,note.origin.x,.7,note.offset.x),
      -28.6+10+200*.7/2-(104/2-2)+4,
      "second style paired donor anchor");
    // A note-kind atlas with a much larger trimmed Sparrow canvas follows its
    // own authored style and stays stable across repeated hitbox rebuilds.
    note.customNotePath="custom-danger";
    note.specialNoteInfo={sourceNoteStyle:"danger",customNoteOffsetX:12.0,
      customNoteOffsetY:5.0};
    note.sourceWidth=635; note.sourceHeight=343;
    for (i in 0...3) {
      note.updateHitbox();
      near(center(300,note.width,note.origin.x,note.scale.x,note.offset.x),
        300+112/2-12,"custom kind center");
    }
    // A style switch to the native atlas must release the custom offset.
    note.customNotePath=null; note.specialNoteInfo=null;
    note.setStyle({});
    note.sourceWidth=160; note.sourceHeight=160;
    note.updateHitbox();
    near(center(300,note.width,note.origin.x,note.scale.x,note.offset.x),
      300+note.width/2,"native style center");
    note.setStyle({vSliceAlias:"HatsuneMiku",noteOffsetX:0});
    note.psychSkinOwner="psych-owner";
    note.sourceWidth=170;
    note.updateHitbox();
    near(center(300,note.width,note.origin.x,note.scale.x,note.offset.x),
      300+note.width/2,"Psych texture keeps own hitbox");
  }
}
'''.replace("RECEPTOR_METHOD", receptor_method).replace("STYLE_METHOD", style_method).replace("CENTER_METHOD", center_method).replace("METHOD", method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
