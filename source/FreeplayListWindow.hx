package;

/** Pure selection helpers for the bounded native Freeplay row window. */
class FreeplayListWindow {
	/** Return matching song indexes in their original registry order. */
	public static function visibleIndices(count:Int, matches:Int->Bool):Array<Int> {
		var visible:Array<Int> = [];
		for (index in 0...count)
			if (matches(index))
				visible.push(index);
		return visible;
	}

	/** Return a bounded slice centered on selected, preserving visible order. */
	public static function window(visible:Array<Int>, selected:Int, radius:Int):Array<Int> {
		if (visible == null || visible.length == 0)
			return [];
		var selectedPosition = visible.indexOf(selected);
		if (selectedPosition < 0)
			return [];
		var safeRadius = radius < 0 ? 0 : radius;
		var first = Std.int(Math.max(0, selectedPosition - safeRadius));
		var end = Std.int(Math.min(visible.length, selectedPosition + safeRadius + 1));
		return visible.slice(first, end);
	}
}
