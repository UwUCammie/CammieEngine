package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

typedef CodenameFrameAtlasAsset = {
	var source:String;
	var relative:String;
}

typedef CodenameFrameAtlasPlan = {
	var mode:String;
	var files:Array<CodenameFrameAtlasAsset>;
	var diagnostics:Array<String>;
}

/**
	Plan the source files needed by a literal Codename `Paths.getFrames` key.

	This mirrors CodenamePaths.getFrames' selection order without evaluating donor
	code: Animate directory, numbered Sparrow pages, direct Sparrow, Packer, then
	plain image. Directory enumeration is restricted to a selected Animate atlas
	folder, and all resolutions remain inside the selected installation root.
*/
class CodenameFrameAtlasAssets {
	static inline var MAX_ATLAS_DEPTH:Int = 12;
	static inline var MAX_ATLAS_FILES:Int = 2048;
	static inline var MAX_SPARROW_PAGES:Int = 16;

	public static function plan(root:String, key:String):CodenameFrameAtlasPlan {
		var result:CodenameFrameAtlasPlan = {mode:'missing', files:[], diagnostics:[]};
		#if sys
		if (root == null || !FileSystem.isDirectory(root)) {
			result.diagnostics.push('atlas source root missing');
			return result;
		}
		var clean = normalizeKey(key);
		if (!safeRelative(clean)) {
			result.diagnostics.push('unsafe Paths.getFrames key: ' + Std.string(key));
			return result;
		}

		var imageStem = 'images/' + clean;
		var manifest = resolve(root, imageStem + '/Animation.json', false);
		if (manifest != null) {
			var folder = Path.directory(manifest);
			var files:Array<CodenameFrameAtlasAsset> = [];
			var overflow = false;
			var visit = function visit(directory:String, targetRelative:String, depth:Int):Void {
				if (overflow || depth > MAX_ATLAS_DEPTH || !withinRoot(root, directory)) return;
				var entries:Array<String>;
				try entries = FileSystem.readDirectory(directory) catch (_:Dynamic) return;
				entries.sort(Reflect.compare);
				for (entry in entries) {
					if (overflow || entry == '' || entry == '.' || entry == '..') continue;
					var path = Path.join([directory, entry]);
					if (!withinRoot(root, path)) continue;
					var child = targetRelative == '' ? entry : Path.join([targetRelative, entry]);
					if (FileSystem.isDirectory(path)) {
						visit(path, child, depth + 1);
						continue;
					}
					var extension = Path.extension(entry).toLowerCase();
					if (!FileSystem.exists(path)
						|| ['json', 'png', 'xml', 'txt', 'jpg', 'jpeg', 'webp'].indexOf(extension) < 0)
						continue;
					if (files.length >= MAX_ATLAS_FILES) {
						overflow = true;
						break;
					}
					files.push({source:path, relative:imageStem + '/' + child});
				}
			};
			visit(folder, '', 0);
			if (overflow) {
				result.diagnostics.push('Animate atlas file limit exceeded: ' + clean);
				return result;
			}
			if (files.length > 0) {
				result.mode = 'animate';
				result.files = files;
				return result;
			}
			result.diagnostics.push('Animate atlas has no supported files: ' + clean);
			return result;
		}

		var pageFiles:Array<CodenameFrameAtlasAsset> = [];
		var sawPage = false;
		for (page in 1...(MAX_SPARROW_PAGES + 1)) {
			var pageStem = imageStem + '/' + page;
			var png = resolve(root, pageStem + '.png', false);
			var xml = resolve(root, pageStem + '.xml', false);
			if (png == null && xml == null) break;
			sawPage = true;
			if (png == null || xml == null) {
				result.diagnostics.push('incomplete Sparrow page: ' + clean + '/' + page);
				return result;
			}
			pageFiles.push({source:png, relative:pageStem + '.png'});
			pageFiles.push({source:xml, relative:pageStem + '.xml'});
		}
		if (sawPage) {
			result.mode = 'pages';
			result.files = pageFiles;
			return result;
		}

		var png = resolve(root, imageStem + '.png', false);
		var xml = resolve(root, imageStem + '.xml', false);
		var txt = resolve(root, imageStem + '.txt', false);
		if (png != null && xml != null) {
			result.mode = 'sparrow';
			result.files = [
				{source:png, relative:imageStem + '.png'},
				{source:xml, relative:imageStem + '.xml'}
			];
			return result;
		}
		if (png != null && txt != null) {
			result.mode = 'packer';
			result.files = [
				{source:png, relative:imageStem + '.png'},
				{source:txt, relative:imageStem + '.txt'}
			];
			return result;
		}
		if (png != null) {
			result.mode = 'image';
			result.files = [{source:png, relative:imageStem + '.png'}];
			return result;
		}
		if (xml != null || txt != null) {
			result.diagnostics.push('atlas metadata has no image: ' + clean);
			return result;
		}
		result.diagnostics.push('no supported atlas or image for Paths.getFrames: ' + clean);
		return result;
		#else
		result.diagnostics.push('Paths.getFrames asset planning requires a filesystem target');
		return result;
		#end
	}

	static function normalizeKey(value:String):String {
		if (value == null) return '';
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		while (clean.startsWith('./')) clean = clean.substr(2);
		if (clean.toLowerCase().startsWith('assets/')) clean = clean.substr('assets/'.length);
		if (clean.toLowerCase().startsWith('images/')) clean = clean.substr('images/'.length);
		if (clean.toLowerCase().endsWith('.png')) clean = clean.substr(0, clean.length - 4);
		return clean;
	}

	static function safeRelative(value:String):Bool {
		if (value == null || value == '' || value.startsWith('/') || value.indexOf(':') >= 0) return false;
		for (part in value.split('/'))
			if (part == '' || part == '.' || part == '..') return false;
		return true;
	}

	#if sys
	static function resolve(root:String, relative:String, directory:Bool):Null<String> {
		if (!safeRelative(relative) || !FileSystem.isDirectory(root)) return null;
		var current = root;
		var chosen:Array<String> = [];
		var parts = relative.split('/');
		for (index in 0...parts.length) {
			var part = parts[index];
			var candidate = Path.join([current, part]);
			if (!FileSystem.exists(candidate)) {
				var matches:Array<String> = [];
				try for (entry in FileSystem.readDirectory(current))
					if (entry.toLowerCase() == part.toLowerCase()) matches.push(entry)
				catch (_:Dynamic) return null;
				if (matches.length != 1) return null;
				part = matches[0];
				candidate = Path.join([current, part]);
			}
			if (!FileSystem.exists(candidate) || !withinRoot(root, candidate)) return null;
			if (index < parts.length - 1 && !FileSystem.isDirectory(candidate)) return null;
			current = candidate;
			chosen.push(part);
		}
		if (FileSystem.isDirectory(current) != directory) return null;
		return Path.join([root, chosen.join('/')]);
	}

	static function withinRoot(root:String, path:String):Bool {
		if (!FileSystem.exists(root) || !FileSystem.exists(path)) return false;
		try {
			var base = Path.normalize(FileSystem.fullPath(root));
			var candidate = Path.normalize(FileSystem.fullPath(path));
			return candidate.startsWith(base + '/');
		} catch (_:Dynamic) {
			return false;
		}
	}
	#end
}
