package;

#if cpp
import flixel.util.FlxTimer;
import hxvlc.flixel.FlxVideoSprite;
import hxvlc.openfl.Location;
import sys.FileSystem;
import SourceVideoPlayback.SourceVideoCallback;

using StringTools;

/**
	Owner-scoped adapter for the `FunkinVideoSprite` used by Nightmare Vision
	stage scripts. It preserves the source callback shape while making every
	video path resolve through that script's selected package.
*/
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionVideoSprite extends FlxVideoSprite {
	public static inline var looping:String = ':input-repeat=65535';
	public static inline var muted:String = ':no-audio';
	static var live:Array<NightmareVisionVideoSprite> = [];

	public var ownerState(default, null):Dynamic;
	public var ownerRoot(default, null):String;
	public var tiedToGame:Bool = true;
	public var canSkip:Bool = false;
	public var playbackRate(default, set):Float = 1.0;
	/** 0..1 like the source; it scales the game volume rather than replacing it. */
	public var volume(default, set):Float = 1.0;
	public var isPlaying(get, never):Bool;
	public var progress(get, never):Float;
	public var currentTime(get, never):Int;
	public var duration(get, never):Int;
	var ownerPaths:Dynamic;
	var formatCallbacks:Array<SourceVideoCallback> = [];
	var endCallbacks:Array<SourceVideoCallback> = [];
	var startTimer:FlxTimer;
	var formatted:Bool = false;
	var finished:Bool = false;
	var disposed:Bool = false;
	var hostPaused:Bool = false;
	var loaded:Bool = false;
	var resolvedPath:String = null;
	var oneTimeUse:Bool = true;

	public function new(ownerState:Dynamic, ownerPaths:Dynamic, x:Float = 0, y:Float = 0,
		oneTimeUse:Bool = true, isSkippable:Bool = false) {
		super(null, x, y);
		if (ownerPaths == null)
			throw '[nightmare-vision-video-owner] Missing selected asset paths';
		this.ownerState = ownerState;
		this.ownerPaths = ownerPaths;
		ownerRoot = Std.string(Reflect.field(ownerPaths, 'root'));
		NightmareVisionSpriteMethods.bind(this, NightmareVisionSpriteRegistry.peek(ownerRoot));
		this.oneTimeUse = oneTimeUse;
		canSkip = isSkippable;
		live.push(this);
		if (bitmap == null) {
			trace('[nightmare-vision-video-error] video decoder was not created');
			finish('decoder-unavailable');
			return;
		}
		bitmap.onFormatSetup.add(onFormatSetup);
		bitmap.onEndReached.add(function() finish('ended'));
		bitmap.onEncounteredError.add(function(error:String) {
			trace('[nightmare-vision-video-error] ' + ownerRoot + ': ' + error);
			finish('decoder-error');
		});
	}

	/** Register the source `onFormat` callback, including late registrations. */
	public function onFormat(callback:Dynamic, once:Bool = false, priority:Int = 0):Void
		register(formatCallbacks, callback, once, priority, formatted, 'format');

	/** Register the source `onEnd` callback, including load and decoder errors. */
	public function onEnd(callback:Dynamic, once:Bool = false, priority:Int = 0):Void
		register(endCallbacks, callback, once, priority, finished, 'end');

	// A late registration still hears an event that already happened, so a
	// `once` callback is spent on the spot instead of being kept.
	function register(list:Array<SourceVideoCallback>, callback:Dynamic, once:Bool, priority:Int,
		alreadyHappened:Bool, phase:String):Void {
		if (callback == null || !Reflect.isFunction(callback))
			return;
		if (!(alreadyHappened && once))
			SourceVideoPlayback.insertByPriority(list, {callback:callback, once:once, priority:priority});
		if (alreadyHappened)
			invokeCallback(callback, phase);
	}

	// The remaining decoder events go straight to hxvlc, wrapped so a script
	// error is reported instead of breaking the decoder's own dispatch.
	public function onStart(callback:Dynamic, once:Bool = false, priority:Int = 0):Void
		if (bitmap != null && Reflect.isFunction(callback))
			bitmap.onOpening.add(function() invokeCallback(callback, 'start'), once, priority);

	public function onPause(callback:Dynamic, once:Bool = false, priority:Int = 0):Void
		if (bitmap != null && Reflect.isFunction(callback))
			bitmap.onPaused.add(function() invokeCallback(callback, 'pause'), once, priority);

	public function onStop(callback:Dynamic, once:Bool = false, priority:Int = 0):Void
		if (bitmap != null && Reflect.isFunction(callback))
			bitmap.onStopped.add(function() invokeCallback(callback, 'stop'), once, priority);

	public function onError(callback:Dynamic, once:Bool = false, priority:Int = 0):Void
		if (bitmap != null && Reflect.isFunction(callback))
			bitmap.onEncounteredError.add(function(error:String) invokeCallback(callback, 'error', [error]), once, priority);

	function set_playbackRate(value:Float):Float {
		playbackRate = SourceVideoPlayback.safeRate(value);
		if (bitmap != null) bitmap.rate = playbackRate;
		return playbackRate;
	}

	// hxvlc rewrites bitmap.volume from the game volume every frame; the
	// adjustment is the part that sticks.
	function set_volume(value:Float):Float {
		volume = SourceVideoPlayback.clampVolume(value);
		if (bitmap != null) bitmap.volumeAdjust = volume;
		return volume;
	}

	function get_isPlaying():Bool return !disposed && bitmap != null && bitmap.isPlaying;
	function get_progress():Float return bitmap == null ? 0.0
		: SourceVideoPlayback.progress(haxe.Int64.toInt(bitmap.time), haxe.Int64.toInt(bitmap.length));
	function get_currentTime():Int return bitmap == null ? -1 : haxe.Int64.toInt(bitmap.time);
	function get_duration():Int return bitmap == null ? -1 : haxe.Int64.toInt(bitmap.length);

	public function seekTo(time:Int):Void
		if (!disposed && bitmap != null) bitmap.time = haxe.Int64.ofInt(time < 0 ? 0 : time);

	public function seekToProgress(value:Float):Void {
		if (disposed || bitmap == null) return;
		var target = SourceVideoPlayback.seekTime(value, haxe.Int64.toInt(bitmap.length));
		if (target >= 0) bitmap.time = haxe.Int64.ofInt(target);
	}

	/** Scale and centre over the whole game window; meant for onFormat. */
	public function fitToScreen():Void {
		setGraphicSize(flixel.FlxG.width, flixel.FlxG.height);
		updateHitbox();
		screenCenter();
	}

	/** The source `instances` list, narrowed to one owner so scripts only see their own clips. */
	public static function instancesFor(root:String):Array<NightmareVisionVideoSprite> {
		var result:Array<NightmareVisionVideoSprite> = [];
		for (video in live) if (video != null && !video.disposed && (root == null || video.ownerRoot == root)) result.push(video);
		return result;
	}

	public static function forEach(callback:Dynamic, ?root:String):Void {
		if (!Reflect.isFunction(callback)) return;
		for (video in instancesFor(root)) Reflect.callMethod(null, callback, [video]);
	}

	public static function forEachAlive(callback:Dynamic, ?root:String):Void {
		if (!Reflect.isFunction(callback)) return;
		for (video in instancesFor(root)) if (video.exists && video.alive) Reflect.callMethod(null, callback, [video]);
	}

	/** Resolve only a path selected by the bound Nightmare Vision Paths facade. */
	public override function load(location:Location, ?options:Array<String>):Bool {
		if (disposed || bitmap == null) {
			trace('[nightmare-vision-video-load] result=failed reason=decoder-unavailable');
			finish('decoder-unavailable');
			return false;
		}
		var resolved = resolveVideo(location);
		if (resolved == null) {
			trace('[nightmare-vision-video-load] result=failed reason=missing-or-outside-owner');
			finish('load-failed');
			return false;
		}
		// Reusable sprites start a new callback cycle for every accepted load.
		// Keep path resolution and decoder ownership shared by source dialects.
		if (startTimer != null) {startTimer.cancel(); startTimer = null;}
		formatted = false;
		finished = false;
		resolvedPath = resolved;
		try {
			loaded = super.load(resolved, options);
			trace('[nightmare-vision-video-load] result=' + (loaded ? 'accepted' : 'failed')
				+ ' path=' + resolved);
			if (!loaded)
				finish('load-failed');
			return loaded;
		} catch (error:Dynamic) {
			trace('[nightmare-vision-video-load] result=failed path=' + resolved + ': ' + Std.string(error));
			finish('load-failed');
			return false;
		}
	}

	/** Start after the next frame, or after `delay` seconds, as the source helper does. */
	public function delayAndStart(delay:Float = 0):Void {
		if (disposed || finished || !loaded || startTimer != null)
			return;
		startTimer = new FlxTimer().start(Math.isNaN(delay) || delay < 0.001 ? 0.001 : delay, function(_:FlxTimer) {
			startTimer = null;
			if (disposed || finished || !loaded)
				return;
			try {
				if (!play()) {
				trace('[nightmare-vision-video-play] result=failed path=' + resolvedPath);
					finish('play-failed');
				} else {
				trace('[nightmare-vision-video-play] result=started path=' + resolvedPath);
				}
			} catch (error:Dynamic) {
			trace('[nightmare-vision-video-play] result=failed path=' + resolvedPath + ': ' + Std.string(error));
				finish('play-failed');
			}
		});
	}

	// A playing owner video is offered to the song as a cutscene. Whether a
	// press may skip it is CutsceneSkip's call, not the video's.
	public override function play():Bool {
		var started = super.play();
		var register:Dynamic = started && ownerState != null ? Reflect.field(ownerState, 'registerSongCutscene') : null;
		if (Reflect.isFunction(register)) {
			var ended = false;
			var shown:Dynamic = this;
			bitmap.onEndReached.add(function() ended = true);
			// The decoder reports playback a few frames after play(), so the clip
			// stays registered until it ends and only has a length while it shows.
			Reflect.callMethod(ownerState, register, [this,
				function() return disposed || bitmap == null || !bitmap.isPlaying || shown.visible == false || shown.alpha <= 0
					? 0.0 : haxe.Int64.toInt(bitmap.length) + 0.0,
				function() return !disposed && !finished && !ended && bitmap != null,
				function(ms:Float) if (!disposed && bitmap != null) bitmap.time = haxe.Int64.ofInt(Std.int(Math.max(0, ms))),
				function() skip(), null,
				function() return disposed || bitmap == null ? Math.NaN : haxe.Int64.toInt(bitmap.time) + 0.0]);
		}
		return started;
	}

	public function skip():Void {
		if (disposed || finished)
			return;
		if (bitmap != null && bitmap.isPlaying)
			bitmap.stop();
		finish('skipped');
	}

	function resolveVideo(location:Location):String {
		if (location == null || !Std.isOfType(location, String)) {
			trace('[nightmare-vision-video-rejected] expected a named owner video');
			return null;
		}
		var key = StringTools.trim(cast location);
		if (key == '')
			return null;
		var candidates:Array<String> = [key];
		var normalized = key.replace('\\', '/');
		if (!normalized.startsWith('assets/')) {
			if (normalized.startsWith('videos/')) {
				var direct = callPaths('getPath', [normalized, null, true]);
				if (direct != null) candidates.push(Std.string(direct));
			} else {
				var byKey = callPaths('video', [normalized]);
				if (byKey != null) candidates.push(Std.string(byKey));
			}
		}
		for (candidate in candidates) {
			var scoped = callPaths('scopeAssetPath', [candidate]);
			if (scoped == null)
				continue;
			var path = Std.string(scoped);
			if (!pathExists(path))
				continue;
			#if sys
			if (FileSystem.isDirectory(path))
				continue;
			#end
			return path;
		}
		trace('[nightmare-vision-video-rejected] no selected-owner file resolved for ' + key);
		return null;
	}

	function callPaths(methodName:String, args:Array<Dynamic>):Dynamic {
		var method = Reflect.field(ownerPaths, methodName);
		return method == null || !Reflect.isFunction(method) ? null
			: Reflect.callMethod(ownerPaths, method, args);
	}

	function pathExists(path:String):Bool {
		var exists = callPaths('exists', [path]);
		return exists == true;
	}

	function onFormatSetup():Void {
		if (disposed || formatted)
			return;
		formatted = true;
		trace('[nightmare-vision-video] phase=format path=' + resolvedPath);
		SourceVideoPlayback.dispatch(formatCallbacks, function(callback) invokeCallback(callback, 'format'));
	}

	function finish(reason:String):Void {
		if (disposed || finished)
			return;
		finished = true;
		if (startTimer != null) {
			startTimer.cancel();
			startTimer = null;
		}
		trace('[nightmare-vision-video] phase=end reason=' + reason + ' path=' + resolvedPath);
		SourceVideoPlayback.dispatch(endCallbacks, function(callback) invokeCallback(callback, 'end'));
		if (oneTimeUse)
			destroy();
	}

	function invokeCallback(callback:Dynamic, phase:String, ?args:Array<Dynamic>):Void {
		if (callback == null || !Reflect.isFunction(callback))
			return;
		try Reflect.callMethod(null, callback, args == null ? [] : args) catch (error:Dynamic)
			trace('[nightmare-vision-video-callback-error] phase=' + phase + ': ' + Std.string(error));
	}

	public static function pauseForState(state:Dynamic):Void {
		for (video in live.copy()) {
			if (video == null || video.ownerState != state || video.disposed || video.bitmap == null)
				continue;
			if (video.bitmap.isPlaying) {
				video.hostPaused = true;
				video.pause();
			}
		}
	}

	public static function resumeForState(state:Dynamic):Void {
		for (video in live.copy()) {
			if (video == null || video.ownerState != state || video.disposed || !video.hostPaused)
				continue;
			video.hostPaused = false;
			if (video.bitmap != null)
				video.resume();
		}
	}

	public static function destroyForState(state:Dynamic):Void {
		for (video in live.copy()) {
			if (video == null || video.ownerState != state)
				continue;
			var members:Dynamic = state == null ? null : Reflect.field(state, 'members');
			var attached = Std.isOfType(members, Array)
				&& (cast members:Array<Dynamic>).indexOf(video) >= 0;
			if (attached) {
				var remove = Reflect.field(state, 'remove');
				if (Reflect.isFunction(remove))
					try Reflect.callMethod(state, remove, [video, true]) catch (_:Dynamic) {}
			}
			video.destroy();
		}
	}

	public override function destroy():Void {
		if (disposed)
			return;
		disposed = true;
		hostPaused = false;
		if (startTimer != null) {
			startTimer.cancel();
			startTimer = null;
		}
		live.remove(this);
		ownerState = null;
		ownerPaths = null;
		formatCallbacks.resize(0);
		endCallbacks.resize(0);
		super.destroy();
	}
}
#else
import flixel.FlxSprite;

/** Renderer-only fallback completes the scripted transition when video output
	is unavailable on the current target. */
@:build(NightmareVisionSpriteMacro.build())
class NightmareVisionVideoSprite extends FlxSprite {
	public static inline var looping:String = ':input-repeat=65535';
	public static inline var muted:String = ':no-audio';
	static var live:Array<NightmareVisionVideoSprite> = [];
	public var ownerState(default, null):Dynamic;
	public var ownerRoot(default, null):String;
	public var tiedToGame:Bool = true;
	public var canSkip:Bool = false;
	public var playbackRate(default, set):Float = 1.0;
	public var volume(default, set):Float = 1.0;
	public var isPlaying(get, never):Bool;
	public var progress(get, never):Float;
	public var currentTime(get, never):Int;
	public var duration(get, never):Int;
	var ownerPaths:Dynamic;
	var endCallbacks:Array<SourceVideoPlayback.SourceVideoCallback> = [];
	var finished:Bool = false;
	var oneTimeUse:Bool = true;

	public function new(ownerState:Dynamic, ownerPaths:Dynamic, x:Float = 0, y:Float = 0,
		oneTimeUse:Bool = true, isSkippable:Bool = false) {
		super(x, y);
		this.ownerState = ownerState;
		this.ownerPaths = ownerPaths;
		ownerRoot = ownerPaths == null ? '' : Std.string(Reflect.field(ownerPaths, 'root'));
		NightmareVisionSpriteMethods.bind(this, NightmareVisionSpriteRegistry.peek(ownerRoot));
		this.oneTimeUse = oneTimeUse;
		canSkip = isSkippable;
		live.push(this);
	}

	// Same members as the decoder build so scripts never hit an unknown field;
	// without a decoder only the end callbacks ever fire.
	public function onFormat(_callback:Dynamic, once:Bool = false, priority:Int = 0):Void {}
	public function onEnd(callback:Dynamic, once:Bool = false, priority:Int = 0):Void {
		if (callback == null || !Reflect.isFunction(callback)) return;
		if (!(finished && once))
			SourceVideoPlayback.insertByPriority(endCallbacks, {callback:callback, once:once, priority:priority});
		if (finished) invokeCallback(callback);
	}
	public function onStart(_callback:Dynamic, once:Bool = false, priority:Int = 0):Void {}
	public function onPause(_callback:Dynamic, once:Bool = false, priority:Int = 0):Void {}
	public function onStop(_callback:Dynamic, once:Bool = false, priority:Int = 0):Void {}
	public function onError(_callback:Dynamic, once:Bool = false, priority:Int = 0):Void {}
	function set_playbackRate(value:Float):Float return playbackRate = SourceVideoPlayback.safeRate(value);
	function set_volume(value:Float):Float return volume = SourceVideoPlayback.clampVolume(value);
	function get_isPlaying():Bool return false;
	function get_progress():Float return 0.0;
	function get_currentTime():Int return -1;
	function get_duration():Int return -1;
	public function seekTo(_time:Int):Void {}
	public function seekToProgress(_value:Float):Void {}
	public function fitToScreen():Void {}

	public static function instancesFor(root:String):Array<NightmareVisionVideoSprite> {
		var result:Array<NightmareVisionVideoSprite> = [];
		for (video in live) if (video != null && (root == null || video.ownerRoot == root)) result.push(video);
		return result;
	}
	public static function forEach(callback:Dynamic, ?root:String):Void {
		if (!Reflect.isFunction(callback)) return;
		for (video in instancesFor(root)) Reflect.callMethod(null, callback, [video]);
	}
	public static function forEachAlive(callback:Dynamic, ?root:String):Void {
		if (!Reflect.isFunction(callback)) return;
		for (video in instancesFor(root)) if (video.exists && video.alive) Reflect.callMethod(null, callback, [video]);
	}

	public function load(_location:Dynamic, ?_options:Array<String>):Bool {
		trace('[nightmare-vision-video] phase=unsupported path=' + ownerRoot);
		finish();
		return false;
	}

	public function delayAndStart(delay:Float = 0):Void {}
	public function play():Bool return false;
	public function skip():Void finish();

	function finish():Void {
		if (finished) return;
		finished = true;
		SourceVideoPlayback.dispatch(endCallbacks, invokeCallback);
		if (oneTimeUse)
			destroy();
	}

	function invokeCallback(callback:Dynamic):Void {
		try Reflect.callMethod(null, callback, []) catch (error:Dynamic)
			trace('[nightmare-vision-video-callback-error] ' + Std.string(error));
	}

	public static function pauseForState(_state:Dynamic):Void {}
	public static function resumeForState(_state:Dynamic):Void {}
	public static function destroyForState(state:Dynamic):Void {
		for (video in live.copy()) if (video != null && video.ownerState == state) video.destroy();
	}

	public override function destroy():Void {
		live.remove(this);
		ownerState = null;
		ownerPaths = null;
		endCallbacks.resize(0);
		super.destroy();
	}
}
#end
