package;

using StringTools;

/** Result of checking and normalizing one Psych `.hx` plain HScript file. */
typedef PsychHscriptCompatResult = {
	var supported:Bool;
	/** Empty when `supported` is false. Successful sources begin with TRANSLATED_MARKER. */
	var source:String;
	var diagnostics:Array<String>;
	var strippedImports:Array<String>;
}

private typedef PsychHscriptImportRange = { var start:Int; var end:Int; }
private typedef PsychHscriptSourceRange = { var start:Int; var end:Int; }

/**
	Small, fail-closed adapter for Psych `.hx` files which are actually HScript.

	Psych uses `.hx` both for callback scripts and for compiled Haxe classes. Only
	the former can enter this engine's HScript interpreter. This adapter removes
	known top-level import declarations after their short names have been seeded
	into the interpreter; it does not attempt to transpile Haxe source.
*/
class PsychHscriptCompat {
	public static inline var TRANSLATED_MARKER:String = '/* psych-hscript-translated */';
	static inline var DIAGNOSTIC_PREFIX:String = '[psych-hscript-unsupported] ';

	/**
		Recognize plain callback scripts before their owner-scoped runtime loads them.
		The engine seeds `FlxG`, `FlxCamera`, and `FlxRect` for this translated
		form. Runtime callers retain direct imports for Iris resolution; legacy
		callers use the seeded surface. Aliases and compiled Haxe declarations
		remain diagnosed until their source loading semantics are implemented.
	*/
	public static function normalize(source:String, resolveNativeImports:Bool = false):PsychHscriptCompatResult {
		var diagnostics:Array<String> = [];
		var strippedImports:Array<String> = [];
		if (source == null) {
			diagnostics.push(DIAGNOSTIC_PREFIX + 'Source is null.');
			return failed(diagnostics, strippedImports);
		}

		var imports:Array<PsychHscriptImportRange> = [];
		var comments:Array<PsychHscriptSourceRange> = [];
		var depth = 0;
		var i = 0;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '/' && i + 1 < source.length) {
				var next = source.charAt(i + 1);
				if (next == '/') {
					var lineStart = i;
					i += 2;
					while (i < source.length && source.charAt(i) != '\n' && source.charAt(i) != '\r') i++;
					comments.push({start:lineStart, end:i});
					continue;
				}
				if (next == '*') {
					var blockStart = i;
					i += 2;
					while (i + 1 < source.length
						&& !(source.charAt(i) == '*' && source.charAt(i + 1) == '/')) i++;
					if (i + 1 >= source.length) {
						diagnostics.push(DIAGNOSTIC_PREFIX + 'Unterminated block comment.');
						comments.push({start:blockStart, end:source.length});
						break;
					}
					i += 2;
					comments.push({start:blockStart, end:i});
					continue;
				}
			}
			if (ch == '"' || ch == "'") {
				i = skipString(source, i);
				continue;
			}
			if (ch == '{') {
				depth++;
				i++;
				continue;
			}
			if (ch == '}') {
				if (depth > 0) depth--;
				i++;
				continue;
			}
			if (depth == 0 && isIdentifierStart(ch)) {
				var tokenStart = i;
				i++;
				while (i < source.length && isIdentifierPart(source.charAt(i))) i++;
				var token = source.substring(tokenStart, i);
				if (isCompiledDeclaration(token)) {
					diagnostics.push(DIAGNOSTIC_PREFIX + 'Compiled Haxe declaration `' + token
						+ '` is not a plain Psych HScript callback.');
					continue;
				}
				if (token == 'import') {
					var end = findImportEnd(source, i);
					if (end < 0) {
						diagnostics.push(DIAGNOSTIC_PREFIX + 'Malformed or unterminated top-level import declaration.');
						continue;
					}
					var declaration = cleanImportDeclaration(source.substring(tokenStart, end + 1));
					if (!StringTools.startsWith(declaration, 'import') || declaration.length <= 'import'.length
						|| !isWhitespace(declaration.charAt('import'.length))) {
						diagnostics.push(DIAGNOSTIC_PREFIX + 'Malformed top-level import declaration.');
					} else {
						var imported = StringTools.trim(declaration.substr('import'.length,
							declaration.length - 'import'.length - 1));
						var binding = bindingForImport(imported);
						if (resolveNativeImports && isQualifiedName(imported)) {
							// Keep the declaration for the owner-scoped Iris resolver.
							// Parsing a valid import does not certify that its class exists.
						} else if (binding == null) {
							if (isQualifiedName(imported))
								diagnostics.push(DIAGNOSTIC_PREFIX + 'Import `' + imported
									+ '` is not in the seeded Psych HScript import allowlist.');
							else
								diagnostics.push(DIAGNOSTIC_PREFIX + 'Unsupported Psych import syntax: `'
									+ imported + '`. Only direct, allowlisted imports are supported.');
						} else {
							strippedImports.push(imported);
							imports.push({start:tokenStart, end:end + 1});
							appendComments(source, tokenStart, end + 1, comments);
						}
					}
					i = end + 1;
					continue;
				}
				continue;
			}
			i++;
		}

		if (diagnostics.length > 0)
			return failed(diagnostics, strippedImports);

		var normalized = maskImports(source, imports, comments);
		return {
			supported:true,
			source:TRANSLATED_MARKER + '\n' + normalized,
			diagnostics:diagnostics,
			strippedImports:strippedImports
		};
	}

	static function failed(diagnostics:Array<String>, strippedImports:Array<String>):PsychHscriptCompatResult {
		return {supported:false, source:'', diagnostics:diagnostics, strippedImports:strippedImports};
	}

	/** Class spelling differs between forks; all values come from the live seed. */
	public static function importBindings():Map<String, String> {
		return [
			'Reflect' => 'Reflect', 'Type' => 'Type',
			'backend.Language' => 'Language', 'backend.DiscordClient' => 'DiscordClient',
			'objects.Alphabet.AlphaCharacter' => 'AlphaCharacter', 'objects.Alphabet.Alignment' => 'Alignment',
			'objects.AttachedText' => 'AttachedText',
			'flixel.FlxG' => 'FlxG', 'flixel.FlxCamera' => 'FlxCamera',
			'flixel.FlxBasic' => 'FlxBasic', 'flixel.FlxObject' => 'FlxObject',
			'flixel.FlxSprite' => 'FlxSprite', 'flixel.math.FlxRect' => 'FlxRect',
			'flixel.math.FlxPoint' => 'FlxPoint', 'flixel.math.FlxMath' => 'FlxMath',
			'flixel.text.FlxText' => 'FlxText', 'flixel.util.FlxTimer' => 'FlxTimer',
			'flixel.tweens.FlxTween' => 'FlxTween', 'flixel.tweens.FlxEase' => 'FlxEase',
			'flixel.util.FlxColor' => 'FlxColor', 'flixel.sound.FlxSound' => 'FlxSound',
			'flixel.group.FlxGroup' => 'FlxGroup', 'flixel.group.FlxGroup.FlxTypedGroup' => 'FlxTypedGroup',
			'flixel.group.FlxSpriteGroup' => 'FlxSpriteGroup',
			'flixel.addons.display.FlxRuntimeShader' => 'FlxRuntimeShader',
			'openfl.filters.ShaderFilter' => 'ShaderFilter', 'flxanimate.FlxAnimate' => 'FlxAnimate',
			'backend.Paths' => 'Paths', 'backend.Conductor' => 'Conductor',
			'backend.Rating' => 'Rating',
			'backend.Achievements' => 'Achievements',
			'backend.ClientPrefs' => 'ClientPrefs', 'backend.CoolUtil' => 'CoolUtil',
			'backend.Controls' => 'Controls', 'backend.BaseStage' => 'BaseStage',
			'backend.BaseStage.Countdown' => 'Countdown', 'backend.Difficulty' => 'Difficulty',
			'backend.MusicBeatState' => 'MusicBeatState', 'states.PlayState' => 'PlayState',
			'objects.Character' => 'Character', 'objects.Alphabet' => 'Alphabet',
			'objects.Note' => 'Note', 'objects.HealthIcon' => 'HealthIcon',
			'psychlua.CustomSubstate' => 'CustomSubstate',
			'backend.PsychCamera' => 'PsychCamera',
			'haxe.ds.StringMap' => 'StringMap', 'haxe.ds.IntMap' => 'IntMap',
			'haxe.ds.ObjectMap' => 'ObjectMap'
		];
	}

	static function bindingForImport(path:String):String {
		return importBindings().get(path);
	}

	static function isCompiledDeclaration(token:String):Bool {
		return token == 'package' || token == 'class' || token == 'enum'
			|| token == 'interface' || token == 'typedef';
	}

	static function isQualifiedName(value:String):Bool {
		if (value == 'Reflect' || value == 'Type') return true;
		if (value == null || value == '') return false;
		var parts = value.split('.');
		if (parts.length < 2) return false;
		for (part in parts) {
			if (part == '' || !isIdentifierStart(part.charAt(0))) return false;
			for (i in 1...part.length)
				if (!isIdentifierPart(part.charAt(i))) return false;
		}
		return true;
	}

	static function isIdentifierStart(ch:String):Bool {
		if (ch == null || ch == '') return false;
		var code = ch.charCodeAt(0);
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || ch == '_';
	}

	static function isIdentifierPart(ch:String):Bool {
		if (isIdentifierStart(ch)) return true;
		if (ch == null || ch == '') return false;
		var code = ch.charCodeAt(0);
		return code >= 48 && code <= 57;
	}

	static function isWhitespace(ch:String):Bool {
		return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n';
	}

	static function skipString(source:String, start:Int):Int {
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

	static function findImportEnd(source:String, start:Int):Int {
		var i = start;
		while (i < source.length) {
			var ch = source.charAt(i);
			if (ch == '/' && i + 1 < source.length) {
				var next = source.charAt(i + 1);
				if (next == '/') {
					i += 2;
					while (i < source.length && source.charAt(i) != '\n' && source.charAt(i) != '\r') i++;
					continue;
				}
				if (next == '*') {
					i += 2;
					while (i + 1 < source.length
						&& !(source.charAt(i) == '*' && source.charAt(i + 1) == '/')) i++;
					if (i + 1 >= source.length) return -1;
					i += 2;
					continue;
				}
			}
			if (ch == '"' || ch == "'") {
				i = skipString(source, i);
				continue;
			}
			if (ch == ';') return i;
			if (ch == '{' || ch == '}') return -1;
			i++;
		}
		return -1;
	}

	static function cleanImportDeclaration(value:String):String {
		var output = new StringBuf();
		var i = 0;
		while (i < value.length) {
			var ch = value.charAt(i);
			if (ch == '/' && i + 1 < value.length) {
				var next = value.charAt(i + 1);
				if (next == '/') {
					output.add(' ');
					i += 2;
					while (i < value.length && value.charAt(i) != '\n' && value.charAt(i) != '\r') i++;
					continue;
				}
				if (next == '*') {
					output.add(' ');
					i += 2;
					while (i + 1 < value.length
						&& !(value.charAt(i) == '*' && value.charAt(i + 1) == '/')) i++;
					i = i + 1 < value.length ? i + 2 : value.length;
					continue;
				}
			}
			output.add(ch);
			i++;
		}
		return StringTools.trim(output.toString());
	}

	static function appendComments(source:String, start:Int, end:Int,
		comments:Array<PsychHscriptSourceRange>):Void {
		var i = start;
		while (i < end) {
			if (source.charAt(i) != '/' || i + 1 >= end) {
				i++;
				continue;
			}
			var next = source.charAt(i + 1);
			if (next == '/') {
				var lineStart = i;
				i += 2;
				while (i < end && source.charAt(i) != '\n' && source.charAt(i) != '\r') i++;
				comments.push({start:lineStart, end:i});
				continue;
			}
			if (next == '*') {
				var blockStart = i;
				i += 2;
				while (i + 1 < end
					&& !(source.charAt(i) == '*' && source.charAt(i + 1) == '/')) i++;
				i = i + 1 < end ? i + 2 : end;
				comments.push({start:blockStart, end:i});
				continue;
			}
			i++;
		}
	}

	static function maskImports(source:String, imports:Array<PsychHscriptImportRange>,
		comments:Array<PsychHscriptSourceRange>):String {
		if (imports.length == 0) return source;
		var output = new StringBuf();
		var importIndex = 0;
		var commentIndex = 0;
		for (i in 0...source.length) {
			while (importIndex < imports.length && i >= imports[importIndex].end) importIndex++;
			while (commentIndex < comments.length && i >= comments[commentIndex].end) commentIndex++;
			var inImport = importIndex < imports.length
				&& i >= imports[importIndex].start && i < imports[importIndex].end;
			var inComment = commentIndex < comments.length
				&& i >= comments[commentIndex].start && i < comments[commentIndex].end;
			var ch = source.charAt(i);
			output.add(inImport && !inComment && ch != '\n' && ch != '\r' ? ' ' : ch);
		}
		return output.toString();
	}
}
