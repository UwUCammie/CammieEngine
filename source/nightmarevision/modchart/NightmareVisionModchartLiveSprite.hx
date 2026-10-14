package nightmarevision.modchart;

/**
	Typed access to the sprite values the modchart renderer reads and writes on
	every note, every frame and around every scripted modifier. Going through
	Reflect boxes each Float into a new heap object, and on modchart songs those
	boxes were most of the garbage that made the collector pause mid-song.

	A sprite that implements this is read and written through these methods
	instead; anything else still goes through reflection. Results must match
	what Reflect.getProperty / Reflect.setProperty would see on the same sprite:
	return NaN for a value the sprite does not have (the renderer then uses the
	same fallback it uses for a missing field), and ignore writes to one.
**/
interface NightmareVisionModchartLiveSprite {
	function modchartLiveFloat(field:Int):Float;
	function modchartLiveBool(field:Int):Bool;
	function modchartSetLiveFloat(field:Int, value:Float):Void;
	/** Calls one of the no-argument sprite methods in NightmareVisionModchartLiveField. */
	function modchartLiveCall(method:Int):Void;
}

/** Field and method ids for NightmareVisionModchartLiveSprite. */
class NightmareVisionModchartLiveField {
	public static inline var X:Int = 0;
	public static inline var Y:Int = 1;
	public static inline var WIDTH:Int = 2;
	public static inline var HEIGHT:Int = 3;
	public static inline var FRAME_HEIGHT:Int = 4;
	public static inline var ANGLE:Int = 5;
	public static inline var M_ANGLE:Int = 6;
	public static inline var SCALE_X:Int = 7;
	public static inline var SCALE_Y:Int = 8;
	/** `baseScale`, or `defScale` when a sprite has no baseScale. */
	public static inline var BASE_SCALE_X:Int = 9;
	public static inline var BASE_SCALE_Y:Int = 10;
	public static inline var MULT_SPEED:Int = 11;
	public static inline var STRUM_TIME:Int = 12;
	public static inline var SUSTAIN_LENGTH:Int = 13;
	/** The sprite's own `offsetX`/`offsetY` numbers, not Flixel's offset point. */
	public static inline var OFFSET_X:Int = 14;
	public static inline var OFFSET_Y:Int = 15;
	public static inline var TYPE_OFFSET_X:Int = 16;
	public static inline var TYPE_OFFSET_Y:Int = 17;
	public static inline var ALPHA_MOD:Int = 18;
	/** `rgbGraphics.flash` and `rgbGraphics.alpha`; NaN without rgbGraphics. */
	public static inline var RGB_FLASH:Int = 19;
	public static inline var RGB_ALPHA:Int = 20;

	public static inline var ACTIVE:Int = 0;
	public static inline var WAS_GOOD_HIT:Int = 1;

	public static inline var UPDATE_HITBOX:Int = 0;
	public static inline var CENTER_ORIGIN:Int = 1;
	public static inline var CENTER_OFFSETS:Int = 2;
}
