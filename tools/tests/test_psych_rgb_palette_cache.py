"""Exercise the Psych palette cache and per-note copy-on-write with Haxe doubles."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PsychRGBPaletteCacheTest(unittest.TestCase):
    def test_shared_defaults_and_isolated_note_mutations(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            for name in ('PsychRGBShader.hx', 'PsychRGBPalette.hx', 'PsychRGBShaderReference.hx'):
                shutil.copyfile(ROOT / 'source' / name, work / name)

            (work / 'flixel/system').mkdir(parents=True)
            (work / 'flixel/system/FlxAssets.hx').write_text('''package flixel.system;
class Uniform<T> {
  public var value:T;
  public function new(value:T) this.value=value;
}
class FlxShader {
  public static var constructions:Int=0;
  public var r:Uniform<Array<Float>>;
  public var g:Uniform<Array<Float>>;
  public var b:Uniform<Array<Float>>;
  public var mult:Uniform<Array<Float>>;
  public function new() {
    constructions++;
    r=new Uniform([0.0,0.0,0.0]); g=new Uniform([0.0,0.0,0.0]);
    b=new Uniform([0.0,0.0,0.0]); mult=new Uniform([0.0]);
  }
}''')
            (work / 'flixel/util').mkdir(parents=True)
            (work / 'flixel/util/FlxColor.hx').write_text('''package flixel.util;
abstract FlxColor(Int) from Int to Int {
  public var redFloat(get,never):Float;
  public var greenFloat(get,never):Float;
  public var blueFloat(get,never):Float;
  inline function get_redFloat():Float return ((this >> 16) & 255) / 255;
  inline function get_greenFloat():Float return ((this >> 8) & 255) / 255;
  inline function get_blueFloat():Float return (this & 255) / 255;
}''')
            (work / 'flixel').mkdir(exist_ok=True)
            (work / 'flixel/FlxSprite.hx').write_text('''package flixel;
class FlxSprite { public var shader:Dynamic; public function new() {} }''')
            (work / 'Probe.hx').write_text('''import flixel.FlxSprite;
import flixel.system.FlxAssets.FlxShader;
class Probe {
  static function check(ok:Bool, label:String):Void if (!ok) throw label;
  static function main():Void {
    var normal=PsychRGBPalette.defaultFor(1,false);
    check(normal == PsychRGBPalette.defaultFor(5,false), 'lane palettes normalize modulo four');
    var otherLane=PsychRGBPalette.defaultFor(2,false);
    var pixel=PsychRGBPalette.defaultFor(1,true);
    var hurt=PsychRGBPalette.defaultFor(1,false,true);
    var pixelHurt=PsychRGBPalette.defaultFor(1,true,true);
    check(normal != otherLane && normal != pixel && normal != hurt && pixel != pixelHurt,
      'lane, pixel, and hurt palettes stay distinct');
    check(FlxShader.constructions == 5, 'one shader per distinct default palette');

    var ownerA=new FlxSprite(); var ownerB=new FlxSprite();
    var noteA=new PsychRGBShaderReference(ownerA,normal);
    var noteB=new PsychRGBShaderReference(ownerB,normal);
    check(ownerA.shader == normal.shader && ownerB.shader == normal.shader,
      'notes initially share the cached shader');
    var originalRed=normal.r;
    noteA.r=0xFF123456;
    check(noteA.parent != normal && noteA.parent.r == 0xFF123456,
      'first custom color clones and updates only the selected note palette');
    check(ownerA.shader == noteA.parent.shader && ownerB.shader == normal.shader
      && normal.r == originalRed, 'copy-on-write leaves sibling notes unchanged');
    check(FlxShader.constructions == 6, 'one shader is created for the isolated palette');
    noteA.g=0xFF654321;
    check(FlxShader.constructions == 6 && noteA.parent.g == 0xFF654321,
      'later channel changes reuse the note clone');
    noteA.mult=2.0;
    check(noteA.mult == 1.0 && noteA.parent.mult == 1.0, 'mix amount keeps Psych bounds');

    noteA.enabled=false;
    check(ownerA.shader == null && ownerB.shader == normal.shader,
      'enabled is per note');
    noteA.usePalette(pixel);
    check(noteA.parent == pixel && ownerA.shader == null,
      'palette changes rebind while preserving the enabled state');
    noteA.enabled=true;
    check(ownerA.shader == pixel.shader, 're-enabled note attaches its selected palette');
    noteB.usePalette(normal);
    check(noteB.parent == normal && ownerB.shader == normal.shader,
      'a note can continue using the original cached palette');
  }
}''')

            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(work),
                                     '-main', 'Probe', '--interp'], cwd=work, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == '__main__':
    unittest.main()
