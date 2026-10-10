package;

import flixel.FlxCamera;
import flixel.text.FlxText;
import flixel.util.FlxColor;

/** Matching native formatting shared by the Psych-family text constructors. */
class SourceTextDefaults {
	public static function apply(text:FlxText, font:String, camera:FlxCamera, forceCamera:Bool = false, ?bindCamera:()->Void):Void {
		text.setFormat(font, 16, FlxColor.WHITE, CENTER, OUTLINE, FlxColor.BLACK);
		if (bindCamera != null) bindCamera();
		else if (camera != null || forceCamera) text.cameras = [camera];
		text.scrollFactor.set();
		text.borderSize = 2;
	}
}
