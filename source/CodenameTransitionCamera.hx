package;

import flixel.FlxCamera;

/** Transition-owned camera with the legacy Codename `flipY` script field.
	This fork's FlxCamera has no camera transform flag; mounted D-Sides transition
	scripts explicitly assign false, which keeps the native default orientation. */
class CodenameTransitionCamera extends FlxCamera {
	public var flipY:Bool = false;
}
