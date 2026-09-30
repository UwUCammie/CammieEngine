package;

import hscript.Expr;
import hscript.ParserEx;
import hscript.Tools;

using StringTools;

typedef CodenameScriptDiagnostic = {
	var code:String;
	var message:String;
	var line:Int;
	@:optional var recoverable:Bool;
}

typedef CodenameScriptParseResult = {
	var source:String;
	var program:Null<Expr>;
	var imports:Array<String>;
	var publicVariables:Array<String>;
	var diagnostics:Array<CodenameScriptDiagnostic>;
	var sourceUseDiagnostics:Array<String>;
	var normalizationTrace:Array<String>;
}

/** Parse-only preparation for classless Codename song and stage companions.
 * The caller supplies exact import bindings and evaluates the program itself. */
class CodenameScriptParser {
	/** Drop only top-level enum declarations whose type name has no code token
		reference elsewhere in this source file. Constructor names and Haxe
		interpolations count as references too. All other declarations remain
		fatal through the regular classless-runtime diagnostic below. */
	static function removeUnusedTopLevelEnums(source:String):{source:String, removed:Array<{name:String, line:Int}>} {
		var result = source == null ? '' : source;
		var mask = codeMask(result);
		var candidates:Array<{name:String, start:Int, end:Int, references:Array<String>}> = [];
		var depth = 0;
		var cursor = 0;
		while (cursor < mask.length) {
			if (depth == 0 && mask.substr(cursor, 4) == 'enum'
				&& (cursor == 0 || !isIdentifierChar(mask.charAt(cursor - 1)))
				&& (cursor + 4 >= mask.length || !isIdentifierChar(mask.charAt(cursor + 4)))) {
				var nameStart = skipSpaces(mask, cursor + 4);
				var nameEnd = nameStart;
				while (nameEnd < mask.length && isIdentifierChar(mask.charAt(nameEnd))) nameEnd++;
				var name = mask.substring(nameStart, nameEnd);
				var open = skipSpaces(mask, nameEnd);
				if (name != '' && open < mask.length && mask.charAt(open) == '{') {
					var braceDepth = 1;
					var close = open + 1;
					while (close < mask.length && braceDepth > 0) {
						if (mask.charAt(close) == '{') braceDepth++;
						else if (mask.charAt(close) == '}') braceDepth--;
						close++;
					}
					if (braceDepth == 0) {
						var end = close;
						while (end < mask.length && (mask.charAt(end) == ' ' || mask.charAt(end) == '\t')) end++;
						if (end < mask.length && mask.charAt(end) == ';') end++;
						var references = [name];
						for (identifier in topLevelEnumIdentifiers(mask, open, close - 1))
							if (references.indexOf(identifier) < 0) references.push(identifier);
						candidates.push({name:name, start:cursor, end:end, references:references});
						cursor = end;
						continue;
					}
				}
			}
			var ch = mask.charAt(cursor);
			if (ch == '{') depth++;
			else if (ch == '}') depth--;
			cursor++;
		}
		if (candidates.length == 0) return {source:result, removed:[]};
		var chars = result.split('');
		var removed:Array<{name:String, line:Int}> = [];
		for (candidate in candidates) {
			var referenced = false;
			for (identifier in candidate.references) {
				if (hasIdentifierReference(mask, identifier, candidate.start, candidate.end)
					|| hasInterpolatedIdentifierReference(result, identifier, candidate.start, candidate.end)) {
					referenced = true;
					break;
				}
			}
			if (referenced) continue;
			removed.push({name:candidate.name, line:lineAt(source, candidate.start)});
			for (index in candidate.start...candidate.end)
				if (chars[index] != '\n' && chars[index] != '\r') chars[index] = ' ';
		}
		return {source:chars.join(''), removed:removed};
	}

	/** Collect selected-module top-level public var names before access
	 * modifiers are normalized away. These are the fields Codename exposes to
	 * other active song/stage script scopes. */
	static function publicTopLevelVariables(source:String):Array<String> {
		var names:Array<String> = [];
		if (source == null || source == '') return names;
		var mask = codeMask(source);
		var depth = 0;
		var cursor = 0;
		while (cursor < mask.length) {
			if (depth == 0 && mask.substr(cursor, 6) == 'public'
				&& (cursor == 0 || !isIdentifierChar(mask.charAt(cursor - 1)))
				&& (cursor + 6 >= mask.length || !isIdentifierChar(mask.charAt(cursor + 6)))) {
				var tokenStart = skipSpaces(mask, cursor + 6);
				var tokenEnd = tokenStart;
				var token = '';
				var modifiers = 0;
				while (modifiers++ < 8) {
					tokenEnd = tokenStart;
					while (tokenEnd < mask.length && letter(mask.charAt(tokenEnd))) tokenEnd++;
					token = mask.substring(tokenStart, tokenEnd);
					if (token == 'var') {
						var declarationStart = tokenEnd;
						var statementEnd = findVariableStatementEnd(mask, declarationStart);
						if (statementEnd >= 0) {
							for (segment in splitVariableDeclaration(source, mask, declarationStart, statementEnd)) {
								var assignment = topLevelAssignment(mask, segment.start, segment.end);
								var prefixEnd = assignment < 0 ? segment.end : assignment;
								var prefix = StringTools.trim(source.substring(segment.start, prefixEnd));
								var match = ~/^([A-Za-z_][A-Za-z0-9_]*)(\s*:\s*[\s\S]+)?$/;
								if (match.match(prefix)) {
									var name = match.matched(1);
									if (names.indexOf(name) < 0) names.push(name);
								}
							}
						}
						break;
					}
					if (token != 'static' && token != 'inline' && token != 'extern'
						&& token != 'override') break;
					tokenStart = skipSpaces(mask, tokenEnd);
				}
			}
			var ch = mask.charAt(cursor);
			if (ch == '{') depth++;
			else if (ch == '}') depth--;
			cursor++;
		}
		return names;
	}

	/** Read ordinary top-level Haxe imports without parsing or evaluating the
	 * surrounding classless script. The same grammar is enforced by prepare(). */
	public static function importPaths(source:String):Array<String> {
		var paths:Array<String> = [];
		if (source == null || source == '') return paths;
		var mask = codeMask(source);
		var depth = 0;
		var cursor = 0;
		while (cursor < mask.length) {
			var lineStart = cursor;
			while (cursor < mask.length && (mask.charAt(cursor) == ' ' || mask.charAt(cursor) == '\t')) cursor++;
			var start = cursor;
			while (cursor < mask.length && letter(mask.charAt(cursor))) cursor++;
			var word = mask.substring(start, cursor);
			if (depth == 0 && word == 'import'
				&& (cursor >= mask.length || !~/^[A-Za-z0-9_]$/.match(mask.charAt(cursor)))) {
				var end = mask.indexOf(';', cursor);
				if (end >= 0) {
				var declaration = parseImportArgument(mask.substring(cursor, end));
				if (declaration.path != '' && paths.indexOf(declaration.path) < 0)
					paths.push(declaration.path);
					cursor = end + 1;
					continue;
				}
			}
			cursor = lineStart;
			while (cursor < mask.length && mask.charAt(cursor) != '\n') {
				if (mask.charAt(cursor) == '{') depth++;
				else if (mask.charAt(cursor) == '}') depth--;
				cursor++;
			}
			if (cursor < mask.length) cursor++;
		}
		return paths;
	}

	/** Haxe import aliases keep the original module path for binding lookup.
		The alias itself is lowered to a runtime variable by prepare(). */
	static function parseImportArgument(raw:String):{path:String, alias:String} {
		var text = StringTools.trim(raw == null ? '' : raw);
		var aliased = ~/^([A-Za-z_][A-Za-z0-9_.]*)[ \t\r\n]+as[ \t\r\n]+([A-Za-z_][A-Za-z0-9_]*)$/;
		var path = text;
		var alias = '';
		if (aliased.match(text)) {
			path = aliased.matched(1);
			alias = aliased.matched(2);
		} else {
			path = ~/[ \t\r\n]+/g.replace(text, '');
		}
		if (!~/^[A-Za-z_][A-Za-z0-9_.]*$/.match(path)) return {path:'', alias:''};
		return {path:path, alias:alias};
	}

	/** Identifiers at the enum body's immediate brace/argument level are
	 * constructor names. Treat any later mention as a use, including the
	 * unqualified constructor form accepted by Haxe. */
	static function topLevelEnumIdentifiers(mask:String, open:Int, close:Int):Array<String> {
		var identifiers:Array<String> = [];
		var braces = 0;
		var parens = 0;
		var brackets = 0;
		var cursor = open + 1;
		while (cursor < close) {
			var ch = mask.charAt(cursor);
			if (braces == 0 && parens == 0 && brackets == 0 && letter(ch)
				&& (cursor == 0 || !isIdentifierChar(mask.charAt(cursor - 1)))) {
				var tokenEnd = cursor + 1;
				while (tokenEnd < close && isIdentifierChar(mask.charAt(tokenEnd))) tokenEnd++;
				identifiers.push(mask.substring(cursor, tokenEnd));
				cursor = tokenEnd;
				continue;
			}
			switch (ch) {
				case '{': braces++;
				case '}': braces--;
				case '(': parens++;
				case ')': parens--;
				case '[': brackets++;
				case ']': brackets--;
				default:
			}
			cursor++;
		}
		return identifiers;
	}

	static function hasIdentifierReference(mask:String, name:String, excludedStart:Int, excludedEnd:Int):Bool {
		var scan = 0;
		while (scan < mask.length) {
			if (scan >= excludedStart && scan < excludedEnd) {
				scan = excludedEnd;
				continue;
			}
			if (letter(mask.charAt(scan))
				&& (scan == 0 || !isIdentifierChar(mask.charAt(scan - 1)))) {
				var tokenEnd = scan + 1;
				while (tokenEnd < mask.length && isIdentifierChar(mask.charAt(tokenEnd))) tokenEnd++;
				if (tokenEnd - scan == name.length && mask.substr(scan, name.length) == name) return true;
				scan = tokenEnd;
			} else scan++;
		}
		return false;
	}

	/** Haxe interpolates single-quoted strings. These references are hidden by
	 * codeMask, so inspect only interpolation expressions and simple $names. */
	static function hasInterpolatedIdentifierReference(source:String, name:String,
		excludedStart:Int, excludedEnd:Int):Bool {
		var cursor = 0;
		while (cursor < source.length) {
			if (cursor >= excludedStart && cursor < excludedEnd) {
				cursor = excludedEnd;
				continue;
			}
			var ch = source.charAt(cursor);
			var next = source.charAt(cursor + 1);
			if (ch == '/' && next == '/') {
				var end = source.indexOf('\n', cursor + 2);
				cursor = end < 0 ? source.length : end + 1;
				continue;
			}
			if (ch == '/' && next == '*') {
				var end = source.indexOf('*/', cursor + 2);
				cursor = end < 0 ? source.length : end + 2;
				continue;
			}
			if (ch != "'" && ch != '"') {
				cursor++;
				continue;
			}
			var quote = ch;
			cursor++;
			while (cursor < source.length && source.charAt(cursor) != quote) {
				if (source.charAt(cursor) == '\\') {
					cursor += cursor + 1 < source.length ? 2 : 1;
					continue;
				}
				if (quote == "'" && source.charAt(cursor) == '$') {
					var expressionStart = cursor + 1;
					if (source.charAt(expressionStart) == '{') {
						expressionStart++;
						var expressionEnd = expressionStart;
						var depth = 1;
						while (expressionEnd < source.length && depth > 0) {
							if (source.charAt(expressionEnd) == '{') depth++;
							else if (source.charAt(expressionEnd) == '}') depth--;
							if (depth > 0) expressionEnd++;
						}
						if (hasIdentifierReference(source.substring(expressionStart, expressionEnd), name, -1, -1))
							return true;
						cursor = depth == 0 ? expressionEnd + 1 : expressionEnd;
						continue;
					}
					if (letter(source.charAt(expressionStart))) {
						var tokenEnd = expressionStart + 1;
						while (tokenEnd < source.length && isIdentifierChar(source.charAt(tokenEnd))) tokenEnd++;
						if (tokenEnd - expressionStart == name.length
							&& source.substr(expressionStart, name.length) == name) return true;
						cursor = tokenEnd;
						continue;
					}
				}
				cursor++;
			}
			cursor++;
		}
		return false;
	}

	/** True when diagnostics contain no fatal parse or binding error. */
	public static function hasFatalDiagnostics(result:CodenameScriptParseResult):Bool {
		if (result == null) return true;
		for (diagnostic in result.diagnostics)
			if (diagnostic.recoverable != true) return true;
		return false;
	}

	/** Log bounded transformations that left a recoverable source diagnostic. */
	public static function reportRecoverableDiagnostics(result:CodenameScriptParseResult,
		?origin:String = 'codename-script'):Void {
		if (result == null) return;
		if (result.sourceUseDiagnostics != null) for (diagnostic in result.sourceUseDiagnostics)
			trace(diagnostic);
		for (diagnostic in result.diagnostics) if (diagnostic.recoverable == true)
			trace('[codename-script-' + diagnostic.code + '] ' + origin + ':'
				+ diagnostic.line + ': ' + diagnostic.message);
	}

	/** ParserEx emits IntIterator for `0...count`, whose inline methods are
	 * invisible to hscript.Interp on native targets. Keep the Haxe range
	 * bounds and evaluate them once through a reflectable iterator. */
	static function normalizeRangeLoops(program:Expr):Expr {
		var mapped = Tools.map(program, normalizeRangeLoops);
		switch (Tools.expr(mapped)) {
			case EFor(name, iterable, body):
				switch (Tools.expr(iterable)) {
					case EBinop('...', first, last):
						var facade = Tools.mk(EIdent('CodenameKeyValueIterator'), iterable);
						var method = Tools.mk(EField(facade, 'range'), iterable);
						var replacement = Tools.mk(ECall(method, [first, last]), iterable);
						return Tools.mk(EFor(name, replacement, body), mapped);
					default:
				}
			default:
		}
		return mapped;
	}

	static function letter(char:String):Bool {
		return char != '' && ~/^[A-Za-z_]$/.match(char);
	}

	static function lineAt(source:String, index:Int):Int {
		var line = 1;
		for (i in 0...index) if (source.charAt(i) == '\n') line++;
		return line;
	}

	/** Hide comments and quoted text while retaining every newline and offset. */
	static function codeMask(source:String):String {
		var out = new StringBuf();
		var state = 0; // code, line comment, block comment, single quote, double quote
		var escaped = false;
		for (i in 0...source.length) {
			var ch = source.charAt(i);
			var next = i + 1 < source.length ? source.charAt(i + 1) : '';
			if (state == 0) {
				if (ch == '/' && next == '/') { state = 1; out.add(' '); continue; }
				if (ch == '/' && next == '*') { state = 2; out.add(' '); continue; }
				if (ch == "'") { state = 3; escaped = false; out.add(' '); continue; }
				if (ch == '"') { state = 4; escaped = false; out.add(' '); continue; }
				out.add(ch);
			} else if (state == 1) {
				if (ch == '\n') { state = 0; out.add('\n'); } else out.add(' ');
			} else if (state == 2) {
				if (ch == '/' && i > 0 && source.charAt(i - 1) == '*') state = 0;
				out.add(ch == '\n' ? '\n' : ' ');
			} else {
				if (!escaped && ((state == 3 && ch == "'") || (state == 4 && ch == '"'))) state = 0;
				if (ch == '\\' && !escaped) escaped = true; else escaped = false;
				out.add(ch == '\n' ? '\n' : ' ');
			}
		}
		return out.toString();
	}

	/** `@:privateAccess` is compile-time-only Haxe metadata. The script
	 * interpreter performs dynamic field access itself, so erase this one
	 * annotation while retaining its source location and record the adaptation. */
	static function removePrivateAccessMetadata(source:String):{source:String, count:Int} {
		if (source == null || source == '') return {source:source, count:0};
		var mask = codeMask(source);
		var chars = source.split('');
		var token = '@:privateAccess';
		var count = 0;
		var cursor = 0;
		while (cursor + token.length <= mask.length) {
			if (mask.substr(cursor, token.length) == token
				&& (cursor == 0 || !isIdentifierChar(mask.charAt(cursor - 1)))) {
				for (index in cursor...cursor + token.length)
					if (chars[index] != '\n' && chars[index] != '\r') chars[index] = ' ';
				count++;
				cursor += token.length;
			} else cursor++;
		}
		return {source:chars.join(''), count:count};
	}

	static function normalizeInterpolatedStrings(source:String):{source:String, error:String} {
		return HaxeStringInterpolation.normalize(source);
	}

	static function activeCoalescingAssignmentCount(source:String):Int {
		if (source == null) return 0;
		var mask = codeMask(source);
		var count = 0;
		var cursor = 0;
		while (cursor < mask.length) {
			var found = findCoalescingAssignment(mask, cursor);
			if (found < 0) break;
			count++;
			cursor = found + 3;
		}
		return count;
	}

	/** `??=` goes through a dedicated fixed-width scanner. In hxcpp, comparing
	 * the repeated-question token through the generic token argument failed even
	 * when the source slice and ASCII codes were correct. */
	static function findToken(source:String, token:String, start:Int):Int {
		if (source == null || token == null || token == '') return -1;
		var first = start < 0 ? 0 : start;
		var cursor = source.indexOf(token, first);
		var last = source.length - token.length;
		return cursor >= first && cursor <= last ? cursor : -1;
	}

	static function findCoalescingAssignment(source:String, start:Int):Int {
		if (source == null) return -1;
		var cursor = source.indexOf('?', start < 0 ? 0 : start);
		while (cursor >= 0 && cursor + 2 < source.length) {
			var first = source.charCodeAt(cursor);
			var second = source.charCodeAt(cursor + 1);
			var third = source.charCodeAt(cursor + 2);
			if (first == 63 && second == 63 && third == 61)
				return cursor;
			cursor = source.indexOf('?', cursor + 1);
		}
		return -1;
	}

	static function codeList(source:String, start:Int, count:Int):String {
		var values:Array<String> = [];
		for (offset in 0...count) {
			var at = start + offset;
			var code = at < 0 || at >= source.length ? null : source.charCodeAt(at);
			values.push(code == null ? 'null' : Std.string(code));
		}
		return values.join(',');
	}

	static function questionTokenProbe(source:String):String {
		var token = '??=';
		var rawAt = findCoalescingAssignment(source, 0);
		var masked = codeMask(source);
		var maskAt = findCoalescingAssignment(masked, 0);
		var tokenInfo = 'tokenLength=' + token.length + ',tokenCodes=' + codeList(token, 0, 3);
		var positions:Array<String> = [];
		var cursor = source.indexOf('?', 0);
		while (cursor >= 0 && positions.length < 8) {
			var start = Std.int(Math.max(0, cursor - 4));
			var candidate = source.substr(cursor, 3);
			positions.push(cursor + ':`' + candidate + '`:sliceEqual=' + (candidate == token)
				+ ':codes=' + codeList(source, start, 11) + ':mask=' + codeList(masked, start, 11));
			cursor = source.indexOf('?', cursor + 1);
		}
		if (rawAt < 0)
			return 'rawToken=absent,maskAt=' + maskAt + ',' + tokenInfo + ',questionCandidates='
				+ (positions.length == 0 ? '<none>' : positions.join('|'));
		var start = Std.int(Math.max(0, rawAt - 4));
		return 'rawAt=' + rawAt + ',maskAt=' + maskAt
			+ ',' + tokenInfo
			+ ',rawCodes=' + codeList(source, start, 11)
			+ ',maskCodes=' + codeList(masked, start, 11)
			+ ',questionCandidates=' + (positions.length == 0 ? '<none>' : positions.join('|'));
	}

	static function directMapArrow(mask:String, start:Int, end:Int):Int {
		var parens = 0;
		var brackets = 0;
		var braces = 0;
		var i = start;
		while (i + 1 < end) {
			var ch = mask.charAt(i);
			switch (ch) {
				case '(': parens++;
				case ')': parens--;
				case '[': brackets++;
				case ']': brackets--;
				case '{': braces++;
				case '}': braces--;
				default:
			}
			if (parens == 0 && brackets == 0 && braces == 0
				&& ch == '=' && mask.charAt(i + 1) == '>') return i;
			i++;
		}
		return -1;
	}

	static function nextMapLiteral(source:String):Null<{start:Int, end:Int, mask:String}> {
		var mask = codeMask(source);
		var i = 0;
		while (i < mask.length) {
			if (mask.charAt(i) != '[') { i++; continue; }
			var depth = 1;
			var end = i + 1;
			while (end < mask.length && depth > 0) {
				if (mask.charAt(end) == '[') depth++;
				else if (mask.charAt(end) == ']') depth--;
				end++;
			}
			if (depth != 0) return null;
			if (directMapArrow(mask, i + 1, end - 1) >= 0)
				return {start:i, end:end, mask:mask};
			i++;
		}
		return null;
	}

	static function mapPairs(source:String, mask:String, start:Int, end:Int):Array<String> {
		var pieces:Array<String> = [];
		var pieceStart = start;
		var parens = 0;
		var brackets = 0;
		var braces = 0;
		var i = start;
		while (i < end) {
			var ch = mask.charAt(i);
			if (parens == 0 && brackets == 0 && braces == 0 && ch == ',') {
				var piece = StringTools.trim(source.substring(pieceStart, i));
				if (piece != '') pieces.push(piece);
				pieceStart = i + 1;
			} else {
				switch (ch) {
					case '(': parens++;
					case ')': parens--;
					case '[': brackets++;
					case ']': brackets--;
					case '{': braces++;
					case '}': braces--;
					default:
				}
			}
			i++;
		}
		var last = StringTools.trim(source.substring(pieceStart, end));
		if (last != '') pieces.push(last);
		var result:Array<String> = [];
		for (piece in pieces) {
			var pieceMask = codeMask(piece);
			var arrow = directMapArrow(pieceMask, 0, pieceMask.length);
			if (arrow <= 0 || arrow + 2 >= piece.length)
				throw 'Map literal entries must use key => value pairs';
			var key = StringTools.trim(piece.substring(0, arrow));
			var value = StringTools.trim(piece.substring(arrow + 2));
			if (key == '' || value == '') throw 'Map literal entries must use key => value pairs';
			result.push('{key:' + key + ', value:' + value + '}');
		}
		return result;
	}

	static function normalizeIndexedLoops(source:String):{source:String, error:String} {
		var result = source;
		var passes = 0;
		while (passes++ < 32) {
			var mask = codeMask(result);
			var expression = new EReg('for[ \\t]*\\([ \\t]*([A-Za-z_][A-Za-z0-9_]*)[ \\t]*=>[ \\t]*([A-Za-z_][A-Za-z0-9_]*)[ \\t]+in[ \\t]+([^\\n)]+)\\)', '');
			if (!expression.match(mask)) return {source:result, error:''};
			var match = expression.matchedPos();
			var bodyStart = match.pos + match.len;
			while (bodyStart < mask.length && [' ', '\t', '\n', '\r'].indexOf(mask.charAt(bodyStart)) >= 0) bodyStart++;
			var bodyOpen = bodyStart;
			var nestedLoop = false;
			// Haxe permits `for (key => value in map) for (...) { ... }`.
			// Keep the complete inner loop as the outer body.
			if (bodyStart < mask.length && mask.charAt(bodyStart) != '{') {
				if (mask.substr(bodyStart, 3) != 'for'
					|| (bodyStart + 3 < mask.length && isIdentifierChar(mask.charAt(bodyStart + 3))))
					return {source:result, error:'Indexed for loops require a braced body'};
				var inner = bodyStart + 3;
				while (inner < mask.length && [' ', '\t', '\n', '\r'].indexOf(mask.charAt(inner)) >= 0) inner++;
				if (inner >= mask.length || mask.charAt(inner) != '(')
					return {source:result, error:'Indexed for loop has an invalid nested loop'};
				var parens = 1;
				inner++;
				while (inner < mask.length && parens > 0) {
					if (mask.charAt(inner) == '(') parens++;
					else if (mask.charAt(inner) == ')') parens--;
					inner++;
				}
				if (parens != 0) return {source:result, error:'Unclosed nested indexed for loop'};
				while (inner < mask.length && [' ', '\t', '\n', '\r'].indexOf(mask.charAt(inner)) >= 0) inner++;
				if (inner >= mask.length || mask.charAt(inner) != '{')
					return {source:result, error:'Nested indexed for loops require a braced inner body'};
				bodyOpen = inner;
				nestedLoop = true;
			}
			if (bodyOpen >= mask.length || mask.charAt(bodyOpen) != '{')
				return {source:result, error:'Indexed for loops require a braced body'};
			var depth = 1;
			var bodyEnd = bodyOpen + 1;
			while (bodyEnd < mask.length && depth > 0) {
				if (mask.charAt(bodyEnd) == '{') depth++;
				else if (mask.charAt(bodyEnd) == '}') depth--;
				bodyEnd++;
			}
			if (depth != 0) return {source:result, error:'Unclosed indexed for loop body'};
			var indexName = expression.matched(1);
			var valueName = expression.matched(2);
			var iterable = StringTools.trim(expression.matched(3));
			if (iterable == '') return {source:result, error:'Indexed for loop has no iterable'};
			var body = nestedLoop ? result.substring(bodyStart, bodyEnd)
				: result.substring(bodyStart + 1, bodyEnd - 1);
			var entryName = '__codenameIndexedEntry' + passes;
			var replacement = 'for (' + entryName + ' in CodenameKeyValueIterator.entries('
				+ iterable + ')) { var ' + indexName + ' = ' + entryName + '.key; var '
				+ valueName + ' = ' + entryName + '.value;' + body + '}';
			result = result.substring(0, match.pos) + replacement + result.substr(bodyEnd);
		}
		return {source:result, error:'Indexed for loop conversion limit reached'};
	}

	static function matchingOpen(mask:String, closeIndex:Int):Int {
		var expected:Array<String> = [];
		var index = closeIndex;
		while (index >= 0) {
			var ch = mask.charAt(index);
			switch (ch) {
				case ')': expected.push('(');
				case ']': expected.push('[');
				case '}': expected.push('{');
				case '(', '[', '{':
					if (expected.length == 0) return -1;
					if (expected.pop() != ch) return -1;
					if (expected.length == 0) return index;
				default:
			}
			index--;
		}
		return -1;
	}

	/** Find the start of the expression immediately before `end`. This accepts
	 * identifiers/member chains, calls, array/map access and parenthesized
	 * expressions; it deliberately stops at an operator or statement boundary. */
	static function previousExpressionStart(mask:String, end:Int):Int {
		var cursor = end;
		while (cursor > 0 && [' ', '\t', '\n', '\r'].indexOf(mask.charAt(cursor - 1)) >= 0) cursor--;
		if (cursor <= 0) return -1;
		var ch = mask.charAt(cursor - 1);
		if (ch == ')' || ch == ']' || ch == '}') {
			var open = matchingOpen(mask, cursor - 1);
			if (open < 0) return -1;
			cursor = open;
			// Calls and indexed expressions include the value before their opener.
			if (ch == ')' || ch == ']') {
				while (cursor > 0 && [' ', '\t', '\n', '\r'].indexOf(mask.charAt(cursor - 1)) >= 0) cursor--;
				if (cursor > 0 && (isIdentifierChar(mask.charAt(cursor - 1))
					|| mask.charAt(cursor - 1) == ')' || mask.charAt(cursor - 1) == ']')) {
					var before = previousExpressionStart(mask, cursor);
					if (before >= 0) cursor = before;
				}
			}
		} else if (isIdentifierChar(ch)) {
			while (cursor > 0 && isIdentifierChar(mask.charAt(cursor - 1))) cursor--;
		} else if (ch == '"' || ch == "'") {
			var quote = ch;
			cursor--;
			while (cursor > 0) {
				cursor--;
				if (mask.charAt(cursor) == quote && (cursor == 0 || mask.charAt(cursor - 1) != '\\')) break;
			}
		} else {
			return -1;
		}
		// Pull a dotted receiver chain into the expression as well.
		while (cursor > 0) {
			var beforeCursor = cursor;
			while (beforeCursor > 0 && [' ', '\t', '\n', '\r'].indexOf(mask.charAt(beforeCursor - 1)) >= 0)
				beforeCursor--;
			if (beforeCursor <= 0 || mask.charAt(beforeCursor - 1) != '.') break;
			var dot = beforeCursor - 1;
			var memberStart = previousExpressionStart(mask, dot);
			if (memberStart < 0) break;
			cursor = memberStart;
		}
		return cursor;
	}

	static function skipDelimited(mask:String, openIndex:Int):Int {
		var close = switch (mask.charAt(openIndex)) {
			case '(': ')';
			case '[': ']';
			case '{': '}';
			default: return -1;
		};
		var depth = 1;
		var index = openIndex + 1;
		while (index < mask.length) {
			var ch = mask.charAt(index);
			if (ch == mask.charAt(openIndex)) depth++;
			else if (ch == close) {
				depth--;
				if (depth == 0) return index + 1;
			}
			index++;
		}
		return -1;
	}

	static function skipSpaces(mask:String, index:Int):Int {
		while (index < mask.length && [' ', '\t', '\n', '\r'].indexOf(mask.charAt(index)) >= 0) index++;
		return index;
	}

	/** Lower Haxe null-safe access (`value?.field`) to an HScript-compatible
	 * closure. The receiver is evaluated once, and an optional assignment is
	 * skipped when its receiver is null. */
	static function normalizeNullSafeAccess(source:String):{source:String, error:String} {
		var result = source;
		var temporaryIndex = 0;
		var passes = 0;
		while (passes++ < 256) {
			var mask = codeMask(result);
			var safeOperator = mask.indexOf('?.');
			if (safeOperator < 0) return {source:result, error:''};
			var expressionStart = previousExpressionStart(mask, safeOperator);
			if (expressionStart < 0)
				return {source:result, error:'Could not locate a null-safe receiver'};
			var current = StringTools.trim(result.substring(expressionStart, safeOperator));
			if (current == '') return {source:result, error:'Null-safe access has an empty receiver'};
			var cursor = safeOperator;
			var lastSegment = '';
			var nextOptional = -1;
			while (true) {
				if (mask.charAt(cursor + 1) != '.')
					return {source:result, error:'Malformed null-safe access'};
				var memberStart = cursor + 2;
				var memberEnd = memberStart;
				while (memberEnd < mask.length && isIdentifierChar(mask.charAt(memberEnd))) memberEnd++;
				if (memberEnd == memberStart || !letter(mask.charAt(memberStart)))
					return {source:result, error:'Null-safe access requires a field or method name'};
				var segmentEnd = memberEnd;
				while (segmentEnd < mask.length) {
					var postfix = skipSpaces(mask, segmentEnd);
					if (postfix + 1 < mask.length && mask.substr(postfix, 2) == '?.') {
						nextOptional = postfix;
						break;
					}
					var next = mask.charAt(postfix);
					if (next == '.') {
						var afterDot = postfix + 1;
						while (afterDot < mask.length && isIdentifierChar(mask.charAt(afterDot))) afterDot++;
						if (afterDot == postfix + 1 || !letter(mask.charAt(postfix + 1))) break;
						segmentEnd = afterDot;
					} else if (next == '[' || next == '(') {
						var afterDelimited = skipDelimited(mask, postfix);
						if (afterDelimited < 0) return {source:result, error:'Unclosed null-safe index or call'};
						segmentEnd = afterDelimited;
					} else break;
				}
				lastSegment = result.substring(cursor + 1, segmentEnd);
				cursor = segmentEnd;
				if (nextOptional >= 0) {
					var temp = '__codenameNullSafe' + temporaryIndex++;
					current = '(function(' + temp + ') return (' + temp + ' == null ? null : '
						+ temp + lastSegment + '))(' + current + ')';
					cursor = nextOptional;
					nextOptional = -1;
					continue;
				}
				break;
			}
			var accessEnd = cursor;
			var suffixEnd = accessEnd;
			var afterSuffix = skipSpaces(mask, accessEnd);
			var assignment = '';
			for (candidate in ['??=', '+=', '-=', '*=', '/=', '%=', '='])
				if (mask.substr(afterSuffix, candidate.length) == candidate
					&& (candidate != '=' || (mask.charAt(afterSuffix + 1) != '=' && mask.charAt(afterSuffix + 1) != '>'))
					&& (candidate != '=' || afterSuffix == 0 || ['=', '!', '<', '>'].indexOf(mask.charAt(afterSuffix - 1)) < 0)) {
					assignment = candidate;
					break;
				}
			var rhs = '';
			if (assignment != '') {
				var rhsStart = afterSuffix + assignment.length;
				var depthParen = 0;
				var depthBracket = 0;
				var depthBrace = 0;
				var rhsEnd = rhsStart;
				while (rhsEnd < mask.length) {
					var ch = mask.charAt(rhsEnd);
					if (depthParen == 0 && depthBracket == 0 && depthBrace == 0
						&& (ch == ';' || ch == ',' || ch == '\n' || ch == ')' || ch == ']' || ch == '}')) break;
					switch (ch) {
						case '(': depthParen++;
						case ')': depthParen--;
						case '[': depthBracket++;
						case ']': depthBracket--;
						case '{': depthBrace++;
						case '}': depthBrace--;
						default:
					}
					rhsEnd++;
				}
				rhs = StringTools.trim(result.substring(rhsStart, rhsEnd));
				if (rhs == '') return {source:result, error:'Null-safe assignment has no right-hand value'};
				suffixEnd = rhsEnd;
			}
			var expression = current;
			var temp = '__codenameNullSafe' + temporaryIndex++;
			var finalAccess = temp + lastSegment;
			var branch = assignment == '' ? finalAccess : '(' + finalAccess + ' ' + assignment + ' (' + rhs + '))';
			expression = '(function(' + temp + ') return (' + temp + ' == null ? null : ' + branch + '))(' + expression + ')';
			var replacement = result.substring(0, expressionStart) + expression + result.substr(suffixEnd);
			result = replacement;
		}
		return {source:result, error:'Null-safe access conversion limit reached'};
	}

	/** Haxe's null-coalescing assignment is statement-safe in Codename scripts.
	 * Capture the receiver once so a field/index base with side effects is not
	 * evaluated twice. */
	static function normalizeNullCoalescingAssignment(source:String):{source:String, error:String} {
		var result = source;
		var passes = 0;
		while (passes++ < 128) {
			var mask = codeMask(result);
			var coalesceOperator = findCoalescingAssignment(mask, 0);
			if (coalesceOperator < 0) return {source:result, error:''};
			var leftStart = previousExpressionStart(mask, coalesceOperator);
			if (leftStart < 0) return {source:result, error:'Could not locate the ??= target'};
			var lhs = StringTools.trim(result.substring(leftStart, coalesceOperator));
			var pathPattern = ~/^(.*)\.([A-Za-z_][A-Za-z0-9_]*)$/;
			var indexPattern = ~/^(.*)\[([\s\S]*)\]$/;
			var hasPath = pathPattern.match(lhs);
			var hasIndex = indexPattern.match(lhs);
			var at = skipSpaces(mask, coalesceOperator + 3);
			var depthParen = 0;
			var depthBracket = 0;
			var depthBrace = 0;
			var end = at;
			while (end < mask.length) {
				var ch = mask.charAt(end);
				if (depthParen == 0 && depthBracket == 0 && depthBrace == 0
					&& (ch == ';' || ch == ',' || ch == '\n' || ch == ')' || ch == ']' || ch == '}')) break;
				switch (ch) {
					case '(': depthParen++;
					case ')': depthParen--;
					case '[': depthBracket++;
					case ']': depthBracket--;
					case '{': depthBrace++;
					case '}': depthBrace--;
					default:
				}
				end++;
			}
			var rhs = StringTools.trim(result.substring(at, end));
			if (rhs == '') return {source:result, error:'??= has no right-hand value'};
			var replacement:String;
			if (~/^[A-Za-z_][A-Za-z0-9_]*$/.match(lhs)) {
				// A closure would capture HScript's local table by value, so an
				// optional argument such as `offset ??= fallback` would update only
				// the temporary closure scope. A plain identifier has no evaluation
				// side effects and can use the direct lazy assignment form.
				replacement = '(' + lhs + ' == null ? (' + lhs + ' = (' + rhs + ')) : ' + lhs + ')';
			} else if (hasPath) {
				var target = '__codenameCoalesceTarget';
				var field = pathPattern.matched(2);
				var base = StringTools.trim(pathPattern.matched(1));
				if (base == '') return {source:result, error:'??= field target has no receiver'};
				replacement = '(function(' + target + ') return (' + target + '.' + field + ' == null ? ('
					+ target + '.' + field + ' = (' + rhs + ')) : ' + target + '.' + field + '))(' + base + ')';
			} else if (hasIndex) {
				var target = '__codenameCoalesceTarget';
				var key = '__codenameCoalesceKey';
				var base = StringTools.trim(indexPattern.matched(1));
				var keyExpression = StringTools.trim(indexPattern.matched(2));
				if (base == '' || keyExpression == '') return {source:result, error:'??= indexed target is invalid'};
				replacement = '(function(' + target + ', ' + key + ') return (' + target + '[' + key + '] == null ? ('
					+ target + '[' + key + '] = (' + rhs + ')) : ' + target + '[' + key + ']))(' + base + ', ('
					+ keyExpression + '))';
			} else return {source:result, error:'Unsupported ??= target: ' + lhs};
			result = result.substring(0, leftStart) + replacement + result.substr(end);
		}
		return {source:result, error:'??= conversion limit reached'};
	}

	/** Lower Haxe's lazy null-coalescing read to a single-evaluation closure. */
	static function normalizeNullCoalescing(source:String):{source:String, error:String} {
		var result = source;
		var passes = 0;
		while (passes++ < 128) {
			var mask = codeMask(result);
			var coalesceOperator = -1;
			var searchFrom = 0;
			while (searchFrom < mask.length) {
				var found = findToken(mask, '??', searchFrom);
				if (found < 0) break;
				if (mask.charAt(found + 2) != '=') coalesceOperator = found;
				searchFrom = found + 2;
			}
			if (coalesceOperator < 0) return {source:result, error:''};
			var leftStart = previousExpressionStart(mask, coalesceOperator);
			if (leftStart < 0) return {source:result, error:'Could not locate the ?? value'};
			var lhs = StringTools.trim(result.substring(leftStart, coalesceOperator));
			var rhsStart = skipSpaces(mask, coalesceOperator + 2);
			var depthParen = 0;
			var depthBracket = 0;
			var depthBrace = 0;
			var rhsEnd = rhsStart;
			while (rhsEnd < mask.length) {
				var ch = mask.charAt(rhsEnd);
				if (depthParen == 0 && depthBracket == 0 && depthBrace == 0
					&& (ch == ';' || ch == ',' || ch == '\n' || ch == ')' || ch == ']' || ch == '}')) break;
				switch (ch) {
					case '(': depthParen++;
					case ')': depthParen--;
					case '[': depthBracket++;
					case ']': depthBracket--;
					case '{': depthBrace++;
					case '}': depthBrace--;
					default:
				}
				rhsEnd++;
			}
			var rhs = StringTools.trim(result.substring(rhsStart, rhsEnd));
			if (lhs == '' || rhs == '') return {source:result, error:'?? needs a value on both sides'};
			var temp = '__codenameCoalesceValue';
			var replacement = '(function(' + temp + ') return (' + temp + ' == null ? (' + rhs
				+ ') : ' + temp + '))(' + lhs + ')';
			result = result.substring(0, leftStart) + replacement + result.substr(rhsEnd);
		}
		return {source:result, error:'?? conversion limit reached'};
	}

	/** Haxe module fields are visible to every class method regardless of their
	 * textual order. Hscript closures instead capture the current local table
	 * when the function is declared, so a later top-level `var` is invisible to
	 * an earlier function. Predeclare top-level fields before all functions and
	 * leave their initializers at the authored position as assignments. This
	 * keeps initialization order while giving Codename classless scripts the
	 * field scope their source format promises. */
	static function hoistTopLevelVariables(source:String):String {
		if (source == null || source == '') return source == null ? '' : source;
		var mask = codeMask(source);
		var replacements:Array<{start:Int, end:Int, text:String}> = [];
		var declarations:Array<String> = [];
		var declared:Map<String, Bool> = new Map();
		var depth = 0;
		var cursor = 0;
		while (cursor < mask.length) {
			if (depth == 0 && cursor + 3 <= mask.length && mask.substr(cursor, 3) == 'var'
				&& (cursor == 0 || !isIdentifierChar(mask.charAt(cursor - 1)))
				&& (cursor + 3 == mask.length || !isIdentifierChar(mask.charAt(cursor + 3)))) {
				var statementEnd = findVariableStatementEnd(mask, cursor + 3);
				if (statementEnd >= 0) {
					var segments = splitVariableDeclaration(source, mask, cursor + 3, statementEnd);
					var predeclared:Array<String> = [];
					var assignments:Array<String> = [];
					var valid = segments.length > 0;
					for (segment in segments) {
						var text = StringTools.trim(source.substring(segment.start, segment.end));
						var masked = StringTools.trim(mask.substring(segment.start, segment.end));
						var assignment = topLevelAssignment(mask, segment.start, segment.end);
						var prefixEnd = assignment < 0 ? segment.end : assignment;
						var prefix = StringTools.trim(source.substring(segment.start, prefixEnd));
						var nameMatch = ~/^([A-Za-z_][A-Za-z0-9_]*)(\s*:\s*[\s\S]+)?$/;
						if (!nameMatch.match(prefix)) {
						valid = false;
						break;
					}
						var name = nameMatch.matched(1);
						if (!declared.exists(name)) {
							declared.set(name, true);
							var defaultValue = '';
							var typeOffset = prefix.indexOf(':');
							if (typeOffset >= 0) {
								switch (StringTools.trim(prefix.substr(typeOffset + 1))) {
									case 'Int', 'Float': defaultValue = ' = 0';
									case 'Bool': defaultValue = ' = false';
									default:
								}
							}
							predeclared.push('var ' + prefix + defaultValue + ';');
						}
						if (assignment >= 0) {
							var initializer = StringTools.trim(source.substring(assignment + 1, segment.end));
						if (initializer == '') {
							valid = false;
							break;
						}
						assignments.push(name + ' = ' + initializer);
						}
					}
					if (valid) {
						for (entry in predeclared) declarations.push(entry);
						var replacement = assignments.length == 0 ? '' : assignments.join('; ') + ';';
						replacements.push({start:cursor, end:statementEnd + 1, text:replacement});
						cursor = statementEnd + 1;
						continue;
					}
				}
			}
			var ch = mask.charAt(cursor);
			if (ch == '{') depth++;
			else if (ch == '}') depth--;
			cursor++;
		}
		if (replacements.length == 0) return source;
		var result = source;
		for (index in 0...replacements.length) {
			var item = replacements[replacements.length - 1 - index];
			result = result.substring(0, item.start) + item.text + result.substr(item.end);
		}
		return declarations.join('\n') + '\n' + result;
	}

	static function isIdentifierChar(char:String):Bool {
		return letter(char) || (char >= '0' && char <= '9');
	}

	static function findVariableStatementEnd(mask:String, start:Int):Int {
		var parens = 0;
		var brackets = 0;
		var braces = 0;
		for (index in start...mask.length) {
			var ch = mask.charAt(index);
			if (ch == ';' && parens == 0 && brackets == 0 && braces == 0) return index;
			switch (ch) {
				case '(': parens++;
				case ')': parens--;
				case '[': brackets++;
				case ']': brackets--;
				case '{': braces++;
				case '}': braces--;
				default:
			}
		}
		return -1;
	}

	static function splitVariableDeclaration(source:String, mask:String, start:Int,
		end:Int):Array<{start:Int, end:Int}> {
		var result:Array<{start:Int, end:Int}> = [];
		var segmentStart = start;
		var parens = 0;
		var brackets = 0;
		var braces = 0;
		var typeDepth = 0;
		var inInitializer = false;
		for (index in start...end) {
			var ch = mask.charAt(index);
			if (ch == '=' && parens == 0 && brackets == 0 && braces == 0
				&& (index + 1 >= end || (mask.charAt(index + 1) != '=' && mask.charAt(index + 1) != '>'))
				&& (index == start || ['=', '!', '<', '>'].indexOf(mask.charAt(index - 1)) < 0))
				inInitializer = true;
			if (!inInitializer) {
				if (ch == '<') typeDepth++;
				else if (ch == '>' && typeDepth > 0) typeDepth--;
			}
			if (ch == ',' && parens == 0 && brackets == 0 && braces == 0 && typeDepth == 0) {
				result.push({start:segmentStart, end:index});
				segmentStart = index + 1;
				inInitializer = false;
			}
			switch (ch) {
				case '(': parens++;
				case ')': parens--;
				case '[': brackets++;
				case ']': brackets--;
				case '{': braces++;
				case '}': braces--;
				default:
			}
		}
		result.push({start:segmentStart, end:end});
		return result;
	}

	static function topLevelAssignment(mask:String, start:Int, end:Int):Int {
		var parens = 0;
		var brackets = 0;
		var braces = 0;
		var typeDepth = 0;
		for (index in start...end) {
			var ch = mask.charAt(index);
			if (ch == '=' && parens == 0 && brackets == 0 && braces == 0 && typeDepth == 0
				&& (index + 1 >= end || (mask.charAt(index + 1) != '=' && mask.charAt(index + 1) != '>'))
				&& (index == start || ['=', '!', '<', '>'].indexOf(mask.charAt(index - 1)) < 0))
				return index;
			switch (ch) {
				case '(': parens++;
				case ')': parens--;
				case '[': brackets++;
				case ']': brackets--;
				case '{': braces++;
				case '}': braces--;
				case '<': if (braces == 0 && parens == 0 && brackets == 0) typeDepth++;
				case '>': if (typeDepth > 0) typeDepth--;
				default:
			}
		}
		return -1;
	}

	/** Haxe permits default expressions on typed arguments, but the bundled
	 * hscript parser only records `?arg` as optional and its interpreter ignores
	 * `Argument.value`. Lower defaults to optional arguments plus a function
	 * entry check so omitted arguments receive their authored expression. */
	static function normalizeDefaultArguments(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var edits:Array<{start:Int, end:Int, text:String}> = [];
		var searchFrom = 0;
		while (searchFrom < mask.length) {
			var found = mask.indexOf('function', searchFrom);
			if (found < 0) break;
			searchFrom = found + 'function'.length;
			if ((found > 0 && isIdentifierChar(mask.charAt(found - 1)))
				|| (searchFrom < mask.length && isIdentifierChar(mask.charAt(searchFrom)))) continue;
			var open = skipSpaces(mask, searchFrom);
			if (open < mask.length && letter(mask.charAt(open))) {
				while (open < mask.length && isIdentifierChar(mask.charAt(open))) open++;
				open = skipSpaces(mask, open);
			}
			if (open >= mask.length || mask.charAt(open) != '(') continue;
			var afterArgs = skipDelimited(mask, open);
			if (afterArgs < 0) return {source:source, error:'Unclosed function argument list while normalizing default arguments'};
			var close = afterArgs - 1;
			var args = splitVariableDeclaration(source, mask, open + 1, close);
			var rewritten:Array<String> = [];
			var defaults:Array<String> = [];
			for (arg in args) {
				var raw = source.substring(arg.start, arg.end);
				var assignment = topLevelAssignment(mask, arg.start, arg.end);
				if (assignment < 0) {
					rewritten.push(raw);
					continue;
				}
				var prefix = StringTools.trim(source.substring(arg.start, assignment));
				var value = StringTools.trim(source.substring(assignment + 1, arg.end));
				var nameStart = prefix.charAt(0) == '?' ? 1 : 0;
				var nameEnd = nameStart;
				if (nameStart >= prefix.length || !letter(prefix.charAt(nameStart)) || value == '')
					return {source:source, error:'Unsupported default function argument: ' + StringTools.trim(raw)};
				while (nameEnd < prefix.length && isIdentifierChar(prefix.charAt(nameEnd))) nameEnd++;
				var name = prefix.substring(nameStart, nameEnd);
				var typeTail = prefix.substr(nameEnd);
				if (StringTools.trim(typeTail) != '' && !StringTools.trim(typeTail).startsWith(':'))
					return {source:source, error:'Unsupported default function argument type: ' + StringTools.trim(raw)};
				var parameter = '?' + name + typeTail;
				rewritten.push(parameter);
				defaults.push('if (' + name + ' == null) ' + name + ' = (' + value + ');');
			}
			if (defaults.length == 0) continue;
			edits.push({start:open + 1, end:close, text:rewritten.join(',')});
			var bodyStart = skipSpaces(mask, afterArgs);
			// Skip a conventional return annotation (for example `:Void`) before
			// selecting the body. The Codename scripts use simple return types.
			if (bodyStart < mask.length && mask.charAt(bodyStart) == ':') {
				bodyStart++;
				while (bodyStart < mask.length && mask.charAt(bodyStart) != '{'
					&& mask.charAt(bodyStart) != ';' && mask.charAt(bodyStart) != '\n') bodyStart++;
				bodyStart = skipSpaces(mask, bodyStart);
			}
			if (bodyStart < mask.length && mask.charAt(bodyStart) == '{') {
				edits.push({start:bodyStart + 1, end:bodyStart + 1,
					text:'\n' + defaults.join('\n') + '\n'});
			} else {
				// Expression-bodied functions are valid in Codename Haxe modules.
				// Wrap the expression in a block so the defaults execute first.
				var exprStart = bodyStart;
				var parens = 0;
				var brackets = 0;
				var braces = 0;
				var exprEnd = exprStart;
				while (exprEnd < mask.length) {
					var ch = mask.charAt(exprEnd);
					if (parens == 0 && brackets == 0 && braces == 0 && ch == ';') break;
					switch (ch) {
						case '(': parens++;
						case ')': parens--;
						case '[': brackets++;
						case ']': brackets--;
						case '{': braces++;
						case '}': braces--;
						default:
					}
					exprEnd++;
				}
				if (exprStart >= exprEnd || exprEnd >= mask.length)
					return {source:source, error:'Could not find expression body for default-argument function'};
				var body = source.substring(exprStart, exprEnd);
				edits.push({start:exprStart, end:exprEnd,
					text:'{\n' + defaults.join('\n') + '\n' + body + '\n}'});
			}
		}
		if (edits.length == 0) return {source:source, error:''};
		edits.sort(function(a, b) return b.start - a.start);
		var result = source;
		for (edit in edits)
			result = result.substring(0, edit.start) + edit.text + result.substr(edit.end);
		return {source:result, error:''};
	}

	/** Haxe top-level maps use `[key => value]`, outside HScript's grammar.
	 * Translate those bounded literals into an explicit facade constructor.
	 * Static top-level declarations are instance-scoped in this interpreter;
	 * callers which need persistence must own that scope explicitly. */
	static function normalizeHaxeSurface(source:String, traceStages:Bool = false):{source:String, error:String, trace:Array<String>} {
		var result = source == null ? '' : source;
		var trace:Array<String> = [];
		var noteStage = function(name:String):Void {
			if (traceStages) {
				var entry = name + ':bytes=' + haxe.io.Bytes.ofString(result).length
					+ ',activeCoalesceAssign=' + activeCoalescingAssignmentCount(result);
				if (name == 'input') entry += ',' + questionTokenProbe(result);
				trace.push(entry);
			}
		};
		noteStage('input');
		var interpolation = normalizeInterpolatedStrings(result);
		result = interpolation.source;
		if (interpolation.error != '') return {source:result, error:interpolation.error, trace:trace};
		var mask = codeMask(result);
		var chars = result.split('');
		var depth = 0;
		var cursor = 0;
		while (cursor < mask.length) {
			var lineStart = cursor;
			while (cursor < mask.length && (mask.charAt(cursor) == ' ' || mask.charAt(cursor) == '\t')) cursor++;
			var wordStart = cursor;
			while (cursor < mask.length && letter(mask.charAt(cursor))) cursor++;
			var word = mask.substring(wordStart, cursor);
			if (depth == 0 && (word == 'static' || word == 'public' || word == 'private')) {
				var following = cursor;
				var declarationStart = following;
				var declaration = '';
				while (following < mask.length) {
					while (following < mask.length && (mask.charAt(following) == ' ' || mask.charAt(following) == '\t')) following++;
					declarationStart = following;
					while (following < mask.length && letter(mask.charAt(following))) following++;
					declaration = mask.substring(declarationStart, following);
					if (declaration != 'static' && declaration != 'public' && declaration != 'private') break;
				}
				if (declaration == 'var' || declaration == 'function')
					for (index in wordStart...declarationStart) if (chars[index] != '\n') chars[index] = ' ';
			}
			cursor = lineStart;
			while (cursor < mask.length && mask.charAt(cursor) != '\n') {
				if (mask.charAt(cursor) == '{') depth++;
				else if (mask.charAt(cursor) == '}') depth--;
				cursor++;
			}
			if (cursor < mask.length) cursor++;
		}
		result = chars.join('');
		result = hoistTopLevelVariables(result);
		noteStage('static-and-hoist');
		// HScript's parser accepts mutable local declarations but does not
		// recognize Haxe's `final` declaration keyword. Preserve the binding
		// and its initializer; only the compile-time reassignment rule is lost.
		var finalMask = codeMask(result);
		var finalChars = result.split('');
		var finalDeclaration = ~/\bfinal(?=\s+[A-Za-z_][A-Za-z0-9_]*\s*(?::|=|;))/g;
		var finalCursor = 0;
		while (finalDeclaration.matchSub(finalMask, finalCursor)) {
			var at = finalDeclaration.matchedPos().pos;
			finalChars[at] = 'v';
			finalChars[at + 1] = 'a';
			finalChars[at + 2] = 'r';
			finalChars[at + 3] = ' ';
			finalChars[at + 4] = ' ';
			finalCursor = at + 5;
		}
		result = finalChars.join('');
		var defaults = normalizeDefaultArguments(result);
		result = defaults.source;
		noteStage('defaults');
		if (defaults.error != '') return {source:result, error:defaults.error, trace:trace};
		var coalescing = normalizeNullCoalescingAssignment(result);
		result = coalescing.source;
		noteStage('coalescing-assignment');
		if (coalescing.error != '') return {source:result, error:coalescing.error, trace:trace};
		if (activeCoalescingAssignmentCount(result) > 0)
			return {source:result, error:'Null-coalescing assignment conversion left an active ??= operator', trace:trace};
		var nullSafe = normalizeNullSafeAccess(result);
		result = nullSafe.source;
		noteStage('null-safe');
		if (nullSafe.error != '') return {source:result, error:nullSafe.error, trace:trace};
		var coalescingRead = normalizeNullCoalescing(result);
		result = coalescingRead.source;
		noteStage('coalescing-read');
		if (coalescingRead.error != '') return {source:result, error:coalescingRead.error, trace:trace};
		var indexed = normalizeIndexedLoops(result);
		result = indexed.source;
		noteStage('indexed-loops');
		if (indexed.error != '') return {source:result, error:indexed.error, trace:trace};
		var passes = 0;
		while (passes++ < 64) {
			var found = nextMapLiteral(result);
			if (found == null) {
				noteStage('complete');
				return {source:result, error:'', trace:trace};
			}
			try {
				var pairs = mapPairs(result, found.mask, found.start + 1, found.end - 1);
				var replacement = 'CodenameMapCompat.fromPairs([' + pairs.join(',') + '])';
				result = result.substring(0, found.start) + replacement + result.substr(found.end);
			} catch (error:Dynamic) {
				return {source:result, error:Std.string(error), trace:trace};
			}
		}
		return {source:result, error:'Haxe map literal conversion limit reached', trace:trace};
	}

	public static function prepare(source:String, allowedImports:Map<String, Dynamic>,
		?origin:String = 'codename-script', ?traceStages:Bool = false):CodenameScriptParseResult {
		var result:CodenameScriptParseResult = {source:source == null ? '' : source,
			program:null, imports:[], publicVariables:[], diagnostics:[], sourceUseDiagnostics:[], normalizationTrace:[]};
		if (source == null) {
			result.diagnostics.push({code:'missing-source', message:'Script source is missing.', line:1});
			return result;
		}
		result.sourceUseDiagnostics = CodenameScriptClassLoader.unsupportedOptionSourceUses(source, origin);
		var mask = codeMask(source);
		var masked = mask.split('');
		var prepared = source.split('');
		var importAliases:Map<String, String> = new Map();
		var importAliasEdits:Array<{start:Int, end:Int, value:String}> = [];
		var depth = 0;
		var cursor = 0;
		while (cursor < mask.length) {
			var lineStart = cursor;
			while (cursor < mask.length && (mask.charAt(cursor) == ' ' || mask.charAt(cursor) == '\t')) cursor++;
			var wordStart = cursor;
			while (cursor < mask.length && letter(mask.charAt(cursor))) cursor++;
			var word = mask.substring(wordStart, cursor);
			if ((word == 'import' || word == 'package' || word == 'using')
				&& (cursor >= mask.length || !~/^[A-Za-z0-9_]$/.match(mask.charAt(cursor)))) {
				var end = mask.indexOf(';', cursor);
				var line = lineAt(source, wordStart);
				if (depth != 0 || end < 0) {
					result.diagnostics.push({code:'invalid-declaration',
						message:'Unsupported ' + word + ' declaration.', line:line});
					break;
				}
				var rawArgument = StringTools.trim(mask.substring(cursor, end));
				var declarationArgument = word == 'import'
					? parseImportArgument(rawArgument)
					: {path:~/\s+/g.replace(rawArgument, ''), alias:''};
				var argument = declarationArgument.path;
				if (word == 'using') {
					argument = ~/\s+/g.replace(rawArgument, '');
					result.diagnostics.push({code:'unsupported-using',
						message:'Using extensions need runtime method binding: ' + argument + '.', line:line});
				} else if (word != 'package' && (!~/^[A-Za-z_][A-Za-z0-9_.]*$/.match(argument)
					|| allowedImports == null || !allowedImports.exists(argument)
					|| allowedImports.get(argument) == null)) {
					result.diagnostics.push({code:'unsupported-import',
						message:'No explicit binding for ' + word + ' ' + argument + '.', line:line});
				} else if (word == 'package' && argument != ''
					&& !~/^[A-Za-z_][A-Za-z0-9_.]*$/.match(argument)) {
					result.diagnostics.push({code:'invalid-package', message:'Invalid package declaration.', line:line});
				} else if (word == 'import' && result.imports.indexOf(argument) < 0) {
					result.imports.push(argument);
				}
				var replacement = '';
				if (word == 'import' && declarationArgument.alias != ''
					&& allowedImports != null && allowedImports.exists(argument)
					&& allowedImports.get(argument) != null) {
					var alias = declarationArgument.alias;
					if (importAliases.exists(alias)) {
						result.diagnostics.push({code:'duplicate-import-alias',
							message:'Import alias is declared more than once: ' + alias + '.', line:line});
					} else {
						importAliases.set(alias, argument);
						replacement = 'var ' + alias + ' = ' + argument.split('.').pop() + ';';
					}
				}
				var replacementStart = wordStart;
				if (replacement != '') {
					// Apply after scanning the original source so arbitrarily long valid
					// aliases do not depend on the authored import line's width. The
					// replacement has no newline, so later source line numbers stay stable.
					importAliasEdits.push({start:replacementStart, end:end + 1, value:replacement});
				} else {
					for (i in replacementStart...end + 1)
						if (prepared[i] != '\n') prepared[i] = ' ';
				}
				for (i in lineStart...end + 1)
					if (masked[i] != '\n') masked[i] = ' ';
				cursor = end + 1;
				continue;
			}
			// Keep the nesting level only for declaration placement; ordinary
			// expressions are validated by ParserEx below.
			cursor = lineStart;
			while (cursor < mask.length && mask.charAt(cursor) != '\n') {
				if (mask.charAt(cursor) == '{') depth++;
				else if (mask.charAt(cursor) == '}') depth--;
				cursor++;
			}
			if (cursor < mask.length) cursor++;
		}
		result.source = prepared.join('');
		if (importAliasEdits.length > 0) {
			importAliasEdits.sort(function(a, b):Int return b.start - a.start);
			for (edit in importAliasEdits)
				result.source = result.source.substring(0, edit.start) + edit.value
					+ result.source.substring(edit.end);
		}
		result.publicVariables = publicTopLevelVariables(result.source);
		var privateAccess = removePrivateAccessMetadata(result.source);
		result.source = privateAccess.source;
		if (privateAccess.count > 0)
			result.diagnostics.push({code:'compile-metadata-elided', recoverable:true,
				message:'Removed ' + privateAccess.count
					+ ' compile-time @:privateAccess annotation(s); dynamic script field access is handled by the runtime.', line:1});
		var enumPass = removeUnusedTopLevelEnums(result.source);
		result.source = enumPass.source;
		for (entry in enumPass.removed)
			result.diagnostics.push({code:'unused-enum-elided', recoverable:true,
				message:'Top-level enum ' + entry.name
					+ ' has no identifier references outside its declaration; the declaration was removed so the surrounding classless script can run.',
				line:entry.line});
		// Preserve source offsets for declaration diagnostics before later
		// normalizers insert hoisted locals or rewrite expressions.
		var declarationSource = result.source;
		var normalized = normalizeHaxeSurface(result.source, traceStages);
		result.source = normalized.source;
		result.normalizationTrace = normalized.trace;
		if (normalized.error != '')
			result.diagnostics.push({code:'unsupported-haxe-surface', message:normalized.error, line:1});
		var declaration = ~/\b(class|interface|enum|typedef|abstract)\s+([A-Za-z_][A-Za-z0-9_]*)/;
		var remaining = codeMask(declarationSource);
		if (declaration.match(remaining)) {
			var kind = declaration.matched(1);
			var name = declaration.matched(2);
			result.diagnostics.push({code:'class-declaration',
				message:'Owner module declaration ' + kind + ' ' + name
					+ ' cannot execute in the classless script runtime; it requires an owner-scoped module loader.',
				line:lineAt(source, declaration.matchedPos().pos)});
		}
		if (hasFatalDiagnostics(result)) return result;
		try {
			var parser = new ParserEx();
			parser.allowTypes = true;
			parser.allowJSON = true;
			result.program = normalizeRangeLoops(parser.parseString(result.source, origin));
		} catch (error:Dynamic) {
			result.diagnostics.push({code:'parse-error', message:Std.string(error), line:1});
		}
		return result;
	}
}
