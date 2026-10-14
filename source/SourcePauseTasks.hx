package;

import flixel.util.FlxTimer;
import flixel.tweens.FlxTween;

/** Freezing and thawing the global timer and tween managers for a pause. */
class SourcePauseTasks {
	/** Source pause transitions visit current managers, including previously inactive tasks. */
	public static function setActive(active:Bool):Void {
		FlxTimer.globalManager.forEach(function(timer:FlxTimer) {
			if (!timer.finished) timer.active = active;
		});
		FlxTween.globalManager.forEach(function(tween:FlxTween) {
			if (!tween.finished) tween.active = active;
		});
	}

	/** Snapshot pause: stops only the tasks running now and adds them to the
	 * lists, so `thaw` restarts exactly those. Tasks a substate starts after
	 * this, and tasks that were already stopped, are left as they are. Calling
	 * it again while frozen adds the newer tasks without listing any twice,
	 * since a frozen task is no longer active. */
	public static function freezeRunning(timers:Array<FlxTimer>, tweens:Array<FlxTween>):Void {
		if (FlxTimer.globalManager != null) FlxTimer.globalManager.forEach(function(timer:FlxTimer) {
			if (timer != null && timer.active && !timer.finished) {
				timers.push(timer);
				timer.active = false;
			}
		});
		if (FlxTween.globalManager != null) FlxTween.globalManager.forEach(function(tween:FlxTween) {
			if (tween != null && tween.active && !tween.finished) {
				tweens.push(tween);
				tween.active = false;
			}
		});
	}

	/** Restarts what `freezeRunning` stopped, except tasks that finished in
	 * between, and empties the lists. */
	public static function thaw(timers:Array<FlxTimer>, tweens:Array<FlxTween>):Void {
		for (timer in timers)
			if (timer != null && !timer.finished) timer.active = true;
		for (tween in tweens)
			if (tween != null && !tween.finished) tween.active = true;
		timers.resize(0);
		tweens.resize(0);
	}
}
