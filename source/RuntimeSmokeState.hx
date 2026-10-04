package;

import flixel.FlxG;
import flixel.FlxState;

/** Direct chart-to-PlayState entry point used only by RuntimeSmokeHarness. */
class RuntimeSmokeState extends FlxState {
	override public function create():Void {
		super.create();
		// Runtime smoke windows may never receive desktop focus when a matrix
		// launches several cases in succession.  Keep the bounded harness moving
		// even when Flixel would otherwise pause the state on focus loss.
		FlxG.autoPause = false;
		// Automated runs remain silent without writing the user's saved volume.
		FlxG.sound.muted = true;
		RuntimeSmokeHarness.installUncaughtErrorHandler();
		RuntimeSmokeHarness.start();
		var request = RuntimeSmokeHarness.config();
		var selection = RuntimeSmokeHarness.nextVisitSelection();
		if (request == null) {
			RuntimeSmokeHarness.fail('arguments', 'smoke configuration was not parsed');
			return;
		}
		try {
			var configurationError = RuntimeSmokeHarness.getConfigurationError();
			if (configurationError != '')
				throw configurationError;
			var rootError = RuntimeSmokeHarness.getRuntimeRootError();
			if (rootError != '')
				throw 'runtime root unavailable: ' + rootError;
			if (selection.songFolder == '')
				throw 'missing --smoke-song/--smoke-folder';
			if (selection.chart == '')
				throw 'missing --smoke-chart and no chart could be derived';

			// These are the same one-time setup calls made by TitleState.  They do
			// not modify OptionsHandler.options or any saved settings.
			if (!RuntimeImportSmokeHarness.consumePreparedRuntimeForPlay()) {
				PluginManager.init();
				DifficultyManager.init();
				ModifierState.init();
				PlayerSettings.init();
			}

			PlayState.isStoryMode = request.storyMode;
			PlayState.storyPlaylist = request.storyMode ? [selection.songFolder] : [];
			PlayState.storyWeek = 'RuntimeSmoke';
			PlayState.storyDifficulty = DifficultyManager.getDiffNum(selection.difficulty);
			PlayState.balls = 0;
			PlayState.watchedCutscene = false;
			ModifierState.isStoryMode = request.storyMode;
			// Long unattended runs need practice so missed notes cannot end the
			// window before mid-song events (character swaps, stage changes)
			// have been exercised.
			if (request.practice) {
				var practiceModifier = Reflect.field(ModifierState.namedModifiers, 'practice');
				if (practiceModifier != null)
					Reflect.setField(practiceModifier, 'value', true);
			}
			RuntimeSmokeHarness.markVisitSelection(selection);
			PlayState.SONG = Song.loadFromJson(selection.chart, selection.songFolder);
			if (request.ownerRoot != '') {
				var manifestPath = 'assets/data/' + selection.songFolder + '/' + CompatScriptManifest.FILE_NAME;
				if (!FNFAssets.exists(manifestPath))
					throw 'selected smoke owner has no chart manifest';
				var manifest = CompatScriptManifest.parse(FNFAssets.getText(manifestPath));
				if (CompatScriptManifest.destinationKey(CompatScriptManifest.selectedRoot(manifest))
					!= CompatScriptManifest.destinationKey(request.ownerRoot))
					throw 'selected smoke owner does not own this chart';
				if (!CodenameModRuntime.activateChartOwner(request.ownerRoot))
					throw 'selected smoke owner has no installed Codename state';
			}
			if (request.returnFreeplay) {
				// Direct smoke entry skips CategoryState, so seed the same merged
				// All-song rows the ordinary category chooser would pass to Freeplay.
				var globalSongs = RuntimeSmokeHarness.selectFreeplaySongs();
				var population = RuntimeSmokeHarness.freeplayReturnPopulation(cast globalSongs,
					function(songName:String):String
						return ImportedModDiscovery.ownerForSong(songName, 'assets/data'));
				if (!RuntimeSmokeHarness.freeplayReturnScopeValid('', '', population))
					throw 'return-Freeplay smoke requires an All list with base and imported rows';
				FreeplayState.currentSongList = globalSongs;
			}
			if (request.chartEditor)
				FlxG.switchState(new ChartingState());
			else
				FlxG.switchState(new PlayState());
		} catch (error:Dynamic) {
			RuntimeSmokeHarness.fail('load', Std.string(error));
		}
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		RuntimeSmokeHarness.tick(elapsed);
	}
}
