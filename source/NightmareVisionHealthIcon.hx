package;

import flixel.FlxSprite;
import flixel.math.FlxPoint;
import flixel.math.FlxMath;
import flixel.util.FlxDestroyUtil;
using StringTools;

/** Actual NV icon sprite with owner-local loading. */
@:keep
@:nullSafety
class NightmareVisionHealthIcon extends FlxSprite implements NightmareVisionIUiSprite
{

	public var sprTracker:Null<FlxSprite> = null;


	public var sprOffsets(default, null):FlxPoint = FlxPoint.get(10, -30);


	public var characterName(default, null):String = '';

	@:allow(funkin.states.editors.ChartEditorState)
	var updateOffset:Bool = true;

	var iconOffsets:Array<Float> = [0, 0];


	var isPlayer:Bool = false;


	public var frameCount(default, set):Int = 2;

	public var alphaMultipler(default, set):Float = 1;

	function set_alphaMultipler(v:Float):Float
	{
		alphaMultipler = FlxMath.bound(v, 0, 1);
		set_alpha(alpha);
		return alphaMultipler;
	}

	override function set_alpha(v:Float)
	{
		v = FlxMath.bound(v, 0, 1);
		v *= alphaMultipler;
		return super.set_alpha(v);
	}

	public function set_frameCount(value:Int)
	{
		frameCount = value;
		changeIcon(characterName, true);

		return value;
	}


	public var updateFrames:Bool = true;

	var owner:Null<SourceHealthIconOwner>;
	function sourceOwner():SourceHealthIconOwner {
		if (owner == null) throw '[source-health-icon] Selected owner has been released';
		return owner;
	}
	public function new(char:String = 'bf', isPlayer:Bool = false, ?owner:SourceHealthIconOwner)
	{
		super();
		if (owner == null) throw "[source-health-icon] Missing selected owner";
		this.owner = owner;
		this.isPlayer = isPlayer;
		changeIcon(char);
	}

	override public function update(elapsed:Float):Void
	{
		super.update(elapsed);

		if (sprTracker != null) setPosition(sprTracker.x + sprTracker.width + sprOffsets.x, sprTracker.y + sprOffsets.y);
	}


	public function changeIcon(char:String, forced:Bool = false):NightmareVisionHealthIcon
	{
		if (this.characterName == char && !forced) return this;

		this.characterName = char;

		var selected = sourceOwner();
		var name = SourceHealthIconLoader.nightmarePath(char, selected);
		final graphic = selected.image(name, false);

		loadGraphic(graphic, true, Math.floor(graphic.width / frameCount), Math.floor(graphic.height));
		iconOffsets[0] = (width - 150) / 2;
		iconOffsets[1] = (width - 150) / 2;
		updateHitbox();

		var c = [];
		for (i in 0...frameCount)
			c.push(i);

		animation.add(char, c, 0, false, isPlayer);
		animation.play(char);

		antialiasing = char.endsWith('-pixel') ? false : selected.antialiasing();

		return this;
	}

	override public function updateHitbox()
	{
		super.updateHitbox();

		if (updateOffset)
		{
			offset.x = iconOffsets[0];
			offset.y = iconOffsets[1];
		}
	}

	override public function destroy()
	{
		sprOffsets = FlxDestroyUtil.put(sprOffsets);
		owner = null;
		super.destroy();
	}


	public inline function updateIconAnim(health:Float):Void
	{
		if (!updateFrames) return;

		animation.frameIndex = health < 0.2 ? 1 : 0;
	}
}
