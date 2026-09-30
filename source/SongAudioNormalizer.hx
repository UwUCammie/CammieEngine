package;

import openfl.media.Sound;

/** Analyze once on load. Cache scalars, never audio buffers or playback objects. */
@:access(openfl.media.Sound)
class SongAudioNormalizer {
	static var gains:Map<String, {stamp:String, gain:Float}> = [];

	public static function prepare(sound:Sound, path:String, enabled:Bool):Sound {
		if (!enabled || sound == null) return sound;
		#if (sys && lime)
		try {
			var resolved = FNFAssets.resolveCaseInsensitivePath(path);
			var key = resolved != null ? sys.FileSystem.fullPath(resolved) : null;
			var stamp:String = null;
			var cachedGain:Null<Float> = null;
			if (key != null) {
				var stat = sys.FileSystem.stat(key);
				stamp = stat.size + ':' + stat.mtime.getTime() + ':' + stat.ctime.getTime();
				var cached = gains.get(key);
				if (cached != null && cached.stamp == stamp)
					cachedGain = cached.gain;
			}
			var buffer = sound.__buffer;
			if (buffer == null) throw 'No decoded audio buffer';
			if (buffer.data == null || buffer.data.byteLength == 0)
				throw 'Decoded PCM unavailable (streaming sounds are not analyzed)';
			var analyzer = new SongAudioLoudness(buffer.bitsPerSample, buffer.channels, buffer.sampleRate);
			var gain:Float;
			if (cachedGain != null) gain = cachedGain;
			else {
				analyzer.addPcm(buffer.data.toBytes(), buffer.data.byteOffset, buffer.data.byteLength);
				gain = analyzer.gain();
				if (key != null) gains.set(key, {stamp:stamp, gain:gain});
			}
			if (gain == 1) return sound;
			// The backend may clamp playback gain above one. Apply the fixed
			// gain to a private PCM buffer instead, leaving cached assets, files,
			// script volumes, fades and miss muting untouched.
			var output = new lime.media.AudioBuffer();
			output.bitsPerSample = buffer.bitsPerSample;
			output.channels = buffer.channels;
			output.sampleRate = buffer.sampleRate;
			output.data = lime.utils.UInt8Array.fromBytes(analyzer.applyGain(
				buffer.data.toBytes(), buffer.data.byteOffset, buffer.data.byteLength, gain));
			return Sound.fromAudioBuffer(output);
		} catch (error:Dynamic) {
			trace('[song-audio-normalization] Could not analyze ' + path + ': ' + error);
		}
		#else
		trace('[song-audio-normalization] PCM analysis is unavailable on this target');
		#end
		return sound;
	}
}
