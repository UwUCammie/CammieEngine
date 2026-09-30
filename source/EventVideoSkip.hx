package;

/** Timing policy for an explicit skip of a chart-owned video event. */
class EventVideoSkip {
	public static function target(currentMs:Float, eventMs:Float, durationMs:Float, songLengthMs:Float):Float {
		if (!Math.isFinite(currentMs) || !Math.isFinite(eventMs)
			|| !Math.isFinite(durationMs) || durationMs <= 0)
			return currentMs;
		var endMs = eventMs + durationMs;
		if (Math.isFinite(songLengthMs) && songLengthMs > 0)
			endMs = Math.min(endMs, songLengthMs);
		return Math.max(currentMs, endMs);
	}
}
