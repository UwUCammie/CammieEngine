package;

using StringTools;

/** Conservative algebraic optimization of nearest-distance reductions, independent of shader names. */
class ShaderSourceOptimizer {
	static var enabled:Bool = #if sys Sys.getEnv('CAMMIE_SHADER_OPTIMIZATIONS') != '0' #else true #end;
	public static function optimize(source:String):String {
		if (!enabled || source == null) return source;
		return ShaderRepeatedCallOptimizer.optimize(nearestDistance(source));
	}

	public static function nearestDistance(source:String):String {
		// Rewritten builtin calls must retain their GLSL meaning.
		if (~/^[ \t]*#[ \t]*define[ \t]+(min|distance|dot|sqrt)\b/m.match(source)
			|| ~/\b(float|vec[234])[ \t\r\n]+(min|distance|dot|sqrt)[ \t\r\n]*\(/.match(source)) return source;
		var tokens = @:privateAccess CodenameShaderSource.glslTokens(source);
		var macros:Map<String, Bool> = [];
		var define = ~/^[ \t]*#[ \t]*define[ \t]+([A-Za-z_][A-Za-z_0-9]*)/m;
		var remaining = source;
		while (define.match(remaining)) {
			macros.set(define.matched(1), true);
			remaining = define.matchedRight();
		}
		var types:Map<String, String> = [];
		for (i in 0...tokens.length - 1) if (['vec2', 'vec3', 'vec4', 'float', 'int'].indexOf(tokens[i].text) >= 0
			&& tokens[i + 1].kind == 'identifier') {
			var name:String = tokens[i + 1].text;
			var type:String = tokens[i].text;
			if (types.exists(name) && types.get(name) != type) types.set(name, 'ambiguous');
			else if (!types.exists(name)) types.set(name, type);
		}
		var edits:Array<{start:Int, end:Int, text:String}> = [];
		var unique = 0;
		for (i in 0...tokens.length - 7) {
			if (tokens[i].text != 'float' || tokens[i + 1].kind != 'identifier' || tokens[i + 2].text != '='
				|| tokens[i + 3].kind != 'number' || tokens[i + 4].text != ';' || tokens[i + 5].text != 'for') continue;
			var name:String = tokens[i + 1].text;
			var initial = Std.parseFloat(tokens[i + 3].text);
			if (!Math.isFinite(initial) || initial < 1e-10 || initial > 1e10) continue;
			var open = i + 6;
			if (tokens[open].text != '(') continue;
			var headerEnd = matching(tokens, open, '(', ')');
			if (headerEnd < 0 || headerEnd + 1 >= tokens.length || tokens[headerEnd + 1].text != '{') continue;
			var end = matching(tokens, headerEnd + 1, '{', '}');
			if (end < 0) continue;
			// Hidden macro reads or conditional declarations can change loop semantics.
			if (source.substring(tokens[i].start, tokens[end].end).indexOf('#') >= 0) continue;
			var hasMacro = false;
			for (j in i...end + 1) if (macros.exists(tokens[j].text)) hasMacro = true;
			if (hasMacro) continue;
			var found = -1;
			var count = 0;
			var parentheses = 0;
			for (j in i + 5...end + 1) {
				if (tokens[j].text == '(') parentheses++;
				else if (tokens[j].text == ')') parentheses--;
				if (tokens[j].text == name) count++;
				if (j > headerEnd + 1 && parentheses == 0 && ['{',';',')','}','else'].indexOf(tokens[j - 1].text) >= 0
					&& j + 13 < end && tokens[j].text == name && tokens[j + 1].text == '=' && tokens[j + 2].text == 'min'
					&& tokens[j + 3].text == '(' && tokens[j + 4].text == name && tokens[j + 5].text == ','
					&& tokens[j + 6].text == 'distance' && tokens[j + 7].text == '(' && tokens[j + 8].kind == 'identifier'
					&& tokens[j + 9].text == ',' && tokens[j + 10].kind == 'identifier' && tokens[j + 11].text == ')'
					&& tokens[j + 12].text == ')' && tokens[j + 13].text == ';') found = j;
			}
			// No comparisons, other writes or reads of the running result inside the loop.
			if (found < 0 || count != 2) continue;
			var a:String = tokens[found + 8].text, b:String = tokens[found + 10].text;
			var type = types.get(a);
			if (['vec2','vec3','vec4'].indexOf(type) < 0 || types.get(b) != type) continue;
			var temp = 'cammieNearestSquared' + unique++;
			while (source.indexOf(temp) >= 0) temp += '_';
			var delta = temp + 'Delta';
			while (source.indexOf(delta) >= 0) delta += '_';
			edits.push({start:tokens[i + 5].start, end:tokens[i + 5].start, text:'float ' + temp + ' = ' + name + ' * ' + name + ';\n'});
			edits.push({start:tokens[found].start, end:tokens[found + 13].end,
				text:'{ ' + type + ' ' + delta + ' = ' + a + ' - ' + b + '; ' + temp + ' = min(' + temp + ', dot(' + delta + ', ' + delta + ')); }'});
			edits.push({start:tokens[end].end, end:tokens[end].end, text:'\n' + name + ' = sqrt(' + temp + ');'});
		}
		edits.sort(function(a,b) return b.start - a.start);
		for (edit in edits) source = source.substring(0,edit.start) + edit.text + source.substring(edit.end);
		return source;
	}
	static function matching(tokens:Array<Dynamic>, start:Int, open:String, close:String):Int {
		var depth = 0;
		for (i in start...tokens.length) {
			if (tokens[i].text == open) depth++;
			else if (tokens[i].text == close && --depth == 0) return i;
		}
		return -1;
	}
}
