package;

/** A minimal listener list with the add/remove/dispatch shape of FlxSignal.
 * Kept free of flixel so the timeline stays usable from plain data code. */
class TimelineSignal {
	var listeners:Array<Void->Void> = [];
	var onceListeners:Array<Void->Void> = [];

	public function new() {}

	public function add(listener:Void->Void):Void {
		if (listener != null && !has(listener))
			listeners.push(listener);
	}

	public function addOnce(listener:Void->Void):Void {
		if (listener != null && !has(listener))
			onceListeners.push(listener);
	}

	public function remove(listener:Void->Void):Void {
		// Script closures are compared as methods, not by identity.
		listeners = [for (current in listeners) if (!Reflect.compareMethods(current, listener)) current];
		onceListeners = [for (current in onceListeners) if (!Reflect.compareMethods(current, listener)) current];
	}

	public function removeAll():Void {
		listeners = [];
		onceListeners = [];
	}

	public function has(listener:Void->Void):Bool {
		for (current in listeners)
			if (Reflect.compareMethods(current, listener))
				return true;
		for (current in onceListeners)
			if (Reflect.compareMethods(current, listener))
				return true;
		return false;
	}

	public function dispatch():Void {
		// Copies let a listener add or remove listeners while being called.
		var once = onceListeners;
		onceListeners = [];
		for (listener in listeners.copy())
			listener();
		for (listener in once)
			listener();
	}
}

/**
	An independent beat clock built from a list of tempo changes.

	The song's own timing lives in the static Conductor. Cutscenes and menus
	sometimes need a second clock that follows another sound (intro music, a
	video), so this one is a plain object: map the tempo changes, call update
	with that sound's time, and it reports the current step, beat and measure
	and fires its signals when they change. Time changes are accepted in both
	the stored chart form (`t`, `bpm`, `n`, `d`) and the long form
	(`timeStamp`, `timeSignatureNum`, `timeSignatureDen`).
**/
class ConductorTimeline {
	static inline var STEPS_PER_BEAT:Int = 4;

	public var onStepHit(default, null):TimelineSignal = new TimelineSignal();
	public var onBeatHit(default, null):TimelineSignal = new TimelineSignal();
	public var onMeasureHit(default, null):TimelineSignal = new TimelineSignal();

	public var songPosition(default, null):Float = 0;
	public var currentStep(default, null):Int = 0;
	public var currentBeat(default, null):Int = 0;
	public var currentMeasure(default, null):Int = 0;
	public var currentStepTime(default, null):Float = 0;
	public var currentBeatTime(default, null):Float = 0;
	public var currentMeasureTime(default, null):Float = 0;

	public var bpm(get, never):Float;
	public var beatLengthMs(get, never):Float;
	public var stepLengthMs(get, never):Float;
	public var measureLengthMs(get, never):Float;
	public var timeSignatureNumerator(get, never):Int;
	public var timeSignatureDenominator(get, never):Int;

	/** Sorted changes: start time, beat at that time, tempo and signature. */
	var changes:Array<{time:Float, beat:Float, bpm:Float, numerator:Int, denominator:Int}> = [];
	var current:{time:Float, beat:Float, bpm:Float, numerator:Int, denominator:Int} = null;
	var bpmOverride:Null<Float> = null;

	public function new() {}

	/** Replace the tempo map. Unreadable entries are skipped. */
	public function mapTimeChanges(timeChanges:Dynamic):Void {
		changes = [];
		if (timeChanges != null && Std.isOfType(timeChanges, Array)) {
			var parsed = [];
			for (raw in (cast timeChanges:Array<Dynamic>)) {
				if (raw == null)
					continue;
				var tempo = number(raw, ['bpm'], 0);
				if (!(tempo > 0))
					continue;
				var time = number(raw, ['t', 'timeStamp'], 0);
				parsed.push({time: time < 0 ? 0.0 : time, beat: 0.0, bpm: tempo,
					numerator: Std.int(Math.max(1, number(raw, ['n', 'timeSignatureNum'], 4))),
					denominator: Std.int(Math.max(1, number(raw, ['d', 'timeSignatureDen'], 4)))});
			}
			parsed.sort(function(a, b) return a.time < b.time ? -1 : (a.time > b.time ? 1 : 0));
			for (change in parsed) {
				if (changes.length > 0 && change.time > 0) {
					var previous = changes[changes.length - 1];
					change.beat = previous.beat + (change.time - previous.time) * previous.bpm / 60000
						* (previous.denominator / 4);
				}
				changes.push(change);
			}
		}
		refresh(songPosition, false);
	}

	/** Force one tempo, or pass null to go back to the mapped changes. */
	public function forceBPM(?value:Float):Void {
		bpmOverride = value != null && value > 0 ? value : null;
	}

	/** Move the clock to `position` (milliseconds) and fire changed signals.
	 * A missing position, such as the time of a sound that was never loaded,
	 * leaves the clock where it is. */
	public function update(?position:Dynamic, ?applyOffsets:Bool = true, ?forceDispatch:Bool = false):Void {
		if (position == null)
			return;
		var value:Float = Std.isOfType(position, Float) || Std.isOfType(position, Int)
			? position : Std.parseFloat(Std.string(position));
		if (Math.isNaN(value))
			return;
		refresh(value, true, forceDispatch == true);
	}

	public function getTimeInSteps(ms:Float):Float {
		var change = changeAt(ms);
		if (change == null)
			return ms / stepLengthMs;
		return change.beat * STEPS_PER_BEAT + (Math.max(ms, 0) - change.time) / stepLength(change);
	}

	public function getStepTimeInMs(stepTime:Float):Float {
		if (changes.length == 0 || bpmOverride != null)
			return stepTime * stepLengthMs;
		var change = changes[0];
		for (candidate in changes)
			if (candidate.beat * STEPS_PER_BEAT <= stepTime)
				change = candidate;
		return change.time + (stepTime - change.beat * STEPS_PER_BEAT) * stepLength(change);
	}

	public function getBeatTimeInMs(beatTime:Float):Float
		return getStepTimeInMs(beatTime * STEPS_PER_BEAT);

	function refresh(position:Float, dispatch:Bool, force:Bool = false):Void {
		var oldStep = currentStep;
		var oldBeat = currentBeat;
		var oldMeasure = currentMeasure;
		songPosition = position;
		current = changeAt(position);
		currentStepTime = round(getTimeInSteps(position));
		currentBeatTime = currentStepTime / STEPS_PER_BEAT;
		var stepsPerMeasure = (current == null ? 4 : current.numerator) * STEPS_PER_BEAT;
		currentMeasureTime = currentStepTime / stepsPerMeasure;
		currentStep = Math.floor(currentStepTime);
		currentBeat = Math.floor(currentBeatTime);
		currentMeasure = Math.floor(currentMeasureTime);
		if (!dispatch)
			return;
		if (force || currentStep != oldStep)
			onStepHit.dispatch();
		if (force || currentBeat != oldBeat)
			onBeatHit.dispatch();
		if (force || currentMeasure != oldMeasure)
			onMeasureHit.dispatch();
	}

	function changeAt(ms:Float) {
		if (bpmOverride != null || changes.length == 0)
			return null;
		var result = changes[0];
		for (change in changes) {
			if (ms < change.time)
				break;
			result = change;
		}
		return result;
	}

	function stepLength(change:{time:Float, beat:Float, bpm:Float, numerator:Int, denominator:Int}):Float
		return 60000 / change.bpm * (4 / change.denominator) / STEPS_PER_BEAT;

	function get_bpm():Float {
		if (bpmOverride != null)
			return bpmOverride;
		var change = current != null ? current : (changes.length > 0 ? changes[0] : null);
		return change == null ? 100 : change.bpm;
	}

	function get_timeSignatureNumerator():Int
		return current == null ? 4 : current.numerator;

	function get_timeSignatureDenominator():Int
		return current == null ? 4 : current.denominator;

	function get_beatLengthMs():Float
		return 60000 / bpm * (4 / timeSignatureDenominator);

	function get_stepLengthMs():Float
		return beatLengthMs / STEPS_PER_BEAT;

	function get_measureLengthMs():Float
		return beatLengthMs * timeSignatureNumerator;

	static function round(value:Float):Float
		return Math.round(value * 1000000) / 1000000;

	static function number(source:Dynamic, fields:Array<String>, fallback:Float):Float {
		for (name in fields) {
			var value:Dynamic = Reflect.field(source, name);
			if (value == null)
				continue;
			var parsed:Float = Std.isOfType(value, Float) || Std.isOfType(value, Int)
				? value : Std.parseFloat(Std.string(value));
			if (!Math.isNaN(parsed))
				return parsed;
		}
		return fallback;
	}
}
