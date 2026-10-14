package;

/**
	Remembers asset ids that did not resolve on disk, so the next probe for the
	same id skips the case-insensitive directory walk.

	A remembered miss is never trusted on its own. The caller still asks the
	filesystem whether the exact spelling exists now, so a file written with the
	requested name is found straight away. Only a file that appears under a
	different letter case can be missed, and only until the epoch moves or the
	entry ages out.
**/
class DiskPathMissCache {
	/** Seconds a miss is remembered. Short on purpose: files can be written by
		code that never tells the asset layer. */
	public static inline var LIFETIME_SECONDS:Float = 2.0;
	/** A probe storm over unique ids must not grow the map without bound. */
	public static inline var MAX_ENTRIES:Int = 4096;
	final misses:Map<String, String> = new Map();
	var epoch:Int = 0;
	var startedAt:Float = 0;
	var entryCount:Int = 0;

	public function new() {}

	inline function refresh(epoch:Int, now:Float):Void {
		if (entryCount > 0 && (epoch != this.epoch || now - startedAt > LIFETIME_SECONDS || now < startedAt))
			clear();
		this.epoch = epoch;
	}

	/** The absolute path remembered for a missed id, or null when nothing is
		known about it. */
	public function missedAt(id:String, epoch:Int, now:Float):Null<String> {
		refresh(epoch, now);
		return entryCount == 0 ? null : misses.get(id);
	}

	public function remember(id:String, absolute:String, epoch:Int, now:Float):Void {
		if (id == null || absolute == null)
			return;
		refresh(epoch, now);
		if (entryCount >= MAX_ENTRIES)
			clear();
		if (entryCount == 0)
			startedAt = now;
		if (!misses.exists(id))
			entryCount++;
		misses.set(id, absolute);
	}

	public function forget(id:String):Void {
		if (misses.remove(id))
			entryCount--;
	}

	public function clear():Void {
		misses.clear();
		entryCount = 0;
	}

	public function count():Int return entryCount;
}
