"""Script translation garbage is collected a few files at a time, not left to pile up."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

POLICY = r'''class TranslationCollectFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var collects:Array<Bool> = [];
  EngineMemory.collector = function(major:Bool) collects.push(major);
  EngineMemory.reset();
  var step = Std.int(EngineMemory.TRANSLATION_COLLECT_CHARS / 4);
  // Small files add up; nothing is collected until the budget is used.
  for (i in 0...3)
   if (EngineMemory.scriptTranslated(step)) fail("collected before the budget was used");
  if (collects.length != 0) fail("collector ran early");
  if (!EngineMemory.scriptTranslated(step)) fail("budget used without a collection");
  // A quick collection is enough to free the dead expressions.
  if (collects.join(",") != "false") fail("expected one minor collection: " + collects.join(","));
  if (EngineMemory.translationCollects != 1) fail("translation collection not counted");
  // One large file collects right after it, and the count starts again.
  if (!EngineMemory.scriptTranslated(EngineMemory.TRANSLATION_COLLECT_CHARS * 3)) fail("large file did not collect");
  if (EngineMemory.scriptTranslated(step)) fail("budget was not reset");
  if (EngineMemory.scriptTranslated(0) || EngineMemory.scriptTranslated(-5)) fail("empty input collected");
  // Pause and handoff spacing is untouched: a pause right after still collects.
  if (!EngineMemory.collectNow(true, 'pause')) fail("translation collection blocked the pause collection");
  Sys.println("OK");
 }
}'''

ANALYZE = '''class Main {
 static function main() {
  var sizes:Array<Int> = [];
  var total = 0;
  EngineMemory.collector = function(major:Bool) sizes.push(total);
  EngineMemory.reset();
  var source = %s;
  // Each file is counted once, companion classes inside it included.
  var big = source;
  while (big.length < EngineMemory.TRANSLATION_COLLECT_CHARS) big += '\\n// padding line for size';
  HxcCompat.analyze(big, 'scripts/songs/pair.hxc');
  if (sizes.length != 1) throw 'one large file should collect once, got ' + sizes.length;
  // Most of this file is the companion class. Counting the companion as a file
  // of its own would pass the budget; counting the file once does not.
  EngineMemory.reset();
  sizes = [];
  var padded = StringTools.replace(source, 'PADDING', [for (i in 0...5500) 'x'].join(''));
  if (padded.length >= EngineMemory.TRANSLATION_COLLECT_CHARS || padded.length * 2 < EngineMemory.TRANSLATION_COLLECT_CHARS)
   throw 'fixture size is off: ' + padded.length;
  HxcCompat.analyze(padded, 'scripts/songs/pair.hxc');
  if (sizes.length != 0) throw 'the companion class was counted as another file';
  Sys.println('OK');
 }
}
'''

PAIR = '''class PairOptions extends Module {
  var pad = "PADDING";
  public function new() { super('PairOptions'); }
  public function onUpdate(event) {}
}
class PairSong extends Song {
  public function new() { super('pair'); }
  public function onBeatHit(event) {}
}
'''


class TranslationCollectTest(unittest.TestCase):
    def run_haxe(self, folder, main, extra):
        return subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
            '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '-cp', folder, *extra, '-main', main, '--interp'],
            cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_budget_policy(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'TranslationCollectFixture.hx').write_text(POLICY, newline=chr(10))
            result = self.run_haxe(folder, 'TranslationCollectFixture', [])
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('OK', result.stdout)

    def test_analyze_counts_each_file_once(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(ANALYZE % json.dumps(PAIR), newline=chr(10))
            result = self.run_haxe(folder, 'Main', [])
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
