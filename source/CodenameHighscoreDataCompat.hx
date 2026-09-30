package;

/** Pure value rules for Codename's song score records. Kept separate from
 * FlxSave so compatibility behavior can be verified without touching a user's
 * live save file. */
class CodenameHighscoreDataCompat {
	public static function key(song:String, difficulty:String, variation:String,
		changes:Array<Dynamic>):String {
		var songKey = song == null ? '' : StringTools.trim(song).toLowerCase();
		var diffKey = difficulty == null ? '' : StringTools.trim(difficulty).toLowerCase();
		var variantKey = variation == null ? '' : StringTools.trim(variation);
		var changeKeys:Array<String> = [];
		if (changes != null) for (change in changes) {
			var value = changeName(change);
			if (value != '') changeKeys.push(value);
		}
		// Keep existing base-mode records readable while keeping variants and
		// opponent/co-op modes in distinct entries.
		if (variantKey == '' && changeKeys.length == 0) return songKey + '|' + diffKey;
		return songKey + '|' + diffKey + '|' + haxe.Json.stringify([variantKey, changeKeys]);
	}

	static function changeName(value:Dynamic):String {
		if (value == null) return '';
		if (Std.isOfType(value, String)) return StringTools.trim(cast value);
		var tag:Dynamic = Reflect.field(value, 'tag');
		if (tag != null) return Std.string(tag);
		return Std.string(value);
	}

	public static function emptyRecord():Dynamic
		return {score:0, accuracy:0.0, misses:0, hits:[], date:null};

	/** Codename replaces a record when forced, when no prior date exists, or
		when the new score is strictly higher. */
	public static function shouldReplace(previous:Dynamic, next:Dynamic, force:Bool = false):Bool {
		if (next == null) return false;
		if (force || previous == null || Reflect.field(previous, 'date') == null) return true;
		var oldScore:Dynamic = Reflect.field(previous, 'score');
		var newScore:Dynamic = Reflect.field(next, 'score');
		var oldValue:Float = oldScore == null ? 0 : Std.parseFloat(Std.string(oldScore));
		var newValue:Float = newScore == null ? 0 : Std.parseFloat(Std.string(newScore));
		if (!Math.isFinite(oldValue)) oldValue = 0;
		if (!Math.isFinite(newValue)) newValue = 0;
		return oldValue < newValue;
	}

	public static function snapshot(record:Dynamic):Dynamic {
		if (record == null) throw '[codename-save] A score record is required';
		return haxe.Json.parse(haxe.Json.stringify(record));
	}
}
