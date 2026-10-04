package;

import flixel.FlxG;
import flixel.math.FlxMath;
import flixel.math.FlxRandom;
import flixel.util.FlxColor;

/** Nightmare Vision's ScriptedFlxRandom call surface over the native RNG.
 * Static helpers and instance methods deliberately match the donor wrapper. */
@:keep
@:access(flixel.math.FlxRandom)
class NightmareVisionSourceRandom {
	public static inline function resetInitialSeed():Int {
		var seed = FlxRandom.rangeBound(Std.int(Math.random() * FlxMath.MAX_VALUE_INT));
		return FlxG.random.initialSeed = seed;
	}

	public function int(min:Int = 0, max:Int = FlxMath.MAX_VALUE_INT, ?excludes:Array<Int>):Int
		return FlxG.random.int(min, max, excludes);

	public static function float(min:Float = 0, max:Float = 1, ?excludes:Array<Float>):Float
		return FlxG.random.float(min, max, excludes);

	public function floatNormal(mean:Float = 0, stdDev:Float = 1):Float
		return FlxG.random.floatNormal(mean, stdDev);

	public static inline function bool(chance:Float = 50):Bool return float(0, 100) < chance;
	public static inline function sign(chance:Float = 50):Int return bool(chance) ? 1 : -1;

	public static function weightedPick(weights:Array<Float>):Int return FlxG.random.weightedPick(weights);

	public static function getObject<T>(objects:Array<T>, ?weights:Array<Float>, startIndex:Int = 0,
		?endIndex:Null<Int>):Null<T> {
		var selected:Null<T> = null;
		if (objects.length != 0) {
		if (weights == null) weights = [for (_ in objects) 1.0];
		if (endIndex == null) endIndex = objects.length - 1;
		startIndex = Std.int(FlxMath.bound(startIndex, 0, objects.length - 1));
		endIndex = Std.int(FlxMath.bound(endIndex, 0, objects.length - 1));
		if (endIndex < startIndex) {
			var swap = startIndex;
			startIndex = endIndex;
			endIndex = swap;
		}
		if (endIndex > weights.length - 1) endIndex = weights.length - 1;
		var rangeWeights = [for (index in startIndex...endIndex + 1) weights[index]];
		selected = objects[startIndex + weightedPick(rangeWeights)];
		}
		return selected;
	}

	public static function shuffle<T>(values:Array<T>):Void {
		if (values == null) return;
		var maxIndex = values.length - 1;
		for (index in 0...maxIndex) {
			var selected = FlxG.random.int(index, maxIndex);
			var prior = values[index];
			values[index] = values[selected];
			values[selected] = prior;
		}
	}

	public static function color(?min:FlxColor, ?max:FlxColor, ?alpha:Int,
		greyScale:Bool = false):FlxColor
		return FlxG.random.color(min, max, alpha, greyScale);
}
