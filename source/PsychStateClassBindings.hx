package;

/** Source names retain native state identity and use the base engine's live registry. */
@:access(PlayState)
class PsychStateClassBindings {
	public static function registry(host:PlayState):Map<String,Dynamic> {
		return host.nightmareVisionLegacyFieldCameras ? host.psychScriptVariables : MusicBeatState.getVariables();
	}
	public static function installScope(scope:SourceNativeClassScope):Void {
		if (!scope.hasRuntimeClass('backend.MusicBeatState')) scope.bindRuntimeClass('backend.MusicBeatState', MusicBeatState);
		if (!scope.hasRuntimeClass('backend.MusicBeatSubstate')) scope.bindRuntimeClass('backend.MusicBeatSubstate', PsychMusicBeatSubstate);
		if (!scope.hasRuntimeClass('psychlua.CustomSubstate')) scope.bindRuntimeClass('psychlua.CustomSubstate', PsychCustomSubstate);
		if (!scope.hasRuntimeClass('states.PlayState')) scope.bindRuntimeClass('states.PlayState', PlayState);
	}
	public static function install(interp:NightmareVisionScriptInterp):Void {
		installScope(interp.sourceClassScope());
		interp.variables.set('MusicBeatState', MusicBeatState);
		interp.variables.set('MusicBeatSubstate', PsychMusicBeatSubstate);
		// Iris otherwise prefers the same-named host class over the source alias.
		interp.bindConstructorFactory(PsychMusicBeatSubstate,
			function(args) return Type.createInstance(PsychMusicBeatSubstate, args), null);
		interp.variables.set('PlayState', PlayState);
		interp.bindImport('backend.MusicBeatState', MusicBeatState);
		interp.bindImport('backend.MusicBeatSubstate', PsychMusicBeatSubstate);
		interp.bindImport('states.PlayState', PlayState);
		interp.bindImport('psychlua.CustomSubstate', PsychCustomSubstate);
	}
}
