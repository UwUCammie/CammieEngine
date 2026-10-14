package;

import haxe.io.Path;

/**
	Path-keyed store for decoded sounds read from disk. It never closes a
	sound it drops: channels and callers that still hold one keep it alive, so
	clearing is always safe and only costs a later decode.
**/
class DiskSoundCache<T> {
	/** Files above this size are only kept when a caller asks for them by name.
		Song tracks and previews would otherwise pin tens of megabytes each. */
	public static inline var AUTO_KEEP_MAX_FILE_BYTES:Int = 512 * 1024;
	/** Encoded bytes retained before the whole store is dropped. Decoded audio
		is roughly ten times larger, so this stays small. */
	public static inline var MAX_RETAINED_FILE_BYTES:Float = 8.0 * 1024 * 1024;

	final entries:Map<String, T> = new Map();
	var retainedBytes:Float = 0;
	var epoch:Int = 0;
	var entryCount:Int = 0;

	public function new() {}

	public static function key(path:String):String {
		return path == null ? '' : Path.normalize(StringTools.trim(path));
	}

	/**
		`epoch` is any counter that moves when files on disk may have changed.
		`pin` keeps the result whatever its size (an explicit precache).
		`useCache` false always decodes and leaves the store untouched.
	**/
	public function getOrLoad(path:String, useCache:Bool, epoch:Int, fileBytes:Void->Float,
			load:Void->T, pin:Bool = false):T {
		if (!useCache)
			return load();
		if (epoch != this.epoch) {
			clear();
			this.epoch = epoch;
		}
		var id = key(path);
		var cached = entries.get(id);
		if (cached != null)
			return cached;
		var loaded = load();
		if (loaded == null)
			return null;
		var size = 0.0;
		try size = fileBytes() catch (_:Dynamic) size = AUTO_KEEP_MAX_FILE_BYTES + 1;
		if (!pin && size > AUTO_KEEP_MAX_FILE_BYTES)
			return loaded;
		if (retainedBytes + size > MAX_RETAINED_FILE_BYTES)
			clear();
		entries.set(id, loaded);
		retainedBytes += size;
		entryCount++;
		return loaded;
	}

	public function peek(path:String, epoch:Int):Null<T> {
		return epoch != this.epoch ? null : entries.get(key(path));
	}

	public function clear():Void {
		entries.clear();
		retainedBytes = 0;
		entryCount = 0;
	}

	public function count():Int return entryCount;
}
