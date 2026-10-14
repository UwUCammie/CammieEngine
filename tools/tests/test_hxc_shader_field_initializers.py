"""A V-Slice script's AdjustColorShader and DropShadowShader fields keep their constructor."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

SONG = '''import funkin.graphics.shaders.AdjustColorShader;
import funkin.graphics.shaders.DropShadowShader;
import openfl.filters.ShaderFilter;
class TintSong extends Song {
  public function new() {
    super('tint');
  }
  function onBeatHit(event) {
    adjustColor.hue = -15;
    shadow.angle = 90;
    PlayState.instance.camGame.filters = [new ShaderFilter(adjustColor)];
  }
  var adjustColor = new AdjustColorShader();
  var shadow:DropShadowShader = new DropShadowShader();
  var tinted = new TintHelper(adjustColor);
}
'''

MAIN = '''class Main {
 static function main() {
  var code:String = HxcCompat.analyze(%s, 'scripts/songs/tint.hxc').generatedHscript;
  for (wanted in ['var adjustColor = new AdjustColorShader();', 'var shadow = new DropShadowShader();'])
   if (code.indexOf(wanted) < 0) throw 'shader field lost its constructor ' + wanted + ': ' + code;
  // Other constructors are still not replayed.
  if (code.indexOf('new TintHelper') >= 0) throw 'unknown constructor was replayed: ' + code;
  new hscript.ParserEx().parseString(code);
  Sys.println('OK');
 }
}
'''


class HxcShaderFieldInitializersTest(unittest.TestCase):
    def test_engine_shader_fields_are_constructed(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps(SONG), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
