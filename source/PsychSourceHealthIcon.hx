package;

import flixel.FlxSprite;
import flixel.math.FlxPoint;
import flixel.math.FlxMath;
import flixel.util.FlxDestroyUtil;
using StringTools;

/** Actual Psych 1.0.4 icon sprite with owner-local loading. */
@:keep
class PsychSourceHealthIcon extends FlxSprite
{
	public var sprTracker:FlxSprite;
	private var isPlayer:Bool = false;
	private var char:String = '';

	var owner:Null<SourceHealthIconOwner>;
	function sourceOwner():SourceHealthIconOwner {
		if (owner == null) throw '[source-health-icon] Selected owner has been released';
		return owner;
	}
	public function new(char:String = 'face', isPlayer:Bool = false, ?allowGPU:Bool = true, ?owner:SourceHealthIconOwner)
	{
		super();
		if (owner == null) throw "[source-health-icon] Missing selected owner";
		this.owner = owner;
		this.isPlayer = isPlayer;
		changeIcon(char, allowGPU);
		scrollFactor.set();
	}

	override public function update(elapsed:Float)
	{
		super.update(elapsed);

		if (sprTracker != null)
			setPosition(sprTracker.x + sprTracker.width + 12, sprTracker.y - 30);
	}

	private var iconOffsets:Array<Float> = [0, 0];
	public function changeIcon(char:String, ?allowGPU:Bool = true) {
		if(this.char != char) {
			var selected = sourceOwner();
			var name = SourceHealthIconLoader.psychPath(char, selected);
			var graphic = selected.image(name, allowGPU);
			var iSize:Float = Math.round(graphic.width / graphic.height);
			loadGraphic(graphic, true, Math.floor(graphic.width / iSize), Math.floor(graphic.height));
			iconOffsets[0] = (width - 150) / iSize;
			iconOffsets[1] = (height - 150) / iSize;
			updateHitbox();

			animation.add(char, [for(i in 0...frames.frames.length) i], 0, false, isPlayer);
			animation.play(char);
			this.char = char;

			if(char.endsWith('-pixel'))
				antialiasing = false;
			else
				antialiasing = selected.antialiasing();
		}
	}

	public var autoAdjustOffset:Bool = true;
	override public function updateHitbox()
	{
		super.updateHitbox();
		if(autoAdjustOffset)
		{
			offset.x = iconOffsets[0];
			offset.y = iconOffsets[1];
		}
	}

	public function getCharacter():String {
		return char;
	}
	override public function destroy():Void {owner = null;super.destroy();}
}
