package;

/** Source static character sets follow the existing selected NV owner lease.
 * Same-owner retries retain metadata; scope setup selects the shared IO view. */
class NightmareVisionAlphabetRegistry {
	static var primaryRoot:Null<String>;
	static var contexts:Map<String, NightmareVisionAlphabetContext> = new Map();
	public static function enterSession(root:Null<String>):Void {
		if (root == '') root = null;
		if (root == primaryRoot) return;
		for (context in contexts) context.release();
		contexts.clear(); primaryRoot = root;
	}
	public static function get(root:String, owner:NightmareVisionAlphabetOwner):NightmareVisionAlphabetContext {
		var context = contexts.get(root);
		if (context == null) {
			context = new NightmareVisionAlphabetContext(owner);
			contexts.set(root, context);
		} else context.rebindOwner(owner);
		return context;
	}
}
