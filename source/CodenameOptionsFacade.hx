package;

import flixel.FlxG;

/**
	Detached view of the Codename Options fields used by mounted HL17 scripts.
	Readable fields are initialized from explicit native equivalents. Supported
	option edits are committed only when the imported menu calls save().
*/
@:keep
class CodenameOptionsFacade {
	var initialValues:Map<String, Dynamic> = new Map();
	var controlSnapshots:Map<String, Array<Int>> = new Map();

	static final CONTROL_FIELDS:Array<String> = [
		'P1_NOTE_LEFT', 'P1_NOTE_DOWN', 'P1_NOTE_UP', 'P1_NOTE_RIGHT',
		'P2_NOTE_LEFT', 'P2_NOTE_DOWN', 'P2_NOTE_UP', 'P2_NOTE_RIGHT',
		'P1_LEFT', 'P1_DOWN', 'P1_UP', 'P1_RIGHT', 'P1_ACCEPT', 'P1_BACK', 'P1_RESET', 'P1_PAUSE',
		'P2_LEFT', 'P2_DOWN', 'P2_UP', 'P2_RIGHT', 'P2_ACCEPT', 'P2_BACK', 'P2_RESET', 'P2_PAUSE'
	];

	// The donor mutates these through Reflect.setField, so they must be real
	// reflected fields rather than getter/setter-only properties.
	@:keep public var downscroll:Dynamic;
	@:keep public var ghostTapping:Dynamic;
	@:keep public var songOffset:Dynamic;
	@:keep public var camZoomOnBeat:Dynamic;
	@:keep public var framerate:Dynamic;
	@:keep public var flashingMenu:Dynamic;
	@:keep public var naughtyness:Dynamic;
	@:keep public var volumeMusic:Dynamic;
	@:keep public var volumeSFX:Dynamic;
	@:keep public var colorHealthBar:Dynamic;
	@:keep public var P1_NOTE_LEFT:Array<Int> = [0];
	@:keep public var P1_NOTE_DOWN:Array<Int> = [0];
	@:keep public var P1_NOTE_UP:Array<Int> = [0];
	@:keep public var P1_NOTE_RIGHT:Array<Int> = [0];
	@:keep public var P2_NOTE_LEFT:Array<Int> = [0];
	@:keep public var P2_NOTE_DOWN:Array<Int> = [0];
	@:keep public var P2_NOTE_UP:Array<Int> = [0];
	@:keep public var P2_NOTE_RIGHT:Array<Int> = [0];
	@:keep public var P1_LEFT:Array<Int> = [0];
	@:keep public var P1_DOWN:Array<Int> = [0];
	@:keep public var P1_UP:Array<Int> = [0];
	@:keep public var P1_RIGHT:Array<Int> = [0];
	@:keep public var P1_ACCEPT:Array<Int> = [0];
	@:keep public var P1_BACK:Array<Int> = [0];
	@:keep public var P1_RESET:Array<Int> = [0];
	@:keep public var P1_PAUSE:Array<Int> = [0];
	@:keep public var P2_LEFT:Array<Int> = [0];
	@:keep public var P2_DOWN:Array<Int> = [0];
	@:keep public var P2_UP:Array<Int> = [0];
	@:keep public var P2_RIGHT:Array<Int> = [0];
	@:keep public var P2_ACCEPT:Array<Int> = [0];
	@:keep public var P2_BACK:Array<Int> = [0];
	@:keep public var P2_RESET:Array<Int> = [0];
	@:keep public var P2_PAUSE:Array<Int> = [0];

	// Flixel uses this default for newly created sprites. Existing sprites keep
	// their own per-sprite values, just as in the native engine.
	@:keep public var antialiasing:Bool = true;
	// HL17 gates its song shaders and stage-17 Flx3D view on the first two
	// values. GPU-only bitmap storage is retained for source compatibility, but
	// this engine has no matching bitmap backend.
	@:keep public var gameplayShaders:Bool = true;
	@:keep public var lowMemoryMode:Bool = false;
	@:keep public var week6PixelPerfect:Dynamic;
	@:keep public var quality:Dynamic;
	@:keep public var gpuOnlyBitmaps:Bool = true;
	// Auto Pause maps to FlxG.autoPause and the persisted native options field.
	@:keep public var autoPause:Dynamic;

	public function new() {
		var options:Dynamic = OptionsHandler.options;
		downscroll = read(options, 'downscroll');
		ghostTapping = read(options, 'useCustomInput');
		songOffset = read(options, 'offset');
		camZoomOnBeat = read(options, 'zoomCamera');
		framerate = read(options, 'fpsCap');
		flashingMenu = read(options, 'flashingLights');
		naughtyness = read(options, 'naughtyness');
		volumeMusic = read(options, 'volumeMusic');
		volumeSFX = read(options, 'volumeSFX');
		colorHealthBar = read(options, 'useCharColor');
		autoPause = read(options, 'autoPause');
		week6PixelPerfect = readBool(options, 'week6PixelPerfect', true);
		quality = CodenameOptionsQualityCompat.infer(options);
		antialiasing = readBool(options, 'antialiasing', true);
		gameplayShaders = readBool(options, 'gameplayShaders', true);
		lowMemoryMode = readBool(options, 'lowMemoryMode', false);
		#if (mac || web)
		gpuOnlyBitmaps = readBool(options, 'gpuOnlyBitmaps', false);
		#else
		gpuOnlyBitmaps = readBool(options, 'gpuOnlyBitmaps', true);
		#end

		initialValues.set('downscroll', downscroll);
		initialValues.set('ghostTapping', ghostTapping);
		initialValues.set('songOffset', songOffset);
		initialValues.set('camZoomOnBeat', camZoomOnBeat);
		initialValues.set('framerate', framerate);
		initialValues.set('flashingMenu', flashingMenu);
		initialValues.set('naughtyness', naughtyness);
		initialValues.set('volumeMusic', volumeMusic);
		initialValues.set('volumeSFX', volumeSFX);
		initialValues.set('colorHealthBar', colorHealthBar);
		initialValues.set('autoPause', autoPause);
		initialValues.set('week6PixelPerfect', week6PixelPerfect);
		initialValues.set('quality', quality);
		initialValues.set('antialiasing', antialiasing);
		initialValues.set('gameplayShaders', gameplayShaders);
		initialValues.set('lowMemoryMode', lowMemoryMode);
		initialValues.set('gpuOnlyBitmaps', gpuOnlyBitmaps);
		for (field in CONTROL_FIELDS) {
			var nativeControl = nativeControlName(field);
			if (nativeControl != null && !controlSnapshots.exists(nativeControl))
				controlSnapshots.set(nativeControl, readNativeControlKeys(nativeControl));
			var slots = nativeControl == null ? [0] : controlSnapshots.get(nativeControl);
			var key = slots == null || slots.length <= fieldSlot(field) ? 0 : slots[fieldSlot(field)];
			var displayed = [key];
			Reflect.setField(this, field, displayed);
			initialValues.set('control.' + field, displayed.copy());
		}
	}

	static function read(options:Dynamic, field:String):Dynamic
		return options == null ? null : Reflect.field(options, field);

	static function readBool(options:Dynamic, field:String, fallback:Bool):Bool {
		var value = read(options, field);
		return Std.isOfType(value, Bool) ? cast value : fallback;
	}

	static function nativeControlName(field:String):String {
		var name = field.substr(3);
		return switch (name) {
			case 'NOTE_LEFT': 'LEFT';
			case 'NOTE_DOWN': 'DOWN';
			case 'NOTE_UP': 'UP';
			case 'NOTE_RIGHT': 'RIGHT';
			case 'LEFT': 'LEFT_MENU';
			case 'DOWN': 'DOWN_MENU';
			case 'UP': 'UP_MENU';
			case 'RIGHT': 'RIGHT_MENU';
			case 'ACCEPT': 'ACCEPT';
			case 'BACK': 'BACK';
			case 'RESET': 'RESET';
			case 'PAUSE': 'PAUSE';
			default: null;
		};
	}

	static function fieldSlot(field:String):Int
		return field.charAt(1) == '1' ? 0 : 1;

	static function readNativeControlKeys(nativeControl:String):Array<Int> {
		if (FlxG.save != null && FlxG.save.data != null) {
			var saved:Dynamic = Reflect.field(FlxG.save.data, 'codenameMenuKeys');
			var slots:Dynamic = saved == null ? null : Reflect.field(saved, nativeControl.toLowerCase());
			if (Std.isOfType(slots, Array)) return (cast slots:Array<Int>).copy();
		}
		var settings = PlayerSettings.player1;
		if (nativeControl == null || settings == null || settings.controls == null) return [];
		var keys = settings.controls.getKeyboardBindingsByName(nativeControl);
		return keys == null ? [] : keys.copy();
	}

	function applyControlKeys(field:String):Bool {
		var nativeControl = nativeControlName(field);
		var settings = PlayerSettings.player1;
		if (nativeControl == null || settings == null || settings.controls == null) return false;
		var values:Dynamic = Reflect.field(this, field);
		var key = 0;
		if (Std.isOfType(values, Array)) {
			for (value in (cast values:Array<Dynamic>)) {
				var parsed = Std.isOfType(value, Int) ? (cast value:Int) : Std.parseInt(Std.string(value));
				if (parsed != null && parsed > 0) {
					key = parsed;
					break;
				}
			}
		}
		var slots = controlSnapshots.get(nativeControl);
		if (slots == null) slots = readNativeControlKeys(nativeControl);
		slots = slots.copy();
		var slot = fieldSlot(field);
		while (slots.length <= slot) slots.push(0);
		slots[slot] = key;
		controlSnapshots.set(nativeControl, slots);
		var keys:Array<Int> = [];
		for (value in slots) if (value > 0 && !keys.contains(value)) keys.push(value);
		settings.controls.setKeyboardBindingsByName(nativeControl, keys);
		return saveControlBindings(nativeControl, keys, slots);
	}

	static function saveControlBindings(nativeControl:String, keys:Array<Int>, slots:Array<Int>):Bool {
		if (FlxG.save == null || FlxG.save.data == null) return false;
		var data:Dynamic = FlxG.save.data;
		var menuKeys:Dynamic = Reflect.field(data, 'codenameMenuKeys');
		if (menuKeys == null) {
			menuKeys = {};
			Reflect.setField(data, 'codenameMenuKeys', menuKeys);
		}
		// Keep Codename's primary/alternate slot positions, including an unbound
		// primary slot. The native action receives only positive key codes.
		Reflect.setField(menuKeys, nativeControl.toLowerCase(), slots.copy());
		switch (nativeControl) {
			case 'LEFT' | 'DOWN' | 'UP' | 'RIGHT':
				var savedKeys:Dynamic = Reflect.field(data, 'keys');
				if (savedKeys == null) return false;
				Reflect.setField(savedKeys, nativeControl.toLowerCase(), keys.copy());
			default:
				// Menu-only actions have no legacy key-save field.
		}
		FlxG.save.flush();
		return true;
	}

	static function equalKeyLists(left:Dynamic, right:Dynamic):Bool {
		if (!Std.isOfType(left, Array) || !Std.isOfType(right, Array)) return left == right;
		var a:Array<Dynamic> = cast left;
		var b:Array<Dynamic> = cast right;
		if (a.length != b.length) return false;
		for (i in 0...a.length) if (a[i] != b[i]) return false;
		return true;
	}

	/** Commit only fields changed through this imported Options object. */
	public function save():Void {
		var changed = new Array<String>();
		var persisted = new Array<String>();
		var nativeOptions:Dynamic = OptionsHandler.options;
		var qualityChanged = quality != initialValues.get('quality');
		if (qualityChanged) {
			CodenameOptionsQualityCompat.apply(this, quality);
			Reflect.setField(nativeOptions, 'quality', quality);
			changed.push('quality'); persisted.push('quality');
		}
		if (downscroll != initialValues.get('downscroll')) {
			Reflect.setField(nativeOptions, 'downscroll', downscroll);
			changed.push('downscroll'); persisted.push('downscroll');
		}
		if (ghostTapping != initialValues.get('ghostTapping')) {
			Reflect.setField(nativeOptions, 'useCustomInput', ghostTapping);
			changed.push('ghostTapping'); persisted.push('useCustomInput');
		}
		if (songOffset != initialValues.get('songOffset')) {
			Reflect.setField(nativeOptions, 'offset', songOffset);
			changed.push('songOffset'); persisted.push('offset');
		}
		if (camZoomOnBeat != initialValues.get('camZoomOnBeat')) {
			Reflect.setField(nativeOptions, 'zoomCamera', camZoomOnBeat);
			changed.push('camZoomOnBeat'); persisted.push('zoomCamera');
		}
		if (framerate != initialValues.get('framerate')) {
			Reflect.setField(nativeOptions, 'fpsCap', framerate);
			changed.push('framerate'); persisted.push('fpsCap');
		}
		if (flashingMenu != initialValues.get('flashingMenu')) {
			Reflect.setField(nativeOptions, 'flashingLights', flashingMenu);
			changed.push('flashingMenu'); persisted.push('flashingLights');
		}
		if (naughtyness != initialValues.get('naughtyness')) {
			Reflect.setField(nativeOptions, 'naughtyness', naughtyness);
			changed.push('naughtyness'); persisted.push('naughtyness');
		}
		if (volumeMusic != initialValues.get('volumeMusic')) {
			Reflect.setField(nativeOptions, 'volumeMusic', volumeMusic);
			changed.push('volumeMusic'); persisted.push('volumeMusic');
		}
		if (volumeSFX != initialValues.get('volumeSFX')) {
			Reflect.setField(nativeOptions, 'volumeSFX', volumeSFX);
			changed.push('volumeSFX'); persisted.push('volumeSFX');
		}
		if (colorHealthBar != initialValues.get('colorHealthBar')) {
			Reflect.setField(nativeOptions, 'useCharColor', colorHealthBar);
			changed.push('colorHealthBar'); persisted.push('useCharColor');
		}
		if (autoPause != initialValues.get('autoPause')) {
			Reflect.setField(nativeOptions, 'autoPause', autoPause);
			changed.push('autoPause'); persisted.push('autoPause');
		}
		if (week6PixelPerfect != initialValues.get('week6PixelPerfect')) {
			Reflect.setField(nativeOptions, 'week6PixelPerfect', week6PixelPerfect);
			changed.push('week6PixelPerfect'); persisted.push('week6PixelPerfect');
		}
		if (antialiasing != initialValues.get('antialiasing')) {
			Reflect.setField(nativeOptions, 'antialiasing', antialiasing);
			changed.push('antialiasing'); persisted.push('antialiasing');
		}
		if (gameplayShaders != initialValues.get('gameplayShaders')) {
			Reflect.setField(nativeOptions, 'gameplayShaders', gameplayShaders);
			changed.push('gameplayShaders'); persisted.push('gameplayShaders');
		}
		if (lowMemoryMode != initialValues.get('lowMemoryMode')) {
			Reflect.setField(nativeOptions, 'lowMemoryMode', lowMemoryMode);
			changed.push('lowMemoryMode'); persisted.push('lowMemoryMode');
		}
		if (qualityChanged && quality != CodenameOptionsQualityCompat.CUSTOM) {
			// Preset selection updates the same advanced fields as Codename's
			// applyQuality(); keep the facade and persisted host object in sync.
			Reflect.setField(nativeOptions, 'antialiasing', antialiasing);
			Reflect.setField(nativeOptions, 'lowMemoryMode', lowMemoryMode);
			Reflect.setField(nativeOptions, 'gameplayShaders', gameplayShaders);
			for (field in ['antialiasing', 'lowMemoryMode', 'gameplayShaders'])
				if (persisted.indexOf(field) < 0) persisted.push(field);
		}
		if (gpuOnlyBitmaps != initialValues.get('gpuOnlyBitmaps')) {
			Reflect.setField(nativeOptions, 'gpuOnlyBitmaps', gpuOnlyBitmaps);
			changed.push('gpuOnlyBitmaps'); persisted.push('gpuOnlyBitmaps');
			trace('[codename-options-effect-unsupported] Options.gpuOnlyBitmaps was saved, but this engine has no GPU-only bitmap backend.');
		}
		if (persisted.length > 0) OptionsHandler.options = cast nativeOptions;
		for (field in CONTROL_FIELDS) {
			var value:Dynamic = Reflect.field(this, field);
			if (!equalKeyLists(value, initialValues.get('control.' + field))) {
				changed.push(field);
				if (applyControlKeys(field)) {
					persisted.push(field);
					initialValues.set('control.' + field, (cast value:Array<Int>).copy());
				} else trace('[codename-options-save-warning] Could not persist control edit ' + field + '.');
			}
		}
		for (field in changed) {
			if (CONTROL_FIELDS.indexOf(field) >= 0) continue;
			initialValues.set(field, Reflect.field(this, field));
		}
		if (qualityChanged) initialValues.set('quality', quality);
		trace('[codename-options-save] Persisted native edits: '
			+ (persisted.length == 0 ? 'none.' : persisted.join(', ') + '.'));
	}

	/** Match Codename's explicit quality action without writing user settings. */
	@:keep public function applyQuality():Void {
		if (!CodenameOptionsQualityCompat.apply(this, quality)) return;
		var options:Dynamic = OptionsHandler.options;
		for (field in ['quality', 'antialiasing', 'lowMemoryMode', 'gameplayShaders'])
			Reflect.setField(options, field, Reflect.field(this, field));
		OptionsHandler.applyDisplayOptions(cast options);
	}

	/** Apply the runtime equivalents used by the imported menu. Gameplay options
	 * are read directly from OptionsHandler by their owning engine systems. */
	public function applySettings():Void {
		var options:Dynamic = OptionsHandler.options;
		Reflect.setField(options, 'week6PixelPerfect', week6PixelPerfect);
		Reflect.setField(options, 'quality', quality);
		if (quality != initialValues.get('quality'))
			CodenameOptionsQualityCompat.apply(options, quality);
		else {
			Reflect.setField(options, 'antialiasing', antialiasing);
			Reflect.setField(options, 'gameplayShaders', gameplayShaders);
			Reflect.setField(options, 'lowMemoryMode', lowMemoryMode);
		}
		antialiasing = readBool(options, 'antialiasing', antialiasing);
		gameplayShaders = readBool(options, 'gameplayShaders', gameplayShaders);
		lowMemoryMode = readBool(options, 'lowMemoryMode', lowMemoryMode);
		var fps:Dynamic = Reflect.field(options, 'fpsCap');
		if (fps != null) {
			FlxG.updateFramerate = Std.int(fps);
			FlxG.drawFramerate = Std.int(fps);
		}
		OptionsHandler.applyDisplayOptions(cast options);
		OptionsHandler.applyAudioOptions(cast options);
		FlxG.autoPause = autoPause == true;
		trace('[codename-options-applied] Updated native framerate, audio groups, antialiasing default, and auto-pause; saved gameplay options are read by engine systems.');
	}
}
