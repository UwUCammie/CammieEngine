package;

import flixel.FlxG;
import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;

/**
	The Psych device query order, separated from the Controls facade so other
	source dialects can share the raw keyboard/gamepad polling rules.
	Binding maps and their arrays stay live; queries never copy them.
*/
class SourceInputDevice {
	public var keyboardBinds:Map<String, Array<FlxKey>>;
	public var gamepadBinds:Map<String, Array<FlxGamepadInputID>>;
	public var controllerMode:Bool = false;

	final keyboardPoll:Array<FlxKey>->String->Bool;
	final gamepadPoll:FlxGamepadInputID->String->Bool;

	/** Optional poll functions are a headless-test seam; production defaults use FlxG. */
	public function new(keyboardBinds:Map<String, Array<FlxKey>>,
		gamepadBinds:Map<String, Array<FlxGamepadInputID>>,
		?keyboardPoll:Array<FlxKey>->String->Bool,
		?gamepadPoll:FlxGamepadInputID->String->Bool) {
		this.keyboardBinds = keyboardBinds;
		this.gamepadBinds = gamepadBinds;
		this.keyboardPoll = keyboardPoll == null ? pollKeyboard : keyboardPoll;
		this.gamepadPoll = gamepadPoll == null ? pollGamepad : gamepadPoll;
	}

	/** Query keyboard first, matching Psych's short-circuit and mode updates. */
	public function query(name:String, phase:String):Bool {
		if (name == null) return false;
		var keys = keyboardBinds == null ? null : keyboardBinds.get(name);
		if (queryKeyboard(keys, phase)) return true;
		return queryGamepad(name, phase);
	}

	/** Poll an already-captured keyboard binding array without looking it up again. */
	public function queryKeyboard(keys:Array<FlxKey>, phase:String):Bool {
		if (keys != null && keyboardPoll(keys, phase)) {
			controllerMode = false;
			return true;
		}
		return false;
	}

	/** Poll only the current gamepad binding for an action. */
	public function queryGamepad(name:String, phase:String):Bool {
		if (name == null) return false;
		var buttons = gamepadBinds == null ? null : gamepadBinds.get(name);
		if (buttons != null) {
			for (button in buttons) if (gamepadPoll(button, phase)) {
				controllerMode = true;
				return true;
			}
		}
		return false;
	}

	static function pollKeyboard(keys:Array<FlxKey>, phase:String):Bool {
		#if FLX_KEYBOARD
		if (keys == null || keys.length == 0 || FlxG.keys == null) return false;
		return switch (phase) {
			case 'justPressed': FlxG.keys.anyJustPressed(keys);
			case 'justReleased': FlxG.keys.anyJustReleased(keys);
			default: FlxG.keys.anyPressed(keys);
		};
		#else
		return false;
		#end
	}

	static function pollGamepad(button:FlxGamepadInputID, phase:String):Bool {
		#if FLX_GAMEPAD
		if (FlxG.gamepads == null) return false;
		return switch (phase) {
			case 'justPressed': FlxG.gamepads.anyJustPressed(button);
			case 'justReleased': FlxG.gamepads.anyJustReleased(button);
			default: FlxG.gamepads.anyPressed(button);
		};
		#else
		return false;
		#end
	}
}
