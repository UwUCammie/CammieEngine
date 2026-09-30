"""Psych character trails use the atlas of the selected native visual."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychCharacterImageTest(unittest.TestCase):
    def test_selected_atlas_identity_and_swap(self):
        character = (ROOT / 'source/Character.hx').read_text()
        self.assertIn('public var imageFile:String', character)
        self.assertIn('imageFile = PsychCharacterImage.resolve(graphicKey, resolvedAssetRoot);', character)
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / 'PsychCharacterImage.hx').write_text(
                (ROOT / 'source/PsychCharacterImage.hx').read_text())
            for name in ('first', 'second', 'actual'):
                atlas = work / 'assets/images/custom_chars' / name
                atlas.mkdir(parents=True)
                (atlas / 'char.png').write_bytes(b'png')
                (atlas / 'char.xml').write_text('<TextureAtlas/>')
            missing_xml = work / 'assets/images/custom_chars/missing_xml'
            missing_xml.mkdir(parents=True)
            (missing_xml / 'char.png').write_bytes(b'png')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
}
''')
            (work / 'Probe.hx').write_text('''
class Probe {
  static function eq(actual:String, wanted:String):Void
    if (actual != wanted) throw 'atlas mismatch: ' + actual + ' wanted ' + wanted;
  static function main():Void {
    var first = 'assets/images/custom_chars/first/char';
    var second = 'assets/images/custom_chars/second/char';
    var actual = 'assets/images/custom_chars/actual/char';
    eq(PsychCharacterImage.resolve(first + '.png', second), first);
    eq(PsychCharacterImage.resolve('opaque bitmap cache key', first.substr(0, first.length - 5)), first);
    eq(PsychCharacterImage.resolve('opaque bitmap cache key', second.substr(0, second.length - 5)), second);
    eq(PsychCharacterImage.resolve(actual + '.png', first.substr(0, first.length - 5)), actual);
    eq(PsychCharacterImage.resolve('assets/images/custom_chars/missing_xml/char.png', first.substr(0, first.length - 5)), '');
    eq(PsychCharacterImage.resolve('../actual/char.png', ''), '');
    eq(PsychCharacterImage.resolve(null, ''), '');
  }
}
''')
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
