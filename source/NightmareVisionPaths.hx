package;

import haxe.io.Path;
import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.system.FlxAssets;
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
	public var DEFAULT_FONT:String = 'vcr.ttf';
	public var COMBO_PREFIX:String = 'UI/combo/';
	public var RATINGS_PREFIX:String = 'UI/ratings/';
	public var COUNTDOWN_PREFIX:String = 'UI/countdown/';
	public var UI_PREFIX:String = 'UI/';

	public function new(root:String, ?baseRoot:String) {
		this.root = checkedRoot(root);
		CORE_DIRECTORY = checkedRoot(baseRoot == null ? this.root + '/' + CORE_SUBTREE : baseRoot);
		if (!CORE_DIRECTORY.startsWith(this.root + '/'))
			throw '[nightmare-vision-asset] Core dependency must belong to the selected owner';
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
		return FlxG.bitmap.add(FNFAssets.getBitmapData(path), false, path);
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
}
