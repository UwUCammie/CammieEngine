"""Psych setTextFont resolves through Paths.font and import ownership."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychFontPathTest(unittest.TestCase):
    def test_selected_font_and_native_fallback(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('var selectedRoot = CompatScriptManifest.selectedRoot(getCompatScriptManifest());', play)
        self.assertIn('var path = PsychFontPath.resolve(font, selectedRoot);', play)
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / 'PsychFontPath.hx').write_text(
                (ROOT / 'source/PsychFontPath.hx').read_text())
            for root in ('first', 'second'):
                (work / f'assets/imported_mods/{root}/fonts').mkdir(parents=True)
            (work / 'assets/imported_mods/first/fonts/Custom.ttf').write_bytes(b'first')
            (work / 'assets/imported_mods/second/fonts/Custom.ttf').write_bytes(b'second')
            (work / 'assets/fonts').mkdir(parents=True)
            (work / 'assets/fonts/Native.ttf').write_bytes(b'native')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
}
''')
            (work / 'Probe.hx').write_text('''
class Probe {
  static function eq(actual:String, wanted:String):Void
    if (actual != wanted) throw 'font mismatch: ' + actual + ' wanted ' + wanted;
  static function main():Void {
    eq(PsychFontPath.resolve('Custom.ttf', 'assets/imported_mods/first'),
      'assets/imported_mods/first/fonts/Custom.ttf');
    eq(PsychFontPath.resolve('fonts/Custom.ttf', 'assets/imported_mods/second'),
      'assets/imported_mods/second/fonts/Custom.ttf');
    eq(PsychFontPath.resolve('Native.ttf', 'assets/imported_mods/first'),
      'assets/fonts/Native.ttf');
    eq(PsychFontPath.resolve('assets/fonts/Native.ttf', ''), 'assets/fonts/Native.ttf');
    eq(PsychFontPath.resolve('Missing.ttf', ''), 'assets/fonts/Missing.ttf');
    eq(PsychFontPath.resolve('../escape.ttf', ''), null);
    eq(PsychFontPath.resolve('/tmp/out.ttf', ''), null);
    eq(PsychFontPath.resolve(null, ''), null);
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
