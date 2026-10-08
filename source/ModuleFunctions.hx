package;

import lime.utils.Assets;
import flixel.util.FlxColor;
import CompatScriptManifest.CompatScriptManifestData;
import CompatScriptManifest.CompatOverlayRecord;
import CodenameScriptDiscovery.CodenameScriptFile;
import CodenameClassScriptPlan;
import HxcAssetPlanner.HxcAssetPlan;
import ImportOverlayPlanner.ImportOverlayMount;
import ImportOverlayPlanner.ImportOverlayRetention;
import ImportOverlayPlanner.ImportOverlaySummary;
import ImportOverlayRuntime;
import PsychStageInference;
import PsychLanguagePublisher.PsychLanguagePublicationPlan;
import SourceMappedAssetPublisher.SourceMappedAssetPlan;
import SourceMappedAssetPublisher.SourceMappedAssetPolicyView;
#if sys
import ImportFile as File;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import ImportFileSystem as FileSystem;
import flash.media.Sound;
#end
using StringTools;

/** A V-Slice character conversion retained on the engine-neutral song plan.
 * Discovery fills these values without writing anything; the import phase
 * later copies the supported mappings and generated HScript. */
typedef VSliceCharacterImport = {
	var reference:String;
	var source:String;
	var conversion:VSliceImporter.VSliceCharacterConversion;
}

/** A V-Slice stage conversion retained on the engine-neutral song plan. */
typedef VSliceStageImport = {
	var reference:String;
	var source:String;
	var conversion:VSliceImporter.VSliceStageConversion;
}

/** A V-Slice custom note-style conversion retained until the song import
 * commits its generated UI pack and registry entry. */
typedef VSliceNoteStyleImport = {
	var reference:String;
	var source:String;
	var conversion:VSliceImporter.VSliceNoteStyleConversion;
}

typedef SongImport = {
	var name:String;
	var p1:String;
	var p2:String;
	var gf:String;
	var stage:String;
	var ui:String;
	var cutscene:String;
	var category:String;
	var isHey:Bool;
	var isCheer:Bool;
	var isMoody:Bool;
	var isSpooky:Bool;
	var stageID:Int;
	var week:Int;
	var char:String;
	var display:String;
	var inst:String;
	var voices:String;
	/** FPS Plus song metadata mapped into the native chart identity fields. */
	@:optional var songArtist:String;
	@:optional var album:String;
	/** Numeric FPS Plus difficulty ratings, retained for every authored chart. */
	@:optional var difficultyRatings:Array<Dynamic>;
	/** NMV source menu entries which should remain selectable after import. */
	@:optional var sourceSelectableDifficulties:Array<String>;
	/** NMV chart difficulties which the destination adapter cannot play. */
	@:optional var sourceUnsupportedDifficulties:Array<String>;
	/** Lossless parsed metadata/provenance envelope for unsupported keys. */
	@:optional var compatMetadata:Dynamic;
	/** V-Slice split stems. The destination name is chart metadata, not a donor path. */
	@:optional var vocalStems:Array<SongImportVocalStem>;
	var dialog:String;
	/** Original FPS/Kade JSON dialogue sidecar; retained beside the generated fallback. */
	@:optional var dialogueJson:String;
	/** Native dialog.txt text generated from dialogueJson without rewriting the donor. */
	@:optional var dialogueText:String;
	/** Original FPS/Kade cutscene metadata sidecar. */
	@:optional var cutsceneJson:String;
	/** Psych/Kade/FPS event sidecar.  The runtime merges this with embedded events. */
	@:optional var events:String;
	/** HXC cutscene class selected by cutscene.json's startCutscene.name. */
	@:optional var cutsceneScript:String;
	@:optional var cutsceneStoryOnly:Bool;
	@:optional var cutscenePlayOnce:Bool;
	var modchart:String;
	/** Generated HScript for a safe Lua modchart subset.  The donor Lua file is
	 * never rewritten; this is a destination-side runtime adapter. */
	@:optional var generatedModchart:String;
	var diffFiles:Array<String>;
	/** Engine-neutral charts which have already been converted in memory. */
	@:optional var convertedCharts:Array<ConvertedSongChart>;
	/** V-Slice authored note kinds materialized as native noteInfo entries. */
	@:optional var noteDefinitions:Array<Dynamic>;
	/** V-Slice visual definitions converted during read-only discovery. */
	@:optional var convertedCharacters:Array<VSliceCharacterImport>;
	/** Source Freeplay pixel icon for this row; kept separate from HUD icon strips. */
	@:optional var freeplayIconSource:String;
	@:optional var convertedStage:VSliceStageImport;
	/** V-Slice custom note-style definition converted during read-only discovery. */
	@:optional var convertedNoteStyle:VSliceNoteStyleImport;
	/** V-Slice note-kind styles which are independent of the song's UI style. */
	@:optional var convertedNoteStyles:Array<VSliceNoteStyleImport>;
	/** Root used to resolve V-Slice definitions/assets during discovery. */
	@:optional var vSliceRoot:String;
	/** Explicit Codename installation asset root for compiled `mods/<name>` imports.
	 * This is never inferred from a sibling mod or used as an owner root. */
	@:optional var codenameEngineBaseAssetRoot:String;
	/** Codename DEFAULT_CHARACTER id captured from this selected mod's flags. */
	@:optional var codenameDefaultCharacter:String;
	@:optional var engine:String;
	@:optional var diagnostics:Array<String>;
	/** Physical root which supplied this candidate during engine-aware discovery. */
	@:optional var sourceRoot:String;
	/** Human-readable package label captured from metadata or the import prompt.
	 * It supplies a fingerprint-gated owner identity only when the package has
	 * no authored ID; it never participates in song storage. */
	@:optional var sourceModName:String;
	/** `metadata`, `user`, or deterministic `inferred` fallback provenance. */
	@:optional var sourceModNameSource:String;
	/** Stable on-disk song key supplied by the donor folder.  A chart's display
	 * name may contain spaces/capitalization (for example "Dad Battle"), while
	 * its data/audio folders use an id such as "dad-battle".  Keep those two
	 * identities separate so Freeplay and DifficultyManager resolve the files
	 * the importer actually wrote. */
	@:optional var sourceFolder:String;
	/** Destination-only key for a selectable V-Slice variation. */
	@:optional var destinationFolder:String;
	/** True when the canonical native song key was already owned by another
	 * donor and this import received a stable owner-qualified destination. */
	@:optional var ownerQualifiedCollision:Bool;
	/** Set when this candidate lost duplicate selection to another source root. */
	@:optional var sourceDuplicate:Bool;
	@:optional var sourceDuplicateOf:String;
	/** Physical chart/audio folders for this candidate. A name-keyed lookup loses
	 * the source when two independent packages contain the same song name. */
	@:optional var importSourceInfo:SongImportSource;
}

/** A receipt-bound mapping plan for one exact source owner. */
typedef PreparedMappedAssetOwner = {
	var sourceRoot:String;
	var engine:String;
	var scope:String;
	var destinationRoot:String;
	var plan:SourceMappedAssetPlan;
}

typedef ConvertedSongChart = {
	var difficulty:String;
	var fileName:String;
	var source:String;
	var chart:Dynamic;
	/** Codename note type table retained for script staging and sidecar fallback. */
	@:optional var noteTypes:Array<Dynamic>;
	/** Original V-Slice identifier when a singleton variant difficulty is
	 * projected onto the destination's configured normal chart slot. */
	@:optional var sourceDifficulty:String;
	@:optional var cameraLines:Array<Dynamic>;
	@:optional var authoredSongTitle:Bool;
}

/** One V-Slice split vocal file before it is copied into the native song tree. */
typedef SongImportVocalStem = {
	var source:String;
	var destination:String;
	@:optional var id:String;
	@:optional var role:String;
}

typedef SongImportBatchResult = {
	var found:Int;
	var imported:Int;
	/** Storage keys of the songs whose chart/audio/registry unit completed.
	 * This is intentionally separate from `found`/`imported`: a worker can be
	 * cancelled after some songs have committed, and the UI must refresh only
	 * those songs' runtime difficulty support. */
	@:optional var importedSongs:Array<String>;
	var skipped:Int;
	var failed:Int;
	var copiedAssets:Int;
	var skippedAssets:Int;
	var errors:Array<String>;
	/** Number of chart-free Psych global packs installed by this import job. */
	@:optional var globalPacksImported:Int;
	/** Overlay operations planned/applied during this import transaction. */
	@:optional var overlayPlanned:Int;
	@:optional var overlayApplied:Int;
	@:optional var overlayRetained:Int;
	@:optional var overlaySkipped:Int;
	@:optional var overlayDiagnostics:Array<String>;
	@:optional var overlayProvenance:Array<String>;
	@:optional var overlayRetentions:Array<ImportOverlayRetention>;
}

/** A bounded legacy-package walk can finish with useful candidates while
 * leaving queued directories unvisited.  Keep this diagnostic generic: it is
 * about the discovery boundary, not about any one donor engine. */
typedef SongPackageDiscoveryDiagnostic = {
	var code:String;
	var severity:String;
	var message:String;
	var scannedDirectories:Int;
	var directoryLimit:Int;
	var queuedDirectories:Int;
}

/** Detailed result for the package/root discovery path.  The compatibility
 * `discoverSongPackageFolders()` API still returns only `folders`; callers
 * which need to explain a partial Auto scan can use this result. */
typedef SongPackageDiscoveryResult = {
	var folders:Array<String>;
	var diagnostics:Array<SongPackageDiscoveryDiagnostic>;
	var truncated:Bool;
	var cancelled:Bool;
	var scannedDirectories:Int;
	var directoryLimit:Int;
	var queuedDirectories:Int;
}

/** One chart-bearing source row which discovery rejected before it became an
 * import candidate. Rejections remain separate from `songs`, so preview and
 * import callers can explain missing source requirements without offering an
 * invalid candidate for selection. */
typedef SongImportDiscoveryRejection = {
	var code:String;
	var song:String;
	var engine:String;
	var sourceRoot:String;
	var sourcePath:String;
	var reason:String;
	var charts:Array<String>;
	var chartsTruncated:Bool;
}

/** Bounded accumulator shared by all roots in one discovery operation. */
typedef SongImportRejectionCollector = {
	var entries:Array<SongImportDiscoveryRejection>;
	var total:Int;
	var truncated:Bool;
	var seen:Map<String, Bool>;
}

/** Engine-aware song discovery plus diagnostics from the legacy package walk.
 * This is additive; the existing `discoverSongImports()` API remains an
 * Array<SongImport> wrapper for older callers. */
typedef SongImportDiscoveryResult = {
	var songs:Array<SongImport>;
	var packageDiscovery:SongPackageDiscoveryResult;
	@:optional var rejectedSongs:Array<SongImportDiscoveryRejection>;
	@:optional var rejectedSongCount:Int;
	@:optional var rejectedSongsTruncated:Bool;
}

/** Progress mailbox payload used by ImportWorkflow while the native importer
 * is running away from the Flixel update thread.  The callback is deliberately
 * Dynamic so this low-level module does not depend on the UI's typedefs. */
typedef SongImportProgress = {
	var phase:String;
	var current:String;
	var completed:Int;
	var total:Int;
	var copied:Int;
	var skipped:Int;
	var failed:Int;
	/** Number of completed file/registry units represented by this event.  A
	 * zero value is a status update (for example, immediately before a large
	 * copy); it is intentionally separate from the cumulative result counters. */
	var work:Int;
}

/** Source folders associated with a discovered song.  Keeping these paths
 * separate from the public song payload lets the batch merge only the trees
 * belonging to songs that were actually imported. */
typedef SongImportSource = {
	var song:String;
	var data:String;
	var destination:String;
	/** Root which supplied this song.  Kept separate from the chart/audio
	 * folders because compatibility scripts are copied once per donor root. */
	@:optional var sourceRoot:String;
	@:optional var engine:String;
}

/** One engine-aware song candidate before duplicate selection.  Keep the
 * physical root and source folders beside the public song payload so choosing
 * a later, more complete donor cannot accidentally keep the first root's
 * chart/audio paths. */
typedef SongImportCandidate = {
	var song:SongImport;
	var root:String;
	var engine:String;
	@:optional var source:SongImportSource;
}

typedef ImportAssetMergeResult = {
	var copied:Int;
	var skipped:Int;
	var failed:Int;
	@:optional var errors:Array<String>;
}

/** One static background sprite recovered from a compiled FPS Plus stage. */
typedef FpsPlusStageSprite = {
	var variable:String;
	var image:String;
	var x:Float;
	var y:Float;
	var scrollX:Float;
	var scrollY:Float;
	var animated:Bool;
	var animations:Array<String>;
}

/** Literal presentation data recovered from one FPS Plus BaseStage module. */
typedef FpsPlusStageSpec = {
	var defaultZoom:Null<Float>;
	var useStartPoints:Bool;
	var offsets:Array<{char:String, x:Float, y:Float}>;
	var sprites:Array<FpsPlusStageSprite>;
}
typedef StageImport = {
	var name:String;
	var like:String;
	var likePath:String;
	var assets:Array<String>;
}
typedef CharImport = {
	var name:String;
	var like:String;
	var likePath:String;
	var assets:Dynamic;
	var iconNums:Array<Float>;
	var colors:String;
}
typedef WeekImport = {
	var name:String;
	var desc:String;
	var like:String;
	var songs:Array<String>;
	var bf:String;
	var gf:String;
	var dad:String;
	var assets:Dynamic;
}

typedef CharCreation = {
	var path:String;
	var charjson:Dynamic;
	var ogname:String;
	var name:String;
	var like:String;
	var isPixel:Bool;
	var isBF:Bool;
	var isGF:Bool;
}

typedef PsychCharacterAtlasSource = {
	var png:String;
	var xml:String;
}

class ModuleFunctions {
	#if sys
	static var importProgressCallback:Dynamic;
	static var importCancelCallback:Dynamic;
	static var importBackgroundMode:Bool = false;
	static var importWorkCounter:Int = 0;

	public static function setImportProgressCallback(callback:Dynamic):Void {
		importProgressCallback = callback;
	}

	/**
	 * Install the cooperative cancellation check used by the background scan.
	 * The callback is only queried by the worker which owns the active import
	 * operation; keeping it here lets discovery and the scan's asset walk stop
	 * between filesystem units instead of leaving the UI waiting for a complete
	 * tree traversal.
	 */
	public static function setImportCancelCallback(callback:Dynamic):Void {
		importCancelCallback = callback;
	}

	public static function importWorkCancelled():Bool {
		if (importCancelCallback == null)
			return false;
		try {
			return cast Reflect.callMethod(null, importCancelCallback, []);
		} catch (_:Dynamic) {
			return false;
		}
	}

	/**
	 * Mark a batch as cooperatively cancelled.  Cancellation is only observed
	 * between filesystem units, so a file whose copy has already started is
	 * allowed to finish and the destination is never left half-written.
	 */
	static function markImportCancelled(result:SongImportBatchResult):Void {
		if (result != null) {
			var message = 'Import cancelled by the user.';
			if (result.errors == null)
				result.errors = [];
			if (result.errors.indexOf(message) < 0)
				result.errors.push(message);
		}
		if (result == null)
			reportImportProgress('import-cancelled', '', 0, 0);
		else
			reportImportProgress('import-cancelled', '', 0, 0, result.copiedAssets, result.skippedAssets,
				result.failed, 0);
	}

	/**
	 * A native worker can otherwise monopolize a single-core machine while it
	 * walks thousands of files and allocates chart JSON.  Yield periodically at
	 * safe filesystem boundaries.  This is deliberately a no-op for synchronous
	 * callers, and `Sys.sleep` is available on both hxcpp/Linux and hxcpp/Windows.
	 */
	public static function yieldImportWork(?force:Bool = false):Void {
		if (!importBackgroundMode)
			return;
		if (!ImportWorkScheduler.cooperate(function() return importWorkCancelled()))
			return;
		importWorkCounter++;
		if (force || importWorkCounter >= 24) {
			importWorkCounter = 0;
			Sys.sleep(0.001);
		}
	}

	/** Keep cache/front-end refreshes on the Flixel thread while the file-copy
	 * portion is running in ImportImportJob's worker. */
	public static function setImportBackgroundMode(value:Bool):Void {
		importBackgroundMode = value;
		if (!value)
			importWorkCounter = 0;
	}

	public static function completeImportOnMainThread(songNames:Array<String>):Void {
		// ImportImportJob performs filesystem work on a native worker.  Both the
		// overlay resolver and Song's visual-registry cache contain process-local
		// mutable state, so invalidate them only at this main-thread handoff.  A
		// worker-side invalidation can race FNFAssets reads from the render thread
		// and leave a partially observed cache between frames.
		ImportOverlayResolver.invalidate();
		NoteKeys.clearPresetCache();
		Song.invalidateVisualRegistryCache();
		if (songNames == null)
			return;
		for (songName in songNames) {
			if (songName == null || StringTools.trim(songName) == '')
				continue;
			try {
				DifficultyManager.addSongSupport(songName);
			} catch (error:Dynamic) {}
		}
	}

	public static function reportImportProgressPayload(payload:Dynamic):Void {
		if (payload == null) return;
		reportImportProgress(payload.phase, payload.current, payload.completed, payload.total,
			payload.copied, payload.skipped, payload.failed, payload.work);
	}

		public static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0,
			copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {
		var callback = importProgressCallback;
		if (callback == null)
			return;
		try {
			Reflect.callMethod(null, callback, [{
				phase: phase,
				current: current == null ? '' : current,
				completed: completed,
				total: total,
				copied: copied,
				skipped: skipped,
				failed: failed,
				work: work
			}]);
		} catch (error:Dynamic) {
			// Import progress is advisory.  A UI callback must never turn an
			// otherwise-valid copy into a failed import.
		}
	}
	#end
	/**
	 * Parse the key/value metadata used by the Modding Plus importer.
	 *
	 * Values are allowed to contain ':' (for example a Windows drive path),
	 * blank/comment lines are ignored, and malformed lines no longer crash the
	 * importer.  The map intentionally remains Dynamic for old callers.
	 */
	static public function processInfo(daInfo:String):Map<String, Dynamic> {
		var processedInfo:Map<String, Dynamic> = new Map<String, Dynamic>();
		if (daInfo == null || StringTools.trim(daInfo) == '')
			return processedInfo;

		var rawInfo:String;
		try {
			rawInfo = File.getContent(daInfo);
		} catch (error:Dynamic) {
			return processedInfo;
		}

		for (line in rawInfo.replace('\r\n', '\n').replace('\r', '\n').split('\n')) {
			var trimmed = StringTools.trim(line);
			if (trimmed == '' || StringTools.startsWith(trimmed, '#') || StringTools.startsWith(trimmed, '//'))
				continue;
			var separator = trimmed.indexOf(':');
			if (separator <= 0)
				continue;
			var key = StringTools.trim(trimmed.substr(0, separator));
			var value = StringTools.trim(trimmed.substr(separator + 1));
			if (key != '')
				processedInfo.set(key, value);
		}
		return processedInfo;
	}

	static public function getInfoValue(info:Map<String, Dynamic>, key:String, fallback:String = 'null'):String {
		if (info == null)
			return fallback;
		var value:Dynamic = info.get(key);
		if (value == null)
			return fallback;
		var text = StringTools.trim(Std.string(value));
		return text == '' ? fallback : text;
	}

	static public function getInfoBool(info:Map<String, Dynamic>, key:String, fallback:Bool = false):Bool {
		var value = getInfoValue(info, key, fallback ? 'true' : 'false').toLowerCase();
		return value == 'true' || value == '1' || value == 'yes';
	}

	static public function getInfoInt(info:Map<String, Dynamic>, key:String, fallback:Int = 0):Int {
		var parsed = Std.parseInt(getInfoValue(info, key, Std.string(fallback)));
		return parsed == null ? fallback : parsed;
	}

	static public function importRoot(?importType:String):String {
		return ImportSettings.getImportRoot(importType);
	}

	static public function importSongsPath(?importType:String):String {
		return ImportSettings.getImportPath('songs', importType);
	}

	// These limits apply only to discovery of a user-selected source.  The
	// destination asset tree is never walked by the importer.
	static inline var MAX_IMPORT_DISCOVERY_DEPTH:Int = 8;
	public static inline var MAX_IMPORT_DISCOVERY_DIRECTORIES:Int = 4096;
	static inline var MAX_ASSETS_ROOT_DEPTH:Int = 8;
	static inline var MAX_ASSETS_ROOT_DIRECTORIES:Int = 512;
	static inline var MAX_SONG_IMPORT_REJECTIONS:Int = 64;
	static inline var MAX_SONG_IMPORT_REJECTION_CHARTS:Int = 8;

	static function newSongImportRejectionCollector():SongImportRejectionCollector {
		return {entries: [], total: 0, truncated: false, seen: new Map<String, Bool>()};
	}

	#if sys
	/** Plan overlays once per detected engine root.  The returned mounts are
	 * safe to retain in ImportWorkflow's read-only scan result and reuse during
	 * the later destination transaction. */
	public static function planImportOverlays(roots:Array<ImportRootScanner.ImportRoot>):Array<ImportOverlayMount> {
		var mounts:Array<ImportOverlayMount> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		if (roots != null)
			for (root in roots) {
				if (root == null || root.root == null || StringTools.trim(root.root) == '')
					continue;
				var key = importPathKey(root.root);
				if (key == '' || seen.exists(key))
					continue;
				seen.set(key, true);
				mounts.push(ImportOverlayRuntime.mount(root.root, root.contentRoot, root.engine));
			}
		return ImportOverlayRuntime.sortMounts(mounts);
	}

	static function appendOverlaySummary(result:SongImportBatchResult, summary:ImportOverlaySummary):Void {
		if (result == null || summary == null)
			return;
		result.overlayPlanned = summary.planned;
		result.overlayApplied = summary.applied;
		result.overlayRetained = summary.retained;
		result.overlaySkipped = summary.skipped;
		result.overlayDiagnostics = summary.diagnostics == null ? [] : summary.diagnostics.copy();
		result.overlayProvenance = summary.provenance == null ? [] : summary.provenance.copy();
		result.overlayRetentions = summary.retainedPatches == null ? [] : summary.retainedPatches.copy();
	}

	static function applyImportOverlays(mounts:Array<ImportOverlayMount>, result:SongImportBatchResult):ImportOverlaySummary {
		var summary = ImportOverlayRuntime.apply(mounts, 'assets');
		if (summary.retainedPatches != null && summary.retainedPatches.length > 0)
			writeOverlayRetentionManifest(summary.retainedPatches, summary);
		// Manifest persistence can itself produce a diagnostic.  Copy the
		// completed summary only after that bounded write so scan/import reports
		// expose the complete non-fatal overlay status.
		appendOverlaySummary(result, summary);
		if (summary.planned > 0)
			reportImportProgress('overlays', summary.applied + ' applied / ' + summary.retained
				+ ' retained', summary.applied, summary.planned, summary.applied, summary.skipped, summary.retained,
				summary.applied + summary.retained);
		return summary;
	}

	static function writeOverlayRetentionManifest(retentions:Array<ImportOverlayRetention>,
		summary:ImportOverlaySummary):Void {
		if (retentions == null || retentions.length == 0)
			return;
		var path = CompatScriptManifest.overlayManifestPath();
		var manifest:CompatScriptManifestData = {version:CompatScriptManifest.VERSION, roots:[], overlays:[]};
		if (FileSystem.exists(path)) {
			try manifest = CompatScriptManifest.parse(File.getContent(path)) catch (_:Dynamic) {}
		}
		if (manifest.overlays == null)
			manifest.overlays = [];
		// Older manifests had no order field.  Give their existing records a
		// stable prefix before assigning ordinals to this import, preserving the
		// transaction's planner traversal order without re-sorting by filename.
		var nextOrder = 0;
		for (existing in manifest.overlays) {
			if (existing == null)
				continue;
			if (existing.order == null || existing.order < 0)
				existing.order = nextOrder;
			if (existing.order >= nextOrder)
				nextOrder = existing.order + 1;
		}
		var orderedRetentions = retentions.copy();
		orderedRetentions.sort(function(a:ImportOverlayRetention, b:ImportOverlayRetention):Int {
			var left = a == null || a.order == null ? -1 : a.order;
			var right = b == null || b.order == null ? -1 : b.order;
			if (left != right)
				return left - right;
			var compared = Reflect.compare(a == null ? '' : a.provenance, b == null ? '' : b.provenance);
			return compared == 0 ? Reflect.compare(a == null ? '' : a.targetPath,
				b == null ? '' : b.targetPath) : compared;
		});
		for (retention in orderedRetentions) {
			if (retention == null)
				continue;
			var duplicate = false;
			for (existing in manifest.overlays)
				if (existing != null && existing.engine == retention.engine && existing.mod == retention.mod
					&& existing.operation == retention.operation && existing.kind == retention.kind
					&& existing.relativePath == retention.relativePath && existing.provenance == retention.provenance
					&& existing.targetPath == retention.targetPath
					&& existing.reason == retention.reason && existing.payload == retention.payload) {
					duplicate = true;
					break;
				}
			if (duplicate)
				continue;
			manifest.overlays.push({
				engine: retention.engine,
				mod: retention.mod,
				operation: retention.operation,
				kind: retention.kind,
				order: nextOrder++,
				relativePath: retention.relativePath,
				targetPath: retention.targetPath,
				provenance: retention.provenance,
				reason: retention.reason,
				payload: retention.payload
			});
		}
		manifest.overlays.sort(function(a:CompatOverlayRecord, b:CompatOverlayRecord):Int {
			var compared = (a.order == null ? -1 : a.order) - (b.order == null ? -1 : b.order);
			if (compared != 0)
				return compared;
			compared = Reflect.compare(a.provenance, b.provenance);
			return compared == 0 ? Reflect.compare(a.targetPath, b.targetPath) : compared;
		});
		try {
			ensureDirectory(Path.directory(path));
			File.saveContent(path, CompatScriptManifest.stringify(manifest));
		} catch (error:Dynamic) {
			if (summary.diagnostics == null)
				summary.diagnostics = [];
			summary.diagnostics.push('[overlay-manifest-write] Could not retain overlay provenance: ' + Std.string(error));
		}
	}

	/** Return a stable absolute key for path comparisons on native targets. */
	static function importPathKey(path:String):String {
		var normalized = ImportSettings.normalizeSourcePath(path);
		if (normalized == '')
			return '';
		var unc = StringTools.startsWith(normalized, '//');
		try {
			// FileSystem.fullPath() can resolve an existing folder but throws for a
			// not-yet-created descendant.  That matters for generated V-Slice UI
			// assets: the first copy creates the destination folder, then every
			// later mapping must still compare against the same absolute base. Walk
			// to the nearest existing ancestor, resolve that ancestor, and append
			// the untouched descendant names.
			var probe = normalized;
			var suffix:Array<String> = [];
			while (!FileSystem.exists(probe)) {
				var parent = Path.directory(probe);
				if (parent == null || parent == '' || parent == probe)
					break;
				suffix.unshift(Path.withoutDirectory(probe));
				probe = parent;
			}
			var resolved = ImportSettings.normalizeSourcePath(FileSystem.fullPath(probe));
			for (part in suffix)
				resolved = Path.join([resolved, part]);
			normalized = ImportSettings.normalizeSourcePath(resolved);
		} catch (error:Dynamic) {
			// A non-native path (for example a Windows path in old metadata) may
			// not be accepted by fullPath.  The normalized spelling is still useful.
		}
		if (unc && !StringTools.startsWith(normalized, '//')) {
			while (StringTools.startsWith(normalized, '/'))
				normalized = normalized.substr(1);
			normalized = normalized == '' ? '//' : '//' + normalized;
		}
		#if windows
		return normalized.toLowerCase();
		#else
		// Linux keeps case-sensitive donor roots distinct.  Folding every path
		// here lets sibling roots such as `Donor` and `donor` share ownership.
		return normalized;
		#end
	}

	static function importPathIsWithin(path:String, root:String):Bool {
		var pathKey = importPathKey(path);
		var rootKey = importPathKey(root);
		if (pathKey == '' || rootKey == '')
			return false;
		if (pathKey == rootKey)
			return true;
		if (StringTools.endsWith(rootKey, '/'))
			return StringTools.startsWith(pathKey, rootKey);
		return StringTools.startsWith(pathKey, rootKey + '/');
	}

	#if sys
	static function mappedAssetOwnerKey(sourceRoot:String, engine:String):String {
		var sourceKey = importPathKey(sourceRoot);
		var engineKey = ImportRevision.normalizeEngine(engine);
		return sourceKey == '' || engineKey == '' ? '' : engineKey + '|' + sourceKey;
	}

	static function mappedOwnerPlan(plans:Map<String, PreparedMappedAssetOwner>,
		sourceRoot:String, engine:String):PreparedMappedAssetOwner {
		if (plans == null) return null;
		var key = mappedAssetOwnerKey(sourceRoot, engine);
		return key == '' ? null : plans.get(key);
	}

	static function mappedOwnerLanguageView(owner:PreparedMappedAssetOwner):SourceMappedAssetPolicyView {
		return owner == null || owner.plan == null || owner.engine != ImportEngine.PSYCH
			? null : SourceMappedMediaPublisher.languageView(owner.plan);
	}

	static function mappedOwnerMediaView(owner:PreparedMappedAssetOwner):SourceMappedAssetPolicyView {
		if (owner == null || owner.plan == null) return null;
		var label = SourceMappedMediaPublisher.mediaLabel(owner.engine, owner.scope);
		return label == '' ? null : SourceMappedMediaPublisher.policyView(owner.plan, label);
	}

	/** Determine NV package/core scope from scanner identity and exact layout.
		Unknown remains empty so a receipt-bound plan uses its unresolved policy. */
	static function authenticatedNightmareVisionScope(sourceRoot:String,
		contentRoot:String):String {
		if (sourceRoot == null || StringTools.trim(sourceRoot) == '') return '';
		var assetRoot = contentRoot;
		if (assetRoot == null || StringTools.trim(assetRoot) == '') {
			var candidate = Path.join([sourceRoot, 'assets']);
			if (FileSystem.isDirectory(candidate)) assetRoot = candidate;
		}
		var packageRoot = assetRoot == null ? null : canonicalNightmareVisionPackageRoot(assetRoot);
		// A scanner-selected <game>/content/<package>/assets root is still
		// package-owned even though its source path is one level below the
		// canonical package root. The canonical resolver requires the direct
		// package meta.json, exact assets/content layout, and authenticated outer
		// game proof, so an app marker copied into the package Project.xml must not
		// relabel this mapped package profile as engine core.
		if (packageRoot != null)
			return SourceMappedMediaPolicy.PACKAGE_SCOPE;
		if (ImportPackageFamilyCatalog.isAuthenticatedNightmareVisionContainer(sourceRoot))
			return SourceMappedMediaPolicy.CORE_SCOPE;
		return '';
	}

	static function skipMappedGlobalFile(owner:PreparedMappedAssetOwner,
		sourcePath:String, destinationPath:String):Bool {
		var logicalPath = mappedLogicalAssetPath(destinationPath);
		return logicalPath == null ? false : skipMappedAssetPath(owner, sourcePath, logicalPath);
	}

	/** Only generic raw copies consult identity blocks. Registry/script/chart
	 * transformations keep their dedicated conversion rules. */
	static function skipMappedRawFile(owner:PreparedMappedAssetOwner,
		sourcePath:String, destinationPath:String):Bool {
		return skipMappedGlobalFile(owner, sourcePath, destinationPath)
			|| SourceMappedMediaPublisher.skipIdentityLegacy(owner == null ? null : owner.plan,
				sourcePath, destinationPath);
	}

	static function skipMappedOwnerMediaFile(owner:PreparedMappedAssetOwner,
		sourcePath:String, destinationPath:String):Bool {
		if (owner == null || destinationPath == null) return false;
		var ownerRelative = relativeImportPath(destinationPath, owner.destinationRoot);
		return ownerRelative == null ? false : skipMappedAssetPath(owner, sourcePath,
			'assets/' + ownerRelative);
	}

	static function skipMappedAssetPath(owner:PreparedMappedAssetOwner,
		sourcePath:String, logicalPath:String):Bool {
		if (owner == null || owner.plan == null) return false;
		var languageView = mappedOwnerLanguageView(owner);
		if (languageView != null && (isLanguagePathForImport(sourcePath)
			|| isLanguagePathForImport(logicalPath))
			&& SourceMappedMediaPublisher.skipLegacyGlobal(owner.sourceRoot, owner.engine,
				owner.destinationRoot, PsychLanguagePublisher.policy(), languageView,
				sourcePath, logicalPath)) return true;
		var mediaPolicy = SourceMappedMediaPublisher.mediaPolicy(owner.engine, owner.scope);
		var mediaView = mappedOwnerMediaView(owner);
		return mediaPolicy != null && mediaView != null
			&& SourceMappedMediaPublisher.skipLegacyGlobal(owner.sourceRoot, owner.engine,
				owner.destinationRoot, mediaPolicy, mediaView, sourcePath, logicalPath);
	}

	static function relativeImportPath(path:String, root:String):Null<String> {
		if (path == null || root == null) return null;
		var normalizedPath = Path.normalize(path);
		var normalizedRoot = Path.normalize(root);
		var pathKey = importPathKey(normalizedPath);
		var rootKey = importPathKey(normalizedRoot);
		if (pathKey == rootKey) return '';
		var prefix = StringTools.endsWith(rootKey, '/') ? rootKey : rootKey + '/';
		if (!StringTools.startsWith(pathKey, prefix)) return null;
		return StringTools.replace(normalizedPath.substr(normalizedRoot.length + 1), '\\', '/');
	}

	static function mappedLogicalAssetPath(destinationPath:String):Null<String> {
		if (destinationPath == null || StringTools.trim(destinationPath) == '') return null;
		var clean = StringTools.replace(Path.normalize(destinationPath), '\\', '/');
		if (clean == 'assets') return 'assets';
		return StringTools.startsWith(clean, 'assets/') ? clean : null;
	}

	static function isLanguagePathForImport(path:String):Bool {
		return path != null && StringTools.trim(path) != ''
			&& StringTools.trim(path).toLowerCase().endsWith('.lang');
	}
	#end

	/** Logical asset roots for one detected engine project. The primary mapped
	 * root is copied first; supplemental Project.xml roots follow so existing
	 * bytes from the primary owner remain authoritative on collisions. */
	static function selectedAssetRootsForEngineRoot(engineRoot:ImportRootScanner.ImportRoot):Array<ImportRootScanner.ImportRootAssetSource> {
		var roots:Array<ImportRootScanner.ImportRootAssetSource> = [];
		if (engineRoot == null)
			return roots;
		var candidates:Array<ImportRootScanner.ImportRootAssetSource> = [
			{path:engineRoot.contentRoot, destinationPrefix:''}
		];
		if (engineRoot.supplementalAssetRoots != null)
			for (supplemental in engineRoot.supplementalAssetRoots)
				candidates.push(supplemental);
		for (candidate in candidates) {
			if (candidate == null || candidate.path == null || StringTools.trim(candidate.path) == ''
				|| !FileSystem.isDirectory(candidate.path))
				continue;
			var key = importPathKey(candidate.path);
			var duplicate = false;
			for (existing in roots)
				if (importPathKey(existing.path) == key) {
					duplicate = true;
					break;
				}
			if (!duplicate)
				roots.push(candidate);
		}
		return roots;
	}

	static function destinationAssetsPath():String {
		return importPathKey('assets');
	}

	static function isLegacyModuleSource(path:String):Bool {
		return importPathIsWithin(path, ImportSettings.getImportRoot())
			|| importPathIsWithin(path, Path.join(['assets', 'module', 'export']));
	}

	/**
	 * The current game's own assets (including a subfolder of assets) are not a
	 * valid import source.  This keeps a parent-folder selection safe while
	 * still allowing a directory containing another game's assets to be used.
	 */
	static public function isSafeImportSource(sourcePath:String):Bool {
		var normalized = ImportSettings.normalizeSourcePath(sourcePath);
		if (normalized == '' || !FileSystem.isDirectory(normalized))
			return false;
		var destination = destinationAssetsPath();
		if (destination != '' && importPathIsWithin(normalized, 'assets') && !isLegacyModuleSource(normalized))
			return false;
		// Selecting the game folder itself contains the destination assets.  Do
		// not reject a broad parent folder; its other game roots are still useful.
		var nestedAssets = Path.join([normalized, 'assets']);
		return destination == '' || importPathKey(nestedAssets) != destination;
	}
	#end

	/**
	 * Find Modding Plus song-package folders below a user-selected path.
	 *
	 * This compatibility API intentionally returns only the folders.  The walk
	 * remains bounded at MAX_IMPORT_DISCOVERY_DIRECTORIES; callers which need to
	 * explain a partial Auto scan should use discoverSongPackageFoldersDetailed.
	 */
	static public function discoverSongPackageFolders(selectedPath:String):Array<String> {
		return discoverSongPackageFoldersDetailed(selectedPath).folders;
	}

	/**
	 * Detailed package discovery with an optional bounded-directory seam for
	 * tests/tools.  Production callers omit directoryLimit and therefore retain
	 * the 4096-directory safety cap.  Cancellation is deliberately distinct from
	 * truncation: a user-cancelled walk must not claim that the safety cap fired.
	 */
	static public function discoverSongPackageFoldersDetailed(selectedPath:String,
		?directoryLimit:Int):SongPackageDiscoveryResult {
		var effectiveLimit = directoryLimit == null || directoryLimit <= 0
			? MAX_IMPORT_DISCOVERY_DIRECTORIES
			: (directoryLimit > MAX_IMPORT_DISCOVERY_DIRECTORIES ? MAX_IMPORT_DISCOVERY_DIRECTORIES : directoryLimit);
		var found:Array<String> = [];
		var diagnostics:Array<SongPackageDiscoveryDiagnostic> = [];
		var scannedDirectories = 0;
		var queuedDirectories = 0;
		var cancelledScan = false;
		#if sys
		if (selectedPath == null)
			return {
				folders: found, diagnostics: diagnostics, truncated: false, cancelled: false,
				scannedDirectories: 0, directoryLimit: effectiveLimit, queuedDirectories: 0
			};
		var root = ImportSettings.normalizeSourcePath(selectedPath);
		if (root == '')
			return {
				folders: found, diagnostics: diagnostics, truncated: false, cancelled: false,
				scannedDirectories: 0, directoryLimit: effectiveLimit, queuedDirectories: 0
			};
		if (!FileSystem.exists(root) || !FileSystem.isDirectory(root))
			return {
				folders: found, diagnostics: diagnostics, truncated: false, cancelled: false,
				scannedDirectories: 0, directoryLimit: effectiveLimit, queuedDirectories: 0
			};
		// A direct selection of this game's assets (or a folder below it) is
		// never a source.  Parent-folder selections remain allowed; descendants
		// are filtered below without touching the large destination tree.
		if (importPathIsWithin(root, 'assets') && !isLegacyModuleSource(root))
			return {
				folders: found, diagnostics: diagnostics, truncated: false, cancelled: false,
				scannedDirectories: 0, directoryLimit: effectiveLimit, queuedDirectories: 0
			};

		var visited:Map<String, Bool> = new Map<String, Bool>();
		var candidates:Map<String, Bool> = new Map<String, Bool>();
		var queue:Array<{path:String, depth:Int}> = [{path:root, depth:0}];
		var cursor = 0;
		while (cursor < queue.length && scannedDirectories < effectiveLimit) {
			if (importWorkCancelled()) {
				cancelledScan = true;
				break;
			}
			var item = queue[cursor++];
			var current = Path.normalize(item.path);
			if (importPathIsWithin(current, 'assets') && !isLegacyModuleSource(current))
				continue;
			var visitKey = importPathKey(current);
			if (visited.exists(visitKey))
				continue;
			visited.set(visitKey, true);
			scannedDirectories++;
			yieldImportWork();
			reportImportProgress('scan-discovery', current, scannedDirectories, effectiveLimit);

			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(current));
			} catch (error:Dynamic) {
				continue;
			}

			var hasInstrument = false;
			var hasJson = false;
			for (entry in entries) {
				if (importWorkCancelled()) {
					cancelledScan = true;
					break;
				}
				var lower = entry.toLowerCase();
				if (lower == 'inst.ogg' || StringTools.endsWith(lower, '_inst.ogg'))
					hasInstrument = true;
				if (StringTools.endsWith(lower, '.json'))
					hasJson = true;
			}
			if (hasInstrument && hasJson) {
				var candidateKey = importPathKey(current);
				if (!candidates.exists(candidateKey)) {
					candidates.set(candidateKey, true);
					found.push(current);
				}
			}

			if (cancelledScan || item.depth >= MAX_IMPORT_DISCOVERY_DEPTH)
				continue;
			for (entry in entries) {
				if (importWorkCancelled()) {
					cancelledScan = true;
					break;
				}
				var child = Path.join([current, entry]);
				var isDirectory = false;
				try {
					isDirectory = FileSystem.isDirectory(child);
				} catch (error:Dynamic) {
					isDirectory = false;
				}
				if (!isDirectory)
					continue;
				if (importPathIsWithin(child, 'assets') && !isLegacyModuleSource(child))
					continue;
				var childName = entry.toLowerCase();
				// These folders either contain only media/build output or can be
				// extremely large.  Supported assets live in data/songs/module
				// and custom_* trees, which are not pruned.
				if (childName == '.git' || childName == '.tools' || childName == '.haxelib'
					|| childName == 'bin' || childName == 'cache' || childName == 'node_modules'
					|| childName == 'music' || childName == 'sounds' || childName == 'videos'
					|| childName == 'fonts' || childName == 'shaders')
					continue;
				// Inspect the first few levels to find assets nested in a game or
				// mod folder; deeper levels are limited to known content containers.
				var knownContainer = childName == 'assets' || childName == 'songs' || childName == 'data'
					|| childName == 'module' || childName == 'import' || childName == 'export'
					|| childName == 'mods' || childName == 'custom_songs';
				if (item.depth < 4 || knownContainer)
					queue.push({path:child, depth:item.depth + 1});
			}
			if (cancelledScan)
				break;
		}
		queuedDirectories = Std.int(Math.max(0, queue.length - cursor));
		var truncated = !cancelledScan && scannedDirectories >= effectiveLimit && queuedDirectories > 0;
		if (truncated) {
			diagnostics.push({
				code: 'package-scan-truncated',
				severity: 'error',
				message: 'Auto package scan stopped after scanning ' + scannedDirectories + ' directories (limit '
					+ effectiveLimit + '); ' + queuedDirectories
					+ ' queued directories were not inspected. Some standalone song packages may be missing. Select a narrower source folder and scan again.',
				scannedDirectories: scannedDirectories,
				directoryLimit: effectiveLimit,
				queuedDirectories: queuedDirectories
			});
		}
		return {
			folders: found,
			diagnostics: diagnostics,
			truncated: truncated,
			cancelled: cancelledScan,
			scannedDirectories: scannedDirectories,
			directoryLimit: effectiveLimit,
			queuedDirectories: queuedDirectories
		};
		#else
		return {
			folders: found,
			diagnostics: diagnostics,
			truncated: false,
			cancelled: false,
			scannedDirectories: 0,
			directoryLimit: effectiveLimit,
			queuedDirectories: 0
		};
		#end
	}

	/** Test/tooling alias for the package walk's bounded detailed seam. */
	static public function discoverSongPackageFoldersBounded(selectedPath:String,
		directoryLimit:Int):SongPackageDiscoveryResult {
		return discoverSongPackageFoldersDetailed(selectedPath, directoryLimit);
	}

	static function normalizedImportFileName(name:String):String {
		return name == null ? '' : StringTools.trim(name).toLowerCase();
	}

	#if sys
	static function findImportFile(basePath:String, names:Array<String>):String {
		if (basePath == null || !FileSystem.isDirectory(basePath))
			return null;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(basePath));
		} catch (error:Dynamic) {
			return null;
		}
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(normalizedImportFileName(a), normalizedImportFileName(b));
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (wanted in names) {
			var wantedName = normalizedImportFileName(wanted);
			for (entry in entries) {
				if (normalizedImportFileName(entry) == wantedName) {
					var path = Path.join([basePath, entry]);
					if (isImportFile(path))
						return path;
				}
			}
		}
		return null;
	}

	static function findImportAudio(basePath:String, voices:Bool = false):String {
		if (basePath == null || !FileSystem.isDirectory(basePath))
			return null;
		// A few FPS/Kade exports use one pre-mixed vocal track.  Treat it as the
		// native direct vocal input only after an exact Voices.ogg match; the
		// importer will materialize a compatibility Voices.ogg alias while the
		// original VoicesTogether file remains in the copied donor tree.
		if (voices) {
			var direct = findImportFile(basePath, ['Voices.ogg', 'voices.ogg']);
			if (direct != null)
				return direct;
			var together = findImportFile(basePath,
				['VoicesTogether.ogg', 'Voices-Together.ogg', 'Voices_Together.ogg']);
			if (together != null)
				return together;
		}
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(basePath));
		} catch (error:Dynamic) {
			return null;
		}
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		var suffixes = voices ? ['_voices.ogg', '-voices.ogg'] : ['_inst.ogg', '-inst.ogg'];
		for (entry in entries) {
			var lower = normalizedImportFileName(entry);
			var matches = lower == (voices ? 'voices.ogg' : 'inst.ogg');
			for (suffix in suffixes)
				if (StringTools.endsWith(lower, suffix))
					matches = true;
			if (matches) {
				var path = Path.join([basePath, entry]);
				if (isImportFile(path))
					return path;
			}
		}
		return null;
	}

	/**
	 * Some Psych/Kade-era packs omit Voices.ogg and ship synchronized stems as
	 * Voices-Player.ogg, Voices-Opponent.ogg, or Voices-<character>.ogg.  Keep
	 * those files as a native vocalStems list so PlayState can load every track
	 * together; a lone first stem is not a valid substitute for the group.
	 */
	static function findImportVocalStems(basePath:String):Array<SongImportVocalStem> {
		var stems:Array<SongImportVocalStem> = [];
		if (basePath == null || !FileSystem.isDirectory(basePath)
			|| findImportFile(basePath, ['Voices.ogg', 'voices.ogg']) != null)
			return stems;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(basePath));
		} catch (_:Dynamic) {
			return stems;
		}
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (entry in entries) {
			var lower = entry.toLowerCase();
			if (!(lower.startsWith('voices-') || lower.startsWith('voices_'))
				|| !(lower.endsWith('.ogg') || lower.endsWith('.wav') || lower.endsWith('.mp3')))
				continue;
			var source = Path.join([basePath, entry]);
			if (!isImportFile(source))
				continue;
			var extensionStart = entry.lastIndexOf('.');
			var stemId = entry.substr(7, extensionStart > 7 ? extensionStart - 7 : entry.length - 7);
			if (StringTools.trim(stemId) == '')
				continue;
			stems.push({source:source, destination:entry, id:stemId, role:'shared'});
		}
		return stems;
	}

	/** Nightmare Vision names its two authored buses Voices-player/Voices-opp.
	 * Store those source IDs as explicit native roles so imported chart metadata
	 * and the PlayableSong vocal groups agree. */
	static function normalizeNightmareVisionVocalRoles(songData:SongImport):Void {
		if (songData == null || songData.vocalStems == null)
			return;
		for (stem in songData.vocalStems)
			if (stem != null)
				stem.role = NightmareVisionVocalRole.resolve(stem.id, stem.role);
	}

	static function vocalStemMetadataMatches(expected:Dynamic, existing:Dynamic):Bool {
		if (expected == null || existing == null || !Std.isOfType(expected, Array)
			|| !Std.isOfType(existing, Array))
			return false;
		var expectedStems:Array<Dynamic> = cast expected;
		var existingStems:Array<Dynamic> = cast existing;
		if (expectedStems.length != existingStems.length)
			return false;
		for (index in 0...expectedStems.length) {
			var planned = expectedStems[index];
			var stored = existingStems[index];
			if (planned == null || stored == null)
				return false;
			var plannedFile:Dynamic = Reflect.field(planned, 'file');
			if (plannedFile == null)
				plannedFile = Reflect.field(planned, 'destination');
			var storedFile:Dynamic = Std.isOfType(stored, String) ? stored : Reflect.field(stored, 'file');
			if (storedFile == null && !Std.isOfType(stored, String))
				storedFile = Reflect.field(stored, 'destination');
			if (plannedFile == null || storedFile == null || Std.string(plannedFile) != Std.string(storedFile))
				return false;
			var plannedId:Dynamic = Reflect.field(planned, 'id');
			var storedId:Dynamic = Std.isOfType(stored, String) ? null : Reflect.field(stored, 'id');
			var plannedRole:Dynamic = Reflect.field(planned, 'role');
			var storedRole:Dynamic = Std.isOfType(stored, String) ? null : Reflect.field(stored, 'role');
			if (plannedId != null && (storedId == null || Std.string(plannedId) != Std.string(storedId)))
				return false;
			if (plannedRole != null && (storedRole == null || Std.string(plannedRole) != Std.string(storedRole)))
				return false;
		}
		return true;
	}

	/** Repair only vocal metadata on an existing chart, preserving its notes and edits. */
	static function updateChartVocalStemMetadata(chart:Dynamic, expected:Array<Dynamic>):Bool {
		if (chart == null || expected == null || expected.length == 0)
			return false;
		var song:Dynamic = Reflect.field(chart, 'song');
		if (song == null)
			return false;
		var existing:Dynamic = Reflect.field(song, 'vocalStems');
		if (vocalStemMetadataMatches(expected, existing))
			return false;
		Reflect.setField(song, 'vocalStems', expected);
		Reflect.setField(song, 'needsVoices', true);
		Reflect.setField(chart, 'song', song);
		return true;
	}

	/** Read a JSON sidecar without making malformed optional metadata fatal. */
	static function readImportJson(path:String):Dynamic {
		if (path == null || !isImportFile(path))
			return null;
		try return CoolUtil.parseJson(File.getContent(path)) catch (_:Dynamic) return null;
	}

	/** Build the native fallback text while retaining the donor JSON unchanged. */
	static function convertImportDialogue(path:String, player1:String, player2:String):String {
		var parsed = readImportJson(path);
		return parsed == null ? null : EngineCompat.legacyDialogueText(parsed, player1, player2);
	}

	/** Extract the HXC cutscene class selected by an FPS/Kade sidecar. */
	static function importCutsceneScript(path:String):String {
		var parsed = readImportJson(path);
		return parsed == null ? null : EngineCompat.legacyCutsceneScript(parsed);
	}

	static function importCutsceneBool(path:String, field:String, fallback:Bool):Bool {
		var parsed = readImportJson(path);
		return parsed == null ? fallback : EngineCompat.legacyCutsceneBool(parsed, field, fallback);
	}

	static function songImportValidationCode(reason:String):String {
		var lower = reason == null ? '' : StringTools.trim(reason).toLowerCase();
		if (lower.indexOf('inst.ogg') >= 0 && lower.indexOf('missing') >= 0)
			return 'missing-required-instrumental';
		if (lower.indexOf('difficulty chart') >= 0)
			return 'missing-difficulty-chart';
		return 'invalid-song-import';
	}

	static function recordSongImportValidationRejection(collector:SongImportRejectionCollector,
		songData:SongImport, sourceRoot:String, sourcePath:String, engine:String, reason:String):Void {
		if (collector == null || reason == null || StringTools.trim(reason) == '')
			return;
		var songName = songData == null || songData.name == null ? '' : StringTools.trim(songData.name);
		if (songName == '')
			songName = sourcePath == null ? '' : Path.withoutDirectory(Path.normalize(sourcePath));
		var root = sourceRoot == null ? '' : StringTools.trim(sourceRoot);
		var path = sourcePath == null ? '' : StringTools.trim(sourcePath);
		var code = songImportValidationCode(reason);
		var key = root + '|' + path + '|' + songName.toLowerCase() + '|' + code + '|' + reason;
		if (collector.seen.exists(key))
			return;
		collector.seen.set(key, true);
		collector.total++;
		if (collector.entries.length >= MAX_SONG_IMPORT_REJECTIONS) {
			collector.truncated = true;
			return;
		}

		var charts:Array<String> = [];
		var seenCharts:Map<String, Bool> = new Map<String, Bool>();
		var chartsTruncated = false;
		var addChart = function(value:String):Void {
			if (value == null || StringTools.trim(value) == '')
				return;
			var clean = StringTools.trim(value);
			if (seenCharts.exists(clean))
				return;
			seenCharts.set(clean, true);
			if (charts.length >= MAX_SONG_IMPORT_REJECTION_CHARTS) {
				chartsTruncated = true;
				return;
			}
			charts.push(clean);
		};
		if (songData != null && songData.diffFiles != null)
			for (chart in songData.diffFiles)
				addChart(chart);
		if (songData != null && songData.convertedCharts != null)
			for (converted in songData.convertedCharts)
				if (converted != null)
					addChart(converted.source);
		collector.entries.push({
			code: code,
			song: songName,
			engine: engine == null || StringTools.trim(engine) == ''
				? (songData == null || songData.engine == null ? '' : songData.engine) : engine,
			sourceRoot: root,
			sourcePath: path,
			reason: reason,
			charts: charts,
			chartsTruncated: chartsTruncated
		});
	}

	static function validateAndRecordSongImport(collector:SongImportRejectionCollector,
		songData:SongImport, sourceRoot:String, sourcePath:String, engine:String):Bool {
		var validationError = validateSongImport(songData);
		if (validationError == null)
			return true;
		recordSongImportValidationRejection(collector, songData, sourceRoot, sourcePath, engine,
			validationError);
		return false;
	}

	static function getImportDifficultyNames():Array<String> {
		var names:Array<String> = [];
		try {
			var parsed:Dynamic = CoolUtil.parseJson(FNFAssets.getText('assets/images/custom_difficulties/difficulties.json'));
			if (parsed != null && parsed.difficulties != null) {
				for (difficulty in (cast parsed.difficulties:Array<Dynamic>)) {
					if (difficulty != null && difficulty.name != null)
						names.push(StringTools.trim(Std.string(difficulty.name)));
				}
			}
		} catch (error:Dynamic) {
			// Standalone Modding Plus packages still support the base trio if
			// the destination registry is unavailable during startup.
		}
		if (names.length == 0)
			names = ['easy', 'normal', 'hard'];
		return names;
	}

	static function findImportChart(basePath:String, difficulty:String, folderName:String):String {
		return findImportFile(basePath, importChartNames(difficulty, folderName));
	}

	static function importChartNames(difficulty:String, folderName:String):Array<String> {
		var names:Array<String> = [];
		for (extension in ['.json', '.jsonc'])
			names.push(difficulty + extension);
		if (difficulty.toLowerCase() == 'normal') {
			for (extension in ['.json', '.jsonc'])
				names.push(folderName + extension);
			// Psych/Kade exports sometimes retain the explicit normal suffix.
			for (extension in ['.json', '.jsonc'])
				names.push(folderName + '-normal' + extension);
		} else
			for (extension in ['.json', '.jsonc'])
				names.push(folderName + '-' + difficulty + extension);
		return names;
	}

	/** Resolve chart candidates from the directory snapshot already used by the
	 * song collector, keeping findImportFile's case and extension priority. */
	static function findImportChartInEntries(basePath:String, difficulty:String, folderName:String,
		entries:Array<String>):String {
		if (entries == null)
			return null;
		for (wanted in importChartNames(difficulty, folderName)) {
			var wantedName = normalizedImportFileName(wanted);
			for (entry in entries)
				if (normalizedImportFileName(entry) == wantedName) {
					var path = Path.join([basePath, entry]);
					if (isImportFile(path))
						return path;
				}
		}
		return null;
	}

	/** Metadata and event sidecars can be JSON documents without being a
	 * playable chart.  Native charts from legacy/Psych/Kade/FPS/Modding Plus
	 * exports all carry a `song.notes` array; use that payload as the final
	 * discriminator instead of assuming every JSON file with a `song` object is
	 * a difficulty.  V-Slice files use their own conversion path and never pass
	 * through this native predicate. */
	static function isImportChartSidecar(path:String):Bool {
		if (path == null)
			return true;
		var name = Path.withoutDirectory(Path.normalize(path)).toLowerCase();
		for (extension in ['.json', '.jsonc'])
			if (name.endsWith(extension))
				name = name.substr(0, name.length - extension.length);
		return name == 'events' || name == 'noteinfo' || name == 'note-info'
			|| name == 'metadata' || name == 'manifest' || name == 'meta'
			|| name == 'dialogue' || name == 'dialog' || name == 'chartmeta'
			|| name == 'importprovenance';
	}

	static function collectImportCharts(basePath:String, ?collectedNoteDefinitions:Array<Dynamic>):Array<String> {
		return collectAssetCharts(basePath, Path.withoutDirectory(Path.normalize(basePath)), collectedNoteDefinitions);
	}

	/** Collect the configured difficulty slots and any additional native chart
	 * files shipped by the source engine.  The old importer only looked at the
	 * destination's easy/normal/hard names, so packs with an `expert`, `mania`
	 * or engine-specific chart were silently reduced to zero/partial charts. */
	static function collectAssetCharts(dataPath:String, folderName:String,
		?collectedNoteDefinitions:Array<Dynamic>):Array<String> {
		var charts:Array<String> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		if (dataPath == null || !FileSystem.isDirectory(dataPath))
			return charts;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(dataPath));
		} catch (_:Dynamic) {
			return charts;
		}
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		var addParsed = function(path:String, chart:Dynamic):Void {
			if (path == null || chart == null)
				return;
			var key = Path.normalize(path).toLowerCase();
			if (seen.exists(key))
				return;
			seen.set(key, true);
			charts.push(path);
			if (collectedNoteDefinitions != null)
				collectSongNoteDefinitions(chart, collectedNoteDefinitions);
		};
		var addKnown = function(path:String):Void {
			if (path == null)
				return;
			var key = Path.normalize(path).toLowerCase();
			if (seen.exists(key))
				return;
			addParsed(path, readSongChart(path));
		};
		for (difficulty in getImportDifficultyNames())
			addKnown(findImportChartInEntries(dataPath, difficulty, folderName, entries));
		for (entry in entries) {
			var lower = entry.toLowerCase();
			if ((!lower.endsWith('.json') && !lower.endsWith('.jsonc')) || isImportChartSidecar(entry))
				continue;
			var path = Path.join([dataPath, entry]);
			if (!isImportFile(path))
				continue;
			var key = Path.normalize(path).toLowerCase();
			if (seen.exists(key))
				continue;
			addParsed(path, readSongChart(path));
		}
		return charts;
	}

	#end

	#if sys
	/** Canonicalize only the authenticated NMV game layout
	 * <game>/content/<package>/assets. The direct package metadata and outer
	 * scanner identity keep ordinary assets roots and unrelated nested packages
	 * on their existing ownership path. */
	static function canonicalNightmareVisionPackageRoot(assetRoot:String):String {
		if (assetRoot == null || StringTools.trim(assetRoot) == '' || !FileSystem.isDirectory(assetRoot)
			|| Path.withoutDirectory(Path.normalize(assetRoot)).toLowerCase() != 'assets')
			return null;
		var packageRoot = Path.directory(Path.normalize(assetRoot));
		var contentRoot = packageRoot == null ? null : Path.directory(packageRoot);
		var gameRoot = contentRoot == null ? null : Path.directory(contentRoot);
		if (packageRoot == null || contentRoot == null || gameRoot == null
			|| Path.withoutDirectory(Path.normalize(contentRoot)).toLowerCase() != 'content'
			|| findImportFile(packageRoot, ['meta.json']) == null
			|| !ImportPackageFamilyCatalog.isAuthenticatedNightmareVisionContainer(gameRoot))
			return null;
		retainNightmareVisionPackageNamespace(packageRoot, assetRoot);
		return packageRoot;
	}

	/** Reuse the namespace already recorded for an assets-root scan. A verified
	 * package-root mapping from an earlier v2 catalog wins when it exists. */
	static function retainNightmareVisionPackageNamespace(packageRoot:String, assetRoot:String):Void {
		var io = ImportIO.current();
		if (io == null || packageRoot == null || assetRoot == null) return;
		var packageNamespace = io.namespace(packageRoot, ImportEngine.NIGHTMARE_VISION);
		if (packageNamespace != null && StringTools.trim(packageNamespace) != '') return;
		var assetsNamespace = io.namespace(assetRoot, ImportEngine.NIGHTMARE_VISION);
		if (assetsNamespace != null && StringTools.trim(assetsNamespace) != '')
			io.setNamespace(packageRoot, ImportEngine.NIGHTMARE_VISION, assetsNamespace);
	}
	#end

	/** Add the conventional data/<song> (or data/songs/<song>) folders from one
	 * engine descriptor.  ImportRootScanner resolves the physical data/audio
	 * paths for packaged roots, so discovery must not infer them again from the
	 * descriptor's contentRoot. */
	static function appendAssetSongImports(result:Array<SongImport>, seenNames:Map<String, Bool>,
		dataRoot:String, audioRoot:String, ?musicRoot:String,
		?sourcePaths:Map<String, SongImportSource>, ?sourceRoot:String, ?engine:String,
		?rejections:SongImportRejectionCollector):Void {
		#if sys
		if (dataRoot == null || StringTools.trim(dataRoot) == '' || !FileSystem.isDirectory(dataRoot))
			return;
		// Some scanner descriptors represent an absent optional audio/music root
		// as an empty string rather than null. Do not pass that sentinel to the
		// staged filesystem facade, where an empty path is intentionally rejected.
		var sourceAudioRoot = audioRoot == null || StringTools.trim(audioRoot) == '' ? null : audioRoot;
		var sourceMusicRoot = musicRoot == null || StringTools.trim(musicRoot) == '' ? null : musicRoot;
		var hasAudioDirectory = sourceAudioRoot != null && FileSystem.isDirectory(sourceAudioRoot);

		var dataRoots:Array<String> = [dataRoot];
		// FPS Plus and a few older packaged builds put native charts below
		// data/songs while their audio remains in the sibling songs tree.  Keep
		// the ordinary data/<song> form too, and only add the nested root when it
		// really contains song directories so a song named "songs" is not lost.
		var nestedSongs = findNamedDirectory(dataRoot, 'songs');
		if (nestedSongs != null) {
			var hasNestedChartFolder = false;
			try {
				for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(nestedSongs))) {
					var candidate = Path.join([nestedSongs, entry]);
					if (FileSystem.isDirectory(candidate)) {
						hasNestedChartFolder = true;
						break;
					}
				}
			} catch (_:Dynamic) {}
			if (hasNestedChartFolder)
				dataRoots.push(nestedSongs);
		}
		// Psych-family game packages also ship charts under data/songData/<song>.
		// Keep this as a separate chart root so the package's engine identity and
		// owner stay attached to the imported song while its ordinary songs/<song>
		// audio path is resolved as usual.
		if (engine == ImportEngine.PSYCH || engine == ImportEngine.KADE
			|| engine == ImportEngine.NIGHTMARE_VISION) {
			var nestedSongData = findNamedDirectory(dataRoot, 'songData');
			if (nestedSongData != null && FileSystem.isDirectory(nestedSongData))
				dataRoots.push(nestedSongData);
		}
		// Nightmare Vision's playable mod packages keep each song's charts and
		// audio together below content/<pack>/songs/<song>/{data,audio}. The game
		// root still owns engine identity; discover only this structural layout
		// for NMV roots so sibling Psych/FPS packages and existing imports retain
		// their current adapters.
		if (engine == ImportEngine.NIGHTMARE_VISION && sourceRoot != null
			&& StringTools.trim(sourceRoot) != '') {
			// The caller may select one content pack directly instead of the
			// executable root. Recognize its own songs/<song>/data shape so it uses
			// this same NMV adapter and keeps that selected package as its owner.
			var rootSongs = findNamedDirectory(sourceRoot, 'songs');
			if (rootSongs != null && FileSystem.isDirectory(rootSongs)) {
				var checkedSongs = 0;
				for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(rootSongs))) {
					if (checkedSongs++ >= MAX_IMPORT_DISCOVERY_DIRECTORIES)
						break;
					var candidateSong = findNamedDirectory(rootSongs, entry);
					if (candidateSong != null && findNamedDirectory(candidateSong, 'data') != null) {
						if (importPathKey(rootSongs) != importPathKey(dataRoot))
							dataRoots.push(rootSongs);
						break;
					}
				}
			}
			var contentRoot = findNamedDirectory(sourceRoot, 'content');
			if (contentRoot != null && FileSystem.isDirectory(contentRoot)) {
				var packageNames:Array<String>;
				try packageNames = ImportDirectoryListing.normalize(FileSystem.readDirectory(contentRoot)) catch (_:Dynamic) packageNames = [];
				packageNames.sort(function(a:String, b:String):Int {
					var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
					return lower == 0 ? Reflect.compare(a, b) : lower;
				});
				var checkedPackages = 0;
				for (packageName in packageNames) {
					if (checkedPackages++ >= MAX_IMPORT_DISCOVERY_DIRECTORIES)
						break;
					var packageRoot = findNamedDirectory(contentRoot, packageName);
					if (packageRoot == null)
						continue;
					var packageSongs = findNamedDirectory(packageRoot, 'songs');
					if (packageSongs != null && FileSystem.isDirectory(packageSongs))
						dataRoots.push(packageSongs);
				}
			}
		}

		// Build one case-insensitive child-directory index per root. The old
		// per-song findNamedDirectory calls reread and sort the same songs/ trees
		// for every chart, which made large imports quadratic in directory size.
		// Callers pass entries in findNamedDirectory's deterministic sort order so
		// case-colliding names keep resolving to the same first directory.
		var indexNamedDirectories = function(parent:String, names:Array<String>):Map<String, String> {
			var indexed = new Map<String, String>();
			if (parent == null || !FileSystem.isDirectory(parent) || names == null)
				return indexed;
			for (entry in names) {
				if (entry == null)
					continue;
				var candidate = Path.join([parent, entry]);
				if (!FileSystem.isDirectory(candidate))
					continue;
				var key = entry.toLowerCase();
				if (!indexed.exists(key))
					indexed.set(key, candidate);
			}
			return indexed;
		};
		var audioSongFolders = new Map<String, String>();
		if (hasAudioDirectory) {
			try {
				var audioFolderNames = ImportDirectoryListing.normalize(FileSystem.readDirectory(sourceAudioRoot));
				audioFolderNames.sort(function(a:String, b:String):Int {
					var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
					return lower == 0 ? Reflect.compare(a, b) : lower;
				});
				audioSongFolders = indexNamedDirectories(sourceAudioRoot, audioFolderNames);
			} catch (_:Dynamic) {}
		}

		for (chartsRoot in dataRoots) {
			var songFolderNames:Array<String>;
			try {
				songFolderNames = ImportDirectoryListing.normalize(FileSystem.readDirectory(chartsRoot));
			} catch (_:Dynamic) {
				continue;
			}
			songFolderNames.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			var chartSongFolders = indexNamedDirectories(chartsRoot, songFolderNames);
			for (songFolderName in songFolderNames) {
				if (importWorkCancelled())
					return;
				var dataFolder = chartSongFolders.get(StringTools.trim(songFolderName).toLowerCase());
				if (dataFolder == null || !FileSystem.isDirectory(dataFolder))
					continue;

				var sourceSongFolder:String = null;
				var chartDataFolder = dataFolder;
				var songFolder:String = null;
				var isNestedNmvPackageSong = false;
				if (engine == ImportEngine.NIGHTMARE_VISION) {
					var nestedDataFolder = findNamedDirectory(dataFolder, 'data');
					var nestedAudioFolder = findNamedDirectory(dataFolder, 'audio');
					if (nestedDataFolder != null) {
						isNestedNmvPackageSong = true;
						sourceSongFolder = dataFolder;
						chartDataFolder = nestedDataFolder;
						// NMV checks for songs/<song>/audio first, then uses
						// Inst/Voices directly under songs/<song> when audio/ is absent.
						songFolder = nestedAudioFolder == null ? dataFolder : nestedAudioFolder;
					}
				}
				if (songFolder == null && !isNestedNmvPackageSong
					&& hasAudioDirectory)
					songFolder = audioSongFolders.get(StringTools.trim(songFolderName).toLowerCase());
				if (sourceSongFolder == null)
					sourceSongFolder = songFolder;
				// A songs/ root is a folder-per-song tree.  A music/ root is a
				// flat legacy stem tree and is passed as the fallback below.
				var flatMusicRoot = sourceMusicRoot;
				if (songFolder == null && hasAudioDirectory
					&& Path.withoutDirectory(Path.normalize(sourceAudioRoot)).toLowerCase() == 'music')
					flatMusicRoot = sourceAudioRoot;

				var songData = songImportFromAssetFolders(songFolder, chartDataFolder, songFolderName, flatMusicRoot);
				if (songData != null && engine == ImportEngine.NIGHTMARE_VISION)
					normalizeNightmareVisionVocalRoles(songData);
				// songImportFromRoots normally derives the destination folder from the
				// chart directory name. For the nested NMV layout that directory is
				// literally `data`; retain the authored songs/<song> key instead.
				if (songData != null && chartDataFolder != dataFolder)
					Reflect.setField(songData, 'sourceFolder', songFolderName);
				// A few native-ish exports flatten audio directly under songs/ rather
				// than creating songs/<name>/.  Resolve only this song's exact stem so
				// one flat library cannot accidentally satisfy another chart.
				if (songData != null && !isNestedNmvPackageSong
					&& hasAudioDirectory) {
					if (songData.inst == null)
						songData.inst = findImportFile(sourceAudioRoot, [songFolderName + '_Inst.ogg',
							songFolderName + '-Inst.ogg', songFolderName + 'Inst.ogg']);
					if (songData.voices == null)
						songData.voices = findImportFile(sourceAudioRoot, [songFolderName + '_Voices.ogg',
							songFolderName + '-Voices.ogg', songFolderName + 'Voices.ogg',
							songFolderName + 'VoicesTogether.ogg']);
				}
				var songSourceRoot = sourceRoot;
				if (isNestedNmvPackageSong) {
					// A full executable-root scan also sees the engine's own assets/data.
					// Give each content/<pack> its own stable song owner so a D-Sides
					// `monster` cannot share the executable-root collision alias with the
					// base-game `monster` candidate.
					var packageRoot = Path.directory(Path.directory(dataFolder));
					var packageContainer = packageRoot == null ? null : Path.directory(packageRoot);
					#if sys
					var canonicalPackageRoot = canonicalNightmareVisionPackageRoot(packageRoot);
					if (canonicalPackageRoot != null)
						songSourceRoot = canonicalPackageRoot;
					else
					#end
					if (packageRoot != null && packageContainer != null
						&& Path.withoutDirectory(Path.normalize(packageContainer)).toLowerCase() == 'content')
						songSourceRoot = packageRoot;
				}
				if (!validateAndRecordSongImport(rejections, songData, songSourceRoot, dataFolder, engine))
					continue;
				// Keep the donor provenance on the public song plan as well as in the
				// source-folder map.  The batch copy phase uses it to write a
				// destination-only compatibility manifest without persisting a donor
				// filesystem path in the destination.
				if (songSourceRoot != null && StringTools.trim(songSourceRoot) != '')
					Reflect.setField(songData, 'sourceRoot', songSourceRoot);
				if (engine != null && StringTools.trim(engine) != '') {
					Reflect.setField(songData, 'engine', engine);
					var compatMetadata:Dynamic = Reflect.field(songData, 'compatMetadata');
					if (compatMetadata != null)
						Reflect.setField(compatMetadata, 'engine', engine);
				}
				if (engine == ImportEngine.NIGHTMARE_VISION) {
					var menu = NightmareVisionDifficultyCompat.fromSourceRoot(songSourceRoot);
					songData.sourceSelectableDifficulties = menu.names;
					var unsupported:Array<String> = [];
					if (menu.diagnostic != null) {
						if (songData.diagnostics == null)
							songData.diagnostics = [];
						songData.diagnostics.push(menu.diagnostic);
					}
					if (songData.diffFiles != null)
						for (index in 0...songData.diffFiles.length) {
							var chartPath = songData.diffFiles[index];
							var targetFolder = importSongFolderName(songData);
							var destinationName = importedChartFileName(targetFolder, chartPath, index, Reflect.field(songData, 'sourceFolder'));
							var stem = Path.withoutDirectory(destinationName);
							stem = stem.substr(0, stem.length - Path.extension(stem).length - 1);
							var prefix = targetFolder.toLowerCase() + '-';
							var destinationDifficulty = stem.toLowerCase() == targetFolder.toLowerCase()
								? 'normal' : (stem.toLowerCase().startsWith(prefix)
									? stem.substr(prefix.length).toLowerCase() : stem.toLowerCase());
							if (!NightmareVisionDifficultyCompat.allows(menu.names, destinationDifficulty)) {
								if (songData.diagnostics == null)
									songData.diagnostics = [];
								songData.diagnostics.push('[nightmare-vision-unselectable-chart] Source chart "'
									+ stem + '" is retained for script/file access, but its difficulty "'
									+ destinationDifficulty + '" is absent from the selected owner\'s Freeplay list.');
							}
							var sourceChart = readSongChart(chartPath);
							if (sourceChart != null) {
								var scriptPlan = NightmareVisionScriptDiscovery.discover(songSourceRoot,
									songFolderName, sourceChart, null, CoolUtil.parseJson);
								for (diagnostic in NightmareVisionScriptDiscovery.unsupportedDiagnostics(scriptPlan)) {
									if (songData.diagnostics == null) songData.diagnostics = [];
									if (songData.diagnostics.indexOf(diagnostic) < 0)
										songData.diagnostics.push(diagnostic);
								}
							}
							var analysis = sourceChart == null ? null
								: NightmareVisionChartCompat.convert(sourceChart, chartPath);
							if (analysis != null && !analysis.supported && unsupported.indexOf(destinationDifficulty) < 0)
								unsupported.push(destinationDifficulty);
							if (analysis != null && analysis.diagnostics != null)
								for (diagnostic in analysis.diagnostics) {
									if (songData.diagnostics == null)
										songData.diagnostics = [];
									if (songData.diagnostics.indexOf(diagnostic) < 0)
										songData.diagnostics.push(diagnostic);
								}
						}
						songData.sourceUnsupportedDifficulties = unsupported;
				}
				if (engine == ImportEngine.PSYCH && sourceRoot != null && StringTools.trim(sourceRoot) != '') {
					var sourceChart:Dynamic = null;
					if (songData.diffFiles != null)
						for (chartPath in songData.diffFiles) {
							sourceChart = readSongChart(chartPath);
							if (sourceChart != null)
								break;
						}
					inferPsychStageForImport(songData,
						sourceChart == null ? null : Reflect.field(sourceChart, 'song'),
						sourceRoot, dataFolder, songFolderName);
				}
				var key = StringTools.trim(songData.name).toLowerCase();
				prepareInstalledDependencyRoots(songData, songSourceRoot, engine);
				var physicalKey = key + '|' + importPathKey(dataFolder);
				if (seenNames.exists(physicalKey))
					continue;
				seenNames.set(physicalKey, true);
				result.push(songData);
				var sourceInfo:SongImportSource = {song:sourceSongFolder, data:chartDataFolder,
					destination:importSongFolderName(songData), sourceRoot:songSourceRoot, engine:engine};
				songData.importSourceInfo = sourceInfo;
				if (sourcePaths != null) sourcePaths.set(key, sourceInfo);
			}
		}
		#end
	}

	/** Discover package charts and legacy assets/songs + assets/data pairs. */
	static function discoverLegacySongImports(selectedPath:String, ?sourcePaths:Map<String, SongImportSource>):Array<SongImport> {
		return discoverLegacySongImportsDetailed(selectedPath, sourcePaths).songs;
	}

	/** Detailed sibling of discoverLegacySongImports.  Keeping the package walk
	 * result beside the songs avoids process-global diagnostic state, which would
	 * let concurrent background scans overwrite one another. */
	static function discoverLegacySongImportsDetailed(selectedPath:String,
		?sourcePaths:Map<String, SongImportSource>,
		?rejections:SongImportRejectionCollector):SongImportDiscoveryResult {
		var result:Array<SongImport> = [];
		var rejectionCollector = rejections == null ? newSongImportRejectionCollector() : rejections;
		var packageDiscovery:SongPackageDiscoveryResult = {
			folders: [], diagnostics: [], truncated: false, cancelled: false,
			scannedDirectories: 0, directoryLimit: MAX_IMPORT_DISCOVERY_DIRECTORIES,
			queuedDirectories: 0
		};
		#if sys
		if (!isSafeImportSource(selectedPath))
			return {songs: result, packageDiscovery: packageDiscovery,
				rejectedSongs: rejectionCollector.entries, rejectedSongCount: rejectionCollector.total,
				rejectedSongsTruncated: rejectionCollector.truncated};
		packageDiscovery = discoverSongPackageFoldersDetailed(selectedPath);
		var seenNames:Map<String, Bool> = new Map<String, Bool>();
		for (packagePath in packageDiscovery.folders) {
			if (importWorkCancelled())
				break;
			if (!ImportRootScanner.retainedSourceRootAllowed(packagePath, ImportEngine.MODDING_PLUS))
				continue;
			yieldImportWork(true);
			var songData = songImportFromFolder(packagePath);
			if (validateAndRecordSongImport(rejectionCollector, songData, packagePath, packagePath,
				ImportEngine.MODDING_PLUS)) {
				// A broad Auto selection can contain several independent roots. Keep
				// the package itself as provenance; using the parent selection here
				// would make compatibility-script repair inspect unrelated siblings.
				Reflect.setField(songData, 'sourceRoot', packagePath);
				Reflect.setField(songData, 'engine', ImportEngine.MODDING_PLUS);
				var key = StringTools.trim(songData.name).toLowerCase();
				var physicalKey = key + '|' + importPathKey(packagePath);
				if (!seenNames.exists(physicalKey)) {
					seenNames.set(physicalKey, true);
					result.push(songData);
					var sourceInfo:SongImportSource = {song:packagePath, data:packagePath,
						destination:importSongFolderName(songData)};
					songData.importSourceInfo = sourceInfo;
					if (sourcePaths != null) sourcePaths.set(key, sourceInfo);
				}
			}
			yieldImportWork(true);
		}

		for (assetsRoot in findSelectedAssetsRoots(selectedPath)) {
			if (importWorkCancelled())
				break;
			if (!ImportRootScanner.retainedSourceRootAllowed(assetsRoot, ImportEngine.MODDING_PLUS))
				continue;
			yieldImportWork(true);
			var songsRoot = Path.join([assetsRoot, 'songs']);
			var dataRoot = Path.join([assetsRoot, 'data']);
			appendAssetSongImports(result, seenNames, dataRoot, songsRoot,
				Path.join([assetsRoot, 'music']), sourcePaths, assetsRoot, ImportEngine.MODDING_PLUS,
				rejectionCollector);
		}
		#end
		return {songs: result, packageDiscovery: packageDiscovery,
			rejectedSongs: rejectionCollector.entries, rejectedSongCount: rejectionCollector.total,
			rejectedSongsTruncated: rejectionCollector.truncated};
	}

	/** Discover songs using the exact paths selected by ImportRootScanner. */
	static function discoverLegacySongImportsFromRoot(root:ImportRootScanner.ImportRoot,
		?sourcePaths:Map<String, SongImportSource>,
		?rejections:SongImportRejectionCollector):Array<SongImport> {
		var result:Array<SongImport> = [];
		#if sys
		if (root == null || root.data == null || StringTools.trim(root.data) == '')
			return result;
		var seenNames:Map<String, Bool> = new Map<String, Bool>();
		var audioRoot = root.audio;
		var musicRoot:String = null;
		if (audioRoot != null && Path.withoutDirectory(Path.normalize(audioRoot)).toLowerCase() == 'music')
			musicRoot = audioRoot;
		appendAssetSongImports(result, seenNames, root.data, audioRoot, musicRoot, sourcePaths,
			root.root, root.engine, rejections);
		#end
		return result;
	}

	#if sys
	/** A broad parent selection may include this checkout's assets as a sibling.
	 * The scanner quite correctly describes that tree, but it is never a donor
	 * for import and must not be allowed to rediscover the destination assets. */
	static function isCurrentGameImportRoot(root:ImportRootScanner.ImportRoot):Bool {
		if (root == null)
			return false;
		// The in-game module importer deliberately stages donor packages below
		// assets/module/import; that subtree is an explicit exception to the
		// current-game-assets guard.
		if (isLegacyModuleSource(root.root) || isLegacyModuleSource(root.contentRoot))
			return false;
		var destination = destinationAssetsPath();
		if (destination != ''
			&& (importPathIsWithin(root.root, destination) || importPathIsWithin(root.contentRoot, destination)))
			return true;
		return false;
	}

	/**
	 * Keep scan/report discovery in lockstep with the writer.  A broad folder
	 * picker can include this checkout as one of its children; that root is a
	 * destination, never donor content, and must not inflate the scan plan.
	 */
	public static function isUsableImportRoot(root:ImportRootScanner.ImportRoot):Bool {
		return root != null && !isCurrentGameImportRoot(root);
	}
	#end

	#if sys
	/** Locate a donor video referenced by a Play Video event.  V-Slice packs
	 * keep them under videos/, assets/videos/, or the doubled videos/videos/. */
	static function findVSliceVideo(root:Dynamic, name:String):Null<String> {
		var bases = [
			Path.join([root.contentRoot == null || root.contentRoot == '' ? root.root : root.contentRoot, 'videos/videos']),
			Path.join([root.contentRoot == null || root.contentRoot == '' ? root.root : root.contentRoot, 'videos']),
			Path.join([root.root, 'assets/videos']),
			Path.join([root.root, 'videos/videos']),
			Path.join([root.root, 'videos'])
		];
		for (base in bases) {
			if (!FileSystem.isDirectory(base))
				continue;
			for (extension in ['mp4', 'webm', 'ogv']) {
				var candidate = Path.join([base, name + '.' + extension]);
				if (FileSystem.exists(candidate))
					return candidate;
			}
		}
		return null;
	}

	/** V-Slice Freeplay uses a separate 50px icon keyed by the source opponent.
	 * Probe only that exact logical id in the selected source image libraries. */
	static function findVSliceFreeplayIcon(root:ImportRootScanner.ImportRoot, characterId:String):Null<String> {
		if (root == null || characterId == null
			|| !new EReg('^[A-Za-z0-9_-]+$', '').match(characterId))
			return null;
		var base = root.contentRoot == null || StringTools.trim(root.contentRoot) == ''
			? root.root : root.contentRoot;
		var stem = characterId.toLowerCase().endsWith('pixel') ? characterId : characterId + 'pixel';
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (candidateRoot in [base, root.root]) {
			if (candidateRoot == null || candidateRoot == '' || seen.exists(candidateRoot))
				continue;
			seen.set(candidateRoot, true);
			for (folder in ['images/freeplay/icons', 'shared/images/freeplay/icons']) {
				var directory = Path.join([candidateRoot, folder]);
				var source = existingImportChild(directory, stem + '.png');
				if (isImportFile(source))
					return source;
			}
		}
		return null;
	}

	static function findVSliceFile(folder:String, suffix:String):String {
		if (folder == null || !FileSystem.isDirectory(folder))
			return null;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(folder));
		} catch (_:Dynamic) {
			return null;
		}
		entries.sort(function(a, b) {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (entry in entries) {
			if (entry.toLowerCase().endsWith(suffix)) {
				var path = Path.join([folder, entry]);
				if (isImportFile(path))
					return path;
			}
		}
		return null;
	}

	/** Resolve a V-Slice custom note-style definition without assuming the
		authored spelling's case.  The definition lives beside songs under
		data/notestyles, while packaged exports may expose the data directory as
		the selected root itself. */
	static function findVSliceNoteStyle(root:ImportRootScanner.ImportRoot, reference:String):String {
		#if sys
		if (root == null || reference == null || StringTools.trim(reference) == '')
			return null;
		var bases:Array<String> = [];
		for (base in [root.data, root.root, root.contentRoot]) {
			if (base == null || StringTools.trim(base) == '')
				continue;
			for (candidate in [Path.join([base, 'notestyles']), Path.join([base, 'data', 'notestyles'])])
				if (FileSystem.isDirectory(candidate) && bases.indexOf(candidate) < 0)
					bases.push(candidate);
		}
		var wanted = StringTools.trim(reference).toLowerCase();
		for (base in bases) {
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(base));
			} catch (_:Dynamic) {
				continue;
			}
			entries.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
			for (entry in entries) {
				if (!entry.toLowerCase().endsWith('.json') && !entry.toLowerCase().endsWith('.jsonc'))
					continue;
				var stem = entry.substr(0, entry.lastIndexOf('.')).toLowerCase();
				if (stem != wanted)
					continue;
				var path = Path.join([base, entry]);
				if (isImportFile(path))
					return path;
			}
		}
		#end
		return null;
	}

	/** Remove a diagnostic emitted by the generic chart converter once a more
	 * specific source-backed adapter has proved that convention supported. */
	static function removeVSliceDiagnosticCode(diagnostics:Array<String>, code:String):Void {
		if (diagnostics == null || code == null)
			return;
		var prefix = '[' + code + ']';
		var kept:Array<String> = [];
		for (diagnostic in diagnostics)
			if (diagnostic == null || !StringTools.startsWith(diagnostic, prefix))
				kept.push(diagnostic);
		diagnostics.resize(0);
		for (diagnostic in kept)
			diagnostics.push(diagnostic);
	}

	static function findVSliceVoices(folder:String, diagnostics:Array<String>):String {
		// Split V-Slice vocals are selected from metadata and attached as a list
		// above. Falling back to the first Voices-* file here can silently play
		// the wrong singer when metadata is incomplete or a variant stem is absent.
		// This fallback is only for a genuine single mixed vocal track.
		return findImportFile(folder, ['Voices.ogg', 'voices.ogg']);
	}

	/** Format a pure V-Slice finding for the importer plan/report without
	 * making the scan depend on the converter's internal diagnostic writer. */
	static function appendVSliceDiagnostic(diagnostics:Array<String>, finding:VSliceImporter.VSliceDiagnostic):Void {
		if (diagnostics == null || finding == null)
			return;
		var code = finding.code == null || StringTools.trim(finding.code) == '' ? 'conversion' : finding.code;
		var message = finding.message == null ? '' : finding.message;
		var text = '[' + code + '] ' + message;
		if (finding.path != null && StringTools.trim(finding.path) != '')
			text += ' (' + finding.path + ')';
		if (finding.difficulty != null && StringTools.trim(finding.difficulty) != '')
			text += ' [' + finding.difficulty + ']';
		// A chart can fire the same donor event hundreds of times.  The
		// conversion still preserves every event row, but the import report only
		// needs one representative diagnostic for each distinct finding.
		if (diagnostics.indexOf(text) == -1)
			diagnostics.push(text);
	}

	static function appendVSliceDiagnostics(diagnostics:Array<String>, findings:Array<VSliceImporter.VSliceDiagnostic>):Void {
		if (findings == null)
			return;
		for (finding in findings)
			appendVSliceDiagnostic(diagnostics, finding);
	}

	/** Return all likely V-Slice definition folders for one detected root.  The
	 * format is found in both direct roots and packaged assets/shared layouts;
	 * keeping the lookup here makes case-insensitive file matching consistent
	 * with the rest of the importer while preserving the converter's asset root. */
	static function vSliceDefinitionFolders(root:ImportRootScanner.ImportRoot, kind:String):Array<String> {
		var folders:Array<String> = [];
		if (root == null)
			return folders;
		var definitionFolder = kind == 'stage' ? 'stages' : 'characters';
		var bases:Array<String> = [root.data, root.contentRoot, root.root, root.shared];
		for (base in bases) {
			if (base == null || StringTools.trim(base) == '')
				continue;
			for (relative in [definitionFolder, 'data/' + definitionFolder, 'shared/' + definitionFolder]) {
				var candidate = Path.join([base, relative]);
				if (!FileSystem.isDirectory(candidate))
					continue;
				var duplicate = false;
				for (existing in folders)
					if (importPathKey(existing) == importPathKey(candidate)) {
						duplicate = true;
						break;
					}
				if (!duplicate)
					folders.push(candidate);
			}
		}
		return folders;
	}

	static function vSliceDefinitionStem(reference:String):String {
		if (reference == null)
			return '';
		var clean = StringTools.replace(StringTools.trim(reference), '\\', '/');
		if (clean == '')
			return '';
		var stem = Path.withoutDirectory(clean);
		if (stem.toLowerCase().endsWith('.json'))
			stem = stem.substr(0, stem.length - 5);
		return stem;
	}

	/** Find a V-Slice character/stage JSON from the detected root only. */
	static function findVSliceDefinition(root:ImportRootScanner.ImportRoot, kind:String, reference:String):String {
		var stem = vSliceDefinitionStem(reference);
		if (stem == '')
			return null;
		for (folder in vSliceDefinitionFolders(root, kind)) {
			var path = findImportFile(folder, [stem + '.json']);
			if (path != null)
				return path;
		}
		return null;
	}

	static function readVSliceDefinition(root:ImportRootScanner.ImportRoot, kind:String, reference:String,
		diagnostics:Array<String>):Dynamic {
		var path = findVSliceDefinition(root, kind, reference);
		if (path == null) {
			diagnostics.push('[missing-' + kind + '-definition] V-Slice ' + kind + ' JSON could not be found for "'
				+ reference + '".');
			return {path:null, data:null};
		}
		try {
			return {path:path, data:CoolUtil.parseJson(File.getContent(path))};
		} catch (error:Dynamic) {
			diagnostics.push('[invalid-' + kind + '-definition] Could not parse V-Slice ' + kind + ' JSON: ' + path
				+ ' (' + Std.string(error) + ')');
			return {path:path, data:null};
		}
	}

	static function appendVSliceFolderAssetDiagnostics(folder:String, metadata:Dynamic,
		diagnostics:Array<String>):Void {
		if (folder == null || !FileSystem.isDirectory(folder))
			return;
		var paths:Array<String> = [];
		try {
			for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(folder))) {
				var path = Path.join([folder, entry]);
				if (isImportFile(path))
					paths.push(path);
			}
		} catch (_:Dynamic) {}
		appendVSliceDiagnostics(diagnostics, VSliceImporter.diagnoseAssets(paths, metadata).diagnostics);
	}

	/** V-Slice HXC/Lua scripts are not native HScript and must be visible in
	 * the read-only report instead of being copied as if they were compatible.
	 * This walk is deliberately limited to script/data/shared trees; it never
	 * crawls the large image/song media libraries. */
	static function appendVSliceScriptDiagnostics(root:ImportRootScanner.ImportRoot,
		diagnostics:Array<String>):Void {
		if (root == null)
			return;
		var bases:Array<String> = [root.scripts, root.data, root.shared];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var budget:Array<Int> = [2048];
		for (base in bases)
			collectVSliceScriptDiagnostics(base, diagnostics, seen, budget, 0);
	}

	/** Keep the scanner report useful when a donor repeats the same HXC class or
	 * engine API from several roots.  Charts are never changed by this pass. */
	static function appendUniqueScriptDiagnostic(diagnostics:Array<String>, message:String):Void {
		if (diagnostics != null && message != null && diagnostics.indexOf(message) == -1)
			diagnostics.push(message);
	}

	static function collectVSliceScriptDiagnostics(path:String, diagnostics:Array<String>, seen:Map<String, Bool>,
		budget:Array<Int>, depth:Int):Void {
		if (path == null || StringTools.trim(path) == '' || budget[0] <= 0 || depth > 8
			|| !FileSystem.isDirectory(path))
			return;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(path));
		} catch (_:Dynamic) {
			return;
		}
		for (entry in entries) {
			if (budget[0]-- <= 0)
				return;
			var child = Path.join([path, entry]);
			if (FileSystem.isDirectory(child)) {
				var lowerDir = entry.toLowerCase();
				if (lowerDir == 'images' || lowerDir == 'songs' || lowerDir == 'music'
					|| lowerDir == 'sounds' || lowerDir == 'videos')
					continue;
				collectVSliceScriptDiagnostics(child, diagnostics, seen, budget, depth + 1);
				continue;
			}
			var lower = entry.toLowerCase();
			if (!lower.endsWith('.hxc') && !lower.endsWith('.lua'))
				continue;
			var key = importPathKey(child);
			if (seen.exists(key))
				continue;
			seen.set(key, true);
			var isHxc = lower.endsWith('.hxc');
			var contents = '';
			try {
				var size = FileSystem.stat(child).size;
				if (size <= 4 * 1024 * 1024)
					contents = File.getContent(child);
			} catch (_:Dynamic) {}
			var recognized:Array<String> = [];
			for (name in EngineCompat.scriptFunctionNames(contents))
				if (EngineCompat.knownScriptFunction(name) && recognized.indexOf(name) == -1)
					recognized.push(name);
			var hxcAnalyzed = false;
			var hxcHasSafeAdapter = false;
			var hxcHasGeneratedRuntime = false;
			var hxcHasSafeLifecycle = false;
			var hxcIsShaderAdapter = false;
			var hxcHasMenuSpec = false;
			var hxcHasPauseSpec = false;
			var hxcHasCustomEventHandler = false;
			if (isHxc && contents != '') {
				try {
					var hxc = HxcCompat.analyze(contents, child);
					hxcAnalyzed = true;
					var generatedRuntime:Dynamic = Reflect.field(hxc, 'generatedHscript');
				hxcHasMenuSpec = Reflect.field(hxc, 'menuSpec') != null;
				hxcHasPauseSpec = Reflect.field(hxc, 'pauseSpec') != null;
				hxcHasCustomEventHandler = hxc.kind == 'song-event'
					&& hxc.customEventKind != null && hxc.customEventKind != ''
					&& hxc.customEventBody != null && StringTools.trim(hxc.customEventBody) != '';
				hxcIsShaderAdapter = hxc.kind == 'shader' && Reflect.field(hxc, 'shaderDefinition') != null;
					for (callback in hxc.callbackAdapters)
						if (callback != null && callback.safe)
							hxcHasSafeLifecycle = true;
					hxcHasGeneratedRuntime = generatedRuntime != null
						&& StringTools.trim(Std.string(generatedRuntime)) != ''
						&& (hxcIsShaderAdapter || hxcHasSafeLifecycle || hxc.eventAdapters.length > 0
							|| hxcHasCustomEventHandler
							|| hxc.moduleDisabled == true || hxcHasMenuSpec || hxcHasPauseSpec);
					// A literal-disabled HXC module intentionally emits no lifecycle
					// callbacks. Its preserved `active = false` state is still a complete
					// no-op adapter, so do not report the donor's never-dispatched hooks as
					// an unsupported script.
					for (finding in hxc.diagnostics) {
						var hxcMessage = '[hxc-' + finding.code + '] ' + finding.message + ' (' + child + ')';
						appendUniqueScriptDiagnostic(diagnostics, hxcMessage);
					}
					for (adapter in hxc.eventAdapters) {
						hxcHasSafeAdapter = true;
						var routeMessage = '[hxc-event-route] ' + child + ': ' + adapter.sourceName
							+ ' -> ' + adapter.canonicalName;
						if (adapter.fields.length > 0)
							routeMessage += ' (fields: ' + adapter.fields.join(', ') + ')';
						appendUniqueScriptDiagnostic(diagnostics, routeMessage);
					}
					if (hxc.nativeNoteDefinitions.length > 0)
						appendUniqueScriptDiagnostic(diagnostics,
							'[hxc-note-adapter] ' + child + ': authored kind identity and generic note lifecycle/graphics callbacks use the native bridge; donor-specific state remains diagnosed separately.');
					if (hxcHasGeneratedRuntime)
						appendUniqueScriptDiagnostic(diagnostics,
							'[hxc-runtime-adapter] Compatible lifecycle code can be routed through native HScript: ' + child);
				} catch (error:Dynamic) {
					appendUniqueScriptDiagnostic(diagnostics,
						'[unsupported-hxc-parser] HXC compatibility pass failed safely for ' + child + ': ' + Std.string(error));
				}
			} else if (!isHxc && contents != '') {
				try {
					var lua = LuaCompat.translate(contents, child);
					for (finding in lua.diagnostics)
						appendUniqueScriptDiagnostic(diagnostics, finding);
					if (StringTools.trim(lua.hscript) != '')
						appendUniqueScriptDiagnostic(diagnostics,
							'[lua-runtime-adapter] Script is routed through the native compatibility runtime: ' + child);
				} catch (error:Dynamic) {
					appendUniqueScriptDiagnostic(diagnostics,
						'[unsupported-lua-parser] Lua compatibility pass failed safely for ' + child + ': ' + Std.string(error));
				}
			}
			var parserMessage = '[unsupported-hxc-script] No safe executable HScript lifecycle could be generated for: ' + child;
			if (recognized.length > 0)
				parserMessage += ' (engine APIs routed: ' + recognized.join(', ') + ')';
			// A recognized event has a real native data adapter, so avoid claiming
			// that its name is wholly unsupported.  The HXC body diagnostic above
			// still records the remaining execution gap.  Modules/note kinds retain
			// the parser warning only when no safe callback body (or event adapter)
			// was generated by the centralized HXC pass.
			if (isHxc && (!hxcAnalyzed || (!hxcHasSafeAdapter && !hxcHasGeneratedRuntime)))
				appendUniqueScriptDiagnostic(diagnostics, parserMessage);
			var unsupported = EngineCompat.unknownScriptFunctions(contents);
			if (unsupported.length > 0)
				appendUniqueScriptDiagnostic(diagnostics,
					'[unsupported-script-api] Unmapped engine API(s) in ' + child + ': ' + unsupported.join(', '));
		}
	}

	static function vSliceNativeCharacterName(conversions:Array<VSliceCharacterImport>, reference:String):String {
		if (conversions != null)
			for (converted in conversions)
				if (converted != null && converted.reference != null && reference != null
					&& converted.reference == reference
					&& converted.conversion != null)
					return converted.conversion.name;
		// Imported registries resolve exact spelling first. A case-insensitive
		// fallback is safe only when exactly one converted reference matches.
		var foldedMatch:VSliceCharacterImport = null;
		if (conversions != null && reference != null)
			for (converted in conversions)
				if (converted != null && converted.reference != null && converted.conversion != null
					&& converted.reference.toLowerCase() == reference.toLowerCase()) {
					if (foldedMatch != null) {
						foldedMatch = null;
						break;
					}
					foldedMatch = converted;
				}
		if (foldedMatch != null) return foldedMatch.conversion.name;
		var value = StringTools.trim(reference == null ? '' : reference).toLowerCase();
		return switch (value) {
			case 'boyfriend': 'bf';
			case 'daddy': 'dad';
			case 'girlfriend': 'gf';
			case 'nogf' | 'no-gf' | 'no_gf': 'no-gf';
			default: reference;
		};
	}

	/** Return a converted owner actor for an exact ID, or for one unambiguous
	 * case-folded match. Ambiguous case variants intentionally remain unresolved. */
	static function codenameConvertedCharacterName(conversions:Array<VSliceCharacterImport>, reference:String):Null<String> {
		if (conversions == null || reference == null) return null;
		for (converted in conversions)
			if (converted != null && converted.reference == reference && converted.conversion != null)
				return converted.conversion.name;
		var foldedMatch:VSliceCharacterImport = null;
		for (converted in conversions)
			if (converted != null && converted.reference != null && converted.conversion != null
				&& converted.reference.toLowerCase() == reference.toLowerCase()) {
				if (foldedMatch != null) return null;
				foldedMatch = converted;
			}
		return foldedMatch == null ? null : foldedMatch.conversion.name;
	}

	/** Resolve an authored Codename ID to its converted actor, destination-native
	 * alias, or the source engine's configured missing-XML character fallback.
	 * An owner XML that failed conversion is not allowed to borrow another actor. */
	static function codenameNativeCharacterName(conversions:Array<VSliceCharacterImport>, reference:String,
		ownerDefinitionExists:Bool, fallbackReference:String, fallbackNativeName:Null<String>):Null<String> {
		var id = StringTools.trim(reference == null ? '' : reference);
		if (id == '') return null;
		var convertedName = codenameConvertedCharacterName(conversions, id);
		if (convertedName != null) return convertedName;
		if (ownerDefinitionExists) return null;
		if (vSliceNativeCharacterReference(id)) {
			var nativeId = StringTools.trim(id).toLowerCase();
			return switch (nativeId) {
				case 'boyfriend': 'bf';
				case 'daddy': 'dad';
				case 'girlfriend': 'gf';
				case 'nogf' | 'no-gf' | 'no_gf': 'no-gf';
				default: id;
			};
		}
		if (fallbackNativeName != null && StringTools.trim(fallbackNativeName) != ''
			&& fallbackReference != null)
			return fallbackNativeName;
		return null;
	}

	/** V-Slice reserves these ids for the destination's built-in actors.  A
	 * blank girlfriend slot is represented as `no-gf` by conversion and is
	 * handled by Character's hidden-girlfriend adapter; it is not a missing
	 * donor JSON definition. */
	static function vSliceNativeCharacterReference(reference:String):Bool {
		var value = StringTools.trim(reference == null ? '' : reference).toLowerCase();
		return switch (value) {
			case 'bf' | 'boyfriend' | 'dad' | 'daddy' | 'gf' | 'girlfriend' | 'nogf' | 'no-gf' | 'no_gf': true;
			default: false;
		};
	}

	/**
		Find the base V-Slice chart pair and every variation pair it declares.
		Variation files are sibling metadata/chart documents. A missing pair is
		reported on the base import plan and never replaced with base metadata or
		notes.
	*/
	static function findVSliceSongPairs(dataFolder:String, folderName:String,
		metadataPath:String, chartPath:String, diagnostics:Array<String>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (metadataPath != null && chartPath != null)
			result.push({metadataPath: metadataPath, chartPath: chartPath, variation: ''});
		if (metadataPath == null) {
			var detached = findVSliceDetachedVariationPairs(dataFolder, folderName, diagnostics);
			if (detached.length > 0 && diagnostics != null)
				diagnostics.push('[variation-base-metadata-missing] V-Slice folder "' + folderName
					+ '" has no base metadata; its exact suffixed metadata/chart pairs are imported as separate songs.');
			for (pair in detached)
				result.push(pair);
			return result;
		}
		if (chartPath == null && diagnostics != null)
			diagnostics.push('[variation-base-chart-missing] V-Slice base metadata exists for "' + folderName
				+ '" but its base chart is absent; declared sibling variations can still be imported.');
		var metadata:Dynamic = null;
		try {
			metadata = CoolUtil.parseJson(File.getContent(metadataPath));
		} catch (error:Dynamic) {
			if (diagnostics != null)
				diagnostics.push('[variation-metadata] Could not read base V-Slice metadata for variation discovery: '
					+ metadataPath + ' (' + Std.string(error) + ')');
			return result;
		}
		for (variation in VSliceImporter.songVariationReferences(metadata)) {
			var safeVariation = safeVSliceVariationSuffix(variation);
			if (safeVariation == '') {
				if (diagnostics != null)
					diagnostics.push('[variation-id-invalid] V-Slice variation id cannot be represented as a safe native key: '
						+ variation + ' (' + metadataPath + ')');
				continue;
			}
			var variationMetadata = findVSliceVariationFile(dataFolder, folderName, 'metadata', variation);
			var variationChart = findVSliceVariationFile(dataFolder, folderName, 'chart', variation);
			if (variationMetadata == null || variationChart == null) {
				if (diagnostics != null)
					diagnostics.push('[variation-pair-missing] V-Slice variation "' + variation
						+ '" needs both metadata and chart files beside ' + Path.withoutDirectory(metadataPath) + '.');
				continue;
			}
			result.push({metadataPath: variationMetadata, chartPath: variationChart, variation: variation});
		}
		return result;
	}

	/** Find one exact unvaried V-Slice metadata or chart filename.  A generic
	 * suffix search can accidentally treat another sibling file as the base. */
	static function findVSliceSongBaseFile(folder:String, songFolder:String, kind:String):String {
		if (folder == null || songFolder == null || kind == null)
			return null;
		var stem = StringTools.trim(songFolder) + '-' + StringTools.trim(kind);
		return findImportFile(folder, [stem + '.json', stem + '.jsonc']);
	}

	/** Enumerate exact `<song>-<kind>-<variation>.json[c]` siblings in stable
	 * order.  The filename suffix is an identity supplied by the source file,
	 * not a guess based on an unrelated chart or audio name. */
	static function findVSliceVariationFiles(folder:String, songFolder:String, kind:String,
		diagnostics:Array<String>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (folder == null || songFolder == null || kind == null || !FileSystem.isDirectory(folder))
			return result;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(folder));
		} catch (_:Dynamic) {
			return result;
		}
		entries.sort(function(a, b) {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		var prefix = normalizedImportFileName(songFolder + '-' + kind + '-');
		var paths:Map<String, String> = new Map<String, String>();
		var extensions:Map<String, String> = new Map<String, String>();
		var ambiguous:Map<String, Bool> = new Map<String, Bool>();
		for (entry in entries) {
			var lower = normalizedImportFileName(entry);
			if (!StringTools.startsWith(lower, prefix))
				continue;
			var extension = lower.endsWith('.jsonc') ? '.jsonc'
				: (lower.endsWith('.json') ? '.json' : '');
			if (extension == '')
				continue;
			var rawSuffix = lower.substring(prefix.length, lower.length - extension.length);
			var suffix = safeVSliceVariationSuffix(rawSuffix);
			if (suffix == '' || suffix != rawSuffix) {
				if (diagnostics != null)
					diagnostics.push('[variation-id-invalid] Ignored V-Slice sibling with an unsafe variation filename: '
						+ entry + '.');
				continue;
			}
			var path = Path.join([folder, entry]);
			if (!isImportFile(path))
				continue;
			if (paths.exists(suffix)) {
				var existingExtension = extensions.get(suffix);
				if (existingExtension == '.jsonc' && extension == '.json') {
					paths.set(suffix, path);
					extensions.set(suffix, extension);
				} else if (existingExtension == extension) {
					paths.remove(suffix);
					extensions.remove(suffix);
					ambiguous.set(suffix, true);
				}
			} else if (!ambiguous.exists(suffix)) {
				paths.set(suffix, path);
				extensions.set(suffix, extension);
			}
		}
		var suffixes:Array<String> = [];
		for (suffix in paths.keys())
			if (!ambiguous.exists(suffix))
				suffixes.push(suffix);
		suffixes.sort(function(a, b) {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (suffix in suffixes)
			result.push({variation:suffix, path:paths.get(suffix)});
		var ambiguousSuffixes:Array<String> = [];
		for (suffix in ambiguous.keys())
			ambiguousSuffixes.push(suffix);
		ambiguousSuffixes.sort(function(a, b) {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		if (diagnostics != null)
			for (suffix in ambiguousSuffixes)
				diagnostics.push('[variation-file-ambiguous] More than one V-Slice ' + kind
					+ ' file normalizes to variation "' + suffix + '" in ' + folder + '.');
		return result;
	}

	/** A mod can provide only the suffixed half of a base-game song.  Preserve
	 * that explicit pair as a standalone native song when there is no local base
	 * metadata.  Unpaired files and pairs that conflict after safe normalization
	 * remain diagnostics, not guessed imports. */
	static function findVSliceDetachedVariationPairs(folder:String, songFolder:String,
		diagnostics:Array<String>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		var metadataFiles = findVSliceVariationFiles(folder, songFolder, 'metadata', diagnostics);
		var chartFiles = findVSliceVariationFiles(folder, songFolder, 'chart', diagnostics);
		var charts:Map<String, String> = new Map<String, String>();
		for (item in chartFiles)
			charts.set(Std.string(Reflect.field(item, 'variation')),
				Std.string(Reflect.field(item, 'path')));
		var matched:Map<String, Bool> = new Map<String, Bool>();
		for (item in metadataFiles) {
			var variation = Std.string(Reflect.field(item, 'variation'));
			if (charts.exists(variation)) {
				result.push({metadataPath:Reflect.field(item, 'path'), chartPath:charts.get(variation),
					variation:variation});
				matched.set(variation, true);
			} else if (diagnostics != null) {
				diagnostics.push('[variation-pair-missing] V-Slice metadata sibling for variation "' + variation
					+ '" has no matching chart file.');
			}
		}
		for (item in chartFiles) {
			var variation = Std.string(Reflect.field(item, 'variation'));
			if (!matched.exists(variation) && diagnostics != null)
				diagnostics.push('[variation-pair-missing] V-Slice chart sibling for variation "' + variation
					+ '" has no matching metadata file.');
		}
		return result;
	}

	static function safeVSliceVariationSuffix(variation:String):String {
		var value = variation == null ? '' : StringTools.trim(variation).toLowerCase();
		value = new EReg('[^a-z0-9_-]+', 'g').replace(value, '-');
		value = new EReg('-+', 'g').replace(value, '-');
		while (StringTools.startsWith(value, '-')) value = value.substr(1);
		while (StringTools.endsWith(value, '-')) value = value.substr(0, value.length - 1);
		return value;
	}

	static function findVSliceVariationFile(folder:String, songFolder:String, kind:String, variation:String):String {
		var suffix = safeVSliceVariationSuffix(variation);
		if (folder == null || suffix == '')
			return null;
		var stem = songFolder + '-' + kind + '-' + variation;
		return findImportFile(folder, [stem + '.json', stem + '.jsonc']);
	}

	/** Resolve the selected metadata instrumental, falling back only to the
	 * base instrumental when the requested variant stem is absent. */
	static function findVSliceInstrumental(folder:String, metadata:Dynamic, diagnostics:Array<String>):String {
		if (folder == null || !FileSystem.isDirectory(folder))
			return null;
		var characters = metadata == null || Reflect.field(metadata, 'playData') == null
			? null : Reflect.field(Reflect.field(metadata, 'playData'), 'characters');
		var instrumental = chartFieldString(characters, 'instrumental', '');
		if (instrumental != '' && instrumental.toLowerCase() != 'default') {
			var selected = findImportFile(folder, [
				'Inst-' + instrumental + '.ogg', 'Inst_' + instrumental + '.ogg',
				instrumental + '_Inst.ogg', instrumental + '-Inst.ogg'
			]);
			if (selected != null)
				return selected;
			if (diagnostics != null)
				diagnostics.push('[instrumental-variant-missing] V-Slice metadata selects instrumental "'
					+ instrumental + '" but no matching audio file exists in ' + folder + '.');
		}
		var base = findImportFile(folder, ['Inst.ogg', 'inst.ogg']);
		if (base != null)
			return base;
		return findImportAudio(folder);
	}

	/** A variation is already a separate selectable song identity. If that
	 * variation authors exactly one difficulty name unknown to the destination,
	 * store its chart in the configured normal slot so Freeplay can launch it.
	 * Multi-chart difficulty sets are left intact and diagnosed by regular
	 * difficulty support checks rather than guessed or collapsed. */
	static function normalizeVSliceVariationDifficulty(charts:Array<ConvertedSongChart>, songName:String,
		nativeDifficulties:Array<String>, diagnostics:Array<String>):Void {
		if (charts == null || charts.length != 1 || charts[0] == null)
			return;
		var chart = charts[0];
		var sourceDifficulty = StringTools.trim(chart.difficulty == null ? '' : chart.difficulty);
		if (sourceDifficulty == '')
			return;
		var supported = false;
		if (nativeDifficulties != null)
			for (difficulty in nativeDifficulties)
				if (difficulty != null && difficulty.toLowerCase() == sourceDifficulty.toLowerCase()) {
					supported = true;
					break;
				}
		if (supported)
			return;
		var targetDifficulty = 'normal';
		if (nativeDifficulties != null && nativeDifficulties.indexOf('normal') < 0) {
			targetDifficulty = '';
			for (difficulty in nativeDifficulties)
				if (difficulty != null && StringTools.trim(difficulty) != '') {
					targetDifficulty = StringTools.trim(difficulty);
					break;
				}
			if (targetDifficulty == '')
				targetDifficulty = 'normal';
		}
		chart.sourceDifficulty = sourceDifficulty;
		chart.difficulty = targetDifficulty;
		chart.fileName = VSliceImporter.nativeFileName(songName, targetDifficulty);
		if (diagnostics != null)
			diagnostics.push('[variation-difficulty-normalized] The single V-Slice variation difficulty "'
				+ sourceDifficulty + '" is not registered by this engine; its chart was mapped to native "'
				+ targetDifficulty + '" so the variation remains selectable.');
	}

	static function vSliceStemMatchesReference(stemId:String, reference:String):Bool {
		if (stemId == null || reference == null)
			return false;
		var stem = StringTools.trim(stemId).toLowerCase();
		var wanted = StringTools.trim(reference).toLowerCase();
		if (stem == '' || wanted == '')
			return false;
		return stem == wanted || StringTools.startsWith(stem, wanted + '-')
			|| StringTools.startsWith(stem, wanted + '_');
	}

	/** Select the actual split vocal stems belonging to this metadata variant. */
	static function selectVSliceVocalStems(metadata:Dynamic, available:Array<Dynamic>, diagnostics:Array<String>,
		?variation:String):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (available == null || available.length == 0)
			return result;
		var references = VSliceImporter.vocalStemReferences(metadata);
		var matchedReferences:Map<String, Bool> = new Map<String, Bool>();
		var chosenRoles:Map<String, String> = new Map<String, String>();
		var variationId = variation == null ? '' : StringTools.trim(variation).toLowerCase();
		for (reference in references) {
			var referenceId = reference == null ? '' : Std.string(Reflect.field(reference, 'id'));
			var referenceKey = referenceId.toLowerCase();
			var candidates:Array<Dynamic> = [];
			var exact:Dynamic = null;
			var variationMatch:Dynamic = null;
			for (stem in available) {
				if (stem == null)
					continue;
				var stemId = Std.string(Reflect.field(stem, 'id'));
				if (!vSliceStemMatchesReference(stemId, referenceId))
					continue;
				candidates.push(stem);
				var lowerStemId = stemId.toLowerCase();
				if (lowerStemId == referenceKey)
					exact = stem;
				if (variationId != '' && (lowerStemId == referenceKey + '-' + variationId
					|| lowerStemId == referenceKey + '_' + variationId))
					variationMatch = stem;
			}
			var selected:Dynamic = variationMatch != null ? variationMatch : exact;
			if (selected == null && candidates.length == 1)
				selected = candidates[0];
			if (selected == null && candidates.length > 1 && diagnostics != null)
				diagnostics.push('[vocal-stem-ambiguous] Multiple split vocal files match "' + referenceId
					+ '"; metadata does not identify which one belongs to variation "' + variationId + '".');
			if (selected != null) {
				var selectedId = Std.string(Reflect.field(selected, 'id'));
				var role = Std.string(Reflect.field(reference, 'role'));
				if (role == '' || role == 'null')
					role = Std.string(Reflect.field(selected, 'role'));
				chosenRoles.set(selectedId.toLowerCase(), role);
				matchedReferences.set(referenceKey, true);
			}
		}
		// Psych-style generic stems can be named by slot instead of character.
		for (stem in available) {
			if (stem == null)
				continue;
			var stemId = Std.string(Reflect.field(stem, 'id'));
			var lowerStemId = stemId.toLowerCase();
			if (chosenRoles.exists(lowerStemId))
				continue;
			var slot = lowerStemId == 'gf' ? 'girlfriend' : lowerStemId;
			if (slot != 'player' && slot != 'opponent' && slot != 'girlfriend')
				continue;
			for (reference in references)
				if (Std.string(Reflect.field(reference, 'role')).toLowerCase() == slot) {
					chosenRoles.set(lowerStemId, slot);
					matchedReferences.set(Std.string(Reflect.field(reference, 'id')).toLowerCase(), true);
					break;
				}
		}
		// Preserve the source directory's stable ordering for synchronized audio.
		for (stem in available) {
			if (stem == null)
				continue;
			var stemId = Std.string(Reflect.field(stem, 'id'));
			var lowerStemId = stemId.toLowerCase();
			if (chosenRoles.exists(lowerStemId))
				result.push({source:Reflect.field(stem, 'source'), destination:Reflect.field(stem, 'destination'),
					id:stemId, role:chosenRoles.get(lowerStemId)});
		}
		var missing:Array<String> = [];
		for (reference in references) {
			var id = reference == null ? '' : Std.string(Reflect.field(reference, 'id'));
			if (id != '' && !matchedReferences.exists(id.toLowerCase()))
				missing.push(id);
		}
		if (missing.length > 0 && diagnostics != null)
			diagnostics.push('[vocal-stem-missing] V-Slice metadata references vocal stem(s) with no matching audio file: '
				+ missing.join(', ') + '.');
		if (result.length == 0 && available.length > 0 && references.length == 0) {
			if (diagnostics != null)
				diagnostics.push('[vocal-stem-selection] Split V-Slice vocals were found but metadata provides no character or vocal-stem references.');
		}
		return result;
	}

	static function discoverVSliceSongImports(root:ImportRootScanner.ImportRoot,
		?sourcePaths:Map<String, SongImportSource>,
		?rejections:SongImportRejectionCollector):Array<SongImport> {
		var result:Array<SongImport> = [];
		if (root == null || root.data == '')
			return result;
		var rootScriptDiagnostics:Array<String> = [];
		appendVSliceScriptDiagnostics(root, rootScriptDiagnostics);
		var rootScriptDiagnosticsAdded = false;
		// A package can contain dozens of dynamic character definitions shared
		// by every song row. Cache the immutable conversions per source file and
		// icon requirement so their atlases/XML are parsed at most once per mode
		// during this root scan.
		var characterConversionCache:Map<String, VSliceImporter.VSliceCharacterConversion>
			= new Map<String, VSliceImporter.VSliceCharacterConversion>();
		var songsData = Path.join([root.data, 'songs']);
		if (!FileSystem.isDirectory(songsData))
			return result;
		var folders:Array<String>;
		try {
			folders = ImportDirectoryListing.normalize(FileSystem.readDirectory(songsData));
		} catch (_:Dynamic) {
			return result;
		}
		folders.sort(function(a, b) {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (folderName in folders) {
			if (importWorkCancelled())
				break;
			yieldImportWork(true);
			var dataFolder = Path.join([songsData, folderName]);
			if (!FileSystem.isDirectory(dataFolder))
				continue;
			var baseMetadataPath = findVSliceSongBaseFile(dataFolder, folderName, 'metadata');
			var baseChartPath = findVSliceSongBaseFile(dataFolder, folderName, 'chart');
			var variationDiscoveryDiagnostics:Array<String> = [];
			var sourcePairs = findVSliceSongPairs(dataFolder, folderName,
				baseMetadataPath, baseChartPath, variationDiscoveryDiagnostics);
			if (sourcePairs.length == 0)
				continue;
			var usedDestinationKeys:Map<String, Bool> = new Map<String, Bool>();
			for (pair in sourcePairs) {
				if (importWorkCancelled())
					break;
				var metadataPath = Std.string(Reflect.field(pair, 'metadataPath'));
				var chartPath = Std.string(Reflect.field(pair, 'chartPath'));
				var variation: String = Reflect.field(pair, 'variation');
				var variationSuffix = safeVSliceVariationSuffix(variation);
			var converted:VSliceImporter.VSliceConversionResult;
			try {
				converted = VSliceImporter.convertFiles(metadataPath, chartPath, dataFolder);
			} catch (error:Dynamic) {
				reportImportProgress('scan-vslice-error', dataFolder, 0, 0, 0, 0, 1);
				continue;
			}
			var diagnostics:Array<String> = [];
			appendVSliceDiagnostics(diagnostics, converted.diagnostics);
			if (variation == '' || ((baseMetadataPath == null || baseChartPath == null)
				&& pair == sourcePairs[0]))
				for (diagnostic in variationDiscoveryDiagnostics)
					if (diagnostics.indexOf(diagnostic) < 0)
						diagnostics.push(diagnostic);
			if (!rootScriptDiagnosticsAdded && rootScriptDiagnostics.length > 0) {
				for (diagnostic in rootScriptDiagnostics)
					diagnostics.push(diagnostic);
				rootScriptDiagnosticsAdded = true;
			}
			var metadata:Dynamic = null;
			try {
				metadata = CoolUtil.parseJson(File.getContent(metadataPath));
			} catch (error:Dynamic) {
				diagnostics.push('[invalid-metadata] Could not parse V-Slice metadata: ' + metadataPath
					+ ' (' + Std.string(error) + ')');
			}
			var audioFolder = root.audio == '' ? null : findNamedDirectory(root.audio, folderName);
			if (audioFolder == null && root.audio != '')
				audioFolder = findNamedDirectory(root.audio, converted.songName);
			appendVSliceFolderAssetDiagnostics(audioFolder, metadata, diagnostics);
			var convertedCharts:Array<ConvertedSongChart> = [];
			for (chart in converted.charts)
				convertedCharts.push({
					difficulty: chart.difficulty,
					fileName: chart.fileName,
					source: chartPath,
					chart: chart.chart
				});
			var convertedNoteStyle:VSliceNoteStyleImport = null;
			var convertedNoteStyles:Array<VSliceNoteStyleImport> = [];
			var playData:Dynamic = metadata == null ? null : Reflect.field(metadata, 'playData');
			var authoredNoteStyle = chartFieldString(playData, 'noteStyle', 'funkin');
			var normalizedNoteStyle = authoredNoteStyle.toLowerCase();
			if (normalizedNoteStyle != '' && normalizedNoteStyle != 'funkin'
				&& normalizedNoteStyle != 'normal' && normalizedNoteStyle != 'default'
				&& normalizedNoteStyle != 'pixel' && normalizedNoteStyle != 'pixelated') {
				var noteStylePath = findVSliceNoteStyle(root, authoredNoteStyle);
				if (noteStylePath == null) {
					diagnostics.push('[unsupported-note-style] V-Slice note style "' + authoredNoteStyle
						+ '" has no data/notestyles definition under the selected source root.');
				} else {
					try {
						var noteStyleData:Dynamic = CoolUtil.parseJson(File.getContent(noteStylePath));
						var noteStyleConversion = VSliceImporter.convertNoteStyle(noteStyleData,
							root.contentRoot == null || StringTools.trim(root.contentRoot) == '' ? root.root : root.contentRoot,
							authoredNoteStyle);
						appendVSliceDiagnostics(diagnostics, noteStyleConversion.diagnostics);
						if (noteStyleConversion.supported) {
							// The generic chart converter cannot read the source style file
							// by itself, so it first emits the safe normal fallback. Once
							// the source-backed conversion proves the style complete, every
							// difficulty receives the generated destination UI id.
							removeVSliceDiagnosticCode(diagnostics, 'unsupported-note-style');
							for (convertedChart in convertedCharts)
								if (convertedChart != null && convertedChart.chart != null
									&& Reflect.field(convertedChart.chart, 'song') != null)
									Reflect.setField(convertedChart.chart.song, 'uiType', noteStyleConversion.name);
							convertedNoteStyle = {
								reference: authoredNoteStyle,
								source: noteStylePath,
								conversion: noteStyleConversion
							};
						}
					} catch (error:Dynamic) {
						diagnostics.push('[note-style-conversion] Could not convert V-Slice note style "'
							+ authoredNoteStyle + '": ' + Std.string(error));
					}
				}
			}
			if (converted.noteStyleConversions != null)
				for (noteKindStyle in converted.noteStyleConversions) {
					if (noteKindStyle == null || noteKindStyle.conversion == null
						|| (convertedNoteStyle != null && convertedNoteStyle.conversion != null
							&& convertedNoteStyle.conversion.name.toLowerCase()
								== noteKindStyle.conversion.name.toLowerCase()))
						continue;
					convertedNoteStyles.push({
						reference: noteKindStyle.reference,
						source: noteKindStyle.source,
						conversion: noteKindStyle.conversion
					});
				}
			var firstSong:Dynamic = convertedCharts.length == 0 ? null : convertedCharts[0].chart.song;
			var playerReference = chartFieldString(firstSong, 'player1', 'bf');
			var opponentReference = chartFieldString(firstSong, 'player2', 'dad');
			var girlfriendReference = chartFieldString(firstSong, 'gf', 'gf');
			var stageReference = chartFieldString(firstSong, 'stage', 'stage');
			var convertedCharacters:Array<VSliceCharacterImport> = [];
			var seenCharacters:Map<String, Bool> = new Map<String, Bool>();
			// HealthIcon is a player/opponent HUD element in this engine.  V-Slice
			// still allows girlfriend-only character definitions to carry an icon id
			// (or omit one entirely), but requiring a donor icon for those definitions
			// turns harmless GF assets such as `nada`, `gf-pixelbar`, and an event-only
			// `gf-markov` into false missing dependencies.  Keep the requirement
			// role-aware and conservative: if the same id is ever used by a player or
			// opponent, it remains required.
			var characterHealthIconRequired:Map<String, Bool> = new Map<String, Bool>();
			var markCharacterHealthIconRole = function(reference:String, required:Bool):Void {
				var key = reference == null ? '' : StringTools.trim(reference).toLowerCase();
				if (key == '' || key == 'none' || key == 'null')
					return;
				if (!characterHealthIconRequired.exists(key) || required)
					characterHealthIconRequired.set(key, required);
			};
			markCharacterHealthIconRole(playerReference, true);
			markCharacterHealthIconRole(opponentReference, true);
			markCharacterHealthIconRole(girlfriendReference, false);
			if (converted.eventCharacterSlots != null)
				for (eventSlot in converted.eventCharacterSlots) {
					if (eventSlot == null)
						continue;
					var eventReference = Std.string(Reflect.field(eventSlot, 'reference'));
					var eventTarget = StringTools.trim(Std.string(Reflect.field(eventSlot, 'slot'))).toLowerCase();
					var requiresIcon = eventTarget != '2' && eventTarget != 'gf'
						&& eventTarget != 'girlfriend' && eventTarget != 'player3';
					markCharacterHealthIconRole(eventReference, requiresIcon);
				}
			// Change Character events can introduce definitions that are not in
			// the initial cast, so include their references in the same engine-level
			// registry/import path as the initial actors. Package-wide safe JSON
			// definitions and runtime-selected script ids are added below as well.
			var characterReferences:Array<String> = [playerReference, opponentReference, girlfriendReference];
			if (converted.eventCharacterReferences != null)
				for (eventReference in converted.eventCharacterReferences)
					if (eventReference != null && characterReferences.indexOf(eventReference) < 0)
						characterReferences.push(eventReference);
			// Scripts can choose character ids at runtime (for example from a
			// costume menu), so chart roles and literal Change Character events do
			// not describe the complete package dependency set. Include every safe
			// definition supplied by this selected V-Slice source root. The importer
			// writes these into the package owner namespace below; it never scans
			// image/audio trees or merges colliding ids into the global registry.
			for (definitionName in VSliceImporter.characterDefinitionNames(
				vSliceDefinitionFolders(root, 'character')))
				if (definitionName != null && characterReferences.indexOf(definitionName) < 0)
					characterReferences.push(definitionName);
			for (reference in characterReferences) {
					var key = reference == null ? '' : StringTools.trim(reference).toLowerCase();
					if (key == '' || key == 'none' || key == 'null' || seenCharacters.exists(key))
						continue;
					seenCharacters.set(key, true);
					// V-Slice's no-girlfriend aliases are engine sentinels, not donor
					// definitions. Keep them on Character's native hidden-GF path.
					if (vSliceNativeCharacterReference(reference))
						continue;
					var definition = readVSliceDefinition(root, 'character', reference, diagnostics);
				var definitionData:Dynamic = Reflect.field(definition, 'data');
				if (definitionData == null)
					continue;
				try {
					// Package-only definitions may be selected by scripts for a visual
					// slot which never appears in chart metadata. Do not claim their HUD
					// icon is required unless a chart/event proves a player/opponent role.
					var healthIconRequired = characterHealthIconRequired.exists(key)
						&& characterHealthIconRequired.get(key);
					var characterDefinitionPath = Std.string(Reflect.field(definition, 'path'));
					var conversionKey = Path.normalize(characterDefinitionPath) + '|icon='
						+ (healthIconRequired ? '1' : '0');
					var conversion = characterConversionCache.get(conversionKey);
					if (conversion == null) {
						conversion = VSliceImporter.convertCharacter(definitionData,
							root.contentRoot == null || StringTools.trim(root.contentRoot) == '' ? root.root : root.contentRoot,
							reference, healthIconRequired, characterDefinitionPath);
						characterConversionCache.set(conversionKey, conversion);
					}
					appendVSliceDiagnostics(diagnostics, conversion.diagnostics);
					// Incomplete definitions remain visible in the report, but their
					// zero-frame/partial conversion must not enter the playable owner
					// registry or rewrite chart ids as if the character were complete.
					if (Reflect.field(conversion, 'supported') == true)
						convertedCharacters.push({
							reference: reference,
							source: characterDefinitionPath,
							conversion: conversion
						});
				} catch (error:Dynamic) {
					diagnostics.push('[character-conversion] Could not convert V-Slice character "' + reference
						+ '": ' + Std.string(error));
				}
			}
			var convertedStage:VSliceStageImport = null;
			// Standard V-Slice stages are provided by the destination's native
			// registry. Their variant is encoded in the authored id (for example
			// schoolEvilErect), so do not report the absent donor JSON as a missing
			// dependency or generate a duplicate custom stage. Unknown ids still go
			// through the donor-definition path and remain diagnosable.
			var stageResolution = EngineCompat.resolveStageResolution(stageReference);
			var stageDefinition:Dynamic = EngineCompat.isBuiltinStageReference(stageReference)
				? {path:null, data:null}
				: readVSliceDefinition(root, 'stage', stageReference, diagnostics);
			var stageDefinitionData:Dynamic = Reflect.field(stageDefinition, 'data');
			if (stageDefinitionData != null) {
				try {
					var stageDefinitionPath = Std.string(Reflect.field(stageDefinition, 'path'));
					var stageConversion = VSliceImporter.convertStage(stageDefinitionData,
						root.contentRoot == null || StringTools.trim(root.contentRoot) == '' ? root.root : root.contentRoot,
						stageReference, stageDefinitionPath);
					convertedStage = {
						reference: stageReference,
						source: stageDefinitionPath,
						conversion: stageConversion
					};
					appendVSliceDiagnostics(diagnostics, stageConversion.diagnostics);
				} catch (error:Dynamic) {
					diagnostics.push('[stage-conversion] Could not convert V-Slice stage "' + stageReference
						+ '": ' + Std.string(error));
				}
			}
			// Change Stage events reference stages the chart never starts on.
			// Convert those definitions too so mid-song stage swaps resolve
			// natively instead of dying as "unregistered stage" while the
			// characters still swap (Wacky World's pixel/mc sections).
			var convertedStages:Array<Dynamic> = [];
			var eventVideoAssets:Array<Dynamic> = [];
			var rawChart:Dynamic = null;
			try {
				rawChart = CoolUtil.parseJson(File.getContent(chartPath));
			} catch (_:Dynamic) {}
			if (rawChart != null) {
				for (eventStageId in VSliceImporter.foreignStageReferences(rawChart)) {
					var normalizedEventStage = eventStageId;
					if (EngineCompat.isBuiltinStageReference(normalizedEventStage)
						|| normalizedEventStage.toLowerCase() == stageReference.toLowerCase())
						continue;
					var eventStageDefinition = readVSliceDefinition(root, 'stage', normalizedEventStage, diagnostics);
					var eventStageData:Dynamic = Reflect.field(eventStageDefinition, 'data');
					if (eventStageData == null) {
						diagnostics.push('[event-stage-missing] V-Slice stage "' + normalizedEventStage
							+ '" is referenced by a Change Stage event but has no definition under the source root.');
						continue;
					}
					try {
						var eventStageConversion = VSliceImporter.convertStage(eventStageData,
							root.contentRoot == null || StringTools.trim(root.contentRoot) == '' ? root.root : root.contentRoot,
							normalizedEventStage, Std.string(Reflect.field(eventStageDefinition, 'path')));
						convertedStages.push({
							reference: normalizedEventStage,
							source: Std.string(Reflect.field(eventStageDefinition, 'path')),
							conversion: eventStageConversion
						});
						appendVSliceDiagnostics(diagnostics, eventStageConversion.diagnostics);
					} catch (error:Dynamic) {
						diagnostics.push('[event-stage-conversion] Could not convert V-Slice stage "'
							+ normalizedEventStage + '": ' + Std.string(error));
					}
				}
				// Play Video events reference donor videos; keep them beside the
				// native tree so the runtime handler finds assets/videos/<name>.
				for (videoName in VSliceImporter.foreignVideoReferences(rawChart)) {
					var videoSource = findVSliceVideo(root, videoName);
					if (videoSource == null) {
						diagnostics.push('[event-video-missing] A Play Video event references "'
							+ videoName + '" but no video file was found under the source root.');
						continue;
					}
					eventVideoAssets.push({
						source: videoSource,
						destination: videoName + '.' + Path.extension(videoSource)
					});
				}
			}
			var nativePlayer = vSliceNativeCharacterName(convertedCharacters, playerReference);
			var nativeOpponent = vSliceNativeCharacterName(convertedCharacters, opponentReference);
			var nativeGirlfriend = vSliceNativeCharacterName(convertedCharacters, girlfriendReference);
			var nativeStage = convertedStage == null
				? (stageResolution == null ? stageReference : stageResolution.nativeName)
				: convertedStage.conversion.name;
			// V-Slice songName is display text.  The folder ID is the only stable
			// native song key because audio is resolved case-sensitively from
			// assets/songs/<song>/<song>_Inst.ogg.  Preserve the display text in the
			// freeplay entry while using folderName for the chart/audio identity.
			var nativeSongName = validModuleName(folderName) ? folderName : converted.songName;
			if (variationSuffix != '') {
				var variantFolder = StringTools.trim(folderName).toLowerCase() + '-' + variationSuffix;
				if (!validModuleName(variantFolder) || usedDestinationKeys.exists(variantFolder.toLowerCase())) {
					diagnostics.push('[variation-key-collision] V-Slice variation "' + variation
						+ '" does not have a unique safe destination song key.');
					continue;
				}
				usedDestinationKeys.set(variantFolder.toLowerCase(), true);
				nativeSongName = variantFolder;
				normalizeVSliceVariationDifficulty(convertedCharts, nativeSongName,
					getImportDifficultyNames(), diagnostics);
			}
			var displayName = StringTools.trim(converted.songName) == StringTools.trim(nativeSongName)
				? 'null' : converted.songName;
			// V-Slice stores vocal ownership as character ids while the audio folder
			// stores one Voices-<id> file per stem. Enumerate the actual files in a
			// stable order, then write only destination-safe basenames into the native
			// chart. The source paths remain in this in-memory import plan and are never
			// written to donor charts or destination metadata.
			var splitVocalStems:Array<Dynamic> = [];
			var splitDestinations:Map<String, Bool> = new Map<String, Bool>();
			if (audioFolder != null && FileSystem.isDirectory(audioFolder)) {
				var audioEntries:Array<String> = [];
				try {
					for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(audioFolder)))
						audioEntries.push(entry);
				} catch (_:Dynamic) {}
				audioEntries.sort(function(a, b) {
					var lowerCompare = Reflect.compare(a.toLowerCase(), b.toLowerCase());
					return lowerCompare == 0 ? Reflect.compare(a, b) : lowerCompare;
				});
				for (entry in audioEntries) {
					var lowerEntry = entry.toLowerCase();
					if (!(lowerEntry.startsWith('voices-') || lowerEntry.startsWith('voices_'))
						|| !(lowerEntry.endsWith('.ogg') || lowerEntry.endsWith('.wav') || lowerEntry.endsWith('.mp3')))
						continue;
					var extensionStart = entry.lastIndexOf('.');
					var extension = extensionStart > 0 ? entry.substr(extensionStart) : '.ogg';
					var stemIdEnd = extensionStart > 7 ? extensionStart : entry.length;
					var stemId = entry.substr(7, stemIdEnd - 7);
					if (StringTools.trim(stemId) == '')
						continue;
					var destination = VSliceImporter.nativeVocalStemFile(stemId, extension);
					var destinationKey = destination.toLowerCase();
					var duplicateIndex = 2;
					while (splitDestinations.exists(destinationKey)) {
						var dot = destination.lastIndexOf('.');
						var base = dot > 0 ? destination.substr(0, dot) : destination;
						var ext = dot > 0 ? destination.substr(dot) : extension;
						destination = base + '-' + duplicateIndex++ + ext;
						destinationKey = destination.toLowerCase();
					}
					splitDestinations.set(destinationKey, true);
						splitVocalStems.push({
							source: Path.join([audioFolder, entry]),
							destination: destination,
							id: stemId,
							role: 'shared'
						});
					}
				}
				splitVocalStems = selectVSliceVocalStems(metadata, splitVocalStems, diagnostics, variation);
				var nativeVocalMetadata:Array<Dynamic> = [];
			for (stem in splitVocalStems)
				nativeVocalMetadata.push({id:Reflect.field(stem, 'id'), role:Reflect.field(stem, 'role'), file:Reflect.field(stem, 'destination')});
			for (convertedChart in convertedCharts)
				if (convertedChart != null && convertedChart.chart != null
					&& Reflect.field(convertedChart.chart, 'song') != null) {
					convertedChart.chart.song.song = nativeSongName;
					// A V-Slice metadata-only vocal list has no usable path until the
					// audio folder is inspected. Prefer actual files and retain legacy
					// Voices.ogg behaviour when no split stems exist.
					Reflect.setField(convertedChart.chart.song, 'vocalStems', splitVocalStems.length == 0 ? null : nativeVocalMetadata);
					if (splitVocalStems.length > 0)
						Reflect.setField(convertedChart.chart.song, 'needsVoices', true);
				}
			var songData:SongImport = {
				name: nativeSongName,
				p1: nativePlayer,
				p2: nativeOpponent,
				gf: nativeGirlfriend,
				stage: nativeStage,
				ui: chartFieldString(firstSong, 'uiType', 'normal'),
				cutscene: chartFieldString(firstSong, 'cutsceneType', 'none'),
				category: 'Imported', isHey: false, isCheer: false, isMoody: false, isSpooky: false,
				stageID: stageResolution == null ? 0 : stageResolution.stageID,
				week: -1, char: nativeOpponent, display: displayName,
				inst: findVSliceInstrumental(audioFolder, metadata, diagnostics),
				voices: splitVocalStems.length == 0 ? findVSliceVoices(audioFolder, diagnostics) : null,
				dialog: null, modchart: null,
				diffFiles: [metadataPath, chartPath],
				convertedCharts: convertedCharts,
				noteDefinitions: converted.noteDefinitions,
				convertedCharacters: convertedCharacters,
				freeplayIconSource: findVSliceFreeplayIcon(root, opponentReference),
				convertedStage: convertedStage,
				convertedNoteStyle: convertedNoteStyle,
				convertedNoteStyles: convertedNoteStyles,
				vSliceRoot: root.contentRoot == null || StringTools.trim(root.contentRoot) == '' ? root.root : root.contentRoot,
				engine: root.engine,
				diagnostics: diagnostics
			};
			if (validModuleName(folderName))
				Reflect.setField(songData, 'sourceFolder', folderName);
			if (variationSuffix != '')
				Reflect.setField(songData, 'destinationFolder', nativeSongName);
			if (convertedStages.length > 0)
				Reflect.setField(songData, 'convertedStages', convertedStages);
			if (eventVideoAssets.length > 0)
				Reflect.setField(songData, 'eventVideoAssets', eventVideoAssets);
			if (splitVocalStems.length > 0)
				Reflect.setField(songData, 'vocalStems', splitVocalStems);
			if (validateAndRecordSongImport(rejections, songData, songData.sourceRoot,
				dataFolder, root.engine)) {
				result.push(songData);
				var sourceInfo:SongImportSource = {song:audioFolder, data:dataFolder,
					destination:importSongFolderName(songData)};
				songData.importSourceInfo = sourceInfo;
				if (sourcePaths != null)
					sourcePaths.set(StringTools.trim(songData.name).toLowerCase(), sourceInfo);
			}
			}
		}
		return result;
	}
	#end

	#if sys
	/** Format one pure Codename finding for the importer plan/report.  Same
		layout as the V-Slice appender so the scan report reads identically. */
	static function appendCodenameDiagnostic(diagnostics:Array<String>, finding:CodenameImporter.CodenameDiagnostic):Void {
		if (diagnostics == null || finding == null)
			return;
		var code = finding.code == null || StringTools.trim(finding.code) == '' ? 'conversion' : finding.code;
		var message = finding.message == null ? '' : finding.message;
		var text = '[' + code + '] ' + message;
		if (finding.path != null && StringTools.trim(finding.path) != '')
			text += ' (' + finding.path + ')';
		if (finding.difficulty != null && StringTools.trim(finding.difficulty) != '')
			text += ' [' + finding.difficulty + ']';
		if (diagnostics.indexOf(text) == -1)
			diagnostics.push(text);
	}

	static function appendCodenameDiagnostics(diagnostics:Array<String>, findings:Array<CodenameImporter.CodenameDiagnostic>):Void {
		if (findings == null)
			return;
		for (finding in findings)
			appendCodenameDiagnostic(diagnostics, finding);
	}

	/**
		Codename song discovery.

		A source mod keeps meta.json/charts under <root>/songs/<song>/.  A
		compiled release keeps the real content below mods/<name>/ and only
		engine sample songs in its embedded assets tree, so discovery recovers
		the mods folders and ignores the samples.
	*/
	static function discoverCodenameSongImports(root:ImportRootScanner.ImportRoot,
		?sourcePaths:Map<String, SongImportSource>,
		?rejections:SongImportRejectionCollector):Array<SongImport> {
		var result:Array<SongImport> = [];
		if (root == null)
			return result;
		var bases:Array<ImportRootScanner.ImportRoot> = [];
		// A compiled release keeps the real mod content below mods/<name>/ and
		// only engine sample songs in its embedded assets tree, so the mods
		// folders win whenever the release carries one.
		var modFolders = ImportRootScanner.codenameModsFolders(root.root);
		// Only a compiled Codename installation explicitly discovered with its
		// own logical data/images roots may supply a base-character dependency.
		// Standalone mods and sibling mod folders never become search roots.
		var engineBaseAssetRoot:String = null;
		if (modFolders.length > 0 && root.contentRoot != null && root.contentRoot != ''
			&& root.data != null && root.data != '' && root.images != null && root.images != ''
			&& importPathIsWithin(root.data, root.contentRoot)
			&& importPathIsWithin(root.images, root.contentRoot))
			engineBaseAssetRoot = root.contentRoot;
		if (modFolders.length > 0) {
			for (modFolder in modFolders) {
				bases.push({
					root: modFolder,
					contentRoot: modFolder,
					engine: root.engine,
					confidence: root.confidence,
					evidence: root.evidence,
					data: findChildDirectory(modFolder, 'data'),
					audio: findChildDirectory(modFolder, 'songs'),
					images: findChildDirectory(modFolder, 'images'),
					shared: '',
					scripts: findChildDirectory(modFolder, 'scripts'),
					paths: {
						data: findChildDirectory(modFolder, 'data'),
						audio: findChildDirectory(modFolder, 'songs'),
						images: findChildDirectory(modFolder, 'images'),
						shared: '',
						scripts: findChildDirectory(modFolder, 'scripts')
					}
				});
			}
		} else if (root.audio != '' && ImportRootScanner.hasCodenameSongs(root.audio)) {
			bases.push(root);
		}
		for (base in bases) {
			if (importWorkCancelled())
				break;
			for (song in discoverCodenameSongsFromBase(base, sourcePaths, engineBaseAssetRoot, rejections)) {
				// A compiled release with one mod has historically used the
				// selected release as its owner. Keep that stable across refreshes;
				// sibling mods need their own roots so same-named songs coexist.
				if (modFolders.length == 1)
					song.sourceRoot = root.root;
				result.push(song);
			}
		}
		return result;
	}

	/** Walk one Codename base's bounded script trees and name the translation
		gap once per file.  Deliberately limited to data scripts/states and the
		global module; never the media trees. */
	static function appendCodenameRootScriptDiagnostics(base:ImportRootScanner.ImportRoot,
		diagnostics:Array<String>):Void {
		if (base == null || base.data == null || base.data == '')
			return;
		var budget:Array<Int> = [12];
		for (relative in ['scripts', 'states'])
			collectCodenameScriptDiagnostics(Path.join([base.data, relative]), diagnostics, budget, 0);
		var globalPath = findImportFile(base.data, ['global.hx']);
		if (globalPath != null && budget[0] > 0) {
			budget[0]--;
			diagnostics.push('[codename-script] Codename Haxe script is not translated: ' + globalPath
				+ ' (its globals are not available to the native runtime).');
		}
	}

	static function collectCodenameScriptDiagnostics(folder:String, diagnostics:Array<String>,
		budget:Array<Int>, depth:Int):Void {
		if (budget[0] <= 0 || depth > 2 || folder == '' || !FileSystem.isDirectory(folder))
			return;
		try {
			for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(folder))) {
				if (budget[0] <= 0)
					return;
				var child = Path.join([folder, entry]);
				if (FileSystem.isDirectory(child)) {
					collectCodenameScriptDiagnostics(child, diagnostics, budget, depth + 1);
					continue;
				}
				if (!StringTools.endsWith(entry.toLowerCase(), '.hx'))
					continue;
				budget[0]--;
				diagnostics.push('[codename-script] Codename Haxe script is not translated: ' + child
					+ ' (native gameplay does not depend on it).');
			}
		} catch (_:Dynamic) {}
	}

	/** Walk one Codename content base's songs/<song> folders. */
	static function discoverCodenameSongsFromBase(base:ImportRootScanner.ImportRoot,
		?sourcePaths:Map<String, SongImportSource>, ?engineBaseAssetRoot:String,
		?rejections:SongImportRejectionCollector):Array<SongImport> {
		var result:Array<SongImport> = [];
		var songsRoot = base.audio;
		if (songsRoot == null || songsRoot == '' || !FileSystem.isDirectory(songsRoot))
			return result;
		var rootScriptDiagnostics:Array<String> = [];
		appendCodenameRootScriptDiagnostics(base, rootScriptDiagnostics);
		var rootScriptDiagnosticsAdded = false;
		var folders:Array<String>;
		try {
			folders = ImportDirectoryListing.normalize(FileSystem.readDirectory(songsRoot));
		} catch (_:Dynamic) {
			return result;
		}
		folders.sort(function(a, b) {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (folderName in folders) {
			if (importWorkCancelled())
				break;
			yieldImportWork(true);
			var songFolder = Path.join([songsRoot, folderName]);
			if (!FileSystem.isDirectory(songFolder))
				continue;
			if (!ImportRootScanner.isCodenameSongFolder(songFolder))
				continue;
			var metaPath = findImportFile(songFolder, ['meta.json']);
			if (metaPath == null)
				continue;
			var meta:Dynamic = null;
			var diagnostics:Array<String> = [];
			try {
				meta = CoolUtil.parseJson(File.getContent(metaPath));
			} catch (error:Dynamic) {
				diagnostics.push('[invalid-metadata] Could not parse Codename meta.json: ' + metaPath
					+ ' (' + Std.string(error) + ')');
				continue;
			}
			if (!CodenameImporter.isCodenameMeta(meta)) {
				diagnostics.push('[invalid-metadata] Codename meta.json is missing difficulties/bpm/stepsPerBeat: ' + metaPath);
				continue;
			}
			var declaredVariants:Dynamic = Reflect.field(meta, 'variants');
			if (Std.isOfType(declaredVariants, Array) && (cast declaredVariants:Array<Dynamic>).length > 0)
				diagnostics.push('[codename-meta-variant-unsupported] Authored metadata declares variants; '
					+ 'the native chart importer selects base difficulty files only: ' + songFolder);
			var configDefaults:Dynamic = {};
			// Codename reads mod flags from data/config/modpack.ini and source
			// flags from data/config/flags.ini. Keep legacy root flags visible.
			var codenameFlagPaths = [Path.join([base.data, 'config', 'modpack.ini']),
				Path.join([base.data, 'config', 'flags.ini']),
				Path.join([base.contentRoot, 'flags.ini']),
				Path.join([base.root, 'flags.ini'])];
			for (flagsPath in codenameFlagPaths)
				if (isImportFile(flagsPath) && CodenameScriptDiscovery.withinRoot(base.root, flagsPath)) {
					try configDefaults = CodenameSongMetadata.configDefaults(File.getContent(flagsPath))
					catch (error:Dynamic)
						diagnostics.push('[codename-meta-flags] Could not parse Codename config: '
							+ flagsPath + ' (' + Std.string(error) + ')');
					diagnostics.push('[codename-meta-flags-unsupported] Other Codename config overrides '
						+ 'may affect engine systems outside song metadata: ' + flagsPath);
					break;
				}
			// Character.FALLBACK_CHARACTER is linked to DEFAULT_CHARACTER in
			// Codename. Read the first package flag that explicitly sets it; the
			// engine default is bf only when no authored override exists.
			var codenameFallbackReference = 'bf';
			var codenameFallbackConfigured = false;
			for (flagsPath in codenameFlagPaths)
				if (!codenameFallbackConfigured && isImportFile(flagsPath)
					&& CodenameScriptDiscovery.withinRoot(base.root, flagsPath))
					try {
						var flagDefaults = CodenameSongMetadata.configDefaults(File.getContent(flagsPath));
						if (Reflect.hasField(flagDefaults, 'characterFallback')) {
							codenameFallbackReference = StringTools.trim(Std.string(
								Reflect.field(flagDefaults, 'characterFallback')));
							codenameFallbackConfigured = true;
						}
					} catch (_:Dynamic) {}
			if (codenameFallbackReference != ''
				&& !CodenameScriptDiscovery.safeRelativeName(codenameFallbackReference)) {
				diagnostics.push('[codename-character-fallback-unsupported] Codename DEFAULT_CHARACTER value "'
					+ codenameFallbackReference + '" cannot be represented safely by the importer.');
				codenameFallbackReference = '';
			} else if (codenameFallbackConfigured && codenameFallbackReference == '') {
				diagnostics.push('[codename-character-fallback-unsupported] Codename DEFAULT_CHARACTER is empty; '
					+ 'the authored fallback cannot be represented safely by the importer.');
			}
			var chartsFolder = findChildDirectory(songFolder, 'charts');
			if (chartsFolder == '')
				continue;
			// The song's shared event sidecar merges with every chart's own
			// events, exactly as the Codename runtime plays them.
			var sidecarPath = findImportFile(songFolder, ['events.json']);
			var sidecar:Dynamic = null;
			if (sidecarPath != null) {
				try {
					sidecar = CoolUtil.parseJson(File.getContent(sidecarPath));
				} catch (error:Dynamic) {
					diagnostics.push('[invalid-event-sidecar] Could not parse Codename events.json: '
						+ sidecarPath + ' (' + Std.string(error) + ')');
				}
			}
			var convertedCharts:Array<ConvertedSongChart> = [];
			// Note definitions are shared across one song's difficulties so a
			// kind keeps the same custom-note marker in every chart.
			var noteDefinitions:Array<Dynamic> = [];
			var noteKindIndexes:Map<String, Int> = new Map<String, Int>();
			var chartDiagnostics:Array<String> = [];
			var authoredStage = '';
			var authoredStages:Dynamic = {};
			var displayName = StringTools.trim(meta == null ? '' : Std.string(Reflect.field(meta, 'displayName')));
			var chartPaths:Array<String> = [metaPath];
			var chartEntries:Array<String> = [];
			var chartDifficulties:Array<String> = [];
			for (entry in safeSortedDirectoryListing(chartsFolder))
				if (StringTools.endsWith(entry.toLowerCase(), '.json')) {
					var candidatePath = Path.join([chartsFolder, entry]);
					try {
						var candidate:Dynamic = haxe.Json.parse(File.getContent(candidatePath));
						if (!CodenameImporter.isCodenameChart(candidate)
							&& !CodenameImporter.isEmbeddedSectionChart(candidate)) {
							chartDiagnostics.push('[codename-nonchart-json] Ignored JSON file without Codename chart structure: '
								+ candidatePath);
							continue;
						}
					} catch (error:Dynamic) {
						chartDiagnostics.push('[codename-chart-conversion] Could not parse Codename chart '
							+ candidatePath + ': ' + Std.string(error));
						continue;
					}
					chartEntries.push(entry);
					chartDifficulties.push(entry.substr(0, entry.lastIndexOf('.')));
				}
			var resolvedMetaEntries:Dynamic = {};
			for (entry in chartEntries) {
				if (!StringTools.endsWith(entry.toLowerCase(), '.json'))
					continue;
				var chartPath = Path.join([chartsFolder, entry]);
				var difficulty = entry.substr(0, entry.lastIndexOf('.'));
				var converted:CodenameImporter.CodenameConversionResult;
				var selectedMetaFile = 'meta.json';
				var selectedMeta:Dynamic = meta;
				var difficultyMetaName = 'meta-' + difficulty + '.json';
				var difficultyMetaPath = Path.join([songFolder, difficultyMetaName]);
				if (CodenameScriptDiscovery.safeName(difficulty)
					&& isImportFile(difficultyMetaPath)
					&& CodenameScriptDiscovery.withinRoot(base.contentRoot, difficultyMetaPath)) {
					try {
						selectedMeta = CoolUtil.parseJson(File.getContent(difficultyMetaPath));
						selectedMetaFile = difficultyMetaName;
					} catch (error:Dynamic) {
						chartDiagnostics.push('[codename-meta-difficulty] Could not parse '
							+ difficultyMetaPath + '; using meta.json (' + Std.string(error) + ')');
					}
				}
				try {
					var sourceChart:Dynamic = haxe.Json.parse(File.getContent(chartPath));
					var inlineMeta:Dynamic = Reflect.field(sourceChart, 'meta');
					if (inlineMeta != null && Std.isOfType(Reflect.field(inlineMeta, 'variants'), Array)
						&& (cast Reflect.field(inlineMeta, 'variants'):Array<Dynamic>).length > 0)
						chartDiagnostics.push('[codename-meta-variant-unsupported] Chart metadata declares variants '
							+ 'without variant chart selection: ' + chartPath);
					var effectiveMeta = CodenameSongMetadata.resolve(folderName,
						selectedMeta, inlineMeta, chartDifficulties, configDefaults);
					if (CodenameImporter.isEmbeddedSectionChart(sourceChart)) {
						var embedded = CodenameImporter.convertEmbeddedSectionChart(sourceChart,
							difficulty, sidecar, chartPath);
						collectSongNoteDefinitions(embedded.chart, noteDefinitions);
						converted = {songName:folderName, displayName:displayName,
							originalMeta:meta, sourcePath:chartPath, charts:[embedded],
							noteDefinitions:noteDefinitions, diagnostics:embedded.diagnostics};
					} else
						converted = CodenameImporter.convertFiles(metaPath, chartPath, difficulty,
							 songFolder, sidecar, noteDefinitions, noteKindIndexes, effectiveMeta);
					Reflect.setField(resolvedMetaEntries, difficulty, {selectedFile:selectedMetaFile,
						fileMeta:selectedMeta, inlineMeta:inlineMeta,
						configDefaults:configDefaults, resolved:effectiveMeta});
				} catch (error:Dynamic) {
					chartDiagnostics.push('[codename-chart-conversion] Could not convert Codename chart '
						+ chartPath + ': ' + Std.string(error));
					continue;
				}
				appendCodenameDiagnostics(chartDiagnostics, converted.diagnostics);
				for (chart in converted.charts) {
					convertedCharts.push({
						difficulty: chart.difficulty,
						fileName: chart.fileName,
						source: chartPath,
						chart: chart.chart,
						noteTypes: chart.noteTypes == null ? [] : chart.noteTypes.copy(),
						cameraLines: chart.cameraLines,
						authoredSongTitle: chart.authoredSongTitle == true
					});
					if (CodenameScriptDiscovery.safeName(chart.difficulty) && chart.chart != null
						&& Reflect.field(chart.chart, 'song') != null) {
						var chartStage = chartFieldString(Reflect.field(chart.chart, 'song'), 'stage', '');
						if (CodenameScriptDiscovery.safeName(chartStage))
							Reflect.setField(authoredStages, chart.difficulty, chartStage);
					}
					if (authoredStage == '' && chart.chart != null
						&& Reflect.field(chart.chart, 'song') != null)
						authoredStage = chartFieldString(Reflect.field(chart.chart, 'song'), 'stage', '');
				}
				chartPaths.push(chartPath);
			}
			if (convertedCharts.length == 0) {
				diagnostics.push('[codename-charts-missing] The Codename song folder has no convertible chart: '
					+ songFolder);
				continue;
			}
			var resolvedSongMeta:Dynamic;
			try resolvedSongMeta = CodenameSongMetadata.createResolved(folderName,
				chartDifficulties, resolvedMetaEntries)
			catch (error:Dynamic) {
				diagnostics.push('[codename-song-meta] Could not preserve resolved song metadata: '
					+ Std.string(error));
				continue;
			}
			diagnostics = chartDiagnostics.concat(diagnostics);
			// Keep each song script in its owning namespace for the Codename
			// compatibility runtime. Individual unsupported constructs are reported
			// by its parser when that script is selected.
			var scriptDifficulties:Array<String> = [];
			for (chart in convertedCharts)
				if (chart != null && scriptDifficulties.indexOf(chart.difficulty) < 0)
					scriptDifficulties.push(chart.difficulty);
			for (script in CodenameScriptDiscovery.discover(base.contentRoot, folderName, scriptDifficulties, null))
				diagnostics.push('[codename-song-script] Codename script ' + script.relative
					+ ' is preserved for the selected song compatibility runtime.');
			if (!rootScriptDiagnosticsAdded && rootScriptDiagnostics.length > 0) {
				for (scriptDiagnostic in rootScriptDiagnostics)
					diagnostics.push(scriptDiagnostic);
				rootScriptDiagnosticsAdded = true;
			}

			// Codename keeps audio in songs/<song>/song/ (Inst plus split stems).
			var audioFolder = findNamedDirectory(songFolder, 'song');
			if (audioFolder == null)
				audioFolder = songFolder;
			var instPath = findImportFile(audioFolder, ['Inst.ogg', 'inst.ogg']);
			if (instPath == null)
				instPath = findImportAudio(audioFolder);
			// Split stems: Voices-Player.ogg / Voices-Opponent.ogg are the
			// Codename convention; Voices-<character>.ogg also occurs.  Roles
			// follow the authored suffix so the native chart records which stem
			// belongs to which side.
			var splitVocalStems:Array<Dynamic> = [];
			if (audioFolder != null && FileSystem.isDirectory(audioFolder)) {
				var audioEntries:Array<String> = [];
				try {
					for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(audioFolder)))
						audioEntries.push(entry);
				} catch (_:Dynamic) {}
				audioEntries.sort(function(a, b) {
					var lowerCompare = Reflect.compare(a.toLowerCase(), b.toLowerCase());
					return lowerCompare == 0 ? Reflect.compare(a, b) : lowerCompare;
				});
				for (entry in audioEntries) {
					var lowerEntry = entry.toLowerCase();
					if (!(lowerEntry.startsWith('voices-') || lowerEntry.startsWith('voices_'))
						|| !(lowerEntry.endsWith('.ogg') || lowerEntry.endsWith('.wav') || lowerEntry.endsWith('.mp3')))
						continue;
					var extensionStart = entry.lastIndexOf('.');
					var extension = extensionStart > 0 ? entry.substr(extensionStart) : '.ogg';
					var stemIdEnd = extensionStart > 7 ? extensionStart : entry.length;
					var stemId = entry.substr(7, stemIdEnd - 7);
					if (StringTools.trim(stemId) == '')
						continue;
					var stemRole = 'shared';
					var stemLower = stemId.toLowerCase();
					if (stemLower == 'player' || stemLower.endsWith('-player') || stemLower.endsWith('_player'))
						stemRole = 'player';
					else if (stemLower == 'opponent' || stemLower.endsWith('-opponent') || stemLower.endsWith('_opponent'))
						stemRole = 'opponent';
					splitVocalStems.push({
						source: Path.join([audioFolder, entry]),
						destination: 'Voices-' + stemId + extension,
						id: stemId,
						role: stemRole
					});
				}
			}
			var nativeVocalMetadata:Array<Dynamic> = [];
			for (stem in splitVocalStems)
				nativeVocalMetadata.push({id:Reflect.field(stem, 'id'), role:Reflect.field(stem, 'role'), file:Reflect.field(stem, 'destination')});
			for (convertedChart in convertedCharts)
				if (convertedChart != null && convertedChart.chart != null
					&& Reflect.field(convertedChart.chart, 'song') != null) {
					Reflect.setField(convertedChart.chart.song, 'vocalStems',
						splitVocalStems.length == 0 ? null : nativeVocalMetadata);
					if (splitVocalStems.length > 0)
						Reflect.setField(convertedChart.chart.song, 'needsVoices', true);
				}

			var firstSong:Dynamic = convertedCharts[0].chart.song;
			var playerReference = chartFieldString(firstSong, 'player1', 'bf');
			var opponentReference = chartFieldString(firstSong, 'player2', 'dad');
			var girlfriendReference = chartFieldString(firstSong, 'gf', 'gf');
			var stageReference = chartFieldString(firstSong, 'stage', 'stage');

			// Codename health icon metadata: meta.icon names the opponent's
			// icon, and the character XMLs repeat it with their color.  The
			// icon/color ride along on the converted characters' registry rows,
			// which is where Freeplay reads presentation data.
			var metaColor = meta == null ? null : Reflect.field(meta, 'color');

			// Convert donor character definitions.  Codename references can also
			// be destination-native ids (boyfriend/dad/gf), which need no donor
			// definition and keep their native names.
			var convertedCharacters:Array<VSliceCharacterImport> = [];
			var codenameIdentityCollision = false;
			var characterOffsets:Map<String, Array<Float>> = new Map<String, Array<Float>>();
			var characterPlayerOffsets:Map<String, Bool> = new Map<String, Bool>();
			var characterReferences:Array<{id:String, iconRequired:Bool, roles:Array<String>}> = [];
			var characterIndexes:Map<String, Int> = new Map<String, Int>();
			var addCharacterReference = function(reference:String, iconRequired:Bool, role:String):Void {
				var id = reference == null ? '' : StringTools.trim(reference);
				var folded = id.toLowerCase();
				if (id == '' || folded == 'none' || folded == 'null') return;
				var roleName = role == null || StringTools.trim(role) == '' ? 'extra' : StringTools.trim(role);
				if (characterIndexes.exists(id)) {
					var existing = characterReferences[characterIndexes.get(id)];
					if (iconRequired) existing.iconRequired = true;
					if (existing.roles.indexOf(roleName) < 0) existing.roles.push(roleName);
					return;
				}
				characterIndexes.set(id, characterReferences.length);
				characterReferences.push({id:id, iconRequired:iconRequired, roles:[roleName]});
			};
			// Preserve first-seen difficulty, strumline and occurrence order.
			// The primary three native actors are only a presentation subset.
			for (convertedChart in convertedCharts) {
				if (convertedChart == null) continue;
				if (convertedChart.cameraLines != null)
					for (line in convertedChart.cameraLines) {
						if (line == null) continue;
						var ids:Dynamic = Reflect.field(line, 'characters');
						if (!Std.isOfType(ids, Array)) continue;
						var role:Dynamic = Reflect.field(line, 'role');
						var roleName = Std.isOfType(role, String) ? StringTools.trim(cast role) : 'extra';
						var iconRequired = roleName == 'player' || roleName == 'opponent';
						for (id in (cast ids:Array<String>))
							addCharacterReference(id, iconRequired, roleName);
					}
				if (convertedChart.chart == null || Reflect.field(convertedChart.chart, 'song') == null)
					continue;
				var difficultySong = convertedChart.chart.song;
				addCharacterReference(chartFieldString(difficultySong, 'player1', ''), true, 'player');
				addCharacterReference(chartFieldString(difficultySong, 'player2', ''), true, 'opponent');
				addCharacterReference(chartFieldString(difficultySong, 'gf',
					chartFieldString(difficultySong, 'gfVersion', '')), false, 'gf');
				// Codename's Change Character event can introduce a character that
				// does not occur on any chart strumline. Those XML definitions are
				// still part of the song's runtime dependencies and need owner-scoped
				// conversion before the event can activate them.
				var eventGroups:Dynamic = Reflect.field(difficultySong, 'events');
				if (!Std.isOfType(eventGroups, Array)) continue;
				for (group in (cast eventGroups:Array<Dynamic>)) {
					if (!Std.isOfType(group, Array)) continue;
					var groupRows:Array<Dynamic> = cast group;
					if (groupRows.length < 2 || !Std.isOfType(groupRows[1], Array)) continue;
					for (eventRow in (cast groupRows[1]:Array<Dynamic>)) {
						if (!Std.isOfType(eventRow, Array)) continue;
						var row:Array<Dynamic> = cast eventRow;
						if (row.length < 5 || row[4] == null
							|| Reflect.field(row[4], 'engine') != 'codename'
							|| StringTools.trim(Std.string(Reflect.field(row[4], 'name'))).toLowerCase() != 'change character')
							continue;
						var params:Dynamic = Reflect.field(row[4], 'params');
						if (!Std.isOfType(params, Array) || (cast params:Array<Dynamic>).length < 4) continue;
						var authoredParams:Array<Dynamic> = cast params;
						var lineIndex = Std.parseInt(Std.string(authoredParams[1]));
						var iconRequired = false;
						var eventRole = 'event';
						if (lineIndex != null && convertedChart.cameraLines != null
							&& lineIndex >= 0 && lineIndex < convertedChart.cameraLines.length) {
							var eventLine = convertedChart.cameraLines[lineIndex];
							var role = eventLine == null ? null : Reflect.field(eventLine, 'role');
							if (Std.isOfType(role, String)) eventRole = cast role;
							iconRequired = eventRole == 'player' || eventRole == 'opponent';
						}
						addCharacterReference(Std.string(authoredParams[3]), iconRequired, eventRole);
					}
				}
			}
			// If a chart omits a role's character list, retain the converter's
			// native fallback identity without fabricating a camera occurrence.
			addCharacterReference(playerReference, true, 'player');
			addCharacterReference(opponentReference, true, 'opponent');
			addCharacterReference(girlfriendReference, false, 'gf');
			if (codenameFallbackReference != '')
				addCharacterReference(codenameFallbackReference, true, 'fallback');
			var nativeNames:Map<String, String> = new Map<String, String>();
			var missingCharacterReferences:Array<{id:String, iconRequired:Bool, roles:Array<String>}> = [];
			for (characterReference in characterReferences) {
				var reference = characterReference.id;
				var key = reference.toLowerCase();
				if (key == '' || key == 'none' || key == 'null')
					continue;
				var definitionPath = findCodenameDefinitionXml(base.data, 'characters', reference);
				if (definitionPath == '') {
					// A donor XML with an id such as bf or boyfriend is authored
					// content. Only use the destination's built-in actor when this
					// owner has no matching definition.
					if (vSliceNativeCharacterReference(reference)) {
						diagnostics.push('[codename-native-character-fallback] No owner XML for "'
							+ reference + '"; using the destination native actor.');
						continue;
					}
					missingCharacterReferences.push(characterReference);
					continue;
				}
				try {
					// Girlfriend-only definitions do not need a donor health icon;
					// player/opponent ids do (HealthIcon is a HUD element here).
					var healthIconRequired = characterReference.iconRequired;
					var conversion = CodenameImporter.convertCharacterXml(definitionPath,
						base.contentRoot, reference, healthIconRequired, Std.string(metaColor), reference);
					var nativeKey = conversion.name;
					if (nativeNames.exists(nativeKey) && nativeNames.get(nativeKey) != reference) {
						diagnostics.push('[codename-character-name-collision] Distinct authored character ids "'
							+ nativeNames.get(nativeKey) + '" and "' + reference
							+ '" produce the same native name "' + conversion.name + '".');
						codenameIdentityCollision = true;
						continue;
					}
					nativeNames.set(nativeKey, reference);
					convertedCharacters.push({
						reference: reference,
						source: definitionPath,
						conversion: conversion
					});
					appendCodenameDiagnostics(diagnostics, conversion.diagnostics);
					// Retain the existing native placement representation. Donor
					// flip-dependent global offsets need the character adapter;
					// they must not be assumed identical to world coordinates.
					var codenameCharMeta:Dynamic = Reflect.field(conversion.registryEntry, 'codenameCharacter');
					if (codenameCharMeta != null) {
						var ownX = Std.parseFloat(Std.string(Reflect.field(codenameCharMeta, 'x')));
						var ownY = Std.parseFloat(Std.string(Reflect.field(codenameCharMeta, 'y')));
						for (slot in ['bf', 'dad', 'gf']) {
							var referenceForSlot = slot == 'bf' ? playerReference : (slot == 'gf' ? girlfriendReference : opponentReference);
							if (reference != StringTools.trim(referenceForSlot)) continue;
							characterOffsets.set(slot, [Math.isNaN(ownX) ? 0 : ownX, Math.isNaN(ownY) ? 0 : ownY]);
							characterPlayerOffsets.set(slot, Reflect.field(codenameCharMeta, 'playerOffsets') == true);
						}
					}
				} catch (error:Dynamic) {
					diagnostics.push('[character-conversion] Could not convert Codename character "'
						+ reference + '": ' + Std.string(error));
				}
			}
			var fallbackDefinitionPath = codenameFallbackReference == '' ? ''
				: findCodenameDefinitionXml(base.data, 'characters', codenameFallbackReference);
			var codenameFallbackNativeName:Null<String> = codenameConvertedCharacterName(
				convertedCharacters, codenameFallbackReference);
			if (codenameFallbackNativeName == null && fallbackDefinitionPath == ''
				&& vSliceNativeCharacterReference(codenameFallbackReference))
				codenameFallbackNativeName = vSliceNativeCharacterName(convertedCharacters,
					codenameFallbackReference);
			if (codenameFallbackNativeName == null && fallbackDefinitionPath == ''
				&& engineBaseAssetRoot != null
				&& CodenameScriptDiscovery.resolveScopedRelative(engineBaseAssetRoot,
					'data/characters/' + codenameFallbackReference + '.xml') != null)
				// The XML will be receipt-materialized into this selected owner by
				// importVSliceVisuals. Keep its authored identity as the host name;
				// runtime construction supplies the source XML directly.
				codenameFallbackNativeName = codenameFallbackReference;
			if (codenameFallbackNativeName != null
				&& (!CodenameScriptDiscovery.safeName(codenameFallbackNativeName)
					|| StringTools.trim(codenameFallbackNativeName) == ''))
				codenameFallbackNativeName = null;
			var sourceFallbackReferences:Map<String, Bool> = new Map<String, Bool>();
			for (missingReference in missingCharacterReferences) {
				var missingId = missingReference.id;
				if (codenameFallbackNativeName != null) {
					sourceFallbackReferences.set(missingId, true);
					diagnostics.push('[codename-character-source-fallback] Codename source fallback for missing "'
						+ missingId + '" in role(s) ' + missingReference.roles.join(', ')
						+ ' uses DEFAULT_CHARACTER "' + codenameFallbackReference + '" mapped to native "'
						+ codenameFallbackNativeName + '"; authored identity remains in the Codename camera metadata.');
				} else {
					var reason = codenameFallbackNativeName == null
						? 'source fallback "' + codenameFallbackReference + '" has no safe owner/native definition'
						: 'the missing id is itself DEFAULT_CHARACTER';
					diagnostics.push('[codename-character-fallback-unavailable] Codename character XML could not be found for "'
						+ missingId + '" in role(s) ' + missingReference.roles.join(', ') + '; ' + reason + '.');
				}
			}
			// A converted owner key must not also be the native/fallback name of
			// another authored reference. Native-only aliases can still share a
			// destination actor, but an owned key would make one id borrow the
			// other's donor definition.
			for (characterReference in characterReferences) {
				var reference = characterReference.id;
				if (sourceFallbackReferences.exists(reference)) continue;
				var definitionPath = findCodenameDefinitionXml(base.data, 'characters', reference);
				var resolvedName = codenameNativeCharacterName(convertedCharacters, reference,
					definitionPath != '', codenameFallbackReference, codenameFallbackNativeName);
				if (resolvedName == null) continue;
				if (nativeNames.exists(resolvedName) && nativeNames.get(resolvedName) != reference) {
					codenameIdentityCollision = true;
					diagnostics.push('[codename-character-name-collision] Authored character "'
						+ reference + '" resolves to owned native name "' + resolvedName
						+ '" belonging to "' + nativeNames.get(resolvedName) + '".');
				}
			}

			// Resolve each difficulty's authored stage independently. A same-donor
			// XML wins over native aliases. A missing owned stage is declared with
			// no implementation so runtime resolution retains its authored identity
			// and cannot borrow a sibling or global stage with the same name.
			var convertedStage:VSliceStageImport = null;
			var convertedStages:Array<VSliceStageImport> = [];
			var stageNames:Map<String, String> = new Map<String, String>();
			var ownedNativeStageNames:Map<String, String> = new Map<String, String>();
			var stagePlacementSignatures:Map<String, String> = new Map<String, String>();
			for (convertedChart in convertedCharts) {
				if (convertedChart == null || convertedChart.chart == null
					|| Reflect.field(convertedChart.chart, 'song') == null) continue;
				var stageSong:Dynamic = convertedChart.chart.song;
				var authoredStageId = chartFieldString(stageSong, 'stage', 'stage');
				var placementLines:Array<Dynamic> = [];
				if (convertedChart.cameraLines != null)
					for (line in convertedChart.cameraLines)
						placementLines.push({type:Reflect.field(line, 'type'),
							position:Reflect.field(line, 'position'), characters:Reflect.field(line, 'characters')});
				var placementSignature = haxe.Json.stringify({
					player:chartFieldString(stageSong, 'player1', 'bf'),
					opponent:chartFieldString(stageSong, 'player2', 'dad'),
					girlfriend:chartFieldString(stageSong, 'gf', 'gf'), lines:placementLines});
				if (stageNames.exists(authoredStageId)) {
					if (stagePlacementSignatures.get(authoredStageId) != placementSignature)
						diagnostics.push('[codename-stage-difficulty-placement] Stage "' + authoredStageId
							+ '" is shared by difficulties with different actor/strumline placements; '
							+ 'the generated native stage uses its first authored occurrence.');
					continue;
				}
				stagePlacementSignatures.set(authoredStageId, placementSignature);
				var resolvedStage = authoredStageId;
				var stageImport:VSliceStageImport = null;
				var stageDefinitionPath = findCodenameDefinitionXml(base.data, 'stages', authoredStageId);
				var stageScriptPath = CodenameScriptDiscovery.safeName(authoredStageId)
					? findImportFile(Path.join([base.data == null ? '' : base.data, 'stages']),
						[authoredStageId + '.hx', authoredStageId + '.hscript']) : null;
				if (stageScriptPath != null)
					diagnostics.push('[codename-stage-script] Codename stage script is not translated: '
						+ stageScriptPath + ' (the converted stage XML does not include its scripted visuals or callbacks).');
				var conversionFailed = false;
				if (stageDefinitionPath != '') {
					try {
						var stageCharacterOffsets:Map<String, Array<Float>> = new Map<String, Array<Float>>();
						var stagePlayerOffsets:Map<String, Bool> = new Map<String, Bool>();
						for (slot in ['bf', 'dad', 'gf']) {
							var actorReference = chartFieldString(stageSong,
								slot == 'bf' ? 'player1' : (slot == 'dad' ? 'player2' : 'gf'), slot);
							for (actor in convertedCharacters)
								if (actor.reference == actorReference) {
									var actorMeta:Dynamic = Reflect.field(actor.conversion.registryEntry, 'codenameCharacter');
									if (actorMeta != null) {
										var actorX = Std.parseFloat(Std.string(Reflect.field(actorMeta, 'x')));
										var actorY = Std.parseFloat(Std.string(Reflect.field(actorMeta, 'y')));
										stageCharacterOffsets.set(slot, [Math.isNaN(actorX) ? 0 : actorX,
											Math.isNaN(actorY) ? 0 : actorY]);
										stagePlayerOffsets.set(slot, Reflect.field(actorMeta, 'playerOffsets') == true);
									}
									break;
								}
							}
						var stageConversion = CodenameImporter.convertStageXml(stageDefinitionPath,
							base.contentRoot, authoredStageId, stageCharacterOffsets,
							convertedChart.cameraLines, stagePlayerOffsets);
						stageImport = {reference:authoredStageId, source:stageDefinitionPath, conversion:stageConversion};
						appendCodenameDiagnostics(diagnostics, stageConversion.diagnostics);
						resolvedStage = stageConversion.name;
					} catch (error:Dynamic) {
						conversionFailed = true;
						diagnostics.push('[stage-conversion] Could not convert Codename stage "'
							+ authoredStageId + '": ' + Std.string(error));
					}
				} else if (EngineCompat.isBuiltinStageReference(authoredStageId)) {
					var resolution = EngineCompat.resolveStageResolution(authoredStageId);
					if (resolution != null && resolution.nativeName != null)
						resolvedStage = resolution.nativeName;
				} else {
					conversionFailed = true;
					diagnostics.push('[missing-stage-definition] Codename stage XML could not be found for "'
						+ authoredStageId + '" under ' + Path.join([base.data == null ? '' : base.data, 'stages'])
						+ '; the authored stage remains unavailable in its owner namespace.');
				}
				if (conversionFailed && validModuleName(authoredStageId)
					&& CodenameScriptDiscovery.safeName(authoredStageId)) {
					stageImport = {reference:authoredStageId, source:stageDefinitionPath,
						conversion:{name:authoredStageId, registryValue:authoredStageId,
							hscript:null, assets:[], diagnostics:[]}};
				} else if (conversionFailed)
					diagnostics.push('[codename-stage-identity] Cannot safely declare authored stage "'
						+ authoredStageId + '" in its owner namespace.');
				if (stageImport != null) {
					var ownedName = stageImport.conversion.name;
					if (ownedNativeStageNames.exists(ownedName)
						&& ownedNativeStageNames.get(ownedName) != authoredStageId) {
						codenameIdentityCollision = true;
						diagnostics.push('[codename-stage-name-collision] Distinct authored stage ids "'
							+ ownedNativeStageNames.get(ownedName) + '" and "' + authoredStageId
							+ '" produce the same owned native name "' + ownedName + '".');
					} else ownedNativeStageNames.set(ownedName, authoredStageId);
					if (authoredStageId == stageReference && convertedStage == null)
						convertedStage = stageImport;
					else convertedStages.push(stageImport);
				}
				stageNames.set(authoredStageId, resolvedStage);
			}
			if (codenameIdentityCollision) {
				// A collision cannot be made safe by an unavailable declaration:
				// that declaration would itself resolve to the other owned stage.
				for (diagnostic in diagnostics)
					if (diagnostic.indexOf('[codename-character-name-collision]') == 0
						|| diagnostic.indexOf('[codename-stage-name-collision]') == 0)
						trace(diagnostic + ' Song import skipped.');
				continue;
			}
			var nativeStage = stageNames.exists(stageReference) ? stageNames.get(stageReference) : stageReference;
			// The native two-lane chart does not retain Codename's indexed
			// strumlines. Keep exact per-difficulty identities and camera offsets in
			// the selected namespace, including IDs not materialized as native actors.
			var authoredCamera:Dynamic = {};
			for (convertedChart in convertedCharts) {
				if (convertedChart == null || convertedChart.cameraLines == null
					|| !CodenameScriptDiscovery.safeName(convertedChart.difficulty)) continue;
				var cameraStage:Dynamic = Reflect.field(authoredStages, convertedChart.difficulty);
				if (!Std.isOfType(cameraStage, String) || !CodenameScriptDiscovery.safeName(cast cameraStage)) {
					diagnostics.push('[codename-camera-metadata] Missing safe authored stage for '
						+ convertedChart.difficulty + '; this difficulty has no camera metadata.');
					continue;
				}
				var cameraCharacters:Dynamic = {};
				var nativeCharacters:Dynamic = {};
				var missingCameraCharacters:Array<String> = [];
				for (line in convertedChart.cameraLines) {
					var ids:Array<String> = cast Reflect.field(line, 'characters');
					for (id in ids) {
						var charPath = findCodenameDefinitionXml(base.data, 'characters', id);
						if (!Reflect.hasField(nativeCharacters, id)) {
							// Keep the authored camera key while resolving the live actor by
							// exact converted identity or Codename's configured source fallback.
							var nativeName = codenameNativeCharacterName(convertedCharacters, id,
								charPath != '', codenameFallbackReference, codenameFallbackNativeName);
							if (nativeName != null && (!CodenameScriptDiscovery.safeName(nativeName)
								|| StringTools.trim(nativeName) == '')) nativeName = null;
							if (nativeName == null)
								diagnostics.push('[codename-native-character] No safe owned/native mapping for "'
									+ id + '" in ' + convertedChart.difficulty + '; the occurrence remains unresolved.');
							Reflect.setField(nativeCharacters, id, nativeName);
						}
						if (Reflect.hasField(cameraCharacters, id) || missingCameraCharacters.indexOf(id) >= 0)
							continue;
						if (charPath == '' || !CodenameScriptDiscovery.withinRoot(base.contentRoot, charPath)) {
							missingCameraCharacters.push(id);
							diagnostics.push('[codename-camera-metadata] Character camera XML unresolved for "' + id + '".');
							continue;
						}
						try Reflect.setField(cameraCharacters, id,
							CodenameImporter.cameraCharacterOffsets(File.getContent(charPath)))
						catch (error:Dynamic) {
							missingCameraCharacters.push(id);
							diagnostics.push('[codename-camera-metadata] Character camera XML invalid for "'
								+ id + '": ' + Std.string(error));
						}
					}
				}
				var stageCameraOffsets:Dynamic = {};
				var stageStartCamera:Dynamic = {x:null, y:null};
				var stagePlacement:Dynamic = null;
				var stageOffsetsKnown = false;
				var cameraStagePath = findCodenameDefinitionXml(base.data, 'stages', cast cameraStage);
				if (cameraStagePath != '' && CodenameScriptDiscovery.withinRoot(base.contentRoot, cameraStagePath)) {
					try {
						var stageCameraInfo = CodenameImporter.cameraStageInfo(File.getContent(cameraStagePath));
						stageCameraOffsets = Reflect.field(stageCameraInfo, 'offsets');
						stageStartCamera = Reflect.field(stageCameraInfo, 'startCamera');
						stagePlacement = Reflect.field(stageCameraInfo, 'placement');
						var companion = findImportFile(Path.join([base.data, 'stages']),
							[cameraStage + '.hx', cameraStage + '.hscript']);
						var companionInitialPlacementChange = false;
						var runtimeMutationHooks:Array<String> = [];
						if (companion != null && CodenameScriptDiscovery.withinRoot(base.contentRoot, companion)) {
							try {
								var placementModel = CodenameStagePlacement.fromData(stagePlacement);
								var effects = CodenameStagePlacement.applyScriptPlacementEffects(placementModel,
									File.getContent(companion));
								companionInitialPlacementChange = effects.initial;
								runtimeMutationHooks = effects.runtimeMutationHooks;
								stagePlacement = CodenameStagePlacement.toData(placementModel);
							} catch (_:Dynamic) companionInitialPlacementChange = true;
						}
						if (companionInitialPlacementChange && stagePlacement != null) {
							var unresolved:Dynamic = Reflect.field(stagePlacement, 'unsupported');
							if (Std.isOfType(unresolved, Array)
								&& (cast unresolved:Array<Dynamic>).indexOf('stage-script') < 0)
								(cast unresolved:Array<Dynamic>).push('stage-script');
						}
						if (runtimeMutationHooks.length > 0)
							diagnostics.push('[codename-stage-runtime-placement] Stage "' + cameraStage
								+ '" has actor-pose writes in delayed callbacks: '
								+ runtimeMutationHooks.join(', ')
								+ '; XML slots describe startup placement only.');
						stageOffsetsKnown = true;
					} catch (error:Dynamic) {
						diagnostics.push('[codename-camera-metadata] Stage camera XML invalid for "'
							+ cameraStage + '": ' + Std.string(error));
					}
				} else diagnostics.push('[codename-camera-metadata] Stage camera XML unresolved for "'
					+ cameraStage + '".');
				Reflect.setField(authoredCamera, convertedChart.difficulty, {
					stage:cameraStage, nativeStage:stageNames.get(cast cameraStage),
					lines:convertedChart.cameraLines,
					characters:cameraCharacters, nativeCharacters:nativeCharacters,
					missingCharacters:missingCameraCharacters,
					stageOffsets:stageCameraOffsets, stageOffsetsKnown:stageOffsetsKnown,
					stageStartCamera:stageStartCamera, stagePlacement:stagePlacement
				});
			}
			for (convertedChart in convertedCharts)
				if (convertedChart != null && convertedChart.chart != null
					&& Reflect.field(convertedChart.chart, 'song') != null)
					Reflect.setField(convertedChart.chart.song, 'stage', stageNames.get(
						chartFieldString(convertedChart.chart.song, 'stage', 'stage')));

			var nativePlayer = codenameNativeCharacterName(convertedCharacters, playerReference,
				findCodenameDefinitionXml(base.data, 'characters', playerReference) != '',
				codenameFallbackReference, codenameFallbackNativeName);
			if (nativePlayer == null) nativePlayer = vSliceNativeCharacterName(convertedCharacters, playerReference);
			var nativeOpponent = codenameNativeCharacterName(convertedCharacters, opponentReference,
				findCodenameDefinitionXml(base.data, 'characters', opponentReference) != '',
				codenameFallbackReference, codenameFallbackNativeName);
			if (nativeOpponent == null) nativeOpponent = vSliceNativeCharacterName(convertedCharacters, opponentReference);
			var nativeGirlfriend = codenameNativeCharacterName(convertedCharacters, girlfriendReference,
				findCodenameDefinitionXml(base.data, 'characters', girlfriendReference) != '',
				codenameFallbackReference, codenameFallbackNativeName);
			if (nativeGirlfriend == null) nativeGirlfriend = vSliceNativeCharacterName(convertedCharacters, girlfriendReference);
			for (convertedChart in convertedCharts)
				if (convertedChart != null && convertedChart.chart != null
					&& Reflect.field(convertedChart.chart, 'song') != null) {
					// The first chart selects the legacy song-level presentation, but
					// each authored difficulty keeps its own primary character IDs.
					// Song's difficulty-default merge is a separate runtime concern.
					var chartSong:Dynamic = convertedChart.chart.song;
					var chartPlayer1 = chartFieldString(chartSong, 'player1', 'bf');
					var chartPlayer2 = chartFieldString(chartSong, 'player2', 'dad');
					var chartGirlfriend = chartFieldString(chartSong, 'gf', 'gf');
					var mappedPlayer1 = codenameNativeCharacterName(convertedCharacters, chartPlayer1,
						findCodenameDefinitionXml(base.data, 'characters', chartPlayer1) != '',
						codenameFallbackReference, codenameFallbackNativeName);
					var mappedPlayer2 = codenameNativeCharacterName(convertedCharacters, chartPlayer2,
						findCodenameDefinitionXml(base.data, 'characters', chartPlayer2) != '',
						codenameFallbackReference, codenameFallbackNativeName);
					var mappedGirlfriend = codenameNativeCharacterName(convertedCharacters, chartGirlfriend,
						findCodenameDefinitionXml(base.data, 'characters', chartGirlfriend) != '',
						codenameFallbackReference, codenameFallbackNativeName);
					Reflect.setField(chartSong, 'player1', mappedPlayer1 == null
						? vSliceNativeCharacterName(convertedCharacters, chartPlayer1) : mappedPlayer1);
					Reflect.setField(chartSong, 'player2', mappedPlayer2 == null
						? vSliceNativeCharacterName(convertedCharacters, chartPlayer2) : mappedPlayer2);
					Reflect.setField(chartSong, 'gf', mappedGirlfriend == null
						? vSliceNativeCharacterName(convertedCharacters, chartGirlfriend) : mappedGirlfriend);
				}

			// Codename displayName is presentation text.  The folder id stays the
			// native song key because audio resolves case-sensitively from
			// assets/songs/<song>/.
			var nativeSongName = validModuleName(folderName) ? folderName : (displayName == '' ? folderName : displayName);
			var displayAlias = StringTools.trim(displayName) == '' || StringTools.trim(displayName) == StringTools.trim(nativeSongName)
				? 'null' : displayName;

			var songData:SongImport = {
				name: nativeSongName,
				p1: nativePlayer,
				p2: nativeOpponent,
				gf: nativeGirlfriend,
				stage: nativeStage,
				ui: chartFieldString(firstSong, 'uiType', 'normal'),
				cutscene: 'none',
				category: 'Imported', isHey: false, isCheer: false, isMoody: false, isSpooky: false,
				stageID: 0,
				week: -1, char: nativeOpponent, display: displayAlias,
				inst: instPath,
				voices: splitVocalStems.length > 0 ? null : findImportAudio(audioFolder, true),
				dialog: null, modchart: null,
				diffFiles: chartPaths,
				convertedCharts: convertedCharts,
				noteDefinitions: noteDefinitions.length > 0 ? noteDefinitions : null,
				convertedCharacters: convertedCharacters,
				convertedStage: convertedStage,
				vSliceRoot: base.contentRoot,
				codenameEngineBaseAssetRoot: engineBaseAssetRoot,
				codenameDefaultCharacter: codenameFallbackReference,
				sourceRoot: base.root,
				engine: ImportEngine.CODENAME,
				diagnostics: diagnostics
			};
			if (validModuleName(folderName))
				Reflect.setField(songData, 'sourceFolder', folderName);
			if (convertedStages.length > 0)
				Reflect.setField(songData, 'convertedStages', convertedStages);
			Reflect.setField(songData, 'codenameStageSource', stageReference);
			Reflect.setField(songData, 'codenameAuthoredStages', authoredStages);
			Reflect.setField(songData, 'codenameAuthoredCamera', authoredCamera);
			// Keep the complete parsed Codename ChartData.meta source object out
			// of native charts; the selected owner receives a data-only sidecar.
			Reflect.setField(songData, 'codenameOriginalMeta', meta);
			Reflect.setField(songData, 'codenameResolvedMeta', resolvedSongMeta);
			if (splitVocalStems.length > 0)
				Reflect.setField(songData, 'vocalStems', splitVocalStems);
			if (validateAndRecordSongImport(rejections, songData, base.root,
				songFolder, base.engine)) {
				result.push(songData);
				var sourceInfo:SongImportSource = {song:audioFolder, data:songFolder,
					destination:importSongFolderName(songData),
					sourceRoot:base.root, engine:base.engine};
				songData.importSourceInfo = sourceInfo;
				if (sourcePaths != null)
					sourcePaths.set(StringTools.trim(songData.name).toLowerCase(), sourceInfo);
			}
		}
		return result;
	}

	/** Locate a Codename data/<kind>/<reference>.xml definition without
		assuming the authored spelling's case. */
	static function findCodenameDefinitionXml(dataFolder:String, kind:String, reference:String):String {
		if (dataFolder == null || dataFolder == '' || reference == null
			|| !CodenameScriptDiscovery.safeRelativeName(reference))
			return '';
		var resolved = CodenameScriptDiscovery.resolveScopedRelative(dataFolder,
			kind + '/' + reference + '.xml');
		return resolved == null ? '' : Path.join([dataFolder, resolved]);
	}

	static function safeSortedDirectoryListing(folder:String):Array<String> {
		var entries:Array<String> = [];
		try {
			for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(folder)))
				entries.push(entry);
		} catch (_:Dynamic) {}
		entries.sort(function(a, b) {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		return entries;
	}
	#end

	#if sys
	/** Count only playable charts in one candidate.  V-Slice candidates keep
	 * their converted charts alongside metadata/chart source paths; prefer the
	 * converted count there so one authored chart is not counted twice. */
	static function songCandidateChartCount(song:SongImport):Int {
		if (song == null)
			return 0;
		if (song.convertedCharts != null) {
			var convertedCount = 0;
			for (converted in song.convertedCharts)
				if (converted != null && converted.chart != null
					&& Reflect.field(converted.chart, 'song') != null)
					convertedCount++;
			if (convertedCount > 0)
				return convertedCount;
		}
		var chartCount = 0;
		if (song.diffFiles != null)
			for (chartPath in song.diffFiles)
				if (validImportPath(chartPath) && readSongChart(chartPath) != null)
					chartCount++;
		return chartCount;
	}

	/** Rank duplicate donors by authored content, then by optional sidecars.
	 * The weights make chart coverage the primary completeness signal while
	 * still preferring a candidate which carries voices/dialogue/modchart data
	 * when both donors have the same difficulty set. */
	static function songCandidateCompleteness(song:SongImport):Int {
		if (song == null)
			return -1;
		var score = songCandidateChartCount(song) * 100000;
		if (validImportPath(song.inst))
			score += 10000;
		if (validImportPath(song.voices))
			score += 1000;
		if (validImportPath(song.dialog))
			score += 100;
		if (validImportPath(song.modchart)
			|| (song.generatedModchart != null && StringTools.trim(song.generatedModchart) != ''))
			score += 100;
		if (song.noteDefinitions != null && song.noteDefinitions.length > 0)
			score += 10;
		if (song.convertedCharacters != null)
			score += song.convertedCharacters.length;
		if (song.convertedStage != null)
			score++;
		return score;
	}

	/** Compare candidates without consulting filesystem enumeration order. */
	static function compareSongCandidates(a:SongImportCandidate, b:SongImportCandidate):Int {
		var aScore = songCandidateCompleteness(a == null ? null : a.song);
		var bScore = songCandidateCompleteness(b == null ? null : b.song);
		if (aScore != bScore)
			return aScore > bScore ? -1 : 1;
		var aRoot = a == null || a.root == null ? '' : importPathKey(a.root);
		var bRoot = b == null || b.root == null ? '' : importPathKey(b.root);
		if (aRoot < bRoot)
			return -1;
		if (aRoot > bRoot)
			return 1;
		// Linux can keep two case-variant directories distinct even though the
		// destination song key is case-insensitive.  Use the original normalized
		// spelling as a final tie-break instead of leaking filesystem order.
		var aStable = a == null || a.root == null ? '' : Path.normalize(StringTools.replace(a.root, '\\', '/'));
		var bStable = b == null || b.root == null ? '' : Path.normalize(StringTools.replace(b.root, '\\', '/'));
		if (aStable < bStable)
			return -1;
		if (aStable > bStable)
			return 1;
		return 0;
	}

	/** A source chart directory identifies one physical song even when Auto sees
	 * it through both a game root and a nested mod root. Different directories
	 * with the same display name remain independent import candidates. */
	static function songCandidateOrigin(candidate:SongImportCandidate):String {
		if (candidate == null || candidate.song == null)
			return '';
		var source = candidate.source == null ? candidate.song.importSourceInfo : candidate.source;
		if (source != null && source.data != null && StringTools.trim(source.data) != '')
			return importPathKey(source.data);
		if (candidate.song.convertedCharts != null)
			for (chart in candidate.song.convertedCharts)
				if (chart != null && chart.source != null && StringTools.trim(chart.source) != '')
					return importPathKey(Path.directory(chart.source));
		if (candidate.song.diffFiles != null)
			for (chart in candidate.song.diffFiles)
				if (chart != null && StringTools.trim(chart) != '')
					return importPathKey(Path.directory(chart));
		return candidate.root == null ? '' : importPathKey(candidate.root);
	}

	/** Select one candidate per physical song and retain alias views as skipped
	 * sources. A separate package's same-named song receives its own destination. */
	static function selectSongCandidates(candidates:Array<SongImportCandidate>):Array<SongImportCandidate> {
		var selected:Array<SongImportCandidate> = [];
		if (candidates == null)
			return selected;
		var groups:Map<String, Array<SongImportCandidate>> = new Map<String, Array<SongImportCandidate>>();
		var keys:Array<String> = [];
		for (candidate in candidates) {
			if (candidate == null || candidate.song == null)
				continue;
			var key = StringTools.trim(candidate.song.name).toLowerCase() + '|' + songCandidateOrigin(candidate);
			if (!groups.exists(key)) {
				groups.set(key, []);
				keys.push(key);
			}
			groups.get(key).push(candidate);
		}
		for (key in keys) {
			var group = groups.get(key);
			group.sort(compareSongCandidates);
			var winner = group[0];
			if (winner.song.sourceRoot == null || StringTools.trim(winner.song.sourceRoot) == '')
				winner.song.sourceRoot = winner.root;
			if (winner.song.importSourceInfo == null)
				winner.song.importSourceInfo = winner.source;
			winner.song.sourceDuplicate = false;
			winner.song.sourceDuplicateOf = null;
			if (winner.song.engine == null || StringTools.trim(winner.song.engine) == '')
				winner.song.engine = winner.engine;
			selected.push(winner);
			for (index in 1...group.length) {
				var skipped = group[index];
				if (skipped.song.sourceRoot == null || StringTools.trim(skipped.song.sourceRoot) == '')
					skipped.song.sourceRoot = skipped.root;
				if (skipped.song.importSourceInfo == null)
					skipped.song.importSourceInfo = skipped.source;
				skipped.song.sourceDuplicate = true;
				skipped.song.sourceDuplicateOf = winner.root;
				if (skipped.song.diagnostics == null)
					skipped.song.diagnostics = [];
				var winnerScore = songCandidateCompleteness(winner.song);
				var skippedScore = songCandidateCompleteness(skipped.song);
				var reason = winnerScore == skippedScore
					? 'the completeness tie was resolved by stable source-root order'
					: 'the selected candidate is more complete';
				skipped.song.diagnostics.push('[duplicate-source-candidate] Duplicate source candidate from "' + skipped.root
					+ '" was skipped; selected candidate from "' + winner.root + '" because ' + reason + '.');
				selected.push(skipped);
			}
		}
		return selected;
	}
	#end

	/**
	 * Engine-aware discovery. Auto classifies every independent root instead of
	 * applying one guess to the entire selected parent folder.
	 */
	static public function discoverSongImports(selectedPath:String, ?sourcePaths:Map<String, SongImportSource>,
		?importType:String):Array<SongImport> {
		return discoverSongImportsDetailed(selectedPath, sourcePaths, importType).songs;
	}

	/** Detailed sibling used by ImportWorkflow so bounded package discovery can
	 * reach the scan report without process-global state. */
	static public function discoverSongImportsDetailed(selectedPath:String,
		?sourcePaths:Map<String, SongImportSource>, ?importType:String,
		?preScannedRoots:Array<ImportRootScanner.ImportRoot>):SongImportDiscoveryResult {
		var result:Array<SongImport> = [];
		var rejectionCollector = newSongImportRejectionCollector();
		var packageDiscovery:SongPackageDiscoveryResult = {
			folders: [], diagnostics: [], truncated: false, cancelled: false,
			scannedDirectories: 0, directoryLimit: MAX_IMPORT_DISCOVERY_DIRECTORIES,
			queuedDirectories: 0
		};
		#if sys
		if (!isSafeImportSource(selectedPath))
			return {songs: result, packageDiscovery: packageDiscovery,
				rejectedSongs: rejectionCollector.entries, rejectedSongCount: rejectionCollector.total,
				rejectedSongsTruncated: rejectionCollector.truncated};
		var selected = ImportSettings.normalizeType(importType);
		var roots = preScannedRoots == null ? ImportRootScanner.scan(selectedPath, selected, {
			onProgress: function(progress):Void {
				reportImportProgress(progress.phase, progress.current, progress.completed, progress.total);
				yieldImportWork();
			},
			isCancelled: function():Bool return importWorkCancelled()
		}) : preScannedRoots.copy();
		var usableRoots:Array<ImportRootScanner.ImportRoot> = [];
		for (root in roots)
			if (!isCurrentGameImportRoot(root))
				usableRoots.push(root);
		roots = usableRoots;
		var candidates:Array<SongImportCandidate> = [];
		for (root in roots) {
			if (importWorkCancelled())
				break;
			var rootSources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
			var songs = root.engine == ImportEngine.V_SLICE
				? discoverVSliceSongImports(root, rootSources, rejectionCollector)
				: (root.engine == ImportEngine.CODENAME
					? discoverCodenameSongImports(root, rootSources, rejectionCollector)
					: discoverLegacySongImportsFromRoot(root, rootSources, rejectionCollector));
			for (song in songs) {
				var key = StringTools.trim(song.name).toLowerCase();
				var sourceInfo = song.importSourceInfo == null
					? (rootSources.exists(key) ? rootSources.get(key) : null) : song.importSourceInfo;
				candidates.push({
					song: song,
					root: song.sourceRoot == null || StringTools.trim(song.sourceRoot) == '' ? root.root : song.sourceRoot,
					engine: root.engine,
					source: sourceInfo
				});
			}
		}
		// Auto may select a parent containing both engine-shaped game roots and
		// standalone Modding Plus packages. Those packages are valid import units
		// even when another root already made the scanner non-empty; omitting them
		// made mixed selections silently lose songs. Feed them through the same
		// duplicate-completeness selection as detected roots.
		if (selected == ImportEngine.AUTO || selected == ImportEngine.MODDING_PLUS) {
			var legacySources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
			var legacyDiscovery = discoverLegacySongImportsDetailed(selectedPath, legacySources,
				rejectionCollector);
			packageDiscovery = legacyDiscovery.packageDiscovery;
			var legacySongs = legacyDiscovery.songs;
			for (song in legacySongs) {
				if (importWorkCancelled())
					break;
				if (song == null)
					continue;
				var key = StringTools.trim(song.name).toLowerCase();
				var source = song.importSourceInfo == null
					? (legacySources.exists(key) ? legacySources.get(key) : null) : song.importSourceInfo;
				var candidateRoot = song.sourceRoot;
				if (candidateRoot == null || StringTools.trim(candidateRoot) == '')
					candidateRoot = source == null ? selectedPath : source.sourceRoot;
				if (candidateRoot == null || StringTools.trim(candidateRoot) == '')
					candidateRoot = selectedPath;
				if (!ImportRootScanner.retainedSourceRootAllowed(candidateRoot, ImportEngine.MODDING_PLUS))
					continue;
				candidates.push({song:song, root:candidateRoot,
					engine:ImportEngine.MODDING_PLUS, source:source});
			}
		}
		for (candidate in selectSongCandidates(candidates)) {
			if (candidate == null || candidate.song == null)
				continue;
			result.push(candidate.song);
			var key = StringTools.trim(candidate.song.name).toLowerCase();
			if (!candidate.song.sourceDuplicate && sourcePaths != null && candidate.source != null)
				sourcePaths.set(key, candidate.source);
		}
		#end
		return {songs: result, packageDiscovery: packageDiscovery,
			rejectedSongs: rejectionCollector.entries, rejectedSongCount: rejectionCollector.total,
			rejectedSongsTruncated: rejectionCollector.truncated};
	}

	/** Return authored `Paths.*` references from one HXC stage without executing
		the donor class.  The generated runtime uses the same relative names below
		the per-source namespace, so this remains safe for multiple V-Slice roots
		which reuse names such as `stage/TB/teto_idle`. */
	static function hxcStageAssetReferences(source:String):Array<{kind:String, key:String}> {
		var result:Array<{kind:String, key:String}> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var add = function(kind:String, key:String):Void {
			if (key == null || StringTools.trim(key) == '')
				return;
			var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
			var identity = kind + ':' + clean.toLowerCase();
			if (seen.exists(identity))
				return;
			seen.set(identity, true);
			result.push({kind:kind, key:clean});
		};
		var collect = function(pattern:String, kind:String):Void {
			if (source == null || source == '')
				return;
			var expression = new EReg(pattern, 'g');
			var remaining = source;
			var attempts = 0;
			while (attempts++ < 4096 && expression.match(remaining)) {
				var key = '';
				try key = expression.matched(1) catch (_:Dynamic) {}
				add(kind, key);
				var position = expression.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length)
					break;
				remaining = remaining.substr(position.pos + position.len);
			}
		};
		collect('Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\']([^"\\\']+)', 'image');
		collect('Paths\\s*\\.\\s*getSparrowAtlas\\s*\\(\\s*["\\\']([^"\\\']+)', 'sparrow');
		collect('Paths\\s*\\.\\s*getPackerAtlas\\s*\\(\\s*["\\\']([^"\\\']+)', 'packer');
		collect('Paths\\s*\\.\\s*getFrames\\s*\\(\\s*["\\\']([^"\\\']+)', 'frames');
		collect('Paths\\s*\\.\\s*frag\\s*\\(\\s*["\\\']([^"\\\']+)', 'frag');
		collect('Paths\\s*\\.\\s*sound\\s*\\(\\s*["\\\']([^"\\\']+)', 'sound');
		collect('Paths\\s*\\.\\s*music\\s*\\(\\s*["\\\']([^"\\\']+)', 'music');
		return result;
	}

	/** Locate one case-insensitive asset in a V-Slice image/media tree. */
	static function findVSliceHxcAssetByBasename(imagesRoot:String, relative:String,
		extensions:Array<String>):String {
		if (imagesRoot == null || relative == null || extensions == null
			|| extensions.length == 0 || !FileSystem.isDirectory(imagesRoot))
			return null;
		var requested = Path.withoutDirectory(StringTools.replace(StringTools.trim(relative), '\\', '/'));
		if (requested == null || StringTools.trim(requested) == '')
			return null;
		var requestedLower = requested.toLowerCase();
		var queue:Array<{path:String, depth:Int}> = [{path:imagesRoot, depth:0}];
		var matches:Array<String> = [];
		var visitedDirectories = 0;
		var visitedEntries = 0;
		var maxDepth = 8;
		var maxEntries = 24000;
		while (queue.length > 0 && visitedEntries < maxEntries) {
			var current = queue.shift();
			if (current == null || !FileSystem.isDirectory(current.path))
				continue;
			visitedDirectories++;
			var entries:Array<String>;
			try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(current.path)) catch (_:Dynamic) continue;
			entries.sort(function(left:String, right:String):Int {
				var l = left.toLowerCase();
				var r = right.toLowerCase();
				return l < r ? -1 : (l > r ? 1 : 0);
			});
			for (entry in entries) {
				if (entry == null || entry == '.' || entry == '..')
					continue;
				visitedEntries++;
				if (visitedEntries > maxEntries)
					break;
				var path = Path.join([current.path, entry]);
				if (FileSystem.isDirectory(path)) {
					if (current.depth < maxDepth)
						queue.push({path:path, depth:current.depth + 1});
					continue;
				}
				var entryLower = entry.toLowerCase();
				for (extension in extensions) {
					var expected = requestedLower;
					var extensionLower = extension == null ? '' : extension.toLowerCase();
					if (extensionLower != '' && !expected.endsWith(extensionLower))
						expected += extensionLower;
					if (entryLower == expected) {
						matches.push(path);
						break;
					}
				}
			}
		}
		if (matches.length == 0)
			return null;
		// A nested alias is useful only when it resolves deterministically. When
		// multiple copies share a basename, prefer the path containing the
		// authored directory hint before falling back to lexical order.
		var hint = StringTools.replace(StringTools.trim(relative), '\\', '/').toLowerCase();
		var best:String = null;
		var bestScore = -1;
		for (match in matches) {
			var lower = match.toLowerCase();
			var score = 0;
			for (part in hint.split('/'))
				if (part != '' && lower.indexOf('/' + part + '/') >= 0)
					score++;
			if (best == null || score > bestScore || (score == bestScore && lower < best.toLowerCase())) {
				best = match;
				bestScore = score;
			}
		}
		return best;
	}

	/** Resolve a literal Paths.file reference inside the selected package root.
	 * The lookup is bounded by its authored path and rejects symlink escapes. */
	static function findVSliceHxcRootFile(sourceRoot:String, relative:String):String {
		if (sourceRoot == null || relative == null) return null;
		var clean = StringTools.replace(StringTools.trim(relative), '\\', '/');
		while (clean.startsWith('./')) clean = clean.substr(2);
		if (clean.toLowerCase().startsWith('assets/')) clean = clean.substr('assets/'.length);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0) return null;
		var parts = clean.split('/');
		for (part in parts) if (part == '' || part == '.' || part == '..') return null;
		var shared = findChildDirectory(sourceRoot, 'shared');
		var roots = shared == null ? [sourceRoot] : [sourceRoot, shared];
		for (root in roots) {
			var parent = root;
			for (index in 0...(parts.length - 1)) {
				parent = findChildDirectory(parent, parts[index]);
				if (parent == null) break;
			}
			if (parent == null) continue;
			var found = findImportFile(parent, [parts[parts.length - 1]]);
			if (found != null && CodenameScriptDiscovery.withinRoot(root, found))
				return found;
		}
		return null;
	}

	/** Locate one case-insensitive asset in a V-Slice image/media tree. */
	static function findVSliceHxcAsset(sourceRoot:String, relative:String, folderName:String,
		extensions:Array<String>):String {
		if (sourceRoot == null || relative == null || folderName == null
			|| extensions == null || extensions.length == 0)
			return null;
		var clean = StringTools.replace(StringTools.trim(relative), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		while (clean.startsWith('/'))
			clean = clean.substr(1);
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean.toLowerCase().startsWith(folderName.toLowerCase() + '/'))
			clean = clean.substr(folderName.length + 1);
		if (clean == '' || clean.indexOf(':') >= 0)
			return null;
		for (part in clean.split('/'))
			if (part == '' || part == '..')
				return null;
		var shared = findChildDirectory(sourceRoot, 'shared');
		var roots:Array<String> = [sourceRoot];
		if (shared != null)
			roots.push(shared);
		for (root in roots) {
			var folder = findChildDirectory(root, folderName);
			if (folder == null)
				continue;
			var candidates = [clean];
			// V-Slice shared music sometimes stores a track at
			// `shared/music/<id>/<id>.ogg`, while HXC calls `Paths.music(<id>)`.
			// Try that canonical package layout after the flat asset key; the
			// caller still maps the resolved file to the runtime's flat `<id>.ogg`
			// alias, and the normal tree merge preserves the original nested file.
			if (folderName.toLowerCase() == 'music' && Path.extension(clean) == '') {
				var basename = Path.withoutDirectory(clean);
				if (basename != null && basename != '')
					candidates.push(clean + '/' + basename);
			}
			for (extension in extensions) {
				for (candidate in candidates) {
					if (!candidate.toLowerCase().endsWith(extension.toLowerCase()))
						candidate += extension;
					var parts = candidate.split('/');
					var fileName = parts.pop();
					var parent = folder;
					// Donor exports are frequently authored on Windows with mixed-case
					// nested image folders. Resolve every directory component using the
					// same case-insensitive lookup as the top-level asset folder so Linux
					// materialization does not strand an otherwise valid HXC reference.
					for (part in parts) {
						parent = findChildDirectory(parent, part);
						if (parent == null)
							break;
					}
					if (parent == null || fileName == null || fileName == '')
						continue;
					var found = findImportFile(parent, [fileName]);
					if (found != null)
						return found;
				}
			}
		}
		// A few shipped V-Slice scripts use a legacy flat alias for an asset that
		// was later moved below a semantic folder (for example
		// `characters/DDLCBoyFriend_Assets` -> `characters/boyfriend/...`).
		// Search only the image roots, with a bounded file/depth budget; this is
		// deliberately not a donor-wide media walk and never mutates the source.
		if (folderName.toLowerCase() == 'images') {
			var requested = Path.withoutDirectory(clean);
			if (requested != null && StringTools.trim(requested) != '') {
				for (root in roots) {
					var folder = findChildDirectory(root, folderName);
					var found = findVSliceHxcAssetByBasename(folder, requested, extensions);
					if (found != null)
						return found;
				}
			}
		}
		return null;
	}

	static function hxcStageAssetStem(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		while (clean.startsWith('/'))
			clean = clean.substr(1);
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean.toLowerCase().startsWith('images/'))
			clean = clean.substr('images/'.length);
		for (extension in ['.png', '.xml', '.txt', '.astc'])
			if (clean.toLowerCase().endsWith(extension))
				return clean.substr(0, clean.length - extension.length);
		return clean;
	}

	/** Copy one image/atlas/media reference used by a selected HXC stage. */
	static function mergeVSliceHxcStageAsset(sourceRoot:String, runtimeNamespace:String,
		reference:{kind:String, key:String}, result:ImportAssetMergeResult,
		?reportMissing:Bool = true):Void {
		if (reference == null || sourceRoot == null || runtimeNamespace == null)
			return;
		var kind = reference.kind == null ? '' : reference.kind.toLowerCase();
		if (kind == 'health-icon') {
			var mappings = VSliceImporter.hxcHealthIconMappings(sourceRoot, reference.key);
			if (mappings == null)
				return;
			if (mappings.length == 0) {
				if (reportMissing) {
					if (result.errors == null) result.errors = [];
					result.errors.push('HXC health icon missing: ' + reference.key + ' (' + sourceRoot + ')');
				}
				return;
			}
			for (mapping in mappings)
				mergeVSliceMapping(mapping, runtimeNamespace, result);
			return;
		}
		if (kind == 'file') {
			var clean = StringTools.replace(StringTools.trim(reference.key), '\\', '/');
			while (clean.startsWith('./')) clean = clean.substr(2);
			if (clean.toLowerCase().startsWith('assets/')) clean = clean.substr('assets/'.length);
			if (!CodenameScriptDiscovery.safeRelativeName(clean)) return;
			var source = findVSliceHxcRootFile(sourceRoot, clean);
			if (source == null) {
				if (reportMissing) {
					if (result.errors == null) result.errors = [];
					result.errors.push('HXC package file missing: ' + reference.key + ' (' + sourceRoot + ')');
				}
			} else
				mergeVSliceMapping({source:source, destination:clean,
					kind:'hxc-package-file', supported:true}, runtimeNamespace, result);
			return;
		}
		var stem = hxcStageAssetStem(reference.key);
		if (stem == '')
			return;
		if (kind == 'frames') {
			var framePlan = CodenameFrameAtlasAssets.plan(sourceRoot, stem);
			if (framePlan.files.length == 0) {
				if (reportMissing) {
					if (result.errors == null)
						result.errors = [];
					for (diagnostic in framePlan.diagnostics)
						result.errors.push('HXC static frame asset ' + reference.key + ': ' + diagnostic);
				}
				return;
			}
			for (asset in framePlan.files)
				mergeVSliceMapping({source:asset.source, destination:asset.relative,
					kind:'hxc-stage-frame-asset', supported:true}, runtimeNamespace, result);
			return;
		}
		if (kind == 'image' || kind == 'sparrow' || kind == 'packer') {
			var png = findVSliceHxcAsset(sourceRoot, stem, 'images', ['.png']);
			var astc = png == null ? findVSliceHxcAsset(sourceRoot, stem, 'images', ['.astc']) : null;
			if (png != null) {
				mergeVSliceMapping({source:png, destination:'images/' + stem + '.png', kind:'hxc-stage-image', supported:true},
					runtimeNamespace, result);
			} else if (astc != null) {
				mergeVSliceMapping({source:astc, destination:'images/' + stem + '.png', kind:'hxc-stage-image',
					supported:true, requiresConversion:true}, runtimeNamespace, result);
			} else {
				if (reportMissing) {
					if (result.errors == null)
						result.errors = [];
					result.errors.push('HXC static asset missing: ' + reference.key + ' (' + sourceRoot + ')');
				}
			}
			if (kind == 'sparrow' || kind == 'packer') {
				var metadataExtension = kind == 'packer' ? '.txt' : '.xml';
				var metadata = findVSliceHxcAsset(sourceRoot, stem, 'images', [metadataExtension]);
				if (metadata != null)
					mergeVSliceMapping({source:metadata, destination:'images/' + stem + metadataExtension,
						kind:'hxc-stage-atlas', supported:true}, runtimeNamespace, result);
				else if (reportMissing) {
					if (result.errors == null)
						result.errors = [];
					result.errors.push('HXC static atlas metadata missing: ' + reference.key + metadataExtension
						+ ' (' + sourceRoot + ')');
				}
			}
			return;
		}
		var folder = switch (kind) {
			case 'frag': 'shaders';
			case 'sound': 'sounds';
			case 'music': 'music';
			default: 'data';
		};
		var extensions = switch (kind) {
			case 'frag': ['.frag'];
			case 'sound' | 'music': ['.ogg', '.wav', '.mp3'];
			default: [''];
		};
		var source = findVSliceHxcAsset(sourceRoot, reference.key, folder, extensions);
		if (source == null) {
			if (reportMissing) {
				if (result.errors == null)
					result.errors = [];
				result.errors.push('HXC static asset missing: ' + reference.key + ' (' + sourceRoot + ')');
			}
			return;
		}
		var clean = StringTools.replace(StringTools.trim(reference.key), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.toLowerCase().startsWith(folder + '/'))
			clean = clean.substr(folder.length + 1);
		var extension = Path.extension(source);
		mergeVSliceMapping({source:source, destination:folder + '/' + clean + (clean.toLowerCase().endsWith('.' + extension.toLowerCase()) ? '' : '.' + extension),
			kind:'hxc-stage-media', supported:true}, runtimeNamespace, result);
	}

	/** Copy only assets referenced by selected V-Slice stage HXC files. */
	static function mergeVSliceHxcStageAssets(sourceRoot:String, scriptSourceRoot:String,
		scriptEngine:String, runtimeNamespace:String, selectedSongs:Map<String, SongImport>,
		result:ImportAssetMergeResult):Void {
		if (sourceRoot == null || runtimeNamespace == null || !FileSystem.isDirectory(sourceRoot))
			return;
		var stageNames:Map<String, Bool> = new Map<String, Bool>();
		var rootKey = importPathKey(sourceRoot);
		var scriptRootKey = scriptSourceRoot == null ? '' : importPathKey(scriptSourceRoot);
		if (selectedSongs != null)
			for (song in selectedSongs) {
				if (song == null || song.engine != ImportEngine.V_SLICE)
					continue;
				var songRoot = song.vSliceRoot == null ? '' : importPathKey(song.vSliceRoot);
				if (songRoot != rootKey && songRoot != scriptRootKey)
					continue;
				if (song.stage != null && StringTools.trim(song.stage) != '')
					stageNames.set(StringTools.trim(song.stage).toLowerCase(), true);
			}
		// Direct calls from tests/tools may not have an imported-song map. In that
		// case retain the safe bounded behavior and inspect every stage HXC file.
		if (selectedSongs == null)
			stageNames = null;
		var scripts:Array<String> = [];
		var bases:Array<String> = [sourceRoot];
		var shared = findChildDirectory(sourceRoot, 'shared');
		if (shared != null)
			bases.push(shared);
		for (base in bases)
			for (relative in ['scripts/stages', 'data/stages', 'stages']) {
				var folder = Path.join([base, relative]);
				if (!FileSystem.isDirectory(folder))
					continue;
				var entries:Array<String>;
				try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(folder)) catch (_:Dynamic) continue;
				for (entry in entries) {
					if (!entry.toLowerCase().endsWith('.hxc'))
						continue;
					var path = Path.join([folder, entry]);
					if (HxcScriptDiscovery.familyForPath(path) != 'stage'
						|| (stageNames != null && !HxcScriptDiscovery.stageMatches(path,
							[for (name in stageNames.keys()) name])))
						continue;
					if (scripts.indexOf(path) < 0)
						scripts.push(path);
				}
			}
		for (script in scripts) {
				if (importWorkCancelled())
					return;
				var references:Array<{kind:String, key:String}> = [];
				try references = hxcStageAssetReferences(File.getContent(script)) catch (_:Dynamic) continue;
				for (reference in references)
					mergeVSliceHxcStageAsset(sourceRoot, runtimeNamespace, reference, result);
		}
	}

	/**
		Copy literal Paths.* assets referenced by every bounded HXC script family
		into the selected manifest namespace.  Menu and Freeplay modules do not
		belong to one chart stage, so the old stage-only pass could never discover
		their atlases.  HxcAssetPlanner reads only HXC files below scripts/data
		families; it does not enumerate donor media or execute donor code.
	*/
	static function mergeVSliceHxcStaticAssets(sourceRoot:String, scriptSourceRoot:String,
		scriptEngine:String, runtimeNamespace:String, result:ImportAssetMergeResult,
		?libraryRoots:Array<String>, ?selectedSongs:Map<String, SongImport>):Void {
		if (sourceRoot == null || runtimeNamespace == null || !FileSystem.isDirectory(sourceRoot))
			return;
		var selectedStages = selectedVSliceHxcStages(sourceRoot, scriptSourceRoot, selectedSongs);
		var roots:Array<String> = [];
		var addRoot = function(root:String):Void {
			if (root == null || !FileSystem.isDirectory(root))
				return;
			var key = importPathKey(root);
			for (existing in roots)
				if (importPathKey(existing) == key)
					return;
			roots.push(root);
		};
		addRoot(sourceRoot);
		addRoot(findChildDirectory(sourceRoot, 'shared'));
		// Some V-Slice scanners select a parent root for scripts while exposing a
		// child content root for images. Keep the reference discovery bounded to
		// those two selected roots and still resolve assets against sourceRoot.
		addRoot(scriptSourceRoot);
		addRoot(findChildDirectory(scriptSourceRoot, 'shared'));

		var plans:Array<HxcAssetPlan> = [];
		var planRoots:Array<String> = [];
		var activeReferences:Map<String, Bool> = new Map<String, Bool>();
		for (root in roots) {
			if (importWorkCancelled())
				return;
			var plan:HxcAssetPlan;
			try plan = HxcAssetPlanner.plan(root) catch (_:Dynamic) continue;
			if (plan == null || plan.references == null)
				continue;
			plans.push(plan);
			planRoots.push(root);
			var activePlan = plan;
			if (selectedStages != null) {
				try activePlan = HxcAssetPlanner.plan(root, selectedStages) catch (_:Dynamic) {}
			}
			if (activePlan != null && activePlan.references != null)
				for (reference in activePlan.references) {
					if (reference == null || reference.kind == null || reference.key == null)
						continue;
					activeReferences.set(reference.kind.toLowerCase() + ':' + reference.key.toLowerCase(), true);
				}
		}

		var seenReferences:Map<String, Bool> = new Map<String, Bool>();
		for (planIndex in 0...plans.length) {
			var plan = plans[planIndex];
			var root = planRoots[planIndex];
			for (reference in plan.references) {
				if (reference == null || reference.kind == null || reference.key == null)
					continue;
				var identity = reference.kind.toLowerCase() + ':' + reference.key.toLowerCase();
				if (seenReferences.exists(identity))
					continue;
				seenReferences.set(identity, true);
				var assetRoot = sourceRoot;
				if (hxcSharedLibraryAlias(reference.key)
					&& (reference.kind.toLowerCase() == 'image'
						|| reference.kind.toLowerCase() == 'sparrow'
						|| reference.kind.toLowerCase() == 'packer'
						|| reference.kind.toLowerCase() == 'frames')) {
					var requestedStem = hxcStageAssetStem(reference.key);
					var localAsset = findVSliceHxcAsset(sourceRoot, requestedStem, 'images', ['.png', '.astc']);
					if (localAsset == null && libraryRoots != null)
						for (candidateRoot in libraryRoots) {
							if (candidateRoot == null || importPathKey(candidateRoot) == importPathKey(sourceRoot))
								continue;
							var candidate = findVSliceHxcAsset(candidateRoot, requestedStem, 'images', ['.png', '.astc']);
							if (candidate != null) {
								assetRoot = candidateRoot;
								break;
							}
						}
				}
				mergeVSliceHxcStageAsset(assetRoot, runtimeNamespace,
					{kind:reference.kind, key:reference.key}, result, activeReferences.exists(identity));
			}
		}
	}

	/** Return selected chart stages only when every song rooted in this import
	 * has an explicit stage name. A null result keeps the conservative full scan
	 * when metadata is incomplete; an empty array means no chart from this root
	 * was selected. This only narrows warning eligibility, never script or asset copy. */
	static function selectedVSliceHxcStages(sourceRoot:String, scriptSourceRoot:String,
		selectedSongs:Map<String, SongImport>):Array<String> {
		if (selectedSongs == null)
			return null;
		var rootKey = sourceRoot == null ? '' : importPathKey(sourceRoot);
		var scriptRootKey = scriptSourceRoot == null ? '' : importPathKey(scriptSourceRoot);
		var stageNames:Map<String, Bool> = new Map<String, Bool>();
		var foundSong = false;
		var complete = true;
		for (song in selectedSongs) {
			if (song == null || song.engine != ImportEngine.V_SLICE)
				continue;
			var songRoot = song.vSliceRoot == null ? '' : importPathKey(song.vSliceRoot);
			if (songRoot != rootKey && songRoot != scriptRootKey)
				continue;
			foundSong = true;
			if (song.stage == null || StringTools.trim(song.stage) == '') {
				complete = false;
				continue;
			}
			stageNames.set(StringTools.trim(song.stage).toLowerCase(), true);
		}
		if (!foundSong)
			return [];
		if (!complete)
			return null;
		var result:Array<String> = [];
		for (stage in stageNames.keys())
			result.push(stage);
		result.sort(function(left:String, right:String):Int {
			return left < right ? -1 : (left > right ? 1 : 0);
		});
		return result;
	}

	/** Shared V-Slice library aliases may be supplied by another selected V-Slice
	 * root (the Miku note-hold atlas is used by TAKEOVER's markov note script).
	 * Keep this allowlist narrow so unrelated chart assets never cross namespaces. */
	static function hxcSharedLibraryAlias(value:String):Bool {
		if (value == null)
			return false;
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/').toLowerCase();
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		while (clean.startsWith('/'))
			clean = clean.substr(1);
		if (clean.startsWith('images/'))
			clean = clean.substr('images/'.length);
		return clean == 'note_hold_assets' || clean == 'noteskins/note_hold_assets';
	}

	/** Resolve display metadata and the fallback owner label for sources without
	 * authored IDs. Labels never become chart folder names. */
	static function applyPackageDisplayNames(songs:Array<SongImport>,
		packageNames:Map<String, String>):Void {
		if (songs == null)
			return;
		for (songData in songs) {
			if (songData == null || songData.sourceRoot == null
				|| StringTools.trim(songData.sourceRoot) == '')
				continue;
			var sourceRoot = ImportSettings.normalizeSourcePath(songData.sourceRoot);
			var sourceRootKey = ImportPackageNamePrompt.rootKey(sourceRoot);
			var overrideName:String = packageNames == null ? null : packageNames.get(sourceRootKey);
			if (ImportPackageNamePrompt.validName(overrideName)) {
				songData.sourceModName = StringTools.trim(overrideName);
				songData.sourceModNameSource = 'user';
				continue;
			}
			var info = ImportSongOwnership.displayNameInfo(sourceRoot);
			if (info != null && StringTools.trim(info.name) != '') {
				songData.sourceModName = StringTools.trim(info.name);
				songData.sourceModNameSource = info.authored ? 'metadata' : 'inferred';
			}
		}
	}

	/** Label shown beside a collision-qualified song and in the imported-mod
	 * catalog. When no authored ID exists, a label only reconnects a moved root
	 * when its bounded chart/audio fingerprint also matches. */
	static function importOwnerDisplayLabel(songData:SongImport):String {
		if (songData == null)
			return '';
		var displayName = songData.sourceModName == null ? '' : StringTools.trim(songData.sourceModName);
		if (displayName == '')
			return ImportSongOwnership.ownerDisplayLabel(songData.sourceRoot, songData.engine);
		return ImportSongOwnership.displayWithEngine(displayName, songData.engine);
	}

	/**
	 * Import every supported song below a user-selected folder.
	 *
	 * The selection may be one Modding Plus song package, an assets folder, or
	 * the game folder containing assets/.  Existing songs are detected before
	 * writing anything, so a batch import cannot replace a user's chart/audio.
	 */
	#if sys
	static public function importSongsFromPath(sourcePath:String, ?importType:String,
		?plannedOverlays:Array<ImportOverlayMount>, ?packageNames:Map<String, String>):SongImportBatchResult {
		ImportSongOwnership.setIdentityOverrides(packageNames);
		var result:SongImportBatchResult;
		try {
			result = importSongsFromPathScoped(sourcePath, importType, plannedOverlays, packageNames);
		} catch (error:Dynamic) {
			ImportSongOwnership.clearIdentityOverrides();
			throw error;
		}
		ImportSongOwnership.clearIdentityOverrides();
		return result;
	}

	static function importSongsFromPathScoped(sourcePath:String, ?importType:String,
		?plannedOverlays:Array<ImportOverlayMount>, ?packageNames:Map<String, String>):SongImportBatchResult {
		var result:SongImportBatchResult = {
			found: 0,
			imported: 0,
			importedSongs: [],
			skipped: 0,
			failed: 0,
			copiedAssets: 0,
			skippedAssets: 0,
			errors: [],
			overlayPlanned: 0,
			overlayApplied: 0,
			overlayRetained: 0,
			overlaySkipped: 0,
			overlayDiagnostics: [],
			overlayProvenance: [],
			overlayRetentions: []
		};
		var normalizedSource = ImportSettings.normalizeSourcePath(sourcePath);
		reportImportProgress('validating', normalizedSource, 0, 0);
		if (normalizedSource == '' || !FileSystem.isDirectory(normalizedSource)) {
			result.errors.push('The selected source folder does not exist.');
			return result;
		}
		if (!isSafeImportSource(normalizedSource)) {
			result.errors.push('The current game assets cannot be used as an import source.');
			return result;
		}
		// A caller may start a direct import after editing the donor without
		// running ImportWorkflow.perform first.  Do not reuse that operation's
		// process-local atlas index across the new import boundary.
		LegacyCharacterAtlasImporter.clearCache();
		if (importWorkCancelled()) {
			markImportCancelled(result);
			return result;
		}

		var importedSources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
		// A detected engine can expose several mapped asset roots, while dozens of
		// selected songs can share one script owner. Stage each selected owner once
		// per import transaction, without caching it across later imports.
		var stagedCompatOwnerRoots:Map<String, Bool> = new Map<String, Bool>();
		var selectedType = ImportSettings.normalizeType(importType);
		var songs = discoverSongImports(normalizedSource, importedSources, selectedType);
		applyPackageDisplayNames(songs, packageNames);
		ImportSongOwnership.setSourceFingerprintHints(cast songs);
		result.found = songs.length;
		if (importWorkCancelled()) {
			markImportCancelled(result);
			return result;
		}
		reportImportProgress('songs', '', 0, songs.length);
		var seenNames:Map<String, Bool> = new Map<String, Bool>();
		// Registry merges may be authored with either the donor display name or
		// its folder id. A collision-qualified import keeps only its destination
		// alias so the donor's original key cannot re-register over the foreign
		// song which already owns it.
		var importedRegistryNames:Map<String, Bool> = new Map<String, Bool>();
		var importedSongs:Map<String, SongImport> = new Map<String, SongImport>();
		var mergeConvertedVisuals = function(songData:SongImport):Void {
			var visualMerge = importVSliceVisuals(songData);
			result.copiedAssets += visualMerge.copied;
			result.skippedAssets += visualMerge.skipped;
			if (visualMerge.failed > 0) {
				result.failed += visualMerge.failed;
				result.errors.push(songData.name + ': could not materialize ' + visualMerge.failed
					+ ' V-Slice visual asset/registry item(s).');
			}
			if (visualMerge.errors != null)
				for (message in visualMerge.errors)
					if (message != null && StringTools.trim(message) != '')
						result.errors.push(songData.name + ': ' + message);
		};
		var songIndex = 0;
		for (songData in songs) {
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
			songIndex++;
			if (songData.sourceDuplicate == true) {
				result.skipped++;
				reportImportProgress('songs', songData.name, songIndex, songs.length, 0, result.skipped, result.failed);
				continue;
			}
			var sourceKey = StringTools.trim(songData.name).toLowerCase();
			var canonicalFolder = importSongFolderName(songData);
			var destinationPlan = ImportSongOwnership.planDestination(
				existingImportChild('assets/data', canonicalFolder), canonicalFolder,
				songData.sourceRoot, songData.engine);
			var ownershipError:Null<String> = Reflect.field(destinationPlan, 'error');
			var wasOwnerQualified = Reflect.field(destinationPlan, 'qualified') == true;
			if (Reflect.field(destinationPlan, 'visualOnly') == true) {
				result.skipped++;
				if (songData.engine == ImportEngine.CODENAME || songData.engine == ImportEngine.V_SLICE)
					try mergeConvertedVisuals(songData) catch (error:Dynamic) {
						result.failed++;
						result.errors.push(songData.name + ': selected-owner visual repair failed: '
							+ Std.string(error));
					}
				reportImportProgress('songs', songData.name, songIndex, songs.length,
					0, result.skipped, result.failed);
				continue;
			}
			if (ownershipError != null) {
				result.failed++;
				result.errors.push(ownershipError);
				reportImportProgress('songs', songData.name, songIndex, songs.length, 0, result.skipped, result.failed);
				continue;
			}
			if (wasOwnerQualified) {
				var ownerFolder:String = Reflect.field(destinationPlan, 'folder');
				if (ownerFolder == null || !validModuleName(ownerFolder)) {
					result.failed++;
					result.errors.push(songData.name + ': selected owner collision did not produce a valid destination key.');
					reportImportProgress('songs', songData.name, songIndex, songs.length, 0, result.skipped, result.failed);
					continue;
				}
				Reflect.setField(songData, 'destinationFolder', ownerFolder);
				Reflect.setField(songData, 'ownerQualifiedCollision', true);
				var currentDisplay = songData.display == null ? '' : StringTools.trim(songData.display);
				if (currentDisplay == '' || currentDisplay.toLowerCase() == 'null')
					currentDisplay = songData.name;
				var ownerLabel = importOwnerDisplayLabel(songData);
				Reflect.setField(songData, 'display', currentDisplay + ' · ' + ownerLabel);
				Reflect.setField(songData, 'sourceLabel', ownerLabel);
				if (songData.diagnostics == null)
					songData.diagnostics = [];
				songData.diagnostics.push('[owner-collision-qualified] ' + canonicalFolder
					+ ' is owned by another selected import; this source is stored as ' + ownerFolder + '.');
			}
			var storageKey = importSongFolderName(songData);
			var key = storageKey.toLowerCase();
			if (seenNames.exists(key)) {
				result.skipped++;
				reportImportProgress('songs', songData.name, songIndex, songs.length, 0, result.skipped, result.failed);
				continue;
			}
			seenNames.set(key, true);
			var selectedSource = songData.importSourceInfo;
			if (selectedSource == null && importedSources.exists(sourceKey))
				selectedSource = importedSources.get(sourceKey);
			if (selectedSource != null)
				importedSources.set(storageKey, {
					song:selectedSource.song, data:selectedSource.data, destination:storageKey,
					sourceRoot:selectedSource.sourceRoot, engine:selectedSource.engine
				});
			if (songTargetExists(songData.name, storageKey) && !songNeedsRepair(songData)) {
				result.skipped++;
				if (wasOwnerQualified)
					importedSongs.set(storageKey, songData);
				// A complete chart/audio import can still be missing some converted
				// owner assets. Revisit only the non-overwriting visual/runtime merges;
				// importSong would needlessly parse and touch the existing chart.
				if ((songData.engine == ImportEngine.CODENAME || songData.engine == ImportEngine.V_SLICE
					|| songData.engine == ImportEngine.PSYCH)
					&& songData.sourceRoot != null && StringTools.trim(songData.sourceRoot) != '') {
					importedSongs.set(storageKey, songData);
					if (songData.engine != ImportEngine.PSYCH)
						try mergeConvertedVisuals(songData) catch (error:Dynamic) {
							result.failed++;
							result.errors.push(songData.name + ': converted visual repair failed: ' + Std.string(error));
						}
				}
				reportImportProgress('songs', songData.name, songIndex, songs.length, 0, result.skipped, result.failed);
				continue;
			}
			try {
				if (importSong(songData)) {
					result.imported++;
					result.importedSongs.push(storageKey);
					if (!wasOwnerQualified)
						importedRegistryNames.set(sourceKey, true);
					if (storageKey != '')
						importedRegistryNames.set(storageKey, true);
					importedSongs.set(storageKey, songData);
					mergeConvertedVisuals(songData);
				} else {
					result.failed++;
					result.errors.push(songData.name + ': import validation failed.');
				}
			} catch (error:Dynamic) {
				result.failed++;
				result.errors.push(songData.name + ': ' + Std.string(error));
			}
			reportImportProgress('songs', songData.name, songIndex, songs.length, result.imported, result.skipped, result.failed);
		}
		if (importWorkCancelled()) {
			markImportCancelled(result);
			return result;
		}

		var assetFailures = 0;
		var selectedAssetRoots:Array<String> = [];
		var selectedAssetDestinations:Array<String> = [];
		var selectedAssetSourceRoots:Array<String> = [];
		var selectedAssetEngines:Array<String> = [];
		var engineRoots = ImportRootScanner.scan(normalizedSource, selectedType, {
			onProgress: function(progress):Void {
				reportImportProgress(progress.phase, progress.current, progress.completed, progress.total);
				yieldImportWork();
			},
			isCancelled: function():Bool return importWorkCancelled()
		});
		if (importWorkCancelled()) {
			markImportCancelled(result);
			return result;
		}
		var usableEngineRoots:Array<ImportRootScanner.ImportRoot> = [];
		for (engineRoot in engineRoots)
			if (!isCurrentGameImportRoot(engineRoot))
				usableEngineRoots.push(engineRoot);
		engineRoots = usableEngineRoots;
		var overlayMounts = plannedOverlays == null ? planImportOverlays(engineRoots) : ImportOverlayRuntime.sortMounts(plannedOverlays);
		var overlaySummary = applyImportOverlays(overlayMounts, result);
		for (engineRoot in engineRoots) {
			// V-Slice and Codename charts/audio are converted explicitly above.
			// Their data and image trees are not native and must never be
			// blindly merged.
			if (engineRoot.engine != ImportEngine.V_SLICE && engineRoot.engine != ImportEngine.CODENAME) {
				for (assetSource in selectedAssetRootsForEngineRoot(engineRoot)) {
					var duplicate = false;
					for (existing in selectedAssetRoots)
						if (importPathKey(existing) == importPathKey(assetSource.path)) {
							duplicate = true;
							break;
						}
					if (duplicate) continue;
					selectedAssetRoots.push(assetSource.path);
					selectedAssetDestinations.push(assetSource.destinationPrefix);
					selectedAssetSourceRoots.push(engineRoot.root);
					selectedAssetEngines.push(engineRoot.engine);
				}
			}
		}
		if (engineRoots.length == 0) {
			selectedAssetRoots = findSelectedAssetsRoots(normalizedSource);
			for (assetsRoot in selectedAssetRoots) {
				selectedAssetDestinations.push('');
				selectedAssetSourceRoots.push(assetsRoot);
				selectedAssetEngines.push(selectedType == ImportEngine.AUTO ? '' : selectedType);
			}
		}
		// Resolve every receipt-bound language/media source before the first owner
		// asset copy. This lets one source root's language and media policies share
		// the same conflict pass, and prevents a later unresolved root from failing
		// after earlier roots have already published mapped files.
		var mappedOwnerPlans:Map<String, PreparedMappedAssetOwner> = new Map();
		var mappedPlanFailed = false;
		var addMappedOwnerPlan = function(sourceRoot:String, engine:String,
			contentHint:String):Void {
			var normalizedEngine = ImportRevision.normalizeEngine(engine);
			if (sourceRoot == null || StringTools.trim(sourceRoot) == ''
				|| (normalizedEngine != ImportEngine.PSYCH
					&& normalizedEngine != ImportEngine.NIGHTMARE_VISION)) return;
			var key = mappedAssetOwnerKey(sourceRoot, normalizedEngine);
			if (key == '' || mappedOwnerPlans.exists(key)) return;
			if (importWorkCancelled()) return;
			var scope = normalizedEngine == ImportEngine.NIGHTMARE_VISION
				? authenticatedNightmareVisionScope(sourceRoot, contentHint) : '';
			var ownerRoot = CompatScriptManifest.destinationRoot(sourceRoot, normalizedEngine);
			var plan = SourceMappedMediaPublisher.prepare(sourceRoot, normalizedEngine,
				ownerRoot, scope, function():Bool return importWorkCancelled());
			var owner:PreparedMappedAssetOwner = {
				sourceRoot:sourceRoot, engine:normalizedEngine, scope:scope,
				destinationRoot:ownerRoot, plan:plan
			};
			mappedOwnerPlans.set(key, owner);
			if (plan.diagnostics != null)
				for (diagnostic in plan.diagnostics)
					if (diagnostic != null && StringTools.trim(diagnostic) != '')
						result.errors.push(diagnostic);
			if (plan.cancelled || importWorkCancelled()) return;
			if (plan.failed) {
				mappedPlanFailed = true;
				result.failed++;
			}
		};
		for (engineRoot in engineRoots)
			addMappedOwnerPlan(engineRoot.root, engineRoot.engine, engineRoot.contentRoot);
		for (index in 0...selectedAssetSourceRoots.length)
			addMappedOwnerPlan(selectedAssetSourceRoots[index], selectedAssetEngines[index],
				selectedAssetRoots[index]);
		for (sourceInfo in importedSources)
			if (sourceInfo != null)
				addMappedOwnerPlan(sourceInfo.sourceRoot, sourceInfo.engine, null);
		if (importWorkCancelled()) {
			markImportCancelled(result);
			return result;
		}
		if (mappedPlanFailed) return result;
		for (owner in mappedOwnerPlans) {
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
			var published:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
			SourceMappedMediaPublisher.publish(owner.plan,
				function(source:String, destination:String):Void
					copyImportFileNonOverwriting(source, destination, published),
				function():Bool return importWorkCancelled(),
				function(path:String, content:String):Void
					writeImportContentNonOverwriting(content, path, published, true));
			result.copiedAssets += published.copied;
			result.skippedAssets += published.skipped;
			assetFailures += published.failed;
			if (published.errors != null)
				for (message in published.errors)
					if (message != null && StringTools.trim(message) != '') result.errors.push(message);
			if (owner.plan.cancelled || importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
		}
		var assetRootIndex = 0;
		reportImportProgress('assets', '', 0, selectedAssetRoots.length);
		for (assetRootIndexValue in 0...selectedAssetRoots.length) {
			var assetsRoot = selectedAssetRoots[assetRootIndexValue];
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
			assetRootIndex++;
			reportImportProgress('assets', assetsRoot, assetRootIndex - 1, selectedAssetRoots.length,
				result.copiedAssets, result.skippedAssets, assetFailures);
			var ownerPlan = mappedOwnerPlan(mappedOwnerPlans,
				selectedAssetSourceRoots[assetRootIndexValue], selectedAssetEngines[assetRootIndexValue]);
				var merged = selectedAssetDestinations[assetRootIndexValue] == ''
					? mergeSupportedAssets(assetsRoot, importedRegistryNames, importedSources,
						selectedAssetSourceRoots[assetRootIndexValue], selectedAssetEngines[assetRootIndexValue],
						stagedCompatOwnerRoots, ownerPlan, mappedOwnerPlans)
				: mergeMappedAssetRoot(assetsRoot, selectedAssetDestinations[assetRootIndexValue],
					selectedAssetSourceRoots[assetRootIndexValue], selectedAssetEngines[assetRootIndexValue],
					ownerPlan);
			result.copiedAssets += merged.copied;
			result.skippedAssets += merged.skipped;
			assetFailures += merged.failed;
			reportImportProgress('assets', assetsRoot, assetRootIndex, selectedAssetRoots.length,
				result.copiedAssets, result.skippedAssets, assetFailures);
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
		}
		// Psych note sheets are keyed by chart/Lua metadata, and must stay with
		// the selected donor even when ordinary images are also merged globally.
		for (engineRoot in engineRoots) {
			if (engineRoot.engine != ImportEngine.PSYCH) continue;
			var psychSourceRoots:Array<String> = [engineRoot.contentRoot];
			if (engineRoot.supplementalAssetRoots != null)
				for (supplemental in engineRoot.supplementalAssetRoots)
					if (supplemental != null && supplemental.path != null
						&& StringTools.trim(supplemental.path) != '')
						psychSourceRoots.push(supplemental.path);
			var uniquePsychSourceRoots:Array<String> = [];
			for (psychSourceRoot in psychSourceRoots) {
				var duplicate = false;
				for (existing in uniquePsychSourceRoots)
					if (importPathKey(existing) == importPathKey(psychSourceRoot)) {
						duplicate = true;
						break;
					}
				if (!duplicate && psychSourceRoot != null && FileSystem.isDirectory(psychSourceRoot))
					uniquePsychSourceRoots.push(psychSourceRoot);
			}
			psychSourceRoots = uniquePsychSourceRoots;
			var ownerRuntimeRoot = CompatScriptManifest.destinationRoot(engineRoot.root, engineRoot.engine);
			var ownerPlan = mappedOwnerPlan(mappedOwnerPlans, engineRoot.root, engineRoot.engine);
			for (mappedRoot in selectedAssetRootsForEngineRoot(engineRoot)) {
				var mediaMerge = mergePsychRuntimeMedia(mappedRoot.path, mappedRoot.destinationPrefix,
					ownerRuntimeRoot, ownerPlan);
				result.copiedAssets += mediaMerge.copied;
				result.skippedAssets += mediaMerge.skipped;
				assetFailures += mediaMerge.failed;
				if (mediaMerge.errors != null)
					for (message in mediaMerge.errors)
						result.errors.push(message);
			}
			var sourceModuleMerge = mergePsychSourceModules(engineRoot.root, ownerRuntimeRoot);
			result.copiedAssets += sourceModuleMerge.copied;
			result.skippedAssets += sourceModuleMerge.skipped;
			assetFailures += sourceModuleMerge.failed;
			if (sourceModuleMerge.errors != null)
				for (message in sourceModuleMerge.errors)
					result.errors.push(message);
			for (psychSourceRoot in psychSourceRoots) {
				var soundMerge = mergePsychRuntimeSounds(psychSourceRoot, ownerRuntimeRoot,
					ownerPlan);
				result.copiedAssets += soundMerge.copied;
				result.skippedAssets += soundMerge.skipped;
				assetFailures += soundMerge.failed;
				if (soundMerge.errors != null)
					for (message in soundMerge.errors)
						result.errors.push(message);
			}
			var charts:Array<Dynamic> = [];
			for (songData in importedSongs)
				if (songData != null && songData.engine == ImportEngine.PSYCH
					&& songData.sourceRoot != null
					&& importPathKey(songData.sourceRoot) == importPathKey(engineRoot.root)) {
					var targetFolder = importSongFolderName(songData);
					var targetData = existingImportChild('assets/data', targetFolder);
					if (songData.convertedCharts != null)
						for (converted in songData.convertedCharts)
							if (converted != null && converted.chart != null)
								charts.push(converted.chart);
					if (songData.diffFiles != null)
						for (index in 0...songData.diffFiles.length) {
							var path = songData.diffFiles[index];
							var chart = readSongChart(path);
							if (chart != null) charts.push(chart);
							var installed = readSongChart(existingImportChild(targetData,
								importedChartFileName(targetFolder, path, index, Reflect.field(songData, 'sourceFolder'))));
							if (installed != null) charts.push(installed);
						}
				}
			if (charts.length == 0) continue;
			for (psychSourceRoot in psychSourceRoots) {
				var skinMerge = PsychSkinImportAssets.copy(psychSourceRoot, ownerRuntimeRoot, charts);
				result.copiedAssets += skinMerge.copied;
				result.skippedAssets += skinMerge.skipped;
				assetFailures += skinMerge.failed;
				for (diagnostic in skinMerge.diagnostics)
					result.errors.push(diagnostic);
			}
		}
		// V-Slice chart/data trees need conversion, but its ordinary media trees
		// are directly useful.  Script-bearing trees are copied below a
		// per-source namespace so HXC discovery cannot execute a foreign global
		// script for an unrelated song.
		var vSliceLibraryRoots:Array<String> = [];
		var addVSliceLibraryRoot = function(root:String):Void {
			if (root == null || StringTools.trim(root) == '' || !FileSystem.isDirectory(root))
				return;
			var key = importPathKey(root);
			for (existing in vSliceLibraryRoots)
				if (importPathKey(existing) == key)
					return;
			vSliceLibraryRoots.push(root);
		};
		for (engineRoot in engineRoots)
			if (engineRoot.engine == ImportEngine.V_SLICE) {
				addVSliceLibraryRoot(engineRoot.contentRoot);
				addVSliceLibraryRoot(engineRoot.root);
			}
		for (engineRoot in engineRoots) {
			if (engineRoot.engine != ImportEngine.V_SLICE)
				continue;
			var mergedRuntime = mergeVSliceRuntimeAssets(engineRoot.contentRoot,
				engineRoot.root, engineRoot.engine, importedSongs, vSliceLibraryRoots);
			result.copiedAssets += mergedRuntime.copied;
			result.skippedAssets += mergedRuntime.skipped;
			assetFailures += mergedRuntime.failed;
			if (mergedRuntime.errors != null)
				for (message in mergedRuntime.errors)
					if (message != null && StringTools.trim(message) != '')
						result.errors.push(message);
		}
		for (songData in importedSongs)
			if (songData != null && songData.engine == ImportEngine.CODENAME) {
				var mergedRuntime = mergeCodenameRuntimeAssets(songData);
				result.copiedAssets += mergedRuntime.copied;
				result.skippedAssets += mergedRuntime.skipped;
				assetFailures += mergedRuntime.failed;
				if (mergedRuntime.errors != null)
					for (message in mergedRuntime.errors)
						result.errors.push(message);
			}
		// Psych charts refer to characters/<name>.json, while the destination
		// engine resolves playable characters through custom_chars.  Reuse the
		// existing converter for complete Psych roots after ordinary assets and
		// registries have been merged.  A failed optional character conversion is
		// isolated to that character and does not discard the song import.
		for (engineRoot in engineRoots) {
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
			if (engineRoot.engine == ImportEngine.PSYCH) {
				importPsychCharacters(engineRoot.contentRoot,
					CompatScriptManifest.destinationRoot(engineRoot.root, engineRoot.engine));
				if (engineRoot.supplementalAssetRoots != null)
					for (supplemental in engineRoot.supplementalAssetRoots)
						if (supplemental != null && supplemental.path != null
							&& StringTools.trim(supplemental.path) != '')
							importPsychCharacters(supplemental.path,
								CompatScriptManifest.destinationRoot(engineRoot.root, engineRoot.engine));
			}
			if (engineRoot.engine == ImportEngine.MODDING_PLUS) {
				try result.copiedAssets += ModPlusCharacterRegistry.repair(engineRoot.contentRoot, 'assets')
				catch (error:Dynamic) {
					result.failed++;
					result.errors.push('Modding Plus character registry repair: ' + Std.string(error));
				}
			}
		}
		// FPS Plus donors compile their character/stage definitions into
		// data/characters and data/stages HXC modules.  The chart ids resolve only
		// through those modules, so convert them into native custom_chars and
		// custom_stages implementations after the ordinary asset/registry merges.
		// A failed optional conversion is isolated and never discards the song.
		for (engineRoot in engineRoots) {
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
			if (engineRoot.engine == ImportEngine.FPS_PLUS) {
				var fpsMerge:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0, errors: []};
				importFpsPlusCharacters(engineRoot.contentRoot, fpsMerge);
				importFpsPlusStages(engineRoot.contentRoot, fpsMerge);
				result.copiedAssets += fpsMerge.copied;
				result.skippedAssets += fpsMerge.skipped;
				assetFailures += fpsMerge.failed;
				if (fpsMerge.errors != null)
					for (message in fpsMerge.errors)
						if (message != null && StringTools.trim(message) != '')
							result.errors.push(message);
			}
		}
		// Kade/FPS/legacy builds may have no character JSON/HScript at all: the
		// compiled donor definition is recoverable when its owning root contains a
		// uniquely associated Sparrow atlas.  This runs after ordinary media and
		// registry merges so native destination files still win on every collision.
		for (importedSong in importedSongs) {
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
			if (importedSong == null || !legacyAtlasEngine(importedSong.engine))
				continue;
			var atlasMerge = importLegacyCharacterAtlases(importedSong);
			result.copiedAssets += atlasMerge.copied;
			result.skippedAssets += atlasMerge.skipped;
			if (atlasMerge.failed > 0)
				result.failed += atlasMerge.failed;
			if (atlasMerge.errors != null)
				for (message in atlasMerge.errors)
					if (message != null && StringTools.trim(message) != '')
						result.errors.push(message);
		}
		// Every accepted imported song gets a destination-only manifest.  This is
		// also the repair path for imports made before script provenance existed:
		// a discovered donor song with no manifest is imported again, while all
		// existing chart/audio/registry bytes remain non-overwriting.
		for (importedSong in importedSongs) {
			if (importWorkCancelled()) {
				markImportCancelled(result);
				return result;
			}
			// importSong has already checked ownership before creating the target.
			// Record that accepted owner before checking the script manifest: a
			// pristine owner-qualified folder now contains charts/audio, so the
			// manifest guard needs this record to distinguish it from an unrelated
			// pre-existing folder.
			var provenanceMerge = writeImportProvenance(importedSong);
			result.copiedAssets += provenanceMerge.copied;
			result.skippedAssets += provenanceMerge.skipped;
			assetFailures += provenanceMerge.failed;
			if (provenanceMerge.errors != null)
				for (message in provenanceMerge.errors)
					if (message != null && StringTools.trim(message) != '')
						result.errors.push(message);
			var manifestMerge = writeCompatScriptManifest(importedSong);
			result.copiedAssets += manifestMerge.copied;
			result.skippedAssets += manifestMerge.skipped;
			assetFailures += manifestMerge.failed;
		}
		// Registry-backed visual validation is cached by Song for chart loading.
		// Refreshes happen on the Flixel thread when ImportImportJob is running in
		// its native worker; synchronous callers retain the old behavior.
		if (!importBackgroundMode) {
			var supportNames:Array<String> = [];
			for (songData in importedSongs) {
				var folderName = importSongFolderName(songData);
				if (folderName != '' && supportNames.indexOf(folderName) < 0)
					supportNames.push(folderName);
			}
			completeImportOnMainThread(supportNames);
		}
		if (assetFailures > 0) {
			result.failed += assetFailures;
			result.errors.push('Could not copy ' + assetFailures + ' supported item(s).');
		}
		reportImportProgress('complete', '', 1, 1, result.copiedAssets, result.skippedAssets, result.failed);
		return result;
	}
	#else
	static public function importSongsFromPath(sourcePath:String, ?importType:String,
		?plannedOverlays:Array<ImportOverlayMount>, ?packageNames:Map<String, String>):SongImportBatchResult {
		return {
			found: 0,
			imported: 0,
			importedSongs: [],
			skipped: 0,
			failed: 0,
			copiedAssets: 0,
			skippedAssets: 0,
			errors: ['Song importing is unavailable on this target.'],
			overlayPlanned: 0,
			overlayApplied: 0,
			overlayRetained: 0,
			overlaySkipped: 0,
			overlayDiagnostics: [],
			overlayProvenance: [],
			overlayRetentions: []
		};
	}
	#end

	static public function importBatchSummary(result:SongImportBatchResult, ?compact:Bool = false):String {
		if (result == null)
			return 'No import result was returned.';
		var summary = 'Found ' + result.found + ' song(s): imported ' + result.imported + ', skipped ' + result.skipped + ' duplicate(s), failed ' + result.failed + '.';
		if (result.copiedAssets > 0)
			summary += ' Copied ' + result.copiedAssets + ' supported asset(s).';
		if (result.globalPacksImported != null && result.globalPacksImported > 0)
			summary += ' Imported ' + result.globalPacksImported + ' Psych global pack(s).';
		if (result.skippedAssets > 0)
			summary += ' Skipped ' + result.skippedAssets + ' existing asset(s).';
		if (result.failed > 0)
			summary += ' Failed ' + result.failed + '.';
		if (result.overlayPlanned != null && result.overlayPlanned > 0)
			summary += ' Overlays: ' + result.overlayApplied + ' applied, ' + result.overlayRetained
				+ ' retained, ' + result.overlaySkipped + ' skipped.';
		if (result.overlayProvenance != null && result.overlayProvenance.length > 0) {
			if (compact)
				summary += ' Overlay provenance: ' + result.overlayProvenance.length + ' source(s).';
			else
				summary += ' Overlay provenance: ' + result.overlayProvenance.join(', ') + '.';
		}
		if (result.overlayDiagnostics != null && result.overlayDiagnostics.length > 0) {
			if (compact)
				summary += ' ' + result.overlayDiagnostics.length
					+ ' overlay diagnostic(s); see the details and import-report.txt.';
			else
				summary += ' Overlay diagnostics: ' + result.overlayDiagnostics.join(' ');
		}
		if (result.errors != null && result.errors.length > 0) {
			if (compact)
				summary += ' ' + result.errors.length + ' diagnostic(s); see the details and import-report.txt.';
			else
				summary += ' ' + result.errors.join(' ');
		}
		return summary;
	}

	#if sys
	static function refreshDifficultySupport(importedNames:Map<String, Bool>):Void {
		if (importedNames == null)
			return;
		for (songName in importedNames.keys()) {
			try {
				DifficultyManager.addSongSupport(songName);
			} catch (error:Dynamic) {
				// DifficultyManager is initialized by TitleState in normal play. A
				// menu test or early startup can legitimately reach this first.
			}
		}
	}
	#end

	/** Build the common Modding Plus song payload from an import folder. */
	static public function songImportFromFolder(basePath:String, ?rename:String):SongImport {
		#if sys
		var folderName = Path.withoutDirectory(Path.normalize(basePath));
		var noteDefinitions:Array<Dynamic> = [];
		var charts = collectImportCharts(basePath, noteDefinitions);
		return songImportFromRoots(basePath, basePath, folderName, charts, rename, noteDefinitions);
		#else
		return null;
		#end
	}

	#if sys
	static function chartFieldString(chart:Dynamic, field:String, fallback:String):String {
		if (chart != null) {
			var value:Dynamic = Reflect.field(chart, field);
			if (value != null) {
				var text = StringTools.trim(Std.string(value));
				if (text != '' && text.toLowerCase() != 'null')
					return text;
			}
		}
		return fallback;
	}

	/** Psych uses backend/StageData.hx to choose a vanilla stage when the chart
		omits its stage. Apply that source-owned default only when neither the chart
		nor info.txt authored a value; later per-chart serialization still keeps
		explicit difficulty-specific stages intact. */
	static function inferPsychStageForImport(songData:SongImport, chartSong:Dynamic,
		sourceRoot:String, chartRoot:String, fallbackSongName:String):Void {
		if (songData == null || sourceRoot == null || StringTools.trim(sourceRoot) == '')
			return;
		var info = processInfo(Path.join([chartRoot, 'info.txt']));
		var infoStage = getInfoValue(info, 'stage', 'null');
		if (infoStage != null && StringTools.trim(infoStage) != ''
			&& infoStage.toLowerCase() != 'null')
			return;
		if (chartFieldString(chartSong, 'stage', null) != null)
			return;
		var songName = chartFieldString(chartSong, 'song', fallbackSongName);
		var inferredStage = PsychStageInference.resolve(sourceRoot, songName);
		if (inferredStage != null && StringTools.trim(inferredStage) != ''
			&& inferredStage.toLowerCase() != 'null')
			songData.stage = inferredStage;
	}

	static function chartFieldBool(chart:Dynamic, field:String, fallback:Bool):Bool {
		if (chart == null)
			return fallback;
		var value:Dynamic = Reflect.field(chart, field);
		if (value == null)
			return fallback;
		if (Std.isOfType(value, Bool))
			return cast value;
		var text = StringTools.trim(Std.string(value)).toLowerCase();
		return text == 'true' || text == '1' || text == 'yes';
	}

	static function chartFieldInt(chart:Dynamic, field:String, fallback:Int):Int {
		if (chart == null)
			return fallback;
		var value:Dynamic = Reflect.field(chart, field);
		if (value == null)
			return fallback;
		var parsed = Std.parseInt(Std.string(value));
		return parsed == null ? fallback : parsed;
	}

	/** Normalize source-game-only labels at the import boundary. `Base Game`
		is relative to the donor installation, so imported songs belong under the
		destination engine's Imported category. Other authored categories remain
		available for packs which organize their songs into named groups. */
	static function normalizeImportedCategory(value:Dynamic):String {
		var category = value == null ? '' : StringTools.trim(Std.string(value));
		if (category == '' || category.toLowerCase() == 'null' || category.toLowerCase() == 'base game')
			return 'Imported';
		return category;
	}

	static function findChildDirectory(parent:String, name:String):String {
		if (parent == null || name == null || !FileSystem.isDirectory(parent))
			return null;
		var exact = Path.join([parent, name]);
		if (FileSystem.isDirectory(exact))
			return exact;
		try {
			var entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(parent));
			entries.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				if (entry.toLowerCase() == name.toLowerCase()) {
					var candidate = Path.join([parent, entry]);
					if (FileSystem.isDirectory(candidate))
						return candidate;
				}
			}
		} catch (error:Dynamic) {
			return null;
		}
		return null;
	}

	/**
		Populate the shared noteInfo table for legacy/Psych chart noteType
		strings. This pass reads only source JSON and does not write or mutate it.
		The authored fourth row value stays in the destination chart; PlayState
		resolves it transiently when it creates runtime Notes.
	*/
	static function prepareSongNoteDefinitions(songData:SongImport):Void {
		#if sys
		if (songData == null || songData.diffFiles == null)
			return;
		if (songData.noteDefinitions == null)
			songData.noteDefinitions = [];
		for (chartPath in songData.diffFiles) {
			if (chartPath == null || !isImportFile(chartPath))
				continue;
			var chart = readSongChart(chartPath);
			if (chart != null)
				collectSongNoteDefinitions(chart, songData.noteDefinitions);
		}
		if (songData.noteDefinitions.length == 0)
			songData.noteDefinitions = null;
		#end
	}

	static function collectSongNoteDefinitions(chart:Dynamic, definitions:Array<Dynamic>):Void {
		if (chart == null || definitions == null)
			return;
		var song:Dynamic = Reflect.field(chart, 'song');
		var notes:Dynamic = song == null ? null : Reflect.field(song, 'notes');
		if (notes == null || !Std.isOfType(notes, Array))
			return;
		for (section in (cast notes:Array<Dynamic>)) {
			if (section == null)
				continue;
			var rows:Dynamic = Reflect.field(section, 'sectionNotes');
			if (rows == null || !Std.isOfType(rows, Array))
				continue;
			for (row in (cast rows:Array<Dynamic>)) {
				if (row == null || !Std.isOfType(row, Array))
					continue;
				var values:Array<Dynamic> = cast row;
				if (values.length < 4 || !NoteTypeCompat.isStringType(values[3]))
					continue;
				NoteTypeCompat.ensureDefinition(values[3], definitions);
			}
		}
	}

	static function songImportFromRoots(audioRoot:String, chartRoot:String, fallbackName:String, charts:Array<String>,
		?rename:String, ?collectedNoteDefinitions:Array<Dynamic>):SongImport {
		var info = processInfo(Path.join([chartRoot, 'info.txt']));
		var primaryChart:Dynamic = null;
		for (chartPath in charts) {
			if (chartPath != null) {
				primaryChart = readSongChart(chartPath);
				if (primaryChart != null)
					break;
			}
		}
		var chartSong:Dynamic = primaryChart == null ? null : primaryChart.song;
		var name = getInfoValue(info, 'songname', chartFieldString(chartSong, 'song', fallbackName));
		if (rename != null && StringTools.trim(rename) != '')
			name = StringTools.trim(rename);
		// Psych calls this field `gfVersion`; native charts use `gf`.  Resolve
		// both spellings before the importer writes the destination chart so
		// imported songs do not silently fall back to the stock girlfriend.
		var chartGirlfriend = chartFieldString(chartSong, 'gf',
			chartFieldString(chartSong, 'gfVersion', 'gf'));
		var modchart = findImportFile(chartRoot, ['modchart.hscript']);
		var generatedModchart:String = null;
		var scriptDiagnostics:Array<String> = [];
		if (modchart == null) {
			var luaModchart = findImportFile(chartRoot, ['modchart.lua']);
			if (luaModchart != null) {
				try {
					var luaResult = LuaCompat.translate(File.getContent(luaModchart), luaModchart);
					generatedModchart = luaResult.hscript;
					for (diagnostic in luaResult.diagnostics)
						scriptDiagnostics.push(diagnostic);
				} catch (error:Dynamic) {
					scriptDiagnostics.push('[lua-translate-error] ' + luaModchart + ': ' + Std.string(error));
				}
			}
		}
		// FPS Plus keeps presentation/credits/difficulty ratings in one
		// song-local meta.json which is intentionally excluded from chart
		// discovery by isImportChartSidecar().  Read that optional sidecar once,
		// map the fields understood by the native chart/freeplay schemas, and
		// retain the complete parsed object so future/unknown keys are not lost.
		var metadataPath = findImportFile(chartRoot, ['meta.json', 'meta.jsonc']);
		var metadata:Dynamic = metadataPath == null ? null : readImportJson(metadataPath);
		var metadataDisplay:String = null;
		var metadataArtist:String = null;
		var metadataAlbum:String = null;
		var metadataRatings:Array<Dynamic> = null;
		var compatibilityMetadata:Dynamic = null;
		var addMetadataDiagnostic = function(message:String):Void {
			if (scriptDiagnostics == null)
				scriptDiagnostics = [];
			scriptDiagnostics.push('[fps-meta-invalid] ' + metadataPath + ': ' + message);
		};
		if (metadataPath != null) {
			compatibilityMetadata = {
				format: 'fps-plus-song-meta',
				sourceFile: Path.withoutDirectory(Path.normalize(metadataPath)),
				raw: metadata
			};
			var metadataIsObject = metadata != null && !Std.isOfType(metadata, Array)
				&& !Std.isOfType(metadata, String) && !Std.isOfType(metadata, Bool)
				&& !Std.isOfType(metadata, Int) && !Std.isOfType(metadata, Float);
			if (!metadataIsObject) {
				Reflect.setField(compatibilityMetadata, 'invalid', true);
				addMetadataDiagnostic('expected a JSON object');
			} else {
				var metadataString = function(fieldName:String):String {
					var value:Dynamic = Reflect.field(metadata, fieldName);
					if (value == null)
						return null;
					if (!Std.isOfType(value, String)) {
						addMetadataDiagnostic(fieldName + ' must be a string');
						return null;
					}
					var text = StringTools.trim(Std.string(value));
					if (text == '') {
						addMetadataDiagnostic(fieldName + ' must not be empty');
						return null;
					}
					return text;
				};
				metadataDisplay = metadataString('name');
				metadataArtist = metadataString('artist');
				metadataAlbum = metadataString('album');
				var rawRatings:Dynamic = Reflect.field(metadata, 'difficulties');
				if (rawRatings != null) {
					if (!Std.isOfType(rawRatings, Array)) {
						addMetadataDiagnostic('difficulties must be an array of numbers');
					} else {
						var parsedRatings:Array<Dynamic> = [];
						var ratingValues:Array<Dynamic> = cast rawRatings;
						var ratingsValid = true;
						for (rawRating in ratingValues) {
							var parsedRating = rawRating == null ? Math.NaN : Std.parseFloat(Std.string(rawRating));
							if (Math.isNaN(parsedRating) || parsedRating == Math.POSITIVE_INFINITY
								|| parsedRating == Math.NEGATIVE_INFINITY) {
								ratingsValid = false;
								break;
							}
							parsedRatings.push(parsedRating);
						}
						if (ratingsValid)
							metadataRatings = parsedRatings;
						else
							addMetadataDiagnostic('difficulties must contain only finite numeric ratings');
					}
				}
			}
		}
		var result:SongImport = {
			name: name,
			p1: getInfoValue(info, 'player1', chartFieldString(chartSong, 'player1', 'bf')),
			p2: getInfoValue(info, 'player2', chartFieldString(chartSong, 'player2', 'dad')),
			gf: getInfoValue(info, 'gf', getInfoValue(info, 'gfVersion', chartGirlfriend)),
			stage: getInfoValue(info, 'stage', chartFieldString(chartSong, 'stage', 'stage')),
			ui: getInfoValue(info, 'uiType', chartFieldString(chartSong, 'uiType', 'normal')),
			cutscene: getInfoValue(info, 'cutsceneType', chartFieldString(chartSong, 'cutsceneType', 'none')),
			category: normalizeImportedCategory(getInfoValue(info, 'category', 'Imported')),
			isHey: getInfoBool(info, 'isHey', chartFieldBool(chartSong, 'isHey', false)),
			isCheer: getInfoBool(info, 'isCheer', chartFieldBool(chartSong, 'isCheer', false)),
			isMoody: getInfoBool(info, 'isMoody', chartFieldBool(chartSong, 'isMoody', false)),
			isSpooky: getInfoBool(info, 'isSpooky', chartFieldBool(chartSong, 'isSpooky', false)),
			stageID: getInfoInt(info, 'stageID', chartFieldInt(chartSong, 'stageID', 0)),
			week: getInfoInt(info, 'week', -1),
			char: getInfoValue(info, 'char', 'null'),
			display: getInfoValue(info, 'display', metadataDisplay == null ? 'null' : metadataDisplay),
			inst: findImportAudio(audioRoot),
			voices: findImportAudio(audioRoot, true),
			dialog: findImportFile(chartRoot, ['dialog.txt']),
			dialogueJson: findImportFile(chartRoot, ['dialogue.json', 'dialogue.jsonc', 'dialog.json', 'dialog.jsonc']),
			cutsceneJson: findImportFile(chartRoot, ['cutscene.json', 'cutscene.jsonc']),
			events: findImportFile(chartRoot, ['events.json', 'events.jsonc']),
			modchart: modchart,
			generatedModchart: generatedModchart,
			diagnostics: scriptDiagnostics.length == 0 ? null : scriptDiagnostics,
			diffFiles: charts
		};
		if (metadataArtist != null)
			Reflect.setField(result, 'songArtist', metadataArtist);
		if (metadataAlbum != null)
			Reflect.setField(result, 'album', metadataAlbum);
		if (metadataRatings != null)
			Reflect.setField(result, 'difficultyRatings', metadataRatings);
		if (compatibilityMetadata != null)
			Reflect.setField(result, 'compatMetadata', compatibilityMetadata);
		// Keep the donor folder id separate from the chart's presentation name.
		// The latter may be "Dad Battle" while the source data/audio folder is
		// `dad-battle`; the destination must retain the id for native lookup.
		var sourceFolder = rename != null && StringTools.trim(rename) != ''
			? name : Path.withoutDirectory(Path.normalize(chartRoot));
		if (validModuleName(sourceFolder))
			Reflect.setField(result, 'sourceFolder', sourceFolder);
		var dialogueText = convertImportDialogue(result.dialogueJson, result.p1, result.p2);
		if (dialogueText != null && StringTools.trim(dialogueText) != '')
			Reflect.setField(result, 'dialogueText', dialogueText);
		var cutsceneScript = importCutsceneScript(result.cutsceneJson);
		if (cutsceneScript != null && StringTools.trim(cutsceneScript) != '') {
			Reflect.setField(result, 'cutsceneScript', cutsceneScript);
			Reflect.setField(result, 'cutsceneStoryOnly', importCutsceneBool(result.cutsceneJson, 'storyOnly', true));
			Reflect.setField(result, 'cutscenePlayOnce', importCutsceneBool(result.cutsceneJson, 'playOnce', true));
		}
		var splitVocalStems = findImportVocalStems(audioRoot);
		if (splitVocalStems.length > 0)
			Reflect.setField(result, 'vocalStems', splitVocalStems);
			// Psych/Kade store a string note type in sectionNotes[3], while this
			// engine's native schema historically expected a numeric alt selector.
			// Collect source names during the read-only plan so repair scans know when
			// noteInfo.json is required. The authored row remains unchanged; the
			// runtime adapter resolves it when Note objects are created.
			if (collectedNoteDefinitions == null)
				prepareSongNoteDefinitions(result);
			else
				result.noteDefinitions = collectedNoteDefinitions.length == 0 ? null : collectedNoteDefinitions;
			applyKadeSourceStageCompatibility(result, chartRoot, chartSong);
			applyKadeSourceCharacterCompatibility(result, chartRoot, chartSong);
		return result;
	}

	/** Check the legacy music folder by exact candidate names only. */
	static function findLegacyMusicAudio(musicPath:String, songName:String, voices:Bool = false):String {
		if (musicPath == null || songName == null || !FileSystem.isDirectory(musicPath))
			return null;
		var suffix = voices ? '_Voices.ogg' : '_Inst.ogg';
		var alternate = voices ? '-Voices.ogg' : '-Inst.ogg';
		var names = [songName + suffix, songName + alternate,
			songName + (voices ? 'Voices.ogg' : 'Inst.ogg')];
		if (voices)
			names.push(songName + 'VoicesTogether.ogg');
		return findImportFile(musicPath, names);
	}

	static function songImportFromAssetFolders(songPath:String, dataPath:String, folderName:String, ?musicPath:String):SongImport {
		var noteDefinitions:Array<Dynamic> = [];
		var charts = collectAssetCharts(dataPath, folderName, noteDefinitions);
		var songData = songImportFromRoots(songPath, dataPath, folderName, charts, null, noteDefinitions);
		if (songData != null && songData.inst == null)
			songData.inst = findLegacyMusicAudio(musicPath, folderName);
		if (songData != null && songData.voices == null)
			songData.voices = findLegacyMusicAudio(musicPath, folderName, true);
		return songData;
	}

	static function isAssetsRoot(path:String):Bool {
		if (path == null || !FileSystem.isDirectory(path))
			return false;
		var baseName = Path.withoutDirectory(Path.normalize(path)).toLowerCase();
		if (baseName == 'assets')
			return true;
		return findChildDirectory(path, 'songs') != null && findChildDirectory(path, 'data') != null;
	}

	static function isAssetRootSearchName(name:String):Bool {
		if (name == null)
			return false;
		var lower = name.toLowerCase();
		return lower == 'assets' || lower == 'game' || lower == 'games' || lower == 'mod'
			|| lower == 'mods' || lower == 'modpack' || lower == 'modpacks' || lower == 'pack'
			|| lower == 'packs' || lower == 'content' || lower == 'songs' || lower == 'data'
			|| lower == 'module' || lower == 'import' || lower == 'export' || lower == 'custom_songs';
	}

	/**
	 * Find all supported assets roots below a selection.  The broad first four
	 * levels make nested downloaded packs discoverable; after that only ordinary
	 * content-container names are followed.  An assets root is a leaf for this
	 * search, so a complete game is never recursively walked a second time.
	 */
	static function findSelectedAssetsRoots(selectedPath:String):Array<String> {
		var roots:Array<String> = [];
		var root = ImportSettings.normalizeSourcePath(selectedPath);
		if (root == '' || !FileSystem.isDirectory(root))
			return roots;

		var seen:Map<String, Bool> = new Map<String, Bool>();
		var addRoot = function(candidate:String):Void {
			if (candidate == null || !isAssetsRoot(candidate))
				return;
			// Never enumerate or copy the current game's own assets tree.
			if (importPathIsWithin(candidate, 'assets'))
				return;
			var key = importPathKey(candidate);
			if (key == '' || seen.exists(key))
				return;
			seen.set(key, true);
			roots.push(Path.normalize(candidate));
		};

		// If the picker was opened from a nested directory, retain the useful
		// ancestor-assets behavior from the old single-folder importer.
		var ancestor = root;
		for (i in 0...MAX_ASSETS_ROOT_DEPTH) {
			if (isAssetsRoot(ancestor))
				addRoot(ancestor);
			var parent = Path.directory(ancestor);
			if (parent == null || parent == '' || parent == ancestor)
				break;
			ancestor = parent;
		}

		var queue:Array<{path:String, depth:Int}> = [{path:root, depth:0}];
		var cursor = 0;
		var scanned = 0;
		while (cursor < queue.length && scanned < MAX_ASSETS_ROOT_DIRECTORIES) {
			if (importWorkCancelled())
				break;
			var item = queue[cursor++];
			var current = Path.normalize(item.path);
			if (importPathIsWithin(current, 'assets') || isAssetsRoot(current)) {
				addRoot(current);
				continue;
			}
			scanned++;
			yieldImportWork();
			reportImportProgress('scan-roots', current, scanned, MAX_ASSETS_ROOT_DIRECTORIES);
			if (item.depth >= MAX_ASSETS_ROOT_DEPTH)
				continue;
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(current));
			} catch (error:Dynamic) {
				continue;
			}
			for (entry in entries) {
				if (importWorkCancelled())
					break;
				var child = Path.join([current, entry]);
				if (!FileSystem.isDirectory(child) || importPathIsWithin(child, 'assets'))
					continue;
				var lower = entry.toLowerCase();
				if (lower == '.git' || lower == '.tools' || lower == '.haxelib' || lower == 'node_modules'
					|| lower == 'bin' || lower == 'cache' || lower == 'music' || lower == 'sounds'
					|| lower == 'videos' || lower == 'fonts' || lower == 'shaders')
					continue;
				if (item.depth < 4 || isAssetRootSearchName(lower))
					queue.push({path:child, depth:item.depth + 1});
			}
		}
		return roots;
	}

	static function findSelectedAssetsRoot(selectedPath:String):String {
		var roots = findSelectedAssetsRoots(selectedPath);
		return roots.length == 0 ? null : roots[0];
	}

	#end

	static function importFileIfPresent(basePath:String, fileName:String):String {
		var path = Path.join([basePath, fileName]);
		return isImportFile(path) ? path : null;
	}

	static function isImportFile(path:String):Bool {
		return path != null && StringTools.trim(path) != '' && FileSystem.exists(path) && !FileSystem.isDirectory(path);
	}

	static function validImportPath(path:String):Bool {
		return isImportFile(path);
	}

	static function validModuleName(name:String):Bool {
		if (name == null)
			return false;
		var trimmed = StringTools.trim(name);
		return trimmed != '' && trimmed != '.' && trimmed != '..'
			&& trimmed.indexOf('/') < 0 && trimmed.indexOf('\\') < 0 && trimmed.indexOf(':') < 0
			&& trimmed.indexOf('\u0000') < 0;
	}

	/**
		Return the destination key used by native chart/audio lookup.

		Foreign charts frequently use a presentation name in their JSON while
		storing the actual data/audio below a slugged folder (for example
		`Dad Battle` -> `dad-battle`).  The source folder is authoritative when
		available; falling back to the song name preserves the legacy package
		workflow and old callers which construct SongImport values themselves.
	*/
	static function importSongFolderName(songData:SongImport):String {
		if (songData == null)
			return '';
		var destinationFolder:Dynamic = Reflect.field(songData, 'destinationFolder');
		if (destinationFolder != null) {
			var destinationValue = StringTools.trim(Std.string(destinationFolder));
			if (validModuleName(destinationValue))
				return destinationValue.toLowerCase();
		}
		var sourceFolder:Dynamic = Reflect.field(songData, 'sourceFolder');
		if (sourceFolder != null) {
			var sourceValue = StringTools.trim(Std.string(sourceFolder));
			if (validModuleName(sourceValue))
				return sourceValue.toLowerCase();
		}
		var name = StringTools.trim(songData.name == null ? '' : songData.name);
		return validModuleName(name) ? name.toLowerCase() : '';
	}

	static function ensureDirectory(path:String):Void {
		if (path == null || StringTools.trim(path) == '' || FileSystem.exists(path))
			return;
		var parent = Path.directory(path);
		if (parent != null && parent != '' && parent != path)
			ensureDirectory(parent);
		FileSystem.createDirectory(path);
	}

	static function copyIfPresent(source:String, destination:String):Void {
		// A song is one import unit.  Once its chart write has started, finish its
		// optional sidecar/audio copies before observing cancellation at the next
		// song boundary; this avoids leaving a partially populated song folder.
		if (validImportPath(source)) {
			// A crashed import may have left this media file behind without
			// registering the song.  Repair only missing files; never replace user
			// audio or sidecars.
			var existingDestination = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
			if (FileSystem.exists(existingDestination)) {
				if (FileSystem.isDirectory(existingDestination))
					throw 'Unable to import asset: destination is a directory: ' + existingDestination;
				return;
			}
			ensureDirectory(Path.directory(destination));
			reportImportProgress('song-assets', destination, 0, 0, 0, 0, 0);
			try {
				File.copy(source, destination);
				reportImportProgress('song-assets', destination, 0, 0, 1, 0, 0, 1);
			} catch (error:Dynamic) {
				reportImportProgress('song-assets', destination, 0, 0, 0, 0, 1, 1);
				throw error;
			}
		}
	}

	/**
		Copy a required song asset and verify that it materialized at the
		destination.  `copyIfPresent` is deliberately best-effort for optional
		sidecars, but using it for Inst.ogg made a donor disappearing between
		validation and copy look like a successful import: the freeplay registry
		was then written even though the song had no instrumental audio.  Keep the
		check here, immediately at the required-copy boundary, so every caller
		gets the same no-visible-song guarantee.
	*/
	static function copyRequired(source:String, destination:String, label:String):Void {
		var materialized = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
		// A repair may be filling a missing chart while a previous attempt already
		// left valid instrumental audio behind.  That destination byte satisfies
		// the required asset even if the donor has since been moved or removed.
		if (FileSystem.exists(materialized)) {
			if (FileSystem.isDirectory(materialized))
				throw 'Required ' + label + ' is a directory: ' + destination;
			if (hasMaterializedFile(materialized))
				return;
		}
		if (!validImportPath(source))
			throw 'Missing required ' + label + ': ' + (source == null ? '' : source);
		copyIfPresent(source, destination);
		materialized = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
		if (!hasMaterializedFile(materialized))
			throw 'Required ' + label + ' did not materialize at: ' + destination;
	}

	/** Required binary assets must not be zero-byte leftovers from a crash. */
	static function hasMaterializedFile(path:String):Bool {
		if (path == null || !FileSystem.exists(path) || FileSystem.isDirectory(path))
			return false;
		try {
			return FileSystem.stat(path).size > 0;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/**
		A previous import can have committed Inst.ogg before its chart or
		freeplay registration.  Let that partial destination repair continue even
		when the donor audio has since moved away; a missing/empty destination is
		still a hard validation failure for a new import.
	*/
	static function hasExistingSongInstrumental(songData:SongImport):Bool {
		if (songData == null)
			return false;
		var folder = importSongFolderName(songData);
		if (!validModuleName(folder))
			return false;
		var songsRoot = Path.join(['assets', 'songs']);
		var songFolder = existingImportChild(songsRoot, folder);
		var instrumental = existingImportChild(songFolder, 'Inst.ogg');
		return hasMaterializedFile(instrumental);
	}

	/**
		An existing destination chart is intentionally never overwritten, but it
		still has to be a readable chart before the song can be registered.  This
		also catches a partial/crashed import which left an empty chart file behind.
	*/
	static function requireChartMaterialized(destination:String):Void {
		var materialized = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
		if (!FileSystem.exists(materialized) || FileSystem.isDirectory(materialized)
			|| readSongChart(materialized) == null)
			throw 'Required chart did not materialize at: ' + destination;
	}

	/** Add destination-only metadata adapters without changing authored charts. */
	static function applyImportedSidecars(chartSong:Dynamic, songData:SongImport, ?difficultyIndex:Int):Void {
		if (chartSong == null || songData == null)
			return;
		// Keep parsed foreign metadata inside the native chart envelope.  This is
		// destination-side provenance: no donor path or executable code is stored,
		// while unknown FPS Plus keys remain available to future adapters.
		var importedMetadata:Dynamic = Reflect.field(songData, 'compatMetadata');
		var compatibilityMetadata:Dynamic = importedMetadata == null ? null : Reflect.copy(importedMetadata);
		var cameraZoomMode = importedCameraZoomMode(chartSong);
		if (cameraZoomMode != '') {
			if (compatibilityMetadata == null)
				compatibilityMetadata = {};
			Reflect.setField(compatibilityMetadata, 'cameraZoomMode', cameraZoomMode);
		}
		if (compatibilityMetadata != null)
			Reflect.setField(chartSong, 'compatMetadata', compatibilityMetadata);
		var difficultyRatings:Dynamic = Reflect.field(songData, 'difficultyRatings');
		if (difficultyRatings != null && Std.isOfType(difficultyRatings, Array)) {
			Reflect.setField(chartSong, 'difficultyRatings', difficultyRatings);
			if (difficultyIndex != null && difficultyIndex >= 0
				&& difficultyIndex < (cast difficultyRatings:Array<Dynamic>).length) {
				var rating = (cast difficultyRatings:Array<Dynamic>)[difficultyIndex];
				if (rating != null)
					Reflect.setField(chartSong, 'difficultyRating', rating);
			}
		}
		var cutsceneScript:Dynamic = Reflect.field(songData, 'cutsceneScript');
		if (cutsceneScript != null && StringTools.trim(Std.string(cutsceneScript)) != '') {
			Reflect.setField(chartSong, 'cutsceneScript', Std.string(cutsceneScript));
			var storyOnly:Dynamic = Reflect.field(songData, 'cutsceneStoryOnly');
			if (storyOnly != null)
				Reflect.setField(chartSong, 'cutsceneStoryOnly', storyOnly == true);
			var playOnce:Dynamic = Reflect.field(songData, 'cutscenePlayOnce');
			if (playOnce != null)
				Reflect.setField(chartSong, 'cutscenePlayOnce', playOnce == true);
		}
	}

	/**
	 * Classify the legacy absolute-target spelling of Add Camera Zoom at import
	 * time. The convention is semantic rather than song-specific: two or more
	 * equal game/HUD values form a strictly increasing target sequence beginning
	 * at time zero before the first playable note. Ordinary Psych pulses remain
	 * additive and receive no metadata.
	 */
	public static function importedCameraZoomMode(chartSong:Dynamic):String {
		if (chartSong == null)
			return '';
		var firstNote = 1e30;
		var sections:Dynamic = Reflect.field(chartSong, 'notes');
		if (sections != null && Std.isOfType(sections, Array))
			for (section in (cast sections:Array<Dynamic>)) {
				var rows:Dynamic = section == null ? null : Reflect.field(section, 'sectionNotes');
				if (rows == null || !Std.isOfType(rows, Array))
					continue;
				for (row in (cast rows:Array<Dynamic>)) {
					if (row == null || !Std.isOfType(row, Array))
						continue;
					var values:Array<Dynamic> = cast row;
					if (values.length < 2 || values[0] == null || values[1] == null)
						continue;
					var lane = Std.parseInt(Std.string(values[1]));
					var time = Std.parseFloat(Std.string(values[0]));
					if (lane != null && lane >= 0 && !Math.isNaN(time) && time < firstNote)
						firstNote = time;
				}
			}
		var events:Dynamic = Reflect.field(chartSong, 'events');
		if (events == null || !Std.isOfType(events, Array))
			return '';
		var firstTime = 1e30;
		var lastTarget = -1e30;
		var targetCount = 0;
		for (eventRow in (cast events:Array<Dynamic>)) {
			if (eventRow == null || !Std.isOfType(eventRow, Array))
				continue;
			var row:Array<Dynamic> = cast eventRow;
			if (row.length < 2 || row[0] == null || row[1] == null
				|| !Std.isOfType(row[1], Array))
				continue;
			var eventTime = Std.parseFloat(Std.string(row[0]));
			if (Math.isNaN(eventTime) || eventTime >= firstNote - 0.000001)
				continue;
			for (eventData in (cast row[1]:Array<Dynamic>)) {
				if (eventData == null || !Std.isOfType(eventData, Array))
					continue;
				var values:Array<Dynamic> = cast eventData;
				if (values.length < 3 || values[0] == null)
					continue;
				var normalized = Std.string(values[0]).toLowerCase();
				for (separator in [' ', '-', '_'])
					normalized = StringTools.replace(normalized, separator, '');
				if (normalized != 'addcamerazoom')
					continue;
				var gameZoom = Std.parseFloat(Std.string(values[1]));
				var hudZoom = Std.parseFloat(Std.string(values[2]));
				if (Math.isNaN(gameZoom) || Math.isNaN(hudZoom) || gameZoom < 0.3
					|| gameZoom > 2 || Math.abs(gameZoom - hudZoom) > 0.000001)
					continue;
				if (targetCount > 0 && gameZoom <= lastTarget + 0.000001)
					return '';
				if (targetCount == 0)
					firstTime = eventTime;
				lastTarget = gameZoom;
				targetCount++;
			}
		}
		return targetCount >= 2 && Math.abs(firstTime) <= 0.000001
			? 'absolute-target-intro' : '';
	}

	/** Write generated fallback text only when an import has no native dialogue. */
	static function writeGeneratedDialogue(songData:SongImport, dataFolder:String):Void {
		if (songData == null || dataFolder == null || songData.dialog != null)
			return;
		var text:Dynamic = Reflect.field(songData, 'dialogueText');
		if (text == null || StringTools.trim(Std.string(text)) == '')
			return;
		var destination = existingImportChild(dataFolder, 'dialog.txt');
		if (FileSystem.exists(destination))
			return;
		try {
			ensureDirectory(dataFolder);
			File.saveContent(Path.join([dataFolder, 'dialog.txt']), Std.string(text));
		} catch (error:Dynamic) {
			trace('Unable to write imported dialogue fallback: ' + error);
		}
	}

	static public function validateSongImport(songData:SongImport):String {
		if (songData == null)
			return 'No song data was provided.';
		if (songData.name == null || StringTools.trim(songData.name) == '')
			return 'The song needs a name.';
		if (StringTools.trim(songData.name) == '.' || StringTools.trim(songData.name) == '..')
			return 'The song name is not valid.';
		if (songData.name.indexOf('/') >= 0 || songData.name.indexOf('\\') >= 0 || songData.name.indexOf(':') >= 0)
			return 'The song name cannot contain a path separator.';
		if (!validImportPath(songData.inst) && !hasExistingSongInstrumental(songData))
			return 'The song is missing Inst.ogg.';
		var chartCount = 0;
		if (songData.convertedCharts != null)
			for (converted in songData.convertedCharts)
				if (converted != null && converted.chart != null && Reflect.field(converted.chart, 'song') != null)
					chartCount++;
		if (songData.diffFiles != null)
			for (chart in songData.diffFiles)
				if (validImportPath(chart) && readSongChart(chart) != null)
					chartCount++;
		if (chartCount == 0)
			return 'The song is missing a difficulty chart.';
		return null;
	}

	static function readSongChart(path:String):Dynamic {
		if (!validImportPath(path))
			return null;
		var content:String;
		try {
			content = File.getContent(path);
		} catch (error:Dynamic) {
			trace('Unable to read imported chart ' + path + ': ' + error);
			return null;
		}
		var parsed:Dynamic = null;
		try {
			parsed = CoolUtil.parseJson(content);
		} catch (error:Dynamic) {
			// Some legacy engines shipped otherwise valid JSON with an omitted
			// comma between two newline-separated object properties. Recover only
			// this unambiguous separator shape in memory; the donor remains read-only
			// and the destination is serialized as valid native JSON below.
			// Keep this recovery expression local so readSongChart remains a
			// self-contained import primitive for isolated scanners/tests.
			var repaired = new EReg(
				'(true|false|null|-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|"(?:\\\\.|[^"\\\\])*"|\\]|\\x7D)([ \\t]*\\r?\\n[ \\t]*"[^"\\r\\n]+"[ \\t]*:)',
				'g').replace(content, '$1,$2');
			if (repaired == content) {
				trace('Unable to parse imported chart ' + path + ': ' + error);
				return null;
			}
			try {
				parsed = CoolUtil.parseJson(repaired);
				trace('[import-chart-json-repaired] Added missing JSON property separator(s) in memory for ' + path + '.');
			} catch (repairError:Dynamic) {
				trace('Unable to parse imported chart ' + path + ' after conservative separator repair: ' + repairError);
				return null;
			}
		}
		try {
			var song:Dynamic = parsed == null ? null : Reflect.field(parsed, 'song');
			return song != null && Std.isOfType(Reflect.field(song, 'notes'), Array) ? parsed : null;
		} catch (error:Dynamic) {
			trace('Unable to inspect imported chart ' + path + ': ' + error);
			return null;
		}
	}

	/**
	 * Conservatively recover a missing comma before a newline-separated JSON
	 * object property. This is intentionally not a general "fix broken JSON"
	 * parser: it runs only after the normal tolerant parser rejects the document
	 * and never changes the source file.
	 */
	public static function repairImportedJsonSeparators(content:String):String {
		if (content == null || content == '')
			return content;
		var missingPropertyComma = new EReg(
			'(true|false|null|-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|"(?:\\\\.|[^"\\\\])*"|\\]|\\x7D)([ \\t]*\\r?\\n[ \\t]*"[^"\\r\\n]+"[ \\t]*:)',
			'g');
		return missingPropertyComma.replace(content, '$1,$2');
	}

	#if sys
	/** Map a source chart's filename to the destination engine's conventional
	 * chart name without changing its JSON.  Known slots retain the normal
	 * `<song>.json`/`<song>-<difficulty>.json` convention; an unknown suffix is
	 * preserved so custom difficulty registries and future loaders can consume
	 * it instead of silently dropping that chart. */
	static function importedChartFileName(targetFolder:String, chartPath:String, index:Int, ?sourceFolder:String):String {
		var stem = Path.withoutDirectory(Path.normalize(chartPath));
		for (extension in ['.jsonc', '.json'])
			if (stem.toLowerCase().endsWith(extension))
				stem = stem.substr(0, stem.length - extension.length);
		var lowerStem = stem.toLowerCase();
		var lowerFolder = targetFolder.toLowerCase();
		var sourceName = sourceFolder == null ? '' : StringTools.trim(sourceFolder).toLowerCase();
		if (sourceName.indexOf('/') >= 0 || sourceName.indexOf('\\') >= 0 || sourceName.indexOf('..') >= 0)
			sourceName = '';
		var suffix = '';
		if (lowerStem == lowerFolder || lowerStem == 'normal' || (sourceName != '' && lowerStem == sourceName)) {
			suffix = '';
		} else if (StringTools.startsWith(lowerStem, lowerFolder + '-')) {
			suffix = stem.substr(targetFolder.length + 1);
			if (sourceName == lowerFolder && suffix.toLowerCase() == 'normal') suffix = '';
		} else if (sourceName != '' && StringTools.startsWith(lowerStem, sourceName + '-')) {
			suffix = stem.substr(sourceName.length + 1);
			if (suffix.toLowerCase() == 'normal') suffix = '';
		} else {
			var known = false;
			for (difficulty in getImportDifficultyNames()) {
				if (lowerStem == difficulty.toLowerCase()) {
					suffix = difficulty.toLowerCase() == 'normal' ? '' : difficulty;
					known = true;
					break;
				}
			}
			// Generic chart/chart1 names have no difficulty encoded.  Use the
			// source order only as a last resort, matching the old importer.
			if (!known && (lowerStem == 'chart' || lowerStem == 'song')) {
				var names = getImportDifficultyNames();
				if (index >= 0 && index < names.length)
					suffix = names[index].toLowerCase() == 'normal' ? '' : names[index];
				else
					suffix = 'chart' + (index < 0 ? '' : Std.string(index));
			} else if (!known) {
				suffix = stem;
			}
		}
		// A basename cannot contain path traversal; strip the few separators
		// that can still arrive in malformed Windows metadata before writing.
		suffix = StringTools.trim(StringTools.replace(StringTools.replace(suffix, '/', '_'), '\\', '_'));
		return targetFolder + (suffix == '' ? '' : '-' + suffix.toLowerCase()) + '.json';
	}
	#end

	#if sys
	/** Resolve the on-disk freeplay registry once for every importer path.
	 * Older FNF/Kade packs and older destination builds use `.json`, while the
	 * current seed uses JSONC.  Reading only the JSONC spelling makes a clean
	 * legacy destination look empty and can leave the game with two competing
	 * registries after an import.  Prefer the current JSONC spelling when both
	 * exist, but preserve an existing legacy JSON file when it is the only
	 * registry. */
	static function freeplayRegistryPath():String {
		return FreeplayRegistry.getPath();
	}

	static function readFreeplayRegistry():Array<Dynamic> {
		try {
			var registryPath = freeplayRegistryPath();
			if (!FNFAssets.exists(registryPath))
				return [];
			var parsed:Dynamic = CoolUtil.parseJson(FNFAssets.getText(registryPath));
			return parsed != null && Std.isOfType(parsed, Array) ? cast parsed : [];
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function freeplayRegistryHasSong(songName:String, ?registry:Array<Dynamic>):Bool {
		if (songName == null || StringTools.trim(songName) == '')
			return false;
		var source = registry == null ? readFreeplayRegistry() : registry;
		if (source == null)
			return false;
		var wanted = StringTools.trim(songName).toLowerCase();
		for (category in source) {
			if (category == null || category.songs == null || !Std.isOfType(category.songs, Array))
				continue;
			for (entry in (cast category.songs:Array<Dynamic>))
				if (entry != null && entry.name != null
					&& StringTools.trim(Std.string(entry.name)).toLowerCase() == wanted)
					return true;
		}
		return false;
	}

	/** Folder existence alone is not a duplicate.  A failed import can leave
	 * chart/audio folders behind before freeplaySongJson is written; the scan
	 * must allow that song to be registered and repaired. */
	static public function songIsRegistered(songName:String):Bool {
		return freeplayRegistryHasSong(songName);
	}

	static public function songTargetExists(songName:String, ?sourceFolder:String):Bool {
		if (!validModuleName(songName))
			return true;
		var folderValue = sourceFolder == null || StringTools.trim(sourceFolder) == ''
			? StringTools.trim(songName) : StringTools.trim(sourceFolder);
		if (!validModuleName(folderValue))
			return true;
		var folder = folderValue.toLowerCase();
		var hasData = FileSystem.exists(existingImportChild(Path.join(['assets', 'data']), folder));
		var hasAudio = FileSystem.exists(existingImportChild(Path.join(['assets', 'songs']), folder));
		// The internal key is what Freeplay/DifficultyManager resolve.  Do not
		// accept a legacy display-name registry entry as a complete duplicate:
		// that is precisely the interrupted/old import shape this repair path must
		// migrate to the source folder id.
		return (hasData || hasAudio) && songIsRegistered(folder);
	}

	/** Return true when a destination song needs missing files or a freeplay
	 * registration.  Existing bytes are never compared or overwritten. */
	static public function songNeedsRepair(songData:SongImport):Bool {
		if (songData == null || !validModuleName(songData.name))
			return true;
		var targetFolder = importSongFolderName(songData);
		if (targetFolder == '' || !songIsRegistered(targetFolder))
			return true;
		var dataFolder = existingImportChild(Path.join(['assets', 'data']), targetFolder);
		var songFolder = existingImportChild(Path.join(['assets', 'songs']), targetFolder);
		if (!FileSystem.isDirectory(dataFolder) || !FileSystem.isDirectory(songFolder))
			return true;
		if (songData.engine == ImportEngine.NIGHTMARE_VISION
			&& songData.sourceSelectableDifficulties != null
			&& songData.sourceUnsupportedDifficulties != null) {
			var receipt = existingImportChild(dataFolder, 'importProvenance.json');
			var expectedOwner = CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
			if (NightmareVisionDifficultyCompat.needsProvenanceUpgrade(receipt, expectedOwner,
				targetFolder, songData.sourceSelectableDifficulties, songData.sourceUnsupportedDifficulties))
				return true;
		}
		if (validImportPath(songData.inst)
			&& !FileSystem.exists(Path.join([songFolder, 'Inst.ogg'])))
			return true;
		var repairVocalStems:Dynamic = Reflect.field(songData, 'vocalStems');
		var repairStemCount = repairVocalStems != null && Std.isOfType(repairVocalStems, Array)
			? (cast repairVocalStems:Array<Dynamic>).length : 0;
		var repairDirectVoiceSource = songData.voices != null
			&& Path.withoutDirectory(Path.normalize(songData.voices)).toLowerCase() == 'voices.ogg';
		if ((repairStemCount <= 1 || repairDirectVoiceSource) && validImportPath(songData.voices)
			&& !FileSystem.exists(existingImportChild(songFolder, 'Voices.ogg')))
			return true;
		if (repairStemCount > 0) {
			for (stem in (cast repairVocalStems:Array<Dynamic>)) {
				if (stem == null)
					continue;
				var destination = Std.string(Reflect.field(stem, 'destination'));
				if (StringTools.trim(destination) != '' && destination != 'null'
					&& !FileSystem.exists(existingImportChild(songFolder, destination)))
					return true;
			}
		}
		if (validImportPath(songData.dialog)
			&& !FileSystem.exists(existingImportChild(dataFolder, 'dialog.txt')))
			return true;
		var importedDialogueText:Dynamic = Reflect.field(songData, 'dialogueText');
		if (songData.dialog == null && importedDialogueText != null
			&& StringTools.trim(Std.string(importedDialogueText)) != ''
			&& !FileSystem.exists(existingImportChild(dataFolder, 'dialog.txt')))
			return true;
		var dialogueSidecar:Dynamic = Reflect.field(songData, 'dialogueJson');
		if (validImportPath(dialogueSidecar)
			&& !FileSystem.exists(existingImportChild(dataFolder, 'dialogue.json')))
			return true;
		var cutsceneSidecar:Dynamic = Reflect.field(songData, 'cutsceneJson');
		if (validImportPath(cutsceneSidecar)
			&& !FileSystem.exists(existingImportChild(dataFolder, 'cutscene.json')))
			return true;
		var eventsSidecar:Dynamic = Reflect.field(songData, 'events');
		if (validImportPath(eventsSidecar)
			&& !FileSystem.exists(existingImportChild(dataFolder, 'events.json')))
			return true;
		var hasSourceModchart = validImportPath(songData.modchart);
		var hasGeneratedModchart = songData.generatedModchart != null
			&& StringTools.trim(songData.generatedModchart) != '';
		if ((hasSourceModchart || hasGeneratedModchart)
			&& !FileSystem.exists(existingImportChild(dataFolder, 'modchart.hscript')))
			return true;
		if (songData.convertedCharts != null && songData.convertedCharts.length > 0) {
			for (converted in songData.convertedCharts) {
				if (converted == null || converted.chart == null || Reflect.field(converted.chart, 'song') == null)
					continue;
				var template = VSliceImporter.nativeFileName('chart', converted.difficulty);
					var fileName = targetFolder + template.substr('chart'.length);
					var existingChartPath = existingImportChild(dataFolder, fileName);
					if (!FileSystem.exists(existingChartPath))
						return true;
					var expectedStems:Dynamic = Reflect.field(songData, 'vocalStems');
					if (expectedStems != null && Std.isOfType(expectedStems, Array)
						&& (cast expectedStems:Array<Dynamic>).length > 0) {
						var existingChart = readSongChart(existingChartPath);
						var existingStems:Dynamic = existingChart == null || existingChart.song == null
							? null : Reflect.field(existingChart.song, 'vocalStems');
						if (!vocalStemMetadataMatches(expectedStems, existingStems))
							return true;
					}
				}
		} else if (songData.diffFiles != null) {
			for (index in 0...songData.diffFiles.length) {
				var chartPath = songData.diffFiles[index];
				if (!validImportPath(chartPath) || readSongChart(chartPath) == null)
					continue;
				var fileName = importedChartFileName(targetFolder, chartPath, index, Reflect.field(songData, 'sourceFolder'));
				var existingChartPath = existingImportChild(dataFolder, fileName);
				if (!FileSystem.exists(existingChartPath))
					return true;
				var expectedStems:Dynamic = Reflect.field(songData, 'vocalStems');
				if (expectedStems != null && Std.isOfType(expectedStems, Array)
					&& (cast expectedStems:Array<Dynamic>).length > 0) {
					var existingChart = readSongChart(existingChartPath);
					var existingStems:Dynamic = existingChart == null || existingChart.song == null
						? null : Reflect.field(existingChart.song, 'vocalStems');
					if (!vocalStemMetadataMatches(expectedStems, existingStems))
						return true;
				}
			}
		}
		if (songData.noteDefinitions != null && songData.noteDefinitions.length > 0
			&& !FileSystem.exists(existingImportChild(dataFolder, 'noteInfo.json')))
			return true;
		// A previous importer version could leave a complete chart/audio folder
		// while flattening foreign global scripts into assets/scripts.  Once the
		// donor is rediscovered, require the destination-only provenance manifest
		// so the isolated script tree can be materialized and selected at runtime.
		var compatSourceRoot:Dynamic = Reflect.field(songData, 'sourceRoot');
		if (compatSourceRoot != null && StringTools.trim(Std.string(compatSourceRoot)) != '') {
			// The destination-only compatScripts.json provenance file must name a
			// complete selected namespace before an import is considered repaired.
			var manifestPath = existingImportChild(dataFolder, CompatScriptManifest.FILE_NAME);
			if (!FileSystem.exists(manifestPath))
				return true;
			// A manifest written after an interrupted copy is not enough: validate
			// that its selected namespace still exists and contains executable files.
			if (compatScriptManifestNeedsRepair(songData))
				return true;
		}
		return false;
	}

	static function findNamedDirectory(parent:String, wantedName:String):String {
		if (parent == null || !FileSystem.isDirectory(parent))
			return null;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(parent));
		} catch (error:Dynamic) {
			return null;
		}
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		var wanted = StringTools.trim(wantedName).toLowerCase();
		for (entry in entries) {
			var candidate = Path.join([parent, entry]);
			if (entry.toLowerCase() == wanted && FileSystem.isDirectory(candidate))
				return candidate;
		}
		return null;
	}

	/** Find an existing child without relying on Linux case sensitivity. */
	static function existingImportChild(parent:String, name:String):String {
		var exact = Path.join([parent, name]);
		if (FileSystem.exists(exact))
			return exact;
		if (parent == null || !FileSystem.isDirectory(parent))
			return exact;
		try {
			var entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(parent));
			entries.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				if (entry.toLowerCase() == name.toLowerCase())
					return Path.join([parent, entry]);
			}
		} catch (error:Dynamic) {
			// Use the exact path below; the copy operation will report an error.
		}
		return exact;
	}

	/** Top-level trees whose contents can execute through a foreign engine
	 * compatibility adapter.  They are deliberately kept out of the ordinary
	 * asset merge; media and native registries continue to use their shared
	 * destination paths. */
	static function compatScriptTreeNames():Array<String> {
		return ['scripts', 'stages', 'custom_events', 'custom_notetypes', 'plugins'];
	}

	/** Read only the validated provenance of selected converted chart rows.
	 * Routed native names are not the authored Codename event identities. */
	static function codenameAuthoredEventNames(songData:SongImport):Array<String> {
		var names:Array<String> = [];
		if (songData == null || songData.convertedCharts == null) return names;
		for (chart in songData.convertedCharts) {
			if (chart == null || chart.chart == null || Reflect.field(chart.chart, 'song') == null) continue;
			var groups:Dynamic = Reflect.field(chart.chart.song, 'events');
			if (!Std.isOfType(groups, Array)) continue;
			for (group in (cast groups:Array<Dynamic>)) {
				if (!Std.isOfType(group, Array) || group.length < 2 || !Std.isOfType(group[1], Array)) continue;
				var time:Float = group[0];
				for (row in (cast group[1]:Array<Dynamic>)) {
					if (!Std.isOfType(row, Array)) continue;
					var authored = CodenameEventMetadata.read(cast row, time);
					if (authored == null) continue;
					var name:String = Reflect.field(authored, 'name');
					if (CodenameScriptDiscovery.safeName(name) && names.indexOf(name) < 0)
						names.push(name);
				}
			}
		}
		return names;
	}

	static function codenameScriptFiles(songData:SongImport):Array<CodenameScriptFile> {
		if (songData == null || songData.engine != ImportEngine.CODENAME)
			return [];
		var root = songData.vSliceRoot;
		var song:String = Reflect.field(songData, 'sourceFolder');
		var stage:String = Reflect.field(songData, 'codenameStageSource');
		var authoredStages:Dynamic = Reflect.field(songData, 'codenameAuthoredStages');
		var difficulties:Array<String> = [];
		var authoredNoteTypes:Array<Dynamic> = [];
		if (songData.convertedCharts != null)
			for (chart in songData.convertedCharts) {
				if (chart != null && chart.difficulty != null && difficulties.indexOf(chart.difficulty) < 0)
					difficulties.push(chart.difficulty);
				if (chart == null) continue;
				var chartNoteTypes:Dynamic = chart.noteTypes;
				if (!Std.isOfType(chartNoteTypes, Array) && chart.chart != null
					&& Reflect.field(chart.chart, 'song') != null)
					chartNoteTypes = Reflect.field(chart.chart.song, 'codenameNoteTypes');
				if (Std.isOfType(chartNoteTypes, Array))
					for (kind in (cast chartNoteTypes:Array<Dynamic>)) authoredNoteTypes.push(kind);
			}
		var files = CodenameScriptDiscovery.discover(root, song, difficulties, stage);
		var noteTypeDiscovery = CodenameScriptDiscovery.discoverNoteTypesDetailed(root, authoredNoteTypes);
		for (diagnostic in noteTypeDiscovery.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			var message = '[codename-note-type-script] ' + diagnostic;
			if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
		}
		var stagedNoteTypes:Map<String, Bool> = new Map();
		for (file in noteTypeDiscovery.files) {
			if (file.authoredId != null) stagedNoteTypes.set(file.authoredId.toLowerCase(), true);
			var already = false;
			for (existing in files)
				if (existing.relative.toLowerCase() == file.relative.toLowerCase()) { already = true; break; }
			if (!already) files.push(file);
		}
		// The generic identity warning remains for missing note scripts. If a
		// selected type has an owner script, that script is staged and will provide
		// its source behavior through the Codename callback runtime.
		if (songData.diagnostics != null && stagedNoteTypes.iterator().hasNext()) {
			var retainedDiagnostics:Array<String> = [];
			for (message in songData.diagnostics) {
				var prefix = '[note-kind-generic] Codename note kind ';
				var marker = ' was preserved as a native custom note identity';
				var start = message == null ? -1 : message.indexOf(prefix);
				var end = start < 0 ? -1 : message.indexOf(marker, start + prefix.length);
				if (end > start) {
					var kind = StringTools.trim(message.substring(start + prefix.length, end)).toLowerCase();
					if (stagedNoteTypes.exists(kind)) continue;
				}
				retainedDiagnostics.push(message);
			}
			songData.diagnostics = retainedDiagnostics;
		}
		var ownerScripts = CodenameScriptDiscovery.discoverOwnerScriptsDetailed(root, song);
		for (diagnostic in ownerScripts.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			if (songData.diagnostics.indexOf(diagnostic) < 0)
				songData.diagnostics.push(diagnostic);
		}
		for (file in ownerScripts.files) {
			var already = false;
			for (existing in files)
				if (existing.relative.toLowerCase() == file.relative.toLowerCase()) {
					already = true;
					break;
			}
			if (!already) files.push(file);
		}
		// Compiled Codename installations keep shared modules under assets/, next
		// to mods/<owner>.  They are part of the installation's script layer, not
		// another mod: materialize only global.hx and data/scripts, with the
		// selected owner winning any same-path override.  State scripts remain
		// owner-local and cannot become accidental launch targets.
		// Derive this from the selected mods/<name> structure, not from donor
		// metadata or an arbitrary path stored on the import payload.
		var installationAssetRoot = CodenameInstallationAssetOverlay.installationAssetsForOwner(root);
		if (root != null && CodenameInstallationAssetOverlay.isInstallationAssetsRoot(installationAssetRoot)
			&& Path.normalize(installationAssetRoot) != Path.normalize(root)) {
			var sharedScripts = CodenameScriptDiscovery.discoverInstallationScriptsDetailed(installationAssetRoot);
			for (diagnostic in sharedScripts.diagnostics) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-install-script] ' + diagnostic;
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
			}
			for (file in sharedScripts.files) {
				var already = false;
				for (existing in files)
					if (existing.relative.toLowerCase() == file.relative.toLowerCase()) {
						already = true;
						break;
					}
				if (!already) files.push(file);
			}
		}
		if (authoredStages != null)
			for (difficulty in difficulties) {
				var authored:Dynamic = Reflect.field(authoredStages, difficulty);
				if (!Std.isOfType(authored, String) || !CodenameScriptDiscovery.safeName(cast authored)
					|| authored == stage) continue;
				for (file in CodenameScriptDiscovery.discover(root, null, null, cast authored)) {
					var already = false;
					for (existing in files)
						if (existing.relative == file.relative) { already = true; break; }
					if (!already) files.push(file);
				}
			}
		var authoredEvents = codenameAuthoredEventNames(songData);
		var eventDiscovery = CodenameScriptDiscovery.discoverEventsDetailed(root, authoredEvents);
		for (diagnostic in eventDiscovery.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			var message = '[codename-event-source] ' + diagnostic;
			if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
		}
		for (file in eventDiscovery.files) files.push(file);
		for (file in CodenameScriptDiscovery.discoverEventSchemas(root, authoredEvents)) files.push(file);
		var characterIds:Array<String> = [];
		var ownerCharacters = CodenameScriptDiscovery.discoverOwnerCharacterIds(root);
		for (diagnostic in ownerCharacters.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			var message = '[codename-character-source] ' + diagnostic;
			if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
		}
		for (id in ownerCharacters.ids) characterIds.push(id);
		var camera:Dynamic = Reflect.field(songData, 'codenameAuthoredCamera');
		if (camera != null) for (difficulty in Reflect.fields(camera)) {
			var entry:Dynamic = Reflect.field(camera, difficulty);
			var lines:Dynamic = entry == null ? null : Reflect.field(entry, 'lines');
			if (!Std.isOfType(lines, Array)) continue;
			for (line in (cast lines:Array<Dynamic>)) {
				var ids:Dynamic = line == null ? null : Reflect.field(line, 'characters');
				if (!Std.isOfType(ids, Array)) continue;
				for (id in (cast ids:Array<Dynamic>))
					if (Std.isOfType(id, String) && characterIds.indexOf(cast id) < 0)
						characterIds.push(cast id);
			}
		}
		var characters = CodenameScriptDiscovery.discoverCharactersDetailed(root, characterIds);
		for (diagnostic in characters.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			var message = '[codename-character-source] ' + diagnostic;
			if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
		}
		for (file in characters.files) files.push(file);
		// Codename transition scripts are selected by a source assignment rather
		// than by the chart registry. Follow bounded literal paths so their own
		// dynamic asset dependencies enter the same owner-scoped copy plan.
		var transitionAssignment = new EReg('MusicBeatTransition\\s*\\.\\s*script\\s*=\\s*["\\\']([^"\\\']*)["\\\']', 'g');
		var scriptIndex = 0;
		while (scriptIndex < files.length && scriptIndex < 128) {
			var current = files[scriptIndex++];
			if (current.family == 'event-schema' || current.family == 'character-xml'
				|| current.path == null || !FileSystem.exists(current.path)
				|| FileSystem.isDirectory(current.path)) continue;
			var scriptSource = '';
			try scriptSource = File.getContent(current.path) catch (_:Dynamic) continue;
			var remaining = scriptSource;
			var attempts = 0;
			while (attempts++ < 64 && transitionAssignment.match(remaining)) {
				var key = StringTools.trim(transitionAssignment.matched(1));
				if (key != '') {
					if (!key.toLowerCase().endsWith('.hx')) key += '.hx';
					if (!CodenameScriptDiscovery.safeRelativeName(key)) {
						var message = '[codename-transition-source] ' + current.relative + ': unsafe script ' + key;
						if (songData.diagnostics == null) songData.diagnostics = [];
						if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
					} else {
						var resolved = CodenameInstallationAssetOverlay.resolve(root, installationAssetRoot, key);
						if (resolved.source == null) {
							var message = '[codename-transition-source] ' + current.relative + ': ' + key + ' ' + resolved.status;
							if (songData.diagnostics == null) songData.diagnostics = [];
							if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
						} else {
							var present = false;
							for (existing in files) if (existing.relative.toLowerCase() == resolved.relative.toLowerCase()) {
								present = true;
								existing.family = 'transition';
								break;
							}
							if (!present) files.push({path:resolved.source,
								relative:resolved.relative, family:'transition'});
						}
					}
				}
				var position = transitionAssignment.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
			if (transitionAssignment.match(remaining)) {
				var message = '[codename-transition-source] ' + current.relative + ': too many script selections';
				if (songData.diagnostics == null) songData.diagnostics = [];
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
			}
		}
		if (scriptIndex < files.length) {
			var message = '[codename-transition-source] script dependency scan exceeds 128 files';
			if (songData.diagnostics == null) songData.diagnostics = [];
			if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
		}
		// The Codename base transition file is always loaded in transition-host
		// context, even when no package explicitly assigns it.
		for (file in files)
			if (Path.withoutDirectory(file.relative).toLowerCase() == 'musicbeattransition.hx')
				file.family = 'transition';
		var classPlan = CodenameClassScriptPlan.build(root, files);
		for (diagnostic in classPlan.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
		}
		return files;
	}

	static function codenameSafeAssetKey(value:String):Bool {
		if (value == null || value == '') return false;
		var clean = StringTools.replace(value, '\\', '/');
		if (clean.startsWith('/') || clean.indexOf(':') >= 0) return false;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..') return false;
		return true;
	}

	/** Exact source-relative files promised by the Codename namespace copy and
	 * checked again on same-owner repair. Literal media keys and bounded folder
	 * enumerations are followed within the selected owner. */
	static function codenameRuntimeFiles(songData:SongImport):Array<{source:String, relative:String, ?content:String, ?family:String}> {
		var files:Array<{source:String, relative:String, ?content:String, ?family:String}> = [];
		if (songData == null || songData.engine != ImportEngine.CODENAME || songData.vSliceRoot == null)
			return files;
		var sourceRoot = songData.vSliceRoot;
		// The source owner path is authoritative. A claimed base root is never
		// allowed to widen the import beyond its actual installation sibling.
		var installationAssetRoot = CodenameInstallationAssetOverlay.installationAssetsForOwner(sourceRoot);
		var appendSoundAsset = function(key:String, reportMissing:Bool):Void {
			var resolved = CodenameInstallationSoundAssets.resolve(sourceRoot, key,
				installationAssetRoot);
			if (resolved.source == null) {
				if (reportMissing) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-audio] ' + resolved.relative + ' ' + resolved.status;
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				}
				return;
			}
			for (existing in files)
				if (existing.relative.toLowerCase() == resolved.relative.toLowerCase()) return;
			files.push({source:resolved.source, relative:resolved.relative});
		};
		var appendExactAsset = function(relative:String, reportMissing:Bool):Void {
			if (!codenameSafeAssetKey(relative)) return;
			if (relative.toLowerCase().startsWith('sounds/')) {
				var soundKey = relative.substr('sounds/'.length);
				var suffix = Path.extension(soundKey).toLowerCase();
				if (['ogg', 'wav', 'mp3'].indexOf(suffix) >= 0) {
					appendSoundAsset(soundKey, reportMissing);
					return;
				}
			}
			var resolved = CodenameInstallationAssetOverlay.resolve(sourceRoot,
				installationAssetRoot, relative);
			if (resolved.source == null) {
				if (reportMissing) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-asset] ' + relative + ' ' + resolved.status;
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				}
				return;
			}
			for (existing in files)
				if (existing.relative == relative) return;
			files.push({source:resolved.source, relative:relative});
		};
		var appendResolvedAsset = function(source:String, relative:String):Void {
			if (!codenameSafeAssetKey(relative)
				|| !CodenameInstallationAssetOverlay.ownsSource(sourceRoot,
					installationAssetRoot, source)) return;
			for (existing in files)
				if (existing.relative == relative) return;
			files.push({source:source, relative:relative});
		};
		var appendNamedAsset = function(folder:String, key:String, extension:String):Void {
			if (key == null || StringTools.trim(key) == '') return;
			var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
			var relative = folder + '/' + clean
				+ (clean.toLowerCase().endsWith(extension) ? '' : extension);
			appendExactAsset(relative, true);
			if (folder == 'models' && extension == '.obj') {
				// A Codename OBJ may load owner-local MTL libraries and diffuse maps
				// through Away3D without another Paths call. Keep that dependency
				// closure in the same selected owner namespace as the model.
				var objRelative = relative;
				for (dependency in CodenameObjAssetDependencies.filesFor(sourceRoot, objRelative))
					appendResolvedAsset(dependency.source, dependency.relative);
			}
		};
		// Codename's shared OptionsMenu reads package-authored XML outside the
		// per-song script closure. Materialize only its known selected-owner paths.
		var optionPlan = CodenameOptionsXmlDependencies.filesFor(sourceRoot);
		for (diagnostic in optionPlan.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
		}
		for (dependency in optionPlan.files)
			appendResolvedAsset(dependency.source, dependency.relative);
		// Codename's note splash handler resolves package splash XML separately
		// from gameplay script references. Stage each selected-owner definition
		// with only its declared Sparrow atlas closure.
		var splashPlan = CodenameSplashDependencies.filesFor(sourceRoot);
		for (diagnostic in splashPlan.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
		}
		for (dependency in splashPlan.files)
			appendResolvedAsset(dependency.source, dependency.relative);
		var appendMenuMusic = function(key:String, relative:String):Void {
			if (!codenameSafeAssetKey(key)) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var invalid = '[codename-runtime-asset] unsafe CoolUtil.playMenuSong key in ' + relative;
				if (songData.diagnostics.indexOf(invalid) < 0) songData.diagnostics.push(invalid);
				return;
			}
			var clean = StringTools.replace(key, '\\', '/');
			var extensions = ['.ogg', '.wav', '.mp3'];
			for (extension in extensions)
				if (clean.toLowerCase().endsWith(extension)) {
					extensions = [extension];
					clean = clean.substr(0, clean.length - extension.length);
					break;
			}
			for (extension in extensions) {
				var sourceRelative = 'music/' + clean + extension;
				var resolved = CodenameInstallationAssetOverlay.resolve(sourceRoot,
					installationAssetRoot, sourceRelative);
				if (resolved.source == null) continue;
				appendExactAsset(sourceRelative, false);
				return;
			}
			if (songData.diagnostics == null) songData.diagnostics = [];
			var missing = '[codename-runtime-asset] CoolUtil.playMenuSong music/' + clean
				+ ' has no supported audio file';
			if (songData.diagnostics.indexOf(missing) < 0) songData.diagnostics.push(missing);
		};
		var collectMenuMusic = function(source:String, relative:String):Void {
			// Codename's shared menu helper defaults an omitted or empty argument to
			// freakyMenu. Stage that exact dependency in the selected owner namespace;
			// runtime lookup remains owner-scoped through CodenamePaths.music().
			var defaults = new EReg('CoolUtil\\s*\\.\\s*playMenuSong\\s*\\(\\s*\\)', 'g');
			var remaining = source;
			var attempts = 0;
			while (attempts++ < 1024 && defaults.match(remaining)) {
				appendMenuMusic('freakyMenu', relative);
				var position = defaults.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
			var named = new EReg('CoolUtil\\s*\\.\\s*playMenuSong\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']\\s*\\)', 'g');
			remaining = source;
			attempts = 0;
			while (attempts++ < 1024 && named.match(remaining)) {
				appendMenuMusic(named.matched(1), relative);
				var position = named.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
		};
		var collectMenuSfx = function(source:String):Void {
			// CoolUtil.playMenuSFX accepts a runtime ID, including an omitted ID
			// for scroll. Its six shared keys are a small bounded dependency set.
			// Stage only sounds present in this selected owner/installation.
			var call = new EReg('CoolUtil\\s*\\.\\s*playMenuSFX\\s*\\(', '');
			if (!call.match(source)) return;
			for (key in ['menu/scroll', 'menu/confirm', 'menu/cancel',
				'editors/checkboxChecked', 'editors/checkboxUnchecked', 'editors/warningMenu'])
				appendSoundAsset(key, false);
		};
		var collectNamedAssets = function(source:String, pattern:String, folder:String, extension:String):Void {
			var remaining = source;
			var expression = new EReg(pattern, 'g');
			var attempts = 0;
			while (attempts++ < 1024 && expression.match(remaining)) {
				var key = expression.matched(1);
				appendNamedAsset(folder, key, extension);
				var position = expression.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
		};
		var collectListedFolderAssets = function(scriptSource:String, scriptRelative:String):Void {
			// A literal folder enumeration can feed a later dynamic Paths call.
			// Materialize the named folder and, for getFolderDirectories, files
			// directly inside its selected child folders. Keep this bounded and
			// owner-scoped instead of scanning an arbitrary media tree.
			var pattern = new EReg('Paths\\s*\\.\\s*getFolder(Directories|Content)\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'g');
			var remaining = scriptSource;
			var attempts = 0;
			while (attempts++ < 128 && pattern.match(remaining)) {
				var kind = pattern.matched(1);
				var key = StringTools.replace(StringTools.trim(pattern.matched(2)), '\\', '/');
				while (key.endsWith('/')) key = key.substr(0, key.length - 1);
				var prefix = '[codename-runtime-folder] ' + scriptRelative + ': ';
				if (!codenameSafeAssetKey(key)) {
					var diagnostic = prefix + 'unsafe folder key ' + key;
					if (songData.diagnostics == null) songData.diagnostics = [];
					if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
				} else {
					var folder = Path.join([sourceRoot, key]);
					if (!FileSystem.exists(folder) || !FileSystem.isDirectory(folder)
						|| !CodenameScriptDiscovery.withinRoot(sourceRoot, folder)) {
						var diagnostic = prefix + 'missing or unowned folder ' + key;
						if (songData.diagnostics == null) songData.diagnostics = [];
						if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
					} else {
						var selected:Array<String> = [];
						var entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(folder));
						entries.sort(Reflect.compare);
						if (entries.length > 256) {
							var diagnostic = prefix + 'folder exceeds 256 entry scan limit: ' + key;
							if (songData.diagnostics == null) songData.diagnostics = [];
							if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
						} else {
							for (entry in entries) {
								if (!CodenameScriptDiscovery.safeName(entry)) continue;
								var child = Path.join([folder, entry]);
								if (!CodenameScriptDiscovery.withinRoot(sourceRoot, child)) continue;
								if (!FileSystem.isDirectory(child)) selected.push(key + '/' + entry);
								else if (kind == 'Directories') {
									var descendants = ImportDirectoryListing.normalize(FileSystem.readDirectory(child));
									descendants.sort(Reflect.compare);
									if (descendants.length > 256) {
										var diagnostic = prefix + 'child folder exceeds 256 entry scan limit: ' + key + '/' + entry;
										if (songData.diagnostics == null) songData.diagnostics = [];
										if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
										selected = [];
										break;
									}
									for (item in descendants) {
										if (!CodenameScriptDiscovery.safeName(item)) continue;
										var candidate = Path.join([child, item]);
										if (CodenameScriptDiscovery.withinRoot(sourceRoot, candidate)
											&& !FileSystem.isDirectory(candidate)) selected.push(key + '/' + entry + '/' + item);
										else if (CodenameScriptDiscovery.withinRoot(sourceRoot, candidate)) {
											var diagnostic = prefix + 'nested folder needs explicit asset plan: '
												+ key + '/' + entry + '/' + item;
											if (songData.diagnostics == null) songData.diagnostics = [];
											if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
										}
									}
								}
							}
							if (selected.length > 256) {
							var diagnostic = prefix + 'folder dependencies exceed 256 files: ' + key;
							if (songData.diagnostics == null) songData.diagnostics = [];
							if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
							} else for (relative in selected) appendExactAsset(relative, false);
						}
					}
				}
				var position = pattern.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
			if (pattern.match(remaining)) {
				var diagnostic = '[codename-runtime-folder] ' + scriptRelative + ': too many folder calls';
				if (songData.diagnostics == null) songData.diagnostics = [];
				if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
			}
		};
		var collectDynamicImageFolders = function(scriptSource:String, scriptRelative:String):Void {
			// Paths.image('hud/damage/' + i) and similar expressions choose a
			// filename at runtime, so literal-reference collection cannot see the
			// individual PNGs. Enumerate only the direct PNG children of the literal
			// folder named by that expression, within this selected owner.
			var pattern = new EReg('Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\']([^"\\\']+/)["\\\']\\s*\\+\\s*[A-Za-z_][A-Za-z0-9_]*(?:\\s*\\.\\s*[A-Za-z_][A-Za-z0-9_]*)*', 'g');
			var remaining = scriptSource;
			var attempts = 0;
			while (attempts++ < 128 && pattern.match(remaining)) {
				var key = StringTools.replace(StringTools.trim(pattern.matched(1)), '\\', '/');
				while (key.endsWith('/')) key = key.substr(0, key.length - 1);
				var prefix = '[codename-runtime-dynamic-image] ' + scriptRelative + ': ';
				if (!codenameSafeAssetKey(key)) {
					var diagnostic = prefix + 'unsafe image folder ' + key;
					if (songData.diagnostics == null) songData.diagnostics = [];
					if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
				} else {
					var relativeFolder = 'images/' + key;
					var folder = Path.join([sourceRoot, relativeFolder]);
					if (!FileSystem.exists(folder) || !FileSystem.isDirectory(folder)
						|| !CodenameScriptDiscovery.withinRoot(sourceRoot, folder)) {
						var diagnostic = prefix + 'missing or unowned image folder ' + relativeFolder;
						if (songData.diagnostics == null) songData.diagnostics = [];
						if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
					} else {
						var entries:Array<String> = [];
						try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(folder)) catch (_:Dynamic) {}
						entries.sort(Reflect.compare);
						if (entries.length > 128) {
							var diagnostic = prefix + 'image folder exceeds 128 entry scan limit: ' + relativeFolder;
						if (songData.diagnostics == null) songData.diagnostics = [];
						if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
						} else for (entry in entries) {
							if (!CodenameScriptDiscovery.safeName(entry)
								|| Path.extension(entry).toLowerCase() != 'png') continue;
						var relative = relativeFolder + '/' + entry;
						appendExactAsset(relative, true);
						}
					}
				}
				var position = pattern.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
			if (pattern.match(remaining)) {
				var diagnostic = '[codename-runtime-dynamic-image] ' + scriptRelative
					+ ': too many dynamic image folders';
				if (songData.diagnostics == null) songData.diagnostics = [];
				if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
			}
		};
		var shaderQueue:Array<{relative:String, source:String, ancestry:Array<String>, depth:Int}> = [];
		var shaderKeyError = function(message:String):Void {
			if (songData.diagnostics == null) songData.diagnostics = [];
			var diagnostic = '[codename-runtime-shader] ' + message;
			if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
		};
		var queueShaderAsset = function(key:String, ancestry:Array<String>, depth:Int):Void {
			if (key == null || StringTools.trim(key) == '') return;
			var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
			if (Path.extension(clean) == '') clean += '.frag';
			if (!codenameSafeAssetKey(clean)) {
				shaderKeyError('unsafe import key ' + key);
				return;
			}
			var relative = 'shaders/' + clean;
			var resolved = CodenameInstallationAssetOverlay.resolve(sourceRoot,
				installationAssetRoot, relative);
			if (resolved.source == null) {
				appendExactAsset(relative, true);
				return;
			}
			appendExactAsset(relative, false);
			// Codename shaders may import a donor-specific vertex shader alongside
			// the fragment shader. Stage it only when the same selected owner has
			// that exact sibling; scripts with fragment-only shaders keep working.
			if (clean.toLowerCase().endsWith('.frag')) {
				var vertexRelative = 'shaders/' + clean.substr(0, clean.length - 5) + '.vert';
				var vertex = CodenameInstallationAssetOverlay.resolve(sourceRoot,
					installationAssetRoot, vertexRelative);
				if (vertex.source != null)
					appendExactAsset(vertexRelative, false);
			}
			shaderQueue.push({relative:relative, source:resolved.source,
				ancestry:ancestry.copy(), depth:depth});
		};
		var collectShaderAssets = function(source:String):Void {
			var remaining = source;
			var expression = new EReg('(?:new\\s+)?CustomShader\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'g');
			var attempts = 0;
			while (attempts++ < 1024 && expression.match(remaining)) {
				queueShaderAsset(expression.matched(1), [], 0);
				var position = expression.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
		};
		var collectDirectIconAssets = function(source:String):Void {
			// Source scripts can select an icon id directly without constructing
			// its character. Stage that selected owner's original Codename icon
			// path; the runtime resolves the same path without a global alias.
			var expression = new EReg('\\.\\s*setIcon\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'g');
			var remaining = source;
			var attempts = 0;
			while (attempts++ < 1024 && expression.match(remaining)) {
				var id = expression.matched(1);
				if (CodenameScriptDiscovery.safeName(id)) {
					for (relative in [
						'images/icons/' + id + '/icon.png',
						'images/icons/icon-' + id + '.png',
						'images/icons/' + id + '.png'
					]) {
						var resolved = CodenameInstallationAssetOverlay.resolve(sourceRoot,
							installationAssetRoot, relative);
						if (resolved.source == null) continue;
						appendExactAsset(relative, false);
						break;
					}
				}
				var position = expression.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= remaining.length) break;
				remaining = remaining.substr(position.pos + position.len);
			}
		};
		var appendNoteStrumSpriteAsset = function(key:String, scriptRelative:String):Void {
			if (key == null || StringTools.trim(key) == '') return;
			var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
			if (StringTools.startsWith(clean.toLowerCase(), 'images/'))
				clean = clean.substr('images/'.length);
			if (!codenameSafeAssetKey(clean)) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-runtime-note-sprite] ' + scriptRelative + ': unsafe image key ' + key;
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				return;
			}
			var extension = Path.extension(clean).toLowerCase();
			if (extension == '') clean += '.png';
			else if (extension != 'png') {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-runtime-note-sprite] ' + scriptRelative
					+ ': unsupported literal image extension in ' + key;
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				return;
			}
			var relative = 'images/' + clean;
			appendExactAsset(relative, true);
			var xmlRelative = 'images/' + Path.withoutExtension(clean) + '.xml';
			if (CodenameInstallationAssetOverlay.resolve(sourceRoot,
				installationAssetRoot, xmlRelative).source != null)
				appendExactAsset(xmlRelative, false);
		};
		var appendDefaultNoteAtlasFolder = function(folder:String, assetRoot:String):Void {
			if (folder == null || assetRoot == null || !FileSystem.isDirectory(folder)
				|| !CodenameScriptDiscovery.withinRoot(assetRoot, folder)) return;
			var rootKey = importPathKey(assetRoot);
			if (rootKey == '') return;
			var pending:Array<String> = [folder];
			var visited:Map<String, Bool> = new Map();
			while (pending.length > 0) {
				if (importWorkCancelled()) return;
				var current = pending.pop();
				if (!FileSystem.isDirectory(current)
					|| !CodenameScriptDiscovery.withinRoot(assetRoot, current)) continue;
				var currentKey = importPathKey(current);
				if (currentKey == '' || visited.exists(currentKey)) continue;
				visited.set(currentKey, true);
				var entries:Array<String> = [];
				try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(current)) catch (_:Dynamic) continue;
				entries.sort(Reflect.compare);
				for (entry in entries) {
					var path = Path.join([current, entry]);
					if (!CodenameScriptDiscovery.withinRoot(assetRoot, path)) continue;
					if (FileSystem.isDirectory(path)) {
						pending.push(path);
						continue;
					}
					if (!FileSystem.exists(path)) continue;
					var pathKey = importPathKey(path);
					var prefix = StringTools.endsWith(rootKey, '/') ? rootKey : rootKey + '/';
					if (!StringTools.startsWith(pathKey, prefix)) continue;
					var relative = pathKey.substr(prefix.length);
					var already = false;
					for (existing in files)
						if (existing.relative.toLowerCase() == relative.toLowerCase()) {
							already = true;
							break;
						}
					if (!already) appendResolvedAsset(path, relative);
				}
			}
		};
		var appendDefaultNoteAtlasAssets = function():Void {
			var folder = 'images/game/notes/default';
			var animationManifest = folder + '/Animation.json';
			var ownerAnimation = CodenameScriptDiscovery.scopedResolution(sourceRoot, animationManifest);
			var ownerImage = CodenameScriptDiscovery.scopedResolution(sourceRoot, folder + '.png');
			var animationSource:String = null;
			var animationRoot:String = null;
			if (ownerAnimation.relative != null) {
				animationSource = Path.join([sourceRoot, ownerAnimation.relative]);
				animationRoot = sourceRoot;
			} else if (ownerImage.relative == null) {
				var installedAnimation = CodenameInstallationAssetOverlay.resolve(sourceRoot,
					installationAssetRoot, animationManifest);
				if (installedAnimation.source != null) {
					animationSource = installedAnimation.source;
					animationRoot = installedAnimation.origin == 'installation'
						? installationAssetRoot : sourceRoot;
				}
			}
			if (animationSource != null) {
				// Animate reads its manifest and texture pages from the sibling folder;
				// those files are the atlas source even when default.png/XML is absent.
				appendDefaultNoteAtlasFolder(Path.directory(animationSource), animationRoot);
				return;
			}
			var page = 1;
		var firstPagePng = 'images/' + folder + '/1.png';
		var firstPageXml = 'images/' + folder + '/1.xml';
		var hasPages = CodenameInstallationAssetOverlay.resolve(sourceRoot,
			installationAssetRoot, firstPagePng).source != null
			|| CodenameInstallationAssetOverlay.resolve(sourceRoot,
				installationAssetRoot, firstPageXml).source != null;
		if (hasPages) {
			while (true) {
				var pagePng = 'images/' + folder + '/' + page + '.png';
				var pageXml = 'images/' + folder + '/' + page + '.xml';
				var hasPng = CodenameInstallationAssetOverlay.resolve(sourceRoot,
					installationAssetRoot, pagePng).source != null;
				var hasXml = CodenameInstallationAssetOverlay.resolve(sourceRoot,
					installationAssetRoot, pageXml).source != null;
				if (!hasPng && !hasXml) break;
				if (hasPng) appendExactAsset(pagePng, false);
				if (hasXml) appendExactAsset(pageXml, false);
				if (hasPng != hasXml) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-note-atlas] incomplete default page ' + page;
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				}
				page++;
			}
			return;
		}
			appendNoteStrumSpriteAsset('game/notes/default', 'Codename default note/receptor atlas');
			var packer = 'images/' + folder + '.txt';
			if (CodenameInstallationAssetOverlay.resolve(sourceRoot,
				installationAssetRoot, packer).source != null)
				appendExactAsset(packer, false);
		};
		var collectNoteStrumCreationAssets = function(source:String, scriptRelative:String):Void {
			// Codename exposes these creation callbacks as named HScript functions.
			// Collect only their literal sprite assignments: generic `.sprite` scans
			// elsewhere would mistake unrelated scene objects for runtime assets.
			var callbacks = new EReg('function\\s+(onNoteCreation|onStrumCreation)\\s*\\(', 'g');
			var remaining = source;
			var sourceOffset = 0;
			var callbackAttempts = 0;
			while (callbackAttempts++ < 128 && callbacks.match(remaining)) {
				var callbackName = callbacks.matched(1);
				var callbackPosition = callbacks.matchedPos();
				var absoluteCallbackStart = sourceOffset + callbackPosition.pos;
				var bodyStart = absoluteCallbackStart + callbackPosition.len;
				var bodyEnd = source.length;
				var tail = source.substr(bodyStart);
				var nextFunction = new EReg('function\\s+[A-Za-z_$][A-Za-z0-9_$]*\\s*\\(', '');
				if (nextFunction.match(tail))
					bodyEnd = bodyStart + nextFunction.matchedPos().pos;
				var callbackBody = source.substr(bodyStart, bodyEnd - bodyStart);
				var property = callbackName == 'onNoteCreation' ? 'noteSprite' : 'sprite';
				var assignment = new EReg('(?:\\.\\s*)?' + property
					+ '\\s*=\\s*["\\\']([^"\\\']+)["\\\']', 'g');
				var assignments = 0;
				while (assignments++ < 128 && assignment.match(callbackBody)) {
					appendNoteStrumSpriteAsset(assignment.matched(1), scriptRelative);
					var assignmentPosition = assignment.matchedPos();
					if (assignmentPosition.len <= 0 || assignmentPosition.pos + assignmentPosition.len >= callbackBody.length)
						break;
					callbackBody = callbackBody.substr(assignmentPosition.pos + assignmentPosition.len);
				}
				if (assignments > 128) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-note-sprite] ' + scriptRelative
						+ ': callback sprite assignments exceed 128 entries';
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				}
				if (callbackPosition.len <= 0 || callbackPosition.pos + callbackPosition.len >= remaining.length)
					break;
				sourceOffset = absoluteCallbackStart + callbackPosition.len;
				remaining = source.substr(sourceOffset);
			}
			if (callbackAttempts > 128) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-runtime-note-sprite] ' + scriptRelative
					+ ': callback count exceeds 128 entries';
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
			}
		};
		var collectImplicitNoteTypeAssets = function():Void {
			// Native Note looks for an atlas at images/game/notes/<noteType> even
			// when the note type has no owner script. Keep those implicit visual
			// dependencies in the selected-owner asset plan as well.
			var names:Array<String> = [];
			var seen:Map<String, Bool> = new Map();
			if (songData.convertedCharts != null)
				for (chart in songData.convertedCharts) {
					if (chart == null) continue;
					var types:Dynamic = chart.noteTypes;
					if (!Std.isOfType(types, Array) && chart.chart != null
						&& Reflect.field(chart.chart, 'song') != null)
						types = Reflect.field(chart.chart.song, 'codenameNoteTypes');
					if (!Std.isOfType(types, Array)) continue;
					for (raw in (cast types:Array<Dynamic>)) {
						if (!Std.isOfType(raw, String)) continue;
						var name:String = StringTools.trim(cast raw);
						if (name == '' || name.toLowerCase() == 'default note'
							|| !CodenameScriptDiscovery.safeName(name)) continue;
						var key = name.toLowerCase();
						if (seen.exists(key)) continue;
						seen.set(key, true);
						names.push(name);
					}
				}
			for (name in names) {
				var pngRelative = 'images/game/notes/' + name + '.png';
				if (CodenameInstallationAssetOverlay.resolve(sourceRoot,
					installationAssetRoot, pngRelative).source == null) continue;
				appendNoteStrumSpriteAsset('game/notes/' + name, 'data/notes/' + name);
			}
		};
		// Runtime scripts may form a source song path from SONG.meta.name (for
		// example a lyrics timeline). Stage only small data sidecars at that
		// song's top level; chart/audio/media trees use their own import plans.
		var songFolder:String = Reflect.field(songData, 'sourceFolder');
		if (CodenameScriptDiscovery.safeName(songFolder)) {
			var songDataFolder = Path.join([sourceRoot, 'songs', songFolder]);
			if (FileSystem.exists(songDataFolder) && FileSystem.isDirectory(songDataFolder)
				&& CodenameScriptDiscovery.withinRoot(sourceRoot, songDataFolder)) {
				var entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(songDataFolder));
				entries.sort(Reflect.compare);
				if (entries.length > 128) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-sidecars] Song folder exceeds 128 entry scan limit: '
						+ songFolder;
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				}
				var examined = 0;
				for (entry in entries) {
					if (examined++ >= 128) break;
					if (!CodenameScriptDiscovery.safeName(entry)
						|| ['json', 'jsonc', 'txt', 'xml'].indexOf(Path.extension(entry).toLowerCase()) < 0)
						continue;
					appendExactAsset('songs/' + songFolder + '/' + entry, false);
				}
			}
		}
		// Rating names are chosen at runtime (for example, Paths.image('game/score/'
		// + rating)), so literal-reference collection cannot see them. Stage the
		// conventional flat score-image folder from this selected owner only.
		var scoreDirectory = Path.join([sourceRoot, 'images/game/score']);
		if (FileSystem.exists(scoreDirectory) && FileSystem.isDirectory(scoreDirectory)) {
			if (!CodenameScriptDiscovery.withinRoot(sourceRoot, scoreDirectory)) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-runtime-score-assets] images/game/score is outside the selected owner';
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
			} else {
				var scoreEntries:Array<String> = [];
				try scoreEntries = ImportDirectoryListing.normalize(FileSystem.readDirectory(scoreDirectory)) catch (_:Dynamic) {}
				scoreEntries.sort(Reflect.compare);
				if (scoreEntries.length > 128) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-score-assets] images/game/score exceeds 128 entry scan limit';
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				} else {
					for (entry in scoreEntries) {
						if (!CodenameScriptDiscovery.safeName(entry)
							|| Path.extension(entry).toLowerCase() != 'png') continue;
						var scoreAsset = Path.join([scoreDirectory, entry]);
						if (FileSystem.isDirectory(scoreAsset)) continue;
						if (!CodenameScriptDiscovery.withinRoot(sourceRoot, scoreAsset)) {
							if (songData.diagnostics == null) songData.diagnostics = [];
							var message = '[codename-runtime-score-assets] images/game/score/' + entry
								+ ' is outside the selected owner';
							if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
							continue;
						}
						appendExactAsset('images/game/score/' + entry, true);
					}
				}
			}
		}
		// StickerPack reads a pack id from chart metadata, then chooses one of
		// the image keys in that owner's data/stickerpacks JSON. Copy the bounded
		// pack catalog and its literal image dependencies for every Codename song;
		// the default pack is also used when a requested pack is absent.
		var stickerDirectory = Path.join([sourceRoot, 'data/stickerpacks']);
		if (FileSystem.exists(stickerDirectory) && FileSystem.isDirectory(stickerDirectory)
			&& CodenameScriptDiscovery.withinRoot(sourceRoot, stickerDirectory)) {
			var stickerEntries:Array<String> = [];
			try stickerEntries = ImportDirectoryListing.normalize(FileSystem.readDirectory(stickerDirectory)) catch (_:Dynamic) {}
			stickerEntries.sort(Reflect.compare);
			if (stickerEntries.length > 128) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-runtime-stickerpack] data/stickerpacks exceeds 128 entry scan limit';
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
			}
			var stickerPacksExamined = 0;
			var stickerReferencesExamined = 0;
			for (entry in stickerEntries) {
				if (stickerPacksExamined++ >= 128) break;
				if (!CodenameScriptDiscovery.safeName(entry)
					|| Path.extension(entry).toLowerCase() != 'json') continue;
				var packRelative = 'data/stickerpacks/' + entry;
				var packResolution = CodenameScriptDiscovery.scopedResolution(sourceRoot, packRelative);
				if (packResolution.relative == null) continue;
				packRelative = packResolution.relative;
				appendExactAsset(packRelative, false);
				var packSource = Path.join([sourceRoot, packRelative]);
				var packSize = -1;
				try packSize = FileSystem.stat(packSource).size catch (_:Dynamic) {}
				if (packSize < 0 || packSize > 1048576) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-stickerpack] ' + packRelative
						+ ' exceeds 1 MiB or could not be read';
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
					continue;
				}
				var packData:Dynamic = null;
				try packData = haxe.Json.parse(File.getContent(packSource)) catch (error:Dynamic) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-stickerpack] ' + packRelative
						+ ' has invalid JSON: ' + Std.string(error);
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
					continue;
				}
				var stickerList:Dynamic = packData == null ? null : Reflect.field(packData, 'stickers');
				if (!Std.isOfType(stickerList, Array)) continue;
				var stickerKeys:Array<Dynamic> = cast stickerList;
				if (stickerKeys.length > 256) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-runtime-stickerpack] ' + packRelative
						+ ' exceeds 256 sticker entries';
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				}
				var stickerIndex = 0;
				for (stickerKey in stickerKeys) {
					if (stickerIndex++ >= 256) break;
					if (stickerReferencesExamined++ >= 512) {
						if (songData.diagnostics == null) songData.diagnostics = [];
						var message = '[codename-runtime-stickerpack] sticker image references exceed 512 entry scan limit';
						if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
						break;
					}
					if (!Std.isOfType(stickerKey, String)) continue;
					appendNamedAsset('images', cast stickerKey, '.png');
				}
				if (stickerReferencesExamined >= 512) break;
			}
		}
			// Codename's Paths.getFrames('game/notes/default') checks the selected
			// owner before the engine asset tree. Materialize that atlas in the
			// owner namespace so runtime lookups stay scoped and source-faithful.
			appendDefaultNoteAtlasAssets();
			collectImplicitNoteTypeAssets();
			var codenameScripts = codenameScriptFiles(songData);
			for (script in codenameScripts) {
			var source = '';
			if (script.embeddedScript != null) {
				files.push({source:null, relative:script.relative, content:script.embeddedScript, family:script.family});
				source = script.embeddedScript;
			} else if (script.family == 'event-pack') {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-event-pack] ' + script.relative + ' has no decoded script';
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
					continue;
			} else {
				files.push({source:script.path, relative:script.relative, family:script.family});
			}
			if (script.family == 'character-xml') {
				// Codename defaults sprite to the authored character ID. Keep the
				// original XML and every Sparrow/Animate atlas page in the same
				// selected namespace; this is also the runtime character visual's
				// dependency resolver, so unowned/global files cannot leak in.
				try {
					var document = Xml.parse(File.getContent(script.path)).firstElement();
					if (document == null) throw 'missing root element';
					var sprite = document.exists('sprite') && StringTools.trim(document.get('sprite')) != ''
						? document.get('sprite') : script.authoredId;
					if (!CodenameScriptDiscovery.safeRelativeName(sprite))
						throw 'unsafe sprite key';
					var atlasFiles = CodenameCharacterAtlas.files(sourceRoot, sprite);
					if (atlasFiles.length == 0) {
						if (songData.diagnostics == null) songData.diagnostics = [];
						var message = '[codename-character-asset] no supported Sparrow or Animate atlas for ' + sprite;
						if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
					}
					for (atlasFile in atlasFiles) {
						var suffix = StringTools.startsWith(atlasFile.relative, '.')
							? atlasFile.relative : '/' + atlasFile.relative;
						appendResolvedAsset(atlasFile.source,
							'images/characters/' + sprite + suffix);
					}
				} catch (error:Dynamic) {
					if (songData.diagnostics == null) songData.diagnostics = [];
					var message = '[codename-character-xml] ' + script.relative + ': ' + Std.string(error);
					if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				}
				continue;
			}
					if (script.family == 'event-schema') continue;
			if (script.family != 'event-pack')
				try source = File.getContent(script.path) catch (_:Dynamic) continue;
			var dynamicAtlases = CodenameDynamicAtlasAssets.filesFor(sourceRoot,
				installationAssetRoot, source);
			for (diagnostic in dynamicAtlases.diagnostics) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-runtime-dynamic-atlas] ' + script.relative + ': ' + diagnostic;
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
			}
			for (asset in dynamicAtlases.files)
				appendResolvedAsset(asset.source, asset.relative);
			collectMenuMusic(source, script.relative);
			collectMenuSfx(source);
			collectListedFolderAssets(source, script.relative);
			collectDynamicImageFolders(source, script.relative);
			collectDirectIconAssets(source);
			collectNoteStrumCreationAssets(source, script.relative);
			// Codename scripts can reach videos through Paths.video or through
			// Assets.getPath(Paths.file(...)); shader ids are resolved by the
			// CustomShader constructor.  These are literal-only and remain rooted
			// in the selected owner namespace, like Paths.* dependencies below.
			collectNamedAssets(source,
				'Paths\\s*\\.\\s*video\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'videos', '.mp4');
			collectNamedAssets(source,
				'Paths\\s*\\.\\s*obj\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'models', '.obj');
			collectNamedAssets(source,
				'(?:new\\s+)?CustomShader\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'shaders', '.frag');
			collectShaderAssets(source);
			var filePattern = new EReg('Paths\\s*\\.\\s*file\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'g');
			var remainingSource = source;
			var fileAttempts = 0;
			while (fileAttempts++ < 1024 && filePattern.match(remainingSource)) {
				var fileKey = StringTools.replace(filePattern.matched(1), '\\', '/');
				var firstFolder = fileKey.indexOf('/') < 0 ? '' : fileKey.substr(0, fileKey.indexOf('/')).toLowerCase();
				if (['images', 'sounds', 'music', 'videos', 'fonts', 'shaders', 'data'].indexOf(firstFolder) >= 0)
					appendExactAsset(fileKey, true);
				var filePosition = filePattern.matchedPos();
				if (filePosition.len <= 0 || filePosition.pos + filePosition.len >= remainingSource.length) break;
				remainingSource = remainingSource.substr(filePosition.pos + filePosition.len);
			}
			for (reference in HxcAssetPlanner.literalReferences(source, true)) {
				if (reference == null || !codenameSafeAssetKey(reference.key)) continue;
				if (reference.kind == 'sound') {
					appendSoundAsset(reference.key, true);
					continue;
				}
				if (reference.kind == 'frames' || reference.kind == 'image') {
					var framePlan = CodenameFrameAtlasAssets.plan(sourceRoot, reference.key);
					if (framePlan.files.length == 0) {
						for (diagnostic in framePlan.diagnostics) {
							if (songData.diagnostics == null) songData.diagnostics = [];
							var message = '[codename-runtime-frame-asset] ' + script.relative + ': ' + diagnostic;
							if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
						}
						continue;
					}
					for (frameAsset in framePlan.files)
						appendResolvedAsset(frameAsset.source, frameAsset.relative);
					continue;
				}
				var folder = switch (reference.kind) {
					case 'image' | 'sparrow' | 'packer': 'images';
					case 'sound': 'sounds';
					case 'music': 'music';
					case 'frag': 'shaders';
					case 'font': 'fonts';
					case 'xml' | 'json' | 'txt': 'data';
					case 'video': 'videos';
					default: '';
				};
			if (folder == '') continue;
			if (reference.kind == 'frag') {
				queueShaderAsset(reference.key, [], 0);
				continue;
			}
			var suffixes = switch (reference.kind) {
					case 'sparrow': ['.png', '.xml'];
					case 'packer': ['.png', '.txt'];
					case 'image': ['.png'];
					case 'frag': ['.frag'];
					case 'font': [''];
					case 'xml': ['.xml'];
					case 'json': ['.json'];
					case 'txt': ['.txt'];
					default: ['.ogg', '.wav', '.mp3'];
				};
				for (suffix in suffixes) {
					var relative = folder + '/' + reference.key
						+ (reference.key.toLowerCase().endsWith(suffix) ? '' : suffix);
					var wasPresent = files.length;
					appendExactAsset(relative, false);
					if (files.length > wasPresent && (suffix == '.ogg' || suffix == '.wav' || suffix == '.mp3')) break;
				}
			}
		}
		var scannedShaders:Map<String, Bool> = new Map();
		var shaderIndex = 0;
		while (shaderIndex < shaderQueue.length) {
			var shader = shaderQueue[shaderIndex++];
			var normalizedRelative = shader.relative.toLowerCase();
			if (shader.depth > 16) {
				shaderKeyError('shader import depth exceeded at ' + shader.relative);
				continue;
			}
			if (shader.ancestry.indexOf(normalizedRelative) >= 0) {
				shaderKeyError('cyclic shader import: ' + shader.ancestry.concat([normalizedRelative]).join(' -> '));
				continue;
			}
			if (scannedShaders.exists(normalizedRelative)) continue;
			scannedShaders.set(normalizedRelative, true);
			var shaderSource = '';
			try shaderSource = File.getContent(shader.source) catch (error:Dynamic) {
				shaderKeyError('could not read ' + shader.relative + ': ' + Std.string(error));
				continue;
			}
			var imports = new EReg('^[ \\t]*#import[ \\t]*<([^>\\r\\n]+)>[ \\t]*\\r?$', 'gm');
			var importRemaining = shaderSource;
			var importAttempts = 0;
			while (importAttempts++ < 256 && imports.match(importRemaining)) {
				var importKey = StringTools.trim(imports.matched(1));
				queueShaderAsset(importKey, shader.ancestry.concat([normalizedRelative]), shader.depth + 1);
				var position = imports.matchedPos();
				if (position.len <= 0 || position.pos + position.len >= importRemaining.length) break;
				importRemaining = importRemaining.substr(position.pos + position.len);
			}
			if (imports.match(importRemaining)) shaderKeyError('too many imports in ' + shader.relative);
		}
		// Source classes remain data-only until Codename HScript has a safe class
		// loader. Resolve only literal asset arguments passed to a class method
		// whose owner source directly calls a known Paths asset function.
		var classPlan = CodenameClassScriptPlan.build(sourceRoot, codenameScripts);
		for (diagnostic in classPlan.diagnostics) {
			if (songData.diagnostics == null) songData.diagnostics = [];
			if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
		}
		for (dependency in classPlan.dependencies) {
			if (dependency.kind != 'sparrow' && dependency.kind != 'packer'
				&& dependency.kind != 'frames' && dependency.kind != 'image') continue;
			var framePlan = CodenameFrameAtlasAssets.plan(sourceRoot, dependency.key);
			if (framePlan.files.length == 0) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				var message = '[codename-class-asset] ' + dependency.consumer + ': '
					+ dependency.sourceClass + '.' + dependency.method + ' '
					+ dependency.key + ' ' + framePlan.diagnostics.join('; ');
				if (songData.diagnostics.indexOf(message) < 0) songData.diagnostics.push(message);
				continue;
			}
			for (asset in framePlan.files) appendResolvedAsset(asset.source, asset.relative);
		}
		return files;
	}

	/** Runtime selection requires the generated stage map and camera plan to have
	 * the same difficulty keys and authored stages. */
	static function codenameMetadataStagesMatch(scripts:Dynamic, camera:Dynamic):Bool {
		if (scripts == null || camera == null) return false;
		var stages:Dynamic = Reflect.field(scripts, 'stages');
		var difficulties:Dynamic = Reflect.field(camera, 'difficulties');
		if (stages == null || difficulties == null) return false;
		var scriptDifficulties = Reflect.fields(stages);
		var cameraDifficulties = Reflect.fields(difficulties);
		if (scriptDifficulties.length != cameraDifficulties.length) return false;
		for (difficulty in scriptDifficulties) {
			var cameraEntry:Dynamic = Reflect.field(difficulties, difficulty);
			var scriptStage:Dynamic = Reflect.field(stages, difficulty);
			var cameraStage:Dynamic = cameraEntry == null ? null : Reflect.field(cameraEntry, 'stage');
			if (!Std.isOfType(scriptStage, String) || !Std.isOfType(cameraStage, String)
				|| StringTools.trim(Std.string(scriptStage)).toLowerCase()
					!= StringTools.trim(Std.string(cameraStage)).toLowerCase()) return false;
		}
		return true;
	}

	static function codenameNoteTypesByDifficulty(songData:SongImport):Dynamic {
		var result:Dynamic = {};
		if (songData == null || songData.convertedCharts == null) return result;
		for (chart in songData.convertedCharts) {
			if (chart == null || !CodenameScriptDiscovery.safeName(chart.difficulty)) continue;
			var types:Dynamic = chart.noteTypes;
			if (!Std.isOfType(types, Array) && chart.chart != null
				&& Reflect.field(chart.chart, 'song') != null)
				types = Reflect.field(chart.chart.song, 'codenameNoteTypes');
			if (Std.isOfType(types, Array))
				Reflect.setField(result, chart.difficulty, (cast types:Array<Dynamic>).copy());
		}
		return result;
	}

	/** Note-type metadata is a new per-song sidecar. Never replace an existing
	 * file, so imports can refresh this runtime support without rewriting charts
	 * or user-owned metadata. */
	static function writeCodenameNoteTypePlanIfMissing(song:String, namespace:String,
		difficulties:Dynamic, result:ImportAssetMergeResult):Void {
		if (difficulties == null || Reflect.fields(difficulties).length == 0) return;
		var path = CodenameScriptPlan.noteTypesMetadataPath(namespace, song);
		if (path == '') return;
		if (FileSystem.exists(path)) {
			result.skipped++;
			return;
		}
		try {
			var plan = CodenameScriptPlan.createNoteTypes(song, difficulties);
			ensureDirectory(Path.directory(path));
			File.saveContent(path, CodenameScriptPlan.stringifyNoteTypes(plan));
			result.copied++;
		} catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not write Codename note type metadata for ' + song + ': '
				+ Std.string(error));
		}
	}

	/** Generated script and camera plans are one selected-owner product: runtime
	 * actor planning validates each camera difficulty against this stage map. */
	static function reconcileCodenameOwnerMetadata(songData:SongImport, namespace:String,
		result:ImportAssetMergeResult):Void {
		if (songData == null || namespace == null || StringTools.trim(namespace) == '') return;
		var rawSong:Dynamic = Reflect.field(songData, 'sourceFolder');
		if (!Std.isOfType(rawSong, String)) return;
		var song:String = cast rawSong;
		var metadataPath = CodenameScriptPlan.metadataPath(namespace, song);
		var cameraPath = CodenameScriptPlan.cameraMetadataPath(namespace, song);
		if (metadataPath == '' || cameraPath == '') return;
		var noteTypeDifficulties = codenameNoteTypesByDifficulty(songData);

		var metadata:String = null;
		var cameraMetadata:String = null;
		try {
			var scripts = CodenameScriptPlan.create(song,
				Reflect.field(songData, 'codenameAuthoredStages'));
			var camera = CodenameScriptPlan.createCamera(song,
				Reflect.field(songData, 'codenameAuthoredCamera'));
			if (!codenameMetadataStagesMatch(scripts, camera))
				throw 'Generated Codename script and camera plans disagree on difficulties or stages';
			metadata = CodenameScriptPlan.stringify(scripts);
			cameraMetadata = CodenameScriptPlan.stringifyCamera(camera);
			writeCodenameNoteTypePlanIfMissing(song, namespace, noteTypeDifficulties, result);
		} catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not build paired Codename metadata for ' + song + ': '
				+ Std.string(error));
			return;
		}

		var hadMetadata = FileSystem.exists(metadataPath);
		var hadCameraMetadata = FileSystem.exists(cameraPath);
		var previousMetadata:String = null;
		var previousCameraMetadata:String = null;
		try {
			if (hadMetadata) previousMetadata = File.getContent(metadataPath);
			if (hadCameraMetadata) previousCameraMetadata = File.getContent(cameraPath);
		} catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not read existing paired Codename metadata for ' + song + ': '
				+ Std.string(error));
			return;
		}
		if (hadMetadata && hadCameraMetadata && previousMetadata == metadata
			&& previousCameraMetadata == cameraMetadata) {
			result.skipped += 2;
			return;
		}
		// These reserved files are a paired product, but an existing sidecar may
		// have been authored or retained by an older import. Never replace one
		// member when its contents differ from this generation; doing so can
		// silently discard camera data and leave the pair inconsistent.
		if ((hadMetadata && previousMetadata != metadata)
			|| (hadCameraMetadata && previousCameraMetadata != cameraMetadata)) {
			result.skipped += 2;
			return;
		}

		var wroteMetadata = false;
		var wroteCameraMetadata = false;
		try {
			if (!hadMetadata) {
				ensureDirectory(Path.directory(metadataPath));
				wroteMetadata = true;
				File.saveContent(metadataPath, metadata);
			}
			if (!hadCameraMetadata) {
				ensureDirectory(Path.directory(cameraPath));
				wroteCameraMetadata = true;
				File.saveContent(cameraPath, cameraMetadata);
			}
			if (hadMetadata) result.skipped++;
			else result.copied++;
			if (hadCameraMetadata) result.skipped++;
			else result.copied++;
		} catch (error:Dynamic) {
			var rollbackErrors:Array<String> = [];
			if (wroteCameraMetadata) try {
				if (FileSystem.exists(cameraPath) && !FileSystem.isDirectory(cameraPath))
					FileSystem.deleteFile(cameraPath);
			} catch (rollback:Dynamic) rollbackErrors.push('camera rollback: ' + Std.string(rollback));
			if (wroteMetadata) try {
				if (FileSystem.exists(metadataPath) && !FileSystem.isDirectory(metadataPath))
					FileSystem.deleteFile(metadataPath);
			} catch (rollback:Dynamic) rollbackErrors.push('script rollback: ' + Std.string(rollback));
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not reconcile paired Codename metadata for ' + song + ': '
				+ Std.string(error) + (rollbackErrors.length == 0 ? ''
					: ' (' + rollbackErrors.join('; ') + ')'));
		}
	}

	/** Copy selected Codename song/stage script dependencies from the owner.
	 * No whole media-tree walk or global native asset merge occurs here. */
	static function mergeCodenameRuntimeAssets(songData:SongImport):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
		if (songData == null || songData.sourceRoot == null)
			return result;
		var namespace = CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
		var runtimeFiles = codenameRuntimeFiles(songData);
		for (entry in runtimeFiles) {
			if (importWorkCancelled()) break;
			var destination = Path.join([namespace, entry.relative]);
			if (entry.content != null)
				writeImportContentNonOverwriting(entry.content, destination, result);
			else
				copyImportFileNonOverwriting(entry.source, destination, result);
		}
		// Register every imported Codename owner, including packages with global
		// scripts but no custom states. The switch menu groups by owner; only its
		// separate Imported Mods route requires launchable state rows.
		var catalogStates:Array<String> = [];
		for (entry in runtimeFiles)
			if (StringTools.startsWith(entry.relative, 'data/states/')
				&& entry.relative.toLowerCase().endsWith('.hx')
				&& entry.family != 'transition'
				&& catalogStates.indexOf(entry.relative) < 0)
				catalogStates.push(entry.relative);
		var catalogPath = CodenameModCatalog.PATH;
		if (songData.engine == ImportEngine.CODENAME) {
			var rawCatalog = '';
			if (FileSystem.exists(catalogPath)) try rawCatalog = File.getContent(catalogPath)
			catch (error:Dynamic) {
				result.failed++;
				result.errors.push('Could not read imported Codename mod catalog: ' + CodenameModCatalog.FILE_NAME
					+ ' (' + Std.string(error) + ')');
				rawCatalog = null;
			}
			if (rawCatalog != null) {
				var label = importOwnerDisplayLabel(songData);
				var mergedCatalog = CodenameModCatalog.merge(rawCatalog, namespace, label, catalogStates);
				if (!mergedCatalog.valid) {
					result.failed++;
					result.errors.push('Could not merge imported Codename mod catalog: ' + CodenameModCatalog.FILE_NAME
						+ ' (' + mergedCatalog.error + ')');
				} else if (mergedCatalog.changed) try {
					ensureDirectory(Path.directory(catalogPath));
					File.saveContent(catalogPath, CodenameModCatalog.stringify(mergedCatalog.data));
					result.copied++;
				} catch (error:Dynamic) {
					result.failed++;
					result.errors.push('Could not write imported Codename mod catalog: ' + CodenameModCatalog.FILE_NAME
						+ ' (' + Std.string(error) + ')');
				} else result.skipped++;
			}
		}
		var song:String = Reflect.field(songData, 'sourceFolder');
		// `namespace` is derived from this source root and engine, so only this
		// owner's reserved pair is reconciled from the current imported charts.
		reconcileCodenameOwnerMetadata(songData, namespace, result);
		var songMetaPath = CodenameSongMetadata.path(namespace, song);
		if (songMetaPath != '') {
			if (FileSystem.exists(songMetaPath))
				result.skipped++;
			else try {
				var songMeta = CodenameSongMetadata.create(song,
					Reflect.field(songData, 'codenameOriginalMeta'));
				ensureDirectory(Path.directory(songMetaPath));
				File.saveContent(songMetaPath, CodenameSongMetadata.stringify(songMeta));
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
				result.errors.push('Could not save Codename song metadata: ' + songMetaPath
					+ ' (' + Std.string(error) + ')');
			}
		}
		var resolvedMetaPath = CodenameSongMetadata.resolvedPath(namespace, song);
		if (resolvedMetaPath != '') {
			if (FileSystem.exists(resolvedMetaPath))
				result.skipped++;
			else try {
				var resolvedMeta:Dynamic = Reflect.field(songData, 'codenameResolvedMeta');
				ensureDirectory(Path.directory(resolvedMetaPath));
				File.saveContent(resolvedMetaPath, CodenameSongMetadata.stringifyResolved(resolvedMeta));
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
				result.errors.push('Could not save Codename resolved metadata: ' + resolvedMetaPath
					+ ' (' + Std.string(error) + ')');
			}
		}
		return result;
	}

	/** `.hx` counts only for Nightmare Vision's copied generic script trees;
		data-family and other-engine checks retain their narrower extension set. */
	static function hasCompatScriptFile(path:String, depth:Int = 0, includeHaxe:Bool = false):Bool {
		if (path == null || !FileSystem.isDirectory(path) || depth > 10)
			return false;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(path));
		} catch (_:Dynamic) {
			return false;
		}
		for (entry in entries) {
			if (!validImportEntryName(entry))
				continue;
			var child = Path.join([path, entry]);
			if (FileSystem.isDirectory(child)) {
				if (hasCompatScriptFile(child, depth + 1, includeHaxe))
					return true;
				continue;
			}
			var lower = entry.toLowerCase();
			if (lower.endsWith('.hscript') || lower.endsWith('.hxs')
				|| lower.endsWith('.lua') || lower.endsWith('.hxc')
				|| (includeHaxe && lower.endsWith('.hx')))
				return true;
		}
		return false;
	}

	/** Collect executable files using the same bounded layout copied by
	 * mergeCompatScriptTrees. `relative` is built only from directory entries,
	 * so it cannot escape the destination namespace. */
	/** `includeHaxe` is passed only for generic trees copied for Nightmare Vision. */
	static function collectCompatScriptFiles(source:String, relative:String, hxcOnly:Bool,
		output:Array<Dynamic>, depth:Int, budget:Array<Int>, ?suffixes:Array<String>,
		?includeHaxe:Bool = false):Void {
		if (source == null || !FileSystem.isDirectory(source) || depth > 10
			|| budget == null || budget.length == 0 || budget[0] <= 0)
			return;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(source));
		} catch (_:Dynamic) {
			return;
		}
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (entry in entries) {
			if (budget[0] <= 0)
				break;
			if (!validImportEntryName(entry))
				continue;
			var sourcePath = Path.join([source, entry]);
			var childRelative = relative == '' ? entry : relative + '/' + entry;
			if (FileSystem.isDirectory(sourcePath)) {
				collectCompatScriptFiles(sourcePath, childRelative, hxcOnly, output, depth + 1, budget,
					suffixes, includeHaxe);
				continue;
			}
			var lower = entry.toLowerCase();
			var executable = hxcOnly ? lower.endsWith('.hxc')
				: (lower.endsWith('.hscript') || lower.endsWith('.hxs')
					|| lower.endsWith('.lua') || lower.endsWith('.hxc')
					|| (includeHaxe && lower.endsWith('.hx')));
			if (suffixes != null) {
				executable = false;
				for (suffix in suffixes)
					if (lower.endsWith(suffix)) executable = true;
			}
			if (!executable)
				continue;
			output.push({relative:childRelative, source:sourcePath});
			budget[0]--;
		}
	}

	/** NMV's FunkinScript loader accepts these source extensions. Keep the
	 * extension list local to its owner-scoped path adapter so other importers
	 * retain their existing HScript/Lua/HXC rules. */
	static function nightmareVisionScriptSuffixes():Array<String> {
		return ['.hx', '.hxs', '.hscript'];
	}

	/** Walk one tree without an arbitrary file/depth cutoff. The explicit stack
	 * avoids recursive stack growth, and ancestry checks stop symlink cycles while
	 * retaining distinct in-root aliases at each authored relative path. */
	static function collectNightmareVisionScriptDirectory(source:String, relative:String,
		sourceRoot:String, output:Array<Dynamic>):Bool {
		if (source == null || !FileSystem.isDirectory(source))
			return true;
		if (output == null || sourceRoot == null || !importPathIsWithin(source, sourceRoot))
			return false;
		var suffixes = nightmareVisionScriptSuffixes();
		var stack:Array<Dynamic> = [{source:source, relative:relative,
			ancestors:[importPathKey(source)]}];
		while (stack.length > 0) {
			if (importWorkCancelled())
				return false;
			var current:Dynamic = stack.pop();
			var currentSource:String = current.source;
			var currentRelative:String = current.relative;
			if (!importPathIsWithin(currentSource, sourceRoot))
				return false;
			var entries:Array<String>;
			try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(currentSource)) catch (_:Dynamic) return false;
			entries.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				if (!validImportEntryName(entry))
					continue;
				var sourcePath = Path.join([currentSource, entry]);
				var childRelative = currentRelative == '' ? entry : currentRelative + '/' + entry;
				if (FileSystem.isDirectory(sourcePath)) {
					if (!importPathIsWithin(sourcePath, sourceRoot))
						return false;
					var key = importPathKey(sourcePath);
					var ancestors:Array<String> = current.ancestors;
					if (ancestors.indexOf(key) >= 0)
						continue;
					var childAncestors = ancestors.copy();
					childAncestors.push(key);
					stack.push({source:sourcePath, relative:childRelative, ancestors:childAncestors});
					continue;
				}
				var lower = entry.toLowerCase();
				var executable = false;
				for (suffix in suffixes)
					if (lower.endsWith(suffix)) executable = true;
				if (!executable)
					continue;
				if (!importPathIsWithin(sourcePath, sourceRoot))
					return false;
				output.push({relative:childRelative, source:sourcePath});
			}
		}
		return true;
	}

	/** The NMV song loader asks for immediate files in these directories only. */
	static function collectNightmareVisionScriptFilesImmediate(source:String, relative:String,
		sourceRoot:String, output:Array<Dynamic>):Bool {
		if (source == null || !FileSystem.isDirectory(source))
			return true;
		if (output == null || sourceRoot == null || !importPathIsWithin(source, sourceRoot))
			return false;
		var entries:Array<String>;
		try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(source)) catch (_:Dynamic) return false;
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (entry in entries) {
			if (!validImportEntryName(entry))
				continue;
			var sourcePath = Path.join([source, entry]);
			if (FileSystem.isDirectory(sourcePath))
				continue;
			var lower = entry.toLowerCase();
			var executable = false;
			for (suffix in nightmareVisionScriptSuffixes())
				if (lower.endsWith(suffix)) executable = true;
			if (!executable)
				continue;
			if (!importPathIsWithin(sourcePath, sourceRoot))
				return false;
			output.push({relative:relative == '' ? entry : relative + '/' + entry, source:sourcePath});
		}
		return true;
	}

	/** Song scripts are enumerated non-recursively by Nightmare Vision's
	 * Paths.listAllFilesInDirectory. Retain only the two directories PlayState
	 * actually asks for; song charts, audio and media remain on their normal
	 * import paths. */
	static function collectNightmareVisionSongScripts(songsRoot:String, relative:String,
		sourceRoot:String, output:Array<Dynamic>):Bool {
		if (songsRoot == null || !FileSystem.isDirectory(songsRoot))
			return true;
		if (output == null || sourceRoot == null || !importPathIsWithin(songsRoot, sourceRoot))
			return false;
		var songs:Array<String>;
		try songs = ImportDirectoryListing.normalize(FileSystem.readDirectory(songsRoot)) catch (_:Dynamic) return false;
		songs.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (song in songs) {
			if (importWorkCancelled())
				return false;
			if (!validImportEntryName(song))
				continue;
			var songRoot = Path.join([songsRoot, song]);
			if (!FileSystem.isDirectory(songRoot))
				continue;
			if (!importPathIsWithin(songRoot, sourceRoot))
				return false;
			var songRelative = relative == '' ? song : relative + '/' + song;
			if (!collectNightmareVisionScriptFilesImmediate(songRoot, songRelative, sourceRoot, output))
				return false;
			var scriptsRoot = Path.join([songRoot, 'scripts']);
			if (FileSystem.isDirectory(scriptsRoot)) {
				if (!collectNightmareVisionScriptFilesImmediate(scriptsRoot, songRelative + '/scripts',
					sourceRoot, output))
					return false;
			}
		}
		return true;
	}

	/** Collect only NMV gameplay script paths that its source runtime searches.
	 * This mirrors the data-first/fallback lookup order for characters, stages,
	 * note types and events, plus PlayState's direct song script directories. */
	static function collectNightmareVisionScriptFiles(root:String, prefix:String,
		output:Array<Dynamic>):Bool {
		if (root == null || !FileSystem.isDirectory(root) || output == null)
			return false;
		for (relative in ['data/characters', 'data/stages', 'data/notetypes', 'data/events',
			'characters', 'events', 'notetypes']) {
			if (importWorkCancelled())
				return false;
			var source = Path.join([root, relative]);
			if (!FileSystem.isDirectory(source))
				continue;
			var destinationRelative = prefix == '' ? relative : prefix + '/' + relative;
			if (!collectNightmareVisionScriptDirectory(source, destinationRelative, root, output))
				return false;
		}
		if (importWorkCancelled())
			return false;
		var songsRoot = Path.join([root, 'songs']);
		if (FileSystem.isDirectory(songsRoot)) {
			var songsRelative = prefix == '' ? 'songs' : prefix + '/songs';
			if (!collectNightmareVisionSongScripts(songsRoot, songsRelative, root, output))
				return false;
		}
		return true;
	}

	/** Collect JSON stage definitions from the two path families used by
	 * NightmareVisionStageData. Every JSON below these roots can be addressed by
	 * a nested stage id, so retain the paths verbatim and do not impose a depth or
	 * file-count limit. */
	static function collectNightmareVisionStageDataFiles(root:String,
		output:Array<Dynamic>):Bool {
		if (root == null || !FileSystem.isDirectory(root) || output == null)
			return false;
		for (relativeRoot in ['data/stages', 'stages']) {
			if (importWorkCancelled())
				return false;
			var sourceRoot = Path.join([root, relativeRoot]);
			if (!FileSystem.isDirectory(sourceRoot))
				continue;
			if (!importPathIsWithin(sourceRoot, root))
				return false;
			var stack:Array<Dynamic> = [{source:sourceRoot, relative:relativeRoot,
				ancestors:[importPathKey(sourceRoot)]}];
			while (stack.length > 0) {
				if (importWorkCancelled())
					return false;
				var current:Dynamic = stack.pop();
				var currentSource:String = current.source;
				if (!importPathIsWithin(currentSource, root))
					return false;
				var entries:Array<String>;
				try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(currentSource)) catch (_:Dynamic) return false;
				entries.sort(function(a:String, b:String):Int {
					var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
					return lower == 0 ? Reflect.compare(a, b) : lower;
				});
				for (entry in entries) {
					if (!validImportEntryName(entry))
						continue;
					var sourcePath = Path.join([currentSource, entry]);
					var childRelative = current.relative + '/' + entry;
					if (FileSystem.isDirectory(sourcePath)) {
						if (!importPathIsWithin(sourcePath, root))
							return false;
						var key = importPathKey(sourcePath);
						var ancestors:Array<String> = current.ancestors;
						if (ancestors.indexOf(key) >= 0)
							continue;
						var childAncestors = ancestors.copy();
						childAncestors.push(key);
						stack.push({source:sourcePath, relative:childRelative,
							ancestors:childAncestors});
						continue;
					}
					// StageData constructs candidate paths with the literal ".json"
					// suffix. Keep exact lookup spellings so completeness matches Linux.
					if (!StringTools.endsWith(entry, '.json'))
						continue;
					if (!importPathIsWithin(sourcePath, root))
						return false;
					output.push({relative:childRelative, source:sourcePath});
				}
			}
		}
		return true;
	}

	/** Copy only selected-owner NMV stage JSON through the importer’s
	 * non-overwriting path. Read failures and cancellation remain explicit. */
	static function mergeNightmareVisionStageDataFiles(sourceRoot:String,
		destinationRoot:String, result:ImportAssetMergeResult,
		?skipPaths:Map<String, Bool>):Bool {
		if (sourceRoot == null || destinationRoot == null || result == null
			|| !FileSystem.isDirectory(sourceRoot))
			return false;
		var files:Array<Dynamic> = [];
		if (!collectNightmareVisionStageDataFiles(sourceRoot, files)) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not fully inspect Nightmare Vision stage metadata in ' + sourceRoot
				+ ' (read failure, cancellation, or path outside source root)');
			return false;
		}
		for (file in files) {
			if (importWorkCancelled())
				return false;
			if (file == null || file.source == null || file.relative == null || file.relative == ''
				|| !importPathIsWithin(file.source, sourceRoot)) {
				result.failed++;
				continue;
			}
			if (skipPaths != null && skipPaths.exists(importPathKey(file.source)))
				continue;
			var destination = Path.join([destinationRoot, file.relative]);
			if (!importPathIsWithin(destination, destinationRoot)) {
				result.failed++;
				continue;
			}
			copyImportFileNonOverwriting(file.source, destination, result);
		}
		return true;
	}

	/** Copy one selected NMV asset layer beneath its own namespace. The collector
	 * supplies canonical-root-checked relative paths; copying remains
	 * non-overwriting so installed owner edits and prior package owners win. */
	static function mergeNightmareVisionAssetFiles(sourceRoot:String,
		destinationRoot:String, result:ImportAssetMergeResult,
		?skipPaths:Map<String, Bool>,
		?mappedOwner:PreparedMappedAssetOwner):Bool {
		if (sourceRoot == null || destinationRoot == null || result == null
			|| !FileSystem.isDirectory(sourceRoot))
			return false;
		var collection = NightmareVisionAssetCollector.collect(sourceRoot,
			function() return importWorkCancelled());
		if (collection == null) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not inspect Nightmare Vision assets in ' + sourceRoot);
			return false;
		}
		if (collection.complete != true) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			var details = collection.errors == null ? '' : collection.errors.join('; ');
			result.errors.push('Could not fully inspect Nightmare Vision assets in ' + sourceRoot
				+ (details == '' ? '' : ' (' + details + ')'));
		}
		if (collection.files == null)
			return false;
		for (file in (cast collection.files:Array<Dynamic>)) {
			if (importWorkCancelled())
				return false;
			if (file == null || file.source == null || file.relative == null || file.relative == ''
				|| !importPathIsWithin(file.source, sourceRoot)) {
				result.failed++;
				continue;
			}
			if (skipPaths != null && skipPaths.exists(importPathKey(file.source)))
				continue;
			var destination = Path.join([destinationRoot, file.relative]);
			if (!importPathIsWithin(destination, destinationRoot)) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Nightmare Vision asset destination escapes its owner: ' + destination);
				continue;
			}
			if (mappedOwner != null
				&& skipMappedOwnerMediaFile(mappedOwner, file.source, destination)) {
				result.skipped++;
				continue;
			}
			copyImportFileNonOverwriting(file.source, destination, result);
		}
		return collection.complete == true;
	}

	/** Verify every source executable which the importer promises to copy has
	 * a destination-relative counterpart. On Linux the exact spelling matters;
	 * Windows' native lookup supplies its usual case-insensitive behavior. */
	static function compatScriptNamespaceHasExpectedFiles(sourceRoot:String, destination:String,
		?engine:String):Bool {
		if (sourceRoot == null || destination == null || !FileSystem.isDirectory(sourceRoot))
			return false;
		var contentRoot = findChildDirectory(sourceRoot, 'assets');
		if (contentRoot == null)
			contentRoot = sourceRoot;
		var roots:Array<{base:String, prefix:String}> = [{base:contentRoot, prefix:''}];
		var shared = findChildDirectory(contentRoot, 'shared');
		if (shared != null)
			roots.push({base:shared, prefix:'shared'});
		var expected:Array<Dynamic> = [];
		var budget:Array<Int> = [4096];
		var luaDependencyCount = 0;
		for (root in roots) {
			var luaDependencies = engine == ImportEngine.PSYCH
				? PsychLuaScriptDependencies.discover(root.base)
				: {files:[], complete:true};
			if (!luaDependencies.complete)
				return false;
			for (dependency in luaDependencies.files) {
				luaDependencyCount++;
				var relative = root.prefix == '' ? dependency.relative
					: root.prefix + '/' + dependency.relative;
				if (!isImportFile(Path.join([destination, relative])))
					return false;
			}
			if (engine == 'Modding Plus') {
				var images = findChildDirectory(root.base, 'images');
				var stages = findChildDirectory(images, 'custom_stages');
				if (stages != null) {
					var relative = root.prefix == '' ? 'images/custom_stages'
						: root.prefix + '/images/custom_stages';
					// Partial packages can ship a directly named stage script without
					// a registry. Verify registry files only when the donor supplies one.
					for (registryName in ['custom_stages.json', 'custom_stages.jsonc'])
						if (isImportFile(Path.join([stages, registryName]))
							&& !isImportFile(Path.join([destination, relative, registryName])))
							return false;
					collectCompatScriptFiles(stages, relative, false, expected, 0, budget);
				}
			}
			for (name in compatScriptTreeNames()) {
				var source = findChildDirectory(root.base, name);
				if (source != null)
					collectCompatScriptFiles(source, (root.prefix == '' ? name : root.prefix + '/' + name),
						false, expected, 0, budget, null, engine == ImportEngine.NIGHTMARE_VISION);
			}
			var dataRoot = findChildDirectory(root.base, 'data');
			// Registry data is a runtime dependency of scripted note styles too.
			var noteStyles = findChildDirectory(dataRoot, 'notestyles');
			if (noteStyles != null)
				collectCompatScriptFiles(noteStyles,
					(root.prefix == '' ? 'data/notestyles' : root.prefix + '/data/notestyles'),
					false, expected, 0, budget, ['.json', '.jsonc']);
			if (dataRoot != null)
				for (family in ['characters', 'stages', 'cutscenes', 'ui', 'events', 'notes', 'modules']) {
					var familyRoot = findChildDirectory(dataRoot, family);
					if (familyRoot == null)
						continue;
					var familyRelative = root.prefix == '' ? 'scripts/' + family
						: root.prefix + '/scripts/' + family;
					collectCompatScriptFiles(familyRoot, familyRelative, true, expected, 0, budget);
				}
			if (engine == ImportEngine.NIGHTMARE_VISION
				&& !collectNightmareVisionScriptFiles(root.base, root.prefix, expected))
				return false;
		}
		// StageData looks up files relative to the selected package root rather
		// than the generic shared-script overlay. Keep repair checks aligned with
		// the owner-scoped copy below.
		if (engine == ImportEngine.NIGHTMARE_VISION
			&& !collectNightmareVisionStageDataFiles(contentRoot, expected))
			return false;
		// Treat an exhausted bounded walk as incomplete rather than silently
		// accepting an unverified tail of a very large donor tree.
		if (budget[0] <= 0)
			return false;
		if (expected.length == 0 && luaDependencyCount == 0)
			return false;
		for (entry in expected) {
			if (entry == null || entry.relative == null || entry.relative == ''
				|| !isImportFile(Path.join([destination, entry.relative])))
				return false;
		}
		return true;
	}

	/** Return whether a donor root contains an executable tree that requires a
	 * per-song provenance manifest.  HXC data families are included because
	 * older FPS/Haxe packs keep character/stage modules below data/. */
	static function sourceHasCompatScriptTree(sourceRoot:String, ?engine:String):Bool {
		if (sourceRoot == null || !FileSystem.isDirectory(sourceRoot))
			return false;
		var nestedAssets = findChildDirectory(sourceRoot, 'assets');
		if (nestedAssets != null)
			sourceRoot = nestedAssets;
		var roots:Array<String> = [sourceRoot];
		var shared = findChildDirectory(sourceRoot, 'shared');
		if (shared != null)
			roots.push(shared);
		for (root in roots) {
			if (engine == ImportEngine.PSYCH
				&& PsychLuaScriptDependencies.discover(root).files.length > 0)
				return true;
			if (engine == 'Modding Plus') {
				var images = findChildDirectory(root, 'images');
				if (hasCompatScriptFile(findChildDirectory(images, 'custom_stages')))
					return true;
			}
			for (name in compatScriptTreeNames())
				if (hasCompatScriptFile(findChildDirectory(root, name), 0,
					engine == ImportEngine.NIGHTMARE_VISION))
					return true;
			var dataRoot = findChildDirectory(root, 'data');
			if (dataRoot != null)
				for (family in ['characters', 'stages', 'cutscenes', 'ui', 'events', 'notes', 'modules'])
					if (hasCompatScriptFile(findChildDirectory(dataRoot, family)))
						return true;
			if (engine == ImportEngine.NIGHTMARE_VISION) {
				var nmvFiles:Array<Dynamic> = [];
				if (!collectNightmareVisionScriptFiles(root, '', nmvFiles) || nmvFiles.length > 0)
					return true;
			}
		}
		return false;
	}

	static function compatScriptManifestPath(songData:SongImport):String {
		if (songData == null || songData.name == null)
			return null;
		var folder = importSongFolderName(songData);
		if (!validModuleName(folder))
			return null;
		var dataFolder = existingImportChild(Path.join(['assets', 'data']), folder);
		return existingImportChild(dataFolder, CompatScriptManifest.FILE_NAME);
	}

	/** Persist destination-only import identity and the bounded source
	 * fingerprint without storing the donor's filesystem path. Existing
	 * provenance is user data and stays untouched on subsequent repairs. */
	static function writeImportProvenance(songData:SongImport):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0};
		if (songData == null)
			return result;
		var folder = importSongFolderName(songData);
		if (!validModuleName(folder) || songData.sourceRoot == null
			|| StringTools.trim(songData.sourceRoot) == '') {
			result.failed++;
			return result;
		}
		var dataFolder = Path.join(['assets', 'data', folder]);
		var destination = Path.join([dataFolder, 'importProvenance.json']);
		var existingProvenance = existingImportChild(dataFolder, 'importProvenance.json');
		if (FileSystem.exists(existingProvenance)) {
			var provenanceUpdated = false;
			if (songData.engine == ImportEngine.NIGHTMARE_VISION
				&& songData.sourceSelectableDifficulties != null
				&& songData.sourceUnsupportedDifficulties != null) {
				var expectedOwner = CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
				var upgrade = NightmareVisionDifficultyCompat.upgradeProvenance(existingProvenance,
					Path.join(['tmp', 'nmv-import-provenance-backups']), expectedOwner, folder,
					songData.sourceSelectableDifficulties, songData.sourceUnsupportedDifficulties);
				if (upgrade.status == 'upgraded') {
					provenanceUpdated = true;
					if (upgrade.diagnostic != null)
						result.errors = [upgrade.diagnostic + ' (' + upgrade.backup + ')'];
					reportImportProgress('import-provenance-upgrade', existingProvenance, 0, 0, 1, 0, 0, 1);
				} else if (upgrade.status == 'failed') {
					result.failed++;
					if (upgrade.diagnostic != null)
						result.errors = [upgrade.diagnostic + (upgrade.backup == null ? '' : ' (' + upgrade.backup + ')')];
					reportImportProgress('import-provenance-upgrade', existingProvenance, 0, 0, 0, 0, 1, 1);
					return result;
				}
			}
			// Retained-source refreshes may correct package display metadata while
			// leaving the imported charts and owner identity untouched. In-memory
			// source roots resolve through ImportIO to the installed owner, so this
			// same check works when the donor has since been removed.
			var existingRecord:Dynamic = null;
			try {
				if (FileSystem.stat(existingProvenance).size <= 131072)
					existingRecord = haxe.Json.parse(File.getContent(existingProvenance));
			} catch (_:Dynamic) {}
			var expectedOwner = CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
			if (existingRecord != null && ImportSongOwnership.refreshDisplayMetadata(existingRecord,
				songData.engine, expectedOwner, folder, songData.sourceModName, songData.sourceModNameSource)) {
				try {
					File.saveContent(existingProvenance, CoolUtil.stringifyJson(existingRecord));
					provenanceUpdated = true;
				} catch (_:Dynamic) {
					result.failed++;
					result.errors = ['Could not refresh package display metadata in ' + existingProvenance];
					reportImportProgress('import-provenance-display-refresh', existingProvenance, 0, 0, 0, 0, 1, 1);
					return result;
				}
			}
			if (provenanceUpdated) {
				result.copied++;
				reportImportProgress('import-provenance-display-refresh', existingProvenance, 0, 0, 1, 0, 0, 1);
			} else {
				result.skipped++;
			}
			return result;
		}
		var sourceFolder:Dynamic = Reflect.field(songData, 'sourceFolder');
		if (sourceFolder == null || StringTools.trim(Std.string(sourceFolder)) == '')
			sourceFolder = songData.name;
		var provenance = ImportSongOwnership.provenance(Std.string(sourceFolder), songData.sourceRoot,
			songData.engine, folder, songData.display, songData.sourceModName, songData.sourceModNameSource);
		if (songData.engine == ImportEngine.NIGHTMARE_VISION
			&& songData.sourceSelectableDifficulties != null)
			Reflect.setField(provenance, 'sourceSelectableDifficulties',
				songData.sourceSelectableDifficulties.copy());
		if (songData.engine == ImportEngine.NIGHTMARE_VISION
			&& songData.sourceUnsupportedDifficulties != null)
			Reflect.setField(provenance, 'sourceUnsupportedDifficulties',
				songData.sourceUnsupportedDifficulties.copy());
		try {
			ensureDirectory(dataFolder);
			File.saveContent(destination, CoolUtil.stringifyJson(provenance));
			ImportSongOwnership.invalidateOwnerIdentityIndex();
			result.copied++;
			reportImportProgress('import-provenance', destination, 0, 0, 1, 0, 0, 1);
		} catch (_:Dynamic) {
			result.failed++;
			reportImportProgress('import-provenance', destination, 0, 0, 0, 0, 1, 1);
		}
		return result;
	}

	/** Detect a missing/partial provenance write without treating ordinary native
	 * imports as repairs.  The destination tree is checked only when the donor
	 * actually contains executable content, keeping the scan metadata bounded. */
	static function compatScriptManifestNeedsRepair(songData:SongImport):Bool {
		if (songData == null || songData.sourceRoot == null
			|| StringTools.trim(songData.sourceRoot) == '')
			return false;
		if (songData.engine == ImportEngine.CODENAME) {
			var expected = codenameRuntimeFiles(songData);
			var song:String = Reflect.field(songData, 'sourceFolder');
			var desired = CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
			var metadataPath = CodenameScriptPlan.metadataPath(desired, song);
			if (metadataPath != '' && !isImportFile(metadataPath)) return true;
			var cameraPath = CodenameScriptPlan.cameraMetadataPath(desired, song);
			if (cameraPath != '' && !isImportFile(cameraPath)) return true;
			if (expected.length == 0) return false;
			var manifestPath = compatScriptManifestPath(songData);
			if (manifestPath == null || !isImportFile(manifestPath)) return true;
			var manifest:CompatScriptManifestData;
			try manifest = CompatScriptManifest.parse(File.getContent(manifestPath))
			catch (_:Dynamic) return true;
			if (CompatScriptManifest.destinationKey(CompatScriptManifest.selectedRoot(manifest))
				!= CompatScriptManifest.destinationKey(desired)) return true;
			var ownerFound = false;
			for (root in manifest.roots)
				if (root != null && root.engine == ImportEngine.CODENAME
					&& CompatScriptManifest.destinationKey(root.path) == CompatScriptManifest.destinationKey(desired))
					ownerFound = true;
			if (!ownerFound) return true;
			for (entry in expected)
				if (!isImportFile(Path.join([desired, entry.relative]))) return true;
			var statePaths:Array<String> = [];
			for (entry in expected)
				if (StringTools.startsWith(entry.relative, 'data/states/')
					&& entry.relative.toLowerCase().endsWith('.hx')
					&& entry.family != 'transition') statePaths.push(entry.relative);
			if (expected.length > 0) {
				var catalogPath = CodenameModCatalog.PATH;
				if (!isImportFile(catalogPath)) return true;
				var parsedCatalog = CodenameModCatalog.parse(File.getContent(catalogPath));
				if (!parsedCatalog.valid) return true;
				var catalogOwner:Dynamic = null;
				for (entry in parsedCatalog.data.entries)
					if (CompatScriptManifest.destinationKey(entry.root)
						== CompatScriptManifest.destinationKey(desired)) catalogOwner = entry;
				if (catalogOwner == null) return true;
				for (statePath in statePaths)
					if (catalogOwner.states.indexOf(statePath) < 0) return true;
			}
			return false;
		}
		if (!sourceHasCompatScriptTree(songData.sourceRoot, songData.engine))
			return false;
		var manifestPath = compatScriptManifestPath(songData);
		if (manifestPath == null || !isImportFile(manifestPath))
			return true;
		var manifest:CompatScriptManifestData;
		try {
			manifest = CompatScriptManifest.parse(File.getContent(manifestPath));
		} catch (_:Dynamic) {
			return true;
		}
		var desired = CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
		var found = false;
		for (root in manifest.roots)
			if (root != null && CompatScriptManifest.destinationKey(root.path)
				== CompatScriptManifest.destinationKey(desired)) {
				found = true;
				if (!FileSystem.isDirectory(root.path) || !hasCompatScriptFile(root.path, 0,
					songData.engine == ImportEngine.NIGHTMARE_VISION))
					return true;
				}
		if (!found)
			return true;
		if (!compatScriptNamespaceHasExpectedFiles(songData.sourceRoot, desired, songData.engine))
			return true;
		// A manifest can retain roots from an interrupted or earlier duplicate
		// import.  Repair its explicit owner as well as its copied namespace so
		// the selected song candidate controls same-id HXC companions.
		return CompatScriptManifest.destinationKey(CompatScriptManifest.selectedRoot(manifest))
			!= CompatScriptManifest.destinationKey(desired);
	}

	static function validImportEntryName(name:String):Bool {
		return name != null && name != '' && name != '.' && name != '..'
			&& name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf(':') < 0
			&& name.indexOf('\u0000') < 0;
	}

	/**
	 * Copy a supported source tree recursively, never replacing a destination
	 * file.  skipPaths contains registry files already handled by a merge.
	 */
	static function mergeTreeNonOverwriting(source:String, destination:String, depth:Int,
		result:ImportAssetMergeResult, ?skipPaths:Map<String, Bool>,
		?skipMapped:(String->String->Bool)):Void {
		if (importWorkCancelled() || source == null || destination == null || depth > 10 || !FileSystem.isDirectory(source))
			return;
		if (importPathIsWithin(source, 'assets'))
			return;
		if (FileSystem.exists(destination) && !FileSystem.isDirectory(destination)) {
			result.skipped++;
			reportImportProgress('assets', destination, 0, 0, 0, 1, 0, 1);
			return;
		}
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(source));
		} catch (error:Dynamic) {
			result.failed++;
			reportImportProgress('assets', source, 0, 0, 0, 0, 1, 1);
			return;
		}
		if (!FileSystem.exists(destination))
			ensureDirectory(destination);
		for (entry in entries) {
			if (importWorkCancelled())
				return;
			if (!validImportEntryName(entry)) {
				result.failed++;
				reportImportProgress('assets', Path.join([source, entry]), 0, 0, 0, 0, 1, 1);
				continue;
			}
			var sourcePath = Path.join([source, entry]);
			if (skipPaths != null && skipPaths.exists(importPathKey(sourcePath)))
				continue;
			var destinationPath = existingImportChild(destination, entry);
			if (FileSystem.isDirectory(sourcePath)) {
				if (FileSystem.exists(destinationPath) && !FileSystem.isDirectory(destinationPath)) {
					result.skipped++;
					reportImportProgress('assets', destinationPath, 0, 0, 0, 1, 0, 1);
					continue;
				}
				mergeTreeNonOverwriting(sourcePath, destinationPath, depth + 1, result, skipPaths, skipMapped);
				continue;
			}
			if (importWorkCancelled())
				return;
			if (skipMapped != null && skipMapped(sourcePath, destinationPath)) {
				result.skipped++;
				continue;
			}
				if (FileSystem.exists(destinationPath)) {
					result.skipped++;
					reportImportProgress('assets', destinationPath, 0, 0, 0, 1, 0, 1);
				continue;
			}
			try {
				ensureDirectory(Path.directory(destinationPath));
				reportImportProgress('assets', destinationPath, 0, 0, 0, 0, 0);
				File.copy(sourcePath, destinationPath);
				result.copied++;
				reportImportProgress('assets', destinationPath, 0, 0, 1, 0, 0, 1);
			} catch (error:Dynamic) {
				result.failed++;
				reportImportProgress('assets', sourcePath, 0, 0, 0, 0, 1, 1);
			}
		}
	}

	/** Retain authored Psych translation inputs in the selected owner's actual
	 * data-library scopes. Only files below a library's data/ tree whose extension
	 * is .lang are copied; unrelated package data and arbitrary mods/ trees stay
	 * outside this runtime publication path. */
	static function mergePsychLanguageDataScopes(contentRoot:String, sourceRoot:String,
		destinationRoot:String, result:ImportAssetMergeResult, ?skipPaths:Map<String, Bool>,
		?languagePlan:PsychLanguagePublicationPlan):Void {
		if (languagePlan != null && (!languagePlan.legacyAllowed || languagePlan.blockAllLegacy))
			return;
		if (contentRoot == null || sourceRoot == null || destinationRoot == null || result == null
			|| !FileSystem.isDirectory(contentRoot) || !importPathIsWithin(contentRoot, sourceRoot)
			|| !importPathIsWithin(destinationRoot, CompatScriptManifest.ROOT_PREFIX))
			return;
		var scopes:Array<{root:String, prefix:String}> = [{root:contentRoot, prefix:''}];
		var shared = findChildDirectory(contentRoot, 'shared');
		if (shared != null && FileSystem.isDirectory(shared) && importPathIsWithin(shared, sourceRoot))
			scopes.push({root:shared, prefix:Path.withoutDirectory(shared)});
		var entries:Array<String> = [];
		try entries = FileSystem.readDirectory(contentRoot) catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not inspect Psych language library roots in ' + contentRoot + ': ' + Std.string(error));
			return;
		}
		entries.sort(Reflect.compare);
		if (entries.length > 4096) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Too many Psych language library roots in ' + contentRoot);
			return;
		}
		for (entry in entries) {
			if (importWorkCancelled()) return;
			if (!validImportEntryName(entry)) continue;
			var lower = entry.toLowerCase();
			if (lower == 'shared' || lower == 'mods' || lower == 'mod' || lower == 'imported_mods'
				|| lower == 'assets' || lower == 'content' || lower == 'source' || lower == 'scripts'
				|| lower == 'songs' || lower == 'data' || lower == 'images' || lower == 'sounds'
				|| lower == 'music' || lower == 'videos' || lower == 'fonts' || lower == 'shaders'
				|| lower == 'animations' || lower == 'plugins' || lower == 'events' || lower == 'characters'
				|| lower == 'stages')
				continue;
			var libraryRoot = Path.join([contentRoot, entry]);
			if (FileSystem.isDirectory(libraryRoot) && importPathIsWithin(libraryRoot, sourceRoot))
				scopes.push({root:libraryRoot, prefix:entry});
			// Some installed builds retain base-game libraries one level below
			// base_game/. Preserve that real lookup shape without descending into
			// unrelated package folders.
			if (lower == 'base_game' || lower == 'library') {
				var libraries:Array<String> = [];
				try libraries = FileSystem.readDirectory(libraryRoot) catch (_:Dynamic) continue;
				libraries.sort(Reflect.compare);
				if (libraries.length > 2048) {
					result.failed++;
					if (result.errors == null) result.errors = [];
					result.errors.push('Too many Psych language libraries in ' + libraryRoot);
					continue;
				}
				for (library in libraries) {
					if (importWorkCancelled()) return;
					if (!validImportEntryName(library)) continue;
					var child = Path.join([libraryRoot, library]);
					if (FileSystem.isDirectory(child) && importPathIsWithin(child, sourceRoot))
						scopes.push({root:child, prefix:entry + '/' + library});
				}
			}
		}
		var counters = {entries:0};
		for (scope in scopes) {
			if (importWorkCancelled()) return;
			if (!importPathIsWithin(scope.root, sourceRoot)) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Psych language scope escaped its authenticated source: ' + scope.root);
				continue;
			}
			var dataRoot = findChildDirectory(scope.root, 'data');
			if (dataRoot == null || !FileSystem.isDirectory(dataRoot)) continue;
			var dataName = Path.withoutDirectory(dataRoot);
			var destinationData = scope.prefix == ''
				? Path.join([destinationRoot, dataName])
				: Path.join([destinationRoot, scope.prefix, dataName]);
			mergePsychLanguageFiles(dataRoot, destinationData, sourceRoot, destinationRoot,
				result, counters, 0, skipPaths, languagePlan);
		}
	}

	/** Copy only .lang files from one already authenticated data/ subtree. */
	static function mergePsychLanguageFiles(source:String, destination:String, sourceRoot:String,
		destinationRoot:String, result:ImportAssetMergeResult, counters:Dynamic, depth:Int,
		?skipPaths:Map<String, Bool>, ?languagePlan:PsychLanguagePublicationPlan):Void {
		if (importWorkCancelled() || source == null || destination == null || depth > 10
			|| !FileSystem.isDirectory(source))
			return;
		if (!importPathIsWithin(source, sourceRoot) || !importPathIsWithin(destination, destinationRoot)) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Psych language copy escaped its authenticated owner scope: ' + source);
			return;
		}
		var entries:Array<String> = [];
		try entries = FileSystem.readDirectory(source) catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('Could not inspect Psych language files in ' + source + ': ' + Std.string(error));
			return;
		}
		entries.sort(Reflect.compare);
		for (entry in entries) {
			if (importWorkCancelled()) return;
			counters.entries++;
			if (counters.entries > 16384) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Psych language file entry limit reached below ' + sourceRoot);
				return;
			}
			if (!validImportEntryName(entry)) {
				result.failed++;
				continue;
			}
			var sourcePath = Path.join([source, entry]);
			if (!FileSystem.exists(sourcePath) || !importPathIsWithin(sourcePath, sourceRoot)) {
				result.failed++;
				continue;
			}
			var destinationPath = existingImportChild(destination, entry);
			if (FileSystem.isDirectory(sourcePath)) {
				if (FileSystem.exists(destinationPath) && !FileSystem.isDirectory(destinationPath)) {
					result.skipped++;
					continue;
				}
				mergePsychLanguageFiles(sourcePath, destinationPath, sourceRoot, destinationRoot,
					result, counters, depth + 1, skipPaths, languagePlan);
				continue;
			}
			if (!entry.toLowerCase().endsWith('.lang')) continue;
			if (skipPaths != null && skipPaths.exists(importPathKey(sourcePath))) continue;
			if (PsychLanguagePublisher.skipLegacy(languagePlan, sourcePath, destinationPath)) continue;
			if (FileSystem.exists(destinationPath)) {
				result.skipped++;
				continue;
			}
			if (!importPathIsWithin(destinationPath, destinationRoot)) {
				result.failed++;
				continue;
			}
			copyImportFileNonOverwriting(sourcePath, destinationPath, result);
		}
	}

	/**
	 * FPS Plus and older Haxe packs keep HXC character/stage modules under
	 * data/, whereas the compatibility runtime discovers executable HXC families
	 * below a source namespace's scripts/ tree.  Copy only those executable
	 * definitions there; charts, JSON and donor media remain handled by their
	 * normal import paths.  The donor is never rewritten and existing destination
	 * files remain authoritative.
	 */
	static function mergeHxcScriptTree(source:String, destination:String, depth:Int,
		result:ImportAssetMergeResult, ?skipPaths:Map<String, Bool>):Void {
		if (importWorkCancelled() || source == null || destination == null || depth > 10
			|| !FileSystem.isDirectory(source))
			return;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(source));
		} catch (_:Dynamic) {
			result.failed++;
			return;
		}
		if (!FileSystem.exists(destination))
			ensureDirectory(destination);
		for (entry in entries) {
			if (importWorkCancelled() || !validImportEntryName(entry))
				continue;
			var sourcePath = Path.join([source, entry]);
			if (skipPaths != null && skipPaths.exists(importPathKey(sourcePath)))
				continue;
			if (FileSystem.isDirectory(sourcePath)) {
				mergeHxcScriptTree(sourcePath, Path.join([destination, entry]), depth + 1, result, skipPaths);
				continue;
			}
			if (!entry.toLowerCase().endsWith('.hxc'))
				continue;
			var destinationPath = existingImportChild(destination, entry);
			if (FileSystem.exists(destinationPath)) {
				result.skipped++;
				reportImportProgress('assets', destinationPath, 0, 0, 0, 1, 0, 1);
				continue;
			}
			try {
				ensureDirectory(Path.directory(destinationPath));
				reportImportProgress('assets', destinationPath, 0, 0, 0, 0, 0);
				File.copy(sourcePath, destinationPath);
				result.copied++;
				reportImportProgress('assets', destinationPath, 0, 0, 1, 0, 0, 1);
			} catch (_:Dynamic) {
				result.failed++;
				reportImportProgress('assets', sourcePath, 0, 0, 0, 0, 1, 1);
			}
		}
	}

	static function registryArrayContains(items:Array<Dynamic>, value:Dynamic):Bool {
		var valueName:Dynamic = value == null ? null : Reflect.field(value, 'name');
		var valueKey = valueName == null ? '' : StringTools.trim(Std.string(valueName)).toLowerCase();
		for (item in items) {
			if (item == null)
				continue;
			var itemName:Dynamic = Reflect.field(item, 'name');
			if (valueKey != '' && itemName != null
				&& StringTools.trim(Std.string(itemName)).toLowerCase() == valueKey)
				return true;
			if (valueKey == '' && CoolUtil.stringifyJson(item) == CoolUtil.stringifyJson(value))
				return true;
		}
		return false;
	}

	/** Recover the legacy simple-map custom stage registry used by some Modding
	 * Plus donors.  Several releases omitted commas between adjacent quoted
	 * entries, even though the current engine expects JSON.  Keep this repair
	 * limited to that registry and require every parsed value to be a string. */
	static function isImportStageMapRegistry(path:String):Bool {
		if (path == null)
			return false;
		var key = StringTools.replace(Path.normalize(path), '\\', '/').toLowerCase();
		return StringTools.endsWith(key, '/images/custom_stages/custom_stages.json');
	}

	static function recoverImportStageMapRegistry(raw:String):Dynamic {
		if (raw == null)
			return null;
		// Insert only a missing separator between a string value and the next
		// quoted key, then remove an optional trailing comma before the object end.
		var repaired = new EReg('("(?:\\\\.|[^"\\\\])*")([\\t\\r\\n ]*)("(?:\\\\.|[^"\\\\])*"\\s*:)', 'g')
			.replace(raw, '$1,$2$3');
		var closeBrace = String.fromCharCode(125);
		repaired = new EReg(',\\s*\\x7d', 'g').replace(repaired, closeBrace);
		try {
			var parsed:Dynamic = CoolUtil.parseJson(repaired);
			if (parsed == null || Std.isOfType(parsed, Array) || Std.isOfType(parsed, String)
				|| Std.isOfType(parsed, Bool) || Std.isOfType(parsed, Int) || Std.isOfType(parsed, Float))
				return null;
			for (field in Reflect.fields(parsed))
				if (!Std.isOfType(Reflect.field(parsed, field), String))
					return null;
			return parsed;
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function parseImportRegistryJson(raw:String, path:String):Dynamic {
		try {
			return CoolUtil.parseJson(raw);
		} catch (_:Dynamic) {
			return isImportStageMapRegistry(path) ? recoverImportStageMapRegistry(raw) : null;
		}
	}

	/** Merge object/array registries by missing keys/items only. */
	static function mergeObjectRegistry(sourcePath:String, destinationPath:String):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0};
		if (sourcePath == null || destinationPath == null || !isImportFile(sourcePath)
			|| importPathKey(sourcePath) == importPathKey(destinationPath))
			return result;
		var sourceData:Dynamic;
		var destinationData:Dynamic;
		try {
			sourceData = parseImportRegistryJson(File.getContent(sourcePath), sourcePath);
			destinationData = FileSystem.exists(destinationPath)
				? parseImportRegistryJson(File.getContent(destinationPath), destinationPath) : null;
		} catch (error:Dynamic) {
			result.failed++;
			return result;
		}
		if (sourceData == null) {
			result.failed++;
			return result;
		}
		if (destinationData == null) {
			try {
				ensureDirectory(Path.directory(destinationPath));
				if (isImportStageMapRegistry(sourcePath))
					File.saveContent(destinationPath, CoolUtil.stringifyJson(sourceData));
				else
					File.copy(sourcePath, destinationPath);
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
			}
			return result;
		}

		var changed = false;
		if (Std.isOfType(sourceData, Array) && Std.isOfType(destinationData, Array)) {
			var sourceArray:Array<Dynamic> = cast sourceData;
			var destinationArray:Array<Dynamic> = cast destinationData;
			for (item in sourceArray) {
				if (registryArrayContains(destinationArray, item))
					result.skipped++;
				else {
					destinationArray.push(item);
					changed = true;
				}
			}
		} else {
			for (field in Reflect.fields(sourceData)) {
				var sourceValue:Dynamic = Reflect.field(sourceData, field);
				if (!Reflect.hasField(destinationData, field)) {
					Reflect.setField(destinationData, field, Reflect.field(sourceData, field));
					changed = true;
				} else {
					var destinationValue:Dynamic = Reflect.field(destinationData, field);
					if (Std.isOfType(sourceValue, Array) && Std.isOfType(destinationValue, Array)) {
						var sourceItems:Array<Dynamic> = cast sourceValue;
						var destinationItems:Array<Dynamic> = cast destinationValue;
						for (item in sourceItems) {
							if (registryArrayContains(destinationItems, item))
								result.skipped++;
							else {
								destinationItems.push(item);
								changed = true;
							}
						}
					} else
						result.skipped++;
				}
			}
		}
		if (!changed) {
			if (result.skipped == 0)
				result.skipped++;
			return result;
		}
		try {
			ensureDirectory(Path.directory(destinationPath));
			File.saveContent(destinationPath, CoolUtil.stringifyJson(destinationData));
			result.copied++;
		} catch (error:Dynamic) {
			result.failed++;
		}
		return result;
	}

	/** Compare parsed JSON values independent of object property order. Arrays
	 * remain ordered, and JSON integer/float spellings compare as the same number. */
	static function importJsonValuesEqual(first:Dynamic, second:Dynamic):Bool {
		if (first == null || second == null) return first == second;
		var firstArray = Std.isOfType(first, Array);
		var secondArray = Std.isOfType(second, Array);
		if (firstArray || secondArray) {
			if (!firstArray || !secondArray) return false;
			var firstItems:Array<Dynamic> = cast first;
			var secondItems:Array<Dynamic> = cast second;
			if (firstItems.length != secondItems.length) return false;
			for (index in 0...firstItems.length)
				if (!importJsonValuesEqual(firstItems[index], secondItems[index])) return false;
			return true;
		}
		var firstType = Type.typeof(first);
		var secondType = Type.typeof(second);
		var firstNumber = firstType == TInt || firstType == TFloat;
		var secondNumber = secondType == TInt || secondType == TFloat;
		if (firstNumber || secondNumber)
			return firstNumber && secondNumber
				&& Std.parseFloat(Std.string(first)) == Std.parseFloat(Std.string(second));
		if (firstType == TObject || secondType == TObject) {
			if (firstType != TObject || secondType != TObject) return false;
			var firstFields = Reflect.fields(first);
			var secondFields = Reflect.fields(second);
			if (firstFields.length != secondFields.length) return false;
			for (field in firstFields)
				if (!Reflect.hasField(second, field)
					|| !importJsonValuesEqual(Reflect.field(first, field), Reflect.field(second, field))) return false;
			return true;
		}
		return firstType == secondType && first == second;
	}

	/** Merge the already-resolved donor registry.  Do not recompute it from
	 * sourceRoot: shared-layout packs can keep the registry under `shared`,
	 * while charts/audio and the caller's root remain elsewhere. */
	static function mergeFreeplayRegistry(sourcePath:String, importedNames:Map<String, Bool>):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0};
		var destinationPath = freeplayRegistryPath();
		if (!isImportFile(sourcePath) || importPathKey(sourcePath) == importPathKey(destinationPath))
			return result;
		var sourceData:Array<Dynamic>;
		var destinationData:Array<Dynamic>;
		var originalDestinationData:Array<Dynamic>;
		try {
			sourceData = cast CoolUtil.parseJson(File.getContent(sourcePath));
			var destinationContents = FileSystem.exists(destinationPath)
				? File.getContent(destinationPath) : '[]';
			destinationData = cast CoolUtil.parseJson(destinationContents);
			originalDestinationData = cast CoolUtil.parseJson(destinationContents);
		} catch (error:Dynamic) {
			result.failed++;
			return result;
		}
		if (sourceData == null || destinationData == null) {
			result.failed++;
			return result;
		}
		var changed = false;
		for (sourceCategory in sourceData) {
			if (sourceCategory == null || sourceCategory.songs == null || sourceCategory.name == null)
				continue;
			var sourceCategoryName = StringTools.trim(Std.string(sourceCategory.name));
			if (sourceCategoryName == '')
				continue;
			var categoryName = normalizeImportedCategory(sourceCategoryName);
			var destinationCategory:Dynamic = null;
			for (candidate in destinationData) {
				if (candidate != null && StringTools.trim(Std.string(candidate.name)).toLowerCase() == categoryName.toLowerCase()) {
					destinationCategory = candidate;
					break;
				}
			}
			var sourceSongs:Array<Dynamic> = cast sourceCategory.songs;
			var eligibleSongs:Array<Dynamic> = [];
			for (sourceSong in sourceSongs) {
				if (sourceSong == null || sourceSong.name == null)
					continue;
				var songName = StringTools.trim(Std.string(sourceSong.name));
				if (importedNames != null && !importedNames.exists(songName.toLowerCase()))
					continue;
				eligibleSongs.push(sourceSong);
			}
			if (eligibleSongs.length == 0)
				continue;
			// importSong creates a fallback entry in the Imported category.  If
			// the source registry carries a real category, remove every such
			// fallback and add the source entry exactly once.  Existing entries in
			// another user category are retained, but the source entry is not added
			// a second time.
			var filteredSongs:Array<Dynamic> = [];
			for (sourceSong in eligibleSongs) {
				var sourceSongName = StringTools.trim(Std.string(sourceSong.name));
				var sourceSongKey = sourceSongName.toLowerCase();
				var duplicateOutsideImported = false;
				for (candidateCategory in destinationData) {
					if (candidateCategory == null || candidateCategory.songs == null)
						continue;
					var candidateCategoryName = StringTools.trim(Std.string(candidateCategory.name)).toLowerCase();
					var candidateSongs:Array<Dynamic> = cast candidateCategory.songs;
					var index = 0;
					while (index < candidateSongs.length) {
						var candidateSong = candidateSongs[index];
						var candidateSongKey = candidateSong == null || candidateSong.name == null
							? '' : StringTools.trim(Std.string(candidateSong.name)).toLowerCase();
						if (candidateSongKey != sourceSongKey) {
							index++;
							continue;
						}
						// Earlier imports could already have copied the donor's
						// Base Game row. Move only the selected imported song into
						// Imported; the donor's unrelated base-game songs are filtered
						// out by importedNames before this pass.
						if (sourceCategoryName.toLowerCase() == 'base game'
							&& categoryName.toLowerCase() == 'imported' && candidateCategoryName == 'base game') {
							candidateSongs.splice(index, 1);
							changed = true;
							continue;
						}
						if (candidateCategoryName == 'imported' && categoryName.toLowerCase() != 'imported') {
							candidateSongs.splice(index, 1);
							changed = true;
							continue;
						}
						duplicateOutsideImported = true;
						index++;
					}
				}
				if (duplicateOutsideImported)
					result.skipped++;
				else
					filteredSongs.push(sourceSong);
			}
			eligibleSongs = filteredSongs;
			if (eligibleSongs.length == 0)
				continue;
			if (destinationCategory == null) {
				destinationCategory = {name: categoryName, songs: []};
				destinationData.push(destinationCategory);
				changed = true;
			}
			if (destinationCategory.songs == null)
				destinationCategory.songs = [];
			var destinationSongs:Array<Dynamic> = cast destinationCategory.songs;
			for (sourceSong in eligibleSongs) {
				var songName = StringTools.trim(Std.string(sourceSong.name));
				var duplicate = false;
				for (destinationSong in destinationSongs) {
					if (destinationSong != null && StringTools.trim(Std.string(destinationSong.name)).toLowerCase() == songName.toLowerCase()) {
						duplicate = true;
						break;
					}
				}
				if (!duplicate) {
					destinationSongs.push(sourceSong);
					changed = true;
				} else
					result.skipped++;
			}
		}
		if (changed && !importJsonValuesEqual(originalDestinationData, destinationData)) {
			try {
				ensureDirectory(Path.directory(destinationPath));
				File.saveContent(destinationPath, CoolUtil.stringifyJson(destinationData));
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
			}
		} else if (result.skipped == 0) {
			result.skipped++;
		}
		return result;
	}

	/** Merge story weeks/songs without replacing an existing week definition. */
	static function mergeStoryRegistry(sourceRoot:String, importedNames:Map<String, Bool>):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0};
		var sourcePath = Path.join([sourceRoot, 'data', 'storySonglist.json']);
		var destinationPath = 'assets/data/storySonglist.json';
		if (!isImportFile(sourcePath) || importPathKey(sourcePath) == importPathKey(destinationPath))
			return result;
		var sourceData:Dynamic;
		var destinationData:Dynamic;
		try {
			sourceData = CoolUtil.parseJson(File.getContent(sourcePath));
			destinationData = FileSystem.exists(destinationPath)
				? CoolUtil.parseJson(File.getContent(destinationPath)) : null;
		} catch (error:Dynamic) {
			result.failed++;
			return result;
		}
		if (sourceData == null) {
			result.failed++;
			return result;
		}

		var storyEntryKey = function(value:Dynamic):String {
			var songName:Dynamic = value;
			if (value != null && !Std.isOfType(value, String)) {
				var named:Dynamic = Reflect.field(value, 'name');
				if (named != null)
					songName = named;
			}
			return StringTools.trim(Std.string(songName)).toLowerCase();
		};
		var isImportedSong = function(value:Dynamic):Bool {
			var songKey = storyEntryKey(value);
			return songKey != '' && songKey != 'null' && (importedNames == null || importedNames.exists(songKey));
		};

		// Modern story registries use weeks with named song objects.  Filter a
		// source-only copy just as strictly as an in-place merge.
		if (Reflect.hasField(sourceData, 'weeks')) {
			var sourceWeeks:Array<Dynamic> = cast Reflect.field(sourceData, 'weeks');
			if (sourceWeeks == null)
				return result;
			var filteredWeeks:Array<Dynamic> = [];
			for (sourceWeek in sourceWeeks) {
				if (sourceWeek == null || sourceWeek.songs == null)
					continue;
				var eligibleSongs:Array<Dynamic> = [];
				for (song in (cast sourceWeek.songs:Array<Dynamic>))
					if (isImportedSong(song))
						eligibleSongs.push(song);
				if (eligibleSongs.length > 0) {
					var filteredWeek = Reflect.copy(sourceWeek);
					filteredWeek.songs = eligibleSongs;
					filteredWeeks.push(filteredWeek);
				}
			}
			if (destinationData == null) {
				if (filteredWeeks.length == 0)
					return result;
				var filteredData = Reflect.copy(sourceData);
				filteredData.weeks = filteredWeeks;
				try {
					ensureDirectory(Path.directory(destinationPath));
					File.saveContent(destinationPath, CoolUtil.stringifyJson(filteredData));
					result.copied++;
				} catch (error:Dynamic) {
					result.failed++;
				}
				return result;
			}
			if (!Reflect.hasField(destinationData, 'weeks'))
				return result;
			var destinationWeeks:Array<Dynamic> = cast Reflect.field(destinationData, 'weeks');
			if (destinationWeeks == null)
				return result;
			var changed = false;
			for (sourceWeek in filteredWeeks) {
				var weekName = sourceWeek.name == null ? '' : StringTools.trim(Std.string(sourceWeek.name));
				var destinationWeek:Dynamic = null;
				for (candidate in destinationWeeks) {
					if (candidate != null && candidate.name != null
						&& StringTools.trim(Std.string(candidate.name)).toLowerCase() == weekName.toLowerCase()) {
						destinationWeek = candidate;
						break;
					}
				}
				if (destinationWeek == null) {
					destinationWeek = Reflect.copy(sourceWeek);
					destinationWeeks.push(destinationWeek);
					changed = true;
					continue;
				}
				if (destinationWeek.songs == null)
					destinationWeek.songs = [];
				var destinationSongs:Array<Dynamic> = cast destinationWeek.songs;
				for (song in (cast sourceWeek.songs:Array<Dynamic>)) {
					var duplicate = false;
					var songKey = storyEntryKey(song);
					for (existing in destinationSongs) {
						var existingKey = storyEntryKey(existing);
						if (existingKey == songKey) {
							duplicate = true;
							break;
						}
					}
					if (duplicate)
						result.skipped++;
					else {
						destinationSongs.push(song);
						changed = true;
					}
				}
			}
			if (changed) {
				try {
					ensureDirectory(Path.directory(destinationPath));
					File.saveContent(destinationPath, CoolUtil.stringifyJson(destinationData));
					result.copied++;
				} catch (error:Dynamic) {
					result.failed++;
				}
			} else if (result.skipped == 0)
				result.skipped++;
			return result;
		}

		// The shipped story registry uses parallel `songs`, `weekNames` and
		// `characters` arrays.  Merge only rows containing newly imported songs.
		if (!Reflect.hasField(sourceData, 'songs'))
			return result;
		var sourceRows:Array<Dynamic> = cast Reflect.field(sourceData, 'songs');
		if (sourceRows == null)
			return result;
		var filteredRows:Array<Dynamic> = [];
		var sourceRowIndexes:Array<Int> = [];
		for (rowIndex in 0...sourceRows.length) {
			var row:Dynamic = sourceRows[rowIndex];
			if (row == null || !Std.isOfType(row, Array))
				continue;
			var rowArray:Array<Dynamic> = cast row;
			var filteredRow:Array<Dynamic> = [];
			if (rowArray.length > 0)
				filteredRow.push(rowArray[0]);
			for (songIndex in 1...rowArray.length)
				if (isImportedSong(rowArray[songIndex]))
					filteredRow.push(rowArray[songIndex]);
			if (filteredRow.length > 1) {
				filteredRows.push(filteredRow);
				sourceRowIndexes.push(rowIndex);
			}
		}
		if (filteredRows.length == 0)
			return result;
		if (destinationData == null) {
			var filteredData = Reflect.copy(sourceData);
			filteredData.songs = filteredRows;
			for (field in ['weekNames', 'characters']) {
				if (!Reflect.hasField(sourceData, field))
					continue;
				var sourceParallel:Array<Dynamic> = cast Reflect.field(sourceData, field);
				if (sourceParallel == null)
					continue;
				var filteredParallel:Array<Dynamic> = [];
				for (rowIndex in sourceRowIndexes) {
					if (rowIndex < sourceParallel.length)
						filteredParallel.push(sourceParallel[rowIndex]);
				}
				Reflect.setField(filteredData, field, filteredParallel);
			}
			try {
				ensureDirectory(Path.directory(destinationPath));
				File.saveContent(destinationPath, CoolUtil.stringifyJson(filteredData));
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
			}
			return result;
		}
		if (!Reflect.hasField(destinationData, 'songs'))
			return result;
		var destinationRows:Array<Dynamic> = cast Reflect.field(destinationData, 'songs');
		if (destinationRows == null)
			return result;
		var changed = false;
		for (sourceRow in filteredRows) {
			var rowName = sourceRow.length == 0 ? '' : StringTools.trim(Std.string(sourceRow[0])).toLowerCase();
			var destinationRow:Array<Dynamic> = null;
			for (candidate in destinationRows) {
				if (candidate != null && Std.isOfType(candidate, Array) && candidate.length > 0
					&& StringTools.trim(Std.string(candidate[0])).toLowerCase() == rowName) {
					destinationRow = cast candidate;
					break;
				}
			}
			if (destinationRow == null) {
				destinationRows.push(sourceRow);
				changed = true;
				continue;
			}
			for (songIndex in 1...sourceRow.length) {
				var songKey = StringTools.trim(Std.string(sourceRow[songIndex])).toLowerCase();
				var duplicate = false;
				for (existingIndex in 1...destinationRow.length)
					if (StringTools.trim(Std.string(destinationRow[existingIndex])).toLowerCase() == songKey) {
						duplicate = true;
						break;
					}
				if (duplicate)
					result.skipped++;
				else {
					destinationRow.push(sourceRow[songIndex]);
					changed = true;
				}
			}
		}
		if (changed) {
			try {
				ensureDirectory(Path.directory(destinationPath));
				File.saveContent(destinationPath, CoolUtil.stringifyJson(destinationData));
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
			}
		} else if (result.skipped == 0)
			result.skipped++;
		return result;
	}

	/**
	 * Return ordinary supported asset trees.  Discovery deliberately avoids
	 * walking donor media libraries, but once the user selects an assets root the
	 * copy phase imports generic images, music, videos, sounds, scripts, fonts,
	 * shaders and future top-level asset folders.  data/songs are handled per
	 * imported song below so skipped songs remain untouched.
	 */
	static function supportedAssetTrees(sourceRoot:String):Array<String> {
		// Copy every ordinary asset subtree from a selected assets root.  `data`
		// and `songs` are handled per imported song below so an existing song is
		// never modified by a broad tree merge.  The discovery walk avoids music,
		// while this user-requested copy phase includes it like every other asset.
		var trees:Array<String> = [];
		var excluded:Map<String, Bool> = new Map<String, Bool>();
		for (name in ['data', 'songs', 'scripts', 'stages', 'custom_events', 'custom_notetypes', 'plugins',
			'.git', '.tools', '.haxelib', 'node_modules', 'bin', 'cache'])
			excluded.set(name, true);
		try {
			for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(sourceRoot))) {
				if (!validImportEntryName(entry) || excluded.exists(entry.toLowerCase()))
					continue;
				var child = Path.join([sourceRoot, entry]);
				if (FileSystem.isDirectory(child))
					trees.push(entry);
			}
		} catch (error:Dynamic) {
			// A missing/locked optional tree should not abort other imports.
		}
		return trees;
	}

	/** Merge an explicitly mapped project asset root such as
	 * assets/shared -> assets/shared. Ordinary files keep that logical prefix;
	 * executable foreign-engine trees remain isolated by mergeCompatScriptTrees
	 * under the selected project owner's namespace. */
	static function mergeMappedAssetRoot(sourceRoot:String, destinationPrefix:String,
		scriptSourceRoot:String, scriptEngine:String,
		?ownerPlan:PreparedMappedAssetOwner):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
		if (sourceRoot == null || !FileSystem.isDirectory(sourceRoot))
			return result;
		var prefix = StringTools.replace(StringTools.trim(destinationPrefix == null ? '' : destinationPrefix), '\\', '/');
		if (prefix == '' || StringTools.startsWith(prefix, '/') || prefix.indexOf(':') >= 0) {
			result.failed++;
			result.errors.push('Invalid mapped asset destination prefix: ' + prefix);
			return result;
		}
		for (part in prefix.split('/'))
			if (part == '' || part == '.' || part == '..') {
				result.failed++;
				result.errors.push('Invalid mapped asset destination prefix: ' + prefix);
				return result;
			}
		var destinationRoot = Path.join(['assets', prefix]);
		var skipMapped = function(source:String, destination:String):Bool
			return skipMappedRawFile(ownerPlan, source, destination);
		var scriptTrees:Map<String, Bool> = new Map<String, Bool>();
		for (name in compatScriptTreeNames())
			scriptTrees.set(name.toLowerCase(), true);
		var entries:Array<String> = [];
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(sourceRoot));
			entries.sort(Reflect.compare);
		} catch (error:Dynamic) {
			result.failed++;
			result.errors.push('Could not inspect mapped asset root: ' + sourceRoot + ' (' + Std.string(error) + ')');
			return result;
		}
		for (entry in entries) {
			if (importWorkCancelled())
				return result;
			if (!validImportEntryName(entry)) {
				result.failed++;
				continue;
			}
			var source = Path.join([sourceRoot, entry]);
			if (FileSystem.isDirectory(source) && scriptTrees.exists(entry.toLowerCase()))
				continue;
			var destination = Path.join([destinationRoot, entry]);
			if (FileSystem.isDirectory(source))
				mergeTreeNonOverwriting(source, destination, 0, result, null, skipMapped);
			else if (skipMapped(source, destination))
				result.skipped++;
			else
				copyImportFileNonOverwriting(source, destination, result);
		}
		mergeCompatScriptTrees(sourceRoot, scriptSourceRoot, scriptEngine, result, null, null, null,
			ownerPlan == null ? null : ownerPlan.plan,
			ownerPlan == null ? '' : ownerPlan.scope);
		return result;
	}

	/** Convert Psych character definitions into the destination custom-char
	 * format when a Psych root is imported.  The converter is intentionally
	 * best-effort: packs often contain optional character JSON without its atlas
	 * (or use a format this old engine cannot represent), and that should not
	 * invalidate otherwise importable songs. */
	static function importPsychCharacters(sourceRoot:String, destinationAssetRoot:String = 'assets'):Void {
		if (sourceRoot == null || !FileSystem.isDirectory(sourceRoot))
			return;
		var scopedAssetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (scopedAssetRoot == '')
			return;
		var roots:Array<{path:String, shared:Bool}> = [{path:sourceRoot, shared:false}];
		var sharedRoot = findChildDirectory(sourceRoot, 'shared');
		if (sharedRoot != null)
			roots.push({path:sharedRoot, shared:true});
		try ensureDirectory(Path.join(['assets', 'images', 'custom_chars'])) catch (_:Dynamic) {}
		if (scopedAssetRoot != 'assets')
			try ensureDirectory(Path.join([scopedAssetRoot, 'images', 'custom_chars'])) catch (_:Dynamic) {}
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (rootInfo in roots) {
			var psychRoot = rootInfo.path;
			var charactersRoot = findChildDirectory(psychRoot, 'characters');
			if (charactersRoot == null)
				continue;
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(charactersRoot));
			} catch (_:Dynamic) {
				continue;
			}
			for (entry in entries) {
				if (importWorkCancelled() || !entry.toLowerCase().endsWith('.json'))
					continue;
				var name = entry.substr(0, entry.length - 5);
				var key = name.toLowerCase();
				if (seen.exists(key))
					continue;
				if (scopedAssetRoot != 'assets')
					preservePsychCharacterJson(Path.join([charactersRoot, entry]), scopedAssetRoot,
						rootInfo.shared);
				try {
					var creation = psychCharDecode(psychRoot, name);
					var animateFolder = psychAnimateFolder(psychRoot, creation.charjson);
					try materializePsychCharacter(creation, animateFolder, 'assets') catch (_:Dynamic) {}
					if (scopedAssetRoot != 'assets')
						try materializePsychCharacter(creation, animateFolder, scopedAssetRoot) catch (_:Dynamic) {}
					seen.set(key, true);
				} catch (error:Dynamic) {
					// Missing atlas/XML/icon data is an optional dependency warning;
					// chart/audio import remains useful without it.
				}
			}
		}
	}

	/** Keep the selected Psych owner's source JSON beside its original character
	 * tree. Position is consumed from this file at runtime, and preserving the
	 * original JSON also retains camera metadata for future compatibility work.
	 * The converted native atlas alone does not carry these fields. Existing
	 * owner files win on re-import. */
	static function preservePsychCharacterJson(sourcePath:String, destinationAssetRoot:String,
		shared:Bool):Void {
		#if sys
		if (!validImportPath(sourcePath))
			return;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '' || assetRoot == 'assets')
			return;
		var fileName = Path.withoutDirectory(sourcePath);
		if (fileName == null || !fileName.toLowerCase().endsWith('.json'))
			return;
		var characterName = fileName.substr(0, fileName.length - 5);
		if (!validModuleName(characterName))
			return;
		var destination = shared
			? Path.join([assetRoot, 'shared', 'characters', fileName])
			: Path.join([assetRoot, 'characters', fileName]);
		if (FileSystem.exists(destination))
			return;
		try {
			ensureDirectory(Path.directory(destination));
			if (!FileSystem.exists(destination))
				File.copy(sourcePath, destination);
		} catch (_:Dynamic) {
			// Character JSON is optional metadata; keep importing playable media.
		}
		#end
	}

	/** Only native relative asset roots and the generated import namespace are valid destinations. */
	static function psychDestinationAssetRoot(value:String):String {
		var clean = Path.normalize(StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/'));
		if (clean == '' || clean == '.')
			return 'assets';
		if (clean == 'assets')
			return clean;
		var prefix = CompatScriptManifest.ROOT_PREFIX + '/';
		if (!StringTools.startsWith(clean, prefix))
			return '';
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				return '';
		return clean;
	}

	/** Convert the same Psych definition into legacy global and owner-scoped assets. */
	static function materializePsychCharacter(creation:CharCreation, animateFolder:String,
		destinationAssetRoot:String):Void {
		if (creation == null || !validModuleName(creation.name))
			return;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '')
			return;
		var destination = Path.join([assetRoot, 'images', 'custom_chars', creation.name]);
		if (FileSystem.exists(destination)) {
			if (hasNativeCharacterFiles(creation.name, assetRoot)) {
				ensurePsychCharacterRegistryEntry(creation.name, creation.charjson, assetRoot,
					animateFolder != null);
				return;
			}
			if (!FileSystem.isDirectory(destination))
				return;
			var entries:Array<String> = null;
			try entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(destination)) catch (_:Dynamic) {}
			// Empty leftovers are safe to retry. Preserve every non-empty partial
			// import so a later owner never overwrites user or donor files.
			if (entries == null || entries.length > 0)
				return;
		}
		if (animateFolder != null)
			psychToDisAnimateChar(creation, animateFolder, assetRoot);
		else
			psychToDisChar(creation, assetRoot);
	}

	/**
		Return true when a previously imported Psych character has enough native
		files to be repaired without touching its destination bytes.  A failed
		conversion may leave an empty directory behind; that directory alone must
		not cause a registry entry to be advertised as playable.
	*/
	static function hasNativeCharacterFiles(name:String, destinationAssetRoot:String = 'assets'):Bool {
		#if sys
		if (!validModuleName(name))
			return false;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '')
			return false;
		var folder = Path.join([assetRoot, 'images', 'custom_chars', name]);
		if (!FileSystem.isDirectory(folder))
			return false;
		return (FileSystem.exists(Path.join([folder, 'char.png']))
			&& FileSystem.exists(Path.join([folder, 'char.xml'])))
			|| FileSystem.exists(Path.join([assetRoot, 'images', 'custom_chars', name + '.hscript']));
		#else
		return false;
		#end
	}

	/**
		Repair the native character registry for an already-materialized Psych
		character.  This deliberately does not run CoolUtil.formatCustomChars():
		that legacy formatter rewrites every entry and can discard newer metadata
		from unrelated imported engines.  Only the missing key is added.
	*/
	static function ensurePsychCharacterRegistryEntry(name:String, charJson:Dynamic,
		destinationAssetRoot:String = 'assets', legacyAnimate:Bool = false):Bool {
		#if sys
		if (!validModuleName(name) || charJson == null)
			return false;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '')
			return false;
		var registryRoot = Path.join([assetRoot, 'images', 'custom_chars']);
		var path = chooseVSliceRegistry(Path.join([registryRoot, 'custom_chars.jsonc']),
			Path.join([registryRoot, 'custom_chars.json']));
		var registry:Dynamic = null;
		if (FileSystem.exists(path)) {
			try {
				registry = CoolUtil.parseJson(File.getContent(path));
			} catch (_:Dynamic) {
				return false;
			}
		}
		if (registry == null)
			registry = {};
		if (Std.isOfType(registry, Array))
			return false;
		if (registryHasVSliceKey(registry, name))
			return false;
		var colors:Array<String> = ['#FFFFFF'];
		var healthbar:Dynamic = Reflect.field(charJson, 'healthbar_colors');
		if (Std.isOfType(healthbar, Array)) {
			var values:Array<Dynamic> = cast healthbar;
			if (values.length >= 3) {
				try {
					var red = Std.int(values[0]);
					var green = Std.int(values[1]);
					var blue = Std.int(values[2]);
					colors = [FlxColor.fromRGB(red, green, blue).toWebString()];
				} catch (_:Dynamic) {}
			}
		}
		try {
			var entry:Dynamic = {like:name, icons:[0, 1, 2, 3], colors:colors};
			if (legacyAnimate)
				Reflect.setField(entry, 'legacyAnimate', true);
			Reflect.setField(registry, name, entry);
			ensureDirectory(Path.directory(path));
			File.saveContent(path, CoolUtil.stringifyJson(registry));
			// Background imports invalidate once they hand their completed batch
			// back to the Flixel thread.  Synchronous callers still need the new
			// registry entry to become visible immediately in this process.
			if (!importBackgroundMode)
				Song.invalidateVisualRegistryCache();
			return true;
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}

	/** Resolve a Psych character's Adobe Animate export.  Psych/Funkadelix
	 * commonly writes `image` as `characters/foo/bar` while shipping an
	 * `Animation.json` + `spritemap*.json/png` directory instead of a Sparrow
	 * PNG/XML pair.  Keep this lookup case-insensitive like the ordinary import
	 * path so Windows-authored packs remain usable on Linux. */
	static function psychAnimateFolder(assetsPath:String, charJson:Dynamic):String {
		#if sys
		if (assetsPath == null || charJson == null || !FileSystem.isDirectory(assetsPath))
			return null;
		var image = Reflect.field(charJson, 'image');
		if (image == null)
			return null;
		for (clean in psychImageReferences(Std.string(image))) {
			for (imageRoot in psychImageRoots(assetsPath)) {
				var current = imageRoot;
				for (part in clean.split('/')) {
					current = findChildDirectory(current, part);
					if (current == null)
						break;
				}
				if (current != null && isImportFile(existingImportChild(current, 'Animation.json')))
					return current;
			}
		}
		return null;
		#else
		return null;
		#end
	}

	static function psychImageReference(image:String):String {
		if (image == null)
			return null;
		var clean = StringTools.replace(StringTools.trim(image), '\\', '/');
		while (StringTools.startsWith(clean, './'))
			clean = clean.substr(2);
		if (clean.toLowerCase().indexOf('assets/') == 0)
			clean = clean.substr(7);
		if (clean.toLowerCase().indexOf('images/') == 0)
			clean = clean.substr(7);
		if (clean.toLowerCase().endsWith('.png') || clean.toLowerCase().endsWith('.xml'))
			clean = clean.substr(0, clean.lastIndexOf('.'));
		if (clean == '')
			return null;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..' || part.indexOf(':') >= 0)
				return null;
		return clean;
	}

	/** Psych character JSON accepts a comma-separated list of Sparrow atlas
	 * paths. Resolve each entry independently; treating the whole value as one
	 * path silently drops multi-sheet characters and their scoped icon registry. */
	static function psychImageReferences(image:String):Array<String> {
		var result:Array<String> = [];
		if (image == null)
			return result;
		for (entry in image.split(',')) {
			var clean = psychImageReference(entry);
			if (clean != null && result.indexOf(clean) < 0)
				result.push(clean);
		}
		return result;
	}

	static function psychImageRoots(assetsPath:String):Array<String> {
		var roots:Array<String> = [];
		if (assetsPath == null || !FileSystem.isDirectory(assetsPath))
			return roots;
		var images = findChildDirectory(assetsPath, 'images');
		if (images != null)
			roots.push(images);
		var shared = findChildDirectory(assetsPath, 'shared');
		if (shared != null) {
			var sharedImages = findChildDirectory(shared, 'images');
			if (sharedImages != null && roots.indexOf(sharedImages) < 0)
				roots.push(sharedImages);
		}
		return roots;
	}

	/** Resolve a Psych image from this root or its shared/images library, case-insensitively. */
	static function psychImageSource(assetsPath:String, image:String, extension:String):String {
		if (extension == null || extension == '')
			return null;
		for (clean in psychImageReferences(image)) {
			var relative = clean + extension;
			for (root in psychImageRoots(assetsPath)) {
				var current = root;
				for (part in relative.split('/')) {
					current = existingImportChild(current, part);
					if (!FileSystem.exists(current))
						break;
				}
				if (isImportFile(current))
					return current;
			}
		}
		return null;
	}

	/** Return only complete Sparrow pairs, preserving Psych's atlas order. */
	static function psychImageSources(assetsPath:String, image:String):Array<PsychCharacterAtlasSource> {
		var result:Array<PsychCharacterAtlasSource> = [];
		for (reference in psychImageReferences(image)) {
			var png = psychImageSource(assetsPath, reference, '.png');
			var xml = psychImageSource(assetsPath, reference, '.xml');
			if (png != null && xml != null)
				result.push({png:png, xml:xml});
		}
		return result;
	}

	static function psychIconSource(assetsPath:String, healthIcon:String):String {
		if (healthIcon == null || StringTools.trim(healthIcon) == '')
			return null;
		var name = StringTools.replace(StringTools.trim(healthIcon), '\\', '/');
		while (StringTools.startsWith(name, './'))
			name = name.substr(2);
		for (part in name.split('/'))
			if (part == '' || part == '.' || part == '..' || part.indexOf(':') >= 0)
				return null;
		var candidates = ['icons/icon-' + name + '.png', 'icons/' + name + '.png'];
		for (candidate in candidates) {
			for (root in psychImageRoots(assetsPath)) {
				var current = root;
				for (part in candidate.split('/')) {
					current = existingImportChild(current, part);
					if (!FileSystem.exists(current))
						break;
				}
				if (isImportFile(current))
					return current;
			}
		}
		return null;
	}

	static function psychAnimateDestination(image:String, destinationAssetRoot:String = 'assets'):String {
		#if sys
		var root = psychDestinationAssetRoot(destinationAssetRoot);
		var references = psychImageReferences(image);
		var clean = references.length == 0 ? null : references[0];
		return root == '' || clean == null ? '' : Path.join([root, 'images', clean]);
		#else
		return image == null ? '' : image;
		#end
	}

	static function psychAnimateQuote(value:String):String {
		return StringTools.replace(StringTools.replace(value == null ? '' : value, '\\', '\\\\'), "'", "\\'");
	}

	/** Generate the native character HScript adapter for an Animate atlas.  The
	 * destination engine already ships flixel-animate through DisSprite, so the
	 * donor's timeline and frame indices can remain lossless; only the loader
	 * and Psych animation metadata need routing. */
	static function psychToDisAnimateChar(charcreation:CharCreation, animateFolder:String,
		destinationAssetRoot:String = 'assets'):Void {
		#if sys
		if (charcreation == null || charcreation.charjson == null || animateFolder == null)
			return;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '')
			return;
		var charJson = charcreation.charjson;
		var image = Std.string(Reflect.field(charJson, 'image'));
		var atlasDestination = psychAnimateDestination(image, assetRoot);
		if (atlasDestination == '')
			return;
		var copyResult:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
		mergeTreeNonOverwriting(animateFolder, atlasDestination, 0, copyResult, new Map<String, Bool>());
		var customCharsRoot = Path.join([assetRoot, 'images', 'custom_chars']);
		var exportPath = Path.join([customCharsRoot, charcreation.name]);
		ensureDirectory(exportPath);
		var healthIcon:Dynamic = Reflect.field(charJson, 'healthicon');
		var sourceIcon = psychIconSource(charcreation.path,
			healthIcon == null ? '' : Std.string(healthIcon));
		var iconDestination = Path.join([exportPath, 'icons.png']);
		if (sourceIcon != null && !FileSystem.exists(iconDestination))
			File.copy(sourceIcon, iconDestination);
		var scriptPath = Path.join([customCharsRoot, charcreation.name + '.hscript']);
		if (!FileSystem.exists(scriptPath)) {
			var script = "function init(char) {\n    char.loadTextureAtlas('"
				+ psychAnimateQuote(atlasDestination) + "');\n";
			var animations:Dynamic = Reflect.field(charJson, 'animations');
			if (animations != null && Std.isOfType(animations, Array)) {
				for (animation in (cast animations:Array<Dynamic>)) {
					if (animation == null)
						continue;
					var animName = StringTools.trim(Std.string(Reflect.field(animation, 'anim')));
					if (animName == '')
						continue;
					var fpsValue:Dynamic = Reflect.field(animation, 'fps');
					var fps = fpsValue == null ? 24 : Std.parseFloat(Std.string(fpsValue));
					if (Math.isNaN(fps) || fps <= 0)
						fps = 24;
					var looped = Reflect.field(animation, 'loop') == true;
					var indices:Dynamic = Reflect.field(animation, 'indices');
					var indexValues:Array<String> = [];
					if (indices != null && Std.isOfType(indices, Array))
						for (index in (cast indices:Array<Dynamic>))
							indexValues.push(Std.string(Std.int(index)));
					if (indexValues.length > 0)
						script += "    char.animation.addByTimelineIndices('" + psychAnimateQuote(animName)
							+ "', char.library.timeline, [" + indexValues.join(', ') + "], " + fps + ", " + looped + ");\n";
					else
						script += "    char.animation.addByTimeline('" + psychAnimateQuote(animName)
							+ "', char.library.timeline, " + fps + ", " + looped + ");\n";
					var offsets:Dynamic = Reflect.field(animation, 'offsets');
					if (offsets != null && Std.isOfType(offsets, Array) && (cast offsets:Array<Dynamic>).length >= 2)
						script += "    char.addOffset('" + psychAnimateQuote(animName) + "', "
							+ Std.string(offsets[0]) + ", " + Std.string(offsets[1]) + ");\n";
				}
			}
			var flip = Reflect.field(charJson, 'flip_x') == true;
			if (flip)
				script += "    char.flipX = true;\n";
			var scaleValue:Dynamic = Reflect.field(charJson, 'scale');
			var scale = scaleValue == null ? 1 : Std.parseFloat(Std.string(scaleValue));
			if (!Math.isNaN(scale) && scale != 1)
				script += "    char.scale.x = " + scale + ";\n    char.scale.y = " + scale + ";\n";
			if (Reflect.field(charJson, 'no_antialiasing') == true)
				script += "    char.antialiasing = false;\n";
			script += "}\n";
			var singDuration:Dynamic = Reflect.field(charJson, 'sing_duration');
			if (singDuration != null)
				script += "dadVar = " + Std.string(singDuration) + ";\n";
			script += PsychCharacterDanceCompat.renderAnimateDance(charJson);
			File.saveContent(scriptPath, script);
		}
		ensurePsychCharacterRegistryEntry(charcreation.name, charJson, assetRoot, true);
		#end
	}

	static function legacyAtlasEngine(engine:String):Bool {
		return engine == ImportEngine.KADE || engine == ImportEngine.FPS_PLUS
			|| engine == ImportEngine.LEGACY_POLYMOD || engine == ImportEngine.MODDING_PLUS;
	}

	/**
		Materialize compiled-definition character fallbacks for one imported song.
		The source roots are deliberately the song's owning root plus its assets
		child only; a broad parent selection must never let another mod satisfy a
		missing character.  Existing destination files/registry keys remain
		authoritative, just like the ordinary importer paths.
	*/
	static function importLegacyCharacterAtlases(songData:SongImport):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
		if (songData == null || !legacyAtlasEngine(songData.engine)
			|| songData.sourceRoot == null || StringTools.trim(songData.sourceRoot) == '')
			return result;
		var owner = songData.sourceRoot;
		if (!FileSystem.isDirectory(owner))
			return result;
		var roots:Array<String> = [owner];
		var content = findChildDirectory(owner, 'assets');
		if (content != null)
			roots.push(content);
		// The ordinary media/registry passes run before this fallback. Include
		// the destination scope only for the generic native-implementation gate;
		// legacy atlas inspection itself remains owner-scoped below so a sibling
		// donor cannot silently provide a character visual.
		var implementationRoots = roots.copy();
		if (FileSystem.isDirectory('assets'))
			implementationRoots.push('assets');
		var references:Array<{name:String, role:String}> = [];
		var addReference = function(reference:String, role:String):Void {
			if (reference == null || StringTools.trim(reference) == '')
				return;
			var value = StringTools.trim(reference);
			if (value.toLowerCase() == 'none' || value.toLowerCase() == 'null'
				|| value.toLowerCase() == 'bf' || value.toLowerCase() == 'dad'
				|| value.toLowerCase() == 'gf' || value.toLowerCase() == 'boyfriend'
				|| value.toLowerCase() == 'daddy' || value.toLowerCase() == 'girlfriend')
				return;
			for (existing in references) {
				if (existing.name.toLowerCase() != value.toLowerCase())
					continue;
				// A shared character can be used by GF and an opponent in the
				// same chart; preserve the stricter sing-animation role when any
				// gameplay slot needs it.
				if (existing.role == 'gf' && role != 'gf')
					existing.role = role;
				return;
			}
			references.push({name:value, role:role});
		};
		addReference(songData.p1, 'player');
		addReference(songData.p2, 'opponent');
		addReference(songData.gf, 'gf');
		for (reference in references) {
			if (importWorkCancelled())
				break;
			if (!ImportWorkflow.ImportScanJob.shouldInferLegacyCharacterAtlas(implementationRoots, reference.name))
				continue;
			var finding = LegacyCharacterAtlasImporter.inspectRoots(roots, reference.name, reference.role);
			if (finding == null)
				continue;
			if (!finding.recoverable) {
				// Optional visual definitions should not make a playable chart fail,
				// but retaining the diagnostic in the batch result makes an ambiguous
				// or incomplete atlas visible after Auto import.
				if (finding.diagnostics != null)
					for (diagnostic in finding.diagnostics)
						if (diagnostic != null && StringTools.trim(diagnostic) != '')
							result.errors.push(songData.name + ': ' + diagnostic);
				continue;
			}
			var materialized = LegacyCharacterAtlasImporter.materialize(finding, 'assets');
			result.copied += materialized.copied;
			result.skipped += materialized.skipped;
			result.failed += materialized.failed;
			if (materialized.errors != null)
				for (message in materialized.errors)
					result.errors.push(songData.name + ': ' + message);
			mergeVSliceRegistryEntry(
				chooseVSliceRegistry('assets/images/custom_chars/custom_chars.jsonc',
					'assets/images/custom_chars/custom_chars.json'),
				finding.nativeName, finding.registryEntry, result);
		}
		return result;
	}

	/**
		Convert compiled FPS Plus character definitions into native custom_chars
		assets.  FPS Plus donors ship characters as art plus `data/characters/*.hxc`
		CharacterInfoBase modules: the module is the only place that maps the
		character id a chart uses (WhitBonkers, GfStandingScared, ...) onto its
		Sparrow atlas, health icon and authored animation offsets.  Without this
		pass the destination registry has no entry for those ids and the runtime
		falls back to Dad even though the atlas and icon shipped inside the donor.
		Conversion is deliberately literal (HxcCompat's data-only reader), never
		overwrites destination bytes, and is idempotent across re-imports.
	*/
	static function importFpsPlusCharacters(contentRoot:String, result:ImportAssetMergeResult):Void {
		if (contentRoot == null || !FileSystem.isDirectory(contentRoot))
			return;
		var charactersRoot = findChildDirectory(findChildDirectory(contentRoot, 'data'), 'characters');
		if (charactersRoot == null)
			return;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(charactersRoot));
		} catch (_:Dynamic)
			return;
		entries.sort(function(a:String, b:String):Int {
			var al = a.toLowerCase();
			var bl = b.toLowerCase();
			return al < bl ? -1 : (al > bl ? 1 : 0);
		});
		for (entry in entries) {
			if (importWorkCancelled())
				return;
			if (entry == null || !entry.toLowerCase().endsWith('.hxc'))
				continue;
			// The chart references the module file name, so that stem is the
			// registry key; info.name inside the module is frequently lowercased.
			var name = entry.substr(0, entry.length - 4);
			if (!validModuleName(name))
				continue;
			var scriptPath = Path.join([charactersRoot, entry]);
			if (!isImportFile(scriptPath))
				continue;
			var source:String = null;
			try source = File.getContent(scriptPath) catch (_:Dynamic) continue;
			var definition = fpsPlusCharacterDefinition(source, scriptPath);
			if (definition == null)
				continue;
			var materialized = materializeFpsPlusCharacter(name, definition, contentRoot, result);
			// A previous import can have completed the files before the registry
			// write (or a later asset merge can restore them).  Existing bytes stay
			// authoritative; the registry key is the repairable part.
			if (materialized || hasNativeCharacterFiles(name)) {
				var registryEntry = fpsPlusCharacterRegistryEntry(name, definition, contentRoot);
				if (registryEntry != null)
					mergeVSliceRegistryEntry(chooseVSliceRegistry(
						'assets/images/custom_chars/custom_chars.jsonc',
						'assets/images/custom_chars/custom_chars.json'), name, registryEntry, result);
			}
		}
	}

	/** Read one FPS Plus CharacterInfo module without executing it. */
	static function fpsPlusCharacterDefinition(source:String, path:String):Dynamic {
		if (source == null || StringTools.trim(source) == '')
			return null;
		try {
			var analyzed = HxcCompat.analyze(source, path);
			if (analyzed == null || analyzed.kind != 'character')
				return null;
			var definition = Reflect.field(analyzed, 'characterDefinition');
			if (definition == null)
				return null;
			var spritePath = StringTools.trim(Std.string(Reflect.field(definition, 'spritePath')));
			var animations = Reflect.field(definition, 'animations');
			if (spritePath == '' || spritePath == 'null' || !Std.isOfType(animations, Array))
				return null;
			return definition;
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Copy the donor atlas/icon and emit the authored animation script. */
	static function materializeFpsPlusCharacter(name:String, definition:Dynamic,
		contentRoot:String, result:ImportAssetMergeResult):Bool {
		var spritePath = StringTools.trim(Std.string(Reflect.field(definition, 'spritePath')));
		var png = findVSliceHxcAsset(contentRoot, spritePath, 'images', ['.png']);
		var xml = findVSliceHxcAsset(contentRoot, spritePath, 'images', ['.xml']);
		if (png == null || xml == null) {
			if (result.errors == null)
				result.errors = [];
			result.errors.push('FPS Plus character "' + name + '" references a Sparrow atlas the donor does not ship: ' + spritePath);
			return false;
		}
		var folder = Path.join(['assets', 'images', 'custom_chars', name]);
		if (FileSystem.exists(folder) && !FileSystem.isDirectory(folder))
			return false;
		ensureDirectory(folder);
		copyImportFileNonOverwriting(png, Path.join([folder, 'char.png']), result);
		copyImportFileNonOverwriting(xml, Path.join([folder, 'char.xml']), result);
		var iconPath = fpsPlusHealthIconPath(definition, contentRoot);
		if (iconPath != null)
			copyImportFileNonOverwriting(iconPath, Path.join([folder, 'icons.png']), result);
		writeVSliceHScript(Path.join(['assets', 'images', 'custom_chars', name + '.hscript']),
			generateFpsPlusCharacterHScript(name, definition), result);
		return true;
	}

	static function fpsPlusHealthIconPath(definition:Dynamic, contentRoot:String):String {
		var iconName = StringTools.trim(Std.string(Reflect.field(definition, 'iconName')));
		if (iconName == '' || iconName == 'null')
			return null;
		return findVSliceHxcAsset(contentRoot, 'ui/healthIcons/' + iconName, 'images', ['.png']);
	}

	/**
		Build the playable registry row.  When the donor ships the character's
		health icon strip it is materialized beside the atlas and the icons array
		selects its frames; otherwise the authored icon id stays an alias the
		native icon resolver can chase (or honestly report as missing).
	*/
	static function fpsPlusCharacterRegistryEntry(name:String, definition:Dynamic, contentRoot:String):Dynamic {
		var icons:Dynamic = [0, 0, 0, 0];
		var iconPath = fpsPlusHealthIconPath(definition, contentRoot);
		if (iconPath != null) {
			// FPS Plus icon strips are 150px columns: normal, dying, winning.
			// Keep every state index inside the shipped strip.
			var frames = readPngHorizontalFrames(iconPath, 150);
			icons = frames >= 4 ? [0, 1, 2, 3]
				: frames == 3 ? [0, 1, 2, 0]
				: frames == 2 ? [0, 1, 0, 0]
				: [0, 0, 0, 0];
		} else {
			var iconName = StringTools.trim(Std.string(Reflect.field(definition, 'iconName')));
			if (iconName != '' && iconName != 'null')
				icons = iconName;
		}
		return {like: name, icons: icons, colors: ['#FFFFFF']};
	}

	/** Count 150px-wide horizontal frames in an icon strip; 0 on any parse error. */
	static function readPngHorizontalFrames(path:String, frameSize:Int):Int {
		if (path == null || frameSize <= 0)
			return 0;
		var frames = 0;
		var input:sys.io.FileInput = null;
		try {
			input = File.read(path, true);
			// Read the 24 byte PNG preamble through Bytes: String conversion on
			// native targets UTF-8-decodes bytes and the lone 0x89 signature byte
			// would survive as U+FFFD, breaking every equality check below.
			var header = haxe.io.Bytes.alloc(24);
			var read = input.readBytes(header, 0, 24);
			if (read < 24)
				return 0;
			var isPng = header.get(0) == 0x89 && header.get(1) == 0x50 && header.get(2) == 0x4E
				&& header.get(3) == 0x47 && header.get(4) == 0x0D && header.get(5) == 0x0A
				&& header.get(6) == 0x1A && header.get(7) == 0x0A;
			// Bytes 8-11 hold the IHDR chunk length; 12-15 hold its type.
			var isIhdr = header.get(12) == 0x49 && header.get(13) == 0x48
				&& header.get(14) == 0x44 && header.get(15) == 0x52;
			if (!isPng || !isIhdr)
				return 0;
			// PNG integers are big-endian; haxe.io.Input.readInt32 is not portable here.
			var width = (header.get(16) << 24) | (header.get(17) << 16) | (header.get(18) << 8) | header.get(19);
			var height = (header.get(20) << 24) | (header.get(21) << 16) | (header.get(22) << 8) | header.get(23);
			if (width <= 0 || height <= 0)
				return 0;
			if (height == frameSize && width % frameSize == 0)
				frames = Std.int(width / frameSize);
		} catch (_:Dynamic) {
			return 0;
		}
		if (input != null)
			try input.close() catch (_:Dynamic) {}
		return frames;
	}

	static function fpsPlusQuote(value:String):String {
		return "'" + StringTools.replace(StringTools.replace(StringTools.replace(value, '\\', '\\\\'), "'", "\\'"), '\n', '\\n') + "'";
	}

	static function fpsPlusNumber(value:Dynamic, fallback:Float):Float {
		if (value == null)
			return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? fallback : parsed;
	}

	static function generateFpsPlusCharacterHScript(name:String, definition:Dynamic):String {
		var lines:Array<String> = [
			"// Generated by ModuleFunctions from the donor's compiled FPS Plus character definition.",
			'function init(char) {',
			"    char.frames = FlxAtlasFrames.fromSparrow(hscriptPath + 'char.png', hscriptPath + 'char.xml');",
			'    char.like = ' + fpsPlusQuote(name) + ';'
		];
		var animations = Reflect.field(definition, 'animations');
		if (animations != null && Std.isOfType(animations, Array)) {
			for (animation in (cast animations:Array<Dynamic>)) {
				if (animation == null)
					continue;
				var animationName = Std.string(Reflect.field(animation, 'name'));
				var prefix = Std.string(Reflect.field(animation, 'prefix'));
				if (animationName == '' || prefix == '' || prefix == 'null')
					continue;
				var frameRate = fpsPlusNumber(Reflect.field(animation, 'fps'), 24);
				if (frameRate <= 0)
					frameRate = 24;
				var looped = Reflect.field(animation, 'loop') == true;
				var indices = Reflect.field(animation, 'indices');
				if (Reflect.field(animation, 'kind') == 'indices' && indices != null
					&& Std.isOfType(indices, Array) && (cast indices:Array<Dynamic>).length > 0) {
					var values:Array<String> = [];
					for (index in (cast indices:Array<Dynamic>))
						values.push(Std.string(index));
					lines.push('    char.animation.addByIndices(' + fpsPlusQuote(animationName) + ', '
						+ fpsPlusQuote(prefix) + ', [' + values.join(', ') + "], '', " + frameRate + ', '
						+ (looped ? 'true' : 'false') + ');');
				} else {
					lines.push('    char.animation.addByPrefix(' + fpsPlusQuote(animationName) + ', '
						+ fpsPlusQuote(prefix) + ', ' + frameRate + ', ' + (looped ? 'true' : 'false') + ');');
				}
				lines.push('    char.addOffset(' + fpsPlusQuote(animationName) + ', '
					+ fpsPlusNumber(Reflect.field(animation, 'offsetX'), 0) + ', '
					+ fpsPlusNumber(Reflect.field(animation, 'offsetY'), 0) + ');');
			}
		}
		lines = lines.concat([
			"    char.playAnim('idle');",
			'    char.flipX = false;',
			'}',
			'portraitOffset = [0, 0];',
			'dadVar = 4.0;',
			'isPixel = false;',
			'function sing(direction, miss, alt, char) {}',
			'function update(elapsed, char) {}',
			"function dance(char) { char.playAnim('idle'); }",
			''
		]);
		return lines.join('\n');
	}

	/**
		Convert compiled FPS Plus stage definitions (data/stages/*.hxc BaseStage
		modules) into native custom_stages implementations.  A donor constructor
		builds its static presentation from literal BGSprite/FlxSprite
		constructions plus start-point offsets; those literals are recovered
		without executing the donor class and emitted as an ordinary native stage
		script and registry key, so a chart stage id such as alleyBalls resolves to
		the donor's art instead of the neutral fallback group.  Stages whose
		presentation is too dynamic stay unregistered and keep their diagnostic.
	*/
	static function importFpsPlusStages(contentRoot:String, result:ImportAssetMergeResult):Void {
		if (contentRoot == null || !FileSystem.isDirectory(contentRoot))
			return;
		var stagesRoot = findChildDirectory(findChildDirectory(contentRoot, 'data'), 'stages');
		if (stagesRoot == null)
			return;
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(stagesRoot));
		} catch (_:Dynamic)
			return;
		entries.sort(function(a:String, b:String):Int {
			var al = a.toLowerCase();
			var bl = b.toLowerCase();
			return al < bl ? -1 : (al > bl ? 1 : 0);
		});
		for (entry in entries) {
			if (importWorkCancelled())
				return;
			if (entry == null || !entry.toLowerCase().endsWith('.hxc'))
				continue;
			var name = entry.substr(0, entry.length - 4);
			if (!validModuleName(name))
				continue;
			var scriptPath = Path.join([stagesRoot, entry]);
			if (!isImportFile(scriptPath))
				continue;
			var source:String = null;
			try source = File.getContent(scriptPath) catch (_:Dynamic) continue;
			var spec = parseFpsPlusStage(source);
			if (spec == null || spec.sprites.length == 0)
				continue;
			var missingMedia = false;
			for (sprite in spec.sprites) {
				if (!materializeFpsPlusStageSprite(sprite, contentRoot, result)) {
					missingMedia = true;
					break;
				}
			}
			if (missingMedia) {
				if (result.errors == null)
					result.errors = [];
				result.errors.push('FPS Plus stage "' + name + '" references art the donor does not ship.');
				continue;
			}
			// Destination bytes stay authoritative; writing the script and the
			// registry key separately keeps partial imports repairable.  Native
			// stage scripts live at the top level of custom_stages/ (registeredStage
			// resolves `<folder>../<script>` against that layout; the optional
			// folder only holds the stage's own art).
			writeVSliceHScript(Path.join(['assets', 'images', 'custom_stages', name + '.hscript']),
				generateFpsPlusStageHScript(spec), result);
			mergeVSliceRegistryEntry('assets/images/custom_stages/custom_stages.json', name, name, result);
		}
	}

	static function materializeFpsPlusStageSprite(sprite:FpsPlusStageSprite, contentRoot:String,
		result:ImportAssetMergeResult):Bool {
		var png = findVSliceHxcAsset(contentRoot, sprite.image, 'images', ['.png']);
		if (png == null)
			return false;
		var clean = StringTools.replace(StringTools.trim(sprite.image), '\\', '/');
		copyImportFileNonOverwriting(png, Path.join(['assets', 'images', clean + '.png']), result);
		if (sprite.animated) {
			var xml = findVSliceHxcAsset(contentRoot, sprite.image, 'images', ['.xml']);
			if (xml == null)
				return false;
			copyImportFileNonOverwriting(xml, Path.join(['assets', 'images', clean + '.xml']), result);
		}
		return true;
	}

	/** Literal-only recovery of one BaseStage constructor.  Never executes donor code. */
	static function parseFpsPlusStage(source:String):Null<FpsPlusStageSpec> {
		if (source == null || StringTools.trim(source) == '')
			return null;
		var zoom:Null<Float> = null;
		var zoomExpression = new EReg('\\bstartingZoom\\s*=\\s*([-+0-9.]+)', 'm');
		if (zoomExpression.match(source)) {
			var parsed = Std.parseFloat(zoomExpression.matched(1));
			if (!Math.isNaN(parsed))
				zoom = parsed;
		}
		var useStartPoints = new EReg('\\buseStartPoints\\s*=\\s*true', 'm').match(source);
		var offsetMap:Map<String, {char:String, x:Float, y:Float}> = new Map<String, {char:String, x:Float, y:Float}>();
		var offsetOrder:Array<String> = [];
		var offsetExpression = new EReg('\\b(bf|dad|gf)Start\\s*\\.\\s*([xy])\\s*(\\+=|-=)\\s*([-+0-9.]+)', 'g');
		var remaining = source;
		var guard = 0;
		while (guard++ < 512 && offsetExpression.match(remaining)) {
			var character = offsetExpression.matched(1);
			var axis = offsetExpression.matched(2);
			var sign = offsetExpression.matched(3) == '-=' ? -1.0 : 1.0;
			var value = Std.parseFloat(offsetExpression.matched(4));
			if (!Math.isNaN(value)) {
				var entry = offsetMap.get(character);
				if (entry == null) {
					entry = {char: character, x: 0.0, y: 0.0};
					offsetMap.set(character, entry);
					offsetOrder.push(character);
				}
				if (axis == 'y')
					entry.y += sign * value;
				else
					entry.x += sign * value;
			}
			var position = offsetExpression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		var offsets:Array<{char:String, x:Float, y:Float}> = [];
		for (character in offsetOrder)
			offsets.push(offsetMap.get(character));

		var backgroundCalls:Map<String, Bool> = new Map<String, Bool>();
		var backgroundExpression = new EReg('\\baddToBackground\\s*\\(\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\)', 'g');
		remaining = source;
		guard = 0;
		while (guard++ < 512 && backgroundExpression.match(remaining)) {
			backgroundCalls.set(backgroundExpression.matched(1), true);
			var position = backgroundExpression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}

		var sprites:Array<FpsPlusStageSprite> = [];
		var usedNames:Map<String, Bool> = new Map<String, Bool>();
		var addSprite = function(sprite:FpsPlusStageSprite):Void {
			var variable = sprite.variable;
			if (variable == null || variable == '' || usedNames.exists(variable)) {
				var suffix = sprites.length;
				do variable = 'fpsStage' + (suffix++) while (usedNames.exists(variable));
			}
			sprite.variable = variable;
			usedNames.set(variable, true);
			sprites.push(sprite);
		};
		// BGSprite(<image>, x, y, scrollX, scrollY, [anims], loop) with an optional
		// `var name:Type = ` or `name = ` prefix.
		var bgExpression = new EReg('(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*[A-Za-z_][A-Za-z0-9_]*)?\\s*=\\s*new\\s+BGSprite\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']'
			+ '\\s*(?:,\\s*([-+0-9.]+))?(?:,\\s*([-+0-9.]+))?(?:,\\s*([-+0-9.]+))?(?:,\\s*([-+0-9.]+))?'
			+ '(?:,\\s*\\[([^\\]]*)\\])?(?:,\\s*(true|false))?\\s*\\)', 'g');
		remaining = source;
		guard = 0;
		while (guard++ < 512 && bgExpression.match(remaining)) {
			var variable = bgExpression.matched(1);
			var image = bgExpression.matched(2);
			if (image != null && StringTools.trim(image) != '') {
				var animations:Array<String> = [];
				var animationList = bgExpression.matched(7);
				if (animationList != null) {
					for (piece in animationList.split(',')) {
						var clean = StringTools.trim(piece);
						if (clean.length >= 2 && (clean.charAt(0) == '"' || clean.charAt(0) == "'")
							&& clean.charAt(clean.length - 1) == clean.charAt(0))
							animations.push(clean.substr(1, clean.length - 2));
					}
				}
				addSprite({
					variable: variable == null ? '' : variable,
					image: StringTools.trim(image),
					x: fpsPlusNumber(bgExpression.matched(3), 0),
					y: fpsPlusNumber(bgExpression.matched(4), 0),
					scrollX: fpsPlusNumber(bgExpression.matched(5), 1),
					scrollY: fpsPlusNumber(bgExpression.matched(6), 1),
					animated: true,
					animations: animations
				});
			}
			var position = bgExpression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		// FlxSprite(x, y).loadGraphic(Paths.image("<image>"))
		var flatExpression = new EReg('(?:var\\s+)?([A-Za-z_][A-Za-z0-9_]*)\\s*(?::\\s*[A-Za-z_][A-Za-z0-9_]*)?\\s*=\\s*new\\s+FlxSprite\\s*\\(([^)]*)\\)\\s*\\.\\s*loadGraphic\\s*\\(\\s*Paths\\s*\\.\\s*image\\s*\\(\\s*["\\\']([^"\\\']+)["\\\']', 'g');
		remaining = source;
		guard = 0;
		while (guard++ < 512 && flatExpression.match(remaining)) {
			var variable = flatExpression.matched(1);
			var image = flatExpression.matched(3);
			if (image != null && StringTools.trim(image) != '') {
				var coordinates = flatExpression.matched(2).split(',');
				var x = coordinates.length > 0 ? fpsPlusNumber(coordinates[0], 0) : 0.0;
				var y = coordinates.length > 1 ? fpsPlusNumber(coordinates[1], 0) : 0.0;
				addSprite({
					variable: variable == null ? '' : variable,
					image: StringTools.trim(image),
					x: x,
					y: y,
					scrollX: 1,
					scrollY: 1,
					animated: false,
					animations: []
				});
			}
			var position = flatExpression.matchedPos();
			if (position.len <= 0 || position.pos + position.len >= remaining.length)
				break;
			remaining = remaining.substr(position.pos + position.len);
		}
		if (sprites.length == 0)
			return null;
		// Donor stages add their presentation through explicit calls; when the
		// literals were recovered but every addToBackground call used a different
		// shape, keep the sprites so the conversion still represents the donor.
		var selected = sprites.filter(function(sprite:FpsPlusStageSprite):Bool
			return backgroundCalls.exists(sprite.variable));
		if (selected.length > 0)
			sprites = selected;
		return {
			defaultZoom: zoom,
			useStartPoints: useStartPoints,
			offsets: offsets,
			sprites: sprites
		};
	}

	static function generateFpsPlusStageHScript(spec:FpsPlusStageSpec):String {
		var lines:Array<String> = [
			"// Generated by ModuleFunctions from the donor's compiled FPS Plus stage definition.",
			'function start(song) {'
		];
		if (spec.defaultZoom != null)
			lines.push('    setDefaultZoom(' + spec.defaultZoom + ');');
		if (spec.useStartPoints)
			lines.push('    stage.useStartPoints = true;');
		for (offset in spec.offsets)
			lines.push("    stage.setOffsets(" + fpsPlusQuote(offset.char) + ', ' + offset.x + ', ' + offset.y + ');');
		for (sprite in spec.sprites) {
			var image = StringTools.replace(StringTools.trim(sprite.image), '\\', '/');
			lines.push('');
			lines.push('    var ' + sprite.variable + ' = new FlxSprite(' + sprite.x + ', ' + sprite.y + ');');
			if (sprite.animated) {
				lines.push("    " + sprite.variable + ".frames = FlxAtlasFrames.fromSparrow('assets/images/"
					+ image + ".png', 'assets/images/" + image + ".xml');");
				for (animation in sprite.animations)
					lines.push('    ' + sprite.variable + '.animation.addByPrefix(' + fpsPlusQuote(animation)
						+ ', ' + fpsPlusQuote(animation) + ', 24, true);');
				if (sprite.animations.length > 0)
					lines.push('    ' + sprite.variable + '.animation.play(' + fpsPlusQuote(sprite.animations[0]) + ');');
			} else {
				lines.push("    " + sprite.variable + ".loadGraphic('assets/images/" + image + ".png');");
			}
			lines.push('    ' + sprite.variable + '.antialiasing = true;');
			lines.push('    ' + sprite.variable + '.scrollFactor.set(' + sprite.scrollX + ', ' + sprite.scrollY + ');');
			lines.push('    addSprite(' + sprite.variable + ', BEHIND_ALL);');
			lines.push("    stage.addElement('" + sprite.variable + "', " + sprite.variable + ');');
		}
		lines = lines.concat([
			'}',
			'function beatHit(beat) {}',
			'function update(elapsed) {}',
			''
		]);
		return lines.join('\n');
	}

	/** Single-file, never-overwrite copy used by the FPS Plus converters. */
	static function copyImportFileNonOverwriting(source:String, destination:String,
		result:ImportAssetMergeResult):Void {
		if (source == null || destination == null || !FileSystem.exists(source))
			return;
		if (FileSystem.exists(destination)) {
			result.skipped++;
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			File.copy(source, destination);
			result.copied++;
		} catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null)
				result.errors = [];
			result.errors.push('Could not copy imported asset: ' + destination + ' (' + Std.string(error) + ')');
		}
	}

	/** Write generated import output without replacing user-edited destinations.
	 * Identity metadata additionally requires an existing staged copy to agree. */
	static function writeImportContentNonOverwriting(content:String, destination:String,
		result:ImportAssetMergeResult, strictExisting:Bool = false):Void {
		if (content == null || destination == null)
			return;
		if (strictExisting) {
			if (ImportGeneratedOutput.write(destination, content, true)) result.copied++;
			else result.skipped++;
			return;
		}
		if (FileSystem.exists(destination)) {
			result.skipped++;
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			File.saveContent(destination, content);
			result.copied++;
		} catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null)
				result.errors = [];
			result.errors.push('Could not write imported script: ' + destination + ' (' + Std.string(error) + ')');
		}
	}

	/** Character ids actually named by charts accepted from this content root.
	 * Do not copy a donor's whole custom-character library into every song owner:
	 * keep only the authored player slots for the songs this batch imported. */
	static function modPlusCharactersUsedByImportedSongs(contentRoot:String,
		importedNames:Map<String, Bool>, importedSources:Map<String, SongImportSource>):Array<String> {
		var result:Array<String> = [];
		if (contentRoot == null || importedNames == null || importedSources == null
			|| !FileSystem.isDirectory(contentRoot))
			return result;
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (songKey in importedNames.keys()) {
			var sourceInfo = importedSources.get(songKey);
			if (sourceInfo == null || sourceInfo.data == null
				|| !importPathIsWithin(sourceInfo.data, contentRoot)
				|| !FileSystem.isDirectory(sourceInfo.data))
				continue;
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(sourceInfo.data));
			} catch (_:Dynamic) {
				continue;
			}
			entries.sort(function(a:String, b:String):Int return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
			for (entry in entries) {
				if (!entry.toLowerCase().endsWith('.json'))
					continue;
				var chart = readImportJson(Path.join([sourceInfo.data, entry]));
				var chartSong:Dynamic = chart == null ? null : Reflect.field(chart, 'song');
				if (chartSong == null || !Std.isOfType(Reflect.field(chartSong, 'notes'), Array))
					continue;
				for (field in ['player1', 'player2', 'gf']) {
					var raw:Dynamic = Reflect.field(chartSong, field);
					if (raw == null || !Std.isOfType(raw, String))
						continue;
					var character = StringTools.trim(Std.string(raw));
					var separator = character.lastIndexOf(':');
					if (separator > 0 && separator < character.length - 1) {
						var role = character.substr(separator + 1).toLowerCase();
						switch (role) {
							case 'bf' | 'boyfriend' | 'player' | 'player1' | 'dad' | 'opponent' | 'player2'
								| 'gf' | 'girlfriend' | 'player3':
								character = StringTools.trim(character.substr(0, separator));
							default:
						}
					}
					if (!validModuleName(character))
						continue;
				var key = character.toLowerCase();
				if (!seen.exists(key)) {
					seen.set(key, true);
					result.push(character);
				}
				}
			}
		}
		return result;
	}

	/** Copy the chart-selected Modding Plus character rows and their files into
	 * the selected owner's namespace. Global assets remain useful for unrelated
	 * characters, while a same-id foreign atlas can no longer win first-writer
	 * precedence for this song. */
	static function mergeModPlusCharacterAssets(sourceCharacters:String, ownerRoot:String,
		characterIds:Array<String>, result:ImportAssetMergeResult):Void {
		if (sourceCharacters == null || ownerRoot == null || characterIds == null
			|| characterIds.length == 0 || !FileSystem.isDirectory(sourceCharacters))
			return;
		var registryPath = findImportFile(sourceCharacters, ['custom_chars.jsonc', 'custom_chars.json']);
		var sourceRegistry:Dynamic = null;
		if (registryPath != null) {
			sourceRegistry = readImportJson(registryPath);
			if (sourceRegistry == null || Std.isOfType(sourceRegistry, Array)) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Could not parse the selected Modding Plus custom character registry: ' + registryPath);
				return;
			}
		}
		var selectedRegistry:Dynamic = {};
		var implementationNames:Map<String, String> = new Map<String, String>();
		for (character in characterIds) {
			if (!validModuleName(character))
				continue;
			var selectedName:String = null;
			if (sourceRegistry != null)
				for (name in Reflect.fields(sourceRegistry))
					if (name.toLowerCase() == character.toLowerCase()) {
						selectedName = name;
						break;
					}
			if (selectedName != null) {
				var row:Dynamic = Reflect.field(sourceRegistry, selectedName);
				Reflect.setField(selectedRegistry, selectedName, row);
				var alias:Dynamic = row == null ? null : Reflect.field(row, 'like');
				var implementation = alias == null || StringTools.trim(Std.string(alias)) == ''
					? selectedName : StringTools.trim(Std.string(alias));
				if (validModuleName(implementation))
					implementationNames.set(implementation.toLowerCase(), implementation);
				implementationNames.set(selectedName.toLowerCase(), selectedName);
			} else {
				// Older Modding Plus packages sometimes provide a standalone script
				// and atlas without a registry row. Keep that direct form scoped too.
				implementationNames.set(character.toLowerCase(), character);
			}
		}
		var ownerCharacters = Path.join([ownerRoot, 'images', 'custom_chars']);
		for (character in characterIds) {
			if (!validModuleName(character))
				continue;
			var registryName:String = null;
			if (sourceRegistry != null)
				for (name in Reflect.fields(sourceRegistry))
					if (name.toLowerCase() == character.toLowerCase()) {
						registryName = name;
						break;
					}
			var ownerName = registryName == null ? character : registryName;
			var sourceFolder = findChildDirectory(sourceCharacters, ownerName);
			if (sourceFolder != null)
				mergeTreeNonOverwriting(sourceFolder, Path.join([ownerCharacters, ownerName]),
					0, result);
		}
		for (implementation in implementationNames) {
			for (extension in ['hscript', 'hxs', 'json', 'jsonc']) {
				var sourceScript = findImportFile(sourceCharacters, [implementation + '.' + extension]);
				if (sourceScript != null)
					copyImportFileNonOverwriting(sourceScript,
						Path.join([ownerCharacters, implementation + '.' + extension]), result);
			}
		}
		if (Reflect.fields(selectedRegistry).length > 0)
			writeImportContentNonOverwriting(CoolUtil.stringifyJson(selectedRegistry),
				Path.join([ownerCharacters, 'custom_chars.jsonc']), result);
	}

	/** Copy only executable foreign-engine trees into the source namespace.  The
	 * logical layout is retained (including shared/) so Psych discovery can use
	 * its normal global/stage/event lookup, while old HXC data families are
	 * exposed below the namespace's scripts/ tree for HxcScriptDiscovery. */
	static function mergeCompatScriptTrees(contentRoot:String, sourceRoot:String, engine:String,
		result:ImportAssetMergeResult, ?skipPaths:Map<String, Bool>,
		?modPlusCharacterIds:Array<String>, ?destinationSubpath:String,
		?mappedAssetPlan:SourceMappedAssetPlan, ?nightmareVisionScope:String):String {
		if (contentRoot == null || !FileSystem.isDirectory(contentRoot)
			|| sourceRoot == null || StringTools.trim(sourceRoot) == '')
			return null;
		if (importPathIsWithin(contentRoot, 'assets') && importPathIsWithin(contentRoot, destinationAssetsPath()))
			return null;
		var destination = CompatScriptManifest.destinationRoot(sourceRoot, engine);
		var destinationRoot = destination;
		if (destinationSubpath != null && StringTools.trim(destinationSubpath) != '') {
			if (!validImportEntryName(destinationSubpath)) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Invalid imported script destination subpath: ' + destinationSubpath);
				return destination;
			}
			destinationRoot = Path.join([destination, destinationSubpath]);
		}
		// Psych-family packs use pack.json for their authored identity and global
		// script scope. Retain the source document beside its owned scripts so
		// runtime settings can validate package names without consulting another
		// import or replacing a previously imported copy.
		var packageMetadata = findImportFile(sourceRoot, ['pack.json']);
		if (packageMetadata == null && sourceRoot != contentRoot)
			packageMetadata = findImportFile(contentRoot, ['pack.json']);
		if (packageMetadata != null)
			copyImportFileNonOverwriting(packageMetadata, Path.join([destinationRoot, 'pack.json']), result);
		// Nightmare Vision reads package settings from the selected mod root's
		// meta.json. Keep only that exact package-local file beside its owned
		// runtime trees; the shared content-container config is a distinct source
		// boundary and is never substituted for a package config.
		if (engine == ImportEngine.NIGHTMARE_VISION) {
			var packageConfig = findImportFile(sourceRoot, ['meta.json']);
			if (packageConfig != null)
				copyImportFileNonOverwriting(packageConfig, Path.join([destination, 'meta.json']), result);
		}
		var roots:Array<{base:String, prefix:String}> = [{base:contentRoot, prefix:''}];
		var shared = findChildDirectory(contentRoot, 'shared');
		if (shared != null)
			roots.push({base:shared, prefix:'shared'});
		if (engine == ImportEngine.MODDING_PLUS && modPlusCharacterIds != null
			&& modPlusCharacterIds.length > 0) {
			var characterRoot = findChildDirectory(findChildDirectory(contentRoot, 'images'), 'custom_chars');
			if (characterRoot == null && shared != null)
				characterRoot = findChildDirectory(findChildDirectory(shared, 'images'), 'custom_chars');
			mergeModPlusCharacterAssets(characterRoot, destinationRoot, modPlusCharacterIds, result);
		}
		for (root in roots) {
			if (importWorkCancelled())
				return destination;
			var luaDependencies = engine == ImportEngine.PSYCH
				? PsychLuaScriptDependencies.discover(root.base)
				: {files:[], complete:true};
			if (!luaDependencies.complete) {
				result.failed++;
				if (result.errors == null)
					result.errors = [];
				result.errors.push('Could not fully inspect literal addLuaScript dependencies in ' + root.base);
			}
			for (dependency in luaDependencies.files) {
				if (skipPaths != null && skipPaths.exists(importPathKey(dependency.source)))
					continue;
				var relative = root.prefix == '' ? dependency.relative
					: root.prefix + '/' + dependency.relative;
				copyImportFileNonOverwriting(dependency.source,
					Path.join([destinationRoot, relative]), result);
			}
			// Modding Plus stage ids share one global registry with the base game.
			// Preserve each donor's scripts and hscriptPath assets under its song
			// manifest namespace so colliding ids still resolve to their owner.
			if (engine == 'Modding Plus') {
				var stages = findChildDirectory(Path.join([root.base, 'images']), 'custom_stages');
				if (stages != null) {
					var scopedStages = root.prefix == ''
						? Path.join([destinationRoot, 'images', 'custom_stages'])
						: Path.join([destinationRoot, root.prefix, 'images', 'custom_stages']);
					mergeTreeNonOverwriting(stages, scopedStages, 0, result);
				}
				// A cutscene registry may reuse a global id while naming a different
				// script. Keep its scripts and relative media with the same owner as
				// the chart, and never replace an existing imported override.
				var cutscenes = findChildDirectory(Path.join([root.base, 'images']), 'custom_cutscenes');
				if (cutscenes != null) {
					var scopedCutscenes = root.prefix == ''
						? Path.join([destinationRoot, 'images', 'custom_cutscenes'])
						: Path.join([destinationRoot, root.prefix, 'images', 'custom_cutscenes']);
					mergeTreeNonOverwriting(cutscenes, scopedCutscenes, 0, result);
				}
			}
			for (name in compatScriptTreeNames()) {
				var source = findChildDirectory(root.base, name);
				if (source == null)
					continue;
				var treeDestination = root.prefix == ''
					? Path.join([destinationRoot, name])
					: Path.join([destinationRoot, root.prefix, name]);
				mergeTreeNonOverwriting(source, treeDestination, 0, result, skipPaths);
			}
			// FPS Plus and older Haxe packs put executable character/stage modules
			// below data/.  Keep those files inside this namespace instead of
			// flattening them into the shared assets/scripts tree.
			var dataRoot = findChildDirectory(root.base, 'data');
			// Scripts may read package-wide data sidecars through Paths.txt/json.
			// Keep only files directly below data/ with the selected owner; song
			// directories are copied separately after their import succeeds.
			if (dataRoot != null) {
				var dataEntries:Array<String> = [];
				try dataEntries = ImportDirectoryListing.normalize(FileSystem.readDirectory(dataRoot)) catch (_:Dynamic) {
					result.failed++;
				}
				if (dataEntries.length > 2048) {
					result.failed++;
					if (result.errors == null) result.errors = [];
					result.errors.push('Too many package data sidecars in ' + dataRoot);
				} else for (entry in dataEntries) {
					if (importWorkCancelled()) return destination;
					if (!validImportEntryName(entry)) continue;
					var sourceFile = Path.join([dataRoot, entry]);
					if (FileSystem.isDirectory(sourceFile) || !importPathIsWithin(sourceFile, dataRoot)) continue;
					if (skipPaths != null && skipPaths.exists(importPathKey(sourceFile))) continue;
					var dataDestination = root.prefix == ''
						? Path.join([destinationRoot, 'data', entry])
						: Path.join([destinationRoot, root.prefix, 'data', entry]);
					copyImportFileNonOverwriting(sourceFile, dataDestination, result);
				}
			}
			// Preserve data-only note style definitions beside their scoped atlases.
			// They must not replace the song's global UI pack or another import's
			// same-id style; runtime lookup stays inside this manifest root.
			var noteStyles = findChildDirectory(dataRoot, 'notestyles');
			if (noteStyles != null) {
				var styleDestination = root.prefix == ''
					? Path.join([destinationRoot, 'data', 'notestyles'])
					: Path.join([destinationRoot, root.prefix, 'data', 'notestyles']);
				mergeTreeNonOverwriting(noteStyles, styleDestination, 0, result, skipPaths);
			}
			if (dataRoot != null)
				for (family in ['characters', 'stages', 'cutscenes', 'ui', 'events', 'notes', 'modules']) {
					var familyRoot = findChildDirectory(dataRoot, family);
					if (familyRoot == null)
						continue;
					var familyDestination = root.prefix == ''
						? Path.join([destinationRoot, 'scripts', family])
						: Path.join([destinationRoot, root.prefix, 'scripts', family]);
					mergeHxcScriptTree(familyRoot, familyDestination, 0, result, skipPaths);
				}
			if (engine == ImportEngine.NIGHTMARE_VISION) {
				var nmvFiles:Array<Dynamic> = [];
				if (!collectNightmareVisionScriptFiles(root.base, root.prefix, nmvFiles)) {
					result.failed++;
					if (result.errors == null) result.errors = [];
					result.errors.push('Could not fully inspect Nightmare Vision gameplay scripts in ' + root.base
						+ ' (read failure, cancellation, or path outside source root)');
				}
				for (file in nmvFiles) {
					if (importWorkCancelled())
						return destination;
					if (file == null || file.source == null || file.relative == null
						|| !importPathIsWithin(file.source, root.base)) {
						result.failed++;
						continue;
					}
					if (skipPaths != null && skipPaths.exists(importPathKey(file.source)))
						continue;
					copyImportFileNonOverwriting(file.source,
						Path.join([destinationRoot, file.relative]), result);
				}
			}
		}
		if (engine == ImportEngine.PSYCH) {
			var mappedPlan = mappedAssetPlan;
			if (mappedPlan == null) {
				mappedPlan = SourceMappedMediaPublisher.prepare(sourceRoot, engine, destination,
					'', function():Bool return importWorkCancelled());
				if (mappedPlan.diagnostics != null && mappedPlan.diagnostics.length > 0) {
					if (result.errors == null) result.errors = [];
					for (diagnostic in mappedPlan.diagnostics)
						if (diagnostic != null) result.errors.push(diagnostic);
				}
				if (mappedPlan.cancelled || importWorkCancelled()) return destination;
				if (mappedPlan.failed) {
					result.failed++;
					return destination;
				}
				SourceMappedMediaPublisher.publish(mappedPlan,
					function(source:String, target:String):Void copyImportFileNonOverwriting(source, target, result),
					function():Bool return importWorkCancelled(),
					function(path:String, content:String):Void
						writeImportContentNonOverwriting(content, path, result, true));
			}
			var languagePlan = SourceMappedMediaPublisher.languageView(mappedPlan);
			mergePsychLanguageDataScopes(contentRoot, sourceRoot, destinationRoot, result,
				skipPaths, languagePlan);
		}
		return destination;
	}

	/** Import selected NMV package content below its owner namespace and keep an
	 * explicit source engine-assets dependency under that owner's `__nmv_core`
	 * subtree. Separate roots preserve package/core lookup precedence and content
	 * collisions without flattening the executable installation into a package. */
	static function mergeSelectedNightmareVisionScriptOwners(importedNames:Map<String, Bool>,
		importedSources:Map<String, SongImportSource>, scriptSourceRoot:String,
		result:ImportAssetMergeResult, stagedOwnerRoots:Map<String, Bool>,
		?skipPaths:Map<String, Bool>,
		?mappedOwnerPlans:Map<String, PreparedMappedAssetOwner>):Void {
		if (importedNames == null || importedSources == null || result == null)
			return;
		var staged = stagedOwnerRoots == null ? new Map<String, Bool>() : stagedOwnerRoots;
		for (songKey in importedNames.keys()) {
			if (importWorkCancelled())
				return;
			var sourceInfo = importedSources.get(songKey);
			if (sourceInfo == null || sourceInfo.engine != ImportEngine.NIGHTMARE_VISION
				|| sourceInfo.sourceRoot == null || StringTools.trim(sourceInfo.sourceRoot) == '')
				continue;
			var ownerRoot = sourceInfo.sourceRoot;
			// importedSources spans the whole Auto import transaction. Each
			// mergeSupportedAssets call owns only one detected installation, so
			// leave rows from other roots for their matching invocation instead of
			// misreporting them as missing/outside this package.
			if (scriptSourceRoot != null && StringTools.trim(scriptSourceRoot) != ''
				&& !importPathIsWithin(ownerRoot, scriptSourceRoot))
				continue;
			if (!FileSystem.isDirectory(ownerRoot)) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Selected Nightmare Vision script owner is missing: ' + ownerRoot);
				continue;
			}
			var ownerKey = importPathKey(ownerRoot);
			if (ownerKey == '') {
				result.failed++;
				continue;
			}
			if (staged.exists(ownerKey))
				continue;
			// Mark before walking so multiple selected songs from this package do
			// not rescan it. A failed walk is reported and can be retried by a later
			// import transaction because this map is never persisted.
			staged.set(ownerKey, true);
			var contentRoot = Path.join([ownerRoot, 'assets']);
			if (!FileSystem.isDirectory(contentRoot))
				contentRoot = ownerRoot;
			if (!importPathIsWithin(contentRoot, ownerRoot)) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Selected Nightmare Vision content root is outside its package: ' + contentRoot);
				continue;
			}
			var coreAssetsRoot = NightmareVisionAssetCollector.resolveCoreAssetsRoot(ownerRoot);
			var coreIsSelectedRoot = coreAssetsRoot != ''
				&& (importPathKey(coreAssetsRoot) == importPathKey(contentRoot)
					|| importPathKey(coreAssetsRoot) == importPathKey(ownerRoot));
			var mappedOwner = mappedOwnerPlan(mappedOwnerPlans, ownerRoot, ImportEngine.NIGHTMARE_VISION);
			var installedOwnerRoot = mergeCompatScriptTrees(contentRoot, ownerRoot,
				ImportEngine.NIGHTMARE_VISION, result, skipPaths, null,
				coreIsSelectedRoot ? NightmareVisionAssetCollector.CORE_SUBTREE : null,
				mappedOwner == null ? null : mappedOwner.plan,
				mappedOwner == null ? '' : mappedOwner.scope);
			if (installedOwnerRoot != null
				&& importPathIsWithin(installedOwnerRoot, CompatScriptManifest.ROOT_PREFIX)) {
				if (!coreIsSelectedRoot)
					mergeNightmareVisionAssetFiles(contentRoot, installedOwnerRoot, result, skipPaths,
						mappedOwner);
				if (coreAssetsRoot != '')
					mergeNightmareVisionAssetFiles(coreAssetsRoot,
						Path.join([installedOwnerRoot, NightmareVisionAssetCollector.CORE_SUBTREE]),
						result, skipPaths, coreIsSelectedRoot ? mappedOwner : null);
				var stageDestination = coreIsSelectedRoot
					? Path.join([installedOwnerRoot, NightmareVisionAssetCollector.CORE_SUBTREE])
					: installedOwnerRoot;
				mergeNightmareVisionStageDataFiles(contentRoot, stageDestination, result, skipPaths);
			} else if (!importWorkCancelled()) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('Could not resolve the selected Nightmare Vision runtime namespace for stage metadata: '
					+ ownerRoot);
			}
		}
	}

	/** Materialize structurally authorized Nightmare Vision package roots even
	 * when their source packages contain no chart rows. The caller supplies roots
	 * from the retained-source family catalog; this method publishes only a
	 * package with its own direct meta.json and uses the normal staged namespace,
	 * asset collectors, collision rules, and shared-core layout. */
	public static function publishNightmareVisionFamilyMemberRoots(sourceRoots:Array<String>,
		?snapshotRoot:String, ?record:Dynamic):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
		#if sys
		if (sourceRoots == null) return result;
		var mappedOwners:Map<String, PreparedMappedAssetOwner> = new Map();
		var mappedCoreOwners:Map<String, PreparedMappedAssetOwner> = new Map();
		var preparedKeys:Map<String, Bool> = new Map();
		for (ownerRoot in sourceRoots) {
			if (importWorkCancelled()) {
				return result;
			}
			if (ownerRoot == null || StringTools.trim(ownerRoot) == '' || !FileSystem.isDirectory(ownerRoot)
				|| findImportFile(ownerRoot, ['meta.json']) == null) continue;
			var ownerKey = importPathKey(ownerRoot);
			var key = mappedAssetOwnerKey(ownerRoot, ImportEngine.NIGHTMARE_VISION);
			if (ownerKey == '' || key == '' || preparedKeys.exists(key)) continue;
			preparedKeys.set(key, true);
			var contentRoot = Path.join([ownerRoot, 'assets']);
			if (!FileSystem.isDirectory(contentRoot)) contentRoot = ownerRoot;
			var scope = authenticatedNightmareVisionScope(ownerRoot, contentRoot);
			var destinationRoot = CompatScriptManifest.destinationRoot(ownerRoot,
				ImportEngine.NIGHTMARE_VISION);
			var plan = SourceMappedMediaPublisher.prepare(ownerRoot,
				ImportEngine.NIGHTMARE_VISION, destinationRoot, scope,
				function():Bool return importWorkCancelled());
			var owner:PreparedMappedAssetOwner = {sourceRoot:ownerRoot,
				engine:ImportEngine.NIGHTMARE_VISION, scope:scope,
				destinationRoot:destinationRoot, plan:plan};
			mappedOwners.set(key, owner);
			if (plan.diagnostics != null)
				for (diagnostic in plan.diagnostics)
					if (diagnostic != null && StringTools.trim(diagnostic) != '') result.errors.push(diagnostic);
			if (plan.cancelled || importWorkCancelled()) {
				return result;
			}
			if (plan.failed) result.failed++;
		}
		var io = ImportIO.current();
		var coreHandoffs:Null<Array<Dynamic>> = null;
		if (snapshotRoot != null && record != null)
			try coreHandoffs = ImportPackageFamilyCatalog.bindCoreAssetHandoffs(snapshotRoot, record, io)
			catch (error:Dynamic) {
				result.failed++;
				result.errors.push("Nightmare Vision core handoff could not be authenticated: " + Std.string(error));
				return result;
			}
		if (coreHandoffs != null) for (handoff in coreHandoffs) {
			if (importWorkCancelled()) return result;
			if (handoff == null || handoff.sourceRoot == null || handoff.destinationRoot == null
				|| handoff.receiverSourceRoot == null || !FileSystem.isDirectory(handoff.sourceRoot)) {
				result.failed++;
				result.errors.push("Nightmare Vision core handoff did not resolve its provider or receiver root.");
				continue;
			}
			var plan = SourceMappedMediaPublisher.prepare(handoff.sourceRoot,
				ImportEngine.NIGHTMARE_VISION, handoff.destinationRoot,
				SourceMappedMediaPolicy.CORE_SCOPE,
				function():Bool return importWorkCancelled());
			var owner:PreparedMappedAssetOwner = {sourceRoot:handoff.sourceRoot,
				engine:ImportEngine.NIGHTMARE_VISION, scope:SourceMappedMediaPolicy.CORE_SCOPE,
				destinationRoot:handoff.destinationRoot, plan:plan};
			var key = mappedAssetOwnerKey(handoff.receiverSourceRoot, ImportEngine.NIGHTMARE_VISION);
			if (key == '' || mappedCoreOwners.exists(key)) {
				result.failed++;
				result.errors.push("Nightmare Vision core handoff has a duplicate or unsafe receiver root.");
				continue;
			}
			mappedCoreOwners.set(key, owner);
			if (plan.diagnostics != null)
				for (diagnostic in plan.diagnostics)
					if (diagnostic != null && StringTools.trim(diagnostic) != '') result.errors.push(diagnostic);
			if (plan.cancelled || importWorkCancelled()) return result;
			if (plan.failed) result.failed++;
		}
		if (result.failed > 0) return result;
		var allMappedOwners:Array<PreparedMappedAssetOwner> = [];
		for (owner in mappedOwners) allMappedOwners.push(owner);
		for (owner in mappedCoreOwners) allMappedOwners.push(owner);
		for (owner in allMappedOwners) {
			if (importWorkCancelled()) {
				return result;
			}
			var published:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
			SourceMappedMediaPublisher.publish(owner.plan,
				function(source:String, destination:String):Void
					copyImportFileNonOverwriting(source, destination, published),
				function():Bool return importWorkCancelled(),
				function(path:String, content:String):Void
					writeImportContentNonOverwriting(content, path, published, true));
			result.copied += published.copied;
			result.skipped += published.skipped;
			result.failed += published.failed;
			if (published.errors != null)
				for (message in published.errors)
					if (message != null && StringTools.trim(message) != '') result.errors.push(message);
			if (owner.plan.cancelled || importWorkCancelled()) {
				return result;
			}
		}
		var seen:Map<String, Bool> = new Map();
		for (ownerRoot in sourceRoots) {
			if (importWorkCancelled()) break;
			if (ownerRoot == null || StringTools.trim(ownerRoot) == '' || !FileSystem.isDirectory(ownerRoot))
				continue;
			var ownerKey = importPathKey(ownerRoot);
			if (ownerKey == '' || seen.exists(ownerKey)) continue;
			seen.set(ownerKey, true);
			// Only an exact file at the package root authorizes config publication.
			// A container-level or song-level meta.json cannot make a sibling a mod.
			var packageConfig = findImportFile(ownerRoot, ['meta.json']);
			if (packageConfig == null) continue;
			var contentRoot = Path.join([ownerRoot, 'assets']);
			if (!FileSystem.isDirectory(contentRoot)) contentRoot = ownerRoot;
			if (!importPathIsWithin(contentRoot, ownerRoot)) {
				result.failed++;
				result.errors.push('Nightmare Vision package content root leaves its owner: ' + ownerRoot);
				continue;
			}
			#if sys
			var canonicalPackageRoot = canonicalNightmareVisionPackageRoot(contentRoot);
			if (canonicalPackageRoot != null && importPathKey(canonicalPackageRoot) == ownerKey)
				retainNightmareVisionPackageNamespace(ownerRoot, contentRoot);
			#end
			var coreAssetsRoot = NightmareVisionAssetCollector.resolveCoreAssetsRoot(ownerRoot);
			var coreIsSelectedRoot = coreAssetsRoot != ''
				&& (importPathKey(coreAssetsRoot) == importPathKey(contentRoot)
					|| importPathKey(coreAssetsRoot) == importPathKey(ownerRoot));
			var mappedOwner = mappedOwnerPlan(mappedOwners, ownerRoot, ImportEngine.NIGHTMARE_VISION);
			var mappedCoreOwner = mappedOwnerPlan(mappedCoreOwners, ownerRoot, ImportEngine.NIGHTMARE_VISION);
			var installedOwnerRoot = mergeCompatScriptTrees(contentRoot, ownerRoot,
				ImportEngine.NIGHTMARE_VISION, result, null, null,
				coreIsSelectedRoot ? NightmareVisionAssetCollector.CORE_SUBTREE : null,
				mappedOwner == null ? null : mappedOwner.plan,
				mappedOwner == null ? '' : mappedOwner.scope);
			if (installedOwnerRoot == null
				|| !importPathIsWithin(installedOwnerRoot, CompatScriptManifest.ROOT_PREFIX)) {
				result.failed++;
				result.errors.push('Could not resolve a staged Nightmare Vision package namespace: ' + ownerRoot);
				continue;
			}
			if (!coreIsSelectedRoot)
				mergeNightmareVisionAssetFiles(contentRoot, installedOwnerRoot, result, null,
					mappedOwner);
			if (coreAssetsRoot != '')
				mergeNightmareVisionAssetFiles(coreAssetsRoot,
					Path.join([installedOwnerRoot, NightmareVisionAssetCollector.CORE_SUBTREE]), result,
				null, coreIsSelectedRoot ? mappedOwner : mappedCoreOwner);
			var stageDestination = coreIsSelectedRoot
				? Path.join([installedOwnerRoot, NightmareVisionAssetCollector.CORE_SUBTREE])
				: installedOwnerRoot;
			mergeNightmareVisionStageDataFiles(contentRoot, stageDestination, result);
		}
		#end
		return result;
	}

	/** Bind an add-on to one proven installed base, preserving its own owner. */
	static function prepareInstalledDependencyRoots(songData:SongImport, sourceRoot:String, engine:String):Void {
		if (songData == null || (engine != ImportEngine.PSYCH && engine != ImportEngine.NIGHTMARE_VISION)
			|| songData.diffFiles == null) return;
		var providers:Array<Dynamic> = [];
		for (path in songData.diffFiles) {
			var chart = readSongChart(path);
			if (chart == null) continue;
			var resolution = ImportInstalledDependencyRoots.resolve(sourceRoot, engine, chart);
			for (diagnostic in resolution.diagnostics) {
				if (songData.diagnostics == null) songData.diagnostics = [];
				if (songData.diagnostics.indexOf(diagnostic) < 0) songData.diagnostics.push(diagnostic);
			}
			for (provider in resolution.providers) {
				var known = false;
				for (existing in providers) if (existing.owner == provider.owner) known = true;
				if (!known) providers.push(provider);
			}
		}
		Reflect.setField(songData, 'installedDependencyRoots', providers);
	}

	/** Add the current donor root to a song's manifest without ever persisting
	 * the donor path.  Existing valid roots are retained so a repaired import
	 * can safely finish after an interrupted previous merge. */
	static function writeCompatScriptManifest(songData:SongImport):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0};
		if (songData == null || songData.sourceRoot == null
			|| StringTools.trim(songData.sourceRoot) == '')
			return result;
		var manifestPath = compatScriptManifestPath(songData);
		if (manifestPath == null)
			return result;
		var ownershipError = ImportSongOwnership.conflict(Path.directory(manifestPath), songData.sourceRoot, songData.engine);
		if (ownershipError != null) {
			result.failed++;
			trace(ownershipError);
			return result;
		}
		var manifest:CompatScriptManifestData = {version:CompatScriptManifest.VERSION, roots:[]};
		if (FileSystem.exists(manifestPath)) {
			try {
				manifest = CompatScriptManifest.parse(File.getContent(manifestPath));
			} catch (_:Dynamic) {
				manifest = {version:CompatScriptManifest.VERSION, roots:[]};
			}
		}
		var desired = CompatScriptManifest.create(songData.sourceRoot, songData.engine);
		var dependencies:Array<Dynamic> = Reflect.field(songData, 'installedDependencyRoots');
		if (dependencies != null)
			for (provider in dependencies)
				if (provider != null)
					desired.roots.push({engine:provider.engine, path:provider.owner, dependency:true});
		desired = CompatScriptManifest.normalize(desired);
		// Thin add-ons may have only song-local Lua and no package-wide trees.
		// Materialize their owner so source APIs still bind to the selected add-on.
		var owner = CompatScriptManifest.selectedRoot(desired);
		if (owner != '' && !FileSystem.exists(Path.join([owner, '.cammie-owner.json']))) {
			try {
				ensureDirectory(owner);
				File.saveContent(Path.join([owner, '.cammie-owner.json']),
					CoolUtil.stringifyJson({engine:songData.engine, version:1}));
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
				return result;
			}
		}
		var changed = false;
		for (wanted in desired.roots) {
			var present = false;
			for (existing in manifest.roots)
				if (existing != null && CompatScriptManifest.destinationKey(existing.path)
					== CompatScriptManifest.destinationKey(wanted.path)) {
					present = true;
					break;
				}
			if (!present) {
				manifest.roots.push(wanted);
				changed = true;
			}
		}
		// Ownership was validated before any writes. A same-donor repair may
		// restore the explicit selected root, but cannot adopt another donor.
		var desiredOwner = CompatScriptManifest.selectedRoot(desired);
		if (desiredOwner != '' && (manifest.selectedRoot == null
			|| CompatScriptManifest.destinationKey(manifest.selectedRoot)
				!= CompatScriptManifest.destinationKey(desiredOwner))) {
			manifest.selectedRoot = desiredOwner;
			changed = true;
		}
		var encoded = CompatScriptManifest.stringify(manifest);
		var existingText:String = null;
		if (FileSystem.exists(manifestPath)) {
			try {
				existingText = File.getContent(manifestPath);
			} catch (_:Dynamic) {}
		}
		if (!changed && existingText == encoded) {
			result.skipped++;
			return result;
		}
		try {
			ensureDirectory(Path.directory(manifestPath));
			File.saveContent(manifestPath, encoded);
			result.copied++;
			reportImportProgress('compat-manifest', manifestPath, 0, 0, 1, 0, 0, 1);
		} catch (_:Dynamic) {
			result.failed++;
			reportImportProgress('compat-manifest', manifestPath, 0, 0, 0, 0, 1, 1);
		}
		return result;
	}

	static function mergeSupportedAssets(sourceRoot:String, importedNames:Map<String, Bool>,
		?importedSources:Map<String, SongImportSource>, ?scriptSourceRoot:String,
		?scriptEngine:String, ?stagedCompatOwnerRoots:Map<String, Bool>,
		?ownerPlan:PreparedMappedAssetOwner,
		?mappedOwnerPlans:Map<String, PreparedMappedAssetOwner>):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0};
		if (sourceRoot == null || !FileSystem.isDirectory(sourceRoot))
			return result;
		if (importPathIsWithin(sourceRoot, 'assets'))
			return result;
		var sharedRoot = findChildDirectory(sourceRoot, 'shared');
		var directData = findChildDirectory(sourceRoot, 'data');
		var directImages = findChildDirectory(sourceRoot, 'images');
		// Packaged Kade/Psych/FPS builds commonly keep the reusable trees below
		// assets/shared while charts/audio stay at assets/data or assets/songs (or
		// charts stay in shared/data).  Treat shared as a logical assets root so
		// its images/scripts land in the destination's ordinary locations instead
		// of being stranded under assets/shared.
		var sharedLayout = sharedRoot != null && (directImages == null
			|| (directData == null && findChildDirectory(sharedRoot, 'data') != null));
		var skipMappedGlobal = function(source:String, destination:String):Bool
			return skipMappedRawFile(ownerPlan, source, destination);

		// Merge registries first, then copy their surrounding trees while telling
		// the file copier not to count the registry a second time.
		var registrySources:Array<{source:String, destination:String}> = [];
		var addRegistry = function(registryRoot:String, sourceRelative:String, destinationRelative:String):Void {
			var source = Path.join([registryRoot, sourceRelative]);
			if (isImportFile(source))
				registrySources.push({source:source, destination:Path.join(['assets', destinationRelative])});
		};
		var registryRoots:Array<String> = [sourceRoot];
		if (sharedLayout)
			registryRoots.push(sharedRoot);
		for (registryRoot in registryRoots) {
			var charsRoot = Path.join([registryRoot, 'images', 'custom_chars']);
			var charsRegistry = findImportFile(charsRoot, ['custom_chars.jsonc', 'custom_chars.json']);
			if (charsRegistry != null)
				addRegistry(registryRoot, Path.join(['images', 'custom_chars', Path.withoutDirectory(charsRegistry)]),
					'images/custom_chars/custom_chars.jsonc');
			addRegistry(registryRoot, 'images/custom_chars/icon_only_chars.json', 'images/custom_chars/icon_only_chars.json');
			addRegistry(registryRoot, 'images/custom_stages/custom_stages.json', 'images/custom_stages/custom_stages.json');
			addRegistry(registryRoot, 'images/custom_cutscenes/cutscenes.json', 'images/custom_cutscenes/cutscenes.json');
			addRegistry(registryRoot, 'images/custom_difficulties/difficulties.json', 'images/custom_difficulties/difficulties.json');
			addRegistry(registryRoot, 'images/custom_ui/ui_packs/ui.json', 'images/custom_ui/ui_packs/ui.json');

			var freeplaySource = FreeplayRegistry.getPathInRoot(registryRoot);
			if (isImportFile(freeplaySource))
				registrySources.push({source:freeplaySource, destination:freeplayRegistryPath()});
			addRegistry(registryRoot, 'data/storySonglist.json', 'data/storySonglist.json');
		}

		var skipPaths:Map<String, Bool> = new Map<String, Bool>();
		for (registry in registrySources) {
			if (importWorkCancelled())
				return result;
			if (skipMappedGlobalFile(ownerPlan, registry.source, registry.destination)) {
				skipPaths.set(importPathKey(registry.source), true);
				continue;
			}
			var merged = (registry.destination == freeplayRegistryPath())
				? mergeFreeplayRegistry(registry.source, importedNames)
				: (registry.destination == 'assets/data/storySonglist.json'
					? mergeStoryRegistry(sourceRoot, importedNames)
					: mergeObjectRegistry(registry.source, registry.destination));
			result.copied += merged.copied;
			result.skipped += merged.skipped;
			result.failed += merged.failed;
			reportImportProgress('registries', registry.destination, 0, 0, merged.copied, merged.skipped, merged.failed,
				merged.copied + merged.skipped + merged.failed > 0 ? 1 : 0);
			skipPaths.set(importPathKey(registry.source), true);
		}

		// Merge only the data/song folders whose imports succeeded.  In
		// particular, a duplicate song is not allowed to gain a missing chart or
		// sidecar from this source tree.  Other ordinary asset trees remain shared
		// dependencies and are merged non-destructively below.
		if (importedNames != null && importedSources != null) {
			for (songKey in importedNames.keys()) {
				if (importWorkCancelled())
					return result;
				var sourceInfo = importedSources.get(songKey);
				if (sourceInfo == null)
					continue;
				if (sourceInfo.song != null && importPathIsWithin(sourceInfo.song, sourceRoot))
					mergeTreeNonOverwriting(sourceInfo.song,
						Path.join(['assets', 'songs', sourceInfo.destination]), 0, result, skipPaths);
				if (sourceInfo.data != null && importPathIsWithin(sourceInfo.data, sourceRoot))
					mergeTreeNonOverwriting(sourceInfo.data,
						Path.join(['assets', 'data', sourceInfo.destination]), 0, result, skipPaths);
			}
		}

		for (relative in supportedAssetTrees(sourceRoot)) {
			if (importWorkCancelled())
				return result;
			if (sharedLayout && relative.toLowerCase() == 'shared')
				continue;
			var source = Path.join([sourceRoot, relative]);
			if (FileSystem.isDirectory(source))
				mergeTreeNonOverwriting(source, Path.join(['assets', relative]), 0, result,
					skipPaths, skipMappedGlobal);
		}
		if (sharedLayout) {
			for (relative in supportedAssetTrees(sharedRoot)) {
				if (importWorkCancelled())
					return result;
				var source = Path.join([sharedRoot, relative]);
				if (FileSystem.isDirectory(source))
					mergeTreeNonOverwriting(source, Path.join(['assets', relative]), 0, result,
						skipPaths, skipMappedGlobal);
			}
		}
		// Foreign global scripts never enter the shared destination tree.  They
		// retain their donor layout below assets/imported_mods/<namespace>, and a
		// song-local manifest written after the copy selects the namespace later.
		var characterChartRoot = scriptSourceRoot == null || StringTools.trim(scriptSourceRoot) == ''
			? sourceRoot : scriptSourceRoot;
		var modPlusCharacterIds = scriptEngine == ImportEngine.MODDING_PLUS
			? modPlusCharactersUsedByImportedSongs(characterChartRoot, importedNames, importedSources) : null;
		mergeCompatScriptTrees(sourceRoot,
			scriptSourceRoot == null || StringTools.trim(scriptSourceRoot) == '' ? sourceRoot : scriptSourceRoot,
			scriptEngine, result, skipPaths, modPlusCharacterIds, null,
			ownerPlan == null ? null : ownerPlan.plan,
			ownerPlan == null ? '' : ownerPlan.scope);
		if (scriptEngine == ImportEngine.NIGHTMARE_VISION)
			mergeSelectedNightmareVisionScriptOwners(importedNames, importedSources,
				scriptSourceRoot == null || StringTools.trim(scriptSourceRoot) == '' ? sourceRoot : scriptSourceRoot,
				result, stagedCompatOwnerRoots, skipPaths, mappedOwnerPlans);
		return result;
	}

	/** Retain Psych's authored Haxe source below its import-owner namespace.
	 * This is source preservation only: imported .hx modules are not executed by
	 * the importer. Bounds and canonical-path checks keep donor traversal inside
	 * the selected source tree, and existing owner files remain authoritative. */
	static function mergePsychSourceModules(sourceRoot:String, ownerRuntimeRoot:String):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0, errors: []};
		if (sourceRoot == null || StringTools.trim(sourceRoot) == '' || ownerRuntimeRoot == null
			|| StringTools.trim(ownerRuntimeRoot) == '')
			return result;
		var sourceDirectory = Path.join([sourceRoot, 'source']);
		if (!FileSystem.isDirectory(sourceDirectory))
			return result;
		if (!importPathIsWithin(sourceDirectory, sourceRoot)) {
			result.failed++;
			result.errors.push('[psych-source-reject] ' + sourceDirectory
				+ ': source directory resolves outside the selected Psych root.');
			return result;
		}
		if (!importPathIsWithin(ownerRuntimeRoot, CompatScriptManifest.ROOT_PREFIX)) {
			result.failed++;
			result.errors.push('[psych-source-reject] ' + ownerRuntimeRoot
				+ ': destination is outside the imported-mod namespace.');
			return result;
		}

		// Psych's full source tree is small, but imported projects are user input.
		// Bound both directory/entry work and bytes read before copying any module.
		var maxDepth = 16;
		var maxDirectories = 2048;
		var maxEntries = 8192;
		var maxFiles = 2048;
		var maxFileBytes = 4 * 1024 * 1024;
		var maxTotalBytes = 16 * 1024 * 1024;
		var entriesVisited = [0];
		var directoriesVisited = [0];
		var filesVisited = [0];
		var bytesCopied = [0];
		var stopped = [false];
		var seenDirectories:Map<String, Bool> = new Map<String, Bool>();
		var destinationSourceRoot = Path.join([ownerRuntimeRoot, 'source']);
		var reject = function(path:String, reason:String, stop:Bool):Void {
			result.failed++;
			result.errors.push('[psych-source-reject] ' + path + ': ' + reason);
			reportImportProgress('psych-source', path, 0, 0, 0, 0, 1, 1);
			if (stop)
				stopped[0] = true;
		};
		var notice = function(path:String, reason:String):Void {
			result.skipped++;
			result.errors.push('[psych-source-skip] ' + path + ': ' + reason);
			reportImportProgress('psych-source', path, 0, 0, 0, 1, 0, 1);
		};
		var destinationFor = function(relative:String):String {
			var path = destinationSourceRoot;
			if (relative == null || relative == '')
				return path;
			for (part in relative.split('/'))
				if (part != '')
					path = existingImportChild(path, part);
			return path;
		};
		var destinationEntryExists = function(path:String):Bool {
			var parent = Path.directory(path);
			var name = Path.withoutDirectory(path);
			if (parent == null || name == null || !FileSystem.isDirectory(parent))
				return false;
			try {
				for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(parent)))
					if (entry.toLowerCase() == name.toLowerCase())
						return true;
			} catch (_:Dynamic) {}
			return false;
		};

		var walk:String->String->Int->Void = null;
		walk = function(directory:String, relativeDirectory:String, depth:Int):Void {
			if (stopped[0] || importWorkCancelled())
				return;
			if (depth > maxDepth) {
				reject(directory, 'source directory depth limit reached (' + maxDepth + ').', false);
				return;
			}
			if (!importPathIsWithin(directory, sourceDirectory)) {
				reject(directory, 'directory resolves outside the selected Psych source tree.', false);
				return;
			}
			var directoryKey = importPathKey(directory);
			if (directoryKey == '') {
				reject(directory, 'could not resolve source directory path.', false);
				return;
			}
			if (seenDirectories.exists(directoryKey)) {
				notice(directory, 'repeated source directory alias or link loop was skipped.');
				return;
			}
			seenDirectories.set(directoryKey, true);
			directoriesVisited[0]++;
			if (directoriesVisited[0] > maxDirectories) {
				reject(directory, 'source directory count limit reached (' + maxDirectories + ').', true);
				return;
			}
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(directory));
			} catch (error:Dynamic) {
				reject(directory, 'could not read source directory: ' + Std.string(error), false);
				return;
			}
			entries.sort(Reflect.compare);
			for (entry in entries) {
				if (stopped[0] || importWorkCancelled())
					return;
				entriesVisited[0]++;
				if (entriesVisited[0] > maxEntries) {
					reject(directory, 'source entry count limit reached (' + maxEntries + ').', true);
					return;
				}
				if (!validImportEntryName(entry)) {
					reject(Path.join([directory, entry]), 'invalid source entry name.', false);
					continue;
				}
				var sourcePath = Path.join([directory, entry]);
				if (!importPathIsWithin(sourcePath, sourceDirectory)) {
					reject(sourcePath, 'source entry resolves outside the selected Psych source tree.', false);
					continue;
				}
				if (!FileSystem.exists(sourcePath)) {
					if (entry.toLowerCase().endsWith('.hx'))
						reject(sourcePath, 'source module disappeared or could not be resolved.', false);
					continue;
				}
				var isDirectory = false;
				try {
					isDirectory = FileSystem.isDirectory(sourcePath);
				} catch (error:Dynamic) {
					reject(sourcePath, 'could not inspect source entry: ' + Std.string(error), false);
					continue;
				}
				if (isDirectory) {
					var childRelative = relativeDirectory == '' ? entry : relativeDirectory + '/' + entry;
					var destinationDirectory = destinationFor(childRelative);
					if (!importPathIsWithin(destinationDirectory, ownerRuntimeRoot)) {
						reject(destinationDirectory, 'destination directory resolves outside its import owner.', false);
						continue;
					}
					if (FileSystem.exists(destinationDirectory) && !FileSystem.isDirectory(destinationDirectory)) {
						notice(destinationDirectory, 'an existing owner file blocks this source directory.');
						continue;
					}
					walk(sourcePath, childRelative, depth + 1);
					continue;
				}
				if (!entry.toLowerCase().endsWith('.hx'))
					continue;
				filesVisited[0]++;
				if (filesVisited[0] > maxFiles) {
					reject(sourcePath, 'Haxe source file limit reached (' + maxFiles + ').', true);
					return;
				}
				var relativeFile = relativeDirectory == '' ? entry : relativeDirectory + '/' + entry;
				var destinationPath = destinationFor(relativeFile);
				if (!importPathIsWithin(destinationPath, ownerRuntimeRoot)) {
					reject(destinationPath, 'destination file resolves outside its import owner.', false);
					continue;
				}
				if (destinationEntryExists(destinationPath)) {
					result.skipped++;
					reportImportProgress('psych-source', destinationPath, 0, 0, 0, 1, 0, 1);
					continue;
				}
				var sourceSize:Int;
				try {
					var sourceStat = FileSystem.stat(sourcePath);
					sourceSize = sourceStat.size;
				} catch (error:Dynamic) {
					reject(sourcePath, 'could not inspect Haxe source size: ' + Std.string(error), false);
					continue;
				}
				if (sourceSize <= 0) {
					reject(sourcePath, 'empty or unsupported Haxe source entry.', false);
					continue;
				}
				if (sourceSize > maxFileBytes) {
					reject(sourcePath, 'Haxe source file size exceeds ' + maxFileBytes + ' bytes.', false);
					continue;
				}
				var remainingBytes = maxTotalBytes - bytesCopied[0];
				if (sourceSize > remainingBytes) {
					reject(sourcePath, 'total Haxe source byte limit reached (' + maxTotalBytes + ').', true);
					return;
				}
				var readLimit = Std.int(Math.min(maxFileBytes, remainingBytes));
				var readCapacity = Std.int(Math.min(sourceSize + 1, readLimit + 1));
				var boundedBytes = haxe.io.Bytes.alloc(readCapacity);
				var sourceInput:sys.io.FileInput = null;
				try {
					sourceInput = File.read(sourcePath, true);
				} catch (error:Dynamic) {
					reject(sourcePath, 'could not open Haxe source: ' + Std.string(error), false);
					continue;
				}
				var byteCount = 0;
				var readError:Dynamic = null;
				try {
					while (byteCount < readCapacity) {
						boundedBytes.set(byteCount, sourceInput.readByte());
						byteCount++;
					}
				} catch (_:haxe.io.Eof) {
				} catch (error:Dynamic) {
					readError = error;
				}
				try {
					sourceInput.close();
				} catch (error:Dynamic) {
					if (readError == null)
						readError = error;
				}
				if (readError != null) {
					reject(sourcePath, 'could not read Haxe source: ' + Std.string(readError), false);
					continue;
				}
				if (byteCount != sourceSize) {
					reject(sourcePath, 'Haxe source size changed while it was being read.', false);
					continue;
				}
				try {
					ensureDirectory(Path.directory(destinationPath));
					if (!importPathIsWithin(destinationPath, ownerRuntimeRoot)) {
						reject(destinationPath, 'destination changed to a path outside its import owner.', false);
						continue;
					}
					if (destinationEntryExists(destinationPath)) {
						result.skipped++;
						reportImportProgress('psych-source', destinationPath, 0, 0, 0, 1, 0, 1);
						continue;
					}
					File.saveBytes(destinationPath, boundedBytes.sub(0, byteCount));
					bytesCopied[0] += byteCount;
					result.copied++;
					reportImportProgress('psych-source', destinationPath, 0, 0, 1, 0, 0, 1);
				} catch (error:Dynamic) {
					reject(sourcePath, 'could not copy Haxe source into owner namespace: ' + Std.string(error), false);
				}
			}
		};

		walk(sourceDirectory, '', 0);
		return result;
	}

	/** Psych sound IDs resolve through the selected import owner's namespace.
	 * Retain the donor's sound tree there and repair absent files on a repeat
	 * import without replacing an existing owner override. */
	static function mergePsychRuntimeSounds(sourceRoot:String, runtimeNamespace:String,
		?mappedOwner:PreparedMappedAssetOwner):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0, errors: []};
		if (sourceRoot == null || runtimeNamespace == null || runtimeNamespace == ''
			|| !FileSystem.isDirectory(sourceRoot))
			return result;
		var skipPaths:Map<String, Bool> = new Map<String, Bool>();
		var roots = [sourceRoot];
		var shared = findChildDirectory(sourceRoot, 'shared');
		if (shared != null)
			roots.push(shared);
		for (root in roots) {
			var sounds = findChildDirectory(root, 'sounds');
			if (sounds != null) {
				var skipMapped = function(source:String, destination:String):Bool
					return mappedOwner != null
						&& skipMappedOwnerMediaFile(mappedOwner, source, destination);
				mergeTreeNonOverwriting(sounds, Path.join([runtimeNamespace, 'sounds']),
					0, result, skipPaths, skipMapped);
			}
		}
		return result;
	}

	/** Keep Psych media folders with the selected compiled-module owner while
	 * preserving their paths as mapped by Project.xml (for example
	 * weekend1/images, week3/sounds and shared/images). Only mapped media
	 * directories are copied; charts, songs and scripts keep their existing
	 * import paths. */
	static function mergePsychRuntimeMedia(sourceRoot:String, destinationPrefix:String,
		runtimeNamespace:String,
		?mappedOwner:PreparedMappedAssetOwner):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
		if (sourceRoot == null || StringTools.trim(sourceRoot) == '' || !FileSystem.isDirectory(sourceRoot))
			return result;
		var ownerRoot = psychDestinationAssetRoot(runtimeNamespace);
		if (ownerRoot == '' || ownerRoot == 'assets') {
			result.failed++;
			result.errors.push('[psych-media-reject] Destination is outside an imported owner namespace: '
				+ Std.string(runtimeNamespace));
			return result;
		}
		var prefix = StringTools.replace(StringTools.trim(destinationPrefix == null ? '' : destinationPrefix), '\\', '/');
		while (StringTools.endsWith(prefix, '/'))
			prefix = prefix.substr(0, prefix.length - 1);
		if (prefix != '') {
			if (StringTools.startsWith(prefix, '/') || prefix.indexOf(':') >= 0) {
				result.failed++;
				result.errors.push('[psych-media-reject] Invalid mapped asset prefix: ' + prefix);
				return result;
			}
			for (part in prefix.split('/'))
				if (!validImportEntryName(part)) {
					result.failed++;
					result.errors.push('[psych-media-reject] Invalid mapped asset prefix: ' + prefix);
					return result;
				}
		}

		// Psych Paths.sound resolves the active library before shared. Keep
		// mapped week/library sound trees at their Project.xml relative paths;
		// mergePsychRuntimeSounds also retains the legacy flat shared fallback.
		var mediaFolders:Map<String, Bool> = new Map<String, Bool>();
		for (name in ['images', 'videos', 'fonts', 'shaders', 'animations', 'sounds', 'music'])
			mediaFolders.set(name, true);
		var excludedTrees:Map<String, Bool> = new Map<String, Bool>();
		for (name in ['data', 'songs', 'source', 'scripts', 'mods', 'export', 'bin', '.git'])
			excludedTrees.set(name, true);
		var maxDepth = 8;
		var maxDirectories = 8192;
		var directoriesVisited = [0];
		var seenDirectories:Map<String, Bool> = new Map<String, Bool>();
		var walk:String->String->Int->Void = null;
		walk = function(directory:String, relative:String, depth:Int):Void {
			if (importWorkCancelled())
				return;
			if (depth > maxDepth) {
				result.failed++;
				result.errors.push('[psych-media-skip] Directory depth limit reached: ' + directory);
				return;
			}
			if (!importPathIsWithin(directory, sourceRoot)) {
				result.failed++;
				result.errors.push('[psych-media-reject] Source directory escaped its mapped root: ' + directory);
				return;
			}
			var directoryKey = importPathKey(directory);
			if (directoryKey == '' || seenDirectories.exists(directoryKey))
				return;
			seenDirectories.set(directoryKey, true);
			directoriesVisited[0]++;
			if (directoriesVisited[0] > maxDirectories) {
				result.failed++;
				result.errors.push('[psych-media-skip] Directory count limit reached (' + maxDirectories + ').');
				return;
			}
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(directory));
				entries.sort(Reflect.compare);
			} catch (error:Dynamic) {
				result.failed++;
				result.errors.push('[psych-media-skip] Could not inspect ' + directory + ': ' + Std.string(error));
				return;
			}
			for (entry in entries) {
				if (importWorkCancelled())
					return;
				if (!validImportEntryName(entry)) {
					result.failed++;
					continue;
				}
				var source = Path.join([directory, entry]);
				if (!FileSystem.isDirectory(source))
					continue;
				var childRelative = relative == '' ? entry : relative + '/' + entry;
				var lower = entry.toLowerCase();
				if (mediaFolders.exists(lower)) {
					if (!importPathIsWithin(source, sourceRoot)) {
						result.failed++;
						result.errors.push('[psych-media-reject] Media directory escaped its mapped root: ' + source);
						continue;
					}
					var mappedRelative = prefix == '' ? childRelative : prefix + '/' + childRelative;
					mergePsychMediaTree(source, Path.join([ownerRoot, mappedRelative]), sourceRoot,
						ownerRoot, 0, result, new Map<String, Bool>(), mappedOwner);
				} else if (!excludedTrees.exists(lower)) {
					walk(source, childRelative, depth + 1);
				}
			}
		};
		walk(sourceRoot, '', 0);
		return result;
	}

	/** Copy one mapped media subtree while checking every entry's canonical
	 * source path. The generic asset copier follows symlinks, so this owner copy
	 * rejects any link that would read outside the selected donor root. */
	static function mergePsychMediaTree(source:String, destination:String, sourceRoot:String,
		ownerRoot:String, depth:Int, result:ImportAssetMergeResult, seen:Map<String, Bool>,
		?mappedOwner:PreparedMappedAssetOwner):Void {
		if (importWorkCancelled() || source == null || destination == null || depth > 10
			|| !FileSystem.isDirectory(source))
			return;
		if (!importPathIsWithin(source, sourceRoot)) {
			result.failed++;
			result.errors.push('[psych-media-reject] Source entry escaped its mapped root: ' + source);
			return;
		}
		if (!importPathIsWithin(destination, ownerRoot)) {
			result.failed++;
			result.errors.push('[psych-media-reject] Destination media directory escaped its owner: ' + destination);
			return;
		}
		var sourceKey = importPathKey(source);
		if (sourceKey == '' || seen.exists(sourceKey))
			return;
		seen.set(sourceKey, true);
		if (FileSystem.exists(destination) && !FileSystem.isDirectory(destination)) {
			result.skipped++;
			return;
		}
		var entries:Array<String>;
		try {
			entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(source));
			entries.sort(Reflect.compare);
		} catch (error:Dynamic) {
			result.failed++;
			result.errors.push('[psych-media-skip] Could not inspect ' + source + ': ' + Std.string(error));
			return;
		}
		if (!FileSystem.exists(destination)) {
			try ensureDirectory(destination) catch (error:Dynamic) {
				result.failed++;
				result.errors.push('[psych-media-skip] Could not create ' + destination + ': ' + Std.string(error));
				return;
			}
		}
		if (!importPathIsWithin(destination, ownerRoot)) {
			result.failed++;
			result.errors.push('[psych-media-reject] Destination media directory escaped its owner: ' + destination);
			return;
		}
		for (entry in entries) {
			if (importWorkCancelled())
				return;
			if (!validImportEntryName(entry)) {
				result.failed++;
				continue;
			}
			var sourcePath = Path.join([source, entry]);
			if (!FileSystem.exists(sourcePath))
				continue;
			if (!importPathIsWithin(sourcePath, sourceRoot)) {
				result.failed++;
				result.errors.push('[psych-media-reject] Source entry escaped its mapped root: ' + sourcePath);
				continue;
			}
			var destinationPath = existingImportChild(destination, entry);
			if (FileSystem.isDirectory(sourcePath)) {
				if (FileSystem.exists(destinationPath) && !FileSystem.isDirectory(destinationPath)) {
					result.skipped++;
					continue;
				}
				mergePsychMediaTree(sourcePath, destinationPath, sourceRoot, ownerRoot, depth + 1,
					result, seen, mappedOwner);
				continue;
			}
			if (mappedOwner != null
				&& skipMappedOwnerMediaFile(mappedOwner, sourcePath, destinationPath)) {
				result.skipped++;
				continue;
			}
			if (FileSystem.exists(destinationPath)) {
				result.skipped++;
				continue;
			}
			try {
				if (!importPathIsWithin(destinationPath, ownerRoot)) {
					result.failed++;
					result.errors.push('[psych-media-reject] Destination file escaped its owner: ' + destinationPath);
					continue;
				}
				ensureDirectory(Path.directory(destinationPath));
				if (!importPathIsWithin(destinationPath, ownerRoot)) {
					result.failed++;
					result.errors.push('[psych-media-reject] Destination file escaped its owner: ' + destinationPath);
					continue;
				}
				if (FileSystem.exists(destinationPath)) {
					result.skipped++;
					continue;
				}
				File.copy(sourcePath, destinationPath);
				result.copied++;
			} catch (error:Dynamic) {
				result.failed++;
				result.errors.push('[psych-media-skip] Could not copy ' + sourcePath + ': ' + Std.string(error));
			}
		}
	}

	/** Copy only V-Slice trees whose formats are runtime-compatible as-is. */
	static function mergeVSliceRuntimeAssets(sourceRoot:String, ?scriptSourceRoot:String,
		?scriptEngine:String, ?selectedSongs:Map<String, SongImport>,
		?libraryRoots:Array<String>):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0, errors: []};
		if (sourceRoot == null || !FileSystem.isDirectory(sourceRoot))
			return result;
		var skipPaths:Map<String, Bool> = new Map<String, Bool>();
		// V-Slice scripts are selected through a song-local compatibility
		// manifest. Keep their runtime assets in that same namespace instead of
		// flattening identically named shaders from unrelated imports into the
		// shared assets/shaders tree.
		var runtimeNamespace = CompatScriptManifest.destinationRoot(
			scriptSourceRoot == null || StringTools.trim(scriptSourceRoot) == '' ? sourceRoot : scriptSourceRoot,
			scriptEngine == null ? ImportEngine.V_SLICE : scriptEngine);
		var roots = [sourceRoot];
		var shared = findChildDirectory(sourceRoot, 'shared');
		if (shared != null)
			roots.push(shared);
		for (root in roots)
			for (relative in ['sounds', 'music', 'videos', 'fonts', 'shaders']) {
				if (importWorkCancelled())
					return result;
				var source = findChildDirectory(root, relative);
				if (source != null)
					mergeTreeNonOverwriting(source, Path.join([runtimeNamespace, relative]), 0, result, skipPaths);
			}
		var sidecars = mergeVSliceSongSidecars(sourceRoot, runtimeNamespace, selectedSongs, skipPaths);
		result.copied += sidecars.copied;
		result.skipped += sidecars.skipped;
		result.failed += sidecars.failed;
		if (sidecars.errors != null)
			for (message in sidecars.errors)
				result.errors.push(message);
		mergeVSliceEventAssets(sourceRoot, runtimeNamespace, result, skipPaths);
		mergeVSliceHxcStaticAssets(sourceRoot, scriptSourceRoot, scriptEngine, runtimeNamespace, result,
			libraryRoots, selectedSongs);
		mergeCompatScriptTrees(sourceRoot,
			scriptSourceRoot == null || StringTools.trim(scriptSourceRoot) == '' ? sourceRoot : scriptSourceRoot,
			scriptEngine, result, skipPaths);
		return result;
	}

	/** Copy selected V-Slice song sidecars into the same owner namespace as
		HXC scripts. Chart and metadata documents are already converted into the
		native song folder and must not be duplicated as opaque runtime files. */
	static function mergeVSliceSongSidecars(sourceRoot:String, ownerRoot:String,
		selectedSongs:Map<String, SongImport>, ?skipPaths:Map<String, Bool>):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0, errors: []};
		if (sourceRoot == null || ownerRoot == null || selectedSongs == null
			|| !FileSystem.isDirectory(sourceRoot))
			return result;
		var sourceDataRoot = findChildDirectory(sourceRoot, 'data');
		var songsRoot = findChildDirectory(sourceDataRoot, 'songs');
		if (songsRoot == null)
			return result;
		if (!importPathIsWithin(sourceDataRoot, sourceRoot) || !importPathIsWithin(songsRoot, sourceRoot)) {
			result.failed++;
			result.errors.push('[vslice-song-sidecar-escape] Rejected a songs data root outside the selected source: ' + songsRoot);
			return result;
		}
		for (songData in selectedSongs) {
			if (importWorkCancelled())
				break;
			if (songData == null || songData.engine != ImportEngine.V_SLICE
				|| songData.vSliceRoot == null
				|| importPathKey(songData.vSliceRoot) != importPathKey(sourceRoot)
				|| songData.importSourceInfo == null)
				continue;
			var sourceSong = songData.importSourceInfo.data;
			var destinationFolder = importSongFolderName(songData);
			if (sourceSong == null || destinationFolder == '' || !validModuleName(destinationFolder)
				|| !FileSystem.isDirectory(sourceSong) || !importPathIsWithin(sourceSong, songsRoot)
				|| !importPathIsWithin(sourceSong, sourceRoot))
				continue;
			var sourceSongId = Path.withoutDirectory(Path.normalize(sourceSong));
			mergeVSliceSongSidecarTree(sourceSong, sourceSong, sourceSongId,
				'songs/' + destinationFolder, ownerRoot, '', 0, result, skipPaths);
		}
		return result;
	}

	static function mergeVSliceSongSidecarTree(source:String, sourceSongRoot:String, sourceSongId:String,
		destinationSongKey:String, ownerRoot:String, relative:String, depth:Int,
		result:ImportAssetMergeResult, skipPaths:Map<String, Bool>):Void {
		if (importWorkCancelled() || source == null || depth > 10)
			return;
		if (!importPathIsWithin(source, sourceSongRoot)) {
			result.failed++;
			result.errors.push('[vslice-song-sidecar-escape] Rejected a sidecar outside its selected song folder: ' + source);
			return;
		}
		if (FileSystem.isDirectory(source)) {
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(source));
			} catch (error:Dynamic) {
				result.failed++;
				result.errors.push('[vslice-song-sidecar-read] Could not list ' + source + ': ' + Std.string(error));
				return;
			}
			entries.sort(function(a:String, b:String):Int {
				var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
				return lower == 0 ? Reflect.compare(a, b) : lower;
			});
			for (entry in entries) {
				if (!validImportEntryName(entry)) {
					result.failed++;
					result.errors.push('[vslice-song-sidecar-name] Rejected an unsafe entry in ' + source);
					continue;
				}
				var childRelative = relative == '' ? entry : Path.join([relative, entry]);
				mergeVSliceSongSidecarTree(Path.join([source, entry]), sourceSongRoot, sourceSongId,
					destinationSongKey, ownerRoot, childRelative, depth + 1, result, skipPaths);
			}
			return;
		}
		if (!FileSystem.exists(source))
			return;
		var sourceFile = Path.withoutDirectory(source).toLowerCase();
		var sourcePrefix = sourceSongId == null ? '' : sourceSongId.toLowerCase();
		var lowerRelative = StringTools.replace(relative, '\\', '/').toLowerCase();
		var sourceChartDocument = lowerRelative.indexOf('/') < 0 && sourcePrefix != ''
			&& (sourceFile == sourcePrefix + '-chart.json' || sourceFile == sourcePrefix + '-chart.jsonc'
				|| sourceFile == sourcePrefix + '-metadata.json' || sourceFile == sourcePrefix + '-metadata.jsonc'
				|| (StringTools.startsWith(sourceFile, sourcePrefix + '-chart-')
					&& (StringTools.endsWith(sourceFile, '.json') || StringTools.endsWith(sourceFile, '.jsonc')))
				|| (StringTools.startsWith(sourceFile, sourcePrefix + '-metadata-')
					&& (StringTools.endsWith(sourceFile, '.json') || StringTools.endsWith(sourceFile, '.jsonc'))));
		if (sourceChartDocument || (skipPaths != null && skipPaths.exists(importPathKey(source))))
			return;
		var childKey = destinationSongKey + '/' + StringTools.replace(relative, '\\', '/');
		var ownerRelative = HxcOwnedPath.songDataRelative(childKey);
		var destination = ownerRelative == null ? null : Path.join([ownerRoot, ownerRelative]);
		if (destination == null || !importPathIsWithin(destination, ownerRoot)) {
			result.failed++;
			result.errors.push('[vslice-song-sidecar-path] Could not map selected sidecar: ' + relative);
			return;
		}
		var existingDestination = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
		if (FileSystem.exists(existingDestination)) {
			if (FileSystem.isDirectory(existingDestination)) {
				result.failed++;
				result.errors.push('[vslice-song-sidecar-conflict] Destination is a directory: ' + existingDestination);
			} else {
				result.skipped++;
				reportImportProgress('vslice-song-sidecars', existingDestination, 0, 0, 0, 1, 0, 1);
			}
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			File.copy(source, destination);
			result.copied++;
			reportImportProgress('vslice-song-sidecars', destination, 0, 0, 1, 0, 0, 1);
		} catch (error:Dynamic) {
			result.failed++;
			result.errors.push('[vslice-song-sidecar-copy] Could not copy ' + source + ': ' + Std.string(error));
		}
	}

	/**
		Retain only media explicitly owned by a routed HXC event. V-Slice's general
		image tree is intentionally not flattened (it can be very large), but a
		compatibility event still needs its authored atlas to be discoverable through
		the song manifest. ASTC event textures cross the portable decoder boundary
		into a native PNG; XML companions remain unchanged. The source identity is
		inspected read-only and all outputs stay under the event script's namespace.
	*/
	static function mergeVSliceEventAssets(sourceRoot:String, runtimeNamespace:String,
		result:ImportAssetMergeResult, skipPaths:Map<String, Bool>):Void {
		if (sourceRoot == null || runtimeNamespace == null || !FileSystem.isDirectory(sourceRoot))
			return;
		var sourceRoots:Array<String> = [sourceRoot];
		var sharedRoot = findChildDirectory(sourceRoot, 'shared');
		if (sharedRoot != null && sourceRoots.indexOf(sharedRoot) < 0)
			sourceRoots.push(sharedRoot);
		var eventDirectories:Array<String> = [];
		for (root in sourceRoots) {
			if (root == null)
				continue;
			var events = findChildDirectory(findChildDirectory(root, 'scripts'), 'events');
			if (events != null && eventDirectories.indexOf(events) < 0)
				eventDirectories.push(events);
		}
		var descriptors:Array<Dynamic> = [];
		for (events in eventDirectories) {
			var entries:Array<String>;
			try {
				entries = ImportDirectoryListing.normalize(FileSystem.readDirectory(events));
			} catch (_:Dynamic) {
				continue;
			}
			for (entry in entries) {
				if (!validImportEntryName(entry) || !entry.toLowerCase().endsWith('.hxc'))
					continue;
				var path = Path.join([events, entry]);
				if (!isImportFile(path))
					continue;
				try {
					var descriptor = EngineCompat.eventSpriteDescriptorFromSource(File.getContent(path));
					if (descriptor != null)
						descriptors.push(descriptor);
				} catch (_:Dynamic) {}
			}
		}
		// Persist only validated literal metadata below the destination namespace.
		// A pre-existing import without this file can still derive descriptors at
		// runtime from its bounded scripts/events folder.
		var catalogContents = HxcEventSpriteDescriptor.serializeCatalog(descriptors);
		descriptors = HxcEventSpriteDescriptor.parseCatalog(catalogContents);
		var catalogPath = Path.join([runtimeNamespace, HxcEventSpriteDescriptor.CATALOG_FILE]);
		try {
			ensureDirectory(runtimeNamespace);
			File.saveContent(catalogPath, catalogContents);
			result.copied++;
		} catch (error:Dynamic) {
			result.failed++;
			if (result.errors == null)
				result.errors = [];
			result.errors.push('Could not write destination HXC event descriptor catalog: ' + Std.string(error));
		}
		for (descriptor in descriptors) {
			if (importWorkCancelled())
				return;
			var atlasKey = HxcEventSpriteDescriptor.safeAtlasKey(Std.string(Reflect.field(descriptor, 'atlasKey')));
			var atlasType = Std.string(Reflect.field(descriptor, 'atlasType'));
			if (atlasKey == '' || (atlasType != 'sparrow' && atlasType != 'packer'))
				continue;
			var metadataExtension = atlasType == 'packer' ? '.txt' : '.xml';
			var imageSource:String = null;
			var metadataSource:String = null;
			for (root in sourceRoots) {
				if (root == null)
					continue;
				var images = findChildDirectory(root, 'images');
				if (images == null)
					continue;
				var metadata = existingImportRelative(images, atlasKey + metadataExtension);
				if (!isImportFile(metadata))
					continue;
				var png = existingImportRelative(images, atlasKey + '.png');
				var astc = existingImportRelative(images, atlasKey + '.astc');
				if (isImportFile(png)) {
					imageSource = png;
				} else if (isImportFile(astc)) {
					imageSource = astc;
				} else
					continue;
				metadataSource = metadata;
				break;
			}
			if (imageSource == null || metadataSource == null)
				continue;
			var destinationBase = Path.join([runtimeNamespace, 'images', atlasKey]);
			mergeVSliceEventFile(imageSource, destinationBase + '.png', result, skipPaths);
			mergeVSliceEventFile(metadataSource, destinationBase + metadataExtension, result, skipPaths);
		}
	}

	/** Resolve a safe nested donor path one case-insensitive component at a time. */
	static function existingImportRelative(parent:String, relative:String):String {
		if (parent == null || relative == null)
			return null;
		var clean = StringTools.replace(StringTools.trim(relative), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0)
			return null;
		var current = parent;
		for (part in clean.split('/')) {
			if (part == '' || part == '.' || part == '..' || !validImportEntryName(part))
				return null;
			current = existingImportChild(current, part);
		}
		return current;
	}

	/** Copy one event-owned asset, decoding ASTC to a native PNG when required. */
	static function mergeVSliceEventFile(source:String, destination:String,
		result:ImportAssetMergeResult, skipPaths:Map<String, Bool>):Void {
		if (importWorkCancelled() || !validImportPath(source))
			return;
		if (skipPaths != null && skipPaths.exists(importPathKey(source)))
			return;
		var existingDestination = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
		if (FileSystem.exists(existingDestination)) {
			result.skipped++;
			reportImportProgress('vslice-event-assets', existingDestination, 0, 0, 0, 1, 0, 1);
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			if (source.toLowerCase().endsWith('.astc')) {
				var decoded = VSliceAstcAdapter.decodeFile(source, destination);
				if (!decoded.success) {
					result.failed++;
					if (result.errors == null)
						result.errors = [];
					var detail = decoded.message;
					try {
						var header = VSliceAstcAdapter.inspectFile(source);
						var exactDiagnostic = VSliceAstcAdapter.diagnostic(source, header);
						if (detail == null || StringTools.trim(detail) == '' || detail.indexOf(exactDiagnostic) < 0)
							detail = exactDiagnostic + (detail == null || StringTools.trim(detail) == '' ? '' : ' ' + detail);
					} catch (_:Dynamic) {}
					result.errors.push(detail);
					trace('[astc-conversion] ' + detail);
					reportImportProgress('vslice-event-assets', source, 0, 0, 0, 0, 1, 1);
					return;
				}
			} else
				File.copy(source, destination);
			result.copied++;
			reportImportProgress('vslice-event-assets', destination, 0, 0, 1, 0, 0, 1);
		} catch (_:Dynamic) {
			result.failed++;
			reportImportProgress('vslice-event-assets', source, 0, 0, 0, 0, 1, 1);
		}
	}

	static function vSliceMappingDestination(base:String, relative:String):String {
		if (base == null || relative == null || StringTools.trim(relative) == '')
			return null;
		var clean = StringTools.replace(StringTools.trim(relative), '\\', '/');
		if (clean.startsWith('/') || clean.indexOf(':') == 1)
			return null;
		var destination = Path.normalize(Path.join([base, clean]));
		return importPathIsWithin(destination, base) ? destination : null;
	}

	static function mergeVSliceMapping(mapping:VSliceImporter.VSliceAssetMapping, base:String,
		result:ImportAssetMergeResult):Void {
		if (mapping == null || !mapping.supported)
			return;
		var destination = vSliceMappingDestination(base, mapping.destination);
		if (destination == null || !validImportPath(mapping.source))
			return;
		// Destination asset names are generated in a stable lower-case form, but
		// an older import or a Windows donor may already have the same file with
		// different casing. Resolve the existing child before copying so Linux
		// does not create a second case-variant file and the non-overwrite rule
		// remains consistent across platforms.
		var existingDestination = existingImportChild(Path.directory(destination), Path.withoutDirectory(destination));
		if (FileSystem.exists(existingDestination)) {
			result.skipped++;
			reportImportProgress('vslice-assets', existingDestination, 0, 0, 0, 1, 0, 1);
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			if (mapping.requiresConversion == true) {
				var decoded = VSliceAstcAdapter.decodeFile(mapping.source, destination);
				if (!decoded.success) {
					result.failed++;
					if (result.errors == null)
						result.errors = [];
					result.errors.push(decoded.message);
					trace('[astc-conversion] ' + decoded.message);
					reportImportProgress('vslice-assets', destination, 0, 0, 0, 0, 1, 1);
					return;
				}
			} else
				File.copy(mapping.source, destination);
			result.copied++;
			reportImportProgress('vslice-assets', destination, 0, 0, 1, 0, 0, 1);
		} catch (error:Dynamic) {
			result.failed++;
			reportImportProgress('vslice-assets', destination, 0, 0, 0, 0, 1, 1);
		}
	}

	static function writeVSliceHScript(destination:String, contents:String,
		result:ImportAssetMergeResult):Void {
		if (destination == null || contents == null || StringTools.trim(contents) == '')
			return;
		if (FileSystem.exists(destination)) {
			result.skipped++;
			reportImportProgress('vslice-scripts', destination, 0, 0, 0, 1, 0, 1);
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			File.saveContent(destination, contents);
			result.copied++;
			reportImportProgress('vslice-scripts', destination, 0, 0, 1, 0, 0, 1);
		} catch (error:Dynamic) {
			result.failed++;
			reportImportProgress('vslice-scripts', destination, 0, 0, 0, 0, 1, 1);
		}
	}

	static function chooseVSliceRegistry(pathJsonc:String, pathJson:String):String {
		if (FileSystem.exists(pathJsonc) && !FileSystem.isDirectory(pathJsonc))
			return pathJsonc;
		if (FileSystem.exists(pathJson) && !FileSystem.isDirectory(pathJson))
			return pathJson;
		return pathJsonc;
	}

	static function registryHasVSliceKey(value:Dynamic, key:String):Bool {
		if (value == null || key == null || StringTools.trim(key) == '')
			return false;
		for (existing in Reflect.fields(value))
			if (existing.toLowerCase() == key.toLowerCase())
				return true;
		return false;
	}

	static function mergeVSliceRegistryEntry(path:String, key:String, value:Dynamic,
		result:ImportAssetMergeResult, ?exactKey:Bool = false,
		?upgradeHealthIconRequired:Bool = false):Void {
		if (path == null || key == null || StringTools.trim(key) == '' || value == null)
			return;
		var registry:Dynamic = null;
		if (FileSystem.exists(path)) {
			try {
				registry = CoolUtil.parseJson(File.getContent(path));
			} catch (error:Dynamic) {
				result.failed++;
				return;
			}
		}
		if (registry == null)
			registry = {};
		if (Std.isOfType(registry, Array)) {
			result.failed++;
			return;
		}
		var existingKey:String = null;
		if (exactKey && Reflect.hasField(registry, key))
			existingKey = key;
		else if (!exactKey)
			for (candidate in Reflect.fields(registry))
				if (candidate.toLowerCase() == key.toLowerCase()) {
					existingKey = candidate;
					break;
				}
		if (existingKey != null) {
			// V-Slice can discover the same character as an unreferenced package
			// definition before another song's chart proves its HUD role. Preserve
			// imported metadata/files, but allow the same selected owner's later
			// proof to strengthen the existing icon requirement monotonically.
			var existingEntry:Dynamic = Reflect.field(registry, existingKey);
			if (upgradeHealthIconRequired && value != null && existingEntry != null
				&& Reflect.field(value, 'vSliceHealthIconRequired') == true
				&& Reflect.field(existingEntry, 'vSliceHealthIconRequired') != true) {
				Reflect.setField(existingEntry, 'vSliceHealthIconRequired', true);
				try {
					File.saveContent(path, CoolUtil.stringifyJson(registry));
					result.copied++;
					reportImportProgress('vslice-registries', path, 0, 0, 1, 0, 0, 1);
				} catch (error:Dynamic) {
					result.failed++;
					reportImportProgress('vslice-registries', path, 0, 0, 0, 0, 1, 1);
				}
				return;
			}
			result.skipped++;
			reportImportProgress('vslice-registries', path, 0, 0, 0, 1, 0, 1);
			return;
		}
		try {
			Reflect.setField(registry, key, value);
			ensureDirectory(Path.directory(path));
			File.saveContent(path, CoolUtil.stringifyJson(registry));
			result.copied++;
			reportImportProgress('vslice-registries', path, 0, 0, 1, 0, 0, 1);
		} catch (error:Dynamic) {
			result.failed++;
			reportImportProgress('vslice-registries', path, 0, 0, 0, 0, 1, 1);
		}
	}

	static function importVSliceCharacterConversion(importData:VSliceCharacterImport,
		result:ImportAssetMergeResult, ?destinationAssetRoot:String = 'assets',
		?exactRegistryKey:Bool = false, ?upgradeHealthIconRequired:Bool = false):Void {
		if (importData == null || importData.conversion == null)
			return;
		var conversion = importData.conversion;
		if (Reflect.field(conversion, 'supported') == false) {
			result.skipped++;
			return;
		}
		var name = StringTools.trim(conversion.name);
		if (!validModuleName(name))
			return;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '') {
			result.failed++;
			return;
		}
		var folder = Path.join([assetRoot, 'images', 'custom_chars', name]);
		if (FileSystem.exists(folder) && !FileSystem.isDirectory(folder)) {
			result.failed++;
			return;
		}
		ensureDirectory(folder);
		if (conversion.assets != null)
			for (mapping in conversion.assets)
				mergeVSliceMapping(mapping, folder, result);
		writeVSliceHScript(Path.join([assetRoot, 'images', 'custom_chars', name + '.hscript']),
			conversion.hscript, result);
		mergeVSliceRegistryEntry(chooseVSliceRegistry(
			Path.join([assetRoot, 'images', 'custom_chars', 'custom_chars.jsonc']),
			Path.join([assetRoot, 'images', 'custom_chars', 'custom_chars.json'])),
			name, conversion.registryEntry, result, exactRegistryKey, upgradeHealthIconRequired);
	}

	/** Keep the selected Codename owner's authored XML and atlas beside its
	 * native conversion. Codename script-created actors and camera swaps read
	 * these source definitions at runtime; a converted custom_chars entry alone
	 * cannot reproduce their animation, placement, or constructor hooks. */
	static function importCodenameCharacterRuntimeSource(importData:VSliceCharacterImport,
		sourceRoot:String, destinationAssetRoot:String, result:ImportAssetMergeResult):Void {
		if (importData == null || importData.conversion == null || sourceRoot == null
			|| destinationAssetRoot == null || !validImportPath(importData.source)) return;
		var definitionRoot = Path.normalize(Path.join([sourceRoot, 'data', 'characters']));
		var definition = Path.normalize(importData.source);
		if (!CodenameScriptDiscovery.withinRoot(sourceRoot, definitionRoot)
			|| !CodenameScriptDiscovery.withinRoot(sourceRoot, definition)
			|| !CodenameScriptDiscovery.withinRoot(definitionRoot, definition)
			|| !definition.toLowerCase().endsWith('.xml')) {
			result.failed++;
			if (result.errors == null) result.errors = [];
			result.errors.push('[codename-character-source] Definition is outside the selected owner: '
				+ definition);
			return;
		}
		var relativeDefinition = definition.substr(definitionRoot.length + 1);
		if (!CodenameScriptDiscovery.safeRelativeName(relativeDefinition)) return;
		mergeVSliceMapping({source:definition,
			destination:'data/characters/' + relativeDefinition,
			kind:'codename-character-definition', supported:true}, destinationAssetRoot, result);

		var atlasRoot = Path.normalize(Path.join([sourceRoot, 'images', 'characters']));
		if (importData.conversion.assets == null) return;
		for (mapping in importData.conversion.assets) {
			if (mapping == null || Reflect.field(mapping, 'kind') != 'character-atlas') continue;
			var source:Dynamic = Reflect.field(mapping, 'source');
			if (!Std.isOfType(source, String)) continue;
			var atlasFile = Path.normalize(cast source);
			if (!CodenameScriptDiscovery.withinRoot(sourceRoot, atlasRoot)
				|| !CodenameScriptDiscovery.withinRoot(sourceRoot, atlasFile)
				|| !CodenameScriptDiscovery.withinRoot(atlasRoot, atlasFile)) continue;
			var relativeAtlas = atlasFile.substr(atlasRoot.length + 1);
			if (!CodenameScriptDiscovery.safeRelativeName(relativeAtlas)) continue;
			mergeVSliceMapping({source:atlasFile,
				destination:'images/characters/' + relativeAtlas,
				kind:'codename-character-atlas', supported:true}, destinationAssetRoot, result);
		}
	}

	static function importVSliceStageConversion(importData:VSliceStageImport,
		result:ImportAssetMergeResult, ?destinationAssetRoot:String = 'assets', ?exactRegistryKey:Bool = false):Void {
		if (importData == null || importData.conversion == null)
			return;
		var conversion = importData.conversion;
		var name = StringTools.trim(conversion.name);
		if (!validModuleName(name))
			return;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '') {
			result.failed++;
			return;
		}
		var folder = Path.join([assetRoot, 'images', 'custom_stages', name]);
		if (FileSystem.exists(folder) && !FileSystem.isDirectory(folder)) {
			result.failed++;
			return;
		}
		ensureDirectory(folder);
		if (conversion.assets != null)
			for (mapping in conversion.assets)
				mergeVSliceMapping(mapping, folder, result);
		writeVSliceHScript(Path.join([assetRoot, 'images', 'custom_stages', name + '.hscript']),
			conversion.hscript, result);
		mergeVSliceRegistryEntry(Path.join([assetRoot, 'images', 'custom_stages', 'custom_stages.json']), name,
			conversion.registryValue, result, exactRegistryKey);
	}

	static function importVSliceNoteStyleConversion(importData:VSliceNoteStyleImport,
		result:ImportAssetMergeResult):Void {
		if (importData == null || importData.conversion == null || !importData.conversion.supported)
			return;
		var conversion = importData.conversion;
		var name = StringTools.trim(conversion.name);
		if (!validModuleName(name))
			return;
		var folder = Path.join(['assets', 'images', 'custom_ui', 'ui_packs', name]);
		if (FileSystem.exists(folder) && !FileSystem.isDirectory(folder)) {
			result.failed++;
			return;
		}
		ensureDirectory(folder);
		if (conversion.assets != null)
			for (mapping in conversion.assets)
				mergeVSliceMapping(mapping, folder, result);
		var presetPath = Path.join([folder, 'multiNotePresets.json']);
		if (FileSystem.exists(presetPath)) {
			result.skipped++;
			reportImportProgress('vslice-ui', presetPath, 0, 0, 0, 1, 0, 1);
		} else {
			try {
				File.saveContent(presetPath, CoolUtil.stringifyJson(conversion.preset));
				result.copied++;
				reportImportProgress('vslice-ui', presetPath, 0, 0, 1, 0, 0, 1);
			} catch (_:Dynamic) {
				result.failed++;
				reportImportProgress('vslice-ui', presetPath, 0, 0, 0, 0, 1, 1);
			}
		}
		mergeVSliceRegistryEntry(chooseVSliceRegistry(
			'assets/images/custom_ui/ui_packs/ui.json',
			'assets/images/custom_ui/ui_packs/ui.json'), name, conversion.registryEntry, result);
	}

	/** Copy only the note/sustain atlases used by a scripted V-Slice NoteKind.
	 * These styles belong to individual note definitions, so registering their
	 * partial UI preset would incorrectly replace the song's receptor/HUD style. */
	static function importVSliceNoteKindStyleConversion(importData:VSliceNoteStyleImport,
		result:ImportAssetMergeResult):Void {
		if (importData == null || importData.conversion == null || importData.conversion.assets == null)
			return;
		var conversion = importData.conversion;
		var name = StringTools.trim(conversion.name);
		if (!validModuleName(name))
			return;
		var folder = Path.join(['assets', 'images', 'custom_ui', 'ui_packs', name]);
		if (FileSystem.exists(folder) && !FileSystem.isDirectory(folder)) {
			result.failed++;
			return;
		}
		for (mapping in conversion.assets)
			if (mapping != null && (mapping.kind == 'note-style-note' || mapping.kind == 'note-style-hold'))
				mergeVSliceMapping(mapping, folder, result);
	}

	/** Materialize V-Slice visual conversions only after the song itself was
	 * accepted.  Every mapping is copied into the native custom_* tree without
	 * replacing existing files, and registry keys are added only when absent. */
	/**
		Kade-family builds define their stages in compiled code, so a chart
		without a `stage` field has no scene data to read.  When the selected
		source ships Haxe (a source release), extract the authored layout
		mechanically with KadeStageSource; when it is a compiled release,
		import nothing for the stage and tell the user to import the mod's
		source release instead.  Approximations and per-mod tables are
		deliberately avoided - the values are either the donor's own or absent.
	*/
	static function applyKadeSourceStageCompatibility(result:SongImport, chartRoot:String, chartSong:Dynamic):Void {
		#if sys
		if (result == null || chartRoot == null)
			return;
		// Only when the donor authored no stage: an explicit chart field keeps
		// its own value so Song.loadFromJson validation stays meaningful.
		if (chartFieldString(chartSong, 'stage', null) != null)
			return;
		var songKey = StringTools.trim(result.name).toLowerCase();
		var sourceRoot = KadeStageSource.findSourceRoot(chartRoot);
		var layout:Dynamic = null;
		if (sourceRoot != null)
			layout = KadeStageSource.extractStage(sourceRoot, songKey,
				StringTools.trim(result.p2 == null ? '' : result.p2).toLowerCase());
		if (result.diagnostics == null)
			result.diagnostics = [];
		if (layout == null) {
			result.diagnostics.push('[kade-compiled-release] ' + result.name
				+ ': this Kade-family release defines its stage in compiled code and ships no stage data, so no stage was imported.'
				+ (sourceRoot == null
					? ' Import the mod from its source release (the published source code repository), not the compiled build, to get the authored stage.'
					: ' The selected source contains no stage block for this song.'));
			return;
		}
		result.diagnostics.push('[kade-source-stage] ' + result.name
			+ ': stage "' + layout.id + '" extracted from the mod source with the donor\'s authored coordinates.');
		var lines:Array<String> = [];
		var layers:Array<Dynamic> = layout.layers;
		for (index in 0...layers.length)
			lines.push('var vSliceProp_' + index + ';');
		lines.push('');
		lines.push('function start(song) {');
		if (layout.zoom != null)
			lines.push('    setDefaultZoom(' + layout.zoom + ');');
		var actorOffsets:Array<Array<Dynamic>> = [
			['bf', 'boyfriend', Reflect.field(layout.actors, 'bf')],
			['dad', 'dad', Reflect.field(layout.actors, 'dad')],
			['gf', 'gf', Reflect.field(layout.actors, 'gf')]
		];
		for (entry in actorOffsets) {
			var position:Array<Dynamic> = entry[2];
			if (position == null)
				continue;
			lines.push('    stage.setOffsets("' + entry[0] + '", ' + position[0] + ', ' + position[1] + ', false);');
			lines.push('    ' + entry[1] + '.x = ' + position[0] + ';');
			lines.push('    ' + entry[1] + '.y = ' + position[1] + ';');
		}
		var assets:Array<Dynamic> = layout.assets;
		for (index in 0...layers.length) {
			var layer:Dynamic = layers[index];
			var scroll:Array<Dynamic> = layer.scroll == null ? [1, 1] : layer.scroll;
			var assetDestination = Std.string(Reflect.field(assets[layer.file], 'destination'));
			var isXml = StringTools.endsWith(assetDestination, '.xml');
			var sheetName = isXml ? assetDestination.substr(0, assetDestination.length - 4) : assetDestination;
			lines.push('    vSliceProp_' + index + ' = new FlxSprite(' + layer.x + ', ' + layer.y + ');');
			var anim:Dynamic = Reflect.field(layer, 'anim');
			if (anim != null) {
				lines.push('    vSliceProp_' + index + '.frames = FlxAtlasFrames.fromSparrow(hscriptPath + "' + sheetName + '", hscriptPath + "' + assetDestination + '");');
				lines.push('    vSliceProp_' + index + '.animation.addByPrefix("' + anim.name + '", "' + anim.prefix + '", ' + anim.fps + ', true);');
			} else {
				lines.push('    vSliceProp_' + index + '.loadGraphic(hscriptPath + "' + assetDestination + '");');
			}
			if (layer.scale != null && layer.scale != 1)
				lines.push('    vSliceProp_' + index + '.scale.set(' + layer.scale + ', ' + layer.scale + ');');
			lines.push('    vSliceProp_' + index + '.scrollFactor.set(' + scroll[0] + ', ' + scroll[1] + ');');
			lines.push('    vSliceProp_' + index + '.alpha = 1;');
			lines.push('    vSliceProp_' + index + '.antialiasing = true;');
			if (anim != null)
				lines.push('    vSliceProp_' + index + '.animation.play("' + anim.name + '");');
			lines.push('    addSprite(vSliceProp_' + index + ', BEHIND_ALL);');
		}
		lines.push('}');
		lines.push('');
		lines.push('function beatHit(beat) {}');
		lines.push('function update(elapsed) {}');
		lines.push('function stepHit(step) {}');
		lines.push('function playerTwoTurn() {}');
		lines.push('function playerTwoMiss() {}');
		lines.push('function playerTwoSing() {}');
		lines.push('function playerOneTurn() {}');
		lines.push('function playerOneMiss() {}');
		lines.push('function playerOneSing() {}');
		var mappings:Array<Dynamic> = [];
		for (asset in assets)
			mappings.push({
				source: Reflect.field(asset, 'source'),
				destination: Reflect.field(asset, 'destination'),
				kind: 'stage-image',
				supported: true
			});
		result.stage = layout.id;
		Reflect.setField(result, 'convertedStage', {
			reference: layout.id,
			source: sourceRoot,
			conversion: {
				name: layout.id,
				registryValue: layout.id,
				hscript: lines.join('\n') + '\n',
				assets: mappings,
				diagnostics: []
			}
		});
		#end
	}

	/**
		Kade-family releases also author CHARACTERS in compiled code: the gf a
		stage selects lives in PlayState.hx's `var gfVersion` switch and the
		opponent may hide itself (`dad.visible = false;`).  When the source
		release provided a stage, extend the generated stage script with the same
		actors - `switchCharacter('<gf>', 'gf')` after the gf placement lines and
		`dad.visible = false;` after the dad placement - and materialize the
		referenced Character.hx case blocks as native custom characters so the
		ids resolve natively.  Characters that already resolved through the
		compiled-asset adapter are left untouched.
	*/
	static function applyKadeSourceCharacterCompatibility(result:SongImport, chartRoot:String, chartSong:Dynamic):Void {
		#if sys
		if (result == null || chartRoot == null)
			return;
		// Mirror the stage gate: an explicit chart stage keeps its own actors.
		if (chartFieldString(chartSong, 'stage', null) != null)
			return;
		var convertedStage:Dynamic = Reflect.field(result, 'convertedStage');
		if (convertedStage == null || Reflect.field(convertedStage, 'conversion') == null)
			return;
		var stageId = StringTools.trim(result.stage == null ? '' : result.stage);
		if (stageId == '')
			return;
		var sourceRoot = KadeStageSource.findSourceRoot(chartRoot);
		if (sourceRoot == null)
			return;
		if (result.diagnostics == null)
			result.diagnostics = [];
		var player2 = StringTools.trim(result.p2 == null ? '' : result.p2).toLowerCase();
		var playStateText = KadeStageSource.playStateSource(sourceRoot);
		var hidesDad = playStateText != null && player2 != ''
			&& KadeStageSource.player2HidesDad(playStateText, player2);
		// The donor's gfVersion switch is keyed by the mod's internal curStage
		// id (for example auditorHell), not by the native stage name this plan
		// registered (the song key), so re-read the same layout to recover it.
		var layout = KadeStageSource.extractStage(sourceRoot,
			StringTools.trim(result.name).toLowerCase(), player2);
		if (layout == null)
			return;
		var donorStageId = Std.string(Reflect.field(layout, 'stageId'));
		var gfCharacter = KadeStageSource.stageGfVersion(sourceRoot, donorStageId);
		if (gfCharacter != null) {
			gfCharacter = StringTools.trim(gfCharacter);
			if (gfCharacter.toLowerCase() == 'gf'
				|| gfCharacter.toLowerCase() == StringTools.trim(result.gf == null ? '' : result.gf).toLowerCase())
				gfCharacter = null;
		}

		var script:String = Reflect.field(convertedStage.conversion, 'hscript');
		var injected = false;
		if (gfCharacter != null) {
			var gfPoint = placedActorPoint(script, 'gf');
			if (prepareKadeSourceCharacter(result, sourceRoot, gfCharacter) && gfPoint != null) {
				script = injectAfterActorPlacement(script, 'gf', [
					'    switchCharacter("' + gfCharacter + '", "gf");',
					'    gf.x = ' + gfPoint[0] + ';',
					'    gf.y = ' + gfPoint[1] + ';'
				]);
				injected = true;
				result.diagnostics.push('[kade-source-character] ' + result.name + ': girlfriend "'
					+ gfCharacter + '" (source stage "' + donorStageId + '" gfVersion) comes from the mod source and is switched in by the stage script.');
			}
		}
		if (hidesDad) {
			// The hide records a staged entrance, not a permanent state: the
			// imported song script's cutscene handback (startCountdown from
			// HScript) restores staged actors, matching the donor engines where
			// the song flow re-shows the opponent after its entrance.
			script = injectAfterActorPlacement(script, 'dad', ['    stage.stageOutActor("dad");']);
			injected = true;
			result.diagnostics.push('[kade-source-character] ' + result.name + ': opponent "' + player2
				+ '" is staged out at song start; the song cutscene handback brings the actor back (stageOutActor).');
		}
		if (injected)
			Reflect.setField(convertedStage.conversion, 'hscript', script);

		// The chart's opponent may also be a code-only definition; native ids
		// load through the chart's player2 field without stage-script wiring.
		if (player2 != '' && player2 != 'gf')
			prepareKadeSourceCharacter(result, sourceRoot, player2);
		#end
	}

	/** Attach a native conversion for one Character.hx case block, unless the
	 * id already resolves natively.  Returns true when the id will resolve. */
	static function prepareKadeSourceCharacter(result:SongImport, sourceRoot:String, characterId:String):Bool {
		if (nativeCharacterComplete(characterId))
			return true;
		if (!validModuleName(characterId)) {
			result.diagnostics.push('[kade-source-character] Character id "' + characterId
				+ '" cannot be represented as a native custom character name.');
			return false;
		}
		var definition:Dynamic = KadeStageSource.extractCharacter(sourceRoot, characterId);
		if (definition == null) {
			result.diagnostics.push('[kade-source-character] Character "' + characterId
				+ '" has no extractable Character.hx case block (or its Sparrow atlas is missing) in the mod source.');
			return false;
		}
		// Kept Dynamic (like convertedStages/eventVideoAssets) so the extraction
		// probes compile without the VSliceImporter typedef module.
		var mappings:Array<Dynamic> = [
			{
				source: Std.string(definition.atlasPng),
				destination: 'char.png',
				kind: 'character-atlas',
				supported: true
			},
			{
				source: Std.string(definition.atlasXml),
				destination: 'char.xml',
				kind: 'character-atlas',
				supported: true
			}
		];
		var conversion:Dynamic = {
			name: characterId,
			registryEntry: {
				like: characterId,
				icons: [0, 0, 0, 0],
				colors: ['#FFFFFF']
			},
			hscript: generateKadeCharacterHScript(definition),
			assets: mappings,
			diagnostics: []
		};
		var converted:Array<Dynamic> = Reflect.field(result, 'convertedCharacters');
		if (converted == null) {
			converted = [];
			Reflect.setField(result, 'convertedCharacters', converted);
		}
		for (existing in converted)
			if (existing != null && existing.conversion != null
				&& existing.conversion.name.toLowerCase() == characterId.toLowerCase())
				return true; // a conversion for this id is already queued
		converted.push({
			reference: characterId,
			source: Std.string(definition.sourceFile),
			conversion: conversion
		});
		result.diagnostics.push('[kade-source-character] Character "' + characterId
			+ '" extracted from the mod source (' + Std.string(definition.atlasKey) + ') as a native custom character.');
		return true;
	}

	/**
		Generate a native character script for one extracted Character.hx case.
		Girlfriend-style ids whose source registers danceLeft/danceRight dance
		exactly like the native gf script; everything else falls back to idle,
		matching the donor's own dance() dispatch.
	*/
	static function generateKadeCharacterHScript(definition:Dynamic):String {
		var dancesLikeGf = false;
		var lines:Array<String> = [
			'// Generated by the source-release importer from the donor\'s compiled Character.hx (\''
				+ Std.string(definition.id) + '\' case).',
			'function init(char) {',
			"    char.frames = FlxAtlasFrames.fromSparrow(hscriptPath + 'char.png', hscriptPath + 'char.xml');"
		];
		var animations:Array<Dynamic> = definition.animations;
		for (anim in animations) {
			if (anim.name == 'danceLeft' || anim.name == 'danceRight')
				dancesLikeGf = true;
			if (anim.indices != null) {
				var indices:Array<Int> = anim.indices;
				var rendered:Array<String> = [];
				for (index in indices)
					rendered.push(Std.string(index));
				lines.push("    char.animation.addByIndices('" + anim.name + "', '" + anim.prefix
					+ "', [" + rendered.join(',') + "], '', " + anim.fps + ', ' + anim.loop + ');');
			} else {
				lines.push("    char.animation.addByPrefix('" + anim.name + "', '" + anim.prefix
					+ "', " + anim.fps + ', ' + anim.loop + ');');
			}
		}
		var offsets:Array<Dynamic> = definition.offsets;
		for (offset in offsets)
			lines.push("    char.addOffset('" + offset.name + "', " + offset.x + ', ' + offset.y + ');');
		lines.push('    char.noFlip = ' + (dancesLikeGf ? 'true' : 'false') + ';');
		lines.push("    char.playAnim('" + (definition.initialAnim == null ? (dancesLikeGf ? 'danceRight' : 'idle') : definition.initialAnim) + "');");
		if (dancesLikeGf) {
			lines.push("    char.like = 'gf';");
			lines.push('    char.likeGf = true;');
			lines.push('    char.gfEpicLevel = Level_Sing;');
		}
		lines = lines.concat([
			'}',
			'portraitOffset = [0, 0];',
			'dadVar = 4.0;',
			'isPixel = false;',
			'function sing(direction, miss, alt, char) {}',
			'function update(elapsed, char) {}',
			'var danced = false;',
			'function dance(char) {',
			dancesLikeGf
				? "    if (!StringTools.startsWith(char.animation.curAnim.name, 'hair')) {\n        danced = !danced;\n\n        if (danced)\n            char.playAnim('danceRight');\n        else\n            char.playAnim('danceLeft');\n    }"
				: "    char.playAnim('idle');",
			'}',
			''
		]);
		return lines.join('\n');
	}

	/** True when the id already resolves as a native custom character the way
	 * Song.resolveCharacterVisual resolves it (registry row + implementation
	 * script + atlas root). */
	static function nativeCharacterComplete(characterId:String):Bool {
		var clean = StringTools.trim(characterId == null ? '' : characterId).toLowerCase();
		if (clean == '' || clean == 'gf')
			return true;
		var root = 'assets/images/custom_chars/';
		var names:Array<String> = [characterId];
		try {
			var registryPath = chooseVSliceRegistry(root + 'custom_chars.jsonc', root + 'custom_chars.json');
			if (FileSystem.exists(registryPath)) {
				var registry:Dynamic = CoolUtil.parseJson(File.getContent(registryPath));
				if (registry != null && !Std.isOfType(registry, Array)) {
					for (field in Reflect.fields(registry))
						if (field.toLowerCase() == clean) {
							names.push(field);
							break;
						}
				}
			}
		} catch (_:Dynamic) {}
		for (name in names) {
			var implementation = false;
			for (extension in ['hscript', 'hxs', 'json', 'jsonc'])
				if (FileSystem.exists(root + name + '.' + extension)) {
					implementation = true;
					break;
				}
			var asset = FileSystem.exists(root + name) && FileSystem.isDirectory(root + name)
				&& (FileSystem.exists(root + name + '/char.png') || FileSystem.exists(root + name + '/char.xml'));
			if (implementation && asset)
				return true;
		}
		return false;
	}

	/** The [x, y] a generated stage script placed one actor at, parsed from
	 * its own `stage.setOffsets(...)` line. */
	static function placedActorPoint(script:String, actor:String):Null<Array<String>> {
		if (script == null)
			return null;
		var pattern = new EReg('stage\\.setOffsets\\("' + actor + '",\\s*(-?[0-9.]+)\\s*,\\s*(-?[0-9.]+)', "");
		if (!pattern.match(script))
			return null;
		return [pattern.matched(1), pattern.matched(2)];
	}

	/** Insert extra statements right after one actor's placement lines in a
	 * generated stage script. */
	static function injectAfterActorPlacement(script:String, actor:String, extraLines:Array<String>):String {
		if (script == null || extraLines == null || extraLines.length == 0)
			return script;
		var marker = 'stage.setOffsets("' + actor + '"';
		var at = script.indexOf(marker);
		if (at < 0)
			return script;
		var placementY = script.indexOf(actor + '.y = ', at);
		if (placementY < 0)
			return script;
		var lineEnd = script.indexOf('\n', placementY);
		if (lineEnd < 0)
			lineEnd = script.length;
		return script.substring(0, lineEnd + 1) + extraLines.join('\n') + '\n' + script.substring(lineEnd + 1);
	}

	static function importVSliceVisuals(songData:SongImport):ImportAssetMergeResult {
		var result:ImportAssetMergeResult = {copied: 0, skipped: 0, failed: 0};
		if (songData == null)
			return result;
		if (songData.engine == ImportEngine.CODENAME
			&& (songData.sourceRoot == null || StringTools.trim(songData.sourceRoot) == '')) {
			result.failed++;
			result.errors = ['Codename visual ownership root is missing.'];
			return result;
		}
		if (songData.engine == ImportEngine.V_SLICE
			&& (songData.sourceRoot == null || StringTools.trim(songData.sourceRoot) == '')) {
			result.failed++;
			result.errors = ['V-Slice character ownership root is missing.'];
			return result;
		}
		var visualAssetRoot = songData.engine == ImportEngine.CODENAME
			? CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine) : 'assets';
		var characterAssetRoot = songData.engine == ImportEngine.V_SLICE
			? CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine) : visualAssetRoot;
		// Stage conversions are engine-neutral; Kade source-stage extraction
		// also materializes one through this shared path. Note styles stay
		// V-Slice-only.
		if (songData.convertedStage != null)
			importVSliceStageConversion(songData.convertedStage, result, visualAssetRoot,
				songData.engine == ImportEngine.CODENAME);
		// Stages referenced only by Change Stage events convert through the
		// same registry path. Keep Play Video media with the selected source
		// owner so identical basenames in unrelated packages cannot collide.
		var eventStages:Array<Dynamic> = Reflect.field(songData, 'convertedStages');
		if (eventStages != null)
			for (eventStage in eventStages)
				importVSliceStageConversion(eventStage, result, visualAssetRoot,
					songData.engine == ImportEngine.CODENAME);
		var eventVideos:Array<Dynamic> = Reflect.field(songData, 'eventVideoAssets');
		var eventVideoRoot = songData.sourceRoot == null || StringTools.trim(songData.sourceRoot) == ''
			? 'assets' : CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
		if (eventVideos != null)
			for (video in eventVideos)
				mergeVSliceMapping({
					source: Reflect.field(video, 'source'),
					destination: 'videos/' + Std.string(Reflect.field(video, 'destination')),
					kind: 'event-video',
					supported: true
				}, eventVideoRoot, result);
		// Character conversions are engine-neutral too: the Kade source path
		// materializes code-defined Character.hx cases through the same native
		// custom-character shape (V-Slice imports fill this field as well).
		var seenChars:Map<String, Bool> = new Map<String, Bool>();
		if (songData.convertedCharacters != null)
			for (converted in songData.convertedCharacters) {
				if (converted == null || converted.conversion == null)
					continue;
				var key = songData.engine == ImportEngine.CODENAME
					? converted.conversion.name : converted.conversion.name.toLowerCase();
				if (seenChars.exists(key))
					continue;
				seenChars.set(key, true);
				importVSliceCharacterConversion(converted, result, characterAssetRoot,
					songData.engine == ImportEngine.CODENAME,
					songData.engine == ImportEngine.V_SLICE);
				if (songData.engine == ImportEngine.CODENAME)
					importCodenameCharacterRuntimeSource(converted, songData.vSliceRoot,
						visualAssetRoot, result);
			}
		if (songData.engine == ImportEngine.CODENAME
			&& songData.codenameEngineBaseAssetRoot != null
			&& StringTools.trim(songData.codenameEngineBaseAssetRoot) != ''
			&& songData.codenameDefaultCharacter != null
			&& StringTools.trim(songData.codenameDefaultCharacter) != '') {
			var dependency = CodenameBaseCharacterDependency.materialize(
				songData.codenameEngineBaseAssetRoot, songData.vSliceRoot, visualAssetRoot,
				songData.codenameDefaultCharacter);
			result.copied += dependency.copied;
			result.skipped += dependency.skipped;
			if (dependency.failed) {
				result.failed++;
				if (result.errors == null) result.errors = [];
				result.errors.push('[codename-engine-base-character] ' + dependency.diagnostic);
			}
		}
		if (songData.engine != ImportEngine.V_SLICE)
			return result;
		if (songData.freeplayIconSource != null && songData.char != null
			&& new EReg('^[A-Za-z0-9_-]+$', '').match(songData.char)
			&& songData.sourceRoot != null) {
			var ownerRoot = CompatScriptManifest.destinationRoot(songData.sourceRoot, songData.engine);
			if (ownerRoot != null && ownerRoot != '')
				mergeVSliceMapping({
					source: songData.freeplayIconSource,
					destination: 'images/freeplay/icons/' + songData.char.toLowerCase()
						+ (songData.char.toLowerCase().endsWith('pixel') ? '' : 'pixel') + '.png',
					kind: 'freeplay-icon',
					supported: true
				}, ownerRoot, result);
		}
		if (songData.convertedNoteStyle != null)
			importVSliceNoteStyleConversion(songData.convertedNoteStyle, result);
		if (songData.convertedNoteStyles != null)
			for (noteStyle in songData.convertedNoteStyles)
				importVSliceNoteKindStyleConversion(noteStyle, result);
		return result;
	}

	#end

	/**
	 * Fill only absent visual fields from the import-level metadata.  An
	 * explicitly authored but unavailable value must remain in the destination
	 * chart: Song.loadFromJson will validate it and select a valid sibling
	 * difficulty, while overwriting it here would erase the evidence needed for
	 * that general fallback (FPS Plus and older Popipo-style packs rely on it).
	 */
	static function applyImportedVisualMetadata(chartSong:Dynamic, songData:SongImport):Void {
		if (chartSong == null || songData == null)
			return;
		var fill = function(fieldName:String, value:Dynamic):Void {
			if (value == null || !Reflect.hasField(chartSong, fieldName)) {
				if (value != null)
					Reflect.setField(chartSong, fieldName, value);
				return;
			}
			var current:Dynamic = Reflect.field(chartSong, fieldName);
			if (current == null || (Std.isOfType(current, String)
				&& (StringTools.trim(Std.string(current)) == '' || Std.string(current).toLowerCase() == 'null')))
				Reflect.setField(chartSong, fieldName, value);
		};
		fill('player1', songData.p1);
		fill('player2', songData.p2);
		if (songData.engine == ImportEngine.PSYCH) {
			// Psych spells this field gfVersion. Convert each difficulty's own
			// value before applying song-level defaults; an absent Easy value must
			// still be able to inherit the authored Normal chart at runtime.
			var currentGf:Dynamic = Reflect.field(chartSong, 'gf');
			var hasGf = currentGf != null && StringTools.trim(Std.string(currentGf)) != ''
				&& Std.string(currentGf).toLowerCase() != 'null';
			var gfVersion:Dynamic = Reflect.field(chartSong, 'gfVersion');
			if (!hasGf && gfVersion != null && StringTools.trim(Std.string(gfVersion)) != ''
				&& Std.string(gfVersion).toLowerCase() != 'null')
				Reflect.setField(chartSong, 'gf', gfVersion);
			else if (!hasGf && songData.gf != 'gf')
				fill('gf', songData.gf);
		} else
			fill('gf', songData.gf);
		fill('stage', songData.stage);
		fill('uiType', songData.ui);
		fill('cutsceneType', songData.cutscene);
		fill('isMoody', songData.isMoody);
		fill('isHey', songData.isHey);
		fill('isCheer', songData.isCheer);
		fill('isSpooky', songData.isSpooky);
		fill('stageID', songData.stageID);
		fill('songArtist', Reflect.field(songData, 'songArtist'));
		fill('album', Reflect.field(songData, 'album'));
	}

	/** Keep authored Psych and embedded Codename chart titles distinct from the safe
	 * native data/audio folder. Other import families retain their existing
	 * collision behavior. */
	static function prepareImportedSongIdentity(chartSong:Dynamic, songData:SongImport,
		targetFolder:String, preserveCodenameTitle:Bool = false):Void {
		var authored:Dynamic = Reflect.field(chartSong, 'song');
		if ((songData.engine == ImportEngine.PSYCH
			|| songData.engine == ImportEngine.NIGHTMARE_VISION
			|| (songData.engine == ImportEngine.CODENAME && preserveCodenameTitle))
			&& authored != null
			&& validModuleName(Std.string(authored))) {
			Reflect.setField(chartSong, 'compatPreserveSongTitle', true);
			return;
		}
		if (Reflect.field(songData, 'ownerQualifiedCollision') != true
			|| authored == null || !validModuleName(Std.string(authored)))
			Reflect.setField(chartSong, 'song', targetFolder);
	}

	static public function importSong(songData:SongImport):Bool {
		var validationError = validateSongImport(songData);
		if (validationError != null) {
			trace(validationError);
			return false;
		}

		var targetName = StringTools.trim(songData.name);
		var targetFolder = importSongFolderName(songData);
		if (targetFolder == '') {
			trace('Unable to import ' + targetName + ': no valid destination song key');
			return false;
		}
		var dataFolder = Path.join(['assets', 'data', targetFolder]);
		var songFolder = Path.join(['assets', 'songs', targetFolder]);
		#if sys
		var ownershipError = ImportSongOwnership.conflict(existingImportChild('assets/data', targetFolder),
			songData.sourceRoot, songData.engine);
		if (ownershipError != null) {
			trace(ownershipError);
			return false;
		}
		if (songTargetExists(targetName, targetFolder) && !songNeedsRepair(songData)) {
			trace('Skipping ' + targetName + ': destination already exists');
			return false;
		}
		// Reuse a case-variant destination folder on Linux rather than creating
		// a second tree beside it during partial repair.
		var existingDataFolder = existingImportChild(Path.join(['assets', 'data']), targetFolder);
		var existingSongFolder = existingImportChild(Path.join(['assets', 'songs']), targetFolder);
		if (FileSystem.isDirectory(existingDataFolder))
			dataFolder = existingDataFolder;
		if (FileSystem.isDirectory(existingSongFolder))
			songFolder = existingSongFolder;
		#end
		if ((FileSystem.exists(dataFolder) && !FileSystem.isDirectory(dataFolder))
			|| (FileSystem.exists(songFolder) && !FileSystem.isDirectory(songFolder))) {
			trace('Unable to import ' + targetName + ': target path is not a directory');
			return false;
		}

		// Read and validate the destination registry before creating either target
		// folder.  A malformed/unreadable registry must not leave charts/audio
		// stranded behind a false failed import; a clean checkout simply starts
		// with an empty in-memory list and writes it below after adding the song.
		var coolSongListFile:Array<Dynamic> = [];
		var freeplayPath = freeplayRegistryPath();
		try {
			if (FNFAssets.exists(freeplayPath))
				coolSongListFile = cast CoolUtil.parseJson(FNFAssets.getText(freeplayPath));
		} catch (error:Dynamic) {
			trace('Unable to read freeplay song registry: ' + error);
			return false;
		}
		if (coolSongListFile == null)
			coolSongListFile = [];
		if (!Std.isOfType(coolSongListFile, Array)) {
			trace('Unable to read freeplay song registry: expected an array.');
			return false;
		}
		ensureDirectory(dataFolder);
		ensureDirectory(songFolder);
		// Build the shared Psych/Kade note-type table before serializing any
		// difficulty. Each chart gets its own parsed object, so this never edits
		// the donor file and all difficulties use stable custom-note indexes.
		prepareSongNoteDefinitions(songData);
		// Inst is required for a playable song.  Materialize it before any chart
		// write so a source disappearing after validation cannot leave a visible
		// freeplay entry with no instrumental audio.
		copyRequired(songData.inst, Path.join([songFolder, 'Inst.ogg']), 'instrumental audio');

		var writtenCharts = 0;
		var importedVocalStems:Dynamic = Reflect.field(songData, 'vocalStems');
		var importedVocalStemCount = importedVocalStems != null && Std.isOfType(importedVocalStems, Array)
			? (cast importedVocalStems:Array<Dynamic>).length : 0;
		// FPS Plus's ratings array follows the configured difficulty order, not
		// merely the number of chart files found.  A song may ship only hard.json
		// (for example Remorse), so resolve the authored suffix before projecting
		// one rating onto a chart; the complete list remains on every chart.
		var ratingIndexFor = function(value:String, fallback:Int):Int {
			var clean = Path.withoutDirectory(Path.normalize(value == null ? '' : value));
			for (extension in ['.jsonc', '.json'])
				if (clean.toLowerCase().endsWith(extension))
					clean = clean.substr(0, clean.length - extension.length);
			var lower = clean.toLowerCase();
			var targetLower = targetFolder.toLowerCase();
			var difficulty = lower == targetLower ? 'normal'
				: lower.startsWith(targetLower + '-') ? lower.substr(targetLower.length + 1) : lower;
			var names = getImportDifficultyNames();
			for (index in 0...names.length)
				if (names[index] != null && names[index].toLowerCase() == difficulty)
					return index;
			return fallback;
		};
		if (songData.convertedCharts != null && songData.convertedCharts.length > 0) {
			for (i in 0...songData.convertedCharts.length) {
				var converted = songData.convertedCharts[i];
				if (converted == null || converted.chart == null || Reflect.field(converted.chart, 'song') == null)
					continue;
				var coolSong:Dynamic = converted.chart;
				var coolSongSong:Dynamic = coolSong.song;
				prepareImportedSongIdentity(coolSongSong, songData, targetFolder,
					Reflect.field(converted, 'authoredSongTitle') == true);
				applyImportedVisualMetadata(coolSongSong, songData);
				applyImportedSidecars(coolSongSong, songData, ratingIndexFor(converted.difficulty, i));
				if (importedVocalStemCount > 0) {
					var vocalMetadata:Array<Dynamic> = [];
					for (stem in (cast importedVocalStems:Array<Dynamic>)) {
						if (stem == null)
							continue;
						var file:Dynamic = Reflect.field(stem, 'file');
						if (file == null)
							file = Reflect.field(stem, 'destination');
						if (file == null || StringTools.trim(Std.string(file)) == '')
							continue;
						vocalMetadata.push({
							id: Reflect.field(stem, 'id'),
							role: Reflect.field(stem, 'role'),
							file: Std.string(file)
						});
					}
					if (vocalMetadata.length > 0) {
						Reflect.setField(coolSongSong, 'vocalStems', vocalMetadata);
						Reflect.setField(coolSongSong, 'needsVoices', true);
					}
				}
				coolSong.song = coolSongSong;
				// Song.loadFromJson resolves charts from the destination folder name,
				// so retain that exact spelling and use only the converted difficulty
				// suffix (normal has no suffix).
				var templateName = VSliceImporter.nativeFileName('chart', converted.difficulty);
				var fileName = targetFolder + templateName.substr('chart'.length);
				var chartDestination = Path.join([dataFolder, fileName]);
					var existingChartPath = existingImportChild(dataFolder, fileName);
					if (!FileSystem.exists(existingChartPath)) {
						trace('[import-chart-serialize-start] source=' + converted.source
							+ ' difficulty=' + converted.difficulty + ' destination=' + chartDestination);
						reportImportProgress('chart-serialize-start',
							converted.source + ' [' + converted.difficulty + '] -> ' + chartDestination,
							i, songData.convertedCharts.length);
						// TJSON's native encoder can SIGSEGV while walking converted
						// Codename note arrays. These generated charts contain plain JSON
						// data, so use Haxe's standard encoder for the import output.
						File.saveContent(chartDestination, haxe.Json.stringify(coolSong));
						reportImportProgress('charts', chartDestination, i + 1, songData.convertedCharts.length, 1, 0, 0);
					} else if (importedVocalStemCount > 0) {
						// A prior import may have written the chart before the split-vocal
						// metadata was added. Repair only that native field in the
						// destination chart; donor charts and all unrelated user edits stay
						// untouched.
						var existingChart = readSongChart(existingChartPath);
						var metadata:Array<Dynamic> = [];
						for (stem in (cast importedVocalStems:Array<Dynamic>)) {
							if (stem == null)
								continue;
							var file:Dynamic = Reflect.field(stem, 'file');
							if (file == null)
								file = Reflect.field(stem, 'destination');
							if (file == null || StringTools.trim(Std.string(file)) == '')
								continue;
							metadata.push({
								id: Reflect.field(stem, 'id'),
								role: Reflect.field(stem, 'role'),
								file: Std.string(file)
							});
						}
						if (metadata.length > 0 && updateChartVocalStemMetadata(existingChart, metadata))
							File.saveContent(existingChartPath, CoolUtil.stringifyJson(existingChart));
					} else {
						// A prior import from a narrower engine root may have written
						// this chart before a V-Slice root supplied converted events
						// (a Kade-family chart carries none). Upgrade only the missing
						// events field: existing notes, characters and user edits stay
						// untouched, and a chart that already has events is never
						// modified.
						var existingChart = readSongChart(existingChartPath);
						var existingSong = existingChart == null ? null : Reflect.field(existingChart, 'song');
						var existingEvents:Dynamic = existingSong == null ? null : Reflect.field(existingSong, 'events');
						var hasExistingEvents = existingEvents != null && Std.isOfType(existingEvents, Array)
							&& (cast existingEvents:Array<Dynamic>).length > 0;
						var convertedEvents:Dynamic = Reflect.field(coolSongSong, 'events');
						var hasConvertedEvents = convertedEvents != null && Std.isOfType(convertedEvents, Array)
							&& (cast convertedEvents:Array<Dynamic>).length > 0;
						if (!hasExistingEvents && hasConvertedEvents && existingSong != null) {
							Reflect.setField(existingSong, 'events', convertedEvents);
							File.saveContent(existingChartPath, CoolUtil.stringifyJson(existingChart));
							reportImportProgress('chart-events-upgraded', existingChartPath, i + 1,
								songData.convertedCharts.length, 1, 0, 0);
						}
					}
					requireChartMaterialized(chartDestination);
					writtenCharts++;
			}
		} else if (songData.diffFiles != null) {
			for (i in 0...songData.diffFiles.length) {
				var chartPath = songData.diffFiles[i];
				var coolSong:Dynamic = readSongChart(chartPath);
				if (coolSong == null)
					continue;
				if (songData.engine == ImportEngine.NIGHTMARE_VISION) {
					var nmvChart = NightmareVisionChartCompat.convert(coolSong, chartPath);
					if (nmvChart != null && nmvChart.chart != null && nmvChart.supported)
						coolSong = nmvChart.chart;
					if (nmvChart != null && nmvChart.diagnostics != null)
						for (diagnostic in nmvChart.diagnostics) {
							if (songData.diagnostics == null)
								songData.diagnostics = [];
							if (songData.diagnostics.indexOf(diagnostic) < 0)
								songData.diagnostics.push(diagnostic);
						}
				}
				var coolSongSong:Dynamic = coolSong.song;
				prepareImportedSongIdentity(coolSongSong, songData, targetFolder);
				applyImportedVisualMetadata(coolSongSong, songData);
				applyImportedSidecars(coolSongSong, songData, ratingIndexFor(chartPath, i));
				if (importedVocalStemCount > 0) {
					var vocalMetadata:Array<Dynamic> = [];
					for (stem in (cast importedVocalStems:Array<Dynamic>)) {
						if (stem == null)
							continue;
						var file:Dynamic = Reflect.field(stem, 'file');
						if (file == null)
							file = Reflect.field(stem, 'destination');
						if (file == null || StringTools.trim(Std.string(file)) == '')
							continue;
						vocalMetadata.push({
							id: Reflect.field(stem, 'id'),
							role: Reflect.field(stem, 'role'),
							file: Std.string(file)
						});
					}
					if (vocalMetadata.length > 0) {
						Reflect.setField(coolSongSong, 'vocalStems', vocalMetadata);
						Reflect.setField(coolSongSong, 'needsVoices', true);
					}
				}
				coolSong.song = coolSongSong;
				var fileName = importedChartFileName(targetFolder, chartPath, i, Reflect.field(songData, 'sourceFolder'));
				var chartDestination = Path.join([dataFolder, fileName]);
				var existingChartPath = existingImportChild(dataFolder, fileName);
				if (!FileSystem.exists(existingChartPath)) {
					trace('[import-chart-serialize-start] source=' + chartPath
						+ ' destination=' + chartDestination);
					reportImportProgress('chart-serialize-start', chartPath + ' -> ' + chartDestination,
						i, songData.diffFiles.length);
					File.saveContent(chartDestination, CoolUtil.stringifyJson(coolSong));
					reportImportProgress('charts', chartDestination, i + 1, songData.diffFiles.length, 1, 0, 0);
				} else if (importedVocalStemCount > 0) {
					var existingChart = readSongChart(existingChartPath);
					var expectedVocalMetadata:Dynamic = Reflect.field(coolSongSong, 'vocalStems');
					if (Std.isOfType(expectedVocalMetadata, Array)
						&& updateChartVocalStemMetadata(existingChart, cast expectedVocalMetadata))
						File.saveContent(existingChartPath, CoolUtil.stringifyJson(existingChart));
				}
				requireChartMaterialized(chartDestination);
				writtenCharts++;
			}
		}
		if (writtenCharts == 0)
			return false;

		// V-Slice kinds which have no built-in event equivalent are kept in the
		// engine's existing custom-note metadata channel. Matching HXC note
		// adapters carry their generic callback/source metadata here; unmatched
		// kinds remain identity-only without editing the donor chart.
		if (songData.noteDefinitions != null && songData.noteDefinitions.length > 0) {
			var noteInfoDestination = existingImportChild(dataFolder, 'noteInfo.json');
			if (!FileSystem.exists(noteInfoDestination))
				File.saveContent(Path.join([dataFolder, 'noteInfo.json']),
					CoolUtil.stringifyJson(songData.noteDefinitions));
		}

		// Keep the old Voices.ogg preview/compatibility file for legacy songs and
		// one-stem imports. For a genuinely split V-Slice song, do not duplicate
		// the first stem under Voices.ogg; the chart metadata selects every copied
		// stem explicitly. A donor-provided direct Voices.ogg is still preserved.
		var directVoiceSource = songData.voices != null
			&& Path.withoutDirectory(Path.normalize(songData.voices)).toLowerCase() == 'voices.ogg';
		if (importedVocalStemCount <= 1 || directVoiceSource)
			copyIfPresent(songData.voices, Path.join([songFolder, 'Voices.ogg']));
		if (importedVocalStemCount > 0) {
			for (stem in (cast importedVocalStems:Array<Dynamic>)) {
				if (stem == null)
					continue;
				var source = Std.string(Reflect.field(stem, 'source'));
				var destination = Std.string(Reflect.field(stem, 'destination'));
				if (StringTools.trim(destination) == '' || destination == 'null')
					continue;
				copyIfPresent(source, Path.join([songFolder, destination]));
			}
		}
		copyIfPresent(songData.dialog, Path.join([dataFolder, 'dialog.txt']));
		writeGeneratedDialogue(songData, dataFolder);
		copyIfPresent(songData.dialogueJson, Path.join([dataFolder, 'dialogue.json']));
		copyIfPresent(songData.cutsceneJson, Path.join([dataFolder, 'cutscene.json']));
		copyIfPresent(songData.events, Path.join([dataFolder, 'events.json']));
		if (songData.modchart != null)
			copyIfPresent(songData.modchart, Path.join([dataFolder, 'modchart.hscript']));
		else if (songData.generatedModchart != null && StringTools.trim(songData.generatedModchart) != '') {
			var generatedDestination = existingImportChild(dataFolder, 'modchart.hscript');
			if (!FileSystem.exists(generatedDestination)) {
				ensureDirectory(dataFolder);
				File.saveContent(Path.join([dataFolder, 'modchart.hscript']), songData.generatedModchart);
			}
		}

		if (songData.char == null || StringTools.trim(songData.char) == '' || songData.char.toLowerCase() == 'null')
			songData.char = songData.p2;
		if (songData.category == null || StringTools.trim(songData.category) == '' || songData.category.toLowerCase() == 'null')
			songData.category = 'Imported';

		var foundCategory:Dynamic = null;
		for (coolCategory in coolSongListFile) {
			if (coolCategory != null && StringTools.trim(Std.string(coolCategory.name)).toLowerCase() == songData.category.toLowerCase()) {
				foundCategory = coolCategory;
				break;
			}
		}
		if (foundCategory == null) {
			foundCategory = {name: songData.category, songs: []};
			coolSongListFile.push(foundCategory);
		}
		if (foundCategory.songs == null)
			foundCategory.songs = [];
		// Freeplay's `name` is the storage key used by Song.loadFromJson and
		// DifficultyManager.  Keep a display alias separately when the donor's
		// chart used presentation text instead of its folder id.
		var freeplayEntry:Dynamic = {name: targetFolder, character: songData.char, week: songData.week};
		if (songData.display != null && StringTools.trim(songData.display) != '' && songData.display.toLowerCase() != 'null')
			Reflect.setField(freeplayEntry, 'display', songData.display);
		else if (targetName.toLowerCase() != targetFolder)
			Reflect.setField(freeplayEntry, 'display', targetName);
		var sourceLabel:Dynamic = Reflect.field(songData, 'sourceLabel');
		if (sourceLabel != null && StringTools.trim(Std.string(sourceLabel)) != '')
			Reflect.setField(freeplayEntry, 'sourceLabel', Std.string(sourceLabel));
		var importedArtist:Dynamic = Reflect.field(songData, 'songArtist');
		if (importedArtist != null && StringTools.trim(Std.string(importedArtist)) != '') {
			// `artist` is the donor-facing spelling; `songArtist` mirrors the
			// native chart field for consumers which read Freeplay metadata only.
			Reflect.setField(freeplayEntry, 'artist', Std.string(importedArtist));
			Reflect.setField(freeplayEntry, 'songArtist', Std.string(importedArtist));
		}
		var importedAlbum:Dynamic = Reflect.field(songData, 'album');
		if (importedAlbum != null && StringTools.trim(Std.string(importedAlbum)) != '')
			Reflect.setField(freeplayEntry, 'album', Std.string(importedAlbum));
		var importedRatings:Dynamic = Reflect.field(songData, 'difficultyRatings');
		if (importedRatings != null && Std.isOfType(importedRatings, Array))
			Reflect.setField(freeplayEntry, 'difficultyRatings', importedRatings);
		// Registration is additive.  A partial repair may encounter an entry
		// already present in another category; preserve that user's category,
		// character and flags instead of moving/replacing it.
		var alreadyRegistered = freeplayRegistryHasSong(targetFolder, coolSongListFile);
		if (!alreadyRegistered) {
			foundCategory.songs.push(freeplayEntry);
			File.saveContent(freeplayPath, CoolUtil.stringifyJson(coolSongListFile));
		}
		if (!importBackgroundMode)
			DifficultyManager.addSongSupport(targetFolder);
		return true;
	}

	static public function exportSong(daSong:String) {
		var diffJson:NewSongState.TDifficulties = CoolUtil.parseJson(Assets.getText("assets/images/custom_difficulties/difficulties.json"));
		var exportPath:String = Path.join(["assets", "module", "export", "songs", daSong]);
		var songPath:String = Path.join(["assets", "songs", daSong]);
		var dataPath:String = Path.join(["assets", "data", daSong]);

		ensureDirectory(exportPath);

		copyIfPresent(CoolUtil.getSongFile(daSong, songPath), Path.join([exportPath, 'Inst.ogg']));
		copyIfPresent(CoolUtil.getSongFile(daSong, songPath, false), Path.join([exportPath, 'Voices.ogg']));

		/*if (FileSystem.exists(songPath + '/' + daSong + '_Inst.ogg'))
			File.copy(songPath + '/' + daSong + '_Inst.ogg', exportPath + '/Inst.ogg');
		else if (FileSystem.exists(songPath + '/Inst.ogg'))
			File.copy(songPath + '/Inst.ogg', exportPath + '/Inst.ogg');
		else if (FileSystem.exists(musicPath + daSong + '_Inst.ogg'))
			File.copy(musicPath + daSong + '_Inst.ogg', exportPath + '/Inst.ogg');

		if (FileSystem.exists(songPath + '/' + daSong + '_Voices.ogg'))
			File.copy(songPath + '/' + daSong + '_Voices.ogg', exportPath + '/Voices.ogg');
		else if (FileSystem.exists(songPath + '/Voices.ogg'))
			File.copy(songPath + '/Voices.ogg', exportPath + '/Voices.ogg');
		else if (FileSystem.exists(musicPath + daSong + '_Voices.ogg'))
			File.copy(musicPath + daSong + '_Voices.ogg', exportPath + '/Voices.ogg');*/

		if (FileSystem.exists(Path.join([dataPath, 'dialog.txt'])))
			File.copy(Path.join([dataPath, 'dialog.txt']), Path.join([exportPath, 'dialog.txt']));

		if (FileSystem.exists(Path.join([dataPath, 'modchart.hscript'])))
			File.copy(Path.join([dataPath, 'modchart.hscript']), Path.join([exportPath, 'modchart.hscript']));

		var daInfo:Array<String> = [];
		var songInfo = null;
		if (FileSystem.exists(Path.join([dataPath, daSong + '.json'])))
			songInfo = Path.join([dataPath, daSong + '.json']);
		else
			for (i in 0...diffJson.difficulties.length) {
				if (songInfo == null)
					switch(diffJson.difficulties[i].name) {
						case 'normal':
							//do nothing
						default:
							if (FileSystem.exists(Path.join([dataPath, daSong + '-' + diffJson.difficulties[i].name + '.json'])))
								songInfo = Path.join([dataPath, daSong + '-' + diffJson.difficulties[i].name + '.json']);
					}
			}
		if (songInfo == null)
			return;
		var coolSong:Dynamic = CoolUtil.parseJson(File.getContent(songInfo));
		var coolSongSong:Dynamic = coolSong.song;
		//var epicCategoryJs:Array<Dynamic> = CoolUtil.parseJson(FNFAssets.getText('assets/data/freeplaySongJson.jsonc'));
		// this looks silly but better than it was before
		var infoLines:Array<String> = [
			'This song info was made using CammieEngine',
			'I would recommend replacing any nulls before importing!',
			"It won't import properly if there are nulls (except for char and display)",
			'',
			'songname:' + coolSongSong.song,
			'player1:' + coolSongSong.player1,
			'player2:' + coolSongSong.player2,
			'gf:' + coolSongSong.gf,
			'stage:' + coolSongSong.stage,
			'uiType:' + coolSongSong.uiType,
			'cutsceneType:' + coolSongSong.cutsceneType,
			'isHey:' + coolSongSong.isHey,
			'isCheer:' + coolSongSong.isCheer,
			'isMoody:' + coolSongSong.isMoody,
			'isSpooky:' + coolSongSong.isSpooky,
			'category:null',
			'stageID:' + coolSongSong.stageID,
			'week:-1',
			'char:null',
			'display:null'
		];
		File.saveContent(Path.join([exportPath, 'info.txt']), infoLines.join('\n') + '\n');

		for (i in 0...diffJson.difficulties.length) {
			switch(diffJson.difficulties[i].name) {
				case 'normal':
					if (FileSystem.exists(Path.join([dataPath, daSong + '.json'])))
						File.copy(Path.join([dataPath, daSong + '.json']), Path.join([exportPath, diffJson.difficulties[i].name + '.json']));
				default:
					if (FileSystem.exists(Path.join([dataPath, daSong + '-' + diffJson.difficulties[i].name + '.json'])))
						File.copy(Path.join([dataPath, daSong + '-' + diffJson.difficulties[i].name + '.json']), Path.join([exportPath, diffJson.difficulties[i].name + '.json']));
			}
		}
	}

	static public function importStage(stageData:StageImport) {
		#if sys
		if (stageData == null || !validModuleName(stageData.name) || !validModuleName(stageData.like)) {
			trace('Unable to import stage: invalid name');
			return;
		}
		var targetFolder = Path.join(['assets', 'images', 'custom_stages', StringTools.trim(stageData.name)]);
		if (FileSystem.exists(targetFolder) && !FileSystem.isDirectory(targetFolder)) {
			trace('Unable to import stage: target path is not a directory');
			return;
		}
		ensureDirectory(targetFolder);
		if (stageData.assets != null)
			for (epicFile in stageData.assets) {
				if (!validImportPath(epicFile))
					continue;
				var fileName = Path.withoutDirectory(Path.normalize(epicFile));
				if (fileName != '' && fileName != '.' && fileName != '..')
					File.copy(epicFile, Path.join([targetFolder, fileName]));
			}
		
		if (validModuleName(stageData.like) && validImportPath(stageData.likePath)) {
			var scriptPath = Path.join(['assets', 'images', 'custom_stages', StringTools.trim(stageData.like) + '.hscript']);
			if (!FileSystem.exists(scriptPath))
				File.copy(stageData.likePath, scriptPath);
		}

		var epicStageFile:Dynamic = CoolUtil.parseJson(FNFAssets.getText('assets/images/custom_stages/custom_stages.json'));
		if (epicStageFile == null)
			epicStageFile = {};
		Reflect.setField(epicStageFile, StringTools.trim(stageData.name), StringTools.trim(stageData.like));

		File.saveContent('assets/images/custom_stages/custom_stages.json', CoolUtil.stringifyJson(epicStageFile));
		Song.invalidateVisualRegistryCache();
		#end
	}
	static public function exportStage(daStage:String) {
		var exportPath = 'assets/module/export/stages/' + daStage + '/';
		var stagePath = 'assets/images/custom_stages/';

		var epicStageFile:Dynamic = CoolUtil.parseJson(FNFAssets.getText('assets/images/custom_stages/custom_stages.json'));

		if (!FileSystem.exists(exportPath)) {
			FileSystem.createDirectory(exportPath);
			FileSystem.createDirectory(exportPath + 'assets');
		}

		for (asset in ImportDirectoryListing.normalize(FileSystem.readDirectory(stagePath + daStage))) {
			File.copy(stagePath + daStage + '/' + asset, exportPath + 'assets/' + asset);
		}

		var stageHScript = Reflect.field(epicStageFile, daStage);
		if (FileSystem.exists(stagePath + stageHScript + '.hscript')) {
			File.copy(stagePath + stageHScript + '.hscript', exportPath + 'like.hscript');
		}
	}

	static public function importChar(charData:CharImport) {
		#if sys
		if (charData == null || !validModuleName(charData.name) || !validModuleName(charData.like)
			|| charData.assets == null || !validImportPath(charData.assets.charpng)
			|| !validImportPath(charData.assets.charxml)) {
			trace('Unable to import character: missing required files or invalid name');
			return;
		}
		var targetFolder = Path.join(['assets', 'images', 'custom_chars', StringTools.trim(charData.name)]);
		if (FileSystem.exists(targetFolder) && !FileSystem.isDirectory(targetFolder)) {
			trace('Unable to import character: target path is not a directory');
			return;
		}
		ensureDirectory(targetFolder);
		File.copy(charData.assets.charpng, Path.join([targetFolder, 'char.png']));

		if (StringTools.endsWith(charData.assets.charxml, "xml"))
			File.copy(charData.assets.charxml, Path.join([targetFolder, 'char.xml']));
		else
			File.copy(charData.assets.charxml, Path.join([targetFolder, 'char.txt']));

		if (validImportPath(charData.assets.deadpng) && validImportPath(charData.assets.deadxml)) {
			File.copy(charData.assets.deadpng, Path.join([targetFolder, 'dead.png']));
			File.copy(charData.assets.deadxml, Path.join([targetFolder, 'dead.xml']));
		}
		if (validImportPath(charData.assets.crazypng) && validImportPath(charData.assets.crazyxml)) {
			File.copy(charData.assets.crazypng, Path.join([targetFolder, 'crazy.png']));
			File.copy(charData.assets.crazyxml, Path.join([targetFolder, 'crazy.xml']));
		}
		if (validImportPath(charData.assets.icons))
			File.copy(charData.assets.icons, Path.join([targetFolder, 'icons.png']));

		if (validImportPath(charData.likePath)) {
			var scriptPath = Path.join(['assets', 'images', 'custom_chars', StringTools.trim(charData.like) + '.hscript']);
			if (!FileSystem.exists(scriptPath))
				File.copy(charData.likePath, scriptPath);
		}

		var epicCharFile:Dynamic = CoolUtil.parseJson(FNFAssets.getJson('assets/images/custom_chars/custom_chars'));
		if (epicCharFile == null)
			epicCharFile = {};
		var commaSeperatedColors = charData.colors == null ? ['255', '255', '255'] : charData.colors.split(",");
		var iconNums = charData.iconNums == null ? [] : charData.iconNums.copy();
		while (iconNums.length < 4)
			iconNums.push(0);
		Reflect.setField(epicCharFile, StringTools.trim(charData.name), {like:StringTools.trim(charData.like),icons: [Std.int(iconNums[0]),Std.int(iconNums[1]),Std.int(iconNums[2]),Std.int(iconNums[3])], colors: commaSeperatedColors});

		File.saveContent('assets/images/custom_chars/custom_chars.jsonc', CoolUtil.stringifyJson(epicCharFile));
		CoolUtil.formatCustomChars();
		Song.invalidateVisualRegistryCache();
		#end
	}

	static public function exportChar(daChar:String) {
		var exportPath = 'assets/module/export/characters/' + daChar + '/';
		var charPath = 'assets/images/custom_chars/' + daChar + '/';

		var epicCharFile:Dynamic = CoolUtil.parseJson(FNFAssets.getJson('assets/images/custom_chars/custom_chars'));

		if (!FileSystem.exists(exportPath)) {
			FileSystem.createDirectory(exportPath);
		}

		File.copy(charPath + 'char.png', exportPath + 'char.png');
		File.copy(charPath + 'char.xml', exportPath + 'char.xml');
		File.copy(charPath + 'icons.png', exportPath + 'icons.png');
		if (FileSystem.exists(charPath + 'icons.xml'))
			File.copy(charPath + 'icons.xml', exportPath + 'icons.xml');

		if (FileSystem.exists(charPath + 'dead.png')) {
			File.copy(charPath + 'dead.png', exportPath + 'dead.png');
			File.copy(charPath + 'dead.xml', exportPath + 'dead.xml');
		}

		if (FileSystem.exists(charPath + 'crazy.png')) {
			File.copy(charPath + 'crazy.png', exportPath + 'crazy.png');
			File.copy(charPath + 'crazy.xml', exportPath + 'crazy.xml');
		}

		/*File.copy(charPath + '../' + Reflect.field(charJson, daChar).like + '.hscript', exportPath + 'like.hscript');

		var sussyInfo = "This song info was made using CammieEngine\n" +
		"I would recommend replacing any nulls before importing!\n\n" +
		"charname:" + daChar +
		"like:" + Reflect.field(charJson, daChar).like +
		"iconnums:" + Reflect.field(charJson, daChar).icons +
		"colors:" + Reflect.field(charJson, daChar).colors;
		File.saveContent(exportPath + '/info.txt', sussyInfo);*/
	}

	static public function psychCharDecode(assetsPath:String, daChar:String) {
		var charPath = haxe.io.Path.join([assetsPath, 'characters/']);

		var charJson = CoolUtil.parseJson(File.getContent(haxe.io.Path.join([charPath, daChar + '.json'])));

		var charcreation:CharCreation = {
			path: assetsPath,
			charjson: charJson,
			ogname: daChar,
			name: daChar,
			like: daChar,
			isPixel: false,
			isBF: false,
			isGF: false
		};

		return charcreation;
	}

	static public function psychToDisChar(charcreation:CharCreation,
		destinationAssetRoot:String = 'assets') {
		#if sys
		if (charcreation == null || charcreation.charjson == null || !validModuleName(charcreation.name))
			return;
		var assetRoot = psychDestinationAssetRoot(destinationAssetRoot);
		if (assetRoot == '')
			return;
		// Assets path is the actual assets path for psych or the mod in the mods folder
		var assetsPath = charcreation.path;
		var charJson = charcreation.charjson;
		var imageValue:Dynamic = Reflect.field(charJson, 'image');
		var sourceAtlases = psychImageSources(assetsPath, imageValue == null ? '' : Std.string(imageValue));
		if (sourceAtlases.length == 0)
			return;

		var customCharsRoot = Path.join([assetRoot, 'images', 'custom_chars']);
		var exportPath = Path.join([customCharsRoot, charcreation.name]);

		ensureDirectory(exportPath);
		var atlasFiles:Array<String> = [];
		for (i in 0...sourceAtlases.length) {
			var atlasName = i == 0 ? 'char' : 'char-' + i;
			atlasFiles.push(atlasName);
			var charPng = Path.join([exportPath, atlasName + '.png']);
			var charXml = Path.join([exportPath, atlasName + '.xml']);
			if (!FileSystem.exists(charPng))
				File.copy(sourceAtlases[i].png, charPng);
			if (!FileSystem.exists(charXml))
				File.copy(sourceAtlases[i].xml, charXml);
		}

		var healthIcon:Dynamic = Reflect.field(charJson, 'healthicon');
		var sourceIcon = psychIconSource(assetsPath, healthIcon == null ? '' : Std.string(healthIcon));
		var iconDestination = Path.join([exportPath, 'icons.png']);
		if (sourceIcon != null && !FileSystem.exists(iconDestination))
			File.copy(sourceIcon, iconDestination);

		// oh god my coding is absolutely terrible to look at

		var scriptPath = Path.join([customCharsRoot, charcreation.like + '.hscript']);
		if (!FileSystem.exists(scriptPath))
			File.saveContent(scriptPath, PsychCharacterDanceCompat.renderStandardScript(charJson,
				charcreation.isPixel, charcreation.isBF, charcreation.isGF, false, atlasFiles));

		// Keep the registry write separate from file materialization so a later
		// duplicate/re-import can repair a partially completed character without
		// replacing its existing atlas or generated script.
		ensurePsychCharacterRegistryEntry(charcreation.name, charJson, assetRoot);
		#end
	}

	static public function importWeek(weekData:WeekImport) {
		#if sys
		var parsedWeekJson:StoryMenuState.StorySongsJson = CoolUtil.parseJson(FNFAssets.getJson("assets/data/storySonglist"));
		
		File.copy(weekData.assets.png, 'assets/images/campaign-ui-week/' + weekData.name + '.png');

		File.copy(weekData.assets.xml, 'assets/images/campaign-ui-week/' + weekData.name + '.xml');

		var coolObject:StoryMenuState.WeekInfo = {animation: weekData.like, name: weekData.name, desc: weekData.desc, bf: weekData.bf, gf: weekData.gf, dad: weekData.dad, songs: weekData.songs};
		parsedWeekJson.weeks.push(coolObject);
		
		File.saveContent('assets/data/storySonglist.json', CoolUtil.stringifyJson(parsedWeekJson));
		#end
	}
}
