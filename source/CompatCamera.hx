package;

import flixel.FlxCamera;

/** Keep the follow target visible to scripts while a donor event owns scroll. */
@:keep
class CompatCamera extends FlxCamera {
	public var followEnabled:Bool = true;

	override function updateFollow():Void {
		if (followEnabled) super.updateFollow();
	}

	override function updateLerp(elapsed:Float):Void {
		// Flixel interpolates scroll separately from computing the follow point.
		// Both phases must stop while an authored tween owns camera.scroll.
		if (followEnabled) super.updateLerp(elapsed);
	}

	override public function snapToTarget():Void {
		// Explicit snaps still work when automatic following was disabled.
		var enabled = followEnabled;
		followEnabled = true;
		super.snapToTarget();
		followEnabled = enabled;
	}
}
