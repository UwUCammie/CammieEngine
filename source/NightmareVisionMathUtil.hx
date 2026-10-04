package;

/** Source arithmetic helpers kept distinct from rounded score formatting. */
@:keep
class NightmareVisionMathUtil {
	public static inline function logBase(base:Float, value:Float):Float return SourceScriptMath.logBase(base, value);
	public static inline function scale(x:Float, low1:Float, high1:Float, low2:Float, high2:Float):Float
		return SourceScriptMath.scale(x, low1, high1, low2, high2);
	public static inline function clamp(value:Float, low:Float, high:Float):Float return SourceScriptMath.clamp(value, low, high);
	public static function rotate(x:Float, y:Float, angle:Float, ?point:flixel.math.FlxPoint):flixel.math.FlxPoint
		return SourceScriptMath.rotate(x, y, angle, point);
	public static inline function quantizeAlpha(value:Float, interval:Float):Float return SourceScriptMath.quantizeAlpha(value, interval);
	public static inline function quantize(value:Float, interval:Float):Float return SourceScriptMath.quantize(value, interval);
	public static inline function fpsLerp(start:Float, end:Float, ratio:Float):Float return SourceScriptMath.fpsLerp(start, end, ratio);
	public static inline function decayLerp(a:Float, b:Float, decay:Float, elapsed:Float):Float
		return SourceScriptMath.decayLerp(a, b, decay, elapsed);
	public static inline function wrap(value:Float, minimum:Float, maximum:Float):Float
		return SourceScriptMath.wrap(value, minimum, maximum);
	public static inline function euclideanMod(value:Float, divisor:Float):Float
		return SourceScriptMath.euclideanMod(value, divisor);
	public static inline function floorDecimal(value:Float, decimals:Int):Float return SourceScriptMath.floorDecimal(value, decimals);
	public static inline function numberArray(?minimum:Int, maximum:Int):Array<Int>
		return SourceScriptMath.numberArray(minimum, maximum);
	public static inline function fastTan(radians:Float):Float return SourceScriptMath.fastTan(radians);
}
