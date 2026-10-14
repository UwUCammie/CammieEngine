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
		// Same conversion as the base Conductor; the initial tempo only covers
		// time before the first entry (the countdown).
		return ConductorTempoMap.stepAtTime(songTimeMs, cast bpmChangeMap, (60 / initialBpm) * 1000 / 4, noteOffsetMs);
	}
}
