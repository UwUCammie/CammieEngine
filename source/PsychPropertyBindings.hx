package;

/** Modern Psych callbacks reuse source traversal and the existing native class scope. */
@:access(PlayState)
class PsychPropertyBindings {
	public static function install(host:PlayState, interp:hscript.Interp, classes:SourceNativeClassScope, parse:Dynamic->Dynamic):Void {
		var service=new SourcePsychReflection(MusicBeatState.getVariables,MusicBeatState.getState,function() return PlayState.instance,
			function():Dynamic {var play=PlayState.instance;return play==null ? MusicBeatState.getState() : play.isDead ? GameOverSubstate.instance : play;},
			function(value) return Std.isOfType(value,MusicBeatState),
			function(name) return classes.hasRuntimeClass(name)?classes.resolveClass(name):host.compatResolveClass(name),
			function(object,key) return classes.read(object,key),
			function(object,key,value):Void {classes.write(object,key,value);},parse,function(message) trace('[psych-reflection] '+message));
		interp.variables.set('getProperty',service.get);
		interp.variables.set('setProperty',service.set);
		interp.variables.set('getPropertyFromClass',service.getClass);
		interp.variables.set('setPropertyFromClass',service.setClass);
		interp.variables.set('callMethod',service.call);
		interp.variables.set('callMethodFromClass',service.callClass);
	}
}
