package;

import haxe.Json;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxSubState;
using StringTools;

#if sys
import haxe.io.Path;
import haxe.io.Bytes;
import sys.FileSystem;
import sys.io.File;
#end

/**
	Small, native-only launch contract used by the post-build smoke gate.

	The normal game has no command-line mode.  A process becomes a smoke process
	only when one of the `--smoke-*` arguments is present, so menu launches and
	all existing command lines retain their normal TitleState entry point.
*/
typedef RuntimeSmokeOptions = {
	var songFolder:String;
	var chart:String;
	var difficulty:String;
	var durationMs:Int;
	var logPath:String;
	var runtimeRoot:String;
	/** Selected installed Codename owner for a direct chart smoke that models
		entry from that owner's menu. */
	var ownerRoot:String;
	/** Enable the native practice modifier so unattended long runs survive
	    note-heavy sections long enough to exercise mid-song events. */
	var practice:Bool;
	/** Enter PlayState with the normal Story cutscene gate for this one chart. */
	var storyMode:Bool;
	/** Song-rate multiplier (1-50) applied like the demo playback speed so a
	    full imported song fits into a short smoke window. */
	var songRate:Float;
	/** Fail success unless native audio completion reaches the song-end path. */
	var requireSongEnd:Bool;
	/** Require a completed ending to leave PlayState, including result screens. */
	var requireEndHandoff:Bool;
	/** Collect bounded owner-scoped Codename callback/visual snapshots. */
	var codenameVisuals:Bool;
	/** Optional native window resize (WxH) applied once at song start, to
	    exercise the real OS-window resize path headlessly. */
	var windowResize:String;
	/** Open the native FreeplayState over a freeplay registry category and
	    measure frame cost while the harness scrolls and leaves. */
	var freeplay:Bool;
	/** Registry category name for --smoke-freeplay; empty merges every one. */
	var freeplayCategory:String;
	/** Milliseconds between simulated selection moves while in freeplay
	    (0 disables scrolling). */
	var freeplayScrollMs:Int;
	/** Milliseconds after freeplay opens before switching back to the main
	    menu, so post-freeplay pacing can be measured (0 stays until the
	    duration window ends). */
	var freeplayLeaveMs:Int;
	/** Milliseconds after freeplay opens before one simulated ENTER accept,
	    so accept-gated menus (imported confirm popups) are exercised (0
	    disables the simulation).  A second accept is sent inside an opened
	    popup so its confirm/close path runs once. */
	var freeplayAcceptMs:Int;
	/** Accept-gate by song name: keep scrolling until this song is selected,
	    then send the accept and continue through ModifierState into PlayState
	    when the modifier menu is enabled. Empty uses --smoke-freeplay-accept-ms. */
	var freeplayAcceptSong:String;
	/** Emit player-one hit owner and animation state for a focused diagnostic run. */
	var tracePlayerHits:Bool;
	/** Exercise normal player-hit callbacks without desktop input; implies practice. */
	var playerHits:Bool;
	/** Exercise the engine's actual demo/botplay route without saving modifiers. */
	var botplay:Bool;
	var frameStats:Bool;
	/** Optional forward seek after audio starts, used only by the native seek smoke. */
	var seekAfterMs:Float;
	var seekToMs:Float;
	/** Number of PlayState creations in one native smoke process (1 or 2). */
	var playstateVisits:Int;
	/** Enter ChartingState and run one companion-event save/reload round-trip. */
	var chartEditor:Bool;
	/** Optional second chart for a two-visit switch between imported songs. */
	var nextSongFolder:String;
	var nextChart:String;
	var nextDifficulty:String;
}

class RuntimeSmokeHarness {
	static var parsed:Null<RuntimeSmokeOptions>;
	static var smokeArgumentsSeen:Bool = false;
	static var started:Bool = false;
	static var playStateStarted:Bool = false;
	static var playStateReady:Bool = false;
	static var finished:Bool = false;
	static var elapsedMs:Float = 0;
	static var deadline:Float = 0;
	/** Full requested gameplay window, measured from PlayState readiness. */
	static var playDeadline:Float = 0;
	static var visitDeadline:Float = 0;
	static var watchdogDeadline:Float = 0;
	static var runToken:String = '';
	static var visitsStarted:Int = 0;
	static var visitsReady:Int = 0;
	static var visitsDestroyed:Int = 0;
	static var teardownsMarked:Int = 0;
	static var validatedTeardown:Dynamic = null;
	static var transitionPending:Bool = false;
	static var uncaughtHandlerInstalled:Bool = false;
	static var runtimeRootError:String = '';
	static var configurationError:String = '';
	static var playStateLoadStartedAt:Float = 0;
	/** Most recent shared Psych note-skin operation, attached only to a smoke failure. */
	static var psychSkinDiagnosticPhase:String = '';
	static var naturalSongEndObserved:Bool = false;
	static var naturalSongEndAt:Float = -1;
	static var songStartObserved:Bool = false;
	static var seekCompleted:Bool = false;
	static var codenameEventVisualMarkers:Int = 0;
	static var codenameCallbackVisualMarkers:Int = 0;
	static var codenameMotionMarkers:Int = 0;
	static var codenameHitActorCalls:Int = 0;
	static var codenameVisualSignatures:Map<String, String> = new Map();
	/** Primitive hit snapshots awaiting the next update tick, after hit callbacks return. */
	static var pendingPlayerHitProbes:Array<Dynamic> = [];
	static var visualNoteKinds:Map<String, Bool> = new Map();
	static var liveVisualNoteKinds:Map<String, Bool> = new Map();
	static var receptorVisualStates:Map<String, Bool> = new Map();
	static var chartEditorPhase:Int = 0;
	static var chartEditorSidecarPath:String = '';
	#if sys
	static var chartEditorSidecarBytes:Bytes = null;
	#end

	/** True only for an explicit smoke command line. */
	public static function enabled():Bool {
		return config() != null && smokeArgumentsSeen;
	}

	/** Return the parsed launch request, or null for an ordinary launch. */
	public static function config():Null<RuntimeSmokeOptions> {
		if (parsed != null)
			return parsed;
		var result:RuntimeSmokeOptions = {
			songFolder: '',
			chart: '',
			difficulty: 'normal',
			durationMs: 5000,
			logPath: 'tmp/runtime-smoke.log',
			runtimeRoot: '',
			ownerRoot: '',
			practice: false,
			storyMode: false,
			songRate: 1,
			requireSongEnd: false,
			requireEndHandoff: false,
			codenameVisuals: false,
			windowResize: '',
			freeplay: false,
			freeplayCategory: '',
			freeplayScrollMs: 400,
			freeplayLeaveMs: 0,
			freeplayAcceptMs: 0,
			freeplayAcceptSong: '',
			tracePlayerHits: false,
			playerHits: false,
			botplay: false,
			frameStats: false,
			seekAfterMs: -1,
			seekToMs: -1,
			playstateVisits: 1,
			chartEditor: false,
			nextSongFolder: '',
			nextChart: '',
			nextDifficulty: ''
		};
		#if sys
		var args = Sys.args();
		var index = 0;
		var difficultyProvided = false;
		while (index < args.length) {
			var raw = args[index];
			var key = raw;
			var value:Null<String> = null;
			var equals = raw.indexOf('=');
			if (equals >= 0) {
				key = raw.substr(0, equals);
				value = raw.substr(equals + 1);
			} else if (index + 1 < args.length && !args[index + 1].startsWith('--')) {
				value = args[index + 1];
				index++;
			}
			switch (key) {
				case '--smoke-song' | '--smoke-folder':
					smokeArgumentsSeen = true;
					result.songFolder = safeToken(value);
				case '--smoke-chart':
					smokeArgumentsSeen = true;
					result.chart = safeToken(value);
				case '--smoke-difficulty':
					smokeArgumentsSeen = true;
					result.difficulty = safeToken(value);
					difficultyProvided = true;
				case '--smoke-duration-ms':
					smokeArgumentsSeen = true;
					result.durationMs = boundedDuration(parseInt(value, result.durationMs));
				case '--smoke-duration':
					smokeArgumentsSeen = true;
					result.durationMs = boundedDuration(parseInt(value, 5) * 1000);
				case '--smoke-log':
					smokeArgumentsSeen = true;
					result.logPath = value == null ? '' : StringTools.trim(value);
				case '--smoke-runtime-root' | '--smoke-fixture-root':
					smokeArgumentsSeen = true;
					result.runtimeRoot = value == null ? '' : StringTools.trim(value);
				case '--smoke-owner-root':
					smokeArgumentsSeen = true;
					result.ownerRoot = value == null ? '' : StringTools.trim(value);
				case '--smoke-practice':
					smokeArgumentsSeen = true;
					result.practice = true;
				case '--smoke-story-mode':
					smokeArgumentsSeen = true;
					result.storyMode = true;
				case '--smoke-window':
					smokeArgumentsSeen = true;
					result.windowResize = value == null ? '' : StringTools.trim(value);
				case '--smoke-song-rate':
					smokeArgumentsSeen = true;
					var rate:Null<Float> = Std.parseFloat(value == null ? '' : StringTools.trim(value));
					result.songRate = rate == null || Math.isNaN(rate) ? 1
						: Math.max(1, Math.min(50, rate));
				case '--smoke-require-song-end':
					smokeArgumentsSeen = true;
					result.requireSongEnd = true;
				case '--smoke-require-end-handoff':
					smokeArgumentsSeen = true;
					result.requireSongEnd = true;
					result.requireEndHandoff = true;
				case '--smoke-codename-visuals':
					smokeArgumentsSeen = true;
					result.codenameVisuals = true;
				case '--smoke-freeplay':
					smokeArgumentsSeen = true;
					result.freeplay = true;
				case '--smoke-freeplay-category':
					smokeArgumentsSeen = true;
					result.freeplayCategory = safeToken(value);
				case '--smoke-freeplay-scroll-ms':
					smokeArgumentsSeen = true;
					result.freeplayScrollMs = parseInt(value, result.freeplayScrollMs);
				case '--smoke-freeplay-leave-ms':
					smokeArgumentsSeen = true;
					result.freeplayLeaveMs = parseInt(value, result.freeplayLeaveMs);
				case '--smoke-freeplay-accept-ms':
					smokeArgumentsSeen = true;
					result.freeplayAcceptMs = parseInt(value, result.freeplayAcceptMs);
				case '--smoke-freeplay-select':
					smokeArgumentsSeen = true;
					result.freeplayAcceptSong = safeToken(value);
				case '--smoke-trace-player-hits':
					smokeArgumentsSeen = true;
					result.tracePlayerHits = true;
				case '--smoke-player-hits':
					smokeArgumentsSeen = true;
					result.playerHits = true;
					result.practice = true;
				case '--smoke-botplay':
					smokeArgumentsSeen = true;
					result.botplay = true;
				case '--smoke-frame-stats':
					smokeArgumentsSeen = true;
					result.frameStats = true;
				case '--smoke-seek-after-ms':
					smokeArgumentsSeen = true;
					result.seekAfterMs = parseSmokeTime(value);
					if (result.seekAfterMs < 0) configurationError = 'invalid --smoke-seek-after-ms';
				case '--smoke-seek-to-ms':
					smokeArgumentsSeen = true;
					result.seekToMs = parseSmokeTime(value);
					if (result.seekToMs < 0) configurationError = 'invalid --smoke-seek-to-ms';
				case '--smoke-playstate-visits':
					smokeArgumentsSeen = true;
					result.playstateVisits = parsePlaystateVisits(value);
				case '--smoke-chart-editor':
					smokeArgumentsSeen = true;
					result.chartEditor = true;
				case '--smoke-next-song':
					smokeArgumentsSeen = true;
					result.nextSongFolder = safeToken(value);
					if (result.nextSongFolder == '') configurationError = 'invalid --smoke-next-song';
				case '--smoke-next-chart':
					smokeArgumentsSeen = true;
					result.nextChart = safeToken(value);
					if (result.nextChart == '') configurationError = 'invalid --smoke-next-chart';
				case '--smoke-next-difficulty':
					smokeArgumentsSeen = true;
					result.nextDifficulty = safeToken(value);
					if (result.nextDifficulty == '') configurationError = 'invalid --smoke-next-difficulty';
				default:
			}
			index++;
		}
		#else
		// The native smoke gate is intentionally unavailable on web/mobile.
		smokeArgumentsSeen = false;
		#end
		if (!smokeArgumentsSeen) {
			parsed = null;
			return null;
		}
		if (result.playstateVisits != 1 && result.playstateVisits != 2) {
			configurationError = '--smoke-playstate-visits requires 1 or 2';
			result.playstateVisits = 1;
		}
		if (result.nextSongFolder == '' && (result.nextChart != '' || result.nextDifficulty != ''))
			configurationError = '--smoke-next-song is required for a second chart';
		if (result.nextSongFolder != '' && result.playstateVisits != 2)
			configurationError = '--smoke-next-song requires --smoke-playstate-visits 2';
		if (result.chartEditor && (result.playstateVisits != 1 || result.freeplay || result.requireSongEnd))
			configurationError = '--smoke-chart-editor cannot be combined with multi-visit, freeplay, or song-end smoke';
		var hasSeekAfter = result.seekAfterMs >= 0;
		var hasSeekTarget = result.seekToMs >= 0;
		if (hasSeekAfter != hasSeekTarget)
			configurationError = 'both --smoke-seek-after-ms and --smoke-seek-to-ms are required';
		if (hasSeekAfter && hasSeekTarget) {
			if (result.seekToMs <= result.seekAfterMs)
				configurationError = '--smoke-seek-to-ms must be greater than --smoke-seek-after-ms';
			if (!result.botplay)
				configurationError = 'native seek smoke requires --smoke-botplay';
			if (result.playstateVisits != 1 || result.chartEditor || result.freeplay || result.requireSongEnd)
				configurationError = 'native seek smoke requires one direct gameplay visit';
		}
		if (result.difficulty == '')
			result.difficulty = 'normal';
		if (result.chart == '' && result.songFolder != '') {
			result.chart = result.difficulty == 'normal'
				? result.songFolder : result.songFolder + '-' + result.difficulty;
		}
		if (!difficultyProvided && result.difficulty == 'normal'
			&& result.chart != '' && result.songFolder != '')
			result.difficulty = inferDifficulty(result.songFolder, result.chart);
		if (result.nextSongFolder != '') {
			if (result.nextDifficulty == '')
				result.nextDifficulty = result.nextChart == '' ? 'normal'
					: inferDifficulty(result.nextSongFolder, result.nextChart);
			if (result.nextChart == '')
				result.nextChart = result.nextDifficulty == 'normal' ? result.nextSongFolder
					: result.nextSongFolder + '-' + result.nextDifficulty;
		}
		parsed = result;
		return parsed;
	}

	/** The second RuntimeSmokeState is created after the first PlayState was destroyed. */
	public static function nextVisitSelection():Dynamic {
		var request = config();
		if (request == null) return null;
		if (visitsStarted == 1 && request.playstateVisits == 2 && request.nextSongFolder != '')
			return {songFolder: request.nextSongFolder, chart: request.nextChart,
				difficulty: request.nextDifficulty};
		return {songFolder: request.songFolder, chart: request.chart,
			difficulty: request.difficulty};
	}

	/** Record the exact storage folder and difficulty before each chart load. */
	public static function markVisitSelection(selection:Dynamic):Void {
		if (!enabled() || selection == null) return;
		emit('visit_selection', {
			visit: visitsStarted + 1,
			songFolder: Reflect.field(selection, 'songFolder'),
			chart: Reflect.field(selection, 'chart'),
			difficulty: Reflect.field(selection, 'difficulty')
		});
	}

	public static function playerHitsEnabled():Bool
		return enabled() && config().playerHits;

	/** Whether ChartingState should run the opt-in editor round-trip. */
	public static function chartEditorSmokeEnabled():Bool
		return enabled() && config().chartEditor;

	/** Mark editor setup boundaries only for the opt-in chart editor smoke. */
	public static function markChartEditorCreatePhase(phase:String):Void {
		if (chartEditorSmokeEnabled() && !finished)
			emit('chart_editor_create_phase', {phase: phase});
	}

	/** True on the ChartingState creation caused by the smoke Quick Save reload. */
	public static function chartEditorReloadExpected():Bool
		return chartEditorSmokeEnabled() && chartEditorPhase == 1;

	public static function markChartEditorLoaded(details:Dynamic):Void {
		if (chartEditorSmokeEnabled() && !finished)
			emit('chart_editor_loaded', details);
	}

	public static function markChartEditorEdited(details:Dynamic):Void {
		if (chartEditorSmokeEnabled() && !finished)
			emit('chart_editor_edited', details);
	}

	public static function markChartEditorRuntimeCollection(details:Dynamic):Void {
		if (chartEditorSmokeEnabled() && !finished)
			emit('chart_editor_runtime_collection', details);
	}

	/** Capture the isolated companion bytes immediately before Quick Save. */
	public static function markChartEditorQuickSave(sidecarPath:String, details:Dynamic):Void {
		if (!chartEditorSmokeEnabled() || finished)
			return;
		if (chartEditorPhase != 0) {
			fail('chart-editor-sequence', 'Quick Save ran outside the first ChartingState visit');
			return;
		}
		#if sys
		try {
			if (!FileSystem.exists(sidecarPath))
				throw 'companion sidecar disappeared before Quick Save: ' + sidecarPath;
			chartEditorSidecarBytes = File.getBytes(sidecarPath);
			chartEditorSidecarPath = sidecarPath;
			chartEditorPhase = 1;
			emit('chart_editor_quicksave', details);
		} catch (error:Dynamic) {
			fail('chart-editor-sidecar', Std.string(error));
		}
		#else
		fail('chart-editor-platform', 'Chart editor smoke requires a native filesystem');
		#end
	}

	/** Verify the reloaded editor kept the original sidecar byte-for-byte. */
	public static function markChartEditorReloadComplete(sidecarPath:String, details:Dynamic):Void {
		if (!chartEditorSmokeEnabled() || finished)
			return;
		if (chartEditorPhase != 1 || sidecarPath != chartEditorSidecarPath) {
			fail('chart-editor-sequence', 'Reload did not return to the selected owner sidecar');
			return;
		}
		#if sys
		try {
			if (!FileSystem.exists(sidecarPath)
				|| chartEditorSidecarBytes.compare(File.getBytes(sidecarPath)) != 0)
				throw 'companion sidecar bytes changed during editor round-trip';
			chartEditorPhase = 2;
			emit('chart_editor_reloaded', details);
			emit('chart_editor_sidecar_unchanged', {path: sidecarPath});
			succeed();
		} catch (error:Dynamic) {
			fail('chart-editor-sidecar', Std.string(error));
		}
		#end
	}

	/** Synchronous swap measurements are separate from the startup decode window. */
	public static function beginCharacterSwap():Float {
		if (!enabled() || !playStateReady || finished)
			return -1;
		RuntimeDecodeMetrics.reset(true);
		return haxe.Timer.stamp();
	}

	public static function markCharacterSwap(startedAt:Float, character:String, role:String):Void {
		if (startedAt < 0)
			return;
		var snapshot:Dynamic = RuntimeDecodeMetrics.snapshot();
		Reflect.setField(snapshot, 'character', character);
		Reflect.setField(snapshot, 'role', role);
		Reflect.setField(snapshot, 'elapsedMs', (haxe.Timer.stamp() - startedAt) * 1000);
		emit('character_swap_decode', snapshot);
		RuntimeDecodeMetrics.reset(false);
	}

	/**
		Switch the process to an optional fixture/export root before OptionsHandler
		or FlxGame resolve any relative assets.  The matrix normally leaves this
		empty (the built binary's directory remains the runtime root); a temporary
		import overlay can provide a root containing its own `assets/` tree without
		copying or modifying donor files.
	*/
	public static function applyRuntimeRoot():Void {
		var request = config();
		if (request == null || request.runtimeRoot == '')
			return;
		#if sys
		try {
			Sys.setCwd(request.runtimeRoot);
		} catch (error:Dynamic) {
			runtimeRootError = Std.string(error);
		}
		#end
	}

	public static function getRuntimeRootError():String
		return runtimeRootError;

	public static function getConfigurationError():String
		return configurationError;

	/** Install a best-effort uncaught-error bridge for failures during create(). */
	public static function installUncaughtErrorHandler():Void {
		if (!enabled() || uncaughtHandlerInstalled)
			return;
		uncaughtHandlerInstalled = true;
		#if sys
		try {
			var current:Dynamic = openfl.Lib.current;
			var loaderInfo:Dynamic = current == null ? null : Reflect.field(current, 'loaderInfo');
			var errorEvents:Dynamic = loaderInfo == null ? null : Reflect.field(loaderInfo, 'uncaughtErrorEvents');
			var add = errorEvents == null ? null : Reflect.field(errorEvents, 'addEventListener');
			if (errorEvents != null && add != null)
				Reflect.callMethod(errorEvents, add, ['uncaughtError', function(event:Dynamic):Void {
					var error = event == null ? 'uncaught error' : Reflect.field(event, 'error');
					fail('uncaught', error == null ? 'uncaught error' : Std.string(error));
				}]);
		} catch (_:Dynamic) {
			// The native process exit code still reports an uncaught exception when
			// a target does not expose OpenFL's event bridge.
		}
		#end
	}

	/** Emit the machine-readable startup marker before loading any chart data. */
	public static function start():Void {
		if (!enabled() || started)
			return;
		started = true;
		elapsedMs = 0;
		runToken = Std.string(haxe.Timer.stamp());
		#if sys
		deadline = Sys.time() + config().durationMs / 1000.0;
		watchdogDeadline = Sys.time() + (config().durationMs / 1000.0) * config().playstateVisits
			+ 120;
		#end
		emit('startup', {
			songFolder: config().songFolder,
			chart: config().chart,
			difficulty: config().difficulty,
			durationMs: config().durationMs,
			fpsCap: OptionsHandler.options.fpsCap,
			updateFramerate: FlxG.updateFramerate,
			drawFramerate: FlxG.drawFramerate,
			runtimeRoot: config().runtimeRoot,
			ownerRoot: config().ownerRoot,
			playstateVisits: config().playstateVisits,
			nextSongFolder: config().nextSongFolder,
			nextChart: config().nextChart,
			nextDifficulty: config().nextDifficulty
		});
	}

	/** Mark entry into PlayState.create(). */
	public static function markPlayStateStart(song:Dynamic):Void {
		if (!enabled() || finished)
			return;
		if (config().playstateVisits == 2) {
			if (visitsStarted >= 2 || (visitsStarted > 0 && visitsDestroyed != visitsStarted)) {
				fail('reload-sequence', 'PlayState started before the previous visit was destroyed');
				return;
			}
			visitsStarted++;
			transitionPending = false;
		} else visitsStarted = 1;
		visualNoteKinds = new Map();
		liveVisualNoteKinds = new Map();
		psychSkinDiagnosticPhase = '';
		playStateStarted = true;
		playStateReady = false;
		playStateLoadStartedAt = haxe.Timer.stamp();
		RuntimeDecodeMetrics.reset(true);
		var name = song == null ? '' : Std.string(Reflect.field(song, 'song'));
		emit('playstate_start', {
			song: name, visit: visitsStarted,
			chartPlayer1: song == null ? null : Reflect.field(song, 'player1'),
			chartPlayer2: song == null ? null : Reflect.field(song, 'player2'),
			chartGf: song == null ? null : Reflect.field(song, 'gf'),
			chartStage: song == null ? null : Reflect.field(song, 'stage')
		});
	}

	/** Emit cumulative timings at a few blocking PlayState.create boundaries. */
	public static function markLoadPhase(phase:String):Void {
		if (!playStateStarted || playStateReady || finished || !enabled())
			return;
		var snapshot:Dynamic = RuntimeDecodeMetrics.snapshot();
		Reflect.setField(snapshot, 'phase', phase);
		Reflect.setField(snapshot, 'elapsedMs', (haxe.Timer.stamp() - playStateLoadStartedAt) * 1000);
		emit('load_phase', snapshot);
	}

	/** Record one bounded chart-row failure context for native smoke replays. */
	public static function markNoteGenerationFailure(section:Int, row:Int, authoredTime:String,
		authoredLane:String, authoredSustain:String, objectKind:String, objectIndex:Int,
		phase:String, error:String):Void {
		if (!enabled())
			return;
		var details:Dynamic = {
			section: section,
			row: row,
			authoredTime: authoredTime,
			authoredLane: authoredLane,
			authoredSustain: authoredSustain,
			objectKind: objectKind,
			objectIndex: objectIndex,
			phase: phase,
			error: error
		};
		if (phase != null && phase.indexOf('psych-skin') >= 0 && psychSkinDiagnosticPhase != '')
			Reflect.setField(details, 'psychSkinPhase', psychSkinDiagnosticPhase);
		emit('note_generation_failure', details);
	}

	/** Keep the current subphase in memory; only the existing failure marker writes it. */
	public static function setPsychSkinDiagnosticPhase(phase:String):Void {
		if (enabled())
			psychSkinDiagnosticPhase = phase == null ? '' : phase;
	}

	/** Mark the end of PlayState.create(), after scripts and stage setup loaded. */
	public static function markPlayStateReady(song:Dynamic):Void {
		if (!enabled() || finished)
			return;
		#if sys
		if (Sys.time() >= watchdogDeadline) {
			fail(config().playstateVisits == 2 ? 'reload-timeout' : 'timeout',
				'PlayState did not finish create() before the smoke watchdog');
			return;
		}
		#end
		#if sys
		playDeadline = Sys.time() + config().durationMs / 1000.0;
		#else
		playDeadline = elapsedMs + config().durationMs;
		#end
		if (config().playstateVisits == 2) {
			if (visitsStarted != visitsReady + 1) {
				fail('reload-sequence', 'Unexpected PlayState ready marker');
				return;
			}
			visitsReady++;
			#if sys
			visitDeadline = Sys.time() + config().durationMs / 1000.0;
			#else
			visitDeadline = elapsedMs + config().durationMs;
			#end
		} else visitsReady = 1;
		playStateReady = true;
		// A target-selected Freeplay smoke spends a variable amount of time
		// traversing the real menus. Give PlayState its full requested window
		// after it has finished creating, like a direct chart smoke.
		if (config().freeplay && config().freeplayAcceptSong != '' && acceptInitiated) {
			#if sys
			deadline = Sys.time() + config().durationMs / 1000.0;
			#end
		}
		if (config().frameStats)
			installFrameStats();
		if (config().requireSongEnd || config().requireEndHandoff)
			installSongEndCompletionWatch();
		var name = song == null ? '' : Std.string(Reflect.field(song, 'song'));
		var snapshot:Dynamic = RuntimeDecodeMetrics.snapshot();
		Reflect.setField(snapshot, 'song', name);
		Reflect.setField(snapshot, 'visit', visitsStarted);
		Reflect.setField(snapshot, 'elapsedMs', (haxe.Timer.stamp() - playStateLoadStartedAt) * 1000);
		emit('playstate_ready', snapshot);
		var visualState = PlayState.instance;
		if (visualState != null) {
			markReceptorLayout('ready');
			emit('character_visual', RuntimeSmokeVisuals.character('player', visualState.boyfriend));
			emit('character_visual', RuntimeSmokeVisuals.character('opponent', visualState.dad));
			emit('character_visual', RuntimeSmokeVisuals.character('girlfriend', visualState.gf));
		}
		RuntimeDecodeMetrics.reset(false);
		if (config().tracePlayerHits) {
			var gameState = PlayState.instance;
			if (gameState != null && gameState.player1GoodHitSignal != null)
				gameState.player1GoodHitSignal.connect(function(note:Note)
					observePlayerOneGoodHit(gameState, note));
		}
	}

	/** Count generated chart heads by input side before gameplay consumes them. */
	public static function markChartNoteSides(format:String, generated:Array<Note>):Void {
		if (!enabled() || finished || generated == null)
			return;
		var player = 0;
		var opponent = 0;
		for (note in generated) {
			if (note == null || note.isSustainNote || note.isLiftNote)
				continue;
			if (note.mustPress) player++;
			else opponent++;
		}
		emit('chart_note_sides', {format:format, player:player, opponent:opponent});
	}

	/** Evidence that a source variation replaced one scored line in place. */
	public static function markHxcNoteDataSwap(player:Bool, generated:Array<Note>):Void {
		if (!enabled() || finished) return;
		var heads = 0;
		if (generated != null)
			for (note in generated)
				if (note != null && !note.isSustainNote) heads++;
		emit('hxc_note_data_swap', {side: player ? 'player' : 'opponent', heads: heads,
			positionMs: Conductor.songPosition});
	}

	/** Primitive-only actor evidence; the caller must not pass live sprites. */
	public static function markCodenameActorSnapshot(summary:Dynamic):Void {
		if (!enabled() || finished || config().playstateVisits != 2) return;
		var payload:Dynamic = {visit:visitsStarted};
		if (summary != null) for (field in Reflect.fields(summary))
			Reflect.setField(payload, field, Reflect.field(summary, field));
		emit('codename_actor_snapshot', payload);
	}

	/** Called after actor cleanup, with counts captured before and after it. */
	public static function markCodenameActorTeardown(summary:Dynamic):Void {
		if (!enabled() || finished || config().playstateVisits != 2) return;
		if (summary == null || teardownsMarked != visitsDestroyed) {
			fail('actor-cleanup', 'Missing or duplicate actor cleanup evidence');
			return;
		}
		var payload:Dynamic = {visit:visitsStarted};
		for (field in Reflect.fields(summary))
			Reflect.setField(payload, field, Reflect.field(summary, field));
		emit('codename_actor_teardown', payload);
		var expected:Dynamic = Reflect.field(summary, 'owned');
		var borrowed:Dynamic = Reflect.field(summary, 'borrowed');
		var actual:Dynamic = Reflect.field(summary, 'destroyCalls');
		var remaining:Dynamic = Reflect.field(summary, 'remainingBindings');
		var errors:Dynamic = Reflect.field(summary, 'cleanupErrors');
		if (!Std.isOfType(expected, Int) || !Std.isOfType(borrowed, Int)
			|| !Std.isOfType(actual, Int)
			|| !Std.isOfType(remaining, Int) || !Std.isOfType(errors, Array)
			|| expected < 0 || borrowed < 0 || actual != expected || remaining != 0
			|| (cast errors:Array<Dynamic>).length > 0) {
			fail('actor-cleanup', 'Owned actors were not released exactly once');
			return;
		}
		teardownsMarked++;
		validatedTeardown = {owned:expected, borrowed:borrowed,
			destroyCalls:actual, remainingBindings:remaining};
	}

	/** Call only after PlayState.super.destroy() returns. */
	public static function markPlayStateDestroyed(summary:Dynamic):Void {
		if (!enabled() || finished || config().playstateVisits != 2) return;
		if (visitsStarted != visitsDestroyed + 1 || teardownsMarked != visitsStarted
			|| validatedTeardown == null || summary == null
			|| Reflect.field(summary, 'owned') != Reflect.field(validatedTeardown, 'owned')
			|| Reflect.field(summary, 'borrowed') != Reflect.field(validatedTeardown, 'borrowed')
			|| Reflect.field(summary, 'destroyCalls') != Reflect.field(validatedTeardown, 'destroyCalls')
			|| Reflect.field(summary, 'remainingBindings') != 0
			|| !Std.isOfType(Reflect.field(summary, 'cleanupErrors'), Array)
			|| (cast Reflect.field(summary, 'cleanupErrors'):Array<Dynamic>).length > 0) {
			fail('reload-sequence', 'Unexpected PlayState destroy marker');
			return;
		}
		visitsDestroyed++;
		validatedTeardown = null;
		var payload:Dynamic = {visit:visitsDestroyed};
		if (summary != null) for (field in Reflect.fields(summary))
			Reflect.setField(payload, field, Reflect.field(summary, field));
		emit('playstate_destroyed', payload);
	}

	/** One actual Flixel binding per custom note kind, after Note.new() loaded
	 * the atlas and registered its Scroll animation. */
	public static function markCustomNoteVisual(note:Note):Void {
		if (!enabled() || finished || note == null || !note.dontEdit || note.isSustainNote)
			return;
		var key = note.sourceKind == null || note.sourceKind == ''
			? (note.coolId == null ? Std.string(note.trueNoteData) : note.coolId)
			: note.sourceKind;
		if (visualNoteKinds.exists(key))
			return;
		visualNoteKinds.set(key, true);
		emit('custom_note_visual', RuntimeSmokeVisuals.note(note, Note.swagWidth));
	}

	/** Once per kind, sample the final position after gameplay's note movement
	 * and receptor snap, while the sprite is visible near its receptor. */
	public static function markLiveCustomNoteVisual(note:Note, receptor:FlxSprite):Void {
		if (!enabled() || finished || note == null || receptor == null
			|| !note.dontEdit || note.isSustainNote || !note.visible || !note.active
			|| Math.abs(note.y - receptor.y) > Note.swagWidth * 4)
			return;
		var key = note.sourceKind == null || note.sourceKind == ''
			? (note.coolId == null ? Std.string(note.trueNoteData) : note.coolId)
			: note.sourceKind;
		if (liveVisualNoteKinds.exists(key))
			return;
		liveVisualNoteKinds.set(key, true);
		var snapshot:Dynamic = RuntimeSmokeVisuals.note(note, Note.swagWidth);
		var receptorCenterX = receptor.x + receptor.width / 2;
		Reflect.setField(snapshot, 'receptorX', receptor.x);
		Reflect.setField(snapshot, 'receptorY', receptor.y);
		Reflect.setField(snapshot, 'receptorWidth', receptor.width);
		Reflect.setField(snapshot, 'receptorCenterX', receptorCenterX);
		var renderCenterX:Dynamic = Reflect.field(snapshot, 'renderCenterX');
		Reflect.setField(snapshot, 'centerErrorToReceptorX',
			renderCenterX == null ? null : (cast renderCenterX:Float) - receptorCenterX);
		emit('live_custom_note_visual', snapshot);
	}

	/** Emit camera measurements only for an explicit native runtime smoke. */
	public static function markCameraSnapshot(phase:String, snapshot:Dynamic):Void {
		if (!enabled() || finished)
			return;
		var payload:Dynamic = {phase: phase};
		if (snapshot != null)
			for (field in Reflect.fields(snapshot))
				Reflect.setField(payload, field, Reflect.field(snapshot, field));
		emit('camera_snapshot', payload);
	}

	/** True only when a test launch explicitly requested scoped Codename probes. */
	public static function codenameVisualsEnabled():Bool {
		return enabled() && config().codenameVisuals && !finished;
	}

	/** Sample native character frames and source video clocks during an explicit
	 * offscreen probe. Keep the marker small enough for long song runs. */
	public static function markCodenameMotionSnapshot(beat:Int, positionMs:Float,
		actors:Array<Dynamic>, videos:Array<Dynamic>):Void {
		if (!codenameVisualsEnabled() || codenameMotionMarkers >= 160) return;
		var boundedActors:Array<Dynamic> = [];
		if (actors != null) for (actor in actors) {
			if (boundedActors.length >= 16) break;
			if (actor == null) continue;
			boundedActors.push({
				lineIndex: Reflect.field(actor, 'lineIndex'),
				occurrenceIndex: Reflect.field(actor, 'occurrenceIndex'),
				inputIndex: Reflect.field(actor, 'inputIndex'),
				visible: Reflect.field(actor, 'visible'),
				exists: Reflect.field(actor, 'exists'),
				active: Reflect.field(actor, 'active'),
				animation: boundedSmokeText(Std.string(Reflect.field(actor, 'animation')), 64),
				frame: Reflect.field(actor, 'frame'),
				x: Reflect.field(actor, 'x'), y: Reflect.field(actor, 'y')
			});
		}
		var boundedVideos:Array<Dynamic> = [];
		if (videos != null) for (video in videos) {
			if (boundedVideos.length >= 8) break;
			if (video == null) continue;
			boundedVideos.push({
				script: safeSmokeRelative(Std.string(Reflect.field(video, 'script')), 192),
				visible: Reflect.field(video, 'visible'),
				exists: Reflect.field(video, 'exists'),
				playing: Reflect.field(video, 'playing'),
				timeMs: Reflect.field(video, 'timeMs'),
				lengthMs: Reflect.field(video, 'lengthMs')
			});
		}
		codenameMotionMarkers++;
		emit('codename_motion_snapshot', {beat:beat,
			positionMs:Math.isFinite(positionMs) ? positionMs : null,
			actors:boundedActors, videos:boundedVideos});
	}

	/** Check which authored actors receive native note events without logging
	 * every hit or retaining any game object in the smoke stream. */
	public static function markCodenameHitActorSnapshot(positionMs:Float, lineIndex:Int,
		cancelled:Bool, animCancelled:Bool, actors:Array<Dynamic>):Void {
		if (!codenameVisualsEnabled()) return;
		codenameHitActorCalls++;
		if (codenameHitActorCalls % 16 != 0 || codenameHitActorCalls > 768) return;
		var bounded:Array<Dynamic> = [];
		if (actors != null) for (actor in actors) {
			if (bounded.length >= 16) break;
			if (actor == null) continue;
			bounded.push({occurrenceIndex:Reflect.field(actor, 'occurrenceIndex'),
				visible:Reflect.field(actor, 'visible')});
		}
		emit('codename_hit_actor_snapshot', {positionMs:Math.isFinite(positionMs) ? positionMs : null,
			lineIndex:lineIndex, cancelled:cancelled, animCancelled:animCancelled,
			actors:bounded});
	}

	/** Keep test evidence scoped and bounded; never serialize arbitrary runtime
	 * objects or absolute donor paths into the marker stream. */
	public static function markCodenameVisualSnapshot(owner:String, script:String,
		callback:String, eventName:String, eventTime:Null<Float>, objects:Array<Dynamic>,
		camera:Dynamic):Void {
		if (!codenameVisualsEnabled()) return;
		var eventCallback = callback == 'onEvent';
		if (eventCallback) {
			if (codenameEventVisualMarkers >= 768) return;
		} else {
			if (callback != 'postCreate' && callback != 'beatHit') return;
			var identity = safeSmokeRelative(owner, 192) + '|' + safeSmokeRelative(script, 192);
			var signature = haxe.Json.stringify(objects == null ? [] : objects)
				+ ':' + Std.string(camera == null ? null : Reflect.field(camera, 'gameVisible'))
				+ ':' + Std.string(camera == null ? null : Reflect.field(camera, 'mainVisible'))
				+ ':' + Std.string(camera == null ? null : Reflect.field(camera, 'hudVisible'));
			if (codenameVisualSignatures.get(identity) == signature
				|| codenameCallbackVisualMarkers >= 128) return;
			codenameVisualSignatures.set(identity, signature);
		}
		var boundedObjects:Array<Dynamic> = [];
		var allowed = ['index', 'kind', 'className', 'exists', 'active', 'visible', 'x', 'y',
			'alpha', 'width', 'height', 'graphicWidth', 'graphicHeight', 'cameraCount',
			'shaderClass', 'videoLoaded', 'videoPlaying', 'videoTimeMs', 'videoLengthMs'];
		if (objects != null) for (object in objects) {
			if (boundedObjects.length >= 16) break;
			if (object == null) continue;
			var copy:Dynamic = {};
			for (field in allowed) if (Reflect.hasField(object, field)) {
				var value:Dynamic = Reflect.field(object, field);
				if (value == null || Std.isOfType(value, String) || Std.isOfType(value, Bool)
					|| Std.isOfType(value, Int) || Std.isOfType(value, Float))
					Reflect.setField(copy, field, Std.isOfType(value, String)
						? boundedSmokeText(Std.string(value), 120) : value);
			}
			boundedObjects.push(copy);
		}
		var boundedCamera:Dynamic = {};
		if (camera != null) for (field in ['gameZoom', 'gameVisible', 'gameAlpha', 'hudZoom',
			'hudVisible', 'hudAlpha', 'otherZoom', 'mainIsGame', 'mainVisible', 'mainAlpha']) {
			var value:Dynamic = Reflect.field(camera, field);
			if (value != null && (Std.isOfType(value, Int) || Std.isOfType(value, Float)
				|| Std.isOfType(value, Bool)))
				Reflect.setField(boundedCamera, field, value);
		}
		var cameraLayers:Dynamic = camera == null ? null : Reflect.field(camera, 'cameraLayers');
		if (Std.isOfType(cameraLayers, Array)) {
			var boundedLayers:Array<Dynamic> = [];
			for (layer in (cast cameraLayers:Array<Dynamic>)) {
				if (boundedLayers.length >= 8) break;
				if (layer == null) continue;
				boundedLayers.push({
					index: Reflect.field(layer, 'index'),
					game: Reflect.field(layer, 'game'),
					hud: Reflect.field(layer, 'hud'),
					visible: Reflect.field(layer, 'visible'),
					alpha: Reflect.field(layer, 'alpha'),
					bgColor: boundedSmokeText(Std.string(Reflect.field(layer, 'bgColor')), 24)
				});
			}
			Reflect.setField(boundedCamera, 'layers', boundedLayers);
		}
		if (eventCallback) codenameEventVisualMarkers++ else codenameCallbackVisualMarkers++;
		emit('codename_visual_snapshot', {
			owner: safeSmokeRelative(owner, 192), script: safeSmokeRelative(script, 192),
			callback: boundedSmokeText(callback, 32),
			eventName: boundedSmokeText(eventName, 120),
			eventTimeMs: eventTime != null && Math.isFinite(eventTime) ? eventTime : null,
			objects: boundedObjects, camera: boundedCamera
		});
	}

	/** Observe the actual pause state and audio clock in a private smoke process. */
	public static function markPauseTransition(event:String):Void {
		if (!enabled() || finished || !playStateReady) return;
		if (event != 'pause_open' && event != 'pause_resume') return;
		emit(event, {
			positionMs: Math.isFinite(Conductor.songPosition) ? Conductor.songPosition : null,
			musicTimeMs: FlxG.sound.music != null && Math.isFinite(FlxG.sound.music.time)
				? FlxG.sound.music.time : null,
			musicPlaying: FlxG.sound.music != null && FlxG.sound.music.playing
		});
	}

	/** Confirm that a Story intro actually handed control to song audio. */
	public static function markSongStart(song:String):Void {
		if (!enabled()) return;
		songStartObserved = true;
		emit('song_start', {song:song,
			musicPlaying:FlxG.sound.music != null && FlxG.sound.music.playing,
			musicTimeMs:FlxG.sound.music == null ? null : FlxG.sound.music.time});
		markReceptorLayout('song_start');
	}

	/** Keep countdown transition positions separate from settled song positions. */
	static function markReceptorLayout(phase:String):Void {
		var state = PlayState.instance;
		if (!enabled() || state == null) return;
		var lines = @:privateAccess [state.enemyStrums, state.playerStrums];
		for (line in lines)
			if (line != null)
				for (receptor in line.members)
					if (receptor != null) {
						var snapshot = RuntimeSmokeVisuals.receptor(receptor, Note.swagWidth);
						Reflect.setField(snapshot, 'phase', phase);
						emit('receptor_layout', snapshot);
					}
	}

	/** Emit the complete state snapshot for one smoke-driven forward seek. */
	public static function markSeekComplete(snapshot:Dynamic):Void {
		if (!enabled() || finished || !playStateReady || seekCompleted) return;
		seekCompleted = true;
		emit('seek_complete', snapshot);
	}


	/** Natural audio completion, emitted once before song-end teardown. */
	public static function markNaturalSongEnd(song:String, songLength:Float,
		position:Float, dispatchedEvents:Int, totalEvents:Int, dueEvents:Int):Void {
		if (!enabled() || finished || naturalSongEndObserved) return;
		naturalSongEndObserved = true;
		#if sys
		naturalSongEndAt = Sys.time();
		#else
		naturalSongEndAt = elapsedMs / 1000;
		#end
		emit('song_end', {
			song: safeToken(song), songLengthMs: Math.isFinite(songLength) ? songLength : null,
			positionMs: Math.isFinite(position) ? position : null,
			dispatchedEvents: Std.int(Math.max(0, Math.min(100000, dispatchedEvents))),
			dueEvents: Std.int(Math.max(0, Math.min(100000, dueEvents))),
			totalEvents: Std.int(Math.max(0, Math.min(100000, totalEvents)))
		});
	}

	/** Native evidence that an explicit chart-video skip crossed the authored interval. */
	public static function markEventVideoSkip(eventTime:Float, from:Float, target:Float,
		duration:Float, crossedEvents:Int):Void {
		if (!enabled() || finished) return;
		emit('event_video_skip', {
			eventTimeMs: Math.isFinite(eventTime) ? eventTime : null,
			fromMs: Math.isFinite(from) ? from : null,
			targetMs: Math.isFinite(target) ? target : null,
			durationMs: Math.isFinite(duration) ? duration : null,
			crossedEvents: Std.int(Math.max(0, Math.min(100000, crossedEvents)))
		});
	}

	/** Small pure gate so end-of-song smoke tests can exercise the policy. */
	public static function missingRequiredSongEnd(required:Bool, observed:Bool):Bool {
		return required && !observed;
	}

	static function safeSmokeRelative(value:String, limit:Int):String {
		if (value == null) return '';
		var clean = StringTools.trim(StringTools.replace(value, '\\', '/'));
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0) return '';
		for (part in clean.split('/')) if (part == '' || part == '.' || part == '..') return '';
		return clean.length > limit ? clean.substr(0, limit) : clean;
	}

	static function boundedSmokeText(value:String, limit:Int):String {
		if (value == null) return '';
		var clean = StringTools.trim(value);
		return clean.length > limit ? clean.substr(0, limit) : clean;
	}

	/** Emit one imported receptor snapshot for each line, lane, and animation. */
	public static function markReceptorVisual(snapshot:Dynamic):Void {
		if (!enabled() || finished || snapshot == null)
			return;
		var key = Std.string(Reflect.field(snapshot, 'type')) + '|'
			+ Std.string(Reflect.field(snapshot, 'lineX')) + '|'
			+ Std.string(Reflect.field(snapshot, 'lineY')) + '|'
			+ Std.string(Reflect.field(snapshot, 'lane')) + '|'
			+ Std.string(Reflect.field(snapshot, 'animation')) + '|'
			+ Std.string(Reflect.field(snapshot, 'frameWidth')) + '|'
			+ Std.string(Reflect.field(snapshot, 'frameHeight'));
		if (receptorVisualStates.exists(key))
			return;
		receptorVisualStates.set(key, true);
		emit('receptor_visual', snapshot);
	}

	/** Queue only primitive note data; goodNoteHit destroys the Note before the next tick. */
	static function observePlayerOneGoodHit(gameState:PlayState, note:Note):Void {
		if (!enabled() || config() == null || !config().tracePlayerHits
			|| gameState == null || note == null)
			return;
		pendingPlayerHitProbes.push({
			signalOwner: 'player1',
			noteTime: note.strumTime,
			judgementSongPosition: Conductor.songPosition,
			noteData: note.noteData,
			mustPress: note.mustPress,
			shouldBeSung: note.shouldBeSung,
			isSustainNote: note.isSustainNote,
			wasGoodHit: note.wasGoodHit,
			soloMode: note.soloMode
		});
	}

	/** Emit the exact owner splash that a successful Codename hit added for drawing. */
	public static function markCodenameNoteSplashRendered(note:Note, ownerRoot:String,
		selectedName:String, atlas:String, animationPrefix:String, lane:Int,
		splash:CodenameNoteSplash, inGroup:Bool):Void {
		if (!enabled() || finished || config() == null || !config().tracePlayerHits
			|| note == null || splash == null)
			return;
		var animation = splash.animation == null ? null : splash.animation.curAnim;
		emit('codename_note_splash_rendered', {
			ownerRoot: ownerRoot,
			selectedSplash: selectedName,
			noteSplash: note.splash,
			atlas: atlas,
			animationPrefix: animationPrefix,
			lane: lane,
			noteStrumTime: note.strumTime,
			noteMustPress: note.mustPress,
			noteIsSustain: note.isSustainNote,
			noteWasGoodHit: note.wasGoodHit,
			renderable: splash.renderable,
			inSplashGroup: inGroup,
			exists: splash.exists,
			alive: splash.alive,
			visible: splash.visible,
			x: splash.x,
			y: splash.y,
			width: splash.width,
			height: splash.height,
			frameWidth: splash.frameWidth,
			frameHeight: splash.frameHeight,
			alpha: splash.alpha,
			scaleX: splash.scale.x,
			scaleY: splash.scale.y,
			cameraCount: splash.cameras == null ? 0 : splash.cameras.length,
			animationName: animation == null ? '' : animation.name,
			animationFrame: animation == null ? -1 : animation.curFrame
		});
	}

	/** Sample live role animation one update after goodNoteHit's callbacks finish. */
	static function flushPlayerHitProbes():Void {
		if (pendingPlayerHitProbes.length == 0)
			return;
		var pending = pendingPlayerHitProbes;
		pendingPlayerHitProbes = [];
		var gameState = PlayState.instance;
		if (gameState == null)
			return;
		for (probe in pending) {
			var actor = probe.soloMode == true ? gameState.getOpponentSinger() : gameState.boyfriend;
			var current:Dynamic = actor == null || actor.animation == null
				? null : actor.animation.curAnim;
			emit('player1_good_hit_postroute', {
				signalOwner: probe.signalOwner,
				noteTime: probe.noteTime,
				judgementSongPosition: probe.judgementSongPosition,
				sampleSongPosition: Conductor.songPosition,
				noteData: probe.noteData,
				mustPress: probe.mustPress,
				shouldBeSung: probe.shouldBeSung,
				isSustainNote: probe.isSustainNote,
				wasGoodHit: probe.wasGoodHit,
				actorMatchesBoyfriend: actor == gameState.boyfriend,
				actor: actor == null ? '' : actor.curCharacter,
				like: actor == null ? '' : actor.like,
				animation: current == null ? '' : Reflect.field(current, 'name'),
				frame: current == null ? -1 : Reflect.field(current, 'curFrame'),
				geometry: RuntimeSmokeVisuals.characterGeometry(actor)
			});
		}
	}

	/** Advance the bounded smoke window from PlayState.update(). */
	static var windowResizeApplied:Bool = false;

	/** One-shot native window resize so the real stage-resize path runs. */
	static function applyWindowResize():Void {
		if (windowResizeApplied)
			return;
		var spec = config().windowResize;
		if (spec == null || spec.indexOf('x') < 0)
			return;
		windowResizeApplied = true;
		#if desktop
		var parts = spec.split('x');
		var w = Std.parseInt(StringTools.trim(parts[0]));
		var h = Std.parseInt(StringTools.trim(parts[1]));
		if (w != null && h != null && w > 0 && h > 0) {
			FlxG.resizeWindow(w, h);
			emit('window-resize', {width: w, height: h});
		}
		#end
	}

	/** Return true when PlayState.update must stop after a queued reload. */
	public static function tick(frameElapsed:Float):Bool {
		if (!enabled() || finished || !started)
			return false;
		#if sys
		if (Sys.time() >= watchdogDeadline && (config().playstateVisits == 2 || !playStateReady)) {
			fail(config().playstateVisits == 2 ? 'reload-timeout' : 'timeout',
				config().playstateVisits == 2 ? 'Two PlayState visits did not finish before the watchdog'
					: 'PlayState was not ready before the smoke watchdog');
			return false;
		}
		#end
		if (transitionPending) return true;
		if (config().chartEditor) {
			if (frameElapsed > 0 && Math.isFinite(frameElapsed))
				elapsedMs += frameElapsed * 1000;
			#if sys
			if (Sys.time() >= deadline)
				fail('chart-editor-timeout', 'ChartingState round-trip did not finish before the deadline');
			#else
			if (elapsedMs >= config().durationMs)
				fail('chart-editor-timeout', 'ChartingState round-trip did not finish before the deadline');
			#end
			return false;
		}
		flushPlayerHitProbes();
		applyWindowResize();
		applySongRate();
		if (frameElapsed > 0 && Math.isFinite(frameElapsed))
			elapsedMs += frameElapsed * 1000;
		maybeRunSeek();
		if (config().playstateVisits == 2) {
			if (!playStateReady) return false;
			#if sys
			var visitExpired = Sys.time() >= visitDeadline;
			#else
			var visitExpired = elapsedMs >= visitDeadline;
			#end
			if (!visitExpired) return false;
			if (visitsStarted == 1) {
				transitionPending = true;
				playStateReady = false;
				emit('playstate_reload_begin', {visit:1, nextVisit:2});
				FlxG.switchState(new RuntimeSmokeState());
				return true;
			}
			if (visitsStarted == 2 && visitsDestroyed == 1) succeed();
			else fail('reload-sequence', 'Second visit ended without first visit teardown');
			return false;
		}
		// A completion-only smoke observes the real audio end and gives immediate
		// callbacks five seconds to fail, even when an authored results screen
		// keeps PlayState open. The stricter ending gate still requires the
		// actual state handoff and teardown before it can succeed.
		if (config().requireSongEnd && naturalSongEndObserved
			&& (!config().requireEndHandoff || !Std.isOfType(FlxG.state, PlayState))) {
			if (config().requireEndHandoff) markEndHandoff();
			#if sys
			var endSettled = Sys.time() - naturalSongEndAt >= 5;
			#else
			var endSettled = elapsedMs / 1000 - naturalSongEndAt >= 5;
			#end
			if (endSettled) {
				succeed();
				return true;
			}
		}
		#if sys
		var expired = playStateReady ? Sys.time() >= playDeadline : Sys.time() >= watchdogDeadline;
		#else
		var startupBudgetMs = config().durationMs * config().playstateVisits + 120000;
		var expired = playStateReady ? elapsedMs >= playDeadline : elapsedMs >= startupBudgetMs;
		#end
		if (!expired)
			return false;
		if (config().requireEndHandoff && Std.isOfType(FlxG.state, PlayState))
			fail('end-handoff-timeout', 'Song ended but its ending did not leave PlayState');
		else if (playStateReady)
			succeed();
		else
			fail('timeout', playStateStarted ? 'PlayState did not finish create()' : 'PlayState was never entered');
		return false;
	}

	static var songEndCompletionWatchInstalled:Bool = false;
	static var endHandoffObserved:Bool = false;

	static function markEndHandoff():Void {
		if (endHandoffObserved || !naturalSongEndObserved || Std.isOfType(FlxG.state, PlayState))
			return;
		endHandoffObserved = true;
		var stateClass = FlxG.state == null ? null : Type.getClass(FlxG.state);
		emit('end_handoff', {state: stateClass == null ? '' : Type.getClassName(stateClass)});
	}

	/** Completion-only runs also need a state-independent settle timer after
	 * song-end switches away from PlayState, because PlayState.update no longer
	 * calls tick() there. Only strict handoff runs emit the handoff marker. */
	static function installSongEndCompletionWatch():Void {
		if (songEndCompletionWatchInstalled) return;
		songEndCompletionWatchInstalled = true;
		FlxG.signals.postUpdate.add(function():Void {
			if (finished || !naturalSongEndObserved)
				return;
			#if sys
			var settled = Sys.time() - naturalSongEndAt >= 5;
			#else
			var settled = elapsedMs / 1000 - naturalSongEndAt >= 5;
			#end
			observeSongEndCompletion(Std.isOfType(FlxG.state, PlayState), settled);
		});
	}

	/** Complete after the settle window once a song-end leaves PlayState. */
	static function observeSongEndCompletion(isPlayState:Bool, settled:Bool):Void {
		if (finished || !naturalSongEndObserved || isPlayState)
			return;
		if (config().requireEndHandoff)
			markEndHandoff();
		if (settled)
			succeed();
	}

	/** Report a loader/runtime failure and terminate with a nonzero status. */
	public static function fail(kind:String, detail:String):Void {
		if (!enabled() || finished)
			return;
		finished = true;
		var snapshot:Dynamic = RuntimeDecodeMetrics.snapshot();
		Reflect.setField(snapshot, 'kind', kind);
		Reflect.setField(snapshot, 'detail', detail == null ? '' : detail);
		emit('failure', snapshot);
		RuntimeDecodeMetrics.reset(false);
		#if sys
		Sys.exit(1);
		#end
	}

	/** Report a bounded successful smoke window and terminate cleanly. */
	public static function succeed():Void {
		if (!enabled() || finished)
			return;
		if (config().seekToMs >= 0 && !seekCompleted) {
			fail('seek-timeout', 'Configured forward seek did not complete before the smoke window ended');
			return;
		}
		if (missingRequiredSongEnd(config().requireSongEnd, naturalSongEndObserved)) {
			fail('song-end-timeout', 'Smoke duration ended before natural song completion');
			return;
		}
		finished = true;
		emit('success', {durationMs: elapsedMs});
		RuntimeDecodeMetrics.reset(false);
		#if sys
		Sys.exit(0);
		#end
	}

	// ---- freeplay smoke mode: frame pacing + bitmap cache observation ----
	// The harness outlives FreeplayState by riding the global FlxG signals, so
	// scrolling, leaving and measuring all keep working across state switches.

	static var frameInstalled:Bool = false;
	static var frameStart:Float = 0;
	static var drawStart:Float = 0;
	static var lastFrameStart:Float = 0;
	static var startedAtMs:Float = 0;
	static var lastSummaryAt:Float = 0;
	static var lastScrollAt:Float = 0;
	static var costs:Array<Float> = [];
	static var updateCosts:Array<Float> = [];
	static var drawCosts:Array<Float> = [];
	static var deltas:Array<Float> = [];
	static var windowHitches:Int = 0;
	static var totalFrames:Int = 0;
	static var freeplaySeen:Bool = false;
	static var freeplaySeenAt:Float = 0;
	static var leftFreeplay:Bool = false;
	static var leaveInitiated:Bool = false;
	static var acceptInitiated:Bool = false;
	static var modifierAcceptInitiated:Bool = false;
	static var modifierAcceptSends:Int = 0;
	static var modifierLastAcceptAt:Float = 0;
	static var popupSeen:Bool = false;
	static var popupSeenAt:Float = 0;
	static var popupConfirmSends:Int = 0;
	static var popupClosed:Bool = false;

	/** Emit one progress marker so headless crashes can be located. */
	public static function markStep(step:String):Void {
		if (!enabled())
			return;
		emit('step', {at: step, songPosition: playStateReady ? Conductor.songPosition : null});
	}

	// smoke-only profiler: accumulate per-section update seconds until the next
	// per-second frame_stats line reports them alongside the pacing percentiles
	static var sectionMs:Map<String, Float> = new Map<String, Float>();

	public static function profileEnabled():Bool {
		var options = config();
		return smokeArgumentsSeen && options != null && options.frameStats;
	}

	/** Accumulate one named section cost (no-op outside smoke runs). */
	public static function profileSection(section:String, seconds:Float):Void {
		if (!profileEnabled())
			return;
		sectionMs[section] = (sectionMs.exists(section) ? sectionMs.get(section) : 0.0) + seconds * 1000;
	}

	static function nowMs():Float
		return haxe.Timer.stamp() * 1000;

	/** Build the freeplay song list for --smoke-freeplay from the live registry. */
	public static function selectFreeplaySongs():Array<FreeplayState.JsonMetadata> {
		var result:Array<FreeplayState.JsonMetadata> = [];
		#if sys
		var wanted = config() == null ? '' : config().freeplayCategory;
		var allCategories = wanted == '' || wanted == 'All';
		var allEntries:Array<FreeplaySongOrder.FreeplaySongEntry> = [];
		var registry:Array<Dynamic> = cast FreeplayRegistry.getJson();
		for (category in registry) {
			if (category == null || Reflect.field(category, 'songs') == null)
				continue;
			var categoryName = Std.string(Reflect.field(category, 'name'));
			if (allCategories && categoryName == 'All')
				continue;
			if (!allCategories && categoryName != wanted)
				continue;
			var songs:Array<Dynamic> = cast Reflect.field(category, 'songs');
			for (song in songs) {
				if (song == null)
					continue;
				var data:FreeplayState.JsonMetadata = Std.isOfType(song, String)
					? {name:cast song, week:-1, character:'face'}
					: {name:Reflect.field(song, 'name'),
						week:Reflect.field(song, 'week') == null ? -1 : Reflect.field(song, 'week'),
						character:Reflect.field(song, 'character') == null ? 'bf' : Reflect.field(song, 'character'),
						display:Reflect.field(song, 'display'),
						sourceLabel:Reflect.field(song, 'sourceLabel')};
				if (data.name == null)
					continue;
				if (allCategories)
					allEntries.push({song:data, base:categoryName == 'Base Game', order:allEntries.length});
				else
					result.push(data);
			}
		}
		if (allCategories) {
			result.push({name:'Random-Song', week:0, character:'bf'});
			for (song in FreeplaySongOrder.sort(allEntries))
				result.push(cast song);
		}
		#end
		return result;
	}

	/** Subscribe the frame observer.  Safe to call from any state's create(). */
	public static function installFrameStats():Void {
		if (frameInstalled || !enabled())
			return;
		frameInstalled = true;
		startedAtMs = nowMs();
		lastSummaryAt = startedAtMs;
		FlxG.signals.preUpdate.add(onFramePreUpdate);
		FlxG.signals.postUpdate.add(onFramePostUpdate);
		FlxG.signals.preDraw.add(onFramePreDraw);
		FlxG.signals.postDraw.add(onFramePostDraw);
	}

	static function onFramePreUpdate():Void {
		frameStart = nowMs();
		if (lastFrameStart > 0) {
			var delta = frameStart - lastFrameStart;
			deltas.push(delta);
			// a 60fps game missing even a 30fps budget is a user-visible hitch
			if (delta > 33.4)
				windowHitches++;
		}
		lastFrameStart = frameStart;
	}

	static function onFramePostUpdate():Void {
		updateCosts.push(nowMs() - frameStart);
	}

	static function onFramePreDraw():Void {
		drawStart = nowMs();
	}

	static function onFramePostDraw():Void {
		var now = nowMs();
		costs.push(now - frameStart);
		drawCosts.push(now - drawStart);
		totalFrames++;
		if (config() != null && config().freeplay)
			freeplayFrame(now);
		if (now - lastSummaryAt >= 1000) {
			lastSummaryAt = now;
			emitFrameSummary();
		}
	}

	/** Drive scrolling/leaving and completion for --smoke-freeplay. */
	static function freeplayFrame(now:Float):Void {
		var cfg = config();
		var inFreeplay = Std.isOfType(FlxG.state, FreeplayState);
		if (inFreeplay && !freeplaySeen) {
			freeplaySeen = true;
			freeplaySeenAt = now;
			lastScrollAt = now;
			emit('freeplay_start', {songs: Reflect.field(FlxG.state, 'songs') == null ? -1
				: (cast Reflect.field(FlxG.state, 'songs'):Array<Dynamic>).length});
		}
		if (!freeplaySeen) {
			if (now - startedAtMs > 20000)
				fail('timeout', 'FreeplayState was never entered');
			return;
		}
		if (!inFreeplay && !leftFreeplay) {
			leftFreeplay = true;
			emit('freeplay_left', {});
			if (cfg.freeplayAcceptSong != '' && !acceptInitiated) {
				fail('freeplay-early-exit', 'Freeplay left before accepting target ' + cfg.freeplayAcceptSong);
				return;
			}
		}
		// The normal Freeplay accept opens ModifierState when that menu is
		// enabled. Its default cursor is the Play action; accept only that action
		// so the smoke does not toggle a modifier or alter test settings.
		if (cfg.freeplayAcceptSong != '' && acceptInitiated
			&& Std.isOfType(FlxG.state, ModifierState)
			&& modifierAcceptSends < 3
			&& (!modifierAcceptInitiated || now - modifierLastAcceptAt >= 1000)) {
			var modifierSelection = modifierSelectionObservation();
			emit('freeplay_modifier_start', modifierSelection);
			if (modifierSelection.action != 'play') {
				fail('freeplay-modifier-selection', 'ModifierState did not open with Play selected');
				return;
			}
			modifierAcceptInitiated = true;
			modifierAcceptSends++;
			modifierLastAcceptAt = now;
			Reflect.setField(modifierSelection, 'send', modifierAcceptSends);
			emit('freeplay_modifier_accept_begin', modifierSelection);
			simulateAccept();
		}
		// Observe accept-gated popup substates (imported confirm menus): the
		// first accept opens them, a second one exercises their confirm/close
		// path so the whole donor lifecycle runs inside the smoke window.
		var popup = FlxG.state == null ? null : FlxG.state.subState;
		if (popup != null && !popupSeen) {
			popupSeen = true;
			popupSeenAt = now;
			emit('freeplay_popup_open', {popup: Type.getClassName(Type.getClass(popup))});
		}
		if (popupSeen && popup != null && popupConfirmSends < 3 && now - popupSeenAt >= 1500 + popupConfirmSends * 2000) {
			// Up to three accepts: the first confirms, later ones cover slow
			// donor unlock timers so the confirm/close path still runs.
			popupConfirmSends++;
			simulateAccept();
			emit('freeplay_popup_confirm_begin', {send: popupConfirmSends, updateDispatches: popupUpdateDispatches(popup)});
		}
		if (popupSeen && popup == null && !popupClosed) {
			popupClosed = true;
			emit('freeplay_popup_close', {});
		}
		if (inFreeplay) {
			// A confirm popup freezes the state underneath; keep driving the
			// selection only while no popup owns the screen, so the accept lands
			// on the capsule the popup will confirm.
			var targetSong = cfg.freeplayAcceptSong;
			var observation = acceptObservation();
			var selectedName:String = observation.song;
			var matched = targetSong != '' && selectedName == targetSong;
			var wantScroll = popup == null && cfg.freeplayScrollMs > 0
				&& (targetSong == '' || (!matched && !acceptInitiated));
			if (wantScroll && now - lastScrollAt >= cfg.freeplayScrollMs) {
				lastScrollAt = now;
				scrollSelection();
			}
			if (targetSong != '' && !matched && !acceptInitiated
				&& now - freeplaySeenAt >= 20000) {
				fail('freeplay-target-not-found', 'Target was never selected: ' + targetSong);
				return;
			}
			var acceptDue = targetSong != ''
				? matched
				: (cfg.freeplayAcceptMs > 0 && now - freeplaySeenAt >= cfg.freeplayAcceptMs);
			if (!acceptInitiated && acceptDue && popup == null) {
				acceptInitiated = true;
				emit('freeplay_accept_begin', observation);
				simulateAccept();
			}
			if (cfg.freeplayLeaveMs > 0 && !leaveInitiated && now - freeplaySeenAt >= cfg.freeplayLeaveMs) {
				leaveInitiated = true;
				emit('freeplay_leave_begin', {});
				LoadingState.loadAndSwitchState(new MainMenuState());
			}
		}
		if (Sys.time() >= deadline) {
			emitFrameSummary();
			if (cfg.freeplayAcceptSong != '' && acceptInitiated) {
				if (playStateReady)
					return; // PlayState.tick owns the gameplay window and its timeout.
				fail('freeplay-launch-timeout', playStateStarted
					? 'PlayState did not finish create()'
					: 'Accepted Freeplay song did not reach PlayState');
				return;
			}
			if (cfg.freeplayAcceptSong != '' && !acceptInitiated) {
				fail('freeplay-accept-missing', 'Target accept was never sent: ' + cfg.freeplayAcceptSong);
				return;
			}
			succeed();
		}
	}

	/** Observe ModifierState's current action without changing modifier values. */
	static function modifierSelectionObservation():Dynamic {
		var selected:Dynamic = Reflect.field(FlxG.state, 'curSelected');
		var index = selected == null ? -1 : Std.int(selected);
		var action = index >= 0 && index < ModifierState.modifiers.length
			? ModifierState.modifiers[index].internName : '';
		return {selection: index, action: action};
	}

	/** Count the imported popup's script update dispatches so a headless run
	 * can prove the donor loop is actually running (the first probe wraps the
	 * script's update with a counting delegate). */
	static function popupUpdateDispatches(popup:FlxSubState):Dynamic {
		try {
			var runtime = Reflect.field(popup, 'runtime');
			var interp = runtime == null ? null : Reflect.field(runtime, 'interp');
			var variables = interp == null ? null : Reflect.field(interp, 'variables');
			if (variables == null)
				return 'no-interp';
			var getFn = Reflect.field(variables, 'get');
			var setFn = Reflect.field(variables, 'set');
			var updateFn = Reflect.callMethod(variables, getFn, ['update']);
			if (updateFn == null)
				return 'no-update';
			var count = Reflect.callMethod(variables, getFn, ['hxcSmokeUpdateCount']);
			if (count == null) {
				// wrap once: count per-frame dispatches of the donor update
				Reflect.callMethod(variables, setFn, ['hxcSmokeUpdateCount', 0]);
				var wrapper = Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
					var current:Dynamic = Reflect.callMethod(variables, getFn, ['hxcSmokeUpdateCount']);
					Reflect.callMethod(variables, setFn, ['hxcSmokeUpdateCount', (current == null ? 0 : current) + 1]);
					return Reflect.callMethod(null, updateFn, args);
				});
				Reflect.callMethod(variables, setFn, ['update', wrapper]);
				return 0;
			}
			return count;
		} catch (error:Dynamic)
			return 'probe-error: ' + error;
	}

	/** Inspect what the accept will land on: selection index/name plus whether
	 * a selected imported capsule has armed a confirm, so a headless run explains itself. */
	static function acceptObservation():Dynamic {
		var observation:Dynamic = {};
		#if sys
		try {
			var stateClass = FlxG.state == null ? null : Type.getClass(FlxG.state);
			// curSelected is a static on FreeplayState; instance fields stay on
			// the state object itself.
			var index:Dynamic = stateClass == null ? null : Reflect.field(stateClass, 'curSelected');
			var difficulty:Dynamic = stateClass == null ? null : Reflect.field(stateClass, 'curDifficulty');
			var songs:Array<Dynamic> = cast Reflect.field(FlxG.state, 'songs');
			observation.selection = index;
			observation.difficulty = difficulty;
			if (difficulty != null)
				observation.difficultyName = DifficultyManager.getDiffName(Std.int(difficulty));
			observation.songCount = songs == null ? -1 : songs.length;
			var token:Dynamic = Reflect.field(FlxG.state, 'hxcConfirmToken');
			observation.confirmArmed = token != null && token != 0;
			if (index != null && songs != null && index >= 0 && index < songs.length) {
				var selectedIndex = Std.int(index);
				var song = songs[selectedIndex];
				observation.song = song == null ? '' : Std.string(Reflect.field(song, 'songName'));
				observation.title = song == null ? '' : Reflect.field(song, 'displayTitle');
				observation.sourceLabel = song == null ? '' : Reflect.field(song, 'sourceLabel');
				observation.previousSong = selectedIndex > 0
					? Reflect.field(songs[selectedIndex - 1], 'songName') : '';
				observation.nextSong = selectedIndex + 1 < songs.length
					? Reflect.field(songs[selectedIndex + 1], 'songName') : '';
			}
		} catch (_:Dynamic) {}
		#end
		return observation;
	}

	/** Dispatch one real ENTER key-down/up through the stage so whatever state
	 * owns the menu sees a genuine accept (simulated selection moves like
	 * scrollSelection() cannot cross accept-gated substate boundaries). */
	static function simulateAccept():Void {
		simulateKey('enter');
	}

	/** Dispatch one real key-down/up through the stage so whatever state owns
	 * the menu sees a genuine key press (simulated selection moves like
	 * scrollSelection() cannot cross accept-gated substate boundaries). */
	static function simulateKey(key:String):Void {
		#if sys
		var stage = FlxG.stage;
		if (stage == null)
			return;
		var keyCode:Int = switch (key) {
			case 'left': openfl.ui.Keyboard.LEFT;
			case 'right': openfl.ui.Keyboard.RIGHT;
			case 'escape': openfl.ui.Keyboard.ESCAPE;
			default: openfl.ui.Keyboard.ENTER;
		};
		try {
			stage.dispatchEvent(new openfl.events.KeyboardEvent(
				openfl.events.KeyboardEvent.KEY_DOWN, true, false, keyCode, keyCode));
			haxe.Timer.delay(function():Void {
				try stage.dispatchEvent(new openfl.events.KeyboardEvent(
					openfl.events.KeyboardEvent.KEY_UP, true, false, keyCode, keyCode));
			}, 80);
		} catch (error:Dynamic)
			emit('accept_failure', {detail: Std.string(error)});
		#end
	}

	/** One simulated selection move on whatever state owns `changeSelection`. */
	static function scrollSelection():Void {
		var method = Reflect.field(FlxG.state, 'changeSelection');
		if (method != null && Reflect.isFunction(method)) {
			try Reflect.callMethod(FlxG.state, method, [1]) catch (error:Dynamic) {
				emit('scroll_failure', {detail: Std.string(error)});
			}
		}
	}

	/** One per-second observation line: pacing percentiles + bitmap census. */
	static function emitFrameSummary():Void {
		// Periodic live samples distinguish working dances from a valid atlas
		// that never starts an animation. This runs only with smoke frame stats.
		var visualState = PlayState.instance;
		if (playStateReady && visualState != null && FlxG.state == visualState) {
			for (role in ['player', 'opponent', 'girlfriend']) {
				var actor = role == 'player' ? visualState.boyfriend
					: (role == 'opponent' ? visualState.dad : visualState.gf);
				var visual = RuntimeSmokeVisuals.character(role, actor);
				Reflect.setField(visual, 'songPosition', Conductor.songPosition);
				emit('character_animation_sample', visual);
			}
		}
		var cache = bitmapCensus();
		var stateName = FlxG.state == null ? '' : Type.getClassName(Type.getClass(FlxG.state));
		var deltaFps:Float = 0;
		var deltaSum:Float = 0;
		for (delta in deltas)
			deltaSum += delta;
		if (deltas.length > 0)
			deltaFps = 1000 / (deltaSum / deltas.length);
		var sections:Map<String, Float> = sectionMs;
		sectionMs = new Map<String, Float>();
		emit('frame_stats', {
			phase: playStateReady ? 'gameplay' : (leftFreeplay ? 'after_freeplay' : (freeplaySeen ? 'freeplay' : 'startup')),
			songPosition: playStateReady ? Conductor.songPosition : null,
			state: stateName,
			frames: costs.length,
			updates: updateCosts.length,
			draws: drawCosts.length,
			totalFrames: totalFrames,
			costP50Ms: rounded(percentile(costs, 0.5)),
			costP95Ms: rounded(percentile(costs, 0.95)),
			costMaxMs: rounded(maxOf(costs)),
			updateP50Ms: rounded(percentile(updateCosts, 0.5)),
			updateP95Ms: rounded(percentile(updateCosts, 0.95)),
			drawP50Ms: rounded(percentile(drawCosts, 0.5)),
			drawP95Ms: rounded(percentile(drawCosts, 0.95)),
			deltaP50Ms: rounded(percentile(deltas, 0.5)),
			deltaP95Ms: rounded(percentile(deltas, 0.95)),
			deltaMaxMs: rounded(maxOf(deltas)),
			fps: Math.round(deltaFps),
			hitches: windowHitches,
			bitmapCount: cache.count,
			bitmapMB: Math.round(cache.mb),
			bitmapTop: cache.top,
			sectionMs: sections
		});
		costs.resize(0);
		updateCosts.resize(0);
		drawCosts.resize(0);
		deltas.resize(0);
		windowHitches = 0;
	}

	static function percentile(samples:Array<Float>, fraction:Float):Float {
		if (samples.length == 0)
			return 0;
		var sorted = samples.copy();
		sorted.sort(Reflect.compare);
		var index = Std.int(Math.min(sorted.length - 1, Math.round(fraction * (sorted.length - 1))));
		return sorted[index];
	}

	static function maxOf(samples:Array<Float>):Float {
		var best:Float = 0;
		for (sample in samples)
			if (sample > best)
				best = sample;
		return best;
	}

	static function rounded(value:Float):Float
		return Math.round(value * 10) / 10;

	/** Count cached bitmaps and report the largest cached textures by bytes. */
	public static function bitmapCensus():{count:Int, mb:Float, top:Array<String>} {
		var result = {count: 0, mb: 0.0, top: new Array<String>()};
		#if sys
		var cache:Map<String, Dynamic> = Reflect.field(FlxG.bitmap, '_cache');
		if (cache == null)
			return result;
		var entries:Array<Dynamic> = [];
		for (key in cache.keys()) {
			var graphic = cache.get(key);
			var bmd = graphic == null ? null : Reflect.field(graphic, 'bitmap');
			var width:Float = bmd == null ? 0 : Reflect.field(bmd, 'width');
			var height:Float = bmd == null ? 0 : Reflect.field(bmd, 'height');
			var bytes:Float = width * height * 4;
			result.count++;
			result.mb += bytes / 1048576;
			entries.push({key: key, bytes: bytes});
		}
		entries.sort(function(a, b) return Reflect.compare(b.bytes, a.bytes));
		for (i in 0...Std.int(Math.min(6, entries.length)))
			result.top.push(Std.string(entries[i].key).substr(0, 90) + ':' + Math.round(entries[i].bytes / 1048576) + 'MB');
		#end
		return result;
	}


	static function emit(event:String, extra:Dynamic):Void {
		var payload:Dynamic = {
			event: event,
			marker: 'runtime-smoke',
			time: #if sys Sys.time() #else 0 #end,
			runToken: runToken
		};
		if (extra != null)
			for (field in Reflect.fields(extra))
				if (field != 'event' && field != 'marker' && field != 'time' && field != 'runToken')
					Reflect.setField(payload, field, Reflect.field(extra, field));
		var line = 'RUNTIME_SMOKE|' + Json.stringify(payload);
		#if sys
		Sys.println(line);
		var path = config() == null ? '' : config().logPath;
		if (path != null && StringTools.trim(path) != '') {
			try {
				ensureParent(path);
				var stream = File.append(path, false);
				stream.writeString(line + '\n');
				stream.close();
			} catch (error:Dynamic) {
				Sys.println('RUNTIME_SMOKE|' + Json.stringify({event: 'log_failure', detail: Std.string(error)}));
			}
		}
		#end
	}

	static function safeToken(raw:Null<String>):String {
		if (raw == null)
			return '';
		var value = StringTools.trim(raw);
		if (value == '' || value.indexOf('/') >= 0 || value.indexOf('\\') >= 0 || value.indexOf('..') >= 0)
			return '';
		return value;
	}

	static function parseSmokeTime(raw:Null<String>):Float {
		var value = Std.parseFloat(raw == null ? '' : StringTools.trim(raw));
		return Math.isFinite(value) && value >= 0 && value <= 600000 ? value : -1;
	}

	/** Request the seek once audio has crossed the configured source position. */
	static function maybeRunSeek():Void {
		var request = config();
		if (request == null || request.seekToMs < 0 || seekCompleted
			|| !playStateReady || !songStartObserved)
			return;
		var music = FlxG.sound.music;
		if (music == null || !Math.isFinite(music.time) || music.time < request.seekAfterMs)
			return;
		var state = PlayState.instance;
		if (state == null || FlxG.state != state) {
			fail('seek-state', 'Configured seek did not run in the active PlayState');
			return;
		}
		var snapshot = state.seekForwardForSmoke(request.seekToMs);
		if (snapshot == null) {
			fail('seek-rejected', 'PlayState could not apply the configured forward seek');
			return;
		}
		markSeekComplete(snapshot);
	}

	static function parseInt(raw:Null<String>, fallback:Int):Int {
		if (raw == null)
			return fallback;
		var value = Std.parseInt(StringTools.trim(raw));
		return value == null ? fallback : value;
	}

	static function parsePlaystateVisits(raw:Null<String>):Int {
		var value = raw == null ? '' : StringTools.trim(raw);
		return value == '1' ? 1 : (value == '2' ? 2 : 0);
	}

	/** Mirror the demo playback-speed effect (music pitch + global time scale)
		without requiring demo mode, so a full imported song fits into a short
		smoke window.  Re-applied every tick because state switches reset the
		global time scale. */
	static function applySongRate():Void {
		var rate = config().songRate;
		if (rate <= 1)
			return;
		#if sys
		FlxG.timeScale = rate;
		if (FlxG.sound.music != null)
			FlxG.sound.music.pitch = rate;
		#end
	}

	static function boundedDuration(value:Int):Int {
		// Full imported songs run past three minutes; the bound only exists so a
		// mistyped flag can never pin the process down forever.
		return Std.int(Math.max(250, Math.min(600000, value)));
	}

	static function inferDifficulty(folder:String, chart:String):String {
		var song = folder.toLowerCase();
		var selected = chart.toLowerCase();
		var prefix = song + '-';
		return selected.startsWith(prefix) ? selected.substr(prefix.length) : 'normal';
	}

	#if sys
	static function ensureParent(path:String):Void {
		var parent = Path.directory(Path.normalize(path));
		if (parent == null || parent == '' || parent == '.')
			return;
		ensureDirectory(parent);
	}

	static function ensureDirectory(path:String):Void {
		var normalized = Path.normalize(path);
		if (normalized == '' || normalized == '.' || FileSystem.exists(normalized))
			return;
		var parent = Path.directory(normalized);
		if (parent != normalized && parent != '')
			ensureDirectory(parent);
		try FileSystem.createDirectory(normalized) catch (_:Dynamic) {}
	}
	#end
}
