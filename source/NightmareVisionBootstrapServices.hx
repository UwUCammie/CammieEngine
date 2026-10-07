package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.addons.transition.FlxTransitionableState;
import flixel.input.keyboard.FlxKey;
import flixel.util.FlxColor;
import openfl.events.Event;
import openfl.display.Stage;

using StringTools;

#if cpp
import hxvlc.util.Handle;
#end
#if FEATURE_DEBUG_TRACY
import cpp.vm.tracy.TracyProfiler;
#end

/** Owner-local implementations of the native Flixel services installed by
	Nightmare Vision's Init state. The native host calls these at each matching
	Init step, then releases this object after its source plugins are unmounted. */
@:keep
class NightmareVisionBootstrapServices {
	public final ownerRoot:String;
	final prefs:Dynamic;
	final paths:NightmareVisionPaths;
	final getControls:Void->Dynamic;
	final sourceReset:Void->Void;
	final sourceRepopulate:Void->Void;
	final sourceApplyConfig:Void->Void;
	final writeOwnerSave:String->Dynamic->Void;
	final diagnostics:NightmareVisionSourceDiagnostics;
	final restorers:Array<Void->Void> = [];
	var hotReload:NightmareVisionHotReloadPlugin;
	var debugText:NightmareVisionDebugTextPlugin;
	var fullScreen:NightmareVisionFullScreenPlugin;
	var oldMusic:flixel.sound.FlxSound;
	var sourceMusic:NightmareVisionSound;
	var scaleMode:NightmareVisionRatioScaleMode;
	var previousScaleMode:flixel.system.scaleModes.BaseScaleMode;
	var sourceTraceReady:Bool = false;
	var configured:Bool = false;
	var antialiasingCaptured:Bool = false;
	var previousDefaultAntialiasing:Bool;
	var sourceDefaultAntialiasing:Bool;
	var released:Bool = false;
	var videoInitialized:Bool = false;
	var tracyStage:Stage;
	var tracyListener:Event->Void;
	var transitionRestorePending:Bool = false;
	var previousSkipTransitionIn:Bool;
	var previousSkipTransitionOut:Bool;
	final previousMuteKeys:Array<FlxKey>;
	final previousVolumeDownKeys:Array<FlxKey>;
	final previousVolumeUpKeys:Array<FlxKey>;
	var sourceMuteKeys:Array<FlxKey>;
	var sourceVolumeDownKeys:Array<FlxKey>;
	var sourceVolumeUpKeys:Array<FlxKey>;
	var soundKeysInstalled:Bool = false;
	var previousMusicPlaying:Bool = false;
	var previousMusicPersist:Bool = false;
	var musicWasPaused:Bool = false;
	var audioSound:Dynamic;
	var previousAudioVolume:Float;
	var previousAudioMuted:Bool;
	var audioBaselineCaptured:Bool = false;
	var sourceAudioVolume:Float;
	var sourceAudioMuted:Bool;
	var sourceAudioApplied:Bool = false;

	public function new(ownerRoot:String, prefs:Dynamic, paths:NightmareVisionPaths,
		getControls:Void->Dynamic, sourceReset:Void->Void, sourceRepopulate:Void->Void,
		sourceApplyConfig:Void->Void, ?writeOwnerSave:String->Dynamic->Void) {
		if (ownerRoot == null || paths == null || paths.root != ownerRoot)
			throw '[nmv-bootstrap-service] Paths does not belong to the selected source owner';
		if (prefs == null || getControls == null || sourceReset == null
			|| sourceRepopulate == null || sourceApplyConfig == null)
			throw '[nmv-bootstrap-service] Missing owner preference, control, or lifecycle view';
		this.ownerRoot = ownerRoot;
		this.prefs = prefs;
		this.paths = paths;
		this.getControls = getControls;
		this.sourceReset = sourceReset;
		this.sourceRepopulate = sourceRepopulate;
		this.sourceApplyConfig = sourceApplyConfig;
		this.writeOwnerSave = writeOwnerSave;
		diagnostics = new NightmareVisionSourceDiagnostics(ownerRoot, paths.CORE_DIRECTORY);
		previousMuteKeys = FlxG.sound == null ? null : FlxG.sound.muteKeys;
		previousVolumeDownKeys = FlxG.sound == null ? null : FlxG.sound.volumeDownKeys;
		previousVolumeUpKeys = FlxG.sound == null ? null : FlxG.sound.volumeUpKeys;
		captureAudioBaseline();
	}

	/** Reload the source Controls view without losing the host's pre-owner key
		arrays. The bootstrap constructs this service before this method runs. */
	public function applySourceSoundKeys(muteKeys:Array<FlxKey>, volumeDownKeys:Array<FlxKey>,
		volumeUpKeys:Array<FlxKey>):Void {
		ensureAlive();
		if (FlxG.sound == null || muteKeys == null || volumeDownKeys == null || volumeUpKeys == null)
			throw '[nmv-bootstrap-service] Source sound-key arrays are unavailable';
		sourceMuteKeys = muteKeys;
		sourceVolumeDownKeys = volumeDownKeys;
		sourceVolumeUpKeys = volumeUpKeys;
		FlxG.sound.muteKeys = muteKeys;
		FlxG.sound.volumeDownKeys = volumeDownKeys;
		FlxG.sound.volumeUpKeys = volumeUpKeys;
		soundKeysInstalled = true;
	}

	/** Apply ClientPrefs' audio values after loading them while retaining the
	 * pre-source FlxG values for conditional teardown restoration. */
	public function applySourceAudioPreferences(volume:Dynamic, muted:Dynamic):Void {
		ensureAlive();
		if (FlxG.sound == null)
			throw '[nmv-bootstrap-service] Source audio preferences require Flixel sound';
		if (!(Std.isOfType(volume, Int) || Std.isOfType(volume, Float)) || !Std.isOfType(muted, Bool))
			throw '[nmv-bootstrap-service] Source volume and mute preferences are unavailable';
		if (!audioBaselineCaptured)
			throw '[nmv-bootstrap-service] Native sound baseline was unavailable before source preferences';
		if (FlxG.sound != audioSound)
			throw '[nmv-bootstrap-service] Flixel sound front-end changed after native audio capture';
		sourceAudioVolume = cast volume;
		sourceAudioMuted = cast muted;
		FlxG.sound.volume = sourceAudioVolume;
		FlxG.sound.muted = sourceAudioMuted;
		sourceAudioApplied = true;
	}

	/** Donor Init: set FlxSprite.defaultAntialiasing after preferences load and
		before Discord/mod loading. */
	public function applyDefaultAntialiasing():Void {
		ensureAlive();
		if (antialiasingCaptured) return;
		var value:Dynamic = Reflect.field(prefs, 'globalAntialiasing');
		if (!Std.isOfType(value, Bool))
			throw '[nmv-bootstrap-service] ClientPrefs.globalAntialiasing is unavailable';
		previousDefaultAntialiasing = FlxSprite.defaultAntialiasing;
		sourceDefaultAntialiasing = value;
		FlxSprite.defaultAntialiasing = sourceDefaultAntialiasing;
		antialiasingCaptured = true;
	}

	/** Donor Init's complete Flixel configuration block, in source order. */
	public function configureFlixelServices():Void {
		ensureAlive();
		if (configured) return;
		var game = FlxG.game;
		if (game == null || FlxG.sound == null || FlxG.keys == null || FlxG.mouse == null)
			throw '[nmv-bootstrap-service] Flixel services require an initialized FlxGame';

		var previousFixedTimestep = FlxG.fixedTimestep;
		FlxG.fixedTimestep = false;
		addRestorer(function() if (FlxG.fixedTimestep == false) FlxG.fixedTimestep = previousFixedTimestep);

		var previousFocusLostFramerate = game.focusLostFramerate;
		game.focusLostFramerate = 60;
		addRestorer(function() if (game.focusLostFramerate == 60) game.focusLostFramerate = previousFocusLostFramerate);

		if (!soundKeysInstalled) applySourceSoundKeys(requirePreferenceArray('muteKeys'),
			requirePreferenceArray('volumeDownKeys'), requirePreferenceArray('volumeUpKeys'));

		var keys = FlxG.keys;
		var sourcePreventDefaultKeys:Array<FlxKey> = [FlxKey.TAB];
		var restorePreventDefaultKeys = installRawFieldOverride(keys, 'preventDefaultKeys', function() {
			keys.preventDefaultKeys = sourcePreventDefaultKeys;
		}, function() return FlxG.keys == keys);
		addRestorer(restorePreventDefaultKeys);

		var previousMouseVisible = FlxG.mouse.visible;
		FlxG.mouse.visible = false;
		var mouse = FlxG.mouse;
		addRestorer(function() if (FlxG.mouse == mouse && mouse.visible == false) mouse.visible = previousMouseVisible);

		var previousDrawOnTop = FlxG.plugins.drawOnTop;
		FlxG.plugins.drawOnTop = true;
		addRestorer(function() if (FlxG.plugins.drawOnTop == true) FlxG.plugins.drawOnTop = previousDrawOnTop);

		previousScaleMode = FlxG.scaleMode;
		scaleMode = new NightmareVisionRatioScaleMode();
		FlxG.scaleMode = scaleMode;
		FlxG.signals.preStateSwitch.add(resetOwnerScale);
		addRestorer(function() {
			FlxG.signals.preStateSwitch.remove(resetOwnerScale);
			if (FlxG.scaleMode == scaleMode) FlxG.scaleMode = previousScaleMode;
		});

		oldMusic = FlxG.sound.music;
		if (oldMusic != null) {
			previousMusicPlaying = oldMusic.playing;
			previousMusicPersist = oldMusic.persist;
			if (previousMusicPlaying) {
				oldMusic.pause();
				musicWasPaused = true;
			}
			// Keep the borrowed host handle alive across Flixel state switches.
			oldMusic.persist = true;
		}
		addRestorer(restoreMusic);
		sourceMusic = new NightmareVisionSound();
		sourceMusic.persist = true;
		FlxG.sound.music = sourceMusic;

		var autoPause:Dynamic = Reflect.field(prefs, 'autoPause');
		if (!Std.isOfType(autoPause, Bool))
			throw '[nmv-bootstrap-service] ClientPrefs.autoPause is unavailable';
		var previousAutoPause = FlxG.autoPause;
		FlxG.autoPause = autoPause;
		addRestorer(function() if (FlxG.autoPause == autoPause) FlxG.autoPause = previousAutoPause);
		configured = true;
	}

	/** The donor installs Iris log hooks globally. Source modules here use a
		separate Iris interpreter, so bind trace to this owner's debug group. */
	public function initializeFunkinScript():Void {
		ensureAlive();
		sourceTraceReady = true;
	}

	public inline function scriptTracingReady():Bool return sourceTraceReady && !released;

	/** Install this owner's trace function before its script is executed. */
	public function configure(interp:NightmareVisionScriptInterp):Void {
		ensureAlive();
		if (!sourceTraceReady)
			throw '[nmv-bootstrap-service] Source script tracing was configured before Init';
		if (interp == null) throw '[nmv-bootstrap-service] Missing source interpreter';
		if (debugText == null)
			throw '[nmv-bootstrap-service] Source DebugTextPlugin has not been initialized';
		diagnostics.bindIris(interp);
		interp.variables.set('trace', Reflect.makeVarArgs(function(arguments:Array<Dynamic>):Void {
			if (released || debugText == null) return;
			var position = interp.posInfos();
			var fileName = position == null ? 'hscript' : position.fileName;
			if (fileName != null && fileName.startsWith(paths.CORE_DIRECTORY + '/'))
				fileName = fileName.substr(paths.CORE_DIRECTORY.length + 1);
			else if (fileName != null && fileName.startsWith(ownerRoot + '/'))
				fileName = fileName.substr(ownerRoot.length + 1);
			var lineNumber = position == null ? 0 : position.lineNumber;
			var message:Dynamic = arguments.length == 0 ? null : arguments.shift();
			if (position != null && arguments.length > 0) position.customParams = arguments.copy();
			debugText.addText('[$fileName:$lineNumber] - ${Std.string(message)}', FlxColor.WHITE);
		}));
	}

	public function initializeHotReloadPlugin():Void {
		ensureAlive();
		if (hotReload != null) return;
		if (!configured) throw '[nmv-bootstrap-service] Flixel services must be configured before HotReloadPlugin';
		hotReload = new NightmareVisionHotReloadPlugin(prefs, getControls, beginSourceReset,
			repopulateSourcePlugins, applySourceConfig, clearOwnerAssetCache);
		FlxG.plugins.addPlugin(hotReload);
	}

	public function initializeDebugTextPlugin():Void {
		ensureAlive();
		if (debugText != null) return;
		if (!configured) throw '[nmv-bootstrap-service] Flixel services must be configured before DebugTextPlugin';
		var font = paths.font('consolas', true);
		if (font == null || !paths.exists(font))
			throw '[nmv-bootstrap-service] Source DebugText font assets/fonts/consolas.ttf are missing';
		debugText = new NightmareVisionDebugTextPlugin(font);
		diagnostics.bindDebugText(function(message:String, colour:FlxColor):Void {
			if (!released && debugText != null) debugText.addText(message, colour);
		});
		FlxG.plugins.addPlugin(debugText);
		FlxG.signals.preStateSwitch.add(clearDebugText);
	}

	public function initializeFullScreenPlugin():Void {
		ensureAlive();
		if (fullScreen != null) return;
		if (writeOwnerSave == null)
			throw '[nmv-bootstrap-service] Fullscreen requires the owner save field writer';
		fullScreen = new NightmareVisionFullScreenPlugin(getControls, writeOwnerSave);
		FlxG.plugins.addPlugin(fullScreen);
	}

	/** SourceModule/PluginHost reporters call this for parser and callback
	 * failures so errors retain the donor red DebugText and console behavior. */
	public function reportError(name:String, callback:String, error:Dynamic):Void
		diagnostics.reportError(name, callback, error);

	/** NightmareVisionVideoSprite and hxvlc are available on the host CPP target;
		the donor's VIDEOS_ALLOWED define is absent from the host project. */
	public function initializeVideoPluginWhenEnabled():Void {
		ensureAlive();
		#if cpp
		if (videoInitialized) return;
		if (!Handle.init() && Handle.sharedInstance == null)
			throw '[nmv-bootstrap-service] Could not initialize hxvlc for the source video adapter';
		videoInitialized = true;
		#end
	}

	/** The host build does not enable FEATURE_DEBUG_TRACY. */
	public function initializeTracyWhenEnabled():Void {
		ensureAlive();
		#if FEATURE_DEBUG_TRACY
		if (tracyListener != null) return;
		tracyStage = openfl.Lib.current == null ? null : openfl.Lib.current.stage;
		if (tracyStage == null) throw '[nmv-bootstrap-service] Tracy needs an initialized OpenFL stage';
		tracyListener = function(_:Event):Void TracyProfiler.frameMark();
		tracyStage.addEventListener(Event.EXIT_FRAME, tracyListener);
		TracyProfiler.setThreadName('main');
		#end
	}

	/** Uninstall source plugins and conditionally restore host globals. */
	public function release():Void {
		if (released) return;
		released = true;
		var failures:Array<String> = [];
		diagnostics.release();
		try if (fullScreen != null) fullScreen.release() catch (error:Dynamic) failures.push(Std.string(error));
		fullScreen = null;
		try if (debugText != null) {
			FlxG.signals.preStateSwitch.remove(clearDebugText);
			debugText.release();
		} catch (error:Dynamic) failures.push(Std.string(error));
		debugText = null;
		try if (hotReload != null) hotReload.release() catch (error:Dynamic) failures.push(Std.string(error));
		hotReload = null;
		#if FEATURE_DEBUG_TRACY
		if (tracyStage != null && tracyListener != null) tracyStage.removeEventListener(Event.EXIT_FRAME, tracyListener);
		tracyStage = null;
		tracyListener = null;
		#end
		// LibVLC is shared by source and native video adapters. Its pinned API
		// has no owner lease, so initialization is process-scoped and retained.
		if (transitionRestorePending) restoreTransitionFlags();
		var i = restorers.length;
		while (i-- > 0) {
			try restorers[i]() catch (error:Dynamic) failures.push(Std.string(error));
		}
		restorers.resize(0);
		if (antialiasingCaptured && FlxSprite.defaultAntialiasing == sourceDefaultAntialiasing)
			FlxSprite.defaultAntialiasing = previousDefaultAntialiasing;
		antialiasingCaptured = false;
		if (soundKeysInstalled && FlxG.sound != null) {
			if (FlxG.sound.muteKeys == sourceMuteKeys) FlxG.sound.muteKeys = previousMuteKeys;
			if (FlxG.sound.volumeDownKeys == sourceVolumeDownKeys)
				FlxG.sound.volumeDownKeys = previousVolumeDownKeys;
			if (FlxG.sound.volumeUpKeys == sourceVolumeUpKeys)
				FlxG.sound.volumeUpKeys = previousVolumeUpKeys;
		}
		restoreAudioPreferences();
		soundKeysInstalled = false;
		sourceMuteKeys = null;
		sourceVolumeDownKeys = null;
		sourceVolumeUpKeys = null;
		if (failures.length > 0)
			throw '[nmv-bootstrap-service] Release had errors: ' + failures.join(' | ');
	}

	function requirePreferenceArray(name:String):Array<FlxKey> {
		var value:Dynamic = Reflect.field(prefs, name);
		if (!Std.isOfType(value, Array))
			throw '[nmv-bootstrap-service] ClientPrefs.' + name + ' is unavailable';
		return cast value;
	}

	/** Preserve the native container identity of generic Flixel fields such as
		Array<Key>, which hxcpp stores as cpp::VirtualArray. A typed Haxe Array
		snapshot preserves values but can produce a different VirtualArray wrapper. */
	static function installRawFieldOverride(target:Dynamic, field:String, install:Void->Void,
		?stillOwner:Void->Bool):Void->Void {
		if (target == null || field == null || install == null)
			throw '[nmv-bootstrap-service] Raw field override requires a target and setter';
		var previousContainer:Dynamic = Reflect.field(target, field);
		install();
		var installedContainer:Dynamic = Reflect.field(target, field);
		return function():Void {
			if ((stillOwner == null || stillOwner()) && Reflect.field(target, field) == installedContainer)
				Reflect.setField(target, field, previousContainer);
		};
	}

	function resetOwnerScale():Void if (!released && scaleMode != null) scaleMode.resetSize();
	function clearDebugText():Void if (debugText != null) debugText.clearText();

	function beginSourceReset():Void {
		setSkipTransitions();
		sourceReset();
	}

	function setSkipTransitions():Void {
		if (!transitionRestorePending) {
			previousSkipTransitionIn = FlxTransitionableState.skipNextTransIn;
			previousSkipTransitionOut = FlxTransitionableState.skipNextTransOut;
			transitionRestorePending = true;
			FlxG.signals.postStateSwitch.addOnce(restoreTransitionFlags);
		}
		FlxTransitionableState.skipNextTransIn = true;
		FlxTransitionableState.skipNextTransOut = true;
	}

	function restoreTransitionFlags():Void {
		if (!transitionRestorePending) return;
		transitionRestorePending = false;
		FlxG.signals.postStateSwitch.remove(restoreTransitionFlags);
		if (FlxTransitionableState.skipNextTransIn == true)
			FlxTransitionableState.skipNextTransIn = previousSkipTransitionIn;
		if (FlxTransitionableState.skipNextTransOut == true)
			FlxTransitionableState.skipNextTransOut = previousSkipTransitionOut;
	}

	function repopulateSourcePlugins():Void sourceRepopulate();
	function applySourceConfig():Void sourceApplyConfig();

	function clearOwnerAssetCache():Void {
		var cache = paths.getOwnerAssetCache();
		cache.clearStoredMemory();
		cache.clearUnusedMemory();
	}

	function restoreMusic():Void {
		var stillOwnerMusic = sourceMusic == null ? FlxG.sound.music == oldMusic : FlxG.sound.music == sourceMusic;
		if (stillOwnerMusic) FlxG.sound.music = oldMusic;
		if (sourceMusic != null) {
			sourceMusic.stop();
			sourceMusic.destroy();
			sourceMusic = null;
		}
		if (oldMusic != null) {
			oldMusic.persist = previousMusicPersist;
			if (stillOwnerMusic && musicWasPaused && previousMusicPlaying && oldMusic.exists)
				oldMusic.resume();
		}
		oldMusic = null;
	}

	function captureAudioBaseline():Void {
		if (audioBaselineCaptured || FlxG.sound == null) return;
		audioSound = FlxG.sound;
		previousAudioVolume = FlxG.sound.volume;
		previousAudioMuted = FlxG.sound.muted;
		audioBaselineCaptured = true;
	}

	function restoreAudioPreferences():Void {
		if (!audioBaselineCaptured || !sourceAudioApplied || FlxG.sound == null || FlxG.sound != audioSound)
			return;
		if (FlxG.sound.volume == sourceAudioVolume) FlxG.sound.volume = previousAudioVolume;
		if (FlxG.sound.muted == sourceAudioMuted) FlxG.sound.muted = previousAudioMuted;
		sourceAudioApplied = false;
		audioSound = null;
	}

	function addRestorer(callback:Void->Void):Void restorers.push(callback);
	function ensureAlive():Void if (released) throw '[nmv-bootstrap-service] Owner services have been released';
}
