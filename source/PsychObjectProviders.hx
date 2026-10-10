package;

/** Shared modern Psych roots; asset and script ownership stay with their adapters. */
@:access(PlayState)
class PsychObjectProviders {
	static var reflection=new SourcePsychReflection(MusicBeatState.getVariables,MusicBeatState.getState,
		function():Dynamic return PlayState.instance,target,function(value)return Std.isOfType(value,MusicBeatState),
		Type.resolveClass,Reflect.getProperty,Reflect.setProperty,function(value)return value,function(message)trace(message));
	public static function target():Dynamic {
		var play=PlayState.instance;
		return play==null ? MusicBeatState.getState() : play.isDead ? GameOverSubstate.instance : play;
	}
	public static function direct(name:String):Dynamic return reflection.direct(name);
	public static function text(path:String):Dynamic return reflection.object(path);
	public static function textRemovalTarget():Dynamic {
		return PsychCustomSubstate.instance!=null ? PsychCustomSubstate.instance : target();
	}
}
