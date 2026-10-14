package;

/** Source static character sets follow the existing selected NV owner lease.
 * Same-owner retries retain metadata; scope setup selects the shared IO view. */
class NightmareVisionAlphabetRegistry {
	static final registry = new SourceOwnerContextRegistry<NightmareVisionAlphabetContext>(function(context) context.release());
	public static function enterSession(root:Null<String>):Void registry.enterSession(root);
	public static function get(root:String, owner:NightmareVisionAlphabetOwner):NightmareVisionAlphabetContext
		return registry.get(root, function() return new NightmareVisionAlphabetContext(owner),
			function(context) context.rebindOwner(owner));
}
