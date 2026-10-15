package;

using StringTools;

typedef SubtitleCue = {
	var start:Float;
	var end:Float;
	var text:String;
}

/**
	Timed subtitle lines read from an SRT file.

	SRT is the format V-Slice uses for song lyrics and cutscene lines: blocks
	separated by a blank line, each with an optional index, a
	`00:00:01,250 --> 00:00:02,000` time line, and one or more text lines.
	`textAt` gives every line visible at a time, newest first, which is how
	V-Slice stacks overlapping cues. Formatting tags are removed because the
	engine's lyric line draws plain text.
**/
class SubtitleTrack {
	public var cues(default, null):Array<SubtitleCue>;

	public function new(cues:Array<SubtitleCue>) {
		this.cues = cues == null ? [] : cues;
	}

	public static function parse(source:String):SubtitleTrack {
		var cues:Array<SubtitleCue> = [];
		if (source == null)
			return new SubtitleTrack(cues);
		var text = source.replace('\r\n', '\n').replace('\r', '\n');
		if (text.length > 0 && text.charCodeAt(0) == 0xFEFF)
			text = text.substr(1);
		for (block in text.split('\n\n')) {
			var trimmed = block.trim();
			if (trimmed == '')
				continue;
			var lines = trimmed.split('\n');
			var index = 0;
			if (lines.length > 0 && isIndex(lines[0]))
				index = 1;
			if (index >= lines.length)
				continue;
			var times = parseTimeLine(lines[index]);
			if (times == null)
				continue;
			var body = [for (line in lines.slice(index + 1)) plain(line)].join('\n').trim();
			cues.push({start: times[0], end: times[1], text: body});
		}
		cues.sort(function(a, b) return a.start < b.start ? -1 : (a.start > b.start ? 1 : 0));
		return new SubtitleTrack(cues);
	}

	/** A number that changes whenever the set of visible cues changes, so a
	 * per-frame caller can skip rebuilding the text. It allocates nothing. */
	public function visibleKey(timeMs:Float):Int {
		var key = 0;
		for (index in 0...cues.length) {
			var cue = cues[index];
			if (cue.start > timeMs)
				break;
			if (timeMs <= cue.end)
				key = key * 31 + index + 1;
		}
		return key;
	}

	/** Lines showing at `timeMs`, newest first, joined by line breaks. */
	public function textAt(timeMs:Float):String {
		var visible:Array<String> = [];
		for (cue in cues) {
			if (cue.start > timeMs)
				break;
			if (timeMs <= cue.end && cue.text != '')
				visible.unshift(cue.text);
		}
		return visible.join('\n');
	}

	/** Parse `HH:MM:SS,mmm --> HH:MM:SS,mmm` into start and end milliseconds. */
	public static function parseTimeLine(line:String):Array<Float> {
		if (line == null)
			return null;
		for (arrow in ['-->', '->']) {
			var at = line.indexOf(arrow);
			if (at < 0)
				continue;
			var start = parseTime(line.substr(0, at));
			// Position settings may follow the end time.
			var rest = line.substr(at + arrow.length).trim();
			var space = rest.indexOf(' ');
			var end = parseTime(space < 0 ? rest : rest.substr(0, space));
			if (Math.isNaN(start) || Math.isNaN(end))
				return null;
			return [start, Math.max(start, end)];
		}
		return null;
	}

	static function parseTime(value:String):Float {
		var clean = value.trim().replace(',', '.');
		var parts = clean.split(':');
		if (parts.length < 2 || parts.length > 3)
			return Math.NaN;
		var seconds = 0.0;
		for (part in parts) {
			var number = Std.parseFloat(part);
			if (Math.isNaN(number) || part.trim() == '')
				return Math.NaN;
			seconds = seconds * 60 + number;
		}
		return Math.round(seconds * 1000);
	}

	static function isIndex(line:String):Bool {
		var clean = line.trim();
		if (clean == '')
			return false;
		for (i in 0...clean.length) {
			var code = clean.charCodeAt(i);
			if (code < '0'.code || code > '9'.code)
				return false;
		}
		return true;
	}

	/** Remove `<i>`, `<font ...>` and `{...}` style tags. */
	static function plain(line:String):String {
		var output = new StringBuf();
		var depth = 0;
		for (i in 0...line.length) {
			var character = line.charAt(i);
			if (character == '<' || character == '{') {
				depth++;
				continue;
			}
			if ((character == '>' || character == '}') && depth > 0) {
				depth--;
				continue;
			}
			if (depth == 0)
				output.add(character);
		}
		return output.toString();
	}
}
