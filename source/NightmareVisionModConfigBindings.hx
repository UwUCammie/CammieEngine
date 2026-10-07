package;

/** Source class statics resolve through the captured session, never host globals. */
class NightmareVisionModConfigBindings {
	public static function install(interp:Dynamic, config:NightmareVisionModConfigRuntime, musicBeatType:Dynamic):Void {
		var scope:SourceNativeClassScope = interp.sourceClassScope();
		interp.variables.set('FunkinTransitionState', NightmareVisionModTransition);
		interp.bindImport('funkin.data.FunkinTransitionState', NightmareVisionModTransition);
		scope.bindRuntimeEnum('funkin.data.FunkinTransitionState', NightmareVisionModTransition);
		interp.variables.set('MusicBeatState', musicBeatType);
		interp.bindImport('funkin.backend.MusicBeatState', musicBeatType);
		scope.bindRuntimeClass('funkin.backend.MusicBeatState', musicBeatType);
		scope.bindStaticField(musicBeatType, 'DEFAULT_TRANSITION_STATE', function() return NightmareVisionModTransition.SWIPE);
		scope.bindStaticField(musicBeatType, 'transitionInState', function() return config.transitionIn,
			function(value) return config.transitionIn = cast value);
		scope.bindStaticField(musicBeatType, 'transitionOutState', function() return config.transitionOut,
			function(value) return config.transitionOut = cast value);
	}
}
