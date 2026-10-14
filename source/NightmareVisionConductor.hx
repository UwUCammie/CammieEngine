package;

/** NMV's millisecond-based timing API over the engine's live transport.
 * The source spelling is crotchet; native charts retain their crochet API. */
@:keep
class NightmareVisionConductor {
	public var bpm(get, set):Float;
	function get_bpm():Float return Conductor.bpm;
	function set_bpm(value:Float):Float { Conductor.changeBPM(value); return value; }
	public var crotchet(get, set):Float;
	function get_crotchet():Float return Conductor.crochet;
	function set_crotchet(value:Float):Float return Conductor.crochet = value;
	public var stepCrotchet(get, set):Float;
	function get_stepCrotchet():Float return Conductor.stepCrochet;
	function set_stepCrotchet(value:Float):Float return Conductor.stepCrochet = value;
	public var songPosition(get, set):Float;
	function get_songPosition():Float return Conductor.songPosition;
	function set_songPosition(value:Float):Float return Conductor.songPosition = value;
	public var lastSongPos(get, set):Float;
	function get_lastSongPos():Float return Conductor.lastSongPos;
	function set_lastSongPos(value:Float):Float return Conductor.lastSongPos = value;
	public var offset(get, set):Float;
	function get_offset():Float return Conductor.offset;
	function set_offset(value:Float):Float return Conductor.offset = value;
	public var safeZoneOffset(get, set):Float;
	function get_safeZoneOffset():Float return Conductor.safeZoneOffset;
	function set_safeZoneOffset(value:Float):Float return Conductor.safeZoneOffset = value;
	public var bpmChangeMap(get, set):Array<Dynamic>;
	function get_bpmChangeMap():Array<Dynamic> return cast Conductor.bpmChangeMap;
	function set_bpmChangeMap(value:Array<Dynamic>):Array<Dynamic> {
		Conductor.bpmChangeMap = cast value;
		return value;
	}
	/** Historical source visual clock; reset at each gameplay owner boundary. */
	public var visualPosition:Float = 0;
	public var ROWS_PER_BEAT:Int = 48;
	public var BEATS_PER_MEASURE:Int = 4;
	public var ROWS_PER_MEASURE:Int = 192;
	public var MAX_NOTE_ROW:Int = 1 << 30;

	public function new() {}

	/** NMV retains an explicit initial tempo and per-event step durations.
	 * Populate the same live map used by native gameplay, once on chart load. */
	public static function initializeMap(initialBpm:Float):Void {
		var map:Array<Dynamic> = cast Conductor.bpmChangeMap;
		if (map.length == 0 || map[0].songTime != 0 || map[0].stepTime != 0 || map[0].bpm != initialBpm)
			map.unshift({stepTime:0, songTime:0.0, bpm:initialBpm, stepCrotchet:15000 / initialBpm});
		for (entry in map)
			if (Reflect.field(entry, 'stepCrotchet') == null)
				Reflect.setField(entry, 'stepCrotchet', 15000 / entry.bpm);
	}

	public function calculateCrochet(value:Float):Float return 60000 / value;
	public function beatToRow(beat:Float):Int return Math.round(beat * ROWS_PER_BEAT);
	public function rowToBeat(row:Int):Float return row / ROWS_PER_BEAT;
	public function beatToNoteRow(beat:Float):Int return Math.round(beat * ROWS_PER_BEAT);
	public function noteRowToBeat(row:Float):Float return row / ROWS_PER_BEAT;
	// Despite the source name, this argument uses milliseconds, like getBeat.
	public function secsToRow(time:Float):Int return Math.round(getBeat(time) * ROWS_PER_BEAT);
	public function getBPMFromSeconds(time:Float):Dynamic {
		var found:Dynamic = null;
		for (entry in bpmChangeMap) if (time >= entry.songTime) found = entry;
		return found == null ? {stepTime:0, songTime:0.0, bpm:bpm, stepCrotchet:stepCrotchet} : found;
	}
	public function getBPMFromStep(step:Float):Dynamic {
		var found:Dynamic = null;
		for (entry in bpmChangeMap) if (entry.stepTime <= step) found = entry;
		return found == null ? {stepTime:0, songTime:0.0, bpm:bpm, stepCrotchet:stepCrotchet} : found;
	}
	public function timeSinceLastBPMChange(time:Float):Float return time - getBPMFromSeconds(time).songTime;
	public function getBeatInMeasure(time:Float):Float {
		var entry = getBPMFromSeconds(time);
		return (time - entry.songTime) / (entry.stepCrotchet * 4);
	}
	// The map-aware conversions live on the base Conductor so Psych scripts get
	// the same answers; this keeps only the source instance spelling.
	public function getCrotchetAtTime(time:Float):Float return Conductor.getCrotchetAtTime(time);
	public function stepToSeconds(step:Float):Float return Conductor.stepToSeconds(step);
	public function beatToSeconds(beat:Float):Float return Conductor.beatToSeconds(beat);
	public function getStep(time:Float):Float return Conductor.getStep(time);
	public function getStepRounded(time:Float):Int return Conductor.getStepRounded(time);
	public function getBeat(time:Float):Float return Conductor.getBeat(time);
	public function getBeatRounded(time:Float):Int return Conductor.getBeatRounded(time);
	public function mapBPMChanges(song:Dynamic):Void {
		var map = bpmChangeMap;
		map.resize(0);
		// The source map starts with an explicit initial tempo entry and measures
		// sections only by sectionBeats.
		map.push({stepTime:0, songTime:0.0, bpm:song.bpm, stepCrotchet:calculateCrochet(song.bpm) / 4});
		for (change in ConductorTempoMap.tempoChanges(song, sourceSectionSteps))
			map.push({stepTime:change.stepTime, songTime:change.songTime, bpm:change.bpm, stepCrotchet:change.stepCrochet});
	}
	static function sourceSectionSteps(section:Dynamic):Int {
		var beats:Dynamic = section == null ? null : Reflect.field(section, 'sectionBeats');
		return Math.round((beats == null ? 4.0 : cast beats) * 4);
	}
}
