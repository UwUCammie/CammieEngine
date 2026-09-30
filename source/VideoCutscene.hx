package;

#if cpp
import flixel.FlxBasic;
import flixel.FlxG;
import hxvlc.flixel.FlxVideo;
import openfl.display.Sprite;

typedef VideoCutsceneOptions = {
	?mute:Bool,
	?timestamp:Float,
	?zIndex:Int,
	?allowSkip:Bool,
	?skipHoldSeconds:Float,
	?skipPressed:Void->Bool
};

/** Owns native video playback and resumes gameplay once it finishes or fails. */
class VideoCutscene extends FlxBasic {
	var filename:String;
	var onComplete:Void->Void;
	var video:FlxVideo;
	var background:Sprite;
	var options:VideoCutsceneOptions;
	var started = false;
	var finished = false;
	var disposed = false;
	var suspended = false;
	var suspendedVideoVisible = true;
	var suspendedBackgroundVisible = true;
	var skipPending = false;
	var skipWaitSeconds:Float = 0;
	var skipHeldSeconds:Float = 0;
	/** Psych's VideoSprite lets a stage replace either transition callback. */
	public var finishCallback:Void->Void = null;
	public var onSkip:Void->Void = null;
	/** True only when the player explicitly skipped the video. */
	public var skipped(default, null):Bool = false;
	/** Records a skip request even when VLC never reports a duration. */
	public var skipRequested(get, never):Bool;
	function get_skipRequested():Bool return skipPending;
	/** Native clip duration in milliseconds, or zero until VLC knows it. */
	public var durationMs(get, never):Float;
	function get_durationMs():Float {
		if (video == null) return 0;
		var value = Std.parseFloat(Std.string(video.length));
		if (!Math.isFinite(value) || value <= 0)
			value = Std.parseFloat(Std.string(video.duration));
		return Math.isNaN(value) || !Math.isFinite(value) || value <= 0 ? 0 : value;
	}

	public function new(filename:String, onComplete:Void->Void, ?options:VideoCutsceneOptions) {
		super();
		this.filename = filename;
		this.onComplete = onComplete;
		this.options = options;
	}

	/** Chart-event videos are OpenFL children, outside FlxState's pause gate.
	 * Suspend VLC and hide both children while the native pause UI is open. */
	public function suspend():Void {
		if (disposed || finished || suspended) return;
		suspended = true;
		if (video != null) {
			suspendedVideoVisible = video.visible;
			video.pause();
			video.visible = false;
		}
		if (background != null) {
			suspendedBackgroundVisible = background.visible;
			background.visible = false;
		}
	}

	public function resume():Void {
		if (disposed || !suspended) return;
		suspended = false;
		if (finished) return;
		if (background != null) background.visible = suspendedBackgroundVisible;
		if (video != null) {
			video.visible = suspendedVideoVisible;
			video.resume();
		}
	}

	/** VLC may resume on OS focus gain even while the native pause menu is open. */
	function onFocusGained():Void {
		if (suspended && video != null)
			video.pause();
	}

	/** Keep an event clip aligned with its chart timestamp after stalls or seeks.
	 * The donor video module checks this on each step with a 550 ms threshold. */
	public function resyncSongTime(expectedMs:Float, ?thresholdMs:Float = 550):Bool {
		if (disposed || finished || suspended || video == null || !video.isPlaying
			|| !Math.isFinite(expectedMs) || expectedMs < 0)
			return false;
		var actualMs = Std.parseFloat(Std.string(video.time));
		if (!Math.isFinite(actualMs) || Math.abs(actualMs - expectedMs) <= thresholdMs)
			return false;
		video.pause();
		video.time = Std.int(expectedMs);
		video.resume();
		return true;
	}

	function start():Void {
		if (!sys.FileSystem.exists(filename)) {
			fail('Missing video: ' + filename);
			return;
		}
		try {
			background = new Sprite();
			FlxG.addChildBelowMouse(background);
			video = new FlxVideo();
			video.resizeMode = NONE;
			video.onEndReached.add(function() finished = true);
			video.onEncounteredError.add(fail);
			video.onFormatSetup.add(resize);
			FlxG.addChildBelowMouse(video);
			FlxG.signals.gameResized.add(onResize);
			FlxG.signals.focusGained.add(onFocusGained);
			resize();
			if (!video.load(sys.FileSystem.fullPath(filename))) {
				fail('Cannot load video: ' + filename);
				return;
			}
			// HXC VideoModule's timestamp is the elapsed song time at which the
			// event fired. PlayState passes the small event-to-frame offset here so
			// a delayed video starts on the same frame as the chart rather than
			// silently dropping the resync request.
			if (options != null && options.timestamp != null && options.timestamp > 0)
				video.time = Std.int(options.timestamp);
			if (options != null && options.mute == true)
				video.volumeAdjust = 0;
			applyZIndex();
			if (!video.play())
				fail('Cannot play video: ' + filename);
		} catch (error:Dynamic) {
			fail(Std.string(error));
		}
	}

	/** Map donor zIndex to the native display list without touching game assets. */
	function applyZIndex():Void {
		if (options == null || options.zIndex == null || FlxG.stage == null
			|| background == null || video == null)
			return;
		try {
			var count = FlxG.stage.numChildren;
			if (count <= 0)
				return;
			var target = Std.int(Math.max(0, Math.min(count - 1, options.zIndex)));
			FlxG.stage.setChildIndex(background, target);
			var videoTarget = Std.int(Math.max(0, Math.min(count - 1, target + 1)));
			FlxG.stage.setChildIndex(video, videoTarget);
		} catch (error:Dynamic) {
			trace('Video cutscene: unable to apply zIndex ' + options.zIndex + ': ' + error);
		}
	}

	function fail(message:String):Void {
		trace('Video cutscene: ' + message);
		finished = true;
	}

	function onResize(width:Int, height:Int):Void resize();

	function resize():Void {
		if (disposed || background == null) return;
		var width = FlxG.stage.stageWidth;
		var height = FlxG.stage.stageHeight;
		background.graphics.clear();
		background.graphics.beginFill(0);
		background.graphics.drawRect(0, 0, width, height);
		background.graphics.endFill();
		if (video != null && video.bitmapData != null) {
			var scale = Math.min(width / video.bitmapData.width, height / video.bitmapData.height);
			video.width = video.bitmapData.width * scale;
			video.height = video.bitmapData.height * scale;
			video.x = (width - video.width) / 2;
			video.y = (height - video.height) / 2;
		}
	}

	override public function update(elapsed:Float):Void {
		if (disposed || suspended) return;
		if (!started) {
			started = true;
			start();
		}
		if (!finished && (options == null || options.allowSkip != false)) {
			if (options != null && options.skipHoldSeconds != null && options.skipHoldSeconds > 0) {
				var pressed = options.skipPressed != null && options.skipPressed();
				if (pressed)
					skipHeldSeconds = Math.min(options.skipHoldSeconds, skipHeldSeconds + Math.max(0, elapsed));
				else if (skipHeldSeconds > 0) {
					var decay = Math.max(0, Math.min(1, elapsed * 3));
					skipHeldSeconds = Math.max(0, skipHeldSeconds + (-0.1 - skipHeldSeconds) * decay);
				}
				if (skipHeldSeconds >= options.skipHoldSeconds) skipPending = true;
			} else if (FlxG.keys.justPressed.SPACE)
				skipPending = true;
		}
		if (skipPending && !finished) {
			if (durationMs > 0) {
				skipped = true;
				finished = true;
			} else {
				// VLC can report its duration a few frames after load. Wait briefly
				// for that metadata so an immediate skip can still seek the song.
				// A malformed clip must never trap the player behind the overlay.
				skipWaitSeconds += Math.max(0, elapsed);
				if (skipWaitSeconds >= 1) {
					trace('Video cutscene: duration unavailable after skip; closing video without song seek.');
					finished = true;
				}
			}
		}
		// Dispose outside VLC callbacks, and resume only once.
		if (finished && onComplete != null) {
			var complete = onComplete;
			onComplete = null;
			complete();
		}
	}

	override public function destroy():Void {
		if (disposed) return;
		disposed = true;
		onComplete = null;
		finishCallback = null;
		onSkip = null;
		FlxG.signals.gameResized.remove(onResize);
		FlxG.signals.focusGained.remove(onFocusGained);
		if (video != null) {
			FlxG.removeChild(video);
			video.dispose();
			video = null;
		}
		if (background != null) {
			FlxG.removeChild(background);
			background = null;
		}
		super.destroy();
	}
}
#end
