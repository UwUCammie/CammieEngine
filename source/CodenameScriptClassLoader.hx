package;

import hscript.Expr.ModuleDecl;
import hscript.Expr.ClassDecl;
import hscript.ParserEx;
import hscript.Printer;
import hscript.ScriptClassScope;
import haxe.io.Path;
import CodenameScriptParser.CodenameScriptParseResult;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

typedef CodenameScriptClassLoad = {
	var scope:ScriptClassScope;
	var imports:Map<String, Dynamic>;
	var diagnostics:Array<String>;
	var sourceUseDiagnostics:Array<String>;
}

typedef CodenameScriptOwnerPrepare = {
	var classLoad:CodenameScriptClassLoad;
	var parsed:CodenameScriptParseResult;
}

/** Small host contract so class-source parsing does not pull in gameplay. */
typedef CodenameOwnerClassHost = {
	var variables:Map<String, Dynamic>;
	function bindScriptClassScope(scope:ScriptClassScope):Void;
}

/**
	Loads only HScript-ex class modules named by an active owner's imports.
	Each loader owns one descriptor registry and refuses path escapes, unsafe
	imports, unsupported parser syntax, and unresolved dependencies.
*/
@:access(CodenameScriptParser)
class CodenameScriptClassLoader {
	static inline var MAX_MODULES:Int = 96;
	static inline var MAX_DEPTH:Int = 16;
	static inline var MAX_SOURCE_BYTES:Int = 4 * 1024 * 1024;
	// HL17 scripts use the shared Options facade for their gameplay shader and
	// stage-17 Flx3D gates. VRAM-only bitmap storage has no native backend here.
	static final UNSUPPORTED_OPTION_FIELDS:Array<String> = ['gpuOnlyBitmaps'];

	final ownerRoot:String;
	final ownerUsesStringTools:Bool;
	final bindings:Map<String, Dynamic>;
	final scope:ScriptClassScope;
	final loaded:Map<String, Bool> = new Map();
	final loading:Map<String, Bool> = new Map();
	final diagnostics:Array<String> = [];
	final sourceUseDiagnostics:Array<String> = [];
	final aliases:Map<String, Dynamic> = new Map();
	var moduleCount:Int = 0;

	function new(ownerRoot:String, bindings:Map<String, Dynamic>, scope:ScriptClassScope) {
		this.ownerRoot = ownerRoot;
		this.ownerUsesStringTools = hasOwnerStringToolsUsing(ownerRoot);
		this.bindings = bindings;
		this.scope = scope;
	}

	static function hasOwnerStringToolsUsing(ownerRoot:String):Bool {
		#if sys
		try {
			var path = Path.join([ownerRoot, 'source/import.hx']);
			if (!FileSystem.exists(path) || FileSystem.isDirectory(path)
				|| !CodenameScriptDiscovery.withinRoot(ownerRoot, path)
				|| FileSystem.stat(path).size > 1048576)
				return false;
			return new EReg('\\busing[ \\t\\r\\n]+StringTools[ \\t\\r\\n]*;', '')
				.match(codeMask(File.getContent(path)));
		} catch (_:Dynamic) {}
		#end
		return false;
	}

	public static function load(ownerRoot:String, imports:Array<String>,
		bindings:Map<String, Dynamic>, symbols:Map<String, Dynamic>):CodenameScriptClassLoad {
		var scope = new ScriptClassScope();
		scope.seedFrom(symbols);
		scope.seedFrom(bindings);
		// Codename's source/import.hx makes common Flixel classes available to
		// owner source modules without a repeated import declaration. Give a
		// class the same unqualified, unambiguous host aliases as its classless
		// script before its constructor runs, while preserving explicit symbols.
		if (bindings != null) for (name in bindings.keys()) {
			var dot = name.lastIndexOf('.');
			if (dot < 0 || dot == name.length - 1) continue;
			var shortName = name.substr(dot + 1);
			if ((symbols != null && symbols.exists(shortName)) || bindings.exists(shortName)) continue;
			scope.bindImport(name.split('.'), bindings.get(name));
		}
		var loader = new CodenameScriptClassLoader(ownerRoot, bindings, scope);
		var classImports:Map<String, Dynamic> = new Map();
		if (imports != null) for (path in imports) {
			if (bindings != null && bindings.exists(path) && bindings.get(path) != null) {
				scope.bindImport(path.split('.'), bindings.get(path));
				continue;
			}
			var resolved = loader.loadImport(path, 0);
			if (resolved.loaded) {
				classImports.set(path, {__codenameScriptClass:true});
			} else if (resolved.expectedSource) {
				scope.markUnavailableImport(path, resolved.reason);
			} else if (resolved.reason == '') {
				var diagnostic = 'no explicit owner binding or source module for import ' + path;
				if (loader.diagnostics.indexOf(diagnostic) < 0) loader.diagnostics.push(diagnostic);
			}
		}
		return {scope:scope, imports:classImports, diagnostics:loader.diagnostics,
			sourceUseDiagnostics:loader.sourceUseDiagnostics};
	}

	/** Load selected-owner class imports, bind only successfully registered
	 * descriptors, then prepare the classless script against that exact map. */
	public static function prepareOwnerScript(ownerRoot:String, source:String,
		bindings:Map<String, Dynamic>, symbols:Map<String, Dynamic>, interp:CodenameOwnerClassHost,
		origin:String, ?traceStages:Bool = false):CodenameScriptOwnerPrepare {
		var classLoad = load(ownerRoot, CodenameScriptParser.importPaths(source), bindings, symbols);
		if (interp != null) interp.bindScriptClassScope(classLoad.scope);

		var aliasPaths:Map<String, String> = new Map();
		var paths = [for (path in classLoad.imports.keys()) path];
		for (path in paths) {
			if (!classLoad.imports.exists(path)) continue;
			var value = classLoad.imports.get(path);
			var shortName = path.substr(path.lastIndexOf('.') + 1);
			var previousPath = aliasPaths.get(shortName);
			var existing = bindings == null ? null : bindings.get(shortName);
			var conflictsWithBinding = bindings != null && bindings.exists(shortName)
				&& existing != value && shortName != path;
			var conflictsWithImport = previousPath != null && previousPath != path;
			if (conflictsWithBinding || conflictsWithImport) {
				var conflict = 'owner class import ' + path + ' has a conflicting unqualified name ' + shortName;
				if (classLoad.diagnostics.indexOf(conflict) < 0) classLoad.diagnostics.push(conflict);
				classLoad.imports.remove(path);
				if (bindings != null) bindings.remove(path);
				if (interp != null) interp.variables.remove(shortName);
				if (conflictsWithImport) {
					classLoad.imports.remove(previousPath);
					if (bindings != null) bindings.remove(previousPath);
					aliasPaths.remove(shortName);
				}
				continue;
			}
			if (bindings != null) {
				bindings.set(path, value);
				bindings.set(shortName, value);
			}
			if (interp != null) interp.variables.set(shortName, value);
			aliasPaths.set(shortName, path);
		}

		return {classLoad:classLoad,
			parsed:CodenameScriptParser.prepare(source, bindings, origin, traceStages)};
	}

	function loadImport(importPath:String, depth:Int):{expectedSource:Bool, loaded:Bool, reason:String} {
		if (!validImport(importPath)) {
			var diagnostic = 'unsafe class import: ' + Std.string(importPath);
			if (diagnostics.indexOf(diagnostic) < 0) diagnostics.push(diagnostic);
			return {expectedSource:false, loaded:false, reason:'unsafe class import: ' + importPath};
		}
		var relative = findSourceModule(importPath);
		if (relative == null) return {expectedSource:false, loaded:false, reason:''};
		if (loaded.exists(relative)) return {expectedSource:true, loaded:true, reason:''};
		if (loading.exists(relative)) return {expectedSource:true, loaded:true, reason:''};
		if (depth >= MAX_DEPTH) return fail(importPath, relative, 'class dependency depth limit reached');
		if (moduleCount >= MAX_MODULES) return fail(importPath, relative, 'class module limit reached');
		moduleCount++;
		loading.set(relative, true);
		var fullPath = Path.join([ownerRoot, relative]);
		var source:String;
		try {
			#if sys
			if (!FileSystem.exists(fullPath) || FileSystem.isDirectory(fullPath)
				|| !CodenameScriptDiscovery.withinRoot(ownerRoot, fullPath))
				return fail(importPath, relative, 'class source escaped its owner root or disappeared');
			if (FileSystem.stat(fullPath).size > MAX_SOURCE_BYTES)
				return fail(importPath, relative, 'class source exceeds the 4 MiB limit');
			source = File.getContent(fullPath);
			#else
			return fail(importPath, relative, 'filesystem-backed class modules are unavailable on this target');
			#end
		} catch (error:Dynamic) {
			return fail(importPath, relative, 'could not read class source: ' + Std.string(error));
		}
		for (diagnostic in unsupportedOptionSourceUses(source, relative))
			if (sourceUseDiagnostics.indexOf(diagnostic) < 0) sourceUseDiagnostics.push(diagnostic);
		var normalized = normalizeModuleSyntax(source, importPath, relative, depth);
		if (normalized.error != '') return fail(importPath, relative, normalized.error);
		source = normalized.source;
		var module:Array<ModuleDecl>;
		try module = parserForRuntimeSource().parseModule(source, relative) catch (error:Dynamic) {
			// Some source HScript modules omit a field terminator after a multiline
			// array initializer. HScript-ex reports EUnexpected on the next class
			// field. Retry only this bounded, same-line grammar repair; preserve
			// the original diagnostic if parsing still fails.
			var repaired = repairMissingArrayFieldTerminator(source);
			if (repaired == source)
				return fail(importPath, relative, 'HScript-ex could not parse the source module: ' + Std.string(error));
			try module = parserForRuntimeSource().parseModule(repaired, relative) catch (_:Dynamic)
				return fail(importPath, relative, 'HScript-ex could not parse the source module: ' + Std.string(error));
			source = repaired;
		}
		var positionDefaults = normalizeNativePositionDefaults(source, module);
		if (positionDefaults.error != '') return fail(importPath, relative, positionDefaults.error);
		if (positionDefaults.source != source) {
			source = positionDefaults.source;
			try module = parserForRuntimeSource().parseModule(source, relative) catch (error:Dynamic)
				return fail(importPath, relative, 'could not parse native position defaults: ' + Std.string(error));
		}
		var classCount = 0;
		var sourcePackage = '';
		var requestedClassDeclared = false;
		var importAliases:Map<String, Array<String>> = new Map();
		var requestedParts = importPath.split('.');
		var requestedName = requestedParts.pop();
		var requestedPackage = requestedParts.join('.');
		for (decl in module) switch (decl) {
			case DClass(declaration):
				classCount++;
				if (declaration.name == requestedName && sourcePackage == requestedPackage)
					requestedClassDeclared = true;
			case DPackage(path): sourcePackage = path == null ? '' : path.join('.');
			case DImport(path, star):
				if (star) {
					loading.remove(relative);
					return fail(importPath, relative, 'wildcard class import could not be expanded safely');
				}
				var dependency = path.join('.');
				importAliases.set(path[path.length - 1], path);
				if (bindings != null && bindings.exists(dependency) && bindings.get(dependency) != null) {
					scope.bindImport(path, bindings.get(dependency));
				} else {
					var nested = loadImport(dependency, depth + 1);
					if (!nested.loaded && nested.expectedSource) {
						loading.remove(relative);
						return fail(importPath, relative,
							'unavailable imported class dependency ' + dependency + ': ' + nested.reason);
					}
					if (!nested.expectedSource) {
						loading.remove(relative);
						return fail(importPath, relative,
							'no explicit owner binding or source module for import ' + dependency);
					}
				}
			case DTypedef(_):
				// A runtime class module may include typedefs that only describe
				// fields, such as Psych's RainShader Light record. Interpreted class
				// fields are dynamically typed, so these declarations need no runtime
				// object. Importing a typedef as the requested class still fails the
				// requestedClassDeclared check below.
		}
		if (classCount == 0) return fail(importPath, relative, 'source module contains no runtime class declaration');
		if (!requestedClassDeclared)
			return fail(importPath, relative, 'owner source module does not declare requested class ' + importPath);
		for (decl in module) switch (decl) {
			case DClass(declaration):
				PsychShaderSourceCompat.prepareClass(declaration, importAliases);
				seedClassFieldDefaults(declaration);
			case _:
		}
		try scope.registerModule(module) catch (error:Dynamic)
			return fail(importPath, relative, 'could not register owner class module: ' + Std.string(error));
		loading.remove(relative);
		loaded.set(relative, true);
		return {expectedSource:true, loaded:true, reason:''};
	}

	/** HScript's parser starts with no target defines. Mirror only capabilities
	 * this runtime actually provides before selecting source #if branches. */
	static function parserForRuntimeSource():ParserEx {
		var parser = new ParserEx();
		#if sys
		parser.preprocesorValues.set('sys', true);
		#end
		#if cpp
		parser.preprocesorValues.set('cpp', true);
		parser.preprocesorValues.set('VIDEOS_ALLOWED', true);
		#end
		return parser;
	}

	/** Haxe constructs every instance field even when the declaration has no
	 * initializer. HScript-ex only adds initialized fields to its variable map,
	 * so later writes to a declared field otherwise raise EUnknownVariable.
	 */
	static function seedClassFieldDefaults(declaration:ClassDecl):Void {
		var parser = new ParserEx();
		var printer = new Printer();
		for (field in declaration.fields) switch (field.kind) {
			case KVar(value):
				if (value.expr != null) continue;
				var literal = 'null';
				if (value.type != null) switch (printer.typeToString(value.type)) {
					case 'Int', 'Float': literal = '0';
					case 'Bool': literal = 'false';
					default:
				}
				value.expr = parser.parseString(literal);
			case _:
		}
	}

	/** Report static source references to unsupported Options fields without
	 * claiming that the expression executed or was read at runtime. The code
	 * mask excludes comments and ordinary string contents; literal `pointer:`
	 * values are then checked separately because the menu resolves those names
	 * dynamically through Reflect.field. */
	public static function unsupportedOptionSourceUses(source:String, relative:String):Array<String> {
		var findings:Array<String> = [];
		var mask = codeMask(source);
		var seen:Map<String, Bool> = new Map();
		for (span in identifierSpans(mask, 'Options')) {
			var dot = skipWhitespace(mask, span.end);
			if (dot >= mask.length || mask.charAt(dot) != '.') continue;
			var fieldStart = skipWhitespace(mask, dot + 1);
			for (field in UNSUPPORTED_OPTION_FIELDS) {
				if (!isWordAt(mask, fieldStart, field)) continue;
				addUnsupportedOptionSourceUse(findings, seen, source, relative,
					field, fieldStart, 'direct Options reference');
				break;
			}
		}

		for (span in identifierSpans(mask, 'pointer')) {
			var previous = previousSignificant(mask, span.start);
			if (previous < 0 || (mask.charAt(previous) != '{' && mask.charAt(previous) != ',')) continue;
			var colon = skipWhitespace(mask, span.end);
			if (colon >= mask.length || mask.charAt(colon) != ':') continue;
			var literalStart = skipWhitespace(source, colon + 1);
			if (literalStart >= source.length || source.charAt(literalStart) != '\'' && source.charAt(literalStart) != '"') continue;
			var quote = source.charAt(literalStart);
			var literalEnd = literalStart + 1;
			var escaped = false;
			while (literalEnd < source.length) {
				var ch = source.charAt(literalEnd);
				if (escaped) escaped = false;
				else if (ch == '\\') escaped = true;
				else if (ch == quote) break;
				literalEnd++;
			}
			if (literalEnd >= source.length || escaped) continue;
			var field = source.substring(literalStart + 1, literalEnd);
			if (UNSUPPORTED_OPTION_FIELDS.indexOf(field) < 0) continue;
			addUnsupportedOptionSourceUse(findings, seen, source, relative,
				field, span.start, 'literal Options pointer');
		}
		return findings;
	}

	static function addUnsupportedOptionSourceUse(findings:Array<String>, seen:Map<String, Bool>,
		source:String, relative:String, field:String, offset:Int, useKind:String):Void {
		var line = sourceLine(source, offset);
		var key = field + ':' + line;
		if (seen.exists(key)) return;
		seen.set(key, true);
		findings.push('[codename-options-source-use] ' + relative + ':' + line
			+ ': unsupported Options.' + field + ' ' + useKind
			+ '; this is static source evidence, not an observed runtime read.');
	}

	static function sourceLine(source:String, offset:Int):Int {
		var line = 1;
		for (index in 0...Std.int(Math.min(offset, source.length)))
			if (source.charAt(index) == '\n') line++;
		return line;
	}

	/** Normalize only the module features for which the class interpreter can
	 * preserve runtime behavior. Anything broader remains a load diagnostic. */
	function normalizeModuleSyntax(source:String, importPath:String, relative:String, depth:Int):{source:String, error:String} {
		// Classless companion scripts already lower Haxe single-quoted
		// interpolation before HScript parsing. Owner class modules use this
		// separate path, so reuse that same transform before parsing the module.
		var interpolation = CodenameScriptParser.normalizeInterpolatedStrings(source);
		if (interpolation.error != '') return {source:source, error:interpolation.error};
		source = interpolation.source;

		var finals = normalizeFinalDeclarations(source);
		if (finals.error != '') return {source:source, error:finals.error};
		source = finals.source;

		var casts = normalizeUntypedPrefixCasts(source);
		if (casts.error != '') return {source:source, error:casts.error};
		source = casts.source;

		var unusedImports = removeUnusedExternalImports(source);
		if (unusedImports.error != '') return {source:source, error:unusedImports.error};
		source = unusedImports.source;

		var aliasesResult = normalizeAliasedImports(source, relative, depth);
		if (aliasesResult.error != '') return {source:source, error:aliasesResult.error};
		source = aliasesResult.source;

		var usingResult = normalizeUsingImports(source);
		if (usingResult.error != '') return {source:source, error:usingResult.error};
		source = usingResult.source;

		var wildcards = expandWildcardImports(source);
		if (wildcards.error != '') return {source:source, error:wildcards.error};
		var generics = normalizeGenericConstructors(wildcards.source, relative, depth);
		if (generics.error != '') return {source:source, error:generics.error};
		var genericTypes = normalizeGenericTypePositions(generics.source);
		if (genericTypes.error != '') return {source:source, error:genericTypes.error};
		var constructors = normalizeSuperConstructorBodies(genericTypes.source);
		if (constructors.error != '') return {source:source, error:constructors.error};
		var indexed = normalizeIndexedModuleLoops(constructors.source);
		if (indexed.error != '') return {source:source, error:indexed.error};
		var ranges = normalizeForRangeArithmetic(indexed.source);
		var enums = normalizeSimpleEnums(ranges);
		if (enums.error != '') return {source:source, error:enums.error};
		return {source:normalizeExpressionBodiedMethods(enums.source), error:''};
	}

	/** Haxe class modules allow a method body to be one expression without
	 * braces, commonly `function get_value() return value;` or a single setter
	 * call. HScript-ex parses the expression but leaves its terminator at class
	 * scope, so the next field read fails on `;`. A single unbraced `if` body
	 * has the same problem. Keep ordinary blocks, comments and strings intact. */
	static function normalizeExpressionBodiedMethods(source:String):String {
		var result = source == null ? '' : source;
		var passes = 0;
		while (passes++ < 96) {
			var mask = codeMask(result);
			var edits:Array<{start:Int, end:Int, value:String}> = [];
			var cursor = 0;
			while (cursor < mask.length) {
				var functionStart = nextWord(mask, 'function', cursor);
				if (functionStart < 0) break;
				var signature = skipWhitespace(mask, functionStart + 'function'.length);
				if (signature < mask.length && isIdentifierStart(mask.charAt(signature))) {
					signature++;
					while (signature < mask.length && isIdentifierChar(mask.charAt(signature))) signature++;
					signature = skipWhitespace(mask, signature);
				}
				if (signature >= mask.length || mask.charAt(signature) != '(') {
					cursor = functionStart + 'function'.length;
					continue;
				}
				var paramsEnd = matchingDelimiter(mask, signature, '(', ')');
				if (paramsEnd < 0) return result;
				var bodyStart = skipWhitespace(mask, paramsEnd + 1);
				if (bodyStart < mask.length && mask.charAt(bodyStart) == ':') {
					var returnType = readGenericType(mask, skipWhitespace(mask, bodyStart + 1));
					if (returnType.error != '') {
						cursor = paramsEnd + 1;
						continue;
					}
					bodyStart = skipWhitespace(mask, returnType.end);
				}
				if (isWordAt(mask, bodyStart, 'return') || isDirectExpressionBody(mask, bodyStart)
					|| isWordAt(mask, bodyStart, 'if')) {
					var bodyEnd = indexedStatementEnd(mask, bodyStart);
					if (bodyEnd > bodyStart && mask.charAt(bodyEnd - 1) == ';') {
						edits.push({start:bodyStart, end:bodyStart, value:'{' });
						edits.push({start:bodyEnd, end:bodyEnd, value:'}' });
						cursor = bodyEnd;
						continue;
					}
				}
				cursor = paramsEnd + 1;
			}
			if (edits.length == 0) return result;
			result = applyEdits(result, edits);
		}
		return result;
	}

	static function isDirectExpressionBody(mask:String, start:Int):Bool {
		if (start >= mask.length || !isIdentifierStart(mask.charAt(start))) return false;
		var end = start + 1;
		while (end < mask.length && isIdentifierChar(mask.charAt(end))) end++;
		return !['if', 'switch', 'for', 'while', 'do', 'try', 'catch', 'function', 'class']
			.contains(mask.substring(start, end));
	}

	/** hscript-ex does not parse Haxe's `for (key => value in iterable)` form.
	 * Rewrite only a direct indexed loop into a lazy pair iterator expression.
	 * Strings, comments, and arrows nested inside the iterable are ignored by the
	 * code mask, while the helper retains live array and map value reads.
	 */
	static function normalizeIndexedModuleLoops(source:String):{source:String, error:String} {
		var result = source;
		var passes = 0;
		while (passes++ < 96) {
			var mask = codeMask(result);
			var loopStart = nextWord(mask, 'for', 0);
			var indexedStart = -1;
			var indexedOpen = -1;
			var indexedClose = -1;
			var indexName = '';
			var valueName = '';
			var iterable = '';
			while (loopStart >= 0) {
				var open = skipWhitespace(mask, loopStart + 3);
				if (open < mask.length && mask.charAt(open) == '(') {
					var close = matchingDelimiter(mask, open, '(', ')');
					if (close < 0) return {source:result, error:'Unclosed for loop header in imported class'};
					var parsed = indexedLoopHeader(result, mask, open + 1, close);
					if (parsed != null) {
						indexedStart = loopStart;
						indexedOpen = open;
						indexedClose = close;
						indexName = parsed.indexName;
						valueName = parsed.valueName;
						iterable = parsed.iterable;
						break;
					}
					loopStart = nextWord(mask, 'for', close + 1);
				} else loopStart = nextWord(mask, 'for', loopStart + 3);
			}
			if (indexedStart < 0) return {source:result, error:''};

			var bodyStart = skipWhitespace(mask, indexedClose + 1);
			var bodyEnd = indexedStatementEnd(mask, bodyStart);
			if (bodyEnd < 0) return {source:result, error:'Indexed for loop in imported class requires a braced body or a single expression statement'};
			var body = result.substring(bodyStart, bodyEnd);
			if (mask.charAt(bodyStart) == '{') body = result.substring(bodyStart + 1, bodyEnd - 1);
			var entryName = '__psychIndexedEntry' + passes;
			var replacement = 'for (' + entryName + ' in CodenameKeyValueIterator.iterate('
				+ iterable + ')) { var ' + indexName + ' = ' + entryName + '.key; var '
				+ valueName + ' = ' + entryName + '.value; ' + body + ' }';
			result = result.substring(0, indexedStart) + replacement + result.substr(bodyEnd);
		}
		return {source:result, error:'Indexed for loop conversion limit reached in imported class'};
	}

	static function indexedLoopHeader(source:String, mask:String, start:Int, end:Int):Null<{indexName:String, valueName:String, iterable:String}> {
		var parens = 0, brackets = 0, braces = 0;
		var arrow = -1;
		var cursor = start;
		while (cursor + 1 < end) {
			var ch = mask.charAt(cursor);
			if (parens == 0 && brackets == 0 && braces == 0 && ch == '=' && mask.charAt(cursor + 1) == '>') {
				arrow = cursor;
				break;
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
			cursor++;
		}
		if (arrow < 0) return null;
		var key = StringTools.trim(mask.substring(start, arrow));
		if (!~/^[A-Za-z_][A-Za-z0-9_]*$/.match(key)) return null;
		cursor = arrow + 2;
		while (cursor < end && isWhitespace(mask.charAt(cursor))) cursor++;
		var valueStart = cursor;
		if (cursor >= end || !isIdentifierStart(mask.charAt(cursor))) return null;
		cursor++;
		while (cursor < end && isIdentifierChar(mask.charAt(cursor))) cursor++;
		var value = mask.substring(valueStart, cursor);
		var afterValue = skipWhitespace(mask, cursor);
		if (!isWordAt(mask, afterValue, 'in')) return null;
		var iterableStart = skipWhitespace(mask, afterValue + 2);
		var expr = StringTools.trim(source.substring(iterableStart, end));
		if (expr == '') return null;
		return {indexName:key, valueName:value, iterable:expr};
	}

	/** Return the full range of a supported loop body, including its braces or
	 * terminating semicolon. Unbraced nested `for` statements are recursively
	 * consumed so the containing indexed loop can safely acquire braces too.
	 */
	static function indexedStatementEnd(mask:String, start:Int):Int {
		if (start >= mask.length) return -1;
		if (mask.charAt(start) == '{') {
			var close = matchingDelimiter(mask, start, '{', '}');
			return close < 0 ? -1 : close + 1;
		}
		if (isWordAt(mask, start, 'for')) {
			var open = skipWhitespace(mask, start + 3);
			if (open >= mask.length || mask.charAt(open) != '(') return -1;
			var close = matchingDelimiter(mask, open, '(', ')');
			if (close < 0) return -1;
			return indexedStatementEnd(mask, skipWhitespace(mask, close + 1));
		}
		if (isWordAt(mask, start, 'if')) {
			var open = skipWhitespace(mask, start + 2);
			if (open >= mask.length || mask.charAt(open) != '(') return -1;
			var close = matchingDelimiter(mask, open, '(', ')');
			if (close < 0) return -1;
			var thenEnd = indexedStatementEnd(mask, skipWhitespace(mask, close + 1));
			if (thenEnd < 0) return -1;
			var next = skipWhitespace(mask, thenEnd);
			return isWordAt(mask, next, 'else')
				? indexedStatementEnd(mask, skipWhitespace(mask, next + 4)) : thenEnd;
		}
		var parens = 0, brackets = 0, braces = 0;
		var cursor = start;
		while (cursor < mask.length) {
			var ch = mask.charAt(cursor);
			if (parens == 0 && brackets == 0 && braces == 0 && ch == ';') return cursor + 1;
			switch (ch) {
				case '(': parens++;
				case ')': if (parens == 0) return -1; parens--;
				case '[': brackets++;
				case ']': if (brackets == 0) return -1; brackets--;
				case '{': braces++;
				case '}': if (braces == 0) return -1; braces--;
				default:
			}
			cursor++;
		}
		return -1;
	}

	static function nextWord(source:String, word:String, start:Int):Int {
		var cursor = start;
		while (cursor < source.length) {
			if (isWordAt(source, cursor, word)) return cursor;
			cursor++;
		}
		return -1;
	}

	static inline function isWhitespace(ch:String):Bool
		return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n';

	/** Haxe binds arithmetic on the right of `...` inside a for iterator.
	 * HScript-ex instead evaluates `(start...end) - n`, leaving a non-iterator.
	 * Parenthesize only a simple, lexical for-range RHS with integer arithmetic. */
	static function normalizeForRangeArithmetic(source:String):String {
		var mask = codeMask(source);
		var pattern = ~/for[ \t\r\n]*\([ \t\r\n]*[A-Za-z_][A-Za-z0-9_]*[ \t\r\n]+in[ \t\r\n]+[0-9]+[ \t\r\n]*\.\.\.[ \t\r\n]*([A-Za-z_][A-Za-z0-9_.]*[ \t]*[-+][ \t]*[0-9]+)[ \t\r\n]*\)/g;
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		var cursor = 0;
		while (pattern.matchSub(mask, cursor)) {
			var span = pattern.matchedPos();
			var matched = source.substr(span.pos, span.len);
			var rhs = pattern.matched(1);
			var at = matched.indexOf(rhs);
			if (at >= 0) {
				var start = span.pos + at;
				edits.push({start:start, end:start + rhs.length, value:'(' + rhs + ')'});
			}
			cursor = span.pos + span.len;
		}
		return applyEdits(source, edits);
	}

	/** Haxe initializes inherited FlxObject positions to zero before a subclass
	 * constructor calls `super`. ScriptClass composes its native base later, so
	 * seed constructor-local x/y only when the explicitly resolved native base
	 * exposes both position fields. Locals shadow the not-yet-created native
	 * object for the authored `super(x, y)` expression and do not alter the native
	 * constructor or other class fields. */
	function normalizeNativePositionDefaults(source:String, module:Array<ModuleDecl>):{source:String, error:String} {
		if (module == null || module.length == 0) return {source:source, error:''};
		var packagePath:Array<String> = null;
		var imports:Map<String, Array<String>> = new Map();
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		var mask = codeMask(source);
		for (decl in module) switch (decl) {
			case DPackage(path): packagePath = path;
			case DImport(path, star):
				if (!star && path != null && path.length > 0) imports.set(path[path.length - 1], path);
			case DClass(declaration):
				if (declaration.extend == null) continue;
				var requester:hscript.ClassDeclEx = {
					imports:imports.copy(), pkg:packagePath == null ? null : packagePath.copy(),
					name:declaration.name, params:declaration.params, meta:declaration.meta,
					isPrivate:declaration.isPrivate, extend:declaration.extend,
					implement:declaration.implement, fields:declaration.fields, isExtern:declaration.isExtern
				};
				var superPath = new Printer().typeToString(declaration.extend);
				if (scope.findDescriptor(superPath, requester) != null) continue;
				var nativeBase = scope.findBinding(superPath, requester);
				if (!isRuntimeClass(nativeBase) || !hasNativeInstanceField(nativeBase, 'x')
					|| !hasNativeInstanceField(nativeBase, 'y')) continue;
				var constructor:hscript.Expr.FunctionDecl = null;
				var hasOwnX = false, hasOwnY = false;
				for (field in declaration.fields) {
					if (field.name == 'x') hasOwnX = true;
					if (field.name == 'y') hasOwnY = true;
					if (field.name == 'new') switch (field.kind) {
						case KFunction(fn): constructor = fn;
						case _:
					}
				}
				if (constructor == null) continue;
				var classOpen = findClassOpen(mask, declaration.name);
				if (classOpen < 0) continue;
				var classClose = matchingDelimiter(mask, classOpen, '{', '}');
				if (classClose < 0) continue;
				var ctor = findConstructorBody(mask, classOpen, classClose);
				if (ctor.open < 0 || ctor.close < 0) continue;
				var constructorMask = mask.substring(ctor.open + 1, ctor.close);
				var args:Map<String, Bool> = new Map();
				for (arg in constructor.args) args.set(arg.name, true);
				var defaults = '';
				if (!hasOwnX && !args.exists('x') && !hasAliasDeclaration(constructorMask, 'x'))
					defaults += '\n\t\tvar x:Float = 0.0;';
				if (!hasOwnY && !args.exists('y') && !hasAliasDeclaration(constructorMask, 'y'))
					defaults += '\n\t\tvar y:Float = 0.0;';
				if (defaults != '') edits.push({start:ctor.open + 1, end:ctor.open + 1, value:defaults});
			default:
		}
		return {source:applyEdits(source, edits), error:''};
	}

	static function hasNativeInstanceField(nativeBase:Dynamic, fieldName:String):Bool {
		try {
			var current:Class<Dynamic> = cast nativeBase;
			while (current != null) {
				var fields = Type.getInstanceFields(current);
				if (fields.indexOf(fieldName) >= 0 || fields.indexOf('get_' + fieldName) >= 0) return true;
				current = Type.getSuperClass(current);
			}
		} catch (_:Dynamic) {}
		return false;
	}

	static function findClassOpen(mask:String, className:String):Int {
		var regex = new EReg('class[ \\t\\r\\n]+' + EReg.escape(className) + '\\b', 'g');
		var cursor = 0;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			cursor = pos.pos + pos.len;
			if (braceDepth(mask, pos.pos) != 0) continue;
			var open = mask.indexOf('{', cursor);
			if (open >= 0) return open;
		}
		return -1;
	}

	static function findConstructorBody(mask:String, classOpen:Int, classClose:Int):{open:Int, close:Int} {
		var regex = new EReg('function[ \\t\\r\\n]+new[ \\t]*\\(', 'g');
		var cursor = classOpen + 1;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			cursor = pos.pos + pos.len;
			if (pos.pos >= classClose) break;
			if (braceDepth(mask, pos.pos) != braceDepth(mask, classOpen) + 1) continue;
			var openParams = mask.indexOf('(', pos.pos);
			var closeParams = matchingDelimiter(mask, openParams, '(', ')');
			if (closeParams < 0) return {open:-1, close:-1};
			var openBody = skipWhitespace(mask, closeParams + 1);
			if (openBody < mask.length && mask.charAt(openBody) == ':') {
				while (openBody < mask.length && mask.charAt(openBody) != '{' && mask.charAt(openBody) != ';') openBody++;
			}
			if (openBody >= classClose || mask.charAt(openBody) != '{') continue;
			var closeBody = matchingDelimiter(mask, openBody, '{', '}');
			return {open:openBody, close:closeBody};
		}
		return {open:-1, close:-1};
	}

	/** HScript-ex has no module enum declaration. Lower only ordinary, payload-free
	 * enums to their constructor names as strings. This preserves the value behavior
	 * used by owner class state machines (assignment, equality, switch, Std.string)
	 * without pretending to support enum payloads, abstracts, or generic enums. */
	static function normalizeSimpleEnums(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var declarations:Array<{name:String, start:Int, end:Int, constructors:Array<String>}> = [];
		var names:Map<String, Bool> = new Map();
		var owners:Map<String, String> = new Map();		// Constructor name -> owning enum, when unique.
		var ambiguous:Map<String, Bool> = new Map();
		var cursor = 0;
		while (cursor < mask.length) {
			if (!isWordAt(mask, cursor, 'enum') || braceDepth(mask, cursor) != 0) {
				cursor++;
				continue;
			}
			var enumStart = cursor;
			var previous = previousSignificant(mask, enumStart);
			var previousStart = previous;
			while (previousStart >= 0 && isIdentifierChar(mask.charAt(previousStart))) previousStart--;
			var previousWord = previous < 0 ? '' : mask.substring(previousStart + 1, previous + 1);
			if (previousWord == 'abstract')
				return {source:source, error:'abstract enum declarations have no HScript-ex runtime representation'};

			var nameStart = skipWhitespace(mask, enumStart + 'enum'.length);
			var nameEnd = nameStart;
			while (nameEnd < mask.length && isIdentifierChar(mask.charAt(nameEnd))) nameEnd++;
			var enumName = mask.substring(nameStart, nameEnd);
			if (!safeModuleName(enumName))
				return {source:source, error:'unsupported enum declaration; expected a plain named enum'};
			if (names.exists(enumName))
				return {source:source, error:'duplicate simple enum declaration: ' + enumName};
			var open = skipWhitespace(mask, nameEnd);
			if (open < mask.length && mask.charAt(open) == '<')
				return {source:source, error:'generic enum declarations have no HScript-ex runtime representation: ' + enumName};
			if (open >= mask.length || mask.charAt(open) != '{')
				return {source:source, error:'unsupported enum declaration; only plain enum bodies are supported: ' + enumName};

			var close = matchingDelimiter(mask, open, '{', '}');
			if (close < 0)
				return {source:source, error:'unterminated simple enum declaration: ' + enumName};
			var enumConstructors:Array<String> = [];
			var fieldCursor = open + 1;
			while (true) {
				fieldCursor = skipWhitespace(mask, fieldCursor);
				if (fieldCursor >= close) break;
				var fieldStart = fieldCursor;
				while (fieldCursor < close && isIdentifierChar(mask.charAt(fieldCursor))) fieldCursor++;
				var constructor = mask.substring(fieldStart, fieldCursor);
				if (!safeModuleName(constructor))
					return {source:source, error:'unsupported simple enum constructor in ' + enumName};
				var delimiter = skipWhitespace(mask, fieldCursor);
				if (delimiter < close && ['(', ':', '<'].indexOf(mask.charAt(delimiter)) >= 0)
					return {source:source, error:'enum constructor payloads are not supported: ' + enumName + '.' + constructor};
				if (enumConstructors.indexOf(constructor) >= 0)
					return {source:source, error:'duplicate simple enum constructor: ' + enumName + '.' + constructor};
				enumConstructors.push(constructor);
				if (delimiter == close) {
					fieldCursor = close;
					break;
				}
				var separator = mask.charAt(delimiter);
				if (separator != ';' && separator != ',')
					return {source:source, error:'unsupported simple enum constructor separator in ' + enumName};
				fieldCursor = delimiter + 1;
			}
			if (enumConstructors.length == 0)
				return {source:source, error:'empty simple enum declarations are not supported: ' + enumName};

			names.set(enumName, true);
			for (constructor in enumConstructors) {
				if (owners.exists(constructor)) ambiguous.set(constructor, true);
				else owners.set(constructor, enumName);
			}
			declarations.push({name:enumName, start:enumStart, end:close + 1, constructors:enumConstructors});
			cursor = close + 1;
		}
		if (declarations.length == 0) return {source:source, error:''};

		var enumRanges:Array<{start:Int, end:Int}> = [];
		for (declaration in declarations) enumRanges.push({start:declaration.start, end:declaration.end});
		var searchMask = replaceRangesWithSpaces(mask, enumRanges);
		for (declaration in declarations) {
			if (hasAliasDeclaration(searchMask, declaration.name))
				return {source:source, error:'simple enum name shadows another module declaration: ' + declaration.name};
			for (constructor in declaration.constructors) {
				if (hasAliasDeclaration(searchMask, constructor))
					return {source:source, error:'simple enum constructor shadows another module declaration: ' + constructor};
			}
		}

		var edits:Array<{start:Int, end:Int, value:String}> = [];
		for (declaration in declarations)
			edits.push({start:declaration.start, end:declaration.end,
				value:spaces(source.substring(declaration.start, declaration.end))});

		for (declaration in declarations) {
			var constructors:Map<String, Bool> = new Map();
			for (constructor in declaration.constructors) constructors.set(constructor, true);
			for (span in identifierSpans(mask, declaration.name)) {
				if (insideRanges(span.start, enumRanges)) continue;
				var previousToken = previousSignificant(mask, span.start);
				if (previousToken >= 0 && mask.charAt(previousToken) == '.') continue;
				var dot = skipWhitespace(mask, span.end);
				if (dot >= mask.length || mask.charAt(dot) != '.') continue;
				var memberStart = skipWhitespace(mask, dot + 1);
				var memberEnd = memberStart;
				while (memberEnd < mask.length && isIdentifierChar(mask.charAt(memberEnd))) memberEnd++;
				var constructor = mask.substring(memberStart, memberEnd);
				if (!constructors.exists(constructor)) continue;
				if (memberEnd == memberStart)
					return {source:source, error:'malformed qualified simple enum constructor: ' + declaration.name};
				edits.push({start:span.start, end:memberEnd, value:'"' + constructor + '"'});
			}
			for (constructor in declaration.constructors) {
				for (span in identifierSpans(mask, constructor)) {
					if (insideRanges(span.start, enumRanges)) continue;
					var previousToken = previousSignificant(mask, span.start);
					if (previousToken >= 0 && mask.charAt(previousToken) == '.') continue;
					if (ambiguous.exists(constructor))
						return {source:source, error:'ambiguous unqualified simple enum constructor: ' + constructor};
					edits.push({start:span.start, end:span.end, value:'"' + constructor + '"'});
				}
			}
		}
		return {source:applyEdits(source, edits), error:''};
	}

	static function insideRanges(position:Int, ranges:Array<{start:Int, end:Int}>):Bool {
		for (range in ranges) if (position >= range.start && position < range.end) return true;
		return false;
	}

	/** ParserEx class fields do not consume a trailing semicolon after an
	 * expression-bodied method. Haxe permits the compact constructor spelling
	 * `function new(...) super(...);`; removing only that field terminator keeps
	 * the same single superclass-constructor call and avoids rewriting arbitrary
	 * expression bodies. */
	static function normalizeSuperConstructorBodies(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		var regex = new EReg('function[ \\t\\r\\n]+new[ \\t]*\\(', 'g');
		var cursor = 0;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			cursor = pos.pos + pos.len;
			if (braceDepth(mask, pos.pos) != 1) continue;
			var open = mask.indexOf('(', pos.pos);
			var close = matchingDelimiter(mask, open, '(', ')');
			if (close < 0) return {source:source, error:'malformed expression-bodied constructor parameters'};
			var body = skipWhitespace(mask, close + 1);
			if (!isWordAt(mask, body, 'super')) continue;
			var superOpen = skipWhitespace(mask, body + 'super'.length);
			if (superOpen >= mask.length || mask.charAt(superOpen) != '(') continue;
			var superClose = matchingDelimiter(mask, superOpen, '(', ')');
			if (superClose < 0) return {source:source, error:'malformed expression-bodied superclass constructor call'};
			var terminator = skipWhitespace(mask, superClose + 1);
			if (terminator >= mask.length || mask.charAt(terminator) != ';') continue;
			var next = skipWhitespace(mask, terminator + 1);
			if (next < mask.length && mask.charAt(next) != '}'
				&& !startsClassField(mask, next)) continue;
			edits.push({start:terminator, end:terminator + 1, value:' '});
		}
		return {source:applyEdits(source, edits), error:''};
	}

	static function startsClassField(mask:String, start:Int):Bool {
		if (start >= mask.length) return false;
		if (mask.charAt(start) == '@') return true;
		for (keyword in ['public', 'private', 'static', 'inline', 'override', 'var', 'function', 'extern', 'macro'])
			if (isWordAt(mask, start, keyword)) return true;
		return false;
	}

	/** Haxe's untyped `cast expr` only changes static typing; there is no target
	 * type or runtime check to preserve in HScript. Erase only the keyword in a
	 * provable prefix-expression position. Parenthesized forms are ambiguous with
	 * `cast(expr, Type)` and remain explicit load failures. */
	function normalizeUntypedPrefixCasts(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		var cursor = 0;
		while (cursor < mask.length) {
			if (!isWordAt(mask, cursor, 'cast')) { cursor++; continue; }
			var next = skipWhitespace(mask, cursor + 4);
			var previous = previousSignificant(mask, cursor);
			if (previous >= 0 && mask.charAt(previous) == '.') { cursor += 4; continue; }
			if (next < mask.length && mask.charAt(next) == ':') { cursor += 4; continue; }
			if (next < mask.length && mask.charAt(next) == '(')
				return {source:source, error:'typed or parenthesized cast syntax is unsupported'};
			if (!isUntypedCastPrefix(mask, cursor))
				return {source:source, error:'cast token is not in a provable untyped prefix expression position'};
			if (!hasCastOperand(source, cursor + 4))
				return {source:source, error:'untyped cast has no expression operand'};
			edits.push({start:cursor, end:cursor + 4, value:spaces(source.substring(cursor, cursor + 4))});
			cursor += 4;
		}
		return {source:applyEdits(source, edits), error:''};
	}

	static function isUntypedCastPrefix(mask:String, start:Int):Bool {
		var previous = previousSignificant(mask, start);
		if (previous < 0) return true;
		var ch = mask.charAt(previous);
		if ('([{,:;=?!+-*/%&|^~<>)'.indexOf(ch) >= 0) return true;
		if (!isIdentifierChar(ch)) return false;
		var wordStart = previous;
		while (wordStart > 0 && isIdentifierChar(mask.charAt(wordStart - 1))) wordStart--;
		var word = mask.substring(wordStart, previous + 1);
		return ['return', 'throw', 'case', 'in', 'else', 'do'].indexOf(word) >= 0;
	}

	static function previousSignificant(mask:String, start:Int):Int {
		var cursor = start - 1;
		while (cursor >= 0 && [' ', '\t', '\r', '\n'].indexOf(mask.charAt(cursor)) >= 0) cursor--;
		return cursor;
	}

	/** Check the raw next token so string literals, which codeMask intentionally
	 * blanks, still count as operands. Comments between cast and operand are
	 * skipped; parser validation handles the operand's remaining grammar. */
	static function hasCastOperand(source:String, start:Int):Bool {
		var cursor = start;
		while (cursor < source.length) {
			var ch = source.charAt(cursor);
			var next = cursor + 1 < source.length ? source.charAt(cursor + 1) : '';
			if ([' ', '\t', '\r', '\n'].indexOf(ch) >= 0) { cursor++; continue; }
			if (ch == '/' && next == '/') {
				cursor += 2;
				while (cursor < source.length && source.charAt(cursor) != '\n' && source.charAt(cursor) != '\r') cursor++;
				continue;
			}
			if (ch == '/' && next == '*') {
				var close = source.indexOf('*/', cursor + 2);
				if (close < 0) return false;
				cursor = close + 2;
				continue;
			}
			return [';', ')', ']', '}', ','].indexOf(ch) < 0;
		}
		return false;
	}

	/** Remove only unreferenced, explicit imports that are not owner source
	 * modules or already-bound names. Import declarations have no Haxe runtime
	 * effect; retaining owner modules preserves this loader's descriptor graph.
	 * The use proof ignores comments/strings and compares whole identifiers, so
	 * a used abstract enum still reaches the normal unsupported-import diagnostic. */
	function removeUnusedExternalImports(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var records:Array<{path:String, start:Int, end:Int}> = [];
		var regex = new EReg('import[ \\t\\r\\n]+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)[ \\t\\r\\n]*;', 'g');
		var cursor = 0;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			if (braceDepth(mask, pos.pos) == 0)
				records.push({path:regex.matched(1), start:pos.pos, end:pos.pos + pos.len});
			cursor = pos.pos + pos.len;
		}
		if (records.length == 0) return {source:source, error:''};

		var ranges:Array<{start:Int, end:Int}> = [];
		for (record in records) ranges.push({start:record.start, end:record.end});
		var searchMask = replaceRangesWithSpaces(mask, ranges);
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		for (record in records) {
			if (!validImport(record.path) || hasIdentifier(searchMask, record.path.split('.').pop())) continue;
			if (findSourceModule(record.path) != null) continue;
			if (bindings != null && bindings.get(record.path) != null) continue;
			edits.push({start:record.start, end:record.end,
				value:spaces(source.substring(record.start, record.end))});
		}
		return {source:applyEdits(source, edits), error:''};
	}

	/** HScript's `new` parser has no type-parameter grammar. Erase only a
	 * balanced, simple type-path list after a constructor type that resolves to
	 * an owner class or native runtime class. Haxe generic parameters are erased
	 * at runtime, so this keeps the constructor and argument evaluation intact. */
	function normalizeGenericConstructors(source:String, relative:String, depth:Int):{source:String, error:String} {
		var mask = codeMask(source);
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		var cursor = 0;
		while (cursor < mask.length) {
			if (!isWordAt(mask, cursor, 'new')) { cursor++; continue; }
			var typeStart = skipWhitespace(mask, cursor + 3);
			var path = readTypePath(mask, typeStart);
			if (path.path == '') {
				if (typeStart < mask.length && mask.charAt(typeStart) == '<')
					return {source:source, error:'malformed explicit constructor type parameters: missing constructor type path'};
				cursor = typeStart;
				continue;
			}
			var open = skipWhitespace(mask, path.end);
			if (!path.valid && open < mask.length && mask.charAt(open) == '<')
				return {source:source, error:'malformed explicit constructor type parameters for ' + path.path + ': incomplete constructor type path'};
			if (open >= mask.length || mask.charAt(open) != '<') { cursor = path.end; continue; }
			var parameters = parseTypeParameterList(mask, open);
			if (parameters.error != '')
				return {source:source, error:'malformed explicit constructor type parameters for ' + path.path + ': ' + parameters.error};
			var after = skipWhitespace(mask, parameters.end + 1);
			if (after >= mask.length || mask.charAt(after) != '(')
				return {source:source, error:'explicit constructor type parameters for ' + path.path + ' are not followed by a constructor call'};
			var resolved = resolveGenericConstructor(path.path, parameters.args, source, relative, depth);
			if (resolved.error != '') return {source:source, error:resolved.error};
			if (resolved.name != path.path)
				edits.push({start:typeStart, end:path.end, value:resolved.name});
			edits.push({start:open, end:parameters.end + 1,
				value:spaces(source.substring(open, parameters.end + 1))});
			cursor = after + 1;
		}
		return {source:applyEdits(source, edits), error:''};
	}

	/** HScript-ex accepts generic constructor expressions after erasure, but its
	 * class parser rejects generic type arguments in field, local, parameter,
	 * return, and inheritance type positions. Erase only balanced lists with a
	 * clear type-position introducer; ordinary expressions such as `factory<T>()`
	 * are left untouched for an explicit parser diagnostic.
	 */
	static function normalizeGenericTypePositions(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		var cursor = 0;
		while (cursor < mask.length) {
			if (mask.charAt(cursor) == ':' && isTypeAnnotationColon(mask, cursor)) {
				var parsed = genericTypeArgumentsAt(mask, skipWhitespace(mask, cursor + 1));
				if (parsed.error != '')
					return {source:source, error:'unsupported generic type annotation: ' + parsed.error};
				if (parsed.end >= 0) {
					edits.push({start:parsed.start, end:parsed.end + 1,
						value:spaces(source.substring(parsed.start, parsed.end + 1))});
					cursor = parsed.end + 1;
					continue;
				}
			}
			if (isWordAt(mask, cursor, 'extends') || isWordAt(mask, cursor, 'implements')) {
				var typeStart = skipWhitespace(mask, cursor + (isWordAt(mask, cursor, 'extends') ? 7 : 10));
				var listCursor = typeStart;
				while (listCursor < mask.length) {
					var path = readTypePath(mask, listCursor);
					if (path.path == '' || !path.valid) break;
					var open = skipWhitespace(mask, path.end);
					listCursor = open;
					if (open < mask.length && mask.charAt(open) == '<') {
						var parameters = parseTypeParameterList(mask, open);
						if (parameters.error != '')
							return {source:source, error:'unsupported generic inheritance type ' + path.path + ': ' + parameters.error};
						if (!validGenericTypeBoundary(mask, parameters.end + 1, true)) break;
						edits.push({start:open, end:parameters.end + 1,
							value:spaces(source.substring(open, parameters.end + 1))});
						listCursor = skipWhitespace(mask, parameters.end + 1);
				}
					if (listCursor >= mask.length || mask.charAt(listCursor) != ',') break;
					listCursor = skipWhitespace(mask, listCursor + 1);
				}
				cursor = listCursor;
				continue;
			}
			cursor++;
		}
		return {source:applyEdits(source, edits), error:''};
	}

	static function genericTypeArgumentsAt(mask:String, typeStart:Int):{start:Int, end:Int, error:String} {
		var path = readTypePath(mask, typeStart);
		if (path.path == '' || !path.valid) return {start:-1, end:-1, error:''};
		var open = skipWhitespace(mask, path.end);
		if (open >= mask.length || mask.charAt(open) != '<') return {start:-1, end:-1, error:''};
		var parameters = parseTypeParameterList(mask, open);
		if (parameters.error != '') {
			// Structural field types have commas and semicolons inside braces.
			// They need no runtime type after the enclosing generic is erased.
			if (mask.charAt(skipWhitespace(mask, open + 1)) != '{')
				return {start:open, end:parameters.end, error:parameters.error};
			var structuralEnd = structuralGenericEnd(mask, open);
			if (structuralEnd < 0)
				return {start:open, end:parameters.end, error:'unclosed structural generic type'};
			if (!validGenericTypeBoundary(mask, structuralEnd + 1, false))
				return {start:-1, end:-1, error:''};
			return {start:open, end:structuralEnd, error:''};
		}
		if (!validGenericTypeBoundary(mask, parameters.end + 1, false)) return {start:-1, end:-1, error:''};
		return {start:open, end:parameters.end, error:''};
	}

	static function structuralGenericEnd(mask:String, open:Int):Int {
		var angle = 1;
		var braces = 0;
		for (cursor in open + 1...mask.length) {
			switch (mask.charAt(cursor)) {
				case '{': braces++;
				case '}': if (--braces < 0) return -1;
				case '<': angle++;
				case '>':
					if (cursor > open && mask.charAt(cursor - 1) == '-') continue;
					if (--angle == 0) return braces == 0 ? cursor : -1;
				case ';': if (braces == 0 && angle == 1) return -1;
				default:
			}
		}
		return -1;
	}

	static function validGenericTypeBoundary(mask:String, after:Int, inheritance:Bool):Bool {
		var cursor = skipWhitespace(mask, after);
		if (cursor >= mask.length) return true;
		if (',;=)}?>'.indexOf(mask.charAt(cursor)) >= 0) return true;
		if (mask.charAt(cursor) == '-' && cursor + 1 < mask.length && mask.charAt(cursor + 1) == '>') return true;
		return inheritance && (isWordAt(mask, cursor, 'implements') || isWordAt(mask, cursor, 'where'));
	}

	static function isTypeAnnotationColon(mask:String, colon:Int):Bool {
		var previous = previousSignificant(mask, colon);
		if (previous < 0) return false;
		if (mask.charAt(previous) == ')') return true;
		if (!isIdentifierChar(mask.charAt(previous))) return false;

		// Parameter annotations are identified by their unmatched signature
		// parenthesis, so map literal fields inside method bodies are not treated
		// as type declarations.
		var stack:Array<Int> = [];
		for (index in 0...colon) {
			switch (mask.charAt(index)) {
				case '(': stack.push(index);
				case ')': if (stack.length > 0) stack.pop();
				case _:
			}
		}
		var signatureIndex = stack.length - 1;
		while (signatureIndex >= 0) {
			var open = stack[signatureIndex];
			var prefix = StringTools.trim(mask.substring(0, open));
			var functionName = ~/function[ \t\r\n]+[A-Za-z_][A-Za-z0-9_]*$/.match(prefix);
			if (functionName || ~/function$/.match(prefix)) return true;
			signatureIndex--;
		}

		// Variable and field annotations occur in a declaration segment before
		// its initializer. Skip braces/statement boundaries so object literal
		// members in the initializer do not inherit the declaration context.
		var segmentStart = colon;
		while (segmentStart > 0 && [';', '{', '}'].indexOf(mask.charAt(segmentStart - 1)) < 0) segmentStart--;
		var tail = mask.substring(segmentStart, colon);
		var lastComma = tail.lastIndexOf(',');
		if (lastComma >= 0) tail = tail.substr(lastComma + 1);
		if (tail.indexOf('=') >= 0) return false;
		return ~/\b(var|final)\b/.match(tail);
	}

	function resolveGenericConstructor(typeName:String, parameters:Array<String>, source:String,
		relative:String, depth:Int):{name:String, error:String} {
		var imported = importedTypePaths(source, typeName);
		if (imported.length > 1)
			return {name:typeName, error:'ambiguous generic constructor type ' + typeName + ' from imports ' + imported.join(', ')};

		var descriptor = scope.findDescriptor(typeName);
		if (descriptor != null) return {name:descriptorFullName(descriptor), error:''};
		var bound = scope.findBinding(typeName);
		if (isRuntimeClass(bound)) return {name:typeName, error:''};

		// `Map` is a Haxe abstract, not a runtime class. Its supported native
		// specializations are selected by key type, as Haxe does at runtime.
		if (typeName == 'Map') {
			if (parameters.length != 2)
				return {name:typeName, error:'generic Map constructor requires exactly two type parameters'};
			var mapClass = parameters[0] == 'String' ? 'haxe.ds.StringMap'
				: parameters[0] == 'Int' ? 'haxe.ds.IntMap' : '';
			if (mapClass == '')
				return {name:typeName, error:'generic Map constructor key type ' + parameters[0] + ' has no proven runtime map implementation'};
			if (Type.resolveClass(mapClass) == null)
				return {name:typeName, error:'generic Map constructor backing class is unavailable: ' + mapClass};
			return {name:mapClass, error:''};
		}

		var candidates:Array<String> = [];
		if (typeName.indexOf('.') >= 0) candidates.push(typeName);
		else if (imported.length == 1) candidates.push(imported[0]);
		else {
			var packagePath = ownerPackage(relative);
			if (packagePath != '') candidates.push(packagePath + '.' + typeName);
			if (Type.resolveClass(typeName) != null) return {name:typeName, error:''};
		}

		for (candidate in candidates) {
			var importedDescriptor = scope.findDescriptor(candidate);
			if (importedDescriptor != null) return {name:descriptorFullName(importedDescriptor), error:''};
			var importedBinding = scope.findBinding(candidate);
			if (isRuntimeClass(importedBinding) || Type.resolveClass(candidate) != null)
				return {name:candidate, error:''};
			var relativeSource = findSourceModule(candidate);
			if (relativeSource != null) {
				var nested = loadImport(candidate, depth + 1);
				if (!nested.loaded)
					return {name:typeName, error:'generic constructor owner type ' + candidate + ' could not be loaded: ' + nested.reason};
				var loadedDescriptor = scope.findDescriptor(candidate);
				if (loadedDescriptor != null) return {name:descriptorFullName(loadedDescriptor), error:''};
				// A module already being parsed is the current owner class. Its
				// descriptor is registered immediately after this normalization.
				if (relativeSource == relative && loading.exists(relative)) return {name:candidate, error:''};
				return {name:typeName, error:'generic constructor owner source does not declare class ' + candidate};
			}
		}
		return {name:typeName, error:'generic constructor type ' + typeName + ' is not a known owner or native class'};
	}

	static function parseTypeParameterList(mask:String, open:Int):{end:Int, args:Array<String>, error:String} {
		var args:Array<String> = [];
		var cursor = skipWhitespace(mask, open + 1);
		if (cursor >= mask.length) return {end:open, args:args, error:'unmatched opening <'};
		if (mask.charAt(cursor) == '>') return {end:cursor, args:args, error:'empty type-parameter list'};
		while (cursor < mask.length) {
			var type = readGenericType(mask, cursor);
			if (type.error != '') return {end:cursor, args:args, error:type.error};
			args.push(type.name);
			cursor = skipWhitespace(mask, type.end);
			if (cursor >= mask.length) return {end:cursor, args:args, error:'unmatched opening <'};
			switch (mask.charAt(cursor)) {
				case ',':
					cursor = skipWhitespace(mask, cursor + 1);
					if (cursor >= mask.length || mask.charAt(cursor) == ',' || mask.charAt(cursor) == '>')
						return {end:cursor, args:args, error:'empty type parameter'};
				case '>': return {end:cursor, args:args, error:''};
				default: return {end:cursor, args:args, error:'expected , or > in type-parameter list'};
			}
		}
		return {end:cursor, args:args, error:'unmatched opening <'};
	}

	static function readGenericType(mask:String, start:Int):{end:Int, name:String, error:String} {
		var path = readTypePath(mask, start);
		if (path.path == '') return {end:start, name:'', error:'expected a simple type path'};
		var cursor = skipWhitespace(mask, path.end);
		var name = path.path;
		if (cursor < mask.length && mask.charAt(cursor) == '<') {
			var nested = parseTypeParameterList(mask, cursor);
			if (nested.error != '') return {end:nested.end, name:'', error:nested.error};
			name += '<' + nested.args.join(',') + '>';
			cursor = nested.end + 1;
		}
		return {end:cursor, name:name, error:''};
	}

	static function readTypePath(mask:String, start:Int):{end:Int, path:String, valid:Bool} {
		var cursor = skipWhitespace(mask, start);
		var parts:Array<String> = [];
		var valid = true;
		while (cursor < mask.length) {
			if (!isIdentifierStart(mask.charAt(cursor))) break;
			var end = cursor + 1;
			while (end < mask.length && isIdentifierChar(mask.charAt(end))) end++;
			parts.push(mask.substring(cursor, end));
			cursor = skipWhitespace(mask, end);
			if (cursor >= mask.length || mask.charAt(cursor) != '.') break;
			cursor = skipWhitespace(mask, cursor + 1);
			if (cursor >= mask.length || !isIdentifierStart(mask.charAt(cursor))) {
				valid = false;
				break;
			}
		}
		return {end:cursor, path:parts.join('.'), valid:valid};
	}

	static function importedTypePaths(source:String, typeName:String):Array<String> {
		if (typeName.indexOf('.') >= 0) return [];
		var result:Array<String> = [];
		var mask = codeMask(source);
		var regex = new EReg('import[ \\t\\r\\n]+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)[ \\t\\r\\n]*;', 'g');
		var cursor = 0;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			if (braceDepth(mask, pos.pos) == 0) {
				var path = regex.matched(1);
				var parts = path.split('.');
				if (parts[parts.length - 1] == typeName && result.indexOf(path) < 0) result.push(path);
			}
			cursor = pos.pos + pos.len;
		}
		return result;
	}

	static function ownerPackage(relative:String):String {
		if (relative == null || relative.indexOf('source/') != 0) return '';
		var slash = relative.lastIndexOf('/');
		if (slash <= 'source/'.length) return '';
		return relative.substring('source/'.length, slash).split('/').join('.');
	}

	static function descriptorFullName(descriptor:hscript.ClassDeclEx):String {
		return descriptor.pkg == null || descriptor.pkg.length == 0
			? descriptor.name : descriptor.pkg.join('.') + '.' + descriptor.name;
	}

	static function isRuntimeClass(value:Dynamic):Bool {
		if (value == null) return false;
		try return Type.getClassName(cast value) != null catch (_:Dynamic) return false;
	}

	/** Haxe final is a compile-time restriction. Accept only initialized final
	 * locals/fields without direct reassignment; these have the same value
	 * behavior in HScript-ex once represented as ordinary script variables. */
	static function normalizeFinalDeclarations(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		var declarations:Array<{name:String, start:Int, end:Int}> = [];
		var cursor = 0;
		while (cursor < mask.length) {
			if (!isWordAt(mask, cursor, 'final')) { cursor++; continue; }
			var start = cursor;
			var after = skipWhitespace(mask, cursor + 5);
			if (isWordAt(mask, after, 'var')) {
				edits.push({start:start, end:cursor + 5, value:''});
				cursor += 5;
				continue;
			}
			var nameEnd = after;
			while (nameEnd < mask.length && isIdentifierChar(mask.charAt(nameEnd))) nameEnd++;
			var name = mask.substring(after, nameEnd);
			if (!safeModuleName(name))
				return {source:source, error:'unsupported final syntax; only initialized final variables are supported'};
			var assignment = findDeclarationAssignment(mask, nameEnd);
			if (assignment < 0)
				return {source:source, error:'final variable ' + name + ' has no initializer and cannot be normalized safely'};
			var end = findDeclarationEnd(mask, nameEnd);
			if (end < 0) end = assignment + 1;
			declarations.push({name:name, start:start, end:end});
			edits.push({start:start, end:cursor + 5, value:'var'});
			cursor += 5;
		}
		for (declaration in declarations)
			if (hasAssignmentTo(mask, declaration.name, declaration.start, declaration.end))
				return {source:source, error:'final variable ' + declaration.name + ' is reassigned; final syntax was not normalized'};
		return {source:applyEdits(source, edits), error:''};
	}

	/** Normalize `import path.Type as Alias;`. Native aliases are bound only
	 * when unambiguous. Source class aliases are rewritten to the imported type
	 * only if no declaration in this module shadows the alias. */
	function normalizeAliasedImports(source:String, relative:String, depth:Int):{source:String, error:String} {
		var mask = codeMask(source);
		var records:Array<{path:String, alias:String, start:Int, end:Int, pathEnd:Int}> = [];
		var regex = new EReg('import[ \\t\\r\\n]+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)[ \\t\\r\\n]+as[ \\t\\r\\n]+([A-Za-z_][A-Za-z0-9_]*)[ \\t\\r\\n]*;', 'g');
		var cursor = 0;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			if (braceDepth(mask, pos.pos) == 0) {
				var path = regex.matched(1);
				var alias = regex.matched(2);
				if (!validImport(path)) return {source:source, error:'unsafe aliased class import: ' + path};
				var pathEnd = mask.indexOf(path, pos.pos) + path.length;
				records.push({path:path, alias:alias, start:pos.pos, end:pos.pos + pos.len, pathEnd:pathEnd});
			}
			cursor = pos.pos + pos.len;
		}
		if (records.length == 0) return {source:source, error:''};

		var edits:Array<{start:Int, end:Int, value:String}> = [];
		for (record in records) {
			var value:Dynamic = bindings == null ? null : bindings.get(record.path);
			if (value != null) {
				var aliasError = bindAlias(record.alias, value, record.path);
				if (aliasError != '') return {source:source, error:aliasError};
			} else {
				var nested = loadImport(record.path, depth + 1);
				if (!nested.loaded)
					return {source:source, error:'unavailable imported alias ' + record.path + ' as ' + record.alias + ': ' + nested.reason};
				var targetName = record.path.split('.').pop();
				if (record.alias != targetName) {
					if (hasAliasDeclaration(mask, record.alias))
						return {source:source, error:'import alias ' + record.alias + ' shadows a module declaration; alias was not normalized'};
					for (span in identifierSpans(mask, record.alias)) {
						var insideImport = false;
						for (other in records) if (span.start >= other.start && span.end <= other.end) insideImport = true;
						if (!insideImport) edits.push({start:span.start, end:span.end, value:targetName});
					}
				}
			}
			edits.push({start:record.pathEnd, end:record.end - 1,
				value:spaces(source.substring(record.pathEnd, record.end - 1))});
		}
		return {source:applyEdits(source, edits), error:''};
	}

	function bindAlias(alias:String, value:Dynamic, importedPath:String):String {
		if (alias == null || alias == '' || value == null) return 'invalid imported class alias for ' + importedPath;
		var existing = scope.findBinding(alias);
		if (existing != null && existing != value) return 'import alias ' + alias + ' conflicts with an owner binding';
		if (aliases.exists(alias) && aliases.get(alias) != value)
			return 'import alias ' + alias + ' resolves to multiple owner bindings';
		aliases.set(alias, value);
		scope.bindImport([alias], value);
		return '';
	}

	/** StringTools extension calls from a module declaration or the owner's
	 * source/import.hx are lowered only for proven String receivers. This
	 * avoids guessing Haxe's extension resolution for arbitrary Dynamic data. */
	function normalizeUsingImports(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var ranges:Array<{start:Int, end:Int}> = [];
		var regex = new EReg('using[ \\t\\r\\n]+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)[ \\t\\r\\n]*;', 'g');
		var cursor = 0;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			if (braceDepth(mask, pos.pos) == 0) {
				var path = regex.matched(1);
				if (path != 'StringTools') return {source:source, error:'unsupported using import: ' + path};
				ranges.push({start:pos.pos, end:pos.pos + pos.len});
			}
			cursor = pos.pos + pos.len;
		}
		if (ranges.length == 0 && !ownerUsesStringTools) return {source:source, error:''};
		var typed = stringTypedIdentifiers(mask);
		source = replaceRangesWithSpaces(source, ranges);
		var helperUsed = false;
		var passes = 0;
		var searchCursor = 0;
		while (passes++ < 128) {
			mask = codeMask(source);
			var call = findStringToolsCall(source, mask, searchCursor);
			if (call == null) break;
			var provenString = typed.get(call.receiver) == true
				|| isTypedStringCaseResult(call.receiver, typed)
				|| isNativeFlxSpriteAnimationName(mask, call.receiver)
				|| isBoundStringFieldPath(call.receiver);
			if (call.receiver == '' || !provenString) {
				if (!ownerUsesStringTools)
					return {source:source, error:'using StringTools call ' + call.receiver + '.' + call.method + ' has no statically proven String receiver'};
				// The owner's global using can reach typed fields outside this
				// module. Keep unknown and non-String calls intact: InterpEx
				// dispatches StringTools only for a live String receiver.
				searchCursor = call.end;
				continue;
			}
			var replacement = 'StringTools.' + call.method + '(' + call.receiver;
			if (call.arguments != '') replacement += ', ' + call.arguments;
			replacement += ')';
			source = source.substring(0, call.start) + replacement + source.substr(call.end);
			helperUsed = true;
			searchCursor = 0;
		}
		if (passes >= 128) return {source:source, error:'using StringTools conversion limit reached'};
		if (helperUsed) scope.bindImport(['StringTools'], StringTools);
		return {source:source, error:''};
	}

	/** A host binding may publish exact nested paths whose runtime value is a
	 * String. This lets owner scripts use Haxe extension syntax on small,
	 * explicitly described compatibility facades without treating arbitrary
	 * Dynamic property chains as Strings. */
	function isBoundStringFieldPath(receiver:String):Bool {
		if (bindings == null || receiver == null) return false;
		var dot = receiver.indexOf('.');
		if (dot <= 0 || dot >= receiver.length - 1) return false;
		var root = receiver.substring(0, dot);
		var path = receiver.substr(dot + 1);
		for (bindingPath in bindings.keys()) {
			var parts = bindingPath.split('.');
			if (parts.pop() != root) continue;
			var value = bindings.get(bindingPath);
			if (value == null) continue;
			var paths:Dynamic = null;
			try paths = Reflect.getProperty(value, '__hscriptStringFieldPaths') catch (_:Dynamic) {}
			if (!Std.isOfType(paths, Array)) continue;
			if ((cast paths:Array<Dynamic>).indexOf(path) >= 0) return true;
		}
		return false;
	}

	/** FlxSprite.animation.curAnim.name is String in pinned Flixel 6.1.2:
	 * FlxSprite.animation is FlxAnimationController, curAnim is FlxAnimation,
	 * and FlxAnimation inherits FlxBaseAnimation.name:String. Permit that exact
	 * property chain only in a single-class module directly extending the actual
	 * bound FlxSprite type, and only when no local declaration can shadow the
	 * inherited `animation` field. */
	function isNativeFlxSpriteAnimationName(mask:String, receiver:String):Bool {
		if (receiver != 'animation.curAnim.name' || hasAliasDeclaration(mask, 'animation')
			|| hasFunctionParameter(mask, 'animation')) return false;
		var base = singleClassBase(mask);
		if (base != 'FlxSprite' && base != 'flixel.FlxSprite') return false;
		var importedPaths = importedTypePaths(mask, 'FlxSprite');
		if (base == 'FlxSprite' && importedPaths.length > 0) {
			if (importedPaths.length != 1 || importedPaths[0] != 'flixel.FlxSprite') return false;
		}
		if (bindings == null || !isNativeFlxSpriteClass(bindings.get('flixel.FlxSprite'))) return false;
		return base == 'flixel.FlxSprite' || importedPaths.length > 0
			|| isNativeFlxSpriteClass(bindings.get('FlxSprite'));
	}

	static function isNativeFlxSpriteClass(value:Dynamic):Bool {
		if (value == null) return false;
		try return Type.getClassName(cast value) == 'flixel.FlxSprite' catch (_:Dynamic) return false;
	}

	/** Return the base type only for one top-level runtime class declaration. */
	static function singleClassBase(mask:String):String {
		var regex = new EReg('class[ \\t\\r\\n]+[A-Za-z_][A-Za-z0-9_]*', 'g');
		var cursor = 0;
		var count = 0;
		var base = '';
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			cursor = pos.pos + pos.len;
			if (braceDepth(mask, pos.pos) != 0) continue;
			count++;
			var afterName = skipWhitespace(mask, pos.pos + pos.len);
			if (afterName < mask.length && mask.charAt(afterName) == '<') {
				var close = matchingDelimiter(mask, afterName, '<', '>');
				if (close < 0) return '';
				afterName = skipWhitespace(mask, close + 1);
			}
			if (!isWordAt(mask, afterName, 'extends')) { base = ''; continue; }
			var typeStart = skipWhitespace(mask, afterName + 'extends'.length);
			var typeEnd = typeStart;
			while (typeEnd < mask.length && (isIdentifierChar(mask.charAt(typeEnd)) || mask.charAt(typeEnd) == '.')) typeEnd++;
			base = mask.substring(typeStart, typeEnd);
		}
		return count == 1 ? base : '';
	}

	static function hasFunctionParameter(mask:String, name:String):Bool {
		var cursor = 0;
		while (cursor < mask.length) {
			var functionStart = mask.indexOf('function', cursor);
			if (functionStart < 0) return false;
			if (!isWordAt(mask, functionStart, 'function')) { cursor = functionStart + 8; continue; }
			var open = mask.indexOf('(', functionStart + 'function'.length);
			if (open < 0) return false;
			var close = matchingDelimiter(mask, open, '(', ')');
			if (close < 0) return true;
			for (argument in mask.substring(open + 1, close).split(',')) {
				var argument = StringTools.trim(argument);
				if (argument.startsWith('?')) argument = StringTools.trim(argument.substr(1));
				var end = 0;
				while (end < argument.length && isIdentifierChar(argument.charAt(end))) end++;
				if (end > 0 && argument.substring(0, end) == name) return true;
			}
			cursor = close + 1;
		}
		return false;
	}

	/** Expand package wildcards only for referenced direct modules in this
	 * owner's source tree. Unused sibling files are not parsed or loaded. */
	function expandWildcardImports(source:String):{source:String, error:String} {
		var mask = codeMask(source);
		var regex = new EReg('import[ \\t\\r\\n]+([A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)*)\\.[ \\t\\r\\n]*\\*[ \\t\\r\\n]*;', 'g');
		var ranges:Array<{packagePath:String, start:Int, end:Int}> = [];
		var cursor = 0;
		while (regex.matchSub(mask, cursor)) {
			var pos = regex.matchedPos();
			if (braceDepth(mask, pos.pos) == 0)
				ranges.push({packagePath:regex.matched(1), start:pos.pos, end:pos.pos + pos.len});
			cursor = pos.pos + pos.len;
		}
		if (ranges.length == 0) return {source:source, error:''};

		var searchChars = mask.split('');
		for (range in ranges) for (index in range.start...range.end) searchChars[index] = ' ';
		var searchMask = searchChars.join('');
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		for (range in ranges) {
			if (!validImport(range.packagePath)) return {source:source, error:'unsafe wildcard class import: ' + range.packagePath};
			var names = packageModuleNames(range.packagePath);
			if (names == null) return {source:source, error:'wildcard class import package is missing or escaped its owner root: ' + range.packagePath};
			var explicit:Array<String> = [];
			for (name in names) if (hasIdentifier(searchMask, name)) explicit.push(range.packagePath + '.' + name);
			if (bindings != null) for (name in bindings.keys()) {
				if (name.indexOf(range.packagePath + '.') != 0) continue;
				var shortName = name.substr(range.packagePath.length + 1);
				if (shortName.indexOf('.') < 0 && hasIdentifier(searchMask, shortName)
					&& explicit.indexOf(name) < 0) explicit.push(name);
			}
			explicit.sort(Reflect.compare);
			var replacement = '';
			for (path in explicit) replacement += 'import ' + path + '; ';
			edits.push({start:range.start, end:range.end, value:replacement});
		}
		return {source:applyEdits(source, edits), error:''};
	}

	function packageModuleNames(packagePath:String):Null<Array<String>> {
		#if sys
		var relativeDir = 'source/' + packagePath.split('.').join('/');
		var full = Path.join([ownerRoot, relativeDir]);
		try {
			if (!FileSystem.exists(full) || !FileSystem.isDirectory(full)
				|| !CodenameScriptDiscovery.withinRoot(ownerRoot, full)) return null;
			var names:Array<String> = [];
			for (entry in FileSystem.readDirectory(full)) {
				if (!entry.endsWith('.hx')) continue;
				var name = entry.substr(0, entry.length - 3);
				if (!safeModuleName(name)) continue;
				var child = relativeDir + '/' + entry;
				var childResolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, child);
				if (childResolution.relative == child) names.push(name);
				if (names.length > MAX_MODULES) return null;
			}
			names.sort(Reflect.compare);
			return names;
		} catch (_:Dynamic) return null;
		#else
		return null;
		#end
	}

	static function codeMask(source:String):String {
		var chars = (source == null ? '' : source).split('');
		var state = 0; // 0 code, 1 single quote, 2 double quote, 3 line comment, 4 block comment
		var escaped = false;
		var cursor = 0;
		while (cursor < chars.length) {
			var ch = chars[cursor];
			var next = cursor + 1 < chars.length ? chars[cursor + 1] : '';
			if (state == 0) {
				if (ch == '/' && next == '/') { chars[cursor] = ' '; chars[cursor + 1] = ' '; state = 3; cursor += 2; continue; }
				if (ch == '/' && next == '*') { chars[cursor] = ' '; chars[cursor + 1] = ' '; state = 4; cursor += 2; continue; }
				if (ch == "'") { chars[cursor] = ' '; state = 1; escaped = false; cursor++; continue; }
				if (ch == '"') { chars[cursor] = ' '; state = 2; escaped = false; cursor++; continue; }
			} else if (state == 1 || state == 2) {
				if (ch != '\n' && ch != '\r') chars[cursor] = ' ';
				if (escaped) escaped = false;
				else if (ch == '\\') escaped = true;
				else if ((state == 1 && ch == "'") || (state == 2 && ch == '"')) state = 0;
			} else if (state == 3) {
				if (ch == '\n' || ch == '\r') state = 0;
				else chars[cursor] = ' ';
			} else if (state == 4) {
				if (ch == '*' && next == '/') { chars[cursor] = ' '; chars[cursor + 1] = ' '; state = 0; cursor += 2; continue; }
				if (ch != '\n' && ch != '\r') chars[cursor] = ' ';
			}
			cursor++;
		}
		return chars.join('');
	}

	static function isWordAt(source:String, start:Int, word:String):Bool {
		if (start < 0 || start + word.length > source.length || source.substr(start, word.length) != word) return false;
		return (start == 0 || !isIdentifierChar(source.charAt(start - 1)))
			&& (start + word.length >= source.length || !isIdentifierChar(source.charAt(start + word.length)));
	}

	static function safeModuleName(name:String):Bool {
		return name != null && name != '' && ~/^[A-Za-z_][A-Za-z0-9_]*$/.match(name);
	}

	static function isIdentifierStart(ch:String):Bool return ch != '' && ~/^[A-Za-z_]$/.match(ch);
	static function isIdentifierChar(ch:String):Bool return ch != '' && ~/^[A-Za-z0-9_]$/.match(ch);

	static function skipWhitespace(source:String, start:Int):Int {
		var cursor = start;
		while (cursor < source.length && [' ', '\t', '\r', '\n'].indexOf(source.charAt(cursor)) >= 0) cursor++;
		return cursor;
	}

	static function braceDepth(source:String, end:Int):Int {
		var depth = 0;
		for (index in 0...end) {
			if (source.charAt(index) == '{') depth++;
			else if (source.charAt(index) == '}') depth--;
		}
		return depth;
	}

	static function hasIdentifier(source:String, name:String):Bool {
		for (_ in identifierSpans(source, name)) return true;
		return false;
	}

	static function identifierSpans(source:String, name:String):Array<{start:Int, end:Int}> {
		var result:Array<{start:Int, end:Int}> = [];
		var cursor = 0;
		while (cursor < source.length) {
			if (!isIdentifierStart(source.charAt(cursor))) { cursor++; continue; }
			var end = cursor + 1;
			while (end < source.length && isIdentifierChar(source.charAt(end))) end++;
			if (end - cursor == name.length && source.substr(cursor, name.length) == name)
				result.push({start:cursor, end:end});
			cursor = end;
		}
		return result;
	}

	static function hasAliasDeclaration(mask:String, alias:String):Bool {
		var escaped = EReg.escape(alias);
		var patterns = [
			new EReg('(^|[^A-Za-z0-9_])(var|function|class|enum|typedef|catch)[ \\t\\r\\n]+' + escaped + '([^A-Za-z0-9_]|$)', 'm'),
			new EReg('for[ \\t\\r\\n]*\\([ \\t\\r\\n]*' + escaped + '[ \\t\\r\\n]+in\\b', '')
		];
		for (pattern in patterns) if (pattern.match(mask)) return true;
		// Treat parameters as declarations only inside function parameter lists.
		// A raw `, NAME:` pattern also matches Haxe's multi-constructor switch
		// case `case A, NAME:`, which is a value pattern, not a shadowing binding.
		return hasFunctionParameter(mask, alias);
	}

	static function spaces(value:String):String {
		var chars = value.split('');
		for (index in 0...chars.length) if (chars[index] != '\n' && chars[index] != '\r') chars[index] = ' ';
		return chars.join('');
	}

	static function applyEdits(source:String, edits:Array<{start:Int, end:Int, value:String}>):String {
		edits.sort(function(a, b) return b.start - a.start);
		var result = source;
		var lastStart = result.length + 1;
		for (edit in edits) {
			if (edit.start < 0 || edit.end < edit.start || edit.end > result.length || edit.end > lastStart) continue;
			result = result.substring(0, edit.start) + edit.value + result.substr(edit.end);
			lastStart = edit.start;
		}
		return result;
	}

	static function replaceRangesWithSpaces(source:String, ranges:Array<{start:Int, end:Int}>):String {
		var edits:Array<{start:Int, end:Int, value:String}> = [];
		for (range in ranges) edits.push({start:range.start, end:range.end, value:spaces(source.substring(range.start, range.end))});
		return applyEdits(source, edits);
	}

	static function findDeclarationAssignment(mask:String, start:Int):Int {
		var parens = 0, brackets = 0, braces = 0;
		var cursor = start;
		while (cursor < mask.length) {
			var ch = mask.charAt(cursor);
			if (parens == 0 && brackets == 0 && braces == 0) {
				if (ch == ';') return -1;
				if (ch == '=' && mask.charAt(cursor + 1) != '=' && mask.charAt(cursor + 1) != '>'
					&& (cursor == 0 || ['=', '!', '<', '>', '+', '-', '*', '/', '%', '&', '|', '^'].indexOf(mask.charAt(cursor - 1)) < 0))
					return cursor;
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
			cursor++;
		}
		return -1;
	}

	static function findDeclarationEnd(mask:String, start:Int):Int {
		var parens = 0, brackets = 0, braces = 0;
		var cursor = start;
		while (cursor < mask.length) {
			var ch = mask.charAt(cursor);
			if (ch == ';' && parens == 0 && brackets == 0 && braces == 0) return cursor + 1;
			switch (ch) {
				case '(': parens++;
				case ')': parens--;
				case '[': brackets++;
				case ']': brackets--;
				case '{': braces++;
				case '}': braces--;
				default:
			}
			cursor++;
		}
		return -1;
	}

	static function hasAssignmentTo(mask:String, name:String, excludedStart:Int, excludedEnd:Int):Bool {
		for (span in identifierSpans(mask, name)) {
			if (span.start >= excludedStart && span.start < excludedEnd) continue;
			var next = skipWhitespace(mask, span.end);
			if (next < mask.length && ['=', '+', '-', '*', '/', '%', '&', '|', '^'].indexOf(mask.charAt(next)) >= 0) {
				var op = mask.charAt(next);
				if (op == '=' && mask.charAt(next + 1) == '=') continue;
				if (op != '=' && mask.charAt(next + 1) != '=') continue;
				return true;
			}
			if (next + 1 < mask.length && ((mask.substr(next, 2) == '++') || (mask.substr(next, 2) == '--'))) return true;
			if (span.start >= 2 && (mask.charAt(span.start - 1) == '+' || mask.charAt(span.start - 1) == '-')
				&& mask.charAt(span.start - 1) == mask.charAt(span.start - 2)) return true;
		}
		return false;
	}

	static function matchingDelimiter(mask:String, open:Int, openChar:String, closeChar:String):Int {
		var depth = 0;
		for (cursor in open...mask.length) {
			if (mask.charAt(cursor) == openChar) depth++;
			else if (mask.charAt(cursor) == closeChar) {
				depth--;
				if (depth == 0) return cursor;
			}
		}
		return -1;
	}

	static function simpleReceiverStart(mask:String, dot:Int):Int {
		var end = dot;
		while (end > 0 && [' ', '\t', '\r', '\n'].indexOf(mask.charAt(end - 1)) >= 0) end--;
		if (end > 0 && mask.charAt(end - 1) == ')') {
			// A native String case conversion still returns a String. Keep its
			// whole expression when a source extension follows it.
			var depth = 1;
			var open = end - 2;
			while (open >= 0 && depth > 0) {
				if (mask.charAt(open) == ')') depth++;
				else if (mask.charAt(open) == '(') depth--;
				if (depth > 0) open--;
			}
			if (open < 0 || StringTools.trim(mask.substring(open + 1, end - 1)) != '') return -1;
			var methodEnd = open;
			while (methodEnd > 0 && [' ', '\t', '\r', '\n'].indexOf(mask.charAt(methodEnd - 1)) >= 0) methodEnd--;
			var methodStart = methodEnd;
			while (methodStart > 0 && isIdentifierChar(mask.charAt(methodStart - 1))) methodStart--;
			var method = mask.substring(methodStart, methodEnd);
			if (method != 'toLowerCase' && method != 'toUpperCase') return -1;
			if (methodStart == 0 || mask.charAt(methodStart - 1) != '.') return -1;
			return simpleReceiverStart(mask, methodStart - 1);
		}
		if (end <= 0 || !isIdentifierChar(mask.charAt(end - 1))) return -1;
		var start = end - 1;
		while (start > 0 && isIdentifierChar(mask.charAt(start - 1))) start--;
		while (start > 0 && mask.charAt(start - 1) == '.') {
			var beforeDot = start - 1;
			while (beforeDot > 0 && [' ', '\t', '\r', '\n'].indexOf(mask.charAt(beforeDot - 1)) >= 0) beforeDot--;
			var identStart = beforeDot;
			while (identStart > 0 && isIdentifierChar(mask.charAt(identStart - 1))) identStart--;
			if (identStart == beforeDot) break;
			start = identStart;
		}
		return start;
	}

	static function isTypedStringCaseResult(receiver:String, typed:Map<String, Bool>):Bool {
		if (receiver == null) return false;
		var matcher = new EReg('^([A-Za-z_][A-Za-z0-9_]*)\\.(?:toLowerCase|toUpperCase)\\(\\)$', '');
		return matcher.match(receiver) && typed.exists(matcher.matched(1));
	}

	static function findStringToolsCall(source:String, mask:String, startCursor:Int = 0):Null<{start:Int, end:Int, receiver:String, method:String, arguments:String}> {
		var cursor = startCursor;
		while (cursor < mask.length) {
			if (mask.charAt(cursor) != '.') { cursor++; continue; }
			var methodStart = cursor + 1;
			var methodEnd = methodStart;
			while (methodEnd < mask.length && isIdentifierChar(mask.charAt(methodEnd))) methodEnd++;
			if (methodEnd == methodStart || !isIdentifierStart(mask.charAt(methodStart))) { cursor++; continue; }
			var method = mask.substring(methodStart, methodEnd);
			var open = skipWhitespace(mask, methodEnd);
			if (open >= mask.length || mask.charAt(open) != '(' || Reflect.field(StringTools, method) == null) {
				cursor = methodEnd;
				continue;
			}
			var close = matchingDelimiter(mask, open, '(', ')');
			if (close < 0) return null;
			var receiverStart = simpleReceiverStart(mask, cursor);
			if (receiverStart < 0)
				return {start:cursor, end:close + 1, receiver:'', method:method,
					arguments:StringTools.trim(source.substring(open + 1, close))};
			var receiver = StringTools.trim(source.substring(receiverStart, cursor));
			if (receiver == 'StringTools' || receiver == 'haxe.StringTools') { cursor = methodEnd; continue; }
			return {start:receiverStart, end:close + 1, receiver:receiver, method:method,
				arguments:StringTools.trim(source.substring(open + 1, close))};
		}
		return null;
	}

	static function stringTypedIdentifiers(mask:String):Map<String, Bool> {
		var declarations:Map<String, Bool> = new Map();
		var cursor = 0;
		while (cursor < mask.length) {
			var varStart = mask.indexOf('var', cursor);
			if (varStart < 0) break;
			if (!isWordAt(mask, varStart, 'var')) { cursor = varStart + 3; continue; }
			var nameStart = skipWhitespace(mask, varStart + 3);
			var nameEnd = nameStart;
			while (nameEnd < mask.length && isIdentifierChar(mask.charAt(nameEnd))) nameEnd++;
			if (nameEnd == nameStart) { cursor = varStart + 3; continue; }
			var typeStart = skipWhitespace(mask, nameEnd);
			var type = '';
			if (typeStart < mask.length && mask.charAt(typeStart) == ':') {
				typeStart = skipWhitespace(mask, typeStart + 1);
				var typeEnd = typeStart;
				while (typeEnd < mask.length && (isIdentifierChar(mask.charAt(typeEnd)) || mask.charAt(typeEnd) == '.')) typeEnd++;
				type = mask.substring(typeStart, typeEnd);
			}
			markStringType(declarations, mask.substring(nameStart, nameEnd), type);
			cursor = nameEnd;
		}
		cursor = 0;
		while (cursor < mask.length) {
			var functionStart = mask.indexOf('function', cursor);
			if (functionStart < 0) break;
			if (!isWordAt(mask, functionStart, 'function')) { cursor = functionStart + 8; continue; }
			var open = mask.indexOf('(', functionStart + 8);
			if (open < 0) break;
			var close = matchingDelimiter(mask, open, '(', ')');
			if (close < 0) break;
			var args = mask.substring(open + 1, close).split(',');
			for (arg in args) {
				var colon = arg.indexOf(':');
				var name = StringTools.trim(colon < 0 ? arg : arg.substring(0, colon));
				if (!safeModuleName(name)) continue;
				var type = colon < 0 ? '' : StringTools.trim(arg.substr(colon + 1));
				var typeEnd = 0;
				while (typeEnd < type.length && (isIdentifierChar(type.charAt(typeEnd)) || type.charAt(typeEnd) == '.')) typeEnd++;
				markStringType(declarations, name, type.substring(0, typeEnd));
			}
			cursor = close + 1;
		}
		var result:Map<String, Bool> = new Map();
		for (name in declarations.keys()) if (declarations.get(name)) result.set(name, true);
		return result;
	}

	static function markStringType(declarations:Map<String, Bool>, name:String, type:String):Void {
		var isString = type == 'String';
		if (!declarations.exists(name)) declarations.set(name, isString);
		else if (!isString) declarations.set(name, false);
	}

	function fail(importPath:String, relative:String, reason:String):{expectedSource:Bool, loaded:Bool, reason:String} {
		loading.remove(relative);
		var message = relative + ': ' + reason;
		if (diagnostics.indexOf(message) < 0) diagnostics.push(message);
		return {expectedSource:true, loaded:false, reason:message};
	}

	function findSourceModule(importPath:String):Null<String> {
		var parts = importPath.split('.');
		var candidates:Array<String> = ['source/' + parts.join('/') + '.hx'];
		if (parts.length > 1) candidates.push('source/' + parts.slice(0, parts.length - 1).join('/') + '.hx');
		for (candidate in candidates) {
			var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, candidate);
			if (resolution.relative != null) return resolution.relative;
		}
		return null;
	}

	static function validImport(path:String):Bool {
		if (path == null || path == '') return false;
		for (part in path.split('.'))
			if (!CodenameScriptDiscovery.safeName(part) || !~/^[A-Za-z_][A-Za-z0-9_]*$/.match(part))
				return false;
		return true;
	}

	/** Close an array-valued class field when the next source line starts a new
	 * access-modified field. The closing `]` must be the entire line, so array
	 * indexing and already terminated declarations remain untouched. */
	static function repairMissingArrayFieldTerminator(source:String):String {
		if (source == null || source.indexOf('class ') < 0) return source;
		var pattern = new EReg('(^[ \\t]*\\])([ \\t]*\\r?\\n(?:[ \\t]*\\r?\\n)*[ \\t]*(?:private|public|static|final|override)\\b)', 'gm');
		return pattern.replace(source, '$1;$2');
	}
}
