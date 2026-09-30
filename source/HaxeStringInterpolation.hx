package;

/** Shared lexical lowering for Haxe single-quoted interpolation. */
class HaxeStringInterpolation {
	/** Haxe interpolates expressions in single-quoted strings; HScript keeps
	 * the dollar text literally. Preserve comments and double-quoted strings. */
	public static function normalize(source:String):{source:String, error:String} {
		var out = new StringBuf();
		var i = 0;
		while (i < source.length) {
			var ch = source.charAt(i);
			var next = source.charAt(i + 1);
			if (ch == '/' && next == '/') {
				var end = source.indexOf('\n', i + 2);
				if (end < 0) end = source.length;
				out.add(source.substring(i, end));
				i = end;
				continue;
			}
			if (ch == '/' && next == '*') {
				var end = source.indexOf('*/', i + 2);
				if (end < 0) end = source.length - 2;
				out.add(source.substring(i, end + 2));
				i = end + 2;
				continue;
			}
			if (ch != "'" && ch != '"') {
				out.add(ch);
				i++;
				continue;
			}
			var quote = ch;
			var start = i;
			var escaped = false;
			i++;
			while (i < source.length) {
				ch = source.charAt(i);
				if (quote == "'" && !escaped && ch == '$' && source.charAt(i + 1) == '$') {
					i += 2;
					continue;
				}
				if (quote == "'" && !escaped && ch == '$' && source.charAt(i + 1) == '{') {
					var expressionEnd = findBracedInterpolationEnd(source, i + 2);
					if (expressionEnd.error != '') return {source:source, error:expressionEnd.error};
					i = expressionEnd.end + 1;
					escaped = false;
					continue;
				}
				if (!escaped && ch == quote) break;
				if (ch == '\\' && !escaped) escaped = true; else escaped = false;
				i++;
			}
			if (i >= source.length) {
				out.add(source.substr(start));
				break;
			}
			var end = i++;
			if (quote == '"') {
				out.add(source.substring(start, i));
				continue;
			}
			var pieces:Array<String> = [];
			var segment = start + 1;
			var cursor = segment;
			while (cursor < end) {
				if (source.charAt(cursor) != '$' || interpolationCharacterIsEscaped(source, cursor)) {
					cursor++;
					continue;
				}
				if (source.charAt(cursor + 1) == '$') {
					if (cursor > segment) pieces.push("'" + source.substring(segment, cursor) + "'");
					pieces.push("'$'");
					cursor += 2;
					segment = cursor;
					continue;
				}
				if (source.charAt(cursor + 1) == '{') {
					var expressionEnd = findBracedInterpolationEnd(source, cursor + 2);
					if (expressionEnd.error != '') return {source:source, error:expressionEnd.error};
					if (cursor > segment) pieces.push("'" + source.substring(segment, cursor) + "'");
					var expression = StringTools.trim(source.substring(cursor + 2, expressionEnd.end));
					var nested = normalize(expression);
					if (nested.error != '') return nested;
					pieces.push("'' + (" + nested.source + ')');
					cursor = expressionEnd.end + 1;
					segment = cursor;
					continue;
				}
				var nameStart = cursor + 1;
				if (!letter(source.charAt(nameStart))) {
					cursor++;
					continue;
				}
				var nameEnd = nameStart + 1;
				while (nameEnd < end && (letter(source.charAt(nameEnd))
					|| ~/^[0-9]$/.match(source.charAt(nameEnd)))) nameEnd++;
				if (cursor > segment) pieces.push("'" + source.substring(segment, cursor) + "'");
				pieces.push("'' + (" + source.substring(nameStart, nameEnd) + ')');
				cursor = nameEnd;
				segment = cursor;
			}
			if (pieces.length == 0) out.add(source.substring(start, i));
			else {
				if (segment < end) pieces.push("'" + source.substring(segment, end) + "'");
				out.add('(' + pieces.join(' + ') + ')');
			}
		}
		return {source:out.toString(), error:''};
	}

	/** Find the matching closing brace for `${...}`, ignoring braces in nested
	 * strings and comments. The returned index points at the matching `}`. */
	static function findBracedInterpolationEnd(source:String, start:Int):{end:Int, error:String} {
		var depth = 1;
		var cursor = start;
		while (cursor < source.length) {
			var ch = source.charAt(cursor);
			var next = cursor + 1 < source.length ? source.charAt(cursor + 1) : '';
			if (ch == '/' && next == '/') {
				var lineEnd = source.indexOf('\n', cursor + 2);
				if (lineEnd < 0) return {end:-1, error:'Unterminated Haxe interpolation expression'};
				cursor = lineEnd + 1;
				continue;
			}
			if (ch == '/' && next == '*') {
				var commentEnd = source.indexOf('*/', cursor + 2);
				if (commentEnd < 0)
					return {end:-1, error:'Unterminated block comment in Haxe interpolation expression'};
				cursor = commentEnd + 2;
				continue;
			}
			if (ch == "'" || ch == '"') {
				var stringEnd = skipInterpolationExpressionString(source, cursor);
				if (stringEnd.error != '') return {end:-1, error:stringEnd.error};
				cursor = stringEnd.end;
				continue;
			}
			if (ch == '{') depth++;
			else if (ch == '}') {
				depth--;
				if (depth == 0) {
					if (StringTools.trim(source.substring(start, cursor)) == '')
						return {end:-1, error:'Empty Haxe interpolation expression'};
					return {end:cursor, error:''};
				}
			}
			cursor++;
		}
		return {end:-1, error:'Unterminated Haxe interpolation expression'};
	}

	/** Skip one quoted string inside a braced Haxe interpolation expression. */
	static function skipInterpolationExpressionString(source:String, start:Int):{end:Int, error:String} {
		var quote = source.charAt(start);
		var escaped = false;
		var cursor = start + 1;
		while (cursor < source.length) {
			var ch = source.charAt(cursor);
			if (!escaped && ch == quote) return {end:cursor + 1, error:''};
			if (ch == '\\' && !escaped) escaped = true; else escaped = false;
			cursor++;
		}
		return {end:-1, error:'Unterminated string in Haxe interpolation expression'};
	}

	/** Count preceding backslashes so `\\$name` still interpolates while
	 * `\$name` remains literal. */
	static function interpolationCharacterIsEscaped(source:String, index:Int):Bool {
		var backslashes = 0;
		var cursor = index - 1;
		while (cursor >= 0 && source.charAt(cursor) == '\\') {
			backslashes++;
			cursor--;
		}
		return backslashes % 2 == 1;
	}

	static function letter(char:String):Bool {
		return char != '' && ~/^[A-Za-z_]$/.match(char);
	}
}
