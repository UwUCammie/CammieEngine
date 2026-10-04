package;

/** Keeps a bounded rolling average of frame times over the last five seconds. */
class AverageFrameRate {
	public static inline var WINDOW_MS:Float = 5000;
	public static inline var REFRESH_INTERVAL_MS:Float = 500;
	public static inline var BUCKET_MS:Float = 1;
	public static inline var BUCKET_COUNT:Int = 5002;

	public var currentFPS(default, null):Int = 0;
	public var sampleCount(get, never):Int;
	var bucketKeys:Array<Float> = [];
	var bucketSampleCounts:Array<Int> = [];
	var totalSamples:Int = 0;
	var elapsedTimeMS:Float = 0;
	var lastPrunedThroughBucket:Float = Math.NaN;
	var nextRefreshAtMS:Float = REFRESH_INTERVAL_MS;

	public function new() {
		for (i in 0...BUCKET_COUNT) {
			bucketKeys.push(Math.NaN);
			bucketSampleCounts.push(0);
		}
	}

	/**
	 * Records one frame interval. Zero is valid when the clock repeats a
	 * timestamp; that frame still counts even though it adds no elapsed time.
	 * Returns true when the display average was refreshed, at most once per
	 * half second.
	 */
	public function addFrameTime(deltaTimeMS:Float):Bool {
		if (!Math.isFinite(deltaTimeMS) || deltaTimeMS < 0)
			return false;

		var nextElapsedTimeMS = elapsedTimeMS + deltaTimeMS;
		if (!Math.isFinite(nextElapsedTimeMS))
			return false;
		elapsedTimeMS = nextElapsedTimeMS;

		var bucketKey = Math.floor(elapsedTimeMS / BUCKET_MS);
		pruneExpiredBuckets(bucketKey);

		var bucketIndex = getBucketIndex(bucketKey);
		if (bucketKeys[bucketIndex] != bucketKey) {
			removeBucket(bucketIndex);
			bucketKeys[bucketIndex] = bucketKey;
		}

		bucketSampleCounts[bucketIndex]++;
		totalSamples++;

		if (elapsedTimeMS < nextRefreshAtMS)
			return false;

		refreshAverage();
		nextRefreshAtMS = elapsedTimeMS + REFRESH_INTERVAL_MS;
		return true;
	}

	function pruneExpiredBuckets(currentBucket:Float):Void {
		var pruneThroughBucket = currentBucket - Std.int(WINDOW_MS / BUCKET_MS) - 1;
		if (!Math.isFinite(lastPrunedThroughBucket)) {
			lastPrunedThroughBucket = pruneThroughBucket;
			return;
		}

		var bucketsToPrune = pruneThroughBucket - lastPrunedThroughBucket;
		if (bucketsToPrune <= 0)
			return;

		// A long pause can skip many buckets. Once the gap reaches the entire
		// ring, every stored sample is outside the rolling window.
		if (bucketsToPrune >= BUCKET_COUNT) {
			clearBuckets();
			lastPrunedThroughBucket = pruneThroughBucket;
			return;
		}

		var count = Std.int(bucketsToPrune);
		for (offset in 1...(count + 1)) {
			var expiredBucket = lastPrunedThroughBucket + offset;
			var bucketIndex = getBucketIndex(expiredBucket);
			if (bucketKeys[bucketIndex] == expiredBucket)
				removeBucket(bucketIndex);
		}
		lastPrunedThroughBucket = pruneThroughBucket;
	}

	function getBucketIndex(bucketKey:Float):Int {
		var wrapped:Float = bucketKey - Math.floor(bucketKey / BUCKET_COUNT) * BUCKET_COUNT;
		if (wrapped < 0)
			wrapped += BUCKET_COUNT;
		return Std.int(wrapped);
	}

	function removeBucket(bucketIndex:Int):Void {
		if (Math.isFinite(bucketKeys[bucketIndex]))
			totalSamples -= bucketSampleCounts[bucketIndex];
		bucketKeys[bucketIndex] = Math.NaN;
		bucketSampleCounts[bucketIndex] = 0;
		if (totalSamples < 0)
			totalSamples = 0;
	}

	function clearBuckets():Void {
		for (i in 0...BUCKET_COUNT) {
			bucketKeys[i] = Math.NaN;
			bucketSampleCounts[i] = 0;
		}
		totalSamples = 0;
	}

	function refreshAverage():Void {
		var observationDurationMS = Math.min(elapsedTimeMS, WINDOW_MS);
		if (totalSamples == 0 || observationDurationMS <= 0)
			currentFPS = 0;
		else
			currentFPS = Std.int(Math.round(totalSamples * 1000 / observationDurationMS));
	}

	function get_sampleCount():Int
		return totalSamples;
}
