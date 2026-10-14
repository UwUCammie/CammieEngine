package;

/** Shared source timing math for Psych states and substates. */
class PsychBeatClock {
	public static function updateStep(state:Dynamic):Void {
		var change = Conductor.getBPMFromSeconds(Conductor.songPosition);
		var fraction = stepFraction(change);
		state.curDecStep = change.stepTime + fraction;
		state.curStep = change.stepTime + Math.floor(fraction);
	}
	// The step length comes from the base Conductor so a map written in the
	// other spelling (stepCrotchet) or with only a bpm still counts.
	static function stepFraction(change:Conductor.BPMChangeEvent):Float
		return ((Conductor.songPosition - PsychClientPrefsCompat.data.noteOffset) - change.songTime) / Conductor.segmentStepCrochet(change);
	public static function getDecimalStep():Float
		return Conductor.getStep(Conductor.songPosition, PsychClientPrefsCompat.data.noteOffset);
	public static function sectionBeats(index:Int):Float {
		var value:Null<Float> = 4;
		if (PlayState.SONG != null && PlayState.SONG.notes[index] != null)
			value = Reflect.field(PlayState.SONG.notes[index], 'sectionBeats');
		return value == null ? 4 : value;
	}
}
