package;

#if cpp
import flixel.util.FlxTimer;
import hxvlc.flixel.FlxVideoSprite;
import hxvlc.openfl.Location;
import sys.FileSystem;

using StringTools;

/**
	Owner-scoped adapter for the `FunkinVideoSprite` used by Nightmare Vision
	stage scripts. It preserves the source callback shape while making every
	video path resolve through that script's selected package.
*/
class NightmareVisionVideoSprite extends FlxVideoSprite {
	public static inline var looping:String = ':input-repeat=65535';
	public static inline var muted:String = ':no-audio';
	static var live:Array<NightmareVisionVideoSprite> = [];

	public var ownerState(default, null):Dynamic;
	public var ownerRoot(default, null):String;
	public var tiedToGame:Bool = true;
	public var canSkip:Bool = false;
	var ownerPaths:Dynamic;
	var formatCallbacks:Array<Dynamic> = [];
	var endCallbacks:Array<Dynamic> = [];
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
	public function onFormat(callback:Dynamic):Void {
		if (callback == null || !Reflect.isFunction(callback))
			return;
		formatCallbacks.push(callback);
		if (formatted)
			invokeCallback(callback, 'format');
	}

	/** Register the source `onEnd` callback, including load and decoder errors. */
	public function onEnd(callback:Dynamic):Void {
		if (callback == null || !Reflect.isFunction(callback))
			return;
		endCallbacks.push(callback);
		if (finished)
			invokeCallback(callback, 'end');
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

	/** Start after the next frame, as the source video-sprite helper does. */
	public function delayAndStart():Void {
		if (disposed || finished || !loaded || startTimer != null)
			return;
		startTimer = new FlxTimer().start(0.001, function(_:FlxTimer) {
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
		for (callback in formatCallbacks.copy())
			invokeCallback(callback, 'format');
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
		for (callback in endCallbacks.copy())
			invokeCallback(callback, 'end');
		if (oneTimeUse)
			destroy();
	}

	function invokeCallback(callback:Dynamic, phase:String):Void {
		if (callback == null || !Reflect.isFunction(callback))
			return;
		try Reflect.callMethod(null, callback, []) catch (error:Dynamic)
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
class NightmareVisionVideoSprite extends FlxSprite {
	static var live:Array<NightmareVisionVideoSprite> = [];
	public var ownerState(default, null):Dynamic;
	public var ownerRoot(default, null):String;
	public var tiedToGame:Bool = true;
	public var canSkip:Bool = false;
	var ownerPaths:Dynamic;
	var endCallbacks:Array<Dynamic> = [];
	var finished:Bool = false;
	var oneTimeUse:Bool = true;

	public function new(ownerState:Dynamic, ownerPaths:Dynamic, x:Float = 0, y:Float = 0,
		oneTimeUse:Bool = true, isSkippable:Bool = false) {
		super(x, y);
		this.ownerState = ownerState;
		this.ownerPaths = ownerPaths;
		ownerRoot = ownerPaths == null ? '' : Std.string(Reflect.field(ownerPaths, 'root'));
		this.oneTimeUse = oneTimeUse;
		canSkip = isSkippable;
		live.push(this);
	}

	public function onFormat(_callback:Dynamic):Void {}
	public function onEnd(callback:Dynamic):Void {
		if (callback == null || !Reflect.isFunction(callback)) return;
		endCallbacks.push(callback);
		if (finished) invokeCallback(callback);
	}

	public function load(_location:Dynamic, ?_options:Array<String>):Bool {
		trace('[nightmare-vision-video] phase=unsupported path=' + ownerRoot);
		finish();
		return false;
	}

	public function delayAndStart():Void {}
	public function play():Bool return false;
	public function skip():Void finish();

	function finish():Void {
		if (finished) return;
		finished = true;
		for (callback in endCallbacks.copy()) invokeCallback(callback);
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
