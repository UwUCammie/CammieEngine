package;

import flixel.util.FlxSort;

/**
	The source SortUtil comparators. zIndex goes through the same owner-aware
	view refreshZ uses, so sorting a group by it agrees with the engine's order.
*/
@:keep
class NightmareVisionSortUtil {
	public static function sortByZ(order:Int, a:Dynamic, b:Dynamic):Int {
		if (a == null || b == null) return 0;
		return FlxSort.byValues(order, number(HxcCompatRuntime.getZIndex(a)), number(HxcCompatRuntime.getZIndex(b)));
	}

	public static function sortByStrumTime(a:Dynamic, b:Dynamic):Int return byField(a, b, 'strumTime');
	public static function sortByTime(a:Dynamic, b:Dynamic):Int return byField(a, b, 'strumTime');
	public static function svSort(a:Dynamic, b:Dynamic):Int return byField(a, b, 'startTime');
	public static function idxSort(a:Dynamic, b:Dynamic):Int return byField(a, b, 'idx');
	public static function laserSort(a:Float, b:Float):Int return FlxSort.byValues(FlxSort.ASCENDING, a, b);

	static function byField(a:Dynamic, b:Dynamic, field:String):Int {
		if (a == null || b == null) return 0;
		return FlxSort.byValues(FlxSort.ASCENDING, number(Reflect.getProperty(a, field)), number(Reflect.getProperty(b, field)));
	}

	static function number(value:Dynamic):Float {
		if (value == null) return 0;
		var parsed:Float = Std.isOfType(value, Float) || Std.isOfType(value, Int) ? value : Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? 0 : parsed;
	}
}
