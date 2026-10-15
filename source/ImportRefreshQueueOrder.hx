package;

/** Picks which queued retained-import refresh runs next.
 *
 * Refreshes run one at a time and each one keeps its own packages locked until
 * it finishes. Running the smallest runnable package first gets the most
 * packages playable soonest: after an importer revision bump, a multi-gigabyte
 * package that happened to sort first used to hold every smaller package in
 * the queue for many minutes. Ties keep queue order, so equal-sized packages
 * still refresh in their receipt order. */
class ImportRefreshQueueOrder {
	/** Index of the next record to start, or -1 when every record is busy. */
	public static function nextIndex<T>(queue:Array<T>, busy:T->Bool, workUnits:T->Float):Int {
		var best = -1;
		var bestUnits:Float = 0;
		if (queue == null) return best;
		for (index in 0...queue.length) {
			var record = queue[index];
			if (busy(record)) continue;
			var units = workUnits(record);
			if (best < 0 || units < bestUnits) {
				best = index;
				bestUnits = units;
			}
		}
		return best;
	}
}
