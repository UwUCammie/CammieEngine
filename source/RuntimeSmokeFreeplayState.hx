package;

import flixel.FlxG;
import flixel.FlxState;
using StringTools;
/**
	Freeplay entry point used only by the `--smoke-freeplay` launch contract.

	Unlike RuntimeSmokeState (which goes straight to PlayState), this state
	hydrates FreeplayState.currentSongList from the live freeplay registry and
	switches into the real FreeplayState, so imported-mod modules, capsule
	hooks and icon builds all run exactly like a human entering freeplay.
	RuntimeSmokeHarness rides the global update/draw signals to scroll the
	list, leave the state and emit frame-pacing observations.
*/
class RuntimeSmokeFreeplayState extends FlxState {
	override public function create():Void {
		super.create();
		// Freeplay windows may never receive desktop focus under Xvfb.
		FlxG.autoPause = false;
		FlxG.sound.muted = true;
		RuntimeSmokeHarness.installUncaughtErrorHandler();
		RuntimeSmokeHarness.start();
		RuntimeSmokeHarness.installFrameStats();
		try {
			var rootError = RuntimeSmokeHarness.getRuntimeRootError();
			if (rootError != '')
				throw 'runtime root unavailable: ' + rootError;

			// same one-time setup calls TitleState makes before freeplay.
			// FreeplayState reads FlxG.save immediately (Highscore.load), and an
			// unbound save's data field is null - a hard crash on native - so the
			// save binding must happen exactly like TitleState does it.
			RuntimeSmokeHarness.markStep('plugin-init');
			if (!RuntimeImportSmokeHarness.consumePreparedRuntimeForPlay()) {
				PluginManager.init();
				DifficultyManager.init();
				ModifierState.init();
			}
			FlxG.save.bind("preferredSave", "bulbyVR");
			var preferredSave:Int = 0;
			if (Reflect.hasField(FlxG.save.data, "preferredSave")) {
				preferredSave = FlxG.save.data.preferredSave;
			} else {
				FlxG.save.data.preferredSave = 0;
			}
			FlxG.save.close();
			FlxG.save.bind("save" + preferredSave, 'bulbyVR');
			PlayerSettings.init();

			RuntimeSmokeHarness.markStep('registry-read');
			FreeplayState.currentSongList = RuntimeSmokeHarness.selectFreeplaySongs();
			// TitleState/MainMenuState leave the menu music playing before
			// freeplay opens.  Without it FlxG.sound.music is null and
			// FreeplayState.create's `FlxG.sound.music.playing` guard is a hard
			// crash on native, so start the same menu track here.
			FlxG.sound.playMusic(FNFAssets.getSound('assets/music/custom_menu_music/'
				+ CoolUtil.parseJson(FNFAssets.getJson('assets/music/custom_menu_music/custom_menu_music')).Menu
				+ '/freakyMenu'
				+ TitleState.soundExt));
			RuntimeSmokeHarness.markStep('freeplay-switch');
			LoadingState.loadAndSwitchState(new FreeplayState());
		} catch (error:Dynamic) {
			RuntimeSmokeHarness.fail('load', Std.string(error));
		}
	}
}
