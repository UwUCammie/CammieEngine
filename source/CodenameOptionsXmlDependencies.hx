package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

typedef CodenameOptionsXmlDependencyFile = {
	var source:String;
	var relative:String;
}

typedef CodenameOptionsXmlDependencyPlan = {
	var files:Array<CodenameOptionsXmlDependencyFile>;
	var diagnostics:Array<String>;
}

/** Selected-owner package options documents consumed by Codename's menu API.
	Only the known options document and XML directly in its options subfolder are
	materialized. This never walks arbitrary package data or another owner.
*/
class CodenameOptionsXmlDependencies {
	static inline var MAX_OPTIONS_XML_FILES:Int = 256;

	public static function filesFor(ownerRoot:String):CodenameOptionsXmlDependencyPlan {
		var result:CodenameOptionsXmlDependencyPlan = {files:[], diagnostics:[]};
		#if sys
		if (ownerRoot == null || !FileSystem.isDirectory(ownerRoot)) return result;
		var seen:Map<String, Bool> = new Map();
		for (relative in ['data/config/options.xml', 'config/options.xml']) {
			var resolved = CodenameScriptDiscovery.scopedResolution(ownerRoot, relative);
			if (resolved.relative == null) continue;
			append(ownerRoot, resolved.relative, relative, seen, result.files);
		}
		for (folder in ['data/config/options', 'config/options']) {
			var resolvedFolder = resolveDirectory(ownerRoot, folder);
			if (resolvedFolder == null) continue;
			var absoluteFolder = Path.join([ownerRoot, resolvedFolder]);
			var entries:Array<String>;
			try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(absoluteFolder)) catch (_:Dynamic) {
				result.diagnostics.push('[codename-options-dependency] Could not enumerate ' + folder);
				continue;
			}
			entries.sort(Reflect.compare);
			if (entries.length > MAX_OPTIONS_XML_FILES)
				result.diagnostics.push('[codename-options-dependency] ' + folder + ' exceeds '
					+ MAX_OPTIONS_XML_FILES + ' entry scan limit');
			var examined = 0;
			for (entry in entries) {
				if (examined++ >= MAX_OPTIONS_XML_FILES) break;
				if (!CodenameScriptDiscovery.safeName(entry)
					|| Path.extension(entry).toLowerCase() != 'xml') continue;
				var sourceRelative = resolvedFolder + '/' + entry;
				var resolution = CodenameScriptDiscovery.scopedResolution(ownerRoot, sourceRelative);
				if (resolution.relative == null) continue;
				append(ownerRoot, resolution.relative, folder + '/' + entry, seen, result.files);
			}
		}
		#end
		return result;
	}

	#if sys
	static function resolveDirectory(ownerRoot:String, relative:String):Null<String> {
		if (ownerRoot == null || !FileSystem.isDirectory(ownerRoot)
			|| !CodenameScriptDiscovery.safeRelativeName(relative)) return null;
		var current = ownerRoot;
		var chosen:Array<String> = [];
		for (part in relative.split('/')) {
			var selected:String = null;
			var exact = Path.join([current, part]);
			if (FileSystem.exists(exact)) selected = part;
			else {
				var matches:Array<String> = [];
				try for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(current)))
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

	static function append(ownerRoot:String, sourceRelative:String, destinationRelative:String,
		seen:Map<String, Bool>, output:Array<CodenameOptionsXmlDependencyFile>):Void {
		if (!CodenameScriptDiscovery.safeRelativeName(sourceRelative)
			|| !CodenameScriptDiscovery.safeRelativeName(destinationRelative)) return;
		var key = destinationRelative.toLowerCase();
		if (seen.exists(key)) return;
		var source = Path.join([ownerRoot, sourceRelative]);
		if (!FileSystem.exists(source) || FileSystem.isDirectory(source)
			|| !CodenameScriptDiscovery.withinRoot(ownerRoot, source)) return;
		seen.set(key, true);
		output.push({source:source, relative:destinationRelative});
	}
	#end
}
