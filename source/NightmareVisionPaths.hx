package;

import haxe.io.Path;
import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.system.FlxAssets;
import animate.FlxAnimateFrames;
import animate.FlxAnimateFrames.SpritemapInput;
import openfl.media.Sound;
import openfl.display.BitmapData;
import haxe.Http;
import RuntimeOwnerAssetIdentity.RuntimeOwnerAssetIdentityResult;
#if sys
import sys.FileSystem;
#end
using StringTools;

/** Source-shaped NMV Paths API. Its core assets are an explicit dependency
 * of this import; neither the native game nor another import is a fallback. */
@:keep
class NightmareVisionPaths implements NightmareVisionScriptPaths {
	public static inline var CORE_SUBTREE:String = '__nmv_core';
	static var missingSoundDiagnostics:Map<String, Bool> = new Map();
	public final root:String;
	/** Borrowed atlas cache uses the resolved PNG path without its extension. */
	public var tempAtlasFramesCache:Map<String, FlxAtlasFrames> = [];
	public final scriptExtensions:Array<String> = ['hx', 'hxs', 'hscript'];
	public final scriptInstances:Map<String, NightmareVisionScriptModule> = [];
	public final CORE_DIRECTORY:String;
	public final hudProfile:NightmareVisionHUDProfile;
	/** Source-visible directory name, translated to this import's owner by
	 * `mods()` and `scopeAssetPath()` instead of exposing sibling packages. */
	public var MODS_DIRECTORY(default, null):String = 'content';
	public final sourceDirectory:Null<String>;
	final clientPrefs:Dynamic;
	public var usesSharedRatingPrefix(default, null):Bool;
	public var DEFAULT_FONT:String = 'vcr.ttf';
	public var COMBO_PREFIX:String;
	public var RATINGS_PREFIX:String;
	public var COUNTDOWN_PREFIX:String;
	public var UI_PREFIX:String;
	var ownerAssetCache:NightmareVisionFunkinAssetCache;
	var ownerAssetFacade:NightmareVisionFunkinAssets;
	var modFamily:NightmareVisionModsContext;
	var familyProviders:Map<String, NightmareVisionPaths> = [];

	/** Keep the lease anchor stable while source lookups follow its authorized family.
	 * Existing sprites/cache keys keep their resolved paths until ordinary teardown. */
	public function bindModFamily(context:NightmareVisionModsContext):Void {
		if (context == null || context.ownerRoot != root)
			throw '[nightmare-vision-asset] Family context does not own this Paths lease';
		if (modFamily != null && modFamily != context)
			throw '[nightmare-vision-asset] Cannot replace a live Paths family context';
		modFamily = context;
	}

	function providerForDirectory(directory:String):NightmareVisionPaths {
		var selectedRoot = modFamily == null ? null : modFamily.rootForDirectory(directory);
		if (selectedRoot == null) return null;
		if (selectedRoot == root) return this;
		var provider = familyProviders.get(selectedRoot);
		if (provider == null) {
			provider = new NightmareVisionPaths(selectedRoot, null, clientPrefs, directory);
			familyProviders.set(selectedRoot, provider);
		}
		return provider;
	}

	function selectedProvider():NightmareVisionPaths {
		if (modFamily == null) return this;
		var selectedRoot = modFamily.selectedRoot();
		if (selectedRoot == null) return null;
		if (selectedRoot == root) return this;
		for (directory in modFamily.familyDirectories())
			if (modFamily.rootForDirectory(directory) == selectedRoot) return providerForDirectory(directory);
		throw '[nightmare-vision-asset] Selected family root is unavailable';
	}

	public function new(root:String, ?baseRoot:String, ?clientPrefs:Dynamic, ?sourceDirectory:String) {
		this.root = checkedRoot(root);
		CORE_DIRECTORY = checkedRoot(baseRoot == null ? this.root + '/' + CORE_SUBTREE : baseRoot);
		this.clientPrefs = clientPrefs;
		this.sourceDirectory = validDirectoryLabel(sourceDirectory) ? sourceDirectory : null;
		if (!CORE_DIRECTORY.startsWith(this.root + '/'))
			throw '[nightmare-vision-asset] Core dependency must belong to the selected owner';
		hudProfile = NightmareVisionHUDProfile.detect(this);
		usesSharedRatingPrefix = hudProfile.usesSharedRatingPrefix;
		COMBO_PREFIX = hudProfile.comboPrefix;
		RATINGS_PREFIX = hudProfile.ratingsPrefix;
		COUNTDOWN_PREFIX = hudProfile.countdownPrefix;
		UI_PREFIX = hudProfile.uiPrefix;
	}

	static function validDirectoryLabel(value:String):Bool {
		if (value == null || value == '' || value == '.' || value == '..'
			|| value.indexOf('/') >= 0 || value.indexOf('\\') >= 0 || value.indexOf('\x00') >= 0)
			return false;
		return true;
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

	public function isDirectory(path:String):Bool {
		var scoped = scopeAssetPath(path);
		if (scoped == null) return false;
		#if sys
		return FileSystem.exists(scoped) && FileSystem.isDirectory(scoped);
		#else
		return FNFAssets.isDirectory(scoped);
		#end
	}

	/** Resolve an owner/core path supplied to the source engine's asset helper.
	 * Paths returned by this API are relative to the game cwd; arbitrary engine
	 * or other-owner paths must not become an escape hatch from this adapter. */
	public function scopeAssetPath(path:String):Null<String> {
		if (!safeRelative(path)) return null;
		if (modFamily != null) {
			// Both old borrowed keys and newly selected keys remain inside the catalog.
			for (directory in modFamily.familyDirectories()) {
				var provider = providerForDirectory(directory);
				if (provider == this) continue;
				var candidate = provider.scopeAssetPath(path);
				if (candidate != null) return candidate;
			}
		}
		var normalized = Path.normalize(path.replace('\\', '/'));
		// Source scripts retain a content/<mod>/ spelling from Paths.mods().
		// Resolve that alias only for this adapter's captured owner.
		if (sourceDirectory != null && normalized == MODS_DIRECTORY + '/' + sourceDirectory)
			return root;
		if (sourceDirectory != null && normalized.startsWith(MODS_DIRECTORY + '/' + sourceDirectory + '/'))
			return scopedPath(root, normalized.substr((MODS_DIRECTORY + '/' + sourceDirectory + '/').length));
		if (normalized == root) return root;
		if (normalized.startsWith(root + '/'))
			return scopedPath(root, normalized.substr(root.length + 1));
		if (normalized == CORE_DIRECTORY) return CORE_DIRECTORY;
		if (normalized.startsWith(CORE_DIRECTORY + '/'))
			return scopedPath(CORE_DIRECTORY, normalized.substr(CORE_DIRECTORY.length + 1));
		return null;
	}

	public function getCorePath(file:String = ''):String {
		var provider = selectedProvider();
		return provider != null && provider != this ? provider.getCorePath(file) : scopedPath(CORE_DIRECTORY, file);
	}

	/** FunkinScript.getPath extension precedence within this owner/core. */
	public function resolveScript(path:String):NightmareVisionScriptDiscovery.NightmareVisionScriptEntry {
		if (path == null || path == '') return null;
		var clean = path.replace('\\', '/');
		var explicitRoot:String = clean.startsWith(root + '/') ? root : null;
		if (modFamily != null) for (directory in modFamily.familyDirectories()) {
			var candidate = modFamily.rootForDirectory(directory);
			if (clean.startsWith(candidate + '/') && (explicitRoot == null || candidate.length > explicitRoot.length)) explicitRoot = candidate;
		}
		if (explicitRoot != null) {
			var scoped = scopeAssetPath(clean);
			if (scoped == null) return null;
			clean = scoped.substr(explicitRoot.length + 1);
		}
		// Reject parent traversal and foreign owner paths before existence checks.
		if (!safeRelative(clean) || clean.startsWith('assets/'))
			throw '[nightmare-vision-script-path] Invalid owner script: ' + path;
		for (extension in ['hx', 'hxs', 'hscript']) {
			var selected = explicitRoot == null ? getPath(clean + '.' + extension, null, true)
				: scopeAssetPath(explicitRoot + '/' + clean + '.' + extension);
			if (selected != null && exists(selected)) {
				var origin = root;
				if (modFamily != null) for (directory in modFamily.familyDirectories()) {
					var candidate = modFamily.rootForDirectory(directory);
					if (selected.startsWith(candidate + '/')) {origin = candidate; break;}
				}
				return {scope:'dynamic', name:clean, path:selected, relative:selected.substr(origin.length + 1)};
			}
		}
		return null;
	}

	/** The selected content package is already mounted at root. This source API
	 * addresses mod content directly; it must not silently select engine core. */
	function existingFamilyModPath(key:String):Null<String> {
		var provider = selectedProvider();
		if (provider != null) {
			var selected = provider.scopedPath(provider.root, key);
			if (exists(selected)) return selected;
		}
		if (modFamily != null) for (directory in modFamily.globalMods) {
			var global = providerForDirectory(directory);
			if (global == null) continue;
			var candidate = global.scopedPath(global.root, key);
			if (exists(candidate)) return candidate;
		}
		return null;
	}

	public function modFolders(key:String):String {
		var found = existingFamilyModPath(key);
		if (found != null) return found;
		var provider = selectedProvider();
		if (provider == null) throw '[nightmare-vision-asset] Shared content-root lookup requires an installed source package';
		return provider.scopedPath(provider.root, key);
	}

	/** Source Paths.mods spelling, scoped to this selected owner. */
	public function mods(key:String = ''):String {
		if (modFamily != null && key != null) {
			var clean = key.replace('\\', '/');
			var slash = clean.indexOf('/');
			var label = slash < 0 ? clean : clean.substr(0, slash);
			var explicit = providerForDirectory(label);
			if (explicit != null) return explicit.scopedPath(explicit.root, slash < 0 ? '' : clean.substr(slash + 1));
		}
		var provider = selectedProvider();
		if (provider == null) throw '[nightmare-vision-asset] No source mod selected';
		if (provider != this) return provider.mods(key);
		var relative = key == null ? '' : key.replace('\\', '/');
		if (sourceDirectory != null && relative == sourceDirectory) relative = '';
		else if (sourceDirectory != null && relative.startsWith(sourceDirectory + '/'))
			relative = relative.substr(sourceDirectory.length + 1);
		if (relative == '' || relative == '.') return root;
		return scopedPath(root, relative);
	}

	public function getPath(file:String, ?parentFolder:String, checkMods:Bool = false):String {
		if (parentFolder != null) file = parentFolder + '/' + file;
		if (checkMods) {
			var selected = existingFamilyModPath(file);
			if (selected != null) return selected;
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
		var path = getPath('images/' + key + '.png', parentFolder, checkMods);
		return ownedAssets().getGraphic(path, true, allowGPU);
	}
	public function sound(key:String, ?parentFolder:String, checkMods:Bool = true):Sound
		return sourceSound(findFileWithExts('sounds/' + key, ['ogg', 'wav'], parentFolder, checkMods));
	public function soundRandom(key:String, min:Int = 0, max:Int = 0, ?parentFolder:String, checkMods:Bool = true):Sound
		return sound(key + FlxG.random.int(min, max), parentFolder, checkMods);
	public function music(key:String, ?parentFolder:String, checkMods:Bool = true):Sound
		return sourceSound(findFileWithExts('music/' + key, ['ogg', 'wav'], parentFolder, checkMods));

	function usesStreamedMusic():Bool {
		var value:Dynamic = clientPrefs == null ? null : Reflect.field(clientPrefs, 'streamedMusic');
		return Std.isOfType(value, Bool) && value == true;
	}

	public function gpuCachingEnabled():Bool {
		var value:Dynamic = clientPrefs == null ? null : Reflect.field(clientPrefs, 'gpuCaching');
		return Std.isOfType(value, Bool) && value == true;
	}

	public function devModeEnabled():Bool {
		var value:Dynamic = clientPrefs == null ? null : Reflect.field(clientPrefs, 'inDevMode');
		return Std.isOfType(value, Bool) && value == true;
	}

	public function getOwnerAssetCache():NightmareVisionFunkinAssetCache {
		if (ownerAssetCache == null) ownerAssetCache = new NightmareVisionFunkinAssetCache(this);
		return ownerAssetCache;
	}

	/** Resolve a symbolic Lime ID through the authenticated package first and
	 * this same owner's explicit core dependency second. A definite package type
	 * mismatch or incomplete catalog never binds another library implicitly. */
	public function resolveOwnerAssetIdentity(id:String, expectedType:Null<String>):RuntimeOwnerAssetIdentityResult {
		var packageResult = RuntimeOwnerAssetIdentity.lookup(root, 'Nightmare Vision', 'package', id, expectedType);
		if (packageResult.state == 'found' || packageResult.state == 'type-mismatch'
			|| packageResult.state == 'unknown' || packageResult.state == 'invalid') return packageResult;
		var coreResult = RuntimeOwnerAssetIdentity.lookup(root, 'Nightmare Vision', 'core', id, expectedType);
		if (coreResult.state != 'no-index' && coreResult.state != 'unclaimed') return coreResult;
		if (packageResult.state == 'missing') return packageResult;
		return coreResult;
	}

	public function bindOwnerAssetFacade(value:NightmareVisionFunkinAssets):Void ownerAssetFacade = value;

	function ownedAssets():NightmareVisionFunkinAssets {
		if (ownerAssetFacade == null) ownerAssetFacade = new NightmareVisionFunkinAssets(this);
		return ownerAssetFacade;
	}

	/** Clear every cache entry owned by this import when its runtime is unmounted. */
	public function releaseOwnerAssets():Void {
		RuntimeOwnerAssetIdentity.releaseOwner(root);
		tempAtlasFramesCache.clear();
		scriptInstances.clear();
		if (ownerAssetCache != null) ownerAssetCache.release();
		ownerAssetCache = null;
		ownerAssetFacade = null;
		for (provider in familyProviders) provider.releaseOwnerAssets();
		familyProviders.clear();
	}

	function songAudioPath(song:String, kind:String, postFix:String, checkMods:Bool):String {
		var name = sanitize(song);
		var songKey = '$name/$kind';
		var audioDirectory = getPath('songs/$name/audio', null, checkMods);
		#if sys
		if (FileSystem.exists(audioDirectory) && FileSystem.isDirectory(audioDirectory)) songKey = '$name/audio/$kind';
		#else
		if (FNFAssets.isDirectory(audioDirectory)) songKey = '$name/audio/$kind';
		#end
		if (postFix != null) songKey += '-$postFix';
		return findFileWithExts('songs/' + songKey, ['ogg', 'wav'], null, checkMods);
	}

	public function trackSwap(song:String, ?postFix:String, checkMods:Bool = true):Null<Sound> {
		var path = songAudioPath(song, 'Track', postFix, checkMods);
		return usesStreamedMusic() ? ownedAssets().getVorbisSound(path) : ownedAssets().getSoundUnsafe(path);
	}

	public function voices(song:String, ?postFix:String, checkMods:Bool = true):Null<Sound> {
		var path = songAudioPath(song, 'Voices', postFix, checkMods);
		return usesStreamedMusic() ? ownedAssets().getVorbisSound(path) : ownedAssets().getSoundUnsafe(path);
	}

	public function inst(song:String, ?postFix:String, checkMods:Bool = true):Sound {
		var path = songAudioPath(song, 'Inst', postFix, checkMods);
		if (usesStreamedMusic()) {
			var streamed = ownedAssets().getVorbisSound(path);
			if (streamed != null) return streamed;
		}
		return ownedAssets().getSound(path);
	}

	/** Source Paths.imageFromURL is PNG-only and returns immediately with an
	 * already cached image, or null while its download is in flight. */
	public function imageFromURL(url:String, ?fallback:String->Void, allowGPU:Bool = true):FlxGraphic {
		if (url == null || !url.contains('.png')) return null;
		var cache = ownedAssets().cache;
		if (cache.currentTrackedGraphics.exists(url)) {
			cache.localTrackedAssets.push(url);
			return cache.currentTrackedGraphics.get(url);
		}
		var http = new Http(url);
		http.onBytes = function(bytes) {
			try {
				var bitmap = BitmapData.fromBytes(bytes);
				if (bitmap != null) {
					if (cache.isReleased()) bitmap.dispose();
					else cache.cacheRemoteBitmap(url, bitmap, allowGPU);
				}
			} catch (_:Dynamic) {}
		};
		http.onError = fallback == null ? function(message:String) trace('Error reading URL image: ' + message) : fallback;
		http.request(false);
		return null;
	}

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

	/** Source listAllFilesInDirectory precedence is core first, then global and
	 * current mods. An imported source owner has no global list, so only the
	 * selected owner contributes after the core dependency. */
	public function listAllFilesInDirectory(directory:String, checkMods:Bool = true):Array<String> {
		var provider = selectedProvider();
		var folders:Array<String> = [];
		var corePath = getCorePath(directory);
		if (exists(corePath) && isDirectory(corePath)) folders.push(corePath);
		if (checkMods) {
			if (modFamily != null) for (label in modFamily.globalMods) {
				var global = providerForDirectory(label);
				if (global == null) continue;
				var globalPath = global.scopedPath(global.root, directory);
				if (exists(globalPath) && isDirectory(globalPath) && !folders.contains(globalPath)) folders.push(globalPath);
			}
			if (provider != null) {
				var ownerPath = provider.scopedPath(provider.root, directory);
				if (exists(ownerPath) && isDirectory(ownerPath) && !folders.contains(ownerPath)) folders.push(ownerPath);
			}
		}
		var files:Array<String> = [];
		for (folder in folders) for (name in ownedAssets().readDirectory(folder)) {
			var path = Path.join([folder, name]);
			if (!files.contains(path)) files.push(path);
		}
		return files;
	}

	/** Resolve a source content/<mod>/... spelling to its mod label. */
	public function getModFolder(path:String, ?exclude:String):String {
		if (path == null) return '';
		var normalized = path.replace('\\', '/');
		if (modFamily != null) {
			var directories = modFamily.familyDirectories();
			for (directory in directories) {
				var provider = providerForDirectory(directory);
				var relative = provider.sourceAliasPath(normalized);
				if (relative != null) return directory == exclude ? '' : directory;
			}
			if (directories.length > 0) return '';
		}
		var relative = sourceAliasPath(normalized);
		if (relative != null) {
			var folder = sourceDirectory == null ? root.substr(root.lastIndexOf('/') + 1) : sourceDirectory;
			return folder == exclude ? '' : folder;
		}
		// Preserve the legacy syntactic label helper outside an enrolled family.
		var prefix = MODS_DIRECTORY + '/';
		var index = normalized.indexOf(prefix);
		if (index < 0) return '';
		var tail = normalized.substr(index + prefix.length);
		var slash = tail.indexOf('/');
		var folder = slash < 0 ? tail : tail.substr(0, slash);
		return folder == exclude ? '' : folder;
	}

	/** Map absolute discovery paths through the same physical owner guard as IO. */
	function sourceAliasPath(path:String):Null<String> {
		#if sys
		if (Path.isAbsolute(path)) {
			var absoluteRoot = Path.normalize(FileSystem.absolutePath(root));
			var normalized = Path.normalize(path);
			#if windows
			var rootKey = absoluteRoot.toLowerCase();
			var key = normalized.toLowerCase();
			#else
			var rootKey = absoluteRoot;
			var key = normalized;
			#end
			if (key != rootKey && !key.startsWith(rootKey + '/')) return null;
			path = root + normalized.substr(absoluteRoot.length);
		}
		#end
		var normalized = Path.normalize(path);
		var alias = sourceDirectory == null ? null : MODS_DIRECTORY + '/' + sourceDirectory;
		if (normalized != root && !normalized.startsWith(root + '/')
			&& (alias == null || (normalized != alias && !normalized.startsWith(alias + '/')))) return null;
		try return scopeAssetPath(path) catch (_:Dynamic) return null;
	}

	public function getSparrowAtlas(key:String, ?parentFolder:String, allowGPU:Bool = true, checkMods:Bool = true):FlxAtlasFrames {
		var directPath = haxe.io.Path.withoutExtension(getPath('images/' + key + '.png', parentFolder, checkMods));
		var cached = tempAtlasFramesCache.get(directPath);
		if (cached != null) return cached;
		var metadata = getPath('images/' + key + '.xml', parentFolder, checkMods);
		var frames = FlxAtlasFrames.fromSparrow(image(key, parentFolder, allowGPU, checkMods), exists(metadata) ? FNFAssets.getText(metadata) : null);
		if (frames != null) tempAtlasFramesCache.set(directPath, frames);
		return frames;
	}
	public function getPackerAtlas(key:String, ?parentFolder:String, allowGPU:Bool = true, checkMods:Bool = true):FlxAtlasFrames {
		var directPath = haxe.io.Path.withoutExtension(getPath('images/' + key + '.png', parentFolder, checkMods));
		var cached = tempAtlasFramesCache.get(directPath);
		if (cached != null) return cached;
		var metadata = getPath('images/' + key + '.txt', parentFolder, checkMods);
		var frames = FlxAtlasFrames.fromSpriteSheetPacker(image(key, parentFolder, allowGPU, checkMods), exists(metadata) ? FNFAssets.getText(metadata) : null);
		if (frames != null) tempAtlasFramesCache.set(directPath, frames);
		return frames;
	}
	public function getAtlasFrames(key:String, ?parentFolder:String, allowGPU:Bool = true, checkMods:Bool = true):FlxAtlasFrames {
		var directPath = haxe.io.Path.withoutExtension(getPath('images/' + key + '.png', parentFolder, checkMods));
		var cached = tempAtlasFramesCache.get(directPath);
		if (cached != null) return cached;
		var xml = getPath('images/' + key + '.xml', parentFolder, checkMods);
		var txt = getPath('images/' + key + '.txt', parentFolder, checkMods);
		var json = getPath('images/' + key + '.json', parentFolder, checkMods);
		var graphic = image(key, parentFolder, allowGPU, checkMods);
		var frames = exists(xml) ? FlxAtlasFrames.fromSparrow(graphic, FNFAssets.getText(xml))
			: exists(json) ? FlxAtlasFrames.fromAseprite(graphic, FNFAssets.getText(json))
			: FlxAtlasFrames.fromSpriteSheetPacker(graphic, exists(txt) ? FNFAssets.getText(txt) : null);
		if (frames != null) tempAtlasFramesCache.set(directPath, frames);
		return frames;
	}

	/** Translate this owner's native graphic key to its bounded source cache
	 * path when loadAtlas evicts a borrowed frame-cache entry. */
	public function forgetAtlasGraphic(graphic:FlxGraphic):Void {
		var key = graphic.key;
		var nativePrefix = 'nightmare-vision:' + root + ':';
		if (key != null && key.startsWith(nativePrefix)) key = key.substr(nativePrefix.length);
		var selected = scopeAssetPath(key);
		if (selected == null) return;
		tempAtlasFramesCache.remove(haxe.io.Path.withoutExtension(selected));
		getOwnerAssetCache().currentTrackedGraphics.remove(selected);
	}

	/** Source multi-atlas merge. The source intentionally shifts the first key
	 * from the caller's array; preserve that observable behavior. */
	public function getMultiAtlas(keys:Array<String>, ?parentFolder:String, allowGPU:Bool = true,
		checkMods:Bool = true):FlxAtlasFrames {
		if (keys == null || keys.length == 0) return null;
		var first = keys.shift();
		if (first == null) return null;
		var frames = getAtlasFrames(StringTools.trim(first), parentFolder, allowGPU, checkMods);
		if (keys.length == 0 || frames == null) return frames;
		var merged = new FlxAtlasFrames(frames.parent);
		merged.addAtlas(frames, true);
		for (key in keys) {
			var next = getAtlasFrames(StringTools.trim(key), parentFolder, allowGPU, checkMods);
			if (next != null) merged.addAtlas(next, false);
		}
		return merged;
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
