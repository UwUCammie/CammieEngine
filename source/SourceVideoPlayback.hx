package;

/**
	Decoder-free playback maths shared by the script-facing video sprites, so
	every layer clamps volume and maps progress the same way.
*/
class SourceVideoPlayback {
	/** Scripts hand volume in as 0..1; anything else (including NaN) is pulled into range. */
	public static function clampVolume(value:Float):Float {
		if (Math.isNaN(value) || value <= 0) return 0.0;
		return value >= 1 ? 1.0 : value;
	}

	/** Playback rates at or below zero would stall or reverse the decoder. */
	public static function safeRate(value:Float):Float
		return Math.isNaN(value) || value <= 0 ? 1.0 : value;

	/** Rate a clip follows from its host state's `playbackRate`, or NaN when the
		host has no usable one. Unlike safeRate this never invents 1: a clip that
		only follows its host keeps whatever rate the decoder already has. */
	public static function hostRate(value:Dynamic):Float {
		if (value == null) return Math.NaN;
		var rate = Std.parseFloat(Std.string(value));
		return Math.isFinite(rate) && rate > 0 ? rate : Math.NaN;
	}

	/** 0..1 position through the clip, 0 while the length is still unknown. */
	public static function progress(timeMs:Float, lengthMs:Float):Float {
		if (Math.isNaN(timeMs) || Math.isNaN(lengthMs) || lengthMs <= 0) return 0.0;
		var value = timeMs / lengthMs;
		return value <= 0 ? 0.0 : value >= 1 ? 1.0 : value;
	}

	/** Millisecond target for a 0..1 seek, or -1 when the clip has no length yet. */
	public static function seekTime(progressValue:Float, lengthMs:Float):Int {
		if (Math.isNaN(lengthMs) || lengthMs <= 0) return -1;
		var clamped = Math.isNaN(progressValue) || progressValue <= 0 ? 0.0 : progressValue >= 1 ? 1.0 : progressValue;
		return Std.int(clamped * lengthMs);
	}

	/** Insert so higher priorities run first and equal ones keep registration order,
		the same order lime's Event gives decoder listeners. */
	public static function insertByPriority(list:Array<SourceVideoCallback>, entry:SourceVideoCallback):Void {
		var index = list.length;
		while (index > 0 && list[index - 1].priority < entry.priority) index--;
		list.insert(index, entry);
	}

	/** Runs every registered callback once, dropping the `once` ones afterwards. */
	public static function dispatch(list:Array<SourceVideoCallback>, invoke:Dynamic->Void):Void {
		if (list.length == 0) return;
		var snapshot = list.copy();
		for (entry in snapshot) if (entry.once) list.remove(entry);
		for (entry in snapshot) invoke(entry.callback);
	}
}

typedef SourceVideoCallback = {
	var callback:Dynamic;
	var once:Bool;
	var priority:Int;
}
