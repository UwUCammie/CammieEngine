package;

import haxe.Json;
import haxe.io.Path;
#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end

using StringTools;

/** Result from importing one chart-free Psych global pack. */
typedef PsychGlobalPackImportResult = {
	var eligible:Bool;
	var imported:Bool;
	var ownerRoot:String;
	var copied:Int;
	var skipped:Int;
	var failed:Int;
	var errors:Array<String>;
}

/**
	Imports Psych-family packs which declare `runsGlobally: true` and contain no
	Psych chart envelopes.  Imported files retain their donor-relative layout
	inside the same stable owner namespace used by song imports.  The only shared
	state this class writes is its global-results selection registry; user options
	remain outside the import path.
*/
class PsychGlobalPackImporter {
	public static inline var RECEIPT_NAME:String = 'psychGlobalPackImport.json';
	public static inline var PROVIDER_CONFIG:String = 'assets/imported_mods/globalResultsProvider.json';
	public static inline var BUNDLED_PROVIDER_ROOT:String = 'assets/imported_mods/bundled-vslice-results';
	static inline var RECEIPT_VERSION:Int = 1;
	static inline var PROVIDER_CONFIG_VERSION:Int = 1;
	static inline var MAX_DEPTH:Int = 12;
	static inline var MAX_DIRECTORIES:Int = 8192;
	static inline var MAX_ENTRIES:Int = 50000;
	static inline var MAX_CHART_PROBES:Int = 2048;
	static inline var MAX_CHART_BYTES:Int = 4 * 1024 * 1024;

	static var scopedTreeNames:Array<String> = [
		'scripts', 'images', 'sounds', 'videos', 'fonts', 'shaders', 'animations', 'music'
	];

	/** Return whether the source satisfies the generic global-pack contract. */
	public static function isEligible(sourceRoot:String, ?contentRoot:String):Bool {
		var source = canonicalDirectory(sourceRoot);
		var content = canonicalDirectory(contentRoot == null || StringTools.trim(contentRoot) == ''
			? sourceRoot : contentRoot);
		if (source == '' || content == '' || !pathWithin(content, source))
			return false;
		var roots = logicalRoots(source, content);
		var packPath = findPackPath(source, content);
		if (packPath == null || !packRunsGlobally(packPath))
			return false;
		return !containsPsychSongCharts(roots, source);
	}

	/**
		Copy the supported scripts, media, pack manifest and settings into the
		stable Psych owner.  Repeated imports repair absent files and preserve all
		existing owner files.  A provider is selected only when no valid selection
		already exists.
	*/
	public static function importPack(sourceRoot:String, ?contentRoot:String):PsychGlobalPackImportResult {
		var result:PsychGlobalPackImportResult = {
			eligible:false, imported:false, ownerRoot:'', copied:0, skipped:0, failed:0, errors:[]
		};
		var source = canonicalDirectory(sourceRoot);
		var content = canonicalDirectory(contentRoot == null || StringTools.trim(contentRoot) == ''
			? sourceRoot : contentRoot);
		if (source == '' || content == '' || !pathWithin(content, source)) {
			result.failed++;
			result.errors.push('[psych-global-pack-reject] Content root is outside the selected source root.');
			return result;
		}
		var roots = logicalRoots(source, content);
		var packPath = findPackPath(source, content);
		if (packPath == null || !packRunsGlobally(packPath)) {
			result.errors.push('[psych-global-pack-skip] The selected root has no valid pack.json with runsGlobally:true.');
			return result;
		}
		if (containsPsychSongCharts(roots, source)) {
			result.errors.push('[psych-global-pack-skip] The selected root contains Psych song charts.');
			return result;
		}
		result.eligible = true;

		var owner = CompatScriptManifest.destinationRoot(source, ImportEngine.PSYCH);
		if (!validOwnerPath(owner)) {
			result.failed++;
			result.errors.push('[psych-global-pack-reject] Stable owner path is outside the imported-mod namespace.');
			return result;
		}
		result.ownerRoot = owner;
		var seenDirectories:Map<String, Bool> = new Map<String, Bool>();
		var counters = {directories:0, entries:0};
		for (root in roots) {
			if (root.prefix == '')
				copyScopedRoot(root.path, '', source, owner, seenDirectories, counters, result);
			else
				copyScopedRoot(root.path, root.prefix, source, owner, seenDirectories, counters, result);
		}
		copyPackMetadata(packPath, owner, source, result);
		if (result.failed > 0)
			return result;

		var installedPack = Path.join([owner, 'pack.json']);
		if (!FileSystem.exists(installedPack) || !packRunsGlobally(installedPack)) {
			result.failed++;
			result.errors.push('[psych-global-pack-reject] The owner copy does not contain a valid global pack.json.');
			return result;
		}
		if (!writeReceipt(owner, installedPack, result))
			return result;
		result.imported = true;
		if (selectedImportedProvider() == null && !selectDefaultProvider(owner)) {
			result.failed++;
			result.errors.push('[psych-global-pack-skip] The pack was imported, but its default-provider config could not be written.');
		}
		return result;
	}

	/** Resolve the selected imported provider, or the packaged default. */
	public static function defaultProvider():Null<String> {
		#if sys
		var selected = selectedImportedProvider();
		return selected != null ? selected : (isBundledGlobalPack() ? BUNDLED_PROVIDER_ROOT : null);
		#else
		return null;
		#end
	}

	static function selectedImportedProvider():Null<String> {
		#if sys
		if (FileSystem.exists(PROVIDER_CONFIG)) {
			try {
				var data:Dynamic = Json.parse(File.getContent(PROVIDER_CONFIG));
				if (data != null && Std.int(Reflect.field(data, 'version')) == PROVIDER_CONFIG_VERSION) {
					var owner = safeOwnerPath(Reflect.field(data, 'defaultOwner'));
					if (owner != null && isImportedGlobalPack(owner))
						return owner;
				}
			} catch (_:Dynamic) {}
		}
		return null;
		#else
		return null;
		#end
	}

	/** Select an imported global pack as the default results provider. */
	public static function selectDefaultProvider(ownerRoot:String):Bool {
		#if sys
		var owner = safeOwnerPath(ownerRoot);
		if (owner == null || !isImportedGlobalPack(owner))
			return false;
		try {
			ensureDirectory(Path.directory(PROVIDER_CONFIG));
			File.saveContent(PROVIDER_CONFIG, Json.stringify({
				version:PROVIDER_CONFIG_VERSION,
				defaultOwner:owner
			}));
			return true;
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}

	/** Stable owner path used by both this helper and Psych song imports. */
	public static function ownerForSource(sourceRoot:String):String {
		var source = canonicalDirectory(sourceRoot);
		return source == '' ? '' : CompatScriptManifest.destinationRoot(source, ImportEngine.PSYCH);
	}

	static function copyScopedRoot(root:String, destinationPrefix:String, sourceRoot:String,
		ownerRoot:String, seenDirectories:Map<String, Bool>, counters:{directories:Int, entries:Int},
		result:PsychGlobalPackImportResult):Void {
		if (!pathWithin(root, sourceRoot)) {
			fail(result, '[psych-global-pack-reject] Source root escaped the selected pack: ' + root);
			return;
		}
		for (name in scopedTreeNames) {
			var sourceTree = existingChild(root, name);
			if (sourceTree != null && FileSystem.isDirectory(sourceTree)) {
				var actualName = Path.withoutDirectory(sourceTree);
				var relative = destinationPrefix == '' ? actualName : destinationPrefix + '/' + actualName;
				copyTree(sourceTree, Path.join([ownerRoot, relative]), sourceRoot, ownerRoot,
					0, seenDirectories, counters, result);
			}
		}
		var shared = existingChild(root, 'shared');
		if (shared != null && FileSystem.isDirectory(shared)) {
			if (!pathWithin(shared, sourceRoot)) {
				fail(result, '[psych-global-pack-reject] Shared source escaped the selected pack: ' + shared);
				return;
			}
			for (name in scopedTreeNames) {
				var sourceTree = existingChild(shared, name);
				if (sourceTree == null || !FileSystem.isDirectory(sourceTree))
					continue;
				var actualName = Path.withoutDirectory(sourceTree);
				var relative = destinationPrefix == '' ? 'shared/' + actualName
					: destinationPrefix + '/shared/' + actualName;
				copyTree(sourceTree, Path.join([ownerRoot, relative]), sourceRoot, ownerRoot,
					0, seenDirectories, counters, result);
			}
		}
		var dataRoot = existingChild(root, 'data');
		var settings = dataRoot == null ? null : existingChild(dataRoot, 'settings.json');
		if (settings != null && !FileSystem.isDirectory(settings)) {
			copyFile(settings, Path.join([ownerRoot, 'data', 'settings.json']), sourceRoot, ownerRoot, result);
		}
	}

	static function copyTree(source:String, destination:String, sourceRoot:String, ownerRoot:String,
		depth:Int, seenDirectories:Map<String, Bool>, counters:{directories:Int, entries:Int},
		result:PsychGlobalPackImportResult):Void {
		if (depth > MAX_DEPTH) {
			fail(result, '[psych-global-pack-skip] Directory depth limit reached: ' + source);
			return;
		}
		if (!pathWithin(source, sourceRoot) || !pathWithin(destination, ownerRoot)) {
			fail(result, '[psych-global-pack-reject] A scoped tree escaped its owner boundary.');
			return;
		}
		var directoryKey = canonicalPath(source);
		if (directoryKey == '' || seenDirectories.exists(directoryKey))
			return;
		seenDirectories.set(directoryKey, true);
		counters.directories++;
		if (counters.directories > MAX_DIRECTORIES) {
			fail(result, '[psych-global-pack-skip] Directory count limit reached.');
			return;
		}
		if (FileSystem.exists(destination) && !FileSystem.isDirectory(destination)) {
			result.skipped++;
			return;
		}
		try {
			ensureDirectory(destination);
		} catch (error:Dynamic) {
			fail(result, '[psych-global-pack-skip] Could not create owner directory: ' + Std.string(error));
			return;
		}
		if (!pathWithin(destination, ownerRoot)) {
			fail(result, '[psych-global-pack-reject] Destination directory escaped its owner: ' + destination);
			return;
		}
		var entries:Array<String>;
		try {
			entries = FileSystem.readDirectory(source);
			entries.sort(Reflect.compare);
		} catch (error:Dynamic) {
			fail(result, '[psych-global-pack-skip] Could not inspect scoped tree: ' + Std.string(error));
			return;
		}
		for (entry in entries) {
			counters.entries++;
			if (counters.entries > MAX_ENTRIES) {
				fail(result, '[psych-global-pack-skip] Entry count limit reached.');
				return;
			}
			if (!validEntry(entry)) {
				fail(result, '[psych-global-pack-reject] Invalid source entry name in ' + source);
				continue;
			}
			var sourcePath = Path.join([source, entry]);
			var destinationPath = existingChildOr(destination, entry);
			if (!FileSystem.exists(sourcePath))
				continue;
			if (!pathWithin(sourcePath, sourceRoot)) {
				fail(result, '[psych-global-pack-reject] Source entry escaped the selected pack: ' + sourcePath);
				continue;
			}
			if (FileSystem.isDirectory(sourcePath)) {
				copyTree(sourcePath, destinationPath, sourceRoot, ownerRoot,
					depth + 1, seenDirectories, counters, result);
				continue;
			}
			copyFile(sourcePath, destinationPath, sourceRoot, ownerRoot, result);
		}
	}

	static function copyFile(source:String, destination:String, sourceRoot:String, ownerRoot:String,
		result:PsychGlobalPackImportResult):Void {
		if (!pathWithin(source, sourceRoot) || !pathWithin(destination, ownerRoot)) {
			fail(result, '[psych-global-pack-reject] File copy escaped its owner boundary.');
			return;
		}
		if (FileSystem.exists(destination)) {
			result.skipped++;
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			if (!pathWithin(destination, ownerRoot)) {
				fail(result, '[psych-global-pack-reject] Destination file escaped its owner: ' + destination);
				return;
			}
			if (FileSystem.exists(destination)) {
				result.skipped++;
				return;
			}
			File.copy(source, destination);
			result.copied++;
		} catch (error:Dynamic) {
			fail(result, '[psych-global-pack-skip] Could not copy ' + source + ': ' + Std.string(error));
		}
	}

	static function copyPackMetadata(packPath:String, owner:String, sourceRoot:String,
		result:PsychGlobalPackImportResult):Void {
		copyFile(packPath, Path.join([owner, 'pack.json']), sourceRoot, owner, result);
		var cover = existingChild(Path.directory(packPath), 'pack.png');
		if (cover != null && !FileSystem.isDirectory(cover))
			copyFile(cover, Path.join([owner, 'pack.png']), sourceRoot, owner, result);
	}

	static function writeReceipt(owner:String, installedPack:String,
		result:PsychGlobalPackImportResult):Bool {
		var pack:Dynamic = readPack(installedPack);
		if (pack == null || Reflect.field(pack, 'runsGlobally') != true)
			return false;
		var receipt = Path.join([owner, RECEIPT_NAME]);
		try {
			if (FileSystem.exists(receipt)) {
				var existing:Dynamic = Json.parse(File.getContent(receipt));
				if (existing == null || Std.int(Reflect.field(existing, 'version')) != RECEIPT_VERSION
					|| Reflect.field(existing, 'ownerRoot') != owner) {
					fail(result, '[psych-global-pack-reject] An unrelated owner receipt blocks import.');
					return false;
				}
				// A refresh may repair missing media, but its provenance receipt is
				// already valid and belongs to this owner. Keep those installed bytes.
				return true;
			}
			ensureDirectory(owner);
			File.saveContent(receipt, Json.stringify({
				version:RECEIPT_VERSION,
				kind:'psych-global-pack',
				engine:ImportEngine.PSYCH,
				ownerRoot:owner,
				packName:packName(pack),
				runsGlobally:true
			}));
			return true;
		} catch (error:Dynamic) {
			fail(result, '[psych-global-pack-skip] Could not write owner receipt: ' + Std.string(error));
			return false;
		}
	}

	static function isImportedGlobalPack(owner:String):Bool {
		#if sys
		if (!validOwnerPath(owner) || !FileSystem.isDirectory(owner))
			return false;
		var receiptPath = Path.join([owner, RECEIPT_NAME]);
		var packPath = Path.join([owner, 'pack.json']);
		if (!FileSystem.exists(receiptPath) || !FileSystem.exists(packPath) || !packRunsGlobally(packPath))
			return false;
		try {
			var receipt:Dynamic = Json.parse(File.getContent(receiptPath));
			return receipt != null && Std.int(Reflect.field(receipt, 'version')) == RECEIPT_VERSION
				&& Reflect.field(receipt, 'kind') == 'psych-global-pack'
				&& Reflect.field(receipt, 'ownerRoot') == owner
				&& Reflect.field(receipt, 'runsGlobally') == true;
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}

	static function isBundledGlobalPack():Bool {
		#if sys
		var root = BUNDLED_PROVIDER_ROOT;
		return FileSystem.isDirectory(root)
			&& packRunsGlobally(Path.join([root, 'pack.json']))
			&& FileSystem.exists(Path.join([root, 'scripts', 'results.lua']));
		#else
		return false;
		#end
	}

	static function findPackPath(source:String, content:String):Null<String> {
		var direct = existingChild(source, 'pack.json');
		if (direct != null && !FileSystem.isDirectory(direct))
			return pathWithin(direct, source) ? direct : null;
		if (content != source) {
			direct = existingChild(content, 'pack.json');
			if (direct != null && !FileSystem.isDirectory(direct))
				return pathWithin(direct, source) ? direct : null;
		}
		return null;
	}

	static function packRunsGlobally(path:String):Bool {
		var data = readPack(path);
		return data != null && Reflect.field(data, 'runsGlobally') == true;
	}

	static function readPack(path:String):Dynamic {
		#if sys
		try {
			var data:Dynamic = Json.parse(File.getContent(path));
			return data != null && !Std.isOfType(data, Array) ? data : null;
		} catch (_:Dynamic) {
			return null;
		}
		#else
		return null;
		#end
	}

	static function packName(pack:Dynamic):String {
		var value:Dynamic = pack == null ? null : Reflect.field(pack, 'name');
		return value == null ? '' : StringTools.trim(Std.string(value));
	}

	static function containsPsychSongCharts(roots:Array<{path:String, prefix:String}>, sourceRoot:String):Bool {
		var checkedDirectories = 0;
		var chartProbes = {count:0};
		for (root in roots) {
			var data = existingChild(root.path, 'data');
			if (data == null || !FileSystem.isDirectory(data))
				continue;
			if (!pathWithin(data, sourceRoot))
				return true;
			if (chartEnvelopeAtDirectory(data, sourceRoot, chartProbes))
				return true;
			var entries:Array<String>;
			try entries = FileSystem.readDirectory(data) catch (_:Dynamic) return true;
			for (entry in entries) {
				var candidate = Path.join([data, entry]);
				if (!FileSystem.exists(candidate) || !pathWithin(candidate, sourceRoot))
					return true;
				if (!FileSystem.isDirectory(candidate))
					continue;
				checkedDirectories++;
				if (checkedDirectories > 256)
					return true;
				var lower = entry.toLowerCase();
				if (lower == 'songdata' || lower == 'songs') {
					var songs:Array<String>;
					try songs = FileSystem.readDirectory(candidate) catch (_:Dynamic) return true;
					for (song in songs) {
						var songPath = Path.join([candidate, song]);
						if (!FileSystem.exists(songPath) || !pathWithin(songPath, sourceRoot))
							return true;
						if (!FileSystem.isDirectory(songPath))
							continue;
						checkedDirectories++;
						if (checkedDirectories > 256 || chartEnvelopeAtDirectory(songPath, sourceRoot,
							chartProbes))
							return true;
					}
				} else if (chartEnvelopeAtDirectory(candidate, sourceRoot, chartProbes)) {
					return true;
				}
			}
		}
		return false;
	}

	static function chartEnvelopeAtDirectory(directory:String, sourceRoot:String,
		chartProbeState:{count:Int}):Bool {
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(directory) catch (_:Dynamic) return true;
		for (entry in entries) {
			var lower = entry.toLowerCase();
			if (!lower.endsWith('.json') && !lower.endsWith('.jsonc'))
				continue;
			chartProbeState.count++;
			if (chartProbeState.count > MAX_CHART_PROBES)
				return true;
			var path = Path.join([directory, entry]);
			if (!FileSystem.exists(path) || !pathWithin(path, sourceRoot))
				return true;
			if (FileSystem.isDirectory(path))
				continue;
			try {
				if (FileSystem.stat(path).size > MAX_CHART_BYTES)
					continue;
				var chart:Dynamic = Json.parse(File.getContent(path));
				var song:Dynamic = chart == null ? null : Reflect.field(chart, 'song');
				if (song != null && Std.isOfType(Reflect.field(song, 'notes'), Array)
					&& Reflect.field(song, 'bpm') != null)
					return true;
			} catch (_:Dynamic) {
				// JSONC chart envelopes cannot be proven absent.  Conservatively reject
				// only documents carrying all three Psych chart field markers.
				try {
					var raw = File.getContent(path).toLowerCase();
					if (raw.indexOf('"song"') >= 0 && raw.indexOf('"notes"') >= 0
						&& raw.indexOf('"bpm"') >= 0)
						return true;
				} catch (_:Dynamic) {}
			}
		}
		return false;
	}

	static function logicalRoots(source:String, content:String):Array<{path:String, prefix:String}> {
		var result:Array<{path:String, prefix:String}> = [{path:source, prefix:''}];
		if (content != source)
			result.push({path:content, prefix:''});
		return result;
	}

	static function canonicalDirectory(path:String):String {
		#if sys
		if (path == null || StringTools.trim(path) == '' || !FileSystem.isDirectory(path))
			return '';
		return canonicalPath(path);
		#else
		return '';
		#end
	}

	static function canonicalPath(path:String):String {
		#if sys
		if (path == null || StringTools.trim(path) == '')
			return '';
		var normalized = Path.normalize(StringTools.replace(path, '\\', '/'));
		if (!Path.isAbsolute(normalized))
			normalized = Path.normalize(Path.join([Sys.getCwd(), normalized]));
		var unresolved:Array<String> = [];
		var existing = normalized;
		while (!FileSystem.exists(existing)) {
			var parent = Path.directory(existing);
			var name = Path.withoutDirectory(existing);
			if (parent == null || parent == existing || name == null || name == '')
				break;
			unresolved.push(name);
			existing = parent;
		}
		try existing = FileSystem.fullPath(existing) catch (_:Dynamic) {}
		while (unresolved.length > 0)
			existing = Path.join([existing, unresolved.pop()]);
		return Path.normalize(existing);
		#else
		return '';
		#end
	}

	static function pathWithin(path:String, parent:String):Bool {
		var child = canonicalPath(path);
		var base = canonicalPath(parent);
		if (child == '' || base == '')
			return false;
		return child == base || child.startsWith(base + '/');
	}

	static function existingChild(directory:String, name:String):Null<String> {
		#if sys
		if (directory == null || name == null || !FileSystem.isDirectory(directory))
			return null;
		try {
			for (entry in FileSystem.readDirectory(directory))
				if (entry.toLowerCase() == name.toLowerCase())
					return Path.join([directory, entry]);
		} catch (_:Dynamic) {}
		#end
		return null;
	}

	static function existingChildOr(directory:String, name:String):String {
		var existing = existingChild(directory, name);
		return existing == null ? Path.join([directory, name]) : existing;
	}

	static function validEntry(name:String):Bool {
		return name != null && name != '' && name != '.' && name != '..'
			&& name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf(':') < 0
			&& name.indexOf(String.fromCharCode(0)) < 0;
	}

	static function validOwnerPath(path:String):Bool {
		return safeOwnerPath(path) != null;
	}

	static function safeOwnerPath(value:Dynamic):Null<String> {
		if (value == null)
			return null;
		var clean = StringTools.replace(StringTools.trim(Std.string(value)), '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0
			|| clean.indexOf(String.fromCharCode(0)) >= 0)
			return null;
		for (part in clean.split('/'))
			if (!validEntry(part))
				return null;
		var normalized = Path.normalize(clean);
		return normalized.startsWith(CompatScriptManifest.ROOT_PREFIX + '/') ? normalized : null;
	}

	static function ensureDirectory(path:String):Void {
		#if sys
		if (path == null || path == '' || FileSystem.exists(path))
			return;
		var parent = Path.directory(path);
		if (parent != null && parent != path && !FileSystem.exists(parent))
			ensureDirectory(parent);
		FileSystem.createDirectory(path);
		#end
	}

	static function fail(result:PsychGlobalPackImportResult, message:String):Void {
		result.failed++;
		result.errors.push(message);
	}
}
