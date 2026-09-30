"""Direct imported Freeplay launches use installed chart ownership safely."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FreeplayDirectEntryTest(unittest.TestCase):
    def test_owner_selection_fallback_and_empty_registry(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "FreeplayDirectEntry.hx").write_text(
                (ROOT / "source/FreeplayDirectEntry.hx").read_text())
            (base / "CompatScriptManifest.hx").write_text('''class CompatScriptManifest {
 public static function destinationKey(value:String):String
  return value == null ? '' : StringTools.trim(value).toLowerCase();
}''')
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var categories:Array<Dynamic> = [
   {name:'All', songs:[{name:'base'}, {name:'owned'}, {name:'other'}]},
   {name:'Imported', songs:[{name:'owned'}, {name:'other'}]}
  ];
  var owner = function(name:String):String
   return name == 'owned' ? 'assets/imported_mods/owned'
    : name == 'other' ? 'assets/imported_mods/other' : '';
  var selected = FreeplayDirectEntry.select(categories,
   'assets/imported_mods/owned', owner);
  if (selected.length != 1 || selected[0].name != 'owned')
   throw 'direct owner selection or duplicate filtering';
  var native = FreeplayDirectEntry.select(categories, '', owner);
  if (native.length != 3 || native[0].name != 'base')
   throw 'native category fallback';
  var unmatched = FreeplayDirectEntry.select(categories,
   'assets/imported_mods/missing', owner);
  if (unmatched.length != 0) throw 'unmatched owner leaked another category';
  if (FreeplayDirectEntry.select(categories,
   'assets/imported_mods/owned', null).length != 0)
   throw 'missing provenance leaked another category';
  if (FreeplayDirectEntry.select([], 'assets/imported_mods/owned', owner).length != 0)
   throw 'empty registry';
 }
}''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(base),
                 "-main", "Main", "--interp"], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_freeplay_state_uses_direct_entry_and_guards_empty_rows(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        self.assertIn("FreeplayDirectEntry.select(categories", source)
        self.assertIn("CodenameModRuntime.activeRoot()", source)
        self.assertIn("if (songs.length == 0)", source)
        empty_route = source.split("if (songs.length == 0)", 1)[1].split(
            "curDifficulty =", 1)[0]
        self.assertIn("ImportedFreeplayCaller.take(directOwnerRoot)", empty_route)
        self.assertIn("CodenameModRuntime.stateInit", empty_route)


if __name__ == "__main__":
    unittest.main()
