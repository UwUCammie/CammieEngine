"""Exercise the Psych palette cache and per-note copy-on-write with Haxe doubles."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
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
  public var __isGenerated:Bool=false;
  public var __data:Dynamic={};
  public var __paramFloat:Array<Dynamic>=[];
  public var glFragmentSource:String='uniform float u_alpha;';
  public var initGLCalls:Int=0;
  var initialized:Bool=false;
  public var r:Uniform<Array<Float>>;
  public var g:Uniform<Array<Float>>;
  public var b:Uniform<Array<Float>>;
  public var mult:Uniform<Array<Float>>;
  public var u_alpha:Uniform<Array<Float>>;
  public var u_flash:Uniform<Array<Float>>;
  public function new() {
    constructions++;
  }
  public function __initGL():Void {
    if (initialized) return;
    if (!__isGenerated) throw 'generated shader initialized before macro construction';
    initialized=true;
    initGLCalls++;
    r=new Uniform([0.0,0.0,0.0]); g=new Uniform([0.0,0.0,0.0]);
    b=new Uniform([0.0,0.0,0.0]); mult=new Uniform([0.0]);
    u_alpha=new Uniform([0.0]); u_flash=new Uniform([0.0]);
  }
}''', newline='\n')
            (work / 'flixel/util').mkdir(parents=True)
            (work / 'flixel/util/FlxColor.hx').write_text('''package flixel.util;
abstract FlxColor(Int) from Int to Int {
  public var redFloat(get,never):Float;
  public var greenFloat(get,never):Float;
  public var blueFloat(get,never):Float;
  inline function get_redFloat():Float return ((this >> 16) & 255) / 255;
  inline function get_greenFloat():Float return ((this >> 8) & 255) / 255;
  inline function get_blueFloat():Float return (this & 255) / 255;
}''', newline='\n')
            (work / 'flixel').mkdir(exist_ok=True)
            (work / 'flixel/FlxSprite.hx').write_text('''package flixel;
class FlxSprite { public var shader:Dynamic; public function new() {} }''', newline='\n')
            (work / 'Probe.hx').write_text('''import flixel.FlxSprite;
import flixel.system.FlxAssets.FlxShader;
class Probe {
  static function check(ok:Bool, label:String):Void if (!ok) throw label;
  static function main():Void {
    var normal=PsychRGBPalette.defaultFor(1,false);
    check(normal.shader.__isGenerated && normal.shader.initGLCalls == 1,
      'Psych shader initializes macro uniforms before assigning defaults');
    check(normal.shader.u_alpha.value[0] == 1.0 && normal.shader.u_flash.value[0] == 0.0,
      'shared shader starts at identity draw alpha and no flash');
    var alphaUniform=normal.shader.u_alpha;
    normal.shader.__initGL();
    check(normal.shader.initGLCalls == 1 && normal.shader.u_alpha == alphaUniform
      && normal.shader.u_alpha.value[0] == 1.0,
      'OpenFL-style generated shader initialization is idempotent');
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
}''', newline='\n')

            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work),
                                     '-main', 'Probe', '--interp'], cwd=work, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_real_openfl_shader_macro_initializes_defaults_before_repeated_construction(self):
        """Exercise the delayed uniform generation in the pinned OpenFL/Flixel source."""
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Probe.hx').write_text('''class Probe {
  static function main():Void {
    for (i in 0...2000) {
      var shader = new PsychRGBShader();
      if (shader.u_alpha.value[0] != 1.0)
        throw 'Psych shader alpha default failed at instance ' + i;
      if (shader.u_flash.value[0] != 0.0)
        throw 'Psych shader flash default failed at instance ' + i;
    }
  }
}''', encoding='utf-8', newline='\n')

            env = dict(os.environ)
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['LD_LIBRARY_PATH'] = os.pathsep.join(filter(None, [
                str(ROOT / '.tools/neko'), env.get('LD_LIBRARY_PATH', '')
            ]))
            env['PATH'] = os.pathsep.join([
                str(ROOT / '.tools/haxe'), str(ROOT / '.tools/neko'), env.get('PATH', '')
            ])
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', str(work), '-lib', 'lime', '-lib', 'openfl', '-lib', 'flixel',
                 '-D', 'FLX_STANDARD_ASSETS_DIRECTORY', '-main', 'Probe', '--interp'],
                cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == '__main__':
    unittest.main()
