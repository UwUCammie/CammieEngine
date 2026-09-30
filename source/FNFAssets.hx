package;

// A helper class to make supporting web easier
#if sys
import sys.FileSystem;
import sys.io.File;
#end
import openfl.utils.Assets;
import lime.utils.Assets as LimeAssets;
import lime.app.Future;
import openfl.display.BitmapData;
import openfl.media.Sound;
import haxe.io.Path;
import flixel.FlxG;
import flash.net.FileReference;
import flash.events.Event;
import openfl.events.IOErrorEvent;
import haxe.io.Bytes;
import openfl.utils.AssetType;
using StringTools;
enum Extensions {
	None;
	Json;
	Hscript;
}
/**
 * Assets reader and writer
 */
class FNFAssets {
    public static var _file:FileReference;
	#if sys
	// Keep only successful resolutions. Imports can add a previously-missing
	// file while the game is running, so misses must never be cached.
	static var caseResolvedPaths:Map<String, String> = new Map<String, String>();
	#end

	/**
	 * Resolve one dynamic asset id against the native filesystem using the
	 * case-insensitive semantics donor engines received on Windows.
	 *
	 * A folded match is accepted only when every path component is unique. A
	 * Linux tree containing both `Icon.png` and `icon.png` is ambiguous and is
	 * intentionally left unresolved instead of selecting by directory order.
	 */
	public static function resolveCaseInsensitivePath(id:String):Null<String> {
		#if sys
		if (id == null || StringTools.trim(id) == '' || id.indexOf(String.fromCharCode(0)) >= 0)
			return null;
		var normalized = Path.normalize(id);
		if (normalized == null || normalized == '')
			return null;
		var absolute = Path.normalize(FileSystem.absolutePath(normalized));
		var embedded = Assets.exists(normalized);
		var inScope = isInScope(absolute);
		if (!embedded && !inScope)
			return null;
		if (inScope && FileSystem.exists(absolute))
			return normalized;
		if (caseResolvedPaths.exists(absolute)) {
			var cached = caseResolvedPaths.get(absolute);
			if (cached != null && FileSystem.exists(cached))
				return Path.normalize(cached);
			caseResolvedPaths.remove(absolute);
		}

		var root = Path.normalize(FileSystem.absolutePath(Main.cwd == null ? Sys.getCwd() : Main.cwd));
		if (absolute != root && !absolute.startsWith(root + '/'))
			return embedded ? normalized : null;
		var relative = absolute == root ? '' : absolute.substr(root.length + 1);
		if (relative == '')
			return normalized;
		var current = root;
		for (part in relative.split('/')) {
			if (part == '' || part == '.' || part == '..' || !FileSystem.isDirectory(current))
				return null;
			var matches:Array<String> = [];
			try {
				for (entry in FileSystem.readDirectory(current))
					if (entry.toLowerCase() == part.toLowerCase())
						matches.push(entry);
			} catch (_:Dynamic) {
				return null;
			}
			if (matches.length != 1)
				return null;
			current = Path.join([current, matches[0]]);
		}
		if (!FileSystem.exists(current))
			return embedded ? normalized : null;
		caseResolvedPaths.set(absolute, current);
		return Path.normalize(current);
		#else
		return Assets.exists(id) ? id : null;
		#end
	}
    /**
     * Get text content of a file. 
     * @param id Path to file.
     * @return String The file content. 
     */
	public static function getText(id:String):String {
		id = Path.normalize(id);
	        #if sys
            // if there a library strip it out..
            // future proofing ftw
			if (!isInScope(id))
				throw "Tried to access a file that is out of scope.";
				var resolved = resolveCaseInsensitivePath(id);
				var path:String = null;
				var content:String = null;
				if (resolved != null && FileSystem.exists(FileSystem.absolutePath(resolved)))
					path = resolved;
				else if (Assets.exists(id)) {
					path = Assets.getPath(id);
					content = Assets.getText(id);
				}
			if (path == null)
				throw 'File $id doesn\'t exist or cannot be read.';
			if (content == null) {
			try {
			content = File.getContent(path);
			} catch (e:Any) {
				throw 'File $path doesn\'t exist or cannot be read.';
			}
			}
			return ImportOverlayResolver.applyText(id, content);
            
        #else
            // no need to strip it out... 
            // assets handles it
            return Assets.getText(id);
        #end
    }
	/**
	 * Get json, auto checking extensions.
	 * @param id Path without extension
	 */
	static public function getJson(id:String):Null<String> {
		id = Path.normalize(id);
		if (CoolUtil.JSON_EXT.indexOf(Path.extension(id)) != -1) {
			if (exists(id)) return getText(id);
			id = Path.withoutExtension(id);
		}
		return getAmbigAsset([id], CoolUtil.JSON_EXT, AssetType.TEXT);
	}
	static public function getHscript(id:String):Null<String> {
		// Script folders are optional. Collapse video/../video before asking
		// the filesystem, which otherwise requires the video directory to exist.
		return getAmbigAsset([Path.normalize(id)], CoolUtil.HSCRIPT_EXT, AssetType.TEXT);
	}
	/**
	 * A safer way to get assets. Checks if the first asset exists and if not ALWAYS uses 2nd asset.
	 * This means backupID should be guarenteed to exist. 
	 * @param id The id wanting to be read
	 * @param backupID the id to read if wanted one does not exist
	 * @param type Type of the file 
	 * @return Dynamic The file, in the type requested.
	 */
	public static function getAssetWithBackup(id:String, backupID:String, type:AssetType):Dynamic {
		// backup id should always exist
		if (FNFAssets.exists(id))
			return FNFAssets.getAsset(id, type);
		return FNFAssets.getAsset(backupID, type);
	} 
	/**
	 * Generic way to get assets
	 * @param id The path/id of the item.
	 * @param type The type of the object.
	 * @return Dynamic The file read in the type requested. 
	 */
	public static function getAsset(id:String, type:AssetType):Dynamic {
		switch (type) {
			case TEXT:
				return FNFAssets.getText(id);
			case BINARY:
				return FNFAssets.getBytes(id);
			case MUSIC | SOUND:
				return FNFAssets.getSound(id);
			case IMAGE:
				return FNFAssets.getBitmapData(id);
			default:
				throw "Unsure of how to get type " + type;
		}
	}
	/**
	 * Get an asset that could have multiple names/extensions.
	 * @param id Array of path names
	 * @param ext Array of string for extension.
	 * @param type Type of asset.
	 * @return Dynamic WARNING, if it doesn't find anything it will return null.
	 */
	public static function getAmbigAsset(id:Array<String>, ext:Array<String>, type:AssetType):Dynamic {
		for (path in id) {
			for (ex in ext) {
				if (exists(path + '.' + ex))
					return getAsset(path + '.' + ex, type);
			}
		}
		return null;
	}
	public static function existsAmbig(id:Array<String>, extension:Array<String>):String {
		for (path in id) {
			for (ext in extension) {
				if (exists(path + '.' + ext))
					return path + '.' + ext;
			}
		}
		return '';
	}
	public static function getBytes(id:String):Bytes {
		#if sys
		// if there a library strip it out..
		// future proofing ftw
			if (!isInScope(id))
				throw "Tried to access a file that is out of scope.";
				var resolved = resolveCaseInsensitivePath(id);
				var path:String = null;
				var content:Bytes = null;
				if (resolved != null && FileSystem.exists(FileSystem.absolutePath(resolved)))
					path = resolved;
				else if (Assets.exists(id)) {
					path = Assets.getPath(id);
					content = Assets.getBytes(id);
				}
			if (path == null)
				throw 'File $id doesn\'t exist or cannot be read.';
			if (content == null) {
			try {
			content = File.getBytes(path);
			} catch (e:Any) {
			throw 'File $path doesn\'t exist or cannot be read.';
			}
			}
			return ImportOverlayResolver.applyBytes(id, content);
			
		#else
		// no need to strip it out...
		// assets handles it
		return LimeAssets.getBytes(id);
		#end
	}
    /**
     * Check if the file exists.
     * @param id The file to check
	 * @param ext Extension to auto check against. For fine tune control use "existsAmbig"
     * @return Bool If file exists, true.
     */
    static public function exists(id:String, ?ext:Extensions):Bool {
		switch (ext) {
			case Json: 
				return existsAmbig([id], CoolUtil.JSON_EXT) != '';
			case Hscript: 
				return existsAmbig([id], CoolUtil.HSCRIPT_EXT) != '';
			default: 
				if (!isInScope(id))
					return false;
				#if sys
				var resolved = resolveCaseInsensitivePath(id);
				if (resolved != null && FileSystem.exists(FileSystem.absolutePath(resolved)))
					return true;
				return Assets.exists(id);
				#else
				return Assets.exists(id);
				#end
		}
    }

	// checks for files with the suffix, if found, returns with that suffix, if not, returns the original file
	static public function getFileWithSuffixes(id:String, suffixes:Array<String>, ext:String = 'txt'):String {
		for (suffix in suffixes) {
			if (exists(id + suffix + '.' + ext))
				return id + suffix + '.' + ext;
		}
		if (exists(id + '.' + ext))
			return id + '.' + ext;
		else
			return '';
	}

	/**
	 * Check if a file is in the cwd. Used to prevent sussy bakas from being sussy
	 * @param id 
	 */
	public static function isInScope(id:String) {
		#if sys
		if (Assets.exists(id))
			return true;
		// If path isn't within cwd return false. Do not use String.contains here:
		// `/game-evil/file` must not count as being under `/game`.
		if (id == null || id.indexOf(String.fromCharCode(0)) >= 0)
			return false;
		var absolute = Path.normalize(FileSystem.absolutePath(id));
		var root = Path.normalize(FileSystem.absolutePath(Main.cwd == null ? Sys.getCwd() : Main.cwd));
		if (absolute != root && !absolute.startsWith(root + '/'))
			return false;
		#end
		return true;
	}
    /**
     * Get bitmap data of a file.
     * @param id Path of file
     * @param useCache Whether to reuse assets if file was already requested.
     * @return BitmapData the data of the file.
     */
    public static function getBitmapData(id:String, ?useCache:Bool=true):BitmapData {
        #if sys
			if (!isInScope(id))
				throw "Tried to access a file that is out of scope.";
            // idk if this works lol
				var resolved = resolveCaseInsensitivePath(id);
				var path:String = null;
				if (resolved != null && FileSystem.exists(FileSystem.absolutePath(resolved)))
					path = resolved;
				else if (Assets.exists(id))
					return Assets.getBitmapData(id, useCache);
			if (path == null)
				throw 'File $id doesn\'t exist or cannot be read.';
			var bitmapKey = DiskBitmapCache.key(FileSystem.absolutePath(path));
			return DiskBitmapCache.getOrLoad(bitmapKey, useCache,
				function(key:String):BitmapData {
					var graphic = FlxG.bitmap.get(key);
					var cached = graphic == null || graphic.isDestroyed ? null : graphic.bitmap;
					if (cached != null)
						RuntimeDecodeMetrics.recordHit();
					return cached;
				},
				function():BitmapData {
					var timing = RuntimeDecodeMetrics.enabled;
					var startedAt = timing ? Sys.time() : 0.0;
					try {
						var bitmap = BitmapData.fromFile(path);
						if (timing)
							RuntimeDecodeMetrics.recordMiss((Sys.time() - startedAt) * 1000);
						return bitmap;
					} catch (_:Any) {
						if (timing)
							RuntimeDecodeMetrics.recordMiss((Sys.time() - startedAt) * 1000);
						throw 'File $path doesn\'t exist or cannot be read.';
					}
				},
				function(key:String, data:BitmapData):BitmapData {
					var graphic = FlxG.bitmap.add(data, false, key);
					return graphic == null ? data : graphic.bitmap;
				});
        #else
            return Assets.getBitmapData(id, useCache);
        #end
    }

	/**
     * Get bitmap data of a file, asychronously.
     * @param id Path of file
     * @param useCache Whether to reuse assets if file was already requested. Only works on non-dynamically loaded assets.
     * @return Future<BitmapData> the data of the file, but in the future.
     */
    public static function loadBitmapData(id:String, ?useCache:Bool=true):Future<BitmapData> {
        #if sys
			if (!isInScope(id))
				throw "Tried to access a file that is out of scope.";
            // idk if this works lol
				var resolved = resolveCaseInsensitivePath(id);
				var path:String = null;
				if (resolved != null && FileSystem.exists(FileSystem.absolutePath(resolved)))
					path = resolved;
				else if (Assets.exists(id))
					return Assets.loadBitmapData(id, useCache);
			if (path == null)
				throw 'File $id doesn\'t exist or cannot be read.';
			try {
				return BitmapData.loadFromFile(path);
			} catch (e:Any) {
				throw 'File $path doesn\'t exist or cannot be read.';
			}
        #else
            return Assets.loadBitmapData(id, useCache);
        #end
    }
    /**
     * Get sound from file.
     * @param id Path of file
     * @param useCache whether to reuse assets if file was already requested. Only works on non-dynamically loaded files.
	 * @return Sound The sound file.
     */
    public static function getSound(id:String, ?useCache:Bool=true):Sound {
        #if sys
			if (!isInScope(id))
				throw "Tried to access a file that is out of scope.";
				var resolved = resolveCaseInsensitivePath(id);
				var path:String = null;
				if (resolved != null && FileSystem.exists(FileSystem.absolutePath(resolved)))
					path = resolved;
				else if (Assets.exists(id))
					// Prefer a manifest asset only when no disk file shadows it.
					return Assets.getSound(id, useCache);
			if (path == null)
				throw 'File $id doesn\'t exist or cannot be read.';
		try {
			return Sound.fromFile(path);
		} catch (e:Any) {
			throw 'File $path doesn\'t exist or cannot be read.';
		}
        #else
            return Assets.getSound(id, useCache);
        #end
    }
    /**
     * Save content to a file. 
     * @param id File to save to. 
     * @param data Data to save.
     */
    public static function saveContent(id:String, data:String):Void {
        #if sys
			if (!isInScope(id))
				throw "Tried to access a file that is out of scope.";
			try {
				File.saveContent(id, data);
			} catch(e:Any) {
				throw "Couldn't save to "+ id +". Is it in use?";
			}
        #else
            askToSave(id, data);
        #end
    }
	/**
	 * Save bytes to a file.
	 * @param id File to save to 
	 * @param data Bytes to save. 
	 */
	public static function saveBytes(id:String, data:Bytes) {
		#if sys
		if (!isInScope(id))
			throw "Tried to access a file that is out of scope.";
		try {
			File.saveBytes(id, data);
		} catch (e:Any) {
			throw "Couldn't save to " + id + ". Is it in use?";
		}
		#else
		askToSave(id, data);
		#end
	}
	/**
	 * Ask the user to pick a path to save to. Used on web when other save functions are called.
	 * @param id Path to save to.
	 * @param data Data. Can be anything. 
	 */
	public static function askToSave(id:String, data:Dynamic) {
		_file = new FileReference();

		_file.addEventListener(Event.COMPLETE, onSaveComplete);
		_file.addEventListener(Event.CANCEL, onSaveCancel);
		_file.addEventListener(IOErrorEvent.IO_ERROR, onSaveError);
		var idSus = Path.withoutDirectory(id);
		_file.save(data, idSus);
	}
	static function onSaveComplete(_):Void {
		_file.removeEventListener(Event.COMPLETE, onSaveComplete);
		_file.removeEventListener(Event.CANCEL, onSaveCancel);
		_file.removeEventListener(IOErrorEvent.IO_ERROR, onSaveError);
		_file = null;
		FlxG.log.notice("Successfully saved LEVEL DATA.");
	};
	static function onSaveCancel(_):Void {
		_file.removeEventListener(Event.COMPLETE, onSaveComplete);
		_file.removeEventListener(Event.CANCEL, onSaveCancel);
		_file.removeEventListener(IOErrorEvent.IO_ERROR, onSaveError);
		_file = null;
	};
	static function onSaveError(_):Void {
		_file.removeEventListener(Event.COMPLETE, onSaveComplete);
		_file.removeEventListener(Event.CANCEL, onSaveCancel);
		_file.removeEventListener(IOErrorEvent.IO_ERROR, onSaveError);
		_file = null;
		FlxG.log.error("Problem saving Level data");
	}
}
