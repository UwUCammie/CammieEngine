package;

import flixel.FlxG;
import flixel.FlxObject;
import flixel.math.FlxMath;
import flixel.util.FlxTimer;

/**
	V-Slice's interval shake (funkin.effects.IntervalShake): every `interval`
	seconds the object jumps to a random offset around where it started, with an
	intensity (a fraction of the object's width) that moves from the start value
	to the end value, then it returns to its starting position. Scripts reach it
	by name, so its static API matches V-Slice's.
**/
class IntervalShake {
	static var boundObjects:Map<FlxObject, IntervalShake> = new Map();

	public var object(default, null):FlxObject;
	public var timer(default, null):FlxTimer;
	public var startIntensity(default, null):Float = 0;
	public var endIntensity(default, null):Float = 0;
	public var duration(default, null):Float = 0;
	public var interval(default, null):Float = 0;
	public var ease(default, null):Float->Float;
	public var completionCallback(default, null):IntervalShake->Void;
	public var progressCallback(default, null):IntervalShake->Void;
	public var scale(default, null):Float = 0;
	public var _secondsSinceStart(default, null):Float = 0;

	var initialX:Float = 0;
	var initialY:Float = 0;

	/** Shake `object`; a call for an object that is already shaking returns its running shake. */
	public static function shake(object:FlxObject, duration:Float = 1, interval:Float = 0.04, startIntensity:Float = 0,
			endIntensity:Float = 0, ?ease:Float->Float, ?completionCallback:IntervalShake->Void,
			?progressCallback:IntervalShake->Void):IntervalShake {
		if (object == null)
			return null;
		var running = boundObjects.get(object);
		// A state switch clears every timer without finishing it; such a shake is over.
		if (running != null && running.timer != null && !running.timer.finished && running.timer.active)
			return running;
		if (interval <= 0)
			interval = FlxG.elapsed;
		var shake = new IntervalShake();
		shake.object = object;
		shake.duration = duration;
		shake.interval = interval;
		shake.startIntensity = startIntensity;
		shake.endIntensity = endIntensity;
		shake.ease = ease;
		shake.completionCallback = completionCallback;
		// V-Slice's start() never stores the progress callback, so mods built against
		// it never see that callback run; storing it here would run code they never ran.
		shake.initialX = object.x;
		shake.initialY = object.y;
		boundObjects.set(object, shake);
		// V-Slice's loop count: a duration of 0 gives 0 loops, which FlxTimer runs forever.
		shake.timer = new FlxTimer().start(interval, shake.progress, Std.int(duration / interval));
		return shake;
	}

	public static function isShaking(object:FlxObject):Bool
		return object != null && boundObjects.exists(object);

	public static function stopShaking(object:FlxObject):Void {
		var shake = object == null ? null : boundObjects.get(object);
		if (shake != null)
			shake.stop();
	}

	function new() {}

	/** End early and put the object back where it started. */
	public function stop():Void {
		if (timer != null)
			timer.cancel();
		restore();
		release();
	}

	function progress(source:FlxTimer):Void {
		_secondsSinceStart += interval;
		scale = duration > 0 ? _secondsSinceStart / duration : 0;
		if (ease != null)
			scale = 1 - ease(scale);
		var intensity = FlxMath.lerp(endIntensity, startIntensity, scale);
		// V-Slice scales both axes by the width, so this does too.
		var reach = intensity * object.width;
		object.x = initialX + FlxG.random.float(-reach, reach);
		object.y = initialY + FlxG.random.float(-reach, reach);
		if (progressCallback != null)
			progressCallback(this);
		if (source.loops > 0 && source.loopsLeft == 0) {
			restore();
			if (completionCallback != null)
				completionCallback(this);
			if (timer == source)
				release();
		}
	}

	function restore():Void {
		if (object == null)
			return;
		object.x = initialX;
		object.y = initialY;
	}

	function release():Void {
		if (object != null && boundObjects.get(object) == this)
			boundObjects.remove(object);
		object = null;
		timer = null;
		ease = null;
		completionCallback = null;
		progressCallback = null;
	}
}
