package;

import crowplexus.hscript.Expr;

private typedef SourceIrisImports = {
	var source:String;
	var paths:Array<String>;
}

/**
	Facade over the engine's persistent Iris interpreter for Psych's plain
	HScript callbacks. The inherited HScript globals map is deliberately shared
	with the evaluator so existing host seeding code continues to work.
*/
class SourceIrisBridge extends hscript.Interp {
	public var evaluator(default, null):NightmareVisionScriptInterp;
	var parser:NightmareVisionScriptParser;
	var previousVarsToBring:Dynamic;

	public function new(parent:Dynamic) {
		super();
		evaluator = new NightmareVisionScriptInterp(parent);
		parser = new NightmareVisionScriptParser();
		variables = evaluator.variables;
	}

	/**
		Normalize and execute one Psych `.hx` HScript file. The Iris interpreter
		stays alive between calls, retaining functions and globals just like the
		source engine. Reapplying normalization to an already marked source is safe.
	*/
	public function evaluate(source:String, origin:String, ?varsToBring:Dynamic):Dynamic {
		applyVarsToBring(varsToBring);
		var extracted = extractImports(source);
		var normalized = PsychHscriptCompat.normalize(extracted.source);
		if (!normalized.supported)
			throw normalized.diagnostics.join('\n');

		// A normalized source may have lost its import list in a previous pass.
		// Bind every known import whose short name was seeded by the host so either
		// raw and marked source forms resolve identically.
		bindKnownSeededLibraries();
		for (path in extracted.paths) {
			var alias = PsychHscriptCompat.importBindings().get(path);
			if (alias == null) alias = path.substr(path.lastIndexOf('.') + 1);
			bindLibrary(alias, path);
		}

		var expression:Expr = parser.parseString(normalized.source,
			origin == null || StringTools.trim(origin) == '' ? 'psych-hscript' : origin);
		return evaluator.execute(expression);
	}

	/** Strip simple top-level imports before Psych's bounded normalizer runs. */
	function extractImports(source:String):SourceIrisImports {
		if (source == null) return {source:null, paths:[]};
		var output = new StringBuf();
		var paths:Array<String> = [];
		var depth = 0;
		var i = 0;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '/' && i + 1 < source.length) {
				var next = source.charAt(i + 1);
				if (next == '/') {
					var end = i + 2;
					while (end < source.length && source.charAt(end) != '\n' && source.charAt(end) != '\r') end++;
					output.add(source.substring(i, end));
					i = end;
					continue;
				}
				if (next == '*') {
					var end = i + 2;
					while (end + 1 < source.length
						&& !(source.charAt(end) == '*' && source.charAt(end + 1) == '/')) end++;
					end = end + 1 < source.length ? end + 2 : source.length;
					output.add(source.substring(i, end));
					i = end;
					continue;
				}
			}
			if (ch == '"' || ch == "'") {
				var end = skipSourceString(source, i);
				output.add(source.substring(i, end));
				i = end;
				continue;
			}
			if (ch == '{') depth++;
			if (ch == '}') depth = depth > 0 ? depth - 1 : 0;
			if (depth == 0 && source.substr(i, 6) == 'import'
				&& (i == 0 || !isSourceIdentifier(source.charAt(i - 1)))
				&& (i + 6 >= source.length || !isSourceIdentifier(source.charAt(i + 6)))) {
				var end = findSourceImportEnd(source, i + 6);
				if (end >= 0) {
					var declaration = StringTools.trim(source.substring(i, end + 1));
					var keywordEnd = declaration.indexOf('import') + 'import'.length;
					var imported = StringTools.trim(declaration.substring(keywordEnd, declaration.length - 1));
					if (isSourceQualifiedName(imported)) {
						paths.push(imported);
						for (p in i...end + 1) {
							var mask = source.charAt(p);
							output.add(mask == '\n' || mask == '\r' ? mask : ' ');
						}
						i = end + 1;
						continue;
					}
					// Leave aliases, wildcard forms and malformed imports in place so
					// PsychHscriptCompat can reject them with its normal diagnostic.
					output.add(source.substring(i, end + 1));
					i = end + 1;
					continue;
				}
			}
			output.add(ch);
			i++;
		}
		return {source:output.toString(), paths:paths};
	}

	static function findSourceImportEnd(source:String, start:Int):Int {
		var i = start;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '/' && i + 1 < source.length) {
				if (source.charAt(i + 1) == '/') {
					i += 2;
					while (i < source.length && source.charAt(i) != '\n' && source.charAt(i) != '\r') i++;
					continue;
				}
				if (source.charAt(i + 1) == '*') {
					i += 2;
					while (i + 1 < source.length
						&& !(source.charAt(i) == '*' && source.charAt(i + 1) == '/')) i++;
					if (i + 1 >= source.length) return -1;
					i += 2;
					continue;
				}
			}
			if (ch == '"' || ch == "'") {
				i = skipSourceString(source, i);
				continue;
			}
			if (ch == ';') return i;
			if (ch == '{' || ch == '}') return -1;
			i++;
		}
		return -1;
	}

	static function skipSourceString(source:String, start:Int):Int {
		var quote = source.charAt(start);
		var i = start + 1;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '\\') { i += 2; continue; }
			if (ch == quote) return i + 1;
			i++;
		}
		return source.length;
	}

	static function isSourceQualifiedName(value:String):Bool {
		if (value == 'Reflect' || value == 'Type') return true;
		if (value == null || value == '') return false;
		var parts = value.split('.');
		if (parts.length < 2) return false;
		for (part in parts) {
			if (part == '' || !isSourceIdentifierStart(part.charAt(0))) return false;
			for (i in 1...part.length)
				if (!isSourceIdentifier(part.charAt(i))) return false;
		}
		return true;
	}

	static function isSourceIdentifierStart(ch:String):Bool {
		if (ch == null || ch == '') return false;
		var code = ch.charCodeAt(0);
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || ch == '_';
	}

	static function isSourceIdentifier(ch:String):Bool {
		if (isSourceIdentifierStart(ch)) return true;
		if (ch == null || ch == '') return false;
		var code = ch.charCodeAt(0);
		return code >= 48 && code <= 57;
	}

	/** Bind a recognized full import path against the host's seeded short name. */
	public function bindLibrary(name:String, packagePath:String):Dynamic {
		if (packagePath == null || StringTools.trim(packagePath) == '')
			throw '[psych-hscript-import] Empty import path';

		var sourceClass = evaluator.sourceClasses == null ? null : evaluator.sourceClasses.importClass(packagePath);
		if (sourceClass != null) {
			var alias = name == null || StringTools.trim(name) == '' ? packagePath.substr(packagePath.lastIndexOf('.') + 1) : StringTools.trim(name);
			if (variables.exists(alias) && variables.get(alias) != sourceClass)
				throw '[psych-hscript-import] Conflicting source class alias: ' + alias + ' (' + packagePath + ')';
			variables.set(alias, sourceClass);evaluator.bindImport(packagePath, sourceClass);
			return sourceClass;
		}

		var aliases = PsychHscriptCompat.importBindings();
		var shortName = name == null || StringTools.trim(name) == ''
			? aliases.get(packagePath) : StringTools.trim(name);
		var value:Dynamic = null;
		if (shortName != null && variables.exists(shortName))
			value = variables.get(shortName);
		else
			value = evaluator.getOrImportClass(packagePath);

		if (value != null && evaluator.nativeClassScope != null && evaluator.nativeClassScope.ownsClass(value)
			&& !evaluator.importBindings.exists(packagePath))
			throw '[psych-hscript-import] Unregistered source module path: ' + packagePath;
		if (value == null)
			throw '[psych-hscript-import] No seeded or resolvable binding for `' + packagePath + '`';
		if (shortName != null && !variables.exists(shortName))
			variables.set(shortName, value);
		evaluator.bindImport(packagePath, value);
		return value;
	}

	/**
		Keep the import table aligned with every alias already installed by the
		host. This also handles source that was normalized before it reached us.
	*/
	public function bindKnownSeededLibraries():Void {
		for (path => shortName in PsychHscriptCompat.importBindings())
			if (variables.exists(shortName))
				evaluator.bindImport(path, variables.get(shortName));
	}

	/** Invoke a callback through Iris's error-frame restoration wrapper. */
	public function callCallback(method:Dynamic, args:Array<Dynamic>):Dynamic {
		if (args == null) args = [];
		return evaluator.callCallback(method, args);
	}

	/** Invoke one named persistent callback through the same guarded path. */
	public function callFunction(name:String, args:Array<Dynamic>):Dynamic {
		if (name == null || !variables.exists(name))
			throw '[psych-hscript-callback] Missing callback `' + name + '`';
		var method:Dynamic = variables.get(name);
		if (!Reflect.isFunction(method))
			throw '[psych-hscript-callback] `' + name + '` is not a function';
		return callCallback(method, args);
	}

	/**
		Mirror Psych HScript.set_varsToBring: remove the previous brought keys,
		then seed the new object's trimmed fields. Removed keys are not restored
		from earlier host presets; every unrelated interpreter global survives.
	*/
	function applyVarsToBring(next:Dynamic):Void {
		if (previousVarsToBring != null) {
			for (field in Reflect.fields(previousVarsToBring)) {
				var key = StringTools.trim(field);
				if (key != '' && variables.exists(key)) variables.remove(key);
			}
		}
		if (next != null) {
			for (field in Reflect.fields(next)) {
				var key = StringTools.trim(field);
				if (key != '') variables.set(key, Reflect.field(next, field));
			}
		}
		previousVarsToBring = next;
	}

	/** Release owner state and sever the façade's reference to Iris globals. */
	public function release():Void {
		if (evaluator != null) evaluator.release();
		previousVarsToBring = null;
		variables = new Map<String, Dynamic>();
		parser = null;
		evaluator = null;
	}
}
