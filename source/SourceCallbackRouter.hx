package;

/** One row of the routing table. Engine differences live here as data. */
class SourceCallbackRoute {
	/** Sinks in call order: 'nv', 'psych', 'hscript'. */
	public var order(default, null):Array<String>;
	public var nightmareVision(default, null):String;
	public var psych(default, null):String;
	public var psychFamily(default, null):String;
	public var psychIgnoreStops(default, null):Bool;
	/** Psych hears this event only when a Psych owner drives the song. */
	public var psychNeedsOwner(default, null):Bool;
	public var hscript(default, null):String;
	/** Only the first owning engine hears it (Nightmare Vision before Psych). */
	public var exclusive(default, null):Bool;

	public function new(order:Array<String>, ?nightmareVision:String, ?psych:String, psychFamily:String = 'Scripts',
		psychIgnoreStops:Bool = false, psychNeedsOwner:Bool = false, ?hscript:String, exclusive:Bool = false) {
		this.order = order;
		this.nightmareVision = nightmareVision;
		this.psych = psych;
		this.psychFamily = psychFamily;
		this.psychIgnoreStops = psychIgnoreStops;
		this.psychNeedsOwner = psychNeedsOwner;
		this.hscript = hscript;
		this.exclusive = exclusive;
	}
}

/**
 * One fan-out point for gameplay lifecycle callbacks that Nightmare Vision,
 * Psych and native HScript share. PlayState used to hand-write each site with
 * its own sentinel comparison and engine order; the table below keeps those
 * differences in one place so an engine cannot silently miss a callback at
 * one site while hearing it at another.
 *
 * Each engine keeps its own stop rule: Nightmare Vision stops on STOP_FUNC and
 * Psych on its STOP sentinel. A Psych script returning 1 is not a stop, and a
 * Nightmare Vision script returning the Psych string is not one either.
 */
class SourceCallbackRouter {
	static var routes:Map<String, SourceCallbackRoute>;

	var nightmareVisionOwns:Void->Bool;
	var psychOwns:Void->Bool;
	var callNightmareVision:(String, Array<Dynamic>) -> Dynamic;
	var callPsych:(String, Array<Dynamic>, String, Bool) -> Dynamic;
	var callHScript:(String, Array<Dynamic>) -> Void;

	/**
	 * nightmareVisionOwns: a Nightmare Vision owner drives this song.
	 * psychOwns: a Psych owner drives this song (only asked for owner-gated rows).
	 */
	public function new(nightmareVisionOwns:Void->Bool, psychOwns:Void->Bool,
		callNightmareVision:(String, Array<Dynamic>) -> Dynamic,
		callPsych:(String, Array<Dynamic>, String, Bool) -> Dynamic,
		callHScript:(String, Array<Dynamic>) -> Void) {
		this.nightmareVisionOwns = nightmareVisionOwns;
		this.psychOwns = psychOwns;
		this.callNightmareVision = callNightmareVision;
		this.callPsych = callPsych;
		this.callHScript = callHScript;
	}

	public static function route(event:SourceLifecycleEvent):SourceCallbackRoute {
		if (routes == null) routes = buildRoutes();
		return routes.get(event);
	}

	static function buildRoutes():Map<String, SourceCallbackRoute> {
		var table = new Map<String, SourceCallbackRoute>();
		// Gates. Psych sends its game over and rating gates to every family but
		// ignores a stop from one script for the rest of the broadcast.
		table.set(SourceLifecycleEvent.GameOver, new SourceCallbackRoute(['nv', 'psych'], 'onGameOver', 'onGameOver', 'Scripts', true,
			false, null, true));
		table.set(SourceLifecycleEvent.RecalculateRating, new SourceCallbackRoute(['nv', 'psych'], 'onRecalculateRating',
			'onRecalculateRating', 'Scripts', true, true, null, true));
		table.set(SourceLifecycleEvent.Pause, new SourceCallbackRoute(['nv'], 'onPause'));
		table.set(SourceLifecycleEvent.EndSong, new SourceCallbackRoute(['nv'], 'onEndSong'));
		// Nightmare Vision's score bar hook keeps the Psych callback name.
		table.set(SourceLifecycleEvent.UpdateScoreBar, new SourceCallbackRoute(['nv'], 'onUpdateScore'));
		table.set(SourceLifecycleEvent.PreUpdateScore, new SourceCallbackRoute(['psych'], null, 'preUpdateScore', 'Scripts', true));
		// Notifications. Psych is told before Nightmare Vision where both hear it.
		table.set(SourceLifecycleEvent.UpdateScore, new SourceCallbackRoute(['psych'], null, 'onUpdateScore'));
		table.set(SourceLifecycleEvent.CountdownStarted, new SourceCallbackRoute(['psych', 'nv'], 'onCountdownStarted', 'onCountdownStarted'));
		table.set(SourceLifecycleEvent.StartCountdownAgain, new SourceCallbackRoute(['psych', 'nv'], 'onStartCountdown', 'onStartCountdown'));
		table.set(SourceLifecycleEvent.CreatePost, new SourceCallbackRoute(['psych', 'nv'], 'onCreatePost', 'onCreatePost', 'Scripts', false, true));
		// Psych hears these through the native HScript name aliases.
		table.set(SourceLifecycleEvent.SongStart, new SourceCallbackRoute(['nv', 'hscript'], 'onSongStart', null, 'Scripts', false, false, 'songStart'));
		table.set(SourceLifecycleEvent.StepHit, new SourceCallbackRoute(['nv', 'hscript'], 'onStepHit', null, 'Scripts', false, false, 'stepHit'));
		return table;
	}

	/** Nightmare Vision's stop sentinel. */
	public static inline function nightmareVisionStops(value:Dynamic):Bool
		return value == NightmareVisionScriptGroup.STOP_FUNC;

	/** Psych's stop sentinel as the broadcast reports it. */
	public static inline function psychStops(value:Dynamic):Bool
		return value == ScriptCallbackResult.STOP;

	/** The single stop check for a value returned by the named sink. */
	public static function stops(sink:String, value:Dynamic):Bool {
		return switch (sink) {
			case 'nv': nightmareVisionStops(value);
			case 'psych': psychStops(value);
			default: false;
		}
	}

	/**
	 * Send one lifecycle event to every engine its row names, in the row's
	 * order. hscriptArgs replaces args for the native HScript sink, whose
	 * callbacks take the counters Nightmare Vision reads from the state.
	 */
	public function dispatch(event:SourceLifecycleEvent, args:Array<Dynamic>, ?hscriptArgs:Array<Dynamic>):SourceCallbackOutcome {
		var row = route(event);
		if (row == null) throw '[source-callbacks] no route for ' + event;
		if (row.exclusive) {
			if (row.nightmareVision != null && nightmareVisionOwns())
				return nightmareVisionStops(callNightmareVision(row.nightmareVision, args)) ? Stop : Continue;
			if (row.psych != null && (!row.psychNeedsOwner || psychOwns()))
				return psychStops(callPsych(row.psych, args, row.psychFamily, row.psychIgnoreStops)) ? Stop : Continue;
			return Unhandled;
		}
		var stopped = false;
		var shared = false;
		for (sink in row.order) {
			// Each sink gets its own argument array, as the separate literals at
			// the old call sites did, so one engine cannot see another's edits.
			// The copy is only made for a sink that actually hears the event,
			// since step hits come through here every step.
			switch (sink) {
				case 'nv':
					if (!nightmareVisionOwns()) continue;
					var sinkArgs = shared ? args.copy() : args;
					shared = true;
					if (nightmareVisionStops(callNightmareVision(row.nightmareVision, sinkArgs))) stopped = true;
				case 'psych':
					if (row.psychNeedsOwner && !psychOwns()) continue;
					var sinkArgs = shared ? args.copy() : args;
					shared = true;
					if (psychStops(callPsych(row.psych, sinkArgs, row.psychFamily, row.psychIgnoreStops))) stopped = true;
				case 'hscript':
					if (hscriptArgs != null) callHScript(row.hscript, hscriptArgs);
					else {
						var sinkArgs = shared ? args.copy() : args;
						shared = true;
						callHScript(row.hscript, sinkArgs);
					}
			}
		}
		return stopped ? Stop : Continue;
	}
}
