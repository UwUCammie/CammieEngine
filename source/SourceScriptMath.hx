package;

/** Shared source-compatible arithmetic used by imported HScript engines. */
@:keep
class SourceScriptMath {
	public static inline function logBase(base:Float, value:Float):Float
		return Math.log(value) / Math.log(base);

	public static inline function scale(x:Float, low1:Float, high1:Float, low2:Float, high2:Float):Float
		return (x - low1) * (high2 - low2) / (high1 - low1) + low2;

	public static inline function clamp(value:Float, low:Float, high:Float):Float
		return value > high ? high : value < low ? low : value;

	public static function rotate(x:Float, y:Float, angle:Float, ?point:flixel.math.FlxPoint):flixel.math.FlxPoint {
		var result = point == null ? flixel.math.FlxPoint.weak() : point;
		return result.set(x * Math.cos(angle) - y * Math.sin(angle), x * Math.sin(angle) + y * Math.cos(angle));
	}

	public static inline function quantizeAlpha(value:Float, interval:Float):Float
		return Std.int((value + interval / 2) / interval) * interval;

	public static inline function quantize(value:Float, interval:Float):Float
		return Std.int((value + interval / 2) / interval) * interval;

	public static inline function fpsLerp(start:Float, end:Float, ratio:Float):Float
		return flixel.math.FlxMath.lerp(start, end,
			flixel.math.FlxMath.getElapsedLerp(ratio, flixel.FlxG.elapsed));

	public static inline function decayLerp(a:Float, b:Float, decay:Float, elapsed:Float):Float
		return b + (a - b) * Math.exp(-decay * elapsed);

	public static inline function wrap(value:Float, minimum:Float, maximum:Float):Float
		return euclideanMod(value - minimum, maximum - minimum + 1) + minimum;

	public static inline function euclideanMod(value:Float, divisor:Float):Float {
		var result = value % divisor;
		return result < 0 ? result + Math.abs(divisor) : result;
	}

	public static function floorDecimal(value:Float, decimals:Int):Float {
		if (decimals < 1) return Math.floor(value);
		var multiplier:Float = 1;
		for (index in 0...decimals) multiplier *= 10;
		return Math.floor(value * multiplier) / multiplier;
	}

	public static inline function numberArray(?minimum:Int, maximum:Int):Array<Int> {
		var start = minimum == null ? 0 : minimum;
		return [for (index in start...maximum) index];
	}

	public static inline function fastTan(radians:Float):Float
		return flixel.math.FlxMath.fastSin(radians) / flixel.math.FlxMath.fastCos(radians);
}
