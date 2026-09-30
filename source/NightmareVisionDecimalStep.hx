package;

/**
 * Pure Nightmare Vision Conductor.getStep / MusicBeatState.curDecStep adapter.
 * The fork's BPMChangeEvent stores `{stepTime, songTime, bpm}`; the source
 * conductor also accepts an optional precomputed `stepCrotchet` field.
 */
class NightmareVisionDecimalStep {
	/**
	 * Convert song milliseconds to a fractional step. `noteOffsetMs` defaults
	 * to zero (the source Conductor.getStep contract); passing the configured
	 * offset reproduces NMV MusicBeatState.curDecStep.
	 *
	 * BPM segment selection uses the unadjusted song time, then subtracts the
	 * note offset within that segment, matching the donor MusicBeatState code.
	 * Negative countdown time uses the initial song BPM until a change at or
	 * before that raw time is present in the map.
	 */
	public static function getStep(songTimeMs:Float, initialBpm:Float,
		bpmChangeMap:Array<Dynamic>, noteOffsetMs:Float = 0):Float {
		var change:Dynamic = null;
		if (bpmChangeMap != null) {
			for (candidate in bpmChangeMap) {
				if (candidate == null) continue;
				var changeTime = numberField(candidate, 'songTime', Math.NaN);
				if (songTimeMs >= changeTime)
					change = candidate;
			}
		}

		var changeTime = change == null ? 0 : numberField(change, 'songTime', 0);
		var changeStep = change == null ? 0 : numberField(change, 'stepTime', 0);
		var stepCrochet = change == null ? Math.NaN : numberField(change, 'stepCrotchet', Math.NaN);
		if (!(stepCrochet > 0)) {
			var bpm = change == null ? initialBpm : numberField(change, 'bpm', initialBpm);
			if (!(bpm > 0)) bpm = initialBpm;
			stepCrochet = (60 / bpm) * 1000 / 4;
		}
		if (!(stepCrochet > 0)) return Math.NaN;
		return changeStep + ((songTimeMs - noteOffsetMs) - changeTime) / stepCrochet;
	}

	static function numberField(value:Dynamic, name:String, fallback:Float):Float {
		var field = Reflect.field(value, name);
		if (field == null) return fallback;
		var parsed = Std.parseFloat(Std.string(field));
		return Math.isNaN(parsed) ? fallback : parsed;
	}
}
