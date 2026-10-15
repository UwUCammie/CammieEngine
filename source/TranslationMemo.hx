package;

/**
	Remembers script translations (HxcCompat.analyze, LuaCompat.translate) so
	the same script is translated once.

	A song load analyzes each HXC script at several places (stage, module and
	timeline setup), and every restart translates all of a song's HXC and Lua
	scripts again. One translation of a large script costs tens of
	milliseconds, plus a full HScript parse of the output for HXC. A caller only
	stores a result that depends on nothing but the source text and the key it
	passes (path plus any options), so a repeat call can hand back a copy.

	Results are kept serialized: one string per script is a single large
	allocation the collector does not walk object by object, so the memo does
	not lengthen collections during a song, and unserializing gives every
	caller its own fresh copy to modify.

	Unserialized arrays are always Array<Dynamic>. On native, reading one
	through a field typed Array<String> (or Int, Float, Bool) converts it into
	a new array on each read, so pushing into such a field of the copy is
	lost. Arrays of objects are unaffected. A caller that edits a basic-typed
	array of its copy rebuilds it typed first, as LuaCompat.translate does.
**/
class TranslationMemo {
	/** Source characters kept before the memo starts over. A song's scripts
		fit many times over; an import that analyzes a whole library just
		cycles through it. */
	public static inline var MAX_SOURCE_CHARS:Int = 4 * 1024 * 1024;

	static var entries:Map<String, TranslationMemoEntry> = new Map();
	static var heldChars:Int = 0;
	public static var hits(default, null):Int = 0;
	public static var stores(default, null):Int = 0;
	#if target.threaded
	// Song loading and import workers translate on their own threads.
	static var lock:sys.thread.Mutex = new sys.thread.Mutex();
	#end

	static inline function keyFor(source:String, path:String):String
		return (path == null ? '' : path) + '\n' + source.length;

	/** A fresh copy of the remembered result, or null when there is none. */
	public static function lookup(source:String, path:String):Dynamic {
		if (source == null)
			return null;
		var serialized:String = null;
		#if target.threaded lock.acquire(); #end
		var entry = entries.get(keyFor(source, path));
		// The key only narrows the search; the whole text must match.
		if (entry != null && entry.source == source) {
			serialized = entry.serialized;
			hits++;
		}
		#if target.threaded lock.release(); #end
		if (serialized == null)
			return null;
		try {
			return new haxe.Unserializer(serialized).unserialize();
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Remember `result` for this source and path. A result that does not
		serialize is simply not remembered. */
	public static function store(source:String, path:String, result:Dynamic):Bool {
		if (source == null || result == null || source.length > MAX_SOURCE_CHARS)
			return false;
		var serialized:String;
		try {
			var serializer = new haxe.Serializer();
			serializer.serialize(result);
			serialized = serializer.toString();
		} catch (_:Dynamic) {
			return false;
		}
		#if target.threaded lock.acquire(); #end
		var key = keyFor(source, path);
		var previous = entries.get(key);
		if (previous != null)
			heldChars -= previous.source.length;
		if (heldChars + source.length > MAX_SOURCE_CHARS) {
			entries = new Map();
			heldChars = 0;
		}
		entries.set(key, {source: source, serialized: serialized});
		heldChars += source.length;
		stores++;
		#if target.threaded lock.release(); #end
		return true;
	}

	/** Forget everything, for tests and memory pressure. */
	public static function clear():Void {
		#if target.threaded lock.acquire(); #end
		entries = new Map();
		heldChars = 0;
		hits = 0;
		stores = 0;
		#if target.threaded lock.release(); #end
	}
}

private typedef TranslationMemoEntry = {
	var source:String;
	var serialized:String;
}
