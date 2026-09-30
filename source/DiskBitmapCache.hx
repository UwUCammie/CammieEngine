package;

import haxe.io.Path;

/** Small injectable adapter for path-keyed native bitmap cache lookups. */
class DiskBitmapCache {
	/** Keep filesystem images in a separate key space from packaged Flx assets. */
	public static function key(path:String):String {
		var clean = path == null ? '' : Path.normalize(StringTools.trim(path));
		return 'fnfassets:disk-bitmap:' + clean;
	}

	/** Reuse cached values only when requested; false always loads fresh data. */
	public static function getOrLoad<T>(key:String, useCache:Bool,
		lookup:String->T, load:Void->T, store:String->T->T):T {
		if (useCache) {
			var cached = lookup(key);
			if (cached != null)
				return cached;
		}
		var loaded = load();
		return useCache && loaded != null ? store(key, loaded) : loaded;
	}
}
