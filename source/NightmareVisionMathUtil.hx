package;

/** Source arithmetic helpers kept distinct from rounded score formatting. */
@:keep
class NightmareVisionMathUtil {
	public static function floorDecimal(value:Float, decimals:Int):Float {
		if (decimals < 1) return Math.floor(value);
		var multiplier:Float = 1;
		for (index in 0...decimals) multiplier *= 10;
		return Math.floor(value * multiplier) / multiplier;
	}
}
