package;

import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;

/** Native group traversal and transforms with shared source callbacks. */
@:build(SourceNativeClassAdapterMacro.build(true, false, true))
class PsychScriptClassSpriteGroup extends FlxTypedSpriteGroup<FlxSprite> implements SourceNativeClassAdapter {
	public function new(x:Float = 0, y:Float = 0, maxSize:Int = 0) {
		super(x, y, maxSize);
	}
}
