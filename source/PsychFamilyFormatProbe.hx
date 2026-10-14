package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

/** What one mod root turned out to contain, see PsychFamilyFormatProbe. */
typedef PsychFamilyShapes = {
	/** A week file with the family's week fields. */
	var week:Bool;
	/** One of that week's songs has a section chart in this root. */
	var weekSongChart:Bool;
	var character:Bool;
	var stage:Bool;
	/** A HScript file declaring one of the family's on* callbacks. */
	var haxeCallback:Bool;
}

/**
	Recognises Psych-family content by the shape of its JSON and scripts
	instead of by folder names or executables.

	Psych Engine and its forks write the same week, character and stage files,
	so a mod with no pack.json and no Lua still gives itself away through them.
	Nothing here tells one member of the family from another: the caller adds
	the fork's own markers on top.

	Every check is bounded. A few small files are read per folder and media
	trees are never walked.
*/
class PsychFamilyFormatProbe {
	static inline var MAX_JSON_FILES:Int = 12;
	static inline var MAX_WEEK_FILES:Int = 32;
	static inline var MAX_SCRIPT_FILES:Int = 16;
	static inline var MAX_SONG_DIRECTORIES:Int = 24;
	static inline var MAX_CHART_FILES:Int = 8;
	static inline var MAX_JSON_BYTES:Int = 1024 * 1024;
	static inline var MAX_CHART_BYTES:Int = 4 * 1024 * 1024;

	/**
		Week file: `songs` rows of [title, icon, colour] next to the story menu
		fields. Other engines keep their week lists as plain name arrays or
		under different keys, so both halves are required.
	*/
	public static function isWeek(document:Dynamic):Bool {
		if (weekSongs(document).length == 0)
			return false;
		if (Std.isOfType(Reflect.field(document, 'weekCharacters'), Array))
			return true;
		for (name in ['weekBefore', 'storyName', 'weekName', 'weekBackground'])
			if (Std.isOfType(Reflect.field(document, name), String))
				return true;
		return false;
	}

	/** Song titles a week lists, formatted the way the family names song
	 * folders. Rows that are not [title, icon, ...] are ignored. */
	public static function weekSongs(document:Dynamic):Array<String> {
		var result:Array<String> = [];
		if (!isStructure(document))
			return result;
		var songs:Dynamic = Reflect.field(document, 'songs');
		if (!Std.isOfType(songs, Array))
			return result;
		for (row in (cast songs:Array<Dynamic>)) {
			if (!Std.isOfType(row, Array))
				continue;
			var values:Array<Dynamic> = cast row;
			if (values.length < 2 || !Std.isOfType(values[0], String) || !Std.isOfType(values[1], String))
				continue;
			var name = PsychSongNameCompat.format(Std.string(values[0]));
			if (name != '' && name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf('..') < 0
				&& result.indexOf(name) < 0)
				result.push(name);
		}
		return result;
	}

	/**
		Character file: an atlas `image`, `animations` rows keyed by `anim`, and
		at least one of the gameplay fields. Other engines with JSON characters
		name the atlas and the animation rows differently.
	*/
	public static function isCharacter(document:Dynamic):Bool {
		if (!isStructure(document) || !Std.isOfType(Reflect.field(document, 'image'), String))
			return false;
		var animations:Dynamic = Reflect.field(document, 'animations');
		if (!Std.isOfType(animations, Array))
			return false;
		for (row in (cast animations:Array<Dynamic>)) {
			if (row == null)
				continue;
			if (!isStructure(row) || !Std.isOfType(Reflect.field(row, 'anim'), String))
				return false;
			break;
		}
		return Std.isOfType(Reflect.field(document, 'healthicon'), String)
			|| isNumber(Reflect.field(document, 'sing_duration'))
			|| Std.isOfType(Reflect.field(document, 'camera_position'), Array)
			|| Std.isOfType(Reflect.field(document, 'healthbar_colors'), Array);
	}

	/** Stage file: the three character positions plus the camera zoom. */
	public static function isStage(document:Dynamic):Bool {
		if (!isStructure(document) || !isNumber(Reflect.field(document, 'defaultZoom')))
			return false;
		for (name in ['boyfriend', 'girlfriend', 'opponent']) {
			var position:Dynamic = Reflect.field(document, name);
			if (!Std.isOfType(position, Array))
				return false;
			var values:Array<Dynamic> = cast position;
			if (values.length < 2 || !isNumber(values[0]) || !isNumber(values[1]))
				return false;
		}
		return true;
	}

	/** A Lua script declaring one of the family's entry callbacks. Legacy
	 * modcharts use start/update instead, and commented-out code is ignored. */
	public static function declaresLuaCallback(source:String):Bool {
		if (source == null)
			return false;
		var code = ~/--\[\[[\s\S]*?\]\]/g.replace(source, '');
		return ~/^[ \t]*(?:local[ \t]+)?function[ \t]+on(?:Create|CreatePost|StartCountdown|SongStart|Update|UpdatePost|Event)[ \t]*\(/m.match(code);
	}

	/**
		A HScript file declaring one of the family's callbacks.

		Only names nobody else uses are listed: other HScript engines call theirs
		create/update/beatHit, and some share onEvent and onStartCountdown.
	*/
	public static function declaresHaxeCallback(source:String):Bool {
		if (source == null)
			return false;
		var code = ~/\/\*[\s\S]*?\*\//g.replace(source, '');
		return ~/^[ \t]*(?:(?:public|private|static|override|inline)[ \t]+)*function[ \t]+on(?:Create|CreatePost|Update|UpdatePost|BeatHit|StepHit|SectionHit|Destroy)[ \t]*\(/m.match(code);
	}

	/** True for a parsed section chart of either wrapping that carries a tempo. */
	public static function isSectionChart(document:Dynamic):Bool {
		var song:Dynamic = PsychFamilyChartFields.payload(document);
		if (song == null)
			return false;
		var bpm = Std.parseFloat(Std.string(Reflect.field(song, 'bpm')));
		if (Math.isNaN(bpm) || bpm <= 0)
			return false;
		for (section in (cast Reflect.field(song, 'notes'):Array<Dynamic>))
			if (section != null && Std.isOfType(Reflect.field(section, 'sectionNotes'), Array))
				return true;
		return false;
	}

	/** True for a flat chart the Psych 1.0 editor marked with its format. */
	public static function isFlatPsychChart(document:Dynamic):Bool {
		if (!PsychFamilyChartFields.isFlat(document))
			return false;
		var format:Dynamic = Reflect.field(document, 'format');
		return Std.isOfType(format, String) && Std.string(format).toLowerCase().indexOf('psych_v1') >= 0;
	}

	#if sys
	var bases:Array<String>;
	var chartRoots:Array<String>;
	var cached:PsychFamilyShapes;

	/**
		`bases` are the folders that may hold weeks/, characters/, stages/ and
		scripts/ (the mod root, its assets root, its data folder). `chartRoots`
		hold one folder per song (data/, or songs/ for the nested layout).
	*/
	public function new(bases:Array<String>, chartRoots:Array<String>) {
		this.bases = unique(bases);
		this.chartRoots = unique(chartRoots);
	}

	/** Read the root once. Several engines score the same root, so the
	 * result is kept on this instance. */
	public function shapes():PsychFamilyShapes {
		if (cached != null)
			return cached;
		var result:PsychFamilyShapes = {week:false, weekSongChart:false, character:false, stage:false, haxeCallback:false};
		for (base in bases) {
			var entries = listing(base);
			if (!result.weekSongChart)
				inspectWeeks(child(base, entries, 'weeks'), result);
			if (!result.character)
				result.character = anyJson(child(base, entries, 'characters'), isCharacter);
			var stages = child(base, entries, 'stages');
			if (!result.stage)
				result.stage = anyJson(stages, isStage);
			if (!result.haxeCallback)
				result.haxeCallback = hasHaxeCallback(stages) || hasHaxeCallback(child(base, entries, 'scripts'));
		}
		if (!result.haxeCallback)
			for (chartRoot in chartRoots) {
				var checked = 0;
				for (entry in listing(chartRoot)) {
					var folder = Path.join([chartRoot, entry]);
					if (!isDirectory(folder))
						continue;
					if (checked++ >= MAX_SONG_DIRECTORIES)
						break;
					if (hasHaxeCallback(folder)) {
						result.haxeCallback = true;
						break;
					}
				}
				if (result.haxeCallback)
					break;
			}
		cached = result;
		return result;
	}

	/** True when a data folder holds a flat chart carrying the psych_v1
	 * format marker. Only immediate song folders are opened. */
	public static function hasFlatPsychChart(dataPath:String):Bool {
		var checkedFolders = 0;
		var checkedCharts = 0;
		for (entry in listing(dataPath)) {
			var folder = Path.join([dataPath, entry]);
			if (!isDirectory(folder))
				continue;
			if (checkedFolders++ >= MAX_SONG_DIRECTORIES)
				break;
			for (file in listing(folder)) {
				if (!isJsonName(file))
					continue;
				if (checkedCharts++ >= MAX_SONG_DIRECTORIES * 2)
					return false;
				// Charts are the big files here. Only parse one that can match.
				var path = Path.join([folder, file]);
				try {
					if (FileSystem.isDirectory(path) || FileSystem.stat(path).size > MAX_CHART_BYTES)
						continue;
					var content = File.getContent(path);
					if (content.indexOf('psych_v1') >= 0 && isFlatPsychChart(haxe.Json.parse(content)))
						return true;
				} catch (_:Dynamic) {}
			}
		}
		return false;
	}

	/** True when a song folder (or its data/ child, for the nested layout)
	 * holds a section chart. */
	public static function folderHasSectionChart(folder:String):Bool {
		var entries = listing(folder);
		var folders = [folder];
		var nested = child(folder, entries, 'data');
		if (nested != '')
			folders.push(nested);
		var checked = 0;
		for (candidate in folders)
			for (file in (candidate == folder ? entries : listing(candidate))) {
				if (!isJsonName(file))
					continue;
				if (checked++ >= MAX_CHART_FILES)
					return false;
				if (isSectionChart(readJson(Path.join([candidate, file]), MAX_CHART_BYTES)))
					return true;
			}
		return false;
	}

	function inspectWeeks(weeks:String, result:PsychFamilyShapes):Void {
		if (weeks == '')
			return;
		var checked = 0;
		for (file in listing(weeks)) {
			if (!isJsonName(file))
				continue;
			if (checked++ >= MAX_WEEK_FILES)
				return;
			var week:Dynamic = readJson(Path.join([weeks, file]), MAX_JSON_BYTES);
			if (!isWeek(week))
				continue;
			result.week = true;
			if (weekSongHasChart(weekSongs(week))) {
				result.weekSongChart = true;
				return;
			}
		}
	}

	function weekSongHasChart(songs:Array<String>):Bool {
		for (chartRoot in chartRoots) {
			var checked = 0;
			for (entry in listing(chartRoot)) {
				if (songs.indexOf(PsychSongNameCompat.format(entry)) < 0)
					continue;
				var folder = Path.join([chartRoot, entry]);
				if (!isDirectory(folder))
					continue;
				if (checked++ >= MAX_SONG_DIRECTORIES)
					break;
				if (folderHasSectionChart(folder))
					return true;
			}
		}
		return false;
	}

	static function anyJson(directory:String, matches:Dynamic->Bool):Bool {
		if (directory == '')
			return false;
		var checked = 0;
		for (file in listing(directory)) {
			if (!isJsonName(file))
				continue;
			if (checked++ >= MAX_JSON_FILES)
				return false;
			if (matches(readJson(Path.join([directory, file]), MAX_JSON_BYTES)))
				return true;
		}
		return false;
	}

	static function hasHaxeCallback(directory:String):Bool {
		if (directory == '')
			return false;
		var checked = 0;
		for (file in listing(directory)) {
			if (!StringTools.endsWith(file.toLowerCase(), '.hx'))
				continue;
			if (checked++ >= MAX_SCRIPT_FILES)
				return false;
			var path = Path.join([directory, file]);
			try {
				if (FileSystem.isDirectory(path) || FileSystem.stat(path).size > MAX_JSON_BYTES)
					continue;
				if (declaresHaxeCallback(File.getContent(path)))
					return true;
			} catch (_:Dynamic) {}
		}
		return false;
	}

	static function readJson(path:String, maxBytes:Int):Dynamic {
		try {
			if (FileSystem.isDirectory(path) || FileSystem.stat(path).size > maxBytes)
				return null;
			return haxe.Json.parse(File.getContent(path));
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function isJsonName(name:String):Bool {
		var lower = name.toLowerCase();
		return StringTools.endsWith(lower, '.json') || StringTools.endsWith(lower, '.jsonc');
	}

	static function listing(directory:String):Array<String> {
		try {
			if (directory == null || directory == '' || !FileSystem.exists(directory)
				|| !FileSystem.isDirectory(directory))
				return [];
			var entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(directory));
			// Enumeration order differs between filesystems, keep the bounded
			// walks deterministic.
			entries.sort(function(a:String, b:String):Int {
				var order = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return order == 0 ? Reflect.compare(a, b) : order;
			});
			return entries;
		} catch (_:Dynamic) {
			return [];
		}
	}

	static function child(directory:String, entries:Array<String>, name:String):String {
		for (entry in entries)
			if (entry.toLowerCase() == name) {
				var path = Path.join([directory, entry]);
				if (isDirectory(path))
					return path;
			}
		return '';
	}

	static function isDirectory(path:String):Bool {
		try {
			return FileSystem.isDirectory(path);
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function unique(paths:Array<String>):Array<String> {
		var result:Array<String> = [];
		if (paths == null)
			return result;
		for (path in paths) {
			if (path == null || path == '')
				continue;
			var normalized = Path.normalize(path);
			var known = false;
			for (existing in result)
				if (existing.toLowerCase() == normalized.toLowerCase())
					known = true;
			if (!known)
				result.push(normalized);
		}
		return result;
	}
	#end

	static function isStructure(value:Dynamic):Bool {
		return value != null && Reflect.isObject(value) && !Std.isOfType(value, String)
			&& !Std.isOfType(value, Array);
	}

	static function isNumber(value:Dynamic):Bool {
		return Std.isOfType(value, Float) && !Math.isNaN(cast value);
	}
}
