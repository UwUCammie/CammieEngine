package;

/** Explicit source owner selected before Character reads definitions or atlases.
 * Native and Codename construction keep their existing omitted-context path. */
class SourceCharacterConstruction {
	public final root:String;
	public final engine:String;
	public final spriteOwner:Null<NightmareVisionSpriteOwner>;
	public final paths:Null<NightmareVisionPaths>;
	public function new(root:String, engine:String, ?spriteOwner:NightmareVisionSpriteOwner, ?paths:NightmareVisionPaths) {
		this.root = root;
		this.engine = engine;
		this.spriteOwner = spriteOwner;
		this.paths = paths;
	}
	public function requireActive():Void {
		if (spriteOwner != null) spriteOwner.requireActive();
	}
	public function resolve(name:String):Dynamic {
		requireActive();
		return Song.resolveCharacterVisualInManifest(name, root, true, engine);
	}
}
