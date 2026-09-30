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
	public function getCrotchetAtTime(time:Float):Float return getBPMFromSeconds(time).stepCrotchet * 4;
	public function stepToSeconds(step:Float):Float {
		var entry = getBPMFromStep(step);
		return entry.songTime + (step - entry.stepTime) * entry.stepCrotchet;
	}
	public function beatToSeconds(beat:Float):Float return stepToSeconds(beat * 4);
	public function getStep(time:Float):Float {
		var entry = getBPMFromSeconds(time);
		return entry.stepTime + (time - entry.songTime) / entry.stepCrotchet;
	}
	public function getStepRounded(time:Float):Int return Math.floor(getStep(time));
	public function getBeat(time:Float):Float return getStep(time) / 4;
	public function getBeatRounded(time:Float):Int return Math.floor(getBeat(time));
	public function mapBPMChanges(song:Dynamic):Void {
		var map = bpmChangeMap;
		map.resize(0);
		map.push({stepTime:0, songTime:0.0, bpm:song.bpm, stepCrotchet:calculateCrochet(song.bpm) / 4});
		var tempo:Float = song.bpm;
		var step = 0;
		var time:Float = 0;
		for (section in (cast song.notes:Array<Dynamic>)) {
			if (section.changeBPM == true && section.bpm != tempo) {
				tempo = section.bpm;
				map.push({stepTime:step, songTime:time, bpm:tempo, stepCrotchet:calculateCrochet(tempo) / 4});
			}
			var beats:Dynamic = Reflect.field(section, 'sectionBeats');
			var delta = Math.round((beats == null ? 4.0 : cast beats) * 4);
			step += delta;
			time += calculateCrochet(tempo) / 4 * delta;
		}
	}
}
