package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

typedef CodenameCharacterAtlasAsset = {
	var source:String;
	var relative:String;
}

typedef CodenameCharacterAtlasData = {
	var mode:String;
	var files:Array<CodenameCharacterAtlasAsset>;
}

/** Resolve character atlas dependencies without leaving the selected Codename
 * installation. Both import-time materialization and live actor construction
 * use these owner-relative results. */
class CodenameCharacterAtlas {
	public static function files(root:String, sprite:String):Array<CodenameCharacterAtlasAsset> {
		var atlas = resolve(root, sprite);
		return atlas == null ? [] : atlas.files;
	}

	public static function resolve(root:String, sprite:String):Null<CodenameCharacterAtlasData> {
		#if sys
		if (root == null || !FileSystem.isDirectory(root)
			|| !CodenameScriptDiscovery.safeRelativeName(sprite)) return null;
		root = normalizeRoot(root);
		var base = 'images/characters/' + sprite;
		var manifest = resolveAsset(root, base + '/Animation.json');
		if (manifest != '') {
			var folder = Path.directory(manifest);
			var files:Array<CodenameCharacterAtlasAsset> = [];
			var visit = function visit(directory:String, relative:String, depth:Int):Void {
				if (depth > 12 || !CodenameScriptDiscovery.withinRoot(root, directory)) return;
				var entries:Array<String>;
				try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(directory)) catch (_:Dynamic) return;
				entries.sort(Reflect.compare);
				for (entry in entries) {
					if (entry == '' || entry == '.' || entry == '..') continue;
					var path = Path.join([directory, entry]);
					if (!CodenameScriptDiscovery.withinRoot(root, path)) continue;
					var child = relative == '' ? entry : Path.join([relative, entry]);
					if (FileSystem.isDirectory(path)) {
						visit(path, child, depth + 1);
						continue;
					}
					var extension = Path.extension(entry).toLowerCase();
					if (!FileSystem.exists(path)
						|| ['json', 'png', 'xml', 'txt', 'jpg', 'jpeg', 'webp'].indexOf(extension) < 0)
						continue;
					files.push({source:path, relative:child});
				}
			};
			visit(folder, '', 0);
			if (files.length > 0) return {mode:'animate', files:files};
		}

		var pages:Array<CodenameCharacterAtlasAsset> = [];
		for (page in 1...17) {
			var prefix = base + '/' + page;
			var png = resolveAsset(root, prefix + '.png');
			var xml = resolveAsset(root, prefix + '.xml');
			if (png == '' && xml == '') break;
			if (png == '' || xml == '') return null;
			pages.push({source:png, relative:page + '.png'});
			pages.push({source:xml, relative:page + '.xml'});
		}
		if (pages.length > 0) return {mode:'pages', files:pages};

		var png = resolveAsset(root, base + '.png');
		var xml = resolveAsset(root, base + '.xml');
		if (png != '' || xml != '') {
			var direct:Array<CodenameCharacterAtlasAsset> = [];
			if (png != '') direct.push({source:png, relative:'.png'});
			if (xml != '') direct.push({source:xml, relative:'.xml'});
			return {mode:'sparrow', files:direct};
		}

		// A short sprite key may omit a unique nested folder. Resolve that only
		// when exactly one paired Sparrow atlas has the requested basename.
		var basename = Path.withoutDirectory(sprite).toLowerCase();
		var candidates:Array<{png:String, xml:String}> = [];
		var characterRoot = Path.join([root, 'images', 'characters']);
		if (!FileSystem.isDirectory(characterRoot)) return null;
		var find = function find(directory:String, depth:Int):Void {
			if (depth > 12 || !CodenameScriptDiscovery.withinRoot(root, directory)) return;
			var entries:Array<String>;
			try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(directory)) catch (_:Dynamic) return;
			entries.sort(Reflect.compare);
			for (entry in entries) {
				var path = Path.join([directory, entry]);
				if (!CodenameScriptDiscovery.withinRoot(root, path)) continue;
				if (FileSystem.isDirectory(path)) {
					find(path, depth + 1);
					continue;
				}
				if (Path.extension(entry).toLowerCase() != 'png'
					|| Path.withoutExtension(entry).toLowerCase() != basename) continue;
				var xmlPath = Path.join([Path.directory(path), Path.withoutExtension(entry) + '.xml']);
				if (FileSystem.exists(xmlPath) && CodenameScriptDiscovery.withinRoot(root, xmlPath))
					candidates.push({png:path, xml:xmlPath});
			}
		};
		find(characterRoot, 0);
		if (candidates.length != 1) return null;
		return {mode:'sparrow', files:[
			{source:candidates[0].png, relative:'.png'},
			{source:candidates[0].xml, relative:'.xml'}
		]};
		#else
		return null;
		#end
	}

	#if sys
	static function resolveAsset(root:String, relative:String):String {
		var resolved = CodenameScriptDiscovery.resolveScopedRelative(root, relative);
		return resolved == null ? '' : Path.join([root, resolved]);
	}

	static function normalizeRoot(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		while (clean.endsWith('/')) clean = clean.substr(0, clean.length - 1);
		return clean;
	}
	#end
}
