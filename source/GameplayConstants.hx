package;

/**
	The plain numbers the default judgement works with, in one place so the
	game and anything that describes the game to a script quote the same ones.
	Health runs from HEALTH_MIN to HEALTH_MAX and a song starts in the middle.
	The per-rating amounts are the defaults for an ordinary note before any
	note type, modifier or health option changes them.
*/
class GameplayConstants {
	public static inline var HEALTH_MIN:Float = 0.0;
	public static inline var HEALTH_MAX:Float = 2.0;
	public static inline var HEALTH_STARTING:Float = 1.0;

	public static inline var HEALTH_SICK_BONUS:Float = 0.07;
	public static inline var HEALTH_GOOD_BONUS:Float = 0.03;
	public static inline var HEALTH_BAD_BONUS:Float = 0.03;
	public static inline var HEALTH_SHIT_BONUS:Float = -0.06;
	/** Health a missed note costs, as a positive amount. */
	public static inline var HEALTH_MISS_PENALTY:Float = 0.04;
	/** Health a key press with no note costs, as a positive amount. */
	public static inline var HEALTH_GHOST_MISS_PENALTY:Float = 0.04;

	/** Score a miss or an empty key press takes away, as a positive amount. */
	public static inline var SCORE_MISS_PENALTY:Int = 5;

	public static inline var MS_PER_SEC:Int = 1000;
	public static inline var SECS_PER_MIN:Int = 60;
	public static inline var STEPS_PER_BEAT:Int = 4;
}
