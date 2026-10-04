package;

import haxe.Timer;
import openfl.display.FPS;
import openfl.events.Event;
import openfl.system.System;
import openfl.text.TextField;
import openfl.text.TextFormat;
// thank you verwex for saving me time :blush:
/**
 * FPS class extension to display memory usage.
 * @author Kirill Poletaev
 */
class MemoryCounter extends TextField {
	static inline var SAMPLE_INTERVAL_MS:Float = 500;
	private var times:Array<Float>;
	private var memPeak:Float = 0;
	private var lastSampleAtMS:Float = Math.NaN;

	public function new(inX:Float = 10.0, inY:Float = 10.0, inCol:Int = 0x000000) {
		super();

		x = inX;
		y = inY;
		selectable = false;
		defaultTextFormat = new TextFormat("_sans", 12, inCol);

		addEventListener(Event.ENTER_FRAME, onEnter);
		width = 150;
		height = 70;
	}

	private function onEnter(_) {
		sampleAt(Timer.stamp() * 1000);
	}

	/** The counter is display-only; sample the native heap twice per second. */
	private function sampleAt(nowMS:Float):Void {
		if (!visible) {
			lastSampleAtMS = Math.NaN;
			return;
		}
		if (!Math.isFinite(nowMS))
			return;
		if (Math.isFinite(lastSampleAtMS) && nowMS >= lastSampleAtMS
			&& nowMS - lastSampleAtMS < SAMPLE_INTERVAL_MS)
			return;
		lastSampleAtMS = nowMS;

		// totalMemory is a 32-bit Int and wraps negative past 2GB
		var mem:Float = Math.round(System.totalMemoryNumber / 1024 / 1024 * 100) / 100;
		if (mem > memPeak)
			memPeak = mem;

		var nextText = Main.fpsCounter != null && Main.fpsCounter.visible
			? "\n\nMEM: " + mem + " MB\nMEM peak: " + memPeak + " MB"
			: "MEM: " + mem + " MB\nMEM peak: " + memPeak + " MB";
		if (text != nextText)
			text = nextText;
	}
}
