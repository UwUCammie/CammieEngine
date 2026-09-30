package;

import flixel.FlxG;
import flixel.graphics.frames.FlxAtlasFrames;
import DynamicSprite.DynamicAtlasFrames;
import openfl.utils.AssetType;
import openfl.utils.Assets as OpenFlAssets;

class Paths
{
	inline public static var SOUND_EXT = #if web "mp3" #else "ogg" #end;

	static var currentLevel:String;
	// Cache only successful case-folded resolutions.  Misses are deliberately
	// not cached because Import Settings may add the requested file later in the
	// same process.
	static var caseResolvedPaths:Map<String, String> = new Map();

	static public function setCurrentLevel(name:String)
	{
		currentLevel = name.toLowerCase();
	}

	static function getPath(file:String, type:AssetType, library:Null<String>)
	{
		if (library != null)
			return getLibraryPath(file, library);

		if (currentLevel != null)
		{
			var levelPath = getLibraryPathForce(file, currentLevel);
			if (OpenFlAssets.exists(levelPath, type))
				return levelPath;

			levelPath = getLibraryPathForce(file, "shared");
			if (OpenFlAssets.exists(levelPath, type))
				return levelPath;
		}

		return getPreloadPath(file);
	}

	static public function getLibraryPath(file:String, library = "preload")
	{
		return if (library == "preload" || library == "default") getPreloadPath(file); else getLibraryPathForce(file, library);
	}

	inline static function getLibraryPathForce(file:String, library:String)
	{
		return '$library:assets/$library/$file';
	}

	inline static function getPreloadPath(file:String)
	{
		return resolveCaseInsensitivePath('assets/$file');
	}

	/**
		Windows-era Psych/Kade/FPS packs often spell an asset id differently from
		the directory entry they ship (for example `whittyback` versus
		`whittyBack.png`).  The old runtime got away with that on Windows, but a
		Linux build passes the path straight to Flixel and fails to load it.  Keep
		the authored path when it exists, and otherwise resolve each directory
		component against the actual native tree.  Embedded OpenFL ids are left
		untouched because this only changes paths which are present on disk.
	*/
	static function resolveCaseInsensitivePath(path:String):String
	{
		#if sys
		if (path == null || path == '')
			return path;
		var normalized = haxe.io.Path.normalize(path);
		if (sys.FileSystem.exists(normalized) || OpenFlAssets.exists(normalized))
			return normalized;
		if (caseResolvedPaths.exists(normalized))
		{
			var cached = caseResolvedPaths.get(normalized);
			if (cached != null && sys.FileSystem.exists(cached))
				return cached;
			caseResolvedPaths.remove(normalized);
		}

		var parent = haxe.io.Path.directory(normalized);
		var name = haxe.io.Path.withoutDirectory(normalized);
		if (parent == null || parent == '' || parent == normalized || name == null || name == '')
			return path;
		var resolvedParent = resolveCaseInsensitivePath(parent);
		if (!sys.FileSystem.exists(resolvedParent) || !sys.FileSystem.isDirectory(resolvedParent))
			return path;
		try
		{
			var entries = sys.FileSystem.readDirectory(resolvedParent);
			entries.sort(function(a:String, b:String):Int
			{
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			var matched:String = null;
			for (entry in entries)
			{
				if (entry.toLowerCase() == name.toLowerCase())
				{
					var candidate = haxe.io.Path.join([resolvedParent, entry]);
					if (sys.FileSystem.exists(candidate))
					{
						// A Linux tree can contain two names that collapse to the
						// same Windows spelling.  Guessing between them would make
						// the selected artwork depend on directory iteration order;
						// keep the authored path unresolved so the normal missing-
						// asset diagnostics can report the ambiguity instead.
						if (matched != null && matched != candidate)
							return path;
						matched = candidate;
					}
				}
			}
			if (matched != null)
			{
				caseResolvedPaths.set(normalized, matched);
				return matched;
			}
		}
		catch (_:Dynamic) {}
		#end
		return path;
	}

	inline static public function file(file:String, type:AssetType = TEXT, ?library:String)
	{
		return getPath(file, type, library);
	}

	inline static public function txt(key:String, ?library:String)
	{
		return getPath('data/$key.txt', TEXT, library);
	}

	inline static public function xml(key:String, ?library:String)
	{
		return getPath('data/$key.xml', TEXT, library);
	}

	inline static public function json(key:String, ?library:String)
	{
		return getPath('data/$key.json', TEXT, library);
	}

	static public function sound(key:String, ?library:String)
	{
		return getPath('sounds/$key.$SOUND_EXT', SOUND, library);
	}

	inline static public function soundRandom(key:String, min:Int, max:Int, ?library:String)
	{
		return sound(key + FlxG.random.int(min, max), library);
	}

	inline static public function music(key:String, ?library:String)
	{
		return getPath('music/$key.$SOUND_EXT', MUSIC, library);
	}

	inline static public function voices(song:String)
	{
		return 'songs:assets/songs/${song.toLowerCase()}/Voices.$SOUND_EXT';
	}

	inline static public function inst(song:String)
	{
		return 'songs:assets/songs/${song.toLowerCase()}/Inst.$SOUND_EXT';
	}

	inline static public function image(key:String, ?library:String)
	{
		return getPath('images/$key.png', IMAGE, library);
	}

	inline static public function font(key:String)
	{
		return 'assets/fonts/$key';
	}

	inline static public function getSparrowAtlas(key:String, ?library:String)
	{
		return FlxAtlasFrames.fromSparrow(image(key, library), file('images/$key.xml', library));
	}

	inline static public function getPackerAtlas(key:String, ?library:String)
	{
		return FlxAtlasFrames.fromSpriteSheetPacker(image(key, library), file('images/$key.txt', library));
	}

	// ported character scripts build their sprite from a TexturePacker JSON-Hash
	// atlas sitting next to the spritesheet (assets/images/custom_chars/<key>/
	// char.json + char.png). hscript calls this via Paths.getCharacterJson(key)
	inline static public function getCharacterJson(key:String, ?library:String)
	{
		var folder = getPath('images/custom_chars/$key', TEXT, library);
		var jsonPath = folder + '/char.json';
		var pngPath = folder + '/char.png';
		// some chars only ship the pair under their 'like' folder - fall back
		// the same way Character.characterExists does
		if (!OpenFlAssets.exists(jsonPath, TEXT))
			return null;
		// cached through DynamicAtlasFrames so a "Change Character" back to a
		// seen char reuses the sheet instead of rebuilding it
		return DynamicAtlasFrames.fromTexturePackerJson(pngPath, jsonPath);
	}
}
