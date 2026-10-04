"""Keep scaled menu rows compact and preserve their measured layout width."""

from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path

import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class AlphabetMenuTextScaleTest(unittest.TestCase):
    def test_glyph_spacing_is_independent_of_row_screen_position(self):
        alphabet = (ROOT / "source/Alphabet.hx").read_text(encoding="utf-8")
        layout = extract_method(alphabet, "public function addText")
        fixture = r'''
class AlphaCharacter {
 public static var alphabet="abcdefghijklmnopqrstuvwxyz";
 public static var numbers="0123456789";
 public static var symbols="!?";
 public var x:Float; public var y:Float; public var width:Float=20;
 public function new(x:Float,y:Float){this.x=x;this.y=y;}
 public function createBold(text:String):Void {}
 public function createLetter(text:String):Void {}
}
class Alphabet {
 public var x:Float; public var y:Float=100; public var text="GAME PLAY";
 public var members:Array<AlphaCharacter>=[];
 var _finalText=""; var splitWords:Array<String>=[]; var lastSprite:AlphaCharacter;
 var lastWasSpace=false; var lastWasEscape=false; var xPosResetted=false;
 var drawHypens=false; var isBold=true;
 public function new(x:Float){this.x=x;}
 function clearText():Void members=[];
 function doSplitWords():Void splitWords=_finalText.split("");
 function add(glyph:AlphaCharacter):Void {
  glyph.x+=x; glyph.y+=y; members.push(glyph);
 }
''' + layout + r'''
}
class AlphabetLayoutMain {
 static function main():Void {
  for(origin in [-240,0,90]) {
   var row=new Alphabet(origin); row.addText();
   if(row.members.length!=8) throw "word glyphs changed";
   for(i in 0...8) {
    var expected=i*20+(i>=4?40:0);
    if(row.members[i].x-origin!=expected) throw "screen position stretched glyph spacing";
   }
  }
 }
}'''
        with tempfile.TemporaryDirectory(prefix="alphabet-layout-", dir=ROOT / "tmp") as directory:
            scratch = Path(directory)
            (scratch / "AlphabetLayoutMain.hx").write_text(fixture, newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(scratch), "--run", "AlphabetLayoutMain"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scales_all_children_spacing_width_and_repeated_calls(self):
        alphabet = (ROOT / "source/Alphabet.hx").read_text(encoding="utf-8")
        freeplay = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        self.assertIn("public function setMenuTextScale(scale:Float):Void", alphabet)
        self.assertIn("row.setMenuTextScale(SONG_ROW_SCALE);", freeplay)
        self.assertNotIn("row.scale.set(SONG_ROW_SCALE, SONG_ROW_SCALE);", freeplay)
        helper = extract_method(alphabet, "public function setMenuTextScale")
        fixture = f"""
class FakePoint {{
    public var x:Float;
    public var y:Float;
    public function new(x:Float, y:Float) {{ this.x = x; this.y = y; }}
    public function set(x:Float, y:Float):FakePoint {{ this.x = x; this.y = y; return this; }}
}}
class FakeSprite {{
    public var x:Float;
    public var y:Float;
    public var width:Float;
    public var height:Float;
    public var scale:FakePoint;
    var frameWidth:Float;
    var frameHeight:Float;
    public function new(x:Float, y:Float, width:Float, height:Float, scaleX:Float, scaleY:Float) {{
        this.x = x; this.y = y; this.width = width; this.height = height;
        scale = new FakePoint(scaleX, scaleY);
        frameWidth = width / scaleX;
        frameHeight = height / scaleY;
    }}
    public function updateHitbox():Void {{
        width = Math.abs(scale.x) * frameWidth;
        height = Math.abs(scale.y) * frameHeight;
    }}
}}
class Alphabet {{
    public var x:Float;
    public var y:Float;
    public var members:Array<FakeSprite>;
    var menuTextScale:Float = 1;
    public function new(x:Float, y:Float, members:Array<FakeSprite>) {{
        this.x = x; this.y = y; this.members = members;
    }}
    public function moveTo(newX:Float, newY:Float):Void {{
        var dx = newX - x; var dy = newY - y;
        for (sprite in members) {{ sprite.x += dx; sprite.y += dy; }}
        x = newX; y = newY;
    }}
    public function width():Float {{
        var minX = Math.POSITIVE_INFINITY; var maxX = Math.NEGATIVE_INFINITY;
        for (sprite in members) {{
            minX = Math.min(minX, sprite.x);
            maxX = Math.max(maxX, sprite.x + sprite.width);
        }}
        return maxX - minX;
    }}
{helper}
}}
class AlphabetMenuTextScaleMain {{
    static function check(ok:Bool, message:String):Void if (!ok) throw message;
    static function close(actual:Float, expected:Float):Bool return Math.abs(actual - expected) < 1e-8;
    static function main():Void {{
        var glyphA = new FakeSprite(100, 200, 20, 30, 1, 1);
        var glyphB = new FakeSprite(120, 204, 15, 20, 1.25, 1);
        var decoration = new FakeSprite(145, 202, 10, 10, 0.4, 0.6);
        var row = new Alphabet(100, 200, [glyphA, glyphB, decoration]);
        check(close(row.width(), 55), 'fixture row width is wrong');

        row.setMenuTextScale(0.85);
        check(close(glyphB.x, 117) && close(glyphB.y, 203.4)
            && close(glyphB.scale.x, 1.0625), 'glyph spacing or custom glyph scale was lost');
        check(close(decoration.x, 138.25) && close(decoration.scale.x, 0.34)
            && close(decoration.scale.y, 0.51), 'non-glyph child was not scaled by the same ratio');
        check(close(row.width(), 55 * 0.85), 'row width did not follow the scaled glyph layout');
        row.setMenuTextScale(0.85);
        check(close(row.width(), 55 * 0.85), 'repeating a scale changed the row a second time');

        row.moveTo(130, 220);
        row.setMenuTextScale(0.55);
        check(close(glyphB.x, 141) && close(glyphB.y, 222.2)
            && close(glyphB.scale.x, 0.6875), 'rescaling after row movement changed its origin');
        check(close(decoration.x, 154.75) && close(decoration.scale.x, 0.22)
            && close(decoration.scale.y, 0.33), 'rescaling lost decoration-relative scale');
        check(close(row.width(), 55 * 0.55), 'rescaled row width was stale');

        row.setMenuTextScale(1);
        check(close(glyphA.x, 130) && close(glyphA.y, 220)
            && close(glyphB.x, 150) && close(glyphB.y, 224)
            && close(decoration.x, 175) && close(decoration.y, 222), 'scale 1 did not restore child spacing');
        check(close(glyphB.scale.x, 1.25) && close(decoration.scale.x, 0.4)
            && close(decoration.scale.y, 0.6) && close(row.width(), 55),
            'scale 1 did not restore child scales and measured width');
        row.setMenuTextScale(0);
        row.setMenuTextScale(Math.NaN);
        check(close(row.width(), 55), 'invalid scale changed the row');
    }}
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AlphabetMenuTextScaleMain.hx"
            path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "AlphabetMenuTextScaleMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
