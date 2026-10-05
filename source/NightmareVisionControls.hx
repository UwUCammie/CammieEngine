package;

import flixel.FlxG;
import flixel.input.FlxInput.FlxInputState;
import flixel.input.actions.FlxAction.FlxActionDigital;
import flixel.input.actions.FlxActionInput.FlxActionInput;
import flixel.input.actions.FlxActionInput.FlxInputDevice;
import flixel.input.actions.FlxActionInput.FlxInputDeviceID;
import flixel.input.actions.FlxActionSet;
import flixel.input.gamepad.FlxGamepad;
import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;
import nightmarevision.input.NightmareVisionInputEnums.Action;
import nightmarevision.input.NightmareVisionInputEnums.Control;
import nightmarevision.input.NightmareVisionInputEnums.Device;
import nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme;

/** Owner-scoped port of Nightmare Vision's source Controls action registry. */
@:keep
class NightmareVisionControls extends FlxActionSet {
	static var instanceResolver:Void->NightmareVisionControls;
	static var instanceWriter:NightmareVisionControls->Void;
	static var preferencesResolver:Void->Dynamic;
	static var gamepadHooksInstalled:Bool = false;
	static var hookedGamepadManager:Dynamic;

	/** The active owner supplies these delegates; this facade never stores a scene. */
	public static var instance(get, set):NightmareVisionControls;

	static function get_instance():NightmareVisionControls {
		if (instanceResolver == null)
			throw '[nmv-controls-unsupported] Controls.instance has no active-owner resolver';
		var value = instanceResolver();
		if (value == null)
			throw '[nmv-controls-unsupported] Controls.instance has no active owner';
		return value;
	}

	static function set_instance(value:NightmareVisionControls):NightmareVisionControls {
		if (instanceWriter == null)
			throw '[nmv-controls-unsupported] Controls.instance has no active-owner writer';
		instanceWriter(value);
		return value;
	}

	/**
	 * Configure dynamic active-owner access. Resolvers should look up the current
	 * owner each call instead of closing over a scene that can later be destroyed.
	 */
	public static function setInstanceAccessors(resolve:Void->NightmareVisionControls,
		write:NightmareVisionControls->Void, ?resolvePreferences:Void->Dynamic):Void {
		if (resolve == null || write == null)
			throw '[nmv-controls] Both active-owner accessors are required';
		instanceResolver = resolve;
		instanceWriter = write;
		preferencesResolver = resolvePreferences;
	}

	/** Remove integration references after the host has cleared its active owner. */
	public static function clearInstanceAccessors():Void {
		detachGamepadHooks();
		instanceResolver = null;
		instanceWriter = null;
		preferencesResolver = null;
	}

	static function detachGamepadHooks():Void {
		if (hookedGamepadManager != null) {
			hookedGamepadManager.deviceConnected.remove(gamepadConnected);
			hookedGamepadManager.deviceDisconnected.remove(gamepadDisconnected);
		}
		hookedGamepadManager = null;
		gamepadHooksInstalled = false;
	}

	/** The source resets this native menu grouping hook, which has no NV facade yet. */
	public static function unimplementedInitHooks():Array<String>
		return ['ControlsSubState.resetGroups'];

	static function gamepadConnected(gamepad:FlxGamepad):Void {
		if (instanceResolver == null) return;
		var current = instanceResolver();
		if (current != null) current.addDefaultGamepad(gamepad.id);
	}

	static function gamepadDisconnected(gamepad:FlxGamepad):Void {
		if (instanceResolver == null) return;
		var current = instanceResolver();
		if (current != null) current.removeGamepad(gamepad.id);
	}

	/** Construct the source singleton inside the currently scoped owner. */
	public static function init():Void {
		if (instanceResolver == null || instanceWriter == null || preferencesResolver == null)
			throw '[nmv-controls-unsupported] init requires active-owner and preferences resolvers';
		var prefs = preferencesResolver();
		if (prefs == null)
			throw '[nmv-controls-unsupported] init could not resolve owner preferences';
		var manager = FlxG.gamepads;
		if (manager == null)
			throw '[nmv-controls-unsupported] init requires the Flixel gamepad manager';

		var controls = new NightmareVisionControls('player', Solo, prefs);
		controls.customActions.clear();
		instance = controls;
		for (id in 0...manager.numActiveGamepads)
			if (manager.getByID(id) != null) controls.addDefaultGamepad(id);

		if (gamepadHooksInstalled && hookedGamepadManager != manager) detachGamepadHooks();
		if (!gamepadHooksInstalled) {
			manager.deviceConnected.add(gamepadConnected);
			manager.deviceDisconnected.add(gamepadDisconnected);
			hookedGamepadManager = manager;
			gamepadHooksInstalled = true;
		}
		// The pinned donor also calls ControlsSubState.resetGroups() here. The
		// native options menu is outside this owner-scoped facade.
	}

	var _ui_up = new FlxActionDigital(Action.UI_UP);
	var _ui_left = new FlxActionDigital(Action.UI_LEFT);
	var _ui_right = new FlxActionDigital(Action.UI_RIGHT);
	var _ui_down = new FlxActionDigital(Action.UI_DOWN);
	var _ui_upP = new FlxActionDigital(Action.UI_UP_P);
	var _ui_leftP = new FlxActionDigital(Action.UI_LEFT_P);
	var _ui_rightP = new FlxActionDigital(Action.UI_RIGHT_P);
	var _ui_downP = new FlxActionDigital(Action.UI_DOWN_P);
	var _ui_upR = new FlxActionDigital(Action.UI_UP_R);
	var _ui_leftR = new FlxActionDigital(Action.UI_LEFT_R);
	var _ui_rightR = new FlxActionDigital(Action.UI_RIGHT_R);
	var _ui_downR = new FlxActionDigital(Action.UI_DOWN_R);

	var _note_up = new FlxActionDigital(Action.NOTE_UP);
	var _note_left = new FlxActionDigital(Action.NOTE_LEFT);
	var _note_right = new FlxActionDigital(Action.NOTE_RIGHT);
	var _note_down = new FlxActionDigital(Action.NOTE_DOWN);
	var _note_upP = new FlxActionDigital(Action.NOTE_UP_P);
	var _note_leftP = new FlxActionDigital(Action.NOTE_LEFT_P);
	var _note_rightP = new FlxActionDigital(Action.NOTE_RIGHT_P);
	var _note_downP = new FlxActionDigital(Action.NOTE_DOWN_P);
	var _note_upR = new FlxActionDigital(Action.NOTE_UP_R);
	var _note_leftR = new FlxActionDigital(Action.NOTE_LEFT_R);
	var _note_rightR = new FlxActionDigital(Action.NOTE_RIGHT_R);
	var _note_downR = new FlxActionDigital(Action.NOTE_DOWN_R);

	var _note_dodge = new FlxActionDigital(Action.NOTE_DODGE);
	var _note_dodgeP = new FlxActionDigital(Action.NOTE_DODGE_P);
	var _note_dodgeR = new FlxActionDigital(Action.NOTE_DODGE_R);

	var _accept = new FlxActionDigital(Action.ACCEPT);
	var _back = new FlxActionDigital(Action.BACK);
	var _pause = new FlxActionDigital(Action.PAUSE);
	var _reset = new FlxActionDigital(Action.RESET);
	var _fullscreen = new FlxActionDigital(Action.FULLSCREEN);
	var switch_debug_display = new FlxActionDigital(Action.SWITCH_DEBUG_DISPLAY);
	var _soft_reload = new FlxActionDigital(Action.SOFT_RELOAD);
	var _hard_reload = new FlxActionDigital(Action.HARD_RELOAD);

	public var actions:Map<Action, FlxActionDigital> = new Map<Action, FlxActionDigital>();
	public var customActions:Map<Action, FlxActionDigital> = new Map<Action, FlxActionDigital>();
	public var gamepadsAdded:Array<Int> = [];
	public var keyboardScheme:KeyboardScheme = None;

	var ownerPrefs:Dynamic;
	var released:Bool = false;

	public var UI_UP(get, never):Bool;
	inline function get_UI_UP():Bool return _ui_up.check();
	public var UI_LEFT(get, never):Bool;
	inline function get_UI_LEFT():Bool return _ui_left.check();
	public var UI_RIGHT(get, never):Bool;
	inline function get_UI_RIGHT():Bool return _ui_right.check();
	public var UI_DOWN(get, never):Bool;
	inline function get_UI_DOWN():Bool return _ui_down.check();
	public var UI_UP_P(get, never):Bool;
	inline function get_UI_UP_P():Bool return _ui_upP.check();
	public var UI_LEFT_P(get, never):Bool;
	inline function get_UI_LEFT_P():Bool return _ui_leftP.check();
	public var UI_RIGHT_P(get, never):Bool;
	inline function get_UI_RIGHT_P():Bool return _ui_rightP.check();
	public var UI_DOWN_P(get, never):Bool;
	inline function get_UI_DOWN_P():Bool return _ui_downP.check();
	public var UI_UP_R(get, never):Bool;
	inline function get_UI_UP_R():Bool return _ui_upR.check();
	public var UI_LEFT_R(get, never):Bool;
	inline function get_UI_LEFT_R():Bool return _ui_leftR.check();
	public var UI_RIGHT_R(get, never):Bool;
	inline function get_UI_RIGHT_R():Bool return _ui_rightR.check();
	public var UI_DOWN_R(get, never):Bool;
	inline function get_UI_DOWN_R():Bool return _ui_downR.check();

	public var NOTE_UP(get, never):Bool;
	inline function get_NOTE_UP():Bool return _note_up.check();
	public var NOTE_LEFT(get, never):Bool;
	inline function get_NOTE_LEFT():Bool return _note_left.check();
	public var NOTE_RIGHT(get, never):Bool;
	inline function get_NOTE_RIGHT():Bool return _note_right.check();
	public var NOTE_DOWN(get, never):Bool;
	inline function get_NOTE_DOWN():Bool return _note_down.check();
	public var NOTE_UP_P(get, never):Bool;
	inline function get_NOTE_UP_P():Bool return _note_upP.check();
	public var NOTE_LEFT_P(get, never):Bool;
	inline function get_NOTE_LEFT_P():Bool return _note_leftP.check();
	public var NOTE_RIGHT_P(get, never):Bool;
	inline function get_NOTE_RIGHT_P():Bool return _note_rightP.check();
	public var NOTE_DOWN_P(get, never):Bool;
	inline function get_NOTE_DOWN_P():Bool return _note_downP.check();
	public var NOTE_UP_R(get, never):Bool;
	inline function get_NOTE_UP_R():Bool return _note_upR.check();
	public var NOTE_LEFT_R(get, never):Bool;
	inline function get_NOTE_LEFT_R():Bool return _note_leftR.check();
	public var NOTE_RIGHT_R(get, never):Bool;
	inline function get_NOTE_RIGHT_R():Bool return _note_rightR.check();
	public var NOTE_DOWN_R(get, never):Bool;
	inline function get_NOTE_DOWN_R():Bool return _note_downR.check();

	public var NOTE_DODGE(get, never):Bool;
	inline function get_NOTE_DODGE():Bool return _note_dodge.check();
	public var NOTE_DODGE_P(get, never):Bool;
	inline function get_NOTE_DODGE_P():Bool return _note_dodgeP.check();
	public var NOTE_DODGE_R(get, never):Bool;
	inline function get_NOTE_DODGE_R():Bool return _note_dodgeR.check();
	public var ACCEPT(get, never):Bool;
	inline function get_ACCEPT():Bool return _accept.check();
	public var BACK(get, never):Bool;
	inline function get_BACK():Bool return _back.check();
	public var PAUSE(get, never):Bool;
	inline function get_PAUSE():Bool return _pause.check();
	public var RESET(get, never):Bool;
	inline function get_RESET():Bool return _reset.check();
	public var FULLSCREEN(get, never):Bool;
	inline function get_FULLSCREEN():Bool return _fullscreen.check();
	public var SWITCH_DEBUG_DISPLAY(get, never):Bool;
	inline function get_SWITCH_DEBUG_DISPLAY():Bool return switch_debug_display.check();
	public var SOFT_RELOAD(get, never):Bool;
	inline function get_SOFT_RELOAD():Bool return _soft_reload.check();
	public var HARD_RELOAD(get, never):Bool;
	inline function get_HARD_RELOAD():Bool return _hard_reload.check();

	/** `ownerPrefs` is the current imported owner's ClientPrefs-shaped view. */
	public function new(name:String, scheme:KeyboardScheme = None, ?ownerPrefs:Dynamic) {
		super(name);
		this.ownerPrefs = ownerPrefs;

		for (action in [
			_ui_up, _ui_left, _ui_right, _ui_down,
			_ui_upP, _ui_leftP, _ui_rightP, _ui_downP,
			_ui_upR, _ui_leftR, _ui_rightR, _ui_downR,
			_note_up, _note_left, _note_right, _note_down,
			_note_upP, _note_leftP, _note_rightP, _note_downP,
			_note_upR, _note_leftR, _note_rightR, _note_downR,
			_note_dodge, _note_dodgeP, _note_dodgeR,
			_accept, _back, _pause, _reset, _fullscreen, switch_debug_display,
			_soft_reload, _hard_reload
		]) add(action);

		for (action in digitalActions) actions.set(cast action.name, action);
		setKeyboardScheme(scheme, false);
	}

	function getActionFromControl(control:Control):FlxActionDigital {
		return switch (control) {
			case UI_UP: _ui_up;
			case UI_DOWN: _ui_down;
			case UI_LEFT: _ui_left;
			case UI_RIGHT: _ui_right;
			case NOTE_UP: _note_up;
			case NOTE_DOWN: _note_down;
			case NOTE_LEFT: _note_left;
			case NOTE_RIGHT: _note_right;
			case NOTE_DODGE: _note_dodge;
			case ACCEPT: _accept;
			case BACK: _back;
			case PAUSE: _pause;
			case RESET: _reset;
			case FULLSCREEN: _fullscreen;
			case SWITCH_DEBUG_DISPLAY: switch_debug_display;
			case SOFT_RELOAD: _soft_reload;
			case HARD_RELOAD: _hard_reload;
		};
	}

	function forEachBound(control:Control, func:FlxActionDigital->FlxInputState->Void):Void {
		switch (control) {
			case UI_UP: func(_ui_up, PRESSED); func(_ui_upP, JUST_PRESSED); func(_ui_upR, JUST_RELEASED);
			case UI_LEFT: func(_ui_left, PRESSED); func(_ui_leftP, JUST_PRESSED); func(_ui_leftR, JUST_RELEASED);
			case UI_RIGHT: func(_ui_right, PRESSED); func(_ui_rightP, JUST_PRESSED); func(_ui_rightR, JUST_RELEASED);
			case UI_DOWN: func(_ui_down, PRESSED); func(_ui_downP, JUST_PRESSED); func(_ui_downR, JUST_RELEASED);
			case NOTE_UP: func(_note_up, PRESSED); func(_note_upP, JUST_PRESSED); func(_note_upR, JUST_RELEASED);
			case NOTE_LEFT: func(_note_left, PRESSED); func(_note_leftP, JUST_PRESSED); func(_note_leftR, JUST_RELEASED);
			case NOTE_RIGHT: func(_note_right, PRESSED); func(_note_rightP, JUST_PRESSED); func(_note_rightR, JUST_RELEASED);
			case NOTE_DOWN: func(_note_down, PRESSED); func(_note_downP, JUST_PRESSED); func(_note_downR, JUST_RELEASED);
			case NOTE_DODGE: func(_note_dodge, PRESSED); func(_note_dodgeP, JUST_PRESSED); func(_note_dodgeR, JUST_RELEASED);
			case ACCEPT: func(_accept, JUST_PRESSED);
			case BACK: func(_back, JUST_PRESSED);
			case PAUSE: func(_pause, JUST_PRESSED);
			case RESET: func(_reset, JUST_PRESSED);
			case FULLSCREEN: func(_fullscreen, JUST_PRESSED);
			case SWITCH_DEBUG_DISPLAY: func(switch_debug_display, JUST_PRESSED);
			case SOFT_RELOAD: func(_soft_reload, JUST_PRESSED);
			case HARD_RELOAD: func(_hard_reload, JUST_PRESSED);
		}
	}

	public function copyFrom(controls:NightmareVisionControls, ?device:Device):Void {
		for (name => action in controls.actions) {
			for (input in action.inputs) {
				if (device == null || isDevice(input, device)) actions.get(name).add(cast input);
			}
		}

		switch (device) {
			case null:
				for (gamepad in controls.gamepadsAdded)
					if (!gamepadsAdded.contains(gamepad)) gamepadsAdded.push(gamepad);
				mergeKeyboardScheme(controls.keyboardScheme);
			case Gamepad(id):
				gamepadsAdded.push(id);
			case Keys:
				mergeKeyboardScheme(controls.keyboardScheme);
		}
	}

	function mergeKeyboardScheme(scheme:KeyboardScheme):Void {
		if (scheme != None) {
			switch (keyboardScheme) {
				case None: keyboardScheme = scheme;
				default: keyboardScheme = Custom;
			}
		}
	}

	/** Add held, press, and release actions and register the key in this owner. */
	public function addCustomKey(_name:String, _keys:Array<FlxKey>):Void {
		ensureAlive();
		if (_name == null) throw '[nmv-controls] Custom action name is null';
		if (_keys == null) throw '[nmv-controls] Custom key list is null';
		final name = _name.toLowerCase();
		var keys = _keys.copy();
		while (keys.length < 2) keys.push(FlxKey.NONE);

		var actionNormal = new FlxActionDigital(name);
		var actionPress = new FlxActionDigital(name + '-press');
		var actionRelease = new FlxActionDigital(name + '-release');
		add(actionNormal);
		add(actionPress);
		add(actionRelease);

		for (pair in [
			{key:name, action:actionNormal},
			{key:name + '-press', action:actionPress},
			{key:name + '-release', action:actionRelease}
		]) {
			var actionKey:Action = cast pair.key;
			actions.set(actionKey, pair.action);
			customActions.set(actionKey, pair.action);
		}

		addOwnerCustomKey(name, keys);
		customBind(name, keys);
	}

	public function checkCustom(_name:String):Bool {
		ensureAlive();
		final name:Action = cast _name.toLowerCase();
		var action = customActions.get(name);
		return action != null && action.check();
	}

	public function customBind(name:String, keys:Array<FlxKey>):Void {
		ensureAlive();
		if (name == null || keys == null) return;
		var copyKeys:Array<FlxKey> = keys.copy();
		copyKeys.remove(FlxKey.NONE);

		for (actionName in [name, name + '-press', name + '-release']) {
			var key:Action = cast actionName;
			var action = customActions.get(key);
			if (action == null) continue;
			var state = actionName.indexOf('-press') >= 0 ? JUST_PRESSED
				: actionName.indexOf('-release') >= 0 ? JUST_RELEASED : PRESSED;
			addKeys(action, copyKeys, state);
		}
	}

	public function bindKeys(control:Control, keys:Array<FlxKey>):Void {
		ensureAlive();
		var copyKeys:Array<FlxKey> = keys == null ? [] : keys.copy();
		copyKeys.remove(FlxKey.NONE);
		forEachBound(control, (action, state) -> addKeys(action, copyKeys, state));
	}

	public function unbindKeys(control:Control, keys:Array<FlxKey>):Void {
		ensureAlive();
		var copyKeys:Array<FlxKey> = keys == null ? [] : keys.copy();
		copyKeys.remove(FlxKey.NONE);
		forEachBound(control, (action, _) -> removeKeys(action, copyKeys));
	}

	static inline function addKeys(action:FlxActionDigital, keys:Array<FlxKey>, state:FlxInputState):Void {
		if (action == null) return;
		for (key in keys) if (key != FlxKey.NONE) action.addKey(key, state);
	}

	static function removeKeys(action:FlxActionDigital, keys:Array<FlxKey>):Void {
		var i = action.inputs.length;
		while (i-- > 0) {
			var input = action.inputs[i];
			if (input.device == FlxInputDevice.KEYBOARD && keys.indexOf(cast input.inputID) != -1) action.remove(input);
		}
	}

	public function setKeyboardScheme(scheme:KeyboardScheme, reset:Bool = true):Void {
		ensureAlive();
		if (reset) removeKeyboard();
		keyboardScheme = scheme;

		switch (scheme) {
			case Solo:
				var keysMap = getKeyboardBinds();
				bindKeys(Control.UI_UP, keysMap.get('ui_up'));
				bindKeys(Control.UI_DOWN, keysMap.get('ui_down'));
				bindKeys(Control.UI_LEFT, keysMap.get('ui_left'));
				bindKeys(Control.UI_RIGHT, keysMap.get('ui_right'));
				bindKeys(Control.NOTE_UP, keysMap.get('note_up'));
				bindKeys(Control.NOTE_DOWN, keysMap.get('note_down'));
				bindKeys(Control.NOTE_LEFT, keysMap.get('note_left'));
				bindKeys(Control.NOTE_RIGHT, keysMap.get('note_right'));
				bindKeys(Control.NOTE_DODGE, keysMap.get('note_dodge'));
				bindKeys(Control.ACCEPT, keysMap.get('accept'));
				bindKeys(Control.BACK, keysMap.get('back'));
				bindKeys(Control.PAUSE, keysMap.get('pause'));
				bindKeys(Control.RESET, keysMap.get('reset'));
				bindKeys(Control.FULLSCREEN, keysMap.get('fullscreen'));
				bindKeys(Control.SWITCH_DEBUG_DISPLAY, keysMap.get('switch_debug_display'));
				bindKeys(Control.SOFT_RELOAD, keysMap.get('soft_reload'));
				bindKeys(Control.HARD_RELOAD, keysMap.get('hard_reload'));
				for (action in customActions.keys()) {
					var actionName:String = cast action;
					if (StringTools.endsWith(actionName, '-release') || StringTools.endsWith(actionName, '-press')) continue;
					customBind(actionName, keysMap.get(actionName));
				}
			case Duo(true):
				bindKeys(Control.UI_UP, [W]);
				bindKeys(Control.UI_DOWN, [S]);
				bindKeys(Control.UI_LEFT, [A]);
				bindKeys(Control.UI_RIGHT, [D]);
				bindKeys(Control.NOTE_UP, [W]);
				bindKeys(Control.NOTE_DOWN, [S]);
				bindKeys(Control.NOTE_LEFT, [A]);
				bindKeys(Control.NOTE_RIGHT, [D]);
				bindKeys(Control.NOTE_DODGE, [SPACE]);
				bindKeys(Control.ACCEPT, [G, Z]);
				bindKeys(Control.BACK, [H, X]);
				bindKeys(Control.PAUSE, [ONE]);
				bindKeys(Control.RESET, [R]);
			case Duo(false):
				bindKeys(Control.UI_UP, [UP]);
				bindKeys(Control.UI_DOWN, [DOWN]);
				bindKeys(Control.UI_LEFT, [LEFT]);
				bindKeys(Control.UI_RIGHT, [RIGHT]);
				bindKeys(Control.NOTE_UP, [UP]);
				bindKeys(Control.NOTE_DOWN, [DOWN]);
				bindKeys(Control.NOTE_LEFT, [LEFT]);
				bindKeys(Control.NOTE_RIGHT, [RIGHT]);
				bindKeys(Control.NOTE_DODGE, [SPACE]);
				bindKeys(Control.ACCEPT, [O]);
				bindKeys(Control.BACK, [P]);
				bindKeys(Control.PAUSE, [ENTER]);
				bindKeys(Control.RESET, [BACKSPACE]);
			case None:
			case Custom:
		}
	}

	function removeKeyboard():Void {
		for (action in digitalActions) {
			var i = action.inputs.length;
			while (i-- > 0) {
				var input = action.inputs[i];
				if (input.device == FlxInputDevice.KEYBOARD) action.remove(input);
			}
		}
	}

	public function addGamepad(id:Int, ?buttonMap:Map<Control, Array<FlxGamepadInputID>>):Void {
		ensureAlive();
		gamepadsAdded.push(id);
		if (buttonMap != null) {
			for (control => buttons in buttonMap) bindButtons(control, id, buttons);
		}
	}

	function addGamepadLiteral(id:Int, ?buttonMap:Map<Control, Array<FlxGamepadInputID>>):Void {
		gamepadsAdded.push(id);
		if (buttonMap != null) {
			for (control => buttons in buttonMap) bindButtons(control, id, buttons);
		}
	}

	public function removeGamepad(deviceID:Int = FlxInputDeviceID.ALL):Void {
		ensureAlive();
		for (action in digitalActions) {
			var i = action.inputs.length;
			while (i-- > 0) {
				var input = action.inputs[i];
				if (input.device == FlxInputDevice.GAMEPAD
					&& (deviceID == FlxInputDeviceID.ALL || input.deviceID == deviceID)) action.remove(input);
			}
		}
		// Match the pinned source: ALL removes bound inputs, but removes only the ALL entry.
		gamepadsAdded.remove(deviceID);
	}

	public function addDefaultGamepad(id:Int):Void {
		var binds = getGamepadBinds();
		addGamepadLiteral(id, [
			Control.ACCEPT => [FlxGamepadInputID.ACCEPT],
			Control.BACK => [FlxGamepadInputID.CANCEL],
			Control.UI_UP => [FlxGamepadInputID.DPAD_UP, FlxGamepadInputID.LEFT_STICK_DIGITAL_UP],
			Control.UI_DOWN => [FlxGamepadInputID.DPAD_DOWN, FlxGamepadInputID.LEFT_STICK_DIGITAL_DOWN],
			Control.UI_LEFT => [FlxGamepadInputID.DPAD_LEFT, FlxGamepadInputID.LEFT_STICK_DIGITAL_LEFT],
			Control.UI_RIGHT => [FlxGamepadInputID.DPAD_RIGHT, FlxGamepadInputID.LEFT_STICK_DIGITAL_RIGHT],
			Control.NOTE_UP => binds.get(Action.NOTE_UP),
			Control.NOTE_DOWN => binds.get(Action.NOTE_DOWN),
			Control.NOTE_LEFT => binds.get(Action.NOTE_LEFT),
			Control.NOTE_RIGHT => binds.get(Action.NOTE_RIGHT),
			Control.NOTE_DODGE => binds.get(Action.NOTE_DODGE),
			Control.PAUSE => [FlxGamepadInputID.START],
			Control.RESET => [cast 8]
		]);
	}

	public function bindButtons(control:Control, id:Int, buttons:Array<FlxGamepadInputID>):Void {
		if (buttons == null) return;
		forEachBound(control, (action, state) -> addButtons(action, buttons, state, id));
	}

	public function unbindButtons(control:Control, gamepadID:Int,
		buttons:Array<FlxGamepadInputID>):Void {
		if (buttons == null) return;
		forEachBound(control, (action, _) -> removeButtons(action, gamepadID, buttons));
	}

	static inline function addButtons(action:FlxActionDigital, buttons:Array<FlxGamepadInputID>,
		state:FlxInputState, id:Int):Void {
		for (button in buttons) action.addGamepad(button, state, id);
	}

	static function removeButtons(action:FlxActionDigital, gamepadID:Int,
		buttons:Array<FlxGamepadInputID>):Void {
		var i = action.inputs.length;
		while (i-- > 0) {
			var input = action.inputs[i];
			if (isGamepad(input, gamepadID) && buttons.indexOf(cast input.inputID) != -1) action.remove(input);
		}
	}

	public function getInputsFor(control:Control, device:Device, ?list:Array<Int>):Array<Int> {
		if (list == null) list = [];
		switch (device) {
			case Keys:
				for (input in getActionFromControl(control).inputs)
					if (input.device == FlxInputDevice.KEYBOARD) list.push(input.inputID);
			case Gamepad(id):
				for (input in getActionFromControl(control).inputs)
					if (input.deviceID == id) list.push(input.inputID);
		}
		return list;
	}

	public function removeDevice(device:Device):Void {
		switch (device) {
			case Keys: setKeyboardScheme(None);
			case Gamepad(id): removeGamepad(id);
		}
	}

	public function checkByName(name:Action):Bool {
		ensureAlive();
		var action = actions.get(name);
		#if debug
		if (action == null) throw 'Invalid name: $name';
		#end
		return action != null && action.check();
	}

	static function isDevice(input:FlxActionInput, device:Device):Bool {
		return switch (device) {
			case Keys: input.device == FlxInputDevice.KEYBOARD;
			case Gamepad(id): isGamepad(input, id);
		};
	}

	static inline function isGamepad(input:FlxActionInput, deviceID:Int):Bool
		return input.device == FlxInputDevice.GAMEPAD
			&& (deviceID == FlxInputDeviceID.ALL || input.deviceID == deviceID);

	function getKeyboardBinds():Map<String, Array<FlxKey>> {
		ensureAlive();
		var value = ownerPrefs == null ? null : Reflect.field(ownerPrefs, 'keyBinds');
		if (value == null)
			throw '[nmv-controls-unsupported] Solo keyboard scheme requires owner keyBinds';
		return cast value;
	}

	function getGamepadBinds():Map<String, Array<FlxGamepadInputID>> {
		ensureAlive();
		var value = ownerPrefs == null ? null : Reflect.field(ownerPrefs, 'gamepadBinds');
		if (value == null)
			throw '[nmv-controls-unsupported] Gamepad binds require owner gamepadBinds';
		return cast value;
	}

	function addOwnerCustomKey(name:String, keys:Array<FlxKey>):Void {
		if (ownerPrefs == null)
			throw '[nmv-controls-unsupported] Custom keys require owner preferences';
		var callback = Reflect.field(ownerPrefs, 'addCustomKey');
		if (callback == null)
			throw '[nmv-controls-unsupported] Owner preferences do not implement addCustomKey';
		Reflect.callMethod(ownerPrefs, callback, [name, keys]);
	}

	function ensureAlive():Void {
		if (released) throw '[nmv-controls] Controls facade was destroyed';
	}

	override public function destroy():Void {
		if (released) return;
		released = true;
		super.destroy();
		actions.clear();
		customActions.clear();
		gamepadsAdded.resize(0);
		ownerPrefs = null;
	}
}
