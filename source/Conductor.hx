package;

import Song.SwagSong;

/**
 * ...
 * @author
 */

typedef BPMChangeEvent =
{
	var stepTime:Int;
	var songTime:Float;
	var bpm:Float;
	@:optional var stepCrochet:Float;
}
/**
 * Class that handles song position and timing. 
 */
class Conductor {
	/**
	 *  Current song bpm.
	 */
	public static var bpm:Float = 100;
	/**
	 * Beats in milliseconds.
	 */
	public static var crochet:Float = ((60 / bpm) * 1000); // beats in milliseconds
	/**
	 * Steps in milliseconds.
	 */
	public static var stepCrochet:Float = crochet / 4; // steps in milliseconds
	/**
	 * Current song position
	 */
	public static var songPosition:Float = 0;
	/**
	 * Updated every update (?) song position of last update
	 */
	public static var lastSongPos:Float;
	
	public static var offset:Float = 0;
	/**
	 * Chart time minus audio time, in ms, from the song's instrumentalOffset.
	 * Positive means the chart runs ahead of the audio (silence before the
	 * music joins), negative means the audio has a lead-in the chart skips.
	 * Same sign as V-Slice's instrumental offset and Psych's song offset.
	 */
	public static var instrumentalOffset:Float = 0;
	/** Chart time for an audio position. */
	public static inline function songTimeFromAudio(audioTime:Float):Float
		return audioTime + instrumentalOffset;
	/** Audio position for a chart time. */
	public static inline function audioTimeFromSong(songTime:Float):Float
		return songTime - instrumentalOffset;
	/**
	 * Chart time the countdown has to reach before the music starts. With a
	 * positive offset the chart plays that long in silence first, unless the
	 * song is started past that point anyway.
	 */
	public static inline function songStartThreshold(startTime:Float):Float
		return instrumentalOffset > startTime ? instrumentalOffset : 0;
	/** Chart time the music is at when playback begins from `startTime`. */
	public static inline function audioStartSongTime(startTime:Float):Float
		return instrumentalOffset > startTime ? instrumentalOffset : startTime;
	/**
	 * Song clock minus audio clock in ms, the value V-Slice calls
	 * `Conductor.combinedOffset`. The song clock here is the audio time plus
	 * the instrumental offset; the player's latency offset moves note and
	 * event times instead of songPosition, so it is not part of the gap.
	 * Scripts that sync media with `songPosition - combinedOffset` therefore
	 * land on the music's real position.
	 */
	public static var combinedOffset(get, never):Float;
	static inline function get_combinedOffset():Float
		return instrumentalOffset;
	/** A chart's authored instrumental offset; anything that is not a finite number is zero. */
	public static function chartInstrumentalOffset(song:Dynamic):Float {
		if (song == null)
			return 0;
		var value:Dynamic = Reflect.field(song, 'instrumentalOffset');
		if (!Std.isOfType(value, Int) && !Std.isOfType(value, Float))
			return 0;
		var number:Float = value;
		return Math.isFinite(number) ? number : 0;
	}
	/**
	 * Time scale. Currently unused (?)
	 */
	public static var timeScale:Float = Conductor.safeZoneOffset /166;
	/**
	 * Unused (?)
	 */
	public static var safeFrames:Int = 10;
	/**
	 * unused ? 
	 */
	public static var safeZoneOffset:Float = (safeFrames / 60) * 1000; // is calculated in create(), is safeFrames in milliseconds
	/**
	 * map used during changing bpm
	 */
	public static var bpmChangeMap:Array<BPMChangeEvent> = [];

	public function new() {
	}
	/** Psych's caller-supplied rating list; judgement does not mutate the note. */
	@:keep public static function judgeNote(arr:Array<SourceRating>, diff:Float = 0):SourceRating {
		return SourceRating.judge(arr, diff);
	}
	/** Select the live source BPM segment using unadjusted song milliseconds. */
	@:keep public static function getBPMFromSeconds(time:Float):BPMChangeEvent {
		var lastChange:BPMChangeEvent = {stepTime:0, songTime:0, bpm:bpm, stepCrochet:stepCrochet};
		for (change in bpmChangeMap) if (time >= change.songTime) lastChange = change;
		return lastChange;
	}

	/** Last tempo change at or before a step, or the live tempo when there is none. */
	@:keep public static function getBPMFromStep(step:Float):BPMChangeEvent {
		var lastChange:BPMChangeEvent = {stepTime:0, songTime:0, bpm:bpm, stepCrochet:stepCrochet};
		for (change in bpmChangeMap) if (change.stepTime <= step) lastChange = change;
		return lastChange;
	}

	/** Step length of a tempo segment in either map spelling (see ConductorTempoMap). */
	public static function segmentStepCrochet(change:BPMChangeEvent, ?fallback:Float):Float {
		return ConductorTempoMap.segmentStepCrochet(change, fallback == null ? stepCrochet : fallback);
	}

	/** Psych/Nightmare Vision Conductor.getStep over the live tempo map. The
	 * optional note offset gives MusicBeatState.curDecStep. */
	@:keep public static function getStep(time:Float, noteOffset:Float = 0):Float {
		return ConductorTempoMap.stepAtTime(time, cast bpmChangeMap, stepCrochet, noteOffset);
	}

	/** Whole step for a song time. Psych 1.0.4's own version floors only part
	 * of the sum; this is the whole-step value both donors' callers expect. */
	@:keep public static function getStepRounded(time:Float):Int {
		return Math.floor(getStep(time));
	}

	@:keep public static function getBeat(time:Float, noteOffset:Float = 0):Float {
		return getStep(time, noteOffset) / 4;
	}

	@:keep public static function getBeatRounded(time:Float):Int {
		return Math.floor(getBeat(time));
	}

	/** Song milliseconds at a step, across tempo changes. */
	@:keep public static function stepToSeconds(step:Float):Float {
		var change = getBPMFromStep(step);
		return change.songTime + (step - change.stepTime) * segmentStepCrochet(change);
	}

	@:keep public static function beatToSeconds(beat:Float):Float {
		return stepToSeconds(beat * 4);
	}

	/** Beat length in ms at a song time (the donors spell it crotchet). */
	@:keep public static function getCrotchetAtTime(time:Float):Float {
		return segmentStepCrochet(getBPMFromSeconds(time)) * 4;
	}

	@:keep public static function getCrochetAtTime(time:Float):Float {
		return getCrotchetAtTime(time);
	}

	@:keep public static function calculateCrochet(bpm:Float):Float {
		return (60 / bpm) * 1000;
	}

	/** Map BPM changes of a song, retaining source step duration for each segment. */
	public static function mapBPMChanges(song:SwagSong) {
		// Native charts carry lengthInSteps; Psych and Nightmare Vision charts
		// may only carry sectionBeats, which used to count as zero steps here.
		bpmChangeMap = cast ConductorTempoMap.tempoChanges(song, EditorSectionLengthCompat.steps);
		trace("new BPM map BUDDY " + bpmChangeMap);
	}
	/**
	 * Change bpm. also updated crochet. 
	 * @param newBpm New bpm.
	 */
	public static function changeBPM(newBpm:Float) {
		bpm = newBpm;

		crochet = ((60 / bpm) * 1000);
		stepCrochet = crochet / 4;
	}

	public static function beatsToTime(beats:Float, ?daBPM:Float):Float {
		if (daBPM == null) daBPM = bpm;
		var dacrochet = ((60 / daBPM) * 1000);

		return dacrochet*beats;
	}
	public static function stepsToTime(steps:Float, ?daBPM:Float):Float {
		if (daBPM == null) daBPM = bpm;
		var dacrochet = ((60 / daBPM) * 250);

		return dacrochet*steps;
	}
	public static function timeToBeats(time:Float, round:Bool = true, ?daBPM:Float):Float {
		if (daBPM == null) daBPM = bpm;
		var dacrochet = ((60 / daBPM) * 1000);

		var joesph = time/dacrochet;
		if (round) joesph = Math.round(joesph);

		return joesph;
	}
	public static function timeToSteps(time:Float, round:Bool = true, ?daBPM:Float):Float {
		if (daBPM == null) daBPM = bpm;
		var dacrochet = ((60 / daBPM) * 250);

		var stephanie = time/dacrochet;
		if (round) stephanie = Math.round(stephanie);

		return stephanie;
	}
}
