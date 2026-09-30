package;

import haxe.Json;
import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
using StringTools;

typedef CodenameModCatalogEntry = {
	var root:String;
	var label:String;
	var states:Array<String>;
}

typedef CodenameModCatalogData = {
	var version:Int;
	var entries:Array<CodenameModCatalogEntry>;
}

typedef CodenameModCatalogMerge = {
	var valid:Bool;
	var changed:Bool;
	var data:CodenameModCatalogData;
	var error:String;
}

typedef CodenameModCatalogParse = {
	var valid:Bool;
	var changed:Bool;
	var data:CodenameModCatalogData;
	var error:String;
}

/** Additive destination-only directory of imported Codename owners and their
 * launchable state scripts. Owners with global scripts but no custom states
 * remain switchable with an empty `states` array. */
class CodenameModCatalog {
	public static inline var VERSION:Int = 1;
	public static inline var ENGINE:String = 'Codename Engine';
	public static inline var FILE_NAME:String = 'codenameMods.json';
	public static inline var PATH:String = 'assets/data/codenameMods.json';

	static function cleanRoot(value:String):String {
		var root = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		if (!root.startsWith(CompatScriptManifest.ROOT_PREFIX + '/')) return '';
		var parts = root.split('/');
		if (parts.length != 3 || !CodenameScriptDiscovery.safeName(parts[2])) return '';
		var probe = CompatScriptManifest.parse(Json.stringify({version:VERSION,
			roots:[{engine:ENGINE, path:root}]}));
		for (entry in probe.roots)
			if (entry != null && entry.engine == ENGINE
				&& CompatScriptManifest.destinationKey(entry.path) == CompatScriptManifest.destinationKey(root))
				return entry.path;
		return '';
	}

	static function cleanLabel(value:String, root:String):String {
		var label = StringTools.trim(value == null ? '' : value);
		if (label == '') label = haxe.io.Path.withoutDirectory(root);
		label = ~/[\x00-\x1F\x7F]/g.replace(label, ' ');
		if (label.length > 80) label = label.substr(0, 80);
		return StringTools.trim(label);
	}

	static function cleanState(value:String, root:String):String {
		if (value == null) return '';
		var relative = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (!StringTools.startsWith(relative, 'data/states/')
			|| !relative.toLowerCase().endsWith('.hx')
			|| !CodenameScriptDiscovery.safeRelativeName(relative)) return '';
		if (Path.withoutDirectory(relative).toLowerCase() == 'musicbeattransition.hx') return '';
		#if sys
		if (isTransitionHelper(root, relative)) return '';
		#end
		// Import planning can run before the destination namespace exists. At
		// runtime, catalog consumers resolve again through scopedResolution(),
		// which rejects stale paths and symlink escapes before reading them.
		#if sys
		if (FileSystem.isDirectory(root)
			&& CodenameScriptDiscovery.scopedResolution(root, relative).relative == null) return '';
		#end
		return relative;
	}

	#if sys
	static var transitionTargetsByRoot:Map<String, Map<String, Bool>> = new Map();

	/** Transition scripts execute with a transition-host lifecycle and injected
	 * transition fields. Exclude the engine's default transition script and any
	 * state script explicitly registered as a MusicBeatTransition hook. */
	static function isTransitionHelper(root:String, relative:String):Bool {
		if (Path.withoutDirectory(relative).toLowerCase() == 'musicbeattransition.hx') return true;
		if (root == null || !FileSystem.isDirectory(root)) return false;
		var rootKey = Path.normalize(root);
		var targets = transitionTargetsByRoot.get(rootKey);
		if (targets == null) {
			targets = new Map();
			targets.set('data/states/musicbeattransition.hx', true);
			var discovery = CodenameScriptDiscovery.discoverOwnerScriptsDetailed(root, '');
			var assignment = new EReg('MusicBeatTransition\\s*\\.\\s*script\\s*=\\s*["\\\']([^"\\\']*)["\\\']', 'g');
			for (script in discovery.files) {
				if (script.path == null || !FileSystem.exists(script.path) || FileSystem.isDirectory(script.path)) continue;
				var source = '';
				try source = File.getContent(script.path) catch (_:Dynamic) continue;
				var remaining = source;
				var attempts = 0;
				while (attempts++ < 64 && assignment.match(remaining)) {
					var key = StringTools.replace(StringTools.trim(assignment.matched(1)), '\\', '/');
					if (key != '') {
						if (!key.toLowerCase().endsWith('.hx')) key += '.hx';
						if (StringTools.startsWith(key, 'data/states/')
							&& CodenameScriptDiscovery.safeRelativeName(key)) targets.set(key.toLowerCase(), true);
					}
					var position = assignment.matchedPos();
					if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
					remaining = remaining.substr(position.pos + position.len);
				}
			}
			transitionTargetsByRoot.set(rootKey, targets);
		}
		return targets.exists(relative.toLowerCase());
	}

	static function pruneMissingOwners(data:CodenameModCatalogData):Bool {
		var kept:Array<CodenameModCatalogEntry> = [];
		var changed = false;
		for (entry in data.entries) {
			if (entry == null || !FileSystem.isDirectory(entry.root)) {
				changed = true;
				continue;
			}
			kept.push(entry);
		}
		data.entries = kept;
		return changed;
	}
	#end

	static function newData():CodenameModCatalogData
		return {version:VERSION, entries:[]};

	public static function parse(raw:String):CodenameModCatalogParse {
		if (raw == null || StringTools.trim(raw) == '') return {valid:true, changed:false, data:newData(), error:''};
		try {
			var value:Dynamic = Json.parse(raw);
			if (value == null || !Std.isOfType(Reflect.field(value, 'entries'), Array))
				return {valid:false, changed:false, data:newData(), error:'invalid entries'};
			var data = newData();
			var changed = false;
			var seen:Map<String, Bool> = new Map();
			for (rawEntry in (cast Reflect.field(value, 'entries'):Array<Dynamic>)) {
				if (rawEntry == null) { changed = true; continue; }
				var root = cleanRoot(Std.string(Reflect.field(rawEntry, 'root')));
				if (root == '') { changed = true; continue; }
				var key = CompatScriptManifest.destinationKey(root);
				if (seen.exists(key)) { changed = true; continue; }
				var states:Array<String> = [];
				var rawStates:Dynamic = Reflect.field(rawEntry, 'states');
				if (Std.isOfType(rawStates, Array)) for (rawState in (cast rawStates:Array<Dynamic>)) {
					var state = cleanState(rawState == null ? '' : Std.string(rawState), root);
					if (state != '' && states.indexOf(state) < 0) states.push(state);
					else changed = true;
				} else changed = true;
				states.sort(Reflect.compare);
				seen.set(key, true);
				data.entries.push({root:root,
					label:cleanLabel(Std.string(Reflect.field(rawEntry, 'label')), root), states:states});
			}
			return {valid:true, changed:changed, data:data, error:''};
		} catch (error:Dynamic) {
			return {valid:false, changed:false, data:newData(), error:Std.string(error)};
		}
	}

	/** Merge one imported root, dropping only stale catalog references and
	 * transition-hook rows that cannot launch as ordinary owner states. No owner
	 * files are removed or rewritten by this catalog reconciliation. */
	public static function merge(raw:String, root:String, label:String,
		statePaths:Array<String>):CodenameModCatalogMerge {
		#if sys
		transitionTargetsByRoot.remove(Path.normalize(root == null ? '' : root));
		#end
		var parsed = parse(raw);
		if (!parsed.valid) return {valid:false, changed:false, data:parsed.data, error:parsed.error};
		#if sys
		var changed = parsed.changed;
		if (pruneMissingOwners(parsed.data)) changed = true;
		#else
		var changed = parsed.changed;
		#end
		var clean = cleanRoot(root);
		if (clean == '') return {valid:false, changed:false, data:parsed.data, error:'unsafe owner root'};
		var states:Array<String> = [];
		if (statePaths != null) for (value in statePaths) {
			var state = cleanState(value, clean);
			if (state != '' && states.indexOf(state) < 0) states.push(state);
		}
		states.sort(Reflect.compare);
		var entry:CodenameModCatalogEntry = null;
		for (existing in parsed.data.entries)
			if (CompatScriptManifest.destinationKey(existing.root) == CompatScriptManifest.destinationKey(clean)) {
				entry = existing;
				break;
			}
		if (entry == null) {
			entry = {root:clean, label:cleanLabel(label, clean), states:[]};
			parsed.data.entries.push(entry);
			changed = true;
		}
		if (entry.label == '') {
			entry.label = cleanLabel(label, clean);
			changed = true;
		}
		for (state in states) if (entry.states.indexOf(state) < 0) {
			entry.states.push(state);
			changed = true;
		}
		entry.states.sort(Reflect.compare);
		return {valid:true, changed:changed, data:parsed.data, error:''};
	}

	public static function stringify(data:CodenameModCatalogData):String
		return Json.stringify(data == null ? newData() : data);
}
