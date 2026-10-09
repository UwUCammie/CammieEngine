"""Historical NV shader math, controls and real interpreter binding routes."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT.parent / 'fnf_sources/NightmareVision'
REVISION = '54c53faa9493b1de88051fda7fcb7ff69e4f3950'


def compact(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    return re.sub(r'\s+', '', text)


class NVLegacyColorSwapTest(unittest.TestCase):
    def test_historical_effect_math_matches_pinned_source(self):
        if not (DONOR / '.git').exists():
            self.skipTest('historical NV checkout unavailable')
        original = subprocess.check_output([
            'git', '-c', 'safe.directory=' + DONOR.as_posix(), '-C', str(DONOR),
            'show', REVISION + ':source/gameObjects/shader/ColorSwap.hx'], text=True)
        current = (ROOT / 'source/NightmareVisionLegacyColorSwap.hx').read_text()
        # Compare all effect operations; shared Flixel handles texture/color transforms.
        expected = original.split('vec3 rgb2hsv', 1)[1].split("')", 1)[0]
        actual = current.split('vec3 rgb2hsv', 1)[1].split("')", 1)[0]
        self.assertEqual(compact(actual), compact(expected))
        self.assertIn('#pragma header', current)
        self.assertNotIn('@:glVertexSource', current)

    def test_interpreter_import_library_reflection_and_uniform_controls(self):
        gameplay = (ROOT / 'source/PlayState.hx').read_text()
        bindings = gameplay.split("\t\tinterp.variables.set('ColorSwap', NightmareVisionColorSwap);", 1)[1].split("\t\tinterp.bindImport('funkin.game.shaders.DropShadowShader'", 1)[0]
        bindings = "interp.variables.set('ColorSwap', NightmareVisionColorSwap);\n" + bindings
        fixture = r'''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function configure(interp:NightmareVisionScriptInterp):Void { BINDINGS }
 static function main() {
  var errors:Array<String> = [];
  var module = NightmareVisionScriptModule.fromSource('owner-a', '
   addHaxeLibrary("ColorSwap", "gameObjects.shader");
   first = new ColorSwap();
   first.hue = 0.25; first.saturation = -0.5; first.brightness = 0.8;
   first.daAlpha = 0.3; first.flash = 0.4;
   first.shader.awesomeOutline.value[0] = true;
   import Type;
   legacyType = Type.resolveClass("gameObjects.shader.ColorSwap");
   second = Type.createInstance(legacyType, []);
   shaderType = Type.resolveClass("gameObjects.shader.ColorSwapShader");
   directShader = Type.createInstance(shaderType, []);
   import gameObjects.shader.ColorSwap.ColorSwapShader;
   nestedShader = new ColorSwapShader();
   modern = Type.createInstance(Type.resolveClass("funkin.game.shaders.ColorSwap"), []);
  ', null, null, configure, function(name, phase, error) errors.push(name + ":" + phase + ":" + Std.string(error)));
  check(module.initialized && errors.length == 0, 'source setup failed: ' + errors);
  var a:NightmareVisionLegacyColorSwap = module.get('first');
  var b:NightmareVisionLegacyColorSwap = module.get('second');
  check(a != null && b != null && a != b && a.shader != b.shader, 'independent live native instances');
  check(a.shader.uTime.value.join(',') == '0.25,-0.5,0.8', 'legacy vector uniform routing');
  check(a.shader.daAlpha.value[0] == 0.3 && a.shader.flash.value[0] == 0.4, 'legacy alpha/flash uniforms');
  check(a.shader.awesomeOutline.value[0], 'direct source outline write');
  check(b.hue == 0 && b.saturation == 0 && b.brightness == 0 && b.daAlpha == 1 && b.flash == 0, 'historical control defaults');
  check(b.shader.uTime.value.join(',') == '0,0,0' && b.shader.daAlpha.value[0] == 1 && !b.shader.awesomeOutline.value[0], 'historical uniform defaults');
  check(module.get('legacyType') == NightmareVisionLegacyColorSwap, 'qualified class identity');
  check(Std.isOfType(module.get('directShader'), NightmareVisionLegacyColorSwap.NightmareVisionLegacyColorSwapShader), 'direct shader reflection');
  check(Std.isOfType(module.get('nestedShader'), NightmareVisionLegacyColorSwap.NightmareVisionLegacyColorSwapShader), 'nested shader import');
  check(Std.isOfType(module.get('modern'), NightmareVisionColorSwap), 'modern qualified contract preserved');
  // Historical setters always write, including after direct uniform edits.
  a.shader.uTime.value = [9, 9, 9]; a.shader.daAlpha.value = [9]; a.shader.flash.value = [9];
  a.hue = 0.25; a.saturation = -0.5; a.brightness = 0.8; a.daAlpha = 0.3; a.flash = 0.4;
  check(a.shader.uTime.value.join(',') == '0.25,-0.5,0.8' && a.shader.daAlpha.value[0] == 0.3 && a.shader.flash.value[0] == 0.4, 'same-value setter restores live uniforms');
  var other = NightmareVisionScriptModule.fromSource('owner-b', 'defaultSwap = new ColorSwap();', null, null, configure, null);
  check(Std.isOfType(other.get('defaultSwap'), NightmareVisionColorSwap), 'explicit import must not change another preset');
  var retained = module.interp; module.destroy();
  check(!retained.importBindings.keys().hasNext() && !retained.variables.keys().hasNext(), 'bindings cleared on teardown');
  check(Std.isOfType(other.get('defaultSwap'), NightmareVisionColorSwap), 'other owner retained');
  other.destroy();
 }
}
'''.replace('BINDINGS', bindings)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'flixel/system').mkdir(parents=True, exist_ok=True)
            (work / 'flixel/system/FlxAssets.hx').write_text('''package flixel.system;
class FlxAssets {}
class Uniform<T> { public var value:Array<T> = []; public function new() {} }
class FlxShader {
 public var uTime = new Uniform<Float>(); public var daAlpha = new Uniform<Float>();
 public var flash = new Uniform<Float>(); public var awesomeOutline = new Uniform<Bool>();
 public var u_hue = new Uniform<Float>(); public var u_saturation = new Uniform<Float>();
 public var u_brightness = new Uniform<Float>(); public var u_alpha = new Uniform<Float>();
 public var u_flash = new Uniform<Float>(); public function new() {}
}''')
            (work / 'HxcCompatRuntime.hx').write_text('''class HxcCompatRuntime {
 public static function getZIndex(o:Dynamic):Dynamic return 0;
 public static function setZIndex(o:Dynamic,v:Dynamic,?op:String='='):Dynamic return v;
}''')
            (work / 'Main.hx').write_text(fixture)
            for defines in ([], ['-D', 'hscriptPos']):
                with self.subTest(defines=defines):
                    result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                        '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                        '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work),
                        *defines, '-main', 'Main', '--interp'], cwd=work,
                        capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
