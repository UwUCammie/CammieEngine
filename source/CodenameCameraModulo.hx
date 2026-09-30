package;

typedef CodenameCameraModuloConfig = {
	var interval:Float;
	var strength:Float;
	var every:String;
	var offset:Float;
}

/** One Codename conductor segment, copied from the source Conductor's model. */
typedef CodenameCameraModuloChange = {
	var songTime:Float;
	var stepTime:Float;
	var beatTime:Float;
	var measureTime:Float;
	var bpm:Float;
	var beatsPerMeasure:Float;
	var stepsPerBeat:Float;
	var endSongTime:Float;
	var endStepTime:Float;
	var continuous:Bool;
}

/**
	Pure configuration and conductor math for Codename's Camera Modulo Change.
	The timeline accepts the same typed `{name, time, params}` events retained by
	CodenameEventMetadata, keeping camera cadence independent of the native
	engine's fixed four-step beat model.
*/
class CodenameCameraModulo {
	public static function defaults():CodenameCameraModuloConfig {
		return {interval:1, strength:1, every:'MEASURE', offset:0};
	}

	/** Codename uses a 4-beat interval on ordinary 4/4 charts, once per measure
	 * on charts that declare a different default or a time-signature event. */
	public static function songDefaults(meta:Dynamic,
		events:Array<Dynamic>):CodenameCameraModuloConfig {
		var config = defaults();
		var beatsPerMeasure = number(field(meta, 'beatsPerMeasure'), 4);
		var stepsPerBeat = number(field(meta, 'stepsPerBeat'), 4);
		var foundSignatures = beatsPerMeasure != 4 || stepsPerBeat != 4;
		if (!foundSignatures && events != null)
			for (event in events) {
				if (event == null || field(event, 'name') != 'Time Signature Change')
					continue;
				var params:Array<Dynamic> = cast field(event, 'params');
				if (params != null && (number(at(params, 0), 4) != 4
					|| number(at(params, 1), 4) != 4)) {
					foundSignatures = true;
					break;
				}
			}
		if (!foundSignatures) {
			config.interval = 4;
			config.every = 'BEAT';
		}
		return config;
	}

	/** Apply the four event slots. The last two are optional in Codename's
	 * runtime handler and preserve their previous values when absent/null. */
	public static function apply(config:CodenameCameraModuloConfig,
		params:Array<Dynamic>):CodenameCameraModuloConfig {
		if (config == null)
			config = defaults();
		if (params == null)
			return config;
		if (params.length > 0 && params[0] != null)
			config.interval = number(params[0], config.interval);
		if (params.length > 1 && params[1] != null)
			config.strength = number(params[1], config.strength);
		if (params.length > 2 && params[2] != null) {
			config.every = switch (StringTools.trim(Std.string(params[2])).toUpperCase()) {
				case 'STEP': 'STEP';
				case 'MEASURE': 'MEASURE';
				default: 'BEAT';
			};
		}
		if (params.length > 3 && params[3] != null)
			config.offset = number(params[3], config.offset);
		return config;
	}

	/** Exact Codename `Conductor.getBeats` bucketing, including its interval
	 * <= 0 branch for directly-authored charts outside the editor's range. */
	public static function bucket(axisValue:Float, interval:Float, offset:Float):Float {
		if (interval <= 0)
			return axisValue - offset;
		return Math.floor((axisValue - offset) / interval) * interval;
	}

	public static function axis(config:CodenameCameraModuloConfig,
		step:Float, beat:Float, measure:Float):Float {
		if (config == null)
			return beat;
		return switch (config.every) {
			case 'STEP': step;
			case 'MEASURE': measure;
			default: beat;
		};
	}

	/** Build the source conductor's cumulative step/beat/measure timeline. */
	public static function buildTimeline(meta:Dynamic,
		events:Array<Dynamic>):Array<CodenameCameraModuloChange> {
		var bpm = number(field(meta, 'bpm'), 100);
		var beatsPerMeasure = number(field(meta, 'beatsPerMeasure'), 4);
		var stepsPerBeat = number(field(meta, 'stepsPerBeat'), 4);
		if (bpm <= 0) bpm = 100;
		if (beatsPerMeasure <= 0) beatsPerMeasure = 4;
		if (stepsPerBeat <= 0) stepsPerBeat = 4;
		var changes:Array<CodenameCameraModuloChange> = [{
			songTime:0, stepTime:0, beatTime:0, measureTime:0,
			bpm:bpm, beatsPerMeasure:beatsPerMeasure, stepsPerBeat:stepsPerBeat,
			endSongTime:0, endStepTime:0, continuous:false
		}];
		if (events == null)
			return changes;

		var conductorEvents:Array<Dynamic> = [];
		for (event in events) {
			if (event == null)
				continue;
			var name:Dynamic = field(event, 'name');
			var time = number(field(event, 'time'), Math.NaN);
			if (Math.isNaN(time) || name == null)
				continue;
			var canonical = Std.string(name);
			if (canonical == 'BPM Change' || canonical == 'Continuous BPM Change'
				|| canonical == 'Time Signature Change')
				conductorEvents.push({name:canonical, time:time,
					params:field(event, 'params'), order:conductorEvents.length});
		}
		conductorEvents.sort(function(a:Dynamic, b:Dynamic):Int {
			if (a.time < b.time) return -1;
			if (a.time > b.time) return 1;
			if (a.name == 'Time Signature Change' && b.name != 'Time Signature Change') return -1;
			if (b.name == 'Time Signature Change' && a.name != 'Time Signature Change') return 1;
			return Std.int(a.order - b.order);
		});

		for (event in conductorEvents) {
			var current = changes[changes.length - 1];
			var time:Float = event.time;
			// Upstream rejects conductor events that land inside a continuous BPM
			// ramp. Keep the same map, rather than letting later events truncate it.
			if (current.continuous && time < current.endSongTime)
				continue;
			var params:Array<Dynamic> = cast event.params;
			switch (event.name) {
				case 'BPM Change':
					var target = number(at(params, 0), Math.NaN);
					if (validBpm(target) && target != current.bpm)
						changes.push(mapChange(current, time, target));
				case 'Time Signature Change':
					var numerator = number(at(params, 0), Math.NaN);
					var denominator = number(at(params, 1), Math.NaN);
					if (!Math.isFinite(numerator) || numerator <= 0
						|| !Math.isFinite(denominator) || denominator <= 0)
						continue;
					var signature = time == current.songTime
						? current : mapChange(current, time, current.bpm);
					if (signature != current)
						changes.push(signature);
					signature.beatsPerMeasure = numerator;
					signature.stepsPerBeat = at(params, 2) == true
						? denominator : Math.floor(16 / denominator);
					if (signature.stepsPerBeat <= 0)
						signature.stepsPerBeat = 4;
					signature.stepTime = Math.floor(signature.stepTime + 0.99998);
					signature.beatTime = Math.floor(signature.beatTime + 0.99998);
					signature.measureTime = Math.floor(signature.measureTime + 0.99998);
				case 'Continuous BPM Change':
					var target = number(at(params, 0), Math.NaN);
					var durationSteps = number(at(params, 1), Math.NaN);
					if (!validBpm(target) || target == current.bpm
						|| !Math.isFinite(durationSteps) || durationSteps <= 0)
						continue;
					var ramp = mapChange(current, time, target);
					ramp.endSongTime = time + durationSteps / (target - current.bpm)
						* Math.log(target / current.bpm) * 15000;
					ramp.endStepTime = ramp.stepTime + durationSteps;
					ramp.continuous = true;
					if (Math.isFinite(ramp.endSongTime) && ramp.endSongTime > time)
						changes.push(ramp);
			}
		}
		return changes;
	}

	/** Current continuous Codename conductor coordinates at a song timestamp. */
	public static function positionAt(changes:Array<CodenameCameraModuloChange>,
		time:Float):Dynamic {
		if (changes == null || changes.length == 0)
			return {step:0.0, beat:0.0, measure:0.0, bpm:100.0};
		var index = 0;
		for (i in 1...changes.length)
			if (changes[i].songTime <= time) index = i;
			else break;
		var change = changes[index];
		var bpm = bpmAt(changes, index, time);
		var step:Float;
		if (change.continuous && index > 0 && time > change.songTime) {
			var previousBpm = changes[index - 1].bpm;
			var logRatio = Math.log(change.bpm / previousBpm);
			if (time > change.endSongTime)
				step = change.stepTime + (((change.endSongTime - change.songTime)
					* (change.bpm - previousBpm)) / logRatio
					+ (time - change.endSongTime) * bpm) / 15000;
			else
				step = change.stepTime + (time - change.songTime)
					* (bpm - previousBpm) / logRatio / 15000;
		} else
			step = change.stepTime + (time - change.songTime) / (15000 / bpm);
		var beat = change.beatTime + (step - change.stepTime) / change.stepsPerBeat;
		var measure = change.measureTime + (beat - change.beatTime) / change.beatsPerMeasure;
		return {step:step, beat:beat, measure:measure, bpm:bpm};
	}

	public static function axisAt(changes:Array<CodenameCameraModuloChange>,
		time:Float, every:String):Float {
		var position = positionAt(changes, time);
		return switch (every) {
			case 'STEP': position.step;
			case 'MEASURE': position.measure;
			default: position.beat;
		};
	}

	static function mapChange(current:CodenameCameraModuloChange, time:Float,
		bpm:Float):CodenameCameraModuloChange {
		var startStep = current.continuous ? current.endStepTime : current.stepTime;
		var startTime = current.continuous ? current.endSongTime : current.songTime;
		var step = startStep + (time - startTime) / (15000 / current.bpm);
		var beat = current.beatTime + (step - current.stepTime) / current.stepsPerBeat;
		var measure = current.measureTime + (beat - current.beatTime) / current.beatsPerMeasure;
		return {songTime:time, stepTime:step, beatTime:beat, measureTime:measure,
			bpm:bpm, beatsPerMeasure:current.beatsPerMeasure,
			stepsPerBeat:current.stepsPerBeat, endSongTime:0, endStepTime:0,
			continuous:false};
	}

	static function bpmAt(changes:Array<CodenameCameraModuloChange>, index:Int,
		time:Float):Float {
		var change = changes[index];
		if (change.continuous && index > 0 && time < change.endSongTime) {
			var previousBpm = changes[index - 1].bpm;
			var ratio = (time - change.songTime) / (change.endSongTime - change.songTime);
			return Math.pow(previousBpm, 1 - ratio) * Math.pow(change.bpm, ratio);
		}
		return change.bpm;
	}

	static function validBpm(value:Float):Bool
		return Math.isFinite(value) && value > 0;

	static function field(value:Dynamic, name:String):Dynamic
		return value == null ? null : Reflect.field(value, name);

	static function at(values:Array<Dynamic>, index:Int):Dynamic
		return values != null && index >= 0 && index < values.length ? values[index] : null;

	static function number(value:Dynamic, fallback:Float):Float {
		if (value == null)
			return fallback;
		if (Std.isOfType(value, Int) || Std.isOfType(value, Float)) {
			var numeric:Float = cast value;
			return Math.isFinite(numeric) ? numeric : fallback;
		}
		if (Std.isOfType(value, String)) {
			var numeric = Std.parseFloat(StringTools.trim(cast value));
			return Math.isFinite(numeric) ? numeric : fallback;
		}
		return fallback;
	}
}
