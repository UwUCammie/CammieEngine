package;

import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

using StringTools;

typedef PsychFamilyModChainRoot = {
	var root:String;
	var engine:String;
}

/** Folder and manifest names one Psych-family engine uses for its mod list. */
typedef PsychFamilyPackDescriptor = {
	var engine:String;
	/** Folder beside the executable that holds every mod. */
	var container:String;
	/** Per-mod manifest that carries the global switch. */
	var manifest:String;
	var globalKey:String;
}

/**
	Psych and Nightmare Vision look files up through the enabled global mods,
	then the top-level mods folder, then the game's own assets, underneath
	whatever the loaded mod supplies. The two engines only differ in folder and
	manifest names, so one resolver rebuilds that chain for a root out of the
	other roots picked up by the same import. Unrelated installed mods are never
	searched, and a mod switched off in modsList.txt stays out.
**/
class PsychFamilyModChain {
	public static final PSYCH:PsychFamilyPackDescriptor = {
		engine:ImportEngine.PSYCH, container:'mods', manifest:'pack.json', globalKey:'runsGlobally'
	};
	public static final NIGHTMARE_VISION:PsychFamilyPackDescriptor = {
		engine:ImportEngine.NIGHTMARE_VISION, container:'content', manifest:'meta.json', globalKey:'global'
	};
	public static inline var MODS_LIST:String = 'modsList.txt';
	static inline var MAX_METADATA_BYTES:Int = 256 * 1024;

	public static function descriptor(engine:String):Null<PsychFamilyPackDescriptor> {
		var dialect = ImportRevision.normalizeEngine(engine);
		if (dialect == ImportEngine.PSYCH) return PSYCH;
		if (dialect == ImportEngine.NIGHTMARE_VISION) return NIGHTMARE_VISION;
		return null;
	}

	/** Dependency roots for `root` in lookup order: enabled global siblings (in
	 * modsList.txt order), the top-level mods folder, then the game assets. Only
	 * roots of the same engine that appear in `batch` can be returned. */
	public static function resolve(root:String, engine:String,
		batch:Array<PsychFamilyModChainRoot>):Array<PsychFamilyModChainRoot> {
		var result:Array<PsychFamilyModChainRoot> = [];
		var family = descriptor(engine);
		var self = clean(root);
		if (family == null || self == '' || batch == null) return result;
		var release = releaseFor(self, family);
		var containerKey = key(Path.join([release, family.container]));
		var assetsKey = key(Path.join([release, 'assets']));
		var releaseKey = key(release);
		var selfKey = key(self);
		var globals:Array<PsychFamilyModChainRoot> = [];
		var top:PsychFamilyModChainRoot = null;
		var assets:PsychFamilyModChainRoot = null;
		var releaseRoot:PsychFamilyModChainRoot = null;
		var seen:Map<String, Bool> = new Map();
		for (entry in batch) {
			if (entry == null || descriptor(entry.engine) != family) continue;
			var path = clean(entry.root);
			var entryKey = key(path);
			if (path == '' || entryKey == selfKey || seen.exists(entryKey)) continue;
			seen.set(entryKey, true);
			var candidate:PsychFamilyModChainRoot = {root:path, engine:family.engine};
			if (entryKey == containerKey) top = candidate;
			else if (entryKey == assetsKey) assets = candidate;
			else if (entryKey == releaseKey) releaseRoot = candidate;
			else if (key(Path.directory(path)) == containerKey && isGlobal(path, family)) globals.push(candidate);
		}
		if (globals.length > 0) {
			var list = readModsList(release);
			var enabled:Array<PsychFamilyModChainRoot> = [];
			for (candidate in globals) {
				var name = folderKey(Path.withoutDirectory(candidate.root));
				if (list.disabled.exists(name)) continue;
				enabled.push(candidate);
			}
			// Listed mods keep their modsList.txt order; Psych appends folders it has
			// not listed yet, and sorting those keeps the result stable here.
			enabled.sort(function(a, b) {
				var left = folderKey(Path.withoutDirectory(a.root));
				var right = folderKey(Path.withoutDirectory(b.root));
				var leftRank = list.order.exists(left) ? list.order.get(left) : 0x3fffffff;
				var rightRank = list.order.exists(right) ? list.order.get(right) : 0x3fffffff;
				if (leftRank != rightRank) return leftRank < rightRank ? -1 : 1;
				return left < right ? -1 : (left > right ? 1 : 0);
			});
			for (candidate in enabled) result.push(candidate);
		}
		if (top != null) result.push(top);
		if (assets != null) result.push(assets);
		else if (releaseRoot != null) result.push(releaseRoot);
		return result;
	}

	/** Whether a mod folder declares itself global in its own manifest. */
	public static function isGlobal(modRoot:String, family:PsychFamilyPackDescriptor):Bool {
		if (modRoot == null || family == null) return false;
		var text = readSmallText(Path.join([modRoot, family.manifest]));
		if (text == null || text.trim() == '') return false;
		try {
			var data:Dynamic = tjson.TJSON.parse(text);
			return data != null && !Std.isOfType(data, Array) && Reflect.field(data, family.globalKey) == true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Work out the folder that holds the executable for a root inside it. */
	static function releaseFor(path:String, family:PsychFamilyPackDescriptor):String {
		var name = Path.withoutDirectory(path).toLowerCase();
		var parent = Path.directory(path);
		if (name == family.container) return parent;
		// Checked before the parent name so a release folder that happens to be
		// called "mods" still keeps its own assets.
		if (name == 'assets' && isDirectory(Path.join([parent, family.container]))) return parent;
		if (parent != '' && Path.withoutDirectory(parent).toLowerCase() == family.container) return Path.directory(parent);
		if (name == 'assets') return parent;
		return path;
	}

	static function isDirectory(path:String):Bool {
		#if sys
		try return FileSystem.exists(path) && FileSystem.isDirectory(path) catch (_:Dynamic) {}
		#end
		return false;
	}

	static function readModsList(release:String):{order:Map<String, Int>, disabled:Map<String, Bool>} {
		var result = {order:new Map<String, Int>(), disabled:new Map<String, Bool>()};
		var text = readSmallText(Path.join([release, MODS_LIST]));
		if (text == null) return result;
		var index = 0;
		for (line in text.split('\n')) {
			var trimmed = line.trim();
			if (trimmed == '') continue;
			var parts = trimmed.split('|');
			var name = folderKey(parts[0].trim());
			if (name == '' || result.order.exists(name)) continue;
			result.order.set(name, index++);
			// Both engines only treat an exact "1" as enabled.
			if (parts.length < 2 || parts[1].trim() != '1') result.disabled.set(name, true);
		}
		return result;
	}

	static function readSmallText(path:String):Null<String> {
		#if sys
		try {
			if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) return null;
			if (FileSystem.stat(path).size > MAX_METADATA_BYTES) return null;
			return File.getContent(path);
		} catch (_:Dynamic) {}
		#end
		return null;
	}

	static function clean(path:String):String {
		if (path == null) return '';
		var normalized = Path.normalize(StringTools.replace(path.trim(), '\\', '/'));
		while (normalized.length > 1 && normalized.endsWith('/'))
			normalized = normalized.substr(0, normalized.length - 1);
		return normalized;
	}

	static function key(path:String):String {
		var value = clean(path);
		#if windows
		value = value.toLowerCase();
		#end
		return value;
	}

	static function folderKey(name:String):String {
		var value = name == null ? '' : name.trim();
		#if windows
		value = value.toLowerCase();
		#end
		return value;
	}
}
