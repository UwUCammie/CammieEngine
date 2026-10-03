/** Audio and animation actions owned by the native game-over host. */
typedef HxcDeathQuotePlaybackActions = {
	var startLoopMusic:Float->Void;
	var playDeathLoop:Void->Void;
	var playQuote:(String, Void->Void)->Dynamic;
	var canFadeLoopMusic:Void->Bool;
	var fadeLoopMusic:(Float, Float, Float)->Void;
	var stopQuote:Dynamic->Void;
}

/**
	Coordinates the V-Slice death-quote sequence without owning Flixel objects.
	The host supplies native audio/animation actions and calls start() only as
	part of its game-over update. A missing quote leaves the host's normal music
	path untouched.
*/
class HxcDeathQuotePlayback {
	public static inline var QUOTE_MUSIC_VOLUME:Float = 0.2;
	public static inline var MUSIC_FADE_SECONDS:Float = 4.0;
	public static inline var MUSIC_FADE_TARGET:Float = 1.0;

	public var isActive(default, null):Bool = true;
	public var hasStarted(default, null):Bool = false;
	public var hasCompleted(default, null):Bool = false;

	final actions:HxcDeathQuotePlaybackActions;
	var quoteHandle:Dynamic = null;
	var generation:Int = 0;

	public function new(actions:HxcDeathQuotePlaybackActions) {
		this.actions = actions;
	}

	/**
		Start once, and only after firstDeath has finished. Returns true when the
		quote sequence took ownership of this game-over ending; false leaves the
		native no-quote music behavior available to the caller.
	*/
	public function start(firstDeathFinished:Bool, quote:Null<String>):Bool {
		if (!isActive || hasStarted || !firstDeathFinished || quote == null)
			return false;

		hasStarted = true;
		var token = generation;
		actions.startLoopMusic(QUOTE_MUSIC_VOLUME);
		if (!isCurrent(token))
			return true;
		actions.playDeathLoop();
		if (!isCurrent(token))
			return true;

		var handle = actions.playQuote(quote, function() completeQuote(token));
		if (!isCurrent(token)) {
			// A reentrant host cancellation can occur while playQuote is creating
			// its handle. Stop that late handle as well as invalidating its callback.
			if (handle != null)
				actions.stopQuote(handle);
		} else if (!hasCompleted) {
			quoteHandle = handle;
		}
		return true;
	}

	/** Stop the quote and invalidate any completion callback still in flight. */
	public function cancel():Void {
		if (!isActive)
			return;
		isActive = false;
		generation++;
		var handle = quoteHandle;
		quoteHandle = null;
		if (handle != null)
			actions.stopQuote(handle);
	}

	/** Release this controller when its owning game-over substate is destroyed. */
	public function destroy():Void {
		cancel();
	}

	function completeQuote(token:Int):Void {
		if (!isCurrent(token) || hasCompleted)
			return;
		hasCompleted = true;
		quoteHandle = null;
		// V-Slice checks both conditions at callback time: the ending must still
		// be active and the game-over music handle must still exist.
		if (actions.canFadeLoopMusic())
			actions.fadeLoopMusic(MUSIC_FADE_SECONDS, QUOTE_MUSIC_VOLUME, MUSIC_FADE_TARGET);
	}

	inline function isCurrent(token:Int):Bool {
		return isActive && token == generation;
	}
}
