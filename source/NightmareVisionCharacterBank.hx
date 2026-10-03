package;

/** Source CharacterGroup's cached actor identity and alpha transfer. The
 * owning state constructs, attaches and destroys every actor exactly once. */
class NightmareVisionCharacterBank {
	final cache:PsychCharacterCache<Dynamic>;
	public var map(get, never):Map<String, Dynamic>;
	public var parent(get, never):Dynamic;

	public function new(parent:Dynamic, construct:String->Dynamic, activate:Dynamic->Dynamic->Void) {
		cache = new PsychCharacterCache<Dynamic>(parent,
			function(actor:Dynamic):String return actor == null ? null : Std.string(Reflect.getProperty(actor, 'requestedCharacter')),
			construct, activate);
	}

	function get_map():Map<String, Dynamic> return cache.map;
	function get_parent():Dynamic return cache.parent;

	public inline function addToList(name:String):Dynamic return cache.addToList(name);
	public inline function change(name:String):Dynamic return cache.change(name);
	/** Source CharacterGroup.parent assignment changes only the reference. */
	public function assignParentReference(value:Dynamic):Dynamic {
		@:privateAccess cache.parent = value;
		return value;
	}

	/** Display ownership remains with the state; drop references on teardown. */
	public inline function release():Void cache.release();
}
