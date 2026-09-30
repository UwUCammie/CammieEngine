package;

/**
 * Preserve absolute writes to Note.offset across FlxSprite.updateHitbox().
 * Each axis is independent so an authored Y offset does not freeze X when
 * a note style or receptor scale changes.
 */
class NoteOffsetState {
	public var x(default, null):Float = 0;
	public var y(default, null):Float = 0;
	var lastX:Null<Float> = null;
	var lastY:Null<Float> = null;
	var writtenX:Null<Float> = null;
	var writtenY:Null<Float> = null;

	public function new() {}

	/** Observe writes made between hitbox updates, before Flixel resets them. */
	public function capture(currentX:Float, currentY:Float, enabled:Bool):Void {
		if (!enabled)
			return;
		if (lastX != null && currentX != lastX)
			writtenX = currentX;
		if (lastY != null && currentY != lastY)
			writtenY = currentY;
	}

	/** Reapply script values after the current scale/style base is calculated. */
	public function finish(baseX:Float, baseY:Float):Void {
		x = writtenX == null ? baseX : writtenX;
		y = writtenY == null ? baseY : writtenY;
		lastX = x;
		lastY = y;
	}
}
