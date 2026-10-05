package;

import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;
import DynamicSprite.DynamicAtlasFrames;
import animate.FlxAnimateFrames;
import haxe.io.Path;
import openfl.utils.AssetType;

using StringTools;

/** Psych-compatible path functions scoped to one imported asset owner. */
class PsychOwnerPaths {
	public static function create(ownerRoot:String, ?initialLibrary:String):Dynamic {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == '') throw '[psych-assets] A valid selected import owner root is required';
		var currentLevel:String = initialLibrary == null || initialLibrary == '' ? null : initialLibrary.toLowerCase();
		var proxy:Dynamic = {};
		Reflect.setField(proxy, 'SOUND_EXT', Paths.SOUND_EXT);
		Reflect.setField(proxy, 'VIDEO_EXT', 'mp4');
		Reflect.setField(proxy, 'getPath', function(file:String, ?type:AssetType = TEXT,
			?parentFolder:String, ?modsAllowed:Bool = true):String {
			return getPath(owner, file, type, parentFolder, modsAllowed, currentLevel);
		});
		Reflect.setField(proxy, 'file', function(file:String, ?type:AssetType = TEXT, ?library:String):String {
			return getPath(owner, file, type, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'txt', function(key:String, ?library:String):String {
			return getPath(owner, 'data/' + key + '.txt', TEXT, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'xml', function(key:String, ?library:String):String {
			return getPath(owner, 'data/' + key + '.xml', TEXT, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'json', function(key:String, ?library:String):String {
			return getPath(owner, 'data/' + key + '.json', TEXT, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'shaderFragment', function(key:String, ?library:String):String {
			return getPath(owner, 'shaders/' + key + '.frag', TEXT, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'shaderVertex', function(key:String, ?library:String):String {
			return getPath(owner, 'shaders/' + key + '.vert', TEXT, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'lua', function(key:String, ?library:String):String {
			return getPath(owner, key + '.lua', TEXT, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'sound', function(key:String, ?library:String):String {
			return getPath(owner, 'sounds/' + key + '.' + Paths.SOUND_EXT, SOUND, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'soundRandom', function(key:String, min:Int, max:Int, ?library:String):String {
			return Reflect.callMethod(proxy, Reflect.field(proxy, 'sound'), [key + FlxG.random.int(min, max), library]);
		});
		Reflect.setField(proxy, 'music', function(key:String, ?library:String):String {
			return getPath(owner, 'music/' + key + '.' + Paths.SOUND_EXT, MUSIC, library, true, currentLevel);
		});
		Reflect.setField(proxy, 'image', function(key:String, ?library:String):FlxGraphic {
			return image(owner, key, library, currentLevel);
		});
		Reflect.setField(proxy, 'font', function(key:String):String {
			return getPath(owner, 'fonts/' + key, FONT, null, true, currentLevel);
		});
		Reflect.setField(proxy, 'video', function(key:String):String {
			var relative = cleanRelative('videos/' + key + '.mp4');
			var imported = ownerAsset(owner, relative, null, currentLevel);
			return imported;
		});
		Reflect.setField(proxy, 'getSparrowAtlas', function(key:String, ?library:String):FlxAtlasFrames {
			return atlas(owner, key, '.xml', library, false, currentLevel);
		});
		Reflect.setField(proxy, 'getAtlas', function(key:String, ?library:String):FlxAtlasFrames {
			return autoAtlas(owner, key, library, currentLevel);
		});
		Reflect.setField(proxy, 'getPackerAtlas', function(key:String, ?library:String):FlxAtlasFrames {
			return atlas(owner, key, '.txt', library, true, currentLevel);
		});
		Reflect.setField(proxy, 'getAsepriteAtlas', function(key:String, ?library:String):FlxAtlasFrames {
			return asepriteAtlas(owner, key, library, currentLevel);
		});
		Reflect.setField(proxy, 'getCharacterJson', function(key:String, ?library:String):FlxAtlasFrames {
			var image = ownerAsset(owner, 'images/custom_chars/' + key + '/char.png', library, currentLevel);
			var json = ownerAsset(owner, 'images/custom_chars/' + key + '/char.json', library, currentLevel);
			if (image == null && json == null) {
				var nativeImage = Paths.file('images/custom_chars/' + key + '/char.png', IMAGE, 'shared');
				var nativeJson = Paths.file('images/custom_chars/' + key + '/char.json', TEXT, 'shared');
				if (!FNFAssets.exists(nativeImage) || !FNFAssets.exists(nativeJson)) return null;
				return DynamicAtlasFrames.fromTexturePackerJson(nativeImage, nativeJson);
			}
			if (image == null || json == null)
				throw '[psych-assets] Incomplete selected-owner character atlas: ' + key;
			return DynamicAtlasFrames.fromTexturePackerJson(image, json);
		});
		Reflect.setField(proxy, 'getFolderPath', function(file:String, ?folder:String = 'shared'):String {
			return getPath(owner, file, TEXT, folder, true, currentLevel);
		});
		Reflect.setField(proxy, 'getSharedPath', function(?file:String = ''):String {
			return getPath(owner, file, TEXT, 'shared', true, currentLevel);
		});
		Reflect.setField(proxy, 'getPreloadPath', function(file:String):String {
			return getPath(owner, file, TEXT, 'preload', true, currentLevel);
		});
		Reflect.setField(proxy, 'getLibraryPath', function(file:String, ?library:String = 'preload'):String {
			return getPath(owner, file, TEXT, library, true, currentLevel);
		});
		// Source modules can switch their own asset level. Keep this state local
		// to the selected owner instead of changing global Paths for other imports.
		Reflect.setField(proxy, 'setCurrentLevel', function(name:String):Void {
			currentLevel = name == null ? null : name.toLowerCase();
		});
		Reflect.setField(proxy, 'formatToSongPath', formatToSongPath);
		Reflect.setField(proxy, 'voices', function(song:String, ?postfix:String = null):String {
			var suffix = postfix == null || postfix == '' ? '' : '-' + postfix;
			var formatted = formatToSongPath(song);
			return songPath(owner, formatted, 'Voices' + suffix + '.' + Paths.SOUND_EXT,
				currentLevel, Paths.voices(formatted));
		});
		Reflect.setField(proxy, 'inst', function(song:String):String {
			var formatted = formatToSongPath(song);
			return songPath(owner, formatted, 'Inst.' + Paths.SOUND_EXT, currentLevel, Paths.inst(formatted));
		});
		// FlxAnimate's installed API loads owner folder atlases directly; donor-only
		// external JSON overloads report an explicit compatibility error.
		Reflect.setField(proxy, 'loadAnimateAtlas', function(sprite:Dynamic, key:Dynamic,
			?spriteJson:Dynamic, ?animationJson:Dynamic):Dynamic {
			return loadAnimateAtlas(owner, sprite, key, spriteJson, animationJson, currentLevel);
		});
		return proxy;
	}

	static function getPath(owner:String, file:String, type:AssetType, library:String,
		modsAllowed:Bool, currentLevel:String):String {
		if (file == null || StringTools.trim(file) == '') return Paths.file(file, type, 'shared');
		var imported = ownerAsset(owner, file, library, currentLevel);
		if (imported != null) return imported;
		var lower = file.toLowerCase();
		if (lower.startsWith('assets/shared/')) return file;
		if (library != null && library != '' && library.toLowerCase() != 'shared'
			&& library.toLowerCase() != 'preload' && library.toLowerCase() != 'default')
			return expectedOwnerPath(owner, file, library, currentLevel);
		if (lower.startsWith('assets/'))
			return expectedOwnerPath(owner, file, library, currentLevel);
		// Psych resolves level assets first and then the engine shared library.
		// Never let the host's global current level or another import satisfy a miss.
		var nativeLibrary = library == null || library == '' ? 'shared' : library;
		return Paths.file(file, type, nativeLibrary);
	}

	static function expectedOwnerPath(owner:String, file:String, library:String, currentLevel:String):String {
		var clean = PsychOwnerAssetPath.cleanId(file);
		if (clean == null) throw '[psych-assets] Refused unsafe Psych path: ' + Std.string(file);
		var relative = clean.toLowerCase().startsWith('assets/') ? clean.substr('assets/'.length) : clean;
		var folder = library;
		if (folder == null || folder == '' || folder.toLowerCase() == 'preload' || folder.toLowerCase() == 'default')
			folder = currentLevel == null || currentLevel == '' ? 'shared' : currentLevel;
		return Path.join([owner, folder, relative]);
	}

	static function ownerAsset(owner:String, file:String, library:String, currentLevel:String):String {
		var clean = PsychOwnerAssetPath.cleanId(file);
		if (clean == null) throw '[psych-assets] Refused unsafe Psych path: ' + Std.string(file);
		if (clean.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/')) {
			var direct = PsychOwnerAssetPath.resolve(owner, clean);
			if (direct.blocked) throw '[psych-assets] Refused Psych path outside selected owner: ' + file;
			if (direct.unavailable) throw '[psych-assets] Asset is unavailable in selected owner: ' + file;
			return direct.owned ? direct.path : null;
		}

		var relative = clean.toLowerCase().startsWith('assets/') ? clean.substr('assets/'.length) : clean;
		var folders:Array<String> = [];
		if (library != null && library != '') {
			var normalizedLibrary = PsychOwnerAssetPath.cleanId(library);
			if (normalizedLibrary == null) throw '[psych-assets] Refused unsafe Psych library path: ' + library;
			if (normalizedLibrary.toLowerCase() == 'preload' || normalizedLibrary.toLowerCase() == 'default') {
				folders.push('');
				folders.push('shared');
			} else {
				folders.push(normalizedLibrary);
			}
		} else {
			if (currentLevel != null && currentLevel != '' && currentLevel != 'shared') {
				folders.push(currentLevel);
				folders.push('base_game/' + currentLevel);
			}
			folders.push('shared');
			folders.push('');
		}

		for (folder in folders) {
			var candidate = folder == '' ? relative : folder + '/' + relative;
			var resolved = PsychOwnerAssetPath.resolve(owner, candidate);
			if (resolved.blocked) throw '[psych-assets] Refused Psych path outside selected owner: ' + file;
			if (resolved.owned) return resolved.path;
		}
		return null;
	}

	static function image(owner:String, key:String, library:String, currentLevel:String):FlxGraphic {
		var clean = PsychOwnerAssetPath.cleanId(key);
		if (clean == null) throw '[psych-assets] Refused unsafe Psych image key: ' + Std.string(key);
		var path = ownerAsset(owner, 'images/' + clean + '.png', library, currentLevel);
		if (path == null) {
			// Psych stages commonly reuse the engine's stock stageback/front assets.
			// This fork keeps those files under custom_stages/stage instead of the
			// flat Psych shared path. Prefer a real shared-library file when present,
			// then the host preload image and its native stage folder.
			var candidates = [
				Paths.file('images/' + clean + '.png', IMAGE, 'shared'),
				Paths.file('images/' + clean + '.png', IMAGE, 'preload'),
				Paths.file('images/custom_stages/stage/' + clean + '.png', IMAGE, 'preload')
			];
			path = null;
			for (candidate in candidates)
				if (FNFAssets.exists(candidate)) {
					path = candidate;
					break;
				}
			if (path == null)
				throw '[psych-assets] Image is unavailable in selected owner and base shared assets: ' + clean;
		}
		return graphic(path);
	}

	static function graphic(path:String):FlxGraphic {
		if (path == null || path == '') return null;
		return FNFAssets.getFlxGraphic(path);
	}

	static function loadAnimateAtlas(owner:String, sprite:Dynamic, key:Dynamic,
		spriteJson:Dynamic, animationJson:Dynamic, currentLevel:String):Dynamic {
		if (spriteJson != null || animationJson != null)
			throw '[psych-assets] Psych Paths.loadAnimateAtlas with external atlas JSON is unsupported by the installed FlxAnimate API';
		if (key == null || !Std.isOfType(key, String))
			throw '[psych-assets] Psych Paths.loadAnimateAtlas requires an owner-relative atlas folder';
		var clean = PsychOwnerAssetPath.cleanId(cast key);
		if (clean == null) throw '[psych-assets] Refused unsafe Psych Animate atlas path: ' + Std.string(key);
		var animation = ownerAsset(owner, 'images/' + clean + '/Animation.json', null, currentLevel);
		if (animation == null)
			throw '[psych-assets] Animate atlas is unavailable in selected owner: ' + clean;
		var atlas = FlxAnimateFrames.fromAnimate(Path.directory(animation));
		if (atlas == null) throw '[psych-assets] Unable to load selected-owner Animate atlas: ' + clean;
		Reflect.setProperty(sprite, 'frames', atlas);
		return atlas;
	}

	static function atlas(owner:String, key:String, metadataExt:String, library:String,
		packer:Bool, currentLevel:String):FlxAtlasFrames {
		var cleanKey = PsychOwnerAssetPath.cleanId(key);
		if (cleanKey == null) throw '[psych-assets] Refused unsafe Psych atlas key: ' + Std.string(key);
		var image = ownerAsset(owner, 'images/' + cleanKey + '.png', library, currentLevel);
		var metadata = ownerAsset(owner, 'images/' + cleanKey + metadataExt, library, currentLevel);
		if (image != null && metadata != null)
			return packer ? DynamicAtlasFrames.fromSpriteSheetPacker(image, FNFAssets.getText(metadata))
				: DynamicAtlasFrames.fromSparrow(image, metadata);
		if (image != null || metadata != null)
			throw '[psych-assets] Incomplete selected-owner atlas: ' + cleanKey;
		var nativeImage = Paths.file('images/' + cleanKey + '.png', IMAGE, 'shared');
		var nativeMetadata = Paths.file('images/' + cleanKey + metadataExt, TEXT, 'shared');
		if (!FNFAssets.exists(nativeImage) || !FNFAssets.exists(nativeMetadata)) return null;
		return packer ? DynamicAtlasFrames.fromSpriteSheetPacker(nativeImage, FNFAssets.getText(nativeMetadata))
			: DynamicAtlasFrames.fromSparrow(nativeImage, nativeMetadata);
	}

	/** Psych's `Paths.getAtlas` tries Sparrow, TexturePacker JSON, then Packer.
		Keep owner files paired together; a partial owner atlas never borrows a
		base-game image or metadata file. An owner PNG without metadata is treated
		as a static image by the Lua sprite bridge. */
	static function autoAtlas(owner:String, key:String, library:String,
		currentLevel:String):FlxAtlasFrames {
		var clean = PsychOwnerAssetPath.cleanId(key);
		if (clean == null) throw '[psych-assets] Refused unsafe Psych atlas key: ' + Std.string(key);
		var imagePath = ownerAsset(owner, 'images/' + clean + '.png', library, currentLevel);
		var sparrow = ownerAsset(owner, 'images/' + clean + '.xml', library, currentLevel);
		var aseprite = ownerAsset(owner, 'images/' + clean + '.json', library, currentLevel);
		var packer = ownerAsset(owner, 'images/' + clean + '.txt', library, currentLevel);
		var hasOwnerMetadata = sparrow != null || aseprite != null || packer != null;
		if (hasOwnerMetadata) {
			if (imagePath == null)
				throw '[psych-assets] Incomplete selected-owner atlas: ' + clean;
			if (sparrow != null) return DynamicAtlasFrames.fromSparrow(imagePath, FNFAssets.getText(sparrow));
			if (aseprite != null) return DynamicAtlasFrames.fromTexturePackerJson(imagePath, FNFAssets.getText(aseprite));
			return DynamicAtlasFrames.fromSpriteSheetPacker(imagePath, FNFAssets.getText(packer));
		}
		if (imagePath != null) return null;

		var nativeImage = Paths.file('images/' + clean + '.png', IMAGE, 'shared');
		if (!FNFAssets.exists(nativeImage)) return null;
		var nativeSparrow = Paths.file('images/' + clean + '.xml', TEXT, 'shared');
		if (FNFAssets.exists(nativeSparrow))
			return DynamicAtlasFrames.fromSparrow(nativeImage, FNFAssets.getText(nativeSparrow));
		var nativeAseprite = Paths.file('images/' + clean + '.json', TEXT, 'shared');
		if (FNFAssets.exists(nativeAseprite))
			return DynamicAtlasFrames.fromTexturePackerJson(nativeImage, FNFAssets.getText(nativeAseprite));
		var nativePacker = Paths.file('images/' + clean + '.txt', TEXT, 'shared');
		if (FNFAssets.exists(nativePacker))
			return DynamicAtlasFrames.fromSpriteSheetPacker(nativeImage, FNFAssets.getText(nativePacker));
		return null;
	}

	static function asepriteAtlas(owner:String, key:String, library:String,
		currentLevel:String):FlxAtlasFrames {
		var clean = PsychOwnerAssetPath.cleanId(key);
		if (clean == null) throw '[psych-assets] Refused unsafe Psych atlas key: ' + Std.string(key);
		var image = ownerAsset(owner, 'images/' + clean + '.png', library, currentLevel);
		var json = ownerAsset(owner, 'images/' + clean + '.json', library, currentLevel);
		if (image != null || json != null) {
			if (image == null || json == null)
				throw '[psych-assets] Incomplete selected-owner TexturePacker atlas: ' + clean;
			return DynamicAtlasFrames.fromTexturePackerJson(image, FNFAssets.getText(json));
		}
		var nativeImage = Paths.file('images/' + clean + '.png', IMAGE, 'shared');
		var nativeJson = Paths.file('images/' + clean + '.json', TEXT, 'shared');
		if (!FNFAssets.exists(nativeImage) || !FNFAssets.exists(nativeJson)) return null;
		return DynamicAtlasFrames.fromTexturePackerJson(nativeImage, FNFAssets.getText(nativeJson));
	}

	static function songPath(owner:String, song:String, filename:String, currentLevel:String, fallback:String):String {
		var imported = ownerAsset(owner, 'songs/' + song + '/' + filename, null, currentLevel);
		return imported == null ? fallback : imported;
	}

	static function cleanRelative(value:String):String {
		var clean = PsychOwnerAssetPath.cleanId(value);
		if (clean == null) throw '[psych-assets] Refused unsafe Psych path: ' + Std.string(value);
		return clean;
	}

	public static function formatToSongPath(path:String):String {
		return PsychSongNameCompat.format(path);
	}
}
