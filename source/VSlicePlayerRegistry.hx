package;

#if sys
import sys.FileSystem;
import sys.io.File;
#end

/**
	V-Slice's `PlayerRegistry.instance`. Playable-character records are read
	from an owner's `data/players/<id>.json` when the mod ships one. The base
	game's own players (bf and pico) always exist in V-Slice, so they answer
	with a default record when no mod ships one; any other unknown id is null,
	as in V-Slice.
*/
@:keep
class VSlicePlayerRegistry {
	public static var instance(get, never):VSlicePlayerRegistry;
	static var shared:VSlicePlayerRegistry;

	static function get_instance():VSlicePlayerRegistry {
		if (shared == null)
			shared = new VSlicePlayerRegistry();
		return shared;
	}

	function new() {}

	/** Player ids the base game always registers. */
	static final BASE_PLAYERS:Array<String> = ['bf', 'pico'];

	/** Character id to owning player id, rebuilt after an import changes the
	 * installed records. Freeplay can ask for every capsule every frame. */
	static var ownerByCharacter:Map<String, String> = null;
	/** The owner roots the map was read from. They follow the active package
	 * and song, so a map built for one package must not answer for another. */
	static var ownerByCharacterRoots:String = null;

	/** Forget remembered records, for example after an import. */
	public static function invalidate():Void {
		ownerByCharacter = null;
		ownerByCharacterRoots = null;
	}

	public function fetchEntry(id:String):Null<VSlicePlayerEntry> {
		var key = id == null ? '' : StringTools.trim(id).toLowerCase();
		if (key == '' || key.indexOf('/') >= 0 || key.indexOf('\\') >= 0 || key.indexOf('..') >= 0)
			return null;
		var data = readPlayer(key);
		if (data == null && BASE_PLAYERS.indexOf(key) < 0)
			return null;
		return new VSlicePlayerEntry(key, data);
	}

	public function hasEntry(id:String):Bool
		return fetchEntry(id) != null;

	public function listEntryIds():Array<String> {
		var result:Array<String> = [];
		#if sys
		for (root in ownerRoots()) {
			var folder = root + '/data/players';
			try {
				if (!FileSystem.isDirectory(folder))
					continue;
				for (file in FileSystem.readDirectory(folder))
					if (StringTools.endsWith(file.toLowerCase(), '.json')) {
						var id = file.substr(0, file.length - 5).toLowerCase();
						if (result.indexOf(id) < 0)
							result.push(id);
					}
			} catch (_:Dynamic) {}
		}
		#end
		return result;
	}

	/** The player whose record owns a character id, or null when none does (as in V-Slice). */
	public function getCharacterOwnerId(characterId:Null<String>):Null<String> {
		if (characterId == null)
			return null;
		var roots = ownerRoots().join('\n');
		if (ownerByCharacter == null || roots != ownerByCharacterRoots) {
			var owners = new Map<String, String>();
			for (id in listEntryIds()) {
				var entry = fetchEntry(id);
				if (entry != null)
					for (owned in entry.getOwnedCharacterIds())
						if (!owners.exists(owned))
							owners.set(owned, id);
			}
			ownerByCharacter = owners;
			ownerByCharacterRoots = roots;
		}
		var owner = ownerByCharacter.get(characterId.toLowerCase());
		return owner == null ? null : owner;
	}

	public function isCharacterOwned(characterId:String):Bool
		return getCharacterOwnerId(characterId) != null;

	public function hasNewCharacter():Bool
		return false;

	public function listNewCharacters():Array<String>
		return [];

	public function countUnlockedCharacters():Int
		return listEntryIds().length;

	static function ownerRoots():Array<String> {
		var roots:Array<String> = [];
		try roots = VSliceRegistryCatalog.ownerRoots() catch (_:Dynamic) {}
		return roots == null ? [] : roots;
	}

	static function readPlayer(id:String):Dynamic {
		#if sys
		for (root in ownerRoots()) {
			var path = root + '/data/players/' + id + '.json';
			try {
				if (FileSystem.exists(path) && !FileSystem.isDirectory(path)
					&& FileSystem.stat(path).size <= VSliceRegistryCatalog.MAX_PROVENANCE_BYTES) {
					var parsed:Dynamic = haxe.Json.parse(File.getContent(path));
					if (parsed != null && Type.typeof(parsed) == TObject)
						return parsed;
				}
			} catch (_:Dynamic) {}
		}
		#end
		return null;
	}
}

/** V-Slice `PlayableCharacter`: the fields freeplay and results scripts read. */
@:keep
class VSlicePlayerEntry {
	public var id(default, null):String;
	var data:Dynamic;

	public function new(id:String, data:Dynamic) {
		this.id = id;
		this.data = data;
	}

	public function getName():String {
		var name:Dynamic = data == null ? null : Reflect.field(data, 'name');
		return name == null ? id : Std.string(name);
	}

	public function getOwnedCharacterIds():Array<String> {
		var owned:Dynamic = data == null ? null : Reflect.field(data, 'ownedChars');
		var result:Array<String> = [];
		if (Std.isOfType(owned, Array))
			for (value in (cast owned:Array<Dynamic>))
				if (value != null)
					result.push(Std.string(value).toLowerCase());
		if (result.length == 0)
			result.push(id);
		return result;
	}

	public function shouldShowUnownedChars():Bool
		return data != null && Reflect.field(data, 'showUnownedChars') == true;

	public function shouldShowCharacter(id:String):Bool
		return getOwnedCharacterIds().indexOf(id == null ? '' : id.toLowerCase()) >= 0 || shouldShowUnownedChars();

	public function getFreeplayStyleID():String {
		var style:Dynamic = data == null ? null : Reflect.field(data, 'freeplayStyle');
		return style == null ? id : Std.string(style);
	}

	public function getStickerPackID():String {
		var pack:Dynamic = data == null ? null : Reflect.field(data, 'stickerPack');
		return pack == null ? 'default' : Std.string(pack);
	}

	public function getFreeplayDJData():Dynamic
		return data == null ? null : Reflect.field(data, 'freeplayDJ');

	/** freeplayDJ.text1..text3 of the record; '' when the mod does not author them. */
	public function getFreeplayDJText(index:Int):String {
		var dj = getFreeplayDJData();
		var text:Dynamic = dj == null ? null : Reflect.field(dj, 'text' + index);
		return text == null ? '' : Std.string(text);
	}

	public function getCharSelectData():Dynamic
		return data == null ? null : Reflect.field(data, 'charSelect');

	public function isUnlocked():Bool
		return data == null || Reflect.field(data, 'unlocked') != false;
}
