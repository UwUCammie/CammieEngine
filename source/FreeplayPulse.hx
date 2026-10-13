package;

typedef FreeplayHint = {
	var key:String;
	var action:String;
}

/** Pure presentation rules for the Freeplay heading beat, the loudness colors
 * of the visualizer and the control hints. */
class FreeplayPulse {
	/** Used until the selected chart's tempo is known. */
	public static inline var DEFAULT_BPM:Float = 100;

	/** Tempo of a chart read as text. Legacy charts repeat the song tempo in
	 * every section, so the most frequent positive value is the song's own. */
	public static function bpmFromChartText(text:String):Float {
		if (text == null) return DEFAULT_BPM;
		// Plain scanning: a chart can hold thousands of sections, and repeated
		// pattern matches from an offset re-encode the whole text each time.
		var counts:Map<String, Int> = []; var order:Array<String> = []; var at = 0;
		while (true) {
			at = text.indexOf('"bpm"', at);
			if (at < 0) break;
			at += 5;
			var cursor = at;
			while (cursor < text.length && isSpace(text.charCodeAt(cursor))) cursor++;
			if (cursor >= text.length || text.charCodeAt(cursor) != 58) continue;
			cursor++;
			while (cursor < text.length && (isSpace(text.charCodeAt(cursor)) || text.charCodeAt(cursor) == 34)) cursor++;
			var start = cursor;
			while (cursor < text.length && cursor - start < 24) {
				var c = text.charCodeAt(cursor);
				if ((c < 48 || c > 57) && c != 46) break;
				cursor++;
			}
			if (cursor == start) continue;
			var value = text.substring(start, cursor);
			var number = Std.parseFloat(value);
			if (!Math.isFinite(number) || number < 20 || number > 1000) continue;
			if (!counts.exists(value)) { counts.set(value, 0); order.push(value); }
			counts.set(value, counts.get(value) + 1);
			if (order.length > 64) break;
		}
		var best = ''; var bestCount = 0;
		for (value in order) if (counts.get(value) > bestCount) { best = value; bestCount = counts.get(value); }
		return best == '' ? DEFAULT_BPM : Std.parseFloat(best);
	}

	static inline function isSpace(code:Int):Bool return code == 32 || (code >= 9 && code <= 13);

	/** 1 on each beat, easing to 0 before the next. */
	public static function strength(seconds:Float, bpm:Float):Float {
		if (!Math.isFinite(seconds) || !Math.isFinite(bpm) || bpm <= 0) return 0;
		var beats = Math.max(0, seconds) * bpm / 60;
		var rest = 1 - (beats - Math.floor(beats));
		return rest * rest * rest;
	}
	/** Whole beats elapsed, for alternating the lean of the heading. */
	public static function beat(seconds:Float, bpm:Float):Int
		return !Math.isFinite(seconds) || !Math.isFinite(bpm) || bpm <= 0 ? 0 : Std.int(Math.floor(Math.max(0, seconds) * bpm / 60));

	/** Quiet is green, moderate is yellow, loud is red. */
	public static function loudness(level:Float):Int {
		var value = !Math.isFinite(level) ? 0 : Math.max(0, Math.min(1, level));
		var from = value < 0.5 ? 0x4CFF86 : 0xF5F05D; var to = value < 0.5 ? 0xF5F05D : 0xFF4D4D;
		var weight = value < 0.5 ? value * 2 : (value - 0.5) * 2;
		var r = Std.int(((from >> 16) & 255) * (1 - weight) + ((to >> 16) & 255) * weight);
		var g = Std.int(((from >> 8) & 255) * (1 - weight) + ((to >> 8) & 255) * weight);
		var b = Std.int((from & 255) * (1 - weight) + (to & 255) * weight);
		return 0xFF000000 | (r << 16) | (g << 8) | b;
	}

	/** Bottom-row controls, each a key and what it does. */
	public static function hints():Array<FreeplayHint> return [
		{key:'CTRL', action:'Search'},
		{key:'UP/DOWN', action:'Browse'},
		{key:'LEFT/RIGHT', action:'Difficulty'},
		{key:'ENTER', action:'Play'},
		{key:'TAB', action:'Library'},
		{key:'F1', action:'Manage'},
		{key:'ESC', action:'Back'},
	];
}
