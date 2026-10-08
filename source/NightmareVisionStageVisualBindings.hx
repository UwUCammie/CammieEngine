package;

import flixel.addons.display.FlxBackdrop;

/** Shared stage-rendering classes exposed by the pinned Nightmare Vision preset. */
class NightmareVisionStageVisualBindings {
	public static inline var RGB_PALETTE_IMPORT = 'funkin.game.shaders.RGBPalette';
	public static inline var FLX_BACKDROP_IMPORT = 'flixel.addons.display.FlxBackdrop';

	public static function install(interp:NightmareVisionScriptInterp):Void {
		if (interp == null) throw '[nightmare-vision-visual] Missing source interpreter';

		// Nightmare Vision exposes FlxBackdrop as a bare preset global.
		interp.variables.set('FlxBackdrop', FlxBackdrop);

		// D-Sides and older Psych-derived scripts import this path. The pinned
		// NV source has no RGBPalette class, while the shared Psych palette has
		// the same channel and shader members used by these scripts.
		var palette:Dynamic = PsychRGBPalette;
		interp.bindImport(RGB_PALETTE_IMPORT, palette);
		interp.sourceClassScope().bindRuntimeClass(RGB_PALETTE_IMPORT, palette);

		// Keep explicitly qualified Flixel imports on the same native class.
		interp.bindImport(FLX_BACKDROP_IMPORT, FlxBackdrop);
		interp.sourceClassScope().bindRuntimeClass(FLX_BACKDROP_IMPORT, FlxBackdrop);
	}
}
