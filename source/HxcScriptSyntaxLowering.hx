package;

using StringTools;

/**
	Haxe syntax the game's HScript parser cannot read, rewritten into the plain
	form it can. It runs once on each finished HXC translation (script load time,
	never per frame), so the simple rescans after every edit are fine.

	- `cast x` and `cast(x, Type)` become `x`: an unsafe cast does nothing at run
	  time, and the parser has no `cast` keyword.
	- `(x : Type)` type checks become `(x)` for the same reason.
	- Object literals with quoted keys (`{"scale.x": 1.5}`, valid Haxe) become
	  `HxcCompatRuntime.objectOf(["scale.x", 1.5])`, because the parser only takes
	  quoted keys in JSON mode and a dotted key cannot be written unquoted.

	Strings and comments are never rewritten: every structural search runs on a
	copy where their contents are blanked out, at the same offsets.
**/
class HxcScriptSyntaxLowering {
	static inline var MAX_EDITS = 512;

	public static function lower(code:String):String {
		if (code == null || code == '')
			return code == null ? '' : code;
		var output = code;
		if (output.indexOf('cast') >= 0)
			output = lowerCasts(output);
		if (output.indexOf(':') >= 0) {
			output = lowerQuotedKeyObjects(output);
			output = lowerTypeChecks(output);
		}
		return output;
	}

	/**
		`import funkin.ui.FullScreenScaleMode as FSSM;` (or `in FSSM`) lets a script
		write the class under a short name. The translator knows classes by their
		own names, so spell every use of the alias out and keep a plain import.
		Only whole identifiers in code (and in `$name` / `${...}` string
		interpolation) change; a field access such as `a.FSSM` is left alone.
	**/
	public static function expandImportAliases(source:String):String {
		if (source == null || (source.indexOf(' as ') < 0 && source.indexOf(' in ') < 0))
			return source == null ? '' : source;
		var pattern = ~/^([ \t]*import[ \t]+)([A-Za-z_][A-Za-z0-9_.]*)[ \t]+(?:as|in)[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*;/m;
		var aliases = new Map<String, String>();
		var output = source;
		for (_ in 0...64) {
			if (!pattern.match(output))
				break;
			var full = pattern.matched(2);
			var alias = pattern.matched(3);
			var target = full.substr(full.lastIndexOf('.') + 1);
			if (alias != target)
				aliases.set(alias, target);
			output = pattern.matchedLeft() + pattern.matched(1) + full + ';' + pattern.matchedRight();
		}
		var any = false;
		for (_ in aliases.keys())
			any = true;
		return any ? renameIdentifiers(output, aliases) : output;
	}

	/** Rename whole identifiers in code and string interpolation, never in plain string text or comments. */
	static function renameIdentifiers(code:String, names:Map<String, String>):String {
		var output = new StringBuf();
		var index = 0;
		var length = code.length;
		// Innermost last: a quote character for string text, 0 for `${...}` code.
		var modes:Array<Int> = [];
		// Open braces inside each `${...}`, so its own closing brace is recognised.
		var braces:Array<Int> = [];
		while (index < length) {
			var c = code.charCodeAt(index);
			var quote = modes.length == 0 ? 0 : modes[modes.length - 1];
			if (quote != 0) {
				if (c == '\\'.code && index + 1 < length) {
					output.addSub(code, index, 2);
					index += 2;
					continue;
				}
				if (c == quote)
					modes.pop();
				else if (quote == "'".code && c == '$'.code && index + 1 < length) {
					var next = code.charCodeAt(index + 1);
					if (next == '{'.code) {
						output.addSub(code, index, 2);
						index += 2;
						modes.push(0);
						braces.push(0);
						continue;
					}
					if (isIdentifierStart(next)) {
						var end = identifierEnd(code, index + 1);
						output.addChar(c);
						output.add(renamed(code.substring(index + 1, end), names));
						index = end;
						continue;
					}
				}
				output.addChar(c);
				index++;
				continue;
			}
			if (c == '"'.code || c == "'".code) {
				modes.push(c);
				output.addChar(c);
				index++;
				continue;
			}
			if (c == '/'.code && index + 1 < length
				&& (code.charCodeAt(index + 1) == '/'.code || code.charCodeAt(index + 1) == '*'.code)) {
				var block = code.charCodeAt(index + 1) == '*'.code;
				var end = block ? code.indexOf('*/', index + 2) : code.indexOf('\n', index);
				end = end < 0 ? length : (block ? end + 2 : end);
				output.addSub(code, index, end - index);
				index = end;
				continue;
			}
			if (modes.length > 0) {
				if (c == '{'.code)
					braces[braces.length - 1]++;
				else if (c == '}'.code) {
					if (braces[braces.length - 1] == 0) {
						// The interpolation ends; back to the string around it.
						modes.pop();
						braces.pop();
					} else
						braces[braces.length - 1]--;
				}
			}
			if (isIdentifierStart(c) && (index == 0
				|| (!isIdentifierCode(code.charCodeAt(index - 1)) && code.charCodeAt(index - 1) != '.'.code))) {
				var end = identifierEnd(code, index);
				output.add(renamed(code.substring(index, end), names));
				index = end;
				continue;
			}
			output.addChar(c);
			index++;
		}
		return output.toString();
	}

	static inline function renamed(word:String, names:Map<String, String>):String
		return names.exists(word) ? names.get(word) : word;

	static function identifierEnd(code:String, start:Int):Int {
		var end = start + 1;
		while (end < code.length && isIdentifierCode(code.charCodeAt(end)))
			end++;
		return end;
	}

	static inline function isIdentifierStart(c:Int):Bool
		return c == '_'.code || (c >= 'a'.code && c <= 'z'.code) || (c >= 'A'.code && c <= 'Z'.code);

	static function lowerCasts(code:String):String {
		var output = code;
		var from = 0;
		for (_ in 0...MAX_EDITS) {
			var masked = mask(output);
			var at = findWord(masked, 'cast', from);
			if (at < 0)
				break;
			var next = skipSpaces(masked, at + 4);
			if (next < masked.length && masked.charCodeAt(next) == '('.code) {
				var close = matching(masked, next);
				if (close < 0)
					break;
				var commas = topLevel(masked, next + 1, close, ','.code);
				if (commas.length == 1) {
					// cast(value, Type): keep only the value, still in parentheses.
					output = output.substring(0, at) + '(' + output.substring(next + 1, commas[0]).trim() + ')'
						+ output.substring(close + 1);
				} else
					output = output.substring(0, at) + output.substring(next);
			} else
				output = output.substring(0, at) + output.substring(next);
			from = at;
		}
		return output;
	}

	static function lowerTypeChecks(code:String):String {
		var output = code;
		var masked = mask(output);
		var from = 0;
		var edits = 0;
		// Only rewrites count toward the bound: a long script has far more brackets than
		// type checks, and every bracket after a scan-count bound would be skipped.
		while (edits < MAX_EDITS) {
			var open = masked.indexOf('(', from);
			if (open < 0)
				break;
			from = open + 1;
			// The parser requires the type in `catch (e:Dynamic)`, so that one stays.
			if (precedingWord(masked, open) == 'catch')
				continue;
			var close = matching(masked, open);
			if (close < 0)
				break;
			var colons = topLevel(masked, open + 1, close, ':'.code);
			var questions = topLevel(masked, open + 1, close, '?'.code);
			var commas = topLevel(masked, open + 1, close, ','.code);
			if (colons.length == 1 && questions.length == 0 && commas.length == 0
				&& isTypeName(output.substring(colons[0] + 1, close).trim())
				&& output.substring(open + 1, colons[0]).trim() != '') {
				output = output.substring(0, colons[0]).rtrim() + output.substring(close);
				masked = mask(output);
				from = open;
				edits++;
			}
		}
		return output;
	}

	/** The identifier just before `index`, skipping spaces; '' when there is none. */
	static function precedingWord(text:String, index:Int):String {
		var end = skipSpacesBackward(text, index - 1);
		var start = end;
		while (start >= 0 && isIdentifierCode(text.charCodeAt(start)))
			start--;
		return text.substring(start + 1, end + 1);
	}

	static function skipSpacesBackward(text:String, index:Int):Int {
		while (index >= 0) {
			var c = text.charCodeAt(index);
			if (c != ' '.code && c != '\t'.code && c != '\n'.code && c != '\r'.code)
				break;
			index--;
		}
		return index;
	}

	static function lowerQuotedKeyObjects(code:String):String {
		var output = code;
		var masked = mask(output);
		var from = 0;
		var edits = 0;
		// As above, only rewrites count: plain blocks and objects are passed over freely.
		while (edits < MAX_EDITS) {
			var open = masked.indexOf('{', from);
			if (open < 0)
				break;
			from = open + 1;
			var keyStart = skipSpaces(masked, open + 1);
			if (keyStart >= masked.length)
				break;
			var quote = masked.charCodeAt(keyStart);
			if (quote != '"'.code && quote != "'".code)
				continue;
			var keyEnd = masked.indexOf(String.fromCharCode(quote), keyStart + 1);
			if (keyEnd < 0 || skipSpaces(masked, keyEnd + 1) >= masked.length
				|| masked.charCodeAt(skipSpaces(masked, keyEnd + 1)) != ':'.code)
				continue;
			var close = matching(masked, open);
			if (close < 0)
				break;
			var parts:Array<String> = [];
			var start = open + 1;
			var commas = topLevel(masked, open + 1, close, ','.code);
			commas.push(close);
			var valid = true;
			for (comma in commas) {
				var entryStart = start;
				start = comma + 1;
				if (output.substring(entryStart, comma).trim() == '')
					continue;
				var colon = topLevel(masked, entryStart, comma, ':'.code);
				if (colon.length == 0) {
					valid = false;
					break;
				}
				var key = output.substring(entryStart, colon[0]).trim();
				var value = output.substring(colon[0] + 1, comma).trim();
				if (!isQuoted(key)) {
					if (!isIdentifier(key)) {
						valid = false;
						break;
					}
					key = '"' + key + '"';
				}
				parts.push(key);
				parts.push(value);
			}
			if (!valid)
				continue;
			output = output.substring(0, open) + 'HxcCompatRuntime.objectOf([' + parts.join(', ') + '])'
				+ output.substring(close + 1);
			masked = mask(output);
			from = open;
			edits++;
		}
		return output;
	}

	/** Blank string contents and comments, keeping quotes and every offset. */
	static function mask(code:String):String {
		var output = new StringBuf();
		var index = 0;
		var length = code.length;
		while (index < length) {
			var c = code.charCodeAt(index);
			if (c == '"'.code || c == "'".code) {
				output.addChar(c);
				index++;
				while (index < length) {
					var inner = code.charCodeAt(index);
					if (inner == '\\'.code && index + 1 < length) {
						output.addChar('_'.code);
						output.addChar('_'.code);
						index += 2;
						continue;
					}
					if (inner == c) {
						output.addChar(c);
						index++;
						break;
					}
					output.addChar(inner == '\n'.code ? '\n'.code : '_'.code);
					index++;
				}
				continue;
			}
			if (c == '/'.code && index + 1 < length && code.charCodeAt(index + 1) == '/'.code) {
				while (index < length && code.charCodeAt(index) != '\n'.code) {
					output.addChar(' '.code);
					index++;
				}
				continue;
			}
			if (c == '/'.code && index + 1 < length && code.charCodeAt(index + 1) == '*'.code) {
				var end = code.indexOf('*/', index + 2);
				end = end < 0 ? length : end + 2;
				while (index < end) {
					output.addChar(code.charCodeAt(index) == '\n'.code ? '\n'.code : ' '.code);
					index++;
				}
				continue;
			}
			output.addChar(c);
			index++;
		}
		return output.toString();
	}

	static function findWord(masked:String, word:String, from:Int):Int {
		var at = masked.indexOf(word, from);
		while (at >= 0) {
			var before = at > 0 ? masked.charCodeAt(at - 1) : ' '.code;
			var after = at + word.length < masked.length ? masked.charCodeAt(at + word.length) : ' '.code;
			if (!isIdentifierCode(before) && before != '.'.code && !isIdentifierCode(after))
				return at;
			at = masked.indexOf(word, at + word.length);
		}
		return -1;
	}

	/** Index of the bracket closing the one at `open`, or -1. */
	static function matching(masked:String, open:Int):Int {
		var depth = 0;
		for (index in open...masked.length) {
			var c = masked.charCodeAt(index);
			if (c == '('.code || c == '['.code || c == '{'.code)
				depth++;
			else if (c == ')'.code || c == ']'.code || c == '}'.code) {
				depth--;
				if (depth == 0)
					return index;
				if (depth < 0)
					return -1;
			}
		}
		return -1;
	}

	/** Offsets of `code` between start and end that sit outside any nested bracket. */
	static function topLevel(masked:String, start:Int, end:Int, code:Int):Array<Int> {
		var found:Array<Int> = [];
		var depth = 0;
		for (index in start...end) {
			var c = masked.charCodeAt(index);
			if (c == '('.code || c == '['.code || c == '{'.code)
				depth++;
			else if (c == ')'.code || c == ']'.code || c == '}'.code)
				depth--;
			else if (depth == 0 && c == code)
				found.push(index);
		}
		return found;
	}

	static function skipSpaces(text:String, index:Int):Int {
		while (index < text.length) {
			var c = text.charCodeAt(index);
			if (c != ' '.code && c != '\t'.code && c != '\n'.code && c != '\r'.code)
				break;
			index++;
		}
		return index;
	}

	/** `Int`, `flixel.FlxSprite`, `Array<Map<String, Int>>`; not anonymous structures. */
	static function isTypeName(text:String):Bool {
		if (text == '')
			return false;
		var generic = text.indexOf('<');
		var head = generic < 0 ? text : text.substr(0, generic);
		if (generic >= 0 && (!text.endsWith('>') || text.indexOf('{') >= 0 || text.indexOf('(') >= 0))
			return false;
		for (part in head.split('.'))
			if (!isIdentifier(part.trim()))
				return false;
		// A type starts with a capital; a lower-case name after ':' is a value, as in `case a: b`.
		var last = head.split('.').pop().trim();
		return last.charCodeAt(0) >= 'A'.code && last.charCodeAt(0) <= 'Z'.code;
	}

	static function isQuoted(text:String):Bool {
		return text.length >= 2 && (text.charCodeAt(0) == '"'.code || text.charCodeAt(0) == "'".code)
			&& text.charCodeAt(text.length - 1) == text.charCodeAt(0);
	}

	static function isIdentifier(text:String):Bool {
		if (text == null || text == '' || (text.charCodeAt(0) >= '0'.code && text.charCodeAt(0) <= '9'.code))
			return false;
		for (index in 0...text.length)
			if (!isIdentifierCode(text.charCodeAt(index)))
				return false;
		return true;
	}

	static inline function isIdentifierCode(c:Int):Bool {
		return c == '_'.code || (c >= 'a'.code && c <= 'z'.code) || (c >= 'A'.code && c <= 'Z'.code)
			|| (c >= '0'.code && c <= '9'.code);
	}
}
