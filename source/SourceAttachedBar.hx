package;

import flixel.FlxSprite;
import flixel.ui.FlxBar;
import flixel.ui.FlxBar.FlxBarFillDirection;

/**
 * A FlxBar that can follow a separately-owned background sprite like a source
 * engine bar group. The background remains owned by its state and is never
 * added to or destroyed by this object.
 */
@:keep
class SourceAttachedBar extends FlxBar
{
	/** The currently attached background, exposed for identity checks. */
	@:keep public var backgroundFollower(default, null):FlxSprite;

	var backgroundAlphaMultiplier:Float = 1;
	var lastAppliedAlpha:Float = 1;

	public function new(x:Float = 0, y:Float = 0, ?direction:FlxBarFillDirection, width:Int = 100, height:Int = 10,
		?parentRef:Dynamic, variable:String = "", min:Float = 0, max:Float = 100, showBorder:Bool = false)
	{
		// Keep the full FlxBar constructor surface. No follower is installed until
		// after this call, so virtual position setters during base construction
		// cannot move a background prematurely.
		super(x, y, direction, width, height, parentRef, variable, min, max, showBorder);
		lastAppliedAlpha = alpha;
	}

	/**
	 * Attach or replace the separate background while preserving its authored
	 * offset. Reattaching the same object is idempotent.
	 */
	@:keep public function attachBackground(background:FlxSprite):SourceAttachedBar
	{
		if (background == backgroundFollower)
			return this;

		backgroundFollower = background;
		lastAppliedAlpha = alpha;
		backgroundAlphaMultiplier = background == null ? 1 : (alpha > 0 ? background.alpha / alpha : background.alpha);
		return this;
	}

	override function set_x(value:Float):Float
	{
		var oldX = x;
		var applied = super.set_x(value);
		var background = backgroundFollower;
		if (background != null)
			background.x += applied - oldX;
		return applied;
	}

	override function set_y(value:Float):Float
	{
		var oldY = y;
		var applied = super.set_y(value);
		var background = backgroundFollower;
		if (background != null)
			background.y += applied - oldY;
		return applied;
	}

	override function set_alpha(value:Float):Float
	{
		var applied = super.set_alpha(value);
		var background = backgroundFollower;
		if (background != null)
		{
			// Direct edits to the background remain meaningful. Learn its current
			// local-alpha factor before applying the bar's new clamped alpha.
			if (lastAppliedAlpha > 0)
				backgroundAlphaMultiplier = background.alpha / lastAppliedAlpha;
			background.alpha = clampAlpha(applied * backgroundAlphaMultiplier);
		}
		lastAppliedAlpha = applied;
		return applied;
	}

	static inline function clampAlpha(value:Float):Float
	{
		return value < 0 ? 0 : (value > 1 ? 1 : value);
	}

	override public function destroy():Void
	{
		// The background belongs to the surrounding state, not this FlxBar.
		backgroundFollower = null;
		backgroundAlphaMultiplier = 1;
		lastAppliedAlpha = 1;
		super.destroy();
	}
}
