package;

#if sys
import haxe.io.Path;
import sys.FileSystem;
#end

using StringTools;

/** One literal asset lookup authored by a foreign HXC script. */
typedef HxcAssetReference = {
	var kind:String;
	var key:String;
}

/**
	The bounded, static part of the HXC asset import contract.

	HXC scripts are copied into a manifest namespace, so their literal
	`Paths.image`/atlas and bounded audio lookups must be planned against that
	same namespace. A
	plan never executes donor code and never walks the donor media tree: only HXC
	scripts below the known script/data families are read, and only literal
	lookups in those files become asset references.
*/
typedef HxcAssetPlan = {
	var scripts:Array<String>;
	var references:Array<HxcAssetReference>;
}

private typedef HxcArgument = {
	var expression:String;
	var consumed:Int;
}

private typedef HxcBalanced = {
	var text:String;
	var consumed:Int;
}

private enum HxcFiniteValue {
	HxcUnknown;
	HxcNullValue;
	HxcStringValue(value:String);
	HxcNumberValue(value:Float);
	HxcBoolValue(value:Bool);
	HxcArrayValue(values:Array<HxcFiniteValue>);
}

private typedef HxcFunctionParameter = {
	var name:String;
	var defaultExpression:String;
}

private typedef HxcFunctionRegion = {
	var name:String;
	var parameters:Array<HxcFunctionParameter>;
	var bodyStart:Int;
	var bodyEnd:Int;
	var body:String;
}

private typedef HxcFiniteLoop = {
	var variable:String;
	var expression:String;
	var bodyStart:Int;
	var bodyEnd:Int;
}

class HxcAssetPlanner {
	/** Return de-duplicated literal Paths.* references from one HXC source. */
	public static function literalReferences(source:String, includeData:Bool = false):Array<HxcAssetReference> {
		var result:Array<HxcAssetReference> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var add = function(kind:String, key:String):Void {
			if (key == null || StringTools.trim(key) == '')
				return;
			var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
			// Paths resolves adjacent separators inside relative keys. Preserve a
			// leading slash so the importer still rejects absolute asset paths.
			while (clean.indexOf('//') >= 0)
				clean = StringTools.replace(clean, '//', '/');
			var identity = kind + ':' + clean.toLowerCase();
			if (seen.exists(identity))
				return;
			seen.set(identity, true);
			result.push({kind:kind, key:clean});
		};
		var collect = function(pattern:String, kind:String):Void {
			if (source == null || source == '')
				return;
			var expression = new EReg(pattern, 'g');
			var remaining = source;
			var attempts = 0;
			while (attempts++ < 4096 && expression.match(remaining)) {
				var key = '';
				try key = expression.matched(1) catch (_:Dynamic) {}
				add(kind, key);
				var position = expression.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length)
					break;
				remaining = remaining.substr(position.pos + position.len);
			}
		};
		// A path literal must be a complete first argument.  The old prefix
		// regexp accepted the first quoted fragment of an expression such as
		// `Paths.getSparrowAtlas('rabbit/speakers/' + img)`, producing a bogus
		// `rabbit/speakers/` dependency.  The bounded expression pass below can
		// expand known values, while genuinely runtime-only expressions remain
		// unplanned and are resolved by the runtime proxy.
		collect('Paths\\s*\\.\\s*frag\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'frag');
		collect('Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'sound');
		collect('Paths\\s*\\.\\s*music\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'music');
		// Paths.file can name a package-root asset such as a window icon.
		// Preserve its exact relative path under the selected import owner.
		collect('Paths\\s*\\.\\s*file\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'file');
		if (includeData) {
		collect('Paths\\s*\\.\\s*font\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'font');
		// Some Codename states pass a relative font file directly to FlxText
		// instead of resolving it through Paths.font. Keep these literal text
		// dependencies in the same owner namespace as Paths.font references.
		collect('\\bsetFormat\\s*\\(\\s*["\\\'](?:\\./)?fonts/([^"\\\']+)["\\\']', 'font');
		collect('(?:\\bfont|\\.font)\\s*=\\s*["\\\'](?:\\./)?fonts/([^"\\\']+)["\\\']', 'font');
		collect('Paths\\s*\\.\\s*xml\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'xml');
		collect('Paths\\s*\\.\\s*json\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'json');
		collect('Paths\\s*\\.\\s*txt\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*(?:\\)|,)', 'txt');
		}
		collectPathExpressions(source, add);
		// V-Slice character hooks commonly construct a temporary death sprite
		// with `FunkinSprite.createSparrow(..., assetId)`.  Keep this import
		// surface literal-only as well, resolving only one-hop string aliases;
		// arbitrary runtime expressions remain a bounded no-op at load time.
		collectCreateSparrowReferences(source, add);
		// Song-credit modules build their icon id from a bounded local variable
		// (`'songCredits/' + iconName`) rather than a Paths.* call. Resolve only
		// literal assignments to that variable so the importer copies authored
		// PNGs without walking the donor image tree or guessing dynamic paths.
		collectSongCreditReferences(source, add);
		// HXC song scripts can change the HUD strip to a semantic health-icon
		// id without naming an image path (for example
		// `PlayState.instance.iconP2.loadCharacter('guest')`). Preserve only
		// literal ids on the engine's iconP slots so the importer can resolve the
		// image in the selected owner namespace without scanning donor media.
		collect('\\biconP[0-9]+\\s*\\.\\s*(?:loadCharacter|setCharacter|setIcon|loadIcon)\\s*\\(\\s*["\\\']([A-Za-z0-9_-]+)["\\\']\\s*(?:\\)|,)', 'health-icon');
		// A few donor helpers pass a literal atlas id through a typed parameter,
		// e.g. `createMenuItem(..., 'mainmenu/PleaseKrillMe', ...)` followed by
		// `Paths.getSparrowAtlas(atlas)`.  Resolve that bounded one-hop alias
		// statically; arbitrary expressions remain runtime fallback paths.
		collectBoundLiteralReferences(source, add);
		remapPermanentTextureCacheSounds(source, result, add);
		return result;
	}

	/** A few HXC packages pass `Paths.sound(key)` to the texture-cache API.
		The texture operation owns the asset kind: resolve that key in the image
		tree and warm a bitmap, while leaving a same-key sound reference intact
		when another call actually requests it as audio. */
	static function remapPermanentTextureCacheSounds(source:String,
		references:Array<HxcAssetReference>, add:String->String->Void):Void {
		if (source == null || source == '' || references == null || add == null)
			return;
		var cached:Array<{key:String, start:Int, end:Int}> = [];
		var textureCache = new EReg('FunkinMemory\\s*\\.\\s*permanentCacheTexture\\s*\\(', 'g');
		var remaining = source;
		var offset = 0;
		var attempts = 0;
		while (attempts++ < 1024 && textureCache.match(remaining)) {
			var position = textureCache.matchedPos();
			var callStart = offset + position.pos;
			var open = callStart + position.len - 1;
			var argument = readCallArgument(source, open + 1);
			if (argument != null) {
				var expression = StringTools.trim(argument.expression);
				var pathCall = new EReg('^Paths\\s*\\.\\s*(?:sound|image)\\s*\\(', 'm');
				if (pathCall.match(expression)) {
					var keyArgument = readCallArgument(expression, pathCall.matchedPos().len);
					var key = keyArgument == null ? null : wholeStringLiteral(StringTools.trim(keyArgument.expression));
					if (key != null && key != '') {
						var callEnd = open + argument.consumed;
						cached.push({key:key, start:callStart, end:callEnd});
					}
				}
			}
			var advance = position.pos + position.len;
			if (position.len <= 0 || advance >= remaining.length)
				break;
			offset += advance;
			remaining = remaining.substr(advance);
		}
		if (cached.length == 0)
			return;

		var outsideLiteralSounds:Map<String, Bool> = new Map();
		var unknownOutsideSound = false;
		var soundCall = new EReg('Paths\\s*\\.\\s*sound\\s*\\(', 'g');
		remaining = source;
		offset = 0;
		attempts = 0;
		while (attempts++ < 4096 && soundCall.match(remaining)) {
			var position = soundCall.matchedPos();
			var callStart = offset + position.pos;
			var insideTextureCache = false;
			for (entry in cached)
				if (callStart >= entry.start && callStart < entry.end) {
					insideTextureCache = true;
					break;
				}
			if (!insideTextureCache) {
				var argument = readCallArgument(source, callStart + position.len);
				var key = argument == null ? null : wholeStringLiteral(StringTools.trim(argument.expression));
				if (key == null)
					unknownOutsideSound = true;
				else
					outsideLiteralSounds.set(key.toLowerCase(), true);
			}
			var advance = position.pos + position.len;
			if (position.len <= 0 || advance >= remaining.length)
				break;
			offset += advance;
			remaining = remaining.substr(advance);
		}

		for (entry in cached) {
			var key = entry.key.toLowerCase();
			if (!unknownOutsideSound && !outsideLiteralSounds.exists(key)) {
				for (index in 0...references.length) {
					var reference = references[index];
					if (reference.kind != null && reference.kind.toLowerCase() == 'sound'
						&& reference.key != null && reference.key.toLowerCase() == key) {
						references.splice(index, 1);
						break;
					}
				}
			}
			add('image', entry.key);
		}
	}

	/**
		Collect Paths.image/atlas/frame/sound/music calls with a bounded string
		expression as their first argument. V-Slice HXC uses this for authored
		finite string templates, and literal integer bounds can expand FlxG.random.int
		into a capped inclusive set of audio paths.
		This is deliberately a bounded lexical evaluator: it tracks literals,
		nested arrays, simple conditions, indices, local assignments, and literal
		function arguments, but never executes donor code or walks arbitrary media.
	*/
	static function collectPathExpressions(source:String, add:String->String->Void):Void {
		if (source == null || StringTools.trim(source) == '')
			return;
		var values = collectStringValues(source);
		var call = new EReg('Paths\\s*\\.\\s*(image|getSparrowAtlas|getPackerAtlas|getFrames|sound|music)\\s*\\(', 'g');
		var remaining = source;
		var sourceOffset = 0;
		var attempts = 0;
		while (attempts++ < 4096 && call.match(remaining)) {
			var method = call.matched(1);
			var position = call.matchedPos();
			var start = position.pos + position.len;
			var first = readCallArgument(remaining, start);
			if (first != null) {
				var kind = switch (method) {
					case 'image': 'image';
					case 'getPackerAtlas': 'packer';
					case 'getFrames': 'frames';
					case 'sound': 'sound';
					case 'music': 'music';
					default: 'sparrow';
				};
				var contextualValues = expandStringExpressionInContext(source,
					first.expression, sourceOffset + position.pos);
				if (contextualValues != null) {
					for (value in contextualValues)
						add(kind, value);
				} else {
					var expanded = expandStringExpression(first.expression, values);
					if (expanded.length == 0)
						expanded = expandFiniteStringExpression(first.expression, values);
					for (value in expanded)
						add(kind, value);
				}
				var consumed = start + first.consumed;
				if (consumed <= position.pos || consumed >= remaining.length)
					break;
				sourceOffset += consumed;
				remaining = remaining.substr(consumed);
			} else {
				if (position.len <= 0 || position.pos + position.len >= remaining.length)
					break;
				sourceOffset += position.pos + position.len;
				remaining = remaining.substr(position.pos + position.len);
			}
		}
	}

	/**
		Evaluate a path template in bounded literal call contexts for its
		containing function. Nested arrays stay grouped, so selecting a row and
		then using an unknown runtime index returns only members of that row.
		`null` means this lexical subset did not resolve the expression and the
		conservative literal resolver should handle it.
	*/
	static function expandStringExpressionInContext(source:String, expression:String,
		callPosition:Int):Null<Array<String>> {
		if (source == null || expression == null || callPosition < 0)
			return null;
		var region = containingFunction(source, callPosition);
		if (region == null)
			return null;
		var globalValues = readFiniteArrays(source);
		var contexts = functionCallContexts(source, region, globalValues);
		if (contexts.length == 0)
			return null;
		var relativeEnd = callPosition - region.bodyStart;
		if (relativeEnd < 0 || relativeEnd > region.body.length)
			return null;
		var statements = splitStatements(region.body.substr(0, relativeEnd));
		var result:Array<String> = [];
		for (context in contexts) {
			var env = copyFiniteEnvironment(globalValues);
			for (name in context.keys())
				env.set(name, context.get(name));
			for (statement in statements) {
				var assignment = parseAssignment(statement);
				if (assignment == null)
					continue;
				var guardResult:Null<Bool> = assignment.condition == null
					? true : evaluateFiniteCondition(assignment.condition, env, 0);
				if (guardResult == false)
					continue;
				var evaluated = evaluateFiniteExpression(assignment.expression, env, 0);
				if (evaluated.length > 0) {
					if (guardResult == null && env.exists(assignment.name))
						for (value in env.get(assignment.name)) addFinite(evaluated, value);
						env.set(assignment.name, evaluated);
				}
			}
			var loopContexts = expandEnclosingFiniteLoops(region, relativeEnd, env);
			for (loopEnv in loopContexts) {
				var finalValues = evaluateFiniteExpression(expression, loopEnv, 0);
				for (value in finalValues) {
					var text = finiteString(value);
					if (text != null && result.indexOf(text) < 0 && result.length < 256)
						result.push(text);
				}
			}
		}
		return result.length == 0 ? null : result;
	}

	/**
		Expand only enclosing `for (name in finiteArray)` loops. The expression
		parser supplies a literal array domain; runtime collections stay unknown,
		and both nesting and cross-products are capped to keep imports bounded.
	*/
	static function expandEnclosingFiniteLoops(region:HxcFunctionRegion, callPosition:Int,
		initial:Map<String, Array<HxcFiniteValue>>):Array<Map<String, Array<HxcFiniteValue>>> {
		var loops:Array<HxcFiniteLoop> = [];
		var pattern = new EReg('for\\s*\\(\\s*(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s+in\\s+([^)]*)\\)\\s*\\{', 'g');
		var remaining = region.body;
		var offset = 0;
		var attempts = 0;
		while (attempts++ < 256 && pattern.match(remaining)) {
			var variable = pattern.matched(1);
			var collection = StringTools.trim(pattern.matched(2));
			var position = pattern.matchedPos();
			var open = offset + position.pos + position.len - 1;
			var balanced = readBalanced(region.body, open, '{', '}');
			if (balanced != null) {
				var bodyStart = open + 1;
				var bodyEnd = open + balanced.consumed - 1;
				if (callPosition >= bodyStart && callPosition < bodyEnd)
					loops.push({variable:variable, expression:collection, bodyStart:bodyStart, bodyEnd:bodyEnd});
			}
			var consumed = position.pos + position.len;
			if (consumed <= 0 || offset + consumed >= region.body.length)
				break;
			offset += consumed;
			remaining = region.body.substr(offset);
		}

		var contexts:Array<Map<String, Array<HxcFiniteValue>>> = [copyFiniteEnvironment(initial)];
		for (loop in loops) {
			var expanded:Array<Map<String, Array<HxcFiniteValue>>> = [];
			for (context in contexts) {
				var domains = evaluateFiniteExpression(loop.expression, context, 0);
				var members:Array<HxcFiniteValue> = [];
				for (domain in domains)
					switch (domain) {
						case HxcArrayValue(values):
							for (value in values) {
								addFinite(members, value);
								if (members.length >= 128) break;
							}
						default:
					}
				if (members.length == 0) {
					var unknownContext = copyFiniteEnvironment(context);
					unknownContext.set(loop.variable, [HxcUnknown]);
					if (expanded.length < 128) expanded.push(unknownContext);
				} else {
					for (member in members) {
						var itemContext = copyFiniteEnvironment(context);
						itemContext.set(loop.variable, [member]);
						if (expanded.length < 128) expanded.push(itemContext);
						else break;
					}
				}
			}
			contexts = expanded;
			if (contexts.length == 0) break;
		}
		return contexts;
	}

	static function containingFunction(source:String, position:Int):Null<HxcFunctionRegion> {
		var declaration = new EReg('function\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(([^)]*)\\)\\s*\\{', 'g');
		var remaining = source;
		var offset = 0;
		var attempts = 0;
		var best:Null<HxcFunctionRegion> = null;
		while (attempts++ < 1024 && declaration.match(remaining)) {
			var functionName = declaration.matched(1);
			var parameterText = declaration.matched(2);
			var matchPosition = declaration.matchedPos();
			var declarationStart = offset + matchPosition.pos;
			var open = declarationStart + matchPosition.len - 1;
			var balanced = readBalanced(source, open, '{', '}');
			if (balanced != null) {
				var bodyStart = open + 1;
				var bodyEnd = open + balanced.consumed - 1;
				if (position >= bodyStart && position < bodyEnd
					&& (best == null || balanced.consumed < best.bodyEnd - best.bodyStart + 2)) {
					var parameters:Array<HxcFunctionParameter> = [];
					for (rawParameter in splitTopLevel(parameterText, ',')) {
						var clean = StringTools.trim(rawParameter);
						if (clean == '') continue;
						if (clean.startsWith('?')) clean = StringTools.trim(clean.substr(1));
						var equals = findTopLevelAssignment(clean);
						var defaultExpression = equals < 0 ? '' : StringTools.trim(clean.substr(equals + 1));
						var declarationText = equals < 0 ? clean : StringTools.trim(clean.substr(0, equals));
						var colon = declarationText.indexOf(':');
						var parameterName = StringTools.trim(colon < 0
							? declarationText : declarationText.substr(0, colon));
						if (parameterName != '')
							parameters.push({name:parameterName, defaultExpression:defaultExpression});
					}
					best = {
						name: functionName,
						parameters: parameters,
						bodyStart: bodyStart,
						bodyEnd: bodyEnd,
						body: source.substr(bodyStart, bodyEnd - bodyStart)
					};
				}
			}
			var consumed = matchPosition.pos + matchPosition.len;
			if (consumed <= 0 || offset + consumed >= source.length)
				break;
			offset += consumed;
			remaining = source.substr(offset);
		}
		return best;
	}

	static function functionCallContexts(source:String, region:HxcFunctionRegion,
		globalValues:Map<String, Array<HxcFiniteValue>>):Array<Map<String, Array<HxcFiniteValue>>> {
		var result:Array<Map<String, Array<HxcFiniteValue>>> = [];
		var pattern = new EReg('\\b' + region.name + '\\s*\\(', 'g');
		var remaining = source;
		var offset = 0;
		var attempts = 0;
		while (attempts++ < 512 && pattern.match(remaining)) {
			var matchPosition = pattern.matchedPos();
			var absolutePosition = offset + matchPosition.pos;
			var before = StringTools.trim(source.substr(0, absolutePosition));
			var isDeclaration = before.endsWith('function');
			var open = absolutePosition + matchPosition.len - 1;
			var argumentsBody = readBalanced(source, open, '(', ')');
			if (!isDeclaration && argumentsBody != null) {
				var argumentsList = splitTopLevel(argumentsBody.text, ',');
				if (argumentsList.length == 1 && argumentsList[0] == '') argumentsList.resize(0);
				var base:Map<String, Array<HxcFiniteValue>> = new Map<String, Array<HxcFiniteValue>>();
				for (index in 0...region.parameters.length) {
					var parameter = region.parameters[index];
					var values:Array<HxcFiniteValue>;
					if (index < argumentsList.length) {
						values = evaluateFiniteExpression(argumentsList[index], globalValues, 0);
					} else if (parameter.defaultExpression != '') {
						values = evaluateFiniteExpression(parameter.defaultExpression, globalValues, 0);
					} else {
						values = [HxcUnknown];
					}
					base.set(parameter.name, values.length == 0 ? [HxcUnknown] : values);
				}
				appendFiniteContext(result, base);
			}
			var consumed = matchPosition.pos + matchPosition.len;
			if (consumed <= 0 || offset + consumed >= source.length)
				break;
			offset += consumed;
			remaining = source.substr(offset);
		}
		if (result.length > 0)
			return result;

		// When no call site is statically visible, evaluate the defaults and the
		// literal alternatives used by simple parameter comparisons. This keeps
		// externally-called helpers bounded without flattening related arrays.
		var domains:Map<String, Array<HxcFiniteValue>> = new Map<String, Array<HxcFiniteValue>>();
		for (parameter in region.parameters) {
			var domain:Array<HxcFiniteValue> = parameter.defaultExpression == ''
				? [HxcUnknown] : evaluateFiniteExpression(parameter.defaultExpression, globalValues, 0);
			var comparison = new EReg('\\b' + parameter.name + '\\s*(?:==|!=)\\s*(["\\\'][^"\\\']*["\\\'])', 'g');
			var bodyRemaining = region.body;
			var comparisonAttempts = 0;
			while (comparisonAttempts++ < 128 && comparison.match(bodyRemaining)) {
				var literal = evaluateFiniteExpression(comparison.matched(1), globalValues, 0);
				for (value in literal)
					if (finiteIndex(domain, value) < 0) domain.push(value);
				var position = comparison.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= bodyRemaining.length) break;
				bodyRemaining = bodyRemaining.substr(position.pos + position.len);
			}
			domains.set(parameter.name, domain.length == 0 ? [HxcUnknown] : domain);
		}
		var fallback:Map<String, Array<HxcFiniteValue>> = new Map<String, Array<HxcFiniteValue>>();
		for (parameter in region.parameters)
			fallback.set(parameter.name, domains.get(parameter.name));
		appendFiniteContext(result, fallback);
		return result;
	}

	static function appendFiniteContext(contexts:Array<Map<String, Array<HxcFiniteValue>>>,
		context:Map<String, Array<HxcFiniteValue>>):Void {
		if (contexts.length >= 128) return;
		contexts.push(context);
	}

	static function readFiniteArrays(source:String):Map<String, Array<HxcFiniteValue>> {
		var result:Map<String, Array<HxcFiniteValue>> = new Map<String, Array<HxcFiniteValue>>();
		if (source == null || source == '') return result;
		var assignment = new EReg('(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*'
			+ '(?::[^=;\\n]+)?=\\s*\\[', 'g');
		var remaining = source;
		var offset = 0;
		var attempts = 0;
		while (attempts++ < 1024 && assignment.match(remaining)) {
			var name = assignment.matched(1);
			var position = assignment.matchedPos();
			var open = offset + position.pos + position.len - 1;
			var balanced = readBalanced(source, open, '[', ']');
			if (balanced != null) {
				var value = evaluateFiniteExpression(source.substr(open, balanced.consumed), result, 0);
				if (value.length > 0) result.set(name, value);
			}
			var consumed = position.pos + position.len;
			if (consumed <= 0 || offset + consumed >= source.length) break;
			offset += consumed;
			remaining = source.substr(offset);
		}
		return result;
	}

	static function copyFiniteEnvironment(source:Map<String, Array<HxcFiniteValue>>):Map<String, Array<HxcFiniteValue>> {
		var result:Map<String, Array<HxcFiniteValue>> = new Map<String, Array<HxcFiniteValue>>();
		if (source != null)
			for (name in source.keys()) result.set(name, source.get(name).copy());
		return result;
	}

	static function splitStatements(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null) return result;
		var start = 0;
		var quote = '';
		var escaped = false;
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") quote = current;
			else if (current == ';') {
				result.push(StringTools.trim(source.substr(start, index - start)));
				start = index + 1;
			}
		}
		if (start < source.length)
			result.push(StringTools.trim(source.substr(start)));
		return result;
	}

	static function parseAssignment(statement:String):Null<{name:String, expression:String, condition:Null<String>}> {
		if (statement == null || StringTools.trim(statement) == '') return null;
		var condition = assignmentGuard(statement);
		var scopeOpen = statement.lastIndexOf('{');
		var scopeClose = statement.lastIndexOf('}');
		if (scopeOpen > scopeClose)
			statement = statement.substr(scopeOpen + 1);
		var index = findTopLevelAssignment(statement);
		if (index < 0) return null;
		var left = StringTools.trim(statement.substr(0, index));
		var right = StringTools.trim(statement.substr(index + 1));
		var blockOpen = left.lastIndexOf('{');
		var blockClose = left.lastIndexOf('}');
		var block = blockOpen > blockClose ? blockOpen : blockClose;
		var close = left.lastIndexOf(')');
		var cut = block > close ? block : close;
		if (cut >= 0) left = StringTools.trim(left.substr(cut + 1));
		var namePattern = new EReg('^(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::[^=]+)?$', '');
		if (!namePattern.match(left) || right == '') return null;
		return {name:namePattern.matched(1), expression:right, condition:condition};
	}

	static function assignmentGuard(statement:String):Null<String> {
		var pattern = new EReg('\\bif\\s*\\(', 'g');
		var remaining = statement;
		var offset = 0;
		var attempts = 0;
		var guard:Null<String> = null;
		while (attempts++ < 16 && pattern.match(remaining)) {
			var position = pattern.matchedPos();
			var open = offset + position.pos + position.len - 1;
			var balanced = readBalanced(statement, open, '(', ')');
			if (balanced != null) guard = balanced.text;
			var consumed = position.pos + position.len;
			if (consumed <= 0 || offset + consumed >= statement.length) break;
			offset += consumed;
			remaining = statement.substr(offset);
		}
		return guard == null ? null : StringTools.trim(guard);
	}

	static function findTopLevelAssignment(source:String):Int {
		var quote = '';
		var escaped = false;
		var parentheses = 0;
		var brackets = 0;
		var braces = 0;
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") { quote = current; continue; }
			switch (current) {
				case '(': parentheses++;
				case ')': if (parentheses > 0) parentheses--;
				case '[': brackets++;
				case ']': if (brackets > 0) brackets--;
				case '{': braces++;
				case '}': if (braces > 0) braces--;
				case '=':
					if (parentheses == 0 && brackets == 0 && braces == 0) {
						var previous = index > 0 ? source.charAt(index - 1) : '';
					var next = index + 1 < source.length ? source.charAt(index + 1) : '';
						if (previous != '=' && previous != '!' && previous != '<' && previous != '>'
							&& next != '=' && next != '>') return index;
					}
				default:
			}
		}
		return -1;
	}

	static function evaluateFiniteExpression(expression:String,
		env:Map<String, Array<HxcFiniteValue>>, depth:Int):Array<HxcFiniteValue> {
		if (expression == null || depth > 16) return [HxcUnknown];
		var clean = StringTools.trim(expression);
		while (clean.endsWith(';')) clean = StringTools.trim(clean.substr(0, clean.length - 1));
		if (clean == '') return [HxcUnknown];
		var whole = readBalanced(clean, 0, '(', ')');
		if (clean.charAt(0) == '(' && whole != null && whole.consumed == clean.length)
			return evaluateFiniteExpression(whole.text, env, depth + 1);

		var question = findTopLevelChar(clean, '?', 0);
		if (question >= 0) {
			var colon = findMatchingConditionalColon(clean, question + 1);
			if (colon >= 0) {
				var condition = evaluateFiniteCondition(clean.substr(0, question), env, depth + 1);
				var left = clean.substr(question + 1, colon - question - 1);
				var right = clean.substr(colon + 1);
				if (condition == true) return evaluateFiniteExpression(left, env, depth + 1);
				if (condition == false) return evaluateFiniteExpression(right, env, depth + 1);
				var alternatives = evaluateFiniteExpression(left, env, depth + 1);
				for (value in evaluateFiniteExpression(right, env, depth + 1)) addFinite(alternatives, value);
				return alternatives;
			}
		}

		var plusTerms = splitTopLevel(clean, '+');
		if (plusTerms.length > 1) {
			var combinations:Array<HxcFiniteValue> = [HxcStringValue('')];
			for (term in plusTerms) {
				var options = evaluateFiniteExpression(term, env, depth + 1);
				var next:Array<HxcFiniteValue> = [];
				for (left in combinations)
					for (right in options) {
						var leftText = finiteString(left);
						var rightText = finiteString(right);
						if (leftText != null && rightText != null)
							addFinite(next, HxcStringValue(leftText + rightText));
						if (next.length >= 256) break;
					}
				combinations = next;
				if (combinations.length == 0) return [HxcUnknown];
			}
			return combinations;
		}

		var indexOpen = findTrailingIndexOpen(clean);
		if (indexOpen > 0) {
			var arrays = evaluateFiniteExpression(clean.substr(0, indexOpen), env, depth + 1);
			var indices = evaluateFiniteExpression(clean.substr(indexOpen + 1, clean.length - indexOpen - 2), env, depth + 1);
			var result:Array<HxcFiniteValue> = [];
			for (array in arrays)
				switch (array) {
					case HxcArrayValue(items):
						for (index in indices)
						switch (index) {
							case HxcNumberValue(value):
								var at = Std.int(value);
								if (at >= 0 && at < items.length) addFinite(result, items[at]);
							case HxcUnknown:
								for (item in items) addFinite(result, item);
							default:
								for (item in items) addFinite(result, item);
						}
					default:
				}
			return result.length == 0 ? [HxcUnknown] : result;
		}

		var arrayLiteral = readBalanced(clean, 0, '[', ']');
		if (clean.charAt(0) == '[' && arrayLiteral != null && arrayLiteral.consumed == clean.length) {
			var members = splitTopLevel(arrayLiteral.text, ',');
			if (members.length == 1 && members[0] == '') members.resize(0);
			var combinations:Array<Array<HxcFiniteValue>> = [[]];
			for (member in members) {
				var options = evaluateFiniteExpression(member, env, depth + 1);
				var next:Array<Array<HxcFiniteValue>> = [];
				for (prior in combinations)
					for (option in options) {
						var copy = prior.copy();
						copy.push(option);
						if (next.length < 128) next.push(copy);
					}
				combinations = next;
			}
			var result:Array<HxcFiniteValue> = [];
			for (items in combinations) addFinite(result, HxcArrayValue(items));
			return result.length == 0 ? [HxcArrayValue([])] : result;
		}

		var literal = wholeStringLiteral(clean);
		if (literal != null) return [HxcStringValue(literal)];
		var randomIntPrefix = new EReg('^FlxG\\s*\\.\\s*random\\s*\\.\\s*int\\s*\\(', '');
		if (randomIntPrefix.match(clean)) {
			// Random integer paths are useful to import only when both inclusive
			// bounds are literal integers and the resulting set stays small. Keep
			// this specific to Flixel's seeded/random API shape; other calls remain
			// runtime-only instead of being guessed by the importer.
			var prefix = randomIntPrefix.matchedPos();
			var open = prefix.pos + prefix.len - 1;
			var arguments = readBalanced(clean, open, '(', ')');
			if (arguments == null || open + arguments.consumed != clean.length)
				return [HxcUnknown];
			var bounds = splitTopLevel(arguments.text, ',');
			if (bounds.length != 2
				|| !new EReg('^-?[0-9]+$', '').match(StringTools.trim(bounds[0]))
				|| !new EReg('^-?[0-9]+$', '').match(StringTools.trim(bounds[1])))
				return [HxcUnknown];
			var minimum = Std.parseFloat(StringTools.trim(bounds[0]));
			var maximum = Std.parseFloat(StringTools.trim(bounds[1]));
			var count = maximum - minimum + 1;
			if (Math.isNaN(minimum) || Math.isNaN(maximum)
				|| minimum < -2147483648 || maximum > 2147483647
				|| count < 1 || count > 128)
				return [HxcUnknown];
			var finiteRange:Array<HxcFiniteValue> = [];
			for (offset in 0...Std.int(count))
				finiteRange.push(HxcNumberValue(minimum + offset));
			return finiteRange;
		}
		if (new EReg('^-?[0-9]+(?:\\.[0-9]+)?$', '').match(clean)) {
			var number = Std.parseFloat(clean);
			return Math.isNaN(number) ? [HxcUnknown] : [HxcNumberValue(number)];
		}
		if (clean == 'true') return [HxcBoolValue(true)];
		if (clean == 'false') return [HxcBoolValue(false)];
		if (clean == 'null') return [HxcNullValue];
		if (new EReg('^[A-Za-z_][A-Za-z0-9_]*$', '').match(clean)) {
			if (env != null && env.exists(clean)) return env.get(clean).copy();
			return [HxcUnknown];
		}
		return [HxcUnknown];
	}

	static function expandFiniteStringExpression(expression:String,
		stringValues:Map<String, Array<String>>):Array<String> {
		var env:Map<String, Array<HxcFiniteValue>> = new Map<String, Array<HxcFiniteValue>>();
		if (stringValues != null)
			for (name in stringValues.keys()) {
				var values:Array<HxcFiniteValue> = [];
				for (value in stringValues.get(name))
					values.push(HxcStringValue(value));
				env.set(name, values);
			}
		var result:Array<String> = [];
		for (value in evaluateFiniteExpression(expression, env, 0)) {
			var text = finiteString(value);
			if (text != null && result.indexOf(text) < 0 && result.length < 256)
				result.push(text);
		}
		return result;
	}

	static function evaluateFiniteCondition(condition:String,
		env:Map<String, Array<HxcFiniteValue>>, depth:Int):Null<Bool> {
		var comparison = findTopLevelComparison(condition);
		if (comparison == null) {
			var values = evaluateFiniteExpression(condition, env, depth + 1);
			var sawTrue = false;
			var sawFalse = false;
			for (value in values)
				switch (value) {
					case HxcBoolValue(flag): if (flag) sawTrue = true else sawFalse = true;
					case HxcNumberValue(number): if (number != 0) sawTrue = true else sawFalse = true;
					default:
				}
			return sawTrue && sawFalse ? null : sawTrue ? true : sawFalse ? false : null;
		}
		var left = evaluateFiniteExpression(condition.substr(0, comparison.position), env, depth + 1);
		var right = evaluateFiniteExpression(condition.substr(comparison.position + comparison.length), env, depth + 1);
		var sawTrue = false;
		var sawFalse = false;
		for (a in left)
			for (b in right) {
				if (a == HxcUnknown || b == HxcUnknown) continue;
				var equal = finiteEqual(a, b);
				var matches = comparison.value == '==' ? equal : !equal;
				if (matches) sawTrue = true else sawFalse = true;
			}
		return sawTrue && sawFalse ? null : sawTrue ? true : sawFalse ? false : null;
	}

	static function findTopLevelComparison(source:String):Null<{position:Int, length:Int, value:String}> {
		var quote = '';
		var escaped = false;
		var parentheses = 0;
		var brackets = 0;
		var braces = 0;
		for (index in 0...source.length - 1) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") { quote = current; continue; }
			switch (current) {
				case '(': parentheses++;
				case ')': if (parentheses > 0) parentheses--;
				case '[': brackets++;
				case ']': if (brackets > 0) brackets--;
				case '{': braces++;
				case '}': if (braces > 0) braces--;
				case '=':
					if (parentheses == 0 && brackets == 0 && braces == 0 && source.charAt(index + 1) == '=')
						return {position:index, length:2, value:'=='};
				case '!':
					if (parentheses == 0 && brackets == 0 && braces == 0 && source.charAt(index + 1) == '=')
						return {position:index, length:2, value:'!='};
				default:
			}
		}
		return null;
	}

	static function findTopLevelChar(source:String, wanted:String, start:Int):Int {
		var quote = '';
		var escaped = false;
		var parentheses = 0;
		var brackets = 0;
		var braces = 0;
		for (index in start...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") { quote = current; continue; }
			if (current == wanted && parentheses == 0 && brackets == 0 && braces == 0) return index;
			switch (current) {
				case '(': parentheses++;
				case ')': if (parentheses > 0) parentheses--;
				case '[': brackets++;
				case ']': if (brackets > 0) brackets--;
				case '{': braces++;
				case '}': if (braces > 0) braces--;
				default:
			}
		}
		return -1;
	}

	static function findMatchingConditionalColon(source:String, start:Int):Int {
		var nested = 0;
		var quote = '';
		var escaped = false;
		var parentheses = 0;
		var brackets = 0;
		var braces = 0;
		for (index in start...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") { quote = current; continue; }
			switch (current) {
				case '(': parentheses++;
				case ')': if (parentheses > 0) parentheses--;
				case '[': brackets++;
				case ']': if (brackets > 0) brackets--;
				case '{': braces++;
				case '}': if (braces > 0) braces--;
				case '?': if (parentheses == 0 && brackets == 0 && braces == 0) nested++;
				case ':':
					if (parentheses == 0 && brackets == 0 && braces == 0) {
						if (nested == 0) return index;
						nested--;
					}
				default:
			}
		}
		return -1;
	}

	static function findTrailingIndexOpen(source:String):Int {
		if (source == null || !source.endsWith(']')) return -1;
		var quote = '';
		var escaped = false;
		var depth = 0;
		var outerOpen = -1;
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") { quote = current; continue; }
			if (current == '[') {
				if (depth == 0) outerOpen = index;
				depth++;
			} else if (current == ']') {
				depth--;
				if (depth == 0 && index == source.length - 1) return outerOpen;
			}
		}
		return -1;
	}

	static function wholeStringLiteral(source:String):Null<String> {
		if (source == null || source.length < 2) return null;
		var quote = source.charAt(0);
		if (quote != '"' && quote != "'") return null;
		var escaped = false;
		for (index in 1...source.length) {
			var current = source.charAt(index);
			if (escaped) escaped = false;
			else if (current == '\\') escaped = true;
			else if (current == quote) {
				if (index != source.length - 1) return null;
				var values = quotedValues(source);
				return values.length == 0 ? '' : values[0];
			}
		}
		return null;
	}

	static function finiteString(value:HxcFiniteValue):Null<String> {
		return switch (value) {
			case HxcStringValue(text): text;
			case HxcNumberValue(number): Std.string(number);
			case HxcBoolValue(flag): flag ? 'true' : 'false';
			default: null;
		};
	}

	static function finiteEqual(left:HxcFiniteValue, right:HxcFiniteValue):Bool {
		return switch ([left, right]) {
			case [HxcNullValue, HxcNullValue]: true;
			case [HxcStringValue(a), HxcStringValue(b)]: a == b;
			case [HxcNumberValue(a), HxcNumberValue(b)]: a == b;
			case [HxcBoolValue(a), HxcBoolValue(b)]: a == b;
			case [HxcArrayValue(a), HxcArrayValue(b)]: finiteArrayEqual(a, b);
			default: false;
		};
	}

	static function finiteArrayEqual(left:Array<HxcFiniteValue>, right:Array<HxcFiniteValue>):Bool {
		if (left.length != right.length) return false;
		for (index in 0...left.length)
			if (!finiteEqual(left[index], right[index])) return false;
		return true;
	}

	static function finiteIndex(values:Array<HxcFiniteValue>, candidate:HxcFiniteValue):Int {
		for (index in 0...values.length)
			if (finiteEqual(values[index], candidate)) return index;
		return -1;
	}

	static function addFinite(values:Array<HxcFiniteValue>, value:HxcFiniteValue):Void {
		if (values != null && values.length < 256 && finiteIndex(values, value) < 0)
			values.push(value);
	}

	/** Read the first call argument until a top-level comma or closing paren. */
	static function readCallArgument(source:String, start:Int):Null<HxcArgument> {
		if (source == null || start < 0 || start >= source.length)
			return null;
		var quote = '';
		var escaped = false;
		var parentheses = 0;
		var brackets = 0;
		var braces = 0;
		var index = start;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				index++;
				continue;
			}
			switch (current) {
				case '(':
					parentheses++;
				case ')':
					if (parentheses == 0 && brackets == 0 && braces == 0)
						return {expression:source.substr(start, index - start), consumed:index - start + 1};
					if (parentheses > 0) parentheses--;
				case '[':
					brackets++;
				case ']':
					if (brackets > 0) brackets--;
				case '{':
					braces++;
				case '}':
					if (braces > 0) braces--;
				case ',':
					if (parentheses == 0 && brackets == 0 && braces == 0)
						return {expression:source.substr(start, index - start), consumed:index - start + 1};
				default:
			}
			index++;
		}
		return null;
	}

	/** Build a finite symbol table from local literal assignments and calls. */
	static function collectStringValues(source:String):Map<String, Array<String>> {
		var values:Map<String, Array<String>> = new Map<String, Array<String>>();
		if (source == null || source == '')
			return values;
		var addValues = function(name:String, incoming:Array<String>):Void {
			if (name == null || StringTools.trim(name) == '' || incoming == null)
				return;
			var key = StringTools.trim(name);
			var current = values.get(key);
			if (current == null) {
				current = [];
				values.set(key, current);
			}
			for (value in incoming)
				if (value != null && current.indexOf(value) < 0 && current.length < 128)
					current.push(value);
		};

		// Function defaults are useful even when the only call is made through a
		// timer/callback. Calls are folded into the same table below.
		var functionPattern = new EReg('function\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\(([^)]*)\\)', 'g');
		var functions = new Array<{name:String, parameters:Array<String>}>();
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 1024 && functionPattern.match(remaining)) {
			var signature = functionPattern.matched(0);
			var nameMatch = new EReg('function\\s+([A-Za-z_][A-Za-z0-9_]*)', '');
			var name = nameMatch.match(signature) ? nameMatch.matched(1) : '';
			var parameters:Array<String> = [];
			for (parameter in splitTopLevel(functionPattern.matched(1), ',')) {
				var clean = StringTools.trim(parameter);
				if (clean.startsWith('?')) clean = clean.substr(1);
				var equals = clean.indexOf('=');
				var defaultText = equals >= 0 ? clean.substr(equals + 1) : '';
				if (equals >= 0) clean = clean.substr(0, equals);
				var colon = clean.indexOf(':');
				if (colon >= 0) clean = clean.substr(0, colon);
				clean = StringTools.trim(clean);
				parameters.push(clean);
				if (clean != '' && defaultText != '')
					addValues(clean, quotedValues(defaultText));
			}
			functions.push({name:name, parameters:parameters});
			var position = functionPattern.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}

		// This permissive table supports older one-hop aliases. The contextual
		// evaluator above retains nested array grouping when a path depends on an
		// indexed row and related local string values.
		var arrayPattern = new EReg('(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::[^=;]+)?=\\s*\\[', 'g');
		remaining = source;
		attempts = 0;
		while (attempts++ < 1024 && arrayPattern.match(remaining)) {
			var arrayName = arrayPattern.matched(1);
			var position = arrayPattern.matchedPos();
			var open = position.pos + position.len - 1;
			var body = readBalanced(source, open, '[', ']');
			if (body != null)
				addValues(arrayName, quotedValues(body.text));
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}

		// Scalar assignments and aliases. A RHS containing an indexed symbol is
		// treated as the complete finite array domain; it is safe for importer
		// planning and avoids trying to evaluate donor control flow.
		var assignmentPattern = new EReg('(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::[^=;]+)?=\\s*([^;\\n]+)', 'g');
		remaining = source;
		attempts = 0;
		while (attempts++ < 4096 && assignmentPattern.match(remaining)) {
			var variable = assignmentPattern.matched(1);
			var rhs = StringTools.trim(assignmentPattern.matched(2));
			var incoming = quotedValues(rhs);
			for (symbol in values.keys())
				if (new EReg('\\b' + symbol + '\\s*\\[', '').match(rhs))
					for (value in values.get(symbol))
						if (incoming.indexOf(value) < 0) incoming.push(value);
			if (incoming.length == 0 && values.exists(rhs))
				incoming = values.get(rhs).copy();
			addValues(variable, incoming);
			var position = assignmentPattern.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}

		// Fold literal call arguments into local function parameters, then
		// propagate those finite values through simple local aliases.
		for (functionInfo in functions) {
			if (functionInfo.name == null || functionInfo.name == '')
				continue;
			var calls = new EReg('\\b' + functionInfo.name + '\\s*\\(', 'g');
			var callText = source;
			var callAttempts = 0;
			while (callAttempts++ < 512 && calls.match(callText)) {
				var position = calls.matchedPos();
				var open = position.pos + position.len - 1;
				var argumentList = readBalanced(callText, open, '(', ')');
				if (argumentList != null) {
					var args = splitTopLevel(argumentList.text, ',');
					for (index in 0...functionInfo.parameters.length)
						if (index < args.length) {
							var incoming = quotedValues(StringTools.trim(args[index]));
							var alias = StringTools.trim(args[index]);
							if (incoming.length == 0 && values.exists(alias))
								incoming = values.get(alias).copy();
							addValues(functionInfo.parameters[index], incoming);
						}
					var consumed = position.pos + position.len - 1 + argumentList.consumed;
					if (consumed >= callText.length)
						break;
					callText = callText.substr(consumed);
				} else {
					if (position.len <= 0 || position.pos + position.len >= callText.length)
						break;
					callText = callText.substr(position.pos + position.len);
				}
			}
		}
		// Alias propagation is intentionally bounded and deterministic.
		for (_ in 0...2) {
			remaining = source;
			attempts = 0;
			while (attempts++ < 4096 && assignmentPattern.match(remaining)) {
				var variable = assignmentPattern.matched(1);
				var rhs = StringTools.trim(assignmentPattern.matched(2));
				if (values.exists(rhs))
					addValues(variable, values.get(rhs));
				var position = assignmentPattern.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length)
					break;
				remaining = remaining.substr(position.pos + position.len);
			}
		}
		// Function-argument folding can add an alias after the first scalar pass.
		// Re-run indexed and plain aliases without guessing runtime strings.
		for (_ in 0...2) {
			remaining = source;
			attempts = 0;
			while (attempts++ < 4096 && assignmentPattern.match(remaining)) {
				var variable = assignmentPattern.matched(1);
				var rhs = StringTools.trim(assignmentPattern.matched(2));
				var bracket = rhs.indexOf('[');
				if (bracket > 0) {
					var base = StringTools.trim(rhs.substr(0, bracket));
					if (values.exists(base))
						addValues(variable, values.get(base));
				}
				if (values.exists(rhs))
					addValues(variable, values.get(rhs));
				var position = assignmentPattern.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length)
					break;
				remaining = remaining.substr(position.pos + position.len);
			}
		}
		// The permissive assignment expression above deliberately accepts donor
		// expressions, but a defaulted function parameter can span the first
		// statement when it is scanned as one regex match.  Keep a second narrow
		// pass for the important `alias = finiteArray[index]` shape; it is
		// statement-local and cannot swallow a function body.
		var indexedPattern = new EReg('\\b([A-Za-z_][A-Za-z0-9_]*)\\s*'
			+ '(?::[^=;\\n]+)?=\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\[', 'g');
		remaining = source;
		attempts = 0;
		while (attempts++ < 4096 && indexedPattern.match(remaining)) {
			var variable = indexedPattern.matched(1);
			var base = indexedPattern.matched(2);
			if (values.exists(base))
				addValues(variable, values.get(base));
			var position = indexedPattern.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		var aliasPattern = new EReg('\\b(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*'
			+ '(?::[^=;\\n]+)?=\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*(?:;|,)', 'g');
		for (_ in 0...2) {
			remaining = source;
			attempts = 0;
			while (attempts++ < 4096 && aliasPattern.match(remaining)) {
				var variable = aliasPattern.matched(1);
				var base = aliasPattern.matched(2);
				if (values.exists(base))
					addValues(variable, values.get(base));
				var position = aliasPattern.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length)
					break;
				remaining = remaining.substr(position.pos + position.len);
			}
		}
		return values;
	}

	static function readBalanced(source:String, open:Int, opener:String, closer:String):Null<HxcBalanced> {
		if (source == null || open < 0 || open >= source.length || source.charAt(open) != opener)
			return null;
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in open...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") {
				quote = current;
				continue;
			}
			if (current == opener) depth++;
			else if (current == closer) {
				depth--;
				if (depth == 0)
					return {text:source.substr(open + 1, index - open - 1), consumed:index - open + 1};
			}
		}
		return null;
	}

	static function quotedValues(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null)
			return result;
		var quote = '';
		var escaped = false;
		var value = new StringBuf();
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote == '') {
				if (current == '"' || current == "'") {
					quote = current;
					value = new StringBuf();
				}
				continue;
			}
			if (escaped) {
				value.add(current);
				escaped = false;
			} else if (current == '\\') {
				escaped = true;
			} else if (current == quote) {
				var text = value.toString();
				if (result.indexOf(text) < 0 && result.length < 128)
					result.push(text);
				quote = '';
			} else {
				value.add(current);
			}
		}
		return result;
	}

	static function splitTopLevel(source:String, delimiter:String):Array<String> {
		var result:Array<String> = [];
		if (source == null) return result;
		var start = 0;
		var quote = '';
		var escaped = false;
		var parentheses = 0;
		var brackets = 0;
		var braces = 0;
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped) escaped = false;
				else if (current == '\\') escaped = true;
				else if (current == quote) quote = '';
				continue;
			}
			if (current == '"' || current == "'") quote = current;
			else switch (current) {
				case '(': parentheses++;
				case ')': if (parentheses > 0) parentheses--;
				case '[': brackets++;
				case ']': if (brackets > 0) brackets--;
				case '{': braces++;
				case '}': if (braces > 0) braces--;
				default:
			}
			if (current == delimiter && quote == '' && parentheses == 0 && brackets == 0 && braces == 0) {
				result.push(StringTools.trim(source.substr(start, index - start)));
				start = index + 1;
			}
		}
		result.push(StringTools.trim(source.substr(start)));
		return result;
	}

	static function expandStringExpression(expression:String, values:Map<String, Array<String>>):Array<String> {
		var terms = splitTopLevel(expression, '+');
		var combinations:Array<String> = [''];
		for (term in terms) {
			var options:Array<String> = quotedValues(term);
			var clean = StringTools.trim(term);
			if (options.length == 0 && values != null) {
				var base = clean;
				var bracket = base.indexOf('[');
				if (bracket >= 0) base = StringTools.trim(base.substr(0, bracket));
				if (values.exists(base)) options = values.get(base).copy();
			}
			if (options.length == 0)
				return [];
			var next:Array<String> = [];
			for (left in combinations)
				for (right in options)
					if (next.length < 256 && next.indexOf(left + right) < 0)
						next.push(left + right);
			combinations = next;
		}
		return combinations;
	}

	static function collectCreateSparrowReferences(source:String,
		add:String->String->Void):Void {
		if (source == null || source == '')
			return;
		var aliases:Map<String, String> = new Map<String, String>();
		var assignment = new EReg('(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*'
			+ '(?::[^=;]+)?=\\s*["\\\']([^"\\\']+)["\\\']', 'g');
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 1024 && assignment.match(remaining)) {
			var name = assignment.matched(1);
			var value = assignment.matched(2);
			if (name != null && value != null)
				aliases.set(name, value);
			var position = assignment.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}

		var call = new EReg('(?:[A-Za-z_][A-Za-z0-9_]*\\.)*createSparrow\\s*'
			+ '\\([^,]+,\\s*[^,]+,\\s*([^,)]+)', 'g');
		remaining = source;
		attempts = 0;
		while (attempts++ < 1024 && call.match(remaining)) {
			var argument = StringTools.trim(call.matched(1));
			var literal = new EReg('^["\\\']([^"\\\']+)["\\\']$', '');
			if (literal.match(argument))
				add('sparrow', literal.matched(1));
			else if (aliases.exists(argument))
				add('sparrow', aliases.get(argument));
			var position = call.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
	}

	static function collectSongCreditReferences(source:String,
		add:String->String->Void):Void {
		if (source == null || source == '')
			return;
		var direct = new EReg('["\\\']songCredits/([A-Za-z0-9_-]{1,48})["\\\']', 'g');
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 1024 && direct.match(remaining)) {
			add('image', 'songCredits/' + direct.matched(1));
			var position = direct.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}

		// Find the identifier used after the literal `songCredits/` prefix. The
		// expression is intentionally narrow: no calls, indexing, or arbitrary
		// concatenations are admitted into the static plan.
		var use = new EReg('["\\\']songCredits/["\\\']\\s*\\+\\s*'
			+ '([A-Za-z_][A-Za-z0-9_]*)', 'g');
		remaining = source;
		attempts = 0;
		while (attempts++ < 1024 && use.match(remaining)) {
			var variable = use.matched(1);
			var assignment = new EReg('\\b' + variable
				+ '\\s*(?::\\s*String)?\\s*=\\s*([^;\\n]+)', 'g');
			var assignmentText = source;
			var assignmentAttempts = 0;
			while (assignmentAttempts++ < 1024 && assignment.match(assignmentText)) {
				var rhs = assignment.matched(1);
				var literals = new EReg('["\\\']([A-Za-z0-9_-]{1,48})["\\\']', 'g');
				var literalText = rhs;
				var literalAttempts = 0;
				while (literalAttempts++ < 64 && literals.match(literalText)) {
					add('image', 'songCredits/' + literals.matched(1));
					var literalPosition = literals.matchedPos();
					if (literalPosition.len <= 0 || literalPosition.pos + literalPosition.len >= literalText.length)
						break;
					literalText = literalText.substr(literalPosition.pos + literalPosition.len);
				}
				var assignmentPosition = assignment.matchedPos();
				if (assignmentPosition.len <= 0 || assignmentPosition.pos + assignmentPosition.len >= assignmentText.length)
					break;
				assignmentText = assignmentText.substr(assignmentPosition.pos + assignmentPosition.len);
			}
			var position = use.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
	}

	static function collectBoundLiteralReferences(source:String,
		add:String->String->Void):Void {
		if (source == null || source == '')
			return;
		var functionPattern = new EReg('function\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(([^)]*)\\)', 'g');
		var remaining = source;
		var attempts = 0;
		while (attempts++ < 1024 && functionPattern.match(remaining)) {
			var functionName = functionPattern.matched(1);
			var parameters = functionPattern.matched(2).split(',');
			for (parameterIndex in 0...parameters.length) {
				var parameter = StringTools.trim(parameters[parameterIndex]);
				var colon = parameter.indexOf(':');
				if (colon >= 0)
					parameter = StringTools.trim(parameter.substr(0, colon));
				if (parameter == '' || !new EReg('^[A-Za-z_][A-Za-z0-9_]*$', '').match(parameter))
					continue;
				var kinds = [
					{method:'image', kind:'image'},
					{method:'getSparrowAtlas', kind:'sparrow'},
					{method:'getPackerAtlas', kind:'packer'}
				];
				for (candidate in kinds) {
					var use = new EReg('Paths\\s*\\.\\s*' + candidate.method
						+ '\\s*\\(\\s*' + parameter + '\\s*\\)', 'm');
					if (!use.match(source))
						continue;
					var callPattern = new EReg('\\b' + functionName
						+ '\\s*\\(([^)]*)\\)', 'g');
					var calls = source;
					var callAttempts = 0;
					while (callAttempts++ < 256 && callPattern.match(calls)) {
						var argumentsText = callPattern.matched(1).split(',');
						if (parameterIndex < argumentsText.length) {
							var argument = StringTools.trim(argumentsText[parameterIndex]);
							var literal = new EReg('^["\\\']([^"\\\']+)["\\\']$', '');
							if (literal.match(argument))
								add(candidate.kind, literal.matched(1));
						}
						var position = callPattern.matchedPos();
						if (position.len <= 0 || position.pos + position.len >= calls.length)
							break;
						calls = calls.substr(position.pos + position.len);
					}
				}
			}
			var position = functionPattern.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
	}

	#if sys
	/**
		Build a static plan for one donor content root.  The root itself is not
		recursed: media folders can be tens of gigabytes, while these bounded
		families contain the executable HXC surface.
	*/
	public static function plan(root:String, ?selectedStages:Array<String>):HxcAssetPlan {
		var scripts = scriptFiles(root, selectedStages);
		var references:Array<HxcAssetReference> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (script in scripts) {
			var source:String;
			try source = sys.io.File.getContent(script) catch (_:Dynamic) continue;
			for (reference in literalReferences(source)) {
				var identity = reference.kind + ':' + reference.key.toLowerCase();
				if (seen.exists(identity))
					continue;
				seen.set(identity, true);
				references.push(reference);
			}
		}
		return {scripts:scripts, references:references};
	}

	/** Find HXC files without entering arbitrary donor media directories. */
	public static function scriptFiles(root:String, ?selectedStages:Array<String>):Array<String> {
		var result:Array<String> = [];
		if (root == null || !FileSystem.isDirectory(root))
			return result;
		var selectedStageNames:Map<String, Bool> = null;
		if (selectedStages != null) {
			selectedStageNames = new Map<String, Bool>();
			for (stage in selectedStages)
				if (stage != null && StringTools.trim(stage) != '')
					selectedStageNames.set(HxcScriptDiscovery.normalizeToken(stage), true);
		}
		var familyNames = [
			'scripts', 'data', 'stages', 'modules', 'states', 'substates', 'ui',
			'events', 'notes', 'characters', 'songs'
		];
		for (family in familyNames) {
			var folder = Path.join([root, family]);
			if (!FileSystem.isDirectory(folder))
				continue;
			// Only filter the direct stage-script families. HXC modules, song
			// scripts, note scripts, and other families remain part of the plan.
			var stageRoot:String = null;
			var inStageFamily = false;
			switch (family) {
				case 'stages':
					stageRoot = folder;
					inStageFamily = true;
				case 'scripts' | 'data':
					stageRoot = Path.join([folder, 'stages']);
				default:
			}
			collectScripts(folder, result, stageRoot, selectedStageNames, inStageFamily);
		}
		result.sort(function(left:String, right:String):Int {
			return left < right ? -1 : (left > right ? 1 : 0);
		});
		return result;
	}

	static function collectScripts(folder:String, result:Array<String>, stageRoot:String,
		selectedStages:Map<String, Bool>, inStageFamily:Bool):Void {
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(folder) catch (_:Dynamic) return;
		for (entry in entries) {
			if (entry == null || entry == '.' || entry == '..')
				continue;
			var path = Path.join([folder, entry]);
			if (FileSystem.isDirectory(path)) {
				var childInStageFamily = inStageFamily;
				if (!childInStageFamily && stageRoot != null
					&& Path.normalize(path) == Path.normalize(stageRoot))
					childInStageFamily = true;
				collectScripts(path, result, stageRoot, selectedStages, childInStageFamily);
				continue;
			}
			if (!entry.toLowerCase().endsWith('.hxc'))
				continue;
			// Declared stage IDs can differ from filenames. Character companions
			// stored beside stages keep their ordinary non-stage dependency scope.
			if (inStageFamily && selectedStages != null
				&& HxcScriptDiscovery.familyForPath(path) == 'stage'
				&& !selectedStages.exists(HxcScriptDiscovery.stageId(path))
				&& !selectedStages.exists(HxcScriptDiscovery.normalizeToken(HxcScriptDiscovery.stem(path))))
				continue;
			result.push(path);
		}
	}
	#else
	public static function plan(_root:String, ?_selectedStages:Array<String>):HxcAssetPlan {
		return {scripts:[], references:[]};
	}
	#end
}
