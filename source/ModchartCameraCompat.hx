import flixel.FlxBasic;
import flixel.FlxCamera;

/** Resolve authored camera assignments without borrowing the current draw's
	global default. Modchart rendering runs outside the native note group's draw,
	where FlxBasic.getCameras() would otherwise select the gameplay camera. */
class ModchartCameraCompat {
	public static function explicitCameras(item:FlxBasic):Array<FlxCamera> {
		if (item == null) return null;
		@:privateAccess var cameras = item._cameras;
		if (cameras != null && cameras.length > 0) return cameras;
		return item.container == null ? null : explicitCameras(item.container);
	}

	public static function resolve(item:FlxBasic, playfield:FlxBasic,
		fallback:Void->Array<FlxCamera>):Array<FlxCamera> {
		var cameras = explicitCameras(item);
		if (cameras == null) cameras = explicitCameras(playfield);
		return cameras == null ? fallback() : cameras;
	}
}
