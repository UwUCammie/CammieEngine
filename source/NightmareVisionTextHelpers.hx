package;

import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.util.FlxColor;

/** Historical NV preset helper, delegated to the shared native text implementation. */
class NightmareVisionTextHelpers {
	public static function setTxtFormat(txt:FlxText, ?font:String, size:Int = 8,
		color:FlxColor = FlxColor.WHITE, ?alignment:FlxTextAlign,
		?borderStyle:FlxTextBorderStyle, borderColor:FlxColor = FlxColor.TRANSPARENT,
		embeddedFont:Bool = true):Void {
		txt.setFormat(font, size, color, alignment, borderStyle, borderColor, embeddedFont);
	}
}
