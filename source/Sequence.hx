package;

import flixel.util.FlxTimer;

/**
	V-Slice's timed callback list (funkin.util.Sequence, in TimerUtil.hx).

	Death animations, cutscenes and intros hand it events shaped
	`{time: seconds, callback: function}` and it runs each callback once at its
	time, measured from the start, on a single FlxTimer. The timer is a normal
	game timer, so it pauses with the game and is cleared on a state switch the
	same way every other script timer is.
**/
@:keep
class Sequence {
	final timer:FlxTimer = new FlxTimer();
	var events:Array<Dynamic>;
	var eventCount:Int = 0;
	var destroyed:Bool = false;

	/** Scales every event time; 2 plays the sequence at half speed. */
	public var multiplier:Float = 1;

	/** Destroy the timer once the last event has run. */
	public var autoDestroy:Bool = true;

	/** The next event to run, or null once the sequence has finished. */
	public var currentEvent(get, never):Dynamic;

	/** Pause or resume the sequence without losing its place. */
	public var running(get, set):Bool;

	/** True once every event has run, or after stop() or destroy(). */
	public var completed(get, never):Bool;

	public function new(events:Array<Dynamic>, mult:Float = 1, start:Bool = true, autoDestroy:Bool = true) {
		this.events = events == null ? [] : events.copy();
		if (this.events.length == 0)
			return;
		this.multiplier = Math.max(0, mult);
		this.autoDestroy = autoDestroy;
		// V-Slice treats a negative time as positive, like FlxTimer does.
		for (event in this.events)
			Reflect.setField(event, 'time', Math.abs(eventTime(event)));
		this.events.sort(function(a, b) return Reflect.compare(eventTime(a), eventTime(b)));
		timer.start(eventTime(currentEvent) * multiplier, onTimer);
		running = start;
	}

	function onTimer(_:FlxTimer):Void {
		var event = currentEvent;
		if (event == null)
			return;
		var callback:Dynamic = Reflect.field(event, 'callback');
		// A script error inside a timer callback is not caught by any script
		// runner and would stop the game; report it and keep the sequence going.
		if (Reflect.isFunction(callback))
			try Reflect.callMethod(null, callback, []) catch (error:Dynamic) trace('[sequence] event failed: ' + Std.string(error));
		// The callback may have stopped or destroyed this sequence.
		if (destroyed || eventCount >= events.length)
			return;
		eventCount++;
		if (!completed)
			timer.reset((eventTime(currentEvent) - eventTime(events[eventCount - 1])) * multiplier);
		else if (autoDestroy)
			destroy();
	}

	static function eventTime(event:Dynamic):Float {
		var value:Dynamic = event == null ? null : Reflect.field(event, 'time');
		return value == null ? 0 : value;
	}

	function get_currentEvent():Dynamic
		return events == null || eventCount >= events.length ? null : events[eventCount];

	function get_running():Bool
		return completed ? false : (timer.active && !timer.finished);

	function set_running(value:Bool):Bool {
		if (completed)
			return false;
		return timer.active = value;
	}

	function get_completed():Bool
		return events == null || eventCount >= events.length;

	/** Run the whole sequence again from its first event. */
	public function start():Void {
		if (events == null || events.length == 0) {
			trace('[sequence] There was an attempt to start a sequence with no events. Was it destroyed?');
			return;
		}
		eventCount = 0;
		timer.reset(eventTime(currentEvent) * multiplier);
	}

	/** Skip every remaining event. */
	public function stop():Void {
		eventCount = events == null ? 0 : events.length;
		timer.cancel();
	}

	public function destroy():Void {
		if (destroyed)
			return;
		destroyed = true;
		timer.cancel();
		timer.destroy();
		if (events != null)
			events.resize(0);
		eventCount = 0;
	}
}
