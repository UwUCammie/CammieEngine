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
	public static function press(state:PlayState, direction:Int = 1, anim:Bool = true):Void {
		if (state.nightmareVisionPrefs.view.ghostTapping == true) return;
		if (!state.boyfriend.stunned) {
			state.health -= SourceHealthDelta.pressMiss(state.healthLoss);
			if (state.instakillOnMiss) {
				state.setSourceVocalVolume('player', 0);
				state.doDeathCheck(true);
			}
			if (state.combo > 5 && state.gf != null && state.gf.animOffsets.exists('sad')) state.gf.playAnim('sad');
			state.combo = 0;
			var delta = SourceScoreLedger.miss(true, state.practiceMode, state.endingSong, true);
			state.songScore += delta.score;
			PlayState.misses += delta.missDelta;
			state.totalPlayed += delta.played;
			state.refreshSourceAccuracy();
			state.RecalculateRating();
			state.playHistoricalNightmareMissSound();
			if (state.boyfriend.hasMissAnimations && anim && state.boyfriend.animTimer <= 0 && !state.boyfriend.voicelining)
				state.boyfriend.playAnim(state.singAnimations[Std.int(Math.abs(direction))] + 'miss', true);
			state.setSourceVocalVolume('player', 0);
		}
		state.broadcastHistoricalNightmareScripts('noteMissPress', [direction]);
	}

}
