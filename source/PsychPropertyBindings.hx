package;

/** Modern Psych callbacks reuse source traversal and the existing native class scope. */
@:access(PlayState)
class PsychPropertyBindings {
	public static function install(host:PlayState, interp:hscript.Interp, classes:SourceNativeClassScope, parse:Dynamic->Dynamic):Void {
		var resolve=function(name:String):Dynamic return classes.hasRuntimeClass(name)?classes.resolveClass(name):host.compatResolveClass(name);
		var target=function():Dynamic {var play=PlayState.instance;return play==null ? MusicBeatState.getState() : play.isDead ? GameOverSubstate.instance : play;};
		var warn=function(message:String):Void trace('[psych-reflection] '+message);
		interp.variables.set('createInstance',function(name:String,type:String,?args:Array<Dynamic>):Bool {
			return SourceScriptInstances.create(name,type,args,MusicBeatState.getVariables,resolve,parse,classes.createInstance,warn);
		});
		interp.variables.set('addInstance',function(name:String,front:Bool=false):Void {
			SourceScriptInstances.add(name,front,MusicBeatState.getVariables,target,function():Dynamic return PlayState.instance,
				function():Dynamic return GameOverSubstate.instance,function() return PsychSceneAnchors.lowestCharacter(PlayState.instance),warn);
		});
		var service=new SourcePsychReflection(MusicBeatState.getVariables,MusicBeatState.getState,function() return PlayState.instance,
			target,
			function(value) return Std.isOfType(value,MusicBeatState),
			resolve,
			function(object,key) return classes.read(object,key),
			function(object,key,value):Void {classes.write(object,key,value);},parse,warn);
		interp.variables.set('getPropertyFromGroup',service.getGroup);
		interp.variables.set('setPropertyFromGroup',service.setGroup);
		interp.variables.set('addToGroup',service.addGroup);
		interp.variables.set('removeFromGroup',service.removeGroup);
		interp.variables.set('getProperty',service.get);
		interp.variables.set('setProperty',service.set);
		interp.variables.set('getPropertyFromClass',service.getClass);
		interp.variables.set('setPropertyFromClass',service.setClass);
		interp.variables.set('callMethod',service.call);
		interp.variables.set('callMethodFromClass',service.callClass);
	}
}
