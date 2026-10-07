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
		instance = this;
		#if sys
		RuntimeSmokeHarness.applyRuntimeRoot();
		RuntimeSmokeSaveIsolation.install(RuntimeImportSmokeHarness.enabled());
		cwd = Sys.getCwd();
		#end
		var initialState:Class<FlxState> = TitleState;
		#if sys
		if (RuntimeImportSmokeHarness.enabled())
			initialState = RuntimeImportSmokeState;
		else if (RuntimeSmokeHarness.config() != null && RuntimeSmokeHarness.config().returnFreeplay)
			initialState = RuntimeSmokeState;
		else if (RuntimeSmokeHarness.config() != null && RuntimeSmokeHarness.config().chartEditor)
			initialState = RuntimeSmokeChartingState;
		else if (RuntimeSmokeHarness.config() != null && RuntimeSmokeHarness.config().freeplay)
			initialState = RuntimeSmokeFreeplayState;
		else if (RuntimeSmokeHarness.enabled())
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
		RuntimeInputProbe.install();
		RuntimeMenuTimingProbe.install();
		RuntimeFreeplayDifficultyProbe.install();
		RuntimeStartupProbe.install();
		FlxG.scaleMode = new flixel.system.scaleModes.RatioScaleMode();

		// the donor engine dropped its asset cache between states; the fork
		// caches hard for freeplay perf, so without a trim the decompressed
		// art + audio of every visited song piles up into multiple GB and
		// native code starts SIGBUSing on rapid scene switching
		FlxG.signals.preStateSwitch.add(function() {
			leavingPlayState = Std.isOfType(FlxG.state, PlayState);
		});
		// Flixel dispatches preStateCreate after destroying the old state and
		// before the new state's create(). Trim here so newly created transition
		// sprites cannot have their graphics destroyed by a late cache sweep.
		FlxG.signals.preStateCreate.add(function(_state:FlxState) {
			syncImportForegroundForState(_state);
			if (leavingPlayState)
				FlxG.bitmap.clearCache();
		});
		FlxG.signals.postStateSwitch.add(function() {
			// dead FlxSounds keep their decoded audio alive from here
			// (members is getter-only, so prune in place)
			var corpses = FlxG.sound.list.members;
			var i = corpses.length;
			while (i-- > 0)
				if (corpses[i] == null || !corpses[i].exists)
					corpses.splice(i, 1);
		});

		distray = new DisSoundTray();
		addChild(distray);
		#if !mobile
		addChild(fpsCounter);

		memoryCounter = new MemoryCounter(10, 3, 0xFFFFFF);
		memoryCounter.visible = false;
		addChild(memoryCounter);
		#end
	}
}
