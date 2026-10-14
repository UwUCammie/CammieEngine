package;

/** Shared owner-local settings sampled once when source gameplay starts. */
@:keep
class SourceGameplayPreferences {
	/**
	 * Capture the gameplay options that the source engines read at PlayState
	 * creation. Keep values returned by the owner getter unchanged; Psych's
	 * getter and Nightmare Vision's getter intentionally differ in how their
	 * default maps are selected.
	 */
	public static function snapshot(owner:Dynamic, nightmare:Bool):Dynamic {
		if (owner == null) throw '[source-gameplay-preferences] Missing owner preferences';

		var getter:Dynamic = Reflect.field(owner, 'getGameplaySetting');
		if (!Reflect.isFunction(getter))
			throw '[source-gameplay-preferences] Owner has no getGameplaySetting(name, defaultValue) method';

		var result:Dynamic = {};
		Reflect.setField(result, 'healthGain', readSetting(owner, getter, 'healthgain', 1.0));
		Reflect.setField(result, 'healthLoss', readSetting(owner, getter, 'healthloss', 1.0));
		Reflect.setField(result, 'instakillOnMiss', readSetting(owner, getter, 'instakill', false));
		Reflect.setField(result, 'practiceMode', readSetting(owner, getter, 'practice', false));
		Reflect.setField(result, 'cpuControlled', readSetting(owner, getter, 'botplay', false));

		if (nightmare) {
			Reflect.setField(result, 'guitarHeroSustains', false);
		} else {
			var data:Dynamic = Reflect.field(owner, 'data');
			if (data == null)
				throw '[source-gameplay-preferences] Psych owner has no data object for guitarHeroSustains';
			if (!Reflect.hasField(data, 'guitarHeroSustains'))
				throw '[source-gameplay-preferences] Psych owner data has no guitarHeroSustains field';
			Reflect.setField(result, 'guitarHeroSustains', Reflect.field(data, 'guitarHeroSustains'));
		}
		return result;
	}

	/** Read Psych data or Nightmare Vision's ClientPrefs-shaped view live. */
	public static function liveBool(owner:Dynamic, nightmare:Bool, name:String, fallback:Bool):Bool {
		var value:Dynamic = liveValue(owner, nightmare, name);
		return Type.typeof(value) == TBool ? cast value : fallback;
	}

	/** Same live read for a number. Anything that is not a finite number is the fallback. */
	public static function liveFloat(owner:Dynamic, nightmare:Bool, name:String, fallback:Float):Float {
		var value:Dynamic = liveValue(owner, nightmare, name);
		if (!Std.isOfType(value, Float)) return fallback;
		var number:Float = value;
		return Math.isFinite(number) ? number : fallback;
	}

	/** Same live read for text. */
	public static function liveString(owner:Dynamic, nightmare:Bool, name:String, fallback:String):String {
		var value:Dynamic = liveValue(owner, nightmare, name);
		return Std.isOfType(value, String) ? cast value : fallback;
	}

	// The preferences gameplay reads from whichever owner is active, under one
	// name each. `owner` is null when no imported owner is active, and then the
	// host default (or the source default) is the answer.

	/** Nightmare Vision keeps this one under its older name. */
	public static function antialiasing(owner:Dynamic, nightmare:Bool, hostDefault:Bool):Bool
		return liveBool(owner, nightmare, nightmare ? 'globalAntialiasing' : 'antialiasing', hostDefault);

	public static function hideHud(owner:Dynamic, nightmare:Bool):Bool
		return liveBool(owner, nightmare, 'hideHud', false);

	public static function healthBarAlpha(owner:Dynamic, nightmare:Bool):Float
		return liveFloat(owner, nightmare, 'healthBarAlpha', 1);

	public static function timeBarType(owner:Dynamic, nightmare:Bool):String
		return liveString(owner, nightmare, 'timeBarType', 'Time Left');

	public static function ghostTapping(owner:Dynamic, nightmare:Bool, hostDefault:Bool):Bool
		return liveBool(owner, nightmare, 'ghostTapping', hostDefault);

	public static function camZooms(owner:Dynamic, nightmare:Bool, hostDefault:Bool):Bool
		return liveBool(owner, nightmare, 'camZooms', hostDefault);

	public static function noteOffset(owner:Dynamic, nightmare:Bool, hostDefault:Float):Float
		return liveFloat(owner, nightmare, 'noteOffset', hostDefault);

	public static function hitsoundVolume(owner:Dynamic, nightmare:Bool):Float
		return liveFloat(owner, nightmare, 'hitsoundVolume', 0);

	/** Nightmare Vision calls the same switch gpuCaching. */
	public static function cacheOnGPU(owner:Dynamic, nightmare:Bool, hostDefault:Bool):Bool
		return liveBool(owner, nightmare, nightmare ? 'gpuCaching' : 'cacheOnGPU', hostDefault);

	static function liveValue(owner:Dynamic, nightmare:Bool, name:String):Dynamic {
		if (owner == null) return null;
		var prefs:Dynamic = nightmare ? Reflect.field(owner, 'view') : Reflect.field(owner, 'data');
		if (prefs == null)
			throw '[source-gameplay-preferences] Owner has no ' + (nightmare ? 'view' : 'data') + ' object for ' + name;
		return Reflect.hasField(prefs, name) ? Reflect.field(prefs, name) : null;
	}

	static function readSetting(owner:Dynamic, getter:Dynamic, name:String, fallback:Dynamic):Dynamic {
		try {
			return Reflect.callMethod(owner, getter, [name, fallback]);
		} catch (error:Dynamic) {
			throw '[source-gameplay-preferences] Could not read gameplay setting ' + name + ': ' + Std.string(error);
		}
	}
}
