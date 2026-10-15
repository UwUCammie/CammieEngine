package;

import VSliceRegistryCatalog.VSliceCatalogSong;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

/**
	V-Slice's `SongRegistry.instance` for imported scripts. Songs come from the
	engine's installed charts through VSliceRegistryCatalog; nothing here loads
	or plays a chart, so a menu can browse freely and hand the result to
	`LoadingState.loadPlayState`, which starts the song the engine's own way.
*/
@:keep
class VSliceSongRegistry {
	public static var instance(get, never):VSliceSongRegistry;
	static var shared:VSliceSongRegistry;

	static function get_instance():VSliceSongRegistry {
		if (shared == null)
			shared = new VSliceSongRegistry();
		return shared;
	}

	function new() {}

	/** `fetchEntry(id, {variation: ...})`; null when no installed chart has that id. */
	public function fetchEntry(id:String, ?params:Dynamic):Null<VSliceSongEntry> {
		var song = VSliceRegistryCatalog.findSong(id);
		if (song == null)
			return null;
		var variation:Dynamic = params == null ? null : Reflect.field(params, 'variation');
		return new VSliceSongEntry(song, variation == null ? null : Std.string(variation));
	}

	public function hasEntry(id:String):Bool
		return VSliceRegistryCatalog.findSong(id) != null;

	public function listEntryIds():Array<String>
		return VSliceRegistryCatalog.listSongIds();

	public function listBaseGameEntryIds():Array<String>
		return listEntryIds();

	public function listModdedEntryIds():Array<String>
		return [];

	public function countEntries():Int
		return listEntryIds().length;

	/** Music metadata authored as JSON text (timeChanges, songName, artist). */
	public function parseMusicDataRaw(contents:String, ?fileName:String):Dynamic {
		if (contents == null || StringTools.trim(contents) == '')
			return null;
		try {
			var parsed:Dynamic = haxe.Json.parse(contents);
			if (parsed == null || Type.typeof(parsed) != TObject)
				return null;
			if (!Std.isOfType(Reflect.field(parsed, 'timeChanges'), Array))
				Reflect.setField(parsed, 'timeChanges', []);
			return parsed;
		} catch (_:Dynamic) {
			return null;
		}
	}

	/**
		Music metadata by id (`music/<id>/<id>-metadata.json` in the active owner)
		or by an explicit JSON path. Missing files give null, as in V-Slice.
	*/
	public function parseMusicData(id:String, ?variation:String):Dynamic {
		#if sys
		if (id == null || StringTools.trim(id) == '')
			return null;
		var clean = StringTools.replace(StringTools.trim(id), '\\', '/');
		if (clean.indexOf('..') >= 0)
			return null;
		var candidates:Array<String> = [];
		var suffix = variation == null || variation == '' || variation == 'default' ? '' : '-' + variation;
		if (StringTools.endsWith(clean.toLowerCase(), '.json')) {
			candidates.push(clean);
		} else if (clean.indexOf('/') < 0) {
			var roots:Array<String> = [];
			try roots = VSliceRegistryCatalog.ownerRoots() catch (_:Dynamic) {}
			for (root in roots)
				if (root != null && root != '')
					candidates.push(root + '/music/' + clean + '/' + clean + '-metadata' + suffix + '.json');
			candidates.push('assets/music/' + clean + '/' + clean + '-metadata' + suffix + '.json');
		}
		for (path in candidates) {
			try {
				if (FileSystem.exists(path) && !FileSystem.isDirectory(path)
					&& FileSystem.stat(path).size <= VSliceRegistryCatalog.MAX_PROVENANCE_BYTES)
					return parseMusicDataRaw(File.getContent(path), path);
			} catch (_:Dynamic) {}
		}
		#end
		return null;
	}
}

/** V-Slice `Song`: one song id with its variations and difficulties. */
@:keep
class VSliceSongEntry {
	public var id(default, null):String;
	/** Variation requested through fetchEntry params, if any. */
	public var variation:Null<String>;
	public var validScore:Bool = true;
	public var variations(get, never):Array<String>;
	public var songName(get, never):String;
	public var songArtist(get, never):String;
	public var charter(get, never):String;
	/** Owner root that installed this song, or '' for a base-game song. */
	public var ownerRoot(get, never):String;
	var song:VSliceCatalogSong;

	public function new(song:VSliceCatalogSong, ?variation:String) {
		this.song = song;
		this.id = song.id;
		this.variation = variation == null || variation == '' ? null : variation.toLowerCase();
	}

	function get_variations():Array<String>
		return song.variationOrder.copy();

	function get_ownerRoot():String
		return song.owner;

	function get_songName():String {
		var folder = storageFolder(variation);
		var display = folder == null ? null : song.display.get(folder);
		return display == null ? id : display;
	}

	function get_songArtist():String {
		var info = VSliceRegistryCatalog.chartInfo(storageFolder(variation), null);
		return info == null ? '' : info.songArtist;
	}

	function get_charter():String
		return '';

	/** Installed chart folder for a variation; the default folder when it has no such variation. */
	public function storageFolder(?variationId:String):Null<String> {
		var key = variationId == null || variationId == '' ? 'default' : variationId.toLowerCase();
		if (song.variations.exists(key))
			return song.variations.get(key);
		if (song.variations.exists('default'))
			return song.variations.get('default');
		return song.variationOrder.length == 0 ? null : song.variations.get(song.variationOrder[0]);
	}

	/** Whether this exact variation was installed (no fallback to the default folder). */
	public function hasVariation(variationId:String):Bool
		return variationId != null && song.variations.exists(variationId.toLowerCase());

	public function getDifficulty(?diffId:String, ?variationId:String, ?variationIds:Array<String>):Null<VSliceSongDifficulty> {
		var difficulty = diffId == null || diffId == '' ? StringTools.trim(VSliceRegistryCatalog.defaultDifficulty()).toLowerCase()
			: diffId.toLowerCase();
		for (candidate in candidateVariations(variationId, variationIds)) {
			if (!song.variations.exists(candidate))
				continue;
			var folder = song.variations.get(candidate);
			if (VSliceRegistryCatalog.hasChart(folder, difficulty))
				return new VSliceSongDifficulty(this, difficulty, candidate, folder);
		}
		return null;
	}

	public function hasDifficulty(diffId:String, ?variationId:String, ?variationIds:Array<String>):Bool
		return getDifficulty(diffId, variationId, variationIds) != null;

	public function listDifficulties(?variationId:String, ?variationIds:Array<String>, showLocked:Bool = false,
		showHidden:Bool = false):Array<String> {
		var result:Array<String> = [];
		var candidates = variationId == null && variationIds == null ? song.variationOrder : candidateVariations(variationId, variationIds);
		for (candidate in candidates) {
			if (!song.variations.exists(candidate))
				continue;
			for (difficulty in VSliceRegistryCatalog.folderDifficulties(song.variations.get(candidate)))
				if (result.indexOf(difficulty) < 0)
					result.push(difficulty);
		}
		return result;
	}

	public function listSuffixedDifficulties(variationIds:Array<String>, ?showLocked:Bool, ?showHidden:Bool):Array<String>
		return listDifficulties(null, variationIds, showLocked == true, showHidden == true);

	public function getFirstValidVariation(?diffId:String, ?currentCharacter:Dynamic, ?possibleVariations:Array<String>):Null<String> {
		var candidates = possibleVariations != null ? possibleVariations : song.variationOrder;
		var difficulty = diffId == null || diffId == '' ? StringTools.trim(VSliceRegistryCatalog.defaultDifficulty()).toLowerCase()
			: diffId.toLowerCase();
		for (candidate in candidates) {
			var key = candidate == null ? '' : candidate.toLowerCase();
			if (song.variations.exists(key) && VSliceRegistryCatalog.hasChart(song.variations.get(key), difficulty))
				return key;
		}
		return null;
	}

	/** The engine keeps no per-character variation ownership, so every installed variation is offered. */
	public function getVariationsByCharacter(?char:Dynamic):Array<String>
		return song.variationOrder.copy();

	public function getVariationsByCharacterId(?charId:String):Array<String>
		return song.variationOrder.copy();

	public function isSongNew(currentDifficulty:String, currentVariation:String):Bool
		return false;

	public function isDifficultyVisible(diffId:String, variationId:String):Bool
		return hasDifficulty(diffId, variationId);

	/** Each installed variation carries its own instrumental, so the base id is always ''. */
	public function getBaseInstrumentalId(difficultyId:String, variationId:String):String
		return '';

	public function listAltInstrumentalIds(difficultyId:String, variationId:String):Array<String>
		return [];

	public function cacheCharts(force:Bool = false):Void {}

	public function clearCharts():Void {}

	public function isDiscordRPCAnonymous():Bool
		return false;

	/** V-Slice metadata shape, one record per installed variation. */
	public function getRawMetadata():Array<Dynamic> {
		var result:Array<Dynamic> = [];
		for (candidate in song.variationOrder) {
			var folder = song.variations.get(candidate);
			var difficulties = VSliceRegistryCatalog.folderDifficulties(folder);
			var info = VSliceRegistryCatalog.chartInfo(folder, difficulties.length == 0 ? null : difficulties[0]);
			result.push({
				songName: song.display.exists(folder) ? song.display.get(folder) : id,
				artist: info == null ? '' : info.songArtist,
				variation: candidate,
				playData: {
					difficulties: difficulties,
					stage: info == null ? '' : info.stage,
					noteStyle: info == null ? '' : info.noteStyle,
					album: info == null ? '' : info.album,
					characters: {
						player: info == null ? '' : info.player,
						opponent: info == null ? '' : info.opponent,
						girlfriend: info == null ? '' : info.girlfriend,
						instrumental: '',
						altInstrumentals: []
					}
				},
				timeChanges: [{t: 0, bpm: info == null ? 100 : info.bpm}]
			});
		}
		return result;
	}

	function candidateVariations(variationId:String, variationIds:Array<String>):Array<String> {
		var result:Array<String> = [];
		function add(value:String):Void {
			var key = value == null || value == '' ? '' : value.toLowerCase();
			if (key != '' && result.indexOf(key) < 0)
				result.push(key);
		}
		add(variationId);
		if (variationIds != null)
			for (value in variationIds)
				add(value);
		if (result.length == 0) {
			add(variation);
			add('default');
		}
		return result;
	}
}

/** V-Slice `SongDifficulty`: the header of one installed chart. */
@:keep
class VSliceSongDifficulty {
	public var song(default, null):VSliceSongEntry;
	public var difficulty(default, null):String;
	public var variation(default, null):String;
	/** Installed chart folder; the engine loads `<folder>[-<difficulty>]`. */
	public var storageFolder(default, null):String;
	public var songName:String;
	public var songArtist:String;
	public var charter:String = '';
	public var stage:String;
	public var noteStyle:String;
	public var scrollSpeed:Float;
	public var album:Null<String>;
	public var characters:Dynamic;
	public var timeChanges:Array<Dynamic>;
	public var difficultyRating:Int = 0;
	public var looped:Bool = false;
	public var stickerPack:Null<String> = null;
	public var discordRPCImage:Null<String> = null;

	public function new(song:VSliceSongEntry, difficulty:String, variation:String, folder:String) {
		this.song = song;
		this.difficulty = difficulty;
		this.variation = variation;
		this.storageFolder = folder;
		var info = VSliceRegistryCatalog.chartInfo(folder, difficulty);
		songName = song.songName;
		songArtist = info == null ? '' : info.songArtist;
		stage = info == null ? '' : info.stage;
		noteStyle = info == null ? '' : info.noteStyle;
		scrollSpeed = info == null ? 1 : info.scrollSpeed;
		album = info == null || info.album == '' ? null : info.album;
		characters = {
			player: info == null ? '' : info.player,
			opponent: info == null ? '' : info.opponent,
			girlfriend: info == null ? '' : info.girlfriend,
			instrumental: '',
			altInstrumentals: []
		};
		timeChanges = [{t: 0, bpm: info == null ? 100 : info.bpm}];
	}

	public function getStartingBPM():Float
		return timeChanges.length == 0 ? 100 : timeChanges[0].bpm;

	public function cacheInst(?instrumental:String):Void {}

	public function cacheVocals():Void {}

	public function clearChart():Void {}
}
