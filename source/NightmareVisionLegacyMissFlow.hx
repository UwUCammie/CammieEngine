package;

/** Historical miss ordering over native note ownership, scoring and audio services. */
@:access(PlayState)
class NightmareVisionLegacyMissFlow {
	public static function miss(state:PlayState, note:Note):Void {
		if (note == null) return;
		state.updateScoreBar();
		state.notes.forEachAlive(function(candidate:Note) {
			var field:NightmareVisionPlayFieldView = cast note.playField;
			if (SourceMissDuplicates.matches(note, candidate, field != null && field.playerControls))
				state.retireNightmareVisionLegacyDuplicate(candidate);
		});
		state.combo = 0;
		state.health -= note.missHealth * state.healthLoss;
		if (state.instakillOnMiss) {
			state.setSourceVocalVolume('player', 0);
			state.doDeathCheck(true);
		}
		var delta = SourceScoreLedger.miss(true, state.practiceMode);
		PlayState.misses += delta.missDelta;
		state.setSourceVocalVolume('player', 0);
		state.songScore += delta.score;
		state.totalPlayed += delta.played;
		state.refreshSourceAccuracy();
		state.RecalculateRating();
		var actor = note.forceGfSing ? state.gf : state.boyfriend;
		if (actor != null && !note.noMissAnimation && actor.hasMissAnimations
			&& actor.animTimer <= 0 && !actor.voicelining) {
			var suffix = note.noteType == 'Alt Animation' ? '-alt' : '';
			actor.playAnim(state.singAnimations[Std.int(Math.abs(note.noteData))] + 'miss' + suffix, true);
		}
		state.dispatchHistoricalNightmareNoteHit(note, 'noteMiss');
		state.publishHistoricalNightmareMiss(note);
	}
}
