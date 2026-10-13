package;

/** Pure motion for the card star stream: many slow, spinning stars that each
 * drag a fading tail. Progress 0..1 is one pass across the card, right to left. */
class FreeplayStarTrail {
	public static inline var STARS:Int = 14;
	/** Fading copies that follow each star. */
	public static inline var GHOSTS:Int = 4;
	/** Seconds for an average star to cross the card. */
	public static inline var PERIOD:Float = 2.6;

	// Stable per-star variation without consuming the game's random stream.
	static function vary(star:Int, salt:Int):Float {
		var value = Math.sin(star * 12.9898 + salt * 78.233) * 43758.5453;
		return value - Math.floor(value);
	}
	public static function progress(clock:Float, star:Int):Float {
		var value = clock / (PERIOD * (0.8 + 0.5 * vary(star, 1))) + vary(star, 2);
		return value - Math.floor(value);
	}
	/** Vertical lane 0..1. The stride spreads neighbouring stars apart. */
	public static function lane(star:Int):Float return ((star * 5) % STARS + 0.5) / STARS;
	public static function size(star:Int):Float return 0.55 + 0.6 * vary(star, 3);
	/** Degrees per second, either direction. */
	public static function spin(star:Int):Float return (vary(star, 4) < 0.5 ? -1 : 1) * (90 + 180 * vary(star, 5));
	/** Share of the crossing after which a star is gone. */
	public static inline var FADE_END:Float = 0.4;
	/** Appear quickly, then fade out long before the far edge. */
	public static function opacity(progress:Float):Float {
		if (progress <= 0 || progress >= FADE_END) return 0;
		return Math.min(1, progress / 0.05) * Math.min(1, (FADE_END - progress) / 0.28) * 0.85;
	}
	/** Progress a tail copy trails its star by. */
	public static function ghostLag(ghost:Int):Float return (ghost + 1) * 0.02;
	public static function ghostOpacity(progress:Float, ghost:Int):Float
		return opacity(progress - ghostLag(ghost)) * (1 - (ghost + 1) / (GHOSTS + 1)) * 0.6;
}
