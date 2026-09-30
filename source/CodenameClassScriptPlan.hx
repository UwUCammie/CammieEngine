package;

import haxe.io.Path;
import CodenameScriptDiscovery.CodenameScriptFile;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

typedef CodenameClassAssetDependency = {
	var kind:String;
	var key:String;
	var sourceClass:String;
	var method:String;
	var consumer:String;
}

typedef CodenameClassScriptPlanData = {
	var dependencies:Array<CodenameClassAssetDependency>;
	var diagnostics:Array<String>;
}

private typedef CodenameClassMethodAsset = {
	var classPath:String;
	var symbols:Array<String>;
	var method:String;
	var parameterIndex:Int;
	var kind:String;
}

private typedef CodenameSourceClassInfo = {
	var path:String;
	var symbols:Array<String>;
	var methods:Array<CodenameClassMethodAsset>;
}

/**
	Static-only bridge between owner-authored Haxe classes and Codename's
	classless HScript modules. This never evaluates a class body. It reports
	imports which cannot run yet and plans only literal asset keys passed to
	methods whose class source directly calls a recognized Paths asset API.
*/
class CodenameClassScriptPlan {
	static inline var MAX_METHODS:Int = 256;
	static inline var MAX_CALLS:Int = 512;
	static inline var MAX_DEPENDENCIES:Int = 128;

	#if sys
	static function readSource(root:String, file:CodenameScriptFile):Null<String> {
		if (file == null) return null;
		if (file.embeddedScript != null) return file.embeddedScript;
		if (root == null || file.path == null || !FileSystem.exists(file.path)
			|| FileSystem.isDirectory(file.path) || !CodenameScriptDiscovery.withinRoot(root, file.path))
			return null;
		try return File.getContent(file.path) catch (_:Dynamic) return null;
	}

	/** Replace comments and string contents with spaces, retaining source offsets. */
	static function maskCode(source:String):String {
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

	static function addSymbol(symbols:Array<String>, value:String):Void {
		if (value == null || value.trim() == '') return;
		var key = value.trim().toLowerCase();
		if (symbols.indexOf(key) < 0) symbols.push(key);
	}

	static function classInfo(root:String, file:CodenameScriptFile):Null<CodenameSourceClassInfo> {
		var source = readSource(root, file);
		if (source == null) return null;
		var masked = maskCode(source);
		var module = Path.withoutExtension(Path.withoutDirectory(file.relative));
		var packageName = '';
		var packagePattern = new EReg('(?:^|\\n)[ \\t]*package\\s+([A-Za-z_][A-Za-z0-9_.]*)\\s*;', '');
		if (packagePattern.match(masked)) packageName = packagePattern.matched(1);
		var symbols:Array<String> = [];
		addSymbol(symbols, module);
		if (packageName != '') addSymbol(symbols, packageName + '.' + module);
		var classPattern = new EReg('\\bclass\\s+([A-Za-z_][A-Za-z0-9_]*)', 'g');
		var remaining = masked;
		var attempts = 0;
		while (attempts++ < 32 && classPattern.match(remaining)) {
			var name = classPattern.matched(1);
			addSymbol(symbols, name);
			if (packageName != '') addSymbol(symbols, packageName + '.' + name);
			var position = classPattern.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
			remaining = remaining.substr(position.pos + position.len);
		}

		var methods:Array<CodenameClassMethodAsset> = [];
		var methodPattern = new EReg('\\bfunction\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(([^)]*)\\)[^;{}]*\\{', 'g');
		remaining = masked;
		var offset = 0;
		attempts = 0;
		while (attempts++ < MAX_METHODS && methodPattern.match(remaining)) {
			var methodName = methodPattern.matched(1);
			var parameters = methodPattern.matched(2).split(',');
			var methodPos = methodPattern.matchedPos();
			var bodyOpen = offset + methodPos.pos + methodPos.len - 1;
			var bodyClose = matchingBrace(masked, bodyOpen);
			if (bodyClose >= bodyOpen) {
				var body = masked.substring(bodyOpen + 1, bodyClose);
				for (api in [
					{method:'getSparrowAtlas', kind:'sparrow'},
					{method:'getPackerAtlas', kind:'packer'},
					{method:'getFrames', kind:'frames'},
					{method:'image', kind:'image'}
				]) {
					var use = new EReg('Paths\\s*\\.\\s*' + api.method
						+ '\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)', 'g');
					var calls = body;
					var apiAttempts = 0;
					while (apiAttempts++ < 32 && use.match(calls)) {
						var parameterName = use.matched(1);
						var parameterIndex = -1;
						for (i in 0...parameters.length) {
							var clean = StringTools.trim(parameters[i]);
							var colon = clean.indexOf(':');
							if (colon >= 0) clean = StringTools.trim(clean.substr(0, colon));
							if (clean.startsWith('?')) clean = clean.substr(1);
							if (clean == parameterName) { parameterIndex = i; break; }
						}
						if (parameterIndex >= 0) methods.push({classPath:file.relative,
							symbols:symbols.copy(), method:methodName, parameterIndex:parameterIndex,
							kind:api.kind});
						var usePos = use.matchedPos();
						if (usePos.len <= 0 || usePos.pos + usePos.len >= calls.length) break;
						calls = calls.substr(usePos.pos + usePos.len);
					}
				}
			}
			var position = methodPattern.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
			offset += position.pos + position.len;
			remaining = remaining.substr(position.pos + position.len);
		}
		return {path:file.relative, symbols:symbols, methods:methods};
	}

	static function matchingBrace(source:String, open:Int):Int {
		if (open < 0 || open >= source.length || source.charAt(open) != '{') return -1;
		var depth = 0;
		for (i in open...source.length) {
			if (source.charAt(i) == '{') depth++;
			else if (source.charAt(i) == '}') {
				depth--;
				if (depth == 0) return i;
			}
		}
		return -1;
	}

	static function imports(source:String):Array<String> {
		var result:Array<String> = [];
		var masked = maskCode(source);
		var pattern = new EReg('\\bimport\\s+([A-Za-z_][A-Za-z0-9_.]*)\\s*;', 'g');
		var remaining = masked;
		var attempts = 0;
		while (attempts++ < 128 && pattern.match(remaining)) {
			var name = pattern.matched(1).toLowerCase();
			if (result.indexOf(name) < 0) result.push(name);
			var position = pattern.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
			remaining = remaining.substr(position.pos + position.len);
		}
		return result;
	}

	static function callArguments(source:String, open:Int):Null<Array<String>> {
		var args:Array<String> = [];
		var start = open + 1;
		var parens = 0;
		var brackets = 0;
		var braces = 0;
		var quote = '';
		var escaped = false;
		for (i in start...source.length) {
			var ch = source.charAt(i);
			if (quote != '') {
				if (ch == '\\' && !escaped) escaped = true;
				else {
					if (ch == quote && !escaped) quote = '';
					escaped = false;
				}
				continue;
			}
			if (ch == "'" || ch == '"') { quote = ch; continue; }
			switch (ch) {
				case '(' : parens++;
				case ')' :
					if (parens == 0 && brackets == 0 && braces == 0) {
						var tail = StringTools.trim(source.substring(start, i));
					if (tail != '' || args.length > 0) args.push(tail);
					return args;
					}
					parens--;
				case '[' : brackets++;
				case ']' : brackets--;
				case '{' : braces++;
				case '}' : braces--;
				case ',' : if (parens == 0 && brackets == 0 && braces == 0) {
					args.push(StringTools.trim(source.substring(start, i)));
					start = i + 1;
				}
				default:
			}
			if (args.length > 32) return null;
		}
		return null;
	}

	static function stringLiteral(value:String):Null<String> {
		var literal = new EReg('^(["\'])(.*)\\1$', 's');
		if (!literal.match(StringTools.trim(value))) return null;
		var result = literal.matched(2);
		// Conservatively reject escapes; resolving their Haxe spelling correctly
		// is unnecessary for asset identifiers and risks guessing another key.
		if (result.indexOf('\\') >= 0 || result.indexOf('\n') >= 0 || result.indexOf('\r') >= 0) return null;
		return result;
	}

	static function addDiagnostic(result:CodenameClassScriptPlanData, message:String):Void {
		if (result.diagnostics.indexOf(message) < 0) result.diagnostics.push(message);
	}
	#end

	/** Report selected-owner class imports and gather finite, literal atlas keys. */
	public static function build(root:String, files:Array<CodenameScriptFile>):CodenameClassScriptPlanData {
		var result:CodenameClassScriptPlanData = {dependencies:[], diagnostics:[]};
		#if sys
		if (files == null || root == null || !FileSystem.isDirectory(root)) return result;
		var classes:Array<CodenameSourceClassInfo> = [];
		for (file in files) if (file != null && file.family == 'class') {
			var info = classInfo(root, file);
			if (info != null) classes.push(info);
		}
		var seenDependencies:Map<String, Bool> = new Map();
		var examinedCalls = 0;
		for (consumer in files) {
			if (consumer == null || consumer.family == 'class' || consumer.family == 'event-schema'
				|| consumer.family == 'character-xml') continue;
			var source = readSource(root, consumer);
			if (source == null) continue;
			var imported = imports(source);
			for (classInfo in classes) {
				var matchedImport = '';
				for (name in imported) if (classInfo.symbols.indexOf(name) >= 0) {
					matchedImport = name;
					break;
				}
				if (matchedImport == '') continue;
				addDiagnostic(result, '[codename-class-script] ' + consumer.relative + ' imports '
					+ matchedImport + ' from ' + classInfo.path
					+ '; the file is staged owner-locally, but HScript cannot execute class declarations');
				for (method in classInfo.methods) {
					var call = new EReg('\\.\\s*' + method.method + '\\s*\\(', 'g');
					var remaining = source;
					var offset = 0;
					var attempts = 0;
					while (attempts++ < MAX_CALLS && call.match(remaining)) {
						if (++examinedCalls > MAX_CALLS) {
							addDiagnostic(result, '[codename-class-dependency] call scan limit reached');
							return result;
						}
						var position = call.matchedPos();
						var open = offset + position.pos + position.len - 1;
						var args = callArguments(source, open);
						if (args == null || method.parameterIndex >= args.length) {
							addDiagnostic(result, '[codename-class-dependency] ' + consumer.relative + ': '
								+ matchedImport + '.' + method.method + ' arguments could not be read safely');
						} else {
							var key = stringLiteral(args[method.parameterIndex]);
							if (key == null) {
								addDiagnostic(result, '[codename-class-dependency] ' + consumer.relative + ': '
									+ matchedImport + '.' + method.method + ' uses a non-literal asset key; skipped static dependency');
							} else if (!CodenameScriptDiscovery.safeRelativeName(key)) {
								addDiagnostic(result, '[codename-class-dependency] ' + consumer.relative + ': '
									+ matchedImport + '.' + method.method + ' has an unsafe asset key');
							} else {
								var identity = method.kind + ':' + key.toLowerCase();
								if (!seenDependencies.exists(identity)) {
									if (result.dependencies.length >= MAX_DEPENDENCIES) {
										addDiagnostic(result, '[codename-class-dependency] dependency limit reached');
										return result;
									}
									seenDependencies.set(identity, true);
									result.dependencies.push({kind:method.kind, key:key,
										sourceClass:classInfo.path, method:method.method, consumer:consumer.relative});
								}
							}
						}
						if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
						offset += position.pos + position.len;
						remaining = remaining.substr(position.pos + position.len);
					}
				}
			}
		}
		#end
		return result;
	}
}
