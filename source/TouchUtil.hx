package;

/**
	V-Slice's touch-screen helper (funkin.util.TouchUtil) on a build with no
	touch screen. V-Slice reads the first FlxG touch, which never exists on
	desktop, so every query there is false and `touch` is null. Scripts guard
	their mouse and keyboard fallbacks behind these checks, so answering the same
	way lets those fallbacks run.
**/
@:keep
class TouchUtil {
	public static var pressed(get, never):Bool;
	public static var justPressed(get, never):Bool;
	public static var justReleased(get, never):Bool;
	public static var released(get, never):Bool;
	public static var justMoved(get, never):Bool;

	/** The first active touch; there is never one on this build. */
	public static var touch(get, never):Dynamic;

	static function get_pressed():Bool
		return false;

	static function get_justPressed():Bool
		return false;

	static function get_justReleased():Bool
		return false;

	// V-Slice reports `released` as true only while a touch exists.
	static function get_released():Bool
		return false;

	static function get_justMoved():Bool
		return false;

	static function get_touch():Dynamic
		return null;

	public static function overlaps(?object:Dynamic, ?camera:Dynamic):Bool
		return false;

	public static function overlapsComplex(?object:Dynamic, ?camera:Dynamic):Bool
		return false;

	/**
		Unlike the other queries this one never reads a touch: it is a plain
		object-versus-point test, so it keeps working on desktop. V-Slice hands
		a weak point back to its pool afterwards whatever the answer.
	**/
	public static function overlapsComplexPoint(?object:flixel.FlxObject, ?point:flixel.math.FlxPoint, inScreenSpace:Bool = false,
			?camera:flixel.FlxCamera):Bool {
		if (object == null || point == null)
			return false;
		if (camera == null && object.cameras != null && object.cameras.length > 0)
			camera = object.cameras[0];
		var hit = object.overlapsPoint(point, inScreenSpace, camera);
		point.putWeak();
		return hit;
	}

	public static function pressAction(?object:Dynamic, ?camera:Dynamic, ?useOverlapsComplex:Bool):Bool
		return false;
}
