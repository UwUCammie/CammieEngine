package;

import animate.FlxAnimate;
import animate.FlxAnimateController;
import flixel.animation.FlxAnimation;

/** Psych aliases over the installed FlxAnimate controller's current clip. */
class PsychFlxAnimateController extends FlxAnimateController {
	var owner:FlxAnimate;

	/** Current frame of the active animation, matching the donor FlxAnimate API. */
	public var curFrame(get, set):Int;

	/** Number of frames in the active animation, matching the donor API's length. */
	public var length(get, never):Int;

	/** Psych exposes animation completion as a no-argument signal. */
	public var onComplete(default, null):PsychFlxAnimateCompleteSignal;

	public function new(sprite:FlxAnimate) {
		owner = sprite;
		super(sprite);
		onComplete = new PsychFlxAnimateCompleteSignal(this);
	}

	override public function destroy():Void {
		onComplete.destroy();
		super.destroy();
	}

	function get_curFrame():Int {
		var current = curAnim;
		return current == null ? 0 : current.curFrame;
	}

	function set_curFrame(value:Int):Int {
		var current:FlxAnimation = curAnim;
		if (current == null)
			return value;

		current.curFrame = value;
		// FlxAnimation.curFrame updates curIndex, which routes the selected atlas
		// frame through this controller's frameIndex setter. Do not write the
		// animation-local frame number directly to frameIndex: clips can contain
		// non-zero or reordered timeline indices.
		return value;
	}

	function get_length():Int {
		var current = curAnim;
		if (current != null)
			return current.numFrames;

		// Before a clip is selected, Psych callers can still inspect the main
		// atlas timeline length. Setting curFrame without an active clip is a
		// harmless no-op, as it is in the controller surface.
		return owner.library == null || owner.library.timeline == null
			? 0 : owner.library.timeline.frameCount;
	}
}
