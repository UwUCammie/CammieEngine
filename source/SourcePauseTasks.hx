package;

import flixel.util.FlxTimer;
import flixel.tweens.FlxTween;

/** Source pause transitions visit current managers, including previously inactive tasks. */
class SourcePauseTasks {
	public static function setActive(active:Bool):Void {
		FlxTimer.globalManager.forEach(function(timer:FlxTimer) {
			if (!timer.finished) timer.active = active;
		});
		FlxTween.globalManager.forEach(function(tween:FlxTween) {
			if (!tween.finished) tween.active = active;
		});
	}
}
