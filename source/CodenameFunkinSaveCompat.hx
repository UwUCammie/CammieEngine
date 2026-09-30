package;

import flixel.FlxG;

/** Small persistence adapter for the Codename `FunkinSave` song-record API.
 * Records retain source fields without replacing this engine's settings or
 * Highscore schema. */
class CodenameFunkinSaveCompat {
	static inline var RECORDS_FIELD:String = 'codenameSongHighscores';

	public static function getSongHighscore(song:String, difficulty:String,
		?variation:String, ?changes:Array<Dynamic>):Dynamic {
		if (song == null || difficulty == null) return CodenameHighscoreDataCompat.emptyRecord();
		if (FlxG.save == null || FlxG.save.data == null)
			return CodenameHighscoreDataCompat.emptyRecord();
		var records:Dynamic = Reflect.field(FlxG.save.data, RECORDS_FIELD);
		var record:Dynamic = records == null ? null : Reflect.field(records,
			CodenameHighscoreDataCompat.key(song, difficulty, variation, changes));
		return record == null ? CodenameHighscoreDataCompat.emptyRecord() : record;
	}

	public static function setSongHighscore(song:String, difficulty:String,
		?variation:String, record:Dynamic, ?changes:Array<Dynamic>, ?force:Bool):Bool {
		if (FlxG.save == null || FlxG.save.data == null || song == null || difficulty == null || record == null)
			return false;
		var storageKey = CodenameHighscoreDataCompat.key(song, difficulty, variation, changes);
		var records:Dynamic = Reflect.field(FlxG.save.data, RECORDS_FIELD);
		if (records == null || Type.typeof(records) != TObject) records = {};
		var previous:Dynamic = Reflect.field(records, storageKey);
		var snapshot = CodenameHighscoreDataCompat.snapshot(record);
		if (!CodenameHighscoreDataCompat.shouldReplace(previous, snapshot, force == true))
			return false;
		Reflect.setField(records, storageKey, snapshot);
		Reflect.setField(FlxG.save.data, RECORDS_FIELD, records);
		FlxG.save.flush();
		return true;
	}
}
