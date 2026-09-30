/** Values Psych passes to characters and stages for its Hey! event. */
class PsychHeyEventCompat {
	/** 0: boyfriend, 1: girlfriend, 2: both. */
	public static function target(value:Dynamic):Int {
		var normalized = value == null ? '' : StringTools.trim(Std.string(value)).toLowerCase();
		return switch (normalized) {
			case 'bf' | 'boyfriend' | '0': 0;
			case 'gf' | 'girlfriend' | '1': 1;
			default: 2;
		};
	}

	public static function duration(value:Dynamic):Float {
		var parsed = value == null ? Math.NaN : Std.parseFloat(StringTools.trim(Std.string(value)));
		return Math.isNaN(parsed) || parsed <= 0 ? 0.6 : parsed;
	}
}
