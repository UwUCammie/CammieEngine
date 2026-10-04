"""Exercise the owner-local mutable Psych 1.0.4 preferences adapter."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


KEYS = r'''package flixel.input.keyboard;
enum abstract FlxKey(Int) from Int to Int {
 var NONE=-1; var A=65; var B=66; var D=68; var R=82; var S=83; var W=87;
 var ZERO=48; var SEVEN=55; var EIGHT=56; var SPACE=32; var ENTER=13;
 var BACKSPACE=8; var ESCAPE=27; var PLUS=187; var MINUS=189;
 var UP=38; var DOWN=40; var LEFT=37; var RIGHT=39;
 var NUMPADPLUS=107; var NUMPADMINUS=109;
}'''

GAMEPAD = r'''package flixel.input.gamepad;
enum abstract FlxGamepadInputID(Int) from Int to Int {
 var NONE=-1; var A=0; var B=1; var X=2; var Y=3; var BACK=6; var START=7;
 var DPAD_UP=11; var DPAD_DOWN=12; var DPAD_LEFT=13; var DPAD_RIGHT=14;
 var LEFT_STICK_DIGITAL_UP=34; var LEFT_STICK_DIGITAL_DOWN=35;
 var LEFT_STICK_DIGITAL_LEFT=36; var LEFT_STICK_DIGITAL_RIGHT=37;
}'''


FIXTURE = r'''import haxe.ds.StringMap;
import flixel.FlxG;

class MemoryOwnerSave {
 public var value:Dynamic;
 public var flushes:Int = 0;
 public function new(?value:Dynamic) this.value = value;
 public function getField(name:String):Dynamic return name == 'psychClientPrefs' ? value : null;
 public function setField(name:String, value:Dynamic):Void if (name == 'psychClientPrefs') this.value = value;
 public function flush():Void flushes++;
}

class PlayState {
 public static var instance:PlayState;
 public var psychClientPrefs:PsychOwnerClientPrefs;
 public function new(prefs:PsychOwnerClientPrefs) psychClientPrefs = prefs;
}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function get(map:Dynamic, name:String):Dynamic return map.get(name);

 static function main():Void {
  var storage = new MemoryOwnerSave();
  var native:Dynamic = {
   downscroll:true, midscroll:true, showFPS:false, flashingLights:false,
   autoPause:false, antialiasing:false, gameplayShaders:false, zoomCamera:false,
   offset:1.75, fpsCap:240
  };
  var prefs = new PsychOwnerClientPrefs('assets/imported_mods/prefs-a', storage, native);
  var defaults = prefs.defaultData;
  check((cast Reflect.getProperty(prefs, '__hscriptStringFieldPaths'):Array<String>).join('|')
   == 'data.noteSkin|defaultData.noteSkin',
   'owner preference instance did not publish the compiled StringTools receiver paths');
  var fields = ['downScroll','middleScroll','opponentStrums','showFPS','flashing','autoPause',
   'antialiasing','noteSkin','splashSkin','splashAlpha','lowQuality','shaders','cacheOnGPU',
   'framerate','camZooms','hideHud','noteOffset','arrowRGB','arrowRGBPixel','ghostTapping',
   'timeBarType','scoreZoom','noReset','healthBarAlpha','hitsoundVolume','pauseMusic',
   'checkForUpdates','comboStacking','gameplaySettings','comboOffset','ratingOffset',
   'sickWindow','goodWindow','badWindow','safeFrames','guitarHeroSustains','discordRPC',
   'loadingScreen','language'];
  for (field in fields) check(Reflect.hasField(defaults, field), 'missing SaveVariables default: ' + field);
  check(prefs.view == prefs && prefs.data != defaults && prefs.data.gameplaySettings != defaults.gameplaySettings,
   'owner view or data/defaultData objects are not stable and separate');
  check(prefs.data.downScroll == true && prefs.data.middleScroll == true && prefs.data.showFPS == false
   && prefs.data.flashing == false && prefs.data.autoPause == false && prefs.data.antialiasing == false
   && prefs.data.shaders == false && prefs.data.camZooms == false && prefs.data.noteOffset == 1.75,
   'native matching option seeds or fractional noteOffset were lost');
  check(prefs.defaultData.noteOffset == 0 && prefs.defaultData.antialiasing == true
   && prefs.data.framerate == 60,
   'native values leaked into defaults or a nonmatching fps option was seeded');
  var replacementDefaults:Dynamic = {noteSkin:'Writable'};
  prefs.defaultData = replacementDefaults;
  check(prefs.defaultData == replacementDefaults, 'defaultData was not writable like the donor static field');
  prefs.defaultData = defaults;
  check(prefs.data.arrowRGB[0][0] == 0xFFC24B99 && prefs.data.arrowRGBPixel[3][2] == 0xFF6C0000,
   'donor RGB defaults changed');
  var defaultRgb = prefs.defaultData.arrowRGB[0][0];
  prefs.data.arrowRGB[0][0] = 123;
  check(prefs.defaultData.arrowRGB[0][0] == defaultRgb,
   'data arrays alias the stable defaultData arrays');

  check(prefs.getGameplaySetting('healthgain', 55) == 1.0
   && prefs.getGameplaySetting('unlisted', 55) == null
   && prefs.getGameplaySetting('unlisted', 55, true) == 55,
   'getGameplaySetting did not preserve donor customDefaultValue semantics');
  prefs.data.gameplaySettings.set('healthgain', 1.4);
  check(prefs.getGameplaySetting('healthgain', 55) == 1.4,
   'an owner gameplay setting did not override the source default');

  var heldDefaultKeys = prefs.defaultKeys;
  var heldAccept = prefs.keyBinds.get('accept');
  check(heldAccept == heldDefaultKeys.get('accept'),
   'loadDefaultKeys did not retain the donor shallow map snapshot');
  prefs.keyBinds.set('note_left', [999]);
  prefs.gamepadBinds.set('note_left', [888]);
  prefs.resetKeys(false);
  check(prefs.keyBinds.get('note_left')[0] == 65 && prefs.gamepadBinds.get('note_left')[0] == 888,
   'keyboard-only reset changed gamepad binds or missed the keyboard default');
  prefs.resetKeys(true);
  check(prefs.gamepadBinds.get('note_left')[0] == 13 && prefs.keyBinds.get('note_left')[0] == 65,
   'gamepad-only reset changed keyboard binds or missed the gamepad default');
  prefs.keyBinds.set('note_left', [-1, 41, -1]);
  prefs.gamepadBinds.set('note_left', [-1, 42, -1]);
  prefs.clearInvalidKeys('note_left');
  check(prefs.keyBinds.get('note_left').join(',') == '41'
   && prefs.gamepadBinds.get('note_left').join(',') == '42',
   'clearInvalidKeys did not remove every NONE binding');

  var diagnostic = false;
  try prefs.reloadVolumeKeys() catch (error:Dynamic)
   diagnostic = Std.string(error).indexOf('psych-client-prefs-unsupported') >= 0;
  check(diagnostic, 'reloadVolumeKeys silently pretended to change native input state');
  var operationCalls:Array<String> = [];
  prefs.bindRuntimeOperation('reloadVolumeKeys', function(args:Array<Dynamic>):Dynamic {
   operationCalls.push('reload:' + args.length); return 'reloaded';
  });
  prefs.bindRuntimeOperation('toggleVolumeKeys', function(args:Array<Dynamic>):Dynamic {
   operationCalls.push('toggle:' + args[0]); return args[0];
  });
  check(prefs.reloadVolumeKeys() == 'reloaded' && prefs.toggleVolumeKeys(false) == false
   && operationCalls.join('|') == 'reload:0|toggle:false',
   'runtime operation seam did not forward its exact method arguments');

  // Persistence includes known SaveVariables fields, arbitrary gameplay keys,
  // and only control names present in the donor defaults.
  prefs.data.noteOffset = -2.25;
  prefs.data.arrowRGB[0][1] = 456;
  prefs.data.gameplaySettings.set('scrollspeed', 2.5);
  prefs.data.gameplaySettings.set('customSetting', 7);
  prefs.keyBinds.set('note_left', [123]);
  prefs.keyBinds.set('unknownControl', [555]);
  prefs.keyBinds.set('volume_mute', [90]);
  prefs.keyBinds.set('volume_up', [91, 92]);
  prefs.keyBinds.set('volume_down', [93]);
  prefs.gamepadBinds.set('accept', [77]);
  prefs.saveSettings();
  check(storage.flushes == 1 && storage.value.version == 1
   && Reflect.hasField(storage.value.values.data, 'language'),
   'saveSettings did not write/flush the complete versioned owner bucket');
  var storedRgb = storage.value.values.data.arrowRGB[0][1];
  prefs.data.arrowRGB[0][1] = 999;
  check(storedRgb == 456, 'saved nested arrays were not cloned from mutable data');

  storage.value.values.data.unknownSaveField = 'ignore';
  storage.value.values.keyBinds.unknownControl = [999];
  var other = new PsychOwnerClientPrefs('assets/imported_mods/prefs-a', storage);
  var stableDefaults = other.defaultData;
  var originalMute = FlxG.sound.muteKeys;
  var originalUp = FlxG.sound.volumeUpKeys;
  var originalDown = FlxG.sound.volumeDownKeys;
  var volumeKeys = new PsychPreferenceVolumeKeys(other);
  other.loadPrefs();
  check(other.defaultData == stableDefaults && other.data.noteOffset == -2.25
   && other.data.arrowRGB[0][1] == 456
   && !Reflect.hasField(other.data, 'unknownSaveField'),
   'loadPrefs failed to clone known values or changed stable defaults');
  check(get(other.data.gameplaySettings, 'scrollspeed') == 2.5
   && get(other.data.gameplaySettings, 'songspeed') == 1.0
   && get(other.data.gameplaySettings, 'customSetting') == 7,
   'gameplay settings did not merge saved values over defaults');
  check(other.keyBinds.get('note_left').join(',') == '123'
   && other.keyBinds.get('note_right')[0] == 68
   && !other.keyBinds.exists('unknownControl')
   && other.gamepadBinds.get('accept').join(',') == '77',
   'controls did not overlay known actions while preserving fresh defaults');
  check(FlxG.sound.muteKeys.join(',') == '90' && FlxG.sound.volumeUpKeys.join(',') == '91,92'
   && FlxG.sound.volumeDownKeys.join(',') == '93',
   'loadPrefs did not reload owner volume shortcuts after loading saved controls');
  check(FlxG.sound.muteKeys != other.keyBinds.get('volume_mute'),
   'volume adapter did not isolate process arrays from mutable owner bindings');
  other.toggleVolumeKeys(false);
  check(FlxG.sound.muteKeys.length == 0 && FlxG.sound.volumeUpKeys.length == 0
   && FlxG.sound.volumeDownKeys.length == 0, 'toggleVolumeKeys(false) did not disable native shortcuts');
  other.toggleVolumeKeys(true);
  check(FlxG.sound.muteKeys.join(',') == '90', 'toggleVolumeKeys(true) did not restore source shortcuts');
  other.keyBinds.get('note_left')[0] = 321;
  check(storage.value.values.keyBinds.note_left[0] == 123,
   'loaded control arrays alias persisted storage');

  volumeKeys.release();
  check(FlxG.sound.muteKeys == originalMute && FlxG.sound.volumeUpKeys == originalUp
   && FlxG.sound.volumeDownKeys == originalDown,
   'volume adapter release did not restore the exact native shortcut arrays');
  var releasedVolumeApi = false;
  try other.toggleVolumeKeys(false) catch (error:Dynamic)
   releasedVolumeApi = Std.string(error).indexOf('psych-client-prefs-unsupported') >= 0;
  check(releasedVolumeApi, 'released scene left volume callbacks bound to its adapter');
  storage.value.values.keyBinds.volume_mute = [101];
  storage.value.values.keyBinds.volume_up = [102];
  storage.value.values.keyBinds.volume_down = [103, 104];
  var reusedVolumeKeys = new PsychPreferenceVolumeKeys(other);
  other.loadPrefs();
  check(FlxG.sound.muteKeys.join(',') == '101' && FlxG.sound.volumeUpKeys.join(',') == '102'
   && FlxG.sound.volumeDownKeys.join(',') == '103,104',
   'a reused scene did not rebind and reload its saved volume shortcuts');
  reusedVolumeKeys.release();
  check(FlxG.sound.muteKeys == originalMute && FlxG.sound.volumeUpKeys == originalUp
   && FlxG.sound.volumeDownKeys == originalDown,
   'reused volume adapter did not restore the native arrays it borrowed');

  var missingReloads = 0;
  var missing = new PsychOwnerClientPrefs('assets/imported_mods/prefs-missing', new MemoryOwnerSave());
  missing.bindRuntimeOperation('reloadVolumeKeys', function(_args:Array<Dynamic>):Dynamic {
   missingReloads++; return null;
  });
  missing.loadPrefs();
  check(missingReloads == 1, 'loadPrefs did not reload controls when no owner record exists');
  var mismatchReloads = 0;
  var mismatchSave = new MemoryOwnerSave({version:999, values:{}});
  var mismatch = new PsychOwnerClientPrefs('assets/imported_mods/prefs-mismatch', mismatchSave);
  mismatch.bindRuntimeOperation('reloadVolumeKeys', function(_args:Array<Dynamic>):Dynamic {
   mismatchReloads++; return null;
  });
  mismatch.loadPrefs();
  check(mismatchReloads == 1, 'loadPrefs did not reload controls after a version mismatch');

  var apiOwner = new PsychOwnerClientPrefs('assets/imported_mods/prefs-api-a', new MemoryOwnerSave());
  var play = new PlayState(apiOwner);
  PlayState.instance = play;
  check(PsychClientPrefsCompat.data == apiOwner.data
   && PsychClientPrefsCompat.defaultData == apiOwner.defaultData,
   'static ClientPrefs bridge did not expose the current owner objects');
  PsychClientPrefsCompat.data.noteSkin = 'ThroughBridge';
  check(apiOwner.data.noteSkin == 'ThroughBridge', 'static ClientPrefs bridge lost nested mutable identity');
  var replacedData:Dynamic = {noteSkin:'Replaced'};
  PsychClientPrefsCompat.data = replacedData;
  check(apiOwner.data == replacedData, 'static ClientPrefs data setter did not replace current owner data');
  var replacedDefaults:Dynamic = {noteSkin:'NewDefault'};
  PsychClientPrefsCompat.defaultData = replacedDefaults;
  check(apiOwner.defaultData == replacedDefaults, 'static ClientPrefs defaultData setter did not reach owner');
  var nextOwner = new PsychOwnerClientPrefs('assets/imported_mods/prefs-api-b', new MemoryOwnerSave());
  play.psychClientPrefs = nextOwner;
  check(PsychClientPrefsCompat.data == nextOwner.data,
   'static ClientPrefs bridge stayed pinned to a previous owner');
  PlayState.instance = null;
  var detachedData = PsychClientPrefsCompat.data;
  check(detachedData == PsychClientPrefsCompat.data,
   'standalone ClientPrefs fallback was not stable after leaving an owner');
  apiOwner.release(); nextOwner.release(); missing.release(); mismatch.release();

  check(other.canReuseFor('assets/imported_mods/prefs-a')
   && !other.canReuseFor('assets/imported_mods/prefs-b'),
   'owner cache key did not compare normalized roots');
  var alias = new PsychOwnerClientPrefs('assets/imported_mods/prefs-a/', new MemoryOwnerSave());
  check(alias.canReuseFor('assets/imported_mods/prefs-a'), 'trailing slash changed the owner key');
  var refused = false;
  try new PsychOwnerClientPrefs('assets/imported_mods/prefs-a/../prefs-b', storage)
   catch (_:Dynamic) refused = true;
  check(refused, 'preference storage accepted a traversing owner root');

  other.release();
  check(!other.canReuseFor('assets/imported_mods/prefs-a'), 'released preferences remained reusable');
  var released = false;
  try other.saveSettings() catch (_:Dynamic) released = true;
  check(released, 'released preference instance continued using owner storage');
  prefs.release(); alias.release();
}
}'''

FLXG = r'''package flixel;
import flixel.input.keyboard.FlxKey;
class FakeSound {
 public var muteKeys:Array<FlxKey> = [FlxKey.SPACE];
 public var volumeUpKeys:Array<FlxKey> = [FlxKey.UP];
 public var volumeDownKeys:Array<FlxKey> = [FlxKey.DOWN];
 public function new() {}
}
class FlxG {
 public static var sound:FakeSound = new FakeSound();
}'''


class PsychOwnerClientPrefsTest(unittest.TestCase):
    def test_mutable_data_owner_storage_and_control_api(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        with tempfile.TemporaryDirectory(prefix="psych-owner-prefs-", dir=ROOT / "tmp") as scratch:
            keyboard = Path(scratch) / "flixel/input/keyboard/FlxKey.hx"
            gamepad = Path(scratch) / "flixel/input/gamepad/FlxGamepadInputID.hx"
            keyboard.parent.mkdir(parents=True, exist_ok=True)
            gamepad.parent.mkdir(parents=True, exist_ok=True)
            keyboard.write_text(KEYS, newline="\n")
            gamepad.write_text(GAMEPAD, newline="\n")
            flxg = Path(scratch) / "flixel/FlxG.hx"
            flxg.parent.mkdir(parents=True, exist_ok=True)
            flxg.write_text(FLXG, newline="\n")
            (Path(scratch) / "Main.hx").write_text(FIXTURE, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", scratch,
                 "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
