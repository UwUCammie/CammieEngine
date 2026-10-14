package;

import PsychFamilyWeekImport.PsychFamilyStoryWeek;
import VSliceImporter.VSliceLevelConversion;

typedef VSliceStoryWeekSource = {
	var weeks:Array<PsychFamilyStoryWeek>;
	/** Week file -> donor title image. Only used while importing and never
	 * written to the owner record, which must not hold donor paths. */
	var titles:Map<String, String>;
}

/**
	V-Slice story levels as Story Mode weeks of the owner that imported them.
	They go through the same owner record Psych and Nightmare Vision weeks use,
	so removing the import removes its weeks and the shared storySonglist.json
	is never rewritten. A level marked `visible: false` is left out, because the
	V-Slice story menu does not list it either, and levels start unlocked as
	V-Slice levels do unless a script says otherwise.
**/
class VSliceStoryWeeks {
	/** Owner-relative folder the level title images are copied into. */
	public static inline var TITLE_FOLDER:String = 'images/vslice-level-titles';

	/** Level song lists name songs by their data/songs folder id. */
	public static function songKey(value:String):String
		return value == null ? '' : StringTools.trim(value).toLowerCase();

	public static function fromLevels(conversions:Array<VSliceLevelConversion>):VSliceStoryWeekSource {
		var result:VSliceStoryWeekSource = {weeks:[], titles:new Map()};
		if (conversions == null) return result;
		var taken:Map<String, Bool> = new Map();
		for (conversion in conversions) {
			if (conversion == null || conversion.week == null) continue;
			var week:Dynamic = conversion.week;
			var flags:Dynamic = Reflect.field(week, 'visibleFlags');
			if (Std.isOfType(flags, Array) && (cast flags:Array<Dynamic>).length > 0) continue;
			var file = text(week, 'name');
			if (file == '' || file.indexOf('/') >= 0 || file.indexOf('\\') >= 0 || taken.exists(file.toLowerCase())) continue;
			var songs:Array<String> = [];
			var authored:Dynamic = Reflect.field(week, 'songs');
			if (Std.isOfType(authored, Array))
				for (song in (cast authored:Array<Dynamic>)) {
					var key = Std.isOfType(song, String) ? songKey(song) : '';
					if (key != '' && songs.indexOf(key) < 0) songs.push(key);
				}
			if (songs.length == 0) continue;
			taken.set(file.toLowerCase(), true);
			var art = '';
			if (conversion.assets != null)
				for (asset in conversion.assets)
					if (asset != null && asset.kind == 'level-title' && asset.supported == true
						&& asset.source != null && asset.source != '') {
						art = TITLE_FOLDER + '/' + file + '.png';
						result.titles.set(file, asset.source);
						break;
					}
			result.weeks.push({
				file:file,
				storyName:text(week, 'desc'),
				songs:songs,
				// Level props are drawn by V-Slice's own story menu and do not map
				// onto the three native menu characters.
				characters:['', '', ''],
				startUnlocked:true,
				weekBefore:'',
				weekBeforeLocal:false,
				hiddenUntilUnlocked:false,
				art:art
			});
		}
		return result;
	}

	#if sys
	/** Read every data/levels file of one V-Slice content root. */
	public static function read(contentRoot:String, ?dataRoot:String):VSliceStoryWeekSource {
		try {
			return fromLevels(VSliceImporter.convertLevelFolder(contentRoot, dataRoot));
		} catch (_:Dynamic) {
			// Story weeks are optional metadata; they never fail a song import.
			return {weeks:[], titles:new Map()};
		}
	}
	#end

	static function text(value:Dynamic, field:String):String {
		var found:Dynamic = Reflect.field(value, field);
		return Std.isOfType(found, String) ? StringTools.trim(found) : '';
	}
}
