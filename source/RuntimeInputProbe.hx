package;

import flixel.FlxG;
import openfl.events.KeyboardEvent;

/** Opt-in native regression probe; presses pass through the ordinary stage
 * and live player bindings without desktop focus or saved-setting changes. */
@:access(Controls)
@:access(PlayState)
@:access(RuntimeSmokeHarness)
class RuntimeInputProbe {
	static var installed:Bool = false;
	static var state:Dynamic;
	static var controls:Controls;
	static var sourceControls:PsychControlsCompat;
	static var nightmareInput:NightmareVisionInputSystem;
	static var keyCode:Int = -1;
	static var prefix:String;
	static var phase:Int = 0;
	static var checks:Int = 0;
	static var previousTick:Int = -1;
	static var sameTickUpdates:Int = 0;
	static var complete:Bool = false;

	public static function install():Void {
		#if sys
		if (installed || !RuntimeSmokeHarness.enabled() || Sys.args().indexOf('--input-regression-probe') < 0)
			return;
		installed = true;
		FlxG.signals.preUpdate.add(checkInput);
		FlxG.signals.postUpdate.add(sendInput);
		#end
	}

	static function sendInput():Void {
		if (complete || PlayerSettings.player1 == null)
			return;
		var gameplay = Std.isOfType(FlxG.state, PlayState);
		if (!gameplay && !Std.isOfType(FlxG.state, FreeplayState))
			return;
		if (gameplay && !RuntimeSmokeHarness.songStartObserved)
			return;
		if (state != FlxG.state) {
			state = FlxG.state;
			controls = PlayerSettings.player1.controls;
			sourceControls = gameplay ? (cast FlxG.state:PlayState).psychControls : null;
			nightmareInput = gameplay && (cast FlxG.state:PlayState).nightmareVisionInputScope != null
				? (cast FlxG.state:PlayState).nightmareVisionInputScope.input : null;
			prefix = gameplay ? 'ctrl1' : 'up';
			phase = 0;
			keyCode = -1;
			var action = controls.byName.get(prefix + '-press');
			if (action != null) for (input in action.inputs) {
				switch (input.device) {
					case KEYBOARD: keyCode = input.inputID;
					default:
				}
				if (keyCode >= 0) break;
			}
			if (sourceControls != null) {
				var sourceKeys = (cast FlxG.state:PlayState).keysArray;
				keyCode = sourceKeys.length > 0 && sourceKeys[0] != null && sourceKeys[0].length > 0
					? cast sourceKeys[0][0] : -1;
			}
			if (nightmareInput != null && nightmareInput.justPressedActions.length > 0) {
				keyCode = -1;
				for (input in nightmareInput.justPressedActions[0].inputs) if (input.device == KEYBOARD) {
					keyCode = input.inputID; break;
				}
			}
			if (keyCode < 0) {
				RuntimeSmokeHarness.fail('input-probe', 'No live keyboard binding for ' + prefix);
				return;
			}
		}
		phase = phase % 4 + 1;
		if (phase == 1 || phase == 3)
			FlxG.stage.dispatchEvent(new KeyboardEvent(phase == 1 ? KeyboardEvent.KEY_DOWN : KeyboardEvent.KEY_UP,
				true, false, keyCode, keyCode));
	}

	static function checkInput():Void {
		if (complete || state != FlxG.state || phase == 0 || controls == null)
			return;
		var expectedPress = phase == 1;
		var expectedHeld = phase == 1 || phase == 2;
		var expectedRelease = phase == 3;
		for (_ in 0...2) {
			var press = nightmareInput != null ? nightmareInput.inputJustPressed(0) : sourceControls == null ? controls.checkByName(cast (prefix + '-press')) : sourceControls.NOTE_LEFT_P;
			var held = nightmareInput != null ? nightmareInput.inputPressed(0) : sourceControls == null ? controls.checkByName(cast prefix) : sourceControls.NOTE_LEFT;
			var release = nightmareInput != null ? nightmareInput.inputJustReleased(0) : sourceControls == null ? controls.checkByName(cast (prefix + '-release')) : sourceControls.NOTE_LEFT_R;
			if (press != expectedPress || held != expectedHeld || release != expectedRelease) {
				RuntimeSmokeHarness.fail('input-probe', 'Live press/hold/release mismatch at phase ' + phase
					+ ' in ' + Type.getClassName(Type.getClass(state)) + ', ticks=' + FlxG.game.ticks);
				return;
			}
		}
		if (previousTick == FlxG.game.ticks) sameTickUpdates++;
		previousTick = FlxG.game.ticks;
		checks++;
		if (checks >= 128 && phase == 4) {
			complete = true;
			RuntimeSmokeHarness.emit('input_probe_success', {checks: checks, sameTickUpdates: sameTickUpdates,
				sourceControls: sourceControls != null, nightmareInput: nightmareInput != null, keyCode: keyCode,
				state: Type.getClassName(Type.getClass(state)), muted: FlxG.sound.muted,
				backendFrameRate: FlxG.stage.frameRate});
		}
	}
}
