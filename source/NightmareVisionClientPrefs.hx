package;

import flixel.input.gamepad.FlxGamepadInputID;
import flixel.input.keyboard.FlxKey;
import haxe.ds.StringMap;
import SourceOwnerPreferences.*;

using StringTools;

/** Owner-local implementation of the Nightmare Vision ClientPrefs data API.

	The source class is process-global and its generated save code reads/writes
	FlxSave directly. Imported modules instead share one view per owner. Values
	remain source defaults unless an owner record exists; a small set of exact
	native option equivalents seed those defaults, but assignments only affect
	this owner view. Everything that is the same for every Psych-family owner
	lives in SourceOwnerPreferences. */
class NightmareVisionClientPrefs {
	public static inline var SAVE_FIELD:String = 'nightmareVisionClientPrefs';
	public static inline var VERSION:Int = 1;
	static inline var LABEL:String = 'nmv-client-prefs';

	/** Shared ClientPrefs-shaped object bound into each owner interpreter. */
	public var view(default, null):Dynamic;
	public var ownerRoot(default, null):String;
	final ownerSave:Dynamic;
	/** Seeded fields that follow the running game; load() keeps them. */
	var liveSeeds:Array<String> = [];
	var released:Bool = false;

	/** `ownerSave` is an already owner-validated CodenameOwnerSaveData view. */
	public function new(ownerRoot:String, ownerSave:Dynamic, ?nativeOptions:Dynamic) {
		this.ownerRoot = normalizeOwner(ownerRoot);
		requireOwnerSave(ownerSave, LABEL, false);
		this.ownerSave = ownerSave;
		view = makeDefaults();
		// Copied, not bound: later writes only touch this detached owner view.
		liveSeeds = seedNativeOptions(view, nativeOptions, true);
		installMethods();
		// Source Main captures reset defaults before Init overlays saved bindings.
		loadDefaultKeys();
	}

	/** The owner key is compared after the same slash cleanup used by imports. */
	public function canReuseFor(owner:String):Bool {
		if (released) return false;
		try return normalizeOwner(owner) == ownerRoot catch (_:Dynamic) return false;
	}

	/** Put the player's engine note keys on the four lanes. Call it before load()
		so binds this owner saved still win; the reset defaults captured in the
		constructor stay the source ones. */
	public function seedNativeNoteKeys(nativeKeys:Array<Dynamic>):Void {
		ensureAlive();
		SourceOwnerPreferences.seedNativeNoteKeys(field(view, 'keyBinds'), nativeKeys);
	}

	/** Overlay this owner's saved values onto the existing source defaults. */
	public function load():Void {
		ensureAlive();
		var record:Dynamic = callOwnerSave('getField', [SAVE_FIELD]);
		if (record == null) return;
		var version = field(record, 'version');
		if (version != VERSION) return;
		var values = field(record, 'values');
		if (values == null || (Type.typeof(values) != TObject && !Std.isOfType(values, StringMap)))
			throw '[nmv-client-prefs] Malformed owner preferences';

		for (name in persistedFields()) {
			if (!hasField(values, name) || liveSeeds.indexOf(name) >= 0) continue;
			var saved:Dynamic = field(values, name);
			if (isMapField(name)) {
				var target:Dynamic = field(view, name);
				if (!isStringMap(target)) {
					target = new StringMap<Dynamic>();
					Reflect.setField(view, name, target);
				}
				copyIntoMap(saved, target);
			} else {
				Reflect.setField(view, name, cloneValue(saved));
			}
		}
	}

	/** Persist only this owner's preference bucket; never bind or flush native controls. */
	public function flush():Void {
		ensureAlive();
		var values:Dynamic = {};
		for (name in persistedFields()) {
			var value:Dynamic = field(view, name);
			Reflect.setField(values, name, isMapField(name) ? mapToObject(value) : cloneValue(value));
		}
		callOwnerSave('setField', [SAVE_FIELD, {version:VERSION, values:values}]);
		var flushOwner:Dynamic = Reflect.field(ownerSave, 'flush');
		if (flushOwner != null) Reflect.callMethod(ownerSave, flushOwner, []);
	}

	public function getGameplaySetting(name:String, defaultValue:Dynamic):Dynamic {
		ensureAlive();
		var settings:Dynamic = field(view, 'gameplaySettings');
		if (mapExists(settings, name)) return mapGet(settings, name);
		return defaultValue;
	}

	/** Break owner save and view references when the runtime switches imports. */
	public function release():Void {
		if (released) return;
		released = true;
		if (view != null) {
			for (name in Reflect.fields(view)) Reflect.setField(view, name, null);
		}
		view = null;
		ownerRoot = '';
	}

	function makeDefaults():Dynamic {
		var value:Dynamic = {
			inDevMode:false, discordEnabled:true, fpsDisplayType:'Simple', streamedMusic:false,
			autoPause:true, gpuCaching:true, globalAntialiasing:true, lowQuality:false,
			shaders:true, unlockedFramerate:false, framerate:60, vsyncMode:'Off',
			noteSplashes:true, noteSplashType:'Both', hideHud:false, showRatings:true, timeBarType:'Time Left',
			flashing:true, camZooms:true, scoreZoom:true, healthBarAlpha:1.0,
			camFollowsCharacters:true, underlayType:'Lane Underlay', underlayOpacity:0.0,
			mechanics:true, modcharts:true, downScroll:false, middleScroll:false,
			opponentStrums:true, ghostTapping:true, noReset:false, hitsoundVolume:0.0,
			ratingOffset:0, useEpicRankings:true, toggleSplashScreen:true,
			epicWindow:22.5, sickWindow:45.0, goodWindow:90.0, badWindow:135.0,
			safeFrames:10.0, noteOffset:0, quants:false, noteSkin:'Vanilla', comboOffset:[0, 0, 0, 0],
			gameplaySettings:gameplayDefaults(),
			arrowRGBdef:[
				[0xFFC24B99, 0xFFFFFFFF, 0xFF3C1F56],
				[0xFF00FFFF, 0xFFFFFFFF, 0xFF1542B7],
				[0xFF12FA05, 0xFFFFFFFF, 0xFF0A4447],
				[0xFFF9393F, 0xFFFFFFFF, 0xFF651038]
			],
			arrowRGBquant:[
				[0xFFE51919, 0xFFFFFF, 0xFF5B0A30], [0xFF193BE5, 0xFFFFFF, 0xFF0A3B5B],
				[0xFFA119E5, 0xFFFFFF, 0xFF1D0A5B], [0xFF26D93E, 0xFFFFFF, 0xFF24560F],
				[0xFF0000B2, 0xFFFFFF, 0xFF002247], [0xFFA119E5, 0xFFFFFF, 0xFF1D0A5B],
				[0xFFE5C319, 0xFFFFFF, 0xFF5B2A0A], [0xFFA119E5, 0xFFFFFF, 0xFF1D0A5B],
				[0xFF13ECA4, 0xFFFFFF, 0xFF085D18], [0xFF3A3A6C, 0xFFFFFF, 0xFF17202B],
				[0xFF3A3A6C, 0xFFFFFF, 0xFF17202B]
			],
			arrowHSV:[[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
			quantHSV:[[0,-20,0],[-130,-20,0],[-80,-20,0],[128,-30,0],[-120,-70,-35],
				[-80,-20,0],[50,-20,0],[-80,-20,0],[160,-15,0],[-120,-70,-35],[-120,-70,-35]],
			quantStepmania:[[10,-20,0],[-110,-40,0],[140,-20,0],[50,25,0],[0,-100,-50],
				[-80,-40,0],[-180,10,-10],[-35,50,30],[160,-15,0],[-120,-70,-35],[-120,-70,-35]],
			keyBinds:keyBindDefaults(), defaultKeys:null,
			gamepadBinds:gamepadBindDefaults(), defaultGamepadBinds:null,
			customKeys:new StringMap<Dynamic>(), customPad:new StringMap<Dynamic>(),
			muteKeys:[FlxKey.ZERO], volumeDownKeys:[FlxKey.NUMPADMINUS, FlxKey.MINUS],
			volumeUpKeys:[FlxKey.NUMPADPLUS, FlxKey.PLUS],
			editorUIColor:0xFF66A3FF,
			editorGradColors:[0xFF53154E,0xFF153E53],
			editorBoxColors:[0xFF3A709F,0xFF8AADCA], editorGradVis:true,
			chartPresetList:['Default'], chartPresets:chartPresetDefaults()
		};
		return value;
	}

	function installMethods():Void {
		Reflect.setField(view, 'load', function():Void load());
		Reflect.setField(view, 'flush', function():Void flush());
		Reflect.setField(view, 'getGameplaySetting', function(name:String, fallback:Dynamic):Dynamic
			return getGameplaySetting(name, fallback));
		Reflect.setField(view, 'loadDefaultKeys', function():Void loadDefaultKeys());
		Reflect.setField(view, 'copyKey', function(keys:Array<Dynamic>):Array<Dynamic> return copyKey(keys));
		Reflect.setField(view, 'addCustomKey', function(name:String, keys:Array<Dynamic>):Void addCustomKey(name, keys));
		Reflect.setField(view, 'tryBindingSave', function(?name:String):Dynamic return unsupported('tryBindingSave'));
		Reflect.setField(view, 'changeFps', function(?fps:Int):Dynamic return unsupported('changeFps'));
		Reflect.setField(view, 'refreshVSyncMode', function():Dynamic return unsupported('refreshVSyncMode'));
		Reflect.setField(view, 'reloadControls', function():Dynamic return unsupported('reloadControls'));
	}

	function loadDefaultKeys():Void {
		Reflect.setField(view, 'defaultKeys', copyMap(field(view, 'keyBinds')));
		Reflect.setField(view, 'defaultGamepadBinds', copyMap(field(view, 'gamepadBinds')));
	}

	function copyKey(keys:Array<Dynamic>):Array<Dynamic> {
		if (keys == null) throw '[nmv-client-prefs-unsupported] copyKey received a null key list';
		var result = keys.copy();
		var i = 0;
		while (i < result.length) {
			if (result[i] == FlxKey.NONE) {
				result.remove(FlxKey.NONE);
				--i;
			}
			i++;
		}
		return result;
	}

	function addCustomKey(name:String, keys:Array<Dynamic>):Void {
		if (name != null && name.length >= 1 && keys != null) {
			while (keys.length < 2) keys.push(FlxKey.NONE);
			var custom:Dynamic = field(view, 'customKeys');
			mapSet(custom, name, keys);
		}
		var custom:Dynamic = field(view, 'customKeys');
		var binds = mapKeys(custom);
		for (key in binds) {
			var value:Dynamic = mapGet(custom, key);
			if (Std.isOfType(value, Array) && (cast value:Array<Dynamic>).length >= 2
				&& !mapExists(field(view, 'keyBinds'), key))
				mapSet(field(view, 'keyBinds'), key, value);
		}
	}

	function unsupported(method:String):Dynamic {
		ensureAlive();
		throw '[nmv-client-prefs-unsupported] ' + method
			+ ' would mutate process-wide input or display state';
		return null;
	}

	function persistedFields():Array<String> {
		// Mirrors @saveVar's auto-save list. keyBinds/gamepadBinds are added here
		// because the donor's explicit flush() saves them to its separate controls
		// file; the owner adapter keeps that behavior inside the owner's bucket.
		return [
			'inDevMode','discordEnabled','fpsDisplayType','streamedMusic','autoPause','gpuCaching',
			'globalAntialiasing','lowQuality','shaders','unlockedFramerate','framerate','vsyncMode',
			'noteSplashes','noteSplashType','hideHud','showRatings','timeBarType','flashing','camZooms','scoreZoom',
			'healthBarAlpha','camFollowsCharacters','underlayType','underlayOpacity','mechanics','modcharts',
			'downScroll','middleScroll','opponentStrums','ghostTapping','noReset','hitsoundVolume',
			'ratingOffset','useEpicRankings','toggleSplashScreen','epicWindow','sickWindow','goodWindow',
			'badWindow','safeFrames','noteOffset','quants','noteSkin','comboOffset','gameplaySettings','arrowRGBdef',
			'arrowRGBquant','arrowHSV','quantHSV','quantStepmania','editorUIColor','editorGradColors',
			'editorBoxColors','editorGradVis','chartPresetList','chartPresets','keyBinds','gamepadBinds'
		];
	}

	static function chartPresetDefaults():StringMap<Dynamic> {
		var map = new StringMap<Dynamic>();
		map.set('Default', [[0xFF000000,0xFF000000], false,
			[0xFFFFFFFF,0xFFD2D2D2], 0xFFFAFAFA]);
		return map;
	}

	static function keyBindDefaults():StringMap<Dynamic> {
		var map = new StringMap<Dynamic>();
		map.set('note_left', [FlxKey.A, FlxKey.LEFT]); map.set('note_down', [FlxKey.S, FlxKey.DOWN]);
		map.set('note_up', [FlxKey.W, FlxKey.UP]); map.set('note_right', [FlxKey.D, FlxKey.RIGHT]);
		map.set('note_dodge', [FlxKey.SPACE, FlxKey.NONE]);
		map.set('ui_left', [FlxKey.A, FlxKey.LEFT]); map.set('ui_down', [FlxKey.S, FlxKey.DOWN]);
		map.set('ui_up', [FlxKey.W, FlxKey.UP]); map.set('ui_right', [FlxKey.D, FlxKey.RIGHT]);
		map.set('accept', [FlxKey.SPACE, FlxKey.ENTER]); map.set('back', [FlxKey.BACKSPACE, FlxKey.ESCAPE]);
		map.set('pause', [FlxKey.ENTER, FlxKey.ESCAPE]); map.set('reset', [FlxKey.R, FlxKey.NONE]);
		map.set('fullscreen', [FlxKey.F11, FlxKey.NONE]); map.set('volume_mute', [FlxKey.ZERO, FlxKey.NONE]);
		map.set('volume_up', [FlxKey.NUMPADPLUS, FlxKey.PLUS]); map.set('volume_down', [FlxKey.NUMPADMINUS, FlxKey.MINUS]);
		map.set('debug_1', [FlxKey.SEVEN, FlxKey.NONE]); map.set('debug_2', [FlxKey.EIGHT, FlxKey.NONE]);
		map.set('soft_reload', [FlxKey.F5, FlxKey.NONE]); map.set('hard_reload', [FlxKey.F6, FlxKey.NONE]);
		map.set('switch_debug_display', [FlxKey.F3, FlxKey.NONE]);
		return map;
	}

	static function gamepadBindDefaults():StringMap<Dynamic> {
		var map = new StringMap<Dynamic>();
		map.set('note_up', [FlxGamepadInputID.DPAD_UP, FlxGamepadInputID.Y]);
		map.set('note_down', [FlxGamepadInputID.DPAD_DOWN, FlxGamepadInputID.A]);
		map.set('note_left', [FlxGamepadInputID.DPAD_LEFT, FlxGamepadInputID.X]);
		map.set('note_right', [FlxGamepadInputID.DPAD_RIGHT, FlxGamepadInputID.B]);
		map.set('note_dodge', [FlxGamepadInputID.GUIDE]);
		return map;
	}

	function callOwnerSave(method:String, args:Array<Dynamic>):Dynamic
		return SourceOwnerPreferences.callOwnerSave(ownerSave, LABEL, method, args);

	function ensureAlive():Void {
		if (released) throw '[nmv-client-prefs] Preference view was released';
	}

	static function normalizeOwner(owner:String):String
		return SourceOwnerPreferences.normalizeOwner(owner, LABEL);

	static function isMapField(name:String):Bool
		return name == 'gameplaySettings' || name == 'chartPresets' || name == 'keyBinds' || name == 'gamepadBinds';
}
