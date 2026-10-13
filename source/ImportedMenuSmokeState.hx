package;

import flixel.FlxG;
import flixel.FlxState;

/** Opt-in native acceptance starts at the real package picker. */
class ImportedMenuSmokeState extends FlxState {
	public override function create():Void {
		super.create();
		FlxG.autoPause = false;
		FlxG.sound.muted = true;
		PluginManager.init(); DifficultyManager.init(); ModifierState.init(); PlayerSettings.init();
		ImportedMenuSmokeHarness.start();
		LoadingState.loadAndSwitchState(new CodenameImportedModsState());
	}
}
