package;

/** Arithmetic for SourceCameraFollowPoint, kept free of display objects. */
class SourceCameraFollowPointMath {
	/** Top-left of a point of the given size whose middle the view is centred on. */
	public static function origin(scroll:Float, viewSize:Float, pointSize:Float):Float
		return scroll + viewSize * 0.5 - pointSize * 0.5;

	/** A script that moved the point itself wants the game camera snapped there. */
	public static function moved(x:Float, y:Float, lastX:Float, lastY:Float):Bool
		return Math.abs(x - lastX) > 0.01 || Math.abs(y - lastY) > 0.01;
}
