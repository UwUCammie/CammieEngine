package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
using StringTools;

private typedef PsychStageToken = {
	var kind:String;
	var value:String;
}

/** Reads Psych's source-owned vanillaSongStage mapping without importing or
	executing donor Haxe code. This keeps the importer generic across Psych
	archives and avoids coupling song defaults to a list of known song names. */
class PsychStageInference {
	/** Resolve StageData.hx from the selected donor root. Keep this lookup
		bounded to conventional source locations; never search sibling owners. */
	public static function resolve(sourceRoot:String, songName:String):String {
		#if sys
		if (sourceRoot == null || StringTools.trim(sourceRoot) == '' || songName == null
			|| StringTools.trim(songName) == '')
			return null;
		var root = Path.normalize(sourceRoot);
		for (relative in ['source/backend/StageData.hx', 'source/StageData.hx',
			'src/backend/StageData.hx', 'backend/StageData.hx']) {
			var path = Path.join([root, relative]);
			try {
				if (!FileSystem.exists(path) || FileSystem.isDirectory(path))
					continue;
				var stage = resolveFromSource(File.getContent(path), songName);
				if (stage != null)
					return stage;
			} catch (_:Dynamic) {}
		}
		#end
		return null;
	}

	/** Parse the switch cases and the literal fallback from vanillaSongStage.
		Psych versions vary in whitespace and quote style, so this deliberately
		uses a small token scan instead of line-oriented regular expressions. */
	public static function resolveFromSource(source:String, songName:String):String {
		if (source == null || songName == null || StringTools.trim(songName) == '')
			return null;
		var tokens = tokenize(source);
		var functionOpen = -1;
		var functionClose = -1;
		for (index in 0...tokens.length - 1) {
			if (tokens[index].kind != 'identifier' || tokens[index].value != 'function'
				|| tokens[index + 1].kind != 'identifier' || tokens[index + 1].value != 'vanillaSongStage')
				continue;
			var bodyOpen = index + 2;
			while (bodyOpen < tokens.length
				&& !(tokens[bodyOpen].kind == 'symbol' && tokens[bodyOpen].value == '{'))
				bodyOpen++;
			if (bodyOpen >= tokens.length)
				return null;
			var bodyClose = matchingBrace(tokens, bodyOpen);
			if (bodyClose < 0)
				return null;
			functionOpen = bodyOpen;
			functionClose = bodyClose;
			break;
		}
		if (functionOpen < 0)
			return null;

		var returnedVariable:String = null;
		for (index in functionOpen + 1...functionClose - 1) {
			if (tokens[index].kind == 'identifier' && tokens[index].value == 'return'
				&& tokens[index + 1].kind == 'identifier')
				returnedVariable = tokens[index + 1].value;
		}
		var initializedFallback:String = null;
		if (returnedVariable != null) {
			var firstSwitch = functionClose;
			for (index in functionOpen + 1...functionClose)
				if (tokens[index].kind == 'identifier' && tokens[index].value == 'switch') {
					firstSwitch = index;
					break;
				}
			for (index in functionOpen + 1...firstSwitch - 2) {
				if (tokens[index].kind != 'identifier' || tokens[index].value != 'var'
					|| tokens[index + 1].value != returnedVariable)
					continue;
				var equals = index + 2;
				if (tokens[equals].kind == 'symbol' && tokens[equals].value == ':') {
					while (equals < firstSwitch && !(tokens[equals].kind == 'symbol'
						&& (tokens[equals].value == '=' || tokens[equals].value == ';')))
						equals++;
				} else if (tokens[equals].kind != 'symbol' || tokens[equals].value != '=')
					continue;
				if (equals + 1 < firstSwitch && tokens[equals].kind == 'symbol' && tokens[equals].value == '='
					&& tokens[equals + 1].kind == 'string')
					initializedFallback = tokens[equals + 1].value;
			}
		}

		var wanted = StringTools.trim(songName).toLowerCase();
		var mapped:String = null;
		var fallback:String = null;
		var fallbackReturns:Bool = false;
		var index = functionOpen + 1;
		while (index < functionClose) {
			if (tokens[index].kind != 'identifier' || tokens[index].value != 'switch') {
				index++;
				continue;
			}
			var switchOpen = index + 1;
			while (switchOpen < functionClose
				&& !(tokens[switchOpen].kind == 'symbol' && tokens[switchOpen].value == '{'))
				switchOpen++;
			if (switchOpen >= functionClose)
				break;
			var switchClose = matchingBrace(tokens, switchOpen);
			if (switchClose < 0 || switchClose > functionClose)
				break;
			var caseIndex = switchOpen + 1;
			while (caseIndex < switchClose) {
				var marker = tokens[caseIndex].value;
				if (tokens[caseIndex].kind != 'identifier' || (marker != 'case' && marker != 'default')) {
					caseIndex++;
					continue;
				}
				var labelStart = caseIndex + 1;
				var colon = labelStart;
				while (colon < switchClose
					&& !(tokens[colon].kind == 'symbol' && tokens[colon].value == ':'))
					colon++;
				if (colon >= switchClose)
					break;
				var branchEnd = colon + 1;
				while (branchEnd < switchClose && !(tokens[branchEnd].kind == 'identifier'
					&& (tokens[branchEnd].value == 'case' || tokens[branchEnd].value == 'default')))
					branchEnd++;
				var branchStage = stageFromBranch(tokens, colon + 1, branchEnd, returnedVariable);
				if (marker == 'default') {
					if (branchStage != null) {
						fallback = branchStage;
						fallbackReturns = branchHasLiteralReturn(tokens, colon + 1, branchEnd);
					}
				} else if (branchStage != null) {
					for (label in labelStart...colon)
						if (tokens[label].kind == 'string'
							&& tokens[label].value.toLowerCase() == wanted) {
							mapped = branchStage;
							break;
						}
				}
				caseIndex = branchEnd;
			}
			index = switchClose + 1;
		}
		if (mapped != null)
			return mapped;
		if (fallback != null && fallbackReturns)
			return fallback;
		var trailingLiteralReturn = literalReturnAtFunctionScope(tokens, functionOpen, functionClose);
		if (trailingLiteralReturn != null)
			return trailingLiteralReturn;
		if (fallback != null)
			return fallback;
		return initializedFallback;
	}

	static function branchHasLiteralReturn(tokens:Array<PsychStageToken>, start:Int, end:Int):Bool {
		for (index in start...end)
			if (tokens[index].kind == 'identifier' && tokens[index].value == 'return' && index + 1 < end
				&& tokens[index + 1].kind == 'string')
				return true;
		return false;
	}

	/** Psych versions often put `return 'stage'` after the switch rather than
		using a default case. Only accept a literal return at function-body scope;
		returns nested in a case or conditional are not a general fallback. */
	static function literalReturnAtFunctionScope(tokens:Array<PsychStageToken>,
		functionOpen:Int, functionClose:Int):String {
		var nestedBlocks = 0;
		var result:String = null;
		for (index in functionOpen + 1...functionClose) {
			if (tokens[index].value == '{') {
				nestedBlocks++;
				continue;
			}
			if (tokens[index].value == '}') {
				nestedBlocks--;
				continue;
			}
			if (nestedBlocks == 0 && tokens[index].kind == 'identifier' && tokens[index].value == 'return'
				&& index + 1 < functionClose && tokens[index + 1].kind == 'string')
				result = tokens[index + 1].value;
		}
		return result;
	}

	static function stageFromBranch(tokens:Array<PsychStageToken>, start:Int, end:Int,
		returnedVariable:String):String {
		for (index in start...end) {
			if (tokens[index].kind == 'identifier' && tokens[index].value == 'return' && index + 1 < end
				&& tokens[index + 1].kind == 'string')
				return tokens[index + 1].value;
			if (returnedVariable != null && tokens[index].value == returnedVariable
				&& index + 2 < end && tokens[index + 1].kind == 'symbol' && tokens[index + 1].value == '='
				&& tokens[index + 2].kind == 'string')
				return tokens[index + 2].value;
		}
		// Some Psych versions implement vanillaSongStage as a switch expression
		// whose case value itself is the stage string.
		if (start < end && tokens[start].kind == 'string')
			return tokens[start].value;
		return null;
	}

	static function matchingBrace(tokens:Array<PsychStageToken>, open:Int):Int {
		var depth = 0;
		for (index in open...tokens.length) {
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

	static function tokenize(source:String):Array<PsychStageToken> {
		var result:Array<PsychStageToken> = [];
		var index = 0;
		while (index < source.length) {
			var code = source.charCodeAt(index);
			if (code <= 32) {
				index++;
				continue;
			}
			if (source.charAt(index) == '/' && index + 1 < source.length) {
				var next = source.charAt(index + 1);
				if (next == '/') {
					index += 2;
					while (index < source.length && source.charAt(index) != '\n')
						index++;
					continue;
				}
				if (next == '*') {
					index += 2;
					while (index + 1 < source.length
						&& !(source.charAt(index) == '*' && source.charAt(index + 1) == '/'))
						index++;
					index = index + 1 < source.length ? index + 2 : source.length;
					continue;
				}
			}
			var character = source.charAt(index);
			if (character == '\'' || character == '"') {
				var quote = character;
				var value = new StringBuf();
				index++;
				while (index < source.length && source.charAt(index) != quote) {
					character = source.charAt(index++);
					if (character == '\\' && index < source.length) {
						var escaped = source.charAt(index++);
						switch (escaped) {
							case 'n': value.add('\n');
							case 'r': value.add('\r');
							case 't': value.add('\t');
							default: value.add(escaped);
						}
					} else
						value.add(character);
				}
				if (index < source.length)
					index++;
				result.push({kind:'string', value:value.toString()});
				continue;
			}
			if (isIdentifierStart(code)) {
				var start = index++;
				while (index < source.length && isIdentifierPart(source.charCodeAt(index)))
					index++;
				result.push({kind:'identifier', value:source.substring(start, index)});
				continue;
			}
			result.push({kind:'symbol', value:character});
			index++;
		}
		return result;
	}

	static inline function isIdentifierStart(code:Int):Bool
		return code == 95 || code == 36 || code >= 65 && code <= 90 || code >= 97 && code <= 122;

	static inline function isIdentifierPart(code:Int):Bool
		return isIdentifierStart(code) || code >= 48 && code <= 57;
}
