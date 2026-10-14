package;

/**
	A broken per-frame callback (update, a beat hook) fails the same way every
	time it runs. Printing each failure floods the log with thousands of copies and
	spends frame time building and writing the line. Report the first few of each
	distinct error, then one note that further copies are hidden.
**/
class RepeatedScriptErrorLog {
	public static inline var SHOWN = 3;
	static inline var MAX_KEYS = 512;

	static var counts:Map<String, Int> = new Map();
	static var keys = 0;

	/** The line to print for this occurrence, or null when it should stay quiet. */
	public static function line(key:String, message:String):Null<String> {
		var seen = counts.get(key);
		var count = seen == null ? 1 : seen + 1;
		if (seen == null) {
			// Bounded so a script generating unique messages cannot grow this forever.
			if (keys >= MAX_KEYS) {
				counts.clear();
				keys = 0;
			}
			keys++;
		}
		counts.set(key, count);
		if (count <= SHOWN)
			return message;
		if (count == SHOWN + 1)
			return message + ' (repeats; further copies of this error are hidden)';
		return null;
	}

	public static function reset():Void {
		counts.clear();
		keys = 0;
	}
}
