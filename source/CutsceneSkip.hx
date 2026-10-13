package;

/** Where an Enter press may take the song while a cutscene is showing.
 *
 * A cutscene is a stretch the chart leaves free of player notes. A video that
 * plays behind notes is scenery and is never skipped. The landing time is where
 * the chart picks play back up, so every event in between still fires and the
 * music lands exactly where it would have been without the skip. */
class CutsceneSkip {
	/** Breathing room kept in front of the first note after a skip. */
	public static inline var NOTE_LEAD_MS:Float = 1000;
	/** Shorter jumps are not worth a seek and would steal the pause key. */
	public static inline var MIN_SKIP_MS:Float = 500;

	/** Song time the chart resumes at: the end of the cutscene, or just ahead
	 * of the next player note when that arrives first. Returns `nowMs` when
	 * there is nothing to skip. `nextPlayerNoteMs` is NaN without a next note. */
	public static function target(nowMs:Float, startMs:Float, durationMs:Float, nextPlayerNoteMs:Float, songLengthMs:Float):Float {
		if (!Math.isFinite(nowMs) || !Math.isFinite(startMs) || !Math.isFinite(durationMs) || durationMs <= 0) return nowMs;
		var end = startMs + durationMs;
		if (Math.isFinite(nextPlayerNoteMs)) end = Math.min(end, nextPlayerNoteMs - NOTE_LEAD_MS);
		if (Math.isFinite(songLengthMs) && songLengthMs > 0) end = Math.min(end, songLengthMs);
		return Math.max(nowMs, end);
	}

	public static function skippable(nowMs:Float, targetMs:Float):Bool
		return Math.isFinite(nowMs) && Math.isFinite(targetMs) && targetMs - nowMs >= MIN_SKIP_MS;

	/** The furthest landing time among several cutscenes showing at once. */
	public static function furthest(targets:Array<Float>, nowMs:Float):Float {
		var best = nowMs;
		for (value in targets) if (Math.isFinite(value) && value > best) best = value;
		return best;
	}
}
