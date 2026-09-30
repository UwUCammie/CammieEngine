package;

/**
	Codename's documented quality preset behavior, shared by the options host
	and the imported Options facade. Mode 2 preserves the user's custom values.
*/
class CodenameOptionsQualityCompat {
	public static inline var LOW:Int = 0;
	public static inline var HIGH:Int = 1;
	public static inline var CUSTOM:Int = 2;
	public static inline var DEFAULT:Int = HIGH;

	static final QUALITY_NAMES:Array<String> = ['LOW', 'HIGH', 'CUSTOM'];
	static final CUSTOM_FIELDS:Array<String> = ['antialiasing', 'lowMemoryMode', 'gameplayShaders'];
	static final HIGH_VALUES:Array<Bool> = [true, false, true];

	public static function sanitize(raw:Dynamic):Int {
		if (!(Std.isOfType(raw, Int) || Std.isOfType(raw, Float))) return DEFAULT;
		var value:Float = raw;
		if (!Math.isFinite(value)) return DEFAULT;
		var mode = Std.int(value);
		return mode == LOW || mode == HIGH || mode == CUSTOM ? mode : DEFAULT;
	}

	/**
		Older host saves have no quality field. If they do contain a complete
		custom triple, retain those choices as CUSTOM; otherwise use Codename's
		HIGH defaults. An explicit quality value always wins.
	*/
	public static function infer(options:Dynamic):Int {
		if (options == null) return DEFAULT;
		var raw:Dynamic = Reflect.field(options, 'quality');
		if (raw != null) return sanitize(raw);
		var complete = true;
		var matchesHigh = true;
		for (i in 0...CUSTOM_FIELDS.length) {
			var field = CUSTOM_FIELDS[i];
			var value:Dynamic = Reflect.field(options, field);
			if (!Reflect.hasField(options, field) || !Std.isOfType(value, Bool)) {
				complete = false;
				break;
			}
			if (value != HIGH_VALUES[i]) matchesHigh = false;
		}
		return complete && !matchesHigh ? CUSTOM : HIGH;
	}

	/** Apply LOW/HIGH exactly as Codename does; CUSTOM keeps individual fields. */
	public static function apply(options:Dynamic, ?requested:Dynamic):Bool {
		if (options == null) return false;
		var mode = requested == null ? infer(options) : sanitize(requested);
		if (!Reflect.hasField(options, 'quality')) return false;
		if (mode != CUSTOM)
			for (field in CUSTOM_FIELDS)
				if (!Reflect.hasField(options, field)) return false;
		Reflect.setField(options, 'quality', mode);
		if (mode == CUSTOM) return true;
		Reflect.setField(options, 'antialiasing', mode == HIGH);
		Reflect.setField(options, 'lowMemoryMode', mode == LOW);
		Reflect.setField(options, 'gameplayShaders', mode == HIGH);
		return true;
	}

	public static function isCustom(options:Dynamic):Bool
		return options != null && sanitize(Reflect.field(options, 'quality')) == CUSTOM;

	public static function isCustomField(field:Dynamic):Bool
		return Std.isOfType(field, String) && CUSTOM_FIELDS.indexOf(cast field) >= 0;

	public static function isLocked(options:Dynamic, field:Dynamic):Bool
		return isCustomField(field) && !isCustom(options);

	public static function name(raw:Dynamic):String
		return QUALITY_NAMES[sanitize(raw)];

	public static function choices():Array<Int>
		return [LOW, HIGH, CUSTOM];

	public static function displayNames():Array<String>
		return QUALITY_NAMES.copy();
}
