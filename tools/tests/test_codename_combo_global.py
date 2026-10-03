"""A source script reads the current native combo during note callbacks."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameComboGlobalTest(unittest.TestCase):
    def test_combo_binding_reads_and_writes_native_count(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        match = re.search(r'\tfunction seedCodenameNoteGlobals\(', source)
        self.assertIsNotNone(match)
        start = source.index('{', match.start())
        depth = 0
        for end in range(start, len(source)):
            depth += (source[end] == '{') - (source[end] == '}')
            if depth == 0:
                break
        method = source[match.start():end + 1]
        fixture = '''class CodenameScriptInterp {
 public var variables:Map<String, Dynamic> = [];
 public var live:Map<String, {read:Void->Dynamic, write:Dynamic->Void}> = [];
 public function new() {}
 public function bindLiveGlobal(name:String, read:Void->Dynamic, write:Dynamic->Void):Void
  live.set(name, {read:read, write:write});
}
class Main {
 var paused=false;
 var accuracy:Dynamic=0;
 var codenameAccuracy:Dynamic=0;
 var comboRatings:Dynamic=[];
 var curRating:Dynamic=null;
 var misses:Dynamic=0;
 var songScore:Dynamic=0;
 var combo:Int=0;
 var comboBreaks:Dynamic=0;
 var downscroll:Dynamic=false;
 var defaultDisplayRating:Dynamic=true;
 var defaultDisplayCombo:Dynamic=true;
 var minDigitDisplay:Dynamic=0;
 var muteVocalsOnMiss:Dynamic=false;
 var accuracyPressedNotes:Dynamic=0;
 var totalAccuracyAmount:Dynamic=0;
 var ratingNum:Dynamic=0;
 public function new() {}
 function updateRating():Void {}
''' + method + '''
 public static function main():Void {
  var state=new Main();var interp=new CodenameScriptInterp();
  state.seedCodenameNoteGlobals(interp);
  var binding=interp.live.get('combo');
  if(binding==null || binding.read()!=0) throw 'missing combo binding';
  state.combo=50;
  if(binding.read()!=50) throw 'combo read became stale';
  binding.write(200);
  if(state.combo!=200) throw 'combo write did not reach native count';
  Sys.println('combo binding ok');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND,
                                     '-cp', folder, '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('combo binding ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
