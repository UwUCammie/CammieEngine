package;

import flixel.util.FlxColor;

/**
	Regular-class facade for the FlxColor abstract. Haxe cannot pass an abstract
	as a runtime HScript value, while imported HXC scripts only need constants
	and the ordinary color constructors.
*/
class HxcFlxColorCompat {
	public static var BLACK(default, never):Int = FlxColor.BLACK;
	public static var WHITE(default, never):Int = FlxColor.WHITE;
	public static var YELLOW(default, never):Int = FlxColor.YELLOW;
	public static var TRANSPARENT(default, never):Int = FlxColor.TRANSPARENT;

	public static function fromRGB(red:Int, green:Int, blue:Int, alpha:Int = 255):Int {
		return FlxColor.fromRGB(red, green, blue, alpha);
	}

	public static function fromHSB(hue:Float, saturation:Float, brightness:Float, alpha:Float = 1):Int {
		return FlxColor.fromHSB(hue, saturation, brightness, alpha);
	}

	public static function fromString(value:String):Int {
		return FlxColor.fromString(value);
	}
}
