"""Repeated worker diagnostics are folded before they reach the unbuffered log."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]


class TraceDigestTest(unittest.TestCase):
    def test_repeats_are_counted_and_output_is_bounded(self):
        body = r"""class Main {
 static function check(ok:Bool, m:String) { if (!ok) throw m; }
 static function main() {
  var noisy = [for (i in 0...900) '[a] same'].concat([for (i in 0...700) '[b] other\r']).concat(['once', '', '   ']).join('\n');
  var folded = TraceDigest.collapse(noisy);
  check(folded == '[a] same (x900)\n[b] other (x700)\nonce', 'repeats not folded in first-seen order: ' + folded);
  var distinct = TraceDigest.collapse([for (i in 0...500) 'line ' + i].join('\n'));
  check(distinct.split('\n').length == TraceDigest.MAX_LINES + 1, 'distinct lines unbounded');
  check(distinct.indexOf('440 more distinct lines omitted') > 0, 'omission not reported');
  var wide = TraceDigest.collapse([for (i in 0...5000) 'x'].join(''));
  check(wide.length == TraceDigest.MAX_LINE && StringTools.endsWith(wide, '...'), 'long line unbounded');
  check(TraceDigest.collapse(null) == '' && TraceDigest.collapse('plain') == 'plain', 'plain text changed');
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            (Path(temp) / 'Main.hx').write_text(body, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manager = (ROOT / 'source/ImportRefreshManager.hx').read_text(encoding='utf-8')
        self.assertIn('"[import-refresh-conversion-error] " + TraceDigest.collapse(Std.string(error))', manager)


if __name__ == '__main__':
    unittest.main()
