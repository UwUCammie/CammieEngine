package;

/** Normalized full card travel. The visible trail ends within its first third. */
class FreeplayStarTrail {
	public static function opacity(progress:Float):Float return Math.max(0, 1 - Math.max(0, progress) * 3) * 0.75;
}
