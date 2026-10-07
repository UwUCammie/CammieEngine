package;

import haxe.io.Path;
using StringTools;

#if sys
import haxe.io.Bytes;
import sys.FileSystem;
import sys.io.File;
import sys.io.FileInput;
#end

/** Filesystem locations belonging to one detected game/mod root. */
typedef ImportRootAssetSource = {
	var path:String;
	/** Destination path relative to the runtime `assets/` directory. */
	var destinationPrefix:String;
}

typedef ImportRootPaths = {
	var data:String;
	var audio:String;
	var images:String;
	var shared:String;
	var scripts:String;
	@:optional var supplementalAssetRoots:Array<ImportRootAssetSource>;
}

/** A root plus the evidence that made Auto choose its engine. */
typedef ImportRoot = {
	var root:String;
	var contentRoot:String;
	var engine:String;
	var confidence:Float;
	var evidence:Array<String>;
	var data:String;
	var audio:String;
	var images:String;
	var shared:String;
	var scripts:String;
	/** Additional logical asset roots from a source project mapping. */
	@:optional var supplementalAssetRoots:Array<ImportRootAssetSource>;
	var paths:ImportRootPaths;
}

typedef ImportRootScanProgress = {
	var phase:String;
	var current:String;
	var completed:Int;
	var total:Int;
}

/** A bounded root walk can finish successfully while still leaving queued
	 * directories unvisited.  Keep this diagnostic separate from progress so
	 * callers can explain that Auto may have missed a root instead of treating
	 * the partial result as a complete empty scan. */
typedef ImportRootScanDiagnostic = {
	var code:String;
	var severity:String;
	var message:String;
	var scannedDirectories:Int;
	var directoryLimit:Int;
	var queuedDirectories:Int;
}

/** Detailed result for callers that need to distinguish a complete walk from
	 * one stopped by the safety cap.  `scan()` remains the compatibility API and
	 * returns only `roots`. */
typedef ImportRootScanResult = {
	var roots:Array<ImportRoot>;
	var diagnostics:Array<ImportRootScanDiagnostic>;
	var truncated:Bool;
	var scannedDirectories:Int;
	var directoryLimit:Int;
	var queuedDirectories:Int;
}

/**
	Callbacks are optional, which keeps the detector useful from synchronous
	tools/tests while ImportWorkflow can inject its worker cancellation and UI
	progress mailbox.  The callback code is guarded so a UI exception cannot
	abort filesystem discovery.
*/
typedef ImportRootScanCallbacks = {
	@:optional var onProgress:ImportRootScanProgress->Void;
	@:optional var isCancelled:Void->Bool;
}

/**
	Discover independent game/mod roots below a selected parent.

	The scanner only inspects directory metadata and a small number of chart
	entries.  It never copies files and never walks media trees such as images,
	songs, videos, or plugins.  `FileSystem.fullPath` follows symlinks, and the
	device/inode identity is included where available so symlink loops and
	hard-linked aliases cannot make an unbounded traversal.
*/
class ImportRootScanner {
	#if target.threaded
	static var retainedEngines = new sys.thread.Tls<Map<String, String>>();
	static var retainedRoots = new sys.thread.Tls<Map<String, String>>();
	#else
	static var retainedEngines:Map<String, String>;
	static var retainedRoots:Map<String, String>;
	#end

	/** Scope trusted original scan identities to the current import worker.
	 * Returning the previous map lets callers restore nested contexts. */
	public static function setRetainedSourceEngines(engines:Map<String, String>):Map<String, String> {
		#if target.threaded
		var previous = retainedEngines.value;
		retainedEngines.value = engines;
		#else
		var previous = retainedEngines;
		retainedEngines = engines;
		#end
		return previous;
	}

	/** Scope an exact retained-root allowlist to the current import worker.
	 * Paths are the selected roots inside the retained snapshot, not owner names.
	 * A null map leaves ordinary interactive scans unchanged; an empty map rejects
	 * every detected root until the previous scope is restored. */
	public static function setRetainedSourceRoots(roots:Map<String, String>):Map<String, String> {
		#if target.threaded
		var previous = retainedRoots.value;
		retainedRoots.value = roots;
		#else
		var previous = retainedRoots;
		retainedRoots = roots;
		#end
		return previous;
	}

	/** True when a discovered root is in the active retained import selection.
	 * This also gates legacy package discovery that can otherwise bypass the
	 * root scanner by walking a selected parent directly. */
	public static function retainedSourceRootAllowed(root:String, engine:String):Bool {
		#if target.threaded
		var allowedRoots = retainedRoots.value;
		#else
		var allowedRoots = retainedRoots;
		#end
		if (allowedRoots == null) return true;
		var normalized = canonicalize(root);
		if (normalized == '') return false;
		var normalizedEngine = ImportEngine.normalize(engine);
		for (path in allowedRoots.keys()) {
			var known = canonicalize(path);
			#if windows
			var samePath = known.toLowerCase() == normalized.toLowerCase();
			#else
			var samePath = known == normalized;
			#end
			if (samePath)
				return ImportEngine.normalize(allowedRoots.get(path)) == normalizedEngine;
		}
		return false;
	}
	public static inline var MAX_DEPTH:Int = 10;
	public static inline var MAX_DIRECTORIES:Int = 8192;
	static inline var MAX_LUA_SONG_DIRECTORIES:Int = 24;
	static inline var MAX_NESTED_LUA_SONG_DIRECTORIES:Int = 64;
	static inline var MAX_NIGHTMARE_VISION_SONG_DIRECTORIES:Int = 64;
	static inline var MAX_NIGHTMARE_VISION_CHART_PROBES:Int = 128;
	static inline var MAX_ENGINE_CHART_BYTES:Int = 4 * 1024 * 1024;
	static inline var MAX_PROJECT_MARKER_BYTES:Int = 1024 * 1024;
	// Keep V-Slice detection bounded, but leave enough room for exports that
	// sort placeholder/bonus song folders and metadata before the first real
	// chart pair.  The old 24/48 probe could reject a valid root before the
	// importer had a chance to inspect it.
	static inline var MAX_VSLICE_SONG_DIRECTORIES:Int = 128;
	static inline var MAX_VSLICE_SONG_FILES:Int = 128;
	// Codename probes stay bounded for the same reason as the V-Slice ones.
	static inline var MAX_CODENAME_SONG_DIRECTORIES:Int = 64;
	static inline var MAX_CODENAME_MOD_DIRECTORIES:Int = 16;
	// Executables are probed in a fixed-size stream.  The marker strings in
	// the supplied Windows builds occur between 10 and 24 MiB; this bound
	// catches those while never allocating a whole executable in memory.
	static inline var EXECUTABLE_PROBE_CHUNK:Int = 64 * 1024;
	static inline var EXECUTABLE_PROBE_LIMIT:Int = 32 * 1024 * 1024;
	static inline var MAX_EXECUTABLE_PROBES:Int = 4;

	/** Scan in Auto mode. */
	public static function scan(sourcePath:String, ?requestedEngine:String = ImportEngine.AUTO,
		?callbacks:ImportRootScanCallbacks):Array<ImportRoot> {
		return scanDetailed(sourcePath, requestedEngine, callbacks).roots;
	}

	/**
		Scan and retain bounded-walk diagnostics.  The optional directory limit is
		an internal/test seam: production callers use MAX_DIRECTORIES, while
		synthetic tests can exercise truncation with a handful of directories.
	*/
	public static function scanDetailed(sourcePath:String, ?requestedEngine:String = ImportEngine.AUTO,
		?callbacks:ImportRootScanCallbacks, ?directoryLimit:Int):ImportRootScanResult {
		var found:Array<ImportRoot> = [];
		var diagnostics:Array<ImportRootScanDiagnostic> = [];
		var effectiveLimit = boundedDirectoryLimit(directoryLimit);
		var scanned = 0;
		var queued = 0;
		var truncated = false;
		#if sys
		var root = canonicalize(sourcePath);
		if (root == '' || !FileSystem.exists(root) || !FileSystem.isDirectory(root))
			return {
				roots: found,
				diagnostics: diagnostics,
				truncated: false,
				scannedDirectories: 0,
				directoryLimit: effectiveLimit,
				queuedDirectories: 0
			};

		var selected = ImportEngine.normalize(requestedEngine);
		var queue:Array<{path:String, depth:Int}> = [{path:root, depth:0}];
		var visited:Map<String, Bool> = new Map<String, Bool>();
		var roots:Map<String, Bool> = new Map<String, Bool>();
		var executableMarkerCache:Map<String, Array<String>> = new Map();
		var cursor = 0;
		var cancelledScan = false;

		while (cursor < queue.length && scanned < effectiveLimit) {
			if (cancelled(callbacks)) {
				cancelledScan = true;
				break;
			}
			var item = queue[cursor++];
			var current = canonicalize(item.path);
			if (current == '')
				continue;
			var identity = identityKey(current);
			if (identity == '' || visited.exists(identity))
				continue;
			visited.set(identity, true);
			scanned++;
			report(callbacks, 'scan-roots', current, scanned, effectiveLimit);

			// The directory listing is also needed to queue children below. Keep
			// one sorted listing for this scan node and share it with classification
			// instead of rereading the same directory for each engine candidate.
			var entries = readDirectory(current);
			var match = inspectRootWithEntries(current, selected, entries, executableMarkerCache);
			if (match != null) {
				// A compiled Codename release classifies as Codename through its
				// mods/ content tree, but the expectation stays "import the mod
				// source"; name that precisely before the importer recovers the
				// mods folders.
				if (match.engine == ImportEngine.CODENAME && isCompiledCodenameRelease(current)) {
					diagnostics.push({
						code: 'codename-compiled-release',
						severity: 'info',
						message: '[codename-compiled-release] ' + Path.withoutDirectory(current)
							+ ': compiled Codename release detected (mods/ content tree, no importable song sources at the root). '
							+ 'Import the mod source download; the importer recovers songs from mods/<name> folders that carry complete content.',
						scannedDirectories: scanned,
						directoryLimit: 0,
						queuedDirectories: 0
					});
				}
				var rootKey = identityKey(match.root);
				var isContentChild = false;
				// A game root with an `assets/` child and that child itself both
				// satisfy the generic layout.  They are one import unit, not two
				// independent mods.  Keep sibling/nested `mods/<name>` roots.
				for (existing in found) {
					if (identityKey(existing.contentRoot) == rootKey) {
						isContentChild = true;
						break;
					}
					// A selected NMV game root imports its playable content/<pack>
					// packages through one owner. Keep those package roots selectable
					// on their own, but do not report duplicate engine roots when the
					// whole game was selected.
					if (existing.engine == ImportEngine.NIGHTMARE_VISION
						&& isNightmareVisionContentPackage(existing.root, match.root)) {
						isContentChild = true;
						break;
					}
				}
				if (rootKey != '' && !roots.exists(rootKey) && !isContentChild
					&& retainedSourceRootAllowed(match.root, match.engine)) {
					roots.set(rootKey, true);
					found.push(match);
				}
			}

			if (item.depth >= MAX_DEPTH)
				continue;
			// A Haxe project manifest without importable content is an incomplete
			// download.  Explain it in the scan diagnostics and keep walking; the
			// root itself is skipped because inspectRoot returned no match.
			if (match == null) {
				var incomplete = incompleteSourceReleaseMessage(current, entries);
				if (incomplete != '')
					diagnostics.push({
						code: 'source-release-incomplete',
						severity: 'warning',
						message: incomplete,
						scannedDirectories: scanned,
						directoryLimit: 0,
						queuedDirectories: 0
					});
			}
			for (entry in entries) {
				if (cancelled(callbacks)) {
					cancelledScan = true;
					break;
				}
				var lower = entry.toLowerCase();
				if (shouldSkipDirectory(lower))
					continue;
				var child = Path.join([current, entry]);
				try {
					if (FileSystem.isDirectory(child))
						queue.push({path:child, depth:item.depth + 1});
				} catch (_:Dynamic) {}
			}
		}
		queued = Std.int(Math.max(0, queue.length - cursor));
		truncated = !cancelledScan && scanned >= effectiveLimit && queued > 0;
		if (truncated) {
			diagnostics.push({
				code: 'root-scan-truncated',
				severity: 'error',
				message: 'Auto root scan stopped after scanning ' + scanned + ' directories (limit ' + effectiveLimit
					+ '); ' + queued + ' queued directories were not inspected. Some import roots may be missing. Select a narrower source folder and scan again.',
				scannedDirectories: scanned,
				directoryLimit: effectiveLimit,
				queuedDirectories: queued
			});
		}
		#end
		return {
			roots: found,
			diagnostics: diagnostics,
			truncated: truncated,
			scannedDirectories: scanned,
			directoryLimit: effectiveLimit,
			queuedDirectories: queued
		};
	}

	/** Test/tooling alias for the bounded detailed scan seam. */
	public static function scanBounded(sourcePath:String, directoryLimit:Int,
		?requestedEngine:String = ImportEngine.AUTO, ?callbacks:ImportRootScanCallbacks):ImportRootScanResult {
		return scanDetailed(sourcePath, requestedEngine, callbacks, directoryLimit);
	}

	public static function scanAuto(sourcePath:String, ?callbacks:ImportRootScanCallbacks):Array<ImportRoot> {
		return scan(sourcePath, ImportEngine.AUTO, callbacks);
	}

	/** Descriptive aliases for callers that use discovery terminology. */
	public static function scanRoots(sourcePath:String, ?requestedEngine:String = ImportEngine.AUTO,
		?callbacks:ImportRootScanCallbacks):Array<ImportRoot> {
		return scan(sourcePath, requestedEngine, callbacks);
	}

	public static function discoverRoots(sourcePath:String, ?requestedEngine:String = ImportEngine.AUTO,
		?callbacks:ImportRootScanCallbacks):Array<ImportRoot> {
		return scan(sourcePath, requestedEngine, callbacks);
	}

	static function boundedDirectoryLimit(requested:Null<Int>):Int {
		if (requested == null || requested <= 0)
			return MAX_DIRECTORIES;
		return requested > MAX_DIRECTORIES ? MAX_DIRECTORIES : requested;
	}

	/** Inspect one known root without recursively scanning its parent. */
	public static function inspectRoot(rootPath:String, ?requestedEngine:String = ImportEngine.AUTO):ImportRoot {
		#if sys
		var root = canonicalize(rootPath);
		if (root == '' || !FileSystem.exists(root) || !FileSystem.isDirectory(root))
			return null;
		return inspectRootWithEntries(root, ImportEngine.normalize(requestedEngine), readDirectory(root), new Map());
		#else
		return null;
		#end
	}

	#if sys
	static function inspectRootWithEntries(root:String, requestedEngine:String, rootEntries:Array<String>,
		executableMarkerCache:Map<String, Array<String>>):ImportRoot {
		var layout = resolveLayout(root, rootEntries);
		var nightmareVisionProject = hasNightmareVisionSourceProject(root, rootEntries);
		var nestedNightmareVisionChart = hasNightmareVisionNestedSongChartFormat(root, rootEntries);
		var nightmareVisionChart = hasNightmareVisionChartFormat(layout.data) || nestedNightmareVisionChart;
		var nestedNightmareVisionOwner = nightmareVisionContentOwner(root, executableMarkerCache);
		var nestedNightmareVisionSongs = nestedNightmareVisionOwner != ''
			&& hasNightmareVisionNestedSongLayout(root, rootEntries);
		if ((nestedNightmareVisionSongs || nestedNightmareVisionChart)
			&& (layout.data == null || layout.data == '')) {
			var nestedSongsRoot = findDirectory(rootEntries, root, 'songs');
			if (nestedSongsRoot != '')
				layout.data = nestedSongsRoot;
		}
		if (!hasImportShape(root, layout, rootEntries) && !nightmareVisionProject && !nightmareVisionChart
			&& !nestedNightmareVisionSongs)
			return null;
		var executableMarkers = probeExecutableMarkers(root, rootEntries, executableMarkerCache);
		var lowerRootEntries:Array<String> = [for (entry in rootEntries) entry.toLowerCase()];
		var selected = ImportEngine.normalize(requestedEngine);
		var retainedEngine = retainedSourceEngine(root);
		if (selected == ImportEngine.AUTO && retainedEngine != '')
			selected = retainedEngine;
		var evidenceByEngine:Map<String, Array<String>> = new Map<String, Array<String>>();
		var scores:Map<String, Int> = new Map<String, Int>();
		var enginesToScore = [ImportEngine.V_SLICE, ImportEngine.KADE, ImportEngine.MODDING_PLUS,
			ImportEngine.NIGHTMARE_VISION, ImportEngine.PSYCH, ImportEngine.FPS_PLUS, ImportEngine.CODENAME,
			ImportEngine.LEGACY_POLYMOD];
		if (selected != ImportEngine.AUTO)
			enginesToScore = [selected];
		for (engine in enginesToScore) {
			var result = scoreEngine(root, layout, engine, executableMarkers, rootEntries, lowerRootEntries);
			scores.set(engine, result.score);
			evidenceByEngine.set(engine, result.evidence);
		}

		var bestEngine = ImportEngine.LEGACY_POLYMOD;
		var bestScore = 0;
		var order = [ImportEngine.V_SLICE, ImportEngine.KADE, ImportEngine.MODDING_PLUS,
			ImportEngine.NIGHTMARE_VISION, ImportEngine.PSYCH, ImportEngine.FPS_PLUS, ImportEngine.CODENAME,
			ImportEngine.LEGACY_POLYMOD];
		for (engine in order) {
			var score = scores.get(engine);
			if (score != null && score > bestScore) {
				bestScore = score;
				bestEngine = engine;
			}
		}
		if (selected != ImportEngine.AUTO) {
			bestEngine = selected;
			bestScore = scores.exists(selected) ? scores.get(selected) : 0;
		}
		if (selected == ImportEngine.AUTO && nestedNightmareVisionOwner != '') {
			bestEngine = ImportEngine.NIGHTMARE_VISION;
			bestScore = 150;
		}
		// A generic data/assets directory with no engine marker is not an
		// Auto match.  Explicit engine selection may still inspect it.
		if (selected == ImportEngine.AUTO && bestScore < 20)
			return null;

		var evidence = evidenceByEngine.get(bestEngine);
		if (evidence == null)
			evidence = [];
		if (retainedEngine == bestEngine)
			evidence.push('Engine identity retained from the original source scan');
		if (nestedNightmareVisionOwner != '' && bestEngine == ImportEngine.NIGHTMARE_VISION)
			evidence.push('Nested content package inherits Nightmare Vision identity from its parent game root');
		var confidence = Math.min(1.0, bestScore / 100.0);
		return {
			root: root,
			contentRoot: layout.contentRoot,
			engine: bestEngine,
			confidence: confidence,
			evidence: evidence.copy(),
			data: layout.data,
			audio: layout.audio,
			images: layout.images,
			shared: layout.shared,
			scripts: layout.scripts,
			supplementalAssetRoots: layout.supplementalAssetRoots,
			paths: {
				data: layout.data,
				audio: layout.audio,
				images: layout.images,
				shared: layout.shared,
				scripts: layout.scripts,
				supplementalAssetRoots: layout.supplementalAssetRoots
			}
		};
	}
	#end

	public static function detectEngine(rootPath:String):String {
		var root = inspectRoot(rootPath, ImportEngine.AUTO);
		return root == null ? '' : root.engine;
	}

	/** Normalize native and legacy Windows spellings to a stable path. */
	public static function canonicalize(path:String):String {
		if (path == null)
			return '';
		var value = StringTools.trim(Std.string(path));
		if (value == '')
			return '';
		value = StringTools.replace(value, '\\', '/');
		var unc = value.startsWith('//');
		#if sys
		try {
			value = FileSystem.fullPath(value);
		} catch (_:Dynamic) {}
		#end
		value = Path.normalize(value);
		if (unc && !value.startsWith('//')) {
			while (value.startsWith('/'))
				value = value.substr(1);
			value = value == '' ? '//' : '//' + value;
		}
		return value;
	}

	#if sys
	static function scoreEngine(root:String, layout:Dynamic, engine:String,
		executableMarkers:Array<String>, entries:Array<String>, lowerEntries:Array<String>):{score:Int, evidence:Array<String>} {
		var score = 0;
		var evidence:Array<String> = [];
		var hasAssets = hasDirectory(entries, 'assets');
		var hasManifest = hasDirectory(entries, 'manifest') || hasFile(entries, 'manifest.json');
		var hasPolymod = hasFile(entries, '_polymod_meta.json');
		var hasPack = hasFile(entries, 'pack.json');
		var hasMeta = hasFile(entries, 'meta.json');
		var hasKadeExecutable = hasKadeMarker(lowerEntries);
		var directData = hasDirectory(entries, 'data');
		var directSongs = hasDirectory(entries, 'songs');
		var directImages = hasDirectory(entries, 'images');
		var directScripts = hasDirectory(entries, 'scripts');

			switch (engine) {
			case ImportEngine.V_SLICE:
				if (hasPolymod) {
					score += 30;
					evidence.push('V-Slice/Polymod marker: _polymod_meta.json');
				}
				if (hasVSlicelikeCharts(layout.data)) {
					score += 60;
					evidence.push('V-Slice chart pair: data/songs/*/*-metadata.json and *-chart.json');
				}
				if (hasDirectory(entries, 'shared') && directData && directSongs) {
					score += 10;
					evidence.push('V-Slice content layout: data + songs + shared');
				}
				if (root.toLowerCase().indexOf('v-slice') >= 0) {
					score += 10;
					evidence.push('V-Slice name marker in selected root');
				}

			case ImportEngine.KADE:
				if (hasKadeExecutable) {
					score += 90;
					evidence.push('Kade Engine executable marker');
				}
				if (hasMarker(executableMarkers, 'kadedev') || hasMarker(executableMarkers, 'kadeenginedata')) {
					score += 85;
					evidence.push('Kade binary marker: KadeDev/KadeEngineData');
				}
				if (hasAssets && hasManifest) {
					score += 10;
					evidence.push('Kade/legacy packaged assets + manifest');
				}
				// Kade-family SOURCE releases ship the compiled game's project tree
				// (Project.xml + source/*.hx) beside the same assets/ layout.  They
				// import through the Kade path, and KadeStageSource reads the authored
				// stage code out of source/PlayState.hx during import.
				if (hasHaxeProjectManifest(entries)) {
					score += 90;
					evidence.push('Haxe source release: Project.xml + source/*.hx');
				} else if (hasHaxeSourceDirectory(root, entries)) {
					// A bare source checkout that lost its project manifest still
					// outranks the generic legacy assets layout.
					score += 40;
					evidence.push('Haxe source modules: source/*.hx');
				}

			case ImportEngine.MODDING_PLUS:
				if (hasMarker(executableMarkers, 'modding plus')
					|| hasMarker(executableMarkers, 'friday night funkin\' modding plus')) {
					score += 120;
					evidence.push('Modding Plus executable marker');
				}
				if (hasCustomRegistry(layout.images)) {
					score += 85;
					evidence.push('Modding Plus custom character/stage/UI registries');
				}
				if (hasAssets && layout.data != '' && layout.audio != '') {
					score += 15;
					evidence.push('Modding Plus assets/data + song audio layout');
				}

			case ImportEngine.NIGHTMARE_VISION:
				if (hasMarker(executableMarkers, 'com.nmvteam.nightmareengine')) {
					score += 150;
					evidence.push('Nightmare Vision executable package marker: com.nmvTeam.nightmareEngine');
				}
				if (hasNightmareVisionSourceProject(root, entries)) {
					score += 150;
					evidence.push('Nightmare Vision Haxe project package: com.nmvTeam.nightmareEngine');
				}
				if (hasNightmareVisionChartFormat(layout.data)) {
					score += 120;
					evidence.push('Nightmare Vision chart metadata: format=nmv2');
				}
				if (hasNightmareVisionNestedSongChartFormat(root, entries)) {
					score += 120;
					evidence.push('Nightmare Vision nested chart metadata: format=nmv2 in songs/<song>/data');
				}

			case ImportEngine.PSYCH:
				if (hasMarker(executableMarkers, 'psychlua')
					|| hasMarker(executableMarkers, 'psychanimationcontroller')
					|| hasMarker(executableMarkers, 'psychengineversion')) {
					// Some Psych forks retain KadeDev/KadeEngineData strings in
					// shared framework code.  A Psych-specific class marker wins
					// over that generic legacy string.
					score += 120;
					evidence.push('Psych Engine executable marker: Psych Lua/version runtime');
				}
				if (hasPsychSourceProject(root, entries)) {
					score += 120;
					evidence.push('Psych Engine Haxe source project: Project.xml + source/psychlua/*.hx');
				}
				if (hasPack) {
					score += 45;
					evidence.push('Psych Engine pack.json marker');
				}
				if (hasDirectory(entries, 'custom_events') || hasDirectory(entries, 'custom_notetypes')) {
					score += 25;
					evidence.push('Psych Engine custom_events/custom_notetypes directory');
				}
				if (directData && directSongs && directImages && hasDirectory(entries, 'characters')
					&& hasDirectory(entries, 'stages') && directScripts) {
					score += 30;
					evidence.push('Psych Engine direct data/songs/images/characters/stages/scripts layout');
				}
				if (hasLuaFile(entries, layout.data)) {
					score += 10;
					evidence.push('Psych Engine Lua chart/script content');
				}
				if (score < 20 && hasThinPsychPackage(root, layout.data)) {
					score += 25;
					evidence.push('Psych Engine section chart + callback Lua + week metadata');
				}
				if (hasPsychSongDataCharts(layout.data)) {
					score += 85;
					evidence.push('Psych Engine chart layout: data/songData/<song>/*.json');
				}

			case ImportEngine.FPS_PLUS:
				if (hasMeta && metadataMentions(root, 'fps plus', entries)) {
					score += 85;
					evidence.push('FPS Plus meta.json/api marker');
				} else if (hasMeta) {
					score += 15;
					evidence.push('Generic meta.json marker (FPS Plus requires an explicit API/name match)');
				}
				if (directData && directSongs && directImages) {
					score += 15;
					evidence.push('FPS Plus direct data/songs/images layout');
				}

			case ImportEngine.CODENAME:
				if (hasCodenameSongs(layout.audio)) {
					score += 60;
					evidence.push('Codename song folder: songs/<song>/meta.json + charts/');
				}
				// A meta.json beside a Codename chart folder is a strong marker
				// on its own, but the parsed shape (difficulties + bpm +
				// stepsPerBeat) is what separates Codename from FPS Plus, which
				// also drops a meta.json at the root.
				if (hasCodenameMetaShape(root, layout.audio)) {
					score += 30;
					evidence.push('Codename meta.json shape: difficulties + bpm + stepsPerBeat');
				}
				if (hasCodenameDefinitionXmls(layout.data)) {
					score += 25;
					evidence.push('Codename XML definitions: data/characters + data/stages');
				}
				if (hasFile(entries, 'modpack.ini') || hasCodenameModpackIni(layout.data)) {
					score += 15;
					evidence.push('Codename modpack.ini marker');
				}
				// Compiled Codename releases ship engine bytecode plus a
				// mods/<name> content tree that still carries complete song
				// folders.  Classify the release as Codename so the importer can
				// recover the mods content and name the source-download
				// expectation in its diagnostics.
				if (hasCodenameModsContentWithEntries(root, entries)) {
					score += 85;
					evidence.push('Codename compiled release layout: mods/<name> with song meta.json');
				}

			case ImportEngine.LEGACY_POLYMOD:
				if (hasPolymod) {
					score += 65;
					evidence.push('Legacy FNF/Polymod marker: _polymod_meta.json');
				}
				if (hasManifest) {
					score += 45;
					evidence.push('Legacy FNF asset manifest');
				}
				if (hasAssets && layout.data != '' && layout.audio != '') {
					score += 25;
					evidence.push('Legacy FNF assets/data + song audio layout');
				}
		}
		return {score:score, evidence:evidence};
	}

	static function hasImportShape(root:String, layout:Dynamic, entries:Array<String>):Bool {
		var marker = hasFile(entries, '_polymod_meta.json') || hasFile(entries, 'pack.json')
			|| hasFile(entries, 'meta.json') || hasDirectory(entries, 'manifest');
		var contentCount = 0;
		if (layout.data != '') contentCount++;
		if (layout.audio != '') contentCount++;
		if (layout.images != '') contentCount++;
		// Chart-free Psych global packs can consist only of pack.json and
		// scripts/. Treat the script tree as importable content so Auto can route
		// those packs through their owner-scoped importer.
		if (layout.scripts != '') contentCount++;
		if (layout.shared != '') contentCount++;
		return contentCount >= 2 || (marker && contentCount >= 1);
	}

	/** A Haxe project manifest at the root: Project.xml (any authored case) or
	 * a top-level .hxml build file. */
	static function hasHaxeProjectManifest(entries:Array<String>):Bool {
		return hasFile(entries, 'project.xml') || hasEntryWithExtension(entries, '.hxml');
	}

	/** A source/ (or src/) directory that really contains Haxe modules. */
	static function hasHaxeSourceDirectory(root:String, entries:Array<String>):Bool {
		var sourceDir = findDirectory(entries, root, 'source');
		if (sourceDir == '')
			sourceDir = findDirectory(entries, root, 'src');
		return sourceDir != '' && hasHaxeSourceFile(sourceDir);
	}

	static function hasHaxeSourceFile(directory:String):Bool {
		try {
			for (entry in ImportDirectoryListing.normalize(FileSystem.readDirectory(directory)))
				if (StringTools.endsWith(entry.toLowerCase(), '.hx'))
					return true;
		} catch (_:Dynamic) {}
		return false;
	}

	/** A full Psych source checkout has a Project.xml and its distinctive
	 * source/psychlua module tree. Kade-family Project.xml files are handled by
	 * their separate source marker, so generic Haxe projects remain ambiguous. */
	static function hasPsychSourceProject(root:String, entries:Array<String>):Bool {
		if (!hasHaxeProjectManifest(entries))
			return false;
		var source = findDirectory(entries, root, 'source');
		if (source == '')
			return false;
		var sourceEntries = readDirectory(source);
		var psychLua = findDirectory(sourceEntries, source, 'psychlua');
		return psychLua != '' && hasHaxeSourceFile(psychLua);
	}

	/** A standalone NMV content pack is still a package root, but its engine
	 * family comes from the executable/source project two levels above it:
	 * <game>/content/<pack>. This reads only the known parent marker, never the
	 * content name or chart names. */
	static function nightmareVisionContentOwner(root:String,
		executableMarkerCache:Map<String, Array<String>>):String {
		var contentRoot = Path.directory(Path.normalize(root));
		if (contentRoot == null || contentRoot == ''
			|| Path.withoutDirectory(contentRoot).toLowerCase() != 'content')
			return '';
		var ownerRoot = Path.directory(contentRoot);
		if (ownerRoot == null || ownerRoot == '' || ownerRoot == contentRoot)
			return '';
		if (retainedSourceEngine(ownerRoot) == ImportEngine.NIGHTMARE_VISION)
			return ownerRoot;
		var ownerEntries = readDirectory(ownerRoot);
		if (hasNightmareVisionSourceProject(ownerRoot, ownerEntries))
			return ownerRoot;
		var markers = probeExecutableMarkers(ownerRoot, ownerEntries, executableMarkerCache);
		return hasMarker(markers, 'com.nmvteam.nightmareengine') ? ownerRoot : '';
	}

	static function retainedSourceEngine(root:String):String {
		#if target.threaded
		var engines = retainedEngines.value;
		#else
		var engines = retainedEngines;
		#end
		if (engines == null) return '';
		var normalized = canonicalize(root);
		for (path in engines.keys()) {
			var known = canonicalize(path);
			#if windows
			if (known.toLowerCase() != normalized.toLowerCase()) continue;
			#else
			if (known != normalized) continue;
			#end
			var engine = ImportEngine.normalize(engines.get(path));
			return engine == ImportEngine.AUTO ? '' : engine;
		}
		return '';
	}

	/** True only for a direct content/<pack> child; nested engine roots outside
	 * this authored NMV container remain independent scan results. */
	static function isNightmareVisionContentPackage(ownerRoot:String, candidateRoot:String):Bool {
		if (ownerRoot == null || candidateRoot == null)
			return false;
		var contentRoot = Path.join([ownerRoot, 'content']);
		return identityKey(Path.directory(Path.normalize(candidateRoot))) == identityKey(contentRoot);
	}

	/** Recognize only the known package layout and inspect at most the configured
	 * number of immediate song directories. No chart names or chart bytes are
	 * needed to associate a package with its already-identified NMV parent. */
	static function hasNightmareVisionNestedSongLayout(root:String, rootEntries:Array<String>):Bool {
		var songs = findDirectory(rootEntries, root, 'songs');
		if (songs == '')
			return false;
		var checked = 0;
		for (entry in readDirectory(songs)) {
			if (checked++ >= MAX_NIGHTMARE_VISION_SONG_DIRECTORIES)
				break;
			var song = Path.join([songs, entry]);
			try {
				if (!FileSystem.isDirectory(song))
					continue;
			} catch (_:Dynamic) continue;
			if (findDirectory(readDirectory(song), song, 'data') != '')
				return true;
		}
		return false;
	}

	/** Nightmare Vision has its own published package id even though its source
	 * and mod APIs descend from Psych. Read only the root project manifest and
	 * require the package attribute on an app element so mentions in comments or
	 * README text cannot classify another Haxe project. */
	static function hasNightmareVisionSourceProject(root:String, entries:Array<String>):Bool {
		var projectPath = findFile(entries, root, 'Project.xml');
		if (projectPath == '')
			return false;
		try {
			if (FileSystem.stat(projectPath).size > MAX_PROJECT_MARKER_BYTES)
				return false;
			var document = Xml.parse(File.getContent(projectPath));
			for (project in document.elements()) {
				if (project.nodeName.toLowerCase() != 'project')
					continue;
				for (element in project.elements()) {
					if (element.nodeName.toLowerCase() != 'app')
						continue;
					for (attribute in ['packageName', 'package']) {
						var value = element.get(attribute);
						if (value != null && value.toLowerCase() == 'com.nmvteam.nightmareengine')
							return true;
					}
				}
			}
		} catch (_:Dynamic) {}
		return false;
	}

	/** NMV charts use a `format: nmv2` marker either on the document or in its
	 * song object. Probe a bounded number of small charts across the common
	 * Psych/NMV data layouts; this is engine metadata detection, not a mod-name
	 * heuristic. */
	static function hasNightmareVisionChartFormat(dataPath:String):Bool {
		if (dataPath == null || dataPath == '' || !FileSystem.isDirectory(dataPath))
			return false;
		var chartRoots:Array<String> = [dataPath];
		for (name in ['songData', 'songs']) {
			var candidate = findDirectory(readDirectory(dataPath), dataPath, name);
			if (candidate != '')
				chartRoots.push(candidate);
		}
		var checkedDirectories = 0;
		var checkedCharts = 0;
		for (chartRoot in chartRoots) {
			for (entry in readDirectory(chartRoot)) {
				if (checkedDirectories >= MAX_NIGHTMARE_VISION_SONG_DIRECTORIES)
					return false;
				var songPath = Path.join([chartRoot, entry]);
				if (chartRoot == dataPath && (entry.toLowerCase() == 'songdata'
					|| entry.toLowerCase() == 'songs'))
					continue;
				try {
					if (!FileSystem.isDirectory(songPath))
						continue;
				} catch (_:Dynamic) continue;
				checkedDirectories++;
				var chartFolders = [songPath, Path.join([songPath, 'charts'])];
				for (chartFolder in chartFolders) {
					if (!FileSystem.isDirectory(chartFolder))
						continue;
					for (fileName in readDirectory(chartFolder)) {
						var lower = fileName.toLowerCase();
						if ((!lower.endsWith('.json') && !lower.endsWith('.jsonc'))
							|| checkedCharts >= MAX_NIGHTMARE_VISION_CHART_PROBES)
							continue;
						checkedCharts++;
						var chartPath = Path.join([chartFolder, fileName]);
						try {
							if (FileSystem.isDirectory(chartPath)
								|| FileSystem.stat(chartPath).size > MAX_ENGINE_CHART_BYTES)
								continue;
							var chart:Dynamic = haxe.Json.parse(File.getContent(chartPath));
							if (hasNightmareVisionFormatField(chart)
								|| hasNightmareVisionFormatField(Reflect.field(chart, 'song')))
								return true;
						} catch (_:Dynamic) {}
					}
				}
			}
		}
		return false;
	}

	/** Content packages keep charts one level deeper than ordinary assets roots:
	 * songs/<song>/data/<difficulty>.json. Probe only that structural layout,
	 * with the same song/chart/byte bounds as the conventional NMV marker check.
	 * The NMV format field is engine metadata; package and chart names are ignored. */
	static function hasNightmareVisionNestedSongChartFormat(root:String, rootEntries:Array<String>):Bool {
		if (root == null || root == '' || !FileSystem.isDirectory(root))
			return false;
		var songsRoot = findDirectory(rootEntries, root, 'songs');
		if (songsRoot == '')
			return false;
		var checkedDirectories = 0;
		var checkedCharts = 0;
		for (entry in readDirectory(songsRoot)) {
			if (checkedDirectories >= MAX_NIGHTMARE_VISION_SONG_DIRECTORIES)
				break;
			var songPath = Path.join([songsRoot, entry]);
			try {
				if (!FileSystem.isDirectory(songPath))
					continue;
			} catch (_:Dynamic) continue;
			checkedDirectories++;
			var dataPath = findDirectory(readDirectory(songPath), songPath, 'data');
			if (dataPath == '')
				continue;
			for (fileName in readDirectory(dataPath)) {
				var lower = fileName.toLowerCase();
				if (!lower.endsWith('.json') && !lower.endsWith('.jsonc'))
					continue;
				if (checkedCharts >= MAX_NIGHTMARE_VISION_CHART_PROBES)
					return false;
				checkedCharts++;
				var chartPath = Path.join([dataPath, fileName]);
				try {
					if (FileSystem.isDirectory(chartPath)
						|| FileSystem.stat(chartPath).size > MAX_ENGINE_CHART_BYTES)
						continue;
					var chart:Dynamic = haxe.Json.parse(File.getContent(chartPath));
					if (hasNightmareVisionFormatField(chart)
						|| hasNightmareVisionFormatField(Reflect.field(chart, 'song')))
						return true;
				} catch (_:Dynamic) {}
			}
		}
		return false;
	}

	static function hasNightmareVisionFormatField(value:Dynamic):Bool {
		if (value == null)
			return false;
		var format:Dynamic = Reflect.field(value, 'format');
		return format != null && Std.isOfType(format, String)
			&& StringTools.trim(cast format).toLowerCase() == 'nmv2';
	}

	/** The older Psych-family packaging used by some chart libraries stores
	 * standard Psych chart envelopes below data/songData/<song>. */
	static function hasPsychSongDataCharts(dataPath:String):Bool {
		if (dataPath == null || dataPath == '' || !FileSystem.isDirectory(dataPath))
			return false;
		var songData = findDirectory(readDirectory(dataPath), dataPath, 'songData');
		if (songData == '')
			return false;
		var checkedDirectories = 0;
		var checkedCharts = 0;
		for (entry in readDirectory(songData)) {
			if (checkedDirectories >= MAX_NIGHTMARE_VISION_SONG_DIRECTORIES)
				break;
			var songPath = Path.join([songData, entry]);
			try {
				if (!FileSystem.isDirectory(songPath))
					continue;
			} catch (_:Dynamic) continue;
			checkedDirectories++;
			for (fileName in readDirectory(songPath)) {
				var lower = fileName.toLowerCase();
				if ((!lower.endsWith('.json') && !lower.endsWith('.jsonc'))
					|| checkedCharts >= MAX_NIGHTMARE_VISION_CHART_PROBES)
					continue;
				checkedCharts++;
				var chartPath = Path.join([songPath, fileName]);
				try {
					if (FileSystem.isDirectory(chartPath)
						|| FileSystem.stat(chartPath).size > MAX_ENGINE_CHART_BYTES)
						continue;
					var chart:Dynamic = haxe.Json.parse(File.getContent(chartPath));
					var song:Dynamic = Reflect.field(chart, 'song');
					if (song != null && Std.isOfType(Reflect.field(song, 'notes'), Array)
						&& Reflect.field(song, 'bpm') != null)
						return true;
				} catch (_:Dynamic) {}
			}
		}
		return false;
	}

	/**
		Diagnostic text for a directory that carries a Haxe project manifest but
		cannot be imported because the download is incomplete.  Returns '' when
		nothing is wrong or the directory is not a Haxe project at all.  The
		scanner never classifies such a root; this only explains why.
	*/
	static function incompleteSourceReleaseMessage(root:String, entries:Array<String>):String {
		if (!hasHaxeProjectManifest(entries))
			return '';
		var missing:Array<String> = [];
		var sourceEntries = readDirectory(root);
		var sourceDir = findDirectory(sourceEntries, root, 'source');
		if (sourceDir == '')
			sourceDir = findDirectory(sourceEntries, root, 'src');
		if (sourceDir == '' || !hasHaxeSourceFile(sourceDir))
			missing.push('source/');
		var layout = resolveLayout(root);
		if (layout.data == '')
			missing.push('assets/data');
		if (missing.length == 0)
			return '';
		var name = Path.withoutDirectory(root);
		return '[source-release-incomplete] ' + name + ': Haxe source project detected but '
			+ missing.join(' or ') + ' is missing \u2014 re-download the complete source release.';
	}

	static function resolveLayout(root:String, ?knownRootEntries:Array<String>):Dynamic {
		var contentRoot = root;
		var supplementalAssetRoots:Array<ImportRootAssetSource> = [];
		var rootEntries = knownRootEntries == null ? readDirectory(root) : knownRootEntries;
		var assetsPath = findDirectory(rootEntries, root, 'assets');
		if (assetsPath != '')
			contentRoot = assetsPath;
		var entries = readDirectory(contentRoot);
		// Full source projects may map the playable base game from
		// assets/base_game -> assets. Select that authored logical asset root
		// when it contains the usual shared/data + songs pairing, while retaining
		// the project directory as ImportRoot.root for exact owner provenance.
		var baseGame = findDirectory(entries, contentRoot, 'base_game');
		if (baseGame != '') {
			var baseGameEntries = readDirectory(baseGame);
			var baseGameShared = findDirectory(baseGameEntries, baseGame, 'shared');
			var baseGameSongs = findDirectory(baseGameEntries, baseGame, 'songs');
			var baseGameData = findDirectory(baseGameEntries, baseGame, 'data');
			if (baseGameData == '' && baseGameShared != '')
				baseGameData = findDirectory(readDirectory(baseGameShared), baseGameShared, 'data');
			if (baseGameShared != '' && baseGameSongs != '' && baseGameData != '') {
				// Psych source Project.xml also maps assets/shared into the logical
				// asset tree separately from base_game. Keep it as a second source so
				// importers can merge it after the base-game files without replacing
				// their bytes or changing owner provenance.
				var projectShared = findDirectory(entries, contentRoot, 'shared');
				if (projectShared != '' && projectShared != baseGameShared)
					supplementalAssetRoots.push({path:projectShared, destinationPrefix:'shared'});
				contentRoot = baseGame;
				entries = baseGameEntries;
			}
		}
		var data = findDirectory(entries, contentRoot, 'data');
		var audio = findDirectory(entries, contentRoot, 'songs');
		if (audio == '') audio = findDirectory(entries, contentRoot, 'music');
		var images = findDirectory(entries, contentRoot, 'images');
		var shared = findDirectory(entries, contentRoot, 'shared');
		var scripts = findDirectory(entries, contentRoot, 'scripts');
		// Some packaged Psych/older FNF builds keep the common tree under
		// assets/shared while songs remain under assets/songs.  Expose the
		// actual chart and visual roots so the importer does not discard them.
		if (shared != '') {
			var sharedEntries = readDirectory(shared);
			if (data == '') data = findDirectory(sharedEntries, shared, 'data');
			if (images == '') images = findDirectory(sharedEntries, shared, 'images');
			if (scripts == '') scripts = findDirectory(sharedEntries, shared, 'scripts');
		}
		// Kade-family Haxe projects map their common tree from the Project.xml
		// `preload` library, so charts live below assets/preload/data while the
		// audio stays at assets/songs.  Only consult it when the ordinary and
		// shared lookups missed, so existing layouts keep their exact roots.
		var preloadPath = findDirectory(entries, contentRoot, 'preload');
		if (preloadPath != '') {
			var preloadEntries = readDirectory(preloadPath);
			if (data == '') data = findDirectory(preloadEntries, preloadPath, 'data');
			if (audio == '') audio = findDirectory(preloadEntries, preloadPath, 'songs');
			if (images == '') images = findDirectory(preloadEntries, preloadPath, 'images');
			if (scripts == '') scripts = findDirectory(preloadEntries, preloadPath, 'scripts');
		}
		return {
			contentRoot:contentRoot,
			data:data,
			audio:audio,
			images:images,
			shared:shared,
			scripts:scripts,
			supplementalAssetRoots:supplementalAssetRoots
		};
	}

	static function hasVSlicelikeCharts(dataPath:String):Bool {
		if (dataPath == null || dataPath == '' || !FileSystem.isDirectory(Path.join([dataPath, 'songs'])))
			return false;
		var songsPath = Path.join([dataPath, 'songs']);
		var dirs = readDirectory(songsPath);
		var checked = 0;
		for (entry in dirs) {
			if (checked++ >= MAX_VSLICE_SONG_DIRECTORIES)
				break;
			var songPath = Path.join([songsPath, entry]);
			try {
				if (!FileSystem.isDirectory(songPath)) continue;
			} catch (_:Dynamic) continue;
			var files = readDirectory(songPath);
			var hasMetadata = false;
			var hasChart = false;
			var seen = 0;
			for (file in files) {
				if (seen++ >= MAX_VSLICE_SONG_FILES) break;
				var lower = file.toLowerCase();
				if (lower.indexOf('-metadata.json') >= 0) hasMetadata = true;
				if (lower.indexOf('-chart.json') >= 0) hasChart = true;
			}
			if (hasMetadata && hasChart) return true;
		}
		return false;
	}

	/** True when at least one songs/<song> folder carries the Codename
		meta.json + charts/ pair.  Probing stays bounded like the V-Slice walk. */
	public static function hasCodenameSongs(songsPath:String):Bool {
		if (songsPath == null || songsPath == '')
			return false;
		var checked = 0;
		for (entry in readDirectory(songsPath)) {
			if (checked++ >= MAX_CODENAME_SONG_DIRECTORIES)
				break;
			var songPath = Path.join([songsPath, entry]);
			try {
				if (!FileSystem.isDirectory(songPath))
					continue;
			} catch (_:Dynamic) continue;
			if (isCodenameSongFolder(songPath))
				return true;
		}
		return false;
	}

	/** True when one song folder has meta.json + charts/ (layout only). */
	public static function isCodenameSongFolder(songPath:String):Bool {
		try {
			if (!FileSystem.isDirectory(songPath))
				return false;
			if (findFile(readDirectory(songPath), songPath, 'meta.json') == '')
				return false;
			var charts = findDirectory(readDirectory(songPath), songPath, 'charts');
			return charts != '' && readDirectory(charts).length > 0;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Parsed-shape confirmation: the first song meta.json must look like a
		Codename document (difficulties + bpm + stepsPerBeat).  Kept inline like
		every other scanner probe so the detector stays dependency-free. */
	public static function hasCodenameMetaShape(root:String, songsPath:String):Bool {
		if (songsPath == null || songsPath == '')
			return false;
		var checked = 0;
		for (entry in readDirectory(songsPath)) {
			if (checked++ >= MAX_CODENAME_SONG_DIRECTORIES)
				break;
			var songPath = Path.join([songsPath, entry]);
			try {
				if (!FileSystem.isDirectory(songPath))
					continue;
			} catch (_:Dynamic) continue;
			var metaPath = findFile(readDirectory(songPath), songPath, 'meta.json');
			if (metaPath == '')
				continue;
			try {
				var meta:Dynamic = haxe.Json.parse(File.getContent(metaPath));
				if (meta == null || !Std.isOfType(Reflect.field(meta, 'difficulties'), Array))
					return false;
				var bpm = Std.parseFloat(Std.string(Reflect.field(meta, 'bpm')));
				var steps = Std.parseFloat(Std.string(Reflect.field(meta, 'stepsPerBeat')));
				return !Math.isNaN(bpm) && bpm > 0 && !Math.isNaN(steps) && steps > 0;
			} catch (_:Dynamic) {
				return false;
			}
		}
		return false;
	}

	/** Codename keeps character/stage definitions as XML under data/. */
	static function hasCodenameDefinitionXmls(dataPath:String):Bool {
		if (dataPath == null || dataPath == '')
			return false;
		for (relative in ['characters', 'stages']) {
			var folder = Path.join([dataPath, relative]);
			if (!FileSystem.isDirectory(folder))
				continue;
			for (entry in readDirectory(folder)) {
				if (!StringTools.endsWith(entry.toLowerCase(), '.xml'))
					continue;
				var path = Path.join([folder, entry]);
				try {
					if (FileSystem.stat(path).size > 256 * 1024)
						continue;
					var content = File.getContent(path);
					if (content.indexOf('codename-engine-' + (relative == 'characters' ? 'character' : 'stage')) >= 0)
						return true;
				} catch (_:Dynamic) continue;
			}
		}
		return false;
	}

	static function hasCodenameModpackIni(dataPath:String):Bool {
		if (dataPath == null || dataPath == '')
			return false;
		return hasFile(readDirectory(dataPath), 'modpack.ini')
			|| hasFile(readDirectory(Path.join([dataPath, 'config'])), 'modpack.ini');
	}

	/** True when mods/<name> carries a complete Codename content tree.  The
		compiled release root has no importable songs itself; its mods folders
		are the recovery source. */
	public static function hasCodenameModsContent(rootPath:String):Bool {
		return hasCodenameModsContentWithEntries(rootPath, readDirectory(rootPath));
	}

	static function hasCodenameModsContentWithEntries(rootPath:String, rootEntries:Array<String>):Bool {
		var modsPath = findDirectory(rootEntries, rootPath, 'mods');
		if (modsPath == '')
			return false;
		var checked = 0;
		for (entry in readDirectory(modsPath)) {
			if (checked++ >= MAX_CODENAME_MOD_DIRECTORIES)
				break;
			var modPath = Path.join([modsPath, entry]);
			try {
				if (!FileSystem.isDirectory(modPath))
					continue;
			} catch (_:Dynamic) continue;
			var songsPath = findDirectory(readDirectory(modPath), modPath, 'songs');
			if (songsPath != '' && hasCodenameSongs(songsPath))
				return true;
		}
		return false;
	}

	/** Compiled-release layout: a mods/ tree with complete Codename content.
		Source mods never carry one, so this alone marks the release kind. */
	public static function isCompiledCodenameRelease(rootPath:String):Bool {
		return hasCodenameModsContent(rootPath);
	}

	/** Codename mods/<name> folders below a compiled release which carry a
		complete content tree.  Order is deterministic case-folded. */
	public static function codenameModsFolders(rootPath:String):Array<String> {
		var result:Array<String> = [];
		var modsPath = findDirectory(readDirectory(rootPath), rootPath, 'mods');
		if (modsPath == '')
			return result;
		var checked = 0;
		for (entry in readDirectory(modsPath)) {
			if (checked++ >= MAX_CODENAME_MOD_DIRECTORIES)
				break;
			var modPath = Path.join([modsPath, entry]);
			try {
				if (!FileSystem.isDirectory(modPath))
					continue;
			} catch (_:Dynamic) continue;
			var songsPath = findDirectory(readDirectory(modPath), modPath, 'songs');
			if (songsPath != '' && hasCodenameSongs(songsPath))
				result.push(modPath);
		}
		return result;
	}

	static function hasCustomRegistry(imagesPath:String):Bool {
		if (imagesPath == null || imagesPath == '') return false;
		var entries = readDirectory(imagesPath);
		return hasDirectory(entries, 'custom_chars') || hasDirectory(entries, 'custom_stages')
			|| hasDirectory(entries, 'custom_ui') || hasDirectory(entries, 'custom_difficulties');
	}

	static function metadataMentions(root:String, text:String, entries:Array<String>):Bool {
		var path = findFile(entries, root, 'meta.json');
		if (path == '') return false;
		try {
			var content = File.getContent(path);
			return content.toLowerCase().indexOf(text.toLowerCase()) >= 0;
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function hasLuaFile(entries:Array<String>, dataPath:String):Bool {
		for (entry in entries)
			if (StringTools.endsWith(entry.toLowerCase(), '.lua')) return true;
		if (dataPath == null || dataPath == '') return false;
		// A chart folder may carry its modchart Lua below data; inspect only
		// immediate song folders and never recurse through the media trees.
		var checked = 0;
		for (entry in readDirectory(dataPath)) {
			if (checked++ >= MAX_LUA_SONG_DIRECTORIES)
				break;
			var child = Path.join([dataPath, entry]);
			try {
				if (!FileSystem.isDirectory(child)) continue;
			} catch (_:Dynamic) continue;
			if (directoryHasLuaFile(child)) return true;
			if (entry.toLowerCase() == 'songdata') {
				var nestedChecked = 0;
				for (songEntry in readDirectory(child)) {
					if (nestedChecked++ >= MAX_NESTED_LUA_SONG_DIRECTORIES)
						break;
					var songDirectory = Path.join([child, songEntry]);
					try {
						if (!FileSystem.isDirectory(songDirectory)) continue;
					} catch (_:Dynamic) continue;
					if (directoryHasLuaFile(songDirectory)) return true;
				}
			}
		}
		return false;
	}

	/** Thin addons omit pack/images/actor trees. Require independent source
	 * contracts for a week-listed song; a Lua filename alone stays ambiguous. */
	static function hasThinPsychPackage(root:String, dataPath:String):Bool {
		if (dataPath == null || dataPath == '') return false;
		var weeks = findDirectory(readDirectory(root), root, 'weeks');
		if (weeks == '') return false;
		var weekSongs:Map<String, Bool> = new Map();
		var checkedWeeks = 0;
		for (file in readDirectory(weeks)) {
			if (checkedWeeks++ >= 32) break;
			if (!file.toLowerCase().endsWith('.json')) continue;
			var path = Path.join([weeks, file]);
			try {
				if (FileSystem.isDirectory(path) || FileSystem.stat(path).size > MAX_PROJECT_MARKER_BYTES) continue;
				var week:Dynamic = haxe.Json.parse(File.getContent(path));
				var characters:Dynamic = Reflect.field(week, 'weekCharacters');
				var songs:Dynamic = Reflect.field(week, 'songs');
				if (!Std.isOfType(characters, Array) || (cast characters:Array<Dynamic>).length != 3
					|| !Std.isOfType(songs, Array)) continue;
				for (row in (cast songs:Array<Dynamic>)) {
					if (!Std.isOfType(row, Array)) continue;
					var values:Array<Dynamic> = cast row;
					if (values.length < 2 || !Std.isOfType(values[0], String) || !Std.isOfType(values[1], String)) continue;
					var name = PsychSongNameCompat.format(Std.string(values[0]));
					if (name != '' && name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf('..') < 0)
						weekSongs.set(name, true);
				}
			} catch (_:Dynamic) {}
		}
		if (!weekSongs.iterator().hasNext()) return false;
		var checkedFolders = 0;
		var checkedFiles = 0;
		for (folder in readDirectory(dataPath)) {
			if (checkedFolders++ >= MAX_LUA_SONG_DIRECTORIES) break;
			if (!weekSongs.exists(PsychSongNameCompat.format(folder))) continue;
			var directory = Path.join([dataPath, folder]);
			try if (!FileSystem.isDirectory(directory)) continue catch (_:Dynamic) continue;
			var hasChart = false;
			var hasCallback = false;
			for (file in readDirectory(directory)) {
				if (checkedFiles++ >= MAX_NIGHTMARE_VISION_CHART_PROBES) break;
				var path = Path.join([directory, file]);
				try {
					if (FileSystem.isDirectory(path)) continue;
					var lower = file.toLowerCase();
					if (lower.endsWith('.lua') && FileSystem.stat(path).size <= MAX_PROJECT_MARKER_BYTES) {
						var contents = File.getContent(path);
						contents = ~/--\[\[[\s\S]*?\]\]/g.replace(contents, '');
						if (~/^[ \t]*(?:local[ \t]+)?function[ \t]+on(?:Create|CreatePost|StartCountdown|SongStart|Update|UpdatePost|Event)[ \t]*\(/m.match(contents))
							hasCallback = true;
					} else if ((lower.endsWith('.json') || lower.endsWith('.jsonc'))
						&& FileSystem.stat(path).size <= MAX_ENGINE_CHART_BYTES) {
						var chart:Dynamic = haxe.Json.parse(File.getContent(path));
						var song:Dynamic = Reflect.field(chart, 'song');
						var sections:Dynamic = song == null ? null : Reflect.field(song, 'notes');
						var bpm = song == null ? Math.NaN : Std.parseFloat(Std.string(Reflect.field(song, 'bpm')));
						if (Std.isOfType(sections, Array) && !Math.isNaN(bpm) && bpm > 0)
							for (section in (cast sections:Array<Dynamic>))
								if (section != null && Std.isOfType(Reflect.field(section, 'sectionNotes'), Array)) {
									hasChart = true; break;
								}
					}
				} catch (_:Dynamic) {}
				if (hasChart && hasCallback) return true;
			}
		}
		return false;
	}

	static function directoryHasLuaFile(directory:String):Bool {
		for (file in readDirectory(directory))
			if (StringTools.endsWith(file.toLowerCase(), '.lua')) {
				var path = Path.join([directory, file]);
				try {
					if (!FileSystem.isDirectory(path)) return true;
				} catch (_:Dynamic) {}
			}
		return false;
	}

	static function hasMarker(markers:Array<String>, marker:String):Bool {
		if (markers == null || marker == null)
			return false;
		var wanted = marker.toLowerCase();
		for (found in markers)
			if (found == wanted)
				return true;
		return false;
	}

	/**
		Read only root-level executable candidates, using a reusable 64 KiB
		buffer and a 32 MiB maximum per file.  Marker matches are ASCII strings
		from the compiled engine, so a filename alone can never identify Kade,
		Psych, or Modding Plus.
	*/
	static function probeExecutableMarkers(root:String, entries:Array<String>,
		?cache:Map<String, Array<String>>):Array<String> {
		var found:Array<String> = [];
		if (cache == null)
			cache = new Map();
		var checked = 0;
		for (entry in entries) {
			if (checked >= MAX_EXECUTABLE_PROBES)
				break;
			var lower = entry.toLowerCase();
			if (!StringTools.endsWith(lower, '.exe'))
				continue;
			var path = Path.join([root, entry]);
			var size = 0;
			var modified:Float = 0;
			try {
				if (FileSystem.isDirectory(path))
					continue;
				var stat = FileSystem.stat(path);
				size = stat.size;
				modified = stat.mtime.getTime();
			} catch (_:Dynamic) {
				continue;
			}
			if (size <= 0)
				continue;
			checked++;
			var cacheKey = identityKey(path) + "|" + size + "|" + modified;
			var executableMarkers = cache.get(cacheKey);
			if (executableMarkers == null) {
				executableMarkers = probeExecutable(path);
				cache.set(cacheKey, executableMarkers.copy());
			}
			for (marker in executableMarkers) {
				if (!hasMarker(found, marker))
					found.push(marker);
			}
			// Once an executable supplies an engine marker, inspecting sibling
			// executables cannot improve Auto for this root and would add I/O.
			if (found.length > 0)
				break;
		}
		return found;
	}

	static function probeExecutable(path:String):Array<String> {
		var wanted = ['kadedev', 'kadeenginedata', 'psychlua', 'psychanimationcontroller',
			'psychengineversion',
			'com.nmvteam.nightmareengine',
			'friday night funkin\' modding plus', 'modding plus'];
		var found:Array<String> = [];
		var input:FileInput = null;
		try {
			input = File.read(path, true);
			var bytes = Bytes.alloc(EXECUTABLE_PROBE_CHUNK);
			var carry = '';
			var readTotal = 0;
			var fileSize = FileSystem.stat(path).size;
			var probeLimit:Int = fileSize < EXECUTABLE_PROBE_LIMIT ? fileSize : EXECUTABLE_PROBE_LIMIT;
			var maxMarkerLength = 0;
			for (marker in wanted)
				if (marker.length > maxMarkerLength)
					maxMarkerLength = marker.length;
			while (readTotal < probeLimit) {
				var remaining = probeLimit - readTotal;
				var request:Int = remaining < EXECUTABLE_PROBE_CHUNK ? remaining : EXECUTABLE_PROBE_CHUNK;
				var count = input.readBytes(bytes, 0, request);
				if (count <= 0)
					break;
				readTotal += count;
				var printable = new StringBuf();
				for (index in 0...count) {
					var code = bytes.get(index);
					printable.addChar(code >= 32 && code <= 126 ? code : 10);
				}
				var haystack = (carry + printable.toString()).toLowerCase();
				for (marker in wanted)
					if (haystack.indexOf(marker) >= 0 && !hasMarker(found, marker))
						found.push(marker);
				if (found.length == wanted.length)
					break;
				var keep:Int = maxMarkerLength > 0 ? maxMarkerLength - 1 : 0;
				carry = haystack.length > keep ? haystack.substr(haystack.length - keep) : haystack;
			}
		} catch (_:Dynamic) {
			// A locked/non-native executable is simply an unrecognised root.
		}
		if (input != null) {
			try {
				input.close();
			} catch (_:Dynamic) {}
		}
		return found;
	}

	static function readDirectory(path:String):Array<String> {
		try {
			if (path == null || path == '' || !FileSystem.exists(path) || !FileSystem.isDirectory(path))
				return [];
			return sortDirectoryEntries(ImportDirectoryListing.normalize(FileSystem.readDirectory(path)));
		} catch (_:Dynamic) {
			return [];
		}
	}

	/** Some native filesystem implementations return null for a missing or
		inaccessible directory instead of throwing. Normalize that result before
		calling Array.sort, whose hxcpp implementation dereferences its receiver. */
	static function sortDirectoryEntries(entries:Array<String>):Array<String> {
		entries = ImportDirectoryListing.normalize(entries);
		entries.sort(function(a:String, b:String):Int {
			var aLower = a.toLowerCase();
			var bLower = b.toLowerCase();
			if (aLower < bLower) return -1;
			if (aLower > bLower) return 1;
			// Case-sensitive filesystems can contain both `Pack` and `pack`.
			// Keep discovery deterministic instead of inheriting directory
			// enumeration order for equal case-folded names.
			return a < b ? -1 : (a > b ? 1 : 0);
		});
		return entries;
	}

	static function findDirectory(entries:Array<String>, root:String, name:String):String {
		for (entry in entries)
			if (entry.toLowerCase() == name.toLowerCase()) {
				var path = Path.join([root, entry]);
				try {
					if (FileSystem.isDirectory(path)) return path;
				} catch (_:Dynamic) {}
			}
		return '';
	}

	static function findFile(entries:Array<String>, root:String, name:String):String {
		for (entry in entries)
			if (entry.toLowerCase() == name.toLowerCase()) {
				var path = Path.join([root, entry]);
				try {
					if (!FileSystem.isDirectory(path)) return path;
				} catch (_:Dynamic) {}
			}
		return '';
	}

	static function hasDirectory(entries:Array<String>, name:String):Bool {
		for (entry in entries) if (entry.toLowerCase() == name.toLowerCase()) return true;
		return false;
	}

	static function hasFile(entries:Array<String>, name:String):Bool {
		return hasDirectory(entries, name);
	}

	static function hasEntryContaining(entries:Array<String>, text:String):Bool {
		for (entry in entries) if (entry.indexOf(text) >= 0) return true;
		return false;
	}

	static function hasEntryWithExtension(entries:Array<String>, ext:String):Bool {
		for (entry in entries) if (StringTools.endsWith(entry, ext)) return true;
		return false;
	}

	static function hasKadeMarker(entries:Array<String>):Bool {
		for (entry in entries) {
			if (!StringTools.endsWith(entry, '.exe'))
				continue;
			var name = entry.substr(0, entry.length - 4);
			// Avoid substring matches such as FUNKADELIX.exe.  Kade builds
			// conventionally retain the engine name in the executable title.
			if (name == 'kade' || name == 'kade engine' || name.indexOf('kade engine ') == 0
				|| name.indexOf('kade_') == 0 || name.indexOf('kade-') == 0)
				return true;
		}
		return false;
	}
	#end

	#if sys
	static function shouldSkipDirectory(name:String):Bool {
		return name == '.git' || name == '.svn' || name == '.hg' || name == '.tools'
			|| name == '.haxelib' || name == 'node_modules' || name == 'export' || name == 'build'
			|| name == 'dist' || name == 'bin' || name == 'cache' || name == 'plugins'
			|| name == 'images' || name == 'songs' || name == 'music' || name == 'sounds'
			|| name == 'data' || name == 'shared'
			|| name == 'videos' || name == 'fonts' || name == 'shaders' || name == 'replays';
	}

	static function canonicalIdentity(path:String):String {
		var value = canonicalize(path);
		if (value == '') return '';
		try {
			var stat = FileSystem.stat(value);
			if (stat.dev != 0 || stat.ino != 0)
				return value + '#dev' + stat.dev + ':ino' + stat.ino;
		} catch (_:Dynamic) {}
		return value;
	}

	static function identityKey(path:String):String {
		var value = canonicalIdentity(path);
		#if windows
		return value.toLowerCase();
		#else
		return value;
		#end
	}

	static function cancelled(callbacks:ImportRootScanCallbacks):Bool {
		if (callbacks == null || callbacks.isCancelled == null) return false;
		try {
			return callbacks.isCancelled();
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function report(callbacks:ImportRootScanCallbacks, phase:String, current:String, completed:Int, total:Int):Void {
		if (callbacks == null || callbacks.onProgress == null) return;
		try {
			callbacks.onProgress({phase:phase, current:current, completed:completed, total:total});
		} catch (_:Dynamic) {}
	}
	#end
}
