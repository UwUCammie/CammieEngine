package;

import flixel.sound.FlxSound;

/** Non-owning reference for source audio that is attached after countdown. */
@:keep
class NightmareVisionAudioSoundView {
	var soundProvider:Void->FlxSound;
	var lengthProvider:Void->Float;
	var rememberedVolume:Float = 1;
	var hasVolumeOverride:Bool = false;
	var rememberedTime:Float = 0;

	@:keep public var volume(get, set):Float;
	@:keep public var time(get, set):Float;
	@:keep public var length(get, never):Float;
	@:keep public var playing(get, never):Bool;
	@:keep public var alive(get, never):Bool;

	public function new(soundProvider:Void->FlxSound, lengthProvider:Void->Float) {
		if (soundProvider == null || lengthProvider == null)
			throw '[nightmare-vision-audio] Sound views require live source providers';
		this.soundProvider = soundProvider;
		this.lengthProvider = lengthProvider;
	}

	/** The active FlxSound is resolved lazily; no dummy sound is created. */
	@:keep public function resolvePlaybackSound():Null<FlxSound> {
		if (soundProvider == null) return null;
		return soundProvider();
	}

	function get_volume():Float {
		var sound = resolvePlaybackSound();
		return sound == null ? rememberedVolume : sound.volume;
	}

	function set_volume(value:Float):Float {
		rememberedVolume = value;
		hasVolumeOverride = true;
		var sound = resolvePlaybackSound();
		if (sound != null) sound.volume = value;
		return value;
	}

	function get_time():Float {
		var sound = resolvePlaybackSound();
		return sound == null ? rememberedTime : sound.time;
	}

	function set_time(value:Float):Float {
		rememberedTime = value;
		var sound = resolvePlaybackSound();
		if (sound != null) sound.time = value;
		return value;
	}

	function get_length():Float {
		var sound = resolvePlaybackSound();
		if (sound != null) return sound.length;
		return lengthProvider == null ? 0 : lengthProvider();
	}

	function get_playing():Bool {
		var sound = resolvePlaybackSound();
		return sound != null && sound.playing;
	}

	function get_alive():Bool return resolvePlaybackSound() != null;

	@:keep public function play(forceRestart:Bool = false, startTime:Float = 0, ?endTime:Null<Float>):Void {
		rememberedTime = startTime;
		var sound = resolvePlaybackSound();
		if (sound != null) sound.play(forceRestart, startTime, endTime);
	}

	@:keep public function pause():Void {
		var sound = resolvePlaybackSound();
		if (sound != null) sound.pause();
	}

	@:keep public function resume():Void {
		var sound = resolvePlaybackSound();
		if (sound != null) sound.resume();
	}

	@:keep public function stop():Void {
		var sound = resolvePlaybackSound();
		if (sound != null) sound.stop();
		rememberedTime = 0;
	}

	/** Apply source group volume when the instrumental FlxSound is finally made. */
	public function attachCurrentSound(sound:FlxSound):Void {
		if (sound == null) return;
		if (hasVolumeOverride) sound.volume = rememberedVolume;
		if (rememberedTime != 0) sound.time = rememberedTime;
	}

	public function release():Void {
		soundProvider = null;
		lengthProvider = null;
	}
}
