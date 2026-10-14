package;

/**
	The one place that talks to the garbage collector.

	A full collection stops the game for tens of milliseconds on a big heap.
	Left alone it lands wherever the allocation budget happens to run out,
	often mid-song. Asking for one at moments where nothing is animating
	(loading handoff, pause menu opening) spends that pause where it is not
	seen and pushes the next automatic one further away.
**/
class EngineMemory {
	/** Collections asked for closer together than this are skipped, so
		mashing pause does not stack pauses. */
	public static inline var MIN_SECONDS_BETWEEN_COLLECTS:Float = 8.0;

	/** Replaceable for tests. `major` asks for a full collection. */
	public static var collector:Bool->Void = nativeCollect;
	public static var clock:Void->Float = haxe.Timer.stamp;
	/** Replaceable for tests: (minimum free megabytes, target free percent). */
	public static var tuner:Int->Int->Void = nativeTune;
	/** The collector takes its minimum free space as a 32 bit byte count, so
		anything from 2048 MB up would wrap around to a tiny or negative size. */
	public static inline var MAX_MIN_FREE_MB:Int = 1024;

	public static var collectCount(default, null):Int = 0;
	public static var lastCollectSeconds(default, null):Float = 0;
	public static var lastReason(default, null):String = '';
	static var lastCollectAt:Float = Math.NEGATIVE_INFINITY;
	static var tuned:Bool = false;

	/**
		Run a collection now. Only call this from a point where a pause cannot
		be seen or felt; never from a per-frame path. Returns false when it was
		skipped because another one ran moments ago.
	**/
	public static function collectNow(major:Bool = true, reason:String = '', force:Bool = false):Bool {
		var now = clock();
		if (!force && now - lastCollectAt < MIN_SECONDS_BETWEEN_COLLECTS)
			return false;
		collector(major);
		var finished = clock();
		lastCollectSeconds = finished - now;
		lastCollectAt = finished;
		lastReason = reason;
		collectCount++;
		return true;
	}

	/**
		Read optional collector tuning from the launch arguments, once.
		`--gc-min-free-mb=N` and `--gc-free-percent=N` are off unless given, so
		the shipped defaults stay as they are until a setting has been measured.
	**/
	public static function applyStartupTuning(args:Array<String>):Bool {
		if (tuned || args == null)
			return false;
		tuned = true;
		var minFreeMb = argumentInt(args, '--gc-min-free-mb=', 0, MAX_MIN_FREE_MB);
		var freePercent = argumentInt(args, '--gc-free-percent=', 0, 400);
		if (minFreeMb <= 0 && freePercent <= 0)
			return false;
		tuner(minFreeMb, freePercent);
		return true;
	}

	public static function argumentInt(args:Array<String>, prefix:String, fallback:Int, maximum:Int):Int {
		for (arg in args) {
			if (arg == null || !StringTools.startsWith(arg, prefix))
				continue;
			var value = Std.parseInt(arg.substr(prefix.length));
			if (value == null || value < 0)
				return fallback;
			return value > maximum ? maximum : value;
		}
		return fallback;
	}

	/** Managed bytes in use right now, or 0 where the target cannot tell. */
	public static function usedBytes():Float {
		#if cpp
		return cpp.vm.Gc.memInfo64(cpp.vm.Gc.MEM_INFO_USAGE);
		#else
		return 0;
		#end
	}

	public static function reservedBytes():Float {
		#if cpp
		return cpp.vm.Gc.memInfo64(cpp.vm.Gc.MEM_INFO_RESERVED);
		#else
		return 0;
		#end
	}

	/** Time one forced full collection. Diagnostics only. */
	public static function probe():{seconds:Float, usedBefore:Float, usedAfter:Float, reservedAfter:Float} {
		var before = usedBytes();
		collectNow(true, 'probe', true);
		return {seconds: lastCollectSeconds, usedBefore: before, usedAfter: usedBytes(), reservedAfter: reservedBytes()};
	}

	/** Test hook: forget the last collection and the applied tuning. */
	public static function reset():Void {
		lastCollectAt = Math.NEGATIVE_INFINITY;
		lastCollectSeconds = 0;
		lastReason = '';
		collectCount = 0;
		tuned = false;
	}

	static function nativeCollect(major:Bool):Void {
		#if cpp
		cpp.vm.Gc.run(major);
		#end
	}

	static function nativeTune(minFreeMb:Int, freePercent:Int):Void {
		#if cpp
		if (minFreeMb > 0)
			cpp.vm.Gc.setMinimumFreeSpace(minFreeMb * 1024 * 1024);
		if (freePercent > 0)
			cpp.vm.Gc.setTargetFreeSpacePercentage(freePercent);
		#end
	}
}
