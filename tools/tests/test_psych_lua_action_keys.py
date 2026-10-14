"""Lua key callbacks ask the same named-action lookup the script controls object uses."""
import unittest

import test_psych_controls_compat as controls_fixture
from base_helper_fixtures import play_state_method
from haxe_test_support import FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import flixel.input.keyboard.FlxKey;
import flixel.input.gamepad.FlxGamepadInputID;

class Host {
 public var psychControls:PsychControlsCompat;
 public var controls:Dynamic;
 public var rawKeys:Array<String> = [];
 public function new() {}
 function compatKeyboardState(key:String, phase:String):Bool { rawKeys.push(phase + ':' + key); return key == 'space'; }
__METHOD__
}

class Main {
 static function check(value:Bool, label:String):Void if (!value) throw label;
 static var phases = ['justPressed', 'pressed', 'justReleased'];

 static function main():Void {
  // Name normalising on its own.
  for (spelling in ['left', 'LEFT', ' left ', 'Left', 'note_left', ' NOTE_LEFT '])
   check(PsychControlsCompat.actionName(spelling) == 'note_left', 'direction spelling: "' + spelling + '"');
  check(PsychControlsCompat.actionName('down') == 'note_down' && PsychControlsCompat.actionName('UP') == 'note_up'
   && PsychControlsCompat.actionName('right') == 'note_right', 'bare directions are the note keys');
  check(PsychControlsCompat.actionName('ui_up') == 'ui_up' && PsychControlsCompat.actionName(' Reset ') == 'reset'
   && PsychControlsCompat.actionName('confirm') == 'accept' && PsychControlsCompat.actionName(null) == '', 'other names pass through');
  for (action in ['note_left', 'note_down', 'note_up', 'note_right', 'ui_left', 'ui_down', 'ui_up', 'ui_right',
   'accept', 'back', 'pause', 'reset'])
   check(PsychControlsCompat.knownAction(action), 'known action: ' + action);
  check(!PsychControlsCompat.knownAction('space') && !PsychControlsCompat.knownAction('left')
   && !PsychControlsCompat.knownAction(''), 'a key name is not an action');

  // With the script controls object: every spelling is one query per phase.
  var calls:Array<String> = [];
  var held = ['note_left', 'accept'];
  var facade:Dynamic = {
   pressed: function(name:String):Bool { calls.push('pressed:' + name); return held.contains(name); },
   justPressed: function(name:String):Bool { calls.push('justPressed:' + name); return held.contains(name); },
   justReleased: function(name:String):Bool { calls.push('justReleased:' + name); return held.contains(name); }
  };
  var host = new Host();
  host.psychControls = new PsychControlsCompat(facade);
  for (phase in phases) {
   calls = [];
   for (spelling in ['LEFT', ' left ', 'note_left'])
    check(host.actionState(spelling, phase), phase + ' did not report the held note key for "' + spelling + '"');
   check(calls.join(',') == [for (i in 0...3) phase + ':note_left'].join(','),
    'spellings reached different queries in ' + phase + ': ' + calls.join(','));
   calls = [];
   check(!host.actionState('reset', phase) && host.actionState('accept', phase) && !host.actionState('ui_up', phase)
    && host.actionState('confirm', phase), 'named action result in ' + phase);
   check(calls.join(',') == [phase + ':reset', phase + ':accept', phase + ':ui_up', phase + ':accept'].join(','),
    'named actions did not reach the action query in ' + phase + ': ' + calls.join(','));
  }
  check(host.rawKeys.length == 0, 'an action name was read as a raw key: ' + host.rawKeys.join(','));

  // A name that is no action anywhere still works as a key, in every phase.
  calls = [];
  for (phase in phases)
   check(host.actionState('space', phase) && !host.actionState('F5', phase), 'raw key fallback in ' + phase);
  check(calls.length == 0, 'a raw key name was sent to the action query');
  check(host.rawKeys.join(',') == 'justPressed:space,justPressed:F5,pressed:space,pressed:F5,justReleased:space,justReleased:F5',
   'raw key fallback phases: ' + host.rawKeys.join(','));

  // An action that only the owner's own bindings define is still an action.
  var keys:Map<String, Array<FlxKey>> = new Map();
  var buttons:Map<String, Array<FlxGamepadInputID>> = new Map();
  keys.set('dodge', [FlxKey.A]);
  buttons.set('taunt', [FlxGamepadInputID.B]);
  var owned = new Host();
  owned.psychControls = new PsychControlsCompat(null, {keyBinds: keys, gamepadBinds: buttons});
  check(owned.psychControls.hasAction('dodge') && owned.psychControls.hasAction(' DODGE ')
   && owned.psychControls.hasAction('taunt') && owned.psychControls.hasAction('left')
   && !owned.psychControls.hasAction('space'), 'owner bindings define actions');
  owned.actionState('dodge', 'justPressed');
  owned.actionState('space', 'justPressed');
  check(owned.rawKeys.join(',') == 'justPressed:space', 'owner action fell through to a raw key: ' + owned.rawKeys.join(','));

  // Without source bindings the game's own controls answer, through one name table.
  var native:Array<String> = [];
  var nativeControls:Dynamic = {
   checkByName: function(name:String):Bool { native.push('check:' + name); return name == 'ctrl1-press' || name == 'accept'; },
   pressedByName: function(name:String):Bool { native.push('held:' + name); return name == 'accept'; }
  };
  var plain = new Host();
  plain.controls = nativeControls;
  check(plain.actionState('left', 'justPressed') && !plain.actionState('RIGHT', 'justPressed'), 'native note press');
  check(native.join(',') == 'check:ctrl1-press,check:ctrl4-press', 'native press names: ' + native.join(','));
  native = [];
  plain.actionState('down', 'pressed'); plain.actionState('up', 'justReleased');
  check(native.join(',') == 'held:note_down,check:ctrl2,check:ctrl3-release', 'native hold and release names: ' + native.join(','));
  native = [];
  check(plain.actionState('accept', 'justPressed') && plain.actionState('accept', 'pressed')
   && !plain.actionState('accept', 'justReleased'), 'native accept phases');
  native = [];
  plain.actionState('ui_up', 'pressed'); plain.actionState('ui_down', 'justPressed');
  check(native.join(',') == 'held:ui_up,check:up-menu-hold,check:down-menu', 'native menu names: ' + native.join(','));
  check(plain.actionState('space', 'pressed') && plain.rawKeys.join(',') == 'pressed:space', 'native raw key fallback');
  // The game's own controls have no entry for the source engine's extra
  // actions, so those names must never be looked up there.
  native = [];
  plain.rawKeys = [];
  for (extra in ['volume_mute', 'volume_up', 'volume_down', 'debug_1', 'debug_2', 'fullscreen'])
   for (phase in phases) {
    check(PsychControlsCompat.knownAction(extra) && !PsychControlsCompat.nativeAction(extra), 'native action table: ' + extra);
    check(!plain.actionState(extra, phase), 'an action the game does not bind reported a press: ' + extra);
   }
  check(native.length == 0, 'a name the game does not bind was looked up in its controls: ' + native.join(','));
  check(plain.rawKeys.length == 18, 'unbound action names fall back to the raw key lookup');
  for (action in ['note_left', 'note_down', 'note_up', 'note_right', 'ui_left', 'ui_down', 'ui_up', 'ui_right',
   'accept', 'back', 'pause', 'reset'])
   check(PsychControlsCompat.nativeAction(action), 'native action: ' + action);
 }
}
'''


class PsychLuaActionKeysTest(unittest.TestCase):
    def test_key_callbacks_share_the_named_action_lookup(self):
        source = MAIN.replace("__METHOD__", play_state_method("public function actionState("))
        result = controls_fixture.PsychControlsCompatTest.run_haxe(self, source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_and_base_registrations_are_thin_calls(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        for name, phase in (("keyJustPressed", "justPressed"), ("keyPressed", "pressed"), ("keyReleased", "justReleased")):
            self.assertIn(
                f"interp.variables.set('{name}', function(?name:String = '') return actionState(name, '{phase}'));", play)
        self.assertNotIn("function compatKeyJustPressed(", play)
        # Raw key callbacks stay raw.
        self.assertIn("interp.variables.set('keyboardJustPressed', compatKeyboardJustPressed);", play)
        bindings = (ROOT / "source/PsychSourceBindings.hx").read_text(encoding="utf-8")
        self.assertNotIn("function actionState(", bindings)
        self.assertIn("host.actionState(name, 'pressed')", bindings)
        self.assertIn("host.actionState(name, 'justReleased')", bindings)


if __name__ == "__main__":
    unittest.main()
