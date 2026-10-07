package;

import haxe.io.Path;
import ModuleFunctions.SongImportBatchResult;
import ModuleFunctions.SongImportDiscoveryResult;
import ModuleFunctions.SongImportDiscoveryRejection;
import ModuleFunctions.SongPackageDiscoveryDiagnostic;
import ImportRootScanner.ImportRoot;
import ImportRootScanner.ImportRootScanDiagnostic;
import ImportRootScanner.ImportRootScanCallbacks;
import ImportRootScanner.ImportRootScanProgress;
import ImportRootScanner.ImportRootScanResult;
import LegacyCharacterAtlasImporter.LegacyCharacterAtlasResult;
import ImportOverlayPlanner.ImportOverlayMount;
import ImportOverlayRuntime;
import PsychSourceStageCompat.PsychCompiledStageSource;
using StringTools;

#if sys
import ImportFileSystem as FileSystem;
import ImportFile as File;
import sys.thread.Thread;
import sys.thread.Mutex;
#end

/** A dependency which was found (or could not be found) while inspecting a
 * chart.  `searched` is deliberately retained in the result: a missing asset
 * report is useful only when it says exactly where the importer looked. */
typedef ImportScanDependency = {
	var kind:String;
	var reference:String;
	var found:Bool;
	var searched:Array<String>;
	var origin:String;
}

typedef ImportScanAsset = {
	var kind:String;
	var name:String;
	var source:String;
	var destination:String;
	var duplicate:Bool;
	var reason:String;
}

/** A source root discovered during a scan.  The importer implementation may
 * fill in `engine`/`confidence` while Auto detection is being added; keeping
 * this metadata on the scan plan means the UI and report can explain which
 * roots were selected without rescanning the source tree. */
typedef ImportScanRoot = {
	var path:String;
	var root:String;
	var contentRoot:String;
	var data:String;
	var engine:String;
	var confidence:Float;
	var evidence:Array<String>;
	var reason:String;
}

/** One song in a scan plan.  No destination file is written while a scan is
 * being performed. */
typedef ImportScanSong = {
	var name:String;
	var duplicate:Bool;
	var willImport:Bool;
	var reason:String;
	@:optional var source:String;
	/** Original donor song folder, retained for provisional availability rows. */
	@:optional var sourceFolder:String;
	/** Scan-authoritative destination folder when duplicate planning resolved it. */
	@:optional var destinationFolder:String;
	@:optional var sourceDuplicate:Bool;
	@:optional var sourceDuplicateOf:String;
	var charts:Array<String>;
	var dependencies:Array<ImportScanDependency>;
	var missing:Array<ImportScanDependency>;
	@:optional var diagnostics:Array<String>;
}

/** A parsed chart paired with its source path.  V-Slice conversion keeps
 * several authored difficulties in memory under one metadata path, so the
 * scanner uses this small neutral shape for both converted and native charts. */
typedef ImportVisualChart = {
	var path:String;
	var chart:Dynamic;
}

typedef ImportScanResult = {
	var source:String;
	/** Normalized selector used to create this plan (for example Auto). */
	var ?importType:String;
	/** Roots and engine decisions made by the scanner. */
	var ?detectedRoots:Array<ImportScanRoot>;
	var ?detectedEngines:Array<String>;
	/** Diagnostics from the bounded Auto root walk.  These are retained in
	 * addition to `errors` so reports and UI can show the exact scan limit and
	 * number of unvisited queued directories. */
	var ?rootScanDiagnostics:Array<ImportRootScanDiagnostic>;
	var ?rootScanTruncated:Bool;
	var ?rootDirectoriesScanned:Int;
	var ?rootDirectoryLimit:Int;
	var ?rootDirectoriesQueued:Int;
	/** Diagnostics from ModuleFunctions' bounded standalone-package walk. */
	var ?packageScanDiagnostics:Array<SongPackageDiscoveryDiagnostic>;
	var ?packageScanTruncated:Bool;
	var ?packageDirectoriesScanned:Int;
	var ?packageDirectoryLimit:Int;
	var ?packageDirectoriesQueued:Int;
	/** Bounded source candidates rejected by song-import validation. They are
	 * reported for diagnosis but are never included in the selectable songs. */
	var ?rejectedSongs:Array<SongImportDiscoveryRejection>;
	var ?rejectedSongCount:Int;
	var ?rejectedSongsTruncated:Bool;
	/** Overlay plans retained from the read-only scan and reused by import. */
	var ?overlayMounts:Array<ImportOverlayMount>;
	var ?overlayPlanned:Int;
	var ?overlayDiagnostics:Array<String>;
	var ?overlayProvenance:Array<String>;
	var logPath:String;
	var songs:Array<ImportScanSong>;
	var assets:Array<ImportScanAsset>;
	var songsFound:Int;
	var songsToImport:Int;
	/** Chart-free Psych global packs available through the scoped importer. */
	@:optional var globalPacksToImport:Int;
	var duplicateSongs:Int;
	var chartsFound:Int;
	var charactersFound:Int;
	var stagesFound:Int;
	var uiPacksFound:Int;
	var layoutsFound:Int;
	var cutscenesFound:Int;
	var scriptsFound:Int;
	var assetFilesFound:Int;
	var assetsToImport:Int;
	var duplicateAssets:Int;
	var missingDependencies:Int;
	var errors:Array<String>;
}

typedef ImportWorkflowProgress = {
	var ?importType:String;
	var phase:String;
	var complete:Bool;
	var progress:Float;
	var current:String;
	var completed:Int;
	var total:Int;
	var result:Dynamic;
	var error:String;
	var copied:Int;
	var skipped:Int;
	var failed:Int;
	/** True after the transaction's main-thread cache/registry handoff succeeds. */
	@:optional var runtimeCommitted:Bool;
}

/**
	The public importer workflow used by Import Settings.

	There are intentionally two phases:

	  1. `beginScan` reads and validates source files only.  It produces a
	     complete plan, including duplicates and missing references, and writes
	     a human-readable report to the game's import directory.
	  2. `beginImport` starts the already-scanned source.  It runs the existing
	     duplicate-safe importer on a native worker thread so the Flixel main
	     loop can continue drawing a progress indicator.

	The worker never receives Flixel/OpenFL objects.  The UI should call
	`poll()` from its update method and only consume the immutable snapshots
	returned by `progress()`.  On non-native targets the same API executes
	synchronously, which keeps the module portable to tools and tests.
*/
class ImportWorkflow {
	public static function beginScan(sourcePath:String, ?importType:String):ImportScanJob {
		return new ImportScanJob(sourcePath, importType);
	}

	// Descriptive aliases used by the import-settings UI.  Keep beginScan and
	// beginImport as the short names for scripts/tools that already adopted the
	// first importer prototype.
	public static function beginSongScan(sourcePath:String, ?importType:String):ImportScanJob {
		return beginScan(sourcePath, importType);
	}

	public static function beginImport(sourcePath:String, scan:ImportScanResult, ?importType:String,
		?packageNames:Map<String, String>):ImportImportJob {
		return new ImportImportJob(sourcePath, scan, importType, packageNames);
	}

	public static function beginSongImport(sourcePath:String, scan:ImportScanResult, ?importType:String,
		?packageNames:Map<String, String>):ImportImportJob {
		return beginImport(sourcePath, scan, importType, packageNames);
	}

	#if sys
	/** Conversion is shared by manual imports and retained-source refreshes. */
	public static function convertRetainedSource(source:String, scan:ImportScanResult,
		names:Map<String,String>):SongImportBatchResult {
		if (scan != null && scan.songsFound == 0 && scan.globalPacksToImport != null
			&& scan.globalPacksToImport > 0)
			return ImportImportJob.importChartFreePsychGlobalPacks(scan);
		return ModuleFunctions.importSongsFromPath(source, scan == null ? ImportEngine.AUTO : scan.importType,
			scan == null ? null : scan.overlayMounts, names);
	}
	#end

	public static function scanNow(sourcePath:String, ?importType:String):ImportScanResult {
		#if sys
		return ImportScanJob.perform(sourcePath, importType);
		#else
		// Native desktop builds are the supported in-game path.  Keep the
		// synchronous API compilable for non-sys tooling, but make its lack of
		// filesystem support explicit rather than pretending a scan succeeded.
		return {
			source: sourcePath,
			importType: ImportSettings.normalizeType(importType),
			detectedRoots: [],
			globalPacksToImport: 0,
			detectedEngines: [],
			rootScanDiagnostics: [],
			rootScanTruncated: false,
			rootDirectoriesScanned: 0,
			rootDirectoryLimit: ImportRootScanner.MAX_DIRECTORIES,
			rootDirectoriesQueued: 0,
			packageScanDiagnostics: [],
			packageScanTruncated: false,
			packageDirectoriesScanned: 0,
			packageDirectoryLimit: ModuleFunctions.MAX_IMPORT_DISCOVERY_DIRECTORIES,
			packageDirectoriesQueued: 0,
			rejectedSongs: [],
			rejectedSongCount: 0,
			rejectedSongsTruncated: false,
			overlayMounts: [],
			overlayPlanned: 0,
			overlayDiagnostics: [],
			overlayProvenance: [],
			logPath: '',
			songsFound: 0,
			songsToImport: 0,
			duplicateSongs: 0,
			chartsFound: 0,
			charactersFound: 0,
			stagesFound: 0,
			uiPacksFound: 0,
			layoutsFound: 0,
			cutscenesFound: 0,
			scriptsFound: 0,
			assetFilesFound: 0,
			assetsToImport: 0,
			duplicateAssets: 0,
			missingDependencies: 0,
			errors: ['Song import scanning requires a native filesystem target.'],
			songs: [],
			assets: []
		};
		#end
	}

	public static function logPath():String {
		return Path.join([ImportSettings.getImportRoot(), 'import-report.txt']);
	}

	public static function writeReport(result:ImportScanResult, ?importSummary:String):Void {
		#if sys
		ImportScanJob.writeReport(result, importSummary);
		#end
	}
}

/** Background scan handle.  Scanning is intentionally done off the render
 * thread because a selected game root may contain thousands of directories. */
class ImportScanJob {
	public var sourcePath(default, null):String;
	public var importType(default, null):String;
	public var done(default, null):Bool = false;
	public var result(default, null):ImportScanResult;
	public var error(default, null):String = null;

	#if sys
	var worker:Thread;
	var stateMutex:Mutex;
	var cancelRequested:Bool = false;
	var phase:String = 'starting';
	var current:String = '';
	var completed:Int = 0;
	var total:Int = 0;
	#end

	#if sys
	// Dependency inspection asks the same case-insensitive paths and registry
	// values for every difficulty of a song.  On a mounted donor tree each
	// readDirectory/stat call can cross a slow filesystem boundary, turning a
	// 96-song scan into minutes of repeated metadata work.  Keep these caches
	// scoped to one scan and clear them before the next scan so they cannot hide
	// files created by a later import.
	static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
	static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
	static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
	static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
	static var registryDocumentCache:Map<String, Dynamic> = new Map<String, Dynamic>();
	static var registryDocumentCacheKnown:Map<String, Bool> = new Map<String, Bool>();
	static var chartCache:Map<String, Dynamic> = new Map<String, Dynamic>();
	static var dependencyCandidateCache:Map<String, Array<String>> = new Map<String, Array<String>>();
	static var luaDiagnosticCache:Map<String, Array<String>> = new Map<String, Array<String>>();
	static var luaDiagnosticCacheKnown:Map<String, Bool> = new Map<String, Bool>();

	static function clearResolutionCaches():Void {
		caseInsensitivePathCache = new Map<String, String>();
		caseInsensitiveFileCache = new Map<String, String>();
		registryValueCache = new Map<String, Dynamic>();
		registryValueCacheKnown = new Map<String, Bool>();
		registryDocumentCache = new Map<String, Dynamic>();
		registryDocumentCacheKnown = new Map<String, Bool>();
		chartCache = new Map<String, Dynamic>();
		dependencyCandidateCache = new Map<String, Array<String>>();
		luaDiagnosticCache = new Map<String, Array<String>>();
		luaDiagnosticCacheKnown = new Map<String, Bool>();
	}

	static function resolutionCacheKey(value:String):String {
		return StringTools.replace(value == null ? '' : value, '\\', '/');
	}

	/** Candidate paths are stable for one scan, but many charts share the same
	 * character, stage, UI, and cutscene references. Cache the completed lookup
	 * per ordered owner-root set and return copies because callers may append
	 * atlas fallbacks to a character's list. */
	static function dependencyCandidateCacheKey(kind:String, roots:Array<String>, reference:String):String {
		var rootKeys:Array<String> = [];
		if (roots != null)
			for (root in roots)
				rootKeys.push(pathKey(root));
		return kind + '\u0000' + rootKeys.join('\u0001') + '\u0000'
			+ (reference == null ? '<null>' : reference);
	}

	static function cachedDependencyCandidates(kind:String, roots:Array<String>, reference:String):Array<String> {
		var key = dependencyCandidateCacheKey(kind, roots, reference);
		return dependencyCandidateCache.exists(key) ? dependencyCandidateCache.get(key).copy() : null;
	}

	static function rememberDependencyCandidates(kind:String, roots:Array<String>, reference:String,
		candidates:Array<String>):Array<String> {
		var value = candidates == null ? [] : candidates;
		dependencyCandidateCache.set(dependencyCandidateCacheKey(kind, roots, reference), value.copy());
		return value;
	}
	#end

	public function new(sourcePath:String, ?importType:String) {
		this.sourcePath = ImportSettings.normalizeSourcePath(sourcePath);
		this.importType = ImportSettings.normalizeType(importType);
		#if sys
		stateMutex = new Mutex();
		worker = Thread.create(function():Void {
			var scanned:ImportScanResult = null;
			var failure:String = null;
			ModuleFunctions.setImportBackgroundMode(true);
			ModuleFunctions.setImportProgressCallback(function(payload:Dynamic):Void {
				acceptProgress(payload);
			});
			ModuleFunctions.setImportCancelCallback(function():Bool {
				return isCancelRequested();
			});
			try {
				scanned = perform(this.sourcePath, this.importType);
			} catch (caught:Dynamic) {
				failure = Std.string(caught);
			}
			ModuleFunctions.setImportProgressCallback(null);
			ModuleFunctions.setImportCancelCallback(null);
			ModuleFunctions.setImportBackgroundMode(false);
			var wasCancelled = isCancelRequested();
			stateMutex.acquire();
			result = scanned;
			error = failure;
			phase = failure == null && wasCancelled ? 'scan-cancelled' : 'scan-complete';
			current = '';
			completed = 1;
			total = 1;
			done = true;
			stateMutex.release();
		});
		#else
		// `perform` is native-only because it uses sys.FileSystem.  Reuse the
		// public fallback result on non-native targets so this handle remains
		// compilable for tooling builds as well.
		result = ImportWorkflow.scanNow(this.sourcePath, this.importType);
		done = true;
		#end
	}

	/** Kept as a method instead of exposing a thread join: callers can invoke
	 * it once per frame without blocking the game loop. */
	public function poll():ImportWorkflowProgress {
		#if sys
		stateMutex.acquire();
		var localDone = done;
		var localResult = result;
		var localError = error;
		var localPhase = phase;
		var localCurrent = current;
		var localCompleted = completed;
		var localTotal = total;
		stateMutex.release();
		#else
		var localDone = done;
		var localResult = result;
		var localError = error;
		var localPhase = 'scan-complete';
		var localCurrent = '';
		var localCompleted = done ? 1 : 0;
		var localTotal = 1;
		#end
		return {
			importType: importType,
			phase: localDone ? localPhase : (localPhase == 'starting' ? 'scanning' : localPhase),
			complete: localDone,
			progress: localDone ? 1 : (localTotal <= 0 ? 0 : Math.min(0.99, localCompleted / localTotal)),
			current: localDone ? '' : (localCurrent == '' ? sourcePath : localCurrent),
			completed: localCompleted,
			total: localTotal,
			result: localResult,
			error: localError,
			copied: 0,
			skipped: 0,
			failed: 0
		};
	}

	public function snapshot():ImportWorkflowProgress {
		return poll();
	}

	public function isFinished():Bool {
		#if sys
		stateMutex.acquire();
		var value = done;
		stateMutex.release();
		return value;
		#else
		return done;
		#end
	}

	function isCancelRequested():Bool {
		#if sys
		stateMutex.acquire();
		var value = cancelRequested;
		stateMutex.release();
		return value;
		#else
		return false;
		#end
	}

	public function cancel():Void {
		#if sys
		stateMutex.acquire();
		cancelRequested = true;
		stateMutex.release();
		#end
	}

	function acceptProgress(payload:Dynamic):Void {
		if (payload == null)
			return;
		#if sys
		stateMutex.acquire();
		var incomingPhase:Dynamic = Reflect.field(payload, 'phase');
		var incomingCurrent:Dynamic = Reflect.field(payload, 'current');
		var incomingCompleted:Dynamic = Reflect.field(payload, 'completed');
		var incomingTotal:Dynamic = Reflect.field(payload, 'total');
		phase = incomingPhase == null ? phase : Std.string(incomingPhase);
		current = incomingCurrent == null ? '' : Std.string(incomingCurrent);
		if (incomingCompleted != null)
			completed = Std.int(incomingCompleted);
		if (incomingTotal != null)
			total = Std.int(incomingTotal);
		stateMutex.release();
		#end
	}

	#if sys
	static inline var MAX_DIRECTORY_SCAN:Int = 4096;
	static inline var MAX_GENERIC_ASSET_FILES:Int = 200000;
	static inline var MAX_SCRIPT_BYTES:Int = 4 * 1024 * 1024;

	static function normalized(path:String):String {
		return ImportSettings.normalizeSourcePath(path);
	}

	static function pathKey(path:String):String {
		var value = normalized(path);
		if (value == '')
			return '';
		var unc = StringTools.startsWith(value, '//');
		// Scanner roots and expanded dependency candidates are already absolute.
		// Re-canonicalizing each one inside uniquePush's comparison loop turns a
		// mounted scan quadratic in filesystem metadata calls. Only expand a
		// genuinely relative spelling.
		if (!Path.isAbsolute(value)) try {
			// Some native targets return an empty string rather than throwing when
			// the candidate does not exist yet.  Keep the normalized authored path
			// in that case: collapsing every missing path (and registry alias id) to
			// the same empty key drops later valid fallback candidates.
			var absolute = normalized(FileSystem.fullPath(value));
			if (absolute != '')
				value = absolute;
		} catch (_:Dynamic) {}
		if (unc && !StringTools.startsWith(value, '//')) {
			while (StringTools.startsWith(value, '/'))
				value = value.substr(1);
			value = value == '' ? '//' : '//' + value;
		}
		#if windows
		return value.toLowerCase();
		#else
		// Keep Linux donor roots case-sensitive; only Windows path identity is
		// case-insensitive.  This prevents dependency/manifest scope crossing
		// between distinct `Pack` and `pack` directories.
		return value;
		#end
	}

	/** Return true when a chart/script belongs to a scanner descriptor's data
	 * or content scope.  Dependency inspection must never use the selected
	 * parent folder as one giant global asset root: unrelated mods can carry a
	 * character with the same name and otherwise hide a missing dependency. */
	static function pathWithin(path:String, parent:String):Bool {
		if (path == null || parent == null || StringTools.trim(path) == '' || StringTools.trim(parent) == '')
			return false;
		var childKey = pathKey(path);
		var parentKey = pathKey(parent);
		if (childKey == '' || parentKey == '')
			return false;
		return childKey == parentKey || StringTools.startsWith(childKey, parentKey + '/');
	}

	static function dependencyRootsForChart(descriptors:Array<ImportRoot>, chartPath:String):Array<String> {
		var scopes:Array<String> = [];
		if (descriptors == null)
			return scopes;
		for (descriptor in descriptors) {
			if (descriptor == null)
				continue;
			var belongs = pathWithin(chartPath, descriptor.data)
				|| pathWithin(chartPath, descriptor.contentRoot)
				|| pathWithin(chartPath, descriptor.root);
			if (!belongs)
				continue;
			var scope = descriptor.contentRoot;
			if (scope == null || StringTools.trim(scope) == '')
				scope = descriptor.root;
			if (scope == null || StringTools.trim(scope) == '')
				continue;
			uniquePush(scopes, scope);
			// Some mixed packs keep shared character/stage definitions outside the
			// chart's contentRoot. Keep that sibling scope attached to its owner so
			// registry/atlas lookup follows the same layout as the importer.
			var shared:Dynamic = Reflect.field(descriptor, 'shared');
			if (shared != null && StringTools.trim(Std.string(shared)) != '')
				uniquePush(scopes, Std.string(shared));
		}
		return scopes;
	}

	static function descriptorScopes(descriptors:Array<ImportRoot>):Array<String> {
		var scopes:Array<String> = [];
		if (descriptors == null)
			return scopes;
		for (descriptor in descriptors) {
			if (descriptor == null)
				continue;
			var scope = descriptor.contentRoot;
			if (scope == null || StringTools.trim(scope) == '')
				scope = descriptor.root;
			if (scope != null && StringTools.trim(scope) != '')
				uniquePush(scopes, scope);
			var shared:Dynamic = Reflect.field(descriptor, 'shared');
			if (shared != null && StringTools.trim(Std.string(shared)) != '')
				uniquePush(scopes, Std.string(shared));
		}
		return scopes;
	}

	static function exists(path:String):Bool {
		return path != null && StringTools.trim(path) != '' && FileSystem.exists(path);
	}

	static function file(path:String):Bool {
		return exists(path) && !FileSystem.isDirectory(path);
	}

	/** Resolve a file name the way the importer resolves chart/audio folders.
	 * Windows packs frequently refer to `Boyfriend` while shipping
	 * `boyfriend.json`; requiring the source spelling here made the read-only
	 * dependency report disagree with the copy phase on Linux. */
	static function caseInsensitiveFile(parent:String, name:String):String {
		if (parent == null || name == null)
			return Path.join([parent == null ? '' : parent, name == null ? '' : name]);
		var cacheKey = resolutionCacheKey(parent) + '\u0000' + resolutionCacheKey(name);
		if (caseInsensitiveFileCache.exists(cacheKey))
			return caseInsensitiveFileCache.get(cacheKey);
		// Resolve the directory itself before reading it.  A donor authored on
		// Windows may use `Data/Characters` while the chart references the
		// conventional lower-case path; checking directory(parent) first would
		// return the unresolved spelling and hide an otherwise valid definition.
		var resolvedParent = caseInsensitivePath(parent);
		if (!directory(resolvedParent)) {
			var missingParent = Path.join([parent, name]);
			caseInsensitiveFileCache.set(cacheKey, missingParent);
			return missingParent;
		}
		var unc = StringTools.startsWith(StringTools.replace(parent, '\\', '/'), '//');
		var restoreUnc = function(value:String):String {
			var result = StringTools.replace(value == null ? '' : value, '\\', '/');
			if (!unc || result.startsWith('//'))
				return result;
			while (result.startsWith('/'))
				result = result.substr(1);
			return result == '' ? '//' : '//' + result;
		};
		try {
			var entries = FileSystem.readDirectory(resolvedParent);
			entries.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				if (entry.toLowerCase() == name.toLowerCase()) {
					var candidate = Path.join([resolvedParent, entry]);
					if (file(candidate)) {
						var resolved = restoreUnc(candidate);
						caseInsensitiveFileCache.set(cacheKey, resolved);
						return resolved;
					}
				}
			}
		} catch (_:Dynamic) {}
		var fallback = restoreUnc(Path.join([parent, name]));
		caseInsensitiveFileCache.set(cacheKey, fallback);
		return fallback;
	}

	/** Resolve a concrete asset path while tolerating the case spelling used by
	 * Windows/macOS packs.  The importer copies the donor tree using the
	 * directory entries it actually finds; dependency inspection must therefore
	 * use the same case-insensitive walk instead of requiring the authored
	 * spelling to exist byte-for-byte on Linux. */
	static function caseInsensitivePath(path:String):String {
		if (path == null || StringTools.trim(path) == '')
			return path;
		var cacheKey = resolutionCacheKey(path);
		if (caseInsensitivePathCache.exists(cacheKey))
			return caseInsensitivePathCache.get(cacheKey);
		if (exists(path))
			{
				caseInsensitivePathCache.set(cacheKey, path);
				return path;
			}
		var parent = Path.directory(path);
		var name = Path.withoutDirectory(path);
		if (parent == null || parent == '' || parent == path || name == null || name == '')
			{
				caseInsensitivePathCache.set(cacheKey, path);
				return path;
			}
		var unc = StringTools.startsWith(StringTools.replace(path, '\\', '/'), '//');
		var restoreUnc = function(value:String):String {
			var result = StringTools.replace(value == null ? '' : value, '\\', '/');
			if (!unc || result.startsWith('//'))
				return result;
			while (result.startsWith('/'))
				result = result.substr(1);
			return result == '' ? '//' : '//' + result;
		};
		var resolvedParent = caseInsensitivePath(parent);
		if (!directory(resolvedParent))
			{
				var missingParent = restoreUnc(path);
				caseInsensitivePathCache.set(cacheKey, missingParent);
				return missingParent;
			}
		try {
			var entries = FileSystem.readDirectory(resolvedParent);
			entries.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				if (entry.toLowerCase() == name.toLowerCase()) {
					var candidate = Path.join([resolvedParent, entry]);
					if (exists(candidate)) {
						var resolved = restoreUnc(candidate);
						caseInsensitivePathCache.set(cacheKey, resolved);
						return resolved;
					}
				}
			}
		} catch (_:Dynamic) {}
		var fallback = restoreUnc(path);
		caseInsensitivePathCache.set(cacheKey, fallback);
		return fallback;
	}

	static function directory(path:String):Bool {
		return exists(path) && FileSystem.isDirectory(path);
	}

	static function ensureDirectory(path:String):Void {
		if (path == null || StringTools.trim(path) == '' || FileSystem.exists(path))
			return;
		var parent = Path.directory(path);
		if (parent != null && parent != '' && parent != path)
			ensureDirectory(parent);
		try {
			FileSystem.createDirectory(path);
		} catch (_:Dynamic) {}
	}

	static function uniquePush(items:Array<String>, value:String):Void {
		if (value == null || StringTools.trim(value) == '')
			return;
		var key = pathKey(value);
		for (item in items)
			if (pathKey(item) == key)
				return;
		items.push(value);
	}

	/** Add a path to a candidate list using a caller-owned set of normalized
	 * keys. Large visual searches build hundreds of candidates across Auto roots;
	 * recomputing every existing path key on each append needlessly multiplies
	 * Path.normalize allocations. The first authored spelling still wins. */
	static function uniquePushKeyed(items:Array<String>, keys:Map<String, Bool>, value:String):Void {
		if (items == null || keys == null || value == null || StringTools.trim(value) == '')
			return;
		var key = pathKey(value);
		if (keys.exists(key))
			return;
		keys.set(key, true);
		items.push(value);
	}

	static function field(value:Dynamic, name:String, fallback:String = ''):String {
		if (value == null)
			return fallback;
		var result:Dynamic = Reflect.field(value, name);
		if (result == null)
			return fallback;
		var text = StringTools.trim(Std.string(result));
		return text == '' || text.toLowerCase() == 'null' ? fallback : text;
	}

	static function readChart(path:String):Dynamic {
		if (!file(path))
			return null;
		var cacheKey = resolutionCacheKey(path);
		if (chartCache.exists(cacheKey))
			return chartCache.get(cacheKey);
		var cached:Dynamic = null;
		try {
			var parsed:Dynamic = CoolUtil.parseJson(File.getContent(path));
			var song:Dynamic = parsed == null ? null : Reflect.field(parsed, 'song');
			// Events/dialogue/noteInfo sidecars can be JSON documents in the same
			// folder, and some donors happen to include a top-level `song` label.
			// A sibling visual donor must be a real chart envelope, not merely a
			// sidecar with a coincidental field name.
			if (song != null && !Std.isOfType(song, String)
				&& (Reflect.hasField(song, 'notes') || Reflect.hasField(song, 'bpm')))
				cached = song;
		} catch (_:Dynamic) {
			cached = null;
		}
		chartCache.set(cacheKey, cached);
		return cached;
	}

	static var visualFallbackFields:Array<String> = [
		'player1', 'player2', 'gf', 'stage', 'uiType', 'cutsceneType',
		'forceLayout', 'uiLayoutType'
	];

	/** Return the song payload for either a native song object or a converted
	 * chart envelope.  V-Slice peers retain their `{song:{...}}` envelope until
	 * inspectChart unwraps the selected chart, so sibling identity/dependency
	 * reads must accept both shapes. */
	static function chartPayload(chart:Dynamic):Dynamic {
		if (chart != null && Reflect.hasField(chart, 'song')) {
			var nested:Dynamic = Reflect.field(chart, 'song');
			if (nested != null && !Std.isOfType(nested, String))
				return nested;
		}
		return chart;
	}

	static function rawChartValue(chart:Dynamic, fieldName:String):String {
		var payload = chartPayload(chart);
		if (payload == null || !Reflect.hasField(payload, fieldName))
			return '';
		var value:Dynamic = Reflect.field(payload, fieldName);
		if (value == null)
			return '';
		var text = StringTools.trim(Std.string(value));
		return text == '' || text.toLowerCase() == 'null' ? '' : text;
	}

	static function chartSongIdentity(chart:Dynamic):String {
		return rawChartValue(chart, 'song').toLowerCase();
	}

	static function visualDependencyKind(fieldName:String):String {
		return switch (fieldName) {
			case 'player1' | 'player2' | 'gf': 'character';
			case 'stage': 'stage';
			case 'uiType': 'ui';
			case 'cutsceneType': 'cutscene';
			case 'forceLayout' | 'uiLayoutType': 'layout';
			default: '';
		};
	}

	/** Check a sibling value using exactly the same donor/destination scopes as
	 * the normal dependency report.  A registry key by itself is not sufficient:
	 * the implementation/atlas must also be present. */
	static function visualDependencyFound(fieldName:String, value:String, sourceRoots:Array<String>):Bool {
		var reference = StringTools.trim(value == null ? '' : value);
		if (reference == '')
			return false;
		var kind = visualDependencyKind(fieldName);
		if (kind == '')
			return true;
		var lowerReference = reference.toLowerCase();
		if (kind == 'cutscene' && lowerReference == 'none')
			return true;
		if (kind == 'layout' && (lowerReference == 'none' || lowerReference == 'normal'))
			return true;
		if (destinationBuiltinDependency(kind, reference))
			return true;
		var roots = dependencyRootsWithDestination(sourceRoots);
		var candidates:Array<String> = switch (kind) {
			case 'character': charCandidates(roots, reference);
			case 'stage': stageCandidates(roots, reference);
			case 'ui': uiCandidates(roots, reference);
			case 'cutscene': cutsceneCandidates(roots, reference);
			case 'layout': layoutCandidates(roots, reference);
			default: [];
		};
		if (kind == 'character')
			return characterRegistryVisualFound(roots, reference) || characterImplementationFound(candidates);
		for (candidate in candidates)
			if (exists(candidate))
				return true;
		return false;
	}

	static function addVisualChartCandidate(result:Array<ImportVisualChart>, path:String, chart:Dynamic):Void {
		if (result == null || chart == null)
			return;
		var key = pathKey(path == null ? '' : path);
		for (existing in result) {
			// Converted charts share a source path.  Object identity is therefore
			// the useful duplicate test for them; native charts use path identity.
			if (chart == existing.chart || (key != '' && key == pathKey(existing.path)))
				return;
		}
		result.push({path:path, chart:chart});
	}

	/** Enumerate native sibling charts without assuming their authored case.
	 * The writer and runtime both accept lower-case destination names, while
	 * Linux source folders may still contain Windows-authored mixed case. */
	static function collectSiblingVisualCharts(chartPath:String, chart:Dynamic,
		?convertedPeers:Array<ImportVisualChart>):Array<ImportVisualChart> {
		var result:Array<ImportVisualChart> = [];
		var selectedIdentity = chartSongIdentity(chart);
		if (convertedPeers != null)
			for (peer in convertedPeers)
				if (peer != null && peer.chart != null && peer.chart != chart
					&& selectedIdentity != '' && chartSongIdentity(peer.chart) == selectedIdentity)
					result.push({path:peer.path, chart:peer.chart});
		var originDir = Path.directory(chartPath);
		if (!directory(originDir))
			return result;
		try {
			var entries = FileSystem.readDirectory(originDir);
			entries.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				var lower = entry.toLowerCase();
				if (!(lower.endsWith('.json') || lower.endsWith('.jsonc')))
					continue;
				var candidatePath = Path.join([originDir, entry]);
				if (pathKey(candidatePath) == pathKey(chartPath))
					continue;
				var candidateChart = readChart(candidatePath);
				if (selectedIdentity != '' && chartSongIdentity(candidateChart) == selectedIdentity)
					addVisualChartCandidate(result, candidatePath, candidateChart);
			}
		} catch (_:Dynamic) {}
		return result;
	}

	static function addSongDiagnostic(song:ImportScanSong, message:String):Void {
		if (song == null || message == null || StringTools.trim(message) == '')
			return;
		if (song.diagnostics == null)
			song.diagnostics = [];
		if (song.diagnostics.indexOf(message) < 0)
			song.diagnostics.push(message);
	}

	/** Resolve only visual metadata for scan-time dependency inspection.  The
	 * selected chart's gameplay fields are deliberately left untouched. */
	static function resolveVisualChartFallback(chartPath:String, chart:Dynamic, sourceRoots:Array<String>,
		scanSong:ImportScanSong, ?convertedPeers:Array<ImportVisualChart>):Dynamic {
		if (chart == null)
			return chart;
		// Resolve onto a detached overlay.  Converted charts are later handed to
		// the writer; mutating one while producing a scan report would silently
		// rewrite the imported chart before the import job starts.
		var resolved:Dynamic = {};
		for (fieldName in Reflect.fields(chart))
			Reflect.setField(resolved, fieldName, Reflect.field(chart, fieldName));
		var siblings = collectSiblingVisualCharts(chartPath, chart, convertedPeers);
		for (fieldName in visualFallbackFields) {
			var requested = rawChartValue(chart, fieldName);
			if (requested != '' && visualDependencyFound(fieldName, requested, sourceRoots))
				continue;
			for (sibling in siblings) {
				var candidate = rawChartValue(sibling.chart, fieldName);
				if (candidate == '' || !visualDependencyFound(fieldName, candidate, sourceRoots))
					continue;
				Reflect.setField(resolved, fieldName, candidate);
				var oldValue = requested == '' ? '<missing>' : '"' + requested + '"';
				var siblingName = sibling.path == null || StringTools.trim(sibling.path) == ''
					? 'a sibling difficulty' : Path.withoutDirectory(sibling.path);
				addSongDiagnostic(scanSong,
					'Compatibility fallback: ' + fieldName + ' ' + oldValue + ' is unavailable in "'
						+ Path.withoutDirectory(chartPath) + '"; using "' + candidate + '" from "' + siblingName + '".');
				break;
			}
		}
		return resolved;
	}

	static function makeResult(source:String, importType:String):ImportScanResult {
		return {
			source: source,
			importType: ImportSettings.normalizeType(importType),
			detectedRoots: [],
			detectedEngines: [],
			rootScanDiagnostics: [],
			rootScanTruncated: false,
			rootDirectoriesScanned: 0,
			rootDirectoryLimit: ImportRootScanner.MAX_DIRECTORIES,
			rootDirectoriesQueued: 0,
			packageScanDiagnostics: [],
			packageScanTruncated: false,
			packageDirectoriesScanned: 0,
			packageDirectoryLimit: ModuleFunctions.MAX_IMPORT_DISCOVERY_DIRECTORIES,
			packageDirectoriesQueued: 0,
			rejectedSongs: [],
			rejectedSongCount: 0,
			rejectedSongsTruncated: false,
			overlayMounts: [],
			overlayPlanned: 0,
			overlayDiagnostics: [],
			overlayProvenance: [],
			logPath: ImportWorkflow.logPath(),
			songs: [],
			assets: [],
			songsFound: 0,
			songsToImport: 0,
			globalPacksToImport: 0,
			duplicateSongs: 0,
			chartsFound: 0,
			charactersFound: 0,
			stagesFound: 0,
			uiPacksFound: 0,
			layoutsFound: 0,
			cutscenesFound: 0,
			scriptsFound: 0,
			assetFilesFound: 0,
			assetsToImport: 0,
			duplicateAssets: 0,
			missingDependencies: 0,
			errors: []
		};
	}

	static function addError(result:ImportScanResult, message:String):Void {
		if (message != null && StringTools.trim(message) != '')
			result.errors.push(message);
	}

	static function findRegistryEntry(root:String, relative:String, name:String):Bool {
		if (name == null || StringTools.trim(name) == '')
			return false;
		var registry = caseInsensitivePath(Path.join([root, relative]));
		if (!file(registry))
			return false;
		var parsed = registryDocument(registry);
		if (parsed == null)
			return false;
		if (Reflect.hasField(parsed, name))
			return true;
		for (key in Reflect.fields(parsed))
			if (key.toLowerCase() == name.toLowerCase())
				return true;
		return false;
	}

	/** Parse each registry at most once during a scan. Distinct chart references
		usually query the same large custom-character registry, so caching only
		individual key results still rereads and reparses that document for every
		character. Both positive and failed parses are scoped to perform(). */
	static function registryDocument(path:String):Dynamic {
		if (path == null || StringTools.trim(path) == '')
			return null;
		var cacheKey = resolutionCacheKey(path);
		if (registryDocumentCacheKnown.exists(cacheKey))
			return registryDocumentCache.get(cacheKey);
		var parsed:Dynamic = null;
		try {
			parsed = CoolUtil.parseJson(File.getContent(path));
		} catch (_:Dynamic) {}
		registryDocumentCacheKnown.set(cacheKey, true);
		registryDocumentCache.set(cacheKey, parsed);
		return parsed;
	}

	/** Read a registry value without treating the key itself as proof that its
	 * implementation exists.  Registries commonly contain aliases (`like`),
	 * stage/cutscene script names, or UI pack `uses` values. */
	static function registryValue(root:String, relative:String, name:String):Dynamic {
		if (name == null || StringTools.trim(name) == '')
			return null;
		var registry = caseInsensitivePath(Path.join([root, relative]));
		if (!file(registry))
			return null;
		var cacheKey = resolutionCacheKey(registry) + '\u0000' + resolutionCacheKey(name);
		if (registryValueCacheKnown.exists(cacheKey))
			return registryValueCache.get(cacheKey);
		var cached:Dynamic = null;
		var parsed = registryDocument(registry);
		if (parsed != null) {
			var direct:Dynamic = Reflect.field(parsed, name);
			if (direct != null)
				cached = direct;
			else
				for (key in Reflect.fields(parsed))
					if (key.toLowerCase() == name.toLowerCase()) {
						cached = Reflect.field(parsed, key);
						break;
					}
		}
		registryValueCacheKnown.set(cacheKey, true);
		registryValueCache.set(cacheKey, cached);
		return cached;
	}

	static function registryText(value:Dynamic, fieldName:String, fallback:String = ''):String {
		if (value == null)
			return fallback;
		var fieldValue:Dynamic = Std.isOfType(value, String) ? value : Reflect.field(value, fieldName);
		if (fieldValue == null)
			return fallback;
		var text = StringTools.trim(Std.string(fieldValue));
		return text == '' || text.toLowerCase() == 'null' ? fallback : text;
	}

	static function characterRegistryEntry(roots:Array<String>, name:String):Bool {
		for (root in roots)
			if (findRegistryEntry(root, 'images/custom_chars/custom_chars.jsonc', name)
				|| findRegistryEntry(root, 'images/custom_chars/custom_chars.json', name)
				|| findRegistryEntry(root, 'images/custom_chars/icon_only_chars.json', name))
				return true;
		return false;
	}

	/**
		Validate a registry-backed character using the same alias shape as
		Song.resolveCharacterVisualFromData. Modding Plus commonly stores an
		atlas pair in `<id>/char.png` + `<id>/char.xml` and points the registry
		entry at a shared implementation with `like`; the XML is not itself a
		character implementation, so a registry key alone must not hide a broken
		entry.
	*/
	static function characterRegistryVisualFound(roots:Array<String>, name:String):Bool {
		if (name == null || StringTools.trim(name) == '')
			return false;
		var references:Array<String> = [StringTools.trim(name)];
		var canonical = canonicalLegacyCharacter(name);
		if (canonical != '')
			uniquePush(references, canonical);
		for (root in roots) {
			for (requested in references) {
				var entry:Dynamic = null;
				for (registryName in ['custom_chars.jsonc', 'custom_chars.json', 'icon_only_chars.json']) {
					entry = registryValue(root, 'images/custom_chars/' + registryName, requested);
					if (entry != null)
						break;
				}
				if (entry == null)
					continue;
				var implementations:Array<String> = [requested];
				var mapped = registryText(entry, 'like');
				if (mapped != '')
					uniquePush(implementations, mapped);
				for (implementation in implementations) {
					var base = Path.join([root, 'images', 'custom_chars', implementation]);
					var png = caseInsensitivePath(Path.join([base, 'char.png']));
					var xml = caseInsensitivePath(Path.join([base, 'char.xml']));
					if (!file(png) || !file(xml))
						continue;
					// The registry alias may point to a top-level native HScript, or
					// to a same-named definition folder. Both are accepted by Song.
					var implementationFound = false;
					for (suffix in ['.hscript', '.hxs', '.json', '.jsonc'])
						if (file(caseInsensitivePath(Path.join([root, 'images', 'custom_chars', implementation + suffix]))))
							implementationFound = true;
					if (implementationFound)
						return true;
				}
			}
		}
		return false;
	}

	/**
	 * Older charts commonly use the role names from the original engine rather
	 * than the character ids used by this destination.  Keep the authored
	 * spelling in the scan result and chart itself, but search the canonical
	 * native ids as a fallback.  This is intentionally a small, explicit alias
	 * table: arbitrary donor names must still be supplied by the donor pack.
	 */
	static function canonicalLegacyCharacter(reference:String):String {
		var value = StringTools.trim(reference == null ? '' : reference).toLowerCase();
		return switch (value) {
			case 'boyfriend': 'bf';
			case 'daddy': 'dad';
			case 'girlfriend': 'gf';
			default: '';
		};
	}

	/**
	 * A scan is read-only, but the destination's native registries are still
	 * valid dependency providers.  Search them in addition to the detected
	 * donor roots without adding the destination to the donor-script inspection
	 * scope (otherwise built-in scripts would be reported as donor assets).
	 */
	static function dependencyRootsWithDestination(sourceRoots:Array<String>, ?descriptors:Dynamic):Array<String> {
		var result:Array<String> = sourceRoots == null ? [] : sourceRoots.copy();
		if (descriptors != null)
			for (descriptor in (cast descriptors:Array<Dynamic>)) {
				if (descriptor == null)
					continue;
				// Auto may select several independent engine roots inside one source
				// folder. A chart's visual dependency can legitimately be supplied by
				// a sibling root (or by a previously imported destination asset), so
				// include only the scanner's bounded, detected roots here. Explicit
				// engine selections pass null and remain owner-scoped.
				var scope = descriptor.contentRoot;
				if (scope == null || StringTools.trim(scope) == '')
					scope = descriptor.root;
				if (scope != null && StringTools.trim(scope) != '')
					uniquePush(result, scope);
				var shared:Dynamic = Reflect.field(descriptor, 'shared');
				if (shared != null && StringTools.trim(Std.string(shared)) != '')
					uniquePush(result, Std.string(shared));
			}
		// Use an absolute destination scope so candidate identity does not depend
		// on a worker/tool changing its current directory after the scan starts.
		uniquePush(result, Path.join([Sys.getCwd(), 'assets']));
		return result;
	}

	/** Dependencies handled by the destination engine without a donor file. */
	static function destinationBuiltinDependency(kind:String, reference:String):Bool {
		var value = StringTools.trim(reference == null ? '' : reference).toLowerCase();
		if (value == '')
			return false;
		return switch (kind) {
			case 'character': value == 'bf' || value == 'boyfriend' || value == 'dad' || value == 'daddy'
				|| value == 'gf' || value == 'girlfriend' || value == 'nogf' || value == 'no-gf' || value == 'no_gf';
			// Psych character JSON stores an icon id in `healthicon`; it is not a
			// JSON/image path.  The destination provides the original role icons
			// without requiring a donor file, just as it provides the characters.
			case 'health-icon': value == 'bf' || value == 'boyfriend' || value == 'dad' || value == 'daddy'
				|| value == 'gf' || value == 'girlfriend';
			case 'cutscene': value == 'senpai' || value == 'angry-senpai';
			case 'layout': value == 'none' || value == 'normal';
			// V-Slice's stock pixel note style is backed by the destination's
			// native pixel UI route. The importer normalizes the authored
			// `pixel`/`pixelated` style to this id, so the scan must not report
			// the absence of a literal custom_ui/ui_packs/pixel directory as a
			// missing dependency.
			case 'ui': value == 'normal' || value == 'pixel';
			default: false;
		};
	}

	static function dependency(result:ImportScanResult, song:ImportScanSong, kind:String, reference:String,
		origin:String, candidates:Array<String>, registryFound:Bool = false, forceMissing:Bool = false,
		?fallbackClassification:String, ?fallbackImpact:String):Void {
		var ref = StringTools.trim(reference == null ? '' : reference);
		if (ref == '' || ref.toLowerCase() == 'none' || ref.toLowerCase() == 'null')
			return;
		var unique = kind + '|' + ref.toLowerCase();
		for (existing in song.dependencies)
			if (existing.kind + '|' + existing.reference.toLowerCase() == unique)
				return;
		var found = false;
		if (!forceMissing) {
			found = registryFound || destinationBuiltinDependency(kind, ref);
			if (!found && kind == 'character')
				found = characterImplementationFound(candidates);
			else if (!found)
				for (candidate in candidates)
					if (exists(candidate)) {
						found = true;
						break;
					}
		}
		var item:ImportScanDependency = {
			kind: kind,
			reference: ref,
			found: found,
			searched: candidates,
			origin: origin
		};
		song.dependencies.push(item);
		if (found && song.diagnostics == null)
			song.diagnostics = [];
		if (found && kind == 'stage') {
			var nativeStage = EngineCompat.resolveStageAlias(ref);
			if (nativeStage != null && nativeStage.toLowerCase() != ref.toLowerCase())
				song.diagnostics.push('[compatibility-alias] Stage "' + ref + '" resolves to native stage "' + nativeStage + '".');
		} else if (found && kind == 'script-asset') {
			var nativeAsset = EngineCompat.resolveLegacyAssetPath(ref);
			if (nativeAsset != null && nativeAsset != ref)
				song.diagnostics.push('[compatibility-alias] Asset "' + ref + '" resolves to native asset "' + nativeAsset + '".');
		}
		if (!found) {
			song.missing.push(item);
			var impact = fallbackImpact == null || StringTools.trim(fallbackImpact) == '' ? switch (kind) {
				case 'stage': 'stage visuals use the neutral native stage group; notes, timing, and gameplay callbacks continue';
				case 'character': 'character visual falls back to Dad at runtime; note lanes, timing, and score gameplay continue';
				case 'health-icon': 'health display uses the neutral icon grid; health values, scoring, and note gameplay continue';
				default: 'the dependent optional visual/module remains unavailable; unrelated gameplay continues';
			} : fallbackImpact;
			var fallbackPlan = EngineCompat.planVisualFallback(kind, ref, origin, candidates, impact,
				fallbackClassification == null || StringTools.trim(fallbackClassification) == ''
					? 'donor-source-omission' : fallbackClassification);
			addSongDiagnostic(song, fallbackPlan.diagnostic.message);
			result.missingDependencies++;
		}
	}

	/** Character.characterExists requires both the registered implementation
	 * file and its name-specific/aliased folder.  Checking any one candidate was
	 * too permissive: an icon or a loose script could make a broken character
	 * appear available.  Legacy `characters/<name>.png` entries remain valid as
	 * a concrete sprite fallback. */
	static function characterImplementationFound(candidates:Array<String>):Bool {
		for (candidate in candidates) {
			if (!file(candidate))
				continue;
			var lower = candidate.toLowerCase().replace('\\', '/');
			if (lower.indexOf('/characters/') >= 0 && lower.endsWith('.png'))
				return true;
			// Character.characterExists does not accept a sprite/atlas by itself;
			// it needs the implementation script or JSON below.  Keep char.png in
			// the searched list so reports explain why a visual-only folder is
			// incomplete, but do not let it satisfy the dependency.
			if (lower.endsWith('/char.png') || lower.endsWith('/char.xml')) {
				// A registry-backed Sparrow pair is a valid native character source;
				// the XML/PNG pair is intentionally considered together below rather
				// than allowing either half to satisfy a dependency on its own.
				var folder = Path.directory(candidate);
				var pairedPng = caseInsensitivePath(Path.join([folder, 'char.png']));
				var pairedXml = caseInsensitivePath(Path.join([folder, 'char.xml']));
				if (file(pairedPng) && file(pairedXml))
					continue;
				continue;
			}
			// Native custom-char aliases are valid when their implementation is a
			// top-level script (`custom_chars/parents.hscript`) rather than a
			// same-named directory.  Character.characterExists() accepts this
			// layout and the importer preserves it; requiring a sibling directory
			// made destination-provided aliases look absent.
			if (lower.indexOf('/images/custom_chars/') >= 0 && lower.endsWith('.hscript'))
				return true;
			if (lower.endsWith('/animation.json') && directory(Path.directory(candidate)))
				return true;
			if (lower.endsWith('.hxc'))
				return true;
			if (lower.endsWith('.hscript') || lower.endsWith('.json') || lower.endsWith('.jsonc')) {
				var implementationBase = Path.withoutExtension(candidate);
				if (directory(implementationBase))
					return true;
			}
		}
		return false;
	}

	/** Inspect compiled-definition fallbacks without broadening the owning root. */
	static function legacyCharacterAtlas(roots:Array<String>, reference:String, ?role:String):LegacyCharacterAtlasResult {
		if (reference == null || StringTools.trim(reference) == ''
			|| destinationBuiltinDependency('character', reference))
			return null;
		// Prefer the chart owner, then each bounded Auto sibling, before asking
		// the atlas index to compare all roots at once. Identical copies of a
		// legacy atlas in two donor roots should not become an artificial
		// ambiguity; the first complete scoped provider is deterministic and
		// matches the import overlay order.
		if (roots != null)
			for (root in roots) {
				var scoped = LegacyCharacterAtlasImporter.inspectRoots([root], reference, role);
				if (scoped != null && scoped.recoverable)
					return scoped;
			}
		return LegacyCharacterAtlasImporter.inspectRoots(roots, reference, role);
	}

	/**
	 * Legacy atlas inference is only a fallback for characters whose native
	 * implementation is absent.  Auto mode can expose both a donor root and
	 * the destination (or a second donor root) to the atlas index; running the
	 * fallback unconditionally then reports the same valid character as an
	 * ambiguous atlas, even though Character/HXC resolution already has an
	 * exact implementation.  Keep the decision at the importer level so all
	 * engine adapters share the same rule.
	 */
	static function legacyCharacterAtlasNeeded(roots:Array<String>, reference:String,
		candidates:Array<String>):Bool {
		if (reference == null || StringTools.trim(reference) == ''
			|| destinationBuiltinDependency('character', reference))
			return false;
		if (characterRegistryVisualFound(roots, reference)
			|| characterImplementationFound(candidates))
			return false;
		return true;
	}

	/**
	 * Shared import-time decision for compiled legacy character fallbacks.
	 *
	 * The read-only scan and the copy phase must agree about whether an atlas is
	 * actually needed. Keeping this wrapper here lets the copy phase reuse the
	 * exact registry-alias, native implementation, HXC, and Psych candidate
	 * checks without duplicating chart-specific character names or filesystem
	 * rules. The caller scopes `roots` to the owning donor plus destination
	 * assets already materialized for this import.
	 */
	public static function shouldInferLegacyCharacterAtlas(roots:Array<String>, reference:String):Bool {
		var scopedRoots = roots == null ? [] : roots;
		return legacyCharacterAtlasNeeded(scopedRoots, reference, charCandidates(scopedRoots, reference));
	}

	static function appendLegacyAtlasCandidates(candidates:Array<String>, finding:LegacyCharacterAtlasResult):Void {
		if (finding == null || finding.candidates == null)
			return;
		for (candidate in finding.candidates) {
			if (candidate == null)
				continue;
			uniquePush(candidates, candidate.png);
			uniquePush(candidates, candidate.xml);
		}
		if (finding.searched != null)
			for (searched in finding.searched)
				uniquePush(candidates, searched);
	}

	static function appendLegacyAtlasDiagnostics(scanSong:ImportScanSong,
		finding:LegacyCharacterAtlasResult):Void {
		if (scanSong == null || finding == null || finding.diagnostics == null)
			return;
		if (scanSong.diagnostics == null)
			scanSong.diagnostics = [];
		for (diagnostic in finding.diagnostics)
			if (diagnostic != null && scanSong.diagnostics.indexOf(diagnostic) < 0)
				scanSong.diagnostics.push(diagnostic);
	}

	static function charCandidates(sourceRoots:Array<String>, reference:String):Array<String> {
		var cached = cachedDependencyCandidates('character', sourceRoots, reference);
		if (cached != null)
			return cached;
		var result:Array<String> = [];
		var resultKeys:Map<String, Bool> = new Map();
		for (root in sourceRoots) {
			var references:Array<String> = [reference];
			var canonical = canonicalLegacyCharacter(reference);
			if (canonical != '')
				references.push(canonical);
			var implementations:Array<String> = [];
			for (requested in references) {
				uniquePush(implementations, requested);
				for (registryName in ['custom_chars.jsonc', 'custom_chars.json']) {
					var mapped = registryText(registryValue(root, 'images/custom_chars/' + registryName, requested), 'like');
					if (mapped != '')
						uniquePush(implementations, mapped);
				}
			}
			for (implementation in implementations) {
				var base = Path.join([root, 'images', 'custom_chars', implementation]);
				// XML/TXT is only an atlas descriptor.  Without a concrete sprite or
				// implementation script it is not enough to import a playable
				// character, and accepting it hid broken registry entries.  The
				// folder + script/JSON pairing mirrors Character.characterExists.
				for (suffix in ['/char.png', '/char.xml', '/char.txt', '.hscript', '.json', '.jsonc'])
					uniquePushKeyed(result, resultKeys, base + suffix);
			}
			for (requested in references)
				uniquePushKeyed(result, resultKeys, Path.join([root, 'images', 'characters', requested + '.png']));
			// V-Slice/FPS Plus keep character definitions separately from their
			// atlases. Resolve assetPath so Linux case sensitivity does not turn a
			// valid `M1KU` atlas into a false missing dependency for `m1ku`.
			for (definition in [
				caseInsensitiveFile(Path.join([root, 'data', 'characters']), reference + '.json'),
				caseInsensitiveFile(Path.join([root, 'data', 'characters']), reference + '.hxc'),
				// Codename keeps character definitions as XML beside the JSON/HXC
				// families; convertCodenameCharacter consumes the same root.
				caseInsensitiveFile(Path.join([root, 'data', 'characters']), reference + '.xml'),
				caseInsensitiveFile(Path.join([root, 'shared', 'characters']), reference + '.json'),
				caseInsensitiveFile(Path.join([root, 'shared', 'characters']), reference + '.hxc'),
				caseInsensitiveFile(Path.join([root, 'shared', 'characters']), reference + '.xml'),
				// Psych Engine keeps character definitions at the game root rather
				// than below data/.  These roots are common in mixed Auto imports
				// (for example PERFEXION) and used to be reported as unsupported
				// even though importPsychCharacters() can convert them later.
				caseInsensitiveFile(Path.join([root, 'characters']), reference + '.json'),
				caseInsensitiveFile(Path.join([root, 'characters']), reference + '.hxc')
			]) {
				uniquePushKeyed(result, resultKeys, definition);
				if (!file(definition))
					continue;
				if (definition.toLowerCase().endsWith('.hxc'))
					continue;
				try {
					var parsed:Dynamic = CoolUtil.parseJson(File.getContent(definition));
					// Psych names this field `image`; V-Slice/FPS definitions use
					// `assetPath`.  Both describe the atlas relative to images/.
					var assetPath = field(parsed, 'assetPath', field(parsed, 'image', 'characters/' + reference));
					for (imageRoot in [Path.join([root, 'images']), Path.join([root, 'shared', 'images'])]) {
						uniquePushKeyed(result, resultKeys, caseInsensitivePath(Path.join([imageRoot, assetPath + '.png'])));
						uniquePushKeyed(result, resultKeys, caseInsensitivePath(Path.join([imageRoot, assetPath + '.xml'])));
						uniquePushKeyed(result, resultKeys, caseInsensitivePath(Path.join([imageRoot, assetPath + '.txt'])));
						// Psych/Funkadelix Animate exports are directories rather than
						// Sparrow pairs. The importer routes these through DisSprite's
						// flixel-animate loader and generates a native HScript adapter.
						uniquePushKeyed(result, resultKeys, caseInsensitivePath(Path.join([imageRoot, assetPath, 'Animation.json'])));
						uniquePushKeyed(result, resultKeys, caseInsensitivePath(Path.join([imageRoot, assetPath + '.astc'])));
					}
				} catch (_:Dynamic) {}
			}
		}
		return rememberDependencyCandidates('character', sourceRoots, reference, result);
	}

	static function stageCandidates(sourceRoots:Array<String>, reference:String):Array<String> {
		var cached = cachedDependencyCandidates('stage', sourceRoots, reference);
		if (cached != null)
			return cached;
		var result:Array<String> = [];
		for (root in sourceRoots) {
			var implementations:Array<String> = [];
			for (requested in EngineCompat.stageLookupNames(reference)) {
				uniquePush(implementations, requested);
				var mapped = registryText(registryValue(root, 'images/custom_stages/custom_stages.json', requested), 'like');
				if (mapped != '')
					uniquePush(implementations, mapped);
			}
			for (implementation in implementations) {
				var base = Path.join([root, 'images', 'custom_stages', implementation]);
				for (suffix in ['.hscript'])
					uniquePush(result, base + suffix);
			}
			for (requested in EngineCompat.stageLookupNames(reference)) {
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'data', 'stages']), requested + '.json'));
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'data', 'stages']), requested + '.hxc'));
				// Codename stage definitions are XML under data/stages.
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'data', 'stages']), requested + '.xml'));
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'shared', 'stages']), requested + '.json'));
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'shared', 'stages']), requested + '.hxc'));
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'shared', 'stages']), requested + '.xml'));
				// Psych/Kade stage definitions and stage Lua scripts live directly
				// under stages/.  A chart dependency report must inspect the same
				// root that the engine-specific importer uses.
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'stages']), requested + '.json'));
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'stages']), requested + '.lua'));
				uniquePush(result, caseInsensitiveFile(Path.join([root, 'stages']), requested + '.hxc'));
			}
		}
		return rememberDependencyCandidates('stage', sourceRoots, reference, result);
	}

	static function uiCandidates(sourceRoots:Array<String>, reference:String):Array<String> {
		var cached = cachedDependencyCandidates('ui', sourceRoots, reference);
		if (cached != null)
			return cached;
		var result:Array<String> = [];
		for (root in sourceRoots) {
			var base = Path.join([root, 'images', 'custom_ui']);
			var implementations:Array<String> = [reference];
			var mapped = registryText(registryValue(root, 'images/custom_ui/ui_packs/ui.json', reference), 'uses');
			if (mapped != '')
				implementations.push(mapped);
			for (implementation in implementations)
				// A layout or a custom note definition is not a UI pack.  Keep
				// those diagnostics in their own dependency categories so an
				// unrelated file cannot make a missing pack look present.
				for (suffix in ['/ui_packs/' + implementation + '/NOTE_assets.png', '/ui_packs/' + implementation + '/arrows-pixels.png'])
					uniquePush(result, base + suffix);
			// A converted V-Slice style is materialized into the destination
			// registry later, but the donor dependency is its source definition
			// under data/notestyles.  Keep this lookup generic so custom styles are
			// recognized during a read-only scan rather than reported as missing
			// merely because V-Slice does not use custom_ui/ui_packs on disk.
			var authoredStyles:Array<String> = [reference];
			var lowerReference = reference == null ? '' : reference.toLowerCase();
			if (lowerReference.startsWith('vslice-') && reference.length > 7)
				authoredStyles.push(reference.substr(7));
			for (style in authoredStyles)
				for (styleBase in [Path.join([root, 'data', 'notestyles']), Path.join([root, 'notestyles'])])
					for (extension in ['.json', '.jsonc'])
						uniquePush(result, Path.join([styleBase, style + extension]));
		}
		return rememberDependencyCandidates('ui', sourceRoots, reference, result);
	}

	static function cutsceneCandidates(sourceRoots:Array<String>, reference:String):Array<String> {
		var cached = cachedDependencyCandidates('cutscene', sourceRoots, reference);
		if (cached != null)
			return cached;
		var result:Array<String> = [];
		for (root in sourceRoots) {
			var base = Path.join([root, 'images', 'custom_cutscenes']);
			var implementations:Array<String> = [reference];
			var mapped = registryText(registryValue(root, 'images/custom_cutscenes/cutscenes.json', reference), 'like');
			if (mapped != '')
				implementations.push(mapped);
			for (implementation in implementations)
				for (suffix in ['/' + implementation + '.hscript'])
					uniquePush(result, base + suffix);
		}
		return rememberDependencyCandidates('cutscene', sourceRoots, reference, result);
	}

	static function layoutCandidates(sourceRoots:Array<String>, reference:String):Array<String> {
		var cached = cachedDependencyCandidates('layout', sourceRoots, reference);
		if (cached != null)
			return cached;
		var result:Array<String> = [];
		for (root in sourceRoots) {
			var base = Path.join([root, 'images', 'custom_ui', 'ui_layouts', reference]);
			for (suffix in ['/' + reference + '.hscript', '.hscript'])
				uniquePush(result, base + suffix);
		}
		return rememberDependencyCandidates('layout', sourceRoots, reference, result);
	}

	static function extractQuotedAfter(line:String, token:String):String {
		var start = line.indexOf(token);
		if (start < 0)
			return null;
		var quote = -1;
		for (i in (start + token.length)...line.length) {
			var ch = line.charAt(i);
			if (ch == '"' || ch == "'") {
				quote = i;
				break;
			}
		}
		if (quote < 0)
			return null;
		var mark = line.charAt(quote);
		var end = line.indexOf(mark, quote + 1);
		return end < 0 ? null : line.substr(quote + 1, end - quote - 1);
	}

	/** Return every simple quoted argument after a loader token.  Packer calls
	 * carry both the PNG and its sibling `.txt`; the older one-value helper is
	 * retained for all other script APIs. */
	static function extractQuotedAfterAll(line:String, token:String):Array<String> {
		var result:Array<String> = [];
		var start = line.indexOf(token);
		if (start < 0)
			return result;
		var cursor = start + token.length;
		while (cursor < line.length) {
			var quote = -1;
			for (i in cursor...line.length) {
				var ch = line.charAt(i);
				if (ch == '"' || ch == "'") {
					quote = i;
					break;
				}
			}
			if (quote < 0)
				break;
			var mark = line.charAt(quote);
			var end = line.indexOf(mark, quote + 1);
			if (end < 0)
				break;
			result.push(line.substr(quote + 1, end - quote - 1));
			cursor = end + 1;
		}
		return result;
	}

	static function scriptCandidates(sourceRoots:Array<String>, scriptPath:String, reference:String):Array<String> {
		return scriptCandidatesForToken(sourceRoots, scriptPath, reference, '');
	}

	/** Resolve script asset references using the same asset-root convention as
	 * Paths.image/sound/music/video.  In particular, a donor root already points
	 * at `assets/`, so `assets/images/foo.png` must not become
	 * `<donor>/assets/assets/images/foo.png`. */
	static function scriptCandidatesForToken(sourceRoots:Array<String>, scriptPath:String, reference:String,
		token:String):Array<String> {
		var result:Array<String> = [];
		var raw = StringTools.trim(reference);
		if (raw == '')
			return result;
		raw = StringTools.replace(raw, '\\', '/');
		while (raw.indexOf('./') == 0)
			raw = raw.substr(2);
		var scriptDir = Path.directory(scriptPath);
		var absolute = StringTools.startsWith(raw, '/') || raw.indexOf(':') == 1;
		var assetRelative = StringTools.startsWith(raw.toLowerCase(), 'assets/') ? raw.substr(7) : raw;
		var nativeAsset = EngineCompat.resolveLegacyAssetPath(raw);
		var nativeAssetRelative = nativeAsset == null ? raw
			: (StringTools.startsWith(nativeAsset.toLowerCase(), 'assets/') ? nativeAsset.substr(7) : nativeAsset);
		var tokenLower = token == null ? '' : token.toLowerCase();
		var folder = tokenLower.indexOf('sound') >= 0 || tokenLower.indexOf('getsound') >= 0 ? 'sounds'
			: (tokenLower.indexOf('music') >= 0 ? 'music'
				: (tokenLower.indexOf('video') >= 0 ? 'videos' : 'images'));
		var extensions:Array<String> = switch (folder) {
			case 'sounds', 'music': ['.ogg', '.wav', '.mp3'];
			case 'videos': ['.mp4', '.webm', '.ogv'];
			default: ['.png', '.xml', '.txt', '.json'];
		};
		var addWithExtensions = function(base:String):Void {
			if (base == null || StringTools.trim(base) == '')
				return;
			uniquePush(result, caseInsensitivePath(base));
			if (Path.extension(base) == '')
				for (extension in extensions)
					uniquePush(result, caseInsensitivePath(base + extension));
			// SpriteSheetPacker stores frame rectangles in a sibling TXT file while
			// the HScript call normally names the PNG first.  Keep the companion in
			// the read-only search even when the script does not spell its path as a
			// separate asset token.
			if (tokenLower.indexOf('spritesheetpacker') >= 0 && Path.extension(base).toLowerCase() == '.png')
				uniquePush(result, caseInsensitivePath(Path.withoutExtension(base) + '.txt'));
		};
		if (absolute) {
			addWithExtensions(raw);
			return result;
		}
		addWithExtensions(Path.join([scriptDir, raw]));
		// Stage/character HScript receives `hscriptPath` at runtime.  In the
		// imported registry this points at the folder named after the script
		// (or its `like` alias), not merely at custom_stages/ or custom_chars/.
		// The lexical reference extracted above is just `tankSky.png` from
		// `hscriptPath + 'tankSky.png'`, so include that script-stem folder in
		// the read-only dependency search as well.  Without it, valid stage
		// assets are reported missing even though the writer copies that folder.
		var scriptStem = Path.withoutExtension(Path.withoutDirectory(Path.normalize(scriptPath)));
		if (scriptStem != null && StringTools.trim(scriptStem) != '')
			addWithExtensions(Path.join([scriptDir, scriptStem, raw]));
		for (root in sourceRoots) {
			// `root` is the donor assets directory.  Strip a leading assets/
			// component before joining it, while retaining the literal path in
			// the searched list for reports.
			addWithExtensions(Path.join([root, assetRelative]));
			if (nativeAssetRelative != assetRelative)
				addWithExtensions(Path.join([root, nativeAssetRelative]));
			// Older FNF/Kade/FPS packs expose their common asset root below
			// `shared/`, while scripts still author the canonical `assets/...`
			// path.  The importer flattens that shared tree into assets/; search
			// it here too so script and JSON diagnostics match the copy phase.
			addWithExtensions(Path.join([root, 'shared', assetRelative]));
			if (nativeAssetRelative != assetRelative)
				addWithExtensions(Path.join([root, 'shared', nativeAssetRelative]));
			if (assetRelative.toLowerCase().indexOf(folder + '/') != 0)
				addWithExtensions(Path.join([root, folder, assetRelative]));
			if (assetRelative.toLowerCase().indexOf(folder + '/') != 0)
				addWithExtensions(Path.join([root, 'shared', folder, assetRelative]));
			if (tokenLower.indexOf('icon') >= 0 || tokenLower.indexOf('healthicon') >= 0) {
				var iconName = raw.toLowerCase().startsWith('icon-') ? raw : 'icon-' + raw;
				for (iconRoot in [Path.join([root, 'images', 'icons']), Path.join([root, 'shared', 'images', 'icons'])])
					addWithExtensions(Path.join([iconRoot, iconName]));
				// Native destination characters store the same health icon as
				// `icons.png`; include it for canonical roles such as bf/dad/gf.
				var canonical = canonicalLegacyCharacter(raw);
				var iconCharacters:Array<String> = canonical == '' ? [raw] : [raw, canonical];
				for (iconCharacter in iconCharacters)
					for (charRoot in [Path.join([root, 'images', 'custom_chars']), Path.join([root, 'shared', 'images', 'custom_chars'])])
						addWithExtensions(Path.join([charRoot, iconCharacter, 'icons']));
			}
		}
		return result;
	}

	static function inspectScript(result:ImportScanResult, song:ImportScanSong, path:String, roots:Array<String>):Void {
		if (!file(path) || pathKey(path) == '')
			return;
		var contents:String;
		try {
			var size = FileSystem.stat(path).size;
			if (size > MAX_SCRIPT_BYTES)
				return;
			contents = File.getContent(path);
		} catch (_:Dynamic) {
			return;
		}
		result.scriptsFound++;
			var tokens = ['Paths.image', 'Paths.sound', 'Paths.music', 'Paths.video', 'loadGraphic',
				'getBitmap', 'getSound', 'bitmap.add', 'fromSparrow', 'fromSpriteSheetPacker', 'fromXML'];
		for (line in contents.replace('\r\n', '\n').replace('\r', '\n').split('\n')) {
			for (token in tokens) {
				var references:Array<String> = token == 'fromSpriteSheetPacker'
					? extractQuotedAfterAll(line, token) : [extractQuotedAfter(line, token)];
				for (reference in references) {
					if (reference == null || StringTools.trim(reference) == '')
						continue;
					var candidates = scriptCandidatesForToken(roots, path, reference, token);
					dependency(result, song, 'script-asset', reference, path, candidates);
				}
			}
		}
	}

	static function inspectImplementationScripts(result:ImportScanResult, song:ImportScanSong,
		candidates:Array<String>, roots:Array<String>):Void {
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (candidate in candidates) {
			if (!candidate.toLowerCase().endsWith('.hscript') || !file(candidate))
				continue;
			var key = pathKey(candidate);
			if (seen.exists(key))
				continue;
			seen.set(key, true);
			inspectScript(result, song, candidate, roots);
		}
	}

	/** Inspect HXC character definitions for their explicit spritePath. HXC
	 * files are executable data rather than JSON, so generic script token scans
	 * do not see this field; missing atlas diagnostics should still name the HXC
	 * file and every resolved image/XML location that was checked. */
	static function inspectImplementationHxcs(result:ImportScanResult, song:ImportScanSong,
		candidates:Array<String>, roots:Array<String>):Void {
		#if sys
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (candidate in candidates) {
			if (candidate == null || !candidate.toLowerCase().endsWith('.hxc') || !file(candidate))
				continue;
			var key = pathKey(candidate);
			if (seen.exists(key))
				continue;
			seen.set(key, true);
			var contents:String;
			try {
				contents = File.getContent(candidate);
			} catch (_:Dynamic) {
				continue;
			}
			for (line in contents.replace('\r\n', '\n').replace('\r', '\n').split('\n')) {
				if (line.toLowerCase().indexOf('spritepath') < 0)
					continue;
				var reference = extractQuotedAfter(line, 'spritePath');
				if (reference == null || StringTools.trim(reference) == '')
					continue;
				dependency(result, song, 'script-asset', reference, candidate,
					scriptCandidatesForToken(roots, candidate, reference, 'spritePath'));
			}
		}
		#end
	}

	static function inspectJsonValue(result:ImportScanResult, song:ImportScanSong, value:Dynamic,
		keyHint:String, path:String, roots:Array<String>):Void {
		if (value == null)
			return;
		if (Std.isOfType(value, String)) {
			var reference = StringTools.trim(Std.string(value));
			if (reference == '')
				return;
			var hint = keyHint == null ? '' : keyHint.toLowerCase();
			var lower = reference.toLowerCase();
			var assetLike = hint.indexOf('image') >= 0 || hint.indexOf('sprite') >= 0 || hint.indexOf('graphic') >= 0
				|| hint.indexOf('atlas') >= 0 || hint.indexOf('texture') >= 0 || hint.indexOf('portrait') >= 0
				|| hint.indexOf('icon') >= 0 || hint.indexOf('sound') >= 0 || hint.indexOf('music') >= 0
				|| hint.indexOf('video') >= 0 || lower.endsWith('.png') || lower.endsWith('.xml')
				|| lower.endsWith('.txt')
				|| lower.endsWith('.ogg') || lower.endsWith('.wav') || lower.endsWith('.mp3')
				|| lower.endsWith('.mp4') || lower.endsWith('.webm') || lower.startsWith('assets/');
			if (assetLike) {
				// Psych's `healthicon` field is a logical icon id.  Treating values
				// such as `dad` or `girl` as arbitrary JSON asset paths produced false
				// `json-asset` findings and obscured genuinely missing icons.
				var dependencyKind = hint == 'healthicon' || hint == 'health_icon' || hint == 'health-icon'
					? 'health-icon' : 'json-asset';
				dependency(result, song, dependencyKind, reference, path,
					scriptCandidatesForToken(roots, path, reference, keyHint));
			}
			return;
		}
		if (Std.isOfType(value, Array)) {
			for (item in (cast value:Array<Dynamic>))
				inspectJsonValue(result, song, item, keyHint, path, roots);
			return;
		}
		for (fieldName in Reflect.fields(value))
			inspectJsonValue(result, song, Reflect.field(value, fieldName), fieldName, path, roots);
	}

	static function inspectImplementationJsons(result:ImportScanResult, song:ImportScanSong,
		candidates:Array<String>, roots:Array<String>):Void {
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (candidate in candidates) {
			var lower = candidate.toLowerCase();
			if ((!lower.endsWith('.json') && !lower.endsWith('.jsonc')) || !file(candidate))
				continue;
			var key = pathKey(candidate);
			if (seen.exists(key))
				continue;
			seen.set(key, true);
			try {
				var parsed:Dynamic = CoolUtil.parseJson(File.getContent(candidate));
				inspectJsonValue(result, song, parsed, '', candidate, roots);
			} catch (_:Dynamic) {
				// The dependency itself is still reported; malformed implementation
				// JSON is an importer diagnostic, not a worker-thread failure.
				result.errors.push('Could not parse implementation JSON: ' + candidate);
			}
		}
	}

	/** Read the companion event payload which Psych/FPS Plus keeps beside the
	 * chart.  Its event names are needed for script diagnostics even when the
	 * chart itself has no embedded `events` array. */
	static function psychCompanionEvents(chartPath:String):Dynamic {
		#if sys
		var origin = Path.directory(chartPath);
		for (name in ['events.json', 'events.jsonc']) {
			var path = caseInsensitiveFile(origin, name);
			if (!file(path))
				continue;
			try {
				return CoolUtil.parseJson(File.getContent(path));
			} catch (_:Dynamic) {}
		}
		#end
		return null;
	}

	/** Inspect the exact Psych/Kade/FPS Lua scripts selected by the chart.  The
	 * runtime bridge is deliberately partial; exposing LuaCompat's stable codes
	 * in the scan report turns a later play-time parser failure into an actionable
	 * per-file diagnostic.  The same plan includes event names from events.json,
	 * so custom event scripts are no longer silently omitted from the audit. */
	static function inspectPsychLuaScripts(scanSong:ImportScanSong, chartPath:String, chart:Dynamic,
		roots:Array<String>):Void {
		#if sys
		if (scanSong == null || chartPath == null || roots == null || roots.length == 0)
			return;
		var songName = field(chart, 'song', Path.withoutDirectory(Path.directory(chartPath)));
		var companionEvents = psychCompanionEvents(chartPath);
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (root in roots) {
			var plan = PsychScriptDiscovery.discover(root, songName, chart, companionEvents, chartPath);
			if (plan == null || plan.scripts == null)
				continue;
			for (entry in plan.scripts) {
				if (entry == null || entry.path == null || !file(entry.path)
					|| !entry.path.toLowerCase().endsWith('.lua'))
					continue;
				var key = pathKey(entry.path);
				if (seen.exists(key))
					continue;
				seen.set(key, true);
				var diagnostics:Array<String> = luaDiagnosticCacheKnown.exists(key)
					? luaDiagnosticCache.get(key).copy() : null;
				if (diagnostics == null) {
					diagnostics = [];
					try {
						var translated = LuaCompat.translate(File.getContent(entry.path), entry.path, true);
						if (translated.diagnostics != null)
							for (diagnostic in translated.diagnostics)
								if (diagnostic != null)
								diagnostics.push(Std.string(diagnostic));
					} catch (error:Dynamic) {
						diagnostics.push('[lua-translate-error] ' + entry.path + ': ' + Std.string(error));
					}
					luaDiagnosticCacheKnown.set(key, true);
					luaDiagnosticCache.set(key, diagnostics.copy());
				}
				for (diagnostic in diagnostics)
					addSongDiagnostic(scanSong, diagnostic);
			}
		}
		#end
	}

	/** Find the Psych descriptor which owns this chart and ask its source tree
	 * whether the authored stage id is dispatched to a compiled Haxe class.  A
	 * donor class body cannot be imported as HScript, so that evidence must stay
	 * visible even when a same-named JSON or native visual alias exists. */
	static function psychSourceStageForChart(descriptors:Array<ImportRoot>, chartPath:String,
		stageName:String):Null<PsychCompiledStageSource> {
		if (descriptors == null || chartPath == null || stageName == null)
			return null;
		for (descriptor in descriptors) {
			if (descriptor == null || descriptor.engine != ImportEngine.PSYCH)
				continue;
			if (!pathWithin(chartPath, descriptor.data) && !pathWithin(chartPath, descriptor.contentRoot)
				&& !pathWithin(chartPath, descriptor.root))
				continue;
			var sourceRoot = descriptor.root;
			if (sourceRoot == null || StringTools.trim(sourceRoot) == '')
				sourceRoot = descriptor.contentRoot;
			var compiledStage = PsychSourceStageCompat.resolve(sourceRoot, stageName);
			if (compiledStage != null)
				return compiledStage;
		}
		return null;
	}

	static function chartBelongsToPsych(descriptors:Array<ImportRoot>, chartPath:String):Bool {
		if (descriptors == null || chartPath == null)
			return false;
		for (descriptor in descriptors) {
			if (descriptor == null || descriptor.engine != ImportEngine.PSYCH)
				continue;
			if (pathWithin(chartPath, descriptor.data) || pathWithin(chartPath, descriptor.contentRoot)
				|| pathWithin(chartPath, descriptor.root))
				return true;
		}
		return false;
	}

	/** Psych stage JSON supplies zoom/start-point metadata; it is not executable
	 * scene code (and stage JSON metadata does not implement the compiled stage class).
	 * Only a stage script can satisfy the source-engine implementation check. */
	static function psychStageImplementationFound(candidates:Array<String>):Bool {
		if (candidates == null)
			return false;
		for (candidate in candidates) {
			if (!file(candidate))
				continue;
			var lower = candidate.toLowerCase().replace('\\', '/');
			if (lower.endsWith('.lua') || lower.endsWith('.hscript') || lower.endsWith('.hxc'))
				return true;
		}
		return false;
	}

	static function chartBelongsToVSlice(descriptors:Array<ImportRoot>, chartPath:String):Bool {
		if (descriptors == null || chartPath == null)
			return false;
		for (descriptor in descriptors) {
			if (descriptor == null || descriptor.engine != ImportEngine.V_SLICE)
				continue;
			if (pathWithin(chartPath, descriptor.data) || pathWithin(chartPath, descriptor.contentRoot)
				|| pathWithin(chartPath, descriptor.root))
				return true;
		}
		return false;
	}

	static function chartBelongsToCodename(descriptors:Array<ImportRoot>, chartPath:String):Bool {
		if (descriptors == null || chartPath == null)
			return false;
		for (descriptor in descriptors) {
			if (descriptor == null || descriptor.engine != ImportEngine.CODENAME)
				continue;
			if (pathWithin(chartPath, descriptor.data) || pathWithin(chartPath, descriptor.contentRoot)
				|| pathWithin(chartPath, descriptor.root))
				return true;
		}
		return false;
	}

	static function vSliceDefinitionCandidateFound(candidates:Array<String>):Bool {
		if (candidates == null)
			return false;
		for (candidate in candidates) {
			if (candidate == null || !file(candidate))
				continue;
			var lower = candidate.toLowerCase().replace('\\', '/');
			if (lower.indexOf('/data/characters/') >= 0 || lower.indexOf('/data/stages/') >= 0
				|| lower.indexOf('/shared/characters/') >= 0 || lower.indexOf('/shared/stages/') >= 0)
				return true;
		}
		return false;
	}

	/** Codename keeps XML definitions under data/characters and data/stages;
		a candidate pointing at one of those XML files is a real dependency. */
	static function codenameDefinitionCandidateFound(candidates:Array<String>):Bool {
		if (candidates == null)
			return false;
		for (candidate in candidates) {
			if (candidate == null || !file(candidate))
				continue;
			var lower = candidate.toLowerCase().replace('\\', '/');
			if (!lower.endsWith('.xml'))
				continue;
			if (lower.indexOf('/data/characters/') >= 0 || lower.indexOf('/data/stages/') >= 0
				|| lower.indexOf('/shared/characters/') >= 0 || lower.indexOf('/shared/stages/') >= 0)
				return true;
		}
		return false;
	}

	static function addVSliceDependency(result:ImportScanResult, song:ImportScanSong, kind:String,
		reference:String, origin:String, candidates:Array<String>, found:Bool):Void {
		if (song == null || reference == null || StringTools.trim(reference) == ''
			|| reference.toLowerCase() == 'none' || reference.toLowerCase() == 'null')
			return;
		var key = kind + '|' + reference.toLowerCase();
		for (existing in song.dependencies)
			if (existing.kind + '|' + existing.reference.toLowerCase() == key)
				return;
		var item:ImportScanDependency = {
			kind: kind,
			reference: StringTools.trim(reference),
			found: found,
			searched: candidates == null ? [] : candidates,
			origin: origin
		};
		song.dependencies.push(item);
		if (!found) {
			song.missing.push(item);
			result.missingDependencies++;
		}
	}

	static function vSliceAssetDestination(kind:String, name:String, relative:String):String {
		if (kind == 'character')
			return Path.join(['assets', 'images', 'custom_chars', name, relative]);
		if (kind == 'ui')
			return Path.join(['assets', 'images', 'custom_ui', 'ui_packs', name, relative]);
		return Path.join(['assets', 'images', 'custom_stages', name, relative]);
	}

	static function addVSliceConversionAssets(result:ImportScanResult, songData:Dynamic,
		seen:Map<String, Bool>):Void {
		// Codename conversions share the V-Slice conversion shape and are
		// materialized by the same writer, so the scan report follows both.
		var conversionEngine = field(songData, 'engine', '');
		if (songData == null || (conversionEngine != ImportEngine.V_SLICE
			&& conversionEngine != ImportEngine.CODENAME))
			return;
		var addConversion = function(kind:String, name:String, conversion:Dynamic, source:String):Void {
			if (conversion == null || name == null || StringTools.trim(name) == '')
				return;
			var mappings:Dynamic = Reflect.field(conversion, 'assets');
			if (mappings != null && Std.isOfType(mappings, Array))
				for (mapping in (cast mappings:Array<Dynamic>)) {
					if (mapping == null || Reflect.field(mapping, 'supported') != true)
						continue;
					var relative = field(mapping, 'destination', '');
					var destination = vSliceAssetDestination(kind, name, relative);
					var sourcePath = field(mapping, 'source', source);
					var key = pathKey(destination);
					if (seen.exists(key))
						continue;
					seen.set(key, true);
						// V-Slice conversion destinations use deterministic casing, but a
						// prior Windows import may have materialized the same file with a
						// different case. Match the writer's non-overwrite decision here so
						// the scan does not claim a TXT companion is new when it will skip it.
						var duplicate = exists(caseInsensitivePath(destination));
					result.assets.push({
						kind: 'v-slice-' + kind,
						name: name + '/' + relative,
						source: sourcePath,
						destination: destination,
						duplicate: duplicate,
						reason: duplicate ? 'destination already exists' : 'new generated mapping'
					});
					result.assetFilesFound++;
					if (duplicate)
						result.duplicateAssets++;
					else
						result.assetsToImport++;
				}
			var hscript = field(conversion, 'hscript', '');
			if (hscript != '' && (kind == 'character' || kind == 'stage')) {
				var scriptDestination = kind == 'character'
					? Path.join(['assets', 'images', 'custom_chars', name + '.hscript'])
					: Path.join(['assets', 'images', 'custom_stages', name + '.hscript']);
				var scriptKey = pathKey(scriptDestination);
				if (!seen.exists(scriptKey)) {
					seen.set(scriptKey, true);
					var scriptDuplicate = exists(scriptDestination);
					result.assets.push({
						kind: 'v-slice-' + kind + '-hscript',
						name: name + '.hscript',
						source: source + ' (generated)',
						destination: scriptDestination,
						duplicate: scriptDuplicate,
						reason: scriptDuplicate ? 'destination already exists' : 'generated HScript'
					});
					result.assetFilesFound++;
					if (scriptDuplicate)
						result.duplicateAssets++;
					else
						result.assetsToImport++;
				}
			}
		};
		var characters:Dynamic = Reflect.field(songData, 'convertedCharacters');
		if (characters != null && Std.isOfType(characters, Array))
			for (item in (cast characters:Array<Dynamic>)) {
				if (item == null)
					continue;
				var conversion:Dynamic = Reflect.field(item, 'conversion');
				addConversion('character', field(conversion, 'name', ''), conversion,
					field(item, 'source', field(songData, 'vSliceRoot', result.source)));
			}
		var stageImport:Dynamic = Reflect.field(songData, 'convertedStage');
		if (stageImport != null) {
			var stageConversion:Dynamic = Reflect.field(stageImport, 'conversion');
			addConversion('stage', field(stageConversion, 'name', ''), stageConversion,
				field(stageImport, 'source', field(songData, 'vSliceRoot', result.source)));
		}
		var noteStyleImport:Dynamic = Reflect.field(songData, 'convertedNoteStyle');
		if (noteStyleImport != null) {
			var noteStyleConversion:Dynamic = Reflect.field(noteStyleImport, 'conversion');
			var noteStyleName = field(noteStyleConversion, 'name', '');
			var noteStyleSource = field(noteStyleImport, 'source', field(songData, 'vSliceRoot', result.source));
			addConversion('ui', noteStyleName, noteStyleConversion, noteStyleSource);
			if (noteStyleName != '' && noteStyleConversion != null
				&& Reflect.field(noteStyleConversion, 'supported') == true) {
				var presetDestination = Path.join(['assets', 'images', 'custom_ui', 'ui_packs', noteStyleName,
					'multiNotePresets.json']);
				var presetKey = pathKey(presetDestination);
				if (!seen.exists(presetKey)) {
					seen.set(presetKey, true);
					var presetDuplicate = exists(caseInsensitivePath(presetDestination));
					result.assets.push({
						kind: 'v-slice-ui-preset',
						name: noteStyleName + '/multiNotePresets.json',
						source: noteStyleSource + ' (generated)',
						destination: presetDestination,
						duplicate: presetDuplicate,
						reason: presetDuplicate ? 'destination already exists' : 'generated note-style preset'
					});
					result.assetFilesFound++;
					if (presetDuplicate)
						result.duplicateAssets++;
					else
						result.assetsToImport++;
				}
				var registryDestination = 'assets/images/custom_ui/ui_packs/ui.json';
				var registryKey = pathKey(registryDestination) + '|' + noteStyleName.toLowerCase();
				if (!seen.exists(registryKey)) {
					seen.set(registryKey, true);
					var registryDuplicate = exists(caseInsensitivePath(registryDestination));
					result.assets.push({
						kind: 'v-slice-ui-registry',
						name: noteStyleName,
						source: noteStyleSource + ' (generated)',
						destination: registryDestination,
						duplicate: registryDuplicate,
						reason: registryDuplicate ? 'destination registry will be merged' : 'generated registry entry'
					});
					result.assetFilesFound++;
					if (registryDuplicate)
						result.duplicateAssets++;
					else
						result.assetsToImport++;
				}
			}
		}
	}

	static function inspectChart(result:ImportScanResult, scanSong:ImportScanSong, chartPath:String,
		descriptors:Array<ImportRoot>, ?chartOverride:Dynamic,
		?convertedPeers:Array<ImportVisualChart>, ?plannedSong:Dynamic):Void {
		var roots = dependencyRootsForChart(descriptors, chartPath);
		var dependencyRoots = dependencyRootsWithDestination(roots,
			result != null && ImportEngine.isAuto(result.importType) ? descriptors : null);
		// V-Slice discovery already converted its non-native chart in memory.
		// Never feed the original metadata/chart pair back through the native
		// `{song:{...}}` parser: it would create a false parse warning and lose
		// the converted character/stage dependencies from the scan report.
		var chart = chartOverride == null ? readChart(chartPath) : chartOverride;
		if (chartOverride != null && Reflect.field(chartOverride, 'song') != null)
			chart = Reflect.field(chartOverride, 'song');
		if (chart == null) {
			addError(result, 'Could not parse chart: ' + chartPath);
			return;
		}
		chart = resolveVisualChartFallback(chartPath, chart, dependencyRoots, scanSong, convertedPeers);
		var originDir = Path.directory(chartPath);
		var p1 = field(chart, 'player1', 'bf');
		var p2 = field(chart, 'player2', 'dad');
		// Psych's chart schema calls the same dependency `gfVersion`; preserve
		// that authored character when inspecting a chart before conversion.
		var gf = field(chart, 'gf', field(chart, 'gfVersion', 'gf'));
		var stage = field(chart, 'stage', 'stage');
		var ui = field(chart, 'uiType', 'normal');
		var layout = field(chart, 'forceLayout', field(chart, 'uiLayoutType', ''));
		var cutscene = field(chart, 'cutsceneType', 'none');
		var isVSlice = chartBelongsToVSlice(descriptors, chartPath);
		var isPsych = chartBelongsToPsych(descriptors, chartPath);
		var compiledPsychStage = isPsych ? psychSourceStageForChart(descriptors, chartPath, stage) : null;
		// A converted Codename chart names ids the importer materializes from
		// the donor's XML definitions in the same transaction, so the scan must
		// resolve them against those definitions instead of the destination
		// registry (which does not hold them yet).
		var isCodename = chartBelongsToCodename(descriptors, chartPath);
		var p1Candidates = charCandidates(roots, p1);
		var p2Candidates = charCandidates(roots, p2);
		var gfCandidates = charCandidates(roots, gf);
		// Kade/FPS/legacy builds sometimes compile their Character definitions
		// into the donor executable while retaining a usable Sparrow atlas in a
		// library folder.  Keep this lookup scoped to the descriptor owning the
		// chart; never use the selected parent as a global asset pool.
		var atlasRoots = result != null && ImportEngine.isAuto(result.importType) ? dependencyRoots : roots;
		var p1Atlas:LegacyCharacterAtlasResult = null;
		var p2Atlas:LegacyCharacterAtlasResult = null;
		var gfAtlas:LegacyCharacterAtlasResult = null;
		if (!isVSlice && legacyCharacterAtlasNeeded(atlasRoots, p1, p1Candidates))
			p1Atlas = legacyCharacterAtlas(atlasRoots, p1, 'player');
		if (!isVSlice && legacyCharacterAtlasNeeded(atlasRoots, p2, p2Candidates))
			p2Atlas = legacyCharacterAtlas(atlasRoots, p2, 'opponent');
		if (!isVSlice && legacyCharacterAtlasNeeded(atlasRoots, gf, gfCandidates))
			gfAtlas = legacyCharacterAtlas(atlasRoots, gf, 'gf');
		appendLegacyAtlasCandidates(p1Candidates, p1Atlas);
		appendLegacyAtlasCandidates(p2Candidates, p2Atlas);
		appendLegacyAtlasCandidates(gfCandidates, gfAtlas);
		appendLegacyAtlasDiagnostics(scanSong, p1Atlas);
		appendLegacyAtlasDiagnostics(scanSong, p2Atlas);
		appendLegacyAtlasDiagnostics(scanSong, gfAtlas);
		var stageCandidatesForChart = stageCandidates(roots, stage);
		var implementationRoots = roots.copy();
		var installedProviders:Array<Dynamic> = plannedSong == null ? null
			: Reflect.field(plannedSong, 'installedDependencyRoots');
		if (installedProviders != null)
			for (provider in installedProviders) if (provider != null) {
				// These are receipt-proven base owners, never an all-mods asset pool.
				uniquePush(implementationRoots, provider.owner);
				uniquePush(dependencyRoots, provider.owner);
				for (candidate in stageCandidates([provider.owner], stage))
					uniquePush(stageCandidatesForChart, candidate);
			}
		var psychStageCandidates = stageCandidatesForChart.copy();
		if (compiledPsychStage != null) {
			uniquePush(psychStageCandidates, compiledPsychStage.sourcePath);
			uniquePush(psychStageCandidates, compiledPsychStage.dispatchPath);
		}
		var uiCandidatesForChart = uiCandidates(roots, ui);
		var cutsceneCandidatesForChart = cutsceneCandidates(roots, cutscene);
		// The chart may rely on a built-in/native destination entry. Keep the
		// donor-only arrays above for implementation-script inspection, then add
		// the destination registry scope only to dependency resolution. In Auto,
		// dependencyRoots also contains the other bounded roots discovered under
		// the selected source folder.
		// Registry validation already proves both the alias and its concrete
		// implementation. Avoid expanding every possible character path across
		// every Auto sibling in that common case; on large mounted packs that was
		// quadratic metadata work. Unregistered/HXC/Psych definitions still use
		// the complete bounded sibling search below.
		var p1RegistryFound = characterRegistryVisualFound(dependencyRoots, p1);
		var p2RegistryFound = characterRegistryVisualFound(dependencyRoots, p2);
		var gfRegistryFound = characterRegistryVisualFound(dependencyRoots, gf);
		var p1DependencyCandidates = p1RegistryFound ? p1Candidates.copy() : charCandidates(dependencyRoots, p1);
		var p2DependencyCandidates = p2RegistryFound ? p2Candidates.copy() : charCandidates(dependencyRoots, p2);
		var gfDependencyCandidates = gfRegistryFound ? gfCandidates.copy() : charCandidates(dependencyRoots, gf);
		appendLegacyAtlasCandidates(p1DependencyCandidates, p1Atlas);
		appendLegacyAtlasCandidates(p2DependencyCandidates, p2Atlas);
		appendLegacyAtlasCandidates(gfDependencyCandidates, gfAtlas);
		var stageDependencyCandidates = stageCandidates(dependencyRoots, stage);
		var uiDependencyCandidates = uiCandidates(dependencyRoots, ui);
		var cutsceneDependencyCandidates = cutsceneCandidates(dependencyRoots, cutscene);
		var layoutDependencyCandidates = layoutCandidates(dependencyRoots, layout);
		// A supported V-Slice note style is converted into a destination UI pack
		// during the later import transaction. It is therefore a planned
		// dependency, not a pre-existing registry entry. Count only the exact
		// generated id as satisfied; unsupported or unrelated styles remain
		// visible as missing dependencies.
		var plannedUiFound = false;
		if (isVSlice && plannedSong != null) {
			var plannedStyle:Dynamic = Reflect.field(plannedSong, 'convertedNoteStyle');
			var plannedConversion:Dynamic = plannedStyle == null ? null : Reflect.field(plannedStyle, 'conversion');
			var plannedName = field(plannedConversion, 'name', '');
			plannedUiFound = plannedConversion != null && Reflect.field(plannedConversion, 'supported') == true
				&& plannedName != '' && plannedName.toLowerCase() == ui.toLowerCase();
		}
		dependency(result, scanSong, 'character', p1, chartPath, p1DependencyCandidates,
			p1RegistryFound
				|| (isVSlice && vSliceDefinitionCandidateFound(p1Candidates))
				|| (isCodename && codenameDefinitionCandidateFound(p1Candidates))
				|| (p1Atlas != null && p1Atlas.recoverable));
		dependency(result, scanSong, 'character', p2, chartPath, p2DependencyCandidates,
			p2RegistryFound
				|| (isVSlice && vSliceDefinitionCandidateFound(p2Candidates))
				|| (isCodename && codenameDefinitionCandidateFound(p2Candidates))
				|| (p2Atlas != null && p2Atlas.recoverable));
		dependency(result, scanSong, 'character', gf, chartPath, gfDependencyCandidates,
			gfRegistryFound
				|| (isVSlice && vSliceDefinitionCandidateFound(gfCandidates))
				|| (isCodename && codenameDefinitionCandidateFound(gfCandidates))
				|| (gfAtlas != null && gfAtlas.recoverable));
		var psychStageScriptFound = isPsych && psychStageImplementationFound(stageCandidatesForChart);
		var compiledPsychStageUnsupported = compiledPsychStage != null;
		// A native destination alias is a visual fallback, not evidence that a
		// Psych source stage implementation was imported. Keep Psych checks scoped
		// to the selected donor root's scripts; native built-ins still resolve by
		// their explicit engine-owned mapping in dependency().
		var psychStageHasNoImplementation = isPsych && !psychStageScriptFound
			&& !EngineCompat.isBuiltinStageReference(stage);
		var stageForceMissing = compiledPsychStageUnsupported || psychStageHasNoImplementation;
		var stageClassification = compiledPsychStageUnsupported ? 'unsupported-engine-behavior' : null;
		var stageImpact = compiledPsychStageUnsupported
			? 'compiled Psych stage class ' + compiledPsychStage.className
				+ ' is not executed; native visual fallback is not equivalent for its props, effects, callbacks, or lifecycle'
			: (psychStageHasNoImplementation
				? 'Psych stage metadata may set camera and character positions, but stage visuals and callbacks remain unavailable'
				: null);
		var stageOrigin = compiledPsychStageUnsupported
			? chartPath + ' -> Psych compiled class ' + compiledPsychStage.className + ' (' + compiledPsychStage.sourcePath + ')'
			: chartPath;
		dependency(result, scanSong, 'stage', stage, stageOrigin,
			isPsych ? psychStageCandidates : stageDependencyCandidates,
			(isVSlice || isCodename)
				&& (vSliceDefinitionCandidateFound(stageCandidatesForChart)
					|| codenameDefinitionCandidateFound(stageCandidatesForChart)),
			stageForceMissing, stageClassification, stageImpact);
		dependency(result, scanSong, 'ui', ui, chartPath, uiDependencyCandidates, plannedUiFound);
		if (layout.toLowerCase() != 'none' && layout.toLowerCase() != 'normal')
			dependency(result, scanSong, 'layout', layout, chartPath, layoutDependencyCandidates);
		dependency(result, scanSong, 'cutscene', cutscene, chartPath, cutsceneDependencyCandidates);
		inspectImplementationScripts(result, scanSong, p1Candidates, roots);
		inspectImplementationScripts(result, scanSong, p2Candidates, roots);
		inspectImplementationScripts(result, scanSong, gfCandidates, roots);
		inspectImplementationScripts(result, scanSong, stageCandidatesForChart, implementationRoots);
		inspectImplementationScripts(result, scanSong, cutsceneCandidatesForChart, roots);
		inspectImplementationHxcs(result, scanSong, p1Candidates, dependencyRoots);
		inspectImplementationHxcs(result, scanSong, p2Candidates, dependencyRoots);
		inspectImplementationHxcs(result, scanSong, gfCandidates, dependencyRoots);
		inspectImplementationHxcs(result, scanSong, stageCandidatesForChart, dependencyRoots);
		inspectImplementationHxcs(result, scanSong, cutsceneCandidatesForChart, dependencyRoots);
		inspectImplementationJsons(result, scanSong, p1Candidates, roots);
		inspectImplementationJsons(result, scanSong, p2Candidates, roots);
		inspectImplementationJsons(result, scanSong, gfCandidates, roots);
		inspectImplementationJsons(result, scanSong, stageCandidatesForChart, implementationRoots);
		inspectImplementationJsons(result, scanSong, cutsceneCandidatesForChart, roots);

		var siblingScripts:Array<String> = [];
		if (directory(originDir)) {
			try {
				for (entry in FileSystem.readDirectory(originDir)) {
					if (entry.toLowerCase().endsWith('.hscript'))
						uniquePush(siblingScripts, Path.join([originDir, entry]));
				}
			} catch (_:Dynamic) {}
		}
		for (script in siblingScripts)
			inspectScript(result, scanSong, script, roots);
		inspectPsychLuaScripts(scanSong, chartPath, chart, roots);
	}

	static function addRegistryAssets(result:ImportScanResult, descriptors:Array<ImportRoot>):Void {
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (descriptor in descriptors) {
			if (ModuleFunctions.importWorkCancelled())
				return;
			// V-Slice and Codename media are not native asset trees.  Only the
			// explicit conversion mappings attached to each song are importable.
			if (descriptor != null && (descriptor.engine == ImportEngine.V_SLICE
				|| descriptor.engine == ImportEngine.CODENAME))
				continue;
			var root = descriptor == null ? '' : descriptor.contentRoot;
			if (root == null || StringTools.trim(root) == '')
				root = descriptor == null ? '' : descriptor.root;
			if (root == null || StringTools.trim(root) == '')
				continue;
			var definitions:Array<{kind:String, relative:String, folder:String}> = [
				{kind:'character', relative:'images/custom_chars', folder:'images/custom_chars'},
				{kind:'stage', relative:'images/custom_stages', folder:'images/custom_stages'},
				{kind:'cutscene', relative:'images/custom_cutscenes', folder:'images/custom_cutscenes'},
				{kind:'ui', relative:'images/custom_ui', folder:'images/custom_ui'}
			];
			for (definition in definitions) {
				if (ModuleFunctions.importWorkCancelled())
					return;
				var base = Path.join([root, definition.relative]);
				if (!directory(base))
					continue;
				var entries:Array<String>;
				try {
					entries = FileSystem.readDirectory(base);
				} catch (_:Dynamic) {
					continue;
				}
				for (entry in entries) {
					if (ModuleFunctions.importWorkCancelled())
						return;
					ModuleFunctions.yieldImportWork();
					var candidate = Path.join([base, entry]);
					if (!directory(candidate) && !file(candidate))
						continue;
					var key = pathKey(candidate);
					if (seen.exists(key))
						continue;
					seen.set(key, true);
					var destination = Path.join(['assets', definition.folder, entry]);
					var duplicate = exists(destination);
					result.assets.push({
						kind: definition.kind,
						name: entry,
						source: candidate,
						destination: destination,
						duplicate: duplicate,
						reason: duplicate ? 'destination already exists' : 'new asset'
					});
				}
			}
		}
	}

	/** Count ordinary asset files without retaining one giant detail row per
	 * image/audio/video.  The importer copies these trees too, so including them
	 * in the plan denominator prevents the progress bar from reaching 100% while
	 * a large media tree is still being copied. */
	static function addGenericAssetCounts(result:ImportScanResult, descriptors:Array<ImportRoot>):Void {
		var excluded:Map<String, Bool> = new Map<String, Bool>();
		for (name in ['data', 'songs', 'scripts', 'stages', 'custom_events', 'custom_notetypes', 'plugins',
			'.git', '.tools', '.haxelib', 'node_modules', 'bin', 'cache'])
			excluded.set(name, true);
		for (descriptor in descriptors) {
			if (ModuleFunctions.importWorkCancelled())
				return;
			var isVSlice = descriptor != null && descriptor.engine == ImportEngine.V_SLICE;
			// Codename media is copied only through the per-song conversion
			// mappings, so counting its whole tree would promise work the
			// importer never performs.
			var isCodename = descriptor != null && descriptor.engine == ImportEngine.CODENAME;
			var root = descriptor == null ? '' : descriptor.contentRoot;
			if (root == null || StringTools.trim(root) == '')
				root = descriptor == null ? '' : descriptor.root;
			if (root == null || StringTools.trim(root) == '')
				continue;
			var queue:Array<{path:String, relative:String, depth:Int}> = [];
			if (isVSlice) {
				// Match ModuleFunctions.mergeVSliceRuntimeAssets: count only ordinary
				// media trees copied directly.  Foreign script trees are counted by
				// their destination namespace and selected through compatScripts.json.
				var roots = [root];
				var shared = Path.join([root, 'shared']);
				if (directory(shared))
					roots.push(shared);
				for (runtimeRoot in roots)
					for (entry in ['sounds', 'music', 'videos', 'fonts', 'shaders']) {
						var child = Path.join([runtimeRoot, entry]);
						if (directory(child))
							queue.push({path: child, relative: entry, depth: 0});
					}
			} else {
				var entries:Array<String>;
				try {
					entries = FileSystem.readDirectory(root);
				} catch (_:Dynamic) {
					continue;
				}
				for (entry in entries) {
					if (!validEntryName(entry) || excluded.exists(entry.toLowerCase()))
						continue;
					var child = Path.join([root, entry]);
					if (directory(child))
						queue.push({path: child, relative: entry, depth: 0});
				}
			}
			var cursor = 0;
			var scannedDirectories = 0;
			if (isCodename) {
				// Keep the plan honest: only the bounded conversion assets below
				// belong to this root, so no generic media rows are counted.
				continue;
			}
			while (cursor < queue.length && scannedDirectories < MAX_DIRECTORY_SCAN
				&& result.assetFilesFound < MAX_GENERIC_ASSET_FILES) {
				if (ModuleFunctions.importWorkCancelled())
					return;
				var item = queue[cursor++];
				scannedDirectories++;
				ModuleFunctions.yieldImportWork();
				ModuleFunctions.reportImportProgress('scan-assets', item.path, scannedDirectories, 0);
				var children:Array<String>;
				try {
					children = FileSystem.readDirectory(item.path);
				} catch (_:Dynamic) {
					continue;
				}
				for (entry in children) {
					if (!validEntryName(entry))
						continue;
					if (ModuleFunctions.importWorkCancelled())
						return;
					var child = Path.join([item.path, entry]);
					var relative = Path.join([item.relative, entry]);
					if (directory(child)) {
						if (item.depth < 10)
							queue.push({path: child, relative: relative, depth: item.depth + 1});
						continue;
					}
					if (!file(child))
						continue;
					var destination = Path.join(['assets', relative]);
					result.assetFilesFound++;
					if (exists(destination))
						result.duplicateAssets++;
					else
						result.assetsToImport++;
					if (result.assetFilesFound % 32 == 0)
						ModuleFunctions.yieldImportWork();
					if (result.assetFilesFound % 32 == 0)
						ModuleFunctions.reportImportProgress('scan-assets', child, result.assetFilesFound, 0);
				}
			}
		}
		if (result.assetFilesFound >= MAX_GENERIC_ASSET_FILES)
			addError(result, 'The source has more than ' + MAX_GENERIC_ASSET_FILES + ' ordinary asset files; the count is capped for responsiveness.');
	}

	static function validEntryName(name:String):Bool {
		return name != null && name != '' && name != '.' && name != '..'
			&& name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf(':') < 0
			&& name.indexOf('\u0000') < 0;
	}

	public static function writeReport(result:ImportScanResult, ?importSummary:String):Void {
		if (result == null)
			return;
		var lines:Array<String> = [];
		lines.push('CammieEngine import report');
		lines.push('Generated: ' + Date.now().toString());
		lines.push('Source: ' + result.source);
		lines.push('Importer type: ' + ImportSettings.normalizeType(result.importType));
		if (result.detectedRoots != null)
			for (root in result.detectedRoots) {
				if (root == null)
					continue;
				lines.push('Detected root: ' + root.path + ' [' + root.engine + ']'
					+ (root.confidence <= 0 ? '' : ' (confidence ' + root.confidence + ')'));
				if (root.reason != null && root.reason != '')
					lines.push('  Detection: ' + root.reason);
				if (root.evidence != null)
					for (evidence in root.evidence)
						if (evidence != null && evidence != '')
							lines.push('  Evidence: ' + evidence);
			}
		if (result.detectedEngines != null && result.detectedEngines.length > 0)
			lines.push('Detected engines: ' + result.detectedEngines.join(', '));
		if (result.rootDirectoriesScanned != null) {
			var rootLimit = result.rootDirectoryLimit == null ? ImportRootScanner.MAX_DIRECTORIES : result.rootDirectoryLimit;
			var rootQueued = result.rootDirectoriesQueued == null ? 0 : result.rootDirectoriesQueued;
			lines.push('Root directories scanned: ' + result.rootDirectoriesScanned + '/' + rootLimit
				+ (result.rootScanTruncated == true ? ' (TRUNCATED; ' + rootQueued + ' queued, unvisited)' : ''));
		}
		if (result.rootScanDiagnostics != null)
			for (diagnostic in result.rootScanDiagnostics) {
				if (diagnostic == null)
					continue;
				lines.push('[ROOT SCAN ' + (diagnostic.severity == null ? 'DIAGNOSTIC' : diagnostic.severity.toUpperCase())
					+ '] ' + diagnostic.code + ': ' + diagnostic.message);
			}
		if (result.packageDirectoriesScanned != null) {
			var packageLimit = result.packageDirectoryLimit == null
				? ModuleFunctions.MAX_IMPORT_DISCOVERY_DIRECTORIES : result.packageDirectoryLimit;
			var packageQueued = result.packageDirectoriesQueued == null ? 0 : result.packageDirectoriesQueued;
			lines.push('Package directories scanned: ' + result.packageDirectoriesScanned + '/' + packageLimit
				+ (result.packageScanTruncated == true ? ' (TRUNCATED; ' + packageQueued + ' queued, unvisited)' : ''));
		}
		if (result.packageScanDiagnostics != null)
			for (diagnostic in result.packageScanDiagnostics) {
				if (diagnostic == null)
					continue;
				lines.push('[PACKAGE SCAN ' + (diagnostic.severity == null ? 'DIAGNOSTIC' : diagnostic.severity.toUpperCase())
					+ '] ' + diagnostic.code + ': ' + diagnostic.message);
			}
		var rejectedSongCount = result.rejectedSongCount == null
			? (result.rejectedSongs == null ? 0 : result.rejectedSongs.length) : result.rejectedSongCount;
		if (rejectedSongCount > 0) {
			lines.push('Rejected song candidates: ' + rejectedSongCount
				+ (result.rejectedSongsTruncated == true ? ' (details truncated)' : ''));
			if (result.rejectedSongs != null)
				for (rejection in result.rejectedSongs) {
					if (rejection == null)
						continue;
					lines.push('[SONG REJECTED ' + rejection.code + '] ' + rejection.song
						+ (rejection.engine == null || StringTools.trim(rejection.engine) == ''
							? '' : ' [' + rejection.engine + ']'));
					if (rejection.sourceRoot != null && StringTools.trim(rejection.sourceRoot) != '')
						lines.push('  Source root: ' + rejection.sourceRoot);
					if (rejection.sourcePath != null && StringTools.trim(rejection.sourcePath) != '')
						lines.push('  Source chart folder: ' + rejection.sourcePath);
					lines.push('  Reason: ' + rejection.reason);
					if (rejection.charts != null)
						for (chart in rejection.charts)
							lines.push('  Chart: ' + chart);
					if (rejection.chartsTruncated == true)
						lines.push('  Chart list truncated.');
				}
		}
		if ((result.overlayPlanned != null && result.overlayPlanned > 0)
			|| (result.overlayDiagnostics != null && result.overlayDiagnostics.length > 0)) {
			lines.push('');
			lines.push('Overlay operations planned: ' + result.overlayPlanned);
			if (result.overlayProvenance != null)
				for (provenance in result.overlayProvenance)
					lines.push('  Provenance: ' + provenance);
			if (result.overlayDiagnostics != null)
				for (diagnostic in result.overlayDiagnostics)
					lines.push('  [OVERLAY] ' + diagnostic);
		}
		lines.push('');
		lines.push('Songs found: ' + result.songsFound);
		lines.push('Songs to import: ' + result.songsToImport);
		lines.push('Duplicate songs (not moved): ' + result.duplicateSongs);
		lines.push('Charts: ' + result.chartsFound);
		lines.push('Characters referenced: ' + result.charactersFound);
		lines.push('Stages referenced: ' + result.stagesFound);
		lines.push('UI packs referenced: ' + result.uiPacksFound);
		lines.push('Layouts referenced: ' + result.layoutsFound);
		lines.push('Cutscenes referenced: ' + result.cutscenesFound);
		lines.push('Scripts inspected: ' + result.scriptsFound);
		lines.push('Other importable assets: ' + result.assetFilesFound);
		lines.push('Other assets to import: ' + result.assetsToImport);
		lines.push('Other duplicate assets (not moved): ' + result.duplicateAssets);
		lines.push('Missing dependencies: ' + result.missingDependencies);
		if (importSummary != null) {
			lines.push('');
			lines.push('Import result: ' + importSummary);
		}
		for (song in result.songs) {
			lines.push('');
			lines.push('[SONG] ' + song.name + (song.duplicate ? ' - DUPLICATE (not moved)' : ' - queued for import'));
			lines.push('  Reason: ' + song.reason);
			if (song.source != null && StringTools.trim(song.source) != '')
				lines.push('  Candidate source: ' + song.source);
			for (chart in song.charts)
				lines.push('  Chart: ' + chart);
			if (song.diagnostics != null)
				for (diagnostic in song.diagnostics)
					lines.push('  ' + ImportDiagnostic.label(diagnostic) + ' ' + diagnostic);
			for (item in song.dependencies) {
				lines.push('  ' + (item.found ? '[OK] ' : '[MISSING] ') + item.kind + ' "' + item.reference + '"');
				lines.push('    Origin: ' + item.origin);
				lines.push('    Searched:');
				for (searched in item.searched)
					lines.push('      ' + searched);
			}
		}
		for (asset in result.assets)
			lines.push('[ASSET] ' + asset.kind + ' ' + asset.name + (asset.duplicate ? ' - DUPLICATE (not moved)' : ' - queued for import')
				+ '\n  Source: ' + asset.source + '\n  Destination: ' + asset.destination);
		for (error in result.errors)
			lines.push('[ERROR] ' + error);
		try {
			ensureDirectory(Path.directory(result.logPath));
			File.saveContent(result.logPath, lines.join('\n') + '\n');
		} catch (error:Dynamic) {
			// A read-only AppImage is allowed to complete the scan; surface the
			// reason in the in-memory result instead of failing the import.
			result.errors.push('Could not write import report: ' + Std.string(error));
		}
	}

	public static function perform(sourcePath:String, ?importType:String):ImportScanResult {
		LegacyCharacterAtlasImporter.clearCache();
		clearResolutionCaches();
		var source = normalized(sourcePath);
		var selectedType = ImportSettings.normalizeType(importType);
		var result = makeResult(source, selectedType);
		if (source == '' || !directory(source)) {
			addError(result, 'The selected source folder does not exist: ' + source);
			writeReport(result);
			return result;
		}
		if (!ModuleFunctions.isSafeImportSource(source)) {
			addError(result, 'The current game assets cannot be used as an import source: ' + source);
			writeReport(result);
			return result;
		}
		var scannerCallbacks:ImportRootScanCallbacks = {
			onProgress: function(progress:ImportRootScanProgress):Void {
				if (progress != null)
					ModuleFunctions.reportImportProgress(progress.phase, progress.current, progress.completed, progress.total);
			},
			isCancelled: function():Bool {
				return ModuleFunctions.importWorkCancelled();
			}
		};
		// ImportRootScanner.scan(source, selectedType, scannerCallbacks) remains
		// the compatibility API; the workflow uses the detailed sibling so a
		// capped Auto walk can be surfaced to the report and Import Settings UI.
		var rootScan:ImportRootScanResult = ImportRootScanner.scanDetailed(source, selectedType, scannerCallbacks);
		var scannedDescriptors:Array<ImportRoot> = rootScan == null || rootScan.roots == null ? [] : rootScan.roots;
		if (rootScan != null) {
			result.rootScanDiagnostics = rootScan.diagnostics == null ? [] : rootScan.diagnostics.copy();
			result.rootScanTruncated = rootScan.truncated;
			result.rootDirectoriesScanned = rootScan.scannedDirectories;
			result.rootDirectoryLimit = rootScan.directoryLimit;
			result.rootDirectoriesQueued = rootScan.queuedDirectories;
			if (rootScan.diagnostics != null)
				for (diagnostic in rootScan.diagnostics)
					if (diagnostic != null && diagnostic.severity != null
						&& diagnostic.severity.toLowerCase() == 'error')
						addError(result, diagnostic.message);
		}
		// The scanner intentionally reports every engine-shaped root so the
		// detector remains useful for broad selections.  Before building the
		// donor plan, remove this checkout's own assets root; otherwise the report
		// would count destination charts/assets as if they were import candidates.
		var descriptors:Array<ImportRoot> = [];
		for (descriptor in scannedDescriptors)
			if (ModuleFunctions.isUsableImportRoot(descriptor))
				descriptors.push(descriptor);
		var overlayMounts = ModuleFunctions.planImportOverlays(descriptors);
		result.overlayMounts = overlayMounts;
		var overlaySummary = ImportOverlayRuntime.summarize(overlayMounts);
		result.overlayPlanned = overlaySummary.planned;
		result.overlayDiagnostics = overlaySummary.diagnostics == null ? [] : overlaySummary.diagnostics.copy();
		result.overlayProvenance = overlaySummary.provenance == null ? [] : overlaySummary.provenance.copy();
		var descriptorEngines:Map<String, Bool> = new Map<String, Bool>();
		if (result.detectedRoots != null)
			for (descriptor in descriptors) {
				if (descriptor == null)
					continue;
				var evidence = descriptor.evidence == null ? [] : descriptor.evidence.copy();
				result.detectedRoots.push({
					path: descriptor.root,
					root: descriptor.root,
					contentRoot: descriptor.contentRoot,
					data: descriptor.data,
					engine: descriptor.engine,
					confidence: descriptor.confidence,
					evidence: evidence,
					reason: evidence.length == 0 ? 'Engine selected from root layout.' : evidence.join('; ')
				});
				if (descriptor.engine != null && StringTools.trim(descriptor.engine) != '')
					descriptorEngines.set(descriptor.engine, true);
			}
		if (result.detectedEngines != null)
			for (engine in descriptorEngines.keys())
				result.detectedEngines.push(engine);
		if (ModuleFunctions.importWorkCancelled()) {
			addError(result, 'Scan cancelled by the user.');
			writeReport(result);
			return result;
		}
		var discovered:Array<Dynamic>;
		try {
			var discovery:SongImportDiscoveryResult = ModuleFunctions.discoverSongImportsDetailed(source, null,
				selectedType, descriptors);
			discovered = discovery == null || discovery.songs == null ? [] : cast discovery.songs;
			var packageScan = discovery == null ? null : discovery.packageDiscovery;
			if (discovery != null) {
				result.rejectedSongs = discovery.rejectedSongs == null ? [] : discovery.rejectedSongs.copy();
				result.rejectedSongCount = discovery.rejectedSongCount == null
					? result.rejectedSongs.length : discovery.rejectedSongCount;
				result.rejectedSongsTruncated = discovery.rejectedSongsTruncated == true;
			}
			if (packageScan != null) {
				result.packageScanDiagnostics = packageScan.diagnostics == null ? [] : packageScan.diagnostics.copy();
				result.packageScanTruncated = packageScan.truncated;
				result.packageDirectoriesScanned = packageScan.scannedDirectories;
				result.packageDirectoryLimit = packageScan.directoryLimit;
				result.packageDirectoriesQueued = packageScan.queuedDirectories;
				if (packageScan.diagnostics != null)
					for (diagnostic in packageScan.diagnostics)
						if (diagnostic != null && diagnostic.severity != null
							&& diagnostic.severity.toLowerCase() == 'error') {
							var packageMessage = diagnostic.message;
							if (diagnostic.code != null && StringTools.trim(diagnostic.code) != '')
								packageMessage = '[' + diagnostic.code + '] ' + packageMessage;
							addError(result, packageMessage);
						}
			}
		} catch (caught:Dynamic) {
			addError(result, 'Song discovery failed: ' + Std.string(caught));
			writeReport(result);
			return result;
		}
		var uniqueKinds:Map<String, Bool> = new Map<String, Bool>();
		var vsliceAssetSeen:Map<String, Bool> = new Map<String, Bool>();
		ModuleFunctions.reportImportProgress('scan-songs', '', 0, discovered.length);
		var discoveredIndex = 0;
		for (songData in discovered) {
			discoveredIndex++;
			if (ModuleFunctions.importWorkCancelled())
				break;
			ModuleFunctions.yieldImportWork();
			if (songData == null)
				continue;
			var name = field(songData, 'name', 'Unnamed song');
			var sourceDuplicate = Reflect.field(songData, 'sourceDuplicate') == true;
			var sourceRoot = field(songData, 'sourceRoot', source);
			var sourceDuplicateOf = field(songData, 'sourceDuplicateOf', '');
			var duplicate = sourceDuplicate;
			var destinationError:String = null;
			var sourceFolderValue:Dynamic = Reflect.field(songData, 'sourceFolder');
			var sourceFolder = sourceFolderValue == null || StringTools.trim(Std.string(sourceFolderValue)) == ''
				? name : StringTools.trim(Std.string(sourceFolderValue));
			var destinationFolder:String = '';
			try {
				var plannedFolder:Dynamic = Reflect.field(songData, 'destinationFolder');
				var storageKey:String = plannedFolder != null && StringTools.trim(Std.string(plannedFolder)) != ''
					? Std.string(plannedFolder)
					: sourceFolder;
				if (!sourceDuplicate) {
					var existingDataFolder = caseInsensitivePath(Path.join(['assets', 'data', storageKey]));
					var destinationPlan = ImportSongOwnership.planDestination(existingDataFolder, storageKey,
						sourceRoot, field(songData, 'engine', ''));
					destinationError = Reflect.field(destinationPlan, 'error');
					if (destinationError != null) {
						duplicate = true;
					} else if (Reflect.field(destinationPlan, 'qualified') == true) {
						var ownerFolder:Dynamic = Reflect.field(destinationPlan, 'folder');
						if (ownerFolder == null || StringTools.trim(Std.string(ownerFolder)) == '')
							destinationError = 'Destination collision did not produce an owner-qualified song folder.';
						else {
							storageKey = Std.string(ownerFolder);
						}
					}
					if (destinationError == null) {
						destinationFolder = storageKey;
						Reflect.setField(songData, 'destinationFolder', storageKey);
					}
				}
				// Existing folders are only a duplicate when the song is already
				// registered and complete.  An interrupted import can leave data/audio
				// behind without freeplaySongJson; keep it in the repair plan.
				duplicate = duplicate || (ModuleFunctions.songTargetExists(name, storageKey)
					&& !ModuleFunctions.songNeedsRepair(cast songData));
				if (destinationError != null) {
					duplicate = true;
					addError(result, name + ': ' + destinationError);
					var diagnostics:Dynamic = Reflect.field(songData, 'diagnostics');
					if (diagnostics == null || !Std.isOfType(diagnostics, Array)) {
						diagnostics = [];
						Reflect.setField(songData, 'diagnostics', diagnostics);
					}
					(cast diagnostics:Array<Dynamic>).push('[owner-collision-blocked] ' + destinationError);
				}
			} catch (_:Dynamic) {
				duplicate = sourceDuplicate;
			}
			var charts:Array<String> = [];
			var inspectionCharts:Array<{path:String, chart:Dynamic}> = [];
			var convertedPeers:Array<ImportVisualChart> = [];
			// Engine-aware discovery may provide charts which were converted in
			// memory (currently V-Slice).  Those are the authoritative chart
			// documents for dependency inspection; the source files are not native
			// chart JSON and must not be parsed as if they were.
			var convertedCharts:Dynamic = Reflect.field(songData, 'convertedCharts');
			if (convertedCharts != null && Std.isOfType(convertedCharts, Array)
				&& (cast convertedCharts:Array<Dynamic>).length > 0) {
				for (converted in (cast convertedCharts:Array<Dynamic>)) {
					if (converted == null)
						continue;
					var convertedPath = field(converted, 'source', field(songData, 'name', source));
					var difficulty = field(converted, 'difficulty', 'normal');
					var convertedChart:Dynamic = Reflect.field(converted, 'chart');
					if (convertedChart == null)
						continue;
					charts.push(convertedPath + ' [' + difficulty + ']');
					inspectionCharts.push({path:convertedPath, chart:convertedChart});
					convertedPeers.push({path:convertedPath, chart:convertedChart});
				}
			} else {
				var rawCharts:Dynamic = Reflect.field(songData, 'diffFiles');
				if (rawCharts != null && Std.isOfType(rawCharts, Array))
					for (chart in (cast rawCharts:Array<Dynamic>))
						if (chart != null && file(Std.string(chart))) {
							var rawPath = Std.string(chart);
							charts.push(rawPath);
							inspectionCharts.push({path:rawPath, chart:null});
						}
			}
			var scanSong:ImportScanSong = {
				name: name,
				duplicate: duplicate,
				willImport: !duplicate,
				reason: sourceDuplicate
					? 'duplicate source candidate skipped; candidate from "' + sourceDuplicateOf + '" won the completeness comparison'
					: (destinationError != null ? 'destination owner collision cannot be imported: ' + destinationError
						: (duplicate ? 'destination data or audio already exists' : 'new song')),
				source: sourceRoot,
				sourceFolder: sourceFolder,
				destinationFolder: destinationFolder == '' ? null : destinationFolder,
				sourceDuplicate: sourceDuplicate,
				sourceDuplicateOf: sourceDuplicateOf,
				charts: charts,
				dependencies: [],
				missing: [],
				diagnostics: []
			};
			var rawDiagnostics:Dynamic = Reflect.field(songData, 'diagnostics');
			if (rawDiagnostics != null && Std.isOfType(rawDiagnostics, Array))
				for (diagnostic in (cast rawDiagnostics:Array<Dynamic>))
					if (diagnostic != null)
						scanSong.diagnostics.push(Std.string(diagnostic));
			addVSliceConversionAssets(result, songData, vsliceAssetSeen);
			result.songs.push(scanSong);
			result.songsFound++;
			result.chartsFound += charts.length;
			if (duplicate)
				result.duplicateSongs++;
			else
				result.songsToImport++;
				var countBefore:Map<String, Bool> = new Map<String, Bool>();
			for (chart in inspectionCharts) {
				// Keep the scan-wide song fraction stable while showing the exact
				// chart currently undergoing potentially expensive dependency scans.
				ModuleFunctions.reportImportProgress('scan-songs', chart.path, discoveredIndex, discovered.length);
				inspectChart(result, scanSong, chart.path, descriptors, chart.chart,
					convertedPeers.length == 0 ? null : convertedPeers, songData);
				ModuleFunctions.yieldImportWork(true);
			}
			for (item in scanSong.dependencies) {
				var kindKey = item.kind + '|' + item.reference.toLowerCase();
				if (countBefore.exists(kindKey))
					continue;
				countBefore.set(kindKey, true);
				 switch (item.kind) {
					case 'character':
						if (item.found && !uniqueKinds.exists(kindKey)) {
							uniqueKinds.set(kindKey, true);
							result.charactersFound++;
						}
					case 'stage':
						if (item.found && !uniqueKinds.exists(kindKey)) {
							uniqueKinds.set(kindKey, true);
							result.stagesFound++;
						}
					case 'ui':
						if (item.found && !uniqueKinds.exists(kindKey)) {
							uniqueKinds.set(kindKey, true);
							result.uiPacksFound++;
						}
					case 'cutscene':
						if (item.found && !uniqueKinds.exists(kindKey)) {
							uniqueKinds.set(kindKey, true);
							result.cutscenesFound++;
						}
					case 'layout':
						if (item.found && !uniqueKinds.exists(kindKey)) {
							uniqueKinds.set(kindKey, true);
							result.layoutsFound++;
						}
					default:
				}
			}
			ModuleFunctions.reportImportProgress('scan-songs', name, discoveredIndex, discovered.length);
		}
		if (ModuleFunctions.importWorkCancelled()) {
			addError(result, 'Scan cancelled by the user.');
			writeReport(result);
			return result;
		}
		addRegistryAssets(result, descriptors);
		if (ModuleFunctions.importWorkCancelled()) {
			addError(result, 'Scan cancelled by the user.');
			writeReport(result);
			return result;
		}
		addGenericAssetCounts(result, descriptors);
		if (ModuleFunctions.importWorkCancelled()) {
			addError(result, 'Scan cancelled by the user.');
			writeReport(result);
			return result;
		}
		if (result.songsFound == 0)
			for (descriptor in descriptors)
				if (descriptor != null && descriptor.engine == ImportEngine.PSYCH
					&& PsychGlobalPackImporter.isEligible(descriptor.root, descriptor.contentRoot))
					result.globalPacksToImport = (result.globalPacksToImport == null ? 0
						: Std.int(result.globalPacksToImport)) + 1;
		ModuleFunctions.reportImportProgress('scan-complete', source, 1, 1);
		writeReport(result);
		return result;
	}
	#end
}

/** Native import handle.  The old synchronous importer is deliberately kept
 * as the single writer so its duplicate and registry rules remain centralized;
 * this wrapper moves that work away from Flixel's render/update thread. */
class ImportImportJob {
	public var sourcePath(default, null):String;
	public var importType(default, null):String;
	public var scan(default, null):ImportScanResult;
	/** Optional display labels gathered by the in-game importer, keyed by
	 * normalized source root. Omitted by automated/smoke callers. */
	var packageNames:Map<String, String>;
	public var done(default, null):Bool = false;
	public var result(default, null):SongImportBatchResult;
	public var error(default, null):String = null;
	public var completed(default, null):Int = 0;
	public var total(default, null):Int = 0;
	public var current(default, null):String = '';

	#if sys
	var worker:Thread;
	var stateMutex:Mutex;
	var cancelRequested:Bool = false;
	#end
	var reportWritten:Bool = false;
	var phase:String = 'starting';
	var copied:Int = 0;
	var skipped:Int = 0;
	var failed:Int = 0;
	var assetCompleted:Int = 0;
	var assetTotal:Int = 0;
	var songCompleted:Int = 0;
	var runtimeCommitted:Bool = false;

	public function new(sourcePath:String, scan:ImportScanResult, ?importType:String,
		?packageNames:Map<String, String>) {
		this.sourcePath = ImportSettings.normalizeSourcePath(sourcePath);
		this.scan = scan;
		this.packageNames = new Map<String, String>();
		if (packageNames != null)
			for (root => name in packageNames) {
				var key = ImportPackageNamePrompt.rootKey(root);
				if (key != '' && ImportPackageNamePrompt.validName(name))
					this.packageNames.set(key, StringTools.trim(name));
			}
		// Prefer the explicit selector from the UI, but preserve the plan's
		// selector when callers are replaying a scan.  This keeps old two-arg
		// callers source-compatible while preventing an import from silently
		// changing engine after the scan was completed.
		var plannedType:Dynamic = scan == null ? null : scan.importType;
		this.importType = ImportSettings.normalizeType(importType == null ? plannedType : importType);
		this.assetTotal = scan == null ? 0 : scan.assetFilesFound;
		this.total = (scan == null ? 0 : scan.songsFound) + this.assetTotal
			+ (scan == null || scan.globalPacksToImport == null ? 0 : scan.globalPacksToImport);
		if (this.total <= 0 && scan != null && scan.songsFound > 0)
			this.total = scan.songsFound;
		this.songCompleted = scan == null ? 0 : scan.duplicateSongs;
		this.completed = this.songCompleted;
		#if sys
		stateMutex = new Mutex();
		worker = Thread.create(function():Void {
			var imported:SongImportBatchResult = null;
			var failure:String = null;
			ModuleFunctions.setImportBackgroundMode(true);
			ModuleFunctions.setImportProgressCallback(function(payload:Dynamic):Void {
				acceptProgress(payload);
			});
				ModuleFunctions.setImportCancelCallback(function():Bool {
					return isCancelRequested();
				});
			try {
				imported = ImportRefreshManager.importOnce(this.sourcePath, this.importType, this.scan,
					this.packageNames, ImportWorkflow.convertRetainedSource, isCancelRequested, acceptProgress);
			} catch (caught:Dynamic) {
				failure = Std.string(caught);
			}
			var wasCancelled = isCancelRequested();
			ModuleFunctions.setImportProgressCallback(null);
			ModuleFunctions.setImportCancelCallback(null);
			ModuleFunctions.setImportBackgroundMode(false);
			if (imported != null) try {
				ImportScanJob.writeReport(this.scan, ModuleFunctions.importBatchSummary(imported));
				reportWritten = true;
			} catch (reportError:Dynamic) {
				trace('[import-report-error] ' + Std.string(reportError));
			}
			stateMutex.acquire();
			result = imported;
			error = failure;
			if (imported != null && !wasCancelled
				&& (imported.found > 0 || (imported.globalPacksImported != null && imported.globalPacksImported > 0)))
				completed = total;
			phase = failure != null ? 'import-failed' : (wasCancelled ? 'import-cancelled' : 'complete');
			done = true;
			stateMutex.release();
		});
		#else
		try {
			result = ModuleFunctions.importSongsFromPath(this.sourcePath, this.importType,
				scan == null ? null : scan.overlayMounts, this.packageNames);
			if (result != null) {
				ModuleFunctions.completeImportOnMainThread(result.importedSongs == null ? [] : result.importedSongs);
				runtimeCommitted = true;
			}
		} catch (caught:Dynamic) {
			error = Std.string(caught);
		}
		done = true;
		#end
	}

	#if sys
	public static function importChartFreePsychGlobalPacks(scan:ImportScanResult):SongImportBatchResult {
		var result:SongImportBatchResult = {
			found:0,
			imported:0,
			importedSongs:[],
			skipped:0,
			failed:0,
			copiedAssets:0,
			skippedAssets:0,
			globalPacksImported:0,
			errors:[]
		};
		var candidates:Array<ImportScanRoot> = [];
		if (scan == null || scan.detectedRoots == null)
			return result;
		for (root in scan.detectedRoots)
			if (root != null && root.engine == ImportEngine.PSYCH
				&& PsychGlobalPackImporter.isEligible(root.root, root.contentRoot))
				candidates.push(root);
		if (candidates.length == 0) {
			result.failed++;
			result.errors.push('[psych-global-pack-stale-scan] No eligible global pack remains at the scanned source roots.');
			return result;
		}
		var packIndex = 0;
		for (root in candidates) {
			if (ModuleFunctions.importWorkCancelled())
				break;
			packIndex++;
			ModuleFunctions.reportImportProgressPayload({phase:'psych-global-pack', current:root.path,
				completed:packIndex - 1, total:candidates.length, copied:0, skipped:0, failed:0, work:0});
			var importedPack = PsychGlobalPackImporter.importPack(root.root, root.contentRoot,
				function():Bool return ModuleFunctions.importWorkCancelled());
			if (!importedPack.eligible) {
				// The source may have changed after its scan. Leave it untouched and
				// make the stale plan visible in the import details.
				result.failed++;
				if (importedPack.errors != null)
					for (message in importedPack.errors)
						result.errors.push(message);
				ModuleFunctions.reportImportProgressPayload({phase:'psych-global-pack', current:root.path,
					completed:packIndex, total:candidates.length, copied:0, skipped:0, failed:1, work:1});
				continue;
			}
			result.copiedAssets += importedPack.copied;
			result.skippedAssets += importedPack.skipped;
			result.failed += importedPack.failed;
			if (importedPack.imported)
				result.globalPacksImported = (result.globalPacksImported == null ? 0
					: Std.int(result.globalPacksImported)) + 1;
			if (importedPack.errors != null)
				for (message in importedPack.errors)
					result.errors.push(message);
			ModuleFunctions.reportImportProgressPayload({phase:'psych-global-pack', current:root.path,
				completed:packIndex, total:candidates.length,
				copied:importedPack.copied, skipped:importedPack.skipped,
				failed:importedPack.failed, work:1});
		}
		return result;
	}
	#end

	function isCancelRequested():Bool {
		#if sys
		stateMutex.acquire();
		var value = cancelRequested;
		stateMutex.release();
		return value;
		#else
		return false;
		#end
	}

	function acceptProgress(payload:Dynamic):Void {
		if (payload == null)
			return;
		var incomingPhase = Reflect.field(payload, 'phase');
		var incomingCurrent = Reflect.field(payload, 'current');
		var incomingCompleted:Dynamic = Reflect.field(payload, 'completed');
		var incomingTotal:Dynamic = Reflect.field(payload, 'total');
		var incomingCopied:Dynamic = Reflect.field(payload, 'copied');
		var incomingSkipped:Dynamic = Reflect.field(payload, 'skipped');
		var incomingFailed:Dynamic = Reflect.field(payload, 'failed');
		// `copied`/`skipped`/`failed` are operation counters supplied by the
		// low-level importer and may be cumulative for a registry merge.  `work`
		// is the unambiguous completed-unit count for this event; status messages
		// immediately before a large copy deliberately carry work=0.
		var incomingWork:Dynamic = Reflect.field(payload, 'work');
		var copiedNow = incomingCopied == null ? 0 : Std.int(incomingCopied);
		var skippedNow = incomingSkipped == null ? 0 : Std.int(incomingSkipped);
		var failedNow = incomingFailed == null ? 0 : Std.int(incomingFailed);
		var workNow = incomingWork == null ? 0 : Std.int(incomingWork);
		#if sys
		stateMutex.acquire();
		phase = incomingPhase == null ? phase : Std.string(incomingPhase);
		current = incomingCurrent == null ? '' : Std.string(incomingCurrent);
		if (incomingPhase != null && Std.string(incomingPhase) == 'songs') {
			var songDone = incomingCompleted == null ? 0 : Std.int(incomingCompleted);
			songCompleted = songDone;
			completed = songCompleted + assetCompleted;
		} else if (workNow > 0) {
			assetCompleted += workNow;
			copied += copiedNow;
			skipped += skippedNow;
			failed += failedNow;
			completed = songCompleted + assetCompleted;
		}
		if (incomingTotal != null && Std.int(incomingTotal) > 0 && Std.string(incomingPhase) == 'assets'
			&& assetTotal < Std.int(incomingTotal))
			assetTotal = Std.int(incomingTotal);
		// The importer may encounter an asset not visible during the bounded scan;
		// expand the denominator rather than claiming 100% early.
		if (completed > total)
			total = completed + 1;
		stateMutex.release();
		#else
		phase = incomingPhase == null ? phase : Std.string(incomingPhase);
		current = incomingCurrent == null ? '' : Std.string(incomingCurrent);
		#end
	}

	public function poll():ImportWorkflowProgress {
		#if sys
		stateMutex.acquire();
		var localDone = done;
		var localResult = result;
		var localError = error;
		var localPhase = phase;
		var localCurrent = current;
		var localCompleted = completed;
		var localTotal = total;
		var localCopied = copied;
		var localSkipped = skipped;
		var localFailed = failed;
		stateMutex.release();
		#else
		var localDone = done;
		var localResult = result;
		var localError = error;
		var localPhase = phase;
		var localCurrent = current;
		var localCompleted = completed;
		var localTotal = total;
		var localCopied = copied;
		var localSkipped = skipped;
		var localFailed = failed;
		#end
			if (localDone && localResult != null) {
				// A cancelled worker may have stopped between song/file units.  Do not
				// turn its partial count into a false 100% import in the UI.
				if (localPhase != 'import-cancelled')
					localCompleted = localTotal;
				localCurrent = '';
				#if sys
				if (!runtimeCommitted) {
					// Use the batch's committed names, not every non-duplicate scan
					// entry.  A song can fail validation/copy after the scan, and a
					// cancellation can legitimately return a partial successful batch.
					// Refreshing only these names keeps DifficultyManager in sync with
					// the registry and still makes songs imported before cancellation
					// playable without restarting the game.
					var importedNames:Array<String> = localResult.importedSongs == null
						? [] : localResult.importedSongs.copy();
					runtimeCommitted = ImportRefreshManager.completeInitialImportHandoff(importedNames);
				}
			#end
			if (!reportWritten) {
				#if sys
				ImportScanJob.writeReport(scan, ModuleFunctions.importBatchSummary(localResult));
				#end
				reportWritten = true;
			}
		}
		var progress = localTotal <= 0 ? (localDone ? 1 : 0) : localCompleted / localTotal;
		if (!localDone && progress >= 1)
			progress = 0.99;
		return {
			importType: importType,
			phase: localDone ? (localPhase == 'import-cancelled' ? 'import-cancelled' : 'import-complete') : localPhase,
			complete: localDone,
			progress: progress,
			current: localCurrent,
			completed: localCompleted,
			total: localTotal,
			result: localResult,
			error: localError,
			copied: localCopied,
			skipped: localSkipped,
			failed: localFailed,
			runtimeCommitted: runtimeCommitted
		};
	}

	public function snapshot():ImportWorkflowProgress {
		return poll();
	}

	public function isFinished():Bool {
		#if sys
		stateMutex.acquire();
		var value = done;
		stateMutex.release();
		return value;
		#else
		return done;
		#end
	}

	/** Request a safe stop between song/file units.  The importer checks this
	 * callback before starting another copy and never interrupts File.copy. */
	public function cancel():Void {
		#if sys
		stateMutex.acquire();
		cancelRequested = true;
		stateMutex.release();
		#end
	}
}
