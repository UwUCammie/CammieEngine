package;

import openfl.media.Sound;

/**
	Fast retries of the song being played.

	A retry (game over, the pause menu, a script) still builds a fresh
	PlayState, so every script engine starts the next attempt exactly like a
	first play. What it skips is the work the attempt that just ended already
	did: the loading screen, the image decodes the song holds, built atlases
	and the decoded song audio. Main keeps the held images through the state
	swap and PlayState takes its audio tracks back from here.

	Only a retry of the same chart takes this path; a different chart or
	difficulty goes through the normal loading screen. An import refresh or a
	file write during the song keeps the quick switch but not the cached
	decodes, since any of them may be stale; the next attempt reads its files
	again. Background import work often refreshes unrelated packages while a
	song plays, so it must not cost the player the quick retry, and the
	loading screen itself never reloaded anything a fresh PlayState does not.
**/
class SongRetry {
	// The attempt being played, recorded when its PlayState finished creating.
	static var attemptChart:Dynamic = null;
	static var attemptDifficulty:Int = -1;
	static var attemptEpoch:Int = -1;

	/** A fast retry was asked for and the next PlayState has not started yet. */
	public static var pending(default, null):Bool = false;
	/** True while a PlayState started by a fast retry is creating. */
	public static var active(default, null):Bool = false;
	/** Whether the last retry request took the fast path. */
	public static var lastFast(default, null):Bool = false;
	/** When the last retry was asked for, in haxe.Timer.stamp() seconds; -1 before any. */
	public static var requestedAt(default, null):Float = -1;

	// Decoded song tracks of the attempt being played, by path and variant.
	static var tracks:Map<String, SongRetryTrack> = new Map();
	// Tracks the attempt before a retry decoded, waiting to be taken back.
	static var carried:Map<String, SongRetryTrack> = new Map();
	// The asset epoch moved between the attempts: a track is only taken back
	// when its own file provably did not change.
	static var carriedAcrossEpoch:Bool = false;
	// Script translations of the attempt being played, and of the one before a
	// retry. A translation is reused only for the very same script text.
	static var translations:Map<String, SongRetryTranslation> = new Map();
	static var carriedTranslations:Map<String, SongRetryTranslation> = new Map();

	/** The rule: a retry is quick only for the same chart object and the same
		difficulty as the attempt that just ended. */
	public static function sameAttempt(startedChart:Dynamic, startedDifficulty:Int, chart:Dynamic,
			difficulty:Int):Bool {
		return startedChart != null && chart == startedChart && difficulty == startedDifficulty;
	}

	/** PlayState calls this at the start of create(). Returns true when this
		start is a fast retry, which may take tracks back with songTrack(). */
	public static function beginAttempt():Bool {
		active = pending;
		pending = false;
		if (!active)
			carriedAcrossEpoch = false;
		carried = active ? tracks : new Map();
		tracks = new Map();
		carriedTranslations = active ? translations : new Map();
		translations = new Map();
		return active;
	}

	/** PlayState calls this at the end of create() with what it now plays.
		Tracks the new attempt did not ask for are let go. */
	public static function finishAttempt(chart:Dynamic, difficulty:Int, epoch:Int):Void {
		attemptChart = chart;
		attemptDifficulty = difficulty;
		attemptEpoch = epoch;
		carried = new Map();
		carriedTranslations = new Map();
		carriedAcrossEpoch = false;
		active = false;
	}

	/** The chart being played was read again from its own file, as a script
		reloading its own song does. The new object stands for the same attempt. */
	public static function chartReloaded(chart:Dynamic):Void {
		if (attemptChart != null && chart != null)
			attemptChart = chart;
	}

	/** Ask to retry the attempt being played. False means another chart or
		difficulty is being asked for, which takes the full loading path. */
	public static function request(chart:Dynamic, difficulty:Int, now:Float):Bool {
		requestedAt = now;
		pending = sameAttempt(attemptChart, attemptDifficulty, chart, difficulty);
		lastFast = pending;
		lastRefusal = pending ? '' : attemptChart == null ? 'no-attempt' : chart != attemptChart ? 'chart' : 'difficulty';
		return pending;
	}

	/** Whether the last state swap kept the song's images for a retry. */
	public static var lastKeptImages(default, null):Bool = false;

	/** Why the last retry took the full loading path, empty when it did not. */
	public static var lastRefusal(default, null):String = '';

	/**
		Main asks this while it swaps states away from a song, before it sweeps
		the song's images. True only for a pending fast retry going into the
		next PlayState with the same asset epoch, so no image can be stale.
		Background import work moves the epoch for unrelated packages, so the
		audio and translations still go along and are checked file by file.
		Anything but a retry forgets the song's tracks, so leaving frees them.
	**/
	public static function keepsSongAssets(enteringPlayState:Bool, epoch:Int):Bool {
		if (pending && enteringPlayState) {
			carriedAcrossEpoch = epoch != attemptEpoch;
			lastKeptImages = !carriedAcrossEpoch;
			return lastKeptImages;
		}
		lastKeptImages = false;
		pending = false;
		tracks = new Map();
		carried = new Map();
		translations = new Map();
		carriedTranslations = new Map();
		return false;
	}

	/**
		The translation of one script for this attempt. A fast retry reuses the
		previous attempt's result when the script text is unchanged; otherwise
		`translate` runs. `key` names the translator, its options and the path.
		Results are shared, so callers must treat them as read only. `keep`
		refuses results that also depend on other files (an HXC character reads
		its base classes), since the text check cannot see those change.
	**/
	public static function translation<T>(key:String, source:String, translate:Void->T, ?keep:Dynamic->Bool):T {
		var previous = carriedTranslations.get(key);
		var result:T = previous != null && previous.source == source ? cast previous.result : translate();
		if (source != null && (keep == null || keep(result)))
			translations.set(key, {source: source, result: result});
		return result;
	}

	/**
		The decoded song track for `path`. A fast retry gets back the one the
		previous attempt decoded; otherwise `decode` runs. `variant` tells
		apart decodes of one file that are not interchangeable, such as with
		and without loudness normalization.
	**/
	public static function songTrack(path:String, variant:String, decode:Void->Sound):Sound {
		var key = trackKey(path, variant);
		var stamp = fileStamp(path);
		var sound:Sound = null;
		var previous = carried.get(key);
		if (previous != null) {
			carried.remove(key);
			if (reusable(previous, stamp))
				sound = previous.sound;
		}
		if (sound == null)
			sound = decode();
		if (sound != null)
			tracks.set(key, {sound: sound, stamp: stamp});
		return sound;
	}

	/** True when a fast retry has the track for `path` waiting, so the caller
		can skip starting a decode it would throw away. */
	public static function hasCarriedTrack(path:String, variant:String):Bool {
		var previous = carried.get(trackKey(path, variant));
		return previous != null && reusable(previous, fileStamp(path));
	}

	static function reusable(track:SongRetryTrack, stamp:String):Bool {
		return track.stamp == stamp && (!carriedAcrossEpoch || stamp != '');
	}

	/** Size, change and status times of a track file; empty when it cannot be
		read. A copied-in replacement keeps the source's mtime, and can keep
		its size too, so ctime is compared as SongAudioNormalizer does. */
	static function fileStamp(path:String):String {
		#if sys
		try {
			if (path != null && sys.FileSystem.exists(path)) {
				var stat = sys.FileSystem.stat(path);
				return stat.size + ':' + stat.mtime.getTime() + ':' + stat.ctime.getTime();
			}
		} catch (_:Dynamic) {}
		#end
		return '';
	}

	static inline function trackKey(path:String, variant:String):String {
		return (path == null ? '' : path) + '|' + (variant == null ? '' : variant);
	}

	/** Forget everything. For tests and a full engine reset. */
	public static function reset():Void {
		attemptChart = null;
		attemptDifficulty = -1;
		attemptEpoch = -1;
		pending = active = lastFast = carriedAcrossEpoch = false;
		requestedAt = -1;
		tracks = new Map();
		carried = new Map();
		translations = new Map();
		carriedTranslations = new Map();
	}
}

private typedef SongRetryTrack = {
	var sound:Sound;
	var stamp:String;
}

private typedef SongRetryTranslation = {
	var source:String;
	var result:Dynamic;
}
