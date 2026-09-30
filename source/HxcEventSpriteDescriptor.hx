package;

import haxe.Json;

using StringTools;

/**
	A data-only description of the small HXC SongEvent sprite pattern which can
	be represented by PlayState.  This parser accepts literal atlas/animation
	metadata and event-value coordinates only; it never evaluates donor Haxe.
*/
class HxcEventSpriteDescriptor {
	public static inline var CATALOG_FILE:String = 'event-sprites.json';
	public static inline var CATALOG_VERSION:Int = 1;

	/** Return one descriptor only when the entire supported event shape is static. */
	public static function extract(source:String):Dynamic {
		if (source == null || StringTools.trim(source) == '')
			return null;
		var clean = stripComments(source);
		var classExpression = new EReg('\\bclass\\s+([A-Za-z_][A-Za-z0-9_]*)\\s+extends\\s+(?:[A-Za-z_][A-Za-z0-9_]*\\.)*ScriptedSongEvent\\b[^\\{]*\\{', 'm');
		if (!classExpression.match(clean))
			return null;
		var classPosition = classExpression.matchedPos();
		var classOpen = clean.indexOf('{', classPosition.pos);
		var classClose = matchingDelimiter(clean, classOpen, '{', '}');
		if (classOpen < 0 || classClose < 0)
			return null;
		var className = classExpression.matched(1);
		var classBody = clean.substr(classOpen + 1, classClose - classOpen - 1);
		var sourceName = firstCallString(classBody, '\\bsuper\\s*\\(');
		if (!validEventText(sourceName))
			return null;

		var method = functionBody(classBody, 'handleEvent');
		if (method == null || method.arguments.length == 0)
			return null;
		var eventArgument = firstIdentifier(method.arguments[0]);
		if (eventArgument == '')
			return null;
		var body:String = method.body;

		var payloadFields:Map<String, String> = new Map<String, String>();
		var assignment = new EReg('\\b(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*'
			+ eventArgument + '\\s*\\.\\s*value\\s*\\.\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*;', 'g');
		var offset = 0;
		while (offset < body.length && assignment.match(body.substr(offset))) {
			var found = assignment.matchedPos();
			payloadFields.set(assignment.matched(1), assignment.matched(2));
			offset += found.pos + found.len;
		}

		var spriteExpression = new EReg('\\b(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)'
			+ '(?:\\s*:\\s*(?:[A-Za-z_][A-Za-z0-9_]*\\.)*FlxSprite)?\\s*=\\s*new\\s+'
			+ '(?:[A-Za-z_][A-Za-z0-9_]*\\.)*FlxSprite\\s*\\(\\s*'
			+ '([A-Za-z_][A-Za-z0-9_]*)\\s*,\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)', 'm');
		if (!spriteExpression.match(body) || countMatches(body,
			'\\bnew\\s+(?:[A-Za-z_][A-Za-z0-9_]*\\.)*FlxSprite\\s*\\(') != 1)
			return null;
		var sprite = spriteExpression.matched(1);
		var xField = payloadFields.get(spriteExpression.matched(2));
		var yField = payloadFields.get(spriteExpression.matched(3));
		if (!validIdentifierText(xField) || !validIdentifierText(yField) || xField == yField)
			return null;

		var framesCall = callArguments(body, '\\b' + sprite + '\\s*\\.\\s*frames\\s*=\\s*Paths\\s*\\.\\s*(getSparrowAtlas|getPackerAtlas)\\s*\\(');
		if (framesCall == null || framesCall.arguments.length != 1)
			return null;
		var atlasType = framesCall.method == 'getPackerAtlas' ? 'packer' : 'sparrow';
		var atlasKey = safeAtlasKey(parseStringLiteral(framesCall.arguments[0]));
		if (atlasKey == '')
			return null;

		var animationCall = callArguments(body,
			'\\b' + sprite + '\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(');
		if (animationCall == null || animationCall.arguments.length != 4
			|| countMatches(body, '\\b' + sprite + '\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(') != 1)
			return null;
		var animationName = parseStringLiteral(animationCall.arguments[0]);
		var framePrefix = parseStringLiteral(animationCall.arguments[1]);
		var frameRate = parseNumber(animationCall.arguments[2]);
		var loop = parseBool(animationCall.arguments[3]);
		if (!validText(animationName) || !validText(framePrefix) || Math.isNaN(frameRate)
			|| frameRate <= 0 || frameRate > 240 || loop != false)
			return null;

		var playCall = callArguments(body,
			'\\b' + sprite + '\\s*\\.\\s*animation\\s*\\.\\s*play\\s*\\(');
		if (playCall == null || playCall.arguments.length != 1
			|| parseStringLiteral(playCall.arguments[0]) != animationName
			|| countMatches(body, '\\b' + sprite + '\\s*\\.\\s*animation\\s*\\.\\s*play\\s*\\(') != 1)
			return null;

		var camera = cameraTarget(body, sprite);
		if (camera == '')
			return null;
		var scroll = scrollTarget(body, sprite);
		if (scroll == null)
			return null;
		var finishBody = callbackBody(body,
			'\\b' + sprite + '\\s*\\.\\s*animation\\s*\\.\\s*finishCallback\\s*=\\s*function\\s*\\([^)]*\\)\\s*\\{');
		if (finishBody == null
			|| !new EReg('(?:\\.\\s*)?remove\\s*\\(\\s*' + sprite + '\\s*\\)', 'm').match(finishBody)
			|| !new EReg('\\b' + sprite + '\\s*\\.\\s*kill\\s*\\(\\s*\\)', 'm').match(finishBody))
			return null;

		return {
			version: CATALOG_VERSION,
			className: className,
			sourceName: sourceName,
			canonicalName: sourceName,
			atlasKey: atlasKey,
			atlasType: atlasType,
			animationName: animationName,
			framePrefix: framePrefix,
			frameRate: frameRate,
			loop: loop,
			xField: xField,
			yField: yField,
			camera: camera,
			scrollX: scroll.x,
			scrollY: scroll.y,
			cleanupOnFinish: true
		};
	}

	/** Validate one serialized descriptor without accepting new executable data. */
	public static function normalize(value:Dynamic):Dynamic {
		if (value == null)
			return null;
		var sourceName = stringField(value, 'sourceName');
		var canonicalName = stringField(value, 'canonicalName');
		var className = stringField(value, 'className');
		var atlasKey = safeAtlasKey(stringField(value, 'atlasKey'));
		var atlasType = stringField(value, 'atlasType');
		var animationName = stringField(value, 'animationName');
		var framePrefix = stringField(value, 'framePrefix');
		var xField = stringField(value, 'xField');
		var yField = stringField(value, 'yField');
		var camera = stringField(value, 'camera');
		var frameRate = numberField(value, 'frameRate');
		var scrollX = numberField(value, 'scrollX');
		var scrollY = numberField(value, 'scrollY');
		var loop:Dynamic = Reflect.field(value, 'loop');
		var cleanup:Dynamic = Reflect.field(value, 'cleanupOnFinish');
		if (!validEventText(sourceName) || !validEventText(canonicalName)
			|| !validIdentifierText(className) || atlasKey == ''
			|| (atlasType != 'sparrow' && atlasType != 'packer')
			|| !validText(animationName) || !validText(framePrefix)
			|| Math.isNaN(frameRate) || frameRate <= 0 || frameRate > 240
			|| !validIdentifierText(xField) || !validIdentifierText(yField) || xField == yField
			|| (camera != 'hud' && camera != 'game')
			|| Math.isNaN(scrollX) || Math.isNaN(scrollY)
			|| scrollX < -100 || scrollX > 100 || scrollY < -100 || scrollY > 100
			|| loop != false || cleanup != true)
			return null;
		return {
			version: CATALOG_VERSION,
			className: className,
			sourceName: sourceName,
			canonicalName: canonicalName,
			atlasKey: atlasKey,
			atlasType: atlasType,
			animationName: animationName,
			framePrefix: framePrefix,
			frameRate: frameRate,
			loop: loop,
			xField: xField,
			yField: yField,
			camera: camera,
			scrollX: scrollX,
			scrollY: scrollY,
			cleanupOnFinish: true
		};
	}

	public static function parseCatalog(raw:String):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (raw == null || StringTools.trim(raw) == '')
			return result;
		try {
			var parsed:Dynamic = Json.parse(raw);
			if (parsed == null || Reflect.field(parsed, 'version') != CATALOG_VERSION)
				return result;
			var descriptors:Dynamic = Reflect.field(parsed, 'descriptors');
			if (!Std.isOfType(descriptors, Array))
				return result;
			for (item in (cast descriptors:Array<Dynamic>)) {
				var normalized = normalize(item);
				if (normalized != null)
					result.push(normalized);
			}
		} catch (_:Dynamic) {}
		return result;
	}

	public static function serializeCatalog(descriptors:Array<Dynamic>):String {
		var clean:Array<Dynamic> = [];
		var seen:Map<String, Dynamic> = new Map<String, Dynamic>();
		if (descriptors != null)
			for (item in descriptors) {
				var normalized = normalize(item);
				if (normalized == null)
					continue;
				var key = stringField(normalized, 'canonicalName').toLowerCase();
				if (seen.exists(key)) {
					if (Json.stringify(seen.get(key)) != Json.stringify(normalized))
						seen.set(key, null);
					continue;
				}
				seen.set(key, normalized);
			}
		for (key in seen.keys()) {
			var item = seen.get(key);
			if (item != null)
				clean.push(item);
		}
		clean.sort(function(a:Dynamic, b:Dynamic):Int {
			var left = stringField(a, 'canonicalName').toLowerCase();
			var right = stringField(b, 'canonicalName').toLowerCase();
			return left < right ? -1 : (left > right ? 1 : 0);
		});
		return Json.stringify({version: CATALOG_VERSION, descriptors: clean});
	}

	public static function find(descriptors:Array<Dynamic>, eventName:String):Dynamic {
		if (descriptors == null || eventName == null || StringTools.trim(eventName) == '')
			return null;
		var match:Dynamic = null;
		var key = StringTools.trim(eventName).toLowerCase();
		for (item in descriptors) {
			var clean = normalize(item);
			if (clean == null || stringField(clean, 'canonicalName').toLowerCase() != key)
				continue;
			if (match != null && Json.stringify(match) != Json.stringify(clean))
				return null;
			match = clean;
		}
		return match;
	}

	public static function safeAtlasKey(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.startsWith('/') || clean.indexOf(':') >= 0 || clean.indexOf('..') >= 0)
			return '';
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean.toLowerCase().startsWith('images/'))
			clean = clean.substr('images/'.length);
		for (extension in ['.png', '.xml', '.txt'])
			if (clean.toLowerCase().endsWith(extension)) {
				clean = clean.substr(0, clean.length - extension.length);
				break;
			}
		if (clean == '' || clean.startsWith('/') || clean.endsWith('/'))
			return '';
		for (part in clean.split('/'))
			if (part == '' || part == '.' || !new EReg('^[A-Za-z0-9_. -]+$', 'm').match(part))
				return '';
		return clean;
	}

	static function functionBody(source:String, name:String):Dynamic {
		var expression = new EReg('\\bfunction\\s+' + name + '\\s*\\(([^)]*)\\)[^\\{]*\\{', 'm');
		if (!expression.match(source))
			return null;
		var position = expression.matchedPos();
		var open = source.indexOf('{', position.pos);
		var close = matchingDelimiter(source, open, '{', '}');
		if (open < 0 || close < 0)
			return null;
		return {arguments: splitTopLevel(expression.matched(1), ','), body: source.substr(open + 1, close - open - 1)};
	}

	static function callbackBody(source:String, pattern:String):Null<String> {
		var expression = new EReg(pattern, 'm');
		if (!expression.match(source))
			return null;
		var position = expression.matchedPos();
		var open = source.indexOf('{', position.pos);
		var close = matchingDelimiter(source, open, '{', '}');
		return open < 0 || close < 0 ? null : source.substr(open + 1, close - open - 1);
	}

	static function callArguments(source:String, pattern:String):Dynamic {
		var expression = new EReg(pattern, 'm');
		if (!expression.match(source))
			return null;
		var position = expression.matchedPos();
		var open = source.indexOf('(', position.pos);
		var close = matchingDelimiter(source, open, '(', ')');
		if (open < 0 || close < 0)
			return null;
		var prefix = source.substr(position.pos, open - position.pos);
		var type = prefix.indexOf('getPackerAtlas') >= 0 ? 'getPackerAtlas'
			: (prefix.indexOf('getSparrowAtlas') >= 0 ? 'getSparrowAtlas' : '');
		return {method: type, arguments: splitTopLevel(source.substr(open + 1, close - open - 1), ',')};
	}

	static function firstCallString(source:String, pattern:String):String {
		var call = callArguments(source, pattern);
		return call == null || call.arguments.length == 0 ? '' : parseStringLiteral(call.arguments[0]);
	}

	static function cameraTarget(source:String, sprite:String):String {
		var expression = new EReg('\\b' + sprite + '\\s*\\.\\s*cameras\\s*=\\s*\\[\\s*(.*?)\\s*\\]', 'm');
		if (!expression.match(source))
			return '';
		var camera = StringTools.trim(expression.matched(1));
		if (new EReg('^(?:PlayState\\s*\\.\\s*instance\\s*\\.\\s*)?camHUD$', 'm').match(camera))
			return 'hud';
		if (new EReg('^(?:PlayState\\s*\\.\\s*instance\\s*\\.\\s*)?camGame$', 'm').match(camera))
			return 'game';
		return '';
	}

	static function scrollTarget(source:String, sprite:String):Null<Dynamic> {
		var call = callArguments(source, '\\b' + sprite + '\\s*\\.\\s*scrollFactor\\s*\\.\\s*set\\s*\\(');
		if (call == null)
			return null;
		if (call.arguments.length == 0)
			return {x: 0.0, y: 0.0};
		if (call.arguments.length != 2)
			return null;
		var x = parseNumber(call.arguments[0]);
		var y = parseNumber(call.arguments[1]);
		return Math.isNaN(x) || Math.isNaN(y) ? null : {x: x, y: y};
	}

	static function parseStringLiteral(value:String):String {
		if (value == null)
			return '';
		var clean = StringTools.trim(value);
		if (clean.length < 2)
			return '';
		var first = clean.charAt(0);
		if ((first != '\'' && first != '"') || clean.charAt(clean.length - 1) != first)
			return '';
		var content = clean.substr(1, clean.length - 2);
		if (content.indexOf('\\') >= 0 || content.indexOf(first) >= 0)
			return '';
		return content;
	}

	static function parseNumber(value:String):Float {
		if (value == null || !new EReg('^[-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)$', 'm').match(StringTools.trim(value)))
			return Math.NaN;
		var result = Std.parseFloat(StringTools.trim(value));
		return Math.isNaN(result) ? Math.NaN : result;
	}

	static function parseBool(value:String):Null<Bool> {
		return switch (StringTools.trim(value == null ? '' : value)) {
			case 'true': true;
			case 'false': false;
			default: null;
		}
	}

	static function firstIdentifier(value:String):String {
		if (value == null)
			return '';
		var expression = new EReg('^\\s*([A-Za-z_][A-Za-z0-9_]*)', 'm');
		return expression.match(value) ? expression.matched(1) : '';
	}

	static function validIdentifierText(value:String):Bool {
		return value != null && new EReg('^[A-Za-z_][A-Za-z0-9_]*$', 'm').match(StringTools.trim(value));
	}

	static function validEventText(value:String):Bool {
		return value != null && value.length > 0 && value.length <= 128
			&& new EReg('^[A-Za-z0-9 _.-]+$', 'm').match(StringTools.trim(value));
	}

	static function validText(value:String):Bool {
		return value != null && value.length > 0 && value.length <= 256;
	}

	static function stringField(value:Dynamic, name:String):String {
		var field:Dynamic = value == null ? null : Reflect.field(value, name);
		return field == null ? '' : StringTools.trim(Std.string(field));
	}

	static function numberField(value:Dynamic, name:String):Float {
		var field:Dynamic = value == null ? null : Reflect.field(value, name);
		if (field == null)
			return Math.NaN;
		var result = Std.parseFloat(Std.string(field));
		return Math.isNaN(result) ? Math.NaN : result;
	}

	static function countMatches(source:String, pattern:String):Int {
		var expression = new EReg(pattern, 'g');
		var count = 0;
		var offset = 0;
		while (offset < source.length && expression.match(source.substr(offset))) {
			var position = expression.matchedPos();
			count++;
			offset += position.pos + (position.len == 0 ? 1 : position.len);
		}
		return count;
	}

	static function splitTopLevel(source:String, separator:String):Array<String> {
		var result:Array<String> = [];
		if (source == null || source == '')
			return result;
		var start = 0;
		var round = 0;
		var square = 0;
		var curly = 0;
		var quote = '';
		var escaped = false;
		for (index in 0...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '\'' || current == '"') {
				quote = current;
				continue;
			}
			switch (current) {
				case '(': round++;
				case ')': round--;
				case '[': square++;
				case ']': square--;
				case '{': curly++;
				case '}': curly--;
				default:
			}
			if (current == separator && round == 0 && square == 0 && curly == 0) {
				result.push(StringTools.trim(source.substr(start, index - start)));
				start = index + 1;
			}
		}
		result.push(StringTools.trim(source.substr(start)));
		return result;
	}

	static function matchingDelimiter(source:String, open:Int, opening:String, closing:String):Int {
		if (source == null || open < 0 || open >= source.length || source.charAt(open) != opening)
			return -1;
		var depth = 0;
		var quote = '';
		var escaped = false;
		for (index in open...source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				continue;
			}
			if (current == '\'' || current == '"') {
				quote = current;
				continue;
			}
			if (current == opening)
				depth++;
			else if (current == closing && --depth == 0)
				return index;
		}
		return -1;
	}

	static function stripComments(source:String):String {
		var output = new StringBuf();
		var quote = '';
		var escaped = false;
		var index = 0;
		while (index < source.length) {
			var current = source.charAt(index);
			var next = index + 1 < source.length ? source.charAt(index + 1) : '';
			if (quote != '') {
				output.add(current);
				if (escaped)
					escaped = false;
				else if (current == '\\')
					escaped = true;
				else if (current == quote)
					quote = '';
				index++;
				continue;
			}
			if (current == '\'' || current == '"') {
				quote = current;
				output.add(current);
				index++;
				continue;
			}
			if (current == '/' && next == '/') {
				index += 2;
				while (index < source.length && source.charAt(index) != '\n' && source.charAt(index) != '\r')
					index++;
				continue;
			}
			if (current == '/' && next == '*') {
				index += 2;
				while (index + 1 < source.length && !(source.charAt(index) == '*' && source.charAt(index + 1) == '/'))
					index++;
				index = index + 1 < source.length ? index + 2 : source.length;
				continue;
			}
			output.add(current);
			index++;
		}
		return output.toString();
	}
}
