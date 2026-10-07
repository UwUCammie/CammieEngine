"""Direct imported Freeplay launches use installed chart ownership safely."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FreeplayDirectEntryTest(unittest.TestCase):
    def test_owner_selection_fallback_and_empty_registry(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "FreeplayDirectEntry.hx").write_text(
                (ROOT / "source/FreeplayDirectEntry.hx").read_text(), newline='\n')
            (base / "FreeplaySongOrder.hx").write_text(
                (ROOT / "source/FreeplaySongOrder.hx").read_text(), newline='\n')
            (base / "FreeplaySourceDisplay.hx").write_text('''class FreeplaySourceDisplay {
 public static function resolve(display:String, source:String, name:String, provenance:Dynamic):Dynamic
  return {source:'', title:display};
}''', newline='\n')
            (base / "CompatScriptManifest.hx").write_text('''class CompatScriptManifest {
 public static function destinationKey(value:String):String
  return value == null ? '' : StringTools.trim(value).toLowerCase();
}''', newline='\n')
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
  var preserved = FreeplayDirectEntry.select(categories, '', owner, 'Imported');
  if (preserved.length != 2 || preserved[0].name != 'owned')
   throw 'preferred Imported category was not preserved';
  var completedRegistry:Array<Dynamic> = [
   {name:'Base Game', songs:[{name:'base'}]},
   {name:'Imported', songs:[{name:'committed-replacement'}]}
  ];
  var currentCategory = 'Imported';
  var replacedPlaceholder = FreeplayDirectEntry.select(completedRegistry, '', owner, currentCategory);
  if (replacedPlaceholder.length != 1 || replacedPlaceholder[0].name != 'committed-replacement'
   || currentCategory != 'Imported')
   throw 'committing a placeholder jumped away from the selected category';
  var emptyPreferred = FreeplayDirectEntry.select([
   {name:'Base Game', songs:[{name:'base'}]}, {name:'Imported', songs:[]}
  ], '', owner, 'Imported');
  if (emptyPreferred.length != 0)
   throw 'an empty selected category fell through to a different category';
  var allRegistry:Array<Dynamic> = [
   {name:'All', songs:[{name:'Random-Song'}]},
   {name:'Base Game', songs:['base']},
   {name:'Imported', songs:[{name:'owned'}]}
  ];
  var preservedAll = FreeplayDirectEntry.select(allRegistry, '', owner, 'All');
  if (preservedAll.length != 3 || preservedAll[0].name != 'Random-Song')
   throw 'virtual All category lost its random row or other categories';
  var preservedAllNames = [for (song in preservedAll) song.name];
  if (preservedAllNames.indexOf('base') < 0 || preservedAllNames.indexOf('owned') < 0)
   throw 'virtual All category did not rebuild the aggregated song list';
  var scopedPreferred = FreeplayDirectEntry.select(categories,
   'assets/imported_mods/owned', owner, 'Base Game');
  if (scopedPreferred.length != 1 || scopedPreferred[0].name != 'owned')
   throw 'preferred category changed explicit owner-scoped selection';
  var unmatched = FreeplayDirectEntry.select(categories,
   'assets/imported_mods/missing', owner);
  if (unmatched.length != 0) throw 'unmatched owner leaked another category';
  if (FreeplayDirectEntry.select(categories,
   'assets/imported_mods/owned', null).length != 0)
   throw 'missing provenance leaked another category';
  if (FreeplayDirectEntry.select([], 'assets/imported_mods/owned', owner).length != 0)
   throw 'empty registry';
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base),
                 "-main", "Main", "--interp"], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_freeplay_state_uses_direct_entry_and_guards_empty_rows(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        self.assertIn("FreeplayDirectEntry.select(categories", source)
        self.assertIn("CodenameModRuntime.activeRoot()", source)
        self.assertIn("return ImportedModDiscovery.ownerForSong(name, 'assets/data'), curCategory);", source)
        self.assertIn("if (preferredCategory == 'All')", (ROOT / "source/FreeplayDirectEntry.hx").read_text())
        self.assertIn("if (songs.length == 0)", source)
        empty_route = source.split("if (songs.length == 0)", 1)[1].split(
            "curDifficulty =", 1)[0]
        self.assertIn("ImportedFreeplayCaller.take(directOwnerRoot)", empty_route)
        self.assertIn("CodenameModRuntime.stateInit", empty_route)
        generation_change = source.split('if (importRefreshGeneration != ImportRefreshManager.generation)', 1)[1].split('\n\t\t#end', 1)[0]
        self.assertIn('currentSongList = [];', generation_change)
        self.assertNotIn('curCategory =', generation_change)


if __name__ == "__main__":
    unittest.main()
