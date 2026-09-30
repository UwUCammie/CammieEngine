"""V-Slice receptor frame geometry and smoke snapshots stay lane aligned."""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class StrumlineReceptorAlignmentTest(unittest.TestCase):
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

    def test_vslice_geometry_is_reapplied_after_each_frame_and_keeps_legacy_confirm_scoped(self):
        source = (ROOT / "source/Strumline.hx").read_text()
        constructor = source[source.index("class StrumNote extends FlxSprite") :]
        update_start = constructor.index("override public function update(elapsed:Float):Void")
        update_end = constructor.index("function alignVSliceFrame()", update_start)
        update = constructor[update_start:update_end]
        align_start = constructor.index("function alignVSliceFrame()")
        align_end = constructor.index("function markReceptorVisual()", align_start)
        align = constructor[align_start:align_end]
        play_start = constructor.index("public function playAnim(")
        play_end = constructor.index("override public function update(", play_start)
        play = constructor[play_start:play_end]

        self.assertIn("daType.vSliceAlias", constructor)
        self.assertIn("authoredStyleOffsetX", align)
        self.assertIn("authoredStyleOffsetY", align)
        self.assertIn("vSliceReceptorOffsetX(frameWidth * Math.abs(scale.x)", align)
        self.assertIn("vSliceReceptorOffsetY(frameHeight * Math.abs(scale.y)", align)
        self.assertIn("vSliceAnchorWidth = vSliceSourceFrameWidth * Math.abs(scale.x)", align)
        self.assertIn("vSliceAnchorHeight = vSliceSourceFrameHeight * Math.abs(scale.y)", align)
        self.assertLess(constructor.index("vSliceSourceFrameWidth = frameWidth"),
                        constructor.index("animation.play('static')"))
        self.assertIn("scale.set(styleScale, styleScale);", constructor)
        self.assertIn("frameHeight * Math.abs(scale.y)", align)
        self.assertIn("super.update(elapsed);", update)
        self.assertIn("alignVSliceFrame();", update)
        self.assertLess(play.index("if (usesVSliceGeometry)"), play.index("offset.x -= 13"))
        self.assertIn("normalSize = usesVSliceGeometry ? scale.x : legacyResetSize;", constructor)
        self.assertIn("animationName + '|' + frameWidth + '|' + frameHeight", constructor)
        self.assertIn("smokeReceptorStates.exists(stateKey)", constructor)
        self.assertIn("markReceptorVisual();", constructor)

    def test_native_smoke_snapshot_reports_active_frame_and_render_center(self):
        fixture_source = r'''
class Main {
  static function fail(message:String):Void throw message;
  static function near(actual:Dynamic, expected:Float, label:String):Void {
    if (actual == null || Math.abs(cast actual - expected) > 0.00001)
      fail(label + ": " + actual + " != " + expected);
  }
  static function main() {
    var scale = 0.7;
    var width = 146.0;
    var height = 148.0;
    var originX = 116.0; // deliberately stale from the prior 232px frame
    var originY = 118.0;
    var laneWidth = 112.0;
    var offsetX = NoteStyleAlignment.vSliceReceptorOffsetX(width * scale, originX,
      scale, laneWidth, 20, 168 * scale);
    var offsetY = NoteStyleAlignment.vSliceReceptorOffsetY(height * scale, originY,
      scale, laneWidth, 24, 152 * scale);
    var receptor:Dynamic = {
      ID: 2,
      type: "vslice-miku",
      x: 316.0,
      y: 50.0,
      frameWidth: 146.0,
      frameHeight: 148.0,
      frame: {name: "left press0001"},
      origin: {x: originX, y: originY},
      offset: {x: offsetX, y: offsetY},
      scale: {x: scale, y: scale},
      parentLine: {x: 92.0},
      animation: {curAnim: {name: "pressed", curFrame: 0}}
    };
    var snapshot = RuntimeSmokeVisuals.receptor(receptor, laneWidth);
    near(Reflect.field(snapshot, "frameWidth"), 146, "frame width");
    near(Reflect.field(snapshot, "frameHeight"), 148, "frame height");
    near(Reflect.field(snapshot, "centerErrorX"),
      -28.6 + 20 + 168 * scale / 2 - (104 / 2 - 2), "donor X anchor");
    near(Reflect.field(snapshot, "centerErrorY"),
      -28.6 + 24 + 152 * scale / 2 - laneWidth / 2, "donor Y anchor");
    if (Reflect.field(snapshot, "animation") != "pressed"
      || Reflect.field(snapshot, "frameName") != "left press0001"
      || Reflect.field(snapshot, "lane") != 2)
      fail("receptor animation/frame/lane snapshot");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture_source)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_receptor_alignment_tracks_source_frame_and_donor_anchor(self):
        method = self.extract_method((ROOT / "source/Strumline.hx").read_text(),
                                     "function alignVSliceFrame():Void")
        source = r'''
class Point { public var x:Float; public var y:Float;
  public function new(x:Float,y:Float) { this.x=x; this.y=y; }
}
class Note { public static var swagWidth:Float=112; }
class ReceptorProbe {
  public var frameWidth:Float=0; public var frameHeight:Float=0;
  public var vSliceSourceFrameWidth:Float=168;
  public var vSliceSourceFrameHeight:Float=152;
  public var vSliceAnchorWidth:Float=0;
  public var vSliceAnchorHeight:Float=0;
  public var scale:Point=new Point(0.7,0.7);
  public var origin:Point=new Point(116,118);
  public var offset:Point=new Point(0,0);
  public var authoredStyleOffsetX:Float=20;
  public var authoredStyleOffsetY:Float=24;
  public function new() {}
  METHOD
  public function align():Void alignVSliceFrame();
}
class Main {
  static function near(actual:Float,expected:Float,label:String):Void
    if(Math.abs(actual-expected)>0.00001) throw label+": "+actual+" != "+expected;
  static function center(width:Float,origin:Float,scale:Float,offset:Float):Float
    return origin-offset-origin*scale+width/2;
  static function main() {
    var receptor=new ReceptorProbe();
    // Miku's static, pressed and confirm up-arrow Sparrow canvas widths.
    // The confirm frame includes a large glow, so its full canvas center
    // moves even though its visible arrow ink remains anchored.
    for (frame in [
      {w:168.0,h:152.0}, {w:168.0,h:151.0}, {w:248.0,h:230.0},
      {w:168.0,h:152.0}
    ]) {
      receptor.frameWidth=frame.w; receptor.frameHeight=frame.h;
      receptor.align();
      var width=frame.w*0.7; var height=frame.h*0.7;
      // Upstream centerOffsets() uses a hitbox retained from setup, and
      // centerOrigin() follows the active frame. Its graphic center is fixed.
      var donorOffsetX=(frame.w-168*.7)/2;
      var donorOffsetY=(frame.h-152*.7)/2;
      near(center(width,frame.w/2,0.7,donorOffsetX),168*.7/2,
        "donor retained hitbox center x");
      near(center(height,frame.h/2,0.7,donorOffsetY),152*.7/2,
        "donor retained hitbox center y");
      near(center(width,receptor.origin.x,0.7,receptor.offset.x)-56,
        -28.6+20+168*.7/2-50,"donor horizontal relation");
      near(center(height,receptor.origin.y,0.7,receptor.offset.y),
        -28.6+24+152*.7/2,"donor vertical anchor");
    }
    receptor.authoredStyleOffsetX=0; receptor.authoredStyleOffsetY=0;
    receptor.frameWidth=232; receptor.frameHeight=236;
    receptor.vSliceSourceFrameWidth=232;
    receptor.vSliceSourceFrameHeight=236;
    receptor.align();
    near(center(232*0.7,receptor.origin.x,0.7,receptor.offset.x)-56,
      -28.6+(232*0.7)/2-50,"other style offsets");
  }
}
'''.replace("METHOD", method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(source)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
