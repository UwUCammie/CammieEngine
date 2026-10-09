package;

import flixel.FlxCamera;
import flixel.text.FlxText;
import flixel.util.FlxColor;

/** Native text with the historical Psych-family mounting flag and defaults. */
@:keep
class SourceModchartText extends FlxText {
	public var wasAdded:Bool = false;
	public function new(x:Float, y:Float, text:String, width:Float, font:String, camera:FlxCamera) {
		super(x, y, width, text, 16);
		setFormat(font, 16, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		cameras = [camera];
		scrollFactor.set();
		borderSize = 2;
	}
}
