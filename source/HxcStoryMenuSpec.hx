package;

/**
	Data-only description of the HXC story-menu module surface supported by the
	native story-menu owner.  Imported code never constructs or owns these
	display objects directly; the selected manifest root remains attached to each
	plan while the native host materializes its visuals and transition.
*/
typedef HxcStoryMenuSpriteSpec = {
	var atlas:String;
	var animation:String;
	var prefix:String;
	var fps:Float;
	var x:Float;
	var y:Float;
	var scaleX:Float;
	var scaleY:Float;
	var zIndex:Int;
	var idleAlpha:Float;
	var selectedAlpha:Float;
	@:optional var startFrame:Int;
	@:optional var loop:Bool;
	@:optional var camera:String;
	@:optional var frameSoundIndex:Int;
	@:optional var frameSoundAlpha:Float;
	@:optional var frameSound:String;
}

/** Complete bounded plan for a level-select visual and its campaign handoff. */
typedef HxcStoryMenuSpecData = {
	/** Literal level id read from the module's selected-level guard. */
	var levelId:String;
	/** Literal song index read from the module's current-level song lookup. */
	var songIndex:Int;
	var transitionDelay:Float;
	var stopCameraEffects:Bool;
	var menuSprite:HxcStoryMenuSpriteSpec;
	var selectionSound:String;
	var frameSound:String;
	/** Optional character/cutscene helper carried by the same module. */
	var characterHelper:Null<HxcStoryMenuSpriteSpec>;
	@:optional var characterHelperName:String;
	@:optional var characterHelperField:String;
}

/** Structural extraction for a bounded level-confirm plus character helper. */
class HxcStoryMenuSpec {
	static var numberPattern = '([-+]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+))';

	/**
		Recognize the complete StoryMenu module contract from its behavior.
		The class/file/module names and the authored level id are data; no donor
		name is used to decide whether this adapter applies.
	*/
	public static function extract(source:String):Null<HxcStoryMenuSpecData> {
		if (source == null || source == '')
			return null;
		var constructor = methodBody(source, 'new');
		var update = methodBody(source, 'onUpdate');
		var stateChange = methodBody(source, 'onStateChangeEnd');
		if (constructor == null || update == null || stateChange == null)
			return null;

		var helperName:String = null;
		var helperBody:String = null;
		var methods = methodNames(source);
		for (name in methods) {
			if (name == 'new' || name == 'onUpdate' || name == 'onStateChangeEnd')
				continue;
			var body = methodBody(source, name);
			if (body != null && body.indexOf('PlayState.instance') >= 0
				&& body.indexOf('camCutscene') >= 0 && body.indexOf('animation.play') >= 0) {
				if (helperName != null)
					return null;
				helperName = name;
				helperBody = body;
			} else
				return null;
		}
		if (helperName == null || helperBody == null)
			return null;

		if (!contains(update, 'ReflectUtil\\s*\\.\\s*getClassNameOf\\s*\\(\\s*FlxG\\s*\\.\\s*state\\s*\\)')
			|| !contains(update, 'selectedLevel') || !contains(update, 'currentLevelId')
			|| !contains(update, 'currentLevel\\s*\\.\\s*getSongs\\s*\\(')
			|| !contains(update, 'SongRegistry\\s*\\.\\s*instance\\s*\\.\\s*fetchEntry')
			|| !contains(update, 'getFirstValidVariation') || !contains(update, 'campaignDifficulty')
			|| !contains(update, 'LoadingState\\s*\\.\\s*loadPlayState')
			|| !contains(update, 'camera\\s*\\.\\s*stopFX\\s*\\(')
			|| !contains(stateChange, 'Paths\\s*\\.\\s*getSparrowAtlas')
			|| !new EReg('\\b[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*false', 'm').match(stateChange))
			return null;

		var levelId = firstString(update,
			'currentLevelId\\s*==\\s*["\\\']([^"\\\']+)["\\\']');
		var songIndex = firstInt(update,
			'currentLevel\\s*\\.\\s*getSongs\\s*\\(\\s*\\)\\s*\\[\\s*(\\d+)\\s*\\]');
		var delay = firstFloat(update,
			'new\\s+FlxTimer\\s*\\(\\s*\\)\\s*\\.\\s*start\\s*\\(\\s*' + numberPattern);
		var atlas = firstString(source,
			'Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		var selectedBodyStart = update.indexOf('currentLevelId');
		var selectedBody = selectedBodyStart < 0 ? update : update.substr(selectedBodyStart);
		var selectionSound = firstString(selectedBody,
			'FlxG\\s*\\.\\s*sound\\s*\\.\\s*play\\s*\\(\\s*Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		var frameSound = firstString(update,
			'frameIndex\\s*==\\s*(\\d+)\\s*&&[^)]*Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']');
		var frameSoundIndex:Null<Int> = null;
		var frameSoundAlpha:Null<Float> = null;
		if (frameSound == '') {
			// The donor callback names the frame argument `i`; accept any simple
			// frame index spelling while retaining the authored alpha guard.
			var frameExpression = new EReg('\\b[A-Za-z_][A-Za-z0-9_]*\\s*==\\s*(\\d+)\\s*&&\\s*[A-Za-z_][A-Za-z0-9_]*\\s*\\.\\s*alpha\\s*==\\s*' + numberPattern + '[^;]*Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'm');
			if (frameExpression.match(update)) {
				frameSound = frameExpression.matched(3);
				frameSoundIndex = Std.parseInt(frameExpression.matched(1));
				frameSoundAlpha = Std.parseFloat(frameExpression.matched(2));
			} else
				return null;
		} else {
			var frameExpression = new EReg('frameIndex\\s*==\\s*(\\d+)[^;]*\\.\\s*alpha\\s*==\\s*' + numberPattern, 'm');
			if (!frameExpression.match(update))
				return null;
			frameSoundIndex = Std.parseInt(frameExpression.matched(1));
			frameSoundAlpha = Std.parseFloat(frameExpression.matched(2));
		}
		if (levelId == '' || songIndex == null || delay == null || atlas == ''
			|| selectionSound == '' || frameSound == '' || songIndex < 0 || delay < 0)
			return null;

		var menuSprite = spriteSpec(update, atlas, 'menu');
		var characterHelper = spriteSpec(helperBody, atlas, 'character');
		if (menuSprite == null || characterHelper == null)
			return null;
		var characterHelperField = firstCapture(helperBody,
			'\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*new\\s+FunkinSprite\\s*\\(');
		if (characterHelperField == '')
			return null;
		menuSprite.frameSoundIndex = frameSoundIndex;
		menuSprite.frameSoundAlpha = frameSoundAlpha;
		menuSprite.frameSound = frameSound;
		characterHelper.camera = 'camCutscene';

		var cachedSounds:Array<String> = [];
		var cacheExpression = new EReg('permanentCacheSound\\s*\\(\\s*Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'g');
		var remaining = constructor;
		while (cacheExpression.match(remaining)) {
			cachedSounds.push(cacheExpression.matched(1));
			var match = cacheExpression.matchedPos();
			if (match.len <= 0 || match.pos + match.len >= remaining.length)
				break;
			remaining = remaining.substr(match.pos + match.len);
		}
		if (cachedSounds.indexOf(selectionSound) < 0 || cachedSounds.indexOf(frameSound) < 0)
			return null;
		if (!contains(selectedBody, 'selectionSound') && !contains(selectedBody,
			'FlxG\\s*\\.\\s*sound\\s*\\.\\s*play\\s*\\(\\s*Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']' + escapeRegex(selectionSound)))
			return null;

		return {
			levelId: levelId,
			songIndex: songIndex,
			transitionDelay: delay,
			stopCameraEffects: true,
			menuSprite: menuSprite,
			selectionSound: selectionSound,
			frameSound: frameSound,
			characterHelper: characterHelper,
			characterHelperName: helperName,
			characterHelperField: characterHelperField
		};
	}

	/** Generate the only HScript callable retained from this module: its helper. */
	public static function helperHscript(spec:HxcStoryMenuSpecData):String {
		if (spec == null || spec.characterHelper == null || spec.characterHelperName == null)
			return '';
		if (spec.characterHelperField == null || spec.characterHelperField == '')
			return '';
		return 'function ' + spec.characterHelperName + '() {\n'
			+ '\t' + spec.characterHelperField
			+ ' = HxcCompatRuntime.createStoryCharacterHelper(PlayState.instance, hxcAssetRoot, '
			+ spriteLiteral(spec.characterHelper) + ');\n}';
	}

	public static function spriteLiteral(spec:HxcStoryMenuSpriteSpec):String {
		if (spec == null)
			return 'null';
		var value = '{atlas:' + quote(spec.atlas) + ', animation:' + quote(spec.animation)
			+ ', prefix:' + quote(spec.prefix) + ', fps:' + spec.fps
			+ ', x:' + spec.x + ', y:' + spec.y + ', scaleX:' + spec.scaleX
			+ ', scaleY:' + spec.scaleY + ', zIndex:' + spec.zIndex
			+ ', idleAlpha:' + spec.idleAlpha + ', selectedAlpha:' + spec.selectedAlpha;
			if (spec.startFrame != null) value += ', startFrame:' + spec.startFrame;
			if (spec.loop != null) value += ', loop:' + spec.loop;
			if (spec.camera != null) value += ', camera:' + quote(spec.camera);
		return value + '}';
	}

	static function spriteSpec(source:String, atlas:String, use:String):Null<HxcStoryMenuSpriteSpec> {
		var spriteName = firstCapture(source, '\\b([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*new\\s+FunkinSprite\\s*\\(');
		var position = numberPair(source, '\\bnew\\s+FunkinSprite\\s*\\(\\s*');
		var animationName = firstCapture(source, '\\b' + spriteName + '\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(\\s*["\\\']([^"\\\']+)');
		var prefix = firstCapture(source, '\\b' + spriteName + '\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(\\s*["\\\'][^"\\\']+["\\\']\\s*,\\s*["\\\']([^"\\\']+)');
		var animationArgs = new EReg('\\b' + spriteName + '\\s*\\.\\s*animation\\s*\\.\\s*addByPrefix\\s*\\(\\s*["\\\'][^"\\\']+["\\\']\\s*,\\s*["\\\'][^"\\\']+["\\\']\\s*,\\s*' + numberPattern + '\\s*,\\s*(true|false)', 'm');
		var scale = numberPair(source, '\\b' + spriteName + '\\s*\\.\\s*scale\\s*\\.\\s*set\\s*\\(\\s*');
		var zIndex = firstInt(source, '\\b' + spriteName + '\\s*\\.\\s*zIndex\\s*=\\s*(\\d+)');
		if (spriteName == '' || position == null || animationName == '' || prefix == ''
			|| !animationArgs.match(source) || scale == null || zIndex == null)
			return null;
		var idleAlpha:Float = 1;
		var selectedAlpha:Float = 1;
		var startFrame:Null<Int> = 0;
		var scrollFactorZero = new EReg('\\b' + spriteName + '\\s*\\.\\s*scrollFactor\\s*\\.\\s*set\\s*\\(\\s*\\)', 'm').match(source);
		if (use == 'menu') {
			var alphaExpression = new EReg('\\b' + spriteName + '\\s*\\.\\s*alpha\\s*=\\s*' + numberPattern, 'g');
			var remaining = source;
			var values:Array<Float> = [];
			while (alphaExpression.match(remaining)) {
				values.push(Std.parseFloat(alphaExpression.matched(1)));
				var match = alphaExpression.matchedPos();
				if (match.len <= 0 || match.pos + match.len >= remaining.length)
					break;
				remaining = remaining.substr(match.pos + match.len);
			}
			if (values.length < 2 || !scrollFactorZero)
				return null;
			idleAlpha = values[0];
			selectedAlpha = values[1];
		} else {
			startFrame = firstInt(source,
				'\\b' + spriteName + '\\s*\\.\\s*animation\\s*\\.\\s*play\\s*\\(\\s*["\\\'][^"\\\']+["\\\']\\s*,\\s*false\\s*,\\s*false\\s*,\\s*(\\d+)');
			if (startFrame == null || !contains(source, '\\b' + spriteName + '\\s*\\.\\s*camera\\s*=\\s*state\\s*\\.\\s*camCutscene'))
				return null;
		}
		var spec:HxcStoryMenuSpriteSpec = {
			atlas: atlas,
			animation: animationName,
			prefix: prefix,
			fps: Std.parseFloat(animationArgs.matched(1)),
			x: position[0],
			y: position[1],
			scaleX: scale[0],
			scaleY: scale[1],
			zIndex: zIndex,
			idleAlpha: idleAlpha,
			selectedAlpha: selectedAlpha,
			startFrame: startFrame,
			loop: animationArgs.matched(2) == 'true'
		};
		return spec;
	}

	static function methodNames(source:String):Array<String> {
		var result:Array<String> = [];
		var expression = new EReg('\\bfunction\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\(', 'g');
		var remaining = source;
		while (expression.match(remaining)) {
			var name = expression.matched(1);
			if (result.indexOf(name) < 0)
				result.push(name);
			var match = expression.matchedPos();
			if (match.len <= 0 || match.pos + match.len >= remaining.length)
				break;
			remaining = remaining.substr(match.pos + match.len);
		}
		return result;
	}

	static function methodBody(source:String, name:String):Null<String> {
		var header = new EReg('\\bfunction\\s+' + name + '\\s*\\([^)]*\\)\\s*(?::[^\\{]+)?\\{', 'm');
		if (!header.match(source))
			return null;
		var position = header.matchedPos();
		var open = position.pos + position.len - 1;
		var depth = 0;
		var quote = '';
		var escaped = false;
		var index = open;
		while (index < source.length) {
			var current = source.charAt(index);
			if (quote != '') {
				if (escaped)
					escaped = false;
				else if (current == '\\\\')
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
			if (current == '{')
				depth++;
			else if (current == '}') {
				depth--;
				if (depth == 0)
					return source.substr(open + 1, index - open - 1);
			}
			index++;
		}
		return null;
	}

	static function contains(source:String, pattern:String):Bool
		return source != null && new EReg(pattern, 'm').match(source);

	static function firstString(source:String, pattern:String):String
		return firstCapture(source, pattern);

	static function firstCapture(source:String, pattern:String):String {
		var expression = new EReg(pattern, 'm');
		if (source == null || !expression.match(source))
			return '';
		return expression.matched(1);
	}

	static function firstInt(source:String, pattern:String):Null<Int> {
		var expression = new EReg(pattern, 'm');
		if (source == null || !expression.match(source))
			return null;
		return Std.parseInt(expression.matched(1));
	}

	static function firstFloat(source:String, pattern:String):Null<Float> {
		var expression = new EReg(pattern, 'm');
		if (source == null || !expression.match(source))
			return null;
		return Std.parseFloat(expression.matched(1));
	}

	static function numberPair(source:String, prefix:String):Null<Array<Float>> {
		var expression = new EReg(prefix + '\\s*' + numberPattern + '\\s*,\\s*' + numberPattern, 'm');
		if (source == null || !expression.match(source))
			return null;
		return [Std.parseFloat(expression.matched(1)), Std.parseFloat(expression.matched(2))];
	}

	static function escapeRegex(value:String):String {
		var result = '';
		for (index in 0...value.length) {
			var character = value.charAt(index);
			if ('\\.^$|?*+()[]{}'.indexOf(character) >= 0)
				result += '\\';
			result += character;
		}
		return result;
	}

	static function quote(value:String):String {
		return '"' + StringTools.replace(StringTools.replace(value == null ? '' : value,
			'\\', '\\\\'), '"', '\\"') + '"';
	}
}
