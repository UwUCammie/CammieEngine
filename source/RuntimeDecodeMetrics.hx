package;

/** Aggregate disk bitmap decode work only while an explicit smoke load runs. */
class RuntimeDecodeMetrics {
	public static var enabled(default, null):Bool = false;
	static var cacheHits:Int = 0;
	static var cacheMisses:Int = 0;
	static var decodeMs:Float = 0;
	static var maxDecodeMs:Float = 0;

	public static function reset(measure:Bool):Void {
		enabled = measure;
		cacheHits = 0;
		cacheMisses = 0;
		decodeMs = 0;
		maxDecodeMs = 0;
	}

	public static function recordHit():Void {
		if (enabled)
			cacheHits++;
	}

	public static function recordMiss(milliseconds:Float):Void {
		if (!enabled)
			return;
		cacheMisses++;
		var duration = Math.isNaN(milliseconds) || milliseconds < 0 ? 0 : milliseconds;
		decodeMs += duration;
		if (duration > maxDecodeMs)
			maxDecodeMs = duration;
	}

	public static function snapshot():Dynamic {
		return {
			bitmapCacheHits: cacheHits,
			bitmapCacheMisses: cacheMisses,
			bitmapDecodeMs: decodeMs,
			bitmapMaxDecodeMs: maxDecodeMs
		};
	}
}
