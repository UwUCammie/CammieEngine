package;

/** Restore by name without bypassing current source difficulty or file availability. */
class LibraryDifficultyPreference {
	public static function resolve(preferred:String, fallback:Int, supported:Array<Int>, names:Array<String>,
		allowed:Array<String>, hasChart:Int->Bool):Int {
		if (preferred == null || preferred == '' || supported == null || names == null) return fallback;
		var name = preferred.toLowerCase();
		if (allowed != null && allowed.length > 0) {
			var present = false;
			for (entry in allowed) if (entry.toLowerCase() == name) present = true;
			if (!present) return fallback;
		}
		var found = -1;
		for (index in supported) if (index >= 0 && index < names.length && names[index].toLowerCase() == name) {
			if (found >= 0) return fallback;
			found = index;
		}
		return found >= 0 && hasChart(found) ? found : fallback;
	}
}
