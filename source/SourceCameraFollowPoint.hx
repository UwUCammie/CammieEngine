package;

import flixel.FlxCamera;
import flixel.FlxObject;

/** Psych-era scripts read and follow `camFollowPos`: the eased point the game
 * camera is looking at right now, not the target it is easing towards. The
 * native camera eases by itself, so this point is written back from it. */
class SourceCameraFollowPoint {
	/** Runs after the cameras updated, so a script camera locked onto the point
	 * shows the same place as the game camera in this very frame. */
	public static function sync(point:FlxObject, game:FlxCamera, cameras:Array<FlxCamera>):Void {
		if (point == null || game == null || game.scroll == null) return;
		point.setPosition(SourceCameraFollowPointMath.origin(game.scroll.x, game.width, point.width),
			SourceCameraFollowPointMath.origin(game.scroll.y, game.height, point.height));
		for (camera in cameras)
			if (camera != null && camera != game && camera.target == point && camera.followLerp >= 1) camera.snapToTarget();
	}
}
