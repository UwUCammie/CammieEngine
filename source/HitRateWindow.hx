package;

/** The notes-per-second readout: hit times in milliseconds, newest last. */
class HitRateWindow {
	/**
		Drop hits from the newest end while they are older than the window,
		then report how many are left. Checking the newest first is how the
		readout has always behaved: it holds its count during a stream and
		empties once a full window passes without a hit.
	**/
	public static function prune(hits:Array<Float>, now:Float, windowMs:Float = 1000):Int {
		while (hits.length > 0 && hits[hits.length - 1] + windowMs < now)
			hits.pop();
		return hits.length;
	}
}
