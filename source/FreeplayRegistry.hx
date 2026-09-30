package;

import haxe.io.Path;
using StringTools;

#if sys
import sys.FileSystem;
#end

/**
 * Shared access to the Freeplay song registry.
 *
 * A few old destination builds shipped `freeplaySongJson.json` while the
 * current seed uses `freeplaySongJson.jsonc`.  Do not use FNFAssets.getJson()
 * with the extension-less basename here: its generic extension order is
 * intentionally shared by unrelated assets and may select the legacy file
 * before the current JSONC seed.  The registry has one explicit precedence
 * rule instead: an existing JSONC file wins, otherwise an existing JSON file
 * is retained, and a new destination is created as JSONC.
 *
 * Some imported/older packs placed this registry below `assets/images`.  That
 * location is accepted only when the normal `assets/data` destination does
 * not already exist; writes therefore stay beside the file the game actually
 * read and never create a competing registry in another tree.
 */
class FreeplayRegistry {
	public static inline var JSONC_PATH:String = 'assets/data/freeplaySongJson.jsonc';
	public static inline var JSON_PATH:String = 'assets/data/freeplaySongJson.json';
	public static inline var IMAGE_JSONC_PATH:String = 'assets/images/freeplaySongJson.jsonc';
	public static inline var IMAGE_JSON_PATH:String = 'assets/images/freeplaySongJson.json';

	static function candidatePaths():Array<String> {
		return [JSONC_PATH, JSON_PATH, IMAGE_JSONC_PATH, IMAGE_JSON_PATH];
	}

	/** Return true only for a regular file, never for a directory with a file's name. */
	static function fileExists(path:String):Bool {
		if (path == null || StringTools.trim(path) == '')
			return false;
		#if sys
		return FileSystem.exists(path) && !FileSystem.isDirectory(path);
		#else
		return FNFAssets.exists(path);
		#end
	}

	/**
	 * Resolve the one authoritative registry path.
	 *
	 * The first existing candidate is selected, so JSONC wins over JSON in the
	 * same tree and the data tree wins over an old image-tree copy.  If neither
	 * exists, return the current seed path for a first write.
	 */
	public static function getPath():String {
		for (path in candidatePaths())
			if (fileExists(path))
				return path;
		return JSONC_PATH;
	}

	/**
	 * Resolve a registry below an externally selected `assets` directory.
	 * ModPlusCarryState uses this for its legacy donor browser; unlike the
	 * destination resolver it must not accidentally read this game's registry.
	 */
	public static function getPathInRoot(assetsRoot:String):String {
		if (assetsRoot == null || StringTools.trim(assetsRoot) == '')
			return JSONC_PATH;
		var candidates = [
			Path.join([assetsRoot, 'data/freeplaySongJson.jsonc']),
			Path.join([assetsRoot, 'data/freeplaySongJson.json']),
			Path.join([assetsRoot, 'images/freeplaySongJson.jsonc']),
			Path.join([assetsRoot, 'images/freeplaySongJson.json'])
		];
		for (path in candidates)
			if (fileExists(path))
				return path;
		return candidates[0];
	}

	/** Whether either supported registry spelling is already present. */
	public static function exists():Bool {
		for (path in candidatePaths())
			if (fileExists(path))
				return true;
		return false;
	}

	/** Read the selected registry as text.  Missing files retain FNFAssets' error. */
	public static function getText():String {
		return FNFAssets.getText(getPath());
	}

	/** Read the selected registry as JSON/JSONC. */
	public static function getJson():Dynamic {
		return CoolUtil.parseJson(getText());
	}

	/** Write beside the registry selected by getPath(). */
	public static function saveContent(data:String):Void {
		FNFAssets.saveContent(getPath(), data);
	}

	/** Encode and write a registry without changing its selected extension/path. */
	public static function saveJson(data:Dynamic):Void {
		saveContent(CoolUtil.stringifyJson(data));
	}
}
