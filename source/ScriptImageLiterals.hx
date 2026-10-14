package;

/**
	Finds the images a Psych script will load by a fixed name: the second
	argument of makeLuaSprite / makeAnimatedLuaSprite when it is a plain quoted
	string. A name built at run time (concatenation, a variable) is skipped,
	so the list only holds images the script can actually ask for.

	Used to decode a global script's images while the song loads. Such a script
	often builds a whole screen in one callback near the end of the song, and
	decoding its images there froze one frame for a third of a second.
**/
class ScriptImageLiterals {
	public static inline var DEFAULT_LIMIT:Int = 64;
	/** Larger images are left to load when used: a script that names one is
		usually choosing between several big sheets, and decoding all of them
		would hold far more memory than the one it shows. */
	public static inline var MAX_IMAGE_PIXELS:Int = 2048 * 2048;
	/** Decoded bytes all prewarmed images of one song may hold together. */
	public static inline var MAX_TOTAL_BYTES:Float = 64 * 1024 * 1024;

	/**
		Pick, in order, the images to decode early: known size, within
		MAX_IMAGE_PIXELS each and MAX_TOTAL_BYTES together. `pixels` gives an
		image's pixel count, or a negative number when it is unknown.
	**/
	public static function withinBudget(images:Array<String>, pixels:String->Int):Array<String> {
		var chosen:Array<String> = [];
		var total = 0.0;
		for (image in images) {
			var count = pixels(image);
			if (count <= 0 || count > MAX_IMAGE_PIXELS || total + count * 4.0 > MAX_TOTAL_BYTES)
				continue;
			total += count * 4.0;
			chosen.push(image);
		}
		return chosen;
	}

	/** Width times height from a PNG header, or -1 when it is not a PNG. */
	public static function pngPixels(header:haxe.io.Bytes):Int {
		if (header == null || header.length < 24 || header.get(0) != 0x89 || header.get(1) != 'P'.code
			|| header.get(2) != 'N'.code || header.get(3) != 'G'.code)
			return -1;
		var width = readBigEndian(header, 16);
		var height = readBigEndian(header, 20);
		if (width <= 0 || height <= 0 || width > 65535 || height > 65535)
			return -1;
		return width * height;
	}

	static inline function readBigEndian(bytes:haxe.io.Bytes, at:Int):Int
		return (bytes.get(at) << 24) | (bytes.get(at + 1) << 16) | (bytes.get(at + 2) << 8) | bytes.get(at + 3);

	static final CONSTRUCTORS:Array<String> = ['makeLuaSprite', 'makeAnimatedLuaSprite'];

	/** Distinct image names, in first-seen order, at most `limit` of them. */
	public static function spriteImages(source:String, limit:Int = DEFAULT_LIMIT):Array<String> {
		var found:Array<String> = [];
		if (source == null || limit <= 0)
			return found;
		var seen = new Map<String, Bool>();
		var index = 0;
		while (index < source.length && found.length < limit) {
			var next = -1;
			var nameLength = 0;
			for (name in CONSTRUCTORS) {
				var at = source.indexOf(name + '(', index);
				// Neither name occurs inside the other, so the nearest match is
				// the next call.
				if (at >= 0 && (next < 0 || at < next)) {
					next = at;
					nameLength = name.length;
				}
			}
			if (next < 0)
				break;
			index = next + nameLength + 1;
			// A longer identifier that merely ends in the name is not the call.
			if (next > 0 && isIdentifierChar(source.charCodeAt(next - 1)))
				continue;
			var image = secondLiteral(source, index);
			if (image == null || image == '' || seen.exists(image))
				continue;
			seen.set(image, true);
			found.push(image);
		}
		return found;
	}

	/** The second argument when it is exactly one quoted string, else null. */
	static function secondLiteral(source:String, start:Int):Null<String> {
		var i = skipArgument(source, start);
		if (i < 0 || source.charCodeAt(i) != ','.code)
			return null;
		i = skipSpace(source, i + 1);
		if (i >= source.length)
			return null;
		var quote = source.charCodeAt(i);
		if (quote != "'".code && quote != '"'.code)
			return null;
		var close = source.indexOf(String.fromCharCode(quote), i + 1);
		if (close < 0)
			return null;
		var text = source.substring(i + 1, close);
		// Escapes and line breaks mean this is not a simple asset name.
		if (text.indexOf('\\') >= 0 || text.indexOf('\n') >= 0)
			return null;
		var after = skipSpace(source, close + 1);
		if (after >= source.length)
			return null;
		var end = source.charCodeAt(after);
		return end == ','.code || end == ')'.code ? text : null;
	}

	/** Index of the comma or bracket that ends the argument starting at `start`. */
	static function skipArgument(source:String, start:Int):Int {
		var depth = 0;
		var i = start;
		while (i < source.length) {
			var code = source.charCodeAt(i);
			if (code == "'".code || code == '"'.code) {
				var close = source.indexOf(String.fromCharCode(code), i + 1);
				if (close < 0)
					return -1;
				i = close + 1;
				continue;
			}
			if (code == '('.code || code == '['.code || code == '{'.code)
				depth++;
			else if (code == ')'.code || code == ']'.code || code == '}'.code) {
				if (depth == 0)
					return i;
				depth--;
			} else if (code == ','.code && depth == 0)
				return i;
			else if (code == '\n'.code && depth == 0)
				return -1;
			i++;
		}
		return -1;
	}

	static function skipSpace(source:String, start:Int):Int {
		var i = start;
		while (i < source.length) {
			var code = source.charCodeAt(i);
			if (code != ' '.code && code != '\t'.code && code != '\r'.code)
				break;
			i++;
		}
		return i;
	}

	static inline function isIdentifierChar(code:Null<Int>):Bool
		return code != null && (code == '_'.code || (code >= 'a'.code && code <= 'z'.code)
			|| (code >= 'A'.code && code <= 'Z'.code) || (code >= '0'.code && code <= '9'.code));
}
