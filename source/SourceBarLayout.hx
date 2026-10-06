package;

import flixel.FlxSprite;
import flixel.math.FlxMath;
import flixel.math.FlxPoint;

/** Both source bar dialects split physical sprite clips using the same math. */
class SourceBarLayout {
	public static function apply(left:FlxSprite, right:FlxSprite, background:FlxSprite,
		offset:FlxPoint, width:Int, height:Int, percent:Float, leftToRight:Bool,
		backgroundOffsetX:Float = 0, backgroundOffsetY:Float = 0):Float {
		left.setPosition(background.x - backgroundOffsetX, background.y - backgroundOffsetY);
		right.setPosition(background.x - backgroundOffsetX, background.y - backgroundOffsetY);
		var leftSize = leftToRight ? FlxMath.lerp(0, width, percent / 100)
			: FlxMath.lerp(0, width, 1 - percent / 100);
		left.clipRect.width = leftSize;
		left.clipRect.height = height;
		left.clipRect.x = offset.x;
		left.clipRect.y = offset.y;
		right.clipRect.width = width - leftSize;
		right.clipRect.height = height;
		right.clipRect.x = offset.x + leftSize;
		right.clipRect.y = offset.y;
		var center = left.x + leftSize + offset.x;
		left.clipRect = left.clipRect;
		right.clipRect = right.clipRect;
		return center;
	}
}
