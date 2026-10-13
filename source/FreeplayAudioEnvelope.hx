package;

import flixel.sound.FlxSound;
import lime.utils.Int16Array;
import lime.utils.UInt8Array;

/** Bounded waveform envelope from the playing preview PCM, independent of output volume. */
class FreeplayAudioEnvelope {
	public var levels(default, null):Array<Float> = [for (i in 0...12) 0.0];
	var sound:FlxSound;
	var data:Int16Array;
	var channels:Int = 0;
	var rate:Int = 0;
	var clock:Float = 0;
	public function new() {}
	public function update(next:FlxSound, elapsed:Float):Void {
		if (next != sound) { sound = next; data = null; channels = 0; clock = 0; }
		clock -= elapsed;
		if (clock > 0) return;
		clock = 1 / 30;
		if (sound == null || !sound.playing) { for (i in 0...levels.length) levels[i] = 0; return; }
		#if (cpp || hl)
		if (data == null) {
			@:privateAccess var channel = sound._channel;
			@:privateAccess var source = channel == null ? null : channel.__audioSource;
			var buffer = source == null ? null : source.buffer;
			if (buffer != null && buffer.bitsPerSample == 16 && buffer.channels > 0 && buffer.sampleRate > 0) {
				var bytes:UInt8Array = buffer.data;
				if (bytes != null && bytes.byteOffset % 2 == 0 && bytes.byteLength % 2 == 0) {
					data = Int16Array.fromBytes(bytes.toBytes(), bytes.byteOffset, Std.int(bytes.byteLength / 2));
					channels = buffer.channels; rate = buffer.sampleRate;
				}
			}
		}
		#end
		if (data == null) {
			var amplitude = sound.amplitude;
			for (i in 0...levels.length) levels[i] = Math.isFinite(amplitude) ? amplitude : 0;
			return;
		}
		var start = Std.int(sound.time / 1000 * rate);
		for (bar in 0...levels.length) {
			var peak = 0.0;
			for (sample in 0...32) {
				var index = (start + bar * 32 + sample) * channels;
				for (channel in 0...channels) if (index + channel >= 0 && index + channel < data.length)
					peak = Math.max(peak, Math.abs(data[index + channel] / 32768));
			}
			levels[bar] = peak;
		}
	}
}
