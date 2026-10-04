package;

import flixel.sound.FlxSound;
import lime.utils.Int16Array;
import lime.utils.UInt8Array;

/** Source-compatible access to the PCM buffer of a currently playing sound. */
@:keep
class NightmareVisionSpectogramAudioData {
	@:keep public var snd(default, null):Dynamic;
	public var setBuffer(default, null):Bool = false;
	@:keep public var audioData:Null<Int16Array>;
	@:keep public var sampleRate:Int = 44100;
	@:keep public var numSamples:Int = 0;

	public var time(get, never):Float;
	public var length(get, never):Float;
	public var playing(get, never):Bool;

	public function new(sound:Dynamic) {
		this.snd = sound;
	}

	function get_time():Float {
		var sound = resolveSound();
		return sound == null ? 0 : sound.time;
	}

	function get_length():Float {
		if (Std.isOfType(snd, NightmareVisionAudioSoundView))
			return (cast snd:NightmareVisionAudioSoundView).length;
		var sound = resolveSound();
		return sound == null ? 0 : sound.length;
	}

	function get_playing():Bool {
		var sound = resolveSound();
		return sound != null && sound.playing;
	}

	function resolveSound():Null<FlxSound> {
		if (snd == null) return null;
		if (Std.isOfType(snd, NightmareVisionAudioSoundView))
			return (cast snd:NightmareVisionAudioSoundView).resolvePlaybackSound();
		if (Std.isOfType(snd, FlxSound)) return cast snd;
		throw '[nightmare-vision-audio] PolygonSpectogram requires a FlxSound or lazy NMV sound view';
	}

	@:keep public function checkAndSetBuffer():Void {
		if (setBuffer) return;
		var sound = resolveSound();
		if (sound == null || !sound.playing) return;

		// This follows the donor's live channel buffer path. No placeholder sound
		// or asset-side decode is created before the real FlxSound starts playing.
		@:privateAccess var channel = sound._channel;
		if (channel == null)
			throw '[nightmare-vision-audio] Playing sound has no active OpenFL channel';
		@:privateAccess var audioSource = channel.__audioSource;
		if (audioSource == null || audioSource.buffer == null)
			throw '[nightmare-vision-audio] Playing sound has no decoded audio source buffer';
		var buffer:Dynamic = audioSource.buffer;
		var bitsPerSample:Dynamic = Reflect.field(buffer, 'bitsPerSample');
		var channels:Dynamic = Reflect.field(buffer, 'channels');
		var rate:Dynamic = Reflect.field(buffer, 'sampleRate');
		if (bitsPerSample != 16 || channels != 2)
			throw '[nightmare-vision-audio] PolygonSpectogram source requires 16-bit stereo PCM; got '
				+ Std.string(bitsPerSample) + '-bit/' + Std.string(channels) + '-channel audio';
		if (rate == null || Std.int(rate) <= 0)
			throw '[nightmare-vision-audio] Playing source buffer has an invalid sample rate';
		var data:UInt8Array = cast Reflect.field(buffer, 'data');
		if (data == null)
			throw '[nightmare-vision-audio] Playing source buffer has no PCM data';
		var byteOffset = data.byteOffset;
		var byteLength = data.byteLength;
		var bytes = data.toBytes();
		if (byteOffset < 0 || byteLength <= 0 || byteOffset + byteLength > bytes.length
			|| byteOffset % Int16Array.BYTES_PER_ELEMENT != 0
			|| byteLength % Int16Array.BYTES_PER_ELEMENT != 0)
			throw '[nightmare-vision-audio] PCM data is not an aligned 16-bit sample range';

		// Lime's Uint8Array is byte-sized; this zero-copy typed view gives the
		// source algorithm the same signed 16-bit indexing used by VisShit.
		audioData = Int16Array.fromBytes(bytes, byteOffset,
			Std.int(byteLength / Int16Array.BYTES_PER_ELEMENT));
		sampleRate = Std.int(rate);
		// The source casts a byte array to Int16Array, then divides its byte count
		// by two. With an actual Int16Array view, its length already is that count.
		numSamples = audioData.length;
		setBuffer = true;
	}

	/** Drop views only; the PlayState and FlxG sound list own playback. */
	public function release():Void {
		snd = null;
		audioData = null;
		numSamples = 0;
		setBuffer = false;
	}

	static inline function boundedSampleIndex(aud:Int16Array, index:Int):Int {
		if (aud == null || aud.length < 3)
			throw '[nightmare-vision-audio] Stereo visualizer needs at least three 16-bit samples';
		// Keep the donor's stereo stride and normalization. Clamp only the final
		// pair so a section ending on the last sample cannot read beyond the view.
		return Std.int(Math.max(0, Math.min(index, aud.length - 3)));
	}

	/** Balanced stereo value for the geometry loop, without a per-sample object. */
	public static inline function getBalanced(aud:Int16Array, index:Int):Float {
		var sampleIndex = boundedSampleIndex(aud, index);
		var left = aud[sampleIndex] / 32767;
		var right = aud[sampleIndex + 2] / 32767;
		return (left + right) / 2;
	}

	public static function getCurAud(aud:Int16Array, index:Int):{var left:Float; var right:Float; var balanced:Float;} {
		var sampleIndex = boundedSampleIndex(aud, index);
		var left = aud[sampleIndex] / 32767;
		var right = aud[sampleIndex + 2] / 32767;
		var balanced = (left + right) / 2;
		return {left: left, right: right, balanced: balanced};
	}
}
