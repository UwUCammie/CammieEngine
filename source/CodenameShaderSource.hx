package;

using StringTools;

/** Keep owner-authored GLSL intact on disk while accepting scalar expressions
 * that the donor shader path permits but OpenFL's GLSL 100 compiler rejects. */
class CodenameShaderSource {
	public static function forOpenFL(source:String, ?resolveImport:String->String):String {
		if (source == null) return null;
		source = expandImports(source, resolveImport, [], 0);
		return normalizeOpenFL(source);
	}

	/** Apply only source-level OpenFL GLSL type compatibility. The shared
	 * runtime shader constructor also calls this after loading native shader
	 * files, including call paths that do not have an owner-scoped importer. */
	public static function normalizeOpenFL(source:String):String {
		if (source == null) return null;
		source = requireOpenFLShaderVersion(source);
		// Preserve the existing declaration-context case: GLSL ES 1.00 rejects
		// an integer literal at the start of a float initializer expression.
		var leadingFloat = ~/^([ \t]*float[ \t]+[A-Za-z_][A-Za-z0-9_]*[ \t]*=[ \t]*)([0-9]+)([ \t]*[+\-][ \t]*[A-Za-z_][A-Za-z0-9_]*[ \t]*\()/gm;
		source = leadingFloat.map(source, function(match:EReg):String
			return match.matched(1) + match.matched(2) + '.0' + match.matched(3));
		var floatNames:Map<String, Bool> = [];
		var intNames:Map<String, Bool> = [];
		var intVectorNames:Map<String, Bool> = [];
		for (token in glslTokens(source)) {
			if (token.text == 'float' && tokenIndexIsIdentifier(token.next))
				floatNames.set(token.next.text, true);
			else if (token.text == 'int' && tokenIndexIsIdentifier(token.next))
				intNames.set(token.next.text, true);
			else if (StringTools.startsWith(token.text, 'ivec') && tokenIndexIsIdentifier(token.next))
				intVectorNames.set(token.next.text, true);
		}
		// GLSL ES 1.00 does not implicitly mix int and float operands. Promote
		// only the integer literal operand paired with a known float expression;
		// loop headers and array subscripts retain their integer types.
		source = promoteFloatExpressionLiterals(source, floatNames);
		// Some imported GLSL writes integral float literals in integer-coordinate
		// expressions (`x + 1.0`, `ivec2(x - 2.0, ...)`). Convert only when the
		// expression is being passed to a declared int parameter or an ivec
		// constructor and its adjacent operand is declared int/ivec. Fractional
		// shader math and expressions with float results stay untouched.
		source = promoteIntegerExpressionLiterals(source, intNames, intVectorNames);
		// Codename shaders can use an integer iterator against a float sample
		// count and multiply it by a float offset. Promote that iterator when its
		// bound is declared float; skip loops that index arrays, where the integer
		// type is essential.
		var floatBoundLoop = ~/for[ \t]*\([ \t]*int[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*([0-9]+)[ \t]*;[ \t]*\1[ \t]*<[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*;[ \t]*\1\+\+[ \t]*\)/g;
		return floatBoundLoop.map(source, function(match:EReg):String {
			var iterator = match.matched(1);
			var bound = match.matched(3);
			if (!floatNames.exists(bound)) return match.matched(0);
			var pos = match.matchedPos();
			var body = source.substr(pos.pos + pos.len);
			var end = body.indexOf('}');
			if (end >= 0) body = body.substr(0, end);
			if (new EReg('\\[[ \\t]*' + iterator + '[ \\t]*\\]', '').match(body))
				return match.matched(0);
			return 'for (float ' + iterator + ' = ' + match.matched(2) + '.0; '
				+ iterator + ' < ' + bound + '; ' + iterator + '++)';
		});
	}

	/** Raise the source to the minimum desktop GLSL version required by its
	 * language features. OpenFL's GL backend normally targets GLSL 1.00, while
	 * imported shaders can use later core built-ins and non-square matrices. */
	static function requireOpenFLShaderVersion(source:String):String {
		var required = 100;
		for (token in glslTokens(source)) {
			var next = token.next;
			if ((token.text == 'round' || token.text == 'roundEven' || token.text == 'isnan' || token.text == 'isinf')
				&& next != null && next.text == '(')
				required = 130;
			else if (token.text.length == 5 && StringTools.startsWith(token.text, 'mat')
				&& token.text.charAt(3) >= '2' && token.text.charAt(3) <= '4'
				&& token.text.charAt(4) == 'x')
				required = Std.int(Math.max(required, 120));
		}
		var gpuShader4Extension = ~/^[ \t]*#extension[ \t]+GL_EXT_gpu_shader4[ \t]*:[ \t]*(enable|require|warn)[ \t]*(?:\/\/.*)?[ \t]*\r?$/gm;
		if (gpuShader4Extension.match(source))
			required = 130;

		var lines = source.split('\n');
		var versionLine = -1;
		var version = 0;
		var versionPattern = ~/^#version[ \t]+([0-9]+)(.*)$/;
		for (i in 0...lines.length) {
			var line = StringTools.trim(lines[i]);
			if (versionPattern.match(line)) {
				versionLine = i;
				version = Std.parseInt(versionPattern.matched(1));
				break;
			}
		}

		if (versionLine < 0) {
			if (required > 100)
				source = '#version ' + required + '\n' + source;
		} else if (required > version) {
			var original = StringTools.trim(lines[versionLine]);
			versionPattern.match(original);
			var suffix = versionPattern.matched(2);
			// GLSL profiles were introduced after 1.30. Drop a profile qualifier
			// when raising an older directive, while preserving later qualifiers.
			if (required < 150 && (StringTools.startsWith(StringTools.trim(suffix), 'core')
				|| StringTools.startsWith(StringTools.trim(suffix), 'compatibility')))
				suffix = '';
			lines[versionLine] = '#version ' + required + suffix;
			source = lines.join('\n');
		}

		// These vendor extensions became core GLSL features by 1.30. Keeping their
		// declarations makes Mesa reject otherwise portable shader code.
		var obsoleteExtension = ~/^[ \t]*#extension[ \t]+GL_(?:NV_non_square_matrices|EXT_gpu_shader4)[ \t]*:[ \t]*(enable|require|warn)[ \t]*(?:\/\/.*)?[ \t]*\r?$/gm;
		source = obsoleteExtension.replace(source, '');
		return source;
	}

	static function tokenIndexIsIdentifier(token:Dynamic):Bool {
		return token != null && Reflect.field(token, 'kind') == 'identifier';
	}

	/** Token records keep offsets into the authored source so normalization can
	 * skip comments, strings, directives, loop headers, and array subscripts. */
	static function glslTokens(source:String):Array<Dynamic> {
		var tokens:Array<Dynamic> = [];
		var index = 0;
		var length = source.length;
		while (index < length) {
			var start = index;
			var code = source.charCodeAt(index);
			if (isWhitespace(code)) {
				index++;
				continue;
			}
			if (code == 47 && index + 1 < length) {
				var next = source.charCodeAt(index + 1);
				if (next == 47) {
					index += 2;
					while (index < length && source.charCodeAt(index) != 10 && source.charCodeAt(index) != 13)
						index++;
					continue;
				}
				if (next == 42) {
					index += 2;
					while (index + 1 < length && !(source.charCodeAt(index) == 42 && source.charCodeAt(index + 1) == 47))
						index++;
					index = index + 1 < length ? index + 2 : length;
					continue;
				}
			}
			if (code == 35 && atLineStart(source, index)) {
				index++;
				while (index < length && source.charCodeAt(index) != 10 && source.charCodeAt(index) != 13)
					index++;
				continue;
			}
			if (code == 34 || code == 39) {
				var quote = code;
				index++;
				while (index < length) {
					var stringCode = source.charCodeAt(index++);
					if (stringCode == 92 && index < length)
						index++;
					else if (stringCode == quote)
						break;
				}
				continue;
			}
			if (isIdentifierStart(code)) {
				index++;
				while (index < length && isIdentifierPart(source.charCodeAt(index)))
					index++;
				tokens.push({text:source.substring(start, index), start:start, end:index, kind:'identifier'});
				continue;
			}
			if (isDigit(code) || (code == 46 && index + 1 < length && isDigit(source.charCodeAt(index + 1)))) {
				index++;
				while (index < length) {
					var numberCode = source.charCodeAt(index);
					if (isIdentifierPart(numberCode) || numberCode == 46) {
						index++;
						continue;
					}
					if ((numberCode == 43 || numberCode == 45) && index > start) {
						var previous = source.charCodeAt(index - 1);
						if (previous == 69 || previous == 101 || previous == 80 || previous == 112) {
							index++;
						continue;
						}
					}
					break;
				}
				tokens.push({text:source.substring(start, index), start:start, end:index, kind:'number'});
				continue;
			}
			var two = index + 1 < length ? source.substr(index, 2) : '';
			if (['++', '--', '==', '!=', '<=', '>=', '&&', '||', '+=', '-=', '*=', '/=', '<<', '>>'].indexOf(two) >= 0) {
				index += 2;
				tokens.push({text:two, start:start, end:index, kind:'punctuation'});
			} else {
				index++;
				tokens.push({text:source.substring(start, index), start:start, end:index, kind:'punctuation'});
			}
		}
		for (i in 0...tokens.length)
			tokens[i].next = i + 1 < tokens.length ? tokens[i + 1] : null;
		return tokens;
	}

	static function promoteFloatExpressionLiterals(source:String, floatNames:Map<String, Bool>):String {
		var tokens = glslTokens(source);
		if (tokens.length == 0) return source;
		var excluded:Array<Bool> = [];
		for (_ in 0...tokens.length) excluded.push(false);
		var index = 0;
		while (index < tokens.length) {
			if (tokens[index].text == 'for' && index + 1 < tokens.length && tokens[index + 1].text == '(') {
				var depth = 0;
				var cursor = index + 1;
				while (cursor < tokens.length) {
					if (tokens[cursor].text == '(') depth++;
					else if (tokens[cursor].text == ')') {
						depth--;
						if (depth == 0) break;
					}
					excluded[cursor] = true;
					cursor++;
				}
				if (cursor < tokens.length) excluded[cursor] = true;
				index = cursor;
			}
			index++;
		}
		var bracketDepth = 0;
		for (i in 0...tokens.length) {
			if (tokens[i].text == '[') bracketDepth++;
			else if (tokens[i].text == ']') bracketDepth = bracketDepth > 0 ? bracketDepth - 1 : 0;
			if (bracketDepth > 0) excluded[i] = true;
		}
		var replacements:Array<Dynamic> = [];
		for (i in 0...tokens.length) {
			if (excluded[i] || tokens[i].kind != 'number' || !isIntegerLiteral(tokens[i].text)) continue;
			var wrappedStart = i;
			var wrappedEnd = i;
			while (wrappedStart > 0 && wrappedEnd + 1 < tokens.length
				&& tokens[wrappedStart - 1].text == '(' && matchingClose(tokens, wrappedStart - 1) == wrappedEnd + 1) {
				wrappedStart--;
				wrappedEnd++;
			}
			if (wrappedStart > 0 && (tokens[wrappedStart - 1].text == '+' || tokens[wrappedStart - 1].text == '-')
				&& isUnaryPosition(tokens, wrappedStart - 1, 0))
				wrappedStart--;
			var promotes = false;
			if (wrappedStart > 0 && isMixedTypeOperator(tokens[wrappedStart - 1].text)) {
				var leftStart = operandStart(tokens, wrappedStart - 2, 0);
				if (leftStart >= 0
					&& shaderOperandType(tokens, leftStart, wrappedStart - 2, floatNames) == 'float')
					promotes = true;
			}
			if (!promotes && wrappedEnd + 1 < tokens.length
				&& isMixedTypeOperator(tokens[wrappedEnd + 1].text)) {
				var rightEnd = operandEnd(tokens, wrappedEnd + 2, tokens.length - 1);
				if (rightEnd >= wrappedEnd + 2
					&& shaderOperandType(tokens, wrappedEnd + 2, rightEnd, floatNames) == 'float')
					promotes = true;
			}
			if (promotes)
				replacements.push({start:tokens[i].start, end:tokens[i].end, text:tokens[i].text + '.0'});
		}
		if (replacements.length == 0) return source;
		replacements.reverse();
		for (replacement in replacements)
			source = source.substring(0, replacement.start) + replacement.text + source.substr(replacement.end);
		return source;
	}

	static function promoteIntegerExpressionLiterals(source:String, intNames:Map<String, Bool>,
		intVectorNames:Map<String, Bool>):String {
		var tokens = glslTokens(source);
		if (tokens.length == 0) return source;
		var intParameters = integerFunctionParameters(tokens);
		var replacements:Array<Dynamic> = [];
		for (i in 0...tokens.length) {
			if (tokens[i].kind != 'number' || !isWholeFloatLiteral(tokens[i].text)
				|| !isIntegerArgument(tokens, i, intParameters)) continue;
			var wrappedStart = i;
			var wrappedEnd = i;
			while (wrappedStart > 0 && wrappedEnd + 1 < tokens.length
				&& tokens[wrappedStart - 1].text == '(' && matchingClose(tokens, wrappedStart - 1) == wrappedEnd + 1) {
				wrappedStart--;
				wrappedEnd++;
			}
			if (wrappedStart > 0 && (tokens[wrappedStart - 1].text == '+' || tokens[wrappedStart - 1].text == '-')
				&& isUnaryPosition(tokens, wrappedStart - 1, 0))
				wrappedStart--;
			var promotes = false;
			if (wrappedStart > 0 && isMixedTypeOperator(tokens[wrappedStart - 1].text)) {
				var leftStart = operandStart(tokens, wrappedStart - 2, 0);
				if (leftStart >= 0 && integerOperand(tokens, leftStart, wrappedStart - 2, intNames, intVectorNames))
					promotes = true;
			}
			if (!promotes && wrappedEnd + 1 < tokens.length
				&& isMixedTypeOperator(tokens[wrappedEnd + 1].text)) {
				var rightEnd = operandEnd(tokens, wrappedEnd + 2, tokens.length - 1);
				if (rightEnd >= wrappedEnd + 2
					&& integerOperand(tokens, wrappedEnd + 2, rightEnd, intNames, intVectorNames))
					promotes = true;
			}
			if (promotes)
				replacements.push({start:tokens[i].start, end:tokens[i].end, text:wholeFloatAsInteger(tokens[i].text)});
		}
		if (replacements.length == 0) return source;
		replacements.reverse();
		for (replacement in replacements)
			source = source.substring(0, replacement.start) + replacement.text + source.substr(replacement.end);
		return source;
	}

	static function integerFunctionParameters(tokens:Array<Dynamic>):Map<String, Array<Bool>> {
		var result:Map<String, Array<Bool>> = [];
		for (nameIndex in 1...tokens.length - 1) {
			if (tokens[nameIndex].kind != 'identifier' || tokens[nameIndex + 1].text != '('
				|| !isShaderTypeName(tokens[nameIndex - 1].text)) continue;
			var open = nameIndex + 1;
			var close = matchingClose(tokens, open);
			if (close < 0 || close + 1 >= tokens.length
				|| (tokens[close + 1].text != '{' && tokens[close + 1].text != ';')) continue;
			var parameters:Array<Bool> = [];
			var segmentStart = open + 1;
			var depth = 0;
			for (cursor in open + 1...close + 1) {
				var isEnd = cursor == close;
				if (!isEnd && tokens[cursor].text == '(') depth++;
				else if (!isEnd && tokens[cursor].text == ')') depth--;
				if (isEnd || (tokens[cursor].text == ',' && depth == 0)) {
					if (segmentStart < cursor) {
					var typeIndex = segmentStart;
					while (typeIndex < cursor && ['const', 'in', 'out', 'inout', 'lowp', 'mediump', 'highp']
						.indexOf(tokens[typeIndex].text) >= 0)
						typeIndex++;
					var typeName = typeIndex < cursor ? tokens[typeIndex].text : '';
						parameters.push(typeName == 'int' || StringTools.startsWith(typeName, 'ivec'));
					}
					segmentStart = cursor + 1;
				}
			}
			result.set(tokens[nameIndex].text, parameters);
		}
		return result;
	}

	static function isIntegerArgument(tokens:Array<Dynamic>, position:Int,
		intParameters:Map<String, Array<Bool>>):Bool {
		var closestSpan = 0x3fffffff;
		var expectedInt = false;
		for (open in 1...position + 1) {
			if (tokens[open].text != '(') continue;
			var close = matchingClose(tokens, open);
			if (close <= position || tokens[open - 1].kind != 'identifier') continue;
			var callName:String = tokens[open - 1].text;
			var parameterIsInt = StringTools.startsWith(callName, 'ivec');
			var parameters = intParameters.get(callName);
			if (parameters == null && !parameterIsInt) continue;
			var argumentIndex = 0;
			var parenDepth = 0;
			var bracketDepth = 0;
			for (cursor in open + 1...position) {
				switch (tokens[cursor].text) {
					case '(': parenDepth++;
					case ')': if (parenDepth > 0) parenDepth--;
					case '[': bracketDepth++;
					case ']': if (bracketDepth > 0) bracketDepth--;
					case ',': if (parenDepth == 0 && bracketDepth == 0) argumentIndex++;
					default:
				}
			}
			if (parameterIsInt) {
				if (argumentIndex >= 2) continue;
			} else if (argumentIndex >= parameters.length || !parameters[argumentIndex]) continue;
			var span = close - open;
			if (span < closestSpan) {
				closestSpan = span;
				expectedInt = true;
			}
		}
		return expectedInt;
	}

	static function isShaderTypeName(name:String):Bool {
		return name == 'void' || name == 'float' || name == 'int' || name == 'uint' || name == 'bool'
			|| name.startsWith('vec') || name.startsWith('ivec') || name.startsWith('uvec')
			|| name.startsWith('bvec') || name.startsWith('mat') || name.startsWith('sampler');
	}

	static function integerOperand(tokens:Array<Dynamic>, start:Int, end:Int, intNames:Map<String, Bool>,
		intVectorNames:Map<String, Bool>):Bool {
		if (start < 0 || end < start || end >= tokens.length) return false;
		if (tokens[start].text == '(' && matchingClose(tokens, start) == end)
			return integerOperand(tokens, start + 1, end - 1, intNames, intVectorNames);
		if (start == end && tokens[start].kind == 'identifier'
			&& (intNames.exists(tokens[start].text) || intVectorNames.exists(tokens[start].text)))
			return true;
		// `operandStart` lands on the final swizzle token for `i.x`; the base
		// ivec declaration determines that the component is integer typed.
		if (start == end && tokens[start].kind == 'identifier' && start >= 2
			&& tokens[start - 1].text == '.' && tokens[start - 2].kind == 'identifier'
			&& intVectorNames.exists(tokens[start - 2].text))
			return true;
		if (tokens[start].text == 'int' && start + 1 <= end && tokens[start + 1].text == '('
			&& matchingClose(tokens, start + 1) == end)
			return true;
		if (tokens[start].kind == 'identifier' && StringTools.startsWith(tokens[start].text, 'ivec')
			&& start + 1 <= end && tokens[start + 1].text == '(' && matchingClose(tokens, start + 1) == end)
			return true;
		return false;
	}

	static function isWholeFloatLiteral(value:String):Bool {
		if (value == null || value == '') return false;
		var dot = value.indexOf('.');
		if (dot < 0) return false;
		var whole = value.substring(0, dot);
		var fraction = value.substr(dot + 1);
		for (i in 0...whole.length)
			if (!isDigit(whole.charCodeAt(i))) return false;
		if (fraction == '') return false;
		for (i in 0...fraction.length)
			if (fraction.charCodeAt(i) != 48) return false;
		return true;
	}

	static function wholeFloatAsInteger(value:String):String {
		var dot = value.indexOf('.');
		return dot == 0 ? '0' : value.substring(0, dot);
	}

	static function isMixedTypeOperator(text:String):Bool
		return ['+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>='].indexOf(text) >= 0;

	static function matchingClose(tokens:Array<Dynamic>, open:Int):Int {
		if (open < 0 || open >= tokens.length || tokens[open].text != '(') return -1;
		var depth = 0;
		for (index in open...tokens.length) {
			if (tokens[index].text == '(') depth++;
			else if (tokens[index].text == ')') {
				depth--;
				if (depth == 0) return index;
			}
		}
		return -1;
	}

	static function matchingOpen(tokens:Array<Dynamic>, close:Int, minimum:Int):Int {
		if (close < 0 || close >= tokens.length || tokens[close].text != ')') return -1;
		var depth = 0;
		var index = close;
		while (index >= minimum) {
			if (tokens[index].text == ')') depth++;
			else if (tokens[index].text == '(') {
				depth--;
				if (depth == 0) return index;
			}
			index--;
		}
		return -1;
	}

	static function operandStart(tokens:Array<Dynamic>, end:Int, minimum:Int):Int {
		if (end < minimum || end >= tokens.length) return -1;
		var start = end;
		if (tokens[end].text == ')') {
			var open = matchingOpen(tokens, end, minimum);
			if (open < 0) return -1;
			start = open;
			if (open > minimum && tokens[open - 1].kind == 'identifier') start = open - 1;
		} else if (tokens[end].text == ']') {
			var depth = 0;
			var cursor = end;
			while (cursor >= minimum) {
				if (tokens[cursor].text == ']') depth++;
				else if (tokens[cursor].text == '[') {
					depth--;
					if (depth == 0) {
						start = cursor > minimum ? cursor - 1 : cursor;
						break;
					}
				}
				cursor--;
			}
		}
		if (start > minimum && (tokens[start - 1].text == '+' || tokens[start - 1].text == '-')
			&& isUnaryPosition(tokens, start - 1, minimum))
			start--;
		return start;
	}

	static function operandEnd(tokens:Array<Dynamic>, start:Int, maximum:Int):Int {
		if (start < 0 || start > maximum || start >= tokens.length) return -1;
		var end = start;
		if (tokens[start].text == '(') {
			end = matchingClose(tokens, start);
			if (end < 0 || end > maximum) return -1;
		} else if (tokens[start].kind == 'identifier' && start + 1 <= maximum
			&& tokens[start + 1].text == '(') {
			end = matchingClose(tokens, start + 1);
			if (end < 0 || end > maximum) return -1;
		} else if (tokens[start].text == '+' || tokens[start].text == '-') {
			return operandEnd(tokens, start + 1, maximum);
		}
		if (end + 1 <= maximum && tokens[end + 1].text == '.') {
			end += 2;
			if (end > maximum) return -1;
		}
		return end;
	}

	static function isUnaryPosition(tokens:Array<Dynamic>, index:Int, minimum:Int):Bool {
		if (index <= minimum) return true;
		return ['(', '[', ',', '=', '+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=']
			.indexOf(tokens[index - 1].text) >= 0;
	}

	static function shaderOperandType(tokens:Array<Dynamic>, start:Int, end:Int,
		floatNames:Map<String, Bool>):String {
		if (start < 0 || end < start || end >= tokens.length) return '';
		if (tokens[start].text == '(' && matchingClose(tokens, start) == end)
			return shaderExpressionType(tokens, start + 1, end - 1, floatNames);
		if (tokens[start].kind == 'number' && start == end)
			return isIntegerLiteral(tokens[start].text) ? 'int' : 'float';
		if (tokens[start].kind == 'identifier') {
			var name:String = tokens[start].text;
			if (name == 'float') return 'float';
			if (name == 'int' || name == 'uint' || name == 'bool') return name == 'float' ? 'float' : 'int';
			if (floatNames.exists(name) || isFloatBuiltin(name)) return 'float';
			if (name.startsWith('vec') || name.startsWith('mat')) return 'vector';
		}
		return shaderExpressionType(tokens, start, end, floatNames);
	}

	static function shaderExpressionType(tokens:Array<Dynamic>, start:Int, end:Int,
		floatNames:Map<String, Bool>):String {
		if (start > end) return '';
		if (tokens[start].text == '(' && matchingClose(tokens, start) == end)
			return shaderExpressionType(tokens, start + 1, end - 1, floatNames);
		if (tokens[start].kind == 'number' && start == end)
			return isIntegerLiteral(tokens[start].text) ? 'int' : 'float';
		if (tokens[start].kind == 'identifier') {
			var name:String = tokens[start].text;
			if ((name == 'float' || name == 'int' || name == 'uint' || name == 'bool')
				&& start + 1 <= end && tokens[start + 1].text == '(')
				return name == 'float' ? 'float' : 'int';
			if (name.startsWith('vec') || name.startsWith('mat')) return 'vector';
			if (start + 1 <= end && tokens[start + 1].text == '(')
				return floatNames.exists(name) || isFloatBuiltin(name) ? 'float' : '';
			if (floatNames.exists(name)) return 'float';
		}
		for (index in start...(end + 1)) {
			if (tokens[index].kind == 'identifier' && floatNames.exists(tokens[index].text)) return 'float';
			if (tokens[index].kind == 'number' && !isIntegerLiteral(tokens[index].text)) return 'float';
		}
		return 'int';
	}

	static function isFloatBuiltin(name:String):Bool
		return ['sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'sinh', 'cosh', 'tanh', 'fract',
			'floor', 'ceil', 'round', 'trunc', 'sqrt', 'inversesqrt', 'abs', 'sign', 'mod',
			'min', 'max', 'clamp', 'mix', 'step', 'smoothstep', 'length', 'distance', 'dot']
			.indexOf(name) >= 0;

	static function isIntegerLiteral(value:String):Bool {
		if (value == null || value == '') return false;
		for (i in 0...value.length) {
			var code = value.charCodeAt(i);
			if (!isDigit(code)) return false;
		}
		return true;
	}

	static function atLineStart(source:String, index:Int):Bool {
		var cursor = index - 1;
		while (cursor >= 0 && source.charCodeAt(cursor) != 10 && source.charCodeAt(cursor) != 13) {
			if (!isWhitespace(source.charCodeAt(cursor))) return false;
			cursor--;
		}
		return true;
	}

	static function isWhitespace(code:Int):Bool return code == 32 || code == 9 || code == 10 || code == 13;
	static function isDigit(code:Int):Bool return code >= 48 && code <= 57;
	static function isIdentifierStart(code:Int):Bool
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || code == 95;
	static function isIdentifierPart(code:Int):Bool return isIdentifierStart(code) || isDigit(code);

	static function expandImports(source:String, resolveImport:String->String,
		active:Array<String>, depth:Int):String {
		if (depth > 32) throw '[codename-shader] Shader import recursion limit reached';
		var expression = new EReg('^[ \\t]*#import[ \\t]*<([^>\\r\\n]+)>[ \\t]*\\r?$', 'gm');
		var result = new StringBuf();
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 256 && expression.match(remaining)) {
			var position = expression.matchedPos();
			var key = StringTools.trim(expression.matched(1));
			if (key == '' || key.startsWith('/') || key.indexOf(':') >= 0 || key.indexOf('\\') >= 0)
				throw '[codename-shader] Invalid scoped shader import: ' + key;
			for (part in key.split('/'))
				if (part == '' || part == '.' || part == '..')
					throw '[codename-shader] Invalid scoped shader import: ' + key;
			if (active.indexOf(key) >= 0)
				throw '[codename-shader] Cyclic shader import: ' + active.concat([key]).join(' -> ');
			if (resolveImport == null)
				throw '[codename-shader] Shader import needs an owner-scoped resolver: ' + key;
			var imported = resolveImport(key);
			if (imported == null)
				throw '[codename-shader] Missing scoped shader import: ' + key;
			result.add(remaining.substring(0, position.pos));
			result.add(expandImports(imported, resolveImport, active.concat([key]), depth + 1));
			remaining = remaining.substr(position.pos + position.len);
		}
		if (expression.match(remaining))
			throw '[codename-shader] Shader import expansion limit reached';
		result.add(remaining);
		return result.toString();
	}
}
