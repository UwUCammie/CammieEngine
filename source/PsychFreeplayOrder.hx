package;

import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

/** Owner-local Freeplay order from the shared Psych-family week reader.
 * This is presentation order only; unlocks belong to Story Mode. */
class PsychFreeplayOrder {
	public static function songKey(value:String, nightmare:Bool):String
		return PsychFamilyWeekImport.songKey(value, nightmare);

	public static function read(root:String, content:String, data:String, nightmare:Bool,
		parse:String->Dynamic):Map<String, Int>
		return fromSource(PsychFamilyWeekImport.readSource(root, content, data, nightmare, parse), nightmare);

	public static function fromSource(source:PsychFamilyWeekImport.PsychFamilyWeekSource, nightmare:Bool):Map<String, Int> {
		var result:Map<String, Int> = [];
		if (source == null) return result;
		var weeks:Map<String, Dynamic> = [];
		for (week in source.weeks) weeks.set(week.name, week.data);
		var next = 0;
		function addSong(value:Dynamic):Void {
			if (!Std.isOfType(value,String)) return;
			var key = songKey(cast value,nightmare);
			if (key != '' && !result.exists(key)) result.set(key,next++);
		}
		function addWeek(value:Dynamic):Void {
			if (!Std.isOfType(value,String)) return;
			var week = weeks.get(cast value);
			if (week == null || Reflect.field(week,'hideFreeplay') == true) return;
			var songs:Dynamic = Reflect.field(week,'songs');
			if (Std.isOfType(songs,Array)) for (song in (cast songs:Array<Dynamic>))
				if (Std.isOfType(song,Array) && (cast song:Array<Dynamic>).length > 0) addSong(song[0]);
		}
		var tabs:Dynamic = source.freeplay == null ? null : Reflect.field(source.freeplay,'tabs');
		if (Std.isOfType(tabs,Array)) {
			for (tab in (cast tabs:Array<Dynamic>)) {
				if (tab == null) continue;
				var from:Dynamic = Reflect.field(tab,'fromWeeks');
				if (Std.isOfType(from,Array)) for (week in (cast from:Array<Dynamic>)) addWeek(week);
				var songs:Dynamic = Reflect.field(tab,'songs');
				if (Std.isOfType(songs,Array)) for (song in (cast songs:Array<Dynamic>)) addSong(song);
			}
		} else {
			// The reader already put weekList.txt weeks first.
			for (week in source.weeks) addWeek(week.name);
		}
		return result;
	}
}
