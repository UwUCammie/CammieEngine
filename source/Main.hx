package;

import flixel.FlxG;
import flixel.FlxGame;
import flixel.FlxState;
import openfl.display.Sprite;
#if typebuild
import plugins.ExamplePlugin;
import plugins.ExamplePlugin.ExampleCharPlugin;
#end
class Main extends Sprite {
	#if sys
	public static var cwd:String;
	#end
	public static var distray:DisSoundTray;
	public static var fpsCounter:AverageFPSCounter;
	public static var memoryCounter:MemoryCounter;
	/** Root display used by owner-scoped Codename scripts that add native
	 * overlays to the game window. */
	public static var instance:Main;
	// set in preStateSwitch, read after old-state teardown
	static var leavingPlayState:Bool = false;
	static var importForegroundLease:Int = 0;
	/** Keep import workers behind gameplay/loading without blocking state swaps. */
	static function syncImportForegroundForState(next:FlxState):Void {
		var previous = importForegroundLease;
		importForegroundLease = Std.isOfType(next, PlayState) || Std.isOfType(next, LoadingState)
			? ImportWorkScheduler.beginGameplay() : 0;
		// Acquire the next lease first so consecutive gameplay states have no gap.
		ImportWorkScheduler.endGameplay(previous);
	}
	public function new() {
		#if typebuild
			// god is dead
			ExamplePlugin;
			ExampleCharPlugin;
		#end
		super();
		RuntimeStartupProbe.begin();
		ImportWorkScheduler.bindForegroundThread();
		SongGraphicRetention.bindOwnerThread();
		instance = this;
		#if sys
		RuntimeSmokeHarness.applyRuntimeRoot();
		RuntimeSmokeSaveIsolation.install(RuntimeImportSmokeHarness.enabled() || ImportedMenuSmokeHarness.enabled());
		cwd = Sys.getCwd();
		EngineMemory.applyStartupTuning(Sys.args());
		ImportRemovalManager.install();
		// Created by name for V-Slice atlas sprites, so it must be compiled in.
		FunkinAtlasSprite;
		RuntimeImportPerformanceProbe.run();
		#end
		var initialState:Class<FlxState> = TitleState;
		#if sys
		if (Sys.getEnv('CAMMIE_SHADER_COMPARE') != null)
			initialState = RuntimeShaderCompareState;
		else if (ImportedMenuSmokeHarness.enabled())
			initialState = ImportedMenuSmokeState;
		else if (RuntimeImportSmokeHarness.enabled())
			initialState = RuntimeImportSmokeState;
		else if (RuntimeSmokeHarness.config() != null && RuntimeSmokeHarness.config().returnFreeplay)
			initialState = RuntimeSmokeState;
		else if (RuntimeSmokeHarness.config() != null && RuntimeSmokeHarness.config().chartEditor)
			initialState = RuntimeSmokeChartingState;
		else if (RuntimeSmokeHarness.config() != null && RuntimeSmokeHarness.config().freeplay)
			initialState = RuntimeSmokeFreeplayState;
		// A startup profile run observes the ordinary TitleState even when the
		// private launcher also passes the smoke runtime root and log flags.
		else if (RuntimeSmokeHarness.enabled() && !RuntimeStartupProbe.enabled())
			initialState = RuntimeSmokeState;
		#end
		// Fixed 1280x720 design space.  Every chart, stage script, and ported
		// mod is authored in FNF's 1280x720 world; a window-sized game let the
		// design space drift on non-16:9 desktops and misplace imported
		// characters, props, and camera framing.  RatioScaleMode letterboxes
		// this fixed space into any OS window: uniform scale, centered bars on
		// non-16:9 windows, and world framing identical to the 1280x720 window
		// on 16:9 ones.  Installed explicitly instead of relying on the flixel
		// default so the contract survives flixel upgrades; the native-resize
		// smoke harness and the tests pin the math.  (Must be assigned after
		// the FlxGame exists: the setter drives game.onResize, and FlxG.game is
		// null while Main is still constructing.)
		// FlxGame constructs its initial state before addChild returns. Imported
		// owner globals may inspect the live FPS counter during that state load.
		#if !mobile
		fpsCounter = new AverageFPSCounter(10, 3, 0xFFFFFF);
		fpsCounter.visible = OptionsHandler.options.showFPS;
		#end
		var initialOptions = OptionsHandler.options;
		addChild(new FlxGame(1280, 720, initialState, initialOptions.fpsCap, initialOptions.fpsCap, true));
		FramerateOptionsCompat.apply(initialOptions);
		FlxG.signals.postUpdate.add(function() ImportRemovalManager.poll());
		RuntimeInputProbe.install();
		RuntimeMenuTimingProbe.install();
		RuntimeSongExitProbe.install();
		RuntimeSongLoadingProbe.install();
		RuntimeUserLibraryProbe.install();
		RuntimeLibraryCategoryProbe.install();
		RuntimeLibraryNavigationProbe.install();
		RuntimeFreeplayScrollProbe.install();
		RuntimeFreeplayDifficultyProbe.install();
		RuntimeStartupProbe.install();
		RuntimeGpuProbe.install();
		FlxG.scaleMode = new flixel.system.scaleModes.RatioScaleMode();

		// the donor engine dropped its asset cache between states; the fork
		// caches hard for freeplay perf, so without a trim the decompressed
		// art + audio of every visited song piles up into multiple GB and
		// native code starts SIGBUSing on rapid scene switching
		FlxG.signals.preStateSwitch.add(function() {
			RuntimeSongExitProbe.mark("pre-state-switch");
			leavingPlayState = Std.isOfType(FlxG.state, PlayState);
		});
		// Flixel dispatches preStateCreate after destroying the old state and
		// before the new state's create(). Trim here so newly created transition
		// sprites cannot have their graphics destroyed by a late cache sweep.
		FlxG.signals.preStateCreate.add(function(_state:FlxState) {
			RuntimeSongExitProbe.mark("pre-state-create");
			syncImportForegroundForState(_state);
			// A retry of the same song keeps its held images and atlases for the
			// next attempt instead of decoding them all again (see SongRetry).
			var retryKeepsAssets = leavingPlayState
				&& SongRetry.keepsSongAssets(Std.isOfType(_state, PlayState), FNFAssets.pathEpoch());
			if (leavingPlayState) {
				// The song's own holds go first. A held graphic has a use count,
				// so the sweep below would otherwise keep every one of them.
				// A kept retry leaves them, and the sweep then only frees what
				// nothing holds (texts, one-off images), as after any song.
				if (!retryKeepsAssets) {
					SongGraphicRetention.end();
					DynamicSprite.DynamicAtlasFrames.releaseAll();
				}
				if (SongLoadingScreen.active) pruneSongBitmapCache();
				else FlxG.bitmap.clearCache();
			}
			RuntimeSongExitProbe.mark("bitmap-cache-cleared");
			// Hold this song's disk images until it ends; see SongGraphicRetention.
			if (Std.isOfType(_state, PlayState)) {
				// Low memory mode keeps only what scripts precache on purpose.
				SongGraphicRetention.maxHeldBytes = OptionsHandler.options.lowMemoryMode
					? 0 : SongGraphicRetention.DEFAULT_MAX_HELD_BYTES;
				// A kept retry carries on with the holds it already has.
				if (!retryKeepsAssets)
					SongGraphicRetention.begin(FNFAssets.pathEpoch());
			}
		});
		FlxG.signals.postStateSwitch.add(function() {
			RuntimeSongExitProbe.mark("post-state-switch");
			// dead FlxSounds keep their decoded audio alive from here
			// (members is getter-only, so prune in place)
			var corpses = FlxG.sound.list.members;
			var i = corpses.length;
			while (i-- > 0)
				if (corpses[i] == null || !corpses[i].exists)
					corpses.splice(i, 1);
			// The group keeps its own length, which only add and remove update.
			// Without this it grew by every pruned sound and never came back.
			@:privateAccess FlxG.sound.list.length = corpses.length;
		});

		SongLoadingScreen.install();

		distray = new DisSoundTray();
		addChild(distray);
		#if !mobile
		addChild(fpsCounter);

		memoryCounter = new MemoryCounter(10, 3, 0xFFFFFF);
		memoryCounter.visible = false;
		addChild(memoryCounter);
		#end
	}
	/** Same eligibility and removal operation as pinned Flixel clearCache,
	 * with a completed-resource checkpoint after each graphic is retired. */
	static function pruneSongBitmapCache():Void {
		@:privateAccess var cache = FlxG.bitmap._cache;
		if (cache == null) {FlxG.bitmap.clearCache(); return;}
		var keys = [for (key in cache.keys()) key];
		SongLoadingScreen.beginWork('cache', Math.max(1, keys.length), 0.5, 0.65);
		for (key in keys) {
			var graphic = FlxG.bitmap.get(key);
			if (graphic != null && !graphic.persist && graphic.useCount <= 0)
				FlxG.bitmap.removeByKey(key);
			SongLoadingScreen.workUnit();
		}
		if (keys.length == 0) SongLoadingScreen.workUnit();
	}

}
