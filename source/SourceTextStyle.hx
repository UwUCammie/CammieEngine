package;

import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.util.FlxColor;

/** Psych-family style parsing over the engine's native text and color types. */
class SourceTextStyle {
	public static function border(text:Dynamic, value:String):Void {
		var style = switch (StringTools.trim(value.toLowerCase())) {
			case 'shadow': FlxTextBorderStyle.SHADOW;
			case 'outline': FlxTextBorderStyle.OUTLINE;
			case 'outline_fast', 'outlinefast': FlxTextBorderStyle.OUTLINE_FAST;
			default: FlxTextBorderStyle.NONE;
		};
		Reflect.setProperty(text, 'borderStyle', style);
	}
	/** Preserve all 32 ARGB bits on Windows, where strtol overflows for full hex words. */
	static function integer(value:String):Null<Int> {
		if (~/^0[xX][0-9a-fA-F]{8}$/.match(value))
			return (Std.parseInt(value.substr(0, 6)) << 16) | Std.parseInt('0x' + value.substr(6));
		return Std.parseInt(value);
	}
	public static function historicalColor(value:String):Dynamic {
		return integer(StringTools.startsWith(value, '0x') ? value : '0xff' + value);
	}
	public static function psychColor(value:String):Int {
		value = StringTools.trim(~/[\t\n\r]/.split(value).join(''));
		if (StringTools.startsWith(value, '0x')) value = value.substring(value.length - 6);
		// FlxColor accepts #AARRGGBB too; avoid its native parseInt overflow for this case.
		var hex = StringTools.startsWith(value, '#') ? value.substr(1) : value;
		if (~/^[0-9a-fA-F]{8}$/.match(hex)) return integer('0x' + hex);
		var parsed = FlxColor.fromString(value);
		if (parsed == null) parsed = FlxColor.fromString('#' + value);
		return parsed == null ? FlxColor.WHITE : parsed;
	}
}
