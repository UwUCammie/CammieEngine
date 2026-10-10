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

	/** Map BPM changes of a song, retaining source step duration for each segment. */
	public static function mapBPMChanges(song:SwagSong) {
		bpmChangeMap = [];

		var curBPM:Float = song.bpm;
		var totalSteps:Int = 0;
		var totalPos:Float = 0;
		for (i in 0...song.notes.length) {
			if(song.notes[i].changeBPM && song.notes[i].bpm != curBPM) {
				curBPM = song.notes[i].bpm;
				var event:BPMChangeEvent = {
					stepTime: totalSteps,
					songTime: totalPos,
					stepCrochet: (60 / curBPM) * 1000 / 4,
					bpm: curBPM
				};
				bpmChangeMap.push(event);
			}

			var deltaSteps:Int = song.notes[i].lengthInSteps;
			totalSteps += deltaSteps;
			totalPos += ((60 / curBPM) * 1000 / 4) * deltaSteps;
		}
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
