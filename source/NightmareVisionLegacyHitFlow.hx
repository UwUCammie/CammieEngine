package;

/** Historical default handlers share host effects, but do not inherit modern field admission. */
@:access(PlayState)
class NightmareVisionLegacyHitFlow {
	public static function hit(state:PlayState, note:Note, field:NightmareVisionPlayFieldView, player:Bool):Void {
		if (player) {
			if (note.wasGoodHit) { state.updateScoreBar(); return; }
			if (field.autoPlayed && (note.ignoreNote || note.hitCausesMiss)) return;
			state.playNightmareVisionLegacyHitSound(note);
			state.confirmNightmareVisionLegacyHit(note, field);
			if (note.hitCausesMiss) {
				state.noteMiss(note.noteData, true, note);
				if (!note.noteSplashDisabled && !note.isSustainNote) state.spawnNoteSplashOnNote(note);
				state.hurtNightmareVisionLegacySinger(note, field);
				note.wasGoodHit = true;
				note.nightmareVisionHitDispatched = true;
				retire(state, note);
				return;
			}
			if (!note.isSustainNote) {
				state.combo = Std.int(Math.min(9999, state.combo + 1));
				state.setAllHaxeVar('combo', state.combo);
				state.popUpScore(note.strumTime, note, true, false, field);
			}
			state.health += note.hitHealth * state.healthGain;
		} else state.camZooming = true;

		state.prepareNightmareVisionLegacyHitSingers(note, field, player);
		if (player) note.wasGoodHit = true;
		if (player || PlayState.SONG.needsVoices) state.setSourceVocalVolume('player', 1);
		if (!player) {
			state.confirmNightmareVisionLegacyHit(note, field);
			note.hitByOpponent = true;
		} else if (note.noteData > 4) note.doAutoSustain = true;

		// Direct default calls are source entrypoints too. Admission and duplicate
		// prevention belong to the input loop, not to an opponent-handler guard.
		state.dispatchHistoricalNightmareNoteHit(note, player ? 'goodNoteHit' : 'opponentNoteHit');
		note.nightmareVisionHitDispatched = true;
		state.finishNightmareVisionExternalHit(note, player, field, field.ID, true, field.autoPlayed);
		retire(state, note);
		if (player) state.updateScoreBar();
	}

	static function retire(state:PlayState, note:Note):Void {
		if (!note.isSustainNote) {
			state.detachNightmareVisionTap(note);
			note.destroy();
		}
	}

	/** Source Note.update commits the opponent flag after its script update. */
	public static function updateFlags(note:Note):Void {
		if (note.hitByOpponent) note.wasGoodHit = true;
	}
}
