package;

/** The one key that skips a cutscene: Left Alt.
 *
 * Flixel reports both Alt keys as one, so the press is taken from the window,
 * which tells them apart. A press counts once, for the frame that first asks
 * about it, and only for a short while: a press made when nothing could be
 * skipped must not skip a cutscene that starts later. */
class CutsceneSkipKey {
	/** Seconds a press stays usable. */
	public static inline var WINDOW:Float = 0.25;
	/** Set by checks and the smoke harness in place of a real key press. */
	public static var forced:Bool = false;

	static var installed:Bool = false;
	static var held:Bool = false;
	static var pressedAt:Float = Math.NEGATIVE_INFINITY;
	static var claimedFrame:Int = -1;

	/** Whether a press made at `pressedAt` may still be acted on at `now`. */
	public static function fresh(pressedAt:Float, now:Float):Bool
		return Math.isFinite(pressedAt) && now >= pressedAt && now - pressedAt <= WINDOW;

	/** True during the frame in which Left Alt went down. */
	public static function pressed():Bool {
		if (forced) return true;
		#if (sys && !eval)
		install();
		var frame = flixel.FlxG.game.inputFrame;
		if (claimedFrame == frame) return true;
		if (!fresh(pressedAt, haxe.Timer.stamp())) return false;
		// Every caller in this frame sees the press; later frames do not.
		pressedAt = Math.NEGATIVE_INFINITY; claimedFrame = frame;
		return true;
		#else
		return false;
		#end
	}

	#if (sys && !eval)
	static function install():Void {
		if (installed) return;
		var window = lime.app.Application.current == null ? null : lime.app.Application.current.window;
		if (window == null) return;
		installed = true;
		window.onKeyDown.add(function(key, _) {
			if (key != lime.ui.KeyCode.LEFT_ALT) return;
			// Holding the key repeats the event; only the first one is a press.
			if (!held) pressedAt = haxe.Timer.stamp();
			held = true;
		});
		window.onKeyUp.add(function(key, _) if (key == lime.ui.KeyCode.LEFT_ALT) held = false);
	}
	#end
}
