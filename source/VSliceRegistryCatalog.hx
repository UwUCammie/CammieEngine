package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** One V-Slice song id as the importer laid it out: every variation is its own installed folder. */
typedef VSliceCatalogSong = {
	var id:String;
	var owner:String;
	/** Variation id -> installed chart folder, in discovery order. */
	var variations:Map<String, String>;
	var variationOrder:Array<String>;
	/** Installed folder -> display name recorded at import time. */
	var display:Map<String, String>;
}

/** The small chart fields a V-Slice SongDifficulty view exposes. */
typedef VSliceCatalogChartInfo = {
	var songName:String;
	var songArtist:String;
	var player:String;
	var opponent:String;
	var girlfriend:String;
	var stage:String;
	var noteStyle:String;
	var scrollSpeed:Float;
	var bpm:Float;
	var album:String;
}

/**
	Installed-song index behind the V-Slice SongRegistry, LevelRegistry and
	PlayStatePlaylist facades. It reads only what the importer already wrote:
	`assets/data/<folder>/importProvenance.json` (owner, source id and
	destination folder) and the owner's story-week record, so imported scripts
	address songs by the ids they were authored with while the engine keeps
	loading charts from its own folders.

	Engine services (difficulty names, chart suffix rules, week completion and
	the active owner) are hooks that the engine binding fills in, so this index
	stays independent of Flixel and can be tested on its own.
*/
class VSliceRegistryCatalog {
	public static inline var MAX_PROVENANCE_BYTES:Int = 65536;
	/** Charts are read only for their header fields; skip pathological files. */
	public static inline var MAX_CHART_BYTES:Int = 16 * 1024 * 1024;

	public static var dataRoot:String = 'assets/data';
	public static var ownerPrefix:String = 'assets/imported_mods';

	/** Owner roots whose songs win when several imports share a song id. */
	public static var ownerRoots:Void->Array<String> = function():Array<String> return [];
	/** The engine's default difficulty name; its chart has no file suffix. */
	public static var defaultDifficulty:Void->String = function():String return 'normal';
	/** Difficulty suffix of one chart file in a folder, or null for a non-chart file. */
	public static var chartSuffix:(String, String)->Null<String> = defaultChartSuffix;
	/** The engine's difficulty names in menu order; listed difficulties follow it. */
	public static var difficultyNames:Void->Array<String> = function():Array<String> return ['easy', 'normal', 'hard'];
	/** Whether a story week (by its engine key) has been completed. */
	public static var weekCompleted:String->Bool = function(_:String):Bool return false;

	static var index:Map<String, Map<String, VSliceCatalogSong>>;
	static var folderIndex:Map<String, VSliceCatalogSong>;
	/** The sorted data folder listing the index was built from. A count alone
	 * missed one song being removed and another added between checks. */
	static var indexedListing:String = null;
	/** When the data folder was last listed; menus may call the registries every frame. */
	static var lastListingStamp:Float = -1;
	static inline var LISTING_RECHECK_SECONDS:Float = 5;
	static var chartInfoCache:Map<String, VSliceCatalogChartInfo> = new Map();

	/** Drop the cached index, for example after an import changes the installed songs. */
	public static function invalidate():Void {
		index = null;
		folderIndex = null;
		indexedListing = null;
		lastListingStamp = -1;
		chartInfoCache = new Map();
	}

	/** Find a song by its authored id or by an installed folder name. */
	public static function findSong(id:String):Null<VSliceCatalogSong> {
		var key = id == null ? '' : StringTools.trim(id).toLowerCase();
		if (key == '' || !safeName(key))
			return null;
		ensureIndex();
		var owners = preferredOwners();
		for (owner in owners) {
			var songs = index.get(ownerKey(owner));
			if (songs != null && songs.exists(key))
				return songs.get(key);
		}
		var byFolder = folderIndex.get(key);
		if (byFolder != null && (owners.length == 0 || byFolder.owner == '' || ownedBy(owners, byFolder.owner)))
			return byFolder;
		if (owners.length == 0) {
			// No active owner: an id one import owns is unambiguous; base-game songs come last.
			var found:VSliceCatalogSong = null;
			for (ownerName => songs in index) {
				if (ownerName == '' || !songs.exists(key))
					continue;
				if (found != null)
					return null;
				found = songs.get(key);
			}
			if (found != null)
				return found;
		}
		var base = index.get('');
		return base == null ? null : base.get(key);
	}

	/** Song ids the active owners (or every owner when none is active) provide. */
	public static function listSongIds():Array<String> {
		ensureIndex();
		var result:Array<String> = [];
		var owners = preferredOwners();
		var sources = owners.length == 0 ? [for (key in index.keys()) key] : [for (owner in owners) ownerKey(owner)];
		sources.sort(Reflect.compare);
		for (source in sources) {
			var songs = index.get(source);
			if (songs == null)
				continue;
			var ids = [for (id in songs.keys()) id];
			ids.sort(Reflect.compare);
			for (id in ids)
				if (result.indexOf(id) < 0)
					result.push(id);
		}
		return result;
	}

	/** Difficulty ids a song folder has charts for, the default difficulty first. */
	public static function folderDifficulties(folder:String):Array<String> {
		var result:Array<String> = [];
		#if sys
		if (!safeName(folder))
			return result;
		var path = Path.join([dataRoot, folder]);
		var entries:Array<String> = [];
		try {
			if (!FileSystem.isDirectory(path))
				return result;
			entries = FileSystem.readDirectory(path);
		} catch (_:Dynamic) {
			return result;
		}
		entries.sort(Reflect.compare);
		var defaultName = StringTools.trim(defaultDifficulty()).toLowerCase();
		for (entry in entries) {
			var suffix:Null<String> = null;
			try suffix = chartSuffix(folder, entry) catch (_:Dynamic) {}
			if (suffix == null)
				continue;
			var name = suffix == '' ? defaultName : suffix.toLowerCase();
			if (name != '' && result.indexOf(name) < 0)
				result.push(name);
		}
		// V-Slice lists difficulties in the game's order (easy, normal, hard, ...);
		// names the engine does not know keep their file order after those.
		var order:Array<String> = [];
		try order = [for (name in difficultyNames()) if (name != null) name.toLowerCase()] catch (_:Dynamic) {}
		var rank = function(name:String):Int {
			var index = order.indexOf(name);
			return index < 0 ? order.length + result.indexOf(name) : index;
		};
		var ranked = result.copy();
		ranked.sort(function(a:String, b:String):Int return rank(a) - rank(b));
		result = ranked;
		#end
		return result;
	}

	/** Chart file name (without extension) for a difficulty in a folder. */
	public static function chartName(folder:String, difficulty:String):String {
		var key = difficulty == null ? '' : StringTools.trim(difficulty).toLowerCase();
		var defaultName = StringTools.trim(defaultDifficulty()).toLowerCase();
		return key == '' || key == defaultName ? folder : folder + '-' + key;
	}

	/** Header fields of one installed chart, read once and cached. */
	public static function chartInfo(folder:String, difficulty:String):Null<VSliceCatalogChartInfo> {
		#if sys
		if (!safeName(folder))
			return null;
		var name = chartName(folder, difficulty);
		var cacheKey = folder + '/' + name;
		if (chartInfoCache.exists(cacheKey))
			return chartInfoCache.get(cacheKey);
		var info:VSliceCatalogChartInfo = null;
		for (extension in ['.json', '.jsonc']) {
			var path = Path.join([dataRoot, folder, name + extension]);
			try {
				if (!FileSystem.exists(path) || FileSystem.isDirectory(path) || FileSystem.stat(path).size > MAX_CHART_BYTES)
					continue;
				var parsed:Dynamic = haxe.Json.parse(File.getContent(path));
				var song:Dynamic = parsed == null ? null : Reflect.field(parsed, 'song');
				if (song == null || Type.typeof(song) != TObject)
					song = parsed;
				info = {
					songName: text(song, 'song'),
					songArtist: text(song, 'songArtist'),
					player: text(song, 'player1'),
					opponent: text(song, 'player2'),
					girlfriend: text(song, 'gf') != '' ? text(song, 'gf') : text(song, 'gfVersion'),
					stage: text(song, 'stage'),
					noteStyle: text(song, 'uiType'),
					scrollSpeed: number(song, 'speed', 1),
					bpm: number(song, 'bpm', 100),
					album: text(song, 'album')
				};
				break;
			} catch (_:Dynamic) {}
		}
		chartInfoCache.set(cacheKey, info);
		return info;
		#else
		return null;
		#end
	}

	/** Whether a chart exists for this folder and difficulty. */
	public static function hasChart(folder:String, difficulty:String):Bool {
		var key = difficulty == null ? '' : StringTools.trim(difficulty).toLowerCase();
		if (key == '')
			key = StringTools.trim(defaultDifficulty()).toLowerCase();
		return folderDifficulties(folder).indexOf(key) >= 0;
	}

	/** Story weeks of the active owners (or every owner), in their authored order. */
	public static function levels():Array<ImportedStoryWeeks.ImportedStoryWeek> {
		var result:Array<ImportedStoryWeeks.ImportedStoryWeek> = [];
		#if sys
		var owners = [for (owner in preferredOwners()) ownerKey(owner)];
		for (week in ImportedStoryWeeks.collect(ownerPrefix))
			if (week != null && (owners.length == 0 || owners.indexOf(ownerKey(week.owner)) >= 0))
				result.push(week);
		#end
		return result;
	}

	/** Lock state for each listed week, using the engine's story unlock rule. */
	public static function levelLocked(week:ImportedStoryWeeks.ImportedStoryWeek):Bool {
		if (week == null)
			return true;
		var all = levels();
		for (listed in ImportedStoryWeeks.menuWeeks(all, [], false, weekCompleted))
			if (listed.week.key == week.key)
				return listed.locked;
		// menuWeeks hides a locked week marked hidden-until-unlocked.
		return true;
	}

	/** Variation an installed folder holds ('default' for a base chart or an unknown folder). */
	public static function folderVariation(folder:String):String {
		var key = folder == null ? '' : StringTools.trim(folder).toLowerCase();
		if (key == '')
			return 'default';
		ensureIndex();
		var song = folderIndex.get(key);
		if (song != null)
			for (variation => installed in song.variations)
				if (installed == key)
					return variation;
		return 'default';
	}

	/** Display name the importer recorded for a folder, or '' when it recorded none. */
	public static function folderDisplay(folder:String):String {
		var key = folder == null ? '' : StringTools.trim(folder).toLowerCase();
		if (key == '')
			return '';
		ensureIndex();
		var song = folderIndex.get(key);
		var display = song == null ? null : song.display.get(key);
		return display == null || display == song.id ? '' : display;
	}

	/** Owner root that installed a folder, or '' for a base-game song. */
	public static function folderOwner(folder:String):String {
		var key = folder == null ? '' : StringTools.trim(folder).toLowerCase();
		if (key == '')
			return '';
		ensureIndex();
		var song = folderIndex.get(key);
		return song == null ? '' : song.owner;
	}

	static function ownedBy(owners:Array<String>, owner:String):Bool {
		var key = ownerKey(owner);
		for (candidate in owners)
			if (ownerKey(candidate) == key)
				return true;
		return false;
	}

	static function preferredOwners():Array<String> {
		var result:Array<String> = [];
		var roots:Array<String> = null;
		try roots = ownerRoots() catch (_:Dynamic) {}
		if (roots != null)
			for (root in roots)
				if (root != null && StringTools.trim(root) != '' && result.indexOf(root) < 0)
					result.push(root);
		return result;
	}

	static function ensureIndex():Void {
		#if sys
		// The listing only notices songs added or removed while the game runs, so
		// it is repeated at most every few seconds instead of on every lookup.
		var now = haxe.Timer.stamp();
		if (index != null && lastListingStamp >= 0 && now - lastListingStamp < LISTING_RECHECK_SECONDS)
			return;
		lastListingStamp = now;
		var entries:Array<String> = [];
		try {
			if (FileSystem.isDirectory(dataRoot))
				entries = FileSystem.readDirectory(dataRoot);
		} catch (_:Dynamic) {}
		entries.sort(Reflect.compare);
		var listing = entries.join('\n');
		if (index != null && listing == indexedListing)
			return;
		index = new Map();
		folderIndex = new Map();
		indexedListing = listing;
		// Songs were added or removed, which is when a reimport rewrites charts too.
		chartInfoCache = new Map();
		for (entry in entries) {
			var folder = entry.toLowerCase();
			if (!safeName(folder))
				continue;
			var path = Path.join([dataRoot, entry]);
			try {
				if (!FileSystem.isDirectory(path))
					continue;
			} catch (_:Dynamic) {
				continue;
			}
			var owner = ImportedModDiscovery.ownerForSong(entry, dataRoot);
			var provenance = readProvenance(path);
			var sourceId = provenance == null ? '' : text(provenance, 'sourceFolder').toLowerCase();
			if (sourceId == '' || !safeName(sourceId))
				sourceId = baseId(folder);
			var destination = provenance == null ? '' : text(provenance, 'destinationFolder').toLowerCase();
			if (destination != '' && destination != folder)
				continue;
			var songs = index.get(ownerKey(owner));
			if (songs == null) {
				songs = new Map();
				index.set(ownerKey(owner), songs);
			}
			var song = songs.get(sourceId);
			if (song == null) {
				song = {id: sourceId, owner: owner, variations: new Map(), variationOrder: [], display: new Map()};
				songs.set(sourceId, song);
			}
			var variation = variationOf(folder, sourceId);
			if (song.variations.exists(variation))
				variation = folder;
			song.variations.set(variation, folder);
			if (variation == 'default')
				song.variationOrder.unshift(variation);
			else
				song.variationOrder.push(variation);
			var display = provenance == null ? '' : text(provenance, 'display');
			song.display.set(folder, display == '' || display == 'null' ? sourceId : display);
			folderIndex.set(folder, song);
		}
		#end
	}

	/** The importer names a variation folder `<id>-<variation>` and may add a `--<owner>` qualifier. */
	public static function variationOf(folder:String, sourceId:String):String {
		var base = baseId(folder);
		if (base == sourceId)
			return 'default';
		if (StringTools.startsWith(base, sourceId + '-') && base.length > sourceId.length + 1)
			return base.substr(sourceId.length + 1);
		return 'default';
	}

	static function baseId(folder:String):String {
		var qualifier = folder.indexOf('--');
		return qualifier > 0 ? folder.substr(0, qualifier) : folder;
	}

	#if sys
	static function readProvenance(folderPath:String):Dynamic {
		var path = Path.join([folderPath, 'importProvenance.json']);
		try {
			if (!FileSystem.exists(path) || FileSystem.isDirectory(path) || FileSystem.stat(path).size > MAX_PROVENANCE_BYTES)
				return null;
			var parsed:Dynamic = haxe.Json.parse(File.getContent(path));
			return parsed != null && Type.typeof(parsed) == TObject ? parsed : null;
		} catch (_:Dynamic) {
			return null;
		}
	}
	#end

	/** Used until the engine binding installs DifficultyManager's rule. */
	static function defaultChartSuffix(folder:String, file:String):Null<String> {
		var name = file.toLowerCase();
		if (name.endsWith('.json'))
			name = name.substr(0, name.length - 5);
		else
			return null;
		var key = folder.toLowerCase();
		if (name == key)
			return '';
		if (!name.startsWith(key + '-'))
			return null;
		var suffix = name.substr(key.length + 1);
		return suffix == '' || suffix == 'events' || suffix == 'metadata' ? null : suffix;
	}

	static inline function ownerKey(owner:String):String
		return owner == null || owner == '' ? '' : CompatScriptManifest.destinationKey(owner);

	static function safeName(value:String):Bool
		return value != null && value != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0;

	static function text(value:Dynamic, field:String):String {
		if (value == null)
			return '';
		var found:Dynamic = Reflect.field(value, field);
		return found == null ? '' : StringTools.trim(Std.string(found));
	}

	static function number(value:Dynamic, field:String, fallback:Float):Float {
		var found:Dynamic = value == null ? null : Reflect.field(value, field);
		var parsed = found == null ? Math.NaN : Std.parseFloat(Std.string(found));
		return Math.isNaN(parsed) ? fallback : parsed;
	}
}
