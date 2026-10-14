package;

/**
	Lua 5.1 string patterns: the matcher behind string.find, string.match,
	string.gmatch and string.gsub.

	This follows the reference matcher step for step (classes, sets, the four
	quantifiers, anchors, captures, position captures, back references, %b and
	%f), so a pattern that works in a stock Lua build gives the same answer
	here. Indices that leave this class are one based, like Lua's.
*/
class LuaPattern {
	static inline var MAX_CAPTURES = 32;
	static inline var CAPTURE_UNFINISHED = -1;
	static inline var CAPTURE_POSITION = -2;
	static inline var ESCAPE = 37; // %
	static inline var SPECIALS = '^$*+?.([%-';

	var source:String;
	var pattern:String;
	var sourceLength:Int;
	var patternLength:Int;
	var level:Int = 0;
	var captureStart:Array<Int> = [];
	var captureLength:Array<Int> = [];

	function new(source:String, pattern:String) {
		this.source = source;
		this.pattern = pattern;
		sourceLength = source.length;
		patternLength = pattern.length;
	}

	/**
		string.find. Returns null for no match, otherwise the one-based start
		and end followed by any captures. `init` is the one-based start
		position (negative counts from the end) and `plain` turns the pattern
		into ordinary text.
	*/
	public static function find(source:String, pattern:String, ?init:Null<Int>, plain:Bool = false):Array<Dynamic> {
		return search(source, pattern, init, plain, true);
	}

	/** string.match. Returns null for no match, otherwise the captures, or the whole match when the pattern has none. */
	public static function match(source:String, pattern:String, ?init:Null<Int>):Array<Dynamic> {
		return search(source, pattern, init, false, false);
	}

	/** Every match string.gmatch would step through, each as its capture list (the whole match when there are no captures). */
	public static function gmatch(source:String, pattern:String):Array<Array<Dynamic>> {
		var matcher = new LuaPattern(source, pattern);
		var results:Array<Array<Dynamic>> = [];
		var position = 0;
		while (position <= matcher.sourceLength) {
			matcher.level = 0;
			var end = matcher.doMatch(position, 0);
			if (end == -1) {
				position++;
				continue;
			}
			results.push(matcher.captures(position, end, true));
			// An empty match still has to move on, or the loop never ends.
			position = end == position ? end + 1 : end;
		}
		return results;
	}

	/**
		string.gsub. `replacement` is a string (with %0-%9), a function called
		with the captures, or a table read through `lookup(table, key)`.
		Returns [result string, number of substitutions].
	*/
	public static function gsub(source:String, pattern:String, replacement:Dynamic, ?maximum:Null<Int>,
			?lookup:Dynamic->Dynamic->Dynamic):Array<Dynamic> {
		var anchored = pattern.length > 0 && pattern.charCodeAt(0) == 94;
		var matcher = new LuaPattern(source, pattern);
		var patternStart = anchored ? 1 : 0;
		var limit = maximum == null ? matcher.sourceLength + 1 : maximum;
		var output = new StringBuf();
		var position = 0;
		var count = 0;
		while (count < limit) {
			matcher.level = 0;
			var end = matcher.doMatch(position, patternStart);
			if (end != -1) {
				count++;
				matcher.addReplacement(output, position, end, replacement, lookup);
			}
			if (end != -1 && end > position)
				position = end;
			else if (position < matcher.sourceLength)
				output.add(source.charAt(position++));
			else
				break;
			if (anchored)
				break;
		}
		output.add(source.substr(position));
		return [output.toString(), count];
	}

	/** True when the text has no pattern magic in it, so a plain search gives the same result. */
	public static function isPlain(pattern:String):Bool {
		for (index in 0...pattern.length)
			if (SPECIALS.indexOf(pattern.charAt(index)) >= 0)
				return false;
		return true;
	}

	static function search(source:String, pattern:String, init:Null<Int>, plain:Bool, wantPositions:Bool):Array<Dynamic> {
		var length = source.length;
		var start = init == null ? 1 : init;
		if (start < 0)
			start = length + start + 1;
		if (start < 1)
			start = 1;
		start--;
		if (start > length)
			start = length;
		if (wantPositions && (plain || isPlain(pattern))) {
			var found = pattern == '' ? start : source.indexOf(pattern, start);
			return found < 0 ? null : [found + 1, found + pattern.length];
		}
		var anchored = pattern.length > 0 && pattern.charCodeAt(0) == 94;
		var matcher = new LuaPattern(source, pattern);
		var patternStart = anchored ? 1 : 0;
		var position = start;
		while (true) {
			matcher.level = 0;
			var end = matcher.doMatch(position, patternStart);
			if (end != -1) {
				if (!wantPositions)
					return matcher.captures(position, end, true);
				var result:Array<Dynamic> = [position + 1, end];
				for (capture in matcher.captures(position, end, false))
					result.push(capture);
				return result;
			}
			position++;
			if (anchored || position > length)
				return null;
		}
	}

	inline function patternCode(index:Int):Int {
		return index < patternLength ? StringTools.fastCodeAt(pattern, index) : -1;
	}

	inline function sourceCode(index:Int):Int {
		return StringTools.fastCodeAt(source, index);
	}

	/** Match the pattern from `p` against the subject from `s`. Returns the end of the match, or -1. */
	function doMatch(s:Int, p:Int):Int {
		while (true) {
			if (p >= patternLength)
				return s;
			var code = patternCode(p);
			if (code == 40) { // (
				if (patternCode(p + 1) == 41)
					return startCapture(s, p + 2, CAPTURE_POSITION);
				return startCapture(s, p + 1, CAPTURE_UNFINISHED);
			}
			if (code == 41) // )
				return endCapture(s, p + 1);
			if (code == ESCAPE) {
				var next = patternCode(p + 1);
				if (next == 98) { // %b
					s = matchBalance(s, p + 2);
					if (s == -1)
						return -1;
					p += 4;
					continue;
				}
				if (next == 102) { // %f
					p += 2;
					if (patternCode(p) != 91)
						throw "missing '[' after '%f' in pattern";
					var setEnd = classEnd(p);
					var previous = s == 0 ? 0 : sourceCode(s - 1);
					var current = s < sourceLength ? sourceCode(s) : 0;
					if (matchSet(previous, p, setEnd - 1) || !matchSet(current, p, setEnd - 1))
						return -1;
					p = setEnd;
					continue;
				}
				if (next >= 48 && next <= 57) { // %1-%9
					s = matchBackReference(s, next);
					if (s == -1)
						return -1;
					p += 2;
					continue;
				}
			} else if (code == 36 && p + 1 == patternLength) // $ at the very end
				return s == sourceLength ? s : -1;

			var end = classEnd(p);
			var matched = s < sourceLength && singleMatch(sourceCode(s), p, end);
			switch (patternCode(end)) {
				case 63: // ?
					if (matched) {
						var result = doMatch(s + 1, end + 1);
						if (result != -1)
							return result;
					}
					p = end + 1;
				case 42: // *
					return maxExpand(s, p, end);
				case 43: // +
					return matched ? maxExpand(s + 1, p, end) : -1;
				case 45: // -
					return minExpand(s, p, end);
				default:
					if (!matched)
						return -1;
					s++;
					p = end;
			}
		}
	}

	/** Index just past the single-character class that starts at `p`. */
	function classEnd(p:Int):Int {
		var code = patternCode(p++);
		if (code == ESCAPE) {
			if (p >= patternLength)
				throw "malformed pattern (ends with '%')";
			return p + 1;
		}
		if (code == 91) { // [
			if (patternCode(p) == 94)
				p++;
			do {
				if (p >= patternLength)
					throw "malformed pattern (missing ']')";
				var inner = patternCode(p++);
				if (inner == ESCAPE && p < patternLength)
					p++;
			} while (patternCode(p) != 93);
			return p + 1;
		}
		return p;
	}

	function singleMatch(code:Int, p:Int, end:Int):Bool {
		return switch (patternCode(p)) {
			case 46: true; // .
			case 37: matchClass(code, patternCode(p + 1));
			case 91: matchSet(code, p, end - 1);
			case other: other == code;
		};
	}

	/** `p` is the opening bracket and `end` the closing one. */
	function matchSet(code:Int, p:Int, end:Int):Bool {
		var positive = true;
		if (patternCode(p + 1) == 94) {
			positive = false;
			p++;
		}
		while (++p < end) {
			var current = patternCode(p);
			if (current == ESCAPE) {
				p++;
				if (matchClass(code, patternCode(p)))
					return positive;
			} else if (patternCode(p + 1) == 45 && p + 2 < end) {
				p += 2;
				if (current <= code && code <= patternCode(p))
					return positive;
			} else if (current == code)
				return positive;
		}
		return !positive;
	}

	/** %a, %d and friends. An upper case class letter means "anything but". */
	public static function matchClass(code:Int, classCode:Int):Bool {
		var lowerClass = classCode >= 65 && classCode <= 90 ? classCode + 32 : classCode;
		var result = switch (lowerClass) {
			case 97: isAlpha(code); // a
			case 99: code < 32 || code == 127; // c
			case 100: isDigit(code); // d
			case 108: code >= 97 && code <= 122; // l
			case 112: isPunctuation(code); // p
			case 115: isSpace(code); // s
			case 117: code >= 65 && code <= 90; // u
			case 119: isAlpha(code) || isDigit(code); // w
			case 120: isDigit(code) || (code >= 65 && code <= 70) || (code >= 97 && code <= 102); // x
			case 122: code == 0; // z
			default: return classCode == code;
		};
		return lowerClass == classCode ? result : !result;
	}

	static inline function isAlpha(code:Int):Bool {
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122);
	}

	static inline function isDigit(code:Int):Bool {
		return code >= 48 && code <= 57;
	}

	public static inline function isSpace(code:Int):Bool {
		return code == 32 || (code >= 9 && code <= 13);
	}

	static inline function isPunctuation(code:Int):Bool {
		return code > 32 && code < 127 && !isAlpha(code) && !isDigit(code);
	}

	function maxExpand(s:Int, p:Int, end:Int):Int {
		var count = 0;
		while (s + count < sourceLength && singleMatch(sourceCode(s + count), p, end))
			count++;
		// Greedy: try the longest run first and give characters back one at a time.
		while (count >= 0) {
			var result = doMatch(s + count, end + 1);
			if (result != -1)
				return result;
			count--;
		}
		return -1;
	}

	function minExpand(s:Int, p:Int, end:Int):Int {
		while (true) {
			var result = doMatch(s, end + 1);
			if (result != -1)
				return result;
			if (s < sourceLength && singleMatch(sourceCode(s), p, end))
				s++;
			else
				return -1;
		}
	}

	function startCapture(s:Int, p:Int, what:Int):Int {
		if (level >= MAX_CAPTURES)
			throw 'too many captures';
		captureStart[level] = s;
		captureLength[level] = what;
		level++;
		var result = doMatch(s, p);
		if (result == -1)
			level--;
		return result;
	}

	function endCapture(s:Int, p:Int):Int {
		var open = -1;
		var index = level - 1;
		while (index >= 0) {
			if (captureLength[index] == CAPTURE_UNFINISHED) {
				open = index;
				break;
			}
			index--;
		}
		if (open < 0)
			throw 'invalid pattern capture';
		captureLength[open] = s - captureStart[open];
		var result = doMatch(s, p);
		if (result == -1)
			captureLength[open] = CAPTURE_UNFINISHED;
		return result;
	}

	function matchBalance(s:Int, p:Int):Int {
		if (p + 1 >= patternLength)
			throw 'unbalanced pattern';
		var open = patternCode(p);
		var close = patternCode(p + 1);
		if (s >= sourceLength || sourceCode(s) != open)
			return -1;
		var depth = 1;
		var index = s + 1;
		while (index < sourceLength) {
			var code = sourceCode(index);
			if (code == close) {
				if (--depth == 0)
					return index + 1;
			} else if (code == open)
				depth++;
			index++;
		}
		return -1;
	}

	function matchBackReference(s:Int, digit:Int):Int {
		var index = digit - 49;
		if (index < 0 || index >= level || captureLength[index] == CAPTURE_UNFINISHED)
			throw 'invalid capture index';
		var length = captureLength[index];
		// A position capture has no text to repeat, so it matches the empty string.
		if (length < 0)
			length = 0;
		if (sourceLength - s >= length && source.substr(captureStart[index], length) == source.substr(s, length))
			return s + length;
		return -1;
	}

	function capture(index:Int, s:Int, end:Int):Dynamic {
		if (index >= level) {
			if (index == 0)
				return source.substring(s, end);
			throw 'invalid capture index';
		}
		var length = captureLength[index];
		if (length == CAPTURE_UNFINISHED)
			throw 'unfinished capture';
		if (length == CAPTURE_POSITION)
			return captureStart[index] + 1;
		return source.substr(captureStart[index], length);
	}

	function captures(s:Int, end:Int, wholeWhenNone:Bool):Array<Dynamic> {
		var count = level == 0 && wholeWhenNone ? 1 : level;
		return [for (index in 0...count) capture(index, s, end)];
	}

	function addReplacement(output:StringBuf, s:Int, end:Int, replacement:Dynamic,
			lookup:Dynamic->Dynamic->Dynamic):Void {
		var value:Dynamic;
		if (Std.isOfType(replacement, String) || Std.isOfType(replacement, Int) || Std.isOfType(replacement, Float)) {
			var text:String = Std.string(replacement);
			var index = 0;
			while (index < text.length) {
				var code = StringTools.fastCodeAt(text, index);
				if (code != ESCAPE) {
					output.add(text.charAt(index));
					index++;
					continue;
				}
				index++;
				// A lone % at the very end is not an error in Lua 5.1, it just adds nothing visible.
				if (index >= text.length)
					break;
				var next = StringTools.fastCodeAt(text, index);
				if (next == 48)
					output.add(source.substring(s, end));
				else if (isDigit(next))
					output.add(Std.string(capture(next - 49, s, end)));
				else
					output.add(text.charAt(index));
				index++;
			}
			return;
		}
		if (Reflect.isFunction(replacement))
			value = Reflect.callMethod(null, replacement, captures(s, end, true));
		else if (replacement != null) {
			var key = capture(0, s, end);
			value = lookup != null ? lookup(replacement, key) : Reflect.field(replacement, Std.string(key));
		} else
			throw 'bad argument #3 to gsub (string/function/table expected)';
		value = LuaValues.first(value);
		if (value == null || value == false) {
			// nil or false keeps the original text.
			output.add(source.substring(s, end));
			return;
		}
		if (!Std.isOfType(value, String) && !Std.isOfType(value, Int) && !Std.isOfType(value, Float))
			throw 'invalid replacement value';
		output.add(Std.string(value));
	}
}
