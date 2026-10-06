package;

import flixel.FlxSprite;
import flixel.FlxCamera;
import flixel.math.FlxPoint;
import flixel.math.FlxMath;

/** The shared source splash animation and screen-offset mechanics only. */
@:keep
class NightmareVisionSplashSprite extends FlxSprite {
	public final baseScale:FlxPoint = FlxPoint.get(1, 1);
	public var defScale(get, set):FlxPoint;
	function get_defScale():FlxPoint return baseScale;
	function set_defScale(value:FlxPoint):FlxPoint {
		if (value == null) throw 'Nightmare Vision baseScale cannot be null';
		return baseScale.copyFrom(value);
	}
	public final spriteOffset:FlxPoint = FlxPoint.get();
	public final animOffset:FlxPoint = FlxPoint.get();
	public final animOffsets:Map<String, Array<Float>> = [];
	public var scalableOffsets:Bool = true;
	public var rotatableOffsets:Bool = true;
	public var skewableOffsets:Bool = true;
	public final skew:FlxPoint = FlxPoint.get();
	public var correctFlippedOffsets:Bool = false;
	public var canPlayAnimations:Bool = true;
	var transformedOffset:FlxPoint = FlxPoint.get();
	public function new(x:Float = 0, y:Float = 0) super(x, y);

	public function addOffset(anim:String, x:Float = 0, y:Float = 0):Void animOffsets.set(anim, [x, y]);
	public function setOffsets(anim:String = 'idle'):Void {
		var values = animOffsets.get(anim);
		if (values == null) return;
		animOffset.set(values[0], values[1]);
		if (correctFlippedOffsets) {
			if (flipX) animOffset.x = frameWidth * (scalableOffsets ? scale.x : 1) - width - animOffset.x;
			if (flipY) animOffset.y = frameHeight * (scalableOffsets ? scale.y : 1) - height - animOffset.y;
		}
	}
	public function getAnimName():String return animation.curAnim == null ? '' : animation.curAnim.name;
	public function correctAnimationName(name:String):Null<String> {
		if (animation.exists(name)) return name;
		var suffix = name.lastIndexOf('-');
		return suffix < 0 ? null : correctAnimationName(name.substring(0, suffix));
	}
	public function playAnim(anim:String, force:Bool = false, isReversed:Bool = false, frame:Int = 0):Void {
		if (canPlayAnimations) {
			var name = correctAnimationName(anim);
			if (name != null) {
				animation.play(name, force, isReversed, frame);
				setOffsets(name);
			}
		}
		centerOffsets();
		centerOrigin();
	}

	/** Source FunkinSprite applies these offsets in screen space, after scale/rotation. */
	override public function getScreenPosition(?result:FlxPoint, ?camera:FlxCamera):FlxPoint {
		transformedOffset.set(spriteOffset.x + animOffset.x, spriteOffset.y + animOffset.y);
		if (scalableOffsets && (Math.abs(scale.x - baseScale.x) > FlxMath.EPSILON || Math.abs(scale.y - baseScale.y) > FlxMath.EPSILON))
			transformedOffset.scale(scale.x / baseScale.x, scale.y / baseScale.y);
		if (rotatableOffsets && Math.abs(angle) > FlxMath.EPSILON) transformedOffset.rotateByDegrees(angle);
		if (skewableOffsets && (Math.abs(skew.x) > FlxMath.EPSILON || Math.abs(skew.y) > FlxMath.EPSILON)) {
			var pX = transformedOffset.x, pY = transformedOffset.y;
			var radiansX = skew.x / 180 * Math.PI, radiansY = skew.y / 180 * Math.PI;
			transformedOffset.x += pY * (FlxMath.fastSin(radiansX) / FlxMath.fastCos(radiansX));
			transformedOffset.y += pX * (FlxMath.fastSin(radiansY) / FlxMath.fastCos(radiansY));
		}
		return super.getScreenPosition(result, camera).subtract(transformedOffset);
	}
	override public function destroy():Void {
		baseScale.put(); spriteOffset.put(); animOffset.put(); skew.put(); transformedOffset.put();
		animOffsets.clear();
		super.destroy();
	}
}
