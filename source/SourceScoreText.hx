package;

import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextFormat;

/** Native rank markup belongs to the text that produced its character range.
 * A script replacing the score must not inherit that range on unrelated digits.
 * Authored formats remain under the script's control. */
class SourceScoreText extends FlxText {
	var sourceFormat:FlxTextFormat;
	var sourceFormatColor:Int;

	public function applySourceFormat(color:Int, start:Int, end:Int):Void {
		if (sourceFormat != null) removeFormat(sourceFormat);
		if (start < 0 || end <= start || end > text.length) return;
		if (sourceFormat == null || sourceFormatColor != color) {
			sourceFormat = new FlxTextFormat(color);
			sourceFormatColor = color;
		}
		addFormat(sourceFormat, start, end);
	}

	override function set_text(value:String):String {
		if (value != text && sourceFormat != null)
			removeFormat(sourceFormat);
		return super.set_text(value);
	}
}
