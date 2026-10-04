package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
import animate.FlxAnimateFrames;
import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.graphics.frames.FlxImageFrame;
import flixel.graphics.frames.FlxFramesCollection;
import openfl.text.Font;
using StringTools;

/** Asset facade owned by one selected Codename namespace. Missing files never
 * borrow another import's same-named native/global assets. */
class CodenamePaths {
	static var ownerFontNames:Map<String, String> = new Map();

	public final root:String;
	var fallbackRoot:String;
	var fallbackFiles:Map<String, Bool> = new Map();
	var fallbackAllowed:Bool = false;
	public function new(root:String, ?fallbackRoot:String, ?fallbackAssetFiles:Array<String>) {
		this.root = root;
		this.fallbackRoot = fallbackRoot;
		#if sys
		if (fallbackRoot == null || fallbackRoot == '' || fallbackAssetFiles == null
			|| fallbackAssetFiles.length == 0 || root == null || root == '') return;
		if (Path.normalize(fallbackRoot) != Path.normalize(Path.join([root,
			CodenameBaseCharacterDependency.RELATIVE_ROOT]))) return;
		// This dependency can contribute only the exact files listed by its
		// receipt. Any matching owner-local atlas file disables the whole layer,
		// so an incomplete local atlas is never silently mixed with base files.
		var ownerHasAtlas = false;
		for (relative in fallbackAssetFiles) {
			if (relative == null || !StringTools.startsWith(relative, 'images/characters/')) continue;
			fallbackFiles.set(relative, true);
			if (CodenameScriptDiscovery.resolveScopedRelative(root, relative) != null)
				ownerHasAtlas = true;
		}
		this.fallbackAllowed = !ownerHasAtlas && fallbackFiles.keys().hasNext();
		#end
	}

	function fallbackFile(relative:String):Null<String> {
		#if sys
		if (!fallbackAllowed || relative == null || !fallbackFiles.exists(relative)) return null;
		var resolved = CodenameScriptDiscovery.resolveScopedRelative(fallbackRoot, relative);
		return resolved == null ? null : Path.join([fallbackRoot, resolved]);
		#else
		return null;
		#end
	}

	#if sys
	/** Resolve a complete owner-relative file path case-insensitively only when
	 * the exact path is absent. Exact full paths keep precedence; otherwise a
	 * unique complete match is accepted. This can backtrack past a same-named
	 * directory whose spelling matches but which does not contain the file. */
	static function resolveOwnerFile(root:String, relative:String):{relative:Null<String>, status:String} {
		if (root == null || !FileSystem.isDirectory(root)
			|| !CodenameScriptDiscovery.safeRelativeName(relative))
			return {relative:null, status:'unsafe'};
		var exact = Path.join([root, relative]);
		if (FileSystem.exists(exact)) {
			if (!CodenameScriptDiscovery.withinRoot(root, exact))
				return {relative:null, status:'escape'};
			if (!FileSystem.isDirectory(exact)) return {relative:relative, status:'ok'};
		}
		var parts = relative.split('/');
		var frontier:Array<{absolute:String, relative:Array<String>}> = [
			{absolute:root, relative:[]}
		];
		var escaped = false;
		for (index in 0...parts.length) {
			var next:Array<{absolute:String, relative:Array<String>}> = [];
			for (candidate in frontier) {
				var entries:Array<String> = [];
				try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(candidate.absolute)) catch (_:Dynamic) continue;
				for (entry in entries) {
					if (!CodenameScriptDiscovery.safeName(entry)
						|| entry.toLowerCase() != parts[index].toLowerCase()) continue;
					var child = Path.join([candidate.absolute, entry]);
					if (!FileSystem.exists(child)) continue;
					if (!CodenameScriptDiscovery.withinRoot(root, child)) {
						escaped = true;
						continue;
					}
					var isLast = index == parts.length - 1;
					if (FileSystem.isDirectory(child) == isLast) continue;
					var selected = candidate.relative.copy();
					selected.push(entry);
					next.push({absolute:child, relative:selected});
				}
			}
			frontier = next;
			if (frontier.length == 0) break;
		}
		if (escaped) return {relative:null, status:'escape'};
		if (frontier.length == 1)
			return {relative:frontier[0].relative.join('/'), status:'ok'};
		if (frontier.length > 1) return {relative:null, status:'ambiguous'};
		return {relative:null, status:'missing'};
	}
	#end

	public function file(relative:String, ?type:Dynamic, ?library:String):String {
		var clean = normalizeRelativePath(relative);
		var path = Path.join([root, clean]);
		#if sys
		var resolution = resolveOwnerFile(root, clean);
		if (resolution.relative != null) return Path.join([root, resolution.relative]);
		if (resolution.status == 'ambiguous')
			throw '[codename-asset] Ambiguous selected-owner asset: ' + clean;
		if (resolution.status == 'escape')
			throw '[codename-asset] Missing scoped asset (escaped selected owner): ' + path;
		var fallback = fallbackFile(clean);
		if (fallback != null) return fallback;
		if (!CodenameScriptDiscovery.withinRoot(root, path) || FileSystem.isDirectory(path))
			throw '[codename-asset] Missing scoped asset: ' + path;
		#end
		if (!FNFAssets.exists(path)) throw '[codename-asset] Missing scoped asset: ' + path;
		return path;
	}

	function normalizeRelativePath(relative:String):String {
		if (relative == null) throw '[codename-asset] Missing asset key';
		var clean = relative.replace('\\', '/');
		if (clean.startsWith('/') || clean.indexOf(':') >= 0)
			throw '[codename-asset] Invalid asset key: ' + relative;
		// Donor scripts commonly concatenate a folder ending in '/' with a
		// filename beginning in '/'. Treat repeated separators like Path.join
		// does, while keeping traversal components invalid.
		var parts:Array<String> = [];
		for (part in clean.split('/')) {
			if (part == '') continue;
			if (part == '.' || part == '..')
				throw '[codename-asset] Invalid asset key: ' + relative;
			parts.push(part);
		}
		if (parts.length == 0)
			throw '[codename-asset] Invalid asset key: ' + relative;
		return parts.join('/');
	}

	function asset(folder:String, key:String, extension:String):String {
		if (key == null) throw '[codename-asset] Missing asset key';
		return file(folder + '/' + key + (key.toLowerCase().endsWith(extension) ? '' : extension));
	}

	public function image(key:String, ?library:String, checkForAtlas:Bool = true):Dynamic {
		if (key == null) throw '[codename-asset] Missing asset key';
		// Codename's Paths.image also names Animate and paged atlas folders.
		// Resolve those owner-local folders to frames before a script passes the
		// result to FunkinSprite.loadSprite; neither has a sibling key.png.
		if (checkForAtlas) {
			if (animateAtlasPath(key) != null) return getFrames(key);
			var firstPage:String = null;
			try firstPage = file('images/' + imageKey(key) + '/1.png') catch (_:Dynamic) {}
			if (firstPage != null) return getFrames(key);
		}
		var imageRelative = normalizeRelativePath('images/' + imageKey(key) + '.png');
		#if sys
		var resolution = resolveOwnerFile(root, imageRelative);
		if (resolution.relative == null) {
			switch (resolution.status) {
				case 'missing':
					var fallback = fallbackFile(imageRelative);
					return fallback == null ? null : FNFAssets.getBitmapData(fallback);
				case 'ambiguous': throw '[codename-asset] Ambiguous selected-owner image: ' + key;
				case 'escape': throw '[codename-asset] Image escaped selected owner: ' + key;
				default: throw '[codename-asset] Invalid image key: ' + key + ' (' + resolution.status + ')';
			}
		}
		return FNFAssets.getBitmapData(Path.join([root, resolution.relative]));
		#else
		return FNFAssets.getBitmapData(file(imageRelative));
		#end
	}
	public function font(key:String):String return file('fonts/' + key);
	/** Resolve and register a font family from a font file inside this import.
	 * FlxText looks up family names in OpenFL's global font registry; reading
	 * Font.fontName from a file alone does not register that font for rendering.
	 */
	public function getFontName(path:String):String {
		var resolved = getPath(path);
		if (ownerFontNames.exists(resolved)) return ownerFontNames.get(resolved);
		var font:Font = null;
		try font = Font.fromFile(resolved) catch (error:Dynamic)
			throw '[codename-font] Could not inspect owner font ' + resolved + ': ' + Std.string(error);
		if (font == null || font.fontName == null || StringTools.trim(font.fontName) == '')
			throw '[codename-font] Could not resolve an installed font family from ' + resolved;
		Font.registerFont(font);
		ownerFontNames.set(resolved, font.fontName);
		return font.fontName;
	}
	public function xml(key:String):String return asset('data', key, '.xml');
	public function json(key:String):String return asset('data', key, '.json');
	public function txt(key:String):String return asset('data', key, '.txt');
	public function frag(key:String):String return asset('shaders', key, '.frag');
	/** Codename Paths lists one directory level, optionally prefixing each name
	 * with the requested asset key. Keep discovery inside the selected owner. */
	public function getFolderDirectories(key:String, addPath:Bool = false, ?source:Dynamic):Array<String> {
		return listFolder(key, addPath, true, false);
	}

	public function getFolderContent(key:String, addPath:Bool = false,
		?source:Dynamic, noExtension:Bool = false):Array<String> {
		return listFolder(key, addPath, false, noExtension);
	}

	function listFolder(key:String, addPath:Bool, directories:Bool, noExtension:Bool):Array<String> {
		#if sys
		if (key == null) throw '[codename-asset] Missing folder key';
		var clean = key.replace('\\', '/');
		while (clean.endsWith('/')) clean = clean.substr(0, clean.length - 1);
		if (!CodenameScriptDiscovery.safeRelativeName(clean))
			throw '[codename-asset] Invalid folder key: ' + key;
		var folder = Path.join([root, clean]);
		if (!FileSystem.exists(folder)) return [];
		if (!CodenameScriptDiscovery.withinRoot(root, folder) || !FileSystem.isDirectory(folder))
			throw '[codename-asset] Invalid scoped folder: ' + key;
		var names = ImportDirectoryListing.normalize(FileSystem.readDirectory(folder));
		names.sort(Reflect.compare);
		var result:Array<String> = [];
		for (name in names) {
			var child = Path.join([folder, name]);
			if (!CodenameScriptDiscovery.withinRoot(root, child)
				|| FileSystem.isDirectory(child) != directories) continue;
			var item = noExtension && !directories ? Path.withoutExtension(name) : name;
			result.push(addPath ? clean + '/' + item : item);
		}
		return result;
		#else
		return [];
		#end
	}
	/** A fragment shader may depend on a same-stem authored vertex program.
	 * Resolve it only beside the already validated selected-owner fragment. */
	public function vertexForFragment(key:String):Null<String> {
		var fragment = frag(key);
		var vertex = fragment.substr(0, fragment.length - '.frag'.length) + '.vert';
		#if sys
		if (!CodenameScriptDiscovery.withinRoot(root, vertex)
			|| sys.FileSystem.isDirectory(vertex)) return null;
		#end
		return FNFAssets.exists(vertex) ? vertex : null;
	}
	/** Read an include from this selected owner's shader directory. */
	public function shaderImport(key:String):String return FNFAssets.getText(file('shaders/' + key));
	public function video(key:String):String return asset('videos', key, '.mp4');
	public function obj(key:String):String return asset('models', key, '.obj');
	/** Load an owner-validated raster into Flixel's shared bitmap cache. The
	 * FNFAssets disk key includes its absolute owner path, so equal names from
	 * different imports cannot alias one another. */
	public function graphic(path:String):FlxGraphic {
		var resolved = getPath(path);
		return FNFAssets.getFlxGraphic(resolved);
	}
	/** Codename accepts both an owner-local relative key and a path already
	 * returned by Paths. Resolve either through the selected namespace. */
	public function getPath(path:String):String {
		#if sys
		if (path != null && CodenameScriptDiscovery.withinRoot(root, path)
			&& !sys.FileSystem.isDirectory(path) && FNFAssets.exists(path)) return path;
		#end
		if (path != null && !path.startsWith('/') && path.indexOf(':') < 0)
			return file(path);
		throw '[codename-asset] Missing scoped asset: ' + path;
	}
	public function assets():Dynamic {
		return {
			getPath: getPath,
			getText: function(path:String):String return FNFAssets.getText(getPath(path)),
			getBitmapData: function(path:String):Dynamic return FNFAssets.getBitmapData(getPath(path)),
			getSound: function(path:String):Dynamic return FNFAssets.getSound(getPath(path)),
			exists: function(path:String, ?type:Dynamic):Bool {
				try {
					getPath(path);
					return true;
				} catch (_:Dynamic) return false;
			}
		};
	}
	/** Lime's getText returns null for a missing asset. Keep that behavior for
	 * safe owner-relative keys while validating the path before treating a miss
	 * as nullable. This facade intentionally exposes only the text operation
	 * needed by imported Lime Assets users; OpenFL Assets remains strict above. */
	public function limeAssets():Dynamic {
		return {
			getText: function(path:String):Null<String> {
				var resolved = limeTextPath(path);
				return resolved == null ? null : FNFAssets.getText(resolved);
			}
		};
	}

	function limeTextPath(path:String):Null<String> {
		if (path == null || path.indexOf(String.fromCharCode(0)) >= 0)
			throw '[codename-asset] Invalid Lime text key: ' + Std.string(path);
		var input = path.replace('\\', '/');
		var relative = input;
		var normalizedRoot = Path.normalize(root).replace('\\', '/');
		if (Path.isAbsolute(input)) {
			if (input != normalizedRoot && !input.startsWith(normalizedRoot + '/'))
				throw '[codename-asset] Lime text path escaped selected owner: ' + path;
			relative = input == normalizedRoot ? '' : input.substr(normalizedRoot.length + 1);
		} else if (input.indexOf(':') >= 0) {
			// Library ids and drive-relative paths are not owner-relative files.
			throw '[codename-asset] Invalid Lime text key: ' + path;
		} else if (!Path.isAbsolute(normalizedRoot)) {
			// Paths returned by Codename can already contain a relative owner root
			// (for example assets/imported_mods/name/assets/shared/...). Strip that
			// exact prefix once; reject sibling roots that share its parent prefix.
			if (input == normalizedRoot || input.startsWith(normalizedRoot + '/')) {
				relative = input == normalizedRoot ? '' : input.substr(normalizedRoot.length + 1);
			} else {
				var rootParent = Path.directory(normalizedRoot);
				if (rootParent != null && rootParent != '' && rootParent != '.'
					&& input.startsWith(rootParent + '/'))
					throw '[codename-asset] Lime text path escaped selected owner: ' + path;
			}
		}
		var parts:Array<String> = [];
		for (part in relative.split('/')) {
			if (part == '') continue;
			if (part == '.' || part == '..' || part.indexOf(':') >= 0)
				throw '[codename-asset] Invalid Lime text key: ' + path;
			parts.push(part);
		}
		if (parts.length == 0)
			throw '[codename-asset] Invalid Lime text key: ' + path;
		var key = parts.join('/');
		#if sys
		var resolution = resolveOwnerFile(root, key);
		switch (resolution.status) {
			case 'ok': return Path.join([root, resolution.relative]);
			case 'missing': return null;
			case 'escape': throw '[codename-asset] Lime text path escaped selected owner: ' + path;
			case 'ambiguous': throw '[codename-asset] Ambiguous Lime text path in selected owner: ' + path;
			default: throw '[codename-asset] Invalid scoped Lime text path: ' + path;
		}
		#else
		var candidate = Path.join([root, key]);
		return FNFAssets.exists(candidate) ? candidate : null;
		#end
	}
	public function sound(key:String, ?library:String):Dynamic return audio('sounds', key);
	public function music(key:String, ?library:String):Dynamic return audio('music', key);
	function audio(folder:String, key:String):Dynamic {
		for (extension in ['.ogg', '.wav', '.mp3']) {
			var path:String = null;
			try path = asset(folder, key, extension) catch (_:Dynamic) {}
			if (path != null) return FNFAssets.getSound(path);
		}
		throw '[codename-asset] Missing scoped audio: ' + folder + '/' + key;
	}
	public function getSparrowAtlas(key:String, ?library:String):FlxAtlasFrames {
		// Explicit Sparrow loading requires the raster even when an Animate or
		// paged atlas shares this basename. A frame collection is not a bitmap.
		var bitmap = image(imageKey(key), library, false);
		if (bitmap == null)
			throw '[codename-asset] Missing Sparrow bitmap: ' + key + ' in ' + root;
		var metadata = asset('images', imageKey(key), '.xml');
		var frames = FlxAtlasFrames.fromSparrow(bitmap, FNFAssets.getText(metadata));
		if (frames == null)
			throw '[codename-asset] Could not construct Sparrow atlas: ' + key + ' in ' + root;
		return frames;
	}
	public function getPackerAtlas(key:String, ?library:String):FlxAtlasFrames
		return FlxAtlasFrames.fromSpriteSheetPacker(image(imageKey(key), library, false), FNFAssets.getText(asset('images', imageKey(key), '.txt')));
	static function imageKey(key:String):String {
		return key != null && key.toLowerCase().endsWith('.png') ? key.substr(0, key.length - 4) : key;
	}
	public function getFrames(key:String, ?unused:Dynamic):FlxFramesCollection {
		key = imageKey(key);
		var animatePath = animateAtlasPath(key);
		if (animatePath != null)
			return FlxAnimateFrames.fromAnimate(animatePath);
		var paged = getPagedSparrowAtlas(key);
		if (paged != null) return paged;
		var metadata:String = null;
		try metadata = asset('images', key, '.xml') catch (_:Dynamic) {}
		if (metadata != null) return getSparrowAtlas(key);
		try metadata = asset('images', key, '.txt') catch (_:Dynamic) {}
		if (metadata != null) return getPackerAtlas(key);
		return FlxImageFrame.fromImage(image(key));
	}

	/** Return the on-disk owner-scoped folder used by flixel-animate. */
	public function animateAtlasPath(key:String):String {
		key = imageKey(key);
		var manifest:String = null;
		try manifest = file('images/' + key + '/Animation.json') catch (_:Dynamic) {}
		return manifest == null ? null : Path.directory(manifest);
	}

	/** Merge all consecutive numbered Sparrow pages for this owner. */
	function getPagedSparrowAtlas(key:String):FlxAtlasFrames {
		var firstPng:String = null;
		var firstXml:String = null;
		try firstPng = file('images/' + key + '/1.png') catch (_:Dynamic) {}
		try firstXml = file('images/' + key + '/1.xml') catch (_:Dynamic) {}
		if (firstPng == null && firstXml == null) return null;
		if (firstPng == null || firstXml == null)
			throw '[codename-asset] Incomplete first Sparrow page: ' + key + '/1';
		var atlas = FlxAtlasFrames.fromSparrow(FNFAssets.getBitmapData(firstPng), FNFAssets.getText(firstXml));
		var page = 2;
		while (true) {
			var png:String = null;
			var xml:String = null;
			try png = file('images/' + key + '/' + page + '.png') catch (_:Dynamic) {}
			try xml = file('images/' + key + '/' + page + '.xml') catch (_:Dynamic) {}
			if (png == null && xml == null) break;
			if (png == null || xml == null)
				throw '[codename-asset] Incomplete Sparrow page: ' + key + '/' + page;
			atlas.addAtlas(FlxAtlasFrames.fromSparrow(FNFAssets.getBitmapData(png), FNFAssets.getText(xml)));
			page++;
		}
		return atlas;
	}
}
