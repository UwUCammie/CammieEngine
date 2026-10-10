package;

/** Source variable operations use a live registry provider, preserving read order. */
class SourceScriptVariables {
	public static function write(registry:()->Dynamic, name:String, value:Dynamic, ?convert:Dynamic->Dynamic):Void {
		var target = registry();
		target.set(name, convert == null ? value : convert(value));
	}
	public static function set(registry:()->Dynamic, name:String, value:Dynamic, ?convert:Dynamic->Dynamic):Dynamic {
		write(registry, name, value, convert);
		return value;
	}
	public static function get(registry:()->Dynamic, name:String, checkExists:Bool = false):Dynamic {
		if (checkExists && !registry().exists(name)) return null;
		return registry().get(name);
	}
	public static function remove(registry:()->Dynamic, name:String, checkExists:Bool = true):Bool {
		if (!checkExists) return registry().remove(name);
		if (!registry().exists(name)) return false;
		registry().remove(name);
		return true;
	}
}
