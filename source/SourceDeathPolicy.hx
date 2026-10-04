package;

/** Source-specific death eligibility predicates kept separate from transition effects. */
class SourceDeathPolicy {
	public static function eligible(nightmare:Bool, health:Float, bounds:Array<Float>,
		skipHealthCheck:Bool, instakillOnMiss:Bool, practiceMode:Bool,
		isDead:Bool, hasTimer:Bool):Bool {
		if (!nightmare)
			return ((skipHealthCheck && instakillOnMiss) || health <= 0)
				&& !practiceMode && !isDead && !hasTimer;

		// NV's donor puts the instakill clause outside the practice/isDead guards.
		// Preserve that precedence; its health-bound clause has separate guards.
		var crossedHealthBound = bounds != null && bounds.length >= 2
			&& ((bounds[1] > bounds[0] && health <= bounds[0])
				|| (bounds[0] > bounds[1] && health >= bounds[0]));
		return (skipHealthCheck && instakillOnMiss)
			|| (crossedHealthBound && !practiceMode && !isDead);
	}
}
