package;

import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;
import haxe.ds.StringMap;
import SourceOwnerPreferences.*;

using StringTools;

/** Owner-local, mutable ClientPrefs surface for imported Psych scripts. The
	owner guard, native seeding and loose map helpers are shared with the other
	Psych-family owners through SourceOwnerPreferences. */
@:keep
class PsychOwnerClientPrefs {
	public static inline var SAVE_FIELD:String = 'psychClientPrefs';
	public static inline var VERSION:Int = 1;
	static inline var LABEL:String = 'psych-client-prefs';
	/** Exact nested string paths recognized by the compiled HScript loader. */
	public final __hscriptStringFieldPaths:Array<String> = ['data.noteSkin', 'defaultData.noteSkin'];
	static final DATA_FIELDS:Array<String> = [
		'downScroll','middleScroll','opponentStrums','showFPS','flashing','autoPause','antialiasing',
		'noteSkin','splashSkin','splashAlpha','lowQuality','shaders','cacheOnGPU','framerate','camZooms',
		'hideHud','noteOffset','arrowRGB','arrowRGBPixel','ghostTapping','timeBarType','scoreZoom',
		'noReset','healthBarAlpha','hitsoundVolume','pauseMusic','checkForUpdates','comboStacking',
		'gameplaySettings','comboOffset','ratingOffset','sickWindow','goodWindow','badWindow','safeFrames',
		'guitarHeroSustains','discordRPC','loadingScreen','language'
	];

	public var ownerRoot(default, null):String;
	/** Psych scripts can mutate this object or replace it, as in the donor API. */
	public var data:Dynamic;
	/** Stable independent source defaults used by getGameplaySetting. */
	public var defaultData:Dynamic;
	public var keyBinds:StringMap<Dynamic>;
	public var gamepadBinds:StringMap<Dynamic>;
	public var defaultKeys:StringMap<Dynamic>;
	public var defaultButtons:StringMap<Dynamic>;
	/** Convenient alias for hosts that expose a `.view`-shaped preference API. */
	public var view(get, never):Dynamic;
	/** Psych 0.x name for the shared antialiasing preference. */
	public var globalAntialiasing(get, set):Bool;
	function get_globalAntialiasing():Bool return data.antialiasing;
	function set_globalAntialiasing(value:Bool):Bool return data.antialiasing = value;

	var ownerSave:Dynamic;
	var runtimeOperations:StringMap<Array<Dynamic>->Dynamic> = new StringMap();
	var released:Bool = false;

	public function new(ownerRoot:String, ownerSave:Dynamic, ?nativeOptions:Dynamic) {
		this.ownerRoot = normalizeOwner(ownerRoot);
		requireOwnerSave(ownerSave, LABEL, true);
		this.ownerSave = ownerSave;
		defaultData = createDataDefaults();
		data = createDataDefaults();
		seedNativeOptions(data, nativeOptions, false);
		keyBinds = keyboardDefaults();
		gamepadBinds = gamepadDefaults();
		loadDefaultKeys();
	}

	/** Fresh complete Psych 1.0.4 SaveVariables-shaped defaults. */
	@:keep public static function createDataDefaults():Dynamic {
		return {
			downScroll:false, middleScroll:false, opponentStrums:true, showFPS:true,
			flashing:true, autoPause:true, antialiasing:true, noteSkin:'Default',
			splashSkin:'Psych', splashAlpha:0.6, lowQuality:false, shaders:true,
			cacheOnGPU:#if switch true #else false #end, framerate:60, camZooms:true,
			hideHud:false, noteOffset:0, arrowRGB:[
				[0xFFC24B99,0xFFFFFFFF,0xFF3C1F56], [0xFF00FFFF,0xFFFFFFFF,0xFF1542B7],
				[0xFF12FA05,0xFFFFFFFF,0xFF0A4447], [0xFFF9393F,0xFFFFFFFF,0xFF651038]
			], arrowRGBPixel:[
				[0xFFE276FF,0xFFFFF9FF,0xFF60008D], [0xFF3DCAFF,0xFFF4FFFF,0xFF003060],
				[0xFF71E300,0xFFF6FFE6,0xFF003100], [0xFFFF884E,0xFFFFFAF5,0xFF6C0000]
			],
			ghostTapping:true, timeBarType:'Time Left', scoreZoom:true, noReset:false,
			healthBarAlpha:1.0, hitsoundVolume:0.0, pauseMusic:'Tea Time',
			checkForUpdates:true, comboStacking:true,
			gameplaySettings:gameplayDefaults(), comboOffset:[0,0,0,0], ratingOffset:0,
			sickWindow:45.0, goodWindow:90.0, badWindow:135.0, safeFrames:10.0,
			guitarHeroSustains:true, discordRPC:true, loadingScreen:true, language:'en-US'
		};
	}

	function get_view():Dynamic return this;

	/** Reuse this mutable owner view only for its normalized import root. */
	public function canReuseFor(owner:String):Bool {
		if (released) return false;
		try return normalizeOwner(owner) == ownerRoot catch (_:Dynamic) return false;
	}

	/** Put the player's engine note keys on the four lanes. Call it before
		loadPrefs() so binds this owner saved still win; resetKeys keeps the
		donor defaults captured in the constructor. */
	public function seedNativeNoteKeys(nativeKeys:Array<Dynamic>):Void {
		ensureAlive();
		SourceOwnerPreferences.seedNativeNoteKeys(keyBinds, nativeKeys);
	}

	/** Read and overlay this owner's saved preferences without binding process globals. */
	public function loadPrefs():Void {
		loadStoredPrefs();
		reloadVolumeKeys();
	}

	/** Detached language/service owners read saved data without borrowing device keys. */
	public function loadStoredPrefs():Void {
		ensureAlive();
		var record:Dynamic = callOwnerSave('getField', [SAVE_FIELD]);
		if (record == null) {
			return;
		}
		var version:Dynamic = field(record, 'version');
		if (version != VERSION) {
			return;
		}
		var values:Dynamic = field(record, 'values');
		if (!isObject(values) && !isStringMap(values))
			throw '[psych-client-prefs] Malformed owner preferences';

		var savedData:Dynamic = field(values, 'data');
		if (savedData != null) {
			for (name in DATA_FIELDS) {
				if (!hasField(savedData, name)) continue;
				var saved:Dynamic = field(savedData, name);
				if (name == 'gameplaySettings') {
					var target:Dynamic = field(data, name);
					if (!isStringMap(target)) {
						target = gameplayDefaults();
						Reflect.setField(data, name, target);
					}
					copyIntoMap(saved, target, true);
				} else {
					Reflect.setField(data, name, cloneValue(saved));
				}
			}
		}
		mergeKnownControls(keyBinds, field(values, 'keyBinds'));
		mergeKnownControls(gamepadBinds, field(values, 'gamepadBinds'));
	}

	/** Store this owner's data and controls together in one versioned bucket. */
	public function saveSettings():Void {
		ensureAlive();
		if (data == null || !isObject(data))
			throw '[psych-client-prefs] Cannot save malformed preference data';
		var savedData:Dynamic = {};
		for (name in DATA_FIELDS) {
			var value:Dynamic = field(data, name);
			Reflect.setField(savedData, name, name == 'gameplaySettings'
				? mapToObject(value) : cloneValue(value));
		}
		var values:Dynamic = {
			data:savedData,
			keyBinds:mapToObject(keyBinds),
			gamepadBinds:mapToObject(gamepadBinds)
		};
		callOwnerSave('setField', [SAVE_FIELD, {version:VERSION, values:values}]);
		callOwnerSave('flush', []);
	}

	/** Match Psych's customDefaultValue switch exactly. */
	public function getGameplaySetting(name:String, defaultValue:Dynamic = null,
		customDefaultValue:Bool = false):Dynamic {
		ensureAlive();
		if (!customDefaultValue) defaultValue = mapGet(field(defaultData, 'gameplaySettings'), name);
		var settings:Dynamic = field(data, 'gameplaySettings');
		return mapExists(settings, name) ? mapGet(settings, name) : defaultValue;
	}

	/** `null` resets both devices; `false` keyboard only; `true` gamepad only. */
	public function resetKeys(?controller:Null<Bool>):Void {
		ensureAlive();
		if (controller != true) resetMap(keyBinds, defaultKeys);
		if (controller != false) resetMap(gamepadBinds, defaultButtons);
	}

	public function clearInvalidKeys(key:String):Void {
		ensureAlive();
		removeNone(mapGet(keyBinds, key), FlxKey.NONE);
		removeNone(mapGet(gamepadBinds, key), FlxGamepadInputID.NONE);
	}

	/** The donor snapshots the maps but leaves each binding array shared. */
	public function loadDefaultKeys():Void {
		ensureAlive();
		defaultKeys = shallowMapCopy(keyBinds);
		defaultButtons = shallowMapCopy(gamepadBinds);
	}

	/** Register owner-safe runtime behavior for APIs that touch native controls. */
	public function bindRuntimeOperation(name:String, callback:Array<Dynamic>->Dynamic):Void {
		ensureAlive();
		if (name != 'reloadVolumeKeys' && name != 'toggleVolumeKeys')
			throw '[psych-client-prefs] Unknown runtime operation: ' + name;
		if (callback == null) runtimeOperations.remove(name);
		else runtimeOperations.set(name, callback);
	}

	public function reloadVolumeKeys():Dynamic return runRuntimeOperation('reloadVolumeKeys', []);

	public function toggleVolumeKeys(turnOn:Bool = true):Dynamic
		return runRuntimeOperation('toggleVolumeKeys', [turnOn]);

	/** Drop the owner storage and mutable data when its import lifetime ends. */
	public function release():Void {
		if (released) return;
		released = true;
		ownerSave = null;
		ownerRoot = '';
		data = null;
		defaultData = null;
		keyBinds = null;
		gamepadBinds = null;
		defaultKeys = null;
		defaultButtons = null;
		runtimeOperations.clear();
	}

	function runRuntimeOperation(name:String, args:Array<Dynamic>):Dynamic {
		ensureAlive();
		var operation = runtimeOperations.get(name);
		if (operation == null)
			throw '[psych-client-prefs-unsupported] ' + name + ' has no owner-safe runtime adapter';
		return operation(args);
	}

	function resetMap(target:StringMap<Dynamic>, defaults:StringMap<Dynamic>):Void {
		if (target == null || defaults == null) return;
		for (name in mapKeys(target)) if (defaults.exists(name)) {
			var keys:Dynamic = defaults.get(name);
			target.set(name, Std.isOfType(keys, Array) ? (cast keys:Array<Dynamic>).copy() : cloneValue(keys));
		}
	}

	static function removeNone(value:Dynamic, none:Dynamic):Void {
		if (!Std.isOfType(value, Array)) return;
		var values:Array<Dynamic> = cast value;
		var index = values.indexOf(none);
		while (index >= 0) {
			values.splice(index, 1);
			index = values.indexOf(none);
		}
	}

	function mergeKnownControls(target:StringMap<Dynamic>, saved:Dynamic):Void {
		if (target == null || saved == null) return;
		for (name in mapKeys(saved)) if (target.exists(name))
			target.set(name, cloneValue(mapGet(saved, name)));
	}

	function callOwnerSave(method:String, args:Array<Dynamic>):Dynamic
		return SourceOwnerPreferences.callOwnerSave(ownerSave, LABEL, method, args);

	function ensureAlive():Void {
		if (released) throw '[psych-client-prefs] Preference view was released';
	}

	static function normalizeOwner(owner:String):String
		return SourceOwnerPreferences.normalizeOwner(owner, LABEL);

	static function keyboardDefaults():StringMap<Dynamic> {
		var keys = new StringMap<Dynamic>();
		keys.set('note_up', [FlxKey.W, FlxKey.UP]); keys.set('note_left', [FlxKey.A, FlxKey.LEFT]);
		keys.set('note_down', [FlxKey.S, FlxKey.DOWN]); keys.set('note_right', [FlxKey.D, FlxKey.RIGHT]);
		keys.set('ui_up', [FlxKey.W, FlxKey.UP]); keys.set('ui_left', [FlxKey.A, FlxKey.LEFT]);
		keys.set('ui_down', [FlxKey.S, FlxKey.DOWN]); keys.set('ui_right', [FlxKey.D, FlxKey.RIGHT]);
		keys.set('accept', [FlxKey.SPACE, FlxKey.ENTER]); keys.set('back', [FlxKey.BACKSPACE, FlxKey.ESCAPE]);
		keys.set('pause', [FlxKey.ENTER, FlxKey.ESCAPE]); keys.set('reset', [FlxKey.R]);
		keys.set('volume_mute', [FlxKey.ZERO]); keys.set('volume_up', [FlxKey.NUMPADPLUS, FlxKey.PLUS]);
		keys.set('volume_down', [FlxKey.NUMPADMINUS, FlxKey.MINUS]);
		keys.set('debug_1', [FlxKey.SEVEN]); keys.set('debug_2', [FlxKey.EIGHT]);
		return keys;
	}

	static function gamepadDefaults():StringMap<Dynamic> {
		var buttons = new StringMap<Dynamic>();
		buttons.set('note_up', [FlxGamepadInputID.DPAD_UP, FlxGamepadInputID.Y]);
		buttons.set('note_left', [FlxGamepadInputID.DPAD_LEFT, FlxGamepadInputID.X]);
		buttons.set('note_down', [FlxGamepadInputID.DPAD_DOWN, FlxGamepadInputID.A]);
		buttons.set('note_right', [FlxGamepadInputID.DPAD_RIGHT, FlxGamepadInputID.B]);
		buttons.set('ui_up', [FlxGamepadInputID.DPAD_UP, FlxGamepadInputID.LEFT_STICK_DIGITAL_UP]);
		buttons.set('ui_left', [FlxGamepadInputID.DPAD_LEFT, FlxGamepadInputID.LEFT_STICK_DIGITAL_LEFT]);
		buttons.set('ui_down', [FlxGamepadInputID.DPAD_DOWN, FlxGamepadInputID.LEFT_STICK_DIGITAL_DOWN]);
		buttons.set('ui_right', [FlxGamepadInputID.DPAD_RIGHT, FlxGamepadInputID.LEFT_STICK_DIGITAL_RIGHT]);
		buttons.set('accept', [FlxGamepadInputID.A, FlxGamepadInputID.START]);
		buttons.set('back', [FlxGamepadInputID.B]); buttons.set('pause', [FlxGamepadInputID.START]);
		buttons.set('reset', [FlxGamepadInputID.BACK]);
		return buttons;
	}

	static function shallowMapCopy(source:StringMap<Dynamic>):StringMap<Dynamic> {
		var copy = new StringMap<Dynamic>();
		for (name in mapKeys(source)) copy.set(name, source.get(name));
		return copy;
	}
}
