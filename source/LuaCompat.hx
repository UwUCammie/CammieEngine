package;

using StringTools;

/**
	Result of the deliberately small Lua-to-HScript compatibility bridge.

	This is a source adapter, not a Lua interpreter.  It only rewrites the
	structured subset which is shared by the Psych/Kade script APIs and the
	HScript runtime.  Unsupported constructs are returned as diagnostics and
	are commented out in the generated source so a donor script cannot execute
	arbitrary Lua/Haxe through the bridge.
*/
typedef LuaCompatResult = {
	var hscript:String;
	var supported:Bool;
	var diagnostics:Array<String>;
}

/** A parsed, whitelisted `_G` reference from the mounted donor corpus. */
typedef LuaDynamicGlobalRef = {
	var startIndex:Int;
	var endIndex:Int;
	var mode:String;
	var key:String;
	var keyExpression:String;
	var indexExpression:String;
	var axis:String;
}

class LuaCompat {
	public static inline var TRANSLATED_MARKER:String = '// lua-compat-translated:v1';
	static inline var MAX_SOURCE_LENGTH:Int = 4 * 1024 * 1024;
	static var collectionCounter:Int = 0;

	/**
		Every emitted donor loop carries an iteration guard. A translated donor
		condition can stay true forever (length helpers that cannot observe a
		nulling write, step math that never lands on the bound), and hscript
		would spin the whole engine inside one callback with no diagnostic and
		no escape. A generous bound turns that hang into a normal catchable
		callback failure; legitimate modchart loops stay orders of magnitude
		under it.
	*/
	static inline var LOOP_GUARD_ITERATIONS:Int = 1000000;
	static var closureCounter:Int = 0;

	static function loopGuardName(?id:Int):String {
		if (id == null)
			id = collectionCounter++;
		return '__luaLoopGuard' + id;
	}

	static function guardIncrement(guardName:String):String {
		return guardName + ' += 1; if (' + guardName + ' > ' + LOOP_GUARD_ITERATIONS
			+ ') throw "lua loop watchdog: donor loop exceeded ' + LOOP_GUARD_ITERATIONS + ' iterations";';
	}

	/** Translate the safe callback/table/control-flow subset used by imported Lua. */
	public static function translate(source:String, ?origin:String,
		?allowEmbeddedHscript:Bool = false):LuaCompatResult {
		var diagnostics:Array<String> = [];
		collectionCounter = 0;
		var name = origin == null || StringTools.trim(origin) == '' ? 'lua' : origin;
		if (source == null)
			return {hscript: '', supported: false, diagnostics: [diagnostic(name, 'lua-empty', 'No Lua source was supplied.')]};
		// File.getContent preserves donor bytes. A few old Psych packs contain
		// Shift-JIS/Windows control bytes in comments; String.charAt can throw on
		// those malformed UTF-8 sequences before the comment pass ever sees them.
		// Replace only invalid byte sequences while preserving valid UTF-8 and all
		// ASCII Lua syntax. This is an engine-level input boundary, so the same
		// protection applies to every imported Lua script and not one donor file.
		source = sanitizeInvalidUtf8(source);
		if (source.length > MAX_SOURCE_LENGTH) {
			return {
				hscript: '',
				supported: false,
				diagnostics: [diagnostic(name, 'lua-size-limit', 'Lua source exceeds the 4 MiB compatibility limit.')]
			};
		}

		var protectedHaxeLiterals:Array<{token:String, value:String, expression:Bool}> = [];
		var protectedClosures:Array<{token:String, value:String}> = [];
		closureCounter = 0;
		var routed = routeKnownRawHaxe(source, name, diagnostics, allowEmbeddedHscript);
		if (allowEmbeddedHscript)
			routed = routeEmbeddedHscript(routed, name, diagnostics, protectedHaxeLiterals);
		var masked = allowEmbeddedHscript ? routed : maskRawHaxe(routed, name, diagnostics);
		masked = stripComments(masked);
		masked = maskLongStrings(masked, name, diagnostics);
		masked = renameReservedLuaIdentifiers(masked);
		// Anonymous Lua closures are lowered into protected placeholders before
		// table conversion so their HScript block braces are never mistaken for
		// Lua table constructors.
		masked = rewriteAnonymousFunctionValues(masked, name, diagnostics, protectedClosures);
		masked = rewriteTableArgumentSugar(masked);
		// These standard-library definitions are shadowing declarations for
		// helpers already seeded by PlayState.  Their bodies use `next`, rawset
		// and other Lua-only details, so remove only the recognized definitions
		// and leave every other user-defined function untouched.
		masked = maskKnownLibraryDefinitions(masked);
		masked = convertTables(masked, name, diagnostics);
		// Lua treats an undeclared global read as nil. Preserve that behavior for
		// a simple addLuaSprite layer variable by deferring its lookup to a safe
		// closure: this keeps locals and existing interpreter bindings intact,
		// while a missing global becomes nil instead of an HScript name error.
		masked = routeOptionalAddLuaSpriteLayers(masked);
		// A small number of donor helpers implement Lua table-copy semantics by
		// combining getfenv(), object-keyed caches and metatables.  Lower that
		// conventional helper after Lua table syntax has been converted so the
		// generated HScript function body is not mistaken for another Lua table.
		masked = routeTableCopyHelper(masked);

		var lines = joinLuaLines(StringTools.replace(masked, '\r\n', '\n').split('\n'));
		var output:Array<String> = [];
		var blocks:Array<String> = [];
		for (rawLine in lines) {
			var line = StringTools.trim(rawLine);
			if (line == '') {
				output.push('');
				continue;
			}
			var converted = translateLine(line, blocks, name, diagnostics);
			for (part in converted)
				output.push(part);
		}
		while (blocks.length > 0) {
			var ended = blocks.pop();
			if (ended == 'function')
				output.push('return null;');
			output.push('}');
			addDiagnostic(diagnostics, name, 'lua-unclosed-block', 'Implicitly closed an unterminated Lua block.');
		}

		var generated = TRANSLATED_MARKER + '\n' + output.join('\n');
		// Placeholders are restored from the outside in, so a closure containing
		// another closure restores its nested function values after its own body.
		for (index in 0...protectedClosures.length) {
			var closure = protectedClosures[protectedClosures.length - index - 1];
			generated = StringTools.replace(generated, closure.token, closure.value);
		}
		// Embedded Haxe literals are restored only after every Lua rewrite. A
		// donor body containing e.g. `math.sin` or `string.format` must reach
		// runHaxeCode byte-for-byte instead of being treated as Lua expression text.
		for (literal in protectedHaxeLiterals)
			generated = StringTools.replace(generated, literal.token, literal.expression
				? literal.value : quoteHaxeString(literal.value));
		// Never hand an invalid generated program to the runtime interpreter. The
		// bridge is intentionally partial, but partial support must still fail as a
		// precise diagnostic rather than as a song-load parser exception.
		try {
			new hscript.Parser().parseString(generated);
		} catch (error:Dynamic) {
			addDiagnostic(diagnostics, name, 'lua-generated-syntax',
				'The translated HScript was not parseable and was disabled safely: ' + Std.string(error));
			generated = '// LuaCompat disabled an unparseable donor script: ' + safeComment(name);
		}
		// A script with no executable callbacks is not useful as a runtime
		// module, but returning the text still makes importer diagnostics useful.
		var supported = diagnostics.length == 0;
		return {hscript: generated, supported: supported, diagnostics: diagnostics};
	}

	/** Return a valid UTF-8 string without asking String.charAt to decode the
	 * untrusted input first. Invalid bytes become `?`; valid multibyte names and
	 * string literals are copied byte-for-byte. */
	static function sanitizeInvalidUtf8(value:String):String {
		var source = haxe.io.Bytes.ofString(value);
		var output = new haxe.io.BytesBuffer();
		var i = 0;
		while (i < source.length) {
			var first = source.get(i);
			if (first < 0x80) {
				output.addByte(first);
				i++;
				continue;
			}
			var length = 0;
			if (first >= 0xC2 && first <= 0xDF)
				length = 2;
			else if (first >= 0xE0 && first <= 0xEF)
				length = 3;
			else if (first >= 0xF0 && first <= 0xF4)
				length = 4;
			var valid = length > 0 && i + length <= source.length;
			if (valid) {
				var second = source.get(i + 1);
				valid = second >= 0x80 && second <= 0xBF;
				if (valid && first == 0xE0) valid = second >= 0xA0;
				if (valid && first == 0xED) valid = second <= 0x9F;
				if (valid && first == 0xF0) valid = second >= 0x90;
				if (valid && first == 0xF4) valid = second <= 0x8F;
				var offset = 2;
				while (valid && offset < length) {
					var continuation = source.get(i + offset);
					valid = continuation >= 0x80 && continuation <= 0xBF;
					offset++;
				}
			}
			if (!valid) {
				output.addByte('?'.code);
				i++;
				continue;
			}
			for (offset in 0...length)
				output.addByte(source.get(i + offset));
			i += length;
		}
		return output.getBytes().toString();
	}

	/**
		Join only physically wrapped Lua expressions before the line-oriented
		control-flow pass.  Resonance's setPropertyFromGroup calls put their
		computed value on the next line; treating the opening line as a complete
		statement would append a semicolon and make the generated HScript invalid.
		Delimiter tracking is lexical and does not join unrelated Lua statements.
	*/
	static function joinLuaLines(rawLines:Array<String>):Array<String> {
		var result:Array<String> = [];
		var pending = '';
		var depth = 0;
		for (index in 0...rawLines.length) {
			var raw = rawLines[index];
			var line = StringTools.trim(raw);
			if (line == '') {
				if (pending == '')
					result.push('');
				continue;
			}
			if (pending == '')
				pending = line;
			else
				pending += ' ' + line;
			depth += luaDelimiterDelta(line);
			var next = '';
			var nextIndex = index + 1;
			while (nextIndex < rawLines.length && next == '') {
				next = StringTools.trim(rawLines[nextIndex]);
				nextIndex++;
			}
			if (depth <= 0 && !luaLineNeedsMore(pending) && !luaLineContinuesWith(next)) {
				result.push(pending);
				pending = '';
				depth = 0;
			}
		}
		if (pending != '')
			result.push(pending);
		return result;
	}

	static function luaLineNeedsMore(value:String):Bool {
		var text = StringTools.trim(value);
		if (text == 'return')
			return true;
		for (suffix in ['=', '+', '-', '*', '/', '%', '..', ',', ' and', ' or'])
			if (StringTools.endsWith(text, suffix))
				return true;
		return false;
	}

	static function luaLineContinuesWith(value:String):Bool {
		var text = StringTools.trim(value);
		if (text == '')
			return false;
		for (prefix in ['and ', 'or ', '+', '-', '*', '/', '%', '..'])
			if (StringTools.startsWith(text, prefix))
				return true;
		return false;
	}

	static function luaDelimiterDelta(value:String):Int {
		var depth = 0;
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			switch (c) {
				case '(' | '[' | '{': depth++;
				case ')' | ']' | '}': depth--;
			}
			i++;
		}
		return depth;
	}

	/**
		Lower the conventional recursive table-copy helper used by old Psych
		camera templates.  Its cache is keyed by table identity, which cannot be
		represented by HScript's array indexing; the native helper keeps that
		identity map private and preserves the optional metatable copy policy.
	*/
	static function routeTableCopyHelper(source:String):String {
		if (source == null || source.indexOf('function tableCopy') < 0
			|| source.indexOf('getfenv') < 0 || source.indexOf('tableCopy(') < 0)
			return source;
		var lines = source.split('\n');
		var output:Array<String> = [];
		var i = 0;
		while (i < lines.length) {
			var line = lines[i];
			var header = ~/^(\s*)(?:local\s+)?function\s+tableCopy\s*\(([^)]*)\)\s*$/;
			if (!header.match(line)) {
				output.push(line);
				i++;
				continue;
			}
			var start = i;
			var depth = 1;
			var end = i;
			var body = new StringBuf();
			i++;
			while (i < lines.length) {
				body.add(lines[i]);
				body.add('\n');
				depth += luaBlockDelta(lines[i]);
				end = i;
				i++;
				if (depth <= 0)
					break;
			}
			var bodyText = body.toString();
			if (end >= start && depth <= 0 && bodyText.indexOf('getmetatable') >= 0
				&& bodyText.indexOf('setmetatable') >= 0) {
				var indent = header.matched(1);
				var args = StringTools.trim(header.matched(2));
				var argList = args == '' ? [] : args.split(',');
				var callArgs:Array<String> = [];
				for (arg in argList)
					callArgs.push(StringTools.trim(arg));
				output.push(indent + 'tableCopy = function(' + args + ') { return luaTableCopy('
					+ callArgs.join(', ') + '); }');
			} else {
				for (lineIndex in start...i) output.push(lines[lineIndex]);
			}
		}
		return output.join('\n');
	}

	/** Remove only known standard-library shadow definitions. */
	static function maskKnownLibraryDefinitions(source:String):String {
		if (source == null)
			return source;
		var lines = source.split('\n');
		var output:Array<String> = [];
		var i = 0;
		while (i < lines.length) {
			var line = lines[i];
			var header = ~/^\s*(?:local\s+)?function\s+(table\.(?:find|clear)|math\.clamp)\s*\(/;
			if (!header.match(line)) {
				output.push(line);
				i++;
				continue;
			}
			var start = i;
			var depth = luaBlockDelta(line);
			// A one-line declaration has already balanced its own function block.
			if (depth > 0) {
				depth = 1;
				i++;
				while (i < lines.length) {
					depth += luaBlockDelta(lines[i]);
					i++;
					if (depth <= 0) break;
				}
			} else {
				i++;
			}
			for (lineIndex in start...i) output.push(blankLuaLine(lines[lineIndex]));
		}
		return output.join('\n');
	}

	static function blankLuaLine(line:String):String {
		if (line == null) return '';
		var chars = line.split('');
		for (i in 0...chars.length) chars[i] = ' ';
		return chars.join('');
	}

	static function luaBlockDelta(line:String):Int {
		if (line == null || line == '') return 0;
		var delta = keywordCount(line, 'function') + keywordCount(line, 'repeat');
		var ifs = keywordCount(line, 'if') - keywordCount(line, 'elseif');
		if (ifs > 0 && keywordCount(line, 'then') > 0) delta += ifs;
		if (keywordCount(line, 'do') > 0)
			delta += keywordCount(line, 'for') + keywordCount(line, 'while');
		delta -= keywordCount(line, 'end');
		return delta;
	}

	/**
		Lua anonymous functions can span statements and return other closures.
		Translate each closure body with the same line/control-flow converter used
		for callbacks, then hold the generated HScript behind a token until Lua
		tables have been lowered. This keeps HScript function-block braces out of
		the Lua table scanner and preserves lexical closure capture.
	*/
	static function rewriteAnonymousFunctionValues(source:String, origin:String, diagnostics:Array<String>,
		protected:Array<{token:String, value:String}>):String {
		if (source == null || source.indexOf('function') < 0)
			return source;
		var out = new StringBuf();
		var cursor = 0;
		var scan = 0;
		while (scan < source.length) {
			var token = nextLuaWord(source, scan);
			if (token == null)
				break;
			scan = token.endIndex;
			if (token.word != 'function')
				continue;
			var open = token.endIndex;
			while (open < source.length && isSpace(source.charAt(open))) open++;
			// Named function declarations are handled by translateLine. Only
			// expressions of the form `function(args) ... end` are lowered here.
			if (open >= source.length || source.charAt(open) != '(')
				continue;
			var close = matchingDelimiter(source, open, '(', ')');
			if (close < 0) {
				addDiagnostic(diagnostics, origin, 'lua-function-expression',
					'Anonymous Lua function has an unclosed parameter list.');
				continue;
			}
			var endToken = matchingLuaFunctionEnd(source, close + 1);
			if (endToken == null) {
				addDiagnostic(diagnostics, origin, 'lua-function-expression',
					'Anonymous Lua function has no matching end.');
				continue;
			}
			var body = source.substr(close + 1, endToken.startIndex - close - 1);
			var args = cleanArguments(source.substr(open + 1, close - open - 1), origin, diagnostics);
			var convertedBody = translateLuaFunctionBody(body, origin, diagnostics, protected);
			var functionValue = 'function(' + args + ') { ' + convertedBody + ' }';
			var closureToken = '__luaCompatClosure' + closureCounter++ + '__';
			while (source.indexOf(closureToken) >= 0
				|| Lambda.exists(protected, function(entry) return entry.token == closureToken))
				closureToken += '_';
			out.add(source.substr(cursor, token.startIndex - cursor));
			out.add(closureToken);
			protected.push({token:closureToken, value:functionValue});
			cursor = endToken.endIndex;
			scan = cursor;
		}
		out.add(source.substr(cursor));
		return out.toString();
	}

	/** Locate a closure's `end`, accounting for nested Lua blocks and strings. */
	static function matchingLuaFunctionEnd(source:String, from:Int):Null<{startIndex:Int, endIndex:Int}> {
		var blocks:Array<String> = ['function'];
		var cursor = from;
		while (cursor < source.length) {
			var token = nextLuaWord(source, cursor);
			if (token == null)
				return null;
			cursor = token.endIndex;
			switch (token.word) {
				case 'function' | 'if' | 'for' | 'while' | 'repeat':
					blocks.push(token.word);
				case 'do':
					if (blocks.length == 0 || (blocks[blocks.length - 1] != 'for'
						&& blocks[blocks.length - 1] != 'while'))
						blocks.push('do');
				case 'end':
					if (blocks.length == 0)
						return null;
					blocks.pop();
					if (blocks.length == 0)
						return {startIndex:token.startIndex, endIndex:token.endIndex};
				case 'until':
					if (blocks.length > 0 && blocks[blocks.length - 1] == 'repeat')
						blocks.pop();
				default:
			}
		}
		return null;
	}

	/** Translate one already-delimited anonymous function body. */
	static function translateLuaFunctionBody(source:String, origin:String, diagnostics:Array<String>,
		protected:Array<{token:String, value:String}>):String {
		var masked = rewriteAnonymousFunctionValues(source, origin, diagnostics, protected);
		masked = rewriteTableArgumentSugar(masked);
		masked = convertTables(masked, origin, diagnostics);
		masked = routeOptionalAddLuaSpriteLayers(masked);
		masked = routeTableCopyHelper(masked);
		var lines = joinLuaLines(StringTools.replace(masked, '\r\n', '\n').split('\n'));
		var output:Array<String> = [];
		var blocks:Array<String> = [];
		for (rawLine in lines) {
			var line = StringTools.trim(rawLine);
			if (line == '') {
				output.push('');
				continue;
			}
			for (part in translateLine(line, blocks, origin, diagnostics))
				output.push(part);
		}
		while (blocks.length > 0) {
			blocks.pop();
			output.push('}');
			addDiagnostic(diagnostics, origin, 'lua-unclosed-block',
				'Anonymous Lua function body contains an unterminated block.');
		}
		// Lua functions without an explicit return always yield nil. HScript's
		// expression-valued blocks otherwise return their last statement (and an
		// empty `{}` body is parsed as an empty object literal).
		output.push('return null;');
		return output.join('\n');
	}

	/**
		Lua permits `call(args) { table }` and `call { table }` as call syntax.
		Parenthesize the table argument so the ordinary HScript call parser sees
		`call(args)(table)` after `convertTables` has lowered the constructor.
	*/
	static function rewriteTableArgumentSugar(source:String):String {
		if (source == null || source.indexOf('{') < 0)
			return source;
		var out = new StringBuf();
		var cursor = 0;
		var i = 0;
		while (i < source.length) {
			var c = source.charAt(i);
			if (c == '"' || c == '\'') {
				var quote = c;
				i++;
				while (i < source.length) {
					if (source.charAt(i) == '\\') { i += 2; continue; }
					if (source.charAt(i) == quote) { i++; break; }
					i++;
				}
				continue;
			}
			if (c != '{') { i++; continue; }
			var close = matchingBrace(source, i);
			if (close < 0) { i++; continue; }
			var wrap = tableArgumentCanFollow(source, i);
			out.add(source.substr(cursor, i - cursor));
			if (wrap) out.add('(');
			out.add('{');
			out.add(rewriteTableArgumentSugar(source.substr(i + 1, close - i - 1)));
			out.add('}');
			if (wrap) out.add(')');
			cursor = close + 1;
			i = cursor;
		}
		out.add(source.substr(cursor));
		return out.toString();
	}

	static function tableArgumentCanFollow(source:String, tableStart:Int):Bool {
		var before = tableStart - 1;
		while (before >= 0 && isSpace(source.charAt(before))) before--;
		if (before < 0)
			return false;
		if (source.charAt(before) == ')') {
			var open = matchingOpenDelimiter(source, before, '(', ')');
			if (open < 0)
				return false;
			var callee = open - 1;
			while (callee >= 0 && isSpace(source.charAt(callee))) callee--;
			return callee >= 0 && (isWord(source.charAt(callee))
				|| source.charAt(callee) == ')' || source.charAt(callee) == ']');
		}
		return isWord(source.charAt(before));
	}

	static function keywordCount(value:String, wanted:String):Int {
		var count = 0;
		var cursor = 0;
		while (cursor < value.length) {
			var at = value.indexOf(wanted, cursor);
			if (at < 0) break;
			var before = at == 0 ? '' : value.charAt(at - 1);
			var afterAt = at + wanted.length;
			var after = afterAt >= value.length ? '' : value.charAt(afterAt);
			if (!isWord(before) && !isWord(after)) count++;
			cursor = afterAt;
		}
		return count;
	}

	/**
		Some HScript tokens are valid Lua variable names. Rename those tokens as
		identifiers throughout Lua source, while preserving strings, object fields,
		and table-constructor field names. Keeping declaration and reference
		renaming in one lexical pass also preserves local shadowing and captures.
	*/
	static function renameReservedLuaIdentifiers(source:String):String {
		if (source == null)
			return source;
		var reserved = ['switch', 'case', 'default', 'var', 'new', 'this', 'super',
			'try', 'catch', 'throw', 'continue', 'null'];
		var renamed:Map<String, String> = new Map();
		for (word in reserved) {
			var replacement = '__luaCompatReserved_' + word;
			while (source.indexOf(replacement) >= 0)
				replacement += '_';
			renamed.set(word, replacement);
		}
		var out = new StringBuf();
		var cursor = 0;
		var i = 0;
		var tableDepth = 0;
		while (i < source.length) {
			var c = source.charAt(i);
			if (c == '"' || c == '\'') {
				var quote = c;
				i++;
				while (i < source.length) {
					if (source.charAt(i) == '\\') { i += 2; continue; }
					if (source.charAt(i) == quote) { i++; break; }
					i++;
				}
				continue;
			}
			if (c == '{') { tableDepth++; i++; continue; }
			if (c == '}') { tableDepth--; i++; continue; }
			if (!isIdentifierStart(c)) { i++; continue; }
			var start = i++;
			while (i < source.length && isWord(source.charAt(i))) i++;
			var word = source.substr(start, i - start);
			if (reserved.indexOf(word) < 0)
				continue;
			var previous = start - 1;
			while (previous >= 0 && isSpace(source.charAt(previous))) previous--;
			var next = i;
			while (next < source.length && isSpace(source.charAt(next))) next++;
			var isMemberName = previous >= 0 && source.charAt(previous) == '.'
				&& (previous == 0 || source.charAt(previous - 1) != '.')
				&& (i >= source.length || source.charAt(i) != '.');
			var isTableField = tableDepth > 0 && next < source.length && source.charAt(next) == '='
				&& (next + 1 >= source.length || source.charAt(next + 1) != '=')
				&& previous >= 0 && (source.charAt(previous) == '{' || source.charAt(previous) == ',');
			if (isMemberName || isTableField)
				continue;
			out.add(source.substr(cursor, start - cursor));
			out.add(renamed.get(word));
			cursor = i;
		}
		out.add(source.substr(cursor));
		return out.toString();
	}

	static function translateLine(line:String, blocks:Array<String>, origin:String, diagnostics:Array<String>):Array<String> {
		var result:Array<String> = [];
		var text = StringTools.trim(line);
		if (text == '') {
			result.push('');
			return result;
		}

		// Lua permits complete if/elseif/else blocks on one physical line. Parse
		// their block keywords before converting the bodies so semicolons and an
		// inline `else` do not leak into one HScript expression.
		var inlineIf = translateInlineIf(text, blocks, origin, diagnostics);
		if (inlineIf != null) {
			for (part in inlineIf)
				result.push(part);
			return result;
		}

		var inlineFor = translateInlineFor(text, blocks, origin, diagnostics);
		if (inlineFor != null) {
			for (part in inlineFor)
				result.push(part);
			return result;
		}

		// Lua permits compact named functions such as
		// `function mathlerp(a,b,t)return ... end`.  Keep the declaration
		// assignment-safe for both plain and dotted names.
		var inlineFunction = ~/^(?:local\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(([^)]*)\)\s*(.+)\s+end\s*;?$/;
		if (inlineFunction.match(text)) {
			var inlineName = inlineFunction.matched(1);
			var inlineArgs = cleanArguments(inlineFunction.matched(2), origin, diagnostics);
			var inlineBody = convertStatement(inlineFunction.matched(3), origin, diagnostics);
			result.push(namedFunctionStatement(inlineName, inlineArgs, inlineBody,
				isLocalNamedFunction(text), blocks));
			return result;
		}

		// Lua semicolons separate statements. Preserve nested call/table syntax
		// and only split at top level; this also handles compact local assignments
		// that otherwise arrive at HScript as one invalid statement.
		var semicolonStatements = splitLuaSemicolonStatements(text);
		if (semicolonStatements.length > 1) {
			for (statement in semicolonStatements)
				for (converted in translateLine(statement, blocks, origin, diagnostics))
					result.push(converted);
			return result;
		}

		// Lua permits consecutive function-call statements on one physical line,
		// and old Psych scripts sometimes put the closing `end` after the final
		// call. Split only at top-level call boundaries; commas and nested calls
		// remain part of the original expression.
		var inlineStatements = splitInlineStatements(text);
		if (inlineStatements.length > 1) {
			for (statement in inlineStatements)
				for (converted in translateLine(statement, blocks, origin, diagnostics))
					result.push(converted);
			return result;
		}

		var functionMatch = ~/^(?:local\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(([^)]*)\)\s*$/;
		if (functionMatch.match(text)) {
			var functionName = functionMatch.matched(1);
			var args = cleanArguments(functionMatch.matched(2), origin, diagnostics);
			result.push(namedFunctionStatement(functionName, args, null,
				isLocalNamedFunction(text), blocks));
			blocks.push('function');
			return result;
		}
		if (~/^(?:local\s+)?function\s+/.match(text)) {
			addDiagnostic(diagnostics, origin, 'lua-function-name', 'Only plain named Lua functions can be routed to HScript: ' + text);
			result.push('// LuaCompat unsupported function: ' + safeComment(text));
			return result;
		}

		var elseifMatch = ~/^elseif\s*(.+)\s*then\s*$/;
		if (elseifMatch.match(text) && text.length > 6 && !isWord(text.charAt(6))
			&& StringTools.trim(elseifMatch.matched(1)) != '') {
			if (blocks.length == 0)
				addDiagnostic(diagnostics, origin, 'lua-unbalanced-elseif', 'elseif has no open block.');
			result.push('} else if (' + convertExpression(elseifMatch.matched(1), origin, diagnostics) + ') {');
			return result;
		}
		if (text == 'else' || text == 'else;') {
			result.push('} else {');
			return result;
		}

		var ifMatch = ~/^if\s*(.+)\s*then\s*$/;
		if (ifMatch.match(text) && text.length > 2 && !isWord(text.charAt(2))
			&& StringTools.trim(ifMatch.matched(1)) != '') {
			result.push('if (' + convertExpression(ifMatch.matched(1), origin, diagnostics) + ') {');
			blocks.push('if');
			return result;
		}
		var whileMatch = ~/^while\s+(.+)\s+do\s*$/;
		if (whileMatch.match(text)) {
			var guardName = loopGuardName();
			result.push('var ' + guardName + ' = 0;');
			result.push('while (' + convertExpression(whileMatch.matched(1), origin, diagnostics) + ') {');
			result.push(guardIncrement(guardName));
			blocks.push('while');
			return result;
		}

		var numericFor = ~/^for\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*,\s*(.+?)(?:\s*,\s*(.+?))?\s+do\s*$/;
		if (numericFor.match(text)) {
			var variable = numericFor.matched(1);
			var first = numericFor.matched(2);
			var last = numericFor.matched(3);
			var step = numericFor.matched(4);
			if (step != null && StringTools.trim(step) != '' && StringTools.trim(step) != '1') {
				var loopId = collectionCounter++;
				var startName = '__luaForStart' + loopId;
				var endName = '__luaForEnd' + loopId;
				var stepName = '__luaForStep' + loopId;
				var guardName = loopGuardName(loopId);
				result.push('var ' + startName + ' = Std.int(' + convertExpression(first, origin, diagnostics) + ');');
				result.push('var ' + endName + ' = Std.int(' + convertExpression(last, origin, diagnostics) + ');');
				result.push('var ' + stepName + ' = Std.int(' + convertExpression(step, origin, diagnostics) + ');');
				result.push('if (' + stepName + ' != 0) {');
				result.push('var ' + variable + ' = ' + startName + ';');
				result.push('var ' + guardName + ' = 0;');
				result.push('while ((' + stepName + ' > 0 && ' + variable + ' <= ' + endName + ') || ('
					+ stepName + ' < 0 && ' + variable + ' >= ' + endName + ')) {');
				result.push(guardIncrement(guardName));
				blocks.push('for-step:' + variable + ':' + loopId);
				return result;
			}
			// HScript's interpreter does not expose Haxe's IntIterator as a
			// reflective iterator. Route inclusive Lua ranges through the
			// engine-owned Array helper instead of emitting a range expression
			// which parses successfully but fails when a callback executes.
			result.push('for (' + variable + ' in makeRangeArray(Std.int('
				+ convertExpression(last, origin, diagnostics) + ') + 1, Std.int('
				+ convertExpression(first, origin, diagnostics) + '))) {');
			blocks.push('for');
			return result;
		}

		var collectionFor = ~/^for\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*,\s*([A-Za-z_][A-Za-z0-9_]*))?\s+in\s+(pairs|ipairs)\s*\((.+)\)\s+do\s*$/;
		if (collectionFor.match(text)) {
			var key = collectionFor.matched(1);
			var value = collectionFor.matched(2);
			var isPairs = collectionFor.matched(3) == 'pairs';
			var lengthHelper = isPairs ? 'luaPairsLength' : 'luaIpairsLength';
			var keyHelper = isPairs ? 'luaPairsKey' : 'luaIpairsKey';
			var valueHelper = isPairs ? 'luaPairsValue' : 'luaIpairsValue';
			var collection = convertExpression(collectionFor.matched(4), origin, diagnostics);
			// ipairs traverses the one-based sequence; pairs also traverses string
			// and object keys attached to an otherwise array-shaped Lua table.
			var pairId = collectionCounter++;
			var tableName = '__luaCollection' + pairId;
			var indexName = '__luaIndex' + pairId;
			result.push('var ' + tableName + ' = ' + collection + ';');
			result.push('for (' + indexName + ' in makeRangeArray(' + lengthHelper + '('
				+ tableName + ') + 1, 1)) {');
			result.push('var ' + key + ' = ' + keyHelper
				+ '(' + tableName + ', ' + indexName + ');');
			if (value != null && StringTools.trim(value) != '')
				result.push('var ' + value + ' = ' + valueHelper
					+ '(' + tableName + ', ' + key + ');');
			blocks.push('for');
			return result;
		}

		// The common Lua split helper uses string.gmatch(input, "([^,]+)").
		// It is a bounded array iterator, not an arbitrary Lua pattern engine.
		var stringIteratorFor = ~/^for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+(string\.gmatch\s*\(.+\))\s+do\s*$/;
		if (stringIteratorFor.match(text)) {
			var iterator = convertExpression(stringIteratorFor.matched(2), origin, diagnostics);
			result.push('for (' + stringIteratorFor.matched(1) + ' in ' + iterator + ') {');
			blocks.push('for');
			return result;
		}

		if (text == 'end' || text == 'end;') {
			var ended = blocks.length == 0 ? null : blocks[blocks.length - 1];
			if (blocks.length == 0)
				addDiagnostic(diagnostics, origin, 'lua-unbalanced-end', 'Lua end has no open block.');
			else
				blocks.pop();
			if (ended == 'function')
				result.push('return null;');
			if (ended != null && StringTools.startsWith(ended, 'for-step:')) {
				// Lua's numeric loop advances after each body execution. Without
				// this update every non-unit step spins until the watchdog fires.
				var parts = ended.split(':');
				result.push(parts[1] + ' += __luaForStep' + parts[2] + ';');
				result.push('}');
				result.push('} else { throw "lua numeric for step is zero"; }');
			} else
				result.push('}');
			return result;
		}
		if (text == 'repeat') {
			addDiagnostic(diagnostics, origin, 'lua-repeat', 'repeat/until loops are not routed by the deterministic bridge.');
			result.push('// LuaCompat unsupported control flow: repeat');
			result.push('if (false) {');
			blocks.push('repeat');
			return result;
		}
		if (StringTools.startsWith(text, 'until ')) {
			addDiagnostic(diagnostics, origin, 'lua-until', 'repeat/until loops are not routed by the deterministic bridge.');
			if (blocks.length > 0 && blocks[blocks.length - 1] == 'repeat')
				blocks.pop();
			result.push('} // LuaCompat unsupported control flow: ' + safeComment(text));
			return result;
		}

		if (StringTools.startsWith(text, 'goto ') || text == '::' || text.indexOf('::') >= 0) {
			addDiagnostic(diagnostics, origin, 'lua-goto', 'goto/labels are not routed by the deterministic bridge.');
			result.push('// LuaCompat unsupported control flow: ' + safeComment(text));
			return result;
		}
		if (text == 'continue' || text == 'continue;') {
			addDiagnostic(diagnostics, origin, 'lua-continue', 'continue is not part of the HScript subset.');
			result.push('// LuaCompat unsupported control flow: continue');
			return result;
		}

		var multiple = splitMultipleAssignment(text, origin, diagnostics);
		if (multiple != null) {
			for (statement in multiple)
				result.push(statement);
			return result;
		}

		// Dynamic-global rewrites happen in convertExpression(), but inspect the
		// routed spelling here too so a supported `_G` read is not rejected before
		// the statement converter gets a chance to lower it.
		var unsupported = unsupportedLibrary(rewriteDynamicGlobals(text));
		if (unsupported != null) {
			addDiagnostic(diagnostics, origin, unsupported.code, unsupported.message);
			result.push('// LuaCompat unsupported expression: ' + safeComment(text));
			return result;
		}
		result.push(convertStatement(text, origin, diagnostics));
		return result;
	}

	/** Translate an inline Lua if-block only when its complete outer block is on this line. */
	static function translateInlineIf(source:String, blocks:Array<String>, origin:String,
		diagnostics:Array<String>):Null<Array<String>> {
		if (source == null || source.length < 2 || source.substr(0, 2) != 'if'
			|| (source.length > 2 && isWord(source.charAt(2))))
			return null;
		var thenToken = findLuaKeyword(source, 'then', 2);
		if (thenToken == null)
			return null;
		var condition = StringTools.trim(source.substr(2, thenToken.startIndex - 2));
		if (condition == '')
			return null;

		var branches:Array<{condition:Null<String>, body:String}> = [];
		var currentCondition:Null<String> = condition;
		var bodyStart = thenToken.endIndex;
		var finished = false;
		while (!finished) {
			var boundary = findLuaInlineBoundary(source, bodyStart);
			if (boundary == null)
				return null;
			branches.push({condition:currentCondition,
				body:source.substr(bodyStart, boundary.startIndex - bodyStart)});
			switch (boundary.word) {
				case 'end':
					var suffix = StringTools.trim(source.substr(boundary.endIndex));
					if (suffix != '' && suffix != ';')
						return null;
					finished = true;
				case 'elseif':
					if (currentCondition == null)
						return null;
					var branchThen = findLuaKeyword(source, 'then', boundary.endIndex);
					if (branchThen == null)
						return null;
					currentCondition = StringTools.trim(source.substr(boundary.endIndex,
						branchThen.startIndex - boundary.endIndex));
					if (currentCondition == '')
						return null;
					bodyStart = branchThen.endIndex;
				case 'else':
					if (currentCondition == null)
						return null;
					currentCondition = null;
					bodyStart = boundary.endIndex;
				default:
					return null;
			}
		}

		var output:Array<String> = [];
		for (index in 0...branches.length) {
			var branch = branches[index];
			if (index == 0)
				output.push('if (' + convertExpression(branch.condition, origin, diagnostics) + ') {');
			else if (branch.condition == null)
				output.push('} else {');
			else
				output.push('} else if (' + convertExpression(branch.condition, origin, diagnostics) + ') {');
			for (statement in splitLuaSemicolonStatements(branch.body)) {
				for (part in splitInlineStatements(statement)) {
					for (converted in translateLine(part, blocks, origin, diagnostics))
						output.push(converted);
				}
			}
		}
		output.push('}');
		return output;
	}

	/** Translate a complete one-line numeric or collection Lua loop. */
	static function translateInlineFor(source:String, blocks:Array<String>, origin:String,
		diagnostics:Array<String>):Null<Array<String>> {
		if (source == null || source.length < 4 || source.substr(0, 3) != 'for'
			|| (source.length > 3 && isWord(source.charAt(3))))
			return null;
		var doToken = findLuaKeyword(source, 'do', 3);
		if (doToken == null)
			return null;
		var boundary = findLuaInlineBoundary(source, doToken.endIndex);
		if (boundary == null || boundary.word != 'end')
			return null;
		var suffix = StringTools.trim(source.substr(boundary.endIndex));
		if (suffix != '' && suffix != ';')
			return null;

		var output:Array<String> = [];
		var header = StringTools.trim(source.substr(0, doToken.endIndex));
		for (part in translateLine(header, blocks, origin, diagnostics))
			output.push(part);
		var body = source.substr(doToken.endIndex, boundary.startIndex - doToken.endIndex);
		for (statement in splitLuaSemicolonStatements(body)) {
			for (part in translateLine(statement, blocks, origin, diagnostics))
				output.push(part);
		}
		for (part in translateLine('end', blocks, origin, diagnostics))
			output.push(part);
		return output;
	}

	/** Find a Lua keyword without treating a quoted string as syntax. */
	static function findLuaKeyword(source:String, wanted:String, from:Int):Null<{word:String,
		startIndex:Int, endIndex:Int}> {
		var cursor = from;
		while (cursor < source.length) {
			var token = nextLuaWord(source, cursor);
			if (token == null)
				return null;
			if (token.word == wanted)
				return token;
			cursor = token.endIndex;
		}
		return null;
	}

	/** Locate an outer `elseif`, `else`, or `end`, skipping nested Lua blocks. */
	static function findLuaInlineBoundary(source:String, from:Int):Null<{word:String,
		startIndex:Int, endIndex:Int}> {
		var nested:Array<String> = [];
		var cursor = from;
		while (cursor < source.length) {
			var token = nextLuaWord(source, cursor);
			if (token == null)
				return null;
			cursor = token.endIndex;
			switch (token.word) {
				case 'if' | 'function' | 'for' | 'while' | 'repeat':
					nested.push(token.word);
				case 'do':
					if (nested.length == 0 || (nested[nested.length - 1] != 'for'
						&& nested[nested.length - 1] != 'while'))
						nested.push('do');
				case 'end':
					if (nested.length == 0)
						return token;
					nested.pop();
				case 'until':
					if (nested.length > 0 && nested[nested.length - 1] == 'repeat')
						nested.pop();
				case 'elseif' | 'else':
					if (nested.length == 0)
						return token;
				default:
			}
		}
		return null;
	}

	/** Return the next identifier-shaped word outside quoted strings. */
	static function nextLuaWord(source:String, from:Int):Null<{word:String,
		startIndex:Int, endIndex:Int}> {
		var cursor = from;
		while (cursor < source.length) {
			var character = source.charAt(cursor);
			if (character == '"' || character == "'") {
				var quote = character;
				cursor++;
				while (cursor < source.length) {
					if (source.charAt(cursor) == '\\') {
						cursor += 2;
						continue;
					}
					if (source.charAt(cursor) == quote) {
						cursor++;
						break;
					}
					cursor++;
				}
				continue;
			}
			if (isIdentifierStart(character)) {
				var start = cursor++;
				while (cursor < source.length && isWord(source.charAt(cursor)))
					cursor++;
				return {word:source.substr(start, cursor - start), startIndex:start, endIndex:cursor};
			}
			cursor++;
		}
		return null;
	}

	/** Split top-level semicolon statements while retaining any nested block body. */
	static function splitLuaSemicolonStatements(value:String):Array<String> {
		var result:Array<String> = [];
		var start = 0;
		var delimiters = 0;
		var blocks:Array<String> = [];
		var cursor = 0;
		while (cursor < value.length) {
			var character = value.charAt(cursor);
			if (character == '"' || character == "'") {
				var quote = character;
				cursor++;
				while (cursor < value.length) {
					if (value.charAt(cursor) == '\\') {
						cursor += 2;
						continue;
					}
					if (value.charAt(cursor) == quote) {
						cursor++;
						break;
					}
					cursor++;
				}
				continue;
			}
			if (character == '(' || character == '[' || character == '{') {
				delimiters++;
				cursor++;
				continue;
			}
			if (character == ')' || character == ']' || character == '}') {
				delimiters--;
				cursor++;
				continue;
			}
			if (isIdentifierStart(character)) {
				var wordStart = cursor++;
				while (cursor < value.length && isWord(value.charAt(cursor)))
					cursor++;
				var word = value.substr(wordStart, cursor - wordStart);
				switch (word) {
					case 'if' | 'function' | 'for' | 'while' | 'repeat': blocks.push(word);
					case 'do':
						if (blocks.length == 0 || (blocks[blocks.length - 1] != 'for'
							&& blocks[blocks.length - 1] != 'while'))
							blocks.push('do');
					case 'end': if (blocks.length > 0) blocks.pop();
					case 'until':
						if (blocks.length > 0 && blocks[blocks.length - 1] == 'repeat')
							blocks.pop();
					default:
				}
				continue;
			}
			if (character == ';' && delimiters == 0 && blocks.length == 0) {
				var statement = StringTools.trim(value.substr(start, cursor - start));
				if (statement != '') result.push(statement);
				start = cursor + 1;
			}
			cursor++;
		}
		var tail = StringTools.trim(value.substr(start));
		if (StringTools.endsWith(tail, ';'))
			tail = StringTools.trim(tail.substr(0, tail.length - 1));
		if (tail != '') result.push(tail);
		return result.length == 0 ? [value] : result;
	}

	/** Lower the simple parallel assignments used by Lua matrix helpers. */
	static function splitMultipleAssignment(text:String, origin:String, diagnostics:Array<String>):Null<Array<String>> {
		var equal = topLevelEquals(text);
		if (equal < 0)
			return null;
		var lhs = StringTools.trim(text.substr(0, equal));
		var local = false;
		if (StringTools.startsWith(lhs, 'local ')) {
			local = true;
			lhs = StringTools.trim(lhs.substr(6));
		}
		var names = splitTopLevel(lhs, ',');
		var right = StringTools.trim(text.substr(equal + 1));
		var stringMatch = parseLuaStringMatch(right);
		if (stringMatch != null) {
			var matchResult:Array<String> = [];
			var matchNames:Array<String> = [];
			for (nameRaw in names) {
				var name = StringTools.trim(nameRaw);
				if (!~/^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$/.match(name))
					return null;
				matchNames.push(name);
				matchResult.push((local ? 'var ' : '') + name + ' = null;');
			}
			var matchId = '__luaStringMatch' + collectionCounter++;
			var patternLiteral = '"' + escapeHscriptString(stringMatch.regex) + '"';
			var input = convertExpression(stringMatch.input, origin, diagnostics);
			matchResult.push('var ' + matchId + ' = new EReg(' + patternLiteral + ', "");');
			matchResult.push('if (' + matchId + '.match(' + input + ')) {');
			for (index in 0...matchNames.length) {
				var value = index < stringMatch.captures ? matchId + '.matched(' + (index + 1) + ')' : 'null';
				matchResult.push(matchNames[index] + ' = ' + value + ';');
			}
			matchResult.push('}');
			return matchResult;
		}
		if (names.length <= 1)
			return null;
		var values = splitTopLevel(right, ',');
		var result:Array<String> = [];
		for (index in 0...names.length) {
			var name = StringTools.trim(names[index]);
			if (!~/^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$/.match(name))
				return null;
			var value = index < values.length ? StringTools.trim(values[index]) : 'nil';
			var convertedValue = value == 'nil' ? 'null' : convertExpression(value, origin, diagnostics);
			if (local)
				result.push('var ' + name + ' = ' + convertedValue + ';');
			else
				result.push(name + ' = ' + convertedValue + ';');
		}
		return result;
	}

	/** Parse the literal-pattern capture subset of Lua string.match. */
	static function parseLuaStringMatch(value:String):Null<{input:String, regex:String, captures:Int}> {
		var text = StringTools.trim(value);
		if (StringTools.endsWith(text, ';'))
			text = StringTools.trim(text.substr(0, text.length - 1));
		if (!StringTools.startsWith(text, 'string.match'))
			return null;
		var cursor = 'string.match'.length;
		if (cursor < text.length && isWord(text.charAt(cursor)))
			return null;
		while (cursor < text.length && isSpace(text.charAt(cursor))) cursor++;
		if (cursor >= text.length || text.charAt(cursor) != '(')
			return null;
		var close = matchingDelimiter(text, cursor, '(', ')');
		if (close < 0 || StringTools.trim(text.substr(close + 1)) != '')
			return null;
		var args = splitTopLevel(text.substr(cursor + 1, close - cursor - 1), ',');
		if (args.length != 2)
			return null;
		var pattern = literalStringValue(args[1]);
		if (pattern == null)
			return null;
		var translated = luaCapturePattern(pattern);
		if (translated == null)
			return null;
		return {input:StringTools.trim(args[0]), regex:translated.regex, captures:translated.captures};
	}

	/** Convert only Lua's portable single-line capture classes and quantifiers. */
	static function luaCapturePattern(pattern:String):Null<{regex:String, captures:Int}> {
		var output = new StringBuf();
		var captures = 0;
		var depth = 0;
		var cursor = 0;
		while (cursor < pattern.length) {
			var character = pattern.charAt(cursor);
			if (character == '%') {
				cursor++;
				if (cursor >= pattern.length)
					return null;
				var escaped = pattern.charAt(cursor);
				switch (escaped) {
					case 'a': output.add('[A-Za-z]');
					case 'd': output.add('[0-9]');
					case 's': output.add('\\s');
					case 'w': output.add('[A-Za-z0-9_]');
					case 'l': output.add('[a-z]');
					case 'u': output.add('[A-Z]');
					case 'A': output.add('[^A-Za-z]');
					case 'D': output.add('[^0-9]');
					case 'S': output.add('\\S');
					case 'W': output.add('[^A-Za-z0-9_]');
					case '%': output.add('%');
					default: return null;
				}
				cursor++;
				continue;
			}
			switch (character) {
				case '(':
					captures++;
					depth++;
					output.add('(');
				case ')':
					depth--;
					if (depth < 0) return null;
					output.add(')');
				case '.' | '*' | '+' | '?' | '^' | '$': output.add(character);
				case '-':
					// Lua's non-greedy repetition follows an atom; Haxe's regular
					// expression spelling is the same quantifier with a trailing ?.
					if (output.toString().length == 0) return null;
					output.add('*?');
				default:
					if ('\\[]{}|'.indexOf(character) >= 0)
						output.add('\\');
					output.add(character);
			}
			cursor++;
		}
		if (depth != 0 || captures == 0)
			return null;
		return {regex:output.toString(), captures:captures};
	}

	static function escapeHscriptString(value:String):String {
		return StringTools.replace(StringTools.replace(value, '\\', '\\\\'), '"', '\\"');
	}

	static function splitInlineStatements(value:String):Array<String> {
		var result:Array<String> = [];
		var quote = '';
		var depth = 0;
		var start = 0;
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '(' || c == '[' || c == '{') depth++;
			else if (c == ')' || c == ']' || c == '}') depth--;
			if (depth == 0 && (c == ')' || c == ']' || c == '}')) {
				var cursor = i + 1;
				while (cursor < value.length && isSpace(value.charAt(cursor))) cursor++;
				if (cursor > i + 1 && cursor < value.length) {
					var wordEnd = cursor;
					while (wordEnd < value.length && isWord(value.charAt(wordEnd))) wordEnd++;
					var word = value.substr(cursor, wordEnd - cursor);
					var functionReturn = word == 'return'
						&& value.substr(start, cursor - start).indexOf('function') >= 0;
					if (word != '' && !functionReturn
						&& ['and', 'or', 'then', 'do', 'else', 'elseif'].indexOf(word) < 0) {
						result.push(StringTools.trim(value.substr(start, cursor - start)));
						start = cursor;
						i = cursor;
						continue;
					}
				}
			}
			i++;
		}
		var tail = StringTools.trim(value.substr(start));
		if (StringTools.endsWith(tail, ' end') && tail.indexOf('function') < 0
			&& !StringTools.startsWith(tail, 'if ')
			&& !StringTools.startsWith(tail, 'while ') && !StringTools.startsWith(tail, 'for ')) {
			result.push(StringTools.trim(tail.substr(0, tail.length - 4)));
			result.push('end');
		} else if (tail != '')
			result.push(tail);
		return result.length == 0 ? [value] : result;
	}

	static function cleanArguments(args:String, origin:String, diagnostics:Array<String>):String {
		if (args == null || StringTools.trim(args) == '')
			return '';
		if (args.indexOf('...') >= 0) {
			addDiagnostic(diagnostics, origin, 'lua-varargs', 'Lua varargs (...) are not routed by the bridge.');
			return '';
		}
		var pieces = args.split(',');
		var out:Array<String> = [];
		for (piece in pieces) {
			var arg = StringTools.trim(piece);
			if (arg == '')
				continue;
			var equal = arg.indexOf('=');
			if (equal >= 0) {
				addDiagnostic(diagnostics, origin, 'lua-default-arg', 'Lua default arguments are not routed: ' + arg);
				arg = StringTools.trim(arg.substr(0, equal));
			}
			if (!~/^[A-Za-z_][A-Za-z0-9_]*$/.match(arg)) {
				addDiagnostic(diagnostics, origin, 'lua-argument', 'Invalid Lua callback argument: ' + arg);
				continue;
			}
			// Lua fills omitted positional parameters with nil and ignores extra
			// arguments. HScript functions are strict by default, so make each
			// translated parameter optional to preserve the donor call convention.
			out.push('?' + arg);
		}
		return out.join(', ');
	}

	/** Emit a function value assignment for a Lua dotted declaration. */
	static function functionAssignment(name:String, args:String, body:Null<String>):String {
		var prefix = name + ' = function(' + args + ') {';
		return body == null ? prefix : prefix + ' ' + body + ' return null; }';
	}

	/**
		Lua's `function name()` is an assignment when nested inside a function.
		Keep the top-level declaration form used by stage callback discovery, while
		lowering nested non-local definitions to a scope-aware HScript assignment.
	*/
	static function namedFunctionStatement(name:String, args:String, body:Null<String>,
		isLocal:Bool, blocks:Array<String>):String {
		var nested = blocks != null && blocks.indexOf('function') >= 0;
		// Lua local functions are lexically scoped even at chunk scope. HScript's
		// named EFunction declaration writes to interpreter globals at depth zero,
		// so declare a local slot first and assign the closure into it. The slot is
		// captured by reference, which also preserves local-function recursion.
		if (isLocal)
			return 'var ' + name + '; ' + functionAssignment(name, args, body);
		if (name.indexOf('.') >= 0 || (!isLocal && nested))
			return functionAssignment(name, args, body);
		var declaration = 'function ' + name + '(' + args + ') {';
		return body == null ? declaration : declaration + ' ' + body + ' return null; }';
	}

	static function isLocalNamedFunction(source:String):Bool {
		return source != null && ~/^local\s+function\s+/.match(source);
	}

	/** Lower the compact anonymous `function(args)return value end` form. */
	static function rewriteInlineFunctionExpressions(value:String):String {
		if (value == null || value.indexOf('function') < 0)
			return value;
		var out = new StringBuf();
		var cursor = 0;
		while (cursor < value.length) {
			var start = value.indexOf('function', cursor);
			if (start < 0) {
				out.add(value.substr(cursor));
				break;
			}
			var before = start == 0 ? '' : value.charAt(start - 1);
			var afterName = start + 'function'.length;
			var after = afterName >= value.length ? '' : value.charAt(afterName);
			if (isWord(before) || isWord(after)) {
				out.add(value.substr(cursor, afterName - cursor));
				cursor = afterName;
				continue;
			}
			var open = afterName;
			while (open < value.length && isSpace(value.charAt(open))) open++;
			if (open >= value.length || value.charAt(open) != '(') {
				out.add(value.substr(cursor, afterName - cursor));
				cursor = afterName;
				continue;
			}
			var close = matchingDelimiter(value, open, '(', ')');
			if (close < 0) {
				out.add(value.substr(cursor));
				break;
			}
			var bodyStart = close + 1;
			while (bodyStart < value.length && isSpace(value.charAt(bodyStart))) bodyStart++;
			if (value.substr(bodyStart, 6) != 'return' || (bodyStart + 6 < value.length && isWord(value.charAt(bodyStart + 6)))) {
				out.add(value.substr(cursor, afterName - cursor));
				cursor = afterName;
				continue;
			}
			var expressionStart = bodyStart + 6;
			while (expressionStart < value.length && isSpace(value.charAt(expressionStart))) expressionStart++;
			var end = findLuaEndKeyword(value, expressionStart);
			if (end < 0) {
				out.add(value.substr(cursor));
				break;
			}
			out.add(value.substr(cursor, start - cursor));
			out.add('function(' + value.substr(open + 1, close - open - 1) + ') { return ');
			out.add(value.substr(expressionStart, end - expressionStart));
			out.add('; }');
			cursor = end + 3;
		}
		return out.toString();
	}

	static function findLuaEndKeyword(value:String, from:Int):Int {
		var quote = '';
		var i = from;
		while (i + 2 < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (value.substr(i, 3) == 'end'
				&& (i == 0 || !isWord(value.charAt(i - 1)))
				&& (i + 3 >= value.length || !isWord(value.charAt(i + 3))))
				return i;
			i++;
		}
		return -1;
	}

	/**
		Lua's colon call implicitly passes the receiver as argument one.  The
		bridge only lowers side-effect-free identifier/property receivers, so a
		complex expression is left untouched and remains diagnosable.
	*/
	static function rewriteColonCalls(value:String, origin:String, diagnostics:Array<String>):String {
		if (value == null || value.indexOf(':') < 0)
			return value;
		var out = new StringBuf();
		var cursor = 0;
		var i = 0;
		var quote = '';
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c != ':') { i++; continue; }
			var receiverStart = colonReceiverStart(value, i);
			if (receiverStart < 0) { i++; continue; }
			var receiverPrefix = receiverStart - 1;
			while (receiverPrefix >= 0 && isSpace(value.charAt(receiverPrefix))) receiverPrefix--;
			// `convertTables()` already uses HScript's `key: value` spelling for
			// anonymous objects.  A call-shaped value after `{`/`,` is therefore a
			// table field, not Lua's receiver-colon syntax.
			if (receiverPrefix >= 0 && (value.charAt(receiverPrefix) == '{' || value.charAt(receiverPrefix) == ',')) {
				i++;
				continue;
			}
			var methodStart = i + 1;
			while (methodStart < value.length && isSpace(value.charAt(methodStart))) methodStart++;
			var methodEnd = methodStart;
			while (methodEnd < value.length && isWord(value.charAt(methodEnd))) methodEnd++;
			if (methodEnd == methodStart) { i++; continue; }
			var open = methodEnd;
			while (open < value.length && isSpace(value.charAt(open))) open++;
			if (open >= value.length || value.charAt(open) != '(') { i++; continue; }
			var close = matchingDelimiter(value, open, '(', ')');
			if (close < 0) { i++; continue; }
			var receiver = StringTools.trim(value.substr(receiverStart, i - receiverStart));
			var args = StringTools.trim(value.substr(open + 1, close - open - 1));
			out.add(value.substr(cursor, receiverStart - cursor));
			out.add(receiver + '.' + value.substr(methodStart, methodEnd - methodStart) + '(' + receiver
				+ (args == '' ? '' : ', ' + args) + ')');
			cursor = close + 1;
			i = cursor;
		}
		out.add(value.substr(cursor));
		return out.toString();
	}

	static function colonReceiverStart(value:String, colon:Int):Int {
		var cursor = colon;
		while (cursor > 0 && isSpace(value.charAt(cursor - 1))) cursor--;
		var end = cursor;
		while (cursor > 0 && isWord(value.charAt(cursor - 1))) cursor--;
		if (cursor == end || !isIdentifierStart(value.charAt(cursor))) return -1;
		while (cursor > 0 && value.charAt(cursor - 1) == '.') {
			cursor--;
			var partEnd = cursor;
			while (cursor > 0 && isWord(value.charAt(cursor - 1))) cursor--;
			if (cursor == partEnd || !isIdentifierStart(value.charAt(cursor))) return -1;
		}
		return cursor;
	}

	static function isIdentifierStart(value:String):Bool {
		if (value == null || value == '') return false;
		var code = value.charCodeAt(0);
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || value == '_';
	}

	static function convertStatement(statement:String, origin:String, diagnostics:Array<String>):String {
		var text = StringTools.trim(statement);
		var localMatch = ~/^local\s+(.+)$/;
		if (localMatch.match(text))
			text = 'var ' + localMatch.matched(1);
		text = convertExpression(text, origin, diagnostics);
		// Lua uses newlines as statement separators; HScript's lexer does not.
		// Preserve explicit semicolons and add one to every ordinary statement.
		return StringTools.endsWith(text, ';') ? text : text + ';';
	}

	/** Convert Lua operators/libraries without touching quoted strings. */
	static function convertExpression(expression:String, origin:String, diagnostics:Array<String>):String {
		var text = rewriteDynamicGlobals(expression);
		text = rewriteLegacyStrumAliases(text, origin, diagnostics);
		text = rewriteInlineFunctionExpressions(text);
		text = rewriteColonCalls(text, origin, diagnostics);
		text = replaceOutsideStrings(text, '..', '+');
		text = replaceOutsideStrings(text, '~=', '!=');
		text = replaceWordOutsideStrings(text, 'and', '&&');
		text = replaceWordOutsideStrings(text, 'or', '||');
		text = replaceWordOutsideStrings(text, 'not', '!');
		text = replaceWordOutsideStrings(text, 'nil', 'null');
		text = replaceMath(text, origin, diagnostics);
		text = replaceLuaBuiltins(text, origin, diagnostics);
		text = replaceTableHelpers(text, origin, diagnostics);
		// Lua's length operator is 1 character and only has a useful direct
		// equivalent for a named array/table in this bridge.
		var length = ~/#\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)/g;
		text = length.replace(text, 'luaSequenceLength($1)');
		return text;
	}

	/**
		Route only the dynamic globals used by the mounted tutorial/Resonance
		modules.  Lua's `_G` table is intentionally not exposed as a general
		HScript environment: an unknown key remains in the source and is reported
		by unsupportedLibrary(), preserving the existing safety boundary.
	*/
	static function rewriteDynamicGlobals(source:String):String {
		if (source == null || source.indexOf('_G') < 0)
			return source;

		// The donor writes only these whitelisted names.  Handle a complete
		// assignment first so the read-side replacement cannot produce an invalid
		// `luaGetScriptGlobal(...) = value` expression.
		var leading = firstDynamicGlobal(source, 0);
		if (leading != null && StringTools.trim(source.substr(0, leading.startIndex)) == '') {
			var after = leading.endIndex;
			while (after < source.length && isSpace(source.charAt(after))) after++;
			if (after < source.length && source.charAt(after) == '=' 
				&& (after + 1 >= source.length || source.charAt(after + 1) != '=')) {
				if (leading.mode == 'script' || (leading.mode == 'literal' && leading.key == 'objects')) {
					var rhs = StringTools.trim(source.substr(after + 1));
					if (StringTools.endsWith(rhs, ';'))
						rhs = StringTools.trim(rhs.substr(0, rhs.length - 1));
					return 'luaSetScriptGlobal(' + leading.keyExpression + ', ' + rhs + ')';
				}
				// The baseline defaultStrum family is read-only.  Preserve an
				// attempted write so unsupportedLibrary() diagnoses it instead of
				// producing an invalid getter-assignment or silently dropping it.
				return source;
			}
		}

		var out = new StringBuf();
		var cursor = 0;
		var quote = '';
		while (cursor < source.length) {
			var c = source.charAt(cursor);
			if (quote != '') {
				out.add(c);
				if (c == '\\' && cursor + 1 < source.length) {
					out.add(source.charAt(cursor + 1));
					cursor += 2;
					continue;
				}
				if (c == quote) quote = '';
				cursor++;
				continue;
			}
			if (c == '"' || c == "'") {
				quote = c;
				out.add(c);
				cursor++;
				continue;
			}
			if (source.substr(cursor, 2) == '_G'
				&& (cursor == 0 || !isWord(source.charAt(cursor - 1)))
				&& (cursor + 2 >= source.length || !isWord(source.charAt(cursor + 2)))) {
				var ref = parseDynamicGlobal(source, cursor);
				if (ref != null) {
					out.add(dynamicGlobalRead(ref));
					cursor = ref.endIndex;
					continue;
				}
			}
			out.add(c);
			cursor++;
		}
		return out.toString();
	}

	/**
		Route Psych's bare side-specific receptor globals through the same native
		baseline adapter used by `_G['defaultPlayerStrumX' .. i]`.  These names are
		engine globals in Psych, not chart-local variables; leaving them as bare
		HScript identifiers makes an otherwise valid imported modchart fail only
		when the callback first reaches the reset/shake branch.
	*/
	static function rewriteLegacyStrumAliases(source:String, origin:String,
		diagnostics:Array<String>):String {
		if (source == null || source.indexOf('default') < 0)
			return source;
		var out = new StringBuf();
		var cursor = 0;
		var quote = '';
		while (cursor < source.length) {
			var c = source.charAt(cursor);
			if (quote != '') {
				out.add(c);
				if (c == '\\' && cursor + 1 < source.length) {
					out.add(source.charAt(cursor + 1));
					cursor += 2;
					continue;
				}
				if (c == quote)
					quote = '';
				cursor++;
				continue;
			}
			if (c == '"' || c == "'") {
				quote = c;
				out.add(c);
				cursor++;
				continue;
			}
			if (!isIdentifierStart(c)) {
				out.add(c);
				cursor++;
				continue;
			}
			var start = cursor;
			cursor++;
			while (cursor < source.length && isWord(source.charAt(cursor)))
				cursor++;
			var identifier = source.substr(start, cursor - start);
			var previous = start == 0 ? '' : source.charAt(start - 1);
			var alias = legacyStrumAlias(identifier);
			// A property named like the Psych global is not a bare engine alias.
			if (alias == null || previous == '.') {
				out.add(identifier);
				continue;
			}
			var after = cursor;
			while (after < source.length && isSpace(source.charAt(after)))
				after++;
			if (after < source.length && source.charAt(after) == '=') {
				addDiagnostic(diagnostics, origin, 'lua-default-strum-write',
					'Psych default receptor globals are read-only: ' + identifier);
				out.add(identifier);
				continue;
			}
			out.add(alias);
		}
		return out.toString();
	}

	static function legacyStrumAlias(identifier:String):Null<String> {
		var match = ~/^default(Player|Opponent)Strum([XY])([0-3])$/;
		if (!match.match(identifier))
			return null;
		var side = match.matched(1).toLowerCase() == 'opponent' ? 'opponent' : 'player';
		var axis = match.matched(2).toLowerCase();
		return 'luaGetSideDefaultStrum("' + side + '", ' + match.matched(3)
			+ ', "' + axis + '")';
	}

	/** Return the first `_G` reference, including its source offset. */
	static function firstDynamicGlobal(source:String, from:Int):Null<LuaDynamicGlobalRef> {
		var cursor = from;
		var quote = '';
		while (cursor < source.length) {
			var c = source.charAt(cursor);
			if (quote != '') {
				if (c == '\\') { cursor += 2; continue; }
				if (c == quote) quote = '';
				cursor++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; cursor++; continue; }
			if (source.substr(cursor, 2) == '_G'
				&& (cursor == 0 || !isWord(source.charAt(cursor - 1)))
				&& (cursor + 2 >= source.length || !isWord(source.charAt(cursor + 2)))) {
				var ref = parseDynamicGlobal(source, cursor);
				if (ref != null)
					return ref;
			}
			cursor++;
		}
		return null;
	}

	/** Parse `_G.name` and `_G["name"]` without evaluating arbitrary Lua. */
	static function parseDynamicGlobal(source:String, start:Int):Null<LuaDynamicGlobalRef> {
		var cursor = start + 2;
		while (cursor < source.length && isSpace(source.charAt(cursor))) cursor++;
		var rawKeyExpression:String = null;
		var key:String = null;
		if (cursor < source.length && source.charAt(cursor) == '.') {
			cursor++;
			while (cursor < source.length && isSpace(source.charAt(cursor))) cursor++;
			var identifierStart = cursor;
			while (cursor < source.length && isWord(source.charAt(cursor))) cursor++;
			if (cursor == identifierStart)
				return null;
			key = source.substr(identifierStart, cursor - identifierStart);
			rawKeyExpression = '"' + key + '"';
		} else if (cursor < source.length && source.charAt(cursor) == '[') {
			var close = matchingDelimiter(source, cursor, '[', ']');
			if (close < 0)
				return null;
			rawKeyExpression = StringTools.trim(source.substr(cursor + 1, close - cursor - 1));
			cursor = close + 1;
		} else {
			return null;
		}

		var literal = literalStringValue(rawKeyExpression);
		if (literal != null)
			key = literal;
		if (key == 'objects')
			return {startIndex: start, endIndex: cursor, mode: 'literal', key: key,
				keyExpression: rawKeyExpression, indexExpression: null, axis: null};
		var parts = splitLuaConcatExpression(rawKeyExpression);
		if (parts.length == 3) {
			var defaultPrefix = literalStringValue(parts[0]);
			var defaultSuffix = literalStringValue(parts[2]);
			if (defaultPrefix == 'defaultStrum' && (defaultSuffix == 'X' || defaultSuffix == 'Y'))
				return {startIndex: start, endIndex: cursor, mode: 'default', key: null,
					keyExpression: null, indexExpression: StringTools.trim(parts[1]), axis: defaultSuffix};
		}
		if (parts.length == 2) {
			var strumPrefix = literalStringValue(parts[0]);
			if (strumPrefix == 'defaultPlayerStrumX' || strumPrefix == 'defaultPlayerStrumY'
				|| strumPrefix == 'defaultOpponentStrumX' || strumPrefix == 'defaultOpponentStrumY')
				return {startIndex: start, endIndex: cursor, mode: 'script', key: null,
					keyExpression: '"' + strumPrefix + '" .. (' + StringTools.trim(parts[1]) + ')',
					indexExpression: StringTools.trim(parts[1]), axis: strumPrefix.substr(strumPrefix.length - 1)};
		}
		return null;
	}

	static function dynamicGlobalRead(ref:LuaDynamicGlobalRef):String {
		if (ref.mode == 'default')
			return 'luaGetDefaultStrum(' + ref.indexExpression + ', "' + ref.axis.toLowerCase() + '")';
		return 'luaGetScriptGlobal(' + ref.keyExpression + ')';
	}

	static function literalStringValue(value:String):Null<String> {
		var text = StringTools.trim(value);
		if (text.length < 2)
			return null;
		var quote = text.charAt(0);
		if ((quote != '"' && quote != "'") || text.charAt(text.length - 1) != quote)
			return null;
		var body = text.substr(1, text.length - 2);
		var out = new StringBuf();
		var i = 0;
		while (i < body.length) {
			var c = body.charAt(i++);
			if (c != '\\') {
				out.add(c);
				continue;
			}
			if (i >= body.length)
				return null;
			var escape = body.charAt(i++);
			switch (escape) {
				case 'a': out.addChar(7);
				case 'b': out.addChar(8);
				case 'f': out.addChar(12);
				case 'n': out.add('\n');
				case 'r': out.add('\r');
				case 't': out.add('\t');
				case 'v': out.addChar(11);
				case '\\' | '"' | "'": out.add(escape);
				case '\n':
				case '\r':
					if (escape == '\r' && i < body.length && body.charAt(i) == '\n') i++;
					out.add('\n');
				case 'z':
					while (i < body.length && isSpace(body.charAt(i))) i++;
				case 'x':
					if (i + 1 >= body.length) return null;
					var hex = body.substr(i, 2);
					if (!~/^[0-9A-Fa-f]{2}$/.match(hex)) return null;
					out.addChar(Std.parseInt('0x' + hex));
					i += 2;
				default:
					if (escape >= '0' && escape <= '9') {
						var digits = escape;
						var count = 1;
						while (count < 3 && i < body.length && body.charAt(i) >= '0' && body.charAt(i) <= '9') {
							digits += body.charAt(i++);
							count++;
						}
						var code = Std.parseInt(digits);
						if (code > 255) return null;
						out.addChar(code);
					} else
						return null;
			}
		}
		return out.toString();
	}

	/** Split a Lua concatenation at top level while preserving nested arithmetic. */
	static function splitLuaConcatExpression(value:String):Array<String> {
		var result:Array<String> = [];
		var start = 0;
		var depth = 0;
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '(' || c == '[' || c == '{') depth++;
			else if (c == ')' || c == ']' || c == '}') depth--;
			if (depth == 0 && c == '.' && i + 1 < value.length && value.charAt(i + 1) == '.') {
				result.push(StringTools.trim(value.substr(start, i - start)));
				start = i + 2;
				i += 2;
				continue;
			}
			i++;
		}
		result.push(StringTools.trim(value.substr(start)));
		return result;
	}

	static function replaceMath(text:String, origin:String, diagnostics:Array<String>):String {
		var mappings:Array<{from:String, to:String}> = [
			{from: 'math.pi', to: 'Math.PI'},
			{from: 'math.sin', to: 'Math.sin'},
			{from: 'math.cos', to: 'Math.cos'},
			{from: 'math.asin', to: 'Math.asin'},
			{from: 'math.tan', to: 'Math.tan'},
			{from: 'math.sqrt', to: 'Math.sqrt'},
			{from: 'math.exp', to: 'Math.exp'},
			{from: 'math.floor', to: 'Math.floor'},
			{from: 'math.ceil', to: 'Math.ceil'},
			{from: 'math.abs', to: 'Math.abs'},
			{from: 'math.min', to: 'Math.min'},
			{from: 'math.max', to: 'Math.max'},
			{from: 'math.pow', to: 'Math.pow'},
			// Psych mods commonly provide math.lerp from their Lua runtime. FlxMath
			// is already exposed to every compatibility interpreter and has the
			// same three-argument interpolation contract.
			{from: 'math.lerp', to: 'FlxMath.lerp'},
			// Lua's random() has three overloads (no args, max, min/max).  Route
			// it through the runtime helper instead of assuming Psych's two-arg
			// getRandomInt shape.
			{from: 'math.randomseed', to: 'luaMathRandomSeed'},
			{from: 'math.random', to: 'luaMathRandom'},
			{from: 'math.rad', to: 'luaMathRad'},
			{from: 'math.clamp', to: 'luaMathClamp'}
		];
		for (entry in mappings)
			text = replaceOutsideStrings(text, entry.from, entry.to);
		text = routeMathFmod(text, origin, diagnostics);
		if (containsOutsideStrings(text, 'math.')) {
			addDiagnostic(diagnostics, origin, 'lua-math', 'Unsupported Lua math helper remains in expression: ' + text);
		}
		return text;
	}

	/** Lower Lua's two-argument fmod through the translated scope's `%` operator. */
	static function routeMathFmod(source:String, origin:String, diagnostics:Array<String>):String {
		if (source == null || !containsOutsideStrings(source, 'math.fmod'))
			return source;
		var output = new StringBuf();
		var cursor = 0;
		while (cursor < source.length) {
			var call = indexOutsideStrings(source, 'math.fmod', cursor);
			if (call < 0) {
				output.add(source.substr(cursor));
				break;
			}
			var before = call == 0 ? '' : source.charAt(call - 1);
			var afterName = call + 'math.fmod'.length;
			if (isWord(before) || (afterName < source.length && isWord(source.charAt(afterName)))) {
				output.add(source.substr(cursor, afterName - cursor));
				cursor = afterName;
				continue;
			}
			var open = afterName;
			while (open < source.length && isSpace(source.charAt(open))) open++;
			var close = open < source.length && source.charAt(open) == '('
				? matchingDelimiter(source, open, '(', ')') : -1;
			if (close < 0) {
				output.add(source.substr(cursor, afterName - cursor));
				cursor = afterName;
				continue;
			}
			var args = splitTopLevel(source.substr(open + 1, close - open - 1), ',');
			if (args.length != 2) {
				output.add(source.substr(cursor, close + 1 - cursor));
				addDiagnostic(diagnostics, origin, 'lua-math',
					'math.fmod expects exactly two arguments: ' + source.substr(call, close + 1 - call));
				cursor = close + 1;
				continue;
			}
			output.add(source.substr(cursor, call - cursor));
			output.add('(' + convertExpression(StringTools.trim(args[0]), origin, diagnostics)
				+ ' % ' + convertExpression(StringTools.trim(args[1]), origin, diagnostics) + ')');
			cursor = close + 1;
		}
		return output.toString();
	}

	/** Route the small Lua standard-library subset used by the donor corpus. */
	static function replaceLuaBuiltins(text:String, origin:String, diagnostics:Array<String>):String {
		text = routeLiteralGsub(text);
		for (entry in [
			{from: 'tonumber', to: 'luaNumber'},
			{from: 'tostring', to: 'luaString'},
			{from: 'string.sub', to: 'luaStringSub'},
			{from: 'string.len', to: 'luaStringLen'},
			{from: 'string.find', to: 'luaStringFind'},
			{from: 'string.lower', to: 'luaStringLower'},
			{from: 'string.upper', to: 'luaStringUpper'},
			{from: 'string.format', to: 'luaStringFormat'},
			{from: 'string.gmatch', to: 'luaStringGmatch'},
			{from: 'os.clock', to: 'luaOsClock'},
			{from: 'os.time', to: 'luaOsTime'},
			{from: 'table.find', to: 'luaTableFind'},
			{from: 'table.clear', to: 'luaTableClear'},
			{from: 'getfenv', to: 'luaGetEnvironment'},
			{from: 'getmetatable', to: 'luaGetMetatable'}
		])
			text = replaceOutsideStrings(text, entry.from, entry.to);
		// Metatable writes are routed only when the metatable is a named local
		// table.  An arbitrary table expression remains visible to the safety
		// checker and therefore keeps the existing lua-metatable diagnostic.
		var safeMetatable = ~/setmetatable\s*\(\s*([^,()]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)/g;
		text = safeMetatable.replace(text, 'luaSetMetatable($1, $2)');
		// HScript has no Lua `type` global.  Keep the call shape and provide a
		// deterministic helper through the interpreter seed in PlayState.
		text = replaceWordOutsideStrings(text, 'type', 'luaType');
		if (containsLibraryPrefix(text, 'string.'))
			addDiagnostic(diagnostics, origin, 'lua-string-library', 'This Lua string helper is not routed: ' + text);
		if (containsLibraryPrefix(text, 'os.'))
			addDiagnostic(diagnostics, origin, 'lua-os', 'This Lua os helper is not routed: ' + text);
		return text;
	}

	/** Route literal gsub patterns plus the small character-class subset used
		for title cleanup. Other Lua patterns stay diagnosed. */
	static function routeLiteralGsub(value:String):String {
		if (value == null || value.indexOf('string.gsub') < 0)
			return value;
		var out = new StringBuf();
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				out.add(c);
				if (c == '\\' && i + 1 < value.length) {
					i++;
					out.add(value.charAt(i));
				} else if (c == quote)
					quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") {
				quote = c;
				out.add(c);
				i++;
				continue;
			}
			if (value.substr(i, 'string.gsub'.length) == 'string.gsub'
				&& (i == 0 || !isWord(value.charAt(i - 1)))) {
				var open = i + 'string.gsub'.length;
				while (open < value.length && isSpace(value.charAt(open))) open++;
				var close = open < value.length && value.charAt(open) == '('
					? matchingDelimiter(value, open, '(', ')') : -1;
				if (close > open) {
					var args = splitTopLevel(value.substr(open + 1, close - open - 1), ',');
					var pattern = args.length >= 3 ? literalStringValue(args[1]) : null;
					var replacement = args.length >= 3 ? literalStringValue(args[2]) : null;
					if (args.length >= 3 && args.length <= 4
						&& supportedGsubPattern(pattern, replacement)) {
						out.add('luaStringGsub');
						i += 'string.gsub'.length;
						continue;
					}
				}
			}
			out.add(c);
			i++;
		}
		return out.toString();
	}

	static function literalGsubPattern(pattern:String):Null<String> {
		if (pattern == null || pattern == '') return null;
		var output = new StringBuf();
		var meta = '.^$*+?-[]()';
		var i = 0;
		while (i < pattern.length) {
			var c = pattern.charAt(i);
			if (c == '%') {
				i++;
				if (i >= pattern.length || meta.indexOf(pattern.charAt(i)) < 0
					&& pattern.charAt(i) != '%') return null;
				output.add(pattern.charAt(i));
			} else {
				if (meta.indexOf(c) >= 0) return null;
				output.add(c);
			}
			i++;
		}
		return output.toString();
	}

	static function supportedGsubPattern(pattern:String, replacement:String):Bool {
		if (pattern == null || replacement == null) return false;
		if (literalGsubPattern(pattern) != null)
			return replacement.indexOf('%') < 0;
		return (pattern == '[^%a%d]' && replacement.indexOf('%') < 0)
			|| (pattern == '%s+' && replacement.indexOf('%') < 0)
			|| (pattern == '^%s*(.-)%s*$' && replacement == '%1');
	}

	/** Match a Lua library token outside strings. A substring such as the `os.`
	 * in `camFollowPos.x` is an object property, not an os-library call. */
	static function containsLibraryPrefix(value:String, prefix:String):Bool {
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (value.substr(i, prefix.length) == prefix && (i == 0 || !isWord(value.charAt(i - 1))))
				return true;
			i++;
		}
		return false;
	}

	static function replaceTableHelpers(text:String, origin:String, diagnostics:Array<String>):String {
		text = routeTableConcat(text, origin, diagnostics);
		var insert = ~/table\.insert\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*,\s*(.+)\)/g;
		text = insert.replace(text, '$1.push($2)');
		var remove = ~/table\.remove\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*,\s*(.+)\)/g;
		text = remove.replace(text, '$1.splice(($2) - 1, 1)');
		if (containsOutsideStrings(text, 'table.'))
			addDiagnostic(diagnostics, origin, 'lua-table-library', 'Unsupported Lua table helper remains in expression: ' + text);
		return text;
	}

	/** Route Lua table.concat call syntax and the `table.concat{...}` shorthand. */
	static function routeTableConcat(source:String, origin:String, diagnostics:Array<String>):String {
		if (source == null || source.indexOf('table.concat') < 0)
			return source;
		var output = new StringBuf();
		var cursor = 0;
		var search = 0;
		while (search < source.length) {
			var character = source.charAt(search);
			if (character == '"' || character == "'") {
				var quote = character;
				search++;
				while (search < source.length) {
					if (source.charAt(search) == '\\') { search += 2; continue; }
					if (source.charAt(search) == quote) { search++; break; }
					search++;
				}
				continue;
			}
			if (source.substr(search, 'table.concat'.length) != 'table.concat'
				|| (search > 0 && isWord(source.charAt(search - 1)))
				|| (search + 'table.concat'.length < source.length
					&& isWord(source.charAt(search + 'table.concat'.length)))) {
				search++;
				continue;
			}
			var nameEnd = search + 'table.concat'.length;
			var open = nameEnd;
			while (open < source.length && isSpace(source.charAt(open))) open++;
			var bracketShorthand = open < source.length && source.charAt(open) == '[';
			var delimiter = bracketShorthand ? '[' : '(';
			if (!bracketShorthand && (open >= source.length || source.charAt(open) != '(')) {
				search = nameEnd;
				continue;
			}
			var closing = bracketShorthand ? ']' : ')';
			var close = matchingDelimiter(source, open, delimiter, closing);
			if (close < 0) {
				search = nameEnd;
				continue;
			}
			var args = bracketShorthand ? ['[' + source.substr(open + 1, close - open - 1) + ']']
				: splitTopLevel(source.substr(open + 1, close - open - 1), ',');
			if (args.length < 1 || args.length > 2) {
				search = close + 1;
				continue;
			}
			var tableExpression = StringTools.trim(args[0]);
			var separator = args.length == 2 ? StringTools.trim(args[1]) : "''";
			var tableLiteral = tableExpression.length >= 2 && tableExpression.charAt(0) == '['
				&& tableExpression.charAt(tableExpression.length - 1) == ']';
			var replacement:String = null;
			if (tableLiteral) {
				var values = splitTopLevel(tableExpression.substr(1, tableExpression.length - 2), ',');
				var parts:Array<String> = [];
				for (value in values) {
					var item = StringTools.trim(value);
					if (item != '')
						parts.push('luaString(' + convertExpression(item, origin, diagnostics) + ')');
				}
				var convertedSeparator = convertExpression(separator, origin, diagnostics);
				replacement = parts.length == 0 ? "''"
					: '(' + parts.join(' + ' + convertedSeparator + ' + ') + ')';
			} else {
				replacement = dynamicTableConcat(convertExpression(tableExpression, origin, diagnostics),
					convertExpression(separator, origin, diagnostics));
			}
			output.add(source.substr(cursor, search - cursor));
			output.add(replacement);
			cursor = close + 1;
			search = close + 1;
		}
		output.add(source.substr(cursor));
		return output.toString();
	}

	/** Build an expression that traverses a runtime Lua sequence through shared helpers. */
	static function dynamicTableConcat(tableExpression:String, separator:String):String {
		var id = collectionCounter++;
		var tableName = '__luaConcatTable' + id;
		var separatorName = '__luaConcatSeparator' + id;
		var indexName = '__luaConcatIndex' + id;
		var valueName = '__luaConcatItem' + id;
		var outputName = '__luaConcatOutput' + id;
		return '(function(' + tableName + ', ' + separatorName + ') { var ' + outputName + ' = ""; '
			+ 'var __luaConcatLength' + id + ' = luaSequenceLength(' + tableName + '); '
			+ 'for (' + indexName + ' in makeRangeArray(__luaConcatLength' + id + ' + 1, 1)) { '
			+ 'var ' + valueName + ' = luaTableValue(' + tableName + ', ' + indexName + '); '
			+ 'if (' + valueName + ' == null) throw "table.concat received nil at index " + ' + indexName + '; '
			+ 'if (' + indexName + ' > 1) ' + outputName + ' += ' + separatorName + '; '
			+ outputName + ' += luaString(' + valueName + '); } return ' + outputName + '; })('
			+ tableExpression + ', ' + separator + ')';
	}

	static function unsupportedLibrary(text:String):{code:String, message:String} {
		// Reads of the scoped environment/metatable and writes whose metatable is
		// a named table are lowered by replaceLuaBuiltins().  Check only the
		// residual write forms here so intentionally unsafe arbitrary metatables
		// retain their diagnostic.
		if (text != null && text.indexOf('setmetatable') >= 0) {
			var residual = ~/setmetatable\s*\(\s*([^,()]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)/g.replace(text, '');
			if (residual.indexOf('setmetatable') >= 0)
				return {code: 'lua-metatable', message: 'Lua metatables are not routed. [' + text + ']'};
		}
		for (entry in [
			{prefix: 'runHaxeCode', code: 'lua-raw-haxe', message: 'runHaxeCode was removed from the generated script.'},
			{prefix: '_G', code: 'lua-global-table', message: '_G dynamic global lookup is not routed.'},
			{prefix: 'setfenv', code: 'lua-environment', message: 'setfenv is not routed.'},
			{prefix: 'coroutine.', code: 'lua-coroutine', message: 'Lua coroutines are not routed.'},
			{prefix: 'require(', code: 'lua-module', message: 'Lua require() modules are not routed.'},
			{prefix: 'loadstring', code: 'lua-dynamic-code', message: 'Lua dynamic code loading is not routed.'}
			// math.rad/math.clamp/randomseed, os.clock/os.time, string.sub/len,
			// tonumber/tostring and table.find/clear are rewritten by
			// replaceLuaBuiltins before the generated statement is emitted.
		]) {
			if (text.indexOf(entry.prefix) >= 0
				&& (entry.prefix != 'runHaxeCode' || containsOutsideStrings(text, entry.prefix)))
				return {code: entry.code, message: entry.message + ' [' + text + ']'};
		}
		return null;
	}

	static function safeComment(value:String):String {
		return StringTools.replace(StringTools.replace(value, '\n', ' '), '*/', '* /');
	}

	static function diagnostic(origin:String, code:String, message:String):String {
		return '[lua-' + code.substr(4) + '] ' + origin + ': ' + message;
	}

	static function addDiagnostic(diagnostics:Array<String>, origin:String, code:String, message:String):Void {
		var value = diagnostic(origin, code, message);
		if (diagnostics.indexOf(value) < 0)
			diagnostics.push(value);
	}

	/** Mask raw Haxe passed through Psych's runHaxeCode before Lua parsing. */
	static function maskRawHaxe(source:String, origin:String, diagnostics:Array<String>):String {
		var chars = source.split('');
		var i = 0;
		var found = false;
		while (i < source.length) {
			var token = source.substr(i, 11);
			if (token == 'runHaxeCode') {
				var open = i + token.length;
				while (open < source.length && isSpace(source.charAt(open))) open++;
				if (open < source.length && source.charAt(open) == '(') {
					var cursor = open + 1;
					while (cursor < source.length && isSpace(source.charAt(cursor))) cursor++;
					var end = findRunHaxeLongEnd(source, cursor + 2);
					if (cursor + 1 < source.length && source.substr(cursor, 2) == '[[' && end >= 0) {
						var close = source.indexOf(')', end + 2);
						if (close < 0) close = end + 2;
						for (p in i...close + 1)
							if (chars[p] != '\n' && chars[p] != '\r') chars[p] = ' ';
						found = true;
						var rawBody = source.substr(cursor + 2, end - cursor - 2);
						var rawLine = source.substr(0, i).split('\n').length;
						var cameraReason = rawCameraAngleDiagnostic(rawBody, rawLine);
						if (cameraReason == null)
							addDiagnostic(diagnostics, origin, 'lua-raw-haxe', 'runHaxeCode blocks are not executed by the Lua bridge.');
						else
							// Keep the established lua-raw-haxe code so callers can group
							// all embedded-Haxe gaps, but include the structural reason
							// instead of hiding a malformed near-match behind a generic
							// "arbitrary Haxe" message.
							addDiagnostic(diagnostics, origin, 'lua-raw-haxe', cameraReason);
						i = close + 1;
						continue;
					}
				}
			}
			i++;
		}
		return chars.join('');
	}

	/**
		Route the common Psych shader-filter bridge without enabling arbitrary
		runHaxeCode. The donor code only names Lua sprites whose shaders were
		already created through the public compatibility API.
	*/
	static function routeKnownRawHaxe(source:String, origin:String, diagnostics:Array<String>,
		lexical:Bool = false):String {
		if (source == null || source.indexOf('runHaxeCode') < 0)
			return source;
		var output = new StringBuf();
		var cursor = 0;
		while (cursor < source.length) {
			var start = lexical ? indexRunHaxeCodeOutsideLua(source, cursor)
				: source.indexOf('runHaxeCode', cursor);
			if (start < 0) {
				output.add(source.substr(cursor));
				break;
			}
			output.add(source.substr(cursor, start - cursor));
			var open = start + 'runHaxeCode'.length;
			while (open < source.length && isSpace(source.charAt(open))) open++;
			if (open >= source.length || source.charAt(open) != '(') {
				output.add('runHaxeCode');
				cursor = start + 'runHaxeCode'.length;
				continue;
			}
			var longStart = open + 1;
			while (longStart < source.length && isSpace(source.charAt(longStart))) longStart++;
			if (longStart + 1 >= source.length || source.substr(longStart, 2) != '[[') {
				var moveCamera = rawQuotedMoveCameraCall(source, longStart);
				if (moveCamera != null) {
					output.add(moveCamera.replacement);
					cursor = moveCamera.endIndex;
				} else {
					output.add(source.substr(start, longStart - start));
					cursor = longStart;
				}
				continue;
			}
			var longEnd = findRunHaxeLongEnd(source, longStart + 2);
			if (longEnd < 0) {
				output.add(source.substr(start));
				break;
			}
			var close = source.indexOf(')', longEnd + 2);
			if (close < 0) close = longEnd + 2;
			var body = source.substr(longStart + 2, longEnd - longStart - 2);
			var replacement = rawKnownHaxeRoute(body);
			if (replacement == null)
				output.add(source.substr(start, close + 1 - start));
			else
				output.add(replacement);
			cursor = close + 1;
		}
		return output.toString();
	}

	/**
		In the opt-in mode, find calls only in Lua code. Raw Haxe bodies, Lua
		quoted strings, long strings and comments are skipped as opaque text so a
		callback name written in prose cannot become executable code.
	*/
	static function indexRunHaxeCodeOutsideLua(source:String, from:Int):Int {
		var i = from;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '"' || ch == "'") {
				i = skipLuaQuotedString(source, i);
				continue;
			}
			if (source.substr(i, 2) == '--') {
				if (source.substr(i + 2, 2) == '[[') {
					var end = source.indexOf(']]', i + 4);
					i = end < 0 ? source.length : end + 2;
				} else {
					var end = source.indexOf('\n', i + 2);
					i = end < 0 ? source.length : end + 1;
				}
				continue;
			}
			if (source.substr(i, 2) == '[[') {
				var end = source.indexOf(']]', i + 2);
				i = end < 0 ? source.length : end + 2;
				continue;
			}
			if (source.substr(i, 'runHaxeCode'.length) == 'runHaxeCode'
				&& (i == 0 || !isWord(source.charAt(i - 1)))
				&& (i + 'runHaxeCode'.length >= source.length
					|| !isWord(source.charAt(i + 'runHaxeCode'.length))))
				return i;
			i++;
		}
		return -1;
	}

	static function skipLuaQuotedString(source:String, start:Int):Int {
		var quote = source.charAt(start);
		var i = start + 1;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '\\') {
				i += 2;
				continue;
			}
			if (ch == quote) return i + 1;
			i++;
		}
		return source.length;
	}

	/**
		Replace embedded Psych calls with the host-seeded source alias. Literal
		Haxe is protected with placeholders until Lua conversion is complete;
		optional varsToBring/function arguments remain ordinary Lua expressions.
	*/
	static function routeEmbeddedHscript(source:String, origin:String, diagnostics:Array<String>,
		protected:Array<{token:String, value:String, expression:Bool}>):String {
		if (source == null || source.indexOf('runHaxeCode') < 0) return source;
		var output = new StringBuf();
		var cursor = 0;
		var tokenCounter = 0;
		while (cursor < source.length) {
			var start = indexRunHaxeCodeOutsideLua(source, cursor);
			if (start < 0) {
				output.add(source.substr(cursor));
				break;
			}
			var open = start + 'runHaxeCode'.length;
			while (open < source.length && isSpace(source.charAt(open))) open++;
			if (open >= source.length || source.charAt(open) != '(') {
				output.add(source.substr(cursor, start - cursor));
				output.add('sourceRunHaxeCode');
				cursor = start + 'runHaxeCode'.length;
				continue;
			}
			var bounds = findLuaCallBounds(source, open);
			if (bounds == null) {
				output.add(source.substr(cursor, start - cursor));
				output.add('sourceRunHaxeCode');
				cursor = start + 'runHaxeCode'.length;
				continue;
			}

			var expression = renderEmbeddedHaxeArgument(source, open + 1, bounds.argumentEnd,
				origin, diagnostics, protected, tokenCounter);
			output.add(source.substr(cursor, start - cursor));
			output.add('sourceRunHaxeCode(');
			output.add(expression == null
				? StringTools.trim(source.substring(open + 1, bounds.argumentEnd)) : expression);
			output.add(source.substring(bounds.argumentEnd, bounds.callEnd + 1));
			cursor = bounds.callEnd + 1;
		}
		return output.toString();
	}

	/** Locate the first argument and matching outer call close, skipping literals. */
	static function findLuaCallBounds(source:String, open:Int):Null<{argumentEnd:Int, callEnd:Int}> {
		var parens = 1;
		var brackets = 0;
		var braces = 0;
		var argumentEnd = -1;
		var i = open + 1;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '"' || ch == "'") {
				i = skipLuaQuotedString(source, i);
				continue;
			}
			if (source.substr(i, 2) == '[[') {
				var end = source.indexOf(']]', i + 2);
				if (end < 0) return null;
				i = end + 2;
				continue;
			}
			if (source.substr(i, 2) == '--') {
				if (source.substr(i + 2, 2) == '[[') {
					var end = source.indexOf(']]', i + 4);
					if (end < 0) return null;
					i = end + 2;
				} else {
					var end = source.indexOf('\n', i + 2);
					i = end < 0 ? source.length : end + 1;
				}
				continue;
			}
			switch (ch) {
				case '(':
					parens++;
				case ')':
					parens--;
					if (parens == 0) {
						if (argumentEnd < 0) argumentEnd = i;
					return {argumentEnd:argumentEnd, callEnd:i};
					}
				case '[': brackets++;
				case ']': if (brackets > 0) brackets--;
				case '{': braces++;
				case '}': if (braces > 0) braces--;
				case ',':
					if (argumentEnd < 0 && parens == 1 && brackets == 0 && braces == 0)
						argumentEnd = i;
				default:
			}
			i++;
		}
		return null;
	}

	/**
		Build a protected HScript string expression from Lua long/quoted string
		pieces and normal Lua concatenation operands. A nonliteral argument remains
		on the established Lua expression path.
	*/
	static function renderEmbeddedHaxeArgument(source:String, start:Int, end:Int,
		origin:String, diagnostics:Array<String>, protected:Array<{token:String, value:String, expression:Bool}>,
		tokenCounter:Int):Null<String> {
		var cursor = start;
		var terms:Array<String> = [];
		var hasLiteral = false;
		while (cursor < end) {
			while (cursor < end && isSpace(source.charAt(cursor))) cursor++;
			if (cursor >= end) break;
			var ch = source.charAt(cursor);
			if (source.substr(cursor, 2) == '[[') {
				var close = source.indexOf(']]', cursor + 2);
				if (close < 0 || close > end) return null;
				terms.push(protectEmbeddedValue(source.substring(cursor + 2, close), false,
					source, protected, tokenCounter++));
				hasLiteral = true;
				cursor = close + 2;
				cursor = skipRawRouteSpaces(source, cursor);
				if (cursor + 1 < end && source.substr(cursor, 2) == '..') cursor += 2;
				continue;
			}
			if (ch == '"' || ch == "'") {
				var literal = readEmbeddedLuaString(source, cursor, end);
				if (literal == null) return null;
				terms.push(protectEmbeddedValue(literal.value, false, source, protected, tokenCounter++));
				hasLiteral = true;
				cursor = literal.endIndex;
				cursor = skipRawRouteSpaces(source, cursor);
				if (cursor + 1 < end && source.substr(cursor, 2) == '..') cursor += 2;
				continue;
			}
			var concatOperator = findLuaConcatOperator(source, cursor, end);
			var termEnd = concatOperator < 0 ? end : concatOperator;
			var term = StringTools.trim(source.substring(cursor, termEnd));
			if (term == '') return null;
			var converted = convertExpression(term, origin, diagnostics);
			terms.push(protectEmbeddedValue('luaString(' + converted + ')', true,
				source, protected, tokenCounter++));
			cursor = termEnd;
			if (concatOperator >= 0) cursor += 2;
		}
		if (!hasLiteral) return null;
		return terms.join(' + ');
	}

	static function findLuaConcatOperator(source:String, start:Int, end:Int):Int {
		var parens = 0;
		var brackets = 0;
		var braces = 0;
		var i = start;
		while (i + 1 < end) {
			var ch = source.charAt(i);
			if (ch == '"' || ch == "'") {
				i = skipLuaQuotedString(source, i);
				continue;
			}
			if (source.substr(i, 2) == '[[') {
				var close = source.indexOf(']]', i + 2);
				if (close < 0 || close >= end) return -1;
				i = close + 2;
				continue;
			}
			switch (ch) {
				case '(': parens++;
				case ')': if (parens > 0) parens--;
				case '[': brackets++;
				case ']': if (brackets > 0) brackets--;
				case '{': braces++;
				case '}': if (braces > 0) braces--;
				case '.':
					if (parens == 0 && brackets == 0 && braces == 0
						&& source.charAt(i + 1) == '.') return i;
				default:
			}
			i++;
		}
		return -1;
	}

	static function readEmbeddedLuaString(source:String, start:Int, end:Int):Null<{value:String, endIndex:Int}> {
		var quote = source.charAt(start);
		var value = new StringBuf();
		var i = start + 1;
		while (i < end) {
			var ch = source.charAt(i);
			if (ch == quote) return {value:value.toString(), endIndex:i + 1};
			if (ch == '\\') {
				i++;
				if (i >= end) return null;
				var escaped = source.charAt(i);
				switch (escaped) {
					case 'n': value.add('\n');
					case 'r': value.add('\r');
					case 't': value.add('\t');
					case '\\': value.add('\\');
					case '"': value.add('"');
					case "'": value.add("'");
					default: value.add(escaped);
				}
			} else {
				value.add(ch);
			}
			i++;
		}
		return null;
	}

	static function protectEmbeddedValue(value:String, expression:Bool, source:String,
		protected:Array<{token:String, value:String, expression:Bool}>, id:Int):String {
		// Terms in an earlier runHaxeCode expression can consume non-consecutive
		// id values, so deriving this token from `id + protected.length` collides
		// when a later expression restarts its per-call id at zero. The array's
		// current length is already a unique monotonic token sequence.
		var token = '__sourceEmbeddedHaxe' + protected.length + '__';
		while (source.indexOf(token) >= 0 || Lambda.exists(protected, function(entry) return entry.token == token))
			token += '_';
		protected.push({token:token, value:value, expression:expression});
		return token;
	}

	static function quoteHaxeString(value:String):String {
		var out = new StringBuf();
		out.add('"');
		for (i in 0...value.length) {
			switch (value.charAt(i)) {
				case '"': out.add('\\"');
				case '\\': out.add('\\\\');
				case '\n': out.add('\\n');
				case '\r': out.add('\\r');
				case '\t': out.add('\\t');
				default: out.add(value.charAt(i));
			}
		}
		out.add('"');
		return out.toString();
	}

	/**
		Lower the common quoted Psych call that interpolates a Lua boolean into
		PlayState.instance.moveCamera(...). Only the complete two-string
		concatenation and a single identifier passed to tostring are accepted.
	*/
	static function rawQuotedMoveCameraCall(source:String, start:Int):Null<{endIndex:Int, replacement:String}> {
		var first = readRawQuotedString(source, start);
		if (first == null || StringTools.trim(first.value) != 'PlayState.instance.moveCamera(')
			return null;
		var cursor = skipRawRouteSpaces(source, first.endIndex);
		if (source.substr(cursor, 2) != '..') return null;
		cursor = skipRawRouteSpaces(source, cursor + 2);
		if (source.substr(cursor, 8) != 'tostring') return null;
		cursor = skipRawRouteSpaces(source, cursor + 8);
		if (cursor >= source.length || source.charAt(cursor) != '(') return null;
		cursor = skipRawRouteSpaces(source, cursor + 1);
		if (cursor >= source.length || !isIdentifierStart(source.charAt(cursor))) return null;
		var nameStart = cursor++;
		while (cursor < source.length && isWord(source.charAt(cursor))) cursor++;
		var booleanName = source.substr(nameStart, cursor - nameStart);
		cursor = skipRawRouteSpaces(source, cursor);
		if (cursor >= source.length || source.charAt(cursor) != ')') return null;
		cursor = skipRawRouteSpaces(source, cursor + 1);
		if (source.substr(cursor, 2) != '..') return null;
		var tail = readRawQuotedString(source, skipRawRouteSpaces(source, cursor + 2));
		if (tail == null || StringTools.trim(tail.value) != ');') return null;
		cursor = skipRawRouteSpaces(source, tail.endIndex);
		if (cursor >= source.length || source.charAt(cursor) != ')') return null;
		return {endIndex:cursor + 1, replacement:'currentPlayState.moveCamera(' + booleanName + ');'};
	}

	static function readRawQuotedString(source:String, start:Int):Null<{value:String, endIndex:Int}> {
		if (start >= source.length) return null;
		var quote = source.charAt(start);
		if (quote != '\'' && quote != '"') return null;
		var value = new StringBuf();
		var cursor = start + 1;
		while (cursor < source.length) {
			var character = source.charAt(cursor);
			if (character == '\\') return null;
			if (character == quote)
				return {value:value.toString(), endIndex:cursor + 1};
			value.add(character);
			cursor++;
		}
		return null;
	}

	static function skipRawRouteSpaces(source:String, cursor:Int):Int {
		while (cursor < source.length && isSpace(source.charAt(cursor))) cursor++;
		return cursor;
	}

	/**
		Find the final delimiter of a Psych long-string expression. Lua permits
		`]] .. value .. [[` inside runHaxeCode, so the first `]]` is not always
		the call's closing delimiter.
	*/
	static function findRunHaxeLongEnd(source:String, from:Int):Int {
		var search = from;
		while (search < source.length) {
			var end = source.indexOf(']]', search);
			if (end < 0)
				return -1;
			var cursor = end + 2;
			while (cursor < source.length && isSpace(source.charAt(cursor))) cursor++;
			if (cursor + 1 < source.length && source.substr(cursor, 2) == '..') {
				var open = source.indexOf('[[', cursor + 2);
				if (open >= 0) {
					search = open + 2;
					continue;
				}
			}
			return end;
		}
		return -1;
	}

	/**
		Dispatch only the small, structurally-recognisable native snippets used
		by the mounted Psych corpus.  This is intentionally a whitelist: a
		`runHaxeCode` block which merely contains one known call is not enough to
		route the block, because silently dropping the rest would change a chart's
		behaviour while pretending it was supported.
	*/
	static function rawKnownHaxeRoute(body:String):Null<String> {
		var replacement = rawDualCameraRuntimeShaderRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawRuntimeShaderStorageRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawStoredShaderFilterRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawShaderCoordFixInstallRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawShaderCoordFixRemoveRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawShaderFilterRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawRuntimeShaderRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawColorTransformRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawCharacterColorRoute(body);
		if (replacement != null)
			return replacement;
		replacement = rawStrumRgbRoute(body);
		if (replacement != null)
			return replacement;
		return rawCameraAngleRoute(body);
	}

	/**
		Route the complete two-camera TV CRT shader setup used by Psych donors.
		Every Haxe statement must match this shape, so unrelated runHaxeCode remains
		behind the normal diagnostic boundary.
	*/
	static function rawDualCameraRuntimeShaderRoute(body:String):Null<String> {
		if (body == null || body.indexOf('createRuntimeShader') < 0
			|| body.indexOf('camGame.setFilters') < 0 || body.indexOf('camHUD.setFilters') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var cursor = 0;
		var initializer = new EReg('^var([A-Za-z_][A-Za-z0-9_]*)="\\]\\] *\\.\\. *([A-Za-z_][A-Za-z0-9_]*) *\\.\\. *\\[\\[";', '');
		if (!initializer.match(clean))
			return null;
		var shaderName = initializer.matched(2);
		cursor = initializer.matchedPos().len;
		var init = 'game.initLuaShader(' + shaderName + ');';
		if (clean.substr(cursor, init.length) != init)
			return null;
		cursor += init.length;
		var create = new EReg('^var([A-Za-z_][A-Za-z0-9_]*)=game\\.createRuntimeShader\\(([A-Za-z_][A-Za-z0-9_]*)\\);', '');
		if (!create.match(clean.substr(cursor)) || create.matched(2) != shaderName)
			return null;
		var shaderVariable = create.matched(1);
		cursor += create.matchedPos().len;
		var gameFilters = 'game.camGame.setFilters([newShaderFilter(' + shaderVariable + ')]);';
		if (clean.substr(cursor, gameFilters.length) != gameFilters)
			return null;
		cursor += gameFilters.length;
		var spriteShader = new EReg('^game\\.getLuaObject\\((["\\\'])([^"\\\']+)\\1\\)\\.shader=([A-Za-z_][A-Za-z0-9_]*);', '');
		if (!spriteShader.match(clean.substr(cursor)) || spriteShader.matched(3) != shaderVariable)
			return null;
		var quote = spriteShader.matched(1);
		var tag = spriteShader.matched(2);
		cursor += spriteShader.matchedPos().len;
		var hudFilters = 'game.camHUD.setFilters([newShaderFilter(game.getLuaObject('
			+ quote + tag + quote + ').shader)]);';
		if (clean.substr(cursor, hudFilters.length) != hudFilters)
			return null;
		cursor += hudFilters.length;
		if (clean.substr(cursor) == 'return;')
			cursor += 'return;'.length;
		if (cursor != clean.length)
			return null;
		var safeTag = escapeHscriptString(tag);
		return 'createRuntimeShaderAndStore("' + safeTag + '", ' + shaderName
			+ ', "__psychRunHaxeShader0"); '
			+ 'setCameraShaderFiltersFromStored("camGame", "__psychRunHaxeShader0"); '
			+ 'setCameraShaderFiltersFromStored("camHUD", "__psychRunHaxeShader0");';
	}

	/**
		Route Reverse Glitch's complete runtime-shader setup block.  The donor
		uses Haxe to interpolate a Lua identifier, create a runtime shader, attach
		it to the named Lua sprite, and keep it in the interpreter variable table.
		All four operations are required for a match: a partial match would make a
		converted script look supported while silently losing shader state.
	*/
	static function rawRuntimeShaderStorageRoute(body:String):Null<String> {
		if (body == null || body.indexOf('createRuntimeShader') < 0 || body.indexOf('variables.set') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var matcher = new EReg('^var([A-Za-z_][A-Za-z0-9_]*)="\\]\\] *\\.\\. *([A-Za-z_][A-Za-z0-9_]*) *\\.\\. *\\[\\[";game\\.initLuaShader\\(\\1\\);var([A-Za-z_][A-Za-z0-9_]*)=game\\.createRuntimeShader\\(\\1\\);game\\.getLuaObject\\((["\\\'])([^"\\\']+)\\4\\)\\.shader=\\3;game\\.variables\\.set\\((["\\\'])([^"\\\']+)\\6,\\3\\);$', '');
		if (!matcher.match(clean))
			return null;
		var spriteTag = StringTools.replace(matcher.matched(5), '"', '\\"');
		var variableName = StringTools.replace(matcher.matched(7), '"', '\\"');
		return 'createRuntimeShaderAndStore("' + spriteTag + '", ' + matcher.matched(2)
			+ ', "' + variableName + '");';
	}

	/** Route a complete stored-shader lookup/filter assignment. */
	static function rawStoredShaderFilterRoute(body:String):Null<String> {
		if (body == null || body.indexOf('variables.get') < 0 || body.indexOf('setFilters') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var matcher = new EReg('^var([A-Za-z_][A-Za-z0-9_]*)=game\\.variables\\.get\\((["\\\'])([^"\\\']+)\\2\\);game\\.(camGame|camHUD|camOther)\\.setFilters\\(\\[newShaderFilter\\(\\1\\)\\]\\);$', '');
		if (!matcher.match(clean))
			return null;
		var variableName = StringTools.replace(matcher.matched(3), '"', '\\"');
		return 'setCameraShaderFiltersFromStored("' + matcher.matched(4) + '", "' + variableName + '");';
	}

	/**
		Route Reverse Glitch's full resize-cache workaround.  The donor closure
		clears both OpenFL filter caches for all three Psych cameras, installs the
		resize callback, and performs the first reset immediately.  The native
		adapter owns that callback so HScript never receives arbitrary closures or
		private DisplayObject access.
	*/
	static function rawShaderCoordFixInstallRoute(body:String):Null<String> {
		if (body == null || body.indexOf('gameResized.add') < 0 || body.indexOf('__cacheBitmap') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var expected = 'resetCamCache=function(?spr){if(spr==null||spr.filters==null)return;spr.__cacheBitmap=null;spr.__cacheBitmapData=null;}'
			+ 'fixShaderCoordFix=function(?_){resetCamCache(game.camGame.flashSprite);resetCamCache(game.camHUD.flashSprite);'
			+ 'resetCamCache(game.camOther.flashSprite);}FlxG.signals.gameResized.add(fixShaderCoordFix);fixShaderCoordFix();';
		if (clean != expected && clean != expected + 'return;')
			return null;
		return 'installShaderCoordFix();';
	}

	/** Route only the named Reverse Glitch resize callback removal. */
	static function rawShaderCoordFixRemoveRoute(body:String):Null<String> {
		if (body == null)
			return null;
		var clean = compactRawHaxe(body);
		if (clean != 'FlxG.signals.gameResized.remove(fixShaderCoordFix);'
			&& clean != 'FlxG.signals.gameResized.remove(fixShaderCoordFix);return;')
			return null;
		return 'removeShaderCoordFix();';
	}

	static function rawShaderFilterRoute(body:String):Null<String> {
		if (body == null || body.indexOf('setFilters') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var camera = rawShaderCamera(clean);
		if (camera == null)
			return null;
		var filtersStart = clean.indexOf('setFilters([');
		if (filtersStart < 0)
			return null;
		var listStart = filtersStart + 'setFilters('.length;
		var listEnd = matchingDelimiter(clean, listStart, '[', ']');
		if (listEnd < 0)
			return null;
		var suffix = clean.substr(listEnd + 1);
		if (suffix != ');' && suffix != ';' && suffix != ')')
			return null;
		var bodyList = StringTools.trim(clean.substr(listStart + 1, listEnd - listStart - 1));
		if (bodyList == '')
			return 'clearCameraShaderFilters("' + camera + '");';
		var tags:Array<String> = [];
		for (entryRaw in splitTopLevel(bodyList, ',')) {
			var entry = StringTools.trim(entryRaw);
			var matcher = new EReg('^newShaderFilter\\(game\\.getLuaObject\\(["\\\']([^"\\\']+)["\\\']\\)\\.shader\\)$', '');
			if (!matcher.match(entry))
				return null;
			var tag = matcher.matched(1);
			if (tags.indexOf(tag) < 0)
				tags.push(tag);
		}
		if (tags.length == 0)
			return null;
		var quoted:Array<String> = [];
		for (tag in tags)
			quoted.push('"' + StringTools.replace(tag, '"', '\\"') + '"');
		return 'setCameraShaderFilters("' + camera + '", [' + quoted.join(', ') + ']);';
	}

	/** Route a runtime shader plus its numeric uniforms and camera filters. */
	static function rawRuntimeShaderRoute(body:String):Null<String> {
		if (body == null || body.indexOf('createRuntimeShader') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var create = new EReg('^var([A-Za-z_][A-Za-z0-9_]*)=game\\.createRuntimeShader\\((["\\\'])([^"\\\']+)\\2\\);', '');
		if (!create.match(clean))
			return null;
		var shaderVariable = create.matched(1);
		var shaderName = create.matched(3);
		var cursor = create.matchedPos().len;
		var uniforms:Array<String> = [];
		while (cursor < clean.length && clean.substr(cursor, 1) != 'g') {
			var uniform = new EReg('^' + shaderVariable + '\\.setFloat\\((["\\\'])([^"\\\']+)\\1,(-?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+))\\);', '');
			var remaining = clean.substr(cursor);
			if (!uniform.match(remaining))
				return null;
			// Use an array of key/value pairs instead of an anonymous object: the
			// Lua table pass intentionally rewrites `{key = value}` literals, while
			// this generated call is already HScript.
			uniforms.push('"' + StringTools.replace(uniform.matched(2), '"', '\\"') + '", ' + uniform.matched(3));
			cursor += uniform.matchedPos().len;
		}
		var filterPrefix = clean.substr(cursor);
		var camera = rawShaderCamera(filterPrefix);
		if (camera == null)
			return null;
		var filtersStart = filterPrefix.indexOf('setFilters([');
		var listStart = filtersStart + 'setFilters('.length;
		var listEnd = matchingDelimiter(filterPrefix, listStart, '[', ']');
		if (filtersStart < 0 || listEnd < 0)
			return null;
		if (filterPrefix.substr(listEnd + 1) != ');' && filterPrefix.substr(listEnd + 1) != ';'
			&& filterPrefix.substr(listEnd + 1) != ')')
			return null;
		var bodyList = StringTools.trim(filterPrefix.substr(listStart + 1, listEnd - listStart - 1));
		var tags:Array<String> = [];
		var runtimeCount = 0;
		for (entryRaw in splitTopLevel(bodyList, ',')) {
			var entry = StringTools.trim(entryRaw);
			var tagMatcher = new EReg('^newShaderFilter\\(game\\.getLuaObject\\(["\\\']([^"\\\']+)["\\\']\\)\\.shader\\)$', '');
			if (tagMatcher.match(entry)) {
				var tag = tagMatcher.matched(1);
				if (tags.indexOf(tag) < 0)
					tags.push(tag);
				continue;
			}
			if (entry == 'newShaderFilter(' + shaderVariable + ')') {
				runtimeCount++;
				continue;
			}
			return null;
		}
		if (runtimeCount != 1)
			return null;
		var quoted:Array<String> = [];
		for (tag in tags)
			quoted.push('"' + StringTools.replace(tag, '"', '\\"') + '"');
		var options = uniforms.length == 0 ? '[]' : '[' + uniforms.join(', ') + ']';
		return 'setCameraShaderFilters("' + camera + '", [' + quoted.join(', ') + '], "'
			+ StringTools.replace(shaderName, '"', '\\"') + '", ' + options + ');';
	}

	/** Route the dynamic Character color-transform snippets used by donor Lua. */
	static function rawCharacterColorRoute(body:String):Null<String> {
		if (body == null || body.indexOf('colorTransform') < 0 || body.indexOf('game.]]') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var tween = new EReg('^varc=game\\.\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[;if\\(c!=null\\)\\{varcolorNum=0x\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[;varr=\\(colorNum>>16\\)&0xFF;varg=\\(colorNum>>8\\)&0xFF;varb=colorNum&0xFF;FlxTween\\.tween\\(c\\.colorTransform,\\{redMultiplier:0,greenMultiplier:0,blueMultiplier:0,redOffset:r,greenOffset:g,blueOffset:b\\},\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[,\\{ease:FlxEase\\.linear\\}\\);c\\.visible=true;c\\.alpha=1;\\}$', '');
		if (tween.match(clean))
			return 'tweenCharacterColorHex(' + tween.matched(1) + ', ' + tween.matched(2) + ', ' + tween.matched(3) + ');';
		var reset = new EReg('^varc=game\\.\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[;if\\(c!=null\\)\\{FlxTween\\.tween\\(c\\.colorTransform,\\{redMultiplier:1,greenMultiplier:1,blueMultiplier:1,redOffset:0,greenOffset:0,blueOffset:0\\},\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[,\\{ease:FlxEase\\.linear\\}\\);\\}$', '');
		if (reset.match(clean))
			return 'resetCharacterColor(' + reset.matched(1) + ', ' + reset.matched(2) + ');';
		return null;
	}

	/** Parse one or more fixed colorTransform tween calls with Lua templates. */
	static function rawColorTransformRoute(body:String):Null<String> {
		if (body == null || body.indexOf('FlxTween.tween(game.') < 0)
			return null;
		var cursor = 0;
		var output:Array<String> = [];
		var clean = stripRawHaxeComments(body);
		while (true) {
			while (cursor < clean.length && isSpace(clean.charAt(cursor))) cursor++;
			if (cursor >= clean.length)
				break;
			var prefix = 'FlxTween.tween(game.';
			if (clean.substr(cursor, prefix.length) != prefix)
				return null;
			cursor += prefix.length;
			var actorEnd = clean.indexOf('.colorTransform', cursor);
			if (actorEnd < 0)
				return null;
			var actor = clean.substr(cursor, actorEnd - cursor);
			if (actor != 'boyfriend' && actor != 'dad' && actor != 'gf')
				return null;
			cursor = actorEnd + '.colorTransform'.length;
			while (cursor < clean.length && isSpace(clean.charAt(cursor))) cursor++;
			if (cursor >= clean.length || clean.charAt(cursor) != ',') return null;
			cursor++;
			while (cursor < clean.length && isSpace(clean.charAt(cursor))) cursor++;
			if (cursor >= clean.length || clean.charAt(cursor) != '{') return null;
			var objectEnd = matchingDelimiter(clean, cursor, '{', '}');
			if (objectEnd < 0) return null;
			var fields = new Map<String, String>();
			for (fieldRaw in splitTopLevel(clean.substr(cursor + 1, objectEnd - cursor - 1), ',')) {
				var field = StringTools.trim(fieldRaw);
				var colon = field.indexOf(':');
				if (colon < 0) return null;
				var key = StringTools.trim(field.substr(0, colon));
				var value = StringTools.trim(field.substr(colon + 1));
				if (fields.exists(key)) return null;
				fields.set(key, value);
			}
			for (key in ['redOffset', 'greenOffset', 'blueOffset', 'redMultiplier', 'greenMultiplier', 'blueMultiplier'])
				if (!fields.exists(key)) return null;
			cursor = objectEnd + 1;
			while (cursor < clean.length && isSpace(clean.charAt(cursor))) cursor++;
			if (cursor >= clean.length || clean.charAt(cursor) != ',') return null;
			cursor++;
			var durationEnd = clean.indexOf(')', cursor);
			if (durationEnd < 0) return null;
			var duration = luaTemplateValue(clean.substr(cursor, durationEnd - cursor));
			if (duration == null) return null;
			cursor = durationEnd + 1;
			while (cursor < clean.length && isSpace(clean.charAt(cursor))) cursor++;
			if (cursor >= clean.length || clean.charAt(cursor) != ';') return null;
			cursor++;
			var red = luaTemplateValue(fields.get('redOffset'));
			var green = luaTemplateValue(fields.get('greenOffset'));
			var blue = luaTemplateValue(fields.get('blueOffset'));
			var redMult = StringTools.trim(fields.get('redMultiplier'));
			var greenMult = StringTools.trim(fields.get('greenMultiplier'));
			var blueMult = StringTools.trim(fields.get('blueMultiplier'));
			if (red == null || green == null || blue == null
				|| (redMult != '0' && redMult != '1') || redMult != greenMult || redMult != blueMult)
				return null;
			var reset = redMult == '1';
			output.push('tweenCharacterColorRGB("' + actor + '", ' + luaIndexValue(red) + ', '
				+ luaIndexValue(green) + ', ' + luaIndexValue(blue) + ', ' + duration + ', ' + reset + ');');
		}
		return output.length == 0 ? null : output.join(' ');
	}

	static function rawStrumRgbRoute(body:String):Null<String> {
		if (body == null || body.indexOf('useRGBShader') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var matcher = new EReg('^for\\(([A-Za-z_][A-Za-z0-9_]*)in0\\.\\.\\.game\\.strumLineNotes\\.length\\)\\{game\\.strumLineNotes\\.members\\[\\1\\]\\.useRGBShader=(true|false);\\}$', '');
		if (!matcher.match(clean))
			return null;
		return 'setStrumLineRGBShader(' + matcher.matched(2) + ');';
	}

	static function rawCameraAngleRoute(body:String):Null<String> {
		var parts = rawCameraAngleParts(body);
		if (parts == null || parts[1] != 'speed' || parts[2] != 'offsetX')
			return null;
		var elapsed = rawCameraAngleElapsed(parts[0]);
		if (elapsed == null)
			return null;
		return 'updateCameraAngle(' + elapsed + ', offsetX, speed);';
	}

	/**
		Return the callback-safe elapsed expression for the legacy camera-angle
		template.  Older Psych packs use both the callback parameter (`elapsed`)
		and short-lived globals (`el`); a common template typo uses `els` after
		assigning the actual callback parameter to `el`.  Keep that alias inside
		the native route so the importer can recover the intended frame delta
		without executing arbitrary interpolated Haxe or editing the donor script.
	*/
	static function rawCameraAngleElapsed(identifier:String):Null<String> {
		return switch (identifier) {
			case 'el' | 'elapsed': identifier;
			case 'els': 'elapsed';
			default: null;
		};
	}

	/**
		Return the identifiers in the one whitelisted Psych camera-angle
		runHaxeCode template.  Keeping this parser separate lets the masking pass
		distinguish a malformed near-match from arbitrary embedded Haxe.
	*/
	static function rawCameraAngleParts(body:String):Null<Array<String>> {
		if (body == null || body.indexOf('FlxMath.bound') < 0)
			return null;
		var clean = compactRawHaxe(body);
		var matcher = new EReg('^varangleLerp=FlxMath\\.bound\\(FlxMath\\.bound\\(\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[\\*2\\.4/0\\.4,0,1\\)\\*\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[\\*cameraSpeed\\*playbackRate,0,1\\);game\\.camGame\\.angle=FlxMath\\.lerp\\(game\\.camGame\\.angle,0\\+\\]\\]\\.\\.([A-Za-z_][A-Za-z0-9_]*)\\.\\.\\[\\[/30,angleLerp\\);$', '');
		if (!matcher.match(clean))
			return null;
		return [matcher.matched(1), matcher.matched(2), matcher.matched(3)];
	}

	/**
		Explain why a camera-angle near-match stayed blocked.  The source is
		still masked by maskRawHaxe(), so this diagnostic never grants arbitrary
		Haxe execution; it only makes a precise donor/runtime mismatch visible.
	*/
	static function rawCameraAngleDiagnostic(body:String, line:Int):Null<String> {
		var parts = rawCameraAngleParts(body);
		if (parts == null)
			return null;
		if (rawCameraAngleElapsed(parts[0]) != null
			&& parts[1] == 'speed' && parts[2] == 'offsetX')
			return null;
		var mismatches:Array<String> = [];
		if (rawCameraAngleElapsed(parts[0]) == null)
			mismatches.push('elapsed identifier "' + parts[0] + '" is not the callback-safe "el", "els", or "elapsed" value');
		if (parts[1] != 'speed')
			mismatches.push('speed identifier "' + parts[1] + '" is not the adapter-owned "speed" value');
		if (parts[2] != 'offsetX')
			mismatches.push('offset identifier "' + parts[2] + '" is not the adapter-owned "offsetX" value');
		return 'camera-angle runHaxeCode near-match at line ' + line + ' was disabled safely: '
			+ mismatches.join('; ') + '. The native route only accepts the proven Psych camera-angle template.';
	}

	static function rawShaderCamera(body:String):Null<String> {
		if (body.indexOf('game.camHUD.setFilters(') >= 0)
			return 'camHUD';
		if (body.indexOf('game.camGame.setFilters(') >= 0 || body.indexOf('FlxG.game.setFilters(') >= 0)
			return 'camGame';
		return null;
	}

	static function compactRawHaxe(body:String):String {
		var value = stripRawHaxeComments(body);
		var out = new StringBuf();
		var quote = '';
		for (i in 0...value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				out.add(c);
				if (c == quote && (i == 0 || value.charAt(i - 1) != '\\')) quote = '';
			} else if (c == '"' || c == "'") {
				quote = c;
				out.add(c);
			} else if (!isSpace(c)) {
				out.add(c);
			}
		}
		return out.toString();
	}

	static function stripRawHaxeComments(body:String):String {
		if (body == null) return '';
		var out = body.split('');
		var quote = '';
		var i = 0;
		while (i < body.length) {
			var c = body.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '/' && i + 1 < body.length && body.charAt(i + 1) == '/') {
				var end = body.indexOf('\n', i + 2);
				if (end < 0) end = body.length;
				for (p in i...end) if (out[p] != '\n' && out[p] != '\r') out[p] = ' ';
				i = end;
				continue;
			}
			i++;
		}
		return out.join('');
	}

	static function matchingDelimiter(source:String, start:Int, opening:String, closing:String):Int {
		var depth = 0;
		var quote = '';
		var i = start;
		while (i < source.length) {
			var c = source.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == opening) depth++;
			else if (c == closing) {
				depth--;
				if (depth == 0) return i;
			}
			i++;
		}
		return -1;
	}

	static function matchingOpenDelimiter(source:String, end:Int, opening:String, closing:String):Int {
		var opens:Array<Int> = [];
		var quote = '';
		var i = 0;
	while (i <= end && i < source.length) {
			var c = source.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == '\'') { quote = c; i++; continue; }
			if (c == opening)
				opens.push(i);
			else if (c == closing) {
				if (opens.length == 0)
					return -1;
				var match = opens.pop();
				if (i == end)
					return match;
			}
			i++;
		}
		return -1;
	}

	static function luaTemplateValue(value:String):Null<String> {
		if (value == null) return null;
		var text = StringTools.trim(value);
		if (text == '') return null;
		if (StringTools.startsWith(text, ']]..') && StringTools.endsWith(text, '..[['))
			return StringTools.trim(text.substr(4, text.length - 8));
		if (~/^-?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$/.match(text))
			return text;
		return null;
	}

	static function luaIndexValue(value:String):String {
		if (value == null) return null;
		var matcher = new EReg('^([A-Za-z_][A-Za-z0-9_]*)\\[([0-9]+)\\]$', '');
		if (matcher.match(value))
			return 'luaTableValue(' + matcher.matched(1) + ', ' + matcher.matched(2) + ')';
		return value;
	}

	/** Remove Lua comments while preserving newlines for useful diagnostics. */
	static function stripComments(source:String):String {
		var out = source.split('');
		var i = 0;
		var quote = '';
		while (i < source.length) {
			var c = source.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '-' && i + 1 < source.length && source.charAt(i + 1) == '-') {
				var long = i + 3 < source.length && source.substr(i + 2, 2) == '[[';
				var end = long ? source.indexOf(']]', i + 4) : source.indexOf('\n', i + 2);
				if (end < 0) end = source.length;
				var maskEnd = long && end < source.length ? end + 2 : end;
				for (p in i...maskEnd)
					if (out[p] != '\n' && out[p] != '\r') out[p] = ' ';
				i = maskEnd;
				continue;
			}
			i++;
		}
		return out.join('');
	}

	static function maskLongStrings(source:String, origin:String, diagnostics:Array<String>):String {
		var out = source.split('');
		var i = 0;
		while (i + 1 < source.length) {
			if (source.substr(i, 2) == '[[') {
				var end = source.indexOf(']]', i + 2);
				if (end >= 0) {
					addDiagnostic(diagnostics, origin, 'lua-long-string', 'Lua long strings are only supported inside runHaxeCode blocks.');
					for (p in i...end + 2)
						if (out[p] != '\n' && out[p] != '\r') out[p] = ' ';
					i = end + 2;
					continue;
				}
			}
			i++;
		}
		return out.join('');
	}

	/** Convert Lua table literals to HScript arrays or anonymous objects. */
	static function convertTables(source:String, origin:String, diagnostics:Array<String>):String {
		var out = new StringBuf();
		var i = 0;
		while (i < source.length) {
			var c = source.charAt(i);
			if (c == '"' || c == "'") {
				var quote = c;
				var start = i++;
				while (i < source.length) {
					if (source.charAt(i) == '\\') { i += 2; continue; }
					if (source.charAt(i) == quote) { i++; break; }
					i++;
				}
				out.add(source.substr(start, i - start));
				continue;
			}
			if (c == '{') {
				var close = matchingBrace(source, i);
				if (close < 0) {
					addDiagnostic(diagnostics, origin, 'lua-table', 'Unclosed Lua table literal.');
					out.add('{}');
					i++;
					continue;
				}
				var body = source.substr(i + 1, close - i - 1);
				out.add(formatTable(body, origin, diagnostics));
				i = close + 1;
				continue;
			}
			out.add(c);
			i++;
		}
		return out.toString();
	}

	static function formatTable(body:String, origin:String, diagnostics:Array<String>):String {
		var converted = convertTables(body, origin, diagnostics);
		var entries = splitTopLevel(converted, ',');
		var hasKey = false;
		var hasValue = false;
		var keyed:Array<String> = [];
		var orderedAssignments:Array<{key:String, value:String}> = [];
		var values:Array<String> = [];
		var needsLuaTable = false;
		var sequenceIndex = 1;
		for (entryRaw in entries) {
			var entry = StringTools.trim(entryRaw);
			if (entry == '') continue;
			var equal = topLevelEquals(entry);
			if (equal >= 0) {
				var key = StringTools.trim(entry.substr(0, equal));
				var value = StringTools.trim(entry.substr(equal + 1));
				if (~/^[A-Za-z_][A-Za-z0-9_]*$/.match(key)) {
					keyed.push(key + ': ' + value);
					orderedAssignments.push({key:quoteHaxeString(key), value:value});
					hasKey = true;
				} else if (key.length > 2 && key.charAt(0) == '[' && key.charAt(key.length - 1) == ']') {
					var bracketKey = StringTools.trim(key.substr(1, key.length - 2));
					var stringKey = literalStringValue(bracketKey);
					if (stringKey != null) {
						// Bracketed string fields are dynamic Lua keys even when the
						// spelling resembles an HScript property (notably "nil").
						needsLuaTable = true;
						orderedAssignments.push({key:quoteHaxeString(stringKey), value:value});
						hasKey = true;
					} else {
						addDiagnostic(diagnostics, origin, 'lua-table-key', 'Only identifier-shaped literal string keys are routed: ' + key);
						return '{}';
					}
				} else {
					addDiagnostic(diagnostics, origin, 'lua-table-key', 'Unsupported Lua table key: ' + key);
					return '{}';
				}
			} else {
				hasValue = true;
				values.push(entry);
				orderedAssignments.push({key:Std.string(sequenceIndex++), value:entry});
			}
		}
		if (hasKey && hasValue && !needsLuaTable) {
			addDiagnostic(diagnostics, origin, 'lua-table-mixed', 'Mixed keyed/array Lua tables are not routed.');
			return '{}';
		}
		if (needsLuaTable) {
			// Use the Lua-owned array sidecar for keys which cannot be represented
			// as HScript object fields. Assignments preserve arbitrary strings,
			// insertion order, one-based sequence entries, and nil-removal behavior.
			var tableName = '__luaCompatTable' + collectionCounter++;
			var statements:Array<String> = ['var ' + tableName + ' = [];'];
			for (entry in orderedAssignments)
				statements.push(tableName + '[' + entry.key + '] = ' + entry.value + ';');
			statements.push('return ' + tableName + ';');
			return '((function() { ' + statements.join(' ') + ' }))()';
		}
		if (hasKey)
			return '{' + keyed.join(', ') + '}';
		return '[' + values.join(', ') + ']';
	}

	static function matchingBrace(source:String, start:Int):Int {
		var depth = 0;
		var quote = '';
		var i = start;
		while (i < source.length) {
			var c = source.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '{') depth++;
			if (c == '}') {
				depth--;
				if (depth == 0) return i;
			}
			i++;
		}
		return -1;
	}

	static function splitTopLevel(value:String, delimiter:String):Array<String> {
		var result:Array<String> = [];
		var start = 0;
		var depth = 0;
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '(' || c == '[' || c == '{') depth++;
			if (c == ')' || c == ']' || c == '}') depth--;
			if (depth == 0 && c == delimiter) {
				result.push(value.substr(start, i - start));
				start = i + 1;
			}
			i++;
		}
		result.push(value.substr(start));
		return result;
	}

	/**
		Route a bare addLuaSprite layer identifier through the runtime optional
		read helper. The closure preserves callback locals and existing engine or
		script globals; the helper converts only a failed name lookup to Lua nil.
	*/
	static function routeOptionalAddLuaSpriteLayers(source:String):String {
		if (source == null || source.indexOf('addLuaSprite') < 0)
			return source;
		var out = new StringBuf();
		var cursor = 0;
		var i = 0;
		while (i < source.length) {
			var c = source.charAt(i);
			if (c == '"' || c == "'") {
				var quote = c;
				i++;
				while (i < source.length) {
					if (source.charAt(i) == '\\') {
						i += 2;
						continue;
					}
					if (source.charAt(i) == quote) {
						i++;
						break;
					}
					i++;
				}
				continue;
			}
			if (!isIdentifierStart(c)) {
				i++;
				continue;
			}
			var start = i++;
			while (i < source.length && isWord(source.charAt(i)))
				i++;
			var name = source.substr(start, i - start);
			if (name != 'addLuaSprite')
				continue;
			var previous = source.substr(0, start).trim();
			if (previous.endsWith('.') || previous.endsWith(':') || ~/\bfunction\s*$/.match(previous))
				continue;
			var open = i;
			while (open < source.length && isSpace(source.charAt(open)))
				open++;
			if (open >= source.length || source.charAt(open) != '(')
				continue;
			var close = matchingDelimiter(source, open, '(', ')');
			if (close < 0)
				break;
			var args = splitTopLevel(source.substr(open + 1, close - open - 1), ',');
			if (args.length < 2)
				continue;
			var layer = StringTools.trim(args[1]);
			if (!~/^[A-Za-z_][A-Za-z0-9_]*$/.match(layer) || layer == 'true' || layer == 'false' || layer == 'nil')
				continue;
			out.add(source.substr(cursor, start - cursor));
			args[1] = 'luaReadOptional(function() { return ' + layer + '; })';
			out.add('addLuaSprite(' + args.join(', ') + ')');
			cursor = close + 1;
			i = cursor;
		}
		if (cursor == 0)
			return source;
		out.add(source.substr(cursor));
		return out.toString();
	}

	static function topLevelEquals(value:String):Int {
		var depth = 0;
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\') { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (c == '(' || c == '[' || c == '{') depth++;
			if (c == ')' || c == ']' || c == '}') depth--;
			if (depth == 0 && c == '=') {
				if ((i > 0 && (value.charAt(i - 1) == '=' || value.charAt(i - 1) == '<' || value.charAt(i - 1) == '>'))
					|| (i + 1 < value.length && value.charAt(i + 1) == '=')) {
					i++;
					continue;
				}
				return i;
			}
			i++;
		}
		return -1;
	}

	static function containsOutsideStrings(value:String, needle:String):Bool {
		return indexOutsideStrings(value, needle, 0) >= 0;
	}

	static function indexOutsideStrings(value:String, needle:String, from:Int):Int {
		if (value == null || needle == null || needle == '')
			return -1;
		var quote = '';
		var i = from < 0 ? 0 : from;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				if (c == '\\' && i + 1 < value.length) { i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; i++; continue; }
			if (value.substr(i, needle.length) == needle)
				return i;
			i++;
		}
		return -1;
	}

	static function replaceOutsideStrings(value:String, from:String, to:String):String {
		var out = new StringBuf();
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				out.add(c);
				if (c == '\\' && i + 1 < value.length) { out.add(value.charAt(i + 1)); i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; out.add(c); i++; continue; }
			if (value.substr(i, from.length) == from) {
				out.add(to);
				i += from.length;
			} else {
				out.add(c);
				i++;
			}
		}
		return out.toString();
	}

	static function replaceWordOutsideStrings(value:String, from:String, to:String):String {
		var out = new StringBuf();
		var quote = '';
		var i = 0;
		while (i < value.length) {
			var c = value.charAt(i);
			if (quote != '') {
				out.add(c);
				if (c == '\\' && i + 1 < value.length) { out.add(value.charAt(i + 1)); i += 2; continue; }
				if (c == quote) quote = '';
				i++;
				continue;
			}
			if (c == '"' || c == "'") { quote = c; out.add(c); i++; continue; }
			if (value.substr(i, from.length) == from
				&& (i == 0 || !isWord(value.charAt(i - 1)))
				&& (i + from.length >= value.length || !isWord(value.charAt(i + from.length)))) {
				out.add(to);
				i += from.length;
			} else {
				out.add(c);
				i++;
			}
		}
		return out.toString();
	}

	static function isWord(value:String):Bool {
		if (value == null || value == '') return false;
		var code = value.charCodeAt(0);
		return (code >= 48 && code <= 57) || (code >= 65 && code <= 90)
			|| (code >= 97 && code <= 122) || value == '_';
	}

	static function isSpace(value:String):Bool {
		return value == ' ' || value == '\t' || value == '\r' || value == '\n';
	}
}
