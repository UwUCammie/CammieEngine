"""Bounded Codename font/data dependency preservation without a media-tree scan."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameDataDependenciesTest(unittest.TestCase):
    def test_concatenated_source_image_normalizes_adjacent_separators(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            base = Path(work)
            (base / 'Main.hx').write_text('''class Main {
 static function main() {
  var source = "var bg_string:String = 'stages/tricky/'; function create() { Paths.image(bg_string + '/tricky_fog'); Paths.image('/absolute'); }";
  var refs = HxcAssetPlanner.literalReferences(source, true);
  var keys = [for (ref in refs) if (ref.kind == 'image') ref.key];
  if (keys.indexOf('stages/tricky/tricky_fog') < 0) throw Std.string(keys);
  if (keys.indexOf('/absolute') < 0) throw 'absolute key was hidden from safety check';
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(base), '--run', 'Main'], cwd=ROOT,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_literal_data_opt_in_preserves_existing_planner_contract(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            base = Path(work)
            (base / 'Main.hx').write_text('''class Main {
 static function main() {
  var source = 'Paths.font("face.ttf"); Paths.json("events/timing"); Paths.xml("layout"); Paths.txt("credits"); Paths.font("dynamic/" + name);';
  if (HxcAssetPlanner.literalReferences(source).length != 0) throw 'legacy planning changed';
  var refs = HxcAssetPlanner.literalReferences(source, true);
  if (refs.length != 4) throw Std.string(refs);
  var seen:Map<String,String> = new Map();
  for (ref in refs) seen.set(ref.kind,ref.key);
  if (seen.get('font') != 'face.ttf' || seen.get('json') != 'events/timing'
      || seen.get('xml') != 'layout' || seen.get('txt') != 'credits') throw 'literal paths';
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(base), '--run', 'Main'], cwd=ROOT,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_direct_owner_font_paths_in_text_format_calls_are_planned(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            base = Path(work)
            (base / 'Main.hx').write_text(r'''class Main {
 static function main() {
  var source = "new FlxText().setFormat('fonts/Technology.ttf', 70); menu.font = './fonts/851MkPOP.ttf';";
  var refs = HxcAssetPlanner.literalReferences(source, true);
  var fonts = [for (ref in refs) if (ref.kind == 'font') ref.key];
  if (fonts.length != 2 || fonts.indexOf('Technology.ttf') < 0
      || fonts.indexOf('851MkPOP.ttf') < 0) throw Std.string(fonts);
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(base), '--run', 'Main'], cwd=ROOT,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
