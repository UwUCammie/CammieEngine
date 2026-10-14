package nightmarevision.modchart;

/** Immutable values read from the active PlayState by the pure evaluator. */
class NightmareVisionModchartContext {
	public final width:Float;
	public final height:Float;
	public final keys:Int;
	public final noteWidth:Float;
	public final songPosition:Float;
	public final beat:Float;
	public final songSpeed:Float;
	public final crotchet:Float;
	public final downScroll:Bool;
	public final lowQuality:Bool;
	public final legacyCoordinates:Bool;
	public final songBpm:Float;

	public function new(width:Float, height:Float, keys:Int, noteWidth:Float,
		songPosition:Float = 0, beat:Float = 0, songSpeed:Float = 1,
		crotchet:Float = 500, downScroll:Bool = false, lowQuality:Bool = false, legacyCoordinates:Bool = false, songBpm:Float = 120) {
		this.width = width;
		this.height = height;
		this.keys = keys < 1 ? 1 : keys;
		this.noteWidth = noteWidth;
		this.songPosition = songPosition;
		this.beat = beat;
		this.songSpeed = songSpeed;
		this.crotchet = crotchet;
		this.downScroll = downScroll;
		this.lowQuality = lowQuality;
		this.legacyCoordinates = legacyCoordinates;
		this.songBpm = songBpm;
	}

	/**
		`previous` when it already holds exactly these values, otherwise a new
		context. The values only change once per frame, but every modifier asks
		for a context for every note, so building a fresh one each time made
		hundreds of throwaway objects per frame. The context is immutable, so
		handing the same one out again cannot change what a caller sees.
	**/
	public static function reuse(previous:Null<NightmareVisionModchartContext>, width:Float, height:Float, keys:Int,
		noteWidth:Float, songPosition:Float = 0, beat:Float = 0, songSpeed:Float = 1, crotchet:Float = 500,
		downScroll:Bool = false, lowQuality:Bool = false, legacyCoordinates:Bool = false,
		songBpm:Float = 120):NightmareVisionModchartContext {
		if (previous != null && previous.width == width && previous.height == height
			&& previous.keys == (keys < 1 ? 1 : keys) && previous.noteWidth == noteWidth
			&& previous.songPosition == songPosition && previous.beat == beat
			&& previous.songSpeed == songSpeed && previous.crotchet == crotchet
			&& previous.downScroll == downScroll && previous.lowQuality == lowQuality
			&& previous.legacyCoordinates == legacyCoordinates && previous.songBpm == songBpm)
			return previous;
		return new NightmareVisionModchartContext(width, height, keys, noteWidth, songPosition, beat, songSpeed,
			crotchet, downScroll, lowQuality, legacyCoordinates, songBpm);
	}
}
