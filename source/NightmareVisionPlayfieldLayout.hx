package;

/**
	Coordinate helpers matching Nightmare Vision's ModManager playfield layout.
	Only field IDs 0 and 1 have dedicated horizontal positions; every other
	field ID uses the source engine's centered fallback.
*/
class NightmareVisionPlayfieldLayout {
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
