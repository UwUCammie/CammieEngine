package;

import flixel.util.FlxSignal;

/**
	V-Slice's `VideoCutscene` statics for imported scripts. Playback is the
	engine's own script cutscene (`PlayState.hxcPlayImportedVideo`); the other
	calls steer the clip that call started, so a custom pause menu can pause,
	resume, restart or skip it and a song script can hide it behind a scene.
*/
@:keep
class VSliceVideoCutscene {
	public static var onVideoStarted(default, null):FlxSignal = new FlxSignal();
	public static var onVideoPaused(default, null):FlxSignal = new FlxSignal();
	public static var onVideoResumed(default, null):FlxSignal = new FlxSignal();
	public static var onVideoRestarted(default, null):FlxSignal = new FlxSignal();
	public static var onVideoEnded(default, null):FlxSignal = new FlxSignal();

	/** `cutsceneType` ENDING finishes the song after the clip; anything else starts the countdown. */
	public static function play(filename:String, ?cutsceneType:Dynamic):Void {
		var ending = cutsceneType != null && Std.string(cutsceneType).toUpperCase() == 'ENDING';
		HxcCompatRuntime.playVideoCutscene(PlayState.instance, filename, ending);
	}

	public static function isPlaying():Bool {
		var video = active();
		return video != null && !video.isFinished && !video.isPaused;
	}

	public static function pauseVideo():Void {
		var video = active();
		if (video == null || video.isPaused) return;
		video.suspend();
		onVideoPaused.dispatch();
	}

	public static function resumeVideo():Void {
		var video = active();
		if (video == null || !video.isPaused) return;
		video.resume();
		onVideoResumed.dispatch();
	}

	public static function restartVideo(resume:Bool = true):Void {
		var video = active();
		if (video == null) return;
		video.restart();
		onVideoRestarted.dispatch();
		if (resume && video.isPaused) {
			video.resume();
			onVideoResumed.dispatch();
		}
	}

	/** Skip to the end; the engine then continues exactly as when the clip ends by itself. */
	public static function finishVideo(?transitionTime:Float):Void {
		var video = active();
		if (video == null) return;
		video.finish();
		if (video.isPaused) video.resume();
	}

	public static function showVideo():Void {
		var video = active();
		if (video != null) video.setShown(true);
	}

	public static function hideVideo():Void {
		var video = active();
		if (video != null) video.setShown(false);
	}

	#if cpp
	static function active():VideoCutscene
		return PlayState.instance == null ? null : PlayState.instance.hxcActiveVideo;
	#else
	static function active():Dynamic
		return null;
	#end
}
