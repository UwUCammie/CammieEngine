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
		if (owner == null) return fallback;
		var prefs:Dynamic = nightmare ? Reflect.field(owner, 'view') : Reflect.field(owner, 'data');
		if (prefs == null)
			throw '[source-gameplay-preferences] Owner has no ' + (nightmare ? 'view' : 'data') + ' object for ' + name;
		if (!Reflect.hasField(prefs, name)) return fallback;
		var value:Dynamic = Reflect.field(prefs, name);
		return Type.typeof(value) == TBool ? cast value : fallback;
	}

	static function readSetting(owner:Dynamic, getter:Dynamic, name:String, fallback:Dynamic):Dynamic {
		try {
			return Reflect.callMethod(owner, getter, [name, fallback]);
		} catch (error:Dynamic) {
			throw '[source-gameplay-preferences] Could not read gameplay setting ' + name + ': ' + Std.string(error);
		}
	}
}
