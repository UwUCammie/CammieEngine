package;

import animate.FlxAnimate;
import animate.FlxAnimateFrames.FlxAnimateSettings;
import flixel.system.FlxAssets.FlxGraphicAsset;

/**
	FlxAnimate surface used by imported Psych stage classes.

	The installed flixel-animate API exposes `anim` as a controller, while
	Psych's FlxAnimate exposes the active animation's `curFrame` and `length` on
	that property. Keep the installed renderer and atlas implementation while adapting the
	controller fields and preserving the donor's authoring-space origin.
*/
class PsychFlxAnimateCompat extends FlxAnimate {
	public function new(?x:Float = 0, ?y:Float = 0, ?simpleGraphic:FlxGraphicAsset,
		?settings:FlxAnimateSettings) {
		super(x, y, simpleGraphic, settings);
		// Psych's atlas instance origin is authored in Animate stage space. Keep
		// that origin by default; scripts can still opt out after construction.
		applyStageMatrix = true;
		// FlxAnimate owns the setter that also updates FlxSprite.animation.
		Reflect.setProperty(this, 'anim', new PsychFlxAnimateController(this));
	}
}
