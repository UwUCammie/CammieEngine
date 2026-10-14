package;

import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

typedef PsychFamilyWeekFile = {
	var name:String;
	var data:Dynamic;
}

typedef PsychFamilyWeekSource = {
	/** Week files in the source engine's load order: weekList.txt first, then the rest by name. */
	var weeks:Array<PsychFamilyWeekFile>;
	/** Nightmare Vision's data/freeplay.json, or null. */
	var freeplay:Dynamic;
}

typedef PsychFamilyStoryWeek = {
	/** Week file name without .json; the source engine keys scores and unlocks on it. */
	var file:String;
	var storyName:String;
	/** Song keys in the source engine's song-path format. */
	var songs:Array<String>;
	/** Opponent, player and girlfriend menu characters; '' leaves the slot empty. */
	var characters:Array<String>;
	var startUnlocked:Bool;
	var weekBefore:String;
	/** True when weekBefore names a week file of this same source, so its
	 * completion is tracked under this owner rather than the base game. */
	var weekBeforeLocal:Bool;
	var hiddenUntilUnlocked:Bool;
	/** Owner-relative title image path for this week. */
	var art:String;
}

/** Reads Psych and Nightmare Vision week files. The two engines share the week
 * format, the weekList.txt order and the lock rule; only the folder the weeks
 * live in, the title art folder and the startUnlocked default differ. Freeplay
 * order and story weeks both come from this one reader, which is bounded and
 * never leaves the owner's folder. */
class PsychFamilyWeekImport {
	public static inline var MAX_WEEKS:Int = 512;
	static inline var MAX_FILE_BYTES:Int = 65536;
	static inline var MAX_TOTAL_BYTES:Int = 4194304;

	public static function songKey(value:String, nightmare:Bool):String
		return nightmare ? NightmareVisionSongNameCompat.format(value) : PsychSongNameCompat.format(value);

	public static function readSource(root:String, content:String, data:String, nightmare:Bool,
		parse:String->Dynamic):PsychFamilyWeekSource {
		var result:PsychFamilyWeekSource = {weeks:[], freeplay:null};
		#if sys
		if (root == null || root == '') return result;
		var directories:Map<String, Array<String>> = [];
		var bytes = 0;
		function within(path:String):Bool {
			try {
				var base = Path.normalize(FileSystem.fullPath(root));
				var resolved = Path.normalize(FileSystem.fullPath(path));
				#if windows
				base = base.toLowerCase(); resolved = resolved.toLowerCase();
				#end
				return resolved == base || StringTools.startsWith(resolved, base + '/');
			} catch (_:Dynamic) { return false; }
		}
		function child(parent:String, name:String):String {
			if (parent == null || parent == '' || name == null || name == ''
				|| name == '.' || name == '..' || ~/[\/\\:\x00-\x1f]/.match(name)) return null;
			try {
				if (!within(parent) || !FileSystem.isDirectory(parent)) return null;
				var direct = Path.join([parent,name]);
				if (FileSystem.exists(direct) && within(direct)) return direct;
				var entries = directories.get(parent);
				if (entries == null) {
					entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(parent));
					if (entries.length > 4096) entries = [];
					entries.sort(Reflect.compare); directories.set(parent,entries);
				}
				for (entry in entries) if (entry.toLowerCase() == name.toLowerCase()) {
					var path = Path.join([parent,entry]);
					if (within(path)) return path;
				}
			} catch (_:Dynamic) {}
			return null;
		}
		function text(path:String):String {
			try {
				if (path == null || !within(path) || FileSystem.isDirectory(path)) return null;
				var size = FileSystem.stat(path).size;
				if (size < 0 || size > MAX_FILE_BYTES || bytes + size > MAX_TOTAL_BYTES) return null;
				bytes += size; return File.getContent(path);
			} catch (_:Dynamic) { return null; }
		}
		function json(path:String):Dynamic {
			var value = text(path);
			try return value == null ? null : parse(value) catch (_:Dynamic) return null;
		}
		var dataRoot = data;
		if (dataRoot == null || dataRoot == '' || !within(dataRoot)) dataRoot = child(content,'data');
		// Nightmare Vision looks in data/weeks before weeks; Psych only has weeks.
		var weeksRoot = nightmare ? child(dataRoot,'weeks') : child(content,'weeks');
		if (weeksRoot == null) weeksRoot = child(content,'weeks');
		if (weeksRoot == null) weeksRoot = child(root,'weeks');
		var byName:Map<String, Dynamic> = [];
		var names:Array<String> = [];
		if (weeksRoot != null) try {
			var entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(weeksRoot));
			entries.sort(Reflect.compare);
			// Oversized optional metadata does not make an otherwise playable import fail.
			if (entries.length <= 4096) for (entry in entries) {
				if (!StringTools.endsWith(entry.toLowerCase(),'.json') || names.length >= MAX_WEEKS) continue;
				var name = entry.substr(0,entry.length-5);
				var week = json(child(weeksRoot,entry));
				if (week == null || byName.exists(name)) continue;
				byName.set(name,week); names.push(name);
			}
		} catch (_:Dynamic) {}
		if (nightmare) {
			var freeplayText = text(child(dataRoot,'freeplay.json'));
			try {
				#if json5hx
				if (freeplayText != null) result.freeplay = haxe.Json5.parse(freeplayText);
				#else
				if (freeplayText != null) result.freeplay = parse(freeplayText);
				#end
			} catch (_:Dynamic) {}
		}
		// Both engines load the weeks named in weekList.txt first, then every
		// other week file in the folder.
		var added:Map<String, Bool> = [];
		function add(name:String):Void {
			if (name == null || added.exists(name) || !byName.exists(name)) return;
			added.set(name, true);
			result.weeks.push({name:name, data:byName.get(name)});
		}
		var listed = text(child(weeksRoot,'weekList.txt'));
		if (listed != null) for (name in listed.split('\n')) add(StringTools.trim(name));
		for (name in names) add(name);
		#end
		return result;
	}

	/** Story Mode weeks in load order. Weeks the source hides from Story Mode
	 * and weeks with no songs are left out. */
	public static function storyWeeks(source:PsychFamilyWeekSource, nightmare:Bool):Array<PsychFamilyStoryWeek> {
		var result:Array<PsychFamilyStoryWeek> = [];
		if (source == null || source.weeks == null) return result;
		var files:Map<String, Bool> = [];
		for (week in source.weeks) if (week != null) files.set(week.name, true);
		for (week in source.weeks) {
			if (week == null || week.data == null || Type.typeof(week.data) != TObject) continue;
			var data:Dynamic = week.data;
			if (Reflect.field(data, 'hideStoryMode') == true) continue;
			var songs:Array<String> = [];
			var authored:Dynamic = Reflect.field(data, 'songs');
			if (Std.isOfType(authored, Array)) for (song in (cast authored:Array<Dynamic>)) {
				if (!Std.isOfType(song, Array) || (cast song:Array<Dynamic>).length == 0) continue;
				var first:Dynamic = song[0];
				if (!Std.isOfType(first, String)) continue;
				var key = songKey(first, nightmare);
				if (key != '') songs.push(key);
			}
			if (songs.length == 0) continue;
			var characters = ['', '', ''];
			var authoredCharacters:Dynamic = Reflect.field(data, 'weekCharacters');
			if (Std.isOfType(authoredCharacters, Array))
				for (slot in 0...3) {
					var value:Dynamic = (cast authoredCharacters:Array<Dynamic>)[slot];
					if (Std.isOfType(value, String)) characters[slot] = StringTools.trim(value);
				}
			// Psych leaves a missing startUnlocked unset, which reads as locked;
			// Nightmare Vision's week class defaults it to true.
			var unlocked:Dynamic = Reflect.field(data, 'startUnlocked');
			var before = StringTools.trim(stringField(data, 'weekBefore'));
			result.push({
				file:week.name,
				storyName:stringField(data, 'storyName'),
				songs:songs,
				characters:characters,
				startUnlocked:Std.isOfType(unlocked, Bool) ? unlocked : nightmare,
				weekBefore:before,
				weekBeforeLocal:before != '' && files.exists(before),
				hiddenUntilUnlocked:Reflect.field(data, 'hiddenUntilUnlocked') == true,
				art:(nightmare ? 'images/menus/story/weeks/' : 'images/storymenu/') + week.name + '.png'
			});
		}
		return result;
	}

	/** The source engine's lock rule: a week is locked only when it does not
	 * start unlocked, names a previous week, and that week is not completed. */
	public static function locked(startUnlocked:Bool, weekBefore:String, completed:String->Bool):Bool
		return !startUnlocked && weekBefore != null && weekBefore != '' && !completed(weekBefore);

	static function stringField(data:Dynamic, name:String):String {
		var value:Dynamic = Reflect.field(data, name);
		return Std.isOfType(value, String) ? value : '';
	}
}
