package;

/** Current Psych argument parsing over native state objects and scoped source classes. */
class PsychInstanceArguments {
	public static function parse(value:Dynamic, recursive:Bool, resolveClass:String->Dynamic,
		?readProperty:(Dynamic,String)->Dynamic):Dynamic {
		if (readProperty == null) readProperty = Reflect.getProperty;
		var read = function(object:Dynamic, key:String):Dynamic
			return SourceScriptReflection.readPsychInstancePart(object, key,
				function(candidate) return Std.isOfType(candidate, MusicBeatState), MusicBeatState.getVariables, readProperty);
		return recursive ? SourceScriptReflection.parsePsychInstances(value, function() return PlayState.instance, resolveClass, read)
			: SourceScriptReflection.parsePsychSingleInstance(value, function() return PlayState.instance, resolveClass, read);
	}
}
