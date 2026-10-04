"""Executable contract tests for the Psych Controls facade and device poller."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;
import flixel.FlxG;

class PlayState {
 public static var instance:PlayState;
 public var psychControls:PsychControlsCompat;
 public var psychClientPrefs:Dynamic;
 public function new(prefs:Dynamic) psychClientPrefs=prefs;
}

class Main {
 static function check(value:Bool, label:String):Void if (!value) throw label;

 static function main():Void {
  var calls:Array<String>=[];
  var controls:Dynamic={
   pressed:function(name:String):Bool { calls.push('held:'+name); return name=='note_up' || name=='ui_up'; },
   justPressed:function(name:String):Bool { calls.push('press:'+name); return name=='note_left' || name=='accept' || name=='ui_down'; },
   justReleased:function(name:String):Bool { calls.push('release:'+name); return name=='note_right'; }
  };
  var fallback=new PsychControlsCompat(controls);
  var surface:Array<Bool>=[fallback.UI_UP,fallback.UI_DOWN,fallback.UI_LEFT,fallback.UI_RIGHT,
   fallback.UI_UP_P,fallback.UI_DOWN_P,fallback.UI_LEFT_P,fallback.UI_RIGHT_P,
   fallback.UI_UP_R,fallback.UI_DOWN_R,fallback.UI_LEFT_R,fallback.UI_RIGHT_R,
   fallback.NOTE_UP,fallback.NOTE_DOWN,fallback.NOTE_LEFT,fallback.NOTE_RIGHT,
   fallback.NOTE_UP_P,fallback.NOTE_DOWN_P,fallback.NOTE_LEFT_P,fallback.NOTE_RIGHT_P,
   fallback.NOTE_UP_R,fallback.NOTE_DOWN_R,fallback.NOTE_LEFT_R,fallback.NOTE_RIGHT_R,
   fallback.ACCEPT,fallback.BACK,fallback.PAUSE,fallback.RESET];
  check(surface.length==28, 'all Psych direction and non-direction aliases should be exposed');
  for (action in ['held:ui_up','held:ui_down','held:ui_left','held:ui_right',
   'press:ui_up','press:ui_down','press:ui_left','press:ui_right',
   'release:ui_up','release:ui_down','release:ui_left','release:ui_right',
   'held:note_up','held:note_down','held:note_left','held:note_right',
   'press:note_up','press:note_down','press:note_left','press:note_right',
   'release:note_up','release:note_down','release:note_left','release:note_right',
   'press:accept','press:back','press:pause','press:reset'])
   check(calls.contains(action), 'missing Psych alias route: '+action);
  check(fallback.NOTE_UP && fallback.pressed('note_up'), 'held note getters and generic query should use the held phase');
  check(fallback.NOTE_LEFT_P && fallback.justPressed('note_left'), 'press getters should use the just-pressed phase');
  check(fallback.NOTE_RIGHT_R && fallback.justReleased('note_right'), 'release getters should use the just-released phase');
  check(fallback.UI_UP && fallback.UI_DOWN_P && fallback.UI_LEFT_R == false,
   'UI aliases should select held, press, and release phases');
  check(fallback.ACCEPT && !fallback.BACK && !fallback.PAUSE && !fallback.RESET,
   'non-directional aliases are just-pressed queries');
  check(calls.indexOf('held:ui_up')>=0 && calls.indexOf('press:ui_down')>=0
   && calls.indexOf('release:ui_left')>=0,
   'UI getters should forward Psych action names exactly');
  fallback.controllerMode=true;
  fallback.justPressed('accept');
  check(fallback.controllerMode, 'native/provided-control fallback must not invent a device-mode change');

  var keys:Map<String,Array<FlxKey>>=new Map();
  var buttons:Map<String,Array<FlxGamepadInputID>>=new Map();
  keys.set('note_left',[FlxKey.A]);
  buttons.set('note_left',[FlxGamepadInputID.A]);
  var prefs:Dynamic={keyBinds:keys,gamepadBinds:buttons};
  var owned=new PsychControlsCompat(null,prefs);
  check(owned.keyboardBinds==keys && owned.gamepadBinds==buttons,
   'source controls must retain the preference map identities');
  var replacement:Array<FlxKey>=[FlxKey.B];
  keys.set('note_left',replacement);
  check(owned.keyboardBinds.get('note_left')==replacement,
   'captured maps must expose in-place binding replacement');
  var captured:Array<FlxKey>=[FlxKey.A];
  var keyboardPolls=0;
  var gamepadPolls=0;
  FlxG.keys={
   anyPressed:function(values:Array<FlxKey>):Bool return false,
   anyJustPressed:function(values:Array<FlxKey>):Bool { keyboardPolls++; return values==captured; },
   anyJustReleased:function(values:Array<FlxKey>):Bool return false
  };
  FlxG.gamepads={
   anyPressed:function(button:FlxGamepadInputID):Bool return false,
   anyJustPressed:function(button:FlxGamepadInputID):Bool { gamepadPolls++; return true; },
   anyJustReleased:function(button:FlxGamepadInputID):Bool { gamepadPolls++; return true; }
  };
  owned.controllerMode=true;
  check(owned.queryKeyboard(captured,'justPressed') && !owned.controllerMode,
   'the captured-key helper should query its passed array and clear controller mode');
  check(owned.queryGamepad('note_left','justPressed') && owned.controllerMode && keyboardPolls==1,
   'the gamepad-only helper should set mode without polling keyboard bindings');
  var keyboardCount=keyboardPolls;
  check(owned.gamepadJustReleased('note_left') && keyboardPolls==keyboardCount,
   'gamepad release edges should remain device-only');

  var detached=PsychControlsCompat.instance;
  var nativePlay=new PlayState(null);
  PlayState.instance=nativePlay;
  check(PsychControlsCompat.instance==detached && nativePlay.psychControls==null
   && detached.keyboardBinds==null,
   'a native PlayState should use the detached fallback without receiving an owner adapter');
  var nativeAssignment=new PsychControlsCompat(null,prefs);
  PsychControlsCompat.instance=nativeAssignment;
  check(nativePlay.psychControls==null && PsychControlsCompat.instance!=nativeAssignment
   && PsychControlsCompat.instance.keyboardBinds==null,
   'static assignments during native gameplay must not attach source bindings');

  var play=new PlayState(prefs);
  play.psychControls=owned;
  PlayState.instance=play;
  check(PsychControlsCompat.instance==owned, 'static instance should resolve the active PlayState facade');
  check(detached.keyboardBinds==null && !detached.justPressed('note_left'),
   'a detached fallback must not attach to owner preferences created later');
  owned.release();
  check(owned.keyboardBinds==null && owned.gamepadBinds==null && !owned.justPressed('note_left'),
   'release must clear owner maps and stop all input reads');
  play.psychControls=null;
  var fresh=PsychControlsCompat.instance;
  check(fresh!=owned && fresh.keyboardBinds==keys,
   'a released owner facade must not be reused by the active scene');
  var replacement=new PsychControlsCompat(controls);
  PsychControlsCompat.instance=replacement;
  check(play.psychControls==replacement && PsychControlsCompat.instance==replacement,
   'the mutable static instance should update the current owner');
  replacement.release();
  play.psychControls=null;
  PlayState.instance=null;
  check(PsychControlsCompat.instance!=replacement,
   'a scene-owned adapter should not remain in the detached fallback after its owner ends');
  var ownerAdapter=new PsychControlsCompat(null,prefs);
  PsychControlsCompat.instance=ownerAdapter;
  check(PsychControlsCompat.instance!=ownerAdapter && PsychControlsCompat.instance.keyboardBinds==null,
   'the detached singleton setter must not retain a source owner ledger');
 }
}
'''


DEVICE_MAIN = r'''import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;
import flixel.FlxG;

class Main {
 static function check(value:Bool, label:String):Void if (!value) throw label;
 static function main():Void {
  var keys:Map<String,Array<FlxKey>>=new Map();
  var pads:Map<String,Array<FlxGamepadInputID>>=new Map();
  var first:Array<FlxKey>=[FlxKey.A,FlxKey.B];
  var second:Array<FlxKey>=[FlxKey.C];
  keys.set('note_left',first);
  pads.set('note_left',[FlxGamepadInputID.A,FlxGamepadInputID.B]);
  var keyDown=true;
  var padDown=false;
  var keyCalls=0;
  var padCalls=0;
  var lastKeys:Array<FlxKey>=null;
  var device=new SourceInputDevice(keys,pads,
   function(values:Array<FlxKey>, phase:String):Bool {
    keyCalls++; lastKeys=values;
    return keyDown && phase=='justPressed';
   },
   function(button:FlxGamepadInputID, phase:String):Bool {
    padCalls++;
    return padDown && phase=='justPressed' && button==FlxGamepadInputID.B;
   });

  device.controllerMode=true;
  check(device.query('note_left','justPressed') && !device.controllerMode,
   'a matching keyboard edge should clear controller mode');
  check(lastKeys==first && padCalls==0,
   'keyboard bindings are passed by identity and short-circuit gamepad polling');

  keyDown=false; padDown=true;
  keys.set('note_left',second);
  check(device.query('note_left','justPressed') && device.controllerMode,
   'a gamepad match should set controller mode after keyboard misses');
  check(lastKeys==second && padCalls==2,
   'queries should see replaced map entries and scan button IDs in order');

  padDown=false;
  device.controllerMode=true;
  check(!device.query('note_left','pressed') && device.controllerMode,
   'a miss should preserve the previous device mode');
  var before=keyCalls+padCalls;
  check(!device.query('missing','justPressed') && keyCalls+padCalls==before,
   'missing actions should not call either input manager');

  var rawKeysSeen=false;
  var rawPadsSeen=false;
  FlxG.keys={
   anyPressed:function(values:Array<FlxKey>):Bool return false,
   anyJustPressed:function(values:Array<FlxKey>):Bool { rawKeysSeen=values==second; return true; },
   anyJustReleased:function(values:Array<FlxKey>):Bool return false
  };
  FlxG.gamepads={
   anyPressed:function(button:FlxGamepadInputID):Bool return false,
   anyJustPressed:function(button:FlxGamepadInputID):Bool { rawPadsSeen=true; return true; },
   anyJustReleased:function(button:FlxGamepadInputID):Bool return false
  };
  var raw=new SourceInputDevice(keys,pads);
  raw.controllerMode=true;
  check(raw.query('note_left','justPressed') && rawKeysSeen && !rawPadsSeen && !raw.controllerMode,
   'the default poller should call FlxG keyboard methods directly and short-circuit');
  keys.set('note_left',[]);
  check(raw.query('note_left','justPressed') && rawPadsSeen && raw.controllerMode,
   'the default poller should call FlxG gamepad methods directly after an empty keyboard binding');
 }
}
'''


class PsychControlsCompatTest(unittest.TestCase):
    def run_haxe(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(source, encoding="utf-8", newline="\n")
            (temp / "PsychFlxCameraCompat.hx").write_text(
                "package; class PsychFlxGCompat { public static var state:Dynamic=null; }\n",
                encoding="utf-8",
                newline="\n",
            )
            (temp / "flixel").mkdir(parents=True, exist_ok=True)
            (temp / "flixel/input/keyboard").mkdir(parents=True)
            (temp / "flixel/input/gamepad").mkdir(parents=True)
            (temp / "flixel/FlxG.hx").write_text(
                "package flixel; class FlxG { public static var keys:Dynamic; public static var gamepads:Dynamic; }\n",
                encoding="utf-8",
                newline="\n",
            )
            (temp / "flixel/input/keyboard/FlxKey.hx").write_text(
                "package flixel.input.keyboard; enum abstract FlxKey(Int) from Int to Int { var A=1; var B=2; var C=3; }\n",
                encoding="utf-8",
                newline="\n",
            )
            (temp / "flixel/input/gamepad/FlxGamepadInputID.hx").write_text(
                "package flixel.input.gamepad; enum abstract FlxGamepadInputID(Int) from Int to Int { var A=1; var B=2; }\n",
                encoding="utf-8",
                newline="\n",
            )
            return subprocess.run(
                [*HAXE_COMMAND, "-D", "FLX_KEYBOARD", "-D", "FLX_GAMEPAD",
                 "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )

    def test_psych_surface_owner_mapping_and_fallback_phases(self):
        result = self.run_haxe(MAIN)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_device_poll_order_and_live_bindings(self):
        result = self.run_haxe(DEVICE_MAIN)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
