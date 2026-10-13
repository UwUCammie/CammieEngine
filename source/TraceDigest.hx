package;

/** Bounded text for the process log. Native trace output is unbuffered and holds
 * the output lock for a whole message, so one huge repeated diagnostic written
 * by a worker can stall every other thread that logs, including the game loop. */
class TraceDigest {
	public static inline var MAX_LINES:Int = 60;
	public static inline var MAX_LINE:Int = 400;

	/** Fold repeated lines into a single counted line, keeping first-seen order. */
	public static function collapse(text:String, maxLines:Int = MAX_LINES):String {
		if (text == null) return '';
		var order:Array<String> = []; var counts:Map<String, Int> = [];
		for (raw in text.split('\n')) {
			var line = StringTools.rtrim(raw);
			if (line == '') continue;
			if (line.length > MAX_LINE) line = line.substr(0, MAX_LINE - 3) + '...';
			if (counts.exists(line)) counts.set(line, counts.get(line) + 1);
			else { counts.set(line, 1); order.push(line); }
		}
		var shown = [for (line in order.slice(0, maxLines)) counts.get(line) > 1 ? line + ' (x' + counts.get(line) + ')' : line];
		if (order.length > maxLines) shown.push('... ' + (order.length - maxLines) + ' more distinct lines omitted');
		return shown.join('\n');
	}
}
