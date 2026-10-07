package;

import haxe.ds.StringMap;

/** Owner-local port of `funkin.data.Highscore`. The imported owner's private
	CodenameOwnerSaveData view is injected, so no native save data is exposed. */
@:keep
class NightmareVisionHighscore {
	static inline var MAP_MARKER:String = '__nightmareVisionHighscoreMap__';

	public var weekScores:Map<String, Int> = new Map();
	public var songScores:Map<String, Int> = new Map();
	public var songRating:Map<String, Float> = new Map();

	var ownerSave:Dynamic;
	var sanitizePath:Null<String->String>;
	var difficultyFilePath:Null<Int->String>;
	var released:Bool = false;

	public function new(ownerSave:Dynamic, sanitizePath:String->String,
		difficultyFilePath:Int->String) {
		if (ownerSave == null || Reflect.field(ownerSave, 'getField') == null
			|| Reflect.field(ownerSave, 'setField') == null || Reflect.field(ownerSave, 'flush') == null)
			throw '[nightmare-vision-highscore] Missing owner-scoped save data';
		if (sanitizePath == null || difficultyFilePath == null)
			throw '[nightmare-vision-highscore] Missing source path callbacks';
		this.ownerSave = ownerSave;
		this.sanitizePath = sanitizePath;
		this.difficultyFilePath = difficultyFilePath;
	}

	public function resetSong(song:String, diff:Int = 0):Void {
		ensureAlive();
		var daSong = formatSong(song, diff);
		setScore(daSong, 0);
		setRating(daSong, 0);
	}

	public function resetWeek(week:String, diff:Int = 0):Void {
		ensureAlive();
		setWeekScore(formatSong(week, diff), 0);
	}

	public function saveScore(song:String, score:Int = 0, ?diff:Int = 0,
		?rating:Float = -1):Void {
		ensureAlive();
		var daSong = formatSong(song, diff);
		if (songScores.exists(daSong)) {
			if (songScores.get(daSong) < score) {
				setScore(daSong, score);
				if (rating >= 0) setRating(daSong, rating);
			}
		} else {
			setScore(daSong, score);
			if (rating >= 0) setRating(daSong, rating);
		}
	}

	public function saveWeekScore(week:String, score:Int = 0, ?diff:Int = 0):Void {
		ensureAlive();
		var daWeek = formatSong(week, diff);
		if (weekScores.exists(daWeek)) {
			if (weekScores.get(daWeek) < score) setWeekScore(daWeek, score);
		} else setWeekScore(daWeek, score);
	}

	/** Source callers pass a sanitized song identifier to these private setters. */
	@:keep
	function setScore(song:String, score:Int):Void {
		ensureAlive();
		songScores.set(song, score);
		persistIntMap('songScores', songScores);
	}

	@:keep
	function setWeekScore(week:String, score:Int):Void {
		ensureAlive();
		weekScores.set(week, score);
		persistIntMap('weekScores', weekScores);
	}

	@:keep
	function setRating(song:String, rating:Float):Void {
		ensureAlive();
		songRating.set(song, rating);
		persistFloatMap('songRating', songRating);
	}

	public function formatSong(song:String, diff:Int):String {
		ensureAlive();
		return sanitizePath(song) + '-' + difficultyFilePath(diff);
	}

	public function getScore(song:String, diff:Int):Int {
		ensureAlive();
		var daSong = formatSong(song, diff);
		if (!songScores.exists(daSong)) setScore(daSong, 0);
		return songScores.get(daSong);
	}

	public function getRating(song:String, diff:Int):Float {
		ensureAlive();
		var daSong = formatSong(song, diff);
		if (!songRating.exists(daSong)) setRating(daSong, 0);
		return songRating.get(daSong);
	}

	public function getWeekScore(week:String, diff:Int):Int {
		ensureAlive();
		var daWeek = formatSong(week, diff);
		if (!weekScores.exists(daWeek)) setWeekScore(daWeek, 0);
		return weekScores.get(daWeek);
	}

	/** Replace each non-null saved map with a typed clone, matching source load's
		map replacement while restoring JSON-decoded owner fields as live Maps. */
	public function load():Void {
		ensureAlive();
		var savedWeekScores = readField('weekScores');
		if (savedWeekScores != null) weekScores = restoreIntMap(savedWeekScores, 'weekScores');
		var savedSongScores = readField('songScores');
		if (savedSongScores != null) songScores = restoreIntMap(savedSongScores, 'songScores');
		var savedSongRating = readField('songRating');
		if (savedSongRating != null) songRating = restoreFloatMap(savedSongRating, 'songRating');
	}

	public function release():Void {
		if (released) return;
		released = true;
		ownerSave = null;
		sanitizePath = null;
		difficultyFilePath = null;
		weekScores = new Map();
		songScores = new Map();
		songRating = new Map();
	}

	function persistIntMap(field:String, values:Map<String, Int>):Void {
		writeField(field, mapSnapshot(values));
		flushOwner();
	}

	function persistFloatMap(field:String, values:Map<String, Float>):Void {
		writeField(field, mapSnapshot(values));
		flushOwner();
	}

	function mapSnapshot<T>(values:Map<String, T>):Dynamic {
		var keys:Array<String> = [];
		for (key in values.keys()) keys.push(key);
		keys.sort(Reflect.compare);
		var entries:Array<Dynamic> = [];
		for (key in keys) entries.push([key, values.get(key)]);
		return {__nightmareVisionHighscoreMap__:true, entries:entries};
	}

	function readField(field:String):Dynamic {
		var method:Dynamic = Reflect.field(ownerSave, 'getField');
		return Reflect.callMethod(ownerSave, method, [field]);
	}

	function writeField(field:String, value:Dynamic):Void {
		var method:Dynamic = Reflect.field(ownerSave, 'setField');
		Reflect.callMethod(ownerSave, method, [field, value]);
	}

	function flushOwner():Void {
		var method:Dynamic = Reflect.field(ownerSave, 'flush');
		Reflect.callMethod(ownerSave, method, []);
	}

	static function restoreIntMap(value:Dynamic, field:String):Map<String, Int> {
		var result:Map<String, Int> = new Map();
		if (Std.isOfType(value, StringMap)) {
			var input:StringMap<Dynamic> = cast value;
			for (key in input.keys()) result.set(key, asInt(input.get(key), field, key));
			return result;
		}
		if (Type.typeof(value) != TObject)
			throw '[nightmare-vision-highscore] Malformed owner map: ' + field;
		var entries:Dynamic = mapEntries(value, field);
		if (entries != null) {
			for (entry in (cast entries:Array<Dynamic>)) {
				var key = entryKey(entry, field);
				result.set(key, asInt((cast entry:Array<Dynamic>)[1], field, key));
			}
		} else for (key in Reflect.fields(value))
			result.set(key, asInt(Reflect.field(value, key), field, key));
		return result;
	}

	static function restoreFloatMap(value:Dynamic, field:String):Map<String, Float> {
		var result:Map<String, Float> = new Map();
		if (Std.isOfType(value, StringMap)) {
			var input:StringMap<Dynamic> = cast value;
			for (key in input.keys()) result.set(key, asFloat(input.get(key), field, key));
			return result;
		}
		if (Type.typeof(value) != TObject)
			throw '[nightmare-vision-highscore] Malformed owner map: ' + field;
		var entries:Dynamic = mapEntries(value, field);
		if (entries != null) {
			for (entry in (cast entries:Array<Dynamic>)) {
				var key = entryKey(entry, field);
				result.set(key, asFloat((cast entry:Array<Dynamic>)[1], field, key));
			}
		} else for (key in Reflect.fields(value))
			result.set(key, asFloat(Reflect.field(value, key), field, key));
		return result;
	}

	static function mapEntries(value:Dynamic, field:String):Null<Array<Dynamic>> {
		if (Reflect.field(value, MAP_MARKER) != true) return null;
		var entries:Dynamic = Reflect.field(value, 'entries');
		if (!Std.isOfType(entries, Array))
			throw '[nightmare-vision-highscore] Malformed owner map entries: ' + field;
		return cast entries;
	}

	static function entryKey(entry:Dynamic, field:String):String {
		if (!Std.isOfType(entry, Array) || (cast entry:Array<Dynamic>).length != 2
			|| !Std.isOfType((cast entry:Array<Dynamic>)[0], String))
			throw '[nightmare-vision-highscore] Malformed owner map entry: ' + field;
		return (cast entry:Array<Dynamic>)[0];
	}

	static function asInt(value:Dynamic, field:String, key:String):Int {
		switch (Type.typeof(value)) {
			case TInt: return cast value;
			case TFloat:
				var numeric:Float = cast value;
				if (Math.isNaN(numeric) || numeric != Math.floor(numeric))
					throw '[nightmare-vision-highscore] Invalid integer in ' + field + ': ' + key;
				return Std.int(numeric);
			default: throw '[nightmare-vision-highscore] Invalid integer in ' + field + ': ' + key;
		}
	}

	static function asFloat(value:Dynamic, field:String, key:String):Float {
		switch (Type.typeof(value)) {
			case TInt: return cast value;
			case TFloat: return cast value;
			default: throw '[nightmare-vision-highscore] Invalid rating in ' + field + ': ' + key;
		}
	}

	function ensureAlive():Void {
		if (released) throw '[nightmare-vision-highscore] This owner highscore view has been released';
	}
}
