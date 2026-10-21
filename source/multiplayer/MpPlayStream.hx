package multiplayer;

/**
	The streams one online play sends (MULTIPLAYER_PROTOCOL.md section 4): the judgeable
	timeline, every key press and release, and every judgement, in the song-position
	milliseconds the judge used.

	A hit records its own backing press at the exact time it was judged, because input
	reaches PlayState by several routes (native controls, source-engine key events, input
	lines) and only the judgement knows which press it used. Once per frame the physical
	lane state is sampled: a lane that went down without a hit is a press that hit nothing,
	and a lane that is up while still marked down gets its release.
**/
class MpPlayStream {
	/** Items per message, which keeps every frame well under the server's 64 KiB limit. */
	public static inline var BATCH:Int = 1200;

	var notes:Array<Array<Float>> = [];
	var noteCount:Int = 0;
	var inputs:Array<Array<Dynamic>> = [];
	var judges:Array<Array<Dynamic>> = [];
	var down:Array<Bool> = [];
	var hitThisFrame:Array<Bool> = [];
	var sequence:Int = 0;

	public function new() {}

	/** Add a judgeable note head; returns its index in the timeline, or -1 when the lane cannot be sent. */
	public function addNote(time:Float, lane:Int, holdLength:Float):Int {
		if (lane < 0 || lane >= 32 || !Math.isFinite(time))
			return -1;
		notes.push([round(time), lane, holdLength > 0 ? round(holdLength) : 0]);
		return noteCount++;
	}

	public function totalNotes():Int
		return noteCount;

	/** The press a hit was judged on, at the song position of the judgement. */
	public function hit(lane:Int, time:Float):Void {
		if (lane < 0 || lane >= 32)
			return;
		inputs.push([round(time), lane, true]);
		down[lane] = true;
		hitThisFrame[lane] = true;
	}

	/** The physical state of one lane this frame. */
	public function sample(lane:Int, isDown:Bool, time:Float):Void {
		if (lane < 0 || lane >= 32)
			return;
		var wasDown = down[lane] == true;
		if (isDown && !wasDown) {
			if (hitThisFrame[lane] != true)
				inputs.push([round(time), lane, true]);
			down[lane] = true;
		} else if (!isDown && wasDown) {
			inputs.push([round(time), lane, false]);
			down[lane] = false;
		}
	}

	public function endFrame():Void {
		for (lane in 0...hitThisFrame.length)
			hitThisFrame[lane] = false;
	}

	/** part 0 is the head, 1 the hold end; offset is null for a miss and for a hold end. */
	public function judge(index:Int, part:Int, judgement:Int, offset:Null<Float>):Void {
		if (index < 0)
			return;
		judges.push([index, part, judgement, offset == null || judgement == 0 || part == 1 ? null : round(offset)]);
	}

	/** Everything recorded since the last call, as protocol messages. */
	public function drain():Array<Dynamic> {
		var messages:Array<Dynamic> = [];
		while (notes.length > 0)
			messages.push({t: 'notes', seq: sequence++, notes: notes.splice(0, BATCH)});
		if (inputs.length > 0) {
			// Song position can step back a little when the audio is resynced.
			inputs.sort(function(a, b) return a[0] < b[0] ? -1 : (a[0] > b[0] ? 1 : 0));
			while (inputs.length > 0)
				messages.push({t: 'input', seq: sequence++, events: inputs.splice(0, BATCH)});
		}
		while (judges.length > 0)
			messages.push({t: 'judge', seq: sequence++, items: judges.splice(0, BATCH)});
		return messages;
	}

	/** Millisecond times keep three decimals, enough for the server's 1 ms and 4 ms tolerances. */
	static inline function round(value:Float):Float
		return Math.round(value * 1000) / 1000;
}
