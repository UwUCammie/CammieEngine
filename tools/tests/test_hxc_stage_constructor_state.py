"""A V-Slice Stage's own state set in new() after super() reaches the generated script."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

STAGE = '''import flixel.util.FlxSave;
class RainyStage extends Stage {
  function new() {
    super('rainy');
    save = new FlxSave();
    save.bind("StageOptions", "Author");
    strikes = 3;
  }
  var unrelated = false;
  function onUpdate(event) {
    if (save.data.effects != false) strikes += 1;
  }
}
'''

MAIN = '''class Main {
 static function main() {
  var code:String = HxcCompat.analyze(%s, 'scripts/stages/RainyStage.hxc').generatedHscript;
  for (wanted in ['var save = __hxcStore;', 'save.bind("StageOptions", "Author");', 'strikes = 3'])
   if (code.indexOf(wanted) < 0) throw 'constructor state lost ' + wanted + ': ' + code;
  // The statement runs once when the script loads, before any callback.
  if (code.indexOf('save.bind') > code.indexOf('function ')) throw 'constructor state must come before the callbacks: ' + code;
  new hscript.ParserEx().parseString(code);
 }
}
'''


class HxcStageConstructorStateTest(unittest.TestCase):
    def test_stage_constructor_state_is_replayed(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps(STAGE), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])


if __name__ == '__main__':
    unittest.main()
