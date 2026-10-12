package;

import FreeplayDifficultyRating.AuthoredDifficultyRating;

typedef LibraryMetricValue = {var value:Float; var scale:String;}

/** Named comparison difficulty is independent of the currently selected launch difficulty. */
class LibraryChartMetric {
	public static function isScore(mode:String):Bool return mode == 'scoreHigh' || mode == 'scoreLow';
	public static function isRating(mode:String):Bool return mode == 'ratingHigh' || mode == 'ratingLow';
	public static function active(mode:String):Bool return isScore(mode) || isRating(mode);
	public static function difficultyIndex(difficulty:String, names:Array<String>):Int {
		var found = -1;
		for (i in 0...names.length) if (names[i].toLowerCase() == difficulty.toLowerCase()) {
			if (found >= 0) return -1;
			found = i;
		}
		return found;
	}
	public static function read(song:String, ratings:Array<AuthoredDifficultyRating>, mode:String,
		difficulty:String, index:Int, supported:Array<Int>, score:(String, Int)->Null<Int>):Null<LibraryMetricValue> {
		if (index < 0 || supported == null || supported.indexOf(index) < 0) return null;
		if (isScore(mode)) {
			var value = score(song, index);
			return value == null ? null : {value:value, scale:'Host score'};
		}
		if (isRating(mode)) {
			var rating = FreeplayDifficultyRating.resolve(ratings, difficulty);
			return rating == null ? null : {value:rating.value, scale:rating.scale};
		}
		return null;
	}
	public static function compare(a:Null<LibraryMetricValue>, b:Null<LibraryMetricValue>, descending:Bool):Int {
		if (a == null) return b == null ? 0 : 1;
		if (b == null) return -1;
		// Scales form deterministic blocks. Their numbers are never compared to one another.
		var scale = Reflect.compare(a.scale, b.scale);
		if (scale != 0) return scale;
		return descending ? Reflect.compare(b.value, a.value) : Reflect.compare(a.value, b.value);
	}
	public static function label(value:Null<LibraryMetricValue>, difficulty:String):String {
		return 'Sort (' + difficulty + '): ' + (value == null ? 'Unknown' : value.value + ' (' + value.scale + ')');
	}
}
