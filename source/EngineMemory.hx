package;

/**
	The one place that talks to the garbage collector.

	A full collection stops the game for tens of milliseconds on a big heap.
	Left alone it lands wherever the allocation budget happens to run out,
	often mid-song. Asking for one at moments where nothing is animating
	(loading handoff, pause menu opening) spends that pause where it is not
	seen and pushes the next automatic one further away.

	hxcpp also reads HXCPP_MINIMUM_FREE_SPACE (bytes), HXCPP_TARGET_FREE_SPACE
	(percent) and HXCPP_MINIMUM_WORKING_MEMORY (bytes) from the environment at
	startup, so collector settings can be tried without a rebuild. A build with
	-D HXCPP_GC_SUMMARY prints a summary of every collection.
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

	/** Minimum free space kept while a song plays. The collector's own trigger
		is relative to the live small-object heap, so a trimmed heap would
		otherwise collect more often mid-song. Applied before the loading handoff
		collection, which is the one that turns it into the next trigger point.

		Each collection stops the game for a time set mostly by the live
		small-object heap (about 35 to 45 ms for a song keeping 100 MB of small
		objects), plus a part that grows with this headroom. Measured over
		90 s on three heavy songs with the same build, longest collection frame
		per run: 192 MB 38 to 46 ms, 256 MB 38 to 47 ms, 384 MB 42 to 47 ms,
		512 MB 47 to 58 ms. Only 512 MB pushed collections past 50 ms (a third
		dropped frame); halving the headroom roughly doubles how often they
		happen. 256 MB keeps every collection under 50 ms with the fewest
		collections that do. */
	public static inline var SONG_MIN_FREE_MB:Int = 256;
	/** Used instead with Low Memory Mode on: about 65 MB less reserved than
		the normal value, slightly shorter pauses, about a quarter more of them. */
	public static inline var LOW_MEMORY_SONG_MIN_FREE_MB:Int = 192;
	/**
		Live small-object heap, measured right after the loading handoff
		collection, from which every collection is over 50 ms whatever the
		headroom. Pause length is set mostly by how many small objects are
		marked, about 0.3 ms per MB: songs keeping 105 to 165 MB of small
		objects paused 35 to 47 ms at 256 MB headroom, one keeping about 198 MB
		paused 61 ms and one keeping about 223 MB paused 60 to 73 ms.
	**/
	public static inline var HEAVY_SMALL_HEAP_MB:Int = 180;
	/** Headroom for a song over HEAVY_SMALL_HEAP_MB. Its pauses drop frames at
		any headroom, so fewer of them drops fewer frames overall. On the 223 MB
		song, two 90 s runs each: 256 MB gave 5 collections and 6 to 7 frames
		over 50 ms, 512 MB 2 collections (69 to 84 ms) and 3 frames, 768 MB 2
		collections and 4 frames. */
	public static inline var HEAVY_SONG_MIN_FREE_MB:Int = 512;
	/** hxcpp's desktop default for the minimum free space, restored after a
		song. Only used when nobody tuned it, so it is always the value in force
		before the song started. */
	public static inline var DEFAULT_MIN_FREE_MB:Int = 10;
	/** Replaceable for tests: reads an environment variable, or null. */
	public static var environment:String->Null<String> = readEnvironment;

	/**
		Script source translated between two collections. Translating one script
		file compiles thousands of short-lived regular expressions, and hxcpp frees
		dead regular expressions in time that grows with the square of how many
		die in one collection: measured in a bare hxcpp program, 20 000 took 0.17 s
		and 100 000 took 15 s. A song with dozens of large V-Slice scripts reached
		that size and froze its loading screen for about 45 s, so collect after
		every few files instead of letting them pile up.

		The budget was 8 KB while HXC translation compiled about 1200 patterns
		per KB (about 10 000 dead per collection). RegexCache now keeps the
		fixed patterns, leaving about 90 per KB for HXC and 55 per KB for Lua,
		so 64 KB still frees fewer per collection than before (about 6000) with
		an eighth of the collections, each of which walks the whole heap.
	**/
	public static inline var TRANSLATION_COLLECT_CHARS:Int = 65536;

	public static var collectCount(default, null):Int = 0;
	public static var translationCollects(default, null):Int = 0;
	static var translatedChars:Int = 0;
	public static var lastCollectSeconds(default, null):Float = 0;
	public static var lastReason(default, null):String = '';
	static var lastCollectAt:Float = Math.NEGATIVE_INFINITY;
	static var tuned:Bool = false;
	/** Minimum free space given on the command line; it wins over the song value. */
	static var explicitMinFreeMb:Int = 0;
	/** `--gc-song-min-free-mb=N` overrides the song value; 0 turns it off for A/B runs. */
	static var songMinFreeMb:Int = SONG_MIN_FREE_MB;
	/** True when `--gc-song-min-free-mb` set songMinFreeMb, which then also wins over Low Memory Mode. */
	static var songMinFreeFromArguments:Bool = false;
	/** Low Memory Mode keeps its smaller headroom even for a heavy song. */
	static var songLowMemory:Bool = false;
	static var songOwner:Dynamic = null;
	static var songTuned:Bool = false;
	/** The headroom is looked at again once per song, after its first full
		collection (the loading handoff), when the live heap is known. */
	static var songHeadroomChecked:Bool = true;
	/** Replaceable for tests: live bytes in small objects right now. */
	public static var smallBytesProvider:Void->Float = nativeSmallBytes;
	public static var heavySong(default, null):Bool = false;

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
		// A full collection also frees the dead translation patterns, so the
		// translation budget starts over. Without this, the loading handoff
		// collection left the count from loading in place and a script added
		// mid-song could cross the budget and collect during play.
		if (major)
			translatedChars = 0;
		if (major && !songHeadroomChecked)
			checkSongHeadroom();
		var finished = clock();
		lastCollectSeconds = finished - now;
		lastCollectAt = finished;
		lastReason = reason;
		collectCount++;
		return true;
	}

	/**
		After the song's first full collection the small-object heap is close to
		what the song keeps. When it is so large that every collection would pass
		50 ms anyway, raise the headroom so there are fewer of them, and collect
		once more right away: the collector only reads a new minimum when a
		collection ends, and this one still sits under the loading overlay.

		A heap over the line is collected once more before deciding. Right after
		loading, one collection leaves objects that only the next one frees: a
		song read over 180 MB after one and 153 MB after two, and taking the
		first reading raised its headroom, which made each of its pauses 53 to
		57 ms instead of 46 to 50 ms.
	**/
	static function checkSongHeadroom():Void {
		songHeadroomChecked = true;
		if (!songTuned || songMinFreeFromArguments || songLowMemory)
			return;
		var heavyBytes = HEAVY_SMALL_HEAP_MB * 1024.0 * 1024.0;
		if (smallBytesProvider() < heavyBytes) {
			// A song that took over from a heavy one is lighter: put the normal
			// headroom back so its pauses are not lengthened for nothing.
			if (heavySong) {
				heavySong = false;
				tuner(songMinFreeMb, 0);
			}
			return;
		}
		// Already raised by the song this one took over from; keep it without
		// spending more collections confirming it.
		if (heavySong)
			return;
		collector(true);
		if (smallBytesProvider() < heavyBytes)
			return;
		heavySong = true;
		tuner(HEAVY_SONG_MIN_FREE_MB, 0);
		collector(true);
	}

	static function nativeSmallBytes():Float {
		var used = usedBytes();
		var large = largeBytes();
		return used > large ? used - large : 0;
	}

	/**
		Count one translated script and collect once enough has been translated.
		Runs on whichever thread translated (song loading or an import worker).
		It does not touch the pause and handoff spacing, so it never cancels one
		of those. Returns true when it collected.
	**/
	public static function scriptTranslated(sourceChars:Int):Bool {
		if (sourceChars <= 0)
			return false;
		translatedChars += sourceChars;
		if (translatedChars < TRANSLATION_COLLECT_CHARS)
			return false;
		translatedChars = 0;
		collector(false);
		translationCollects++;
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
		explicitMinFreeMb = minFreeMb;
		songMinFreeMb = argumentInt(args, '--gc-song-min-free-mb=', SONG_MIN_FREE_MB, MAX_MIN_FREE_MB);
		songMinFreeFromArguments = argumentInt(args, '--gc-song-min-free-mb=', -1, MAX_MIN_FREE_MB) >= 0;
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

	/**
		Raise the minimum free space for the song `owner` is playing. Call it
		when the song state is created, before the loading handoff collection.
		A minimum given on the command line or through HXCPP_MINIMUM_FREE_SPACE
		wins and is left alone. A new song state taking over from one that has
		not been torn down yet keeps the value already in force.
	**/
	public static function enterSong(owner:Dynamic, lowMemory:Bool = false):Bool {
		if (owner == null || songOwner == owner)
			return false;
		var alreadyActive = songOwner != null;
		songOwner = owner;
		// A retry or a script-loaded next song can be created before the old
		// state is destroyed. The value in force stays, but the new song may
		// keep a very different heap, so its first full collection looks again.
		if (alreadyActive && songTuned)
			songHeadroomChecked = false;
		if (alreadyActive || songTuned || !songTuningAllowed())
			return false;
		tuner(lowMemory && !songMinFreeFromArguments ? LOW_MEMORY_SONG_MIN_FREE_MB : songMinFreeMb, 0);
		songTuned = true;
		songLowMemory = lowMemory;
		songHeadroomChecked = false;
		heavySong = false;
		return true;
	}

	/** Put the minimum free space back when the song that raised it ends. A
		stale state destroyed after its replacement started changes nothing. */
	public static function leaveSong(owner:Dynamic):Bool {
		if (owner == null || owner != songOwner)
			return false;
		songOwner = null;
		if (!songTuned)
			return false;
		songTuned = false;
		songHeadroomChecked = true;
		heavySong = false;
		tuner(DEFAULT_MIN_FREE_MB, 0);
		return true;
	}

	static function songTuningAllowed():Bool {
		if (songMinFreeMb <= 0 || explicitMinFreeMb > 0)
			return false;
		var fromEnvironment = environment('HXCPP_MINIMUM_FREE_SPACE');
		if (fromEnvironment != null) {
			var bytes = Std.parseInt(fromEnvironment);
			if (bytes != null && bytes > 0)
				return false;
		}
		return true;
	}

	static function readEnvironment(name:String):Null<String> {
		#if sys
		return Sys.getEnv(name);
		#else
		return null;
		#end
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

	/** Replaceable for tests: bytes held by large objects (over 4000 bytes each:
		bitmaps, decoded audio, big arrays and strings). */
	public static var largeBytesProvider:Void->Float = nativeLargeBytes;

	/**
		Bytes in large objects. These cost almost nothing to mark, so a heap that
		is mostly large bytes has short pauses; the rest of the heap is small
		objects, whose count is what makes a pause long.
	**/
	public static function largeBytes():Float
		return largeBytesProvider();

	static function nativeLargeBytes():Float {
		#if cpp
		return cpp.vm.Gc.memInfo64(cpp.vm.Gc.MEM_INFO_LARGE);
		#else
		return 0;
		#end
	}

	/** Time one forced full collection. Diagnostics only. */
	public static function probe():{seconds:Float, usedBefore:Float, usedAfter:Float, reservedAfter:Float,
		largeBefore:Float, largeAfter:Float} {
		var before = usedBytes();
		var largeBefore = largeBytes();
		collectNow(true, 'probe', true);
		return {seconds: lastCollectSeconds, usedBefore: before, usedAfter: usedBytes(), reservedAfter: reservedBytes(),
			largeBefore: largeBefore, largeAfter: largeBytes()};
	}

	/** Test hook: forget the last collection and the applied tuning. */
	public static function reset():Void {
		lastCollectAt = Math.NEGATIVE_INFINITY;
		lastCollectSeconds = 0;
		lastReason = '';
		collectCount = 0;
		translationCollects = 0;
		translatedChars = 0;
		tuned = false;
		explicitMinFreeMb = 0;
		songMinFreeMb = SONG_MIN_FREE_MB;
		songMinFreeFromArguments = false;
		songOwner = null;
		songTuned = false;
		songLowMemory = false;
		songHeadroomChecked = true;
		heavySong = false;
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
