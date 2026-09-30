package;

import haxe.Json;
using StringTools;

/** Engine-neutral presentation values used by FPS Plus/Kade dialogue portraits. */
typedef LegacyDialoguePortraitConfig = {
	var scale:Float;
	var offsetX:Float;
	var offsetY:Float;
	var antialiasing:Null<Bool>;
	var frameRate:Float;
	var looped:Bool;
}

/**
	Compatibility helpers for legacy dialogue portrait bundles.

	FPS Plus/Kade packs commonly store `<portrait>.png`, `<portrait>.xml`, and
	`<portrait>.json` together below `images/ui/dialogue/portraits`.  Keep JSON
	parsing and path-token validation outside DialogueBox so malformed optional
	metadata cannot break a cutscene and can be regression-tested without Flixel.
*/
class LegacyDialoguePortraitCompat {
	public static function defaults():LegacyDialoguePortraitConfig {
		return {
			scale: 1,
			offsetX: 0,
			offsetY: 0,
			antialiasing: null,
			frameRate: 24,
			looped: true
		};
	}

	/** Reject path syntax while retaining ordinary authored ids and spaces. */
	public static function safeId(value:String):String {
		if (value == null)
			return '';
		var clean = StringTools.trim(value);
		if (clean == '' || clean == '.' || clean == '..' || clean.indexOf('/') >= 0
			|| clean.indexOf('\\') >= 0 || clean.indexOf(':') >= 0
			|| clean.indexOf('\u0000') >= 0 || clean.indexOf('..') >= 0)
			return '';
		return clean;
	}

	/** Parse the optional portrait JSON using safe defaults for every bad field. */
	public static function parse(text:String):LegacyDialoguePortraitConfig {
		var result = defaults();
		var data = parseObject(text);
		if (data == null)
			return result;
		result.scale = finitePositive(Reflect.field(data, 'scale'), result.scale);
		result.frameRate = finitePositive(firstField(data, ['frameRate', 'framerate', 'fps']), result.frameRate);
		var antialiasing = Reflect.field(data, 'antialiasing');
		if (antialiasing == true || antialiasing == false)
			result.antialiasing = antialiasing;
		var looped = firstField(data, ['looped', 'loop']);
		if (looped == true || looped == false)
			result.looped = looped;
		var offset:Dynamic = Reflect.field(data, 'offset');
		if (isObject(offset)) {
			result.offsetX = finiteNumber(Reflect.field(offset, 'x'), result.offsetX);
			result.offsetY = finiteNumber(Reflect.field(offset, 'y'), result.offsetY);
		}
		return result;
	}

	/** Return whether text is a valid object containing portrait metadata. */
	public static function hasMetadata(text:String):Bool {
		var data = parseObject(text);
		if (data == null)
			return false;
		for (field in ['scale', 'offset', 'antialiasing', 'frameRate', 'framerate', 'fps', 'looped', 'loop'])
			if (Reflect.hasField(data, field))
				return true;
		return false;
	}

	/** Build the complete frame order without depending on a donor prefix. */
	public static function frameIndices(count:Int):Array<Int> {
		var result:Array<Int> = [];
		if (count <= 0)
			return result;
		for (index in 0...count)
			result.push(index);
		return result;
	}

	static function firstField(data:Dynamic, names:Array<String>):Dynamic {
		if (!isObject(data))
			return null;
		for (name in names) {
			var value = Reflect.field(data, name);
			if (value != null)
				return value;
		}
		return null;
	}

	static function finiteNumber(value:Dynamic, fallback:Float):Float {
		if (value == null)
			return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) || parsed == Math.POSITIVE_INFINITY
			|| parsed == Math.NEGATIVE_INFINITY ? fallback : parsed;
	}

	static function finitePositive(value:Dynamic, fallback:Float):Float {
		var parsed = finiteNumber(value, fallback);
		return parsed > 0 ? parsed : fallback;
	}

	static function parseObject(text:String):Dynamic {
		if (text == null || StringTools.trim(text) == '')
			return null;
		try {
			var data:Dynamic = Json.parse(text);
			return isObject(data) ? data : null;
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function isObject(value:Dynamic):Bool {
		return value != null && !Std.isOfType(value, Array) && !Std.isOfType(value, String)
			&& !Std.isOfType(value, Bool) && !Std.isOfType(value, Int)
			&& !Std.isOfType(value, Float);
	}
}
