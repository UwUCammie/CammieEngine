package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

typedef CodenameDynamicAtlasFile = {
	var source:String;
	var relative:String;
}

typedef CodenameDynamicAtlasPlan = {
	var files:Array<CodenameDynamicAtlasFile>;
	var diagnostics:Array<String>;
}

/** Collect direct Sparrow atlases named through a statically known folder and
	 a runtime-selected basename, such as `directory + 'icons/' + song.icon`.
	The script is inspected as text only; every source path remains under the
	selected owner or its structurally validated Codename installation assets.
*/
class CodenameDynamicAtlasAssets {
	public static function filesFor(ownerRoot:String, installationAssetRoot:String,
		script:String):CodenameDynamicAtlasPlan {
		var result:CodenameDynamicAtlasPlan = {files:[], diagnostics:[]};
		#if sys
		if (script == null || StringTools.trim(script) == '') return result;
		if (ownerRoot == null || !FileSystem.isDirectory(ownerRoot)) {
			result.diagnostics.push('selected owner directory is unavailable');
			return result;
		}

		var cleanSource = stripComments(script);
		var bindings = stringBindings(cleanSource);
		var seen:Map<String, Bool> = new Map();
		var reported:Map<String, Bool> = new Map();
		var report = function(message:String):Void {
			if (!reported.exists(message)) {
				reported.set(message, true);
				result.diagnostics.push(message);
			}
		};
		var calls = new EReg('Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(', 'g');
		var remaining = cleanSource;
		var offset = 0;
		while (calls.match(remaining)) {
			var callPosition = calls.matchedPos();
			var openParen = offset + callPosition.pos + callPosition.len - 1;
			var argument = firstArgument(cleanSource, openParen + 1);
			if (argument == null) {
				report('could not parse a Paths.getSparrowAtlas argument');
				var next = callPosition.pos + callPosition.len;
				if (next >= remaining.length) break;
				offset += next;
				remaining = remaining.substr(next);
				continue;
			}

			var prefix = dynamicPrefix(argument, bindings);
			if (prefix.hasDynamicTerm) {
				if (prefix.value == '') {
					report('dynamic atlas expression has no statically known directory prefix: '
						+ StringTools.trim(argument));
				} else if (!prefix.value.endsWith('/')) {
					report('dynamic atlas expression prefix is not a complete directory: '
						+ prefix.value + ' (expected a trailing slash)');
				} else {
					var directory = imageDirectory(prefix.value);
					if (directory == null) {
						report('dynamic atlas directory prefix is unsafe: ' + prefix.value);
					} else {
						var sourceDirectory = directory == '' ? 'images' : 'images/' + directory;
						var collected = collectDirectory(ownerRoot, sourceDirectory, directory, seen, result, report);
						if (CodenameInstallationAssetOverlay.isInstallationAssetsRootForOwner(
							ownerRoot, installationAssetRoot))
							collected += collectDirectory(installationAssetRoot, sourceDirectory,
								directory, seen, result, report);
						if (collected == 0)
							report('dynamic atlas directory ' + sourceDirectory
								+ ' was not found in the selected owner or its Codename installation assets');
					}
				}
			}

			var consumed = openParen + 1;
			var depth = 0;
			var quote = '';
			var escaped = false;
			while (consumed < cleanSource.length) {
				var ch = cleanSource.charAt(consumed);
				if (quote != '') {
					if (escaped) escaped = false;
					else if (ch == '\\') escaped = true;
					else if (ch == quote) quote = '';
				} else if (ch == '\'' || ch == '"') quote = ch;
				else if (ch == '(') depth++;
				else if (ch == ')') {
					if (depth == 0) { consumed++; break; }
					depth--;
				}
				consumed++;
			}
			if (consumed <= offset || consumed >= cleanSource.length) break;
			offset = consumed;
			remaining = cleanSource.substr(offset);
		}
		#end
		return result;
	}

	#if sys
	static function collectDirectory(root:String, relativeDirectory:String,
		destinationDirectory:String, seen:Map<String, Bool>, result:CodenameDynamicAtlasPlan,
		report:String->Void):Int {
		var resolved = CodenameScriptDiscovery.resolveScopedDirectory(root, relativeDirectory);
		if (resolved.relative == null) {
			if (resolved.status != 'missing')
				report('dynamic atlas directory ' + relativeDirectory + ' is ' + resolved.status);
			return 0;
		}
		var absolute = Path.join([root, resolved.relative]);
		var entries:Array<String>;
		try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(absolute)) catch (error:Dynamic) {
			report('could not list dynamic atlas directory ' + relativeDirectory
				+ ': ' + Std.string(error));
			return 0;
		}
		entries.sort(Reflect.compare);
		var discovered = 0;
		for (entry in entries) {
			if (!CodenameScriptDiscovery.safeName(entry)) continue;
			var extension = Path.extension(entry).toLowerCase();
			if (extension != 'png' && extension != 'xml') continue;
			var source = Path.join([absolute, entry]);
			if (FileSystem.isDirectory(source) || !CodenameScriptDiscovery.withinRoot(root, source)) continue;
			var target = destinationDirectory == '' ? 'images/' + entry
				: 'images/' + destinationDirectory + '/' + entry;
			discovered++;
			var identity = target;
			if (seen.exists(identity)) continue;
			seen.set(identity, true);
			result.files.push({source:source, relative:target});
		}
		return discovered;
	}

	static function stripComments(source:String):String {
		var output = source.split('');
		var quote = '';
		var escaped = false;
		var index = 0;
		while (index < output.length) {
			var ch = output[index];
			if (quote != '') {
				if (escaped) escaped = false;
				else if (ch == '\\') escaped = true;
				else if (ch == quote) quote = '';
				index++;
				continue;
			}
			if (ch == '\'' || ch == '"') {
				quote = ch;
				index++;
				continue;
			}
			if (ch == '/' && index + 1 < output.length && output[index + 1] == '/') {
				while (index < output.length && output[index] != '\n') output[index++] = ' ';
				continue;
			}
			if (ch == '/' && index + 1 < output.length && output[index + 1] == '*') {
				output[index++] = ' ';
				output[index++] = ' ';
				while (index < output.length) {
					if (output[index] == '*' && index + 1 < output.length && output[index + 1] == '/') {
						output[index++] = ' ';
						output[index++] = ' ';
						break;
					}
					if (output[index] != '\n' && output[index] != '\r') output[index] = ' ';
					index++;
				}
				continue;
			}
			index++;
		}
		return output.join('');
	}

	static function stringBindings(source:String):Map<String, String> {
		var result:Map<String, String> = new Map();
		var ambiguous:Map<String, Bool> = new Map();
		var declarationEquals:Map<Int, Bool> = new Map();
		var code = stripStringContents(source);
		var declaration = new EReg('\\b(?:var|final|const)\\s+([A-Za-z_$][A-Za-z0-9_$]*)\\s*(?::\\s*String)?\\s*=', 'g');
		var remaining = code;
		var offset = 0;
		while (declaration.match(remaining)) {
			var position = declaration.matchedPos();
			var name = declaration.matched(1);
			var equalAt = offset + position.pos + position.len - 1;
			declarationEquals.set(equalAt, true);
			var value = readStringLiteral(source, equalAt + 1);
			var next = position.pos + position.len;
			if (value != null && standaloneString(source, value.end) && !ambiguous.exists(name)) {
				if (result.exists(name) && result.get(name) != value.value) {
					result.remove(name);
					ambiguous.set(name, true);
				} else result.set(name, value.value);
			} else {
				result.remove(name);
				ambiguous.set(name, true);
			}
			if (next >= remaining.length) break;
			offset += next;
			remaining = remaining.substr(next);
		}
		var assignment = new EReg('\\b([A-Za-z_$][A-Za-z0-9_$]*)\\s*=(?!=)', 'g');
		remaining = code;
		offset = 0;
		while (assignment.match(remaining)) {
			var position = assignment.matchedPos();
			var name = assignment.matched(1);
			var equalAt = offset + position.pos + position.len - 1;
			if (!declarationEquals.exists(equalAt) && result.exists(name)) {
				var value = readStringLiteral(source, equalAt + 1);
				if (value == null || !standaloneString(source, value.end)
					|| result.get(name) != value.value) {
					result.remove(name);
					ambiguous.set(name, true);
				}
			}
			var next = position.pos + position.len;
			if (next >= remaining.length) break;
			offset += next;
			remaining = remaining.substr(next);
		}
		return result;
	}

	static function stripStringContents(source:String):String {
		var output = source.split('');
		var quote = '';
		var escaped = false;
		for (index in 0...output.length) {
			var ch = output[index];
			if (quote != '') {
				if (ch != '\n' && ch != '\r') output[index] = ' ';
				if (escaped) escaped = false;
				else if (ch == '\\') escaped = true;
				else if (ch == quote) quote = '';
			} else if (ch == '\'' || ch == '"') {
				quote = ch;
				output[index] = ' ';
			}
		}
		return output.join('');
	}

	static function standaloneString(source:String, end:Int):Bool {
		var index = end;
		while (index < source.length && (source.charAt(index) == ' ' || source.charAt(index) == '\t')) index++;
		return index >= source.length || source.charAt(index) == ';'
			|| source.charAt(index) == '\n' || source.charAt(index) == '\r'
			|| source.charAt(index) == '}';
	}

	static function readStringLiteral(source:String, start:Int):Null<{value:String, end:Int}> {
		var index = start;
		while (index < source.length && (source.charAt(index) == ' ' || source.charAt(index) == '\t')) index++;
		if (index >= source.length) return null;
		var quote = source.charAt(index);
		if (quote != '\'' && quote != '"') return null;
		index++;
		var value = '';
		var escaped = false;
		while (index < source.length) {
			var ch = source.charAt(index++);
			if (escaped) {
				value += switch (ch) {
					case 'n': '\n';
					case 'r': '\r';
					case 't': '\t';
					default: ch;
				};
				escaped = false;
			} else if (ch == '\\') escaped = true;
			else if (ch == quote) return {value:value, end:index};
			else value += ch;
		}
		return null;
	}

	static function firstArgument(source:String, start:Int):Null<String> {
		var depth = 0;
		var quote = '';
		var escaped = false;
		var index = start;
		while (index < source.length) {
			var ch = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (ch == '\\') escaped = true;
				else if (ch == quote) quote = '';
			} else if (ch == '\'' || ch == '"') quote = ch;
			else if (ch == '(') depth++;
			else if (ch == ')') {
				if (depth == 0) return source.substr(start, index - start);
				depth--;
			} else if (ch == ',' && depth == 0) return source.substr(start, index - start);
			index++;
		}
		return null;
	}

	static function splitConcatenation(expression:String):Array<String> {
		var terms:Array<String> = [];
		var start = 0;
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in 0...expression.length) {
			var ch = expression.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (ch == '\\') escaped = true;
				else if (ch == quote) quote = '';
			} else if (ch == '\'' || ch == '"') quote = ch;
			else if (ch == '(') depth++;
			else if (ch == ')') depth--;
			else if (ch == '+' && depth == 0) {
				terms.push(StringTools.trim(expression.substr(start, index - start)));
				start = index + 1;
			}
		}
		terms.push(StringTools.trim(expression.substr(start)));
		return terms;
	}

	static function dynamicPrefix(expression:String, bindings:Map<String, String>):{hasDynamicTerm:Bool, value:String} {
		var prefix = '';
		var hasDynamicTerm = false;
		for (term in splitConcatenation(expression)) {
			var clean = unwrap(term);
			var literal = literalValue(clean);
			if (literal != null) {
				prefix += literal;
				continue;
			}
			if (new EReg('^[A-Za-z_$][A-Za-z0-9_$]*$', '').match(clean)
				&& bindings.exists(clean)) {
				prefix += bindings.get(clean);
				continue;
			}
			hasDynamicTerm = true;
			break;
		}
		return {hasDynamicTerm:hasDynamicTerm, value:prefix};
	}

	static function unwrap(value:String):String {
		var clean = StringTools.trim(value);
		while (clean.length >= 2 && clean.charAt(0) == '(' && clean.charAt(clean.length - 1) == ')')
			clean = StringTools.trim(clean.substr(1, clean.length - 2));
		return clean;
	}

	static function literalValue(value:String):Null<String> {
		if (value.length < 2) return null;
		var quote = value.charAt(0);
		if ((quote != '\'' && quote != '"') || value.charAt(value.length - 1) != quote) return null;
		var decoded = readStringLiteral(value, 0);
		return decoded != null && decoded.end == value.length ? decoded.value : null;
	}

	static function imageDirectory(prefix:String):Null<String> {
		var clean = StringTools.replace(StringTools.trim(prefix), '\\', '/');
		while (clean.indexOf('//') >= 0) clean = StringTools.replace(clean, '//', '/');
		if (clean.startsWith('/') || clean.indexOf(':') >= 0) return null;
		if (clean.toLowerCase().startsWith('assets/images/')) clean = clean.substr('assets/images/'.length);
		else if (clean.toLowerCase().startsWith('images/')) clean = clean.substr('images/'.length);
		if (!clean.endsWith('/')) return null;
		while (clean.endsWith('/')) clean = clean.substr(0, clean.length - 1);
		if (clean == '') return '';
		return CodenameScriptDiscovery.safeRelativeName(clean) ? clean : null;
	}
	#end
}
