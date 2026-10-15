package;

import flixel.FlxG;

/**
	Connects the V-Slice registry facades to the engine: which import is active,
	the difficulty list, chart naming and week completion all come from the
	existing engine services, and `LoadingState.loadPlayState` starts a song the
	same way Freeplay and Story Mode do (chart folder plus difficulty suffix).
*/
class VSliceGameBinding {
	static var installed:Bool = false;

	/** Install the engine hooks once; every script interpreter calls this when it seeds the registries. */
	public static function install():Void {
		if (installed)
			return;
		installed = true;
		VSliceRegistryCatalog.ownerRoots = activeOwnerRoots;
		VSliceRegistryCatalog.defaultDifficulty = defaultDifficultyName;
		VSliceRegistryCatalog.chartSuffix = DifficultyManager.difficultySuffixFromChartFile;
		VSliceRegistryCatalog.difficultyNames = DifficultyManager.getDifficultyNames;
		VSliceRegistryCatalog.weekCompleted = function(key:String):Bool {
			try return @:privateAccess StoryMenuState.weekCompleted(key) catch (_:Dynamic) return false;
		};
	}

	/** The active import menu session first, then the import that owns the chart being played. */
	static function activeOwnerRoots():Array<String> {
		var roots:Array<String> = [];
		try roots = ImportedMenuEntry.activeOwnerRoots() catch (_:Dynamic) {}
		if (roots == null)
			roots = [];
		if (PlayState.SONG != null) {
			var owner = '';
			try owner = ImportedModDiscovery.ownerForSong(Song.storageFolder(PlayState.SONG), 'assets/data') catch (_:Dynamic) {}
			if (owner != '' && roots.indexOf(owner) < 0)
				roots.push(owner);
		}
		return roots;
	}

	static function defaultDifficultyName():String {
		try {
			var names = DifficultyManager.getDifficultyNames();
			var index = DifficultyManager.getDefaultDiff();
			if (index >= 0 && index < names.length)
				return names[index].toLowerCase();
		} catch (_:Dynamic) {}
		return 'normal';
	}

	/** Engine difficulty index for a V-Slice difficulty id, or -1 when the engine has no such difficulty. */
	static function difficultyIndex(difficulty:String):Int {
		var names = DifficultyManager.getDifficultyNames();
		for (index in 0...names.length)
			if (names[index] != null && names[index].toLowerCase() == difficulty)
				return index;
		return -1;
	}

	/**
		V-Slice `LoadingState.loadPlayState({targetSong, targetDifficulty,
		targetVariation, ...}, shouldStopMusic)`. Story mode follows
		`PlayStatePlaylist`: the remaining playlist ids become the engine's story
		playlist. Returns false (and logs why) when the song cannot be started.
	*/
	public static function loadPlayState(params:Dynamic, shouldStopMusic:Bool = false, asSubState:Bool = false):Bool {
		install();
		var storyMode = VSlicePlayStatePlaylist.isStoryMode;
		var plan = VSliceSongLaunchPlan.resolve(params, storyMode);
		if (plan.error != null) {
			trace('[vslice-load-play-state] ' + plan.error);
			return false;
		}
		var index = difficultyIndex(plan.difficulty);
		if (index < 0) {
			trace('[vslice-load-play-state] The engine has no difficulty named ' + plan.difficulty);
			return false;
		}
		var chart = plan.folder + DifficultyManager.getDiffEnding(index);
		var song = Song.loadFromJson(chart, plan.folder);
		if (song == null) {
			trace('[vslice-load-play-state] Could not load chart ' + chart);
			return false;
		}
		PlayState.SONG = song;
		PlayState.isStoryMode = storyMode;
		PlayState.storyDifficulty = index;
		PlayState.balls = 0;
		PlayState.watchedCutscene = false;
		ModifierState.isStoryMode = storyMode;
		if (storyMode) {
			PlayState.storyPlaylist = plan.storyFolders;
			PlayState.defaultPlaylistLength = plan.storyFolders.length;
			PlayState.campaignScore = VSlicePlayStatePlaylist.campaignScore;
			PlayState.campaignAccuracy = 0;
			PlayState.campaignMisses = 0;
			// A retry from the end-of-week screen replays StoryMenuState's copy of
			// the week, so it must hold this playlist rather than an older week.
			StoryMenuState.storySongPlaylist = plan.storyFolders.copy();
			// The week key decides where the campaign score is saved and which
			// weeks it unlocks. Without a known level, keep it out of every real
			// week instead of crediting whichever week was played last.
			var week = plan.levelKey;
			PlayState.storyWeek = week == null ? '' : week;
			PlayState.storyWeekNum = -1;
		} else {
			Song.attachFreeplayScoreSongId(PlayState.SONG, plan.folder);
		}
		if (shouldStopMusic && FlxG.sound.music != null)
			FlxG.sound.music.stop();
		LoadingState.loadAndSwitchState(new PlayState());
		return true;
	}
}
