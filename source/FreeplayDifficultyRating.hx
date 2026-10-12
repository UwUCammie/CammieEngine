package;

typedef AuthoredDifficultyRating = {
	var difficulty:String;
	var value:Float;
	var scale:String;
}

/** Authored ratings only. Completion scores and host difficulty indexes never imply ratings. */
class FreeplayDifficultyRating {
	static function number(value:Dynamic):Null<Float> {
		if (!Std.isOfType(value, Int) && !Std.isOfType(value, Float)) return null;
		var result:Float = value;
		return Math.isFinite(result) && result >= 0 ? result : null;
	}
	static function name(value:Dynamic):String return Std.isOfType(value, String) ? StringTools.trim(cast value).toLowerCase() : '';

	/** JSON object keys are authored difficulty IDs, not positions in the host registry. */
	public static function named(values:Dynamic, scale:String):Array<AuthoredDifficultyRating> {
		var result:Array<AuthoredDifficultyRating> = [];
		if (values == null || Std.isOfType(values, Array) || Type.typeof(values) != TObject) return result;
		for (key in Reflect.fields(values)) {
			var value = number(Reflect.field(values, key));
			var difficulty = name(key);
			if (value != null && difficulty != '') result.push({difficulty:difficulty, value:value, scale:scale});
		}
		result.sort(function(a,b) return Reflect.compare(a.difficulty,b.difficulty));
		return result;
	}

	/** Copy/validate an imported descriptor list. Unknown or malformed metadata stays unknown. */
	public static function read(raw:Dynamic):Array<AuthoredDifficultyRating> {
		var result:Array<AuthoredDifficultyRating> = [];
		if (!Std.isOfType(raw, Array)) return result;
		for (entry in (cast raw:Array<Dynamic>)) {
			if (entry == null || Type.typeof(entry) != TObject) continue;
			var difficulty = name(Reflect.field(entry, 'difficulty'));
			var value = number(Reflect.field(entry, 'value'));
			var scale:Dynamic = Reflect.field(entry, 'scale');
			if (difficulty != '' && value != null && Std.isOfType(scale, String) && StringTools.trim(scale) != '')
				result.push({difficulty:difficulty, value:value, scale:StringTools.trim(scale)});
		}
		return result;
	}

	/** Converted difficulties share one authored rating table; export it without chart-file reads. */
	public static function forImport(song:Dynamic):Array<AuthoredDifficultyRating> {
		if (song == null) return [];
		var result = read(Reflect.field(song, 'authoredDifficultyRatings'));
		if (result.length > 0) return result;
		var converted:Dynamic = Reflect.field(song, 'convertedCharts');
		if (Std.isOfType(converted, Array)) for (entry in (cast converted:Array<Dynamic>)) {
			var chart = entry == null ? null : Reflect.field(entry, 'chart');
			var data = chart == null ? null : Reflect.field(chart, 'song');
			result = read(data == null ? null : Reflect.field(data, 'authoredDifficultyRatings'));
			if (result.length > 0) return result;
		}
		return [];
	}

	public static function resolve(entries:Array<AuthoredDifficultyRating>, difficulty:String):Null<AuthoredDifficultyRating> {
		var key = name(difficulty);
		var found:AuthoredDifficultyRating = null;
		if (entries != null) for (entry in entries) if (entry.difficulty == key) {
			// Case-colliding donor keys are ambiguous, including equal values on different scales.
			if (found != null) return null;
			found = entry;
		}
		return found;
	}

	public static function label(entries:Array<AuthoredDifficultyRating>, difficulty:String):String {
		var rating = resolve(entries, difficulty);
		return rating == null ? 'Difficulty rating: Unknown'
			: 'Difficulty rating: ' + rating.value + ' (' + rating.scale + ')';
	}
}
