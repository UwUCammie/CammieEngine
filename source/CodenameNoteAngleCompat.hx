package;

/** Shared Codename strum/note angle resolution and note travel geometry. */
class CodenameNoteAngleCompat {
	static var cachedTravelAngle:Float = Math.NaN;
	static var cachedTravelSin:Float = 0;
	static var cachedTravelCos:Float = 1;

	/** Per-note direction overrides per-strum direction, which overrides visual strum angle. */
	public static function resolve(noteAngle:Null<Float>, strumNoteAngle:Null<Float>, strumAngle:Float):Float {
		if (noteAngle != null)
			return noteAngle;
		if (strumNoteAngle != null)
			return strumNoteAngle;
		return strumAngle;
	}

	/** Tap heads copy the visible receptor angle; sustain bodies follow travel direction. */
	public static inline function spriteAngle(isSustain:Bool, strumAngle:Float, travelAngle:Float):Float
		return isSustain ? travelAngle : strumAngle;

	/** Codename angle zero travels down on upscroll and up on downscroll. */
	public static function travelOffset(distance:Float, travelAngle:Float, downscroll:Bool):{x:Float, y:Float} {
		var directedDistance = downscroll ? -distance : distance;
		if (travelAngle != cachedTravelAngle) {
			var radians = travelAngle * Math.PI / 180;
			cachedTravelAngle = travelAngle;
			cachedTravelSin = Math.sin(radians);
			cachedTravelCos = Math.cos(radians);
		}
		return {
			x: -cachedTravelSin * directedDistance,
			y: cachedTravelCos * directedDistance
		};
	}
}
