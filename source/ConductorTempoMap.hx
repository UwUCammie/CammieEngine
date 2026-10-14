package;

/** One tempo segment, the same shape as Conductor.BPMChangeEvent. */
typedef ConductorTempoChange = {
	var stepTime:Int;
	var songTime:Float;
	var bpm:Float;
	@:optional var stepCrochet:Float;
}

/**
 * Tempo map maths shared by the base Conductor and the Psych and Nightmare
 * Vision layers. It holds no state and imports nothing, so every caller and
 * every interpreter fixture uses this same code.
 */
class ConductorTempoMap {
	/** Step length of one tempo segment. Native and Psych maps store it as
	 * stepCrochet, Nightmare Vision maps as stepCrotchet, and hand-built maps
	 * may only carry the bpm, so all three are read here once. */
	public static function segmentStepCrochet(change:ConductorTempoChange, fallback:Float):Float {
		var stored:Null<Float> = change.stepCrochet;
		if (stored != null && stored > 0) return stored;
		var spelled:Dynamic = Reflect.field(change, 'stepCrotchet');
		if ((Std.isOfType(spelled, Float) || Std.isOfType(spelled, Int)) && spelled > 0) return spelled;
		if (change.bpm > 0) return (60 / change.bpm) * 1000 / 4;
		return fallback;
	}

	/**
	 * Fractional step for a song time across a tempo map. The segment is picked
	 * with the raw time and the note offset is taken off inside it, which is how
	 * Psych and Nightmare Vision both compute curDecStep. Before the first
	 * change, `fallbackStepCrochet` is the step length.
	 */
	public static function stepAtTime(time:Float, map:Array<ConductorTempoChange>, fallbackStepCrochet:Float,
		noteOffset:Float = 0):Float {
		var change:ConductorTempoChange = null;
		if (map != null) for (candidate in map) if (candidate != null && time >= candidate.songTime) change = candidate;
		var duration = change == null ? fallbackStepCrochet : segmentStepCrochet(change, fallbackStepCrochet);
		if (!(duration > 0)) return Math.NaN;
		if (change == null) return (time - noteOffset) / duration;
		return change.stepTime + ((time - noteOffset) - change.songTime) / duration;
	}

	/**
	 * Tempo changes of a chart's sections. `sectionSteps` is the only thing the
	 * chart dialects disagree on: how long a section is.
	 */
	public static function tempoChanges(song:Dynamic, sectionSteps:Dynamic->Int):Array<ConductorTempoChange> {
		var changes:Array<ConductorTempoChange> = [];
		var curBPM:Float = song.bpm;
		var totalSteps:Int = 0;
		var totalPos:Float = 0;
		var sections:Array<Dynamic> = song.notes;
		if (sections == null) return changes;
		for (section in sections) {
			if (section != null && section.changeBPM == true && section.bpm != curBPM) {
				curBPM = section.bpm;
				changes.push({
					stepTime: totalSteps,
					songTime: totalPos,
					stepCrochet: (60 / curBPM) * 1000 / 4,
					bpm: curBPM
				});
			}

			var deltaSteps:Int = sectionSteps(section);
			totalSteps += deltaSteps;
			totalPos += ((60 / curBPM) * 1000 / 4) * deltaSteps;
		}
		return changes;
	}
}
