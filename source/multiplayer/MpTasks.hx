package multiplayer;

#if sys
import sys.thread.Deque;
import sys.thread.Thread;
#end

/** Run blocking work on a worker thread and hand its result back on the main thread,
 * where every Flixel object may be touched. pump() runs once per frame. */
class MpTasks {
	#if sys
	static var finished:Deque<Void->Void> = new Deque();
	#end
	static var installed:Bool = false;
	static var ticks:Array<Void->Void> = [];

	public static function install():Void {
		if (installed)
			return;
		installed = true;
		flixel.FlxG.signals.postUpdate.add(pump);
	}

	public static function run<T>(work:Void->T, done:T->Void, ?failed:String->Void):Void {
		install();
		#if sys
		Thread.create(function() {
			var result:Null<T> = null;
			var error:Null<String> = null;
			try result = work() catch (failure:Dynamic) error = Std.string(failure);
			finished.add(function() {
				if (error != null) {
					if (failed != null)
						failed(error);
				} else
					done(result);
			});
		});
		#else
		if (failed != null)
			failed('Multiplayer needs a native build.');
		#end
	}

	/** Call `tick` every frame until it is removed. */
	public static function every(tick:Void->Void):Void {
		install();
		if (ticks.indexOf(tick) < 0)
			ticks.push(tick);
	}

	public static function stop(tick:Void->Void):Void
		ticks.remove(tick);

	static function pump():Void {
		#if sys
		while (true) {
			var callback = finished.pop(false);
			if (callback == null)
				break;
			callback();
		}
		#end
		for (tick in ticks.copy())
			tick();
	}
}
