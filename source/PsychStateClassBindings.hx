package;

/** Source names retain native state identity and use the base engine's live registry. */
@:access(PlayState)
class PsychStateClassBindings {
	public static function registry(host:PlayState):Map<String,Dynamic> {
		return host.nightmareVisionLegacyFieldCameras ? host.psychScriptVariables : MusicBeatState.getVariables();
	}
	public static function installScope(scope:SourceNativeClassScope):Void {
		scope.bindInstanceProperty(MusicBeatState, 'controls', function(object:MusicBeatState):Dynamic
			return object.psychSourceTiming ? PsychControlsCompat.instance : Reflect.getProperty(object, 'controls'));
		if (!scope.hasRuntimeClass('backend.MusicBeatState')) {
			scope.bindRuntimeClass('backend.MusicBeatState', MusicBeatState);
			var previous = scope.construct;
			scope.construct = function(type:Dynamic, args:Array<Dynamic>):Dynamic {
				if (type == MusicBeatState) {
					var state:MusicBeatState = previous == null ? createState(args) : previous(type, args);
					state.psychSourceTiming = true;
					return state;
				}
				return previous == null ? Type.createInstance(type, args) : previous(type, args);
			};
		}
		if (!scope.hasRuntimeClass('backend.BaseStage')) {
			scope.bindRuntimeClass('backend.BaseStage', PsychBaseStageCompat);
			var previous = scope.construct;
			scope.construct = function(type:Dynamic, args:Array<Dynamic>):Dynamic {
				if (type == PsychBaseStageCompat) return createStage(args);
				return previous == null ? Type.createInstance(type, args) : previous(type, args);
			};
		}
		if (!scope.hasRuntimeClass('backend.MusicBeatSubstate')) scope.bindRuntimeClass('backend.MusicBeatSubstate', PsychMusicBeatSubstate);
		if (!scope.hasRuntimeClass('psychlua.CustomSubstate')) scope.bindRuntimeClass('psychlua.CustomSubstate', PsychCustomSubstate);
		if (!scope.hasRuntimeClass('states.PlayState')) scope.bindRuntimeClass('states.PlayState', PlayState);
	}
	static function createStage(args:Array<Dynamic>):PsychBaseStageCompat
		return PsychStageConstruction.createNative(PsychObjectProviders.stageContext());

	static function createState(args:Array<Dynamic>):MusicBeatState {
		var state = Type.createInstance(MusicBeatState, args);
		state.psychSourceTiming = true;
		return state;
	}
	public static function install(interp:NightmareVisionScriptInterp):Void {
		installScope(interp.sourceClassScope());
		interp.variables.set('BaseStage', PsychBaseStageCompat);
		interp.bindImport('backend.BaseStage', PsychBaseStageCompat);
		interp.bindConstructorFactory(PsychBaseStageCompat, createStage, null);
		interp.variables.set('MusicBeatState', MusicBeatState);
		interp.bindConstructorFactory(MusicBeatState, createState, null);
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
