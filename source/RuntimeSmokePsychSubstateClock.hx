package;

/** Native source import, fractional clock and shared section traversal checks. */
@:access(MusicBeatSubstate)
class RuntimeSmokePsychSubstateClock {
	static function check(ok:Bool, message:String):Void {if (!ok) throw message;}
	public static function verify(state:PlayState):Void {
		#if sys
		if (Sys.getEnv('CAMMIE_PSYCH_SUBSTATE_CLOCK_SMOKE') != '1') return;
		#else
		return;
		#end
		var oldSong = PlayState.SONG;
		var oldPosition = Conductor.songPosition;
		var oldMap = Conductor.bpmChangeMap;
		var oldStep = Conductor.stepCrochet;
		var oldTime = MusicBeatState.timePassedOnState;
		var prefs = PsychClientPrefsCompat.data;
		var oldOffset:Dynamic = prefs.noteOffset;
		var iris = new SourceIrisBridge(state);
		var probe:PsychMusicBeatSubstate = null;
		var cleanup = function() {
			PlayState.SONG = oldSong;Conductor.songPosition = oldPosition;Conductor.bpmChangeMap = oldMap;
			Conductor.stepCrochet = oldStep;MusicBeatState.timePassedOnState = oldTime;prefs.noteOffset = oldOffset;
			if (probe != null) probe.destroy();
			iris.release();
		};
		try {
			PsychStateClassBindings.install(iris.evaluator);
			iris.variables.set('made', null);
			iris.variables.set('scriptControls', null);
			iris.variables.set('expectedControls', PsychControlsCompat.instance);
			iris.evaluate('import backend.MusicBeatSubstate; made = new MusicBeatSubstate(); scriptControls = made.controls;', '__source_substate_clock');
			probe = cast iris.variables.get('made');
			check(probe != null && probe.sourceTiming, 'Native imported source substate class');
			check(iris.variables.get('scriptControls') == PsychControlsCompat.instance, 'Source script control identity');
			PlayState.SONG = cast {notes:[{sectionBeats:1.5}, null, {sectionBeats:null}, {sectionBeats:3.0}]};
			Conductor.bpmChangeMap = [{stepTime:8,songTime:1000,bpm:60,stepCrochet:250}, {stepTime:16,songTime:3000,bpm:240,stepCrochet:62.5}];
			Conductor.stepCrochet = 125;prefs.noteOffset = 75;
			MusicBeatState.timePassedOnState = 0;
			probe.persistentUpdate = false;
			Conductor.songPosition = 1000;probe.update(0.125);
			check(probe.curStep == 7 && Math.abs(probe.curDecStep - 7.7) < 0.00001 && probe.curSection == 1, 'Raw boundary selection then source offset and fractional section');
			check(probe.controls == PsychControlsCompat.instance && MusicBeatState.timePassedOnState == 0.125, 'Live source controls and paused-state clock');
			Conductor.songPosition = 3500;probe.update(0.125);
			check(probe.curStep == 22 && Math.abs(probe.curDecStep - 22.8) < 0.00001 && probe.curSection == 2, 'Forward section traversal across BPM change');
			probe.persistentUpdate = true;
			Conductor.songPosition = 100;probe.update(0.125);
			check(probe.curStep == 0 && probe.curSection == 0 && MusicBeatState.timePassedOnState == 0.25, 'Rollback and persistent-update elapsed rule');
			probe.sourceTiming = false;
			check(probe.controls == PlayerSettings.player1.controls, 'Historical native controls remain distinct');
			@:privateAccess RuntimeSmokeHarness.emit('psych_substate_clock_native_verified', {sourceImport:true,liveControls:true,fractionalTiming:true,sectionTraversal:true,rollback:true,elapsedRule:true,historicalControls:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
