package;

// Event/action contract ported from NV 733165c; the native host owns frame draining.

import flixel.FlxG;
import nightmarevision.input.NightmareVisionInputEnums.Device;

import openfl.events.KeyboardEvent;
import openfl.events.EventType;
import openfl.events.EventDispatcher;

import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.gamepad.FlxGamepad;
import flixel.input.FlxInput.FlxInputState;
import flixel.input.actions.FlxActionInput;
import flixel.input.actions.FlxAction.FlxActionDigital;

import NightmareVisionControls;
import nightmarevision.input.NightmareVisionInputEnums.Action;

import lime.system.System;
#if FLX_GAMEINPUT_API
import lime.ui.GamepadButton;
import lime.ui.GamepadAxis;



typedef GamepadEvent<T> = (id:T) -> Void;
typedef AxisEvent<T> = (id:T, value:Float) -> Void;
#end

/**
 * An `NightmareVisionInputSystem` object tracks note inputs with events
 * You can add listeners to check for when an input is pressed and released
 * ```haxe
 * input = new NightmareVisionInputSystem();
 * input.addEventListener(NightmareVisionInputEvent.INPUT_PRESSED, onInputPressed);
 * input.addEventListener(NightmareVisionInputEvent.INPUT_RELEASED, onInputReleased);
 * ```
 * Input events can also be cancelled
 * ```haxe
 * function onInputPressed(event:NightmareVisionInputEvent)
 * {
 *  if (badInput)
 *      event.preventDefault();
 * }
 * ```
 */
@:keep
class NightmareVisionInputSystem extends EventDispatcher implements flixel.util.FlxDestroyUtil.IFlxDestroyable
{
	/**
	 * The list of actions checked for, in order of their note direction
	 */
	public static var ACTION_LIST:Array<Action> = [NOTE_LEFT, NOTE_DOWN, NOTE_UP, NOTE_RIGHT];

	/**
	 * The current controls instance used for this input system
	 */
	public var controls:NightmareVisionControls;

	// the actions themselves
	public var pressedActions:Array<FlxActionDigital> = [];
	public var justPressedActions:Array<FlxActionDigital> = [];
	public var justReleasedActions:Array<FlxActionDigital> = [];

	// the index of these arrays correlates to the input ID of the input (ex: justPressedKeyInputs[FlxKey.DOWN] would exist if that key was bound)
	// specific device action inputs
	var justPressedKeyInputs:Array<Array<FlxActionInput>> = [];
	var justReleasedKeyInputs:Array<Array<FlxActionInput>> = [];

	// note incase if matters to anyone: this counts all non-keyboard inputs under `FlxActionInput.device`
	var justPressedGamepadInputs:Array<Array<FlxActionInput>> = [];
	var justReleasedGamepadInputs:Array<Array<FlxActionInput>> = [];

	// cleared out every frame
	var awaitingEvents:Array<NightmareVisionInputEvent> = [];

	#if FLX_GAMEINPUT_API
	var awaitingAxisEvents:Array<{id:FlxGamepadInputID, gamepad:FlxGamepad, timer:Float}> = [];

	@:noCompletion
	var _gamepadMap:Map<FlxGamepad,
		{
			up:GamepadEvent<GamepadButton>,
			down:GamepadEvent<GamepadButton>,
			axis:AxisEvent<GamepadAxis>,
		}> = [];
	#end

	/**
	 * Creates a new input system
	 * @param controls
	 */
	public function new(?controls:NightmareVisionControls, attachDevices:Bool = true, ?actionList:Array<Action>)
	{
		super();

		this.controls = controls != null ? controls : NightmareVisionControls.instance;
		if (this.controls == null) throw "Missing Control Bind.\n[If your bind is modded-in, Was it named correctly?]";

		for (noteData => action in (actionList == null ? ACTION_LIST : actionList))
		{
			final pressed:Action = action;
			final justPressed:Action = '$action-press';
			final justReleased:Action = '$action-release';

			pressedActions[noteData] = this.controls.actions.get(pressed) ?? throw "Missing Control Bind.\n[If your bind is modded-in, Was it named correctly?]";
			justPressedActions[noteData] = this.controls.actions.get(justPressed) ?? throw "Missing Control Bind.\n[If your bind is modded-in, Was it named correctly?]";
			justReleasedActions[noteData] = this.controls.actions.get(justReleased) ?? throw "Missing Control Bind.\n[If your bind is modded-in, Was it named correctly?]";

			justPressedKeyInputs[noteData] = [];
			justReleasedKeyInputs[noteData] = [];

			justPressedGamepadInputs[noteData] = [];
			justReleasedGamepadInputs[noteData] = [];

			// assign each input to its direction and inputID
			inline function findInputs(action:FlxActionDigital, keys:Array<Array<FlxActionInput>>, gamepad:Array<Array<FlxActionInput>>)
			{
				for (input in action.inputs)
				{
					switch input.device
					{
						case KEYBOARD:
							keys[noteData][input.inputID] = input;
						case _:
							gamepad[noteData][input.inputID] = input;
					}
				}
			}

			findInputs(justPressedActions[noteData], justPressedKeyInputs, justPressedGamepadInputs);
			findInputs(justReleasedActions[noteData], justReleasedKeyInputs, justReleasedGamepadInputs);
		}

		if (attachDevices) attachDeviceListeners();
	}

	var devicesAttached:Bool = false;
	function attachDeviceListeners():Void {
		if (devicesAttached) return;
		devicesAttached = true;
		FlxG.stage.addEventListener(KeyboardEvent.KEY_DOWN, onKeyboardEvent);
		FlxG.stage.addEventListener(KeyboardEvent.KEY_UP, onKeyboardEvent);
		#if FLX_GAMEINPUT_API
		for (id in this.controls.gamepadsAdded)
			addGamepad(FlxG.gamepads.getByID(id));
		FlxG.gamepads.deviceConnected.add(addGamepad);
		FlxG.gamepads.deviceDisconnected.add(removeGamepad);
		#end
	}

	/**
	 * Checks if a note direction is pressed
	 * @param noteData
	 */
	public function inputPressed(noteData:Int)
	{
		return pressedActions[noteData].check();
	}

	/**
	 * Checks if a note direction has just been pressed
	 * @param noteData
	 */
	public function inputJustPressed(noteData:Int)
	{
		return justPressedActions[noteData].check();
	}

	/**
	 * Checks if a note direction has just been released
	 * @param noteData
	 */
	public function inputJustReleased(noteData:Int)
	{
		return justReleasedActions[noteData].check();
	}

	/**
	 * Dispatches all awaiting input events
	 */
	@:nullSafety(Off)
	public function update():Void
	{
		#if FLX_GAMEINPUT_API
		while (awaitingAxisEvents.length > 0)
		{
			final info = awaitingAxisEvents.shift();
			if (info.gamepad.checkStatus(info.id, JUST_PRESSED)) onInputEvent(NightmareVisionInputEvent.INPUT_PRESSED, Gamepad(info.gamepad.id), info.id, info.timer);
			else if (info.gamepad.checkStatus(info.id, JUST_RELEASED)) onInputEvent(NightmareVisionInputEvent.INPUT_RELEASED, Gamepad(info.gamepad.id), info.id, info.timer);
		}
		#end
		while (awaitingEvents.length > 0)
			dispatchEvent(awaitingEvents.shift());
	}

	public function destroy():Void
	{
		if (!devicesAttached) return;
		devicesAttached = false;
		FlxG.stage.removeEventListener(KeyboardEvent.KEY_DOWN, onKeyboardEvent);
		FlxG.stage.removeEventListener(KeyboardEvent.KEY_UP, onKeyboardEvent);
		#if FLX_GAMEINPUT_API
		for (gamepad in _gamepadMap.keys())
			removeGamepad(gamepad);
		FlxG.gamepads.deviceConnected.remove(addGamepad);
		FlxG.gamepads.deviceDisconnected.remove(removeGamepad);
		#end
	}

	/** Owner teardown additionally releases script listeners and captured scene actions. */
	@:allow(NightmareVisionInputScope)
	function releaseOwner():Void {
		destroy();
		@:privateAccess __eventMap = null;
		@:privateAccess __iterators = null;
		awaitingEvents.resize(0);
		#if FLX_GAMEINPUT_API
		awaitingAxisEvents.resize(0);
		#end
		pressedActions.resize(0); justPressedActions.resize(0); justReleasedActions.resize(0);
		justPressedKeyInputs.resize(0); justReleasedKeyInputs.resize(0);
		justPressedGamepadInputs.resize(0); justReleasedGamepadInputs.resize(0);
		controls = null;
	}

	@:access(flixel.input.FlxKeyManager.resolveKeyCode)
	function onKeyboardEvent(event:KeyboardEvent)
	{
		if (event.keyCode > -1) onInputEvent(event.type == KeyboardEvent.KEY_DOWN ? NightmareVisionInputEvent.INPUT_PRESSED : NightmareVisionInputEvent.INPUT_RELEASED, Keys, FlxG.keys.resolveKeyCode(event), System.getTimer());
	}

	#if FLX_GAMEINPUT_API
	static function limeGamepadOf(gamepad:FlxGamepad):Null<lime.ui.Gamepad> {
		if (gamepad == null) return null;
		@:privateAccess return gamepad._device == null ? null : gamepad._device.__gamepad;
	}

	function addGamepad(gamepad:FlxGamepad)
	{
		if (gamepad != null && !_gamepadMap.exists(gamepad))
		{
			final limeGamepad = limeGamepadOf(gamepad);
			if (limeGamepad != null)
			{
				final events =
					{
						down: button -> onButtonEvent(NightmareVisionInputEvent.INPUT_PRESSED, gamepad, button),
						up: button -> onButtonEvent(NightmareVisionInputEvent.INPUT_RELEASED, gamepad, button),
						axis: (axis, value) -> onAxisEvent(gamepad, axis, value),
					}
				_gamepadMap.set(gamepad, events);
				limeGamepad.onButtonDown.add(events.down);
				limeGamepad.onButtonUp.add(events.up);
				limeGamepad.onAxisMove.add(events.axis);
			}
		}
	}

	function removeGamepad(gamepad:FlxGamepad)
	{
		final events = _gamepadMap.get(gamepad);
		@:nullSafety(Off)
		if (events != null)
		{
			final limeGamepad = limeGamepadOf(gamepad);
			limeGamepad?.onButtonDown.remove(events.down);
			limeGamepad?.onButtonUp.remove(events.up);
			limeGamepad?.onAxisMove.remove(events.axis);
			_gamepadMap.remove(gamepad);
		}
	}

	function onAxisEvent(gamepad:FlxGamepad, axis:GamepadAxis, value:Float):Void
	{
		final id = gamepad.mapping.getID(cast axis);
		if (id != NONE) awaitingAxisEvents.push({id: id, gamepad: gamepad, timer: System.getTimer()});
	}

	function onButtonEvent(event:EventType<NightmareVisionInputEvent>, gamepad:FlxGamepad, button:GamepadButton):Void
	{
		onInputEvent(event, Gamepad(gamepad.id), gamepad.mapping.getID(button + 6), System.getTimer());
	}
	#end

	function onInputEvent(event:EventType<NightmareVisionInputEvent>, device:Device, inputID:Int, timer:Float)
	{
		final inputState:FlxInputState = switch event
		{
			case NightmareVisionInputEvent.INPUT_PRESSED: JUST_PRESSED;
			case NightmareVisionInputEvent.INPUT_RELEASED: JUST_RELEASED;
			default: throw "Invalid Event";
		}

		switch device
		{
			case Keys:
				#if debug
				@:privateAccess if (!FlxG.keys._keyListMap.exists(inputID)) return;
				#end
				// with lime, it counts repeated key inputs when you hold down the key.
				if (!FlxG.keys.checkStatus(inputID, inputState)) return;
			case _:
		}

		final inputList:Array<Array<FlxActionInput>> = switch event
		{
			case NightmareVisionInputEvent.INPUT_PRESSED:
				switch device
				{
					case Keys: justPressedKeyInputs;
					case Gamepad(_): justPressedGamepadInputs;
				}
			case NightmareVisionInputEvent.INPUT_RELEASED:
				switch device
				{
					case Keys: justReleasedKeyInputs;
					case Gamepad(_): justReleasedGamepadInputs;
				}
			default:
				throw "Invalid Event";
		}

		for (noteData => inputs in inputList)
		{
			@:nullSafety(Off)
			if (inputs[inputID] != null)
			{
				awaitingEvents.push(new NightmareVisionInputEvent(event, false, true, noteData, device, inputID, timer));
				// if we don't break here, then people would be able to bind multiple controls to the same key
				// i don't know if we would want that and it's kinda cheaty so i'll just break
				break;
			}
		}
	}
}
