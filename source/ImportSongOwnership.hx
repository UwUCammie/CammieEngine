package;

import haxe.Json;
import haxe.crypto.Md5;
import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

private typedef ImportSongOwnerIdentityCache = {
	var index:Map<String, String>;
	var ambiguous:Map<String, Bool>;
	var ready:Bool;
}

/** A non-overwriting repair cannot change the donor which owns chart/audio.
 * Script provenance and chart provenance must move together. */
class ImportSongOwnership {
	static var baseSongKeys:Map<String, Bool> = null;
	static var baseSongRegistryValid:Bool = false;
	static var identityOverrides:Map<String, String> = null;
	static var sourceFingerprintHints:Map<String, String> = null;
	#if target.threaded
	static var ownerIdentityCacheTls:sys.thread.Tls<ImportSongOwnerIdentityCache> = new sys.thread.Tls();
	#else
	static var ownerIdentityCacheValue:ImportSongOwnerIdentityCache;
	#end
	static inline var MAX_OWNER_IDENTITY_RECORDS:Int = 8192;
	static inline var MAX_OWNER_IDENTITY_FILE_BYTES:Int = 131072;
	static inline var MAX_FINGERPRINT_CHARTS:Int = 2048;
	static inline var MAX_FINGERPRINT_CHART_BYTES:Int = 8388608;
	static inline var MAX_FINGERPRINT_TOTAL_BYTES:Int = 134217728;
	static inline var MAX_FINGERPRINT_AUDIO_ENTRIES:Int = 256;
	static inline var MAX_FINGERPRINT_PACKAGE_CHARTS:Int = 16384;
	static inline var MAX_FINGERPRINT_PACKAGE_BYTES:Int = 268435456;
	static inline var MAX_FINGERPRINT_PACKAGE_ENTRIES:Int = 32768;

	/** Package labels entered for this import are a user-confirmed fallback
	 * identity when the selected package has no authored ID. Keys use the same
	 * normalized-root form as the import prompt. */
	public static function setIdentityOverrides(overrides:Map<String, String>):Void {
		identityOverrides = new Map<String, String>();
		sourceFingerprintHints = new Map<String, String>();
		if (overrides == null)
			return;
		for (key in overrides.keys()) {
			var value = overrides.get(key);
			if (key != null && validIdentityLabel(value))
				identityOverrides.set(identityRootKey(key), StringTools.trim(value));
		}
	}

	public static function clearIdentityOverrides():Void {
		identityOverrides = null;
		sourceFingerprintHints = null;
	}

	/** Build a bounded, path-independent fingerprint for each selected source
	 * package from the charts already discovered for the import and the direct
	 * audio filename/size manifest. Chart bytes are hashed; large audio files are
	 * never read into memory. Any missing, out-of-root, or oversized input omits
	 * that root's fingerprint so labels alone cannot claim an existing owner. */
	public static function setSourceFingerprintHints(songs:Array<Dynamic>):Void {
		sourceFingerprintHints = new Map<String, String>();
		#if sys
		if (songs == null) return;
		var entries:Map<String, Array<String>> = new Map<String, Array<String>>();
		var invalid:Map<String, Bool> = new Map<String, Bool>();
		var chartCounts:Map<String, Int> = new Map<String, Int>();
		var chartBytes:Map<String, Float> = new Map<String, Float>();
		for (song in songs) {
			if (song == null || Reflect.field(song, 'sourceDuplicate') == true) continue;
			var rawRoot:Dynamic = Reflect.field(song, 'sourceRoot');
			if (rawRoot == null || StringTools.trim(Std.string(rawRoot)) == '') continue;
			var root = normalizeIdentityRoot(Std.string(rawRoot));
			var key = identityRootKey(root);
			if (key == '') continue;
			if (!entries.exists(key)) {
				entries.set(key, []);
				chartCounts.set(key, 0);
				chartBytes.set(key, 0.0);
			}
			var budget = fingerprintChartBudget(song);
			if (budget == null) {
				invalid.set(key, true);
				continue;
			}
			var nextCount = chartCounts.get(key) + budget.count;
			var nextBytes = chartBytes.get(key) + budget.bytes;
			if (nextCount > MAX_FINGERPRINT_PACKAGE_CHARTS
				|| nextBytes > MAX_FINGERPRINT_PACKAGE_BYTES) {
				invalid.set(key, true);
				continue;
			}
			chartCounts.set(key, nextCount);
			chartBytes.set(key, nextBytes);
			var item = fingerprintSong(root, song);
			if (item == null || item.length == 0) {
				invalid.set(key, true);
				continue;
			}
			if (entries.get(key).length + item.length > MAX_FINGERPRINT_PACKAGE_ENTRIES) {
				invalid.set(key, true);
				continue;
			}
			for (value in item) entries.get(key).push(value);
		}
		for (key in entries.keys()) {
			if (invalid.exists(key)) continue;
			var values = entries.get(key);
			if (values == null || values.length == 0) continue;
			values.sort(Reflect.compare);
			sourceFingerprintHints.set(key, Md5.encode(values.join('\n')));
		}
		#end
	}

	/** A destination-safe logical identity for a package. Authored IDs can stand
	 * alone; authored package names and explicit user labels require a matching
	 * source fingerprint before they recover an old owner. Directory-derived
	 * labels are deliberately excluded because roots are commonly renamed. */
	public static function stableIdentity(sourceRoot:String, engine:String):String {
		if (sourceRoot == null || StringTools.trim(sourceRoot) == ''
			|| engine == null || StringTools.trim(engine) == '')
			return '';
		var info = packageIdentityInfo(sourceRoot);
		var identityKind = info == null ? '' : info.kind;
		var identityValue = info == null ? '' : info.value;
		var overrideName = identityOverride(sourceRoot);
		if (overrideName != '' && (info == null
			|| (info.kind != 'id' && info.kind != 'package-name'))) {
			identityKind = 'user-name';
			identityValue = overrideName;
		}
		if (identityKind == '' || identityValue == '')
			return '';
		return StringTools.trim(engine).toLowerCase() + '|' + identityKind + '|'
			+ StringTools.trim(identityValue).toLowerCase();
	}

	/** Resolve a prior destination namespace for a moved package. Fresh imports
	 * keep the historical path-derived namespace. A metadata ID or matching
	 * package identity plus source fingerprint is required to reuse an owner. */
	public static function priorNamespace(sourceRoot:String, engine:String,
		legacyNamespace:String):String {
		var identity = stableIdentity(sourceRoot, engine);
		if (identity == '')
			return legacyNamespace;
		var cache = ownerIdentityCache();
		buildOwnerIdentityIndex(cache);
		if (!cache.ready)
			return legacyNamespace;
		var identityParts = identity.split('|');
		var usesStrongId = identityParts.length > 1 && identityParts[1] == 'id';
		var lookupKey = identity;
		if (!usesStrongId) {
			var fingerprint = sourceFingerprint(sourceRoot);
			if (fingerprint == '') return legacyNamespace;
			lookupKey += '|' + fingerprint;
		}
		if (cache.ambiguous.exists(lookupKey))
			return legacyNamespace;
		return cache.index.exists(lookupKey) ? cache.index.get(lookupKey) : legacyNamespace;
	}

	/** Each native worker and the main thread keep an independent installed-tree
	 * identity index. A worker's staged ImportFileSystem view must not replace
	 * the cache that menu/gameplay readers built against the live installation. */
	static function ownerIdentityCache():ImportSongOwnerIdentityCache {
		#if target.threaded
		var cache = ownerIdentityCacheTls.value;
		if (cache == null) {
			cache = {index:null, ambiguous:null, ready:false};
			ownerIdentityCacheTls.value = cache;
		}
		return cache;
		#else
		if (ownerIdentityCacheValue == null)
			ownerIdentityCacheValue = {index:null, ambiguous:null, ready:false};
		return ownerIdentityCacheValue;
		#end
	}

	/** A successful receipt write changes this thread's view. The import manager
	 * also calls this on the main thread after the runtime handoff commits. */
	public static function invalidateOwnerIdentityIndex():Void {
		var cache = ownerIdentityCache();
		cache.index = null;
		cache.ambiguous = null;
		cache.ready = false;
	}

	static function sourceFingerprint(sourceRoot:String):String {
		if (sourceFingerprintHints == null || sourceRoot == null) return '';
		var value = sourceFingerprintHints.get(identityRootKey(sourceRoot));
		return value == null ? '' : value;
	}

	static function fingerprintSong(sourceRoot:String, song:Dynamic):Null<Array<String>> {
		#if sys
		var chartPaths:Array<String> = [];
		var seenCharts:Map<String, Bool> = new Map<String, Bool>();
		var addChart = function(value:Dynamic):Bool {
			if (value == null || !Std.isOfType(value, String)) return true;
			var path = StringTools.trim(cast value);
			if (path == '') return true;
			var key = StringTools.replace(Path.normalize(path), '\\', '/');
			#if windows
			key = key.toLowerCase();
			#end
			if (seenCharts.exists(key)) return true;
			seenCharts.set(key, true);
			chartPaths.push(path);
			return chartPaths.length <= MAX_FINGERPRINT_CHARTS;
		};
		var rawDiffs:Dynamic = Reflect.field(song, 'diffFiles');
		if (Std.isOfType(rawDiffs, Array))
			for (path in (cast rawDiffs:Array<Dynamic>))
				if (!addChart(path)) return null;
		var rawConverted:Dynamic = Reflect.field(song, 'convertedCharts');
		if (Std.isOfType(rawConverted, Array))
			for (chart in (cast rawConverted:Array<Dynamic>))
				if (chart != null && !addChart(Reflect.field(chart, 'source'))) return null;
		if (chartPaths.length == 0) return null;
		var entries:Array<String> = [];
		var totalBytes = 0.0;
		for (chartPath in chartPaths) {
			var relative = sourceRelativePath(sourceRoot, chartPath);
			if (relative == '' || !FileSystem.exists(chartPath) || FileSystem.isDirectory(chartPath))
				return null;
			var size = FileSystem.stat(chartPath).size;
			if (size < 0 || size > MAX_FINGERPRINT_CHART_BYTES) return null;
			totalBytes += size;
			if (totalBytes > MAX_FINGERPRINT_TOTAL_BYTES) return null;
			entries.push('chart|' + relative + '|' + Md5.encode(File.getContent(chartPath)));
		}
		var sourceFolder:Dynamic = Reflect.field(song, 'sourceFolder');
		if (sourceFolder == null) sourceFolder = Reflect.field(song, 'name');
		var cleanSongFolder = cleanIdentityValue(sourceFolder == null ? '' : Std.string(sourceFolder));
		if (cleanSongFolder == '') return null;
		entries.push('song|' + cleanSongFolder.toLowerCase());
		var sourceInfo:Dynamic = Reflect.field(song, 'importSourceInfo');
		var audioRoot:Dynamic = sourceInfo == null ? null : Reflect.field(sourceInfo, 'song');
		if (audioRoot != null && Std.isOfType(audioRoot, String)
			&& FileSystem.isDirectory(cast audioRoot)) {
			var audioDirectory = cast audioRoot;
			if (sourceRelativePath(sourceRoot, audioDirectory) == '') return null;
			var audioFiles:Array<String>;
			try audioFiles = FileSystem.readDirectory(audioDirectory) catch (_:Dynamic) return null;
			if (audioFiles.length > MAX_FINGERPRINT_AUDIO_ENTRIES) return null;
			var audioManifest:Array<String> = [];
			for (name in audioFiles) {
				var path = Path.join([audioDirectory, name]);
				if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) continue;
				var extension = Path.extension(name).toLowerCase();
				if (['ogg', 'mp3', 'wav', 'flac', 'm4a', 'aac'].indexOf(extension) < 0) continue;
				var relative = sourceRelativePath(sourceRoot, path);
				if (relative == '') return null;
				audioManifest.push(relative + '|' + Std.string(FileSystem.stat(path).size));
			}
			audioManifest.sort(Reflect.compare);
			for (entry in audioManifest) entries.push('audio|' + entry);
		} else entries.push('audio|none');
		return entries;
		#end
		return null;
	}

	static function fingerprintChartBudget(song:Dynamic):Dynamic {
		#if sys
		var paths:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var add = function(value:Dynamic):Bool {
			if (value == null || !Std.isOfType(value, String)) return true;
			var path = StringTools.trim(cast value);
			if (path == '') return true;
			var key = StringTools.replace(Path.normalize(path), '\\', '/');
			#if windows
			key = key.toLowerCase();
			#end
			if (seen.exists(key)) return true;
			seen.set(key, true);
			paths.push(path);
			return paths.length <= MAX_FINGERPRINT_CHARTS;
		};
		var rawDiffs:Dynamic = Reflect.field(song, 'diffFiles');
		if (Std.isOfType(rawDiffs, Array))
			for (path in (cast rawDiffs:Array<Dynamic>)) if (!add(path)) return null;
		var rawConverted:Dynamic = Reflect.field(song, 'convertedCharts');
		if (Std.isOfType(rawConverted, Array))
			for (chart in (cast rawConverted:Array<Dynamic>))
				if (chart != null && !add(Reflect.field(chart, 'source'))) return null;
		if (paths.length == 0) return null;
		var bytes = 0.0;
		for (path in paths) {
			var relative = sourceRelativePath(Std.string(Reflect.field(song, 'sourceRoot')), path);
			if (relative == '' || !FileSystem.exists(path) || FileSystem.isDirectory(path)) return null;
			var size = FileSystem.stat(path).size;
			if (size < 0 || size > MAX_FINGERPRINT_CHART_BYTES) return null;
			bytes += size;
			if (bytes > MAX_FINGERPRINT_TOTAL_BYTES) return null;
		}
		return {count:paths.length, bytes:bytes};
		#end
		return null;
	}

	static function sourceRelativePath(sourceRoot:String, sourcePath:String):String {
		#if sys
		try {
			var root = normalizeIdentityRoot(FileSystem.fullPath(sourceRoot));
			var path = normalizeIdentityRoot(FileSystem.fullPath(sourcePath));
			var prefix = StringTools.endsWith(root, '/') ? root : root + '/';
			var comparisonRoot = prefix;
			var comparisonPath = path;
			#if windows
			comparisonRoot = comparisonRoot.toLowerCase();
			comparisonPath = comparisonPath.toLowerCase();
			#end
			if (!StringTools.startsWith(comparisonPath, comparisonRoot)) return '';
			return path.substr(prefix.length);
		} catch (_:Dynamic) {}
		#end
		return '';
	}

	static function identityRootKey(sourceRoot:String):String {
		var normalized = normalizeIdentityRoot(sourceRoot);
		#if windows
		return normalized.toLowerCase();
	#else
		return normalized;
	#end
	}

	static function identityOverride(sourceRoot:String):String {
		if (identityOverrides == null || sourceRoot == null)
			return '';
		var normalized = normalizeIdentityRoot(sourceRoot);
		#if windows
		normalized = normalized.toLowerCase();
		#end
		var value = identityOverrides.get(normalized);
		return value == null ? '' : StringTools.trim(value);
	}

	static function normalizeIdentityRoot(sourceRoot:String):String {
		var normalized = StringTools.replace(StringTools.trim(sourceRoot == null ? '' : sourceRoot), '\\', '/');
		if (normalized == '') return '';
		var unc = StringTools.startsWith(normalized, '//');
		normalized = Path.normalize(normalized);
		if (unc && !StringTools.startsWith(normalized, '//')) {
			while (StringTools.startsWith(normalized, '/')) normalized = normalized.substr(1);
			normalized = normalized == '' ? '//' : '//' + normalized;
		}
		while (normalized.length > 1 && StringTools.endsWith(normalized, '/')) {
			if (normalized == '/' || normalized == '//'
				|| (normalized.length == 3 && normalized.charAt(1) == ':')) break;
			normalized = normalized.substr(0, normalized.length - 1);
		}
		return normalized;
	}

	static function validIdentityLabel(value:String):Bool {
		if (value == null) return false;
		var name = StringTools.trim(value);
		if (name == '' || name.length > 80) return false;
		for (index in 0...name.length) {
			var code = name.charCodeAt(index);
			if (code == null || code < 32 || code == 127) return false;
		}
		return true;
	}

	static function packageIdentityInfo(sourceRoot:String):Dynamic {
		#if sys
		var roots:Array<String> = [sourceRoot];
		var mods = Path.join([sourceRoot, 'mods']);
		if (FileSystem.isDirectory(mods)) {
			var children:Array<String> = [];
			try {
				for (entry in FileSystem.readDirectory(mods))
					if (FileSystem.isDirectory(Path.join([mods, entry]))) children.push(entry);
			} catch (_:Dynamic) {}
			if (children.length == 1)
				roots.unshift(Path.join([mods, children[0]]));
		}
		for (root in roots) {
			for (file in ['_polymod_meta.json', 'pack.json', 'mod.json', 'metadata.json']) {
				var path = Path.join([root, file]);
				if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) continue;
				try {
					if (FileSystem.stat(path).size > MAX_OWNER_IDENTITY_FILE_BYTES) continue;
					var data:Dynamic = Json.parse(File.getContent(path));
					for (field in ['id', 'modId', 'modID', 'uuid', 'packageId', 'packageID']) {
						var raw:Dynamic = Reflect.field(data, field);
						if (raw != null && Std.isOfType(raw, String)) {
							var value = cleanIdentityValue(cast raw);
							if (value != '') return {kind:'id', value:value, label:metadataLabel(data, value)};
						}
					}
					for (field in ['title', 'name', 'displayName']) {
						var raw:Dynamic = Reflect.field(data, field);
						if (raw != null && Std.isOfType(raw, String)) {
							var value = cleanIdentityValue(cast raw);
							if (value != '') return {kind:'package-name', value:value, label:value};
						}
					}
				} catch (_:Dynamic) {}
			}
		}
		// Compiled Codename releases often contain one actual mod under mods/;
		// this authored inner directory remains stable when the outer archive is
		// renamed, unlike the selected extraction root.
		if (FileSystem.isDirectory(mods)) try {
			var children:Array<String> = [];
			for (entry in FileSystem.readDirectory(mods))
				if (FileSystem.isDirectory(Path.join([mods, entry]))) children.push(entry);
			if (children.length == 1) {
				var value = cleanIdentityValue(children[0]);
				if (value != '') return {kind:'inner-package-name', value:value, label:value};
			}
		} catch (_:Dynamic) {}
		// Some standalone source packages identify themselves only through their
		// HaxeFlixel project title. `displayNameInfo` marks this authored value and
		// the import prompt relies on it, so use the same title for owner recovery.
		var display = displayNameInfo(sourceRoot);
		if (display != null && display.authored) {
			var value = cleanIdentityValue(display.name);
			if (value != '') return {kind:'package-title', value:value, label:value};
		}
		#end
		return null;
	}

	static function metadataLabel(data:Dynamic, fallback:String):String {
		for (field in ['title', 'name', 'displayName']) {
			var raw:Dynamic = Reflect.field(data, field);
			if (raw != null && Std.isOfType(raw, String)) {
				var value = cleanIdentityValue(cast raw);
				if (value != '') return value;
			}
		}
		return fallback;
	}

	/** Psych's starter pack.json is copied with these literal template values.
	 * Treat the pair as missing package metadata, while still allowing a real
	 * package whose authored title happens to be "Name". */
	static function isGenericPackageTemplateMetadata(data:Dynamic):Bool {
		if (data == null || Std.isOfType(data, Array) || Std.isOfType(data, String)
			|| Std.isOfType(data, Bool) || Std.isOfType(data, Int) || Std.isOfType(data, Float))
			return false;
		var displayName = '';
		for (field in ['title', 'name', 'displayName']) {
			var raw:Dynamic = Reflect.field(data, field);
			if (raw != null && Std.isOfType(raw, String)) {
				displayName = StringTools.trim(cast raw);
				if (displayName != '')
					break;
			}
		}
		var rawDescription:Dynamic = Reflect.field(data, 'description');
		var description = rawDescription != null && Std.isOfType(rawDescription, String)
			? StringTools.trim(cast rawDescription) : '';
		return displayName.toLowerCase() == 'name' && description.toLowerCase() == 'description';
	}

	static function cleanIdentityValue(value:String):String {
		if (value == null) return '';
		var clean = StringTools.trim(value);
		if (clean == '' || clean.length > 256 || clean.toLowerCase() == 'null') return '';
		for (index in 0...clean.length) {
			var code = clean.charCodeAt(index);
			if (code == null || code < 32 || code == 127) return '';
		}
		return clean;
	}

	static function buildOwnerIdentityIndex(cache:ImportSongOwnerIdentityCache):Void {
		if (cache.ready) return;
		cache.index = new Map<String, String>();
		cache.ambiguous = new Map<String, Bool>();
		#if sys
		var dataRoot = 'assets/data';
		if (!FileSystem.isDirectory(dataRoot)) return;
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(dataRoot) catch (_:Dynamic) return;
		if (entries.length > MAX_OWNER_IDENTITY_RECORDS) return;
		for (entry in entries) {
			var directory = Path.join([dataRoot, entry]);
			if (!FileSystem.isDirectory(directory)) continue;
			var path = Path.join([directory, 'importProvenance.json']);
			if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) continue;
			try {
				if (FileSystem.stat(path).size > MAX_OWNER_IDENTITY_FILE_BYTES) continue;
				var record:Dynamic = Json.parse(File.getContent(path));
				if (Reflect.field(record, 'version') != 1
					|| Reflect.field(record, 'destinationFolder') != Path.withoutDirectory(directory)) continue;
				var rawEngine:Dynamic = Reflect.field(record, 'sourceEngine');
				var rawOwner:Dynamic = Reflect.field(record, 'sourceOwner');
				if (rawEngine == null || rawOwner == null) continue;
				var engine = StringTools.trim(Std.string(rawEngine)).toLowerCase();
				var owner = validOwnerNamespace(Std.string(rawOwner));
				if (engine == '' || owner == '') continue;
				var rawIdentity:Dynamic = Reflect.field(record, 'sourceIdentity');
				if (rawIdentity == null || !Std.isOfType(rawIdentity, String)) continue;
				var identity = StringTools.trim(cast rawIdentity);
				var identityParts = identity.split('|');
				if (identity == '' || identityParts.length < 3
					|| identityParts[0].toLowerCase() != engine) continue;
				var lookupKey = identity;
				if (identityParts[1] != 'id') {
					var rawFingerprint:Dynamic = Reflect.field(record, 'sourceFingerprint');
					if (rawFingerprint == null || !Std.isOfType(rawFingerprint, String)
						|| StringTools.trim(cast rawFingerprint) == '') continue;
					lookupKey += '|' + StringTools.trim(cast rawFingerprint);
				}
				addOwnerIdentity(cache.index, cache.ambiguous, lookupKey, owner);
			} catch (_:Dynamic) {}
		}
		#end
		cache.ready = true;
	}

	static function addOwnerIdentity(index:Map<String, String>, ambiguous:Map<String, Bool>,
		key:String, namespace:String):Void {
		if (key == null || key == '' || namespace == '') return;
		if (index.exists(key) && index.get(key) != namespace) {
			index.remove(key);
			ambiguous.set(key, true);
		} else if (!ambiguous.exists(key)) index.set(key, namespace);
	}

	static function validOwnerNamespace(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		var prefix = CompatScriptManifest.ROOT_PREFIX + '/';
		if (!StringTools.startsWith(clean, prefix)) return '';
		var namespace = clean.substr(prefix.length);
		if (namespace == '' || namespace.indexOf('/') >= 0 || namespace == '.' || namespace == '..')
			return '';
		return namespace;
	}
	/** Stable alternative destination for two donor roots that use the same
	 * native song key.  The engine slug is readable; the namespace digest keeps
	 * two donors from one engine distinct without persisting an absolute path. */
	public static function ownerQualifiedFolder(folder:String, sourceRoot:String, engine:String):String {
		if (folder == null || StringTools.trim(folder) == '' || sourceRoot == null
			|| StringTools.trim(sourceRoot) == '' || engine == null || StringTools.trim(engine) == '')
			return '';
		var namespace = CompatScriptManifest.namespaceFor(sourceRoot, engine);
		var split = namespace.lastIndexOf('-');
		var digest = split < 0 ? namespace : namespace.substr(split + 1);
		var label = slug(engine);
		return StringTools.trim(folder) + '--' + label + '-' + digest;
	}

	/** Human-readable collision label used beside the owner-qualified Freeplay
	 * display name. */
	public static function ownerDisplayLabel(sourceRoot:String, engine:String):String {
		return displayWithEngine(modDisplayName(sourceRoot), engine);
	}

	public static function displayWithEngine(name:String, engine:String):String {
		var displayName = name == null ? '' : StringTools.trim(name);
		var engineName = engine == null ? '' : StringTools.trim(engine);
		if (displayName == '') return engineName;
		if (engineName == '')
			return displayName;
		var suffixAt = displayName.length - engineName.length;
		if (suffixAt >= 0 && displayName.substr(suffixAt).toLowerCase() == engineName.toLowerCase()
			&& (suffixAt == 0 || ' :·-'.indexOf(displayName.charAt(suffixAt - 1)) >= 0))
			return displayName;
		return displayName + ' · ' + engineName;
	}

	/** Read package-authored metadata when present. Compiled Codename releases
	 * often put one actual mod in mods/ while the archive's outer name varies. */
	public static function modDisplayName(sourceRoot:String):String {
		return displayNameInfo(sourceRoot).name;
	}

	/** `authored` is false when the only available label is a directory name.
	 * Interactive importers can ask the user in that case. */
	public static function displayNameInfo(sourceRoot:String):{name:String, authored:Bool, template:Bool} {
		if (sourceRoot == null || StringTools.trim(sourceRoot) == '')
			return {name:'', authored:false, template:false};
		var skippedTemplateMetadata = false;
		#if sys
		var roots = [sourceRoot];
		var innerMod:String = null;
		var mods = Path.join([sourceRoot, 'mods']);
		if (FileSystem.isDirectory(mods)) {
			roots.unshift(mods);
			var children:Array<String> = [];
			try {
				for (entry in FileSystem.readDirectory(mods))
					if (FileSystem.isDirectory(Path.join([mods, entry]))) children.push(entry);
			} catch (_:Dynamic) {}
			if (children.length == 1) {
				innerMod = children[0];
				roots.unshift(Path.join([mods, innerMod]));
			}
		}
		for (root in roots) {
			for (file in ['_polymod_meta.json', 'pack.json', 'mod.json']) {
				var path = Path.join([root, file]);
				if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) continue;
				try {
					if (FileSystem.stat(path).size > 131072) continue;
					var data:Dynamic = Json.parse(File.getContent(path));
					if (isGenericPackageTemplateMetadata(data)) {
						skippedTemplateMetadata = true;
						continue;
					}
					for (field in ['title', 'name', 'displayName']) {
						var raw:Dynamic = Reflect.field(data, field);
						if (raw != null && Std.isOfType(raw, String)) {
							var name = StringTools.trim(cast raw);
							if (name != '' && name.toLowerCase() != 'null')
								return {name:name, authored:true, template:false};
						}
					}
				} catch (_:Dynamic) {}
			}
		}
		// A standalone HaxeFlixel source package can author its display title in
		// Project.xml. Keep an inner mod's own metadata/folder identity ahead of
		// the host engine project's title.
		if (innerMod == null) {
			var projectFile = Path.join([sourceRoot, 'Project.xml']);
			if (FileSystem.exists(projectFile) && !FileSystem.isDirectory(projectFile)) try {
				if (FileSystem.stat(projectFile).size <= 131072) {
					var project = Xml.parse(File.getContent(projectFile)).firstElement();
					if (project != null && project.nodeName == 'project')
						for (app in project.elementsNamed('app')) {
							var rawTitle = app.get('title');
							var title = rawTitle == null ? '' : StringTools.trim(rawTitle);
							if (title != '' && title.toLowerCase() != 'null'
								&& title.indexOf('$') < 0)
								return {name:title, authored:true, template:false};
						}
				}
			} catch (_:Dynamic) {}
		}
		if (innerMod != null) return {name:innerMod, authored:false, template:skippedTemplateMetadata};
		#end
		var fallbackRoot = sourceRoot;
		if (skippedTemplateMetadata
			&& Path.withoutDirectory(Path.normalize(sourceRoot)).toLowerCase() == 'mods') {
			var parentRoot = Path.directory(Path.normalize(sourceRoot));
			if (parentRoot != null && StringTools.trim(parentRoot) != '' && parentRoot != '.')
				fallbackRoot = parentRoot;
		}
		return {name:Path.withoutDirectory(Path.normalize(fallbackRoot)), authored:false,
			template:skippedTemplateMetadata};
	}

	/** Destination-only import provenance for a selected source owner. */
	public static function provenance(sourceFolder:String, sourceRoot:String, engine:String,
		destinationFolder:String, display:String, ?modName:String, ?nameSource:String):Dynamic {
		var result:Dynamic = {
			version: 1,
			sourceFolder: sourceFolder == null ? '' : sourceFolder,
			sourceEngine: engine == null ? '' : engine,
			sourceOwner: sourceRoot == null || StringTools.trim(sourceRoot) == '' ? ''
				: CompatScriptManifest.destinationRoot(sourceRoot, engine),
			destinationFolder: destinationFolder == null ? '' : destinationFolder,
			display: display == null ? '' : display
		};
		// Source script API label; separate from stable ownership and display names.
		if (sourceRoot != null && StringTools.trim(sourceRoot) != '')
			Reflect.setField(result, 'sourceModDirectory', Path.withoutDirectory(normalizeIdentityRoot(sourceRoot)));
		#if sys
		var context = ImportIO.current();
		if (context != null) {
			var label = context.sourceLabel(sourceRoot);
			if (label != null && label != '') Reflect.setField(result, 'sourceModDirectory', label);
		}
		#end
		var identity = stableIdentity(sourceRoot, engine);
		if (identity != '')
			Reflect.setField(result, 'sourceIdentity', identity);
		var fingerprint = sourceFingerprint(sourceRoot);
		if (fingerprint != '')
			Reflect.setField(result, 'sourceFingerprint', fingerprint);
		if (modName != null && StringTools.trim(modName) != '')
			Reflect.setField(result, 'modName', StringTools.trim(modName));
		if (nameSource != null && StringTools.trim(nameSource) != '')
			Reflect.setField(result, 'nameSource', StringTools.trim(nameSource));
		return result;
	}

	/** Update only the package subtitle fields on a receipt for this exact owner.
	 * Ownership, source identity/fingerprint, song display, and extension fields
	 * stay intact. A previously user-entered package label remains authoritative
	 * unless the importer received another explicit user override. */
	public static function refreshDisplayMetadata(record:Dynamic, engine:String, sourceOwner:String,
		destinationFolder:String, modName:String, nameSource:String):Bool {
		if (record == null || Std.isOfType(record, Array) || Std.isOfType(record, String)
			|| Std.isOfType(record, Bool) || Std.isOfType(record, Int) || Std.isOfType(record, Float)
			|| engine == null || StringTools.trim(engine) == ''
			|| destinationFolder == null || StringTools.trim(destinationFolder) == '')
			return false;
		if (Reflect.field(record, 'version') != 1
			|| Reflect.field(record, 'destinationFolder') != destinationFolder)
			return false;
		var rawEngine:Dynamic = Reflect.field(record, 'sourceEngine');
		var rawOwner:Dynamic = Reflect.field(record, 'sourceOwner');
		if (rawEngine == null || !Std.isOfType(rawEngine, String)
			|| StringTools.trim(cast rawEngine).toLowerCase() != StringTools.trim(engine).toLowerCase()
			|| rawOwner == null || !Std.isOfType(rawOwner, String)
			|| validOwnerNamespace(sourceOwner) == '' || validOwnerNamespace(cast rawOwner) == ''
			|| CompatScriptManifest.destinationKey(cast rawOwner)
				!= CompatScriptManifest.destinationKey(sourceOwner))
			return false;
		var cleanName = cleanIdentityValue(modName);
		var cleanSource = nameSource == null ? '' : StringTools.trim(nameSource).toLowerCase();
		if (cleanName == '' || (cleanSource != 'user' && cleanSource != 'metadata' && cleanSource != 'inferred'))
			return false;
		var oldSource:Dynamic = Reflect.field(record, 'nameSource');
		if (oldSource != null && Std.isOfType(oldSource, String)
			&& StringTools.trim(cast oldSource).toLowerCase() == 'user' && cleanSource != 'user')
			return false;
		var oldName:Dynamic = Reflect.field(record, 'modName');
		if (oldName != null && Std.isOfType(oldName, String)
			&& StringTools.trim(cast oldName) == cleanName
			&& oldSource != null && Std.isOfType(oldSource, String)
			&& StringTools.trim(cast oldSource).toLowerCase() == cleanSource)
			return false;
		Reflect.setField(record, 'modName', cleanName);
		Reflect.setField(record, 'nameSource', cleanSource);
		return true;
	}

	/** Plan a destination when the canonical chart folder is already owned by
	 * another selected donor.  The returned error is only populated when the
	 * existing collision cannot be moved to this donor's stable key. */
	public static function planDestination(existingFolder:String, folder:String,
		sourceRoot:String, engine:String):Dynamic {
		var ownershipError = conflict(existingFolder, sourceRoot, engine);
		if (ownershipError == null)
			return {folder:folder, qualified:false, error:null};
		// Older imports may retain several script roots in one chart folder. If
		// the selected root is this exact source, we can repair its owned visuals
		// without touching the mixed-owner chart, audio, or menu registration.
		// A second owner-qualified chart here would duplicate an existing song.
		if (selectedVisualOnlyOwner(existingFolder, sourceRoot, engine))
			return {folder:folder, qualified:false, error:null, visualOnly:true};

		var qualified = ownerQualifiedFolder(folder, sourceRoot, engine);
		if (qualified == '')
			return {folder:folder, qualified:false, error:ownershipError};
		var parent = Path.directory(existingFolder);
		var qualifiedPath = parent == null || StringTools.trim(parent) == ''
			? qualified : Path.join([parent, qualified]);
		var qualifiedError = conflict(qualifiedPath, sourceRoot, engine);
		if (qualifiedError != null)
			return {folder:qualified, qualified:true, error:qualifiedError};
		return {folder:qualified, qualified:true, error:null};
	}

	static function selectedVisualOnlyOwner(folder:String, sourceRoot:String,
		engine:String):Bool {
		#if sys
		if (folder == null || sourceRoot == null || engine == null
			|| StringTools.trim(sourceRoot) == '' || StringTools.trim(engine) == '') return false;
		var normalized = StringTools.replace(Path.normalize(folder), '\\', '/');
		var parent = Path.directory(normalized);
		if (parent != 'assets/data' && !StringTools.endsWith(parent, '/assets/data')) return false;
		if (isBaseSong(Path.withoutDirectory(normalized))) return false;
		if (!FileSystem.exists(normalized) || !FileSystem.isDirectory(normalized)) return false;
		var path = Path.join([normalized, CompatScriptManifest.FILE_NAME]);
		if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) return false;
		try {
			if (FileSystem.stat(path).size > MAX_OWNER_IDENTITY_FILE_BYTES) return false;
			var manifest = CompatScriptManifest.parse(File.getContent(path));
			if (manifest == null || manifest.roots == null
				|| manifest.roots.filter(function(root) return root.dependency != true).length < 2) return false;
			var desired = CompatScriptManifest.destinationKey(
				CompatScriptManifest.destinationRoot(sourceRoot, engine));
			var selected = CompatScriptManifest.destinationKey(
				CompatScriptManifest.selectedRoot(manifest));
			if (desired == '' || selected != desired) return false;
			for (root in manifest.roots)
				if (root != null && CompatScriptManifest.destinationKey(root.path) == desired
					&& root.engine != null && root.engine.toLowerCase() == engine.toLowerCase())
					return true;
		} catch (_:Dynamic) {}
		#end
		return false;
	}

	public static function conflict(folder:String, sourceRoot:String, engine:String):Null<String> {
		#if sys
		if (folder == null || StringTools.trim(folder) == '')
			return 'Missing destination folder; preserving existing files.';
		var normalized = StringTools.replace(Path.normalize(folder), '\\', '/');
		var parent = Path.directory(normalized);
		var dataFolder = parent == 'assets/data' || StringTools.endsWith(parent, '/assets/data');
		if (dataFolder) {
			isBaseSong(Path.withoutDirectory(normalized));
			if (!baseSongRegistryValid)
				return 'Base song ownership registry is missing or invalid; import cannot safely write charts.';
		}
		if (dataFolder && isBaseSong(Path.withoutDirectory(normalized)))
			return 'Destination ' + folder + ' is an engine-owned base song.';
		var context = ImportIO.current();
		if (context != null && context.hasOwnedPath(normalized)) {
			// Masked charts regenerate into staging, but their installed ownership
			// still decides which source may reuse the destination key.
			var installed = haxe.io.Path.join([Sys.getCwd(), normalized, CompatScriptManifest.FILE_NAME]);
			if (sys.FileSystem.exists(installed)) try {
				var old = CompatScriptManifest.parse(sys.io.File.getContent(installed));
				var desired = CompatScriptManifest.destinationRoot(sourceRoot, engine);
				if (old.roots.length > 0 && CompatScriptManifest.selectedRoot(old) == desired
					&& old.roots.filter(function(root) return root.dependency != true && root.path != desired).length == 0) return null;
			} catch (_:Dynamic) {}
		}
		if (!FileSystem.exists(folder)) return null;
		if (sourceRoot == null || StringTools.trim(sourceRoot) == '')
			return 'Destination ' + folder + ' exists but the source owner is unknown.';
		var path = Path.join([folder, CompatScriptManifest.FILE_NAME]);
		if (!FileSystem.exists(path)) {
			// The chart writer records provenance before the asset merger writes its
			// script manifest. Accept only that same-owner intermediate state so an
			// interrupted import can finish without claiming an unrelated folder.
			var provenancePath = Path.join([folder, 'importProvenance.json']);
			if (FileSystem.exists(provenancePath) && !FileSystem.isDirectory(provenancePath)) try {
				if (FileSystem.stat(provenancePath).size <= 131072) {
					var record:Dynamic = Json.parse(File.getContent(provenancePath));
					var desiredRoot = CompatScriptManifest.destinationRoot(sourceRoot, engine);
					if (Reflect.field(record, 'version') == 1
						&& Reflect.field(record, 'sourceEngine') == engine
						&& Reflect.field(record, 'destinationFolder') == Path.withoutDirectory(normalized)
						&& Std.isOfType(Reflect.field(record, 'sourceOwner'), String)
						&& CompatScriptManifest.destinationKey(Reflect.field(record, 'sourceOwner'))
							== CompatScriptManifest.destinationKey(desiredRoot)) return null;
				}
			} catch (_:Dynamic) {}
			return 'Destination ' + folder + ' has no import ownership record; preserving its existing files.';
		}
		var manifest;
		try manifest = CompatScriptManifest.parse(File.getContent(path))
		catch (_:Dynamic)
			return 'Destination ' + folder + ' has an unreadable import ownership record.';
		if (manifest.roots.length == 0)
			return 'Destination ' + folder + ' has no valid import owner; preserving its existing files.';
		var desired = CompatScriptManifest.destinationKey(CompatScriptManifest.destinationRoot(sourceRoot, engine));
		if (CompatScriptManifest.destinationKey(CompatScriptManifest.selectedRoot(manifest)) != desired)
			return 'Destination ' + folder + ' belongs to another selected import; preserving its existing files.';
		for (root in manifest.roots)
			if (root.dependency != true && CompatScriptManifest.destinationKey(root.path) != desired)
				return 'Destination ' + folder + ' belongs to another import (' + root.engine
					+ '). Back up and reset that imported song before replacing its donor; charts, audio and scripts cannot be merged.';
		#end
		return null;
	}

	static function isBaseSong(folder:String):Bool {
		#if sys
		if (baseSongKeys == null) {
			baseSongKeys = new Map<String, Bool>();
			var path = 'assets/data/baseSongKeys.json';
			if (FileSystem.exists(path)) try {
				var keys:Dynamic = Json.parse(File.getContent(path));
				if (Std.isOfType(keys, Array)) {
					baseSongRegistryValid = true;
					for (key in (cast keys:Array<Dynamic>))
						if (key != null) baseSongKeys.set(Std.string(key).toLowerCase(), true);
				}
			} catch (_:Dynamic) {}
		}
		return baseSongKeys.exists(folder.toLowerCase());
		#end
		return false;
	}

	static function slug(value:String):String {
		var output:Array<String> = [];
		var previousDash = false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			var lower = value.charAt(index).toLowerCase();
			var valid = (lower >= 'a' && lower <= 'z') || (lower >= '0' && lower <= '9');
			if (valid) {
				output.push(lower);
				previousDash = false;
			} else if (output.length > 0 && !previousDash) {
				output.push('-');
				previousDash = true;
			}
		}
		while (output.length > 0 && output[output.length - 1] == '-') output.pop();
		return output.length == 0 ? 'import' : output.join('');
	}
}
