package;

import openfl.display.FPS;
import haxe.Timer;

/** OpenFL FPS display backed by a bounded rolling average of frame times. */
class AverageFPSCounter extends FPS {
	var frameRate:AverageFrameRate;
	var lastDisplayedCurrentFPS:Int = -1;
	var lastDisplayedAverageFPS:Int = -1;
	var lastDisplayedText:String = "";
	var lastFrameTimeMS:Float = Math.NaN;
	@:keep public var averageFPS(default, null):Int = 0;

	public function new(x:Float = 10, y:Float = 3, color:Int = 0xFFFFFF) {
		super(x, y, color);
		frameRate = new AverageFrameRate();
		text = "FPS: 0\nAvg FPS: 0";
	}

	@:noCompletion private #if !flash override #end function __enterFrame(deltaTime:Float):Void {
		// Preserve OpenFL's existing currentFPS calculation and script-facing
		// readback. Measure elapsed time independently of timer-event deltas;
		// repeated clock timestamps still represent separate rendered frames.
		super.__enterFrame(deltaTime);
		recordFrameAt(Timer.stamp() * 1000);
		if (currentFPS != lastDisplayedCurrentFPS || averageFPS != lastDisplayedAverageFPS) {
			lastDisplayedText = "FPS: " + currentFPS + "\nAvg FPS: " + averageFPS;
			lastDisplayedCurrentFPS = currentFPS;
			lastDisplayedAverageFPS = averageFPS;
		}
		// The base FPS implementation can rewrite its first line independently.
		// Restore the average line after such a write.
		if (text != lastDisplayedText)
			text = lastDisplayedText;
	}

	function recordFrameAt(nowMS:Float):Void {
		if (!Math.isFinite(nowMS))
			return;

		// A repeated millisecond-resolution timestamp is still a rendered
		// frame. Record its zero interval instead of dropping the callback.
		if (Math.isFinite(lastFrameTimeMS) && nowMS >= lastFrameTimeMS)
			if (frameRate.addFrameTime(nowMS - lastFrameTimeMS))
				averageFPS = frameRate.currentFPS;
		lastFrameTimeMS = nowMS;
	}
}
