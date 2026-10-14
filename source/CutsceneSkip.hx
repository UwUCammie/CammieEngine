package;

/** Where the skip key (see CutsceneSkipKey) may take the song while a cutscene is showing.
 *
 * A cutscene is a stretch the chart leaves free of player notes. A video that
 * plays behind notes is scenery and is never skipped. A skip lands a few seconds
 * before the point where play picks back up, so the player sees the cutscene
 * hand over and has time to get ready. Every event in between still fires and
 * the music lands exactly where it would have been without the skip. */
class CutsceneSkip {
	/** How much of a cutscene is left to play after a skip: the landing point
	 * sits this far before play resumes, for song cutscenes and intro clips alike. */
	public static inline var LEAD_MS:Float = 5000;
	/** Shorter jumps are not worth a seek. */
	public static inline var MIN_SKIP_MS:Float = 500;

	/** Song time a skip lands at: LEAD_MS before the cutscene ends, or before
	 * the next player note when that arrives first. Returns `nowMs` when there
	 * is nothing to skip, so a skip with LEAD_MS or less left does nothing.
	 * `nextPlayerNoteMs` is NaN without a next note. */
	public static function target(nowMs:Float, startMs:Float, durationMs:Float, nextPlayerNoteMs:Float, songLengthMs:Float):Float {
		if (!Math.isFinite(nowMs) || !Math.isFinite(startMs) || !Math.isFinite(durationMs) || durationMs <= 0) return nowMs;
		var end = startMs + durationMs;
		if (Math.isFinite(nextPlayerNoteMs)) end = Math.min(end, nextPlayerNoteMs);
		if (Math.isFinite(songLengthMs) && songLengthMs > 0) end = Math.min(end, songLengthMs);
		return Math.max(nowMs, end - LEAD_MS);
	}

	/** Clip time an intro cutscene is moved to when skipped at `positionMs`:
	 * LEAD_MS before its end, so the clip still finishes on its own and its end
	 * callbacks run as usual. NaN when there is nothing to skip: an unknown
	 * length, or LEAD_MS or less left. An unreadable playhead still allows the
	 * skip, since the end of the clip is known. */
	public static function leadSeekMs(durationMs:Float, positionMs:Float):Float {
		if (!Math.isFinite(durationMs) || durationMs <= LEAD_MS) return Math.NaN;
		var seek = durationMs - LEAD_MS;
		if (Math.isFinite(positionMs) && positionMs >= seek) return Math.NaN;
		return seek;
	}

	/** Part of an intro clip a skip at `positionMs` jumps over, which script
	 * timers waiting on the clip move forward by. */
	public static function leadAdvanceMs(durationMs:Float, positionMs:Float):Float
		return Math.max(0, unwatchedMs(durationMs, positionMs) - LEAD_MS);

	public static function skippable(nowMs:Float, targetMs:Float):Bool
		return Math.isFinite(nowMs) && Math.isFinite(targetMs) && targetMs - nowMs >= MIN_SKIP_MS;

	/** Part of a clip nobody watched when it was skipped at `positionMs`. Zero
	 * when either value is unknown, so an unreadable clip never moves anything. */
	public static function unwatchedMs(durationMs:Float, positionMs:Float):Float {
		if (!Math.isFinite(durationMs) || durationMs <= 0 || !Math.isFinite(positionMs) || positionMs < 0) return 0;
		return Math.max(0, durationMs - positionMs);
	}

	/** Seconds a running script timer moves on when a cutscene is skipped by
	 * `skipSeconds`. It stops just short of the timer's own end, so the timer still
	 * fires through its manager on the next frame and its callback runs normally. */
	public static function timerAdvance(timeLeft:Float, skipSeconds:Float):Float {
		if (!Math.isFinite(timeLeft) || !Math.isFinite(skipSeconds) || skipSeconds <= 0) return 0;
		return Math.max(0, Math.min(skipSeconds, timeLeft - TIMER_EDGE));
	}

	/** How far before its end a skipped-ahead timer is left. */
	public static inline var TIMER_EDGE:Float = 0.0001;

	/** The furthest landing time among several cutscenes showing at once. */
	public static function furthest(targets:Array<Float>, nowMs:Float):Float {
		var best = nowMs;
		for (value in targets) if (Math.isFinite(value) && value > best) best = value;
		return best;
	}
}
