package;

import flixel.FlxSprite;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;

/**
	V-Slice's sprite text (funkin.ui.AtlasText): one animated sprite per
	letter, laid out left to right, with the font picked by name.

	A font is the Sparrow atlas `images/fonts/<name>`. Imported scripts pass
	their owner's asset proxy as the optional last argument so a font shipped
	with that content is found there first; the engine's own `images/fonts`
	folder comes next. V-Slice's base fonts (`bold`, `default`) are not
	shipped with the engine, so those, and any font that cannot be found, are
	drawn from the engine's alphabet atlas with the matching letter style
	instead of leaving the text blank.
**/
@:keep
class AtlasText extends FlxTypedSpriteGroup<AtlasChar> {
	static var fonts:Map<String, AtlasTextFont> = new Map();

	public var text(default, set):String = '';
	public var font(default, null):AtlasTextFont;
	public var atlas(get, never):FlxAtlasFrames;
	public var maxHeight(get, never):Float;

	/** `Both`, `Upper` or `Lower`: which letter case the font has. */
	public var caseAllowed(get, never):String;

	public function new(x:Float = 0, y:Float = 0, text:String = '', fontName:String = 'default', ?paths:Dynamic) {
		super(x, y);
		font = loadFont(fontName == null ? 'default' : fontName, paths);
		this.text = text;
	}

	inline function get_atlas():FlxAtlasFrames
		return font.atlas;

	inline function get_maxHeight():Float
		return font.maxHeight;

	inline function get_caseAllowed():String
		return font.caseAllowed;

	/**
		Fonts from an owner proxy are kept per proxy, so two imports with a
		font of the same name never share one.
	**/
	static function loadFont(name:String, paths:Dynamic):AtlasTextFont {
		// An imported menu that did not pass its proxy still owns its fonts.
		var sessionRoot = '';
		if (paths == null) {
			sessionRoot = HxcStateFactory.menuSessionRoot();
			if (sessionRoot == null)
				sessionRoot = '';
			var cached = fonts.get(sessionRoot + '|' + name);
			if (cached != null && (cached.atlas == null || (cached.atlas.parent != null && cached.atlas.parent.bitmap != null)))
				return cached;
			if (sessionRoot != '')
				paths = HxcStateAssetScope.paths(sessionRoot);
		}
		var atlas = paths == null ? null : ownerAtlas(paths, 'fonts/' + name);
		if (atlas == null && FNFAssets.exists('assets/images/fonts/' + name + '.png')
			&& FNFAssets.exists('assets/images/fonts/' + name + '.xml')) {
			try atlas = FlxAtlasFrames.fromSparrow('assets/images/fonts/' + name + '.png', 'assets/images/fonts/' + name + '.xml')
			catch (_:Dynamic) {}
		}
		var made = atlas != null ? AtlasTextFont.fromAtlas(atlas) : AtlasTextFont.engineAlphabet(name.toLowerCase() == 'bold');
		if (sessionRoot != '' || paths == null)
			fonts.set(sessionRoot + '|' + name, made);
		return made;
	}

	/** An owner atlas with at least one frame, or null when the owner has none. */
	static function ownerAtlas(paths:Dynamic, key:String):FlxAtlasFrames {
		var load = Reflect.field(paths, 'getSparrowAtlas');
		if (!Reflect.isFunction(load))
			return null;
		var atlas:FlxAtlasFrames = null;
		try atlas = Reflect.callMethod(paths, load, [key]) catch (_:Dynamic) {}
		return atlas != null && atlas.frames != null && atlas.frames.length > 0 ? atlas : null;
	}

	function set_text(value:String):String {
		if (value == null)
			value = '';
		var caseValue = restrictCase(value);
		var caseText = restrictCase(this.text);
		this.text = value;
		if (caseText == caseValue)
			return value;
		if (caseValue.indexOf(caseText) == 0) {
			// New text only adds to the end, so keep the letters already drawn.
			appendTextCased(caseValue.substr(caseText.length));
			return this.text;
		}
		group.kill();
		if (caseValue != '')
			appendTextCased(caseValue);
		return this.text;
	}

	public function appendText(str:String):Void {
		if (str == null)
			throw 'cannot append null';
		if (str != '')
			this.text += str;
	}

	function restrictCase(str:String):String {
		return switch (caseAllowed) {
			case 'Upper': str.toUpperCase();
			case 'Lower': str.toLowerCase();
			default: str;
		};
	}

	function appendTextCased(str:String):Void {
		var charCount = group.countLiving();
		var xPos:Float = 0;
		var yPos:Float = 0;
		if (charCount == -1) {
			charCount = 0;
		} else if (charCount > 0) {
			var lastChar = group.members[charCount - 1];
			xPos = lastChar.x + lastChar.width - x;
			yPos = lastChar.y + lastChar.height - maxHeight - y;
		}
		for (char in str.split('')) {
			switch (char) {
				case ' ':
					xPos += 40;
				case '\n':
					xPos = 0;
					yPos += maxHeight;
				default:
					var charSprite:AtlasChar;
					if (group.members.length <= charCount) {
						charSprite = new AtlasChar(0, 0, font, char);
					} else {
						charSprite = group.members[charCount];
						charSprite.revive();
						charSprite.char = char;
						charSprite.alpha = 1;
					}
					charSprite.x = xPos;
					charSprite.y = yPos + maxHeight - charSprite.height;
					add(charSprite);
					xPos += charSprite.width;
					charCount++;
			}
		}
	}

	/** Width of the text in pixels, measured the way V-Slice measures it. */
	public function getWidth():Int {
		var width = 0;
		for (char in text.split('')) {
			switch (char) {
				case ' ':
					width += 40;
				case '\n':
				default:
					var sprite = new AtlasChar(0, 0, font, char);
					width += Std.int(sprite.width);
					sprite.destroy();
			}
		}
		return width;
	}
}

/** One letter of an AtlasText. */
@:keep
class AtlasChar extends FlxSprite {
	public var char(default, set):String;

	final font:AtlasTextFont;

	public function new(x:Float = 0, y:Float = 0, font:AtlasTextFont, char:String) {
		super(x, y);
		this.font = font;
		if (font.atlas != null)
			frames = font.atlas;
		this.char = char;
	}

	function set_char(value:String):String {
		if (this.char == value)
			return this.char;
		if (font.atlas != null) {
			// A recycled letter still holds the previous character's animation.
			if (animation.exists('anim'))
				animation.remove('anim');
			for (prefix in font.prefixesFor(value)) {
				animation.addByPrefix('anim', prefix, 24);
				if (animation.exists('anim'))
					break;
			}
			if (animation.exists('anim'))
				animation.play('anim', true);
		}
		updateHitbox();
		return this.char = value;
	}
}

/** A loaded font: its atlas, tallest frame, letter case and frame naming. */
@:keep
class AtlasTextFont {
	public var atlas(default, null):FlxAtlasFrames;
	public var maxHeight(default, null):Float = 0;
	public var caseAllowed(default, null):String = 'Both';

	/** True for the engine alphabet stand-in, which names frames differently. */
	public var engineAlphabetStyle(default, null):Bool = false;
	public var bold(default, null):Bool = false;

	function new() {}

	public static function fromAtlas(atlas:FlxAtlasFrames):AtlasTextFont {
		var font = new AtlasTextFont();
		font.atlas = atlas;
		if (atlas.parent != null) {
			atlas.parent.destroyOnNoUse = false;
			atlas.parent.persist = true;
		}
		var containsUpper = false;
		var containsLower = false;
		for (frame in atlas.frames) {
			font.maxHeight = Math.max(font.maxHeight, frame.frame.height);
			if (!containsUpper)
				containsUpper = isLetterFrame(frame.name, true);
			if (!containsLower)
				containsLower = isLetterFrame(frame.name, false);
		}
		if (containsUpper != containsLower)
			font.caseAllowed = containsUpper ? 'Upper' : 'Lower';
		return font;
	}

	public static function engineAlphabet(bold:Bool):AtlasTextFont {
		var font = new AtlasTextFont();
		font.engineAlphabetStyle = true;
		font.bold = bold;
		font.caseAllowed = bold ? 'Upper' : 'Both';
		try font.atlas = FlxAtlasFrames.fromSparrow('assets/images/alphabet.png', 'assets/images/alphabet.xml') catch (_:Dynamic) {}
		if (font.atlas != null) {
			if (font.atlas.parent != null) {
				font.atlas.parent.destroyOnNoUse = false;
				font.atlas.parent.persist = true;
			}
			for (frame in font.atlas.frames)
				font.maxHeight = Math.max(font.maxHeight, frame.frame.height);
		}
		return font;
	}

	/** V-Slice's `^[A-Z]\d+$` / `^[a-z]\d+$` frame test, without a regex. */
	static function isLetterFrame(name:String, upper:Bool):Bool {
		if (name == null || name.length < 2)
			return false;
		var first = name.charCodeAt(0);
		if (upper ? (first < 'A'.code || first > 'Z'.code) : (first < 'a'.code || first > 'z'.code))
			return false;
		for (i in 1...name.length) {
			var code = name.charCodeAt(i);
			if (code < '0'.code || code > '9'.code)
				return false;
		}
		return true;
	}

	/** Animation prefixes to try for one character, best match first. */
	public function prefixesFor(char:String):Array<String> {
		if (!engineAlphabetStyle)
			return [vslicePrefix(char)];
		var lower = char.toLowerCase();
		var isLetter = lower != char.toUpperCase();
		if (bold) {
			if (isLetter || (char.length == 1 && char.charCodeAt(0) >= '0'.code && char.charCodeAt(0) <= '9'.code))
				return [char.toUpperCase() + ' bold'];
			var named = engineSymbolName(char);
			return named == null ? [char + ' bold'] : [named + ' bold'];
		}
		if (isLetter) {
			if (char == lower)
				return [char + ' lowercase'];
			// The engine atlas spells two capitals "captial".
			return [char + ' capital', char + ' captial'];
		}
		var named = engineSymbolName(char);
		return named == null ? [char] : [named, named + ' bold'];
	}

	static function engineSymbolName(char:String):String {
		return switch (char) {
			case '.': 'period';
			case "'": 'apostraphie';
			case '?': 'question mark';
			case '!': 'exclamation point';
			case ',': 'comma';
			case '\\': 'bs';
			case '/': 'fs';
			case '↓': 'down arrow';
			case '↑': 'up arrow';
			case '←': 'left arrow';
			case '→': 'right arrow';
			case '♥' | '♡': 'heart';
			default: null;
		};
	}

	/** V-Slice's frame names for the characters it does not name by themselves. */
	static function vslicePrefix(char:String):String {
		return switch (char) {
			case '&': '-andpersand-';
			case "'": '-apostraphie-';
			case '\\': '-back slash-';
			case ',': '-comma-';
			case '-': '-dash-';
			case '↓': '-down arrow-';
			case '”': '-end quote-';
			case '!': '-exclamation point-';
			case '/': '-forward slash-';
			case '>': '-greater than-';
			case '♥' | '♡': '-heart-';
			case '←': '-left arrow-';
			case '<': '-less than-';
			case '*': '-multiply x-';
			case '.': '-period-';
			case '?': '-question mark-';
			case '→': '-right arrow-';
			case '“': '-start quote-';
			case '↑': '-up arrow-';
			default: char;
		};
	}
}
