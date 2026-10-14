"""Refreshing one import keeps other imports' keyless rows in a shared registry list."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
TJSON = ROOT / '.haxelib/tjson/1,4,0'

MAIN = r'''class Main {
 static function row(provenance:String, order:Int):String
  return '{"engine":"V-Slice","mod":"","operation":"_merge","kind":"jsonPatch","order":' + order
   + ',"relativePath":"' + provenance + '","targetPath":"' + provenance + '","provenance":"_merge/' + provenance
   + '","reason":"missing-merge-base","payload":"[]"}';
 static function list(rows:Array<String>):String return '{"version":1,"roots":[],"overlays":[' + rows.join(',') + ']}';
 static function provenances(text:String):Array<String> {
  var data:Dynamic = haxe.Json.parse(text);
  return [for (entry in (cast data.overlays:Array<Dynamic>)) entry.provenance];
 }
 static function main() {
  var first = row('data/a.json', 0);
  var owned = row('data/owned.json', 1);
  var other = row('data/other.json', 2);
  var before = list([first]);
  var previous = list([first, owned]);            // this package's earlier output
  var live = list([first, owned, other]);         // another package imported later
  var prepared = ImportRegistryRefresh.prepare(before, previous, live);
  if (prepared.conflicts.length != 0) throw 'prepare conflicted: ' + prepared.conflicts;
  if (provenances(prepared.text).join(',') != '_merge/data/a.json,_merge/data/other.json')
   throw 'prepare must drop only the owned row: ' + prepared.text;
  var seed = ImportRegistryRefresh.regenerationSeed(before, previous, live);
  if (seed.conflicts.length != 0) throw 'seed conflicted: ' + seed.conflicts;
  // The converter re-adds this package's row after the rows it found.
  var generated = list([first, other, row('data/owned.json', 3)]);
  var merged = ImportRegistryRefresh.merge(previous, generated, live);
  if (merged.conflicts.length != 0) throw 'merge conflicted: ' + merged.conflicts;
  var kept = provenances(merged.text);
  if (kept.indexOf('_merge/data/other.json') < 0 || kept.indexOf('_merge/data/owned.json') < 0 || kept.length != 3)
   throw 'merge lost or duplicated rows: ' + merged.text;
  var validated = ImportRegistryRefresh.prepare(prepared.text, generated, merged.text);
  if (validated.conflicts.length != 0) throw 'validation conflicted: ' + validated.conflicts;
  // Two identical rows cannot say which one is owned, so that stays a conflict.
  var twice = ImportRegistryRefresh.regenerationSeed(before, list([first, owned, owned]), list([first, owned, owned, other]));
  if (twice.conflicts.length == 0) throw 'duplicate rows must not be guessed';
 }
}
'''


class ImportRegistryValueRecordsTest(unittest.TestCase):
    def test_keyless_rows_from_other_imports_survive_a_refresh(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(TJSON), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
