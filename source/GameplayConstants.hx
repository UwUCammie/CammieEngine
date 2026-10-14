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

	/**
		How far each rating moves health, without a sign. A note's heal cutoff
		decides which ratings heal and which hurt (Note.getHealth). At the
		default cutoff sick and good heal while bad and shit hurt.
	*/
	public static inline var HEALTH_SICK_AMOUNT:Float = 0.07;
	public static inline var HEALTH_GOOD_AMOUNT:Float = 0.03;
	public static inline var HEALTH_BAD_AMOUNT:Float = 0.03;
	public static inline var HEALTH_SHIT_AMOUNT:Float = 0.06;
	/** The same amounts with the Kade health option on. */
	public static inline var KADE_HEALTH_SICK_AMOUNT:Float = 0.1;
	public static inline var KADE_HEALTH_GOOD_AMOUNT:Float = 0.04;
	public static inline var KADE_HEALTH_BAD_AMOUNT:Float = 0.06;
	public static inline var KADE_HEALTH_SHIT_AMOUNT:Float = 0.2;

	/**
		Signed health change per rating at the default cutoff, as a script reads
		it. A bad hit loses health by default, so its bonus is negative.
	*/
	public static inline var HEALTH_SICK_BONUS:Float = HEALTH_SICK_AMOUNT;
	public static inline var HEALTH_GOOD_BONUS:Float = HEALTH_GOOD_AMOUNT;
	public static inline var HEALTH_BAD_BONUS:Float = -HEALTH_BAD_AMOUNT;
	public static inline var HEALTH_SHIT_BONUS:Float = -HEALTH_SHIT_AMOUNT;
	/** Health a missed note costs, as a positive amount. */
	public static inline var HEALTH_MISS_PENALTY:Float = 0.04;
	/** Health a key press with no note costs, as a positive amount. */
	public static inline var HEALTH_GHOST_MISS_PENALTY:Float = 0.04;
	/**
		Base step of a note type with consistent health: one step of loss for
		ratings under its cutoff, one step of gain for the rest, each scaled by
		the type's damage or heal multiplier.
	*/
	public static inline var HEALTH_CONSISTENT_STEP:Float = 0.04;
	/** Health hitting a mine note costs, as a positive amount. Missing one is free. */
	public static inline var HEALTH_MINE_PENALTY:Float = 0.45;
	/** Health hitting a nuke note costs: more than the whole bar, so it always kills. */
	public static inline var HEALTH_NUKE_PENALTY:Float = 69;

	/** Score a miss or an empty key press takes away, as a positive amount. */
	public static inline var SCORE_MISS_PENALTY:Int = 5;

	public static inline var MS_PER_SEC:Int = 1000;
	public static inline var SECS_PER_MIN:Int = 60;
	public static inline var STEPS_PER_BEAT:Int = 4;
}
