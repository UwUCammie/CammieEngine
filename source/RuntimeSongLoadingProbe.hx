package;

import flixel.FlxG;

/** Opt-in native check of the real Freeplay chart-preparation launch. */
@:access(FreeplayState)
@:access(RuntimeSmokeHarness)
class RuntimeSongLoadingProbe {
	static var launched:Bool = false;
	public static function install():Void {
		#if sys
		if (!RuntimeSmokeHarness.enabled() || !RuntimeSmokeHarness.config().freeplay
			|| Sys.args().indexOf('--verify-song-loading-phases') < 0) return;
		if (Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') == null) throw 'Loading probe requires a private save';
		// Match main-menu entry before registry generations reconcile the list.
		FreeplayState.curCategory = 'All';
		FlxG.signals.postUpdate.add(observe);
		#end
	}
	static function observe():Void {
		if (launched || RuntimeSmokeHarness.finished || !Std.isOfType(FlxG.state, FreeplayState)) return;
		FlxG.sound.muted = true;
		if (ImportRefreshManager.browseTick().busy) return;
		try {
			var selection = RuntimeSmokeHarness.nextVisitSelection();
			var menu:FreeplayState = cast FlxG.state;
			for (index in 0...menu.songs.length) {
				if (menu.songs[index].songName.toLowerCase() != selection.songFolder.toLowerCase()) continue;
				var difficulty = DifficultyManager.getDiffNum(selection.difficulty);
				if (!menu.availabilityAllowsLaunch(index, difficulty)) return;
				if (!OptionsHandler.options.skipModifierMenu) throw 'Loading probe requires skipModifierMenu';
				RuntimeSmokeHarness.markVisitSelection(selection);
				launched = true;
				if (!menu.launchSelection(index, difficulty)) throw 'Freeplay refused loading probe chart';
				return;
			}
			throw 'Loading probe chart absent from Freeplay';
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('loading-probe', Std.string(error));
	}
}
