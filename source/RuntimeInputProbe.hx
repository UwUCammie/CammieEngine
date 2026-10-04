package;

import flixel.FlxG;
import openfl.events.KeyboardEvent;

/** Opt-in native regression probe; presses pass through the ordinary stage
 * and live player bindings without desktop focus or saved-setting changes. */
@:access(Controls)
@:access(RuntimeSmokeHarness)
class RuntimeInputProbe {
	static var installed:Bool = false;
	static var state:Dynamic;
	static var controls:Controls;
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
			prefix = gameplay ? 'ctrl1' : 'up';
			phase = 0;
			var action = controls.byName.get(prefix + '-press');
			if (action != null) for (input in action.inputs) {
				switch (input.device) {
					case KEYBOARD: keyCode = input.inputID;
					default:
				}
				if (keyCode >= 0) break;
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
			if (controls.checkByName(cast (prefix + '-press')) != expectedPress
				|| controls.checkByName(cast prefix) != expectedHeld
				|| controls.checkByName(cast (prefix + '-release')) != expectedRelease) {
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
				state: Type.getClassName(Type.getClass(state)), muted: FlxG.sound.muted,
				backendFrameRate: FlxG.stage.frameRate});
		}
	}
}
