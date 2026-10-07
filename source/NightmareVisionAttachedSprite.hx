package;

import flixel.FlxObject;
import flixel.FlxSprite;

/** Source sprite owns its node while borrowing the node's tracked object. */
@:keep
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionAttachedSprite extends FlxSprite
{
	public var attachedNode:NightmareVisionAttachedNode;

	public function new(?tracker:FlxObject)
	{
		super();
		attachedNode = new NightmareVisionAttachedNode(this, tracker);
	}

	override public function update(elapsed:Float)
	{
		super.update(elapsed);
		attachedNode.update(elapsed);
	}

	override public function destroy()
	{
		attachedNode.destroy();
		super.destroy();
	}
}
