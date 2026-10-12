package;

/** Completed lifecycle stages, not a guess at time remaining. */
class SongLoadingProgress {
	public static inline var TOTAL:Int = 4;
	public var completed(default, null):Int = 0;
	public var label(default, null):String = 'Preparing your track';
	public function new() {}
	public function finish(stage:Int, text:String):Void {
		if (stage <= completed || stage > TOTAL) return;
		completed = stage;
		label = text;
	}
	public function fraction():Float return completed / TOTAL;
}
