package;

using StringTools;

/**
	Conditional compilation for scripted classes (`#if`, `#elseif`, `#else`,
	`#end`), as Polymod evaluates it before parsing. Conditions support `!`,
	`&&`, `||`, parentheses, plain defines and comparisons against a define's
	value (`haxe >= "4.0.0"`).

	Inactive text and the directives themselves are blanked to spaces with
	every line break kept, so offsets and line numbers still point at the
	original source. Strings and comments are skipped while scanning, so a
	`#end` inside a string never closes a block.
*/
class HxcPreprocessor {
	static var cachedEngineDefines:Map<String, String>;

	/** The defines a scripted class sees in this build: a native desktop game. */
	public static function engineDefines():Map<String, String> {
		if (cachedEngineDefines != null)
			return cachedEngineDefines;
		var defines = new Map<String, String>();
		for (name in ['desktop', 'sys', 'cpp', 'hxcpp', 'haxe4', 'flixel', 'openfl', 'lime', 'polymod'])
			defines.set(name, '1');
		defines.set('haxe', '4.3.0');
		defines.set('haxe_ver', '4.3');
		// Library defines carry their version, and scripts compare against it
		// (`flixel >= "5.0.0"`), so hand them the versions this build really has.
		setVersion(defines, 'haxe', haxe.macro.Compiler.getDefine('haxe'));
		setVersion(defines, 'flixel', haxe.macro.Compiler.getDefine('flixel'));
		setVersion(defines, 'openfl', haxe.macro.Compiler.getDefine('openfl'));
		setVersion(defines, 'lime', haxe.macro.Compiler.getDefine('lime'));
		setVersion(defines, 'hxcpp', haxe.macro.Compiler.getDefine('hxcpp'));
		#if windows
		defines.set('windows', '1');
		#elseif mac
		defines.set('mac', '1');
		#elseif linux
		defines.set('linux', '1');
		#end
		return cachedEngineDefines = defines;
	}

	/** Keeps the fallback unless the build defines a dotted version for `name`. */
	static function setVersion(defines:Map<String, String>, name:String, value:String):Void {
		if (value != null && value.indexOf('.') > 0)
			defines.set(name, value);
	}

	/** Source with only the active branches left; null and directive-free text come back as they are. */
	public static function apply(source:String, ?defines:Map<String, String>):String {
		if (source == null || source.indexOf('#') < 0)
			return source;
		if (defines == null)
			defines = engineDefines();
		var output = new StringBuf();
		// Each frame: whether the enclosing block is live, whether a branch of
		// this block has already been taken, and whether the current branch is live.
		var parentLive:Array<Bool> = [];
		var taken:Array<Bool> = [];
		var live = true;
		var index = 0;
		var length = source.length;
		while (index < length) {
			var code = source.fastCodeAt(index);
			// Strings and comments are copied (or blanked) whole.
			var skipEnd = -1;
			if (code == '"'.code || code == "'".code)
				skipEnd = stringEnd(source, index);
			else if (code == '/'.code && index + 1 < length && source.fastCodeAt(index + 1) == '/'.code)
				skipEnd = lineEnd(source, index);
			else if (code == '/'.code && index + 1 < length && source.fastCodeAt(index + 1) == '*'.code) {
				var close = source.indexOf('*/', index + 2);
				skipEnd = close < 0 ? length : close + 2;
			}
			if (skipEnd > index) {
				emit(output, source, index, skipEnd, live);
				index = skipEnd;
				continue;
			}
			if (code == '#'.code && (index == 0 || !isIdentifierPart(source.fastCodeAt(index - 1)))) {
				var wordEnd = index + 1;
				while (wordEnd < length && isIdentifierPart(source.fastCodeAt(wordEnd)))
					wordEnd++;
				var word = source.substring(index + 1, wordEnd);
				switch (word) {
					case 'if' | 'elseif':
						var conditionEnd = conditionEnd(source, wordEnd);
						var condition = evaluate(source.substring(wordEnd, conditionEnd), defines);
						if (word == 'if') {
							parentLive.push(live);
							taken.push(live && condition);
							live = live && condition;
						} else if (parentLive.length > 0) {
							var parent = parentLive[parentLive.length - 1];
							var already = taken[taken.length - 1];
							live = parent && !already && condition;
							if (live)
								taken[taken.length - 1] = true;
						}
						emit(output, source, index, conditionEnd, false);
						index = conditionEnd;
						continue;
					case 'else':
						if (parentLive.length > 0) {
							var parent = parentLive[parentLive.length - 1];
							live = parent && !taken[taken.length - 1];
							taken[taken.length - 1] = true;
						}
						emit(output, source, index, wordEnd, false);
						index = wordEnd;
						continue;
					case 'end':
						if (parentLive.length > 0) {
							live = parentLive.pop();
							taken.pop();
						}
						emit(output, source, index, wordEnd, false);
						index = wordEnd;
						continue;
					default:
				}
			}
			emit(output, source, index, index + 1, live);
			index++;
		}
		return output.toString();
	}

	static function emit(output:StringBuf, source:String, start:Int, end:Int, live:Bool):Void {
		if (live) {
			output.addSub(source, start, end - start);
			return;
		}
		for (i in start...end) {
			var code = source.fastCodeAt(i);
			output.addChar(code == '\n'.code || code == '\r'.code ? code : ' '.code);
		}
	}

	static function stringEnd(source:String, start:Int):Int {
		var quote = source.fastCodeAt(start);
		var index = start + 1;
		while (index < source.length) {
			var code = source.fastCodeAt(index);
			if (code == '\\'.code) {
				index += 2;
				continue;
			}
			index++;
			if (code == quote)
				break;
		}
		return index > source.length ? source.length : index;
	}

	static function lineEnd(source:String, start:Int):Int {
		var index = start;
		while (index < source.length && source.fastCodeAt(index) != '\n'.code)
			index++;
		return index;
	}

	/** End of an `#if` condition: a balanced parenthesised expression, or `!`* and one define name. */
	static function conditionEnd(source:String, start:Int):Int {
		var index = start;
		while (index < source.length && (source.fastCodeAt(index) == ' '.code || source.fastCodeAt(index) == '\t'.code))
			index++;
		while (index < source.length && source.fastCodeAt(index) == '!'.code)
			index++;
		if (index < source.length && source.fastCodeAt(index) == '('.code) {
			var depth = 0;
			while (index < source.length) {
				var code = source.fastCodeAt(index);
				if (code == '"'.code || code == "'".code) {
					index = stringEnd(source, index);
					continue;
				}
				index++;
				if (code == '('.code)
					depth++;
				else if (code == ')'.code && --depth == 0)
					break;
			}
			return index;
		}
		while (index < source.length && (isIdentifierPart(source.fastCodeAt(index)) || source.fastCodeAt(index) == '.'.code))
			index++;
		return index;
	}

	/** Evaluate one condition; anything malformed is false. */
	public static function evaluate(condition:String, ?defines:Map<String, String>):Bool {
		if (defines == null)
			defines = engineDefines();
		var tokens = tokenize(condition == null ? '' : condition);
		var position = [0];
		var value = parseOr(tokens, position, defines);
		return value != null && position[0] == tokens.length && truthy(value);
	}

	static function tokenize(text:String):Array<String> {
		var tokens:Array<String> = [];
		var index = 0;
		while (index < text.length) {
			var code = text.fastCodeAt(index);
			if (code == ' '.code || code == '\t'.code || code == '\r'.code || code == '\n'.code) {
				index++;
				continue;
			}
			var two = text.substr(index, 2);
			if (two == '&&' || two == '||' || two == '>=' || two == '<=' || two == '==' || two == '!=') {
				tokens.push(two);
				index += 2;
			} else if (code == '"'.code || code == "'".code) {
				var end = stringEnd(text, index);
				tokens.push('"' + text.substring(index + 1, end - 1));
				index = end;
			} else if (isIdentifierPart(code) || code == '.'.code) {
				var start = index;
				while (index < text.length && (isIdentifierPart(text.fastCodeAt(index)) || text.fastCodeAt(index) == '.'.code))
					index++;
				tokens.push(text.substring(start, index));
			} else {
				tokens.push(text.charAt(index));
				index++;
			}
		}
		return tokens;
	}

	// Values are strings: a define's value, a literal ('"' prefixed in tokens),
	// or '' for an undefined name. Booleans from operators are '1' or ''.
	static function parseOr(tokens:Array<String>, position:Array<Int>, defines:Map<String, String>):Null<String> {
		var left = parseAnd(tokens, position, defines);
		while (left != null && position[0] < tokens.length && tokens[position[0]] == '||') {
			position[0]++;
			var right = parseAnd(tokens, position, defines);
			if (right == null)
				return null;
			left = truthy(left) || truthy(right) ? '1' : '';
		}
		return left;
	}

	static function parseAnd(tokens:Array<String>, position:Array<Int>, defines:Map<String, String>):Null<String> {
		var left = parseCompare(tokens, position, defines);
		while (left != null && position[0] < tokens.length && tokens[position[0]] == '&&') {
			position[0]++;
			var right = parseCompare(tokens, position, defines);
			if (right == null)
				return null;
			left = truthy(left) && truthy(right) ? '1' : '';
		}
		return left;
	}

	static function parseCompare(tokens:Array<String>, position:Array<Int>, defines:Map<String, String>):Null<String> {
		var left = parseUnary(tokens, position, defines);
		if (left == null || position[0] >= tokens.length)
			return left;
		var op = tokens[position[0]];
		if (op != '==' && op != '!=' && op != '>=' && op != '<=' && op != '>' && op != '<')
			return left;
		position[0]++;
		var right = parseUnary(tokens, position, defines);
		if (right == null)
			return null;
		// An undefined name never satisfies a comparison.
		if (left == '' || right == '')
			return '';
		var order = compareValues(left, right);
		var result = switch (op) {
			case '==': order == 0;
			case '!=': order != 0;
			case '>=': order >= 0;
			case '<=': order <= 0;
			case '>': order > 0;
			default: order < 0;
		}
		return result ? '1' : '';
	}

	static function parseUnary(tokens:Array<String>, position:Array<Int>, defines:Map<String, String>):Null<String> {
		if (position[0] >= tokens.length)
			return null;
		var token = tokens[position[0]++];
		if (token == '!') {
			var inner = parseUnary(tokens, position, defines);
			return inner == null ? null : (truthy(inner) ? '' : '1');
		}
		if (token == '(') {
			var inner = parseOr(tokens, position, defines);
			if (inner == null || position[0] >= tokens.length || tokens[position[0]] != ')')
				return null;
			position[0]++;
			return inner;
		}
		if (token.startsWith('"'))
			return token.substr(1);
		if (token.length > 0 && (isIdentifierPart(token.fastCodeAt(0)) || token.fastCodeAt(0) == '.'.code)) {
			var first = token.fastCodeAt(0);
			if (first >= '0'.code && first <= '9'.code)
				return token;
			var value = defines.get(token);
			return value == null ? '' : value;
		}
		return null;
	}

	static function truthy(value:String):Bool
		return value != null && value != '' && value != '0' && value != 'false';

	/** Compare dotted version numbers part by part, falling back to text order. */
	static function compareValues(left:String, right:String):Int {
		var a = left.split('.');
		var b = right.split('.');
		var count = a.length > b.length ? a.length : b.length;
		for (i in 0...count) {
			var x = i < a.length ? Std.parseFloat(a[i]) : 0;
			var y = i < b.length ? Std.parseFloat(b[i]) : 0;
			if (Math.isNaN(x) || Math.isNaN(y))
				return left < right ? -1 : left > right ? 1 : 0;
			if (x != y)
				return x < y ? -1 : 1;
		}
		return 0;
	}

	static inline function isIdentifierPart(code:Int):Bool
		return (code >= 'a'.code && code <= 'z'.code) || (code >= 'A'.code && code <= 'Z'.code)
			|| (code >= '0'.code && code <= '9'.code) || code == '_'.code;
}
