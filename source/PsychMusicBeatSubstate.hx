package;

/** Psych's source clock over the common native substate and section services. */
@:keep
class PsychMusicBeatSubstate extends MusicBeatSubstate {
	public var sourceTiming:Bool;
	public var curSection:Int = 0;
	var stepsToDo:Int = 0;
	public var curDecStep:Float = 0;
	public var curDecBeat:Float = 0;

	public function new(sourceTiming:Bool = true) {
		this.sourceTiming = sourceTiming;
		super();
	}
	override function get_controls():Dynamic
		return sourceTiming ? PsychControlsCompat.instance : super.get_controls();

	override function update(elapsed:Float):Void {
		if (!sourceTiming) {super.update(elapsed);return;}
		if (!persistentUpdate) MusicBeatState.timePassedOnState += elapsed;
		var oldStep = curStep;
		updateCurStep();
		updateBeat();
		if (oldStep != curStep) {
			if (curStep > 0) stepHit();
			if (PlayState.SONG != null) {
				if (oldStep < curStep) updateSection(); else rollbackSection();
			}
		}
		updateSubstateChildren(elapsed);
	}
	override function updateCurStep():Void {
		if (!sourceTiming) {super.updateCurStep();return;}
		PsychBeatClock.updateStep(this);
	}
	function updateBeat():Void {curBeat = Math.floor(curStep / 4);curDecBeat = curDecStep / 4;}
	function updateSection():Void SourceBeatSections.advance(this, getBeatsOnSection, sectionHit);
	function rollbackSection():Void SourceBeatSections.rollback(this,
		function() return PlayState.SONG.notes.length,
		function(index) return PlayState.SONG.notes[index] != null, getBeatsOnSection, sectionHit);
	function getBeatsOnSection():Float return PsychBeatClock.sectionBeats(curSection);
	public function sectionHit():Void {}
}
