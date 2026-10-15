package;

import ImportedStoryWeeks.ImportedStoryWeek;

/**
	V-Slice's `LevelRegistry.instance`. Levels are the story weeks the importer
	recorded for each owner, so a custom story menu lists and starts the same
	weeks the engine's Story Mode shows.
*/
@:keep
class VSliceLevelRegistry {
	public static var instance(get, never):VSliceLevelRegistry;
	static var shared:VSliceLevelRegistry;

	static function get_instance():VSliceLevelRegistry {
		if (shared == null)
			shared = new VSliceLevelRegistry();
		return shared;
	}

	function new() {}

	public function fetchEntry(id:String, ?params:Dynamic):Null<VSliceLevelEntry> {
		var key = id == null ? '' : StringTools.trim(id).toLowerCase();
		if (key == '')
			return null;
		for (week in VSliceRegistryCatalog.levels())
			if (levelId(week).toLowerCase() == key)
				return new VSliceLevelEntry(week);
		return null;
	}

	public function hasEntry(id:String):Bool
		return fetchEntry(id) != null;

	/** Level ids in the order their owner authored them. */
	public function listSortedLevelIds():Array<String> {
		var result:Array<String> = [];
		for (week in VSliceRegistryCatalog.levels()) {
			var id = levelId(week);
			if (result.indexOf(id) < 0)
				result.push(id);
		}
		return result;
	}

	public function listEntryIds():Array<String>
		return listSortedLevelIds();

	public function listBaseGameEntryIds():Array<String>
		return listSortedLevelIds();

	public function countEntries():Int
		return listSortedLevelIds().length;

	/** A week's key is '<owner namespace>:<level file>'; scripts know the level file. */
	public static function levelId(week:ImportedStoryWeek):String {
		var separator = week.key.lastIndexOf(':');
		return separator < 0 ? week.key : week.key.substr(separator + 1);
	}
}

/** V-Slice `Level`: title, songs and lock state of one story week. */
@:keep
class VSliceLevelEntry {
	public var id(default, null):String;
	/** Read with privateAccess by some scripts; mirrors the authored level data fields. */
	public var _data(default, null):Dynamic;
	var week:ImportedStoryWeek;

	public function new(week:ImportedStoryWeek) {
		this.week = week;
		this.id = VSliceLevelRegistry.levelId(week);
		_data = {name: week.title, songs: week.songs.copy(), titleAsset: week.art, visible: true};
	}

	/** Installed song folders; SongRegistry.fetchEntry accepts them as ids. */
	public function getSongs():Array<String>
		return week.songs.copy();

	public function getTitle():String
		return week.title;

	public function getCapsuleTitle():String
		return week.title;

	public function getSongDisplayNames(?difficulty:String):Array<String> {
		var result:Array<String> = [];
		for (folder in week.songs) {
			var song = VSliceSongRegistry.instance.fetchEntry(folder);
			result.push(song == null ? folder : song.songName);
		}
		return result;
	}

	public function isUnlocked():Bool
		return !VSliceRegistryCatalog.levelLocked(week);

	public function isVisible():Bool
		return true;

	/** Difficulties every song of the level has, in the first song's order. */
	public function getDifficulties():Array<String> {
		var result:Array<String> = null;
		for (folder in week.songs) {
			var available = VSliceRegistryCatalog.folderDifficulties(folder);
			if (result == null)
				result = available;
			else
				result = [for (difficulty in result) if (available.indexOf(difficulty) >= 0) difficulty];
		}
		return result == null ? [] : result;
	}

	public function isBackgroundSimple():Bool
		return true;
}
