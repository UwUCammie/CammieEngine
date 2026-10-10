package;

/** Shared source timing math for Psych states and substates. */
class PsychBeatClock {
	public static function updateStep(state:Dynamic):Void {
		var change = Conductor.getBPMFromSeconds(Conductor.songPosition);
		var fraction = ((Conductor.songPosition - PsychClientPrefsCompat.data.noteOffset) - change.songTime) / change.stepCrochet;
		state.curDecStep = change.stepTime + fraction;
		state.curStep = change.stepTime + Math.floor(fraction);
	}
	public static function sectionBeats(index:Int):Float {
		var value:Null<Float> = 4;
		if (PlayState.SONG != null && PlayState.SONG.notes[index] != null)
			value = Reflect.field(PlayState.SONG.notes[index], 'sectionBeats');
		return value == null ? 4 : value;
	}
}
