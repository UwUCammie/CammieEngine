package;

/** One host update's fixed-rate compatibility script callbacks.
 * The same batch is consumed before and after native PlayState work so the
 * source onUpdate/onUpdatePost phases receive matching counts and deltas. */
class CompatScriptTickBatch {
	public final tickCount:Int;
	public final tickElapsed:Float;
	var didUpdate:Bool = false;
	var didUpdatePost:Bool = false;

	public function new(tickCount:Int, tickElapsed:Float) {
		this.tickCount = tickCount < 0 ? 0 : tickCount;
		this.tickElapsed = tickElapsed;
	}

	/** Dispatch the pre-native phase once, preserving tick index for input snapshots. */
	public function dispatchUpdate(callback:Int->Float->Void):Void {
		if (didUpdate)
			throw '[compat-script-clock] onUpdate batch was already dispatched';
		didUpdate = true;
		if (callback == null) return;
		for (index in 0...tickCount)
			callback(index, tickElapsed);
	}

	/** Dispatch the post-native phase with exactly the same indices and delta. */
	public function dispatchUpdatePost(callback:Int->Float->Void):Void {
		if (!didUpdate)
			throw '[compat-script-clock] onUpdatePost cannot precede onUpdate';
		if (didUpdatePost)
			throw '[compat-script-clock] onUpdatePost batch was already dispatched';
		didUpdatePost = true;
		if (callback == null) return;
		for (index in 0...tickCount)
			callback(index, tickElapsed);
	}
}
