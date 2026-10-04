package;

/** Schedules held numeric-option changes at a stable rate across frame rates. */
class OptionsValueRepeat {
	public static inline var REPEAT_INTERVAL:Float = 1.0 / 60.0;
	public static inline var MAX_CHANGES_PER_FRAME:Int = 8;
	static inline var TIMER_EPSILON:Float = 0.000000001;

	var direction:Int = 0;
	var repeatElapsed:Float = 0;
	var selectedOption:Int = -1;
	var hasSelection:Bool = false;

	public function new() {}

	/**
	 * Returns the number of changes to apply this frame. A new direction changes
	 * immediately once; held input then repeats at 60 changes per second.
	 */
	public function update(nextDirection:Int, elapsed:Float, option:Int, enabled:Bool):Int {
		if (!enabled || nextDirection == 0) {
			reset();
			selectedOption = option;
			hasSelection = true;
			return 0;
		}

		if (!hasSelection) {
			selectedOption = option;
			hasSelection = true;
		}
		else if (selectedOption != option) {
			selectedOption = option;
			repeatElapsed = 0;
			if (direction == nextDirection && direction != 0)
				return 0;
			direction = nextDirection;
			return 1;
		}

		if (direction != nextDirection) {
			direction = nextDirection;
			repeatElapsed = 0;
			return 1;
		}

		if (!Math.isFinite(elapsed) || elapsed <= 0)
			return 0;

		repeatElapsed += elapsed;
		if (!Math.isFinite(repeatElapsed)) {
			repeatElapsed = 0;
			return 0;
		}

		var dueEstimate = (repeatElapsed + TIMER_EPSILON) / REPEAT_INTERVAL;
		if (dueEstimate >= MAX_CHANGES_PER_FRAME + 1) {
			// Keep sub-frame timing but discard a hitch's unbounded backlog.
			repeatElapsed %= REPEAT_INTERVAL;
			if (repeatElapsed < TIMER_EPSILON || REPEAT_INTERVAL - repeatElapsed < TIMER_EPSILON)
				repeatElapsed = 0;
			return MAX_CHANGES_PER_FRAME;
		}

		// The estimate is known to be below the small catch-up cap before it is
		// converted to Int, so even an enormous finite hitch cannot overflow it.
		var due = Std.int(dueEstimate);
		if (due <= 0)
			return 0;
		repeatElapsed -= due * REPEAT_INTERVAL;
		if (repeatElapsed < 0)
			repeatElapsed = 0;
		return due;
	}

	public function reset():Void {
		direction = 0;
		repeatElapsed = 0;
		hasSelection = false;
		selectedOption = -1;
	}
}
