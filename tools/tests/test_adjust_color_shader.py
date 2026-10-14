"""The base-game AdjustColorShader that V-Slice scripts construct by name."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
SHADER = ROOT / 'source/shaders/AdjustColorShader.hx'

# Stands in for the OpenFL shader macro, which adds one ShaderParameter field per uniform.
FLX_SHADER_STUB = '''package flixel.system;
class Param { public var value:Array<Float>; public function new() {} }
class FlxAssets {}
class FlxShader {
 public var uHue = new Param();
 public var uSaturation = new Param();
 public var uBrightness = new Param();
 public var uContrast = new Param();
 public function new() {}
}
'''

MAIN = '''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  var shader = new shaders.AdjustColorShader();
  check(shader.uHue.value[0] == 0 && shader.uSaturation.value[0] == 0
   && shader.uBrightness.value[0] == 0 && shader.uContrast.value[0] == 0,
   'a new shader must start neutral with every uniform written');
  // Scripts write the plain properties through reflection, as hscript does.
  Reflect.setProperty(shader, 'hue', -26);
  Reflect.setProperty(shader, 'saturation', -16);
  Reflect.setProperty(shader, 'brightness', -5);
  Reflect.setProperty(shader, 'contrast', 12);
  check(shader.hue == -26 && shader.uHue.value[0] == -26, 'hue did not reach its uniform');
  check(shader.saturation == -16 && shader.uSaturation.value[0] == -16, 'saturation did not reach its uniform');
  check(shader.brightness == -5 && shader.uBrightness.value[0] == -5, 'brightness did not reach its uniform');
  check(shader.contrast == 12 && shader.uContrast.value[0] == 12, 'contrast did not reach its uniform');
 }
}
'''


def glsl_body(text, start):
    """Return the shader functions from `start` on, without comments or blank space."""
    text = re.sub(r'//[^\n]*', '', text[text.index(start):])
    return re.sub(r'\s+', '', text)


class AdjustColorShaderTest(unittest.TestCase):
    def test_properties_write_their_uniforms(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            (root / 'flixel/system').mkdir(parents=True)
            (root / 'flixel/system/FlxAssets.hx').write_text(FLX_SHADER_STUB, newline='\n')
            (root / 'shaders').mkdir()
            (root / 'shaders/AdjustColorShader.hx').write_text(SHADER.read_text(encoding='utf-8'), newline='\n')
            (root / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_colour_maths_matches_the_shipped_adjust_color_shader(self):
        source = SHADER.read_text(encoding='utf-8')
        fragment = source[source.index("@:glFragmentSource('") + 20:source.index("')", source.index('@:glFragmentSource'))]
        shipped = (ROOT / 'assets/shaders/adjustColor.frag').read_text(encoding='utf-8')
        for name in ('hue', 'saturation', 'brightness', 'contrast'):
            self.assertIn('uniform float u%s;' % name.capitalize(), fragment)
            # The shipped file uses the plain names; the class prefixes them only
            # because the plain names are its public properties.
            shipped = re.sub(r'\b%s\b' % name, 'u' + name.capitalize(), shipped)
        start = 'const vec3 grayscaleValues'
        self.assertEqual(glsl_body(fragment, start), glsl_body(shipped, start))

    def test_every_script_interpreter_can_construct_it(self):
        plugins = (ROOT / 'source/PluginManager.hx').read_text(encoding='utf-8')
        self.assertIn('interp.variables.set("AdjustColorShader", shaders.AdjustColorShader);', plugins)


if __name__ == '__main__':
    unittest.main()
