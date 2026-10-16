package;

import animate.FlxAnimate;

/** The Animate sprite imported V-Slice scripts get from `loadTextureAtlas`: an
 * ordinary FlxAnimate whose controller plays frame labels and symbols by name the
 * way the base game's FunkinSprite does. */
@:keep
class FunkinAtlasSprite extends FlxAnimate {
	override function initVars():Void {
		super.initVars();
		anim = new FunkinAtlasAnimationController(this);
	}
}
