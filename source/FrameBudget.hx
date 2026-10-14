package;

/**
	Time box for work that is drained a little each frame. One instance is
	reused: call `restart` when the frame's drain begins and `next` before each
	item. The first item always runs, so a queue can never stall.
**/
class FrameBudget {
	public var seconds:Float;
	/** Zero means no item cap, only the time box. */
	public var maxItems:Int;
	var clock:Void->Float;
	var startedAt:Float = 0;
	var started:Int = 0;

	public function new(seconds:Float, maxItems:Int = 0, ?clock:Void->Float) {
		this.seconds = seconds;
		this.maxItems = maxItems;
		this.clock = clock == null ? haxe.Timer.stamp : clock;
	}

	public function restart():Void {
		started = 0;
		startedAt = clock();
	}

	/** True when another item may start now. */
	public function next():Bool {
		if (started > 0) {
			if (maxItems > 0 && started >= maxItems)
				return false;
			var spent = clock() - startedAt;
			// A clock that steps backwards must not turn into an unlimited frame.
			if (spent >= seconds || spent < 0)
				return false;
		}
		started++;
		return true;
	}

	public inline function count():Int return started;
}
