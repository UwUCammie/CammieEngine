package;

import flixel.FlxBasic;
import flixel.FlxG;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;

/**
	Opt-in native smoke check for song retries. Ordinary launches never
	install it.

	`--smoke-retry-after-ms <ms>` retries once the first attempt reaches that
	song position. `--smoke-retry-route gameover|pause` picks how: a death
	confirmed with the accept key once the game over has shown for a second,
	or the pause menu's Restart. It reports how long the retry took to reach
	the first playable frame and compares that frame with the first attempt's
	(notes, scripts, sprites, timers, tweens, sounds), so a retry that doubles
	scripts or leaks sprites shows up.
**/
@:access(RuntimeSmokeHarness)
@:access(PlayState)
class RuntimeRetryProbe {
	static var installed:Bool = false;
	static var afterMs:Float = -1;
	static var route:String = 'gameover';
	// 0 first attempt, 1 waiting for the game over, 2 waiting for the pause
	// menu, 3 waiting for the retried attempt, 4 done.
	static var phase:Int = 0;
	static var first:PlayState;
	static var firstStats:Dynamic;
	// Image cache keys seen at the previous playable frame, to name new ones.
	static var knownBitmaps:Map<String, Bool>;
	static var waitStarted:Float = -1;
	// When the death or pause was set off, so a script that restarts the song
	// on its own (a custom game over substate) is still timed from there.
	static var triggerAt:Float = -1;
	static var pressAt:Float = -1;
	// Whether the probe pressed the key or a script restarted by itself.
	static var pressedBy:String = 'probe';
	// Asset epoch and import generation at the attempt's first playable frame.
	static var startEpoch:Int = -1;
	static var startGeneration:Int = -1;
	static var readyAt:Float = -1;
	// `--smoke-retry-count <n>` retries n times in a row (default once), so a
	// leak that grows with every retry shows up in the later attempts.
	static var retries:Int = 1;
	static var retried:Int = 0;

	/** RuntimeSmokeHarness calls this each time a PlayState is ready. */
	public static function install():Void {
		#if sys
		readyAt = haxe.Timer.stamp();
		if (installed || !RuntimeSmokeHarness.enabled()) return;
		var args = Sys.args();
		var index = args.indexOf('--smoke-retry-after-ms');
		if (index < 0 || index + 1 >= args.length) return;
		afterMs = Std.parseFloat(args[index + 1]);
		if (!Math.isFinite(afterMs) || afterMs < 0) return;
		var routeIndex = args.indexOf('--smoke-retry-route');
		if (routeIndex >= 0 && routeIndex + 1 < args.length) route = StringTools.trim(args[routeIndex + 1]);
		var countIndex = args.indexOf('--smoke-retry-count');
		if (countIndex >= 0 && countIndex + 1 < args.length) {
			var count = Std.parseInt(args[countIndex + 1]);
			if (count != null && count > 0 && count <= 10) retries = count;
		}
		if (route != 'gameover' && route != 'pause') {
			RuntimeSmokeHarness.fail('retry-probe', 'Unknown --smoke-retry-route ' + route);
			return;
		}
		installed = true;
		FlxG.signals.postUpdate.add(tick);
		#end
	}

	static function tick():Void {
		var now = haxe.Timer.stamp();
		var state = PlayState.instance;
		switch (phase) {
			case 0:
				// Both attempts are compared at their first playable frame.
				if (firstStats == null && playable(state)) {
					first = state;
					firstStats = stats(state);
					RuntimeSmokeHarness.emit('retry_attempt', {attempt: 1, stats: firstStats});
				}
				if (state == first && startEpoch < 0 && playable(state)) {
					startEpoch = FNFAssets.pathEpoch();
					startGeneration = ImportRefreshManager.generation;
				}
				if (firstStats == null || state != first || !playable(state) || Conductor.songPosition < afterMs) return;
				triggerAt = now;
				pressedBy = 'probe';
				if (route == 'gameover') {
					state.health = PlayState.opponentPlayer ? 2 : 0;
					phase = 1;
				} else {
					state.openPauseMenu();
					phase = 2;
				}
				waitStarted = -1;
			case 1:
				if (restartedByScript(state, now)) return;
				// A script may run its own game over in a custom substate
				// instead of GameOverSubstate. Confirm that one the same way.
				if (GameOverSubstate.instance == null && (state == null || state.subState == null)) return;
				if (waitStarted < 0) waitStarted = now;
				if (now - waitStarted < 1.0) return;
				pressAt = now;
				RuntimeSmokeHarness.simulateKey('enter');
				phase = 3;
			case 2:
				if (restartedByScript(state, now)) return;
				var pause = state == null ? null : Std.downcast(state.subState, PauseSubState);
				if (pause == null) return;
				if (waitStarted < 0) waitStarted = now;
				if (now - waitStarted < 0.5) return;
				pressAt = now;
				pause.restartSong();
				phase = 3;
			case 3:
				if (now - pressAt > 120) {
					RuntimeSmokeHarness.fail('retry-probe', 'The retried song never became playable');
					phase = 4;
					return;
				}
				if (state == first || !playable(state)) return;
				var secondStats = stats(state);
				retried++;
				RuntimeSmokeHarness.emit('retry_attempt', {attempt: retried + 1, stats: secondStats});
				var requested = SongRetry.requestedAt;
				RuntimeSmokeHarness.emit('retry_timing', {
					route: route,
					pressedBy: pressedBy,
					// A moved epoch makes the retry decode its images again.
					epochMoved: startEpoch >= 0 && FNFAssets.pathEpoch() != startEpoch,
					importGenerationMoved: startGeneration >= 0 && ImportRefreshManager.generation != startGeneration,
					fast: SongRetry.lastFast,
					refusal: SongRetry.lastRefusal,
					keptImages: SongRetry.lastKeptImages,
					pressToPlayableMs: (now - pressAt) * 1000,
					requestToPlayableMs: requested < 0 ? null : (now - requested) * 1000,
					requestToReadyMs: requested < 0 || readyAt < requested ? null : (readyAt - requested) * 1000,
					sameNotes: Reflect.field(firstStats, 'notes') == Reflect.field(secondStats, 'notes'),
					sameScripts: Reflect.field(firstStats, 'scripts') == Reflect.field(secondStats, 'scripts')
				});
				startEpoch = startGeneration = -1;
				if (retried < retries) {
					// Retry again from this attempt, still compared with the first.
					first = state;
					phase = 0;
					return;
				}
				phase = 4;
				FlxG.signals.postUpdate.remove(tick);
			default:
		}
	}

	/**
		A script restarted the song before the probe pressed anything, as a
		custom game over substate that restarts by itself does. That restart
		is the retry; it is timed from the death or pause that set it off.
	**/
	static function restartedByScript(state:PlayState, now:Float):Bool {
		if (state == null || state == first || !playable(state)) return false;
		pressAt = triggerAt;
		pressedBy = 'script';
		phase = 3;
		return true;
	}

	/** The song is on screen and running: created, nothing over it. */
	static function playable(state:PlayState):Bool {
		return state != null && FlxG.state == state && state.subState == null && !state.paused
			&& RuntimeSmokeHarness.playStateReady && !SongLoadingScreen.active;
	}

	static function stats(state:PlayState):Dynamic {
		var scripts = 0;
		for (_ in state.hscriptStates.keys()) scripts++;
		var bitmaps = 0;
		var added:Array<String> = [];
		// Text graphics the previous playable frame already had. Every text
		// of that attempt should be gone by now, so these are leaks (or a
		// later text that took a freed key such as the bare 'text').
		var keptTexts:Array<String> = [];
		var seen = new Map<String, Bool>();
		@:privateAccess for (key in FlxG.bitmap._cache.keys()) {
			bitmaps++;
			seen.set(key, true);
			var graphic = FlxG.bitmap.get(key);
			if (knownBitmaps != null && !knownBitmaps.exists(key) && added.length < 12) {
				added.push(key.substr(key.length > 90 ? key.length - 90 : 0)
					+ '#' + (graphic == null ? -1 : graphic.useCount));
			}
			if (knownBitmaps != null && knownBitmaps.exists(key) && StringTools.startsWith(key, 'text') && keptTexts.length < 12) {
				keptTexts.push(key + '#' + (graphic == null ? -1 : graphic.useCount)
					+ (graphic == null ? '' : ' ' + graphic.width + 'x' + graphic.height));
			}
		}
		knownBitmaps = seen;
		@:privateAccess var timers = FlxTimer.globalManager._timers.length;
		@:privateAccess var tweens = FlxTween.globalManager._tweens.length;
		return {
			notes: state.unspawnNotes.length + (state.notes == null ? 0 : state.notes.length),
			scripts: scripts,
			psychRuntimes: state.psychRuntimeBindings.length,
			codenameScripts: state.codenameScriptScopes.length,
			objects: countObjects(state.members, 0),
			bitmaps: bitmaps,
			newBitmaps: added,
			keptTexts: keptTexts,
			sounds: FlxG.sound.list.length,
			soundsAlive: FlxG.sound.list.countLiving(),
			soundsPlaying: [for (sound in FlxG.sound.list.members) if (sound != null && sound.exists && sound.playing) sound].length,
			soundsPersist: [for (sound in FlxG.sound.list.members) if (sound != null && sound.exists && sound.persist) sound].length,
			timers: timers,
			tweens: tweens
		};
	}

	static function countObjects(members:Array<FlxBasic>, depth:Int):Int {
		if (members == null || depth > 8) return 0;
		var count = 0;
		for (member in members) {
			if (member == null || !member.exists) continue;
			count++;
			if (Std.isOfType(member, FlxTypedGroup))
				count += countObjects((cast member:FlxTypedGroup<FlxBasic>).members, depth + 1);
		}
		return count;
	}
}
