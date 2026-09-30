package;

import haxe.io.Bytes;

/**
	Accumulates PCM samples and estimates a single playback gain for one song
	asset. Analysis leaves PCM intact; applyGain returns a private scaled copy.
*/
class SongAudioLoudness {
	public static inline var BLOCK_MILLISECONDS:Float = 50.0;
	public static inline var ABSOLUTE_GATE_DBFS:Float = -60.0;
	public static inline var RELATIVE_GATE_DB:Float = -20.0;
	public static inline var TARGET_RMS_DBFS:Float = -18.0;
	public static inline var PEAK_CEILING:Float = 0.95;

	public final bitsPerSample:Int;
	public final channels:Int;
	public final sampleRate:Int;

	/** Number of PCM sample values seen, including every channel. */
	public var sampleCount(default, null):Int = 0;
	/** Highest absolute normalized PCM sample seen. */
	public var samplePeak(default, null):Float = 0;

	final bytesPerSample:Int;
	final samplesPerBlock:Int;
	final blockMeanSquares:Array<Float> = [];
	final blockSampleCounts:Array<Int> = [];
	var currentSquareSum:Float = 0;
	var currentSampleCount:Int = 0;

	/**
	 * Create an analyzer for unsigned 8-bit or signed little-endian 16-bit PCM.
	 * Other formats fail explicitly so callers can keep the feature disabled for
	 * a format the analyzer cannot measure correctly.
	 */
	public function new(bitsPerSample:Int, channels:Int, sampleRate:Int) {
		if (bitsPerSample != 8 && bitsPerSample != 16)
			throw 'SongAudioLoudness supports only 8-bit or 16-bit PCM (got ' + bitsPerSample + ').';
		if (channels <= 0)
			throw 'SongAudioLoudness requires at least one channel.';
		if (sampleRate <= 0)
			throw 'SongAudioLoudness requires a positive sample rate.';

		this.bitsPerSample = bitsPerSample;
		this.channels = channels;
		this.sampleRate = sampleRate;
		bytesPerSample = bitsPerSample >> 3;
		var framesPerBlock = Std.int(Math.max(1, Math.round(sampleRate * BLOCK_MILLISECONDS / 1000.0)));
		samplesPerBlock = framesPerBlock * channels;
	}

	/**
	 * Add one PCM chunk. Chunks may split a time block but must end on a sample
	 * boundary. The bytes use unsigned 8-bit or signed little-endian 16-bit PCM.
	 */
	public function addPcm(bytes:Bytes, offset:Int = 0, length:Int = -1):Void {
		if (bytes == null)
			throw 'SongAudioLoudness cannot analyze a null PCM chunk.';
		if (length == -1)
			length = bytes.length - offset;
		validatePcmRange(bytes, offset, length);

		var end = offset + length;
		var position = offset;
		while (position < end) {
			var sample:Float;
			if (bitsPerSample == 8) {
				// 8-bit PCM is unsigned and centered at 128.
				sample = ((bytes.get(position) & 0xFF) - 128) / 128.0;
			} else {
				var value = (bytes.get(position) & 0xFF) | ((bytes.get(position + 1) & 0xFF) << 8);
				if ((value & 0x8000) != 0)
					value -= 0x10000;
				sample = value / 32768.0;
			}
			position += bytesPerSample;

			var absolute = Math.abs(sample);
			if (absolute > samplePeak)
				samplePeak = absolute;
			sampleCount++;
			currentSquareSum += sample * sample;
			currentSampleCount++;
			if (currentSampleCount >= samplesPerBlock)
				finishBlock();
		}
	}

	/**
	 * Return a new compact PCM byte buffer with this gain applied. The source
	 * buffer remains untouched; callers can give the returned bytes to a fresh
	 * playback buffer while leaving cached assets and donor files unchanged.
	 */
	public function applyGain(bytes:Bytes, offset:Int, length:Int, gain:Float):Bytes {
		validatePcmRange(bytes, offset, length);
		if (!Math.isFinite(gain) || gain < 0)
			throw 'SongAudioLoudness gain must be finite and non-negative.';

		var scaled = Bytes.alloc(length);
		scaled.blit(0, bytes, offset, length);
		var position = 0;
		while (position < length) {
			if (bitsPerSample == 8) {
				var sample = (((scaled.get(position) & 0xFF) - 128) / 128.0) * gain;
				sample = Math.max(-1.0, Math.min(1.0, sample));
				var value = Std.int(Math.round(sample * 128.0 + 128.0));
				scaled.set(position, Std.int(Math.max(0, Math.min(255, value))));
				position++;
			} else {
				var value = (scaled.get(position) & 0xFF) | ((scaled.get(position + 1) & 0xFF) << 8);
				if ((value & 0x8000) != 0)
					value -= 0x10000;
				var sample = Math.max(-1.0, Math.min(1.0, value / 32768.0 * gain));
				var scaledValue = Std.int(Math.round(sample * 32768.0));
				scaledValue = Std.int(Math.max(-32768, Math.min(32767, scaledValue)));
				scaled.set(position, scaledValue & 0xFF);
				scaled.set(position + 1, (scaledValue >> 8) & 0xFF);
				position += 2;
			}
		}
		return scaled;
	}

	/**
	 * Return the multiplicative playback gain. Repeated calls do not change the
	 * accumulator, and later chunks can still be appended before calling again.
	 */
	public function gain():Float {
		if (sampleCount == 0 || samplePeak <= 0)
			return 1.0;

		var loudestMeanSquare:Float = currentSampleCount > 0
			? currentSquareSum / currentSampleCount : 0;
		for (meanSquare in blockMeanSquares)
			if (meanSquare > loudestMeanSquare)
				loudestMeanSquare = meanSquare;
		if (loudestMeanSquare <= 0)
			return 1.0;

		var absoluteGate = Math.pow(10, ABSOLUTE_GATE_DBFS / 20.0);
		var relativeGate = Math.sqrt(loudestMeanSquare) * Math.pow(10, RELATIVE_GATE_DB / 20.0);
		var gate = Math.max(absoluteGate, relativeGate);
		var gatedSquareSum:Float = 0;
		var gatedSampleCount:Float = 0;

		for (index in 0...blockMeanSquares.length) {
			var meanSquare = blockMeanSquares[index];
			if (Math.sqrt(meanSquare) >= gate) {
				var count = blockSampleCounts[index];
				gatedSquareSum += meanSquare * count;
				gatedSampleCount += count;
			}
		}
		if (currentSampleCount > 0
			&& Math.sqrt(currentSquareSum / currentSampleCount) >= gate) {
			gatedSquareSum += currentSquareSum;
			gatedSampleCount += currentSampleCount;
		}
		if (gatedSampleCount <= 0 || gatedSquareSum <= 0)
			return 1.0;

		var measuredRms = Math.sqrt(gatedSquareSum / gatedSampleCount);
		if (!Math.isFinite(measuredRms) || measuredRms <= 0)
			return 1.0;

		var targetRms = Math.pow(10, TARGET_RMS_DBFS / 20.0);
		var requestedGain = targetRms / measuredRms;
		var peakLimitedGain = PEAK_CEILING / samplePeak;
		return Math.min(requestedGain, peakLimitedGain);
	}

	function finishBlock():Void {
		blockMeanSquares.push(currentSquareSum / currentSampleCount);
		blockSampleCounts.push(currentSampleCount);
		currentSquareSum = 0;
		currentSampleCount = 0;
	}

	function validatePcmRange(bytes:Bytes, offset:Int, length:Int):Void {
		if (bytes == null)
			throw 'SongAudioLoudness cannot read a null PCM buffer.';
		if (offset < 0 || length < 0 || offset > bytes.length || length > bytes.length - offset)
			throw 'SongAudioLoudness PCM range is outside the byte buffer.';
		if (length % bytesPerSample != 0)
			throw 'SongAudioLoudness PCM chunks must end on a sample boundary.';
	}
}
