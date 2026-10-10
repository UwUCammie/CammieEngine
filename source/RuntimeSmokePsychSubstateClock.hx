package;

import flixel.FlxG;

/** Native source import, fractional clock and shared section traversal checks. */
@:access(MusicBeatSubstate)
@:access(MusicBeatState)
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
		var sourceState:MusicBeatState = null;
		var reflectedState:MusicBeatState = null;
		var oldFullscreen:Dynamic = FlxG.save.data == null ? null : FlxG.save.data.fullscreen;
		var cleanup = function() {
			PlayState.SONG = oldSong;Conductor.songPosition = oldPosition;Conductor.bpmChangeMap = oldMap;
			Conductor.stepCrochet = oldStep;MusicBeatState.timePassedOnState = oldTime;prefs.noteOffset = oldOffset;
			if (probe != null) probe.destroy();
			if (sourceState != null) sourceState.destroy();
			if (reflectedState != null) reflectedState.destroy();
			if (FlxG.save.data != null) FlxG.save.data.fullscreen = oldFullscreen;
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
			iris.variables.set('madeState', null);
			iris.variables.set('stateControls', null);
			iris.evaluate('import backend.MusicBeatState; madeState = new MusicBeatState(); stateControls = madeState.controls;', '__source_state_clock');
			sourceState = cast iris.variables.get('madeState');
			check(Type.getClass(sourceState) == MusicBeatState && sourceState.psychSourceTiming, 'Source state keeps native identity and selects source clock');
			check(iris.variables.get('stateControls') == PsychControlsCompat.instance && !state.psychSourceTiming, 'Source controls isolated from gameplay host');
			var scope = new SourceNativeClassScope();
			PsychStateClassBindings.installScope(scope);
			PsychStateClassBindings.installScope(scope);
			reflectedState = scope.createInstance(scope.resolveClass('backend.MusicBeatState'), []);
			check(reflectedState.psychSourceTiming, 'Reflection constructor source mode');
			scope.release();
			MusicBeatState.timePassedOnState = 0;
			Conductor.songPosition = 1000;sourceState.update(0.125);
			check(sourceState.curStep == 7 && Math.abs(sourceState.curDecBeat - 1.925) < 0.00001 && sourceState.curSection == 1, 'State fractional clock and section');
			Conductor.songPosition = 3500;sourceState.update(0.125);
			check(sourceState.curStep == 22 && sourceState.curSection == 2, 'State forward sections');
			Conductor.songPosition = 100;sourceState.update(0.125);
			check(sourceState.curStep == 0 && sourceState.curSection == 0 && MusicBeatState.timePassedOnState == 0.375, 'State rollback and elapsed');
			@:privateAccess RuntimeSmokeHarness.emit('psych_state_clock_native_verified', {sourceImport:true,reflection:true,nativeIdentity:true,hostIsolation:true,fractionalTiming:true,sectionTraversal:true,rollback:true});
			@:privateAccess RuntimeSmokeHarness.emit('psych_substate_clock_native_verified', {sourceImport:true,liveControls:true,fractionalTiming:true,sectionTraversal:true,rollback:true,elapsedRule:true,historicalControls:true});
		} catch (error:Dynamic) {cleanup();throw error;}
		cleanup();
	}
}
