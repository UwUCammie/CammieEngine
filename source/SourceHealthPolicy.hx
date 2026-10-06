package;

import flixel.math.FlxMath;

/** Source assignment, update-phase limits and icon thresholds; no host state. */
class SourceHealthPolicy {
	public static inline function psychAssignment(value:Float):Float
		return FlxMath.roundDecimal(value, 5);

	public static inline function psychUpdateBound(value:Float, maximum:Null<Float>):Float
		return shouldPsychUpdateBound(value, maximum) ? maximum : value;

	public static inline function shouldPsychUpdateBound(value:Float, maximum:Null<Float>):Bool
		return maximum != null && value > maximum;

	public static inline function shouldNightmareUpdateBound(value:Float, minimum:Float, maximum:Float):Bool
		return (maximum > minimum && value > maximum) || (minimum > maximum && maximum > value);

	public static inline function nightmareUpdateBound(value:Float, minimum:Float, maximum:Float):Float {
		return shouldNightmareUpdateBound(value, minimum, maximum) ? maximum : value;
	}

	public static inline function percent(value:Float, minimum:Float, maximum:Float):Float
		return FlxMath.remapToRange(FlxMath.bound(value, minimum, maximum), minimum, maximum, 0, 100);

	public static inline function psychPlayerFrame(percent:Float):Int return percent < 20 ? 1 : 0;
	public static inline function psychOpponentFrame(percent:Float):Int return percent > 80 ? 1 : 0;
}
