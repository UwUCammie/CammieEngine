package;

using StringTools;

/**
	Small lexical identity reader for HXC scripts. It deliberately does not use
	HxcCompat or parse/execute Haxe: runtime discovery only needs the declared
	engine family and a character/stage wrapper's literal constructor id.
*/
typedef HxcScriptIdentityData = {
	var family:String;
	var characterId:String;
	var characterClassName:String;
	var stageId:String;
	var stageClassName:String;
	var hasCharacterClass:Bool;
	var hasStageClass:Bool;
	var hasDeclarations:Bool;
}

private typedef HxcIdentityToken = {
	var value:String;
	var kind:String;
	var validLiteral:Bool;
	var offset:Int;
	var endOffset:Int;
}

typedef HxcScriptClassDeclaration = {
	var name:String;
	var base:String;
	var source:String;
	var start:Int;
	var end:Int;
}

private typedef HxcIdentityClass = {
	var name:String;
	var base:String;
	var family:String;
	var start:Int;
	var end:Int;
}

class HxcScriptIdentity {
	/** Balanced top-level class spans; strings, regexes and comments stay opaque. */
	public static function classDeclarations(source:String):Array<HxcScriptClassDeclaration> {
		var text = source == null ? '' : source;
		var tokens = tokenize(text);
		var result:Array<HxcScriptClassDeclaration> = [];
		for (declaration in collectClasses(tokens)) {
			var start = tokens[declaration.start].offset;
			var end = tokens[declaration.end].endOffset;
			result.push({name: declaration.name, base: declaration.base,
				source: text.substring(start, end), start: start, end: end});
		}
		return result;
	}

	/** End of a Haxe regex literal, including flags; callers have checked `~/`. */
	public static function regexLiteralEnd(source:String, start:Int):Int {
		var index = start + 2;
		var escaped = false;
		while (index < source.length) {
			var current = source.charAt(index++);
			if (!escaped && current == '/')
				break;
			if (!escaped && current == '\\') escaped = true; else escaped = false;
		}
		while (index < source.length && isIdentifierPart(source.charAt(index)))
			index++;
		return index;
	}

	/**
		Read the class family selected for this path. A declared character class
		can correct a misplaced path, while a declaration matching the path's
		existing family keeps mixed stage/song/module files in that family.
	*/
	public static function inspect(source:String, pathFamily:String, fileStem:String):HxcScriptIdentityData {
		var tokens = tokenize(source == null ? '' : source);
		var declarations = collectClasses(tokens);
		var family = pathFamily == null || pathFamily == '' ? 'unknown' : pathFamily;
		var selected:HxcIdentityClass = null;
		var characterClass:HxcIdentityClass = null;

		// A class that matches its owning directory remains primary when a file
		// also contains helper classes from another family.
		for (declaration in declarations) {
			if (declaration.family == 'character' && characterClass == null)
				characterClass = declaration;
			if (declaration.family == family && family != 'stage' && selected == null)
				selected = declaration;
		}

		// Stage source files can contain helper declarations before their actual
		// owner. Prefer a Stage whose class name or literal constructor id matches
		// the filename, then fall back to the first declared Stage.
		if (family == 'stage')
			selected = selectStageClass(tokens, declarations, fileStem);

		if (selected == null && characterClass != null) {
			selected = selectCharacterClass(tokens, declarations, fileStem);
			family = 'character';
		}
		// A stages/ path is only a fallback for classless or untyped legacy
		// scripts. If it declares a recognized concrete owner from another
		// family and no Stage declaration exists, let that source type own it.
		if (selected == null && family == 'stage') {
			selected = selectOtherRecognizedClass(declarations);
			if (selected != null)
				family = selected.family;
		}
		if (family == 'character')
			selected = selectCharacterClass(tokens, declarations, fileStem);

		var selectedCharacter = selected != null && selected.family == 'character';
		var selectedStage = selected != null && selected.family == 'stage';
		return {
			family: family,
			characterId: selectedCharacter ? constructorTargetId(tokens, selected) : '',
			characterClassName: selectedCharacter ? selected.name : '',
			stageId: selectedStage ? constructorTargetId(tokens, selected) : '',
			stageClassName: selectedStage ? selected.name : '',
			hasCharacterClass: selectedCharacter,
			hasStageClass: selectedStage,
			hasDeclarations: declarations.length > 0
		};
	}

	static function selectCharacterClass(tokens:Array<HxcIdentityToken>,
		declarations:Array<HxcIdentityClass>, fileStem:String):HxcIdentityClass {
		var first:HxcIdentityClass = null;
		var wanted = normalize(fileStem);
		for (declaration in declarations) {
			if (declaration.family != 'character')
				continue;
			if (first == null)
				first = declaration;
			if (wanted != '' && (normalize(declaration.name) == wanted
				|| normalize(constructorTargetId(tokens, declaration)) == wanted))
				return declaration;
		}
		return first;
	}

	static function selectStageClass(tokens:Array<HxcIdentityToken>,
		declarations:Array<HxcIdentityClass>, fileStem:String):HxcIdentityClass {
		var first:HxcIdentityClass = null;
		var wanted = normalize(fileStem);
		for (declaration in declarations) {
			if (declaration.family != 'stage')
				continue;
			if (first == null)
				first = declaration;
			if (wanted != '' && (normalize(declaration.name) == wanted
				|| normalize(constructorTargetId(tokens, declaration)) == wanted))
				return declaration;
		}
		return first;
	}

	static function selectOtherRecognizedClass(declarations:Array<HxcIdentityClass>):HxcIdentityClass {
		if (declarations == null)
			return null;
		for (declaration in declarations)
			if (declaration.family != '' && declaration.family != 'stage')
				return declaration;
		return null;
	}

	static function constructorTargetId(tokens:Array<HxcIdentityToken>, declaration:HxcIdentityClass):String {
		if (declaration == null || tokens == null)
			return '';
		var depth = 0;
		var index = declaration.start + 1;
		while (index < declaration.end) {
			var token = tokens[index];
			if (token.kind == 'symbol' && token.value == '{') {
				depth++;
				index++;
				continue;
			}
			if (token.kind == 'symbol' && token.value == '}') {
				depth--;
				index++;
				continue;
			}
			if (depth == 1 && token.kind == 'identifier' && token.value == 'function'
				&& index + 1 < declaration.end && tokens[index + 1].value == 'new') {
				var bodyStart = index + 2;
				while (bodyStart < declaration.end
					&& !(tokens[bodyStart].kind == 'symbol' && tokens[bodyStart].value == '{'))
					bodyStart++;
				if (bodyStart >= declaration.end)
					return '';
				var bodyEnd = matchingBrace(tokens, bodyStart, declaration.end);
				if (bodyEnd < 0)
					return '';
				for (call in (bodyStart + 1)...bodyEnd) {
					if (tokens[call].kind != 'identifier' || tokens[call].value != 'super'
						|| call + 2 >= bodyEnd || tokens[call + 1].value != '('
						|| tokens[call + 2].kind != 'string' || !tokens[call + 2].validLiteral)
						continue;
					var next = call + 3;
					if (next < bodyEnd && tokens[next].value != ',' && tokens[next].value != ')')
						continue;
					return tokens[call + 2].value;
				}
				return '';
			}
			index++;
		}
		return '';
	}

	static function collectClasses(tokens:Array<HxcIdentityToken>):Array<HxcIdentityClass> {
		var result:Array<HxcIdentityClass> = [];
		var index = 0;
		var outerDepth = 0;
		while (index < tokens.length) {
			var token = tokens[index];
			if (token.kind == 'symbol' && token.value == '{') {
				outerDepth++;
				index++;
				continue;
			}
			if (token.kind == 'symbol' && token.value == '}') {
				outerDepth--;
				index++;
				continue;
			}
			if (outerDepth != 0 || token.kind != 'identifier' || token.value != 'class'
				|| index + 1 >= tokens.length || tokens[index + 1].kind != 'identifier') {
				index++;
				continue;
			}

			var name = tokens[index + 1].value;
			var base = '';
			var open = index + 2;
			while (open < tokens.length
				&& !(tokens[open].kind == 'symbol' && tokens[open].value == '{')) {
				if (tokens[open].kind == 'identifier' && tokens[open].value == 'extends') {
					var baseEnd = open + 1;
					if (baseEnd < tokens.length && tokens[baseEnd].kind == 'identifier') {
						var parts = [tokens[baseEnd].value];
						baseEnd++;
						while (baseEnd + 1 < tokens.length && tokens[baseEnd].value == '.'
							&& tokens[baseEnd + 1].kind == 'identifier') {
							parts.push(tokens[baseEnd + 1].value);
							baseEnd += 2;
						}
						base = parts.join('.');
						open = baseEnd;
						continue;
					}
				}
				open++;
			}
			if (open >= tokens.length || tokens[open].kind != 'symbol' || tokens[open].value != '{') {
				index++;
				continue;
			}
			var close = matchingBrace(tokens, open, tokens.length);
			if (close < 0) {
				index++;
				continue;
			}
			result.push({name: name, base: base, family: familyForBase(base), start: index, end: close});
			// Class declarations cannot legally nest in Haxe. Skipping the body also
			// prevents a local token sequence from looking like another declaration.
			index = close + 1;
		}
		return result;
	}

	static function matchingBrace(tokens:Array<HxcIdentityToken>, open:Int, limit:Int):Int {
		var depth = 0;
		for (index in open...limit) {
			if (tokens[index].kind == 'symbol' && tokens[index].value == '{')
				depth++;
			else if (tokens[index].kind == 'symbol' && tokens[index].value == '}') {
				depth--;
				if (depth == 0)
					return index;
			}
		}
		return -1;
	}

	public static function familyForBase(base:String):String {
		if (base == null || base == '')
			return '';
		var dot = base.lastIndexOf('.');
		var simple = (dot < 0 ? base : base.substr(dot + 1)).toLowerCase();
		switch (simple) {
			case 'sparrowcharacter' | 'multisparrowcharacter' | 'character' | 'basecharacter'
				| 'funkincharacter' | 'characterinfobase' | 'multicharacter' | 'basesparrowcharacter':
				return 'character';
			case 'song': return 'song';
			case 'stage' | 'basestage': return 'stage';
			case 'module' | 'scriptedmodule': return 'module';
			case 'songevent' | 'scriptedsong_event' | 'scriptedsong-event' | 'scriptedsongevent'
				| 'scriptevent': return 'event';
			case 'notekind' | 'scriptednotekind': return 'note';
			case 'flxruntimeshader': return 'shader';
			case 'musicbeatstate' | 'scriptedmusicbeatstate': return 'state';
			case 'musicbeatsubstate' | 'scriptedmusicbeatsubstate': return 'substate';
			default:
				// V-Slice content commonly chains costume classes through names such
				// as MonikaBaseCharacter. Accept that explicit family suffix without
				// treating arbitrary types containing "character" as actors.
				return simple.endsWith('basecharacter') ? 'character' : '';
		}
	}

	static function tokenize(source:String):Array<HxcIdentityToken> {
		var result:Array<HxcIdentityToken> = [];
		var index = 0;
		while (index < source.length) {
			var character = source.charAt(index);
			var code = character.charCodeAt(0);
			if (code <= 32) {
				index++;
				continue;
			}
			if (character == '/' && index + 1 < source.length) {
				var next = source.charAt(index + 1);
				if (next == '/') {
					index += 2;
					while (index < source.length && source.charAt(index) != '\n' && source.charAt(index) != '\r')
						index++;
					continue;
				}
				if (next == '*') {
					index += 2;
					var commentDepth = 1;
					while (index < source.length && commentDepth > 0) {
						if (index + 1 < source.length && source.charAt(index) == '/' && source.charAt(index + 1) == '*') {
							commentDepth++;
							index += 2;
						} else if (index + 1 < source.length && source.charAt(index) == '*' && source.charAt(index + 1) == '/') {
							commentDepth--;
							index += 2;
						} else {
							index++;
						}
					}
					continue;
				}
			}
			if ((character == '"' || character == '\'') ) {
				var start = index;
				var quote = character;
				var value = new StringBuf();
				var valid = true;
				index++;
				var closed = false;
				while (index < source.length) {
					var current = source.charAt(index++);
					if (current == quote) {
						closed = true;
						break;
					}
					if (current == '\\') {
						valid = false;
						if (index < source.length)
							index++;
						continue;
					}
					value.add(current);
				}
				result.push({value: value.toString(), kind: 'string', validLiteral: valid && closed,
					offset: start, endOffset: index});
				continue;
			}
			// Haxe regular-expression literals can contain text that resembles a
			// class declaration or constructor. Keep their body opaque as well.
			if (character == '~' && index + 1 < source.length && source.charAt(index + 1) == '/') {
				index = regexLiteralEnd(source, index);
				continue;
			}
			if (isIdentifierStart(character)) {
				var start = index++;
				while (index < source.length && isIdentifierPart(source.charAt(index)))
					index++;
				result.push({value: source.substring(start, index), kind: 'identifier', validLiteral: false,
					offset: start, endOffset: index});
				continue;
			}
			result.push({value: character, kind: 'symbol', validLiteral: false,
				offset: index, endOffset: index + 1});
			index++;
		}
		return result;
	}

	static function isIdentifierStart(value:String):Bool {
		if (value == null || value == '') return false;
		var code = value.charCodeAt(0);
		return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || value == '_';
	}

	static function isIdentifierPart(value:String):Bool {
		if (isIdentifierStart(value)) return true;
		if (value == null || value == '') return false;
		var code = value.charCodeAt(0);
		return code >= 48 && code <= 57;
	}

	static function normalize(value:String):String {
		if (value == null) return '';
		var output = new StringBuf();
		for (index in 0...value.length) {
			var character = value.charAt(index).toLowerCase();
			var code = character.charCodeAt(0);
			if ((code >= 97 && code <= 122) || (code >= 48 && code <= 57))
				output.add(character);
		}
		return output.toString();
	}
}
