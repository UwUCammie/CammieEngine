package;

import PsychFlxCameraCompat.PsychFlxGCompat;
import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;

/** Owner-scoped facade for Psych 1.0.4's static backend.Controls API. */
@:keep
class PsychControlsCompat {
	static var _instance:PsychControlsCompat;
	final providedControls:Dynamic;
	var boundSourcePrefs:Dynamic;
	var sourceBindingsBound:Bool = false;
	var released:Bool = false;
	final inputDevice:SourceInputDevice;

	var _keyboardBinds:Map<String, Array<FlxKey>>;
	var _gamepadBinds:Map<String, Array<FlxGamepadInputID>>;

	/** Authored assignments update the current PlayState owner when one exists. */
	@:keep public static var instance(get, set):PsychControlsCompat;
	static function get_instance():PsychControlsCompat {
		var play = activePlayState();
		var prefs = play == null ? null : readField(play, 'psychClientPrefs');
		if (play != null && prefs != null) {
			var current = readField(play, 'psychControls');
			if (current != null && !cast(current, PsychControlsCompat).released) return cast current;
			var created = new PsychControlsCompat(null, prefs);
			try Reflect.setProperty(play, 'psychControls', created) catch (_:Dynamic) {}
			return created;
		}
		if (_instance != null && _instance.released) _instance = null;
		if (_instance == null) _instance = new PsychControlsCompat();
		return _instance;
	}

	static function set_instance(value:PsychControlsCompat):PsychControlsCompat {
		var play = activePlayState();
		var prefs = play == null ? null : readField(play, 'psychClientPrefs');
		if (play != null && prefs != null) {
			try Reflect.setProperty(play, 'psychControls', value) catch (_:Dynamic) {}
		} else {
			// A detached static fallback must never keep an owner preference ledger.
			_instance = value != null && value.sourceBindingsBound
				? new PsychControlsCompat(value.providedControls) : value;
		}
		return value;
	}

	/** Psych captures the preference maps themselves; reads see live entry arrays. */
	@:keep public var keyboardBinds(get, set):Map<String, Array<FlxKey>>;
	function get_keyboardBinds():Map<String, Array<FlxKey>> return _keyboardBinds;
	function set_keyboardBinds(value:Map<String, Array<FlxKey>>):Map<String, Array<FlxKey>> {
		if (released) return null;
		_keyboardBinds = value;
		inputDevice.keyboardBinds = value;
		return value;
	}

	@:keep public var gamepadBinds(get, set):Map<String, Array<FlxGamepadInputID>>;
	function get_gamepadBinds():Map<String, Array<FlxGamepadInputID>> return _gamepadBinds;
	function set_gamepadBinds(value:Map<String, Array<FlxGamepadInputID>>):Map<String, Array<FlxGamepadInputID>> {
		if (released) return null;
		_gamepadBinds = value;
		inputDevice.gamepadBinds = value;
		return value;
	}

	@:keep public var controllerMode(get, set):Bool;
	function get_controllerMode():Bool return !released && inputDevice.controllerMode;
	function set_controllerMode(value:Bool):Bool {
		inputDevice.controllerMode = !released && value;
		return inputDevice.controllerMode;
	}

	/** Optional native-control source is used by compatibility tests and hosts. */
	public function new(?providedControls:Dynamic, ?sourcePrefs:Dynamic) {
		this.providedControls = providedControls;
		inputDevice = new SourceInputDevice(null, null);
		var prefs = sourcePrefs;
		if (prefs == null && providedControls == null) prefs = resolveSourcePrefs();
		if (prefs != null && providedControls == null) bindSourcePrefs(prefs);
	}

	/** Psych held-state query for an arbitrary named action. */
	@:keep public function pressed(name:String):Bool return query(name, 'pressed');

	/** Psych JUST_PRESSED query for an arbitrary named action. */
	@:keep public function justPressed(name:String):Bool return query(name, 'justPressed');

	/** Psych JUST_RELEASED query for an arbitrary named action. */
	@:keep public function justReleased(name:String):Bool return query(name, 'justReleased');

	/** Query the note-key arrays captured by Psych's PlayState at scene creation. */
	@:keep public function queryKeyboard(keys:Array<FlxKey>, phase:String):Bool
		return !released && inputDevice.queryKeyboard(keys, phase);

	/** Query one named action on gamepads without also polling keyboard bindings. */
	@:keep public function queryGamepad(name:String, phase:String):Bool
		return !released && inputDevice.queryGamepad(name, phase);

	@:keep public function keyboardJustPressed(keys:Array<FlxKey>):Bool
		return queryKeyboard(keys, 'justPressed');

	@:keep public function keyboardJustReleased(keys:Array<FlxKey>):Bool
		return queryKeyboard(keys, 'justReleased');

	/** Device-only phase queries keep current keyboard remaps out of gamepad edges. */
	@:keep public function gamepadJustPressed(name:String):Bool
		return queryGamepad(name, 'justPressed');

	@:keep public function gamepadJustReleased(name:String):Bool
		return queryGamepad(name, 'justReleased');

	/** Detach owner maps when the owning chart scope is destroyed. */
	@:keep public function release():Void {
		if (released) return;
		released = true;
		boundSourcePrefs = null;
		sourceBindingsBound = false;
		_keyboardBinds = null;
		_gamepadBinds = null;
		inputDevice.keyboardBinds = null;
		inputDevice.gamepadBinds = null;
		inputDevice.controllerMode = false;
	}

	@:keep public var UI_UP(get, never):Bool;
	function get_UI_UP():Bool return pressed('ui_up');
	@:keep public var UI_DOWN(get, never):Bool;
	function get_UI_DOWN():Bool return pressed('ui_down');
	@:keep public var UI_LEFT(get, never):Bool;
	function get_UI_LEFT():Bool return pressed('ui_left');
	@:keep public var UI_RIGHT(get, never):Bool;
	function get_UI_RIGHT():Bool return pressed('ui_right');
	@:keep public var UI_UP_P(get, never):Bool;
	function get_UI_UP_P():Bool return justPressed('ui_up');
	@:keep public var UI_DOWN_P(get, never):Bool;
	function get_UI_DOWN_P():Bool return justPressed('ui_down');
	@:keep public var UI_LEFT_P(get, never):Bool;
	function get_UI_LEFT_P():Bool return justPressed('ui_left');
	@:keep public var UI_RIGHT_P(get, never):Bool;
	function get_UI_RIGHT_P():Bool return justPressed('ui_right');
	@:keep public var UI_UP_R(get, never):Bool;
	function get_UI_UP_R():Bool return justReleased('ui_up');
	@:keep public var UI_DOWN_R(get, never):Bool;
	function get_UI_DOWN_R():Bool return justReleased('ui_down');
	@:keep public var UI_LEFT_R(get, never):Bool;
	function get_UI_LEFT_R():Bool return justReleased('ui_left');
	@:keep public var UI_RIGHT_R(get, never):Bool;
	function get_UI_RIGHT_R():Bool return justReleased('ui_right');

	@:keep public var NOTE_UP(get, never):Bool;
	function get_NOTE_UP():Bool return pressed('note_up');
	@:keep public var NOTE_DOWN(get, never):Bool;
	function get_NOTE_DOWN():Bool return pressed('note_down');
	@:keep public var NOTE_LEFT(get, never):Bool;
	function get_NOTE_LEFT():Bool return pressed('note_left');
	@:keep public var NOTE_RIGHT(get, never):Bool;
	function get_NOTE_RIGHT():Bool return pressed('note_right');
	@:keep public var NOTE_UP_P(get, never):Bool;
	function get_NOTE_UP_P():Bool return justPressed('note_up');
	@:keep public var NOTE_DOWN_P(get, never):Bool;
	function get_NOTE_DOWN_P():Bool return justPressed('note_down');
	@:keep public var NOTE_LEFT_P(get, never):Bool;
	function get_NOTE_LEFT_P():Bool return justPressed('note_left');
	@:keep public var NOTE_RIGHT_P(get, never):Bool;
	function get_NOTE_RIGHT_P():Bool return justPressed('note_right');
	@:keep public var NOTE_UP_R(get, never):Bool;
	function get_NOTE_UP_R():Bool return justReleased('note_up');
	@:keep public var NOTE_DOWN_R(get, never):Bool;
	function get_NOTE_DOWN_R():Bool return justReleased('note_down');
	@:keep public var NOTE_LEFT_R(get, never):Bool;
	function get_NOTE_LEFT_R():Bool return justReleased('note_left');
	@:keep public var NOTE_RIGHT_R(get, never):Bool;
	function get_NOTE_RIGHT_R():Bool return justReleased('note_right');

	@:keep public var ACCEPT(get, never):Bool;
	function get_ACCEPT():Bool return justPressed('accept');
	@:keep public var BACK(get, never):Bool;
	function get_BACK():Bool return justPressed('back');
	@:keep public var PAUSE(get, never):Bool;
	function get_PAUSE():Bool return justPressed('pause');
	@:keep public var RESET(get, never):Bool;
	function get_RESET():Bool return justPressed('reset');

	function query(name:String, phase:String):Bool {
		if (released || name == null) return false;
		if (providedControls == null && sourceBindingsBound) return inputDevice.query(name, phase);
		return queryNativeControls(resolveControls(), name, phase);
	}

	function bindSourcePrefs(prefs:Dynamic):Void {
		boundSourcePrefs = prefs;
		sourceBindingsBound = true;
		keyboardBinds = cast readField(prefs, 'keyBinds');
		gamepadBinds = cast readField(prefs, 'gamepadBinds');
	}

	function resolveSourcePrefs():Dynamic {
		if (boundSourcePrefs != null) return boundSourcePrefs;
		var play = activePlayState();
		return play == null ? null : readField(play, 'psychClientPrefs');
	}

	function resolveControls():Dynamic {
		if (providedControls != null) return providedControls;
		#if cpp
		// MusicBeatState controls are private and inline on native builds; preserve
		// the same live player binding lookup used by Psych's static fallback.
		if (PlayerSettings.player1 != null && PlayerSettings.player1.controls != null)
			return PlayerSettings.player1.controls;
		#end
		var state:Dynamic = null;
		try state = PsychFlxGCompat.state catch (_:Dynamic) {}
		if (state != null) {
			var controls = readField(state, 'controls');
			if (controls != null) return controls;
		}
		var settingsClass:Dynamic = Type.resolveClass('PlayerSettings');
		if (settingsClass == null) return null;
		var player = readField(settingsClass, 'player1');
		return player == null ? null : readField(player, 'controls');
	}

	static function queryNativeControls(controls:Dynamic, name:String, phase:String):Bool {
		if (controls == null) return false;
		var direct = switch (phase) {
			case 'justPressed': 'justPressed';
			case 'justReleased': 'justReleased';
			default: 'pressed';
		};
		if (phase == 'pressed') {
			var held = Reflect.field(controls, 'pressedByName');
			if (Reflect.isFunction(held) && invokeBool(controls, held, [name])) return true;
		}
		var directMethod = Reflect.field(controls, direct);
		if (Reflect.isFunction(directMethod) && invokeBool(controls, directMethod, [name])) return true;

		var check = Reflect.field(controls, 'checkByName');
		if (!Reflect.isFunction(check)) return false;
		var action = nativeActionName(name, phase);
		return action != null && invokeBool(controls, check, [action]);
	}

	static function nativeActionName(name:String, phase:String):Null<String> {
		var token = switch (name) {
			case 'note_left': 'ctrl1';
			case 'note_down': 'ctrl2';
			case 'note_up': 'ctrl3';
			case 'note_right': 'ctrl4';
			case 'ui_up': phase == 'pressed' ? 'up-menu-hold' : 'up-menu';
			case 'ui_down': phase == 'pressed' ? 'down-menu-hold' : 'down-menu';
			case 'ui_left': phase == 'pressed' ? 'left-menu-hold' : 'left-menu';
			case 'ui_right': phase == 'pressed' ? 'right-menu-hold' : 'right-menu';
			default: name;
		};
		if (phase == 'justReleased') {
			if (StringTools.startsWith(name, 'ui_') || name == 'accept' || name == 'back'
				|| name == 'pause' || name == 'reset') return null;
			return token + '-release';
		}
		if (phase == 'justPressed' && StringTools.startsWith(name, 'note_')) return token + '-press';
		return token;
	}

	static function invokeBool(receiver:Dynamic, method:Dynamic, args:Array<Dynamic>):Bool {
		try return Reflect.callMethod(receiver, method, args) == true catch (_:Dynamic) return false;
	}

	static function activePlayState():Dynamic {
		var playClass = Type.resolveClass('PlayState');
		return playClass == null ? null : readField(playClass, 'instance');
	}

	static function readField(value:Dynamic, name:String):Dynamic {
		if (value == null) return null;
		try return Reflect.getProperty(value, name) catch (_:Dynamic) return null;
	}
}
