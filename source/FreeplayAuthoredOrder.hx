package;

/** Validate optional generated menu ranks without involving importer I/O in Freeplay. */
class FreeplayAuthoredOrder {
	public static function rank(value:Dynamic):Null<Int>
		return Std.isOfType(value, Int) && value >= 0 ? cast value : null;
}
