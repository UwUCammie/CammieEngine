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
	public static function translate(source:String, ?origin:String):LuaCompatResult {
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

		var routed = routeKnownRawHaxe(source, name, diagnostics);
		var masked = maskRawHaxe(routed, name, diagnostics);
		masked = stripComments(masked);
		masked = maskLongStrings(masked, name, diagnostics);
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
			blocks.pop();
			output.push('}');
			addDiagnostic(diagnostics, name, 'lua-unclosed-block', 'Implicitly closed an unterminated Lua block.');
		}

		var generated = TRANSLATED_MARKER + '\n' + output.join('\n');
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

	static function translateLine(line:String, blocks:Array<String>, origin:String, diagnostics:Array<String>):Array<String> {
		var result:Array<String> = [];
		var text = StringTools.trim(line);
		if (text == '') {
			result.push('');
			return result;
		}

		// Lua permits a single statement after a block opener.  Expand the
		// common `if ... then return ... end` shape before handling braces.
		var oneLine = ~/^if\s+(.+)\s+then\s+(.+)\s+end\s*;?$/;
		if (oneLine.match(text)) {
			var condition = oneLine.matched(1);
			var body = oneLine.matched(2);
			result.push('if (' + convertExpression(condition, origin, diagnostics) + ') {');
			result.push(convertStatement(body, origin, diagnostics));
			result.push('}');
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
			result.push(functionAssignment(inlineName, inlineArgs, inlineBody));
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
			result.push(functionName.indexOf('.') >= 0
				? functionAssignment(functionName, args, null)
				: 'function ' + functionName + '(' + args + ') {');
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
		if (names.length <= 1)
			return null;
		var values = splitTopLevel(StringTools.trim(text.substr(equal + 1)), ',');
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
					if (word != '' && ['and', 'or', 'then', 'do', 'else', 'elseif'].indexOf(word) < 0) {
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
		if (StringTools.endsWith(tail, ' end') && !StringTools.startsWith(tail, 'if ')
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
		return body == null ? prefix : prefix + ' ' + body + ' }';
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
		if (body.indexOf('\\') >= 0)
			return null;
		return body;
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
			{from: 'math.tan', to: 'Math.tan'},
			{from: 'math.sqrt', to: 'Math.sqrt'},
			{from: 'math.exp', to: 'Math.exp'},
			{from: 'math.floor', to: 'Math.floor'},
			{from: 'math.ceil', to: 'Math.ceil'},
			{from: 'math.abs', to: 'Math.abs'},
			{from: 'math.min', to: 'Math.min'},
			{from: 'math.max', to: 'Math.max'},
			{from: 'math.pow', to: 'Math.pow'},
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
		if (text.indexOf('math.') >= 0) {
			addDiagnostic(diagnostics, origin, 'lua-math', 'Unsupported Lua math helper remains in expression: ' + text);
		}
		return text;
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
		var insert = ~/table\.insert\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*,\s*(.+)\)/g;
		text = insert.replace(text, '$1.push($2)');
		var remove = ~/table\.remove\s*\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s*,\s*(.+)\)/g;
		text = remove.replace(text, '$1.splice(($2) - 1, 1)');
		if (text.indexOf('table.') >= 0)
			addDiagnostic(diagnostics, origin, 'lua-table-library', 'Unsupported Lua table helper remains in expression: ' + text);
		return text;
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
			if (text.indexOf(entry.prefix) >= 0)
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
	static function routeKnownRawHaxe(source:String, origin:String, diagnostics:Array<String>):String {
		if (source == null || source.indexOf('runHaxeCode') < 0)
			return source;
		var output = new StringBuf();
		var cursor = 0;
		while (cursor < source.length) {
			var start = source.indexOf('runHaxeCode', cursor);
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
		var replacement = rawRuntimeShaderStorageRoute(body);
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
		if (clean != expected)
			return null;
		return 'installShaderCoordFix();';
	}

	/** Route only the named Reverse Glitch resize callback removal. */
	static function rawShaderCoordFixRemoveRoute(body:String):Null<String> {
		if (body == null || compactRawHaxe(body) != 'FlxG.signals.gameResized.remove(fixShaderCoordFix);')
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
		var values:Array<String> = [];
		for (entryRaw in entries) {
			var entry = StringTools.trim(entryRaw);
			if (entry == '') continue;
			var equal = topLevelEquals(entry);
			if (equal >= 0) {
				var key = StringTools.trim(entry.substr(0, equal));
				var value = StringTools.trim(entry.substr(equal + 1));
				if (~/^[A-Za-z_][A-Za-z0-9_]*$/.match(key)) {
					keyed.push(key + ': ' + value);
					hasKey = true;
				} else if (key.length > 2 && key.charAt(0) == '[' && key.charAt(key.length - 1) == ']') {
					keyed.push(key.substr(1, key.length - 2) + ': ' + value);
					hasKey = true;
				} else {
					addDiagnostic(diagnostics, origin, 'lua-table-key', 'Unsupported Lua table key: ' + key);
					return '{}';
				}
			} else {
				hasValue = true;
				values.push(entry);
			}
		}
		if (hasKey && hasValue) {
			addDiagnostic(diagnostics, origin, 'lua-table-mixed', 'Mixed keyed/array Lua tables are not routed.');
			return '{}';
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
