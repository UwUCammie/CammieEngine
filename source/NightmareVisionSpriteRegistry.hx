package;

/** Providers are borrowed by sprites; only the existing primary owner lease
 * releases IO. Setup rebinds views; construction never changes a live view. */
class NightmareVisionSpriteRegistry {
	static var primaryRoot:Null<String>;
	static var owners:Map<String, NightmareVisionSpriteOwner> = new Map();
	public static function enterSession(root:Null<String>):Void {
		if (root == '') root = null;
		if (root == primaryRoot) return;
		for (owner in owners) owner.release();
		owners.clear(); primaryRoot = root;
	}
	public static function setup(paths:NightmareVisionPaths):NightmareVisionSpriteOwner {
		var owner = capture(paths);
		owner.rebind(function(path) return paths.getAtlasFrames(path));
		return owner;
	}
	/** A constructor may create a missing cell, but never rebind an existing one. */
	public static function capture(paths:NightmareVisionPaths):NightmareVisionSpriteOwner {
		if (paths == null) return null;
		var owner = owners.get(paths.root);
		if (owner == null) {
			owner = new NightmareVisionSpriteOwner(function(path) return paths.getAtlasFrames(path));
			owners.set(paths.root, owner);
		}
		return owner;
	}
	public static function peek(root:String):Null<NightmareVisionSpriteOwner> return owners.get(root);
}
