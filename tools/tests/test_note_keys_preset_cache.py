"""Exercise the production note-preset cache with isolated assets."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NoteKeysPresetCacheTest(unittest.TestCase):
    def test_cache_is_bounded_mutation_isolated_and_import_aware(self):
        source = (ROOT / "source/NoteKeys.hx").read_text()
        play_state = (ROOT / "source/PlayState.hx").read_text()
        module_functions = (ROOT / "source/ModuleFunctions.hx").read_text()

        create_start = play_state.index("\toverride public function create() {")
        create_cache_reset = play_state.index("NoteKeys.clearPresetCache();", create_start)
        first_create_work = play_state.index("Sys.println('[dims]", create_start)
        self.assertLess(create_cache_reset, first_create_work)

        import_start = module_functions.index("public static function completeImportOnMainThread(")
        import_end = module_functions.index("\n\t\tpublic static function reportImportProgress", import_start)
        self.assertIn("NoteKeys.clearPresetCache();", module_functions[import_start:import_end])

        fixture = r'''class Note {
 public static var NOTE_AMOUNT:Int = 4;
}
class FNFAssets {
 public static var files:Map<String,String> = new Map();
 public static var existsCalls:Map<String,Int> = new Map();
 public static var readCalls:Map<String,Int> = new Map();
 static function increment(calls:Map<String,Int>, path:String):Void
  calls.set(path, calls.exists(path) ? calls.get(path) + 1 : 1);
 public static function exists(path:String):Bool {
  increment(existsCalls, path);
  return files.exists(path);
 }
 public static function getText(path:String):String {
  increment(readCalls, path);
  if (!files.exists(path)) throw 'missing asset: ' + path;
  return files.get(path);
 }
 public static function count(calls:Map<String,Int>, path:String):Int
  return calls.exists(path) ? calls.get(path) : 0;
}
class CoolUtil {
 public static function parseJson(value:String):Dynamic return haxe.Json.parse(value);
}
'''
        main = r'''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function note(prefix:String, lane:String):Dynamic return {
  note: prefix + ' ' + lane, splashes: [prefix + ' splash'], idle: lane,
  pressed: lane + ' press', confirm: lane + ' confirm', sing: 'sing' + lane
 };
 static function preset(prefix:String):String return haxe.Json.stringify({
  definitions: {
   left: note(prefix, 'left'), down: note(prefix, 'down'),
   up: note(prefix, 'up'), right: note(prefix, 'right')
  },
  key4: ['left', 'down', 'up', 'right'],
  key5: ['left', 'down', 'up', 'up', 'right']
 });
 static function path(pack:String):String
  return 'assets/images/custom_ui/ui_packs/' + pack + '/multiNotePresets.json';
 static function main():Void {
  var defaultPath = 'assets/data/defaultNotePresets.json';
  FNFAssets.files.set(defaultPath, preset('default'));
  FNFAssets.files.set(path('normal'), preset('normal'));
  NoteKeys.clearPresetCache();

  var first = new NoteKeys('normal');
  var second = new NoteKeys('normal');
  check(FNFAssets.count(FNFAssets.existsCalls, path('normal')) == 1,
   'same preset path was probed for every instance');
  check(FNFAssets.count(FNFAssets.readCalls, path('normal')) == 1,
   'same preset JSON was reread for every instance');
  check(first.getNote(0) == 'normal left' && second.getNote(0) == 'normal left',
   'cached preset changed selected animation data');

  first.preset.definitions.left.note = 'mutated animation';
  first.preset.definitions.left.splashes[0] = 'mutated splash';
  first.preset.key4[0] = 'right';
  check(second.preset.definitions.left.note == 'normal left',
   'one note instance mutated another instance preset');
  check(second.preset.definitions.left.splashes[0] == 'normal splash',
   'one note instance mutated another instance nested array');
  check(second.preset.key4[0] == 'left' && second.getNote(0) == 'normal left',
   'one note instance mutated another instance key table');

  Note.NOTE_AMOUNT = 5;
  first.newKey('normal');
  check(first.keyAmount == 5 && first.getNote(4) == 'normal right',
   'cached template did not resolve the active key amount');
  check(FNFAssets.count(FNFAssets.readCalls, path('normal')) == 1,
   'changing key amount reparsed the same preset');

  Note.NOTE_AMOUNT = 4;
  var fallback = new NoteKeys('imported');
  check(fallback.getNote(0) == 'default left', 'missing pack did not use the default preset');
  var importedPath = path('imported');
  FNFAssets.files.set(importedPath, preset('imported'));
  NoteKeys.clearPresetCache(); // same lifecycle handoff used after a song/import
  var imported = new NoteKeys('imported');
  check(imported.getNote(0) == 'imported left',
   'a preset created by an import stayed hidden behind a cached miss');
  check(FNFAssets.count(FNFAssets.readCalls, importedPath) == 1,
   'imported preset was not loaded once after cache invalidation');

  var pixelPath = StringTools.replace(path('normal'), '.json', '-pixel.json');
  FNFAssets.files.set(pixelPath, preset('pixel'));
  NoteKeys.clearPresetCache();
  var pixel = new NoteKeys('normal', true);
  check(pixel.getNote(0) == 'pixel left', 'pixel preset path was not selected');
  check(FNFAssets.count(FNFAssets.readCalls, pixelPath) == 1,
   'pixel preset did not use the parsed cache');

  FNFAssets.files.set(path('broken'), '{ invalid json');
  NoteKeys.clearPresetCache();
  var parseFailed = false;
  try new NoteKeys('broken') catch (_:Dynamic) parseFailed = true;
  check(parseFailed, 'invalid preset parsing error was hidden by the cache');
 }
}
'''

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            (base / "NoteKeys.hx").write_text(source)
            (base / "Main.hx").write_text(main)
            # Haxe resolves same-package secondary types by module name, so
            # provide the three tiny test doubles in their own source modules.
            (base / "Note.hx").write_text(fixture[fixture.index("class Note {"):fixture.index("class FNFAssets {")])
            (base / "FNFAssets.hx").write_text(fixture[fixture.index("class FNFAssets {"):fixture.index("class CoolUtil {")])
            (base / "CoolUtil.hx").write_text(fixture[fixture.index("class CoolUtil {"):])
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
