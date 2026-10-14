package;

import flixel.FlxSprite;
import flixel.math.FlxMath;
import flixel.math.FlxPoint;
import flixel.math.FlxRect;
import flixel.util.FlxColor;

/** Both source bar dialects split physical sprite clips using the same math. */
class SourceBarLayout {
	/** Fill percent for a bar's value function, as both donors compute it in
	 * update(); no function means an empty bar. The donors keep the result in a
	 * Null<Float>, which boxes on native every frame per bar for a value that is
	 * never null, so it stays a plain Float here. */
	public static function percentFor(valueFunction:Null<Void->Float>, min:Float, max:Float):Float {
		if (valueFunction == null) return 0;
		return FlxMath.remapToRange(FlxMath.bound(valueFunction(), min, max), min, max, 0, 100);
	}

	/** Resize one fill sprite to the background and reset its clip. Nightmare
	 * Vision remakes the fill when its frame no longer matches the background's
	 * (a swapped background image); Psych always rescales. */
	public static function regenerateClip(bar:FlxSprite, background:FlxSprite, remakeOnFrameChange:Bool):Void {
		if (bar == null) return;
		if (remakeOnFrameChange && (Std.int(bar.frameWidth) != Std.int(background.frameWidth)
			|| Std.int(bar.frameHeight) != Std.int(background.frameHeight)))
			bar.makeGraphic(Std.int(background.width), Std.int(background.height), FlxColor.WHITE);
		else
			bar.setGraphicSize(Std.int(background.width), Std.int(background.height));
		bar.updateHitbox();
		bar.clipRect = new FlxRect(0, 0, Std.int(background.width), Std.int(background.height));
	}

	/** Nightmare Vision's alphaMultipler rule, shared by its bar and health icon. */
	public static inline function multipliedAlpha(value:Float, multiplier:Float):Float
		return FlxMath.bound(value, 0, 1) * multiplier;

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
