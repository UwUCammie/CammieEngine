package;

#if sys
import haxe.Json;
import haxe.io.Path;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.input.keyboard.FlxKey;
import lime.app.Application;
import sys.FileSystem;
import sys.io.File;
import ImportRefreshTransaction.ImportRefreshManifest;
using StringTools;

/** Opt-in generated source constructor/plugin/redirect/reset lifecycle check. */
@:access(RuntimeSmokeHarness)
@:access(NightmareVisionStateSession)
@:access(NightmareVisionMainRuntime)
@:access(NightmareVisionSplashState)
@:access(NightmareVisionVideoSprite)
class RuntimeNvStateProbe {
	static var session:NightmareVisionStateSession;
	static var phase:Int = 0;
	static var expectedLoads:Int = 0;
	static var events:Array<String> = [];
	static var rendered:Int = 0;
	static var capturing:Bool = false;
	static var initialTitle:String;
	static var currentCapture:String;
	static var missingTransitionObserved:Bool = false;
	static var expectedBetaRoot:String;
	static var retainedEvidence:Dynamic;
	static var highscoreServiceObserved:Bool = false;
	static var startMetaObserved:Bool = false;
	static var mainRuntimeObserved:Bool = false;
	static var mainResizeHandler:Int->Int->Void;
	static var nativeHostSettings:Dynamic;
	static var splash:NightmareVisionSplashState;
	static var splashCaptured:Bool = false;
	static var splashActionRequested:Bool = false;
	static var splashRetiredAt:Float = -1;
	static var splashVerified:Bool = false;
	static function splashMode():String {
		var mode = Sys.getEnv('CAMMIE_NV_SPLASH_MODE');
		return mode == null || mode == '' ? 'None' : mode;
	}

	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_NV_STATE_SMOKE') == '1';
	static function check(ok:Bool, message:String):Void if (!ok) throw message;

	public static function tick():Void {
		if (!enabled() || RuntimeSmokeHarness.finished || capturing) return;
		try {
			if (phase == 0) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null, 'Muted isolated native state probe required');
				nativeHostSettings = captureNativeHostSettings();
				var a:String;
				var b:String;
				var family:Array<NightmareVisionModFamilyMember>;
				if (Sys.getEnv('CAMMIE_NV_STATE_RETAINED') == '1') {
					retainedEvidence = resolveRetainedEvidence();
					a = cast Reflect.field(retainedEvidence, 'alphaRoot');
					b = cast Reflect.field(retainedEvidence, 'betaRoot');
					family = cast Reflect.field(retainedEvidence, 'family');
					expectedBetaRoot = b;
					RuntimeSmokeHarness.emit('nv_state_retained_import_verified', {
						owner:Reflect.field(retainedEvidence, 'owner'), transactionId:Reflect.field(retainedEvidence, 'transactionId'),
						snapshotId:Reflect.field(retainedEvidence, 'snapshotId'), catalogVersion:2,
						containerRelative:Reflect.field(retainedEvidence, 'containerRelative'),
						alphaRoot:a, betaRoot:b, chart:Reflect.field(retainedEvidence, 'chart'),
						audio:Reflect.field(retainedEvidence, 'audio'), sourceChart:Reflect.field(retainedEvidence, 'sourceChart'),
						sourceAudio:Reflect.field(retainedEvidence, 'sourceAudio'),
						sourceCore:Reflect.field(retainedEvidence, 'sourceCore'),
						sourceFont:Reflect.field(retainedEvidence, 'sourceFont'),
						familyDirectories:[for (member in family) member.directory], sourceSnapshotVerified:true
					});
				} else {
					a = Sys.getEnv('CAMMIE_NV_STATE_ALPHA');
					b = Sys.getEnv('CAMMIE_NV_STATE_BETA');
					check(a != null && b != null && a != b, 'Private source family required');
					family = [{directory:'alpha',root:a},{directory:'beta',root:b}];
					expectedBetaRoot = b;
				}
				initialTitle = Application.current.window.title;
				var familySession = new NightmareVisionModFamilySession('alpha', a, family);
				var mods = new NightmareVisionModsContext(a, 'alpha', familySession);
				var prefs = new NightmareVisionClientPrefs(a, new CodenameOwnerSaveData(a), OptionsHandler.options);
				if (retainedEvidence == null) {prefs.load(); prefs.view.loadDefaultKeys();}
				var paths = new NightmareVisionPaths(a, null, prefs.view, 'alpha'); paths.bindModFamily(mods);
				new NightmareVisionModConfigRuntime(mods, paths);
				if (retainedEvidence == null) {mods.pushGlobalMods(); mods.applyModConfig();}
				var save = new CodenameOwnerSaveData(a); save.setField('flashing', true); save.flush();
				if (splashMode() != 'None') {
					save.setField('mute', true); save.setField('volume', 0.37); save.flush();
				}
				session = NightmareVisionStateSession.adopt(mods, paths, prefs, new NightmareVisionDifficultyAdapter(a));
				session.configureScript = function(interp) interp.variables.set('Probe', {
					skipSplash:splashMode() == 'None',
					verifyMain:verifySourceMain,
					mark:function(name:String, parent:Dynamic) {
						if (name == 'highscore-bound') {
							check(parent != null && Reflect.field(parent, 'initial') == 0
								&& Reflect.field(parent, 'reloaded') == 17
								&& Reflect.field(parent, 'formatted') == 'retained-state-fixture-easy',
								'Source Highscore binding did not return, format, save and reload its owner-local values');
							highscoreServiceObserved = true;
						} else if (name == 'start-meta-title-class') {
							check(parent == true, 'Main.startMeta did not expose its source TitleState class and skipSplash value');
							startMetaObserved = true;
						} else if (name != 'plugin-load') check(Std.isOfType(parent, NightmareVisionMusicBeatState)
							|| Std.isOfType(parent, NightmareVisionMusicBeatSubstate), 'State parent not bound before callback');
						events.push(name);
						RuntimeSmokeHarness.emit('nv_state_callback', {name:name, owner:mods.currentModDirectory});
					}
				});
				phase = 1;
				if (retainedEvidence != null) {
					check(session.startMeta.initialState == NightmareVisionTitleState, 'Source Main.startMeta lost its source TitleState class');
					session.startMeta.skipSplash = splashMode() == 'None';
					session.switchState(session.createStateFactory('Init'));
				} else session.plugins = NightmareVisionPluginHost.mount(a, function(interp, entry, plugins) {
					session.plugins = plugins;
					PlayState.seedNightmareVisionCommon(interp, paths, prefs, plugins, mods, session.difficulty, null, entry);
				}, paths);
				return;
			}
			var loads = count('redirect-create');
			if (phase == 1 && splashMode() != 'None' && !observeSplash(loads)) return;
			if (phase >= 1 && phase <= 3) {
				if (loads < phase) return;
				check(Std.isOfType(FlxG.state, NightmareVisionScriptedState), 'Redirect did not create source scripted state');
				check(count('redirect-load') == phase, 'Constructor onLoad count does not match create');
				check(session.mods.currentModDirectory == 'beta', 'Plugin selected package not retained');
				check(session.mods.selectedRoot() == expectedBetaRoot, 'Plugin-selected root differs from authenticated family member');
				check(Application.current.window.title == 'State fixture beta', 'Selected native title configuration lost');
				if (phase == 1) {
					if (retainedEvidence != null) {
						check(session.bootstrapComplete, 'Source Init did not complete before its initial source title');
						check(session.startMeta.skipSplash == (splashMode() == 'None')
							&& session.startMeta.initialState == NightmareVisionTitleState,
							'Source Init did not honor source Main.startMeta');
						check(highscoreServiceObserved, 'Source plugin could not read and reload the owner-scoped Highscore service');
						check(startMetaObserved, 'Source plugin could not read Main.startMeta source class identity');
						checkSourceInitHostSettings();
						var tracked:haxe.ds.ObjectMap<FlxState, String> = cast Reflect.field(session, 'states');
						var trackedCount = 0;
						for (state in tracked.keys()) {
							check(state == FlxG.state, 'Destroyed source startup state remained registered');
							trackedCount++;
						}
						check(trackedCount == 1, 'Source current state registration was lost');
					}
					check(count('constructed-base') == 1 && count('constructed-substate') == 1
						&& count('direct-state-load') == 1 && count('direct-state-destroy') == 1,
						'Captured source state/substate constructors failed');
					check(events.indexOf('plugin-load') < events.indexOf('redirect-load'), 'Plugin initialized after title constructor');
					capture('redirect'); return;
				}
				if (phase == 2) {
					check(count('redirect-destroy') == 1, 'First reset did not destroy prior state');
					// Reset must retain the resolved source constructor, even after config changes.
					Reflect.setField(Reflect.field(session.mods.currentModConfig, 'stateRedirects'), 'TitleState', 'MissingState');
					phase = 3; invoke('onProbeReset'); return;
				}
				check(count('redirect-destroy') == 2, 'Second reset lifecycle wrong');
				phase = 4;
				session.config.transitionOut = SCRIPTED('MissingTransition');
				session.switchState(session.createStateFactory('TitleState')); return;
			}
			if (phase == 4) {
				if (count('native-title-create') < 1) return;
				check(Std.isOfType(FlxG.state, NightmareVisionTitleState), 'Missing redirect did not retain intended source TitleState');
				if (FlxG.state.subState != null) {
					check(Std.isOfType(FlxG.state.subState, NightmareVisionStateTransition), 'Wrong source transition substate');
					missingTransitionObserved = true; return;
				}
				check(missingTransitionObserved, 'Missing scripted transition did not execute native fallback');
				capture('native-title'); return;
			}
			if (phase == 5) {
				if (!Std.isOfType(FlxG.state, FreeplayState)) return;
				check(session.released && NightmareVisionStateSession.active == null, 'Unrelated state retained source session');
				if (retainedEvidence != null) {
					check(Reflect.field(session.highscores, 'released') == true, 'Source Highscore service survived session departure');
					check(highscoreServiceObserved && startMetaObserved && session.bootstrapComplete,
						'Retained source Init evidence was lost before cleanup');
					checkNativeHostSettingsRestored();
					check(mainRuntimeObserved && mainResizeHandler != null
						&& !FlxG.signals.gameResized.has(mainResizeHandler), 'Source Main resize listener survived departure');
					check(session.mainRuntime.released && session.mainRuntime.capturedStage == null,
						'Source Main did not release its captured stage');
				}
				check(Application.current.window.title == initialTitle, 'Native title leaked after source departure');
				check(NightmareVisionPluginHost.activeHost == null, 'Plugin owner survived source departure');
				RuntimeSmokeHarness.emit('nv_state_verified', {pluginBeforeTitle:true, selectedPackage:true,
					capturedStateConstructors:true, directScriptedState:true,
					missingTransitionCompleted:missingTransitionObserved,
					constructorLoads:count('redirect-load'), resets:2, missingRedirectFallback:true,
					stateDestroyCalls:count('redirect-destroy'), nativeTitleScript:true, released:true,
					retainedImport:retainedEvidence != null,
					retainedSnapshotId:retainedEvidence == null ? null : Reflect.field(retainedEvidence, 'snapshotId'),
					bootstrapComplete:retainedEvidence != null && session.bootstrapComplete,
					retiredStartupState:retainedEvidence != null,
					sourceHighscoreService:retainedEvidence != null && highscoreServiceObserved,
						sourceStartMeta:retainedEvidence != null && startMetaObserved,
						sourceMainRuntime:retainedEvidence != null && mainRuntimeObserved,
						sourceSplash:splashVerified,
					capped:!OptionsHandler.options.unlimitedFPS});
				RuntimeSmokeHarness.succeed();
			}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('nv-state', Std.string(error));
	}

	/** Exercise the real source Splash through Init. Timers, video callbacks and
	 * source input drive completion; abort deliberately tests the destroy path. */
	static function observeSplash(loads:Int):Bool {
		if (Std.isOfType(FlxG.state, NightmareVisionSplashState)) {
			var state:NightmareVisionSplashState = cast FlxG.state;
			if (splash == null) splash = state;
			// finish restores services before Flixel consumes the queued switch.
			if (state.completed) return false;
			check(splash == state && !state.disposed && !FlxG.autoPause && FlxG.sound.muted,
				'Source Splash ownership, pause or mute contract differs');
			var visible = state.logo != null && state.logo.visible && state.logo.alpha > 0.9
				&& Math.abs(state.logo.scale.x / state.logoScale - 1) < 0.1
				&& Math.abs(state.logo.scale.y / state.logoScale - 1) < 0.1;
			#if cpp
			if (splashMode() == 'Video') visible = state.video != null && state.video.formatted
				&& state.video.bitmap != null && state.video.bitmap.time > 200 && state.video.width > 0;
			#end
			if (splashMode() == 'AbortBranding') visible = visible && state.ownedTweens.length > 0;
			if (visible && !splashCaptured) {capture('splash'); return false;}
			if (splashCaptured && !splashActionRequested) {
				splashActionRequested = true;
				if (splashMode() == 'SkipBranding') FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(
					openfl.events.KeyboardEvent.KEY_DOWN, true, false, 0, FlxKey.SPACE));
				else if (splashMode() == 'AbortBranding') session.switchState(session.startupConstructor(session.startMeta.initialState));
			}
			return false;
		}
		if (loads < 1) return false;
		check(splash != null && splashCaptured, 'Source Splash reached its destination without visible media evidence');
		check(splash.completed && splash.disposed && splash.resourcesCleaned && splash.audioRestored
			&& splash.startupDelay == null && splash.spriteEvents == null && splash.animationEvents == null
			&& splash.completionDelay == null && splash.ownedTweens.length == 0,
			'Source Splash did not retire all callbacks and restore its audio services');
		#if cpp
		check(splash.video == null, 'Source Splash retained its video instance');
		#end
		check(FlxG.sound.muted && Math.abs(FlxG.sound.volume - 0.37) < 0.0001
			&& FlxG.autoPause == splash.cachedAutoPause, 'Source Splash did not restore owner audio/pause values');
		if (splashRetiredAt < 0) {
			splashRetiredAt = Sys.time();
			if (splashMode() == 'SkipBranding') FlxG.stage.dispatchEvent(new openfl.events.KeyboardEvent(
				openfl.events.KeyboardEvent.KEY_UP, true, false, 0, FlxKey.SPACE));
		}
		check(loads == 1 && count('redirect-load') == 1, 'Retired Splash caused an extra startup state');
		if (Sys.time() - splashRetiredAt < 1.2) return false;
		if (!splashVerified) RuntimeSmokeHarness.emit('nv_splash_verified', {mode:splashMode(),
			formattedOrLogoVisible:true, completed:true, disposed:true, cleaned:true,
			audioRestored:true, noLateSwitch:true});
		splashVerified = true;
		return true;
	}

	/** Native OpenFL objects through the imported source interpreter, with the
	 * actual session listener rather than a hand-built test runtime. */
	static function verifySourceMain(mainClass:Dynamic, clear:Dynamic, reflectedClear:Dynamic, resize:Dynamic):Void {
		check(mainClass == NightmareVisionMainMetadata && session.startMeta.startFullScreen == false,
			'Source Main identity or donor fullscreen metadata field differs');
		check(Reflect.isFunction(clear) && Reflect.isFunction(reflectedClear) && Reflect.isFunction(resize),
			'Source Main direct or reflected cache helpers missing');
		for (callback in [clear, reflectedClear]) {
			var sprite = new openfl.display.Sprite();
			var data = new openfl.display.BitmapData(1, 1, true, 0xFFFFFFFF);
			@:privateAccess sprite.__cacheBitmap = new openfl.display.Bitmap(data);
			@:privateAccess sprite.__cacheBitmapData = data;
			Reflect.callMethod(null, callback, [sprite]);
			check((@:privateAccess sprite.__cacheBitmap) == null && (@:privateAccess sprite.__cacheBitmapData) == null,
				'Source Main did not clear the real OpenFL sprite cache');
			data.dispose();
			Reflect.callMethod(null, callback, [null]);
		}
		mainResizeHandler = session.mainRuntime.resizeHandler;
		check(mainResizeHandler != null && FlxG.signals.gameResized.has(mainResizeHandler)
			&& session.mainRuntime.capturedStage == FlxG.stage, 'Source Main listener not installed on native host');
		Reflect.callMethod(null, resize, [FlxG.width, FlxG.height]);
		FlxG.signals.gameResized.dispatch(FlxG.width, FlxG.height);
		mainRuntimeObserved = true;
		RuntimeSmokeHarness.emit('nv_main_runtime_verified', {directCache:true, reflectedCache:true,
			resizeSignal:true, nativeOpenfl:true, startFullScreen:true});
	}

	static function captureNativeHostSettings():Dynamic {
		return {
			fixedTimestep:FlxG.fixedTimestep, autoPause:FlxG.autoPause, scaleMode:FlxG.scaleMode,
			defaultAntialiasing:FlxSprite.defaultAntialiasing,
			focusLostFramerate:FlxG.game.focusLostFramerate, drawOnTop:FlxG.plugins.drawOnTop,
			preventDefaultKeys:Reflect.field(FlxG.keys, 'preventDefaultKeys'),
			preventDefaultKeyValues:copyDynamicArray(FlxG.keys.preventDefaultKeys),
			muteKeys:FlxG.sound.muteKeys, muteKeyValues:copyDynamicArray(FlxG.sound.muteKeys),
			volumeDownKeys:FlxG.sound.volumeDownKeys, volumeDownKeyValues:copyDynamicArray(FlxG.sound.volumeDownKeys),
			volumeUpKeys:FlxG.sound.volumeUpKeys, volumeUpKeyValues:copyDynamicArray(FlxG.sound.volumeUpKeys),
			mouseVisible:FlxG.mouse.visible, soundMuted:FlxG.sound.muted, soundVolume:FlxG.sound.volume,
			windowFrameRate:Application.current.window.frameRate,
			updateFramerate:FlxG.updateFramerate, drawFramerate:FlxG.drawFramerate
		};
	}

	static function checkSourceInitHostSettings():Void {
		check(!FlxG.fixedTimestep, 'Source Init did not disable fixed timestep');
		check(FlxG.game.focusLostFramerate == 60, 'Source Init focus-lost framerate is not 60');
		check(FlxG.plugins.drawOnTop == true, 'Source Init did not place plugins above native states');
		check(!FlxG.mouse.visible, 'Source Init left the mouse cursor visible');
		var prevent = FlxG.keys.preventDefaultKeys;
		check(prevent != null && prevent.length == 1 && prevent[0] == FlxKey.TAB,
			'Source Init prevent-default key contract is not TAB');
		check(FlxG.updateFramerate == 60, 'Source Init update framerate is not capped at 60');
		if (OptionsHandler.options.unlimitedFPS)
			check(FlxG.updateFramerate == 60, 'Source Init changed its 60 Hz update cadence in uncapped host mode');
		check(Application.current.window.frameRate == Reflect.field(nativeHostSettings, 'windowFrameRate'),
			'Source Init changed the native host window frame-rate option');
		var scaleMode:Dynamic = FlxG.scaleMode;
		var scaleClass = scaleMode == null || Type.getClass(scaleMode) == null ? '' : Type.getClassName(Type.getClass(scaleMode));
		check(scaleClass.toLowerCase().indexOf('ratio') >= 0, 'Source Init did not install the Nightmare Vision ratio scale mode');
		var hostWindowRate:Dynamic = Reflect.field(nativeHostSettings, 'windowFrameRate');
		check(hostWindowRate == 0 || hostWindowRate == 60,
			'Source Init native host frame-rate option was not one of the preserved 0/60 modes');
	}

	static function checkNativeHostSettingsRestored():Void {
		check(FlxG.fixedTimestep == Reflect.field(nativeHostSettings, 'fixedTimestep'), 'Native fixed timestep did not restore');
		check(FlxG.autoPause == Reflect.field(nativeHostSettings, 'autoPause'), 'Native auto-pause did not restore');
		check(FlxG.scaleMode == Reflect.field(nativeHostSettings, 'scaleMode'), 'Native scale-mode identity did not restore');
		check(FlxSprite.defaultAntialiasing == Reflect.field(nativeHostSettings, 'defaultAntialiasing'),
			'Native default antialiasing did not restore');
		check(FlxG.game.focusLostFramerate == Reflect.field(nativeHostSettings, 'focusLostFramerate'),
			'Native focus-lost framerate did not restore');
		check(FlxG.plugins.drawOnTop == Reflect.field(nativeHostSettings, 'drawOnTop'), 'Native plugin draw order did not restore');
		check(Reflect.field(FlxG.keys, 'preventDefaultKeys') == Reflect.field(nativeHostSettings, 'preventDefaultKeys')
			&& sameDynamicArray(FlxG.keys.preventDefaultKeys, Reflect.field(nativeHostSettings, 'preventDefaultKeyValues')),
			'Native prevent-default keys did not restore by identity and value');
		check(FlxG.sound.muteKeys == Reflect.field(nativeHostSettings, 'muteKeys')
			&& sameDynamicArray(FlxG.sound.muteKeys, Reflect.field(nativeHostSettings, 'muteKeyValues')),
			'Native mute keys did not restore by identity and value');
		check(FlxG.sound.volumeDownKeys == Reflect.field(nativeHostSettings, 'volumeDownKeys')
			&& sameDynamicArray(FlxG.sound.volumeDownKeys, Reflect.field(nativeHostSettings, 'volumeDownKeyValues')),
			'Native volume-down keys did not restore by identity and value');
		check(FlxG.sound.volumeUpKeys == Reflect.field(nativeHostSettings, 'volumeUpKeys')
			&& sameDynamicArray(FlxG.sound.volumeUpKeys, Reflect.field(nativeHostSettings, 'volumeUpKeyValues')),
			'Native volume-up keys did not restore by identity and value');
		check(FlxG.mouse.visible == Reflect.field(nativeHostSettings, 'mouseVisible'), 'Native mouse visibility did not restore');
		check(FlxG.sound.muted == Reflect.field(nativeHostSettings, 'soundMuted')
			&& FlxG.sound.volume == Reflect.field(nativeHostSettings, 'soundVolume'), 'Native sound settings did not restore');
		check(Application.current.window.frameRate == Reflect.field(nativeHostSettings, 'windowFrameRate'),
			'Native window frame-rate option did not restore');
		check(FlxG.updateFramerate == Reflect.field(nativeHostSettings, 'updateFramerate')
			&& FlxG.drawFramerate == Reflect.field(nativeHostSettings, 'drawFramerate'),
			'Native Flixel frame-rate settings did not restore');
	}

	static function copyDynamicArray(value:Dynamic):Array<Dynamic> {
		if (value == null) return null;
		check(Std.isOfType(value, Array), 'Expected native key binding array');
		return (cast value:Array<Dynamic>).copy();
	}

	static function sameDynamicArray(value:Dynamic, expected:Array<Dynamic>):Bool {
		if (expected == null) return value == null;
		if (!Std.isOfType(value, Array)) return false;
		var actual:Array<Dynamic> = cast value;
		if (actual.length != expected.length) return false;
		for (index in 0...actual.length) if (actual[index] != expected[index]) return false;
		return true;
	}

	/** Resolve the current generated fixture only through a committed retained
	 * import, its verified source snapshot, and the public installed family API. */
	static function resolveRetainedEvidence():Dynamic {
		var install = Sys.getCwd();
		var recordsRoot = Path.join([install, 'import-cache', 'records']);
		check(FileSystem.isDirectory(recordsRoot), 'Retained import record directory missing');
		var candidates:Array<Dynamic> = [];
		var candidateFailures:Array<String> = [];
		var names = FileSystem.readDirectory(recordsRoot);
		names.sort(Reflect.compare);
		for (name in names) {
			if (!~/^[a-f0-9]{64}\.json$/i.match(name)) continue;
			var id = name.substr(0, 64).toLowerCase();
			var pointerPath = Path.join([recordsRoot, name]);
			if (!FileSystem.exists(pointerPath) || FileSystem.isDirectory(pointerPath)) continue;
			try {
				var pointer:Dynamic = Json.parse(File.getContent(pointerPath));
				if (Reflect.field(pointer, 'id') != id) continue;
				var owner = 'retained-import:' + id;
				var manifest = ImportRefreshTransaction.loadManifest(Path.join([install, 'import-cache', 'state']), owner);
				if (manifest == null || manifest.owner != owner || manifest.revision == null) continue;
				var record:Dynamic = Reflect.field(manifest.revision, 'importRecord');
				if (record == null || Reflect.field(record, 'id') != id) continue;
				var catalog:Dynamic = manifest.packageFamilyCatalog;
				if (catalog == null || Reflect.field(catalog, 'version') != 2
					|| Reflect.field(catalog, 'engine') != 'Nightmare Vision') continue;
				var rawMembers:Dynamic = Reflect.field(catalog, 'members');
				if (!Std.isOfType(rawMembers, Array)) continue;
				var catalogMembers:Array<Dynamic> = cast rawMembers;
				if (catalogMembers.length != 2) continue;
				var alpha:Dynamic = null;
				var beta:Dynamic = null;
				for (member in catalogMembers) {
					if (member == null || !Std.isOfType(Reflect.field(member, 'directory'), String)) continue;
					var label = Std.string(Reflect.field(member, 'directory'));
					if (label.toLowerCase() == 'alpha') alpha = member;
					if (label.toLowerCase() == 'beta') beta = member;
				}
				if (alpha == null || beta == null) continue;
				try candidates.push(verifyRetainedCandidate(install, id, owner, manifest, record, catalog, alpha, beta))
				catch (error:Dynamic) candidateFailures.push(Std.string(error));
			} catch (_:Dynamic) {
				// One unrelated or stale record cannot mask the new committed import.
			}
		}
		if (candidates.length == 0) {
			var detail = candidateFailures.length == 0 ? '' : ': ' + candidateFailures[0];
			throw 'No unique committed alpha/beta retained import with a valid chart and source audio' + detail;
		}
	check(candidates.length == 1, 'Ambiguous committed alpha/beta retained import records');
		return candidates[0];
	}

	static function verifyRetainedCandidate(install:String, id:String, owner:String, manifest:ImportRefreshManifest,
		record:Dynamic, catalog:Dynamic, alphaCatalog:Dynamic, betaCatalog:Dynamic):Dynamic {
		var snapshotIdValue:Dynamic = Reflect.field(record, 'snapshotId');
		check(Std.isOfType(snapshotIdValue, String) && ~/^[a-f0-9]{64}$/i.match(Std.string(snapshotIdValue)),
			'Retained import snapshot id invalid');
		var snapshotId = Std.string(snapshotIdValue).toLowerCase();
		check(Reflect.field(record, 'source') == 'sources/' + snapshotId + '/content', 'Retained import source path invalid');
		var snapshotRoot = Path.join([install, 'import-cache', 'sources', snapshotId]);
		// This opt-in probe runs on the game thread. A child verification pool
		// would wait behind its gameplay lease while the game waits for the pool.
		ImportSourceSnapshot.verify(snapshotRoot, snapshotId, null, null, 1);
		var snapshotReceipt:Dynamic = Json.parse(File.getContent(Path.join([snapshotRoot, 'receipt.json'])));
		var incomplete:Dynamic = Reflect.field(snapshotReceipt, 'incompleteReasons');
		check(Std.isOfType(incomplete, Array) && (cast incomplete:Array<Dynamic>).length == 0,
			'Retained source receipt is incomplete');
		var snapshotFiles:Dynamic = Reflect.field(snapshotReceipt, 'files');
		check(Std.isOfType(snapshotFiles, Array), 'Retained source receipt file list missing');
		var alphaSource = checkedSourceRelative(alphaCatalog, catalog);
		var betaSource = checkedSourceRelative(betaCatalog, catalog);
		var containerRelative = Std.string(Reflect.field(catalog, 'containerRelative'));
		check(alphaSource.startsWith(containerRelative + '/') && betaSource.startsWith(containerRelative + '/'),
			'Retained family paths do not match their catalog container');
		var sourceChart = findRetainedSourceFile(snapshotRoot, cast snapshotFiles, alphaSource, 'chart');
		var sourceAudio = findRetainedSourceFile(snapshotRoot, cast snapshotFiles, alphaSource, 'audio');
		var sourceCore = findRetainedSourceCore(snapshotRoot, cast snapshotFiles);
		var sourceFont = findRetainedSourceAsset(snapshotRoot, cast snapshotFiles, 'assets/fonts/consolas.ttf');
		check(sourceChart != null && sourceAudio != null, 'Alpha source snapshot lacks its chart or audio payload');
		check(!hasRetainedSongPayload(cast snapshotFiles, betaSource), 'Chartless beta source unexpectedly contains song data or audio');
		var sourceChartData:Dynamic = Json.parse(File.getContent(Path.join([snapshotRoot, 'content', sourceChart.path])));
		check(isPlayableNmvChart(sourceChartData), 'Retained alpha source chart is not a playable NMV chart');
		check(ImportSourceSnapshot.sha256File(Path.join([snapshotRoot, 'content', sourceChart.path])) == sourceChart.sha256
			&& ImportSourceSnapshot.sha256File(Path.join([snapshotRoot, 'content', sourceAudio.path])) == sourceAudio.sha256,
			'Retained source chart or audio digest changed after verification');

		var alphaRootFromCatalog = rootForCatalog(alphaCatalog);
		var betaRootFromCatalog = rootForCatalog(betaCatalog);
		var family = ImportPackageFamilyCatalog.forOwner(alphaRootFromCatalog);
		check(family != null && family.length == 2, 'Public retained owner resolver did not return both family members');
		var alphaRoot = memberRoot(family, 'alpha');
		var betaRoot = memberRoot(family, 'beta');
		check(alphaRoot == alphaRootFromCatalog && betaRoot == betaRootFromCatalog,
			'Public retained family roots differ from the committed catalog');
		verifyPackageMetadata(install, alphaRoot, 'alpha');
		verifyPackageMetadata(install, betaRoot, 'beta');
		verifyManifestOutput(install, manifest, owner, Path.join([alphaRoot, 'meta.json']));
		verifyManifestOutput(install, manifest, owner, Path.join([betaRoot, 'meta.json']));
		var alphaCore = verifyManifestOutput(install, manifest, owner,
			Path.join([alphaRoot, NightmareVisionAssetCollector.CORE_SUBTREE, 'data', 'retained-source-core.txt']));
		var betaCore = verifyManifestOutput(install, manifest, owner,
			Path.join([betaRoot, NightmareVisionAssetCollector.CORE_SUBTREE, 'data', 'retained-source-core.txt']));
		var alphaFont = verifyManifestOutput(install, manifest, owner,
			Path.join([alphaRoot, NightmareVisionAssetCollector.CORE_SUBTREE, 'fonts', 'consolas.ttf']));
		var betaFont = verifyManifestOutput(install, manifest, owner,
			Path.join([betaRoot, NightmareVisionAssetCollector.CORE_SUBTREE, 'fonts', 'consolas.ttf']));
		check(Reflect.field(alphaCore, 'sha256') == sourceCore.sha256
			&& Reflect.field(betaCore, 'sha256') == sourceCore.sha256,
			'Root-owned source core asset did not reach both retained family roots intact');
		check(Reflect.field(alphaFont, 'sha256') == sourceFont.sha256
			&& Reflect.field(betaFont, 'sha256') == sourceFont.sha256,
			'Root-owned Consolas font did not reach both retained family roots intact');
		verifyManifestOutput(install, manifest, owner, Path.join([alphaRoot, 'scripts', 'plugins', 'FixtureInit.hx']));
		verifyManifestOutput(install, manifest, owner, Path.join([betaRoot, 'scripts', 'states', 'FixtureTitle.hx']));

		var alphaKey = ImportPackageFamilyCatalog.forOwner(alphaRoot);
		check(alphaKey.length == 2, 'Retained family lookup became unstable during validation');
		var chart = findImportedChart(install, manifest, owner, alphaRoot);
		check(chart != null, 'Retained alpha source chart was not converted and published');
		checkNoImportedChart(install, manifest, owner, betaRoot);
		var audio = findImportedAudio(install, manifest, owner, chart.folder);
		check(audio != null, 'Retained alpha chart audio was not published');
		return {
			owner:owner, transactionId:manifest.transactionId, snapshotId:snapshotId,
			containerRelative:containerRelative, alphaRoot:alphaRoot, betaRoot:betaRoot, family:family,
			chart:{folder:chart.folder, path:chart.path, sha256:chart.sha256, owner:alphaRoot},
			audio:{path:audio.path, sha256:audio.sha256},
			sourceCore:{path:sourceCore.path, sha256:sourceCore.sha256},
			sourceFont:{path:sourceFont.path, sha256:sourceFont.sha256},
			sourceChart:{path:sourceChart.path, sha256:sourceChart.sha256},
			sourceAudio:{path:sourceAudio.path, sha256:sourceAudio.sha256}
		};
	}

	static function checkedSourceRelative(member:Dynamic, catalog:Dynamic):String {
		var sourceValue:Dynamic = Reflect.field(member, 'sourceRelative');
		var namespaceValue:Dynamic = Reflect.field(member, 'namespace');
		check(Std.isOfType(sourceValue, String) && Std.isOfType(namespaceValue, String)
			&& Std.string(namespaceValue) != '', 'V2 retained catalog member is incomplete');
		var source = StringTools.replace(Std.string(sourceValue), '\\', '/');
		check(!source.startsWith('/') && source.indexOf(':') < 0, 'Retained source member path is not relative');
		for (part in source.split('/')) check(part != '' && part != '.' && part != '..', 'Retained source member path is unsafe');
		check(Reflect.field(catalog, 'version') == 2, 'Retained family catalog is not v2');
		return source;
	}

	static function rootForCatalog(member:Dynamic):String {
		var namespace = Std.string(Reflect.field(member, 'namespace'));
		check(CodenameScriptDiscovery.safeName(namespace), 'Retained namespace is invalid');
		return Path.normalize('assets/imported_mods/' + namespace);
	}

	static function memberRoot(family:Array<NightmareVisionModFamilyMember>, directory:String):String {
		var found:String = null;
		for (member in family) if (member != null && member.directory.toLowerCase() == directory) {
			check(found == null, 'Retained family has duplicate directory labels');
			found = member.root;
		}
		check(found != null, 'Retained family member missing: ' + directory);
		return found;
	}

	static function verifyPackageMetadata(install:String, root:String, label:String):Void {
		var path = Path.join([install, root, 'meta.json']);
		check(FileSystem.exists(path) && !FileSystem.isDirectory(path), 'Installed package meta.json missing: ' + label);
		var meta:Dynamic = Json.parse(File.getContent(path));
		check(Reflect.field(meta, 'name') == label, 'Installed package metadata label mismatch: ' + label);
	}

	static function verifyManifestOutput(install:String, manifest:ImportRefreshManifest, owner:String, relativePath:String):Dynamic {
		var clean = StringTools.replace(Path.normalize(relativePath), '\\', '/');
		var found:Dynamic = null;
		for (entry in manifest.files) if (StringTools.replace(entry.path, '\\', '/').toLowerCase() == clean.toLowerCase()) {
			check(found == null, 'Retained manifest duplicates an output path: ' + clean);
			found = entry;
		}
		check(found != null && Reflect.field(found, 'owner') == owner, 'Retained import does not own expected output: ' + clean);
		var absolute = Path.join([install, clean]);
		check(FileSystem.exists(absolute) && !FileSystem.isDirectory(absolute), 'Retained import output missing: ' + clean);
		check(ImportSourceSnapshot.sha256File(absolute) == Reflect.field(found, 'sha256'), 'Retained import output hash changed: ' + clean);
		return found;
	}

	static function findRetainedSourceFile(snapshotRoot:String, files:Array<Dynamic>, sourceRoot:String, kind:String):Dynamic {
		var prefix = sourceRoot.toLowerCase() + '/assets/songs/';
		var matches:Array<Dynamic> = [];
		for (entry in files) {
			var pathValue:Dynamic = Reflect.field(entry, 'path');
			if (!Std.isOfType(pathValue, String)) continue;
			var path = StringTools.replace(Std.string(pathValue), '\\', '/');
			var lower = path.toLowerCase();
			if (!lower.startsWith(prefix)) continue;
			var selected = kind == 'chart'
				? lower.indexOf('/data/') >= 0 && Path.extension(path).toLowerCase() == 'json'
				: lower.endsWith('/audio/inst.ogg');
			if (selected) matches.push(entry);
		}
		check(matches.length == 1, 'Retained source must contain exactly one fixture ' + kind);
		var entry:Dynamic = matches[0];
		var relative = Std.string(Reflect.field(entry, 'path'));
		var expectedHash:Dynamic = Reflect.field(entry, 'sha256');
		check(Std.isOfType(expectedHash, String) && ~/^[a-f0-9]{64}$/i.match(Std.string(expectedHash)),
			'Retained source receipt hash is invalid: ' + relative);
		var path = Path.join([snapshotRoot, 'content', relative]);
		check(FileSystem.exists(path) && !FileSystem.isDirectory(path), 'Retained source payload missing: ' + relative);
		return {path:relative, sha256:Std.string(expectedHash).toLowerCase()};
	}

	static function findRetainedSourceCore(snapshotRoot:String, files:Array<Dynamic>):Dynamic {
		return findRetainedSourceAsset(snapshotRoot, files, 'assets/data/retained-source-core.txt');
	}

	static function findRetainedSourceAsset(snapshotRoot:String, files:Array<Dynamic>, relativePath:String):Dynamic {
		var expectedPath = StringTools.replace(relativePath, '\\', '/').toLowerCase();
		var found:Dynamic = null;
		for (entry in files) {
			var pathValue:Dynamic = Reflect.field(entry, 'path');
			if (!Std.isOfType(pathValue, String)
				|| StringTools.replace(Std.string(pathValue), '\\', '/').toLowerCase() != expectedPath) continue;
			check(found == null, 'Retained source receipt duplicates root-owned asset: ' + relativePath);
			var expectedHash:Dynamic = Reflect.field(entry, 'sha256');
			check(Std.isOfType(expectedHash, String) && ~/^[a-f0-9]{64}$/i.match(Std.string(expectedHash)),
				'Retained game-root asset receipt hash is invalid: ' + relativePath);
			var path = Path.join([snapshotRoot, 'content', relativePath]);
			check(FileSystem.exists(path) && !FileSystem.isDirectory(path)
				&& ImportSourceSnapshot.sha256File(path) == Std.string(expectedHash).toLowerCase(),
				'Retained game-root asset does not match its source receipt: ' + relativePath);
			found = {path:relativePath, sha256:Std.string(expectedHash).toLowerCase()};
		}
		check(found != null, 'Retained source receipt omitted its root-owned asset: ' + relativePath);
		return found;
	}

	static function hasRetainedSongPayload(files:Array<Dynamic>, sourceRoot:String):Bool {
		var prefix = StringTools.replace(sourceRoot, '\\', '/').toLowerCase() + '/assets/songs/';
		for (entry in files) {
			var path:Dynamic = Reflect.field(entry, 'path');
			if (Std.isOfType(path, String)
				&& StringTools.replace(Std.string(path), '\\', '/').toLowerCase().startsWith(prefix)) return true;
		}
		return false;
	}

	static function isPlayableNmvChart(chart:Dynamic):Bool {
		var song:Dynamic = chart == null ? null : Reflect.field(chart, 'song');
		var notes:Dynamic = song == null ? null : Reflect.field(song, 'notes');
		return song != null && Reflect.field(song, 'format') == 'nmv2'
			&& Std.isOfType(notes, Array) && (cast notes:Array<Dynamic>).length > 0;
	}

	static function findImportedChart(install:String, manifest:ImportRefreshManifest, owner:String, alphaRoot:String):Dynamic {
		var matches:Array<Dynamic> = [];
		for (entry in manifest.files) {
			var path = StringTools.replace(entry.path, '\\', '/');
			var parts = path.split('/');
			if (parts.length != 4 || parts[0].toLowerCase() != 'assets' || parts[1].toLowerCase() != 'data'
				|| Path.extension(path).toLowerCase() != 'json') continue;
			if (entry.owner != owner) continue;
			var folder = parts[2];
			// Retained song companions also contain playable donor JSON. Select
			// the registered default chart, exactly as native Freeplay does.
			if (Path.withoutExtension(parts[3]).toLowerCase() != folder.toLowerCase()) continue;
			if (ImportedModDiscovery.ownerForSong(folder, 'assets/data') != alphaRoot) continue;
			var compatPath = Path.join([install, 'assets', 'data', folder, CompatScriptManifest.FILE_NAME]);
			if (!FileSystem.exists(compatPath) || FileSystem.isDirectory(compatPath)) continue;
			var compat = CompatScriptManifest.parse(File.getContent(compatPath));
			if (CompatScriptManifest.selectedRoot(compat) != alphaRoot) continue;
			var absolute = Path.join([install, path]);
			if (!FileSystem.exists(absolute) || FileSystem.isDirectory(absolute)) continue;
			var chart:Dynamic = Json.parse(File.getContent(absolute));
			if (!isPlayableNmvChart(chart)) continue;
			verifyManifestOutput(install, manifest, owner, path);
			matches.push({folder:folder, path:path, sha256:entry.sha256});
		}
		check(matches.length == 1, 'Retained alpha import must publish exactly one owned NMV chart');
		return matches[0];
	}

	static function findImportedAudio(install:String, manifest:ImportRefreshManifest, owner:String, songFolder:String):Dynamic {
		var prefix = ('assets/songs/' + songFolder + '/').toLowerCase();
		var matches:Array<Dynamic> = [];
		for (entry in manifest.files) {
			var path = StringTools.replace(entry.path, '\\', '/');
			if (entry.owner != owner || path.toLowerCase() != prefix + 'inst.ogg') continue;
			verifyManifestOutput(install, manifest, owner, path);
			matches.push({path:path, sha256:entry.sha256});
		}
		check(matches.length == 1, 'Retained alpha import must publish exactly one owned Inst.ogg');
		return matches[0];
	}

	static function checkNoImportedChart(install:String, manifest:ImportRefreshManifest, owner:String, betaRoot:String):Void {
		for (entry in manifest.files) {
			var path = StringTools.replace(entry.path, '\\', '/');
			var parts = path.split('/');
			if (entry.owner != owner || parts.length != 4 || parts[0].toLowerCase() != 'assets'
				|| parts[1].toLowerCase() != 'data' || Path.extension(path).toLowerCase() != 'json') continue;
			if (ImportedModDiscovery.ownerForSong(parts[2], 'assets/data') == betaRoot)
				throw 'Chartless beta unexpectedly owns an imported chart: ' + path;
		}
	}

	static function count(name:String):Int {var result = 0; for (event in events) if (event == name) result++; return result;}
	static function invoke(name:String):Void {
		var state:NightmareVisionMusicBeatState = cast FlxG.state;
		state.scriptGroup.call(name, []);
	}
	static function capture(name:String):Void {
		currentCapture = name; rendered = 0; capturing = true;
		Application.current.window.onRender.add(onRendered, false, -1000);
	}
	static function onRendered(context:lime.graphics.RenderContext):Void {
		if (!capturing || RuntimeSmokeHarness.finished || ++rendered < 3) return;
		Application.current.window.onRender.remove(onRendered);
		try {
			var pixels = Application.current.window.readPixels(); check(pixels != null, 'Native state framebuffer missing');
			var stem = Sys.getEnv('CAMMIE_NV_STATE_CAPTURE'); check(stem != null && stem != '', 'State capture stem missing');
			File.saveBytes(stem + '-' + currentCapture + '.png', pixels.encode()); capturing = false;
			if (currentCapture == 'splash') {splashCaptured = true; return;}
			if (phase == 1) {phase = 2; invoke('onProbeReset');}
			else {phase = 5; FlxG.switchState(FreeplayState.new);}
		} catch (error:Dynamic) RuntimeSmokeHarness.fail('nv-state-render', Std.string(error));
	}
}
#end
