"""A script error that repeats every frame is printed a few times, then hidden."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = '''class Main {
 static function main() {
  var printed = [];
  for (_ in 0...1000) {
   var line = RepeatedScriptErrorLog.line('scope.update:EUnknownVariable(x)', 'hscript error in scope.update: EUnknownVariable(x)');
   if (line != null) printed.push(line);
  }
  if (printed.length != RepeatedScriptErrorLog.SHOWN + 1) throw 'expected the first few and one notice, got ' + printed.length;
  if (printed[printed.length - 1].indexOf('further copies') < 0) throw 'the last line must say copies are hidden';
  // A different error, or the same error in another callback, is reported on its own.
  if (RepeatedScriptErrorLog.line('scope.update:EUnknownVariable(y)', 'y') != 'y') throw 'a new error was hidden';
  if (RepeatedScriptErrorLog.line('scope.beatHit:EUnknownVariable(x)', 'b') != 'b') throw 'another callback was hidden';
  // Unique messages never grow the table without bound.
  for (index in 0...5000) RepeatedScriptErrorLog.line('unique' + index, 'u');
  if (@:privateAccess RepeatedScriptErrorLog.keys > 512) throw 'the table grew past its bound';
  var play = sys.io.File.getContent('source/PlayState.hx');
  if (play.indexOf('RepeatedScriptErrorLog.line(usehaxe') < 0) throw 'script errors do not go through the repeat filter';
  var create = play.indexOf('override public function create() {');
  if (play.indexOf('RepeatedScriptErrorLog.reset();', create) < 0 || play.indexOf('RepeatedScriptErrorLog.reset();', create) > play.indexOf('EngineMemory.enterSong(this);', create))
   throw 'a new song must report errors again';
 }
}
'''


class RepeatedScriptErrorLogTest(unittest.TestCase):
    def test_repeats_are_hidden_after_a_few(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'RepeatedScriptErrorLog.hx').write_text(
                (ROOT / 'source/RepeatedScriptErrorLog.hx').read_text(encoding='utf-8'), newline=chr(10))
            (Path(folder) / 'Main.hx').write_text(MAIN, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
