package;

import haxe.io.Path;
import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.system.FlxAssets;
import animate.FlxAnimateFrames;
import animate.FlxAnimateFrames.SpritemapInput;
import openfl.media.Sound;
#if sys
import sys.FileSystem;
#end
using StringTools;

/** Source-shaped NMV Paths API. Its core assets are an explicit dependency
 * of this import; neither the native game nor another import is a fallback. */
@:keep
class NightmareVisionPaths {
	public static inline var CORE_SUBTREE:String = '__nmv_core';
	static var missingSoundDiagnostics:Map<String, Bool> = new Map();
	public final root:String;
	public final CORE_DIRECTORY:String;
	public final hudProfile:NightmareVisionHUDProfile;
	public var usesSharedRatingPrefix(default, null):Bool;
	public var DEFAULT_FONT:String = 'vcr.ttf';
	public var COMBO_PREFIX:String;
	public var RATINGS_PREFIX:String;
	public var COUNTDOWN_PREFIX:String;
	public var UI_PREFIX:String;

	public function new(root:String, ?baseRoot:String) {
		this.root = checkedRoot(root);
		CORE_DIRECTORY = checkedRoot(baseRoot == null ? this.root + '/' + CORE_SUBTREE : baseRoot);
		if (!CORE_DIRECTORY.startsWith(this.root + '/'))
			throw '[nightmare-vision-asset] Core dependency must belong to the selected owner';
		hudProfile = NightmareVisionHUDProfile.detect(this);
		usesSharedRatingPrefix = hudProfile.usesSharedRatingPrefix;
		COMBO_PREFIX = hudProfile.comboPrefix;
		RATINGS_PREFIX = hudProfile.ratingsPrefix;
		COUNTDOWN_PREFIX = hudProfile.countdownPrefix;
		UI_PREFIX = hudProfile.uiPrefix;
	}

	static function checkedRoot(value:String):String {
		if (value == null) throw '[nightmare-vision-asset] Missing owner root';
		var clean = value.replace('\\', '/');
		if (!clean.startsWith('assets/imported_mods/') || !safeRelative(clean))
			throw '[nightmare-vision-asset] Invalid installed owner root: ' + value;
		return Path.normalize(clean);
	}

	static function safeRelative(value:String):Bool {
		if (value == null || value.startsWith('/') || value.indexOf(':') >= 0 || value.indexOf('\x00') >= 0) return false;
		for (part in value.split('/')) if (part == '..' || part == '.') return false;
		return true;
	}

	function scopedPath(base:String, relative:String):String {
		if (!safeRelative(relative)) throw '[nightmare-vision-asset] Invalid relative path: ' + relative;
		var path = Path.join([base, relative]);
		#if sys
		// Check existing ancestors too: a missing child beneath a symlink must
		// not later resolve outside its selected dependency tree.
		var ancestor = path;
		while (!FileSystem.exists(ancestor) && ancestor != base) {
			var parent = Path.directory(ancestor);
			if (parent == ancestor || parent == '') break;
			ancestor = parent;
		}
		if (FileSystem.exists(base) && FileSystem.exists(ancestor)) {
			var canonicalBase = Path.normalize(FileSystem.fullPath(base));
			var canonicalOwner = Path.normalize(FileSystem.fullPath(root));
			if (canonicalBase != canonicalOwner && !canonicalBase.startsWith(canonicalOwner + '/'))
				throw '[nightmare-vision-asset] Dependency escaped owner: ' + base;
			var canonical = Path.normalize(FileSystem.fullPath(ancestor));
			if (canonical != canonicalBase && !canonical.startsWith(canonicalBase + '/'))
				throw '[nightmare-vision-asset] Path escaped owner: ' + path;
		}
		#end
		return path;
	}

	public function exists(path:String):Bool {
		#if sys
		return FileSystem.exists(path);
		#else
		return FNFAssets.exists(path);
		#end
	}

	/** Resolve an owner/core path supplied to the source engine's asset helper.
	 * Paths returned by this API are relative to the game cwd; arbitrary engine
	 * or other-owner paths must not become an escape hatch from this adapter. */
	public function scopeAssetPath(path:String):Null<String> {
		if (!safeRelative(path)) return null;
		var normalized = Path.normalize(path.replace('\\', '/'));
		if (normalized == root) return root;
		if (normalized.startsWith(root + '/'))
			return scopedPath(root, normalized.substr(root.length + 1));
		if (normalized == CORE_DIRECTORY) return CORE_DIRECTORY;
		if (normalized.startsWith(CORE_DIRECTORY + '/'))
			return scopedPath(CORE_DIRECTORY, normalized.substr(CORE_DIRECTORY.length + 1));
		return null;
	}

	public function getCorePath(file:String = ''):String return scopedPath(CORE_DIRECTORY, file);

	/** FunkinScript.getPath extension precedence within this owner/core. */
	public function resolveScript(path:String):NightmareVisionScriptDiscovery.NightmareVisionScriptEntry {
		if (path == null || path == '') return null;
		var clean = path.replace('\\', '/');
		if (clean.startsWith(root + '/')) {
			var scoped = scopeAssetPath(clean);
			if (scoped == null) return null;
			clean = scoped.substr(root.length + 1);
		}
		// Reject parent traversal and foreign owner paths before existence checks.
		if (!safeRelative(clean) || clean.startsWith('assets/'))
			throw '[nightmare-vision-script-path] Invalid owner script: ' + path;
		for (extension in ['hx', 'hxs', 'hscript']) {
			var selected = getPath(clean + '.' + extension, null, true);
			if (exists(selected)) return {scope:'dynamic', name:clean, path:selected,
				relative:selected.substr(root.length + 1)};
		}
		return null;
	}

	/** The selected content package is already mounted at root. This source API
	 * addresses mod content directly; it must not silently select engine core. */
	public function modFolders(key:String):String return scopedPath(root, key);

	public function getPath(file:String, ?parentFolder:String, checkMods:Bool = false):String {
		if (parentFolder != null) file = parentFolder + '/' + file;
		if (checkMods) {
			var selected = scopedPath(root, file);
			if (exists(selected)) return selected;
		}
		return getCorePath(file);
	}

	public function txt(key:String, ?parentFolder:String, checkMods:Bool = true):String
		return getPath('data/' + key + '.txt', parentFolder, checkMods);
	public function xml(key:String, ?parentFolder:String, checkMods:Bool = true):String
		return getPath('data/' + key + '.xml', parentFolder, checkMods);
	public function json(key:String, ?parentFolder:String, checkMods:Bool = true):String
		return getPath('songs/' + key + '.json', parentFolder, checkMods);
	public function fragment(key:String, checkMods:Bool = true):String
		return getPath('shaders/' + key + '.frag', null, checkMods);
	public function vertex(key:String, checkMods:Bool = true):String
		return getPath('shaders/' + key + '.vert', null, checkMods);
	public function textureAtlas(key:String, ?parentFolder:String, checkMods:Bool = true):String
		return getPath('images/' + key, parentFolder, checkMods);
	public function noteskin(key:String, ?parentFolder:String, checkMods:Bool = true):String {
		var path = getPath('data/noteskins/' + key + '.json', parentFolder, checkMods);
		return exists(path) ? path : getPath('noteskins/' + key + '.json', parentFolder, checkMods);
	}

	public function findFileWithExts(key:String, exts:Array<String>, ?parentFolder:String, checkMods:Bool = true):String {
		for (extension in exts) {
			var path = getPath(key + '.' + extension, parentFolder, checkMods);
			if (exists(path)) return path;
		}
		return getPath(key, parentFolder, checkMods);
	}
	public function fileExists(key:String, ?parentFolder:String, checkMods:Bool = true):Bool
		return exists(getPath(key, parentFolder, checkMods));
	public function getTextFromFile(key:String, ?parentFolder:String, checkMods:Bool = true):String {
		var path = getPath(key, parentFolder, checkMods);
		return exists(path) ? FNFAssets.getText(path) : '';
	}
	public function font(key:String, checkMods:Bool = true):String
		return findFileWithExts('fonts/' + key, ['ttf', 'otf'], null, checkMods);
	public function video(key:String, ?ext:String, checkMods:Bool = true):String
		return findFileWithExts('videos/' + key, ext == null ? ['mp4', 'mov', 'webm'] : [ext, 'mp4', 'mov', 'webm'], null, checkMods);

	function requireFile(path:String):String {
		if (!exists(path)) throw '[nightmare-vision-asset] Missing installed asset: ' + path;
		#if sys
		if (FileSystem.isDirectory(path)) throw '[nightmare-vision-asset] Expected a file: ' + path;
		#end
		return path;
	}
	public function image(key:String, ?parentFolder:String, allowGPU:Bool = true, checkMods:Bool = true):FlxGraphic {
		var path = requireFile(getPath('images/' + key + '.png', parentFolder, checkMods));
		return FNFAssets.getFlxGraphic(path);
	}
	public function sound(key:String, ?parentFolder:String, checkMods:Bool = true):Sound
		return sourceSound(findFileWithExts('sounds/' + key, ['ogg', 'wav'], parentFolder, checkMods));
	public function soundRandom(key:String, min:Int = 0, max:Int = 0, ?parentFolder:String, checkMods:Bool = true):Sound
		return sound(key + FlxG.random.int(min, max), parentFolder, checkMods);
	public function music(key:String, ?parentFolder:String, checkMods:Bool = true):Sound
		return sourceSound(findFileWithExts('music/' + key, ['ogg', 'wav'], parentFolder, checkMods));

	/** Source FunkinAssets.getSound returns Flixel's embedded beep when no
	 * requested owner/core sound exists. Keep that harmless fallback so an
	 * optional/missing sound does not abort the rest of its HScript callback. */
	function sourceSound(path:String):Sound {
		if (!exists(path)) {
			var diagnosticKey = root + '|' + path;
			if (!missingSoundDiagnostics.exists(diagnosticKey)) {
				missingSoundDiagnostics.set(diagnosticKey, true);
				trace('[nightmare-vision-asset-missing] requested=' + path
					+ ' fallback=flixel/sounds/beep (source FunkinAssets behavior)');
			}
			return FlxAssets.getSoundAddExtension('flixel/sounds/beep');
		}
		#if sys
		if (FileSystem.isDirectory(path)) throw '[nightmare-vision-asset] Expected a file: ' + path;
		#end
		return FNFAssets.getSound(path);
	}

	/** Source Paths.sanitize behavior, including its original character and
	 * whitespace handling. */
	public function sanitize(path:String):String
		return ~/[^- a-zA-Z0-9..\/]+\//g.replace(path, '').replace(' ', '-').trim().toLowerCase();

	public function getSparrowAtlas(key:String, ?parentFolder:String, allowGPU:Bool = true, checkMods:Bool = true):FlxAtlasFrames {
		var metadata = requireFile(getPath('images/' + key + '.xml', parentFolder, checkMods));
		return FlxAtlasFrames.fromSparrow(image(key, parentFolder, allowGPU, checkMods), FNFAssets.getText(metadata));
	}
	public function getPackerAtlas(key:String, ?parentFolder:String, allowGPU:Bool = true, checkMods:Bool = true):FlxAtlasFrames {
		var metadata = requireFile(getPath('images/' + key + '.txt', parentFolder, checkMods));
		return FlxAtlasFrames.fromSpriteSheetPacker(image(key, parentFolder, allowGPU, checkMods), FNFAssets.getText(metadata));
	}
	public function getAtlasFrames(key:String, ?parentFolder:String, allowGPU:Bool = true, checkMods:Bool = true):FlxAtlasFrames {
		if (fileExists('images/' + key + '.xml', parentFolder, checkMods)) return getSparrowAtlas(key, parentFolder, allowGPU, checkMods);
		var json = getPath('images/' + key + '.json', parentFolder, checkMods);
		if (exists(json)) return FlxAtlasFrames.fromAseprite(image(key, parentFolder, allowGPU, checkMods), FNFAssets.getText(json));
		return getPackerAtlas(key, parentFolder, allowGPU, checkMods);
	}

	/** Load an Animate texture atlas from this owner, with the same ordinary
	 * Sparrow/Aseprite/Packer fallback used by Bopper when no Animate atlas exists. */
	public function getTextureAtlas(key:String, ?parentFolder:String, allowGPU:Bool = true,
		checkMods:Bool = true):FlxAtlasFrames {
		var clean = key != null && key.toLowerCase().endsWith('.png') ? key.substr(0, key.length - 4) : key;
		var manifest = getPath('images/' + clean + '/Animation.json', parentFolder, checkMods);
		if (!exists(manifest))
			return getAtlasFrames(clean, parentFolder, allowGPU, checkMods);
		var atlasPath = Path.directory(manifest);
		var atlas:FlxAnimateFrames;
		#if sys
		// fromAnimate(folder) enumerates through FlxAnimateAssets' global library
		// index, which cannot see a newly imported owner directory. Pass the
		// already validated owner's manifest, sprite maps, and bitmap contents
		// directly so neither path lookup nor cache identity depends on a global
		// mod/working-directory switch.
		if (!FileSystem.isDirectory(atlasPath))
			throw '[nightmare-vision-asset] Expected owner atlas directory: ' + atlasPath;
		var names = FileSystem.readDirectory(atlasPath);
		names.sort(Reflect.compare);
		var spritemaps:Array<SpritemapInput> = [];
		for (name in names) {
			if (!name.toLowerCase().startsWith('spritemap') || !name.toLowerCase().endsWith('.json')) continue;
			var stem = Path.withoutExtension(name);
			var imageName:String = null;
			for (candidate in names)
				if (Path.withoutExtension(candidate) == stem && !candidate.toLowerCase().endsWith('.json')) {
					imageName = candidate;
					break;
				}
			if (imageName == null)
				throw '[nightmare-vision-asset] Missing owner spritemap image for ' + name;
			var jsonPath = scopeAssetPath(Path.join([atlasPath, name]));
			var imagePath = scopeAssetPath(Path.join([atlasPath, imageName]));
			if (jsonPath == null || imagePath == null)
				throw '[nightmare-vision-asset] Atlas file escaped its selected owner: ' + atlasPath;
			spritemaps.push({source:FNFAssets.getBitmapData(imagePath), json:FNFAssets.getText(jsonPath)});
		}
		if (spritemaps.length == 0)
			throw '[nightmare-vision-asset] No owner spritemaps found in ' + atlasPath;
		var metadataPath = scopeAssetPath(Path.join([atlasPath, 'metadata.json']));
		var metadata = metadataPath != null && exists(metadataPath) ? FNFAssets.getText(metadataPath) : null;
		atlas = FlxAnimateFrames.fromAnimate(FNFAssets.getText(manifest), spritemaps, metadata, atlasPath);
		#else
		atlas = FlxAnimateFrames.fromAnimate(atlasPath);
		#end
		if (atlas == null)
			throw '[nightmare-vision-asset] Could not load owner texture atlas: ' + atlasPath;
		return atlas;
	}
}
