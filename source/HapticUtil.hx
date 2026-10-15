package;

/**
	V-Slice's vibration helper (funkin.util.HapticUtil) on a build with no
	haptics device. V-Slice itself compiles every call to a no-op on desktop and
	reports `hapticsAvailable` as false, so scripts written for it check that
	flag and skip their rumble code. Keeping the same names here lets those
	scripts run their real logic instead of stopping on an unknown class.
**/
@:keep
class HapticUtil {
	/** V-Slice keeps its running amplitude tween here; nothing ever starts one on desktop. */
	public static var amplitudeTween:Dynamic = null;

	/** Always false: there is no vibration motor to drive. */
	public static var hapticsAvailable(get, never):Bool;

	/** The default preset V-Slice builds from its constants, kept for scripts that read it. */
	public static var defaultVibrationPreset(get, never):Dynamic;

	static function get_hapticsAvailable():Bool
		return false;

	static function get_defaultVibrationPreset():Dynamic
		return {period: 0.1, duration: 0.1, amplitude: 0.5, sharpness: 1.0};

	public static function vibrate(?period:Float, ?duration:Float, ?amplitude:Float, ?sharpness:Float,
			?targetHapticsModes:Array<Dynamic>):Void {}

	public static function vibrateByPreset(?vibrationPreset:Dynamic):Void {}

	public static function increasingVibrate(?startAmplitude:Float, ?targetAmplitude:Float, ?tweenDuration:Float):Void {}
}
