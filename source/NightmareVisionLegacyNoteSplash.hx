package;

/** Historical source class identity with coordinate/HSL setup over the shared sprite. */
@:keep
class NightmareVisionLegacyNoteSplash extends NightmareVisionNoteSplash {
	public function new(x:Float = 0, y:Float = 0, note:Int = 0,
		?owner:NightmareVisionNoteSplash.NightmareVisionNoteSplashOwner) {
		super(x, y, note, 0, owner, true);
	}
}
