package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

typedef CodenameSplashDependencyFile = {
	var source:String;
	var relative:String;
}

typedef CodenameSplashDependencyPlan = {
	var files:Array<CodenameSplashDependencyFile>;
	var diagnostics:Array<String>;
}

/** Selected-owner Codename splash definitions and their Sparrow atlas files.
	Only direct XML children of data/splashes are inspected; sprite dependencies
	come from each definition's `sprite` attribute and stay within the same owner.
*/
class CodenameSplashDependencies {
	static inline var MAX_SPLASH_DEFINITIONS:Int = 256;

	public static function filesFor(ownerRoot:String):CodenameSplashDependencyPlan {
		var result:CodenameSplashDependencyPlan = {files:[], diagnostics:[]};
		#if sys
		if (ownerRoot == null || !FileSystem.isDirectory(ownerRoot)) return result;
		// Direct Codename mods use data/ + images/ at the owner root. Older
		// FNF-style packages keep the same logical owner paths under assets/.
		// Select one layout as a unit so definitions and atlases never mix roots.
		var layoutPrefix = chooseLayout(ownerRoot);
		if (layoutPrefix == null) return result;
		var folderRelative = resolveDirectory(ownerRoot, layoutPrefix + 'data/splashes');
		if (folderRelative == null) return result;
		var folder = Path.join([ownerRoot, folderRelative]);
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(folder) catch (_:Dynamic) {
			result.diagnostics.push('[codename-splash-dependency] Could not enumerate data/splashes');
			return result;
		}
		entries.sort(Reflect.compare);
		if (entries.length > MAX_SPLASH_DEFINITIONS)
			result.diagnostics.push('[codename-splash-dependency] data/splashes exceeds '
				+ MAX_SPLASH_DEFINITIONS + ' entry scan limit');
		var seen:Map<String, Bool> = new Map();
		var examined = 0;
		for (entry in entries) {
			if (examined++ >= MAX_SPLASH_DEFINITIONS) break;
			if (!CodenameScriptDiscovery.safeName(entry)
				|| Path.extension(entry).toLowerCase() != 'xml') continue;
			var sourceRelative = folderRelative + '/' + entry;
			var definition = resolveFile(ownerRoot, sourceRelative);
			if (definition == null) continue;
			append(ownerRoot, result.files, seen, Path.join([ownerRoot, definition]),
				'data/splashes/' + entry);
			var sourcePath = Path.join([ownerRoot, definition]);
			var content:String;
			try content = File.getContent(sourcePath) catch (_:Dynamic) {
				result.diagnostics.push('[codename-splash-dependency] Could not read data/splashes/' + entry);
				continue;
			}
			var root:Xml = null;
			try root = Xml.parse(content).firstElement() catch (_:Dynamic) {}
			if (root == null || root.nodeName != 'splashes' || !root.exists('sprite')) {
				result.diagnostics.push('[codename-splash-dependency] Invalid splash definition data/splashes/' + entry);
				continue;
			}
			var sprite = StringTools.trim(root.get('sprite'));
			if (!CodenameScriptDiscovery.safeRelativeName(sprite)) {
				result.diagnostics.push('[codename-splash-dependency] Unsafe sprite key in data/splashes/' + entry);
				continue;
			}
			// CodenamePaths.getSparrowAtlas strips only a trailing .png, then
			// requests images/<key>.png and images/<key>.xml from the same owner.
			var imageKey = StringTools.endsWith(sprite.toLowerCase(), '.png')
				? sprite.substr(0, sprite.length - 4) : sprite;
			for (extension in ['.png', '.xml']) {
				var sourceAtlasRelative = layoutPrefix + 'images/' + imageKey + extension;
				var atlasRelative = 'images/' + imageKey + extension;
				var atlas = resolveFile(ownerRoot, sourceAtlasRelative);
				if (atlas == null) {
					result.diagnostics.push('[codename-splash-dependency] Missing selected-owner '
						+ atlasRelative + ' referenced by data/splashes/' + entry);
					continue;
				}
				append(ownerRoot, result.files, seen, Path.join([ownerRoot, atlas]), atlasRelative);
			}
		}
		#end
		return result;
	}

	#if sys
	static function chooseLayout(ownerRoot:String):Null<String> {
		var direct = resolveDirectory(ownerRoot, 'data/splashes');
		if (direct != null) return '';
		var legacy = resolveDirectory(ownerRoot, 'assets/data/splashes');
		if (legacy != null) return 'assets/';
		return null;
	}

	static function resolveDirectory(ownerRoot:String, relative:String):Null<String> {
		if (!CodenameScriptDiscovery.safeRelativeName(relative)) return null;
		var current = ownerRoot;
		var chosen:Array<String> = [];
		for (part in relative.split('/')) {
			var selected:String = null;
			var exact = Path.join([current, part]);
			if (FileSystem.exists(exact)) selected = part;
			else {
				var matches:Array<String> = [];
				try for (entry in FileSystem.readDirectory(current))
					if (CodenameScriptDiscovery.safeName(entry) && entry.toLowerCase() == part.toLowerCase())
						matches.push(entry)
				catch (_:Dynamic) return null;
				if (matches.length != 1) return null;
				selected = matches[0];
			}
			current = Path.join([current, selected]);
			if (!FileSystem.isDirectory(current) || !CodenameScriptDiscovery.withinRoot(ownerRoot, current))
				return null;
			chosen.push(selected);
		}
		return chosen.join('/');
	}

	static function resolveFile(ownerRoot:String, relative:String):Null<String> {
		if (!CodenameScriptDiscovery.safeRelativeName(relative)) return null;
		var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, relative);
		if (resolution.relative == null) return null;
		var source = Path.join([ownerRoot, resolution.relative]);
		if (FileSystem.isDirectory(source) || !CodenameScriptDiscovery.withinRoot(ownerRoot, source))
			return null;
		return resolution.relative;
	}

	static function append(ownerRoot:String, output:Array<CodenameSplashDependencyFile>, seen:Map<String, Bool>,
		source:String, relative:String):Void {
		if (!CodenameScriptDiscovery.safeRelativeName(relative) || source == null
			|| !FileSystem.exists(source) || FileSystem.isDirectory(source)
			|| !CodenameScriptDiscovery.withinRoot(ownerRoot, source)) return;
		var key = relative;
		if (seen.exists(key)) return;
		seen.set(key, true);
		output.push({source:source, relative:relative});
	}
	#end
}
