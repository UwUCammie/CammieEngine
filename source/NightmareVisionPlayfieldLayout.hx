package;

/**
	Coordinate helpers matching Nightmare Vision's ModManager playfield layout.
	Only field IDs 0 and 1 have dedicated horizontal positions; every other
	field ID uses the source engine's centered fallback.
*/
class NightmareVisionPlayfieldLayout {
	/** Historical getBaseX uses top-left positions and fixed four-column offsets. */
	public static function legacyBaseX(direction:Int, player:Int, width:Float, noteWidth:Float):Float {
		var x = width * 0.5 - noteWidth - 54 + noteWidth * direction;
		if (player == 0) x += width * 0.5 - noteWidth * 2 - 100;
		else if (player == 1) x -= width * 0.5 - noteWidth * 2 - 100;
		return x - 56;
	}

	/** Initial source placement precedes the independent modifier-space position. */
	public static function legacyEntranceX(baseX:Float, direction:Int, noteWidth:Float, split:Bool):Float {
		var x = baseX - noteWidth * 0.5 - noteWidth * 2 + noteWidth * direction + 54;
		return x + (split ? noteWidth * (direction > 1 ? 3 : -3) : 0);
	}

	public static inline function centerX(field:Int, keys:Int, screenWidth:Float, swagWidth:Float):Float {
		return switch (field) {
			case 0: screenWidth - swagWidth * (keys / 2) - 100 - 3;
			case 1: swagWidth * (keys / 2) + 100 - 3;
			default: screenWidth * 0.5 - 3;
		};
	}

	public static inline function receptorCenterX(field:Int, direction:Int, keys:Int, screenWidth:Float, swagWidth:Float):Float {
		return centerX(field, keys, screenWidth, swagWidth) + swagWidth * (direction - (keys / 2) + 0.5);
	}

	public static inline function receptorCenterY(screenHeight:Float, swagWidth:Float, downscroll:Bool):Float {
		final baseY = swagWidth * 0.5 + 50;
		return downscroll ? screenHeight - baseY : baseY;
	}
}
