package;

import flixel.FlxBasic;
import flixel.FlxObject;
import flixel.FlxSprite;
import flixel.math.FlxPoint;
import flixel.util.FlxAxes;

/** Source attachment node. Root and tracked objects are borrowed. */
@:keep
@:nullSafety
class NightmareVisionAttachedNode extends FlxBasic
{
	public var root:Null<FlxObject> = null;
	public var tracked:Null<FlxObject> = null;
	public var copyAxis:FlxAxes = XY;
	public var copyAlpha:Bool = true;
	public var copyVisibility:Bool = true;
	public var copyAngle:Bool = true;
	public var positionOffset:FlxPoint = FlxPoint.get();
	public var angleOffset:Float = 0;
	public var alphaMultiplier:Float = 1;

	public function new(root:FlxObject, tracked:FlxObject)
	{
		super();
		this.root = root;
		this.tracked = tracked;
	}

	override public function update(elapsed:Float)
	{
		super.update(elapsed);
		updateRoot();
	}

	function updateRoot()
	{
		if (root != null && tracked != null) {
			if (copyAxis.x) root.x = tracked.x + positionOffset.x;
			if (copyAxis.y) root.y = tracked.y + positionOffset.y;
			if (copyVisibility) root.visible = tracked.visible;
			if (copyAngle) root.angle = tracked.angle + angleOffset;
			if (copyAlpha && root is FlxSprite && tracked is FlxSprite)
				(cast root:FlxSprite).alpha = (cast tracked:FlxSprite).alpha * alphaMultiplier;
		}
	}

	override public function destroy()
	{
		positionOffset.put();
		super.destroy();
	}
}
