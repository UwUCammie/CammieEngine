package;

import haxe.Json;
import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

typedef ImportedModPackage = {
	var root:String;
	var title:String;
	var engine:String;
	var launchState:String;
	var songCount:Int;
}

typedef ImportedModDiscoveryResult = {
	var valid:Bool;
	var packages:Array<ImportedModPackage>;
	var diagnostics:Array<String>;
}

private typedef ImportedModDiscoveryCandidate = {
	var root:String;
	var title:String;
	var titleRank:Int;
	var engine:String;
	var songCount:Int;
	var songs:Map<String, Bool>;
	var statePaths:Array<String>;
}

/** Build one package row per imported owner from small chart provenance files.
	The scan is bounded to direct children of assets/data; it never walks media
	trees. Codename state entry points are discovered only below their owner.
*/
class ImportedModDiscovery {
	public static inline var MAX_PROVENANCE_FOLDERS:Int = 8192;
	public static inline var MAX_PROVENANCE_BYTES:Int = 65536;

	public static function discover(dataRoot:String, codenameCatalogRaw:String):ImportedModDiscoveryResult {
		var result:ImportedModDiscoveryResult = {valid:true, packages:[], diagnostics:[]};
		var candidates:Map<String, ImportedModDiscoveryCandidate> = new Map();
		#if sys
		if (dataRoot != null && FileSystem.isDirectory(dataRoot)) {
			var folders:Array<String> = [];
			try folders = FileSystem.readDirectory(dataRoot) catch (_:Dynamic) {
				result.diagnostics.push('Imported package provenance could not be scanned.');
			}
			folders.sort(Reflect.compare);
			if (folders.length > MAX_PROVENANCE_FOLDERS) {
				folders = folders.slice(0, MAX_PROVENANCE_FOLDERS);
				result.diagnostics.push('Imported package provenance scan limit reached.');
			}
			for (folder in folders) {
				if (!CodenameScriptDiscovery.safeName(folder)) continue;
				var folderPath = Path.join([dataRoot, folder]);
				if (!FileSystem.isDirectory(folderPath)) continue;
				var provenancePath = Path.join([folderPath, 'importProvenance.json']);
				if (!FileSystem.exists(provenancePath) || FileSystem.isDirectory(provenancePath)) continue;
				try {
					if (FileSystem.stat(provenancePath).size > MAX_PROVENANCE_BYTES) continue;
					var provenance:Dynamic = Json.parse(File.getContent(provenancePath));
					if (provenance == null || Reflect.field(provenance, 'version') != 1
						|| fieldString(provenance, 'destinationFolder') != folder) continue;
					var engine = supportedEngine(fieldString(provenance, 'sourceEngine'));
					var root = cleanOwnerRoot(fieldString(provenance, 'sourceOwner'));
					if (engine == '' || root == '') continue;
					var candidate = getOrCreate(candidates, root, engine);
					var modName = cleanTitle(fieldString(provenance, 'modName'));
					var rank = titleRank(fieldString(provenance, 'nameSource'));
					if (modName != '' && rank > candidate.titleRank) {
						candidate.title = modName;
						candidate.titleRank = rank;
					}
					var songKey = fieldString(provenance, 'sourceFolder');
					if (songKey == '') songKey = folder;
					songKey = songKey.toLowerCase();
					if (!candidate.songs.exists(songKey)) {
						candidate.songs.set(songKey, true);
						candidate.songCount++;
					}
				} catch (_:Dynamic) {
					// One stale or malformed receipt does not hide unrelated packages.
				}
			}
		}
		#end

		var catalog = CodenameModCatalog.parse(codenameCatalogRaw);
		if (!catalog.valid) {
			result.valid = false;
			result.diagnostics.push('[codename-mod-catalog] invalid catalog: ' + catalog.error);
		} else {
			for (owner in catalog.data.entries) {
				if (owner == null) continue;
				var root = cleanOwnerRoot(owner.root);
				if (root == '') continue;
				var candidate = getOrCreate(candidates, root, ImportEngine.CODENAME);
				var catalogTitle = titleFromCatalogLabel(owner.label, ImportEngine.CODENAME);
				if (candidate.title == '' && catalogTitle != '') candidate.title = catalogTitle;
				if (owner.states != null) for (state in owner.states)
					if (candidate.statePaths.indexOf(state) < 0) candidate.statePaths.push(state);
			}
		}

		for (candidate in candidates) {
			candidate.statePaths.sort(Reflect.compare);
			var launchState = '';
			if (candidate.engine == ImportEngine.CODENAME)
				launchState = CodenameModEntryPoint.find(candidate.root, candidate.statePaths);
			var title = candidate.title == '' ? humanizeRoot(candidate.root) : candidate.title;
			result.packages.push({root:candidate.root, title:title, engine:candidate.engine,
				launchState:launchState, songCount:candidate.songCount});
		}
		result.packages.sort(function(a:ImportedModPackage, b:ImportedModPackage):Int {
			var titleOrder = Reflect.compare(a.title.toLowerCase(), b.title.toLowerCase());
			if (titleOrder != 0) return titleOrder;
			var engineOrder = Reflect.compare(a.engine.toLowerCase(), b.engine.toLowerCase());
			return engineOrder == 0 ? Reflect.compare(a.root, b.root) : engineOrder;
		});
		return result;
	}

	/** Resolve the selected source owner for one native Freeplay row. Prefer the
		compatibility manifest, then use import provenance for packages with no
		copied script tree. */
	public static function ownerForSong(songName:String, dataRoot:String):String {
		#if sys
		if (!CodenameScriptDiscovery.safeName(songName) || dataRoot == null) return '';
		var folder = Path.join([dataRoot, songName.toLowerCase()]);
		if (!FileSystem.isDirectory(folder)) return '';
		var manifestPath = Path.join([folder, CompatScriptManifest.FILE_NAME]);
		if (FileSystem.exists(manifestPath) && !FileSystem.isDirectory(manifestPath)) try {
			if (FileSystem.stat(manifestPath).size <= MAX_PROVENANCE_BYTES) {
				var manifest = CompatScriptManifest.parse(File.getContent(manifestPath));
				var selected = cleanOwnerRoot(CompatScriptManifest.selectedRoot(manifest));
				if (selected != '') return selected;
			}
		} catch (_:Dynamic) {}
		var provenancePath = Path.join([folder, 'importProvenance.json']);
		if (FileSystem.exists(provenancePath) && !FileSystem.isDirectory(provenancePath)) try {
			if (FileSystem.stat(provenancePath).size <= MAX_PROVENANCE_BYTES) {
				var provenance:Dynamic = Json.parse(File.getContent(provenancePath));
				if (provenance != null && Reflect.field(provenance, 'version') == 1)
					return cleanOwnerRoot(fieldString(provenance, 'sourceOwner'));
			}
		} catch (_:Dynamic) {}
		#end
		return '';
	}

	static function getOrCreate(candidates:Map<String, ImportedModDiscoveryCandidate>,
		root:String, engine:String):ImportedModDiscoveryCandidate {
		var key = CompatScriptManifest.destinationKey(root);
		var candidate = candidates.get(key);
		if (candidate != null) {
			if (candidate.engine == '' && engine != '') candidate.engine = engine;
			return candidate;
		}
		candidate = {root:root, title:'', titleRank:0, engine:engine,
			songCount:0, songs:new Map(), statePaths:[]};
		candidates.set(key, candidate);
		return candidate;
	}

	static function supportedEngine(value:String):String {
		var engine = ImportEngine.normalize(value);
		return engine == ImportEngine.AUTO ? '' : engine;
	}

	static function cleanOwnerRoot(value:String):String {
		if (value == null) return '';
		var root = StringTools.replace(StringTools.trim(value), '\\', '/');
		var parts = root.split('/');
		if (parts.length != 3 || parts[0] != 'assets' || parts[1] != 'imported_mods'
			|| !CodenameScriptDiscovery.safeName(parts[2])) return '';
		var parsed = CompatScriptManifest.parse(Json.stringify({version:1,
			roots:[{engine:ImportEngine.CODENAME, path:root}]}));
		for (entry in parsed.roots)
			if (entry != null && CompatScriptManifest.destinationKey(entry.path)
				== CompatScriptManifest.destinationKey(root)) return entry.path;
		return '';
	}

	static function titleRank(source:String):Int {
		return switch (source == null ? '' : source.toLowerCase()) {
			case 'user': 3;
			case 'metadata': 2;
			case 'inferred': 1;
			default: 0;
		};
	}

	static function cleanTitle(value:String):String {
		if (value == null) return '';
		var title = StringTools.trim(value);
		if (title == '' || title.toLowerCase() == 'null' || title.length > 80) return '';
		for (index in 0...title.length) {
			var code = title.charCodeAt(index);
			if (code == null || code < 32 || code == 127) return '';
		}
		return title;
	}

	static function titleFromCatalogLabel(label:String, engine:String):String {
		var title = cleanTitle(label);
		if (title == '') return '';
		var suffix = ' · ' + engine;
		if (title.toLowerCase().endsWith(suffix.toLowerCase()))
			title = StringTools.trim(title.substr(0, title.length - suffix.length));
		return title;
	}

	static function humanizeRoot(root:String):String {
		var leaf = Path.withoutDirectory(root);
		var words = StringTools.replace(leaf, '-', ' ').split(' ');
		for (index in 0...words.length)
			if (words[index] != '') words[index] = words[index].substr(0, 1).toUpperCase() + words[index].substr(1);
		return words.join(' ');
	}

	static function fieldString(value:Dynamic, field:String):String {
		if (value == null) return '';
		var fieldValue:Dynamic = Reflect.field(value, field);
		return fieldValue == null ? '' : Std.string(fieldValue);
	}
}
