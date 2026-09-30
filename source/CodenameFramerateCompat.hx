package;

import openfl.display.FPS;

/** Small shared adapter for Codename scripts that control the engine FPS
 * display. The display itself is the live native counter; debugMode remains
 * owner script state as it does in Codename's Framerate class. */
class CodenameFramerateCompat {
	static var shared:CodenameFramerateCompat;
	public var debugMode:Int = 0;
	public var instance:FPS;

	function new() {}

	/** Native hxcpp HScript reflection does not expose a static getter here.
	 * Keep one mutable source view and refresh its live counter on access. */
	public static function facade():CodenameFramerateCompat {
		if (shared == null) shared = new CodenameFramerateCompat();
		shared.instance = Main.fpsCounter;
		return shared;
	}
}
