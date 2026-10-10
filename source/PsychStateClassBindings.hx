package;

/** Source names retain native state identity and use the base engine's live registry. */
class PsychStateClassBindings {
	public static function installScope(scope:SourceNativeClassScope):Void {
		if (!scope.hasRuntimeClass('backend.MusicBeatState')) scope.bindRuntimeClass('backend.MusicBeatState', MusicBeatState);
		if (!scope.hasRuntimeClass('states.PlayState')) scope.bindRuntimeClass('states.PlayState', PlayState);
	}
	public static function install(interp:NightmareVisionScriptInterp):Void {
		installScope(interp.sourceClassScope());
		interp.variables.set('MusicBeatState', MusicBeatState);
		interp.variables.set('PlayState', PlayState);
		interp.bindImport('backend.MusicBeatState', MusicBeatState);
		interp.bindImport('states.PlayState', PlayState);
	}
}
