package;

/** Psych's tagged FlxAnimate sprite with the Lua ModchartSprite play surface. */
class PsychModchartAnimateSprite extends PsychFlxAnimateCompat {
	public var animOffsets:Map<String, Array<Float>> = new Map<String, Array<Float>>();

	public function new(?x:Float = 0, ?y:Float = 0) {
		super(x, y);
		antialiasing = flixel.FlxSprite.defaultAntialiasing;
	}

	public function playAnim(name:String, forced:Bool = false,
		?reversed:Bool = false, ?startFrame:Int = 0):Void {
		anim.play(name, forced, reversed, startFrame);
		var animationOffset = animOffsets.get(name);
		if (animationOffset != null && animationOffset.length >= 2)
			offset.set(animationOffset[0], animationOffset[1]);
	}

	public function addOffset(name:String, x:Float, y:Float):Void {
		if (name != null)
			animOffsets.set(name, [x, y]);
	}
}
