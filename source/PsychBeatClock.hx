package;

/** Shared source timing math for Psych states and substates. */
class PsychBeatClock {
	public static function updateStep(state:Dynamic):Void {
		var change = Conductor.getBPMFromSeconds(Conductor.songPosition);
		var fraction = stepFraction(change);
		state.curDecStep = change.stepTime + fraction;
		state.curStep = change.stepTime + Math.floor(fraction);
	}
	static function stepFraction(change:Conductor.BPMChangeEvent):Float
		return ((Conductor.songPosition - PsychClientPrefsCompat.data.noteOffset) - change.songTime) / change.stepCrochet;
	public static function getDecimalStep():Float {
		var change = Conductor.getBPMFromSeconds(Conductor.songPosition);
		return change.stepTime + stepFraction(change);
	}
	public static function sectionBeats(index:Int):Float {
		var value:Null<Float> = 4;
		if (PlayState.SONG != null && PlayState.SONG.notes[index] != null)
			value = Reflect.field(PlayState.SONG.notes[index], 'sectionBeats');
		return value == null ? 4 : value;
	}
}
