package;

import haxe.io.Path;
import PsychFamilyWeekImport.PsychFamilyStoryWeek;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

/** One Story Mode week contributed by an installed import. */
typedef ImportedStoryWeek = {
	/** Score and unlock identity: '<owner namespace>:<week file>'. */
	var key:String;
	var owner:String;
	var title:String;
	/** Installed song folders under assets/data, in week order. */
	var songs:Array<String>;
	var characters:Array<String>;
	var startUnlocked:Bool;
	/** Score key of the week that unlocks this one, or ''. */
	var unlockAfter:String;
	var hiddenUntilUnlocked:Bool;
	/** Title image path, or '' when the owner has none. */
	var art:String;
}

/** An imported week Story Mode lists, with its lock state. */
typedef ImportedStoryMenuWeek = {
	var week:ImportedStoryWeek;
	var locked:Bool;
}

/** Story weeks of Psych-family imports. The importer stores the converted
 * weeks next to the owner's other files, so removing the owner removes its
 * weeks too and the shared storySonglist.json is never rewritten. The record
 * keeps source song keys plus the folder each one was installed to; a week
 * only shows songs that are still installed. */
class ImportedStoryWeeks {
	public static inline var FILE_NAME:String = '.cammie-story-weeks.json';
	public static inline var VERSION:Int = 1;
	public static inline var MAX_RECORD_BYTES:Int = 262144;
	public static inline var MAX_OWNERS:Int = 1024;
	public static inline var OWNER_PREFIX:String = 'assets/imported_mods';

	/** Combine this import's weeks with the record an earlier import of the
	 * same owner left. Song mappings accumulate because one owner can be
	 * imported in several batches; weeks are replaced because they are always
	 * read from the whole source folder. */
	public static function merge(existing:String, engine:String, weeks:Array<PsychFamilyStoryWeek>,
		songs:Map<String, String>):String {
		var mapped:Map<String, String> = [];
		var previous = parse(existing);
		if (previous != null && Reflect.field(previous, 'engine') == engine) {
			var oldSongs:Dynamic = Reflect.field(previous, 'songs');
			if (oldSongs != null && Type.typeof(oldSongs) == TObject)
				for (field in Reflect.fields(oldSongs)) {
					var value:Dynamic = Reflect.field(oldSongs, field);
					if (Std.isOfType(value, String) && safeFolder(value)) mapped.set(field, value);
				}
			if (weeks == null) {
				var oldWeeks:Dynamic = Reflect.field(previous, 'weeks');
				if (Std.isOfType(oldWeeks, Array)) weeks = cast oldWeeks;
			}
		}
		if (songs != null) for (key in songs.keys()) {
			var folder = songs.get(key);
			if (key != '' && safeFolder(folder)) mapped.set(key, folder);
		}
		var keys = [for (key in mapped.keys()) key];
		keys.sort(Reflect.compare);
		var songObject:Dynamic = {};
		for (key in keys) Reflect.setField(songObject, key, mapped.get(key));
		return haxe.Json.stringify({version:VERSION, engine:engine, weeks:weeks == null ? [] : weeks,
			songs:songObject}, null, '\t');
	}

	/** Weeks one owner record offers, keeping only installed songs.
	 * `installed` answers whether assets/data/<folder> is present and `exists`
	 * whether an owner file is present. */
	public static function fromRecord(owner:String, content:String, installed:String->Bool,
		exists:String->Bool):Array<ImportedStoryWeek> {
		var result:Array<ImportedStoryWeek> = [];
		var record = parse(content);
		if (record == null || owner == null || owner == '') return result;
		var namespace = Path.withoutDirectory(Path.removeTrailingSlashes(StringTools.replace(owner, '\\', '/')));
		var songs:Dynamic = Reflect.field(record, 'songs');
		var weeks:Dynamic = Reflect.field(record, 'weeks');
		if (!Std.isOfType(weeks, Array) || songs == null || Type.typeof(songs) != TObject) return result;
		for (raw in (cast weeks:Array<Dynamic>)) {
			if (raw == null || Type.typeof(raw) != TObject) continue;
			var file = text(raw, 'file');
			if (file == '' || !safeFolder(file)) continue;
			var folders:Array<String> = [];
			var authored:Dynamic = Reflect.field(raw, 'songs');
			if (Std.isOfType(authored, Array)) for (song in (cast authored:Array<Dynamic>)) {
				if (!Std.isOfType(song, String)) continue;
				var folder:Dynamic = Reflect.field(songs, song);
				if (Std.isOfType(folder, String) && safeFolder(folder) && installed(folder)) folders.push(folder);
			}
			if (folders.length == 0) continue;
			var characters:Array<String> = [];
			var authoredCharacters:Dynamic = Reflect.field(raw, 'characters');
			for (slot in 0...3) {
				var value:Dynamic = Std.isOfType(authoredCharacters, Array) ? (cast authoredCharacters:Array<Dynamic>)[slot] : null;
				characters.push(Std.isOfType(value, String) ? value : '');
			}
			var before = text(raw, 'weekBefore');
			var art = text(raw, 'art');
			var artPath = art != '' && art.indexOf('..') < 0 && !Path.isAbsolute(art) ? owner + '/' + art : '';
			result.push({
				key:namespace + ':' + file,
				owner:owner,
				title:text(raw, 'storyName'),
				songs:folders,
				characters:characters,
				startUnlocked:Reflect.field(raw, 'startUnlocked') == true,
				unlockAfter:before == '' ? '' : (Reflect.field(raw, 'weekBeforeLocal') == true ? namespace + ':' + before : before),
				hiddenUntilUnlocked:Reflect.field(raw, 'hiddenUntilUnlocked') == true,
				art:artPath != '' && exists(artPath) ? artPath : ''
			});
		}
		return result;
	}

	/** The imported weeks Story Mode lists, in order, with their lock state.
	 * The source engines' lock rule applies, and a locked week marked
	 * hiddenUntilUnlocked is left out. A previous week that is not installed
	 * here (neither a base week nor an imported one) can never be completed,
	 * so it does not lock. */
	public static function menuWeeks(weeks:Array<ImportedStoryWeek>, baseWeekNames:Array<String>,
		ignoreUnlocks:Bool, completed:String->Bool):Array<ImportedStoryMenuWeek> {
		var result:Array<ImportedStoryMenuWeek> = [];
		if (weeks == null) return result;
		var known:Map<String, Bool> = [];
		if (baseWeekNames != null) for (name in baseWeekNames) if (name != null) known.set(name, true);
		for (week in weeks) if (week != null) known.set(week.key, true);
		for (week in weeks) {
			if (week == null) continue;
			var locked = !ignoreUnlocks && known.exists(week.unlockAfter)
				&& PsychFamilyWeekImport.locked(week.startUnlocked, week.unlockAfter, completed);
			if (locked && week.hiddenUntilUnlocked) continue;
			result.push({week:week, locked:locked});
		}
		return result;
	}

	#if sys
	/** Write or update one owner's record. Returns false when it could not be saved. */
	public static function write(owner:String, engine:String, weeks:Array<PsychFamilyStoryWeek>,
		songs:Map<String, String>):Bool {
		if (owner == null || owner == '') return false;
		var path = Path.join([owner, FILE_NAME]);
		var existing:String = null;
		try {
			if (FileSystem.exists(path) && FileSystem.stat(path).size <= MAX_RECORD_BYTES)
				existing = File.getContent(path);
		} catch (_:Dynamic) {}
		// An owner without weeks gets no record unless an earlier import made one.
		if (existing == null && (weeks == null || weeks.length == 0)) return true;
		try {
			if (!FileSystem.exists(owner)) FileSystem.createDirectory(owner);
			var content = merge(existing, engine, weeks, songs);
			if (content != existing) File.saveContent(path, content);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Every installed owner's story weeks, owners in name order. */
	public static function collect(?root:String):Array<ImportedStoryWeek> {
		var result:Array<ImportedStoryWeek> = [];
		var base = root == null ? OWNER_PREFIX : root;
		var owners:Array<String> = [];
		try {
			if (!FileSystem.isDirectory(base)) return result;
			owners = FileSystem.readDirectory(base);
		} catch (_:Dynamic) { return result; }
		owners.sort(Reflect.compare);
		if (owners.length > MAX_OWNERS) owners = owners.slice(0, MAX_OWNERS);
		function exists(path:String):Bool {
			try return FileSystem.exists(path) catch (_:Dynamic) return false;
		}
		function installed(folder:String):Bool {
			try return FileSystem.isDirectory('assets/data/' + folder) catch (_:Dynamic) return false;
		}
		for (name in owners) {
			if (!safeFolder(name)) continue;
			var owner = base + '/' + name;
			var path = owner + '/' + FILE_NAME;
			try {
				if (!FileSystem.exists(path) || FileSystem.isDirectory(path)
					|| FileSystem.stat(path).size > MAX_RECORD_BYTES) continue;
				for (week in fromRecord(owner, File.getContent(path), installed, exists)) result.push(week);
			} catch (_:Dynamic) {
				// One unreadable record never hides other owners' weeks.
			}
		}
		return result;
	}
	#else
	/** Imports only exist where there is a filesystem. */
	public static function collect(?root:String):Array<ImportedStoryWeek>
		return [];
	#end

	static function parse(text:String):Dynamic {
		if (text == null || text == '') return null;
		try {
			var value:Dynamic = haxe.Json.parse(text);
			return value != null && Type.typeof(value) == TObject && Reflect.field(value, 'version') == VERSION ? value : null;
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function text(value:Dynamic, field:String):String {
		var found:Dynamic = Reflect.field(value, field);
		return Std.isOfType(found, String) ? StringTools.trim(found) : '';
	}

	static function safeFolder(value:String):Bool
		return value != null && value != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0;
}
