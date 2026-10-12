package;

import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

/** Bounded owner-local menu metadata; never reads charts, assets or sibling mods.
 * This is presentation order only, not a recreation of donor unlock/visibility rules. */
class PsychFreeplayOrder {
	public static function songKey(value:String, nightmare:Bool):String
		return nightmare ? NightmareVisionSongNameCompat.format(value) : PsychSongNameCompat.format(value);

	public static function read(root:String, content:String, data:String, nightmare:Bool,
		parse:String->Dynamic):Map<String, Int> {
		var result:Map<String, Int> = [];
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
				if (size < 0 || size > 65536 || bytes + size > 4194304) return null;
				bytes += size; return File.getContent(path);
			} catch (_:Dynamic) { return null; }
		}
		function json(path:String):Dynamic {
			var value = text(path);
			try return value == null ? null : parse(value) catch (_:Dynamic) return null;
		}
		var dataRoot = data;
		if (dataRoot == null || dataRoot == '' || !within(dataRoot)) dataRoot = child(content,'data');
		var weeksRoot = nightmare ? child(dataRoot,'weeks') : child(content,'weeks');
		if (weeksRoot == null) weeksRoot = child(content,'weeks');
		if (weeksRoot == null) weeksRoot = child(root,'weeks');
		var weeks:Map<String, Dynamic> = [];
		var weekNames:Array<String> = [];
		if (weeksRoot != null) try {
			var entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(weeksRoot));
			entries.sort(Reflect.compare);
			// Oversized optional metadata does not make an otherwise playable import fail.
			if (entries.length <= 4096) for (entry in entries) {
				if (!StringTools.endsWith(entry.toLowerCase(),'.json') || weekNames.length >= 512) continue;
				var name = entry.substr(0,entry.length-5);
				var week = json(child(weeksRoot,entry));
				if (week == null || weeks.exists(name)) continue;
				weeks.set(name,week); weekNames.push(name);
			}
		} catch (_:Dynamic) {}
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
		var freeplay:Dynamic = null;
		if (nightmare) {
			var freeplayText = text(child(dataRoot,'freeplay.json'));
			try {
				#if json5hx
				if (freeplayText != null) freeplay = haxe.Json5.parse(freeplayText);
				#else
				if (freeplayText != null) freeplay = parse(freeplayText);
				#end
			} catch (_:Dynamic) {}
		}
		var tabs:Dynamic = freeplay == null ? null : Reflect.field(freeplay,'tabs');
		if (Std.isOfType(tabs,Array)) {
			for (tab in (cast tabs:Array<Dynamic>)) {
				if (tab == null) continue;
				var from:Dynamic = Reflect.field(tab,'fromWeeks');
				if (Std.isOfType(from,Array)) for (week in (cast from:Array<Dynamic>)) addWeek(week);
				var songs:Dynamic = Reflect.field(tab,'songs');
				if (Std.isOfType(songs,Array)) for (song in (cast songs:Array<Dynamic>)) addSong(song);
			}
		} else {
			var listed = text(child(weeksRoot,'weekList.txt'));
			if (listed != null) for (name in listed.split('\n')) addWeek(StringTools.trim(name));
			// Unlisted weeks retain deterministic discovery order after explicit weeks.
			for (name in weekNames) addWeek(name);
		}
		#end
		return result;
	}
}
