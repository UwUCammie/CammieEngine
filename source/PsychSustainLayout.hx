package;

/** Psych 1.0.4 hold generation/geometry; native and NV use their own rules. */
class PsychSustainLayout {
	public static inline var SUSTAIN_SIZE:Float = 44;

	/** Preserve authored short/one-step holds; the native tap sentinel is not a Psych rule. */
	public static function holdLength(value:Dynamic):Float {
		var length:Float;
		if (Std.isOfType(value, String)) length = Std.parseFloat(StringTools.trim(cast value));
		else if (Std.isOfType(value, Float) || Std.isOfType(value, Int)) length = cast value;
		else return 0;
		return Math.isFinite(length) && length > 0 ? length : 0;
	}

	public static function sectionBpm(current:Float, changed:Bool, authored:Null<Float>):Float
		return changed && authored != null && Math.isFinite(authored) && authored > 0 ? authored : current;

	public static function stepCrochet(bpm:Float, fallback:Float):Float
		return Math.isFinite(bpm) && bpm > 0 ? 15000 / bpm : fallback;

	public static function segmentCount(length:Float, localStep:Float):Int {
		if (!Math.isFinite(length) || !Math.isFinite(localStep) || length <= 0 || localStep <= 0) return 0;
		return Math.round(length / localStep);
	}

	public static function segmentTime(headTime:Float, index:Int, localStep:Float):Float
		return headTime + index * localStep;

	/** Donor Note constructor stretches the previous piece before finalizing the current pixel cap. */
	public static function bodyStretchRatio(baseStep:Float, songSpeed:Float,
		pixelStage:Bool, currentEndHeight:Float):Float {
		var ratio = baseStep / 100 * 1.05 * songSpeed;
		if (pixelStage) ratio *= 1.19 * (6 / currentEndHeight);
		return ratio;
	}

	/** Donor PlayState applies local-BPM/rate correction after the final source frames exist. */
	public static function generationStretchRatio(localStep:Float, baseStep:Float,
		playbackRate:Float, pixelStage:Bool, previousFrameHeight:Float):Float {
		var ratio = pixelStage ? 1 : SUSTAIN_SIZE / previousFrameHeight;
		return ratio / playbackRate * (localStep / baseStep);
	}
}
