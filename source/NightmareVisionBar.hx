package;

import flixel.FlxSprite;
import flixel.group.FlxSpriteGroup;
import flixel.math.FlxRect;
import flixel.math.FlxPoint;
import flixel.math.FlxMath;
import flixel.util.FlxColor;
import flixel.util.helpers.FlxBounds;

/** Actual Nightmare Vision source bar group, with owner-local image loading. */
@:keep
@:nullSafety
class NightmareVisionBar extends FlxSpriteGroup implements NightmareVisionIUiSprite
{
	public final bg:FlxSprite;
	public final leftBar:FlxSprite;
	public final rightBar:FlxSprite;

	public var valueFunction:Null<Void->Float> = null;

	public var percent(default, set):Float = 0;

	public var bounds:FlxBounds<Float> = new FlxBounds(0.0, 0.0);

	public var leftToRight(default, set):Bool = true;

	public var barCenter(default, null):Float = 0;


	public var barWidth(default, set):Int = 1;


	public var barHeight(default, set):Int = 1;


	public var barOffset:FlxPoint = new FlxPoint(3, 3);


	public var bgOffset:FlxPoint = new FlxPoint(0, 0);

	public function new(x:Float, y:Float, image:String = 'healthBar', ?valueFunction:Void->Float, boundX:Float = 0, boundY:Float = 1, ?owner:SourceBarOwner)
	{
		super(x, y);
		if (owner == null) throw "[source-bar] Missing selected owner";

		this.valueFunction = valueFunction;

		bg = new FlxSprite().loadGraphic(owner.image(image));
		bg.setPosition(bg.x + bgOffset.x, bg.y + bgOffset.y);

		@:bypassAccessor barWidth = Std.int(bg.width - 6);
		@:bypassAccessor barHeight = Std.int(bg.height - 6);

		leftBar = new FlxSprite().makeGraphic(Std.int(bg.width), Std.int(bg.height), FlxColor.WHITE);

		rightBar = new FlxSprite().makeGraphic(Std.int(bg.width), Std.int(bg.height), FlxColor.WHITE);
		rightBar.color = FlxColor.BLACK;

		add(leftBar);
		add(rightBar);
		add(bg);

		setBounds(boundX, boundY);

		regenerateClips();
	}

	public var enabled:Bool = true;

	override public function update(elapsed:Float)
	{
		if (!enabled)
		{
			super.update(elapsed);
			return;
		}

		if (valueFunction != null)
		{
			var value:Null<Float> = FlxMath.remapToRange(FlxMath.bound(valueFunction(), bounds.min, bounds.max), bounds.min, bounds.max, 0, 100);
			percent = (value != null ? value : 0);
		}
		else percent = 0;
		super.update(elapsed);
	}

	public function setBGOffset(x:Float, y:Float)
	{
		bgOffset.set(x, y);
		bg.x += bgOffset.x;
		bg.y += bgOffset.y;
	}

	public function setBounds(min:Float, max:Float)
	{
		bounds.min = min;
		bounds.max = max;
	}

	public function setColors(?left:FlxColor, ?right:FlxColor)
	{
		if (left != null) leftBar.color = left;
		if (right != null) rightBar.color = right;
	}

	public function updateBar():Void {
		if (leftBar == null || rightBar == null) return;
		barCenter = SourceBarLayout.apply(leftBar, rightBar, bg, barOffset, barWidth, barHeight, percent, leftToRight, bgOffset.x, bgOffset.y);
	}

	public function regenerateClips()
	{
		if (leftBar != null)
		{
			if (Std.int(leftBar.frameWidth) != Std.int(bg.frameWidth) || Std.int(leftBar.frameHeight) != Std.int(bg.frameHeight))
			{
				leftBar.makeGraphic(Std.int(bg.width), Std.int(bg.height), FlxColor.WHITE);
			}
			else
			{
				leftBar.setGraphicSize(Std.int(bg.width), Std.int(bg.height));
			}
			leftBar.updateHitbox();
			leftBar.clipRect = new FlxRect(0, 0, Std.int(bg.width), Std.int(bg.height));
		}
		if (rightBar != null)
		{
			if (rightBar.frameWidth != Std.int(bg.frameWidth) || rightBar.frameHeight != Std.int(bg.frameHeight))
			{
				rightBar.makeGraphic(Std.int(bg.width), Std.int(bg.height), FlxColor.WHITE);
			}
			else
			{
				rightBar.setGraphicSize(Std.int(bg.width), Std.int(bg.height));
			}
			rightBar.updateHitbox();
			rightBar.clipRect = new FlxRect(0, 0, Std.int(bg.width), Std.int(bg.height));
		}
		updateBar();
	}

	private function set_percent(value:Float)
	{
		var doUpdate:Bool = false;
		if (value != percent) doUpdate = true;
		percent = value;

		if (doUpdate) updateBar();
		return value;
	}

	private function set_leftToRight(value:Bool)
	{
		leftToRight = value;
		updateBar();
		return value;
	}

	private function set_barWidth(value:Int)
	{
		barWidth = value;
		regenerateClips();
		return value;
	}

	private function set_barHeight(value:Int)
	{
		barHeight = value;
		regenerateClips();
		return value;
	}

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
}
