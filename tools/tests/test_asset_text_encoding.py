"""UTF-8 asset signatures are decoded in memory without donor edits."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class AssetTextEncodingTest(unittest.TestCase):
    def test_signature_only_and_read_only_asset_round_trip(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            asset = work / 'Animation.json'
            payload = b'\xef\xbb\xbf {"label":"inside \xef\xbb\xbf text"}\r\n'
            asset.write_bytes(payload)
            (work / 'Main.hx').write_text(r'''
class Main {
 static function main() {
  var raw = sys.io.File.getContent('Animation.json');
  var text = AssetTextEncoding.stripBom(raw);
  var data:Dynamic = haxe.Json.parse(text);
  if (data.label != 'inside \uFEFF text') throw 'internal character changed';
  if (text != ' {"label":"inside \uFEFF text"}\r\n') throw 'authored whitespace changed';
  if (AssetTextEncoding.stripBom(null) != null || AssetTextEncoding.stripBom('') != '') throw 'empty changed';
  var normal = ' {"x":1}\n';
  if (AssetTextEncoding.stripBom(normal) != normal) throw 'unmarked text changed';
  var bytes = String.fromCharCode(0xEF)+String.fromCharCode(0xBB)+String.fromCharCode(0xBF)+normal;
  if (AssetTextEncoding.stripBom(bytes) != normal) throw 'byte target signature';
 }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', str(work), '--main', 'Main', '--interp'], cwd=work,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(asset.read_bytes(), payload)
