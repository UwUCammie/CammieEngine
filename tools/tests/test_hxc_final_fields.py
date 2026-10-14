"""A V-Slice script's `final` class fields reach the generated script like its `var` fields."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

SONG = '''import flixel.tweens.FlxTween;
class FadeSong extends Song {
  final FADE_TIME:Float = 3.5;
  static final LABELS:Array<String> = ['a', 'b'];
  var props:Array<Dynamic> = [];
  function new() {
    super('fade');
  }
  final function fadeProps(on:Bool) {
    for (prop in props) FlxTween.tween(prop, {alpha: on ? 1 : 0}, FADE_TIME);
    return LABELS.length;
  }
  public function onBeatHit(event) {
    super.onBeatHit(event);
    fadeProps(true);
  }
}
'''

MAIN = '''class Main {
 static function main() {
  var code:String = HxcCompat.analyze(%s, 'scripts/songs/fade.hxc').generatedHscript;
  for (wanted in ['var FADE_TIME = 3.5;', "var LABELS = ['a', 'b'];", 'var props = [];', 'function fadeProps('])
   if (code.indexOf(wanted) < 0) throw 'missing ' + wanted + ': ' + code;
  // A final method is a function, not a field named "function".
  if (code.indexOf('var function') >= 0) throw 'final method read as a field: ' + code;
  // The constants are declared before the callbacks that read them.
  if (code.indexOf('var FADE_TIME') > code.indexOf('function ')) throw 'constant declared after use: ' + code;
  new hscript.ParserEx().parseString(code);
  Sys.println('OK');
 }
}
'''


class HxcFinalFieldsTest(unittest.TestCase):
    def test_final_fields_are_declared_for_the_methods(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps(SONG), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
