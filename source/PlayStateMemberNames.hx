package;

#if macro
import haxe.macro.Context;
import haxe.macro.Expr;
#end

/**
	Names of the public instance members PlayState really declares, read from
	the PlayState source (and its superclasses in this source tree) at compile
	time. Script gates that must tell real PlayState members from donor-only
	ones use this instead of a hand-kept list, so a new PlayState member can
	never be rejected just because nobody remembered to list it.
**/
class PlayStateMemberNames {
	public static macro function collect():ExprOf<Array<String>> {
		var names:Array<String> = [];
		var seen:Map<String, Bool> = [];
		var className = 'PlayState';
		var guard = 0;
		// Read the classes beside this file, not whatever a class path lookup
		// finds first: a test fixture's stand-in PlayState must not change them.
		var sourceDir:String = null;
		try {
			sourceDir = haxe.io.Path.directory(Context.resolvePath('PlayStateMemberNames.hx'));
		} catch (error:Dynamic) {
			sourceDir = null;
		}
		while (className != null && guard++ < 8) {
			var path:String = sourceDir == null ? null : haxe.io.Path.join([sourceDir, className + '.hx']);
			if (path == null || !sys.FileSystem.exists(path))
				break;
			Context.registerModuleDependency(Context.getLocalModule(), path);
			var parsed = scan(sys.io.File.getContent(path), className);
			for (name in parsed.names)
				if (!seen.exists(name)) {
					seen.set(name, true);
					names.push(name);
				}
			className = parsed.parent;
		}
		if (names.length == 0)
			Context.warning('[playstate-member-names] PlayState source not found; no members collected', Context.currentPos());
		return macro $v{names};
	}

	// Plain helpers, not macro-only, so tests can drive the scanner directly.

	/** Blank comments, string contents and regex literals so braces and keywords inside them are ignored. */
	public static function clean(source:String):String {
		var out = new StringBuf();
		var i = 0;
		var length = source.length;
		// Each entry is the brace depth at which an interpolation inside a single-quoted string began.
		var interpolation:Array<Int> = [];
		var depth = 0;
		var inSingle = false;
		while (i < length) {
			var c = source.charAt(i);
			if (inSingle) {
				if (c == '\\' && i + 1 < length) {
					out.add('  ');
					i += 2;
					continue;
				}
				if (c == "'") {
					inSingle = false;
					out.add("'");
					i++;
					continue;
				}
				if (c == '$' && i + 1 < length && source.charAt(i + 1) == '{') {
					inSingle = false;
					interpolation.push(depth);
					depth++;
					out.add('  ');
					i += 2;
					continue;
				}
				out.add(c == '\n' ? '\n' : ' ');
				i++;
				continue;
			}
			var next = i + 1 < length ? source.charAt(i + 1) : '';
			if (c == '/' && next == '/') {
				while (i < length && source.charAt(i) != '\n') {
					out.add(' ');
					i++;
				}
				continue;
			}
			if (c == '/' && next == '*') {
				var end = source.indexOf('*/', i + 2);
				var stop = end < 0 ? length : end + 2;
				while (i < stop) {
					out.add(source.charAt(i) == '\n' ? '\n' : ' ');
					i++;
				}
				continue;
			}
			if (c == '~' && next == '/') {
				out.add('  ');
				i += 2;
				while (i < length) {
					var r = source.charAt(i);
					if (r == '\\' && i + 1 < length) {
						out.add('  ');
						i += 2;
						continue;
					}
					out.add(' ');
					i++;
					if (r == '/')
						break;
				}
				continue;
			}
			if (c == '"') {
				out.add('"');
				i++;
				while (i < length) {
					var s = source.charAt(i);
					if (s == '\\' && i + 1 < length) {
						out.add('  ');
						i += 2;
						continue;
					}
					i++;
					if (s == '"') {
						out.add('"');
						break;
					}
					out.add(s == '\n' ? '\n' : ' ');
				}
				continue;
			}
			if (c == "'") {
				inSingle = true;
				out.add("'");
				i++;
				continue;
			}
			if (c == '{')
				depth++;
			else if (c == '}') {
				depth--;
				if (interpolation.length > 0 && interpolation[interpolation.length - 1] == depth) {
					interpolation.pop();
					inSingle = true;
					out.add(' ');
					i++;
					continue;
				}
			}
			out.add(c);
			i++;
		}
		return out.toString();
	}

	/** Public, non-static members declared directly in the body of `className`, plus its superclass name. */
	public static function scan(source:String, className:String):{names:Array<String>, parent:String} {
		var text = clean(source);
		var header = new EReg('\\bclass\\s+' + className + '\\b([^{]*)\\{', '');
		if (!header.match(text))
			return {names: [], parent: null};
		var parent:String = null;
		var extendsPattern = ~/\bextends\s+([A-Za-z_][A-Za-z0-9_.]*)/;
		if (extendsPattern.match(header.matched(1))) {
			parent = extendsPattern.matched(1);
			var dot = parent.lastIndexOf('.');
			if (dot >= 0)
				parent = parent.substr(dot + 1);
		}
		var position = header.matchedPos();
		var i = position.pos + position.len;
		var depth = 1;
		var level = new StringBuf();
		while (i < text.length && depth > 0) {
			var c = text.charAt(i);
			if (c == '{') {
				if (depth == 1)
					level.add(';');
				depth++;
			} else if (c == '}') {
				depth--;
				if (depth == 1)
					level.add(';');
			} else if (depth == 1)
				level.add(c);
			i++;
		}
		var names:Array<String> = [];
		var declaration = ~/\b(var|final|function)\s+([A-Za-z_][A-Za-z0-9_]*)/;
		var keywords = ['var', 'final', 'function', 'new'];
		for (statement in level.toString().split(';')) {
			var rest = statement;
			while (declaration.match(rest)) {
				var name = declaration.matched(2);
				if (keywords.indexOf(name) >= 0) {
					rest = declaration.matchedRight();
					continue;
				}
				var prefix = statement.substr(0, statement.length - rest.length) + declaration.matchedLeft();
				if (~/\bpublic\b/.match(prefix) && !~/\bstatic\b/.match(prefix) && names.indexOf(name) < 0)
					names.push(name);
				break;
			}
		}
		return {names: names, parent: parent};
	}
}
