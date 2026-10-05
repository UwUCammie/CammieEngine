package;

import haxe.Json;
import haxe.crypto.Md5;
import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
#end

using StringTools;

typedef CompatScriptRoot = {
	var engine:String;
	var path:String;
	/** Explicit base-provider scope; it supplies resources but never chart/audio ownership. */
	@:optional var dependency:Bool;
}

/** Destination-only record for a validated overlay retained when its base
 * target was unavailable or protected; ImportOverlayResolver consumes it as
 * a read-only virtual asset layer. */
typedef CompatOverlayRecord = {
	var engine:String;
	var mod:String;
	var operation:String;
	var kind:String;
	/** Import-plan traversal order; -1 denotes an older manifest. */
	@:optional var order:Int;
	var relativePath:String;
	var targetPath:String;
	var provenance:String;
	var reason:String;
	var payload:String;
}

typedef CompatScriptManifestData = {
	var version:Int;
	var roots:Array<CompatScriptRoot>;
	/**
		Root which owns this song's companion scripts.  Older manifests did not
		carry ownership, so normalization falls back to their first root.
	*/
	@:optional var selectedRoot:String;
	/** Validated overlay provenance consumed by ImportOverlayResolver as a
		read-only virtual asset layer. */
	@:optional var overlays:Array<CompatOverlayRecord>;
}

/**
	Per-song provenance for imported compatibility scripts.

	Foreign engines commonly use a global `scripts/` directory, but merging
	several selected games into one destination must not make every global script
	run for every imported song.  The importer copies each donor's script-bearing
	trees below a deterministic namespace and stores only that destination path in
	the song folder.  Donor paths are never persisted or executed at runtime.
*/
class CompatScriptManifest {
	public static inline var VERSION:Int = 1;
	public static inline var FILE_NAME:String = 'compatScripts.json';
	public static inline var ROOT_PREFIX:String = 'assets/imported_mods';
	public static inline var OVERLAY_FILE_NAME:String = 'compatOverlays.json';

	/** Stable destination namespace for one engine root. */
	public static function namespaceFor(sourceRoot:String, engine:String):String {
		#if sys
		var context = ImportIO.current();
		if (context != null) {
			var retained = context.namespace(sourceRoot, engine);
			if (retained != null && retained != '') return retained;
		}
		#end
		var normalized = normalizeSource(sourceRoot);
		var base = Path.withoutDirectory(normalized);
		if (base == null || StringTools.trim(base) == '')
			base = 'root';
		var label = slug(engine) + '-' + slug(base);
		if (label == '-' || label == '')
			label = 'imported-root';
		var legacyNamespace = label + '-' + Md5.encode(normalized).substr(0, 10);
		return ImportSongOwnership.priorNamespace(sourceRoot, engine, legacyNamespace);
	}

	public static function destinationRoot(sourceRoot:String, engine:String):String {
		return Path.normalize(Path.join([ROOT_PREFIX, namespaceFor(sourceRoot, engine)]));
	}

	/** Global destination-only sidecar for bounded overlays not yet materialized. */
	public static function overlayManifestPath():String {
		return Path.normalize(Path.join([ROOT_PREFIX, OVERLAY_FILE_NAME]));
	}

	/** Compare destination-only namespace paths using the host filesystem's
	 * case rules.  Linux can legitimately retain two case-variant legacy
	 * namespaces; Windows cannot. */
	public static function destinationKey(value:String):String {
		var clean = safeDestination(value == null ? '' : value);
		#if windows
		return clean.toLowerCase();
		#else
		return clean;
		#end
	}

	/** Dialects with their own loader must not enter legacy Psych discovery. */
	public static function usesDedicatedScriptRuntime(data:CompatScriptManifestData, root:String):Bool {
		if (data == null || data.roots == null) return false;
		var key = destinationKey(root);
		if (key == '') return false;
		for (entry in data.roots) if (entry != null && destinationKey(entry.path) == key
			&& (entry.engine == ImportEngine.NIGHTMARE_VISION || entry.engine == ImportEngine.CODENAME)) return true;
		return false;
	}

	public static function create(sourceRoot:String, engine:String):CompatScriptManifestData {
		var destination = destinationRoot(sourceRoot, engine);
		return {
			version: VERSION,
			roots: [{engine:engine == null ? '' : engine, path:destination}],
			selectedRoot: destination
		};
	}

	public static function stringify(data:CompatScriptManifestData):String {
		return Json.stringify(normalize(data));
	}

	/** Parse and validate destination-only paths; traversal/absolute paths drop. */
	public static function parse(raw:String):CompatScriptManifestData {
		if (raw == null || StringTools.trim(raw) == '')
			return {version:VERSION, roots:[]};
		try {
			return normalize(cast Json.parse(raw));
		} catch (_:Dynamic) {
			return {version:VERSION, roots:[]};
		}
	}

	public static function normalize(data:Dynamic):CompatScriptManifestData {
		var result:CompatScriptManifestData = {version:VERSION, roots:[], overlays:[]};
		if (data == null)
			return result;
		var rawOverlays:Dynamic = Reflect.field(data, 'overlays');
		if (Std.isOfType(rawOverlays, Array)) {
			var seenOverlays:Map<String, Bool> = new Map<String, Bool>();
			for (entry in (cast rawOverlays:Array<Dynamic>)) {
				if (entry == null)
					continue;
				var relative = safeOverlayRelative(fieldString(entry, 'relativePath'));
				var target = safeOverlayRelative(fieldString(entry, 'targetPath'));
				var operation = fieldString(entry, 'operation');
				if (relative == '' || target == ''
					|| (operation != '_append' && operation != '_replace' && operation != '_merge'))
					continue;
				var provenance = fieldString(entry, 'provenance');
				var rawOrder:Dynamic = Reflect.field(entry, 'order');
				var parsedOrder = rawOrder == null ? null : Std.parseInt(Std.string(rawOrder));
				var order = parsedOrder == null ? -1 : parsedOrder;
				// Duplicate identity is independent of traversal order.  The order is
				// execution metadata, not a second operation; keeping it out of this
				// key prevents repeated persisted records from being applied twice while
				// still preserving same-payload operations from different mods.
				var key = fieldString(entry, 'engine') + '|' + fieldString(entry, 'mod') + '|'
					+ operation + '|' + fieldString(entry, 'kind') + '|' + relative + '|'
					+ target + '|' + provenance + '|' + fieldString(entry, 'reason') + '|'
					+ fieldString(entry, 'payload');
				if (seenOverlays.exists(key))
					continue;
				seenOverlays.set(key, true);
				result.overlays.push({
					engine: fieldString(entry, 'engine'),
					mod: fieldString(entry, 'mod'),
					operation: operation,
					kind: fieldString(entry, 'kind'),
					order: order,
					relativePath: relative,
					targetPath: target,
					provenance: provenance,
					reason: fieldString(entry, 'reason'),
					payload: fieldString(entry, 'payload')
				});
			}
		}
		var rawRoots:Dynamic = Reflect.field(data, 'roots');
		if (!Std.isOfType(rawRoots, Array)) {
			if (result.overlays.length == 0)
				result.overlays = null;
			return result;
		}
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (entry in (cast rawRoots:Array<Dynamic>)) {
			if (entry == null)
				continue;
			var engineValue:Dynamic = Reflect.field(entry, 'engine');
			var pathValue:Dynamic = Reflect.field(entry, 'path');
			var engine = engineValue == null ? '' : StringTools.trim(Std.string(engineValue));
			var path = safeDestination(pathValue == null ? '' : Std.string(pathValue));
			var key = destinationKey(path);
			if (path == '' || seen.exists(key))
				continue;
			seen.set(key, true);
			var root:CompatScriptRoot = {engine:engine, path:path};
			if (Reflect.field(entry, 'dependency') == true) root.dependency = true;
			result.roots.push(root);
		}
		// Keep old manifests readable while making ownership explicit for every
		// normalized manifest.  A selected root must already be one of the safe
		// destination roots; malformed/foreign values cannot redirect runtime
		// discovery outside the manifest.
		var selectedValue:Dynamic = Reflect.field(data, 'selectedRoot');
		var selected = safeDestination(selectedValue == null ? '' : Std.string(selectedValue));
		if (selected != '') {
			var selectedKnown = false;
			for (root in result.roots)
				if (root != null && root.dependency != true && destinationKey(root.path) == destinationKey(selected)) {
					selected = root.path;
					selectedKnown = true;
					break;
				}
			if (!selectedKnown)
				selected = '';
		}
		if (selected == '')
			for (root in result.roots) if (root.dependency != true) {selected = root.path; break;}
		if (selected == '') result.roots = [];
		if (selected != '')
			result.selectedRoot = selected;
		if (result.overlays.length == 0)
			result.overlays = null;
		return result;
	}

	/** Return the manifest's explicit owner, or its deterministic legacy owner. */
	public static function selectedRoot(data:CompatScriptManifestData):String {
		if (data == null)
			return '';
		var normalized = normalize(data);
		return normalized.selectedRoot == null ? '' : normalized.selectedRoot;
	}

	/**
		Return roots in runtime precedence order.  The selected owner is first;
		remaining roots retain their manifest order so old multi-root manifests
		remain deterministic and can still provide unique non-character assets.
	*/
	public static function rootsInPrecedence(data:CompatScriptManifestData):Array<CompatScriptRoot> {
		var normalized = normalize(data);
		var result:Array<CompatScriptRoot> = [];
		var selected = selectedRoot(normalized);
		if (selected != '')
			for (root in normalized.roots)
				if (root != null && destinationKey(root.path) == destinationKey(selected)) {
					result.push(root);
					break;
				}
		for (root in normalized.roots)
			if (root != null && (selected == '' || destinationKey(root.path) != destinationKey(selected)))
				result.push(root);
		return result;
	}

	static function safeDestination(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0)
			return '';
		var parts = clean.split('/');
		for (part in parts)
			if (part == '..' || part == '')
				return '';
		var normalized = Path.normalize(clean);
		var prefix = ROOT_PREFIX + '/';
		return normalized.startsWith(prefix) ? normalized : '';
	}

	static function safeOverlayRelative(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0)
			return '';
		var parts = clean.split('/');
		for (part in parts)
			if (part == '' || part == '.' || part == '..')
				return '';
		return clean == 'data' || clean.startsWith('data/') ? parts.join('/') : '';
	}

	static function fieldString(value:Dynamic, field:String):String {
		if (value == null)
			return '';
		var raw:Dynamic = Reflect.field(value, field);
		return raw == null ? '' : Std.string(raw);
	}

	static function normalizeSource(value:String):String {
		var normalized = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		var unc = normalized.startsWith('//');
		var drive = normalized.length > 1 && normalized.charAt(1) == ':';
		// ImportRootScanner normally supplies an absolute path, but legacy module
		// callers can still hand this helper a relative donor root. Canonicalize
		// those spellings before hashing so `mods/Pack` and `<cwd>/mods/Pack`
		// retain one materialized namespace. Keep foreign Windows spellings intact
		// when the current host cannot interpret them (for example Linux auditing a
		// saved C:/ path).
		#if sys
		#if windows
		try {
			normalized = StringTools.replace(FileSystem.fullPath(normalized), '\\', '/');
		} catch (_:Dynamic) {}
		#else
		if (!drive && !unc) {
			try {
				normalized = StringTools.replace(FileSystem.fullPath(normalized), '\\', '/');
			} catch (_:Dynamic) {}
		}
		#end
		#end
		normalized = Path.normalize(normalized);
		if (unc && !normalized.startsWith('//')) {
			while (normalized.startsWith('/'))
				normalized = normalized.substr(1);
			normalized = normalized == '' ? '//' : '//' + normalized;
		}
		while (normalized.length > 1 && normalized.endsWith('/'))
			normalized = normalized.substr(0, normalized.length - 1);
		#if windows
		normalized = normalized.toLowerCase();
		#end
		return normalized;
	}

	static function slug(value:String):String {
		var input = value == null ? '' : value.toLowerCase();
		var output = new StringBuf();
		var lastDash = false;
		for (index in 0...input.length) {
			var code = input.charCodeAt(index);
			var alphaNumeric = (code >= 97 && code <= 122) || (code >= 48 && code <= 57);
			if (alphaNumeric) {
				output.addChar(code);
				lastDash = false;
			} else if (!lastDash && output.length > 0) {
				output.add('-');
				lastDash = true;
			}
		}
		var result = output.toString();
		while (result.endsWith('-'))
			result = result.substr(0, result.length - 1);
		return result;
	}
}
