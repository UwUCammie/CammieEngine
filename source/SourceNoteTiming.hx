package;

/** Pure timing predicates for the Psych and Nightmare Vision chart APIs. */
@:keep
class SourceNoteTiming {
	/** Convert source safe frames to the millisecond window used by both donors.
	 * NV copies this value into each note's hitbox at construction; recomputing
	 * this value does not mutate hitboxes already captured by existing notes. */
	public static inline function safeWindow(safeFrames:Float, playbackRate:Float = 1):Float
		return (safeFrames / 60) * 1000 * playbackRate;

	/** Psych's player-note bounds are asymmetric and strictly exclude both endpoints. */
	public static inline function psychCanBeHit(strumTime:Float, songPosition:Float,
		safeZone:Float, earlyHitMult:Float = 1, lateHitMult:Float = 1):Bool {
		return strumTime > songPosition - (safeZone * lateHitMult)
			&& strumTime < songPosition + (safeZone * earlyHitMult);
	}

	/** Psych's tooLate cutoff uses the unscaled safe zone and is strict. */
	public static inline function isLate(strumTime:Float, songPosition:Float,
		safeZone:Float, wasGoodHit:Bool):Bool
		return strumTime < songPosition - safeZone && !wasGoodHit;

	/** NV's canBeHit predicate uses signed raw noteDiff, a note-local captured
	 * hitbox rather than a live global window, and inclusive symmetric bounds. */
	public static inline function nightmareCanBeHit(strumTime:Float, songPosition:Float,
		hitbox:Float, earlyHitMult:Float = 1):Bool
		return Math.abs(strumTime - songPosition) <= hitbox * earlyHitMult;

	/** Rating windows are separate from canBeHit: apply ratingOffset, take the
	 * absolute difference, then divide by playback rate as both donors do. */
	public static inline function ratingDiff(strumTime:Float, songPosition:Float,
		ratingOffset:Float, playbackRate:Float = 1):Float
		return Math.abs(strumTime - songPosition + ratingOffset) / playbackRate;
}
