package;

/** Pure motion for the card star stream: a regular lattice of spinning stars
 * that each drag a short fading tail. Nothing varies by chance: every star has
 * the same speed, size and spin, spawns are evenly spaced in time, and lanes
 * are taken in order. Progress 0..1 is one pass across the card, right to left. */
class FreeplayStarTrail {
	public static inline var STARS:Int = 32;
	/** Rows the stream cycles through, top to bottom. */
	public static inline var LANES:Int = 8;
	/** Fading copies that follow each star. */
	public static inline var GHOSTS:Int = 4;
	/** Seconds for a star to cross the card. */
	public static inline var PERIOD:Float = 2.0;
	public static inline var SIZE:Float = 0.8;
	/** Degrees per second. */
	public static inline var SPIN:Float = 200;
	/** Share of the crossing after which a star is gone. */
	public static inline var FADE_END:Float = 0.4;
	/** Progress between a star and each successive tail copy. */
	public static inline var GHOST_STEP:Float = 0.007;

	/** Star `n` enters exactly PERIOD / STARS after star `n - 1`. */
	public static function progress(clock:Float, star:Int):Float {
		var value = clock / PERIOD - star / STARS;
		return value - Math.floor(value);
	}
	/** Vertical lane 0..1, taken in order so the stream forms even diagonals. */
	public static function lane(star:Int):Float return (star % LANES + 0.5) / LANES;
	/** Appear quickly, then fade out long before the far edge. */
	public static function opacity(progress:Float):Float {
		if (progress <= 0 || progress >= FADE_END) return 0;
		return Math.min(1, progress / 0.05) * Math.min(1, (FADE_END - progress) / 0.28) * 0.85;
	}
	/** Progress a tail copy trails its star by. */
	public static function ghostLag(ghost:Int):Float return (ghost + 1) * GHOST_STEP;
	public static function ghostOpacity(progress:Float, ghost:Int):Float
		return opacity(progress - ghostLag(ghost)) * (1 - (ghost + 1) / (GHOSTS + 1)) * 0.6;
}
