package;

/** Shared source metadata follows the existing primary Psych preference lease.
 * Per-interpreter resource views are rebound without resetting authored maps. */
class PsychAlphabetRegistry {
	static var primaryRoot:Null<String>;
	static var contexts:Map<String, PsychAlphabetContext> = new Map();
	static var loaders:Map<String, Dynamic> = new Map();
	public static function enterSession(root:Null<String>):Void {
		if (root == primaryRoot) return;
		for (context in contexts) context.release();
		contexts.clear(); loaders.clear(); primaryRoot = root;
	}
	public static function get(root:String, owner:PsychAlphabetOwner, initialize:Bool = true):PsychAlphabetContext {
		var context = contexts.get(root);
		if (context == null) {
			context = new PsychAlphabetContext(owner);
			contexts.set(root, context);
		} else context.rebindOwner(owner);
		if (initialize) context.initialize();
		return context;
	}
	public static function loader(root:String):Dynamic {
		if (!loaders.exists(root)) {
			var context = contexts.get(root);
			loaders.set(root, function(request:String = 'alphabet'):Void context.loadAlphabetData(request));
		}
		return loaders.get(root);
	}
}
