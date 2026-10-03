"""Owner-local Nightmare Vision ClientPrefs values and persistence."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionClientPrefsTest(unittest.TestCase):
    def test_owner_local_defaults_load_flush_and_script_access(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(r'''
import crowplexus.hscript.Parser;
import haxe.ds.StringMap;

class MemoryOwnerSave {
 public var values:Dynamic = {};
 public var flushes:Int = 0;
 public function new() {}
 public function getField(name:String):Dynamic return Reflect.field(values, name);
 public function setField(name:String, value:Dynamic):Dynamic {
  Reflect.setField(values, name, haxe.Json.parse(haxe.Json.stringify(value)));
  return value;
 }
 public function flush():Void flushes++;
}

class Main {
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic, name:String):Void
  if (actual != expected) fail(name + ': expected ' + expected + ', got ' + actual);
 static function truth(value:Bool, name:String):Void if (!value) fail(name);
 static function main() {
  var nativeOptions:Dynamic = {
   autoPause:false, antialiasing:false, gameplayShaders:false,
   flashingLights:false, downscroll:true, midscroll:true,
   showNoteSplashes:false, offset:47.5, fpsCap:144
  };
  var save = new MemoryOwnerSave();
  var prefs = new NightmareVisionClientPrefs('assets/imported_mods/author-mod', save, nativeOptions);
  eq(prefs.view.autoPause, false, 'native autoPause seed');
  eq(prefs.view.globalAntialiasing, false, 'native antialiasing seed');
  eq(prefs.view.shaders, false, 'native shader seed');
  eq(prefs.view.flashing, false, 'native flashing seed');
  eq(prefs.view.downScroll, true, 'native downscroll seed');
  eq(prefs.view.middleScroll, true, 'native middlescroll seed');
  eq(prefs.view.toggleSplashScreen, true, 'splash screen must keep source default');
  eq(prefs.view.noteSplashType, 'Both', 'note splash setting is not title splash');
  eq(prefs.view.lowQuality, false, 'unsupported quality option keeps source default');
  eq(prefs.view.timeBarType, 'Time Left', 'unsupported time bar option keeps source default');
  eq(prefs.view.hideHud, false, 'unsupported hide HUD option keeps source default');
  eq(prefs.view.noteOffset, 0, 'float native offset is not coerced to source integer');
  eq(prefs.view.framerate, 60, 'fps option does not rewrite source framerate');
  eq(prefs.getGameplaySetting('healthgain', 9), 1.0, 'source gameplay default');
  eq(prefs.getGameplaySetting('absent', false), false, 'missing gameplay default');
  truth(Std.isOfType(prefs.view.gameplaySettings, StringMap), 'gameplaySettings must be a StringMap');
  truth(Std.isOfType(prefs.view.chartPresets, StringMap), 'chartPresets must be a StringMap');

  // A source-style import can read and write direct fields and map values.
  var parser = new Parser(); parser.allowTypes = true; parser.allowMetadata = true;
  var interp = new NightmareVisionScriptInterp();
  interp.bindImport('funkin.data.ClientPrefs', prefs.view);
  interp.execute(parser.parseString('import funkin.data.ClientPrefs;\n'
   + 'ClientPrefs.downScroll = false;\n'
   + 'ClientPrefs.gameplaySettings.set("botplay", true);\n'
   + 'ClientPrefs.showRatings = false;\n'
   + 'ClientPrefs.flush();'));
  eq(prefs.view.downScroll, false, 'script assignment is owner-local');
  eq(prefs.getGameplaySetting('botplay', false), true, 'script map write');
  eq(nativeOptions.downscroll, true, 'owner write did not mutate native downscroll');
  eq(nativeOptions.showNoteSplashes, false, 'unrelated native setting untouched');
  eq(save.flushes, 1, 'owner record flushed');
  var saved = Reflect.field(save.values, NightmareVisionClientPrefs.SAVE_FIELD);
  eq(Reflect.field(saved, 'version'), NightmareVisionClientPrefs.VERSION, 'record version');
  truth(Reflect.hasField(Reflect.field(saved, 'values'), 'keyBinds'), 'manual key bind flush kept owner-local');

  // JSON object maps are hydrated as StringMaps; false and zero overlay defaults.
  var loadedSave = new MemoryOwnerSave();
  Reflect.setField(loadedSave.values, NightmareVisionClientPrefs.SAVE_FIELD, {
   version:1,
   values:{
    flashing:false, noteOffset:0, healthBarAlpha:0.0, showRatings:false, fpsDisplayType:null,
    gameplaySettings:{healthgain:0.0, botplay:false, ownerFlag:'loaded'},
    comboOffset:[0,1,2,3], keyBinds:{custom_action:[65,-1]},
    chartPresets:{Loaded:'owner'}
   }
  });
  var loaded = new NightmareVisionClientPrefs('assets/imported_mods/author-mod', loadedSave, nativeOptions);
  loaded.load();
  eq(loaded.view.flashing, false, 'saved false value');
  eq(loaded.view.noteOffset, 0, 'saved zero value');
  eq(loaded.view.healthBarAlpha, 0.0, 'saved float zero');
  eq(loaded.view.showRatings, false, 'saved visual boolean');
  eq(loaded.view.fpsDisplayType, null, 'saved null value');
  truth(Std.isOfType(loaded.view.gameplaySettings, StringMap), 'loaded gameplay map remains StringMap');
  eq(loaded.getGameplaySetting('healthgain', 9), 0.0, 'loaded map zero');
  eq(loaded.getGameplaySetting('botplay', true), false, 'loaded map false');
  eq(loaded.getGameplaySetting('ownerFlag', null), 'loaded', 'loaded map extension');
  eq(loaded.getGameplaySetting('scrollspeed', null), 1.0, 'map load merges into source defaults');
  eq(loaded.view.comboOffset.join(','), '0,1,2,3', 'nested array loaded');
  truth(Std.isOfType(loaded.view.keyBinds, StringMap), 'loaded key map remains StringMap');
  truth(loaded.view.keyBinds.exists('note_left'), 'key map load preserves source defaults');
  eq(loaded.view.keyBinds.get('custom_action')[0], 65, 'owner custom bind loaded');
  truth(loaded.view.chartPresets.exists('Default') && loaded.view.chartPresets.exists('Loaded'),
   'chart preset map load merges defaults');

  // Mutable arrays/maps and saves are detached across owner instances.
  var otherSave = new MemoryOwnerSave();
  var other = new NightmareVisionClientPrefs('assets/imported_mods/other-mod', otherSave);
  loaded.view.comboOffset[0] = 99;
  loaded.view.gameplaySettings.set('healthgain', 3.0);
  loaded.flush();
  var persisted = Reflect.field(loadedSave.values, NightmareVisionClientPrefs.SAVE_FIELD);
  var persistedValues = Reflect.field(persisted, 'values');
  eq(Reflect.field(persistedValues, 'comboOffset')[0], 99, 'flush snapshots nested arrays');
  eq(Reflect.field(Reflect.field(persistedValues, 'gameplaySettings'), 'healthgain'), 3.0,
   'flush serializes StringMap as a JSON object');
  eq(other.view.gameplaySettings.get('healthgain'), 1.0, 'different owner has independent defaults');
  truth(!other.canReuseFor('assets/imported_mods/author-mod'), 'owner identity mismatch');
  truth(loaded.canReuseFor('assets/imported_mods/author-mod'), 'same owner can reuse preference view');

  // Source helpers that are local data operations work; global controls actions fail clearly.
  loaded.view.loadDefaultKeys();
  truth(loaded.view.defaultKeys.exists('note_left'), 'loadDefaultKeys local snapshot');
  var copied:Array<Dynamic> = loaded.view.copyKey([65, -1, 66, -1]);
  eq(copied.join(','), '65,66', 'copyKey removes NONE');
  var custom:Array<Dynamic> = [70]; loaded.view.addCustomKey('custom_local', custom);
  eq(custom.length, 2, 'addCustomKey pads source array in place');
  truth(loaded.view.keyBinds.exists('custom_local'), 'addCustomKey modifies owner-local map');
  var threw = false;
  try loaded.view.reloadControls() catch (error:Dynamic) {
   threw = Std.string(error).indexOf('[nmv-client-prefs-unsupported] reloadControls') >= 0;
  }
  truth(threw, 'reloadControls must report unsupported host-wide mutation');

  loaded.release();
  eq(loaded.view, null, 'release clears preference view');
  truth(!loaded.canReuseFor('assets/imported_mods/author-mod'), 'released owner view cannot be reused');
  threw = false;
  try loaded.load() catch (_:Dynamic) threw = true;
  truth(threw, 'released view rejects calls');
  threw = false;
  try new NightmareVisionClientPrefs('assets/imported_mods/../outside', new MemoryOwnerSave())
   catch (_:Dynamic) threw = true;
  truth(threw, 'owner traversal refused');
 }
}
''', newline='\n')
            for defines in ([], ['-D', 'hscriptPos']):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                         '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'),
                         '-cp', str(ROOT / '.haxelib/flixel/6,1,2'), '-cp', str(work)]
                        + defines + ['--main', 'Main', '--interp'], cwd=work,
                        capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
