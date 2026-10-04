package;

import flixel.FlxG;

/** Applies the native engine's frame cap settings, including its uncapped mode. */
@:access(flixel.FlxGame)
class FramerateOptionsCompat {
	// This value is used only for Flixel's finite internal step size while the
	// native display loop is uncapped. It is not the user's selected FPS cap.
	public static inline var UNLIMITED_UPDATE_FRAMERATE:Int = 60;

	public static function apply(options:Dynamic):Void {
		if (options == null || FlxG.game == null)
			return;

		var cap = OptionsHandler.sanitizeFpsCap(Reflect.field(options, "fpsCap"));
		// A high finite cap can make Flixel's fixed-step accumulation window
		// smaller than one clock tick, causing elapsed time to be discarded.
		// Variable timesteps preserve real elapsed time at every selected cap.
		FlxG.fixedTimestep = false;
		if (Reflect.field(options, "unlimitedFPS") == true) {
			// Variable timesteps let Flixel update on every native frame event.
			// Keep the legacy update-rate value finite for scripts and engine
			// calculations; the native stage itself receives Lime's uncapped 0.
			FlxG.updateFramerate = UNLIMITED_UPDATE_FRAMERATE;
			#if html5
			// Lime maps 60+ to requestAnimationFrame on browsers. A stage rate of
			// 0 would instead select its one-frame-per-second timer fallback.
			FlxG.drawFramerate = 60;
			#else
			FlxG.drawFramerate = 0;
			#end
			// FlxG's 0 draw-rate setter produces an infinite fixed-step catch-up
			// limit. Keep it finite in case an imported script later switches the
			// game back to fixed timestep mode.
			FlxG.game._maxAccumulation = 2000 / UNLIMITED_UPDATE_FRAMERATE - 1;
		} else {
			FlxG.updateFramerate = cap;
			FlxG.drawFramerate = cap;
		}
	}
}
