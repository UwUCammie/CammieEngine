"""Executable contracts for the owner-scoped Nightmare Vision controls facade."""

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''import flixel.input.FlxInput.FlxInputState;
import flixel.input.actions.FlxActionInput.FlxInputDevice;
import flixel.input.actions.FlxActionInput.FlxInputDeviceID;
import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;
import NightmareVisionControls;
import nightmarevision.input.NightmareVisionInputEnums.Action;
import nightmarevision.input.NightmareVisionInputEnums.Control;
import nightmarevision.input.NightmareVisionInputEnums.Device;
import nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  var keyBinds:Map<String, Array<FlxKey>> = new Map();
  keyBinds.set('ui_up', [FlxKey.W, FlxKey.UP]);
  keyBinds.set('note_left', [FlxKey.A, FlxKey.LEFT]);
  keyBinds.set('accept', [FlxKey.SPACE, FlxKey.ENTER]);
  var gamepadBinds:Map<String, Array<FlxGamepadInputID>> = new Map();
  gamepadBinds.set('note_up', [FlxGamepadInputID.Y]);
  gamepadBinds.set('note_down', [FlxGamepadInputID.A]);
  gamepadBinds.set('note_left', [FlxGamepadInputID.X]);
  gamepadBinds.set('note_right', [FlxGamepadInputID.B]);
  gamepadBinds.set('note_dodge', [FlxGamepadInputID.GUIDE]);
  var prefsCalls = 0;
  var customKeyName = '';
  var customKeyValues:Array<FlxKey> = null;
  var prefs:Dynamic = {
   keyBinds:keyBinds,
   gamepadBinds:gamepadBinds,
   addCustomKey:function(name:String, keys:Array<FlxKey>):Void {
    prefsCalls++;
    customKeyName = name;
    customKeyValues = keys;
    keyBinds.set(name, keys);
   }
  };

  var controls = new NightmareVisionControls('player', Solo, prefs);
  var expected:Array<String> = [
   'ui_up','ui_left','ui_right','ui_down',
   'ui_up-press','ui_left-press','ui_right-press','ui_down-press',
   'ui_up-release','ui_left-release','ui_right-release','ui_down-release',
   'note_up','note_left','note_right','note_down',
   'note_up-press','note_left-press','note_right-press','note_down-press',
   'note_up-release','note_left-release','note_right-release','note_down-release',
   'note_dodge','note_dodge-press','note_dodge-release',
   'accept','back','pause','reset','fullscreen','switch_debug_display','soft_reload','hard_reload'
  ];
  eq(controls.digitalActions.length, 35, 'the action set has the source 35 digital actions');
  eq(controls.actions.keys().hasNext(), true, 'the source action map is populated');
  for (name in expected) {
   var action:Action = cast name;
   check(controls.actions.exists(action), 'missing source action ' + name);
   check(controls.customActions.get(action) == null, 'built-in action was marked custom: ' + name);
  }
  eq(controls.actions.keys().hasNext(), true, 'action names remain iterable');
  check(controls.actions.get(Action.UI_UP) == controls.actions.get(Action.UI_UP),
   'the registry returns the same FlxAction object and preserves its per-frame cache');

  var upHeld = controls.actions.get(Action.UI_UP).inputs;
  var upPressed = controls.actions.get(Action.UI_UP_P).inputs;
  var upReleased = controls.actions.get(Action.UI_UP_R).inputs;
  eq(upHeld.length, 2, 'Solo binds both preference keys to the held action');
  eq(upPressed.length, 2, 'Solo binds both preference keys to the pressed action');
  eq(upReleased.length, 2, 'Solo binds both preference keys to the released action');
  eq(upHeld[0].device, FlxInputDevice.KEYBOARD, 'keyboard source device');
  eq(upHeld[0].trigger, FlxInputState.PRESSED, 'held action trigger');
  eq(upPressed[0].trigger, FlxInputState.JUST_PRESSED, 'pressed action trigger');
  eq(upReleased[0].trigger, FlxInputState.JUST_RELEASED, 'released action trigger');
  eq(controls.getInputsFor(Control.UI_UP, Keys).join(','), '87,38',
   'getInputsFor returns the physical keyboard IDs in bind order');
  check(!controls.checkByName(cast 'not_an_action'), 'unknown checkByName returns false outside debug builds');
  check(!controls.checkCustom('not_a_custom_action'), 'missing custom actions return false');

  // Preference maps are consulted when the scheme is applied, not polled on reads.
  keyBinds.set('note_left', [FlxKey.C]);
  eq(controls.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '65,37',
   'preference edits alone do not rewrite already attached FlxAction inputs');
  controls.setKeyboardScheme(Solo);
  eq(controls.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '67',
   'reapplying Solo reads the owner preference map and replaces keyboard bindings');

  controls.addCustomKey('MiXeD', [FlxKey.B]);
  eq(prefsCalls, 1, 'custom key is recorded through the injected owner preferences');
  eq(customKeyName, 'mixed', 'custom key names are lowercased without trimming');
  eq(customKeyValues.length, 2, 'custom key preferences are padded to two entries');
  eq(customKeyValues[1], FlxKey.NONE, 'custom key padding uses NONE');
  check(controls.actions.exists(cast 'mixed') && controls.actions.exists(cast 'mixed-press')
   && controls.actions.exists(cast 'mixed-release'), 'custom held/press/release actions are registered');
  check(controls.customActions.exists(cast 'mixed') && controls.customActions.exists(cast 'mixed-press')
   && controls.customActions.exists(cast 'mixed-release'), 'custom actions appear in both registries');
  eq(controls.actions.get(cast 'mixed').inputs.length, 1, 'custom key binds its held action');
  eq(controls.actions.get(cast 'mixed-press').inputs[0].trigger, FlxInputState.JUST_PRESSED,
   'custom press action uses JUST_PRESSED');
  eq(controls.actions.get(cast 'mixed-release').inputs[0].trigger, FlxInputState.JUST_RELEASED,
   'custom release action uses JUST_RELEASED');
  controls.customBind('mixed', [FlxKey.D, FlxKey.NONE]);
  eq(controls.actions.get(cast 'mixed').inputs.length, 2,
   'customBind appends keys and filters NONE instead of replacing old inputs');
  eq(controls.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '67',
   'custom registration does not replace unrelated controls');

  controls.addDefaultGamepad(3);
  eq(controls.gamepadsAdded.join(','), '3', 'default gamepad ID is recorded');
  eq(controls.getInputsFor(Control.NOTE_LEFT, Gamepad(3)).join(','), '2',
   'gamepad binds use owner preference buttons and preserve the device ID');
  var copySource = new NightmareVisionControls('copy-source', Solo, prefs);
  copySource.addDefaultGamepad(3);
  var sourcePadInput:Dynamic = null;
  for (input in copySource.actions.get(Action.NOTE_LEFT).inputs)
   if (input.device == FlxInputDevice.GAMEPAD) sourcePadInput = input;
  var keyOnlyCopy = new NightmareVisionControls('key-copy', None, prefs);
  keyOnlyCopy.copyFrom(copySource, Keys);
  eq(keyOnlyCopy.keyboardScheme, Solo, 'a None scheme adopts the copied keyboard scheme');
  eq(keyOnlyCopy.actions.get(Action.NOTE_LEFT).inputs[0], copySource.actions.get(Action.NOTE_LEFT).inputs[0],
   'copyFrom shares existing FlxActionInput objects instead of recreating cached actions');
  var gamepadOnlyCopy = new NightmareVisionControls('pad-copy', None, prefs);
  gamepadOnlyCopy.copyFrom(copySource, Gamepad(3));
  eq(gamepadOnlyCopy.gamepadsAdded.join(','), '3', 'gamepad-only copy tracks the selected ID');
  eq(gamepadOnlyCopy.getInputsFor(Control.NOTE_LEFT, Gamepad(3)).join(','), '2',
   'gamepad-only copy filters physical inputs by device ID');
  eq(gamepadOnlyCopy.actions.get(Action.NOTE_LEFT).inputs[0], sourcePadInput,
   'gamepad copy keeps the shared source FlxActionInput identity');
  eq(gamepadOnlyCopy.keyboardScheme, None, 'gamepad-only copy does not merge keyboard schemes');

  controls.removeGamepad(3);
  eq(controls.getInputsFor(Control.NOTE_LEFT, Gamepad(3)).length, 0,
   'removing one gamepad removes that device input');
  eq(controls.gamepadsAdded.length, 0, 'removing one gamepad removes its recorded ID');
  controls.addDefaultGamepad(4);
  controls.removeGamepad(FlxInputDeviceID.ALL);
  eq(controls.getInputsFor(Control.NOTE_LEFT, Gamepad(4)).length, 0,
   'ALL removes inputs across connected gamepads');
  eq(controls.gamepadsAdded.join(','), '4',
   'source removeGamepad(ALL) quirk retains each concrete ID in gamepadsAdded');

  controls.setKeyboardScheme(Duo(true));
  var firstPlayerScheme = false;
  switch (controls.keyboardScheme) {
   case Duo(true): firstPlayerScheme = true;
   default:
  }
  check(firstPlayerScheme, 'first-player Duo scheme is retained');
  eq(controls.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '65', 'Duo first uses A for left');
  eq(controls.getInputsFor(Control.ACCEPT, Keys).join(','), '71,90', 'Duo first accept keys are G and Z');
  controls.setKeyboardScheme(Duo(false));
  eq(controls.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '37', 'Duo second uses the arrow keys');
  eq(controls.getInputsFor(Control.ACCEPT, Keys).join(','), '79', 'Duo second accept key is O');
  controls.removeDevice(Keys);
  eq(controls.keyboardScheme, None, 'removing keyboard selects the None scheme');
  eq(controls.getInputsFor(Control.NOTE_LEFT, Keys).length, 0, 'removing keyboard clears keyboard inputs');
  eq(controls.getInputsFor(Control.NOTE_LEFT, Gamepad(4)).length, 0,
   'removing keyboard leaves gamepad inputs removed only by their own operation');

  var active:NightmareVisionControls = null;
  NightmareVisionControls.setInstanceAccessors(function() return active,
   function(value) active = value, function() return prefs);
  NightmareVisionControls.instance = controls;
  eq(NightmareVisionControls.instance, controls, 'instance getter resolves through the active owner');
  NightmareVisionControls.instance = null;
  eq(active, null, 'instance setter writes through the host instead of ignoring assignment');
  var ownerUnavailable = false;
  try { var noOwner = NightmareVisionControls.instance; } catch (error:Dynamic)
   ownerUnavailable = Std.string(error).indexOf('has no active owner') >= 0;
  check(ownerUnavailable, 'a resolver with no current owner does not silently return null');
  NightmareVisionControls.clearInstanceAccessors();
  var removedHooks = 0;
  var fakeManager:Dynamic = {
   deviceConnected:{remove:function(_:Dynamic) removedHooks++},
   deviceDisconnected:{remove:function(_:Dynamic) removedHooks++}
  };
  @:privateAccess NightmareVisionControls.hookedGamepadManager = cast fakeManager;
  @:privateAccess NightmareVisionControls.gamepadHooksInstalled = true;
  NightmareVisionControls.clearInstanceAccessors();
  eq(removedHooks, 2, 'clearing the owner removes both static gamepad signal hooks');
  @:privateAccess check(!NightmareVisionControls.gamepadHooksInstalled,
   'clearing the owner resets the hook installation guard');
  @:privateAccess eq(NightmareVisionControls.hookedGamepadManager, null,
   'clearing the owner drops the prior gamepad manager reference');
  @:privateAccess NightmareVisionControls.gamepadConnected(null);
  @:privateAccess NightmareVisionControls.gamepadDisconnected(null);
  var refused = false;
  try { var unscoped = NightmareVisionControls.instance; } catch (error:Dynamic)
   refused = Std.string(error).indexOf('[nmv-controls-unsupported]') >= 0;
  check(refused, 'unscoped instance lookup fails with an explicit diagnostic');
  refused = false;
  try NightmareVisionControls.init() catch (error:Dynamic)
   refused = Std.string(error).indexOf('[nmv-controls-unsupported]') >= 0;
  check(refused, 'unscoped init fails with an explicit diagnostic');
  check(NightmareVisionControls.unimplementedInitHooks().indexOf('ControlsSubState.resetGroups') >= 0,
   'the missing native controls-menu reset hook stays inventoried');

  var destroyTarget = new NightmareVisionControls('destroy-target', None, prefs);
  destroyTarget.addGamepad(9, [Control.NOTE_LEFT => [FlxGamepadInputID.X]]);
  destroyTarget.destroy();
  eq(destroyTarget.actions.iterator().hasNext(), false, 'destroy clears owner action registries');
  eq(destroyTarget.gamepadsAdded.length, 0, 'destroy clears recorded gamepad IDs');
  refused = false;
  try destroyTarget.setKeyboardScheme(None) catch (_:Dynamic) refused = true;
  check(refused, 'destroyed owner controls reject later binding operations');
 }
}
'''


class NightmareVisionControlsTest(unittest.TestCase):
    def test_action_registry_bindings_devices_schemes_and_owner_lifecycle(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["PATH"] = os.pathsep.join((str(ROOT / ".tools/haxe"),
                                             str(ROOT / ".tools/neko"), env.get("PATH", "")))
            result = subprocess.run(
                [*HAXE_COMMAND,
                 "-cp", str(ROOT / "source"),
                 "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
                 "-D", "FLX_STANDARD_ASSETS_DIRECTORY",
                 "-D", "FLX_DEFAULT_SOUND_EXT=ogg", "-D", "FLX_SOUND_SYSTEM",
                 "-D", "FLX_GAMEINPUT_API", "-D", "FLX_KEYBOARD", "-D", "FLX_GAMEPAD", "-D", "FLX_NO_MOUSE",
                 "-cp", str(work),
                 "-main", "Main", "--interp"],
                cwd=work, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
