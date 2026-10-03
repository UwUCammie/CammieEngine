package nightmarevision.modchart;

/** Small exact copies of the numerical helpers used by NMV and Flixel 6.1.2. */
class NightmareVisionModchartMath {
	public static inline var EPSILON:Float = 0.0000001;

	public static inline function fastSin(value:Float):Float {
		var n = value * 0.3183098862;
		if (n > 1) n -= (Math.ceil(n) >> 1) << 1;
		else if (n < -1) n += (Math.ceil(-n) >> 1) << 1;
		if (n > 0) return n * (3.1 + n * (0.5 + n * (-7.2 + n * 3.6)));
		return n * (3.1 - n * (0.5 + n * (7.2 + n * 3.6)));
	}

	public static inline function fastCos(value:Float):Float return fastSin(value + 1.570796327);
}
