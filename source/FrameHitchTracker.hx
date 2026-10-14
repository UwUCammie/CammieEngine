package;

/**
	Per-frame hitch bookkeeping for the smoke harness, kept free of flixel so
	it can be driven with a scripted clock.

	A frame's start-to-start gap always contains the previous frame's own
	update and draw, so reporting every long gap counted each slow frame twice
	(the second report also blamed whatever section happened to be slowest in
	the innocent next frame). Here the gap is split into the previous frame's
	update and draw, the previous OpenFL render (texture uploads, shader
	compiles, filters) and whatever is left (vsync, the OS, the collector), and
	a frame is reported once, only when one of its own parts is slow.

	hxcpp has no collection counter, but its current heap figure only ever goes
	down when a collection ran, so a drop between two samples marks one.

	hxcpp starts a collection for one of two reasons: the small-object blocks
	outgrew their target, or the large objects (over 4000 bytes) allocated since
	the last collection passed a budget of max(40 MB, the block heap). Large
	objects are almost always freed by a collection, so the large heap's growth
	between collections (a lower bound on what was allocated) tells which
	trigger fired. Big growth before a drop points at per-frame large
	allocations; small growth points at small-object churn.
**/
class FrameHitchTracker {
	public static inline var HITCH_MS:Float = 33.4;
	/** hxcpp's floor for the large-allocation budget (Immix.cpp). */
	public static inline var LARGE_BUDGET_MIN_BYTES:Float = 40 * 1024 * 1024;
	/** Samples are a frame apart, so growth just before the collection is
		missed. Count the budget as reached a little early. */
	public static inline var LARGE_BUDGET_TOLERANCE:Float = 0.9;

	/** Collections seen so far (heap drops), for the per-window heap snapshot. */
	public var suspectedCollections(default, null):Int = 0;

	/** Figures for the frame that endFrame last closed. */
	public var gapMs(default, null):Float = 0;
	public var insideMs(default, null):Float = 0;
	public var renderMs(default, null):Float = 0;
	public var outsideMs(default, null):Float = 0;
	public var collectedInside(default, null):Bool = false;
	public var collectedOutside(default, null):Bool = false;
	public var heapDropBytes(default, null):Float = 0;
	/** Harness work (log writes, probes) since the previous report, so frames
		inflated by the harness itself can be told apart from game work. */
	public var harnessMs(default, null):Float = 0;
	/** Heap growth seen between samples since the last takeAllocatedBytes. A
		lower bound on what was allocated (growth just before a collection is
		lost), but enough to tell how fast the next collection is coming. */
	public var allocatedBytes(default, null):Float = 0;
	/** Large-object heap at the last sample, or -1 when none was given. */
	public var largeBytes(default, null):Float = -1;
	/** Large heap growth from the previous collection up to the sample before
		this frame's heap drop. 0 when the frame had no drop. */
	public var largeGrowthBeforeDropBytes(default, null):Float = 0;
	/** The frame's drop came after the large heap reached hxcpp's
		large-allocation budget, so that trigger most likely fired. */
	public var largeTriggerSuspected(default, null):Bool = false;
	/** Collections so far that look large-allocation triggered. */
	public var largeTriggeredCollections(default, null):Int = 0;

	var frameOpen:Bool = false;
	var frameStart:Float = 0;
	var lastFrameStart:Float = -1;
	var lastInsideMs:Float = 0;
	var renderStart:Float = -1;
	var pendingRenderMs:Float = 0;
	var heapAtFrameStart:Float = -1;
	var heapAfterLastFrame:Float = -1;
	var pendingHarnessMs:Float = 0;
	var lastHeapSample:Float = -1;
	var largeAfterCollection:Float = -1;
	var blocksAfterCollection:Float = 0;
	/** The large baseline came from a sample right after a collection, not
		from the first sample, so growth against it is the trigger's measure. */
	var largeBaselineFromCollection:Bool = false;

	public function new() {}

	/** First update of a frame. A second update before the draw (flixel can
		step more than once per frame) stays part of the same frame. Pass a
		negative heap figure when none is available. The large-object and
		reserved figures are optional and only feed the trigger attribution. */
	public function beginFrame(now:Float, heapBytes:Float, largeHeapBytes:Float = -1,
		reservedBytes:Float = -1):Void {
		if (frameOpen)
			return;
		frameOpen = true;
		// a render window the end listener never closed must not swallow this frame
		renderStart = -1;
		gapMs = lastFrameStart < 0 ? 0 : now - lastFrameStart;
		renderMs = pendingRenderMs;
		pendingRenderMs = 0;
		outsideMs = lastFrameStart < 0 ? 0 : Math.max(0, gapMs - lastInsideMs - renderMs);
		heapDropBytes = 0;
		largeGrowthBeforeDropBytes = 0;
		largeTriggerSuspected = false;
		collectedInside = false;
		collectedOutside = heapBytes >= 0 && heapAfterLastFrame >= 0 && heapBytes < heapAfterLastFrame;
		if (collectedOutside) {
			heapDropBytes = heapAfterLastFrame - heapBytes;
			suspectedCollections++;
		}
		frameStart = now;
		lastFrameStart = now;
		heapAtFrameStart = heapBytes;
		noteHeap(heapBytes);
		noteLargeHeap(collectedOutside, largeHeapBytes, reservedBytes);
	}

	public function beginRender(now:Float):Void
		renderStart = now;

	public function endRender(now:Float):Void {
		if (renderStart < 0)
			return;
		pendingRenderMs += now - renderStart;
		renderStart = -1;
	}

	public function addHarnessTime(ms:Float):Void
		pendingHarnessMs += ms;

	/** Close the frame after its draw. Returns true when it should be reported. */
	public function endFrame(now:Float, heapBytes:Float, largeHeapBytes:Float = -1,
		reservedBytes:Float = -1):Bool {
		if (!frameOpen)
			return false;
		frameOpen = false;
		insideMs = now - frameStart;
		collectedInside = heapBytes >= 0 && heapAtFrameStart >= 0 && heapBytes < heapAtFrameStart;
		if (collectedInside) {
			heapDropBytes += heapAtFrameStart - heapBytes;
			suspectedCollections++;
		}
		heapAfterLastFrame = heapBytes;
		noteHeap(heapBytes);
		noteLargeHeap(collectedInside, largeHeapBytes, reservedBytes);
		lastInsideMs = insideMs;
		harnessMs = pendingHarnessMs;
		pendingHarnessMs = 0;
		return insideMs > HITCH_MS || renderMs > HITCH_MS || outsideMs > HITCH_MS;
	}

	/** Read and clear the allocation total, once per summary window. */
	public function takeAllocatedBytes():Float {
		var total = allocatedBytes;
		allocatedBytes = 0;
		return total;
	}

	function noteHeap(heapBytes:Float):Void {
		if (heapBytes < 0)
			return;
		if (lastHeapSample >= 0 && heapBytes > lastHeapSample)
			allocatedBytes += heapBytes - lastHeapSample;
		lastHeapSample = heapBytes;
	}

	function noteLargeHeap(collected:Bool, sample:Float, reservedBytes:Float):Void {
		if (sample < 0)
			return;
		if (collected) {
			if (largeAfterCollection >= 0 && largeBytes >= 0) {
				var growth = Math.max(0, largeBytes - largeAfterCollection);
				largeGrowthBeforeDropBytes += growth;
				var budget = Math.max(LARGE_BUDGET_MIN_BYTES, blocksAfterCollection);
				if (largeBaselineFromCollection && growth >= budget * LARGE_BUDGET_TOLERANCE) {
					largeTriggerSuspected = true;
					largeTriggeredCollections++;
				}
			}
			largeAfterCollection = sample;
			// reserved is the large heap plus every small-object block
			blocksAfterCollection = reservedBytes > sample ? reservedBytes - sample : 0;
			largeBaselineFromCollection = true;
		} else if (largeAfterCollection < 0) {
			largeAfterCollection = sample;
			blocksAfterCollection = reservedBytes > sample ? reservedBytes - sample : 0;
		}
		largeBytes = sample;
	}

	/** Which part of the reported frame was largest. */
	public function cause():String {
		if (insideMs >= renderMs && insideMs >= outsideMs)
			return 'update-draw';
		return renderMs >= outsideMs ? 'render' : 'outside';
	}
}
