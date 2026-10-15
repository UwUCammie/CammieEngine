"""Removal hashes text as the UTF-8 bytes written to disk, so non-ASCII registries and paths match."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import sys.io.File;
@:access(ImportRemovalTransaction)
class Main {
	static function check(ok:Bool, why:String):Void if (!ok) throw why;
	static function main() {
		var dir = Sys.args()[0];
		for (text in ['plain ascii registry', '{"name":"Café Tomodachi ともだち","weeks":["週"]}', 'assets/data/歌/song.json']) {
			var path = dir + '/staged.txt';
			File.saveBytes(path, Bytes.ofString(text));
			var onDisk = Sha256.make(File.getBytes(path)).toHex();
			check(ImportRemovalTransaction.key(text) == onDisk, 'removal hash differs from the bytes on disk for: ' + text);
			File.saveContent(path, text);
			check(Sha256.make(File.getBytes(path)).toHex() == ImportRemovalTransaction.key(text), 'saveContent wrote other bytes for: ' + text);
		}
		// A journal written before the fix recorded Sha256.encode; its cleanup must still finish.
		var legacy = '{"name":"Café ともだち"}';
		File.saveContent(dir + '/legacy.txt', legacy);
		check(ImportRemovalTransaction.stagedTextMatches(dir + '/legacy.txt', Sha256.encode(legacy)), 'legacy journal hash refused');
		check(ImportRemovalTransaction.stagedTextMatches(dir + '/legacy.txt', ImportRemovalTransaction.key(legacy)), 'current hash refused');
		check(!ImportRemovalTransaction.stagedTextMatches(dir + '/legacy.txt', ImportRemovalTransaction.key(legacy + ' ')), 'edited staged file accepted');
		// ASCII keys (state folders, staged names) must not move.
		check(ImportRemovalTransaction.key('retained-import:abc') == Sha256.encode('retained-import:abc'), 'ascii key changed');
		Sys.println('unicode hash contract passed');
	}
}
'''


class ImportRemovalUnicodeHashTest(unittest.TestCase):
    def test_non_ascii_text_hashes_like_its_file(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(FIXTURE, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/tjson/1,4,0'),
                '-cp', str(work), '--run', 'Main', str(work)], cwd=work, capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('unicode hash contract passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
