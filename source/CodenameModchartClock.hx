package;

/** Song-time conversion shared by the standalone modchart adapter. */
class CodenameModchartClock {
	/** The adapter interface calls this a step, but the backend passes song time in ms. */
	public static function beatAtTime(songTime:Float, initialBpm:Float, changes:Array<Dynamic>):Float {
		var segment = segmentAtTime(songTime, initialBpm, changes);
		return segment.beat + ((songTime - segment.time) * segment.bpm / 60000);
	}

	public static function bpmAtTime(songTime:Float, initialBpm:Float, changes:Array<Dynamic>):Float {
		return segmentAtTime(songTime, initialBpm, changes).bpm;
	}

	public static function crochetAtTime(songTime:Float, initialBpm:Float, changes:Array<Dynamic>):Float {
		return 60000 / bpmAtTime(songTime, initialBpm, changes);
	}

	static function segmentAtTime(songTime:Float, initialBpm:Float, changes:Array<Dynamic>):{time:Float, beat:Float, bpm:Float} {
		if (!Math.isFinite(songTime) || !validBpm(initialBpm))
			throw '[funkin-modchart-clock] invalid song time or initial BPM';

		var result = {time:0.0, beat:0.0, bpm:initialBpm};
		var previousTime = Math.NEGATIVE_INFINITY;
		if (changes == null)
			return result;

		for (change in changes) {
			if (change == null)
				throw '[funkin-modchart-clock] null BPM change in map';
			var changeTime:Float = fieldFloat(change, 'songTime');
			var changeStep:Float = fieldFloat(change, 'stepTime');
			var changeBpm:Float = fieldFloat(change, 'bpm');
			if (!Math.isFinite(changeTime) || !Math.isFinite(changeStep) || !validBpm(changeBpm)
				|| changeTime < previousTime)
				throw '[funkin-modchart-clock] malformed or unsorted BPM map';
			previousTime = changeTime;
			if (changeTime > songTime)
				break;
			result = {time:changeTime, beat:changeStep / 4, bpm:changeBpm};
		}
		return result;
	}

	static function fieldFloat(value:Dynamic, name:String):Float {
		var field:Dynamic = Reflect.field(value, name);
		if (!Std.isOfType(field, Float) && !Std.isOfType(field, Int))
			return Math.NaN;
		return field;
	}

	static inline function validBpm(value:Float):Bool
		return Math.isFinite(value) && value > 0;
}
