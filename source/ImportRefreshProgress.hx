package;

/** Worker-owned whole-operation estimates. Measured throughput replaces phase
 * priors as work becomes known. Queue cost uses observed complete-job duration;
 * discovery limits never become real work totals. No filesystem inspection. */
class ImportRefreshProgress {
	public var phase(default, null):String = "preparing-import";
	public var current(default, null):String = "";
	public var completed(default, null):Int = 0;
	public var total(default, null):Int = 0;
	var started:Float;
	var phaseStarted:Float;
	var lastActivity:Float;
	var initialCompleted:Int = 0;
	var phaseDurations:Map<Int,Float> = [];
	var finished:Bool = false;
	var furthestStage:Int = 0;
	// Written only by the coordinator while holding its mutex.
	static var secondsPerWorkUnit:Float = 0.5;
	var workUnits:Float;

	public function finish(now:Float):Void {
		if (finished) return;
		finished = true;
		var duration = Math.max(0, now-started);
		if (duration >= 2) secondsPerWorkUnit = secondsPerWorkUnit*0.5+Math.max(0,duration-10)/workUnits*0.5;
	}

	public static function estimatedWorkUnits(value:Dynamic, fallback:Float = 100):Float {
		if (!Std.isOfType(value,Int) && !Std.isOfType(value,Float)) return fallback;
		var units:Float = value;
		return Math.isFinite(units) && units > 0 ? units : fallback;
	}

	static function stage(name:String):Int {
		if (name == 'loading-imported-songs') return 7;
		if (name == 'cleaning-up-import') return 6;
		if (name == 'publishing-import' || name == 'backing-up-import') return 5;
		if (name == 'preparing-output' || name == 'checking-output' || name == 'checking-installed') return 4;
		if (name == 'assets' || name == 'overlays' || name == 'registries' || name == 'complete') return 3;
		if (name == 'songs' || name == 'converting-import' || name == 'analyzing-chart-difficulty') return 2;
		if (name == 'retaining-source' || name == 'checking-retained-source') return 0;
		return 1;
	}

	static function prior(index:Int):Float {
		return switch(index) { case 0: 10; case 1: 5; case 2: 20; case 3: 15;
			case 4: 4; case 5: 4; case 6: 1; default: 2; };
	}

	public function new(now:Float, estimatedWorkUnits:Float = 100) {
		workUnits = Math.max(1,estimatedWorkUnits);
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
		if (nextPhase != phase) {
			var index = stage(phase);
			var duration = Math.max(0, now-phaseStarted);
			if (duration > 0) phaseDurations.set(index, (phaseDurations.exists(index) ? phaseDurations.get(index) : 0)+duration);
		}
		if (nextPhase != phase || nextCompleted < completed || nextTotal != total) {
			phaseStarted = now;
			initialCompleted = nextCompleted;
		}
		if (nextPhase != phase || nextCurrent != current || nextCompleted != completed || nextTotal != total)
			lastActivity = now;
		furthestStage = Std.int(Math.max(furthestStage,stage(nextPhase)));
		phase = nextPhase;
		current = nextCurrent;
		completed = nextCompleted;
		total = nextTotal;
	}

	public function snapshot(now:Float, queueRemaining:Int, queuedWorkUnits:Float = -1):Dynamic {
		var phaseElapsed = Math.max(0, now - phaseStarted);
		var processed = completed - initialCompleted;
		var phaseEta = total > 0 && processed > 0 && phaseElapsed >= 2
			? phaseElapsed * (total - completed) / processed : -1.0;
		var index = furthestStage;
		// Unknown work gets an explicit estimate, not the previous phase's rate.
		// If a phase exceeds its prior, reserve half its elapsed time for work left.
		var remaining = phaseEta >= 0 ? phaseEta : Math.max(prior(index)-phaseElapsed,phaseElapsed*0.5);
		for (next in (index+1)...8) remaining += phaseDurations.exists(next) ? Math.max(prior(next),phaseDurations.get(next)) : prior(next);
		var elapsed = Math.max(0,now-started);
		var queuedCount = Math.max(0,queueRemaining);
		var units = queuedWorkUnits < 0 ? queuedCount*100 : Math.max(0,queuedWorkUnits);
		// Already-loaded manifest item counts distinguish tiny and huge packages.
		// Per-package overhead remains even if all file work is very cheap.
		var eta = (finished ? prior(7) : remaining)+queuedCount*10+units*secondsPerWorkUnit;
		return {
			phase:phase, current:current, completed:completed, total:total,
			elapsedSeconds:Math.max(0, now - started),
			activityAgeSeconds:Math.max(0, now - lastActivity),
			phaseElapsedSeconds:phaseElapsed, phaseEtaSeconds:phaseEta, etaSeconds:eta, etaEstimated:true,
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
