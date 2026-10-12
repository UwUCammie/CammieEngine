package;

/** Retargetable bounded-time card movement. All geometry shares one easing clock. */
class FreeplayCardMotion {
	public static inline var DURATION:Float = 0.18;
	public var x:Float = 0;
	public var y:Float = 0;
	public var height:Float = FreeplayBrowserLayout.ROW_HEIGHT;
	public var focus:Float = 0;
	public var targetX(default, null):Float = 0;
	public var targetY(default, null):Float = 0;
	var targetHeight:Float = FreeplayBrowserLayout.ROW_HEIGHT;
	var targetFocus:Float = 0;
	var fromX:Float = 0;
	var fromY:Float = 0;
	var fromHeight:Float = FreeplayBrowserLayout.ROW_HEIGHT;
	var fromFocus:Float = 0;
	var time:Float = DURATION;
	public var initialized(default, null):Bool = false;
	public function new() {}
	public function place(x:Float, y:Float):Void {
		this.x = targetX = x; this.y = targetY = y; initialized = true;
	}
	public function target(x:Float, y:Float, height:Float, selected:Bool, snap:Bool = false):Void {
		var focus = selected ? 1.0 : 0.0;
		if (!initialized) { place(x, y); snap = true; }
		if (snap) {
			this.x = targetX = x; this.y = targetY = y;
			this.height = targetHeight = height; this.focus = targetFocus = focus; time = DURATION;
			return;
		}
		if (targetX == x && targetY == y && targetHeight == height && targetFocus == focus) return;
		fromX = this.x; fromY = this.y; fromHeight = this.height; fromFocus = this.focus;
		targetX = x; targetY = y; targetHeight = height; targetFocus = focus; time = 0;
	}
	public function advance(elapsed:Float):Bool {
		if (time >= DURATION) return false;
		time = Math.min(DURATION, time + Math.max(0, elapsed));
		var remaining = 1 - time / DURATION;
		var amount = 1 - remaining * remaining * remaining;
		x = fromX + (targetX - fromX) * amount; y = fromY + (targetY - fromY) * amount;
		height = fromHeight + (targetHeight - fromHeight) * amount; focus = fromFocus + (targetFocus - fromFocus) * amount;
		return true;
	}
}
