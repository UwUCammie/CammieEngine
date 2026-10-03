package;

/** Rendering-independent cadence for frame-based compatibility script callbacks.
 * PlayState still updates and renders at its configured rate; this clock only
 * schedules onUpdate/onUpdatePost pairs at the source engine's default 60 Hz. */
class CompatScriptClock {
	public static inline var DEFAULT_SOURCE_HZ:Int = 60;
	static inline var CREDIT_EPSILON:Float = 1e-10;

	var tickCredit:Float = 0;
	public final sourceHz:Int;
	public final tickElapsed:Float;
	public var isPaused(default, null):Bool = false;

	public function new(?sourceHz:Int = DEFAULT_SOURCE_HZ) {
		if (sourceHz <= 0)
			throw '[compat-script-clock] Source rate must be positive';
		this.sourceHz = sourceHz;
		this.tickElapsed = 1.0 / sourceHz;
	}

	/** Add host elapsed time and return every complete source tick, without a cap. */
	public function advance(elapsedSeconds:Float):CompatScriptTickBatch {
		var ticks = 0;
		if (!isPaused && elapsedSeconds > 0 && Math.isFinite(elapsedSeconds)) {
			tickCredit += elapsedSeconds * sourceHz;
			ticks = Std.int(Math.floor(tickCredit + CREDIT_EPSILON));
			if (ticks > 0) {
				tickCredit -= ticks;
				// The epsilon allows exact 60/240/480 Hz boundaries to survive
				// floating-point summation. Keep the remaining phase nonnegative.
				if (tickCredit < 0 && tickCredit > -CREDIT_EPSILON)
					tickCredit = 0;
			}
		}
		return new CompatScriptTickBatch(ticks, tickElapsed);
	}

	/** Exclude paused wall time while preserving the fractional tick phase. */
	public function pause():Void isPaused = true;
	public function resume():Void isPaused = false;

	/** Start a new script owner with no accumulated or paused time. */
	public function reset():Void {
		tickCredit = 0;
		isPaused = false;
	}
}
