package;

/** Worker-owned measurements. Time estimates describe the current phase only;
 * discovering work never invents a total or an overall completion percentage. */
class ImportRefreshProgress {
	public var phase(default, null):String = "preparing-import";
	public var current(default, null):String = "";
	public var completed(default, null):Int = 0;
	public var total(default, null):Int = 0;
	var started:Float;
	var phaseStarted:Float;
	var lastActivity:Float;
	var initialCompleted:Int = 0;

	public function new(now:Float) {
		started = phaseStarted = lastActivity = now;
	}

	public function update(payload:Dynamic, now:Float):Void {
		if (payload == null) return;
		var nextPhase = text(payload, "phase");
		if (nextPhase == "") nextPhase = phase;
		var nextCurrent = text(payload, "current");
		var nextTotal = count(payload, "total");
		// These scanners report their safety limit, not discovered work totals.
		if (nextPhase == "scan-roots" || nextPhase == "scan-discovery") nextTotal = 0;
		var nextCompleted = count(payload, "completed");
		// File/chart callbacks belong to the current song batch. Keep its
		// measurable count and rate while showing the latest file as activity.
		if (phase == "songs" && (StringTools.startsWith(nextPhase, "chart") || nextPhase == "song-assets"
			|| StringTools.startsWith(nextPhase, "import-provenance"))) {
			nextPhase = phase;
			nextTotal = total;
			nextCompleted = completed;
		}
		if (phase == "assets" && nextPhase == "assets" && total > 0 && nextTotal == 0) {
			nextTotal = total;
			nextCompleted = completed;
		}
		if (nextTotal > 0) nextCompleted = Std.int(Math.min(nextCompleted, nextTotal));
		if (nextPhase != phase || nextCompleted < completed || nextTotal != total) {
			phaseStarted = now;
			initialCompleted = nextCompleted;
		}
		if (nextPhase != phase || nextCurrent != current || nextCompleted != completed || nextTotal != total)
			lastActivity = now;
		phase = nextPhase;
		current = nextCurrent;
		completed = nextCompleted;
		total = nextTotal;
	}

	public function snapshot(now:Float, queueRemaining:Int):Dynamic {
		var phaseElapsed = Math.max(0, now - phaseStarted);
		var processed = completed - initialCompleted;
		var eta = total > 0 && processed > 0 && phaseElapsed >= 2
			? phaseElapsed * (total - completed) / processed : -1.0;
		return {
			phase:phase, current:current, completed:completed, total:total,
			elapsedSeconds:Math.max(0, now - started),
			activityAgeSeconds:Math.max(0, now - lastActivity),
			phaseElapsedSeconds:phaseElapsed, etaSeconds:eta,
			queueRemaining:Std.int(Math.max(0, queueRemaining))
		};
	}

	static function text(payload:Dynamic, field:String):String {
		var value = Reflect.field(payload, field);
		return value == null ? "" : Std.string(value);
	}

	static function count(payload:Dynamic, field:String):Int {
		var value = Std.parseFloat(text(payload, field));
		return Math.isNaN(value) || !Math.isFinite(value) || value < 0 ? 0 : Std.int(value);
	}
}
