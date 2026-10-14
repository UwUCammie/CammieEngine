"""Notes with identical RGB uniforms draw with one shared shader; any other note gets its own."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PALETTE = '''class PsychRGBPalette {
 public static var made:Int = 0;
 public var shader:Dynamic;
 public var r(default, set):Int; public var g(default, set):Int; public var b(default, set):Int;
 public var mult(default, set):Float;
 public function new() {
  made++;
  shader = {r:{value:null}, g:{value:null}, b:{value:null}, mult:{value:null}, u_alpha:{value:[1.0]}, u_flash:{value:[0.0]}, id:made};
  r = 0xFFFF0000; g = 0xFF00FF00; b = 0xFF0000FF; mult = 1.0;
 }
 function set_r(v:Int):Int { r = v; shader.r.value = [v]; return v; }
 function set_g(v:Int):Int { g = v; shader.g.value = [v]; return v; }
 function set_b(v:Int):Int { b = v; shader.b.value = [v]; return v; }
 function set_mult(v:Float):Float { mult = Math.max(0, Math.min(1, v)); shader.mult.value = [mult]; return mult; }
 public function copy():PsychRGBPalette { var p = new PsychRGBPalette(); p.r = r; p.g = g; p.b = b; p.mult = mult; return p; }
 public function copyValues(o:PsychRGBPalette):Void { if (o == null) { mult = 0.0; return; } r = o.r; g = o.g; b = o.b; mult = o.mult; }
}'''

MAIN = r'''
class Main {
 static function fail(m:String):Void throw m;
 static function check(ok:Bool, m:String):Void if (!ok) fail(m);
 static function uniform(shader:Dynamic, name:String):Dynamic return Reflect.field(Reflect.field(shader, name), 'value')[0];
 // What the old code rendered: a private palette copy with the uniforms written by apply.
 static function oldUniforms(base:PsychRGBPalette, enabled:Bool, alpha:Float, flash:Float):Array<Dynamic> {
  var p = base.copy();
  return [p.r, p.g, p.b, enabled ? p.mult : 0, alpha, flash];
 }
 static function rendered(sprite:flixel.FlxSprite):Array<Dynamic>
  return [uniform(sprite.shader, 'r'), uniform(sprite.shader, 'g'), uniform(sprite.shader, 'b'),
   uniform(sprite.shader, 'mult'), uniform(sprite.shader, 'u_alpha'), uniform(sprite.shader, 'u_flash')];
 static function same(a:Array<Dynamic>, b:Array<Dynamic>, m:String):Void
  check(a.join(',') == b.join(','), m + ': ' + a.join(',') + ' vs ' + b.join(','));
 static function main() {
  var lane = new PsychRGBPalette(); lane.r = 0xFFC24B99; lane.g = 0xFFFFFFFF; lane.b = 0xFF3C1F56;
  var before = PsychRGBPalette.made;
  var notes = [for (i in 0...200) new NightmareVisionRGBGraphics(lane)];
  check(PsychRGBPalette.made == before, 'building note graphics made a palette per note');
  var sprites = [for (i in 0...200) new flixel.FlxSprite()];
  for (i in 0...200) notes[i].apply(sprites[i]);
  check(PsychRGBPalette.made == before + 1, 'identical notes did not share one shader, made ' + (PsychRGBPalette.made - before));
  for (s in sprites) check(s.shader == sprites[0].shader, 'a plain note drew with another shader');
  same(rendered(sprites[0]), oldUniforms(lane, true, 1, 0), 'shared uniforms differ from a private copy');

  // A faded or flashing note gets its own shader; the shared one keeps its values.
  notes[5].alpha = 0.4; notes[5].flash = 0.3; notes[5].apply(sprites[5]);
  check(sprites[5].shader != sprites[0].shader, 'a faded note drew with the shared shader');
  same(rendered(sprites[5]), oldUniforms(lane, true, 0.4, 0.3), 'faded note uniforms');
  same(rendered(sprites[0]), oldUniforms(lane, true, 1, 0), 'shared uniforms were written by a faded note');
  // Disabled colouring is a different set of uniforms, so a different shader.
  notes[6].enabled = false; notes[6].apply(sprites[6]);
  same(rendered(sprites[6]), oldUniforms(lane, false, 1, 0), 'disabled note uniforms');
  check(sprites[6].shader != sprites[0].shader, 'disabled note shared the enabled shader');
  // Colour changes alone stay shared and render the new colours.
  notes[7].setColors([0xFF112233, 0xFF445566, 0xFF778899]); notes[7].apply(sprites[7]);
  check(notes[7].ownPalette() == null, 'setting colours made an own palette');
  check(notes[7].getColors().join(',') == [0xFF112233, 0xFF445566, 0xFF778899].join(','), 'colours not kept');
  check(uniform(sprites[7].shader, 'r') == 0xFF112233 && uniform(sprites[0].shader, 'r') == 0xFFC24B99, 'colour change leaked');
  notes[8].mult = 2.5; check(notes[8].mult == 1, 'mult clamp differs from the palette');
  notes[8].copyValues(null); check(notes[8].mult == 0, 'copyValues(null) must zero mult like the palette');

  // Asking for the palette gives a private copy holding the same values.
  var own = notes[9].palette;
  check(own != null && notes[9].ownPalette() == own, 'palette access did not create an own palette');
  check(own.r == 0xFFC24B99 && own.mult == 1, 'own palette lost the values');
  own.g = 0xFF000000; check(notes[9].g == 0xFF000000, 'own palette and getters disagree');
  // Released palettes are reused, with the new owner's values.
  var made = PsychRGBPalette.made;
  notes[5].release(); check(notes[5].ownPalette() == null, 'release kept the palette');
  check(notes[5].alpha == 0.4 && notes[5].r == 0xFFC24B99, 'release lost the values');
  notes[10].flash = 0.5; notes[10].apply(sprites[10]);
  check(PsychRGBPalette.made == made, 'a released palette was not reused');
  same(rendered(sprites[10]), oldUniforms(lane, true, 1, 0.5), 'reused palette uniforms');

  // An own palette re-applied each frame writes its uniforms in place: same
  // values a fresh array would carry, no new array per frame.
  var fading = new NightmareVisionRGBGraphics(lane); var fadingSprite = new flixel.FlxSprite();
  fading.alpha = 0.9; fading.apply(fadingSprite);
  var alphaArray:Dynamic = Reflect.field(Reflect.field(fadingSprite.shader, 'u_alpha'), 'value');
  var multArray:Dynamic = Reflect.field(Reflect.field(fadingSprite.shader, 'mult'), 'value');
  for (step in 1...6) {
   fading.alpha = 0.9 - step * 0.1; fading.flash = step * 0.05; fading.enabled = step % 2 == 0;
   fading.apply(fadingSprite);
   same(rendered(fadingSprite), oldUniforms(lane, step % 2 == 0, 0.9 - step * 0.1, step * 0.05), 'own palette frame ' + step);
   check(Reflect.field(Reflect.field(fadingSprite.shader, 'u_alpha'), 'value') == alphaArray, 'alpha uniform array replaced');
   check(Reflect.field(Reflect.field(fadingSprite.shader, 'mult'), 'value') == multArray, 'mult uniform array replaced');
  }

  // A colour tween makes a new combination every frame. Shared palettes stop
  // at the cap; past it a note draws with its own palette and right values.
  var tween = new NightmareVisionRGBGraphics(lane);
  var tweenSprite = new flixel.FlxSprite();
  var sharedBefore = PsychRGBPalette.made;
  for (frame in 0...(NightmareVisionRGBGraphics.MAX_SHARED + 50)) {
   if (tween.ownPalette() == null) tween.r = 0xFF000000 + frame;
   else tween.palette.r = 0xFF000000 + frame;
   tween.apply(tweenSprite);
   check(uniform(tweenSprite.shader, 'r') == 0xFF000000 + frame, 'tweened colour not rendered at frame ' + frame);
  }
  check(PsychRGBPalette.made - sharedBefore <= NightmareVisionRGBGraphics.MAX_SHARED,
   'shared palettes grew past the cap: ' + (PsychRGBPalette.made - sharedBefore));
  check(tween.ownPalette() != null, 'past the cap the note did not get its own palette');
  // A new note with a colour no shared palette holds also falls back, correctly.
  var late = new NightmareVisionRGBGraphics(lane); late.setColors([0xFF010203, 0xFF040506, 0xFF070809]);
  var lateSprite = new flixel.FlxSprite(); late.apply(lateSprite);
  check(late.ownPalette() != null && lateSprite.shader == late.ownPalette().shader, 'late note did not fall back to its own palette');
  same(rendered(lateSprite), [0xFF010203, 0xFF040506, 0xFF070809, 1, 1, 0], 'late note uniforms');
  // Existing shared combinations keep sharing after the cap.
  var plain = new NightmareVisionRGBGraphics(lane); var plainSprite = new flixel.FlxSprite(); plain.apply(plainSprite);
  check(plainSprite.shader == sprites[0].shader, 'an existing shared combination stopped sharing after the cap');
 }
}
'''


class NightmareVisionRgbSharedShaderTest(unittest.TestCase):
    def test_shared_shader_renders_the_same_uniforms(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "NightmareVisionRGBGraphics.hx").write_text(
                (ROOT / "source/NightmareVisionRGBGraphics.hx").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            (work / "PsychRGBPalette.hx").write_text(PALETTE, encoding="utf-8", newline="\n")
            (work / "NightmareVisionLegacyColorSwap.hx").write_text(
                "class NightmareVisionLegacyColorSwap {public var shader:Dynamic;public var daAlpha:Float=1;public var flash:Float=0;}", newline="\n")
            (work / "NightmareVisionHSLColorSwap.hx").write_text(
                "class NightmareVisionHSLColorSwap {public var shader:Dynamic;}", newline="\n")
            (work / "flixel").mkdir()
            (work / "flixel/FlxSprite.hx").write_text(
                "package flixel; class FlxSprite {public var shader:Dynamic; public function new() {}}", newline="\n")
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(FixturePath(directory)), "--main", "Main", "--interp"],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_destroyed_notes_hand_their_palette_back(self):
        note = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        self.assertIn("if (nightmareVisionRGB != null) nightmareVisionRGB.release();\n\t\tnightmareVisionRGB = null;",
                      note.replace("\r\n", "\n"))
        skin = (ROOT / "source/NightmareVisionNoteSkin.hx").read_text(encoding="utf-8")
        self.assertIn("else graphics.copyValues(palette(lane));", skin)


if __name__ == "__main__":
    unittest.main()
