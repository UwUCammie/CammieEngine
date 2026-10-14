package;

/** Arithmetic for SourceCameraFollowPoint, kept free of display objects. */
class SourceCameraFollowPointMath {
	/** Top-left of a point of the given size whose middle the view is centred on. */
	public static function origin(scroll:Float, viewSize:Float, pointSize:Float):Float
		return scroll + viewSize * 0.5 - pointSize * 0.5;

	/** A script that moved the point itself wants the game camera snapped there. */
	public static function moved(x:Float, y:Float, lastX:Float, lastY:Float):Bool
		return Math.abs(x - lastX) > 0.01 || Math.abs(y - lastY) > 0.01;

	public static inline var PLAYER:Int = 0;
	public static inline var OPPONENT:Int = 1;
	public static inline var GIRLFRIEND:Int = 2;
	/** Psych looks 150 px past the opponent's middle, Nightmare Vision only 100. */
	public static inline var PSYCH_OPPONENT_BASE_X:Float = 150;
	public static inline var NIGHTMARE_OPPONENT_BASE_X:Float = 100;

	/**
		Psych-family section focus, X offset from the character's middle: the
		side's base, the character's camera_position (mirrored for the player,
		who faces the other way) and the stage's camera offset for that side.
	**/
	public static function focusOffsetX(side:Int, cameraX:Float, stageX:Float, opponentBaseX:Float):Float {
		if (side == PLAYER) return -100 + -cameraX + stageX;
		if (side == GIRLFRIEND) return 0 + cameraX + stageX;
		return opponentBaseX + cameraX + stageX;
	}

	/** The Y half of focusOffsetX; only the girlfriend side has no -100 base. */
	public static function focusOffsetY(side:Int, cameraY:Float, stageY:Float):Float
		return (side == GIRLFRIEND ? 0 : -100) + cameraY + stageY;
}
