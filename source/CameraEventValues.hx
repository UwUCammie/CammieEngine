package;

/** Text parsing for the Psych-family camera events, kept free of display objects. */
class CameraEventValues {
	/** A zoom amount as Psych reads it: whatever number the text starts with, else the event default. */
	public static function amount(value:String, fallback:Float):Float {
		var parsed = Std.parseFloat(value);
		return Math.isNaN(parsed) ? fallback : parsed;
	}

	/**
		One camera's "duration, intensity" text as [duration, intensity], or null
		when Psych would leave that camera alone. Fields past the second are
		ignored and a bad number counts as 0, so "0.5" or "0, 0.01" never shake.
	**/
	public static function shake(value:String):Array<Float> {
		var split = value.split(',');
		var duration = split[0] == null ? 0 : Std.parseFloat(StringTools.trim(split[0]));
		var intensity = split[1] == null ? 0 : Std.parseFloat(StringTools.trim(split[1]));
		if (Math.isNaN(duration)) duration = 0;
		if (Math.isNaN(intensity)) intensity = 0;
		return duration > 0 && intensity != 0 ? [duration, intensity] : null;
	}
}
