"""The generated All category groups chart versions by title."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'


class FreeplaySongOrderTest(unittest.TestCase):
    def test_base_and_imported_versions_are_adjacent(self):
        if not HAXE.is_file():
            self.skipTest('portable Haxe interpreter is unavailable')
        fixture = '''import FreeplaySongOrder.FreeplaySongEntry;
class FreeplaySongOrderFixture {
 static function main():Void {
  var rows:Array<FreeplaySongEntry> = [
   {song:{name:"Tutorial", week:0}, base:true, order:0},
   {song:{name:"Bopeebo"}, base:true, order:1},
   {song:{name:"tutorial--codename-engine-d97d25757d",
    display:"Tutorial · D-Sides REDUX · Codename Engine"}, base:false, order:2},
   {song:{name:"custom", display:"Title · With Separator"}, base:false, order:3},
   {song:{name:"tutorial--psych-engine-d942d5457b",
    display:"Tutorial · Friday Night Funkin': Psych Engine"}, base:false, order:4},
   {song:{name:"title-mod", display:"Title · With Separator · Pack",
    sourceLabel:"Pack"}, base:false, order:5}
  ];
  var sorted = FreeplaySongOrder.sort(rows);
  var names = [for (row in sorted) Std.string(Reflect.field(row, "name"))];
  var expected = ["Bopeebo", "custom", "title-mod", "Tutorial",
   "tutorial--codename-engine-d97d25757d", "tutorial--psych-engine-d942d5457b"];
  if (names.join("|") != expected.join("|"))
   throw names.join("|");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'FreeplaySongOrderFixture.hx').write_text(fixture)
            result = subprocess.run(
                [str(HAXE), '-cp', folder, '-cp', str(ROOT / 'source'),
                 '--run', 'FreeplaySongOrderFixture'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OK', result.stdout + result.stderr)

    def test_only_generated_all_category_uses_sort(self):
        source = (ROOT / 'source/CategoryState.hx').read_text()
        self.assertIn("if (categories[i] == 'All')", source)
        self.assertIn("if (c == i || categories[c] == 'All')", source)
        self.assertIn('FreeplaySongOrder.sort(allEntries)', source)
        self.assertIn("base:categories[c] == 'Base Game'", source)
        smoke = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text()
        self.assertIn("var allCategories = wanted == '' || wanted == 'All'", smoke)
        self.assertIn('FreeplaySongOrder.sort(allEntries)', smoke)

    def test_older_import_groups_by_receipted_title(self):
        if not HAXE.is_file():
            self.skipTest('portable Haxe interpreter is unavailable')
        fixture = '''import FreeplaySongOrder.FreeplaySongEntry;
class LegacyFreeplayOrderFixture {
 static function main():Void {
  var entries:Array<FreeplaySongEntry> = [
   {song:{name:"A Lovely Title"}, base:true, order:0},
   {song:{name:"f-id--codename-engine-d97d25757d",
    display:"A Lovely Title · Pack · Codename Engine"}, base:false, order:1},
   {song:{name:"Another Song"}, base:true, order:2}
  ];
  var sorted = FreeplaySongOrder.sort(entries);
  var names = [for (row in sorted) Std.string(Reflect.field(row, "name"))];
  if (names.join("|") != "A Lovely Title|f-id--codename-engine-d97d25757d|Another Song")
   throw names.join("|");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            directory = Path(folder)
            owner = directory / 'assets/data/f-id--codename-engine-d97d25757d'
            owner.mkdir(parents=True)
            (owner / 'importProvenance.json').write_text(json.dumps({
                'destinationFolder': owner.name,
                'display': 'A Lovely Title · Pack · Codename Engine',
                'modName': 'Pack',
                'sourceEngine': 'Codename Engine',
            }))
            (directory / 'LegacyFreeplayOrderFixture.hx').write_text(fixture)
            result = subprocess.run(
                [str(HAXE), '-cp', folder, '-cp', str(ROOT / 'source'),
                 '--run', 'LegacyFreeplayOrderFixture'],
                cwd=directory, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OK', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
