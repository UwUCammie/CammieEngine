package;

/** Shared source metadata follows the existing primary Psych preference lease.
 * Per-interpreter resource views are rebound without resetting authored maps. */
class PsychAlphabetRegistry {
	static var loaders:Map<String, Dynamic> = new Map();
	static final registry = new SourceOwnerContextRegistry<PsychAlphabetContext>(function(context) context.release(),
		function() loaders.clear());
	public static function enterSession(root:Null<String>):Void registry.enterSession(root);
	public static function get(root:String, owner:PsychAlphabetOwner, initialize:Bool = true):PsychAlphabetContext {
		var context = registry.get(root, function() return new PsychAlphabetContext(owner),
			function(context) context.rebindOwner(owner));
		if (initialize) context.initialize();
		return context;
	}
	public static function loader(root:String):Dynamic {
		if (!loaders.exists(root)) {
			var context = registry.existing(root);
			loaders.set(root, function(request:String = 'alphabet'):Void context.loadAlphabetData(request));
		}
		return loaders.get(root);
	}
}
