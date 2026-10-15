package;

/**
	Compiled regular expressions shared by the script translators.

	`new EReg(...)` compiles its pattern every time it runs, and the HXC and Lua
	translators run hundreds of fixed rewrite passes over every method body. A
	V-Slice pack spent most of its translation time compiling the same few
	hundred patterns tens of thousands of times, and left them all for the
	collector afterwards. `get` compiles each pattern once per thread instead.

	An EReg keeps the state of its last match, so a cached one is only safe
	where nothing reads that state after another use of the same pattern could
	have run. Use it for a direct `replace`, `split` or a `match` whose result is
	only tested, never for a `match` followed by `matched`/`matchedPos` across
	other calls, and never for `map` (its callback could reuse the pattern).
	Each thread has its own table because a match on one thread would overwrite
	a match running on another (song loading and import workers translate at the
	same time).
**/
class RegexCache {
	/** Patterns built from script names can grow without bound; start over past this. */
	public static inline var MAX_PATTERNS:Int = 4096;

	#if target.threaded
	static var tables:sys.thread.Tls<RegexCacheTable> = new sys.thread.Tls();
	#else
	static var table:RegexCacheTable;
	#end

	/** The compiled pattern for `pattern` and `flags`, reused on this thread. */
	public static function get(pattern:String, flags:String):EReg {
		var cache = current();
		var key = flags + '/' + pattern;
		var found = cache.patterns.get(key);
		if (found != null)
			return found;
		if (cache.count >= MAX_PATTERNS) {
			cache.patterns = new Map();
			cache.count = 0;
		}
		found = new EReg(pattern, flags);
		cache.patterns.set(key, found);
		cache.count++;
		cache.compiled++;
		return found;
	}

	/** Patterns compiled on this thread so far (for tests and diagnostics). */
	public static function compiledOnThisThread():Int {
		return current().compiled;
	}

	static function current():RegexCacheTable {
		#if target.threaded
		var cache = tables.value;
		if (cache == null) {
			cache = new RegexCacheTable();
			tables.value = cache;
		}
		return cache;
		#else
		if (table == null)
			table = new RegexCacheTable();
		return table;
		#end
	}
}

private class RegexCacheTable {
	public var patterns:Map<String, EReg> = new Map();
	public var count:Int = 0;
	public var compiled:Int = 0;

	public function new() {}
}
