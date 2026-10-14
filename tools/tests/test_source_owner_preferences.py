"""Both Psych-family owner preference stores share one seeding and owner-root core."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


KEYS = r'''package flixel.input.keyboard;
enum abstract FlxKey(Int) from Int to Int {
 var NONE=-1; var A=65; var B=66; var D=68; var F=70; var J=74; var K=75; var R=82; var S=83; var W=87;
 var ZERO=48; var SEVEN=55; var EIGHT=56; var SPACE=32; var ENTER=13;
 var BACKSPACE=8; var ESCAPE=27; var PLUS=187; var MINUS=189;
 var UP=38; var DOWN=40; var LEFT=37; var RIGHT=39;
 var NUMPADPLUS=107; var NUMPADMINUS=109; var F3=114; var F5=116; var F6=117; var F11=122;
}'''

GAMEPAD = r'''package flixel.input.gamepad;
enum abstract FlxGamepadInputID(Int) from Int to Int {
 var NONE=-1; var A=0; var B=1; var X=2; var Y=3; var BACK=6; var START=7; var GUIDE=8;
 var DPAD_UP=11; var DPAD_DOWN=12; var DPAD_LEFT=13; var DPAD_RIGHT=14;
 var LEFT_STICK_DIGITAL_UP=34; var LEFT_STICK_DIGITAL_DOWN=35;
 var LEFT_STICK_DIGITAL_LEFT=36; var LEFT_STICK_DIGITAL_RIGHT=37;
}'''

FIXTURE = r'''import haxe.ds.StringMap;

class MemoryOwnerSave {
 public var values:Dynamic = {};
 public function new() {}
 public function getField(name:String):Dynamic return Reflect.field(values, name);
 public function setField(name:String, value:Dynamic):Void Reflect.setField(values, name, value);
 public function flush():Void {}
}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function accepts(build:Void->Void):Bool {
  try build() catch (_:Dynamic) return false;
  return true;
 }

 static function main():Void {
  var native:Dynamic = {
   downscroll:true, midscroll:true, showFPS:false, flashingLights:false, autoPause:false,
   antialiasing:false, gameplayShaders:false, zoomCamera:false, showNoteSplashes:false, offset:12.5
  };
  var before = haxe.Json.stringify(native);
  var nativeKeys:Array<Dynamic> = [[68], [70], [74], [75]];

  var psych = new PsychOwnerClientPrefs('assets/imported_mods/owner-a', new MemoryOwnerSave(), native);
  var nightmare = new NightmareVisionClientPrefs('assets/imported_mods/owner-a', new MemoryOwnerSave(), native);

  // The native "zoom camera" switch reaches both owners.
  check(psych.data.camZooms == false, 'psych owner ignored the native camera zoom option');
  check(nightmare.view.camZooms == false, 'nightmare owner ignored the native camera zoom option');

  // Splashes off: one owner has a switch, the other only has an alpha.
  check(nightmare.view.noteSplashes == false, 'nightmare owner ignored the native splash option');
  check(psych.data.splashAlpha == 0, 'psych owner kept visible splashes with native splashes off');
  check(psych.defaultData.splashAlpha == 0.6, 'native splash option leaked into the stable defaults');

  // Every other shared option still lands on each owner's own field name.
  check(psych.data.downScroll && psych.data.middleScroll && !psych.data.showFPS && !psych.data.flashing
   && !psych.data.autoPause && !psych.data.antialiasing && !psych.data.shaders && psych.data.noteOffset == 12.5,
   'psych seed table lost a shared option');
  check(nightmare.view.downScroll && nightmare.view.middleScroll && !nightmare.view.flashing
   && !nightmare.view.autoPause && !nightmare.view.globalAntialiasing && !nightmare.view.shaders
   && nightmare.view.noteOffset == 12.5, 'nightmare seed table lost a shared option');
  check(!Reflect.hasField(nightmare.view, 'showFPS'), 'a psych-only option was written into the nightmare view');

  // Options left on keep the donor defaults.
  var on:Dynamic = {zoomCamera:true, showNoteSplashes:true};
  var psychOn = new PsychOwnerClientPrefs('assets/imported_mods/owner-on', new MemoryOwnerSave(), on);
  var nightmareOn = new NightmareVisionClientPrefs('assets/imported_mods/owner-on', new MemoryOwnerSave(), on);
  check(psychOn.data.camZooms == true && psychOn.data.splashAlpha == 0.6, 'psych defaults changed with options on');
  check(nightmareOn.view.camZooms == true && nightmareOn.view.noteSplashes == true,
   'nightmare defaults changed with options on');

  // Native note keys go on the four lanes of both owners; reset defaults stay donor ones.
  psych.seedNativeNoteKeys(nativeKeys);
  nightmare.seedNativeNoteKeys(nativeKeys);
  var names = ['note_left', 'note_down', 'note_up', 'note_right'];
  for (index in 0...names.length) {
   check(psych.keyBinds.get(names[index]).join(',') == Std.string(nativeKeys[index][0]),
    'psych lane did not take the native key: ' + names[index]);
   check(nightmare.view.keyBinds.get(names[index]).join(',') == Std.string(nativeKeys[index][0]),
    'nightmare lane did not take the native key: ' + names[index]);
  }
  check(psych.defaultKeys.get('note_left').join(',') == '65,37', 'psych reset defaults were overwritten');
  check(nightmare.view.defaultKeys.get('note_left').join(',') == '65,37', 'nightmare reset defaults were overwritten');
  check(psych.keyBinds.get('accept').join(',') == '32,13' && nightmare.view.keyBinds.get('accept').join(',') == '32,13',
   'seeding note keys touched a menu bind');
  psych.keyBinds.get('note_left').push(1);
  check(nativeKeys[0].length == 1, 'owner binds alias the native key arrays');
  psych.seedNativeNoteKeys([null, [70]]);
  check(psych.keyBinds.get('note_left').length == 2 && psych.keyBinds.get('note_up').join(',') == '74',
   'a missing native lane cleared an owner bind');

  // A bind the owner saved earlier beats the seeded native key.
  var psychSave = new MemoryOwnerSave();
  psychSave.values.psychClientPrefs = {version:1, values:{keyBinds:{note_left:[90]}}};
  var savedPsych = new PsychOwnerClientPrefs('assets/imported_mods/owner-b', psychSave, native);
  savedPsych.seedNativeNoteKeys(nativeKeys);
  savedPsych.loadStoredPrefs();
  check(savedPsych.keyBinds.get('note_left').join(',') == '90' && savedPsych.keyBinds.get('note_down').join(',') == '70',
   'psych saved bind did not overlay the seeded keys');
  var nightmareSave = new MemoryOwnerSave();
  nightmareSave.values.nightmareVisionClientPrefs = {version:1, values:{keyBinds:{note_left:[90, -1]}, camZooms:true}};
  var savedNightmare = new NightmareVisionClientPrefs('assets/imported_mods/owner-b', nightmareSave, native);
  savedNightmare.seedNativeNoteKeys(nativeKeys);
  savedNightmare.load();
  check(savedNightmare.view.keyBinds.get('note_left').join(',') == '90,-1'
   && savedNightmare.view.keyBinds.get('note_down').join(',') == '70',
   'nightmare saved bind did not overlay the seeded keys');
  check(savedNightmare.view.camZooms == true, 'a saved owner preference did not beat the native seed');

  // Both owners accept and refuse exactly the same roots.
  var roots = ['assets/imported_mods/owner-a', 'assets/imported_mods/owner-a/', 'assets\\imported_mods\\owner-a',
   'assets/imported_mods//owner-a', 'assets/imported_mods/', 'assets/imported_mods', 'assets/imported_mods/a/../b',
   'assets/imported_mods/a/..', 'assets/imported_mods/a/./b', 'assets/imported_mods/a/.', 'assets/other/owner-a', ''];
  var expected = [true, true, true, true, false, false, false, false, false, false, false, false];
  for (index in 0...roots.length) {
   var root = roots[index];
   var psychOk = accepts(function() new PsychOwnerClientPrefs(root, new MemoryOwnerSave()));
   var nightmareOk = accepts(function() new NightmareVisionClientPrefs(root, new MemoryOwnerSave()));
   check(psychOk == expected[index] && nightmareOk == expected[index],
    'owner root "' + root + '": psych ' + psychOk + ', nightmare ' + nightmareOk + ', expected ' + expected[index]);
  }
  check(nightmare.canReuseFor('assets/imported_mods/owner-a/') && psych.canReuseFor('assets/imported_mods/owner-a/'),
   'a trailing slash changed the owner key');
  check(accepts(function() new NightmareVisionClientPrefs(null, new MemoryOwnerSave())) == false
   && accepts(function() new PsychOwnerClientPrefs('assets/imported_mods/x', null)) == false
   && accepts(function() new NightmareVisionClientPrefs('assets/imported_mods/x', {})) == false,
   'a missing root or unusable owner save was accepted');

  // Owner writes stay local.
  psych.data.camZooms = true; psych.data.downScroll = false; psych.data.noteOffset = 3;
  nightmare.view.camZooms = true; nightmare.view.noteSplashes = true; nightmare.view.noteOffset = 4;
  psych.saveSettings(); nightmare.flush();
  check(haxe.Json.stringify(native) == before, 'an owner write changed the native options');
  check(nativeKeys[0].join(',') == '68', 'an owner write changed the native keys');

  // The shared value helpers copy deeply.
  var inner:Array<Dynamic> = [2];
  var list:Array<Dynamic> = [1, inner];
  var source:Dynamic = {list:list, map:['a' => {b:1}]};
  var copy:Dynamic = SourceOwnerPreferences.cloneValue(source);
  copy.list[1][0] = 9; copy.map.get('a').b = 9;
  check(source.list[1][0] == 2 && source.map.get('a').b == 1, 'cloneValue shared a nested value');
  check(Std.isOfType(copy.map, StringMap), 'cloneValue lost a string map');
 }
}'''


class SourceOwnerPreferencesTest(unittest.TestCase):
    def test_owner_stores_seed_native_options_and_keys_the_same_way(self):
        with tempfile.TemporaryDirectory(prefix='source-owner-prefs-', dir=ROOT / 'tmp') as scratch:
            for relative, text in (('flixel/input/keyboard/FlxKey.hx', KEYS),
                                   ('flixel/input/gamepad/FlxGamepadInputID.hx', GAMEPAD),
                                   ('Main.hx', FIXTURE)):
                target = Path(scratch) / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', scratch, '--run', 'Main'],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
