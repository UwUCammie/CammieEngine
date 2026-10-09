package;

/** Legacy NV atlas convenience, using the same owner-bound sprite base. */
@:keep
class NightmareVisionSpriteFromSheet extends NightmareVisionFlxSprite {
	var currentAnim:String;

	public function new(x:Float = 0, y:Float = 0, source:String, anim:String,
		?paths:NightmareVisionPaths, antialiasing:Bool = true) {
		super(x, y, null, paths);
		frames = requireOwnerPaths().getSparrowAtlas(source);
		animation.addByPrefix(anim, anim);
		animation.play(anim);
		currentAnim = anim;
		this.antialiasing = antialiasing;
	}

	public function adjust(fps:Int = 24, loop:Bool = true, playNow:Bool = true):Void {
		animation.remove(currentAnim);
		animation.addByPrefix(currentAnim, currentAnim, fps, loop);
		if (playNow) animation.play(currentAnim, true);
	}

	public function play(forced:Bool = false, reversed:Bool = false, frame:Int = 0):Void {
		// Preserve the declared public argument contract. The historical body
		// omitted forced and passed frame into Flixel's Bool reversed argument.
		animation.play(currentAnim, forced, reversed, frame);
	}
}
