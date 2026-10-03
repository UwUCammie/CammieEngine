package;

/** Source queue geometry, independent of note assets and chart identity. */
class NightmareVisionSustainLayout {
	public static function segmentCount(length:Float, step:Float):Int {
		if (!Math.isFinite(length) || !Math.isFinite(step) || step <= 0 || length <= 0) return 0;
		var rounded = Math.round(length / step);
		return rounded <= 0 ? 0 : rounded + 1;
	}

	public static function segmentTime(headTime:Float, index:Int, step:Float):Float
		return headTime + index * step;
}
