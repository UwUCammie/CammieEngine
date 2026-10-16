package;

import animate.FlxAnimate;
import animate.FlxAnimateController;

/** The animation controller of a V-Slice FunkinSprite loaded with a texture atlas.
 * V-Slice scripts play an atlas's frame labels and symbols by name straight through
 * `animation.play(name)`, without adding them first: the base game's controller adds
 * the animation the first time it is asked for, as a label before a symbol, once-only
 * and at the document's frame rate. The plain Animate controller only warns. */
@:access(animate.FlxAnimate)
class FunkinAtlasAnimationController extends FlxAnimateController {
	public function new(sprite:FlxAnimate) {
		super(sprite);
	}

	/** Whether `name` is, or can be made into, an animation of this sprite. */
	public function hasOrAddAnimation(name:String):Bool {
		if (name == null || name == '')
			return false;
		if (exists(name))
			return true;
		if (!hasAnimateAtlas)
			return false;
		var rate = _animate.library.frameRate;
		if (findFrameLabelIndices(name).length > 0 || labelInCollection(name)) {
			addByFrameLabel(name, name, rate, false);
			return exists(name);
		}
		if (_animate.library.getSymbol(name) != null) {
			addBySymbol(name, name, rate, false);
			return exists(name);
		}
		return false;
	}

	function labelInCollection(label:String):Bool {
		for (timeline in getCollectionTimelines())
			if (timeline != null && timeline.findFrameLabelIndices(label).length > 0)
				return true;
		return false;
	}

	override public function play(animName:String, force:Bool = false, reversed:Bool = false, frame:Int = 0):Void {
		if (!hasOrAddAnimation(animName)) {
			trace('Animation ' + animName + ' does not exist!');
			return;
		}
		super.play(animName, force, reversed, frame);
	}
}
