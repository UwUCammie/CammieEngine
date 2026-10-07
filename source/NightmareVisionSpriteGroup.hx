package;

import flixel.group.FlxSpriteGroup;

/** Generic source construction keeps the native group parent and its virtual
 * child transforms while supplying the five real source convenience methods. */
@:keep
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionSpriteGroup extends FlxSpriteGroup {
	public function new(x:Float = 0, y:Float = 0, maxSize:Int = 0, ?owner:NightmareVisionSpriteOwner) {
		super(x, y, maxSize);
		NightmareVisionSpriteMethods.bind(this, owner);
	}
}
