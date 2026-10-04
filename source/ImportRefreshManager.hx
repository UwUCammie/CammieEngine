package;

#if sys
import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import sys.thread.Mutex;
import sys.thread.Thread;
import ImportWorkflow.ImportScanResult;
import ModuleFunctions.SongImportBatchResult;
import ImportRefreshTransaction.ImportRefreshStagedOutput;
import ImportRefreshTransaction.ImportRefreshManifestFile;

typedef ImportRefreshBrowseStatus = {
	var busy:Bool;
	var label:String;
	var fraction:Float;
	var complete:Bool;
	var changed:Bool;
	var blocked:Bool;
	@:optional var phase:String;
	@:optional var current:String;
	@:optional var completed:Int;
	@:optional var total:Int;
	@:optional var elapsedSeconds:Float;
	@:optional var activityAgeSeconds:Float;
	@:optional var phaseElapsedSeconds:Float;
	@:optional var etaSeconds:Float;
	@:optional var queueRemaining:Int;
}

/** Retained source -> private conversion -> owned, recoverable publication.
 * Only metadata is inspected on a normal launch. Source bytes are read again
 * when importer revisions change, never merely because the app version changes. */
class ImportRefreshManager {
	public static inline var CACHE_ROOT:String = "import-cache";
	static var mutex:Mutex = new Mutex();
	static var checked:Bool = false;
	static var active:Bool = false;
	static var status:ImportRefreshBrowseStatus = {
		busy:false, label:"", fraction:0, complete:false, changed:false, blocked:false
	};
	static var completedNames:Array<String> = [];
	static var handedOff:Bool = false;
	static var pendingHandoff:Bool = false;
	static var queue:Array<Dynamic> = [];
	static var measurements:ImportRefreshProgress;
	public static var generation(default,null):Int = 0;

	/** Called by the existing native import worker. Its renderer stays on the
 	 * installed tree; only that worker receives the filesystem staging context. */
	public static function importOnce(source:String, type:String, scan:ImportScanResult,
		names:Map<String,String>, convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void):SongImportBatchResult {
		mutex.acquire();
		if (active) { mutex.release(); throw "Another import refresh is already running."; }
		active = true;
		mutex.release();
		try {
			var result = captureImport(source,type,scan,names,convert,cancel,progress);
			mutex.acquire(); active = false; mutex.release();
			return result;
		} catch (error:Dynamic) {
			trace("[import-refresh-error] " + Std.string(error) + "\n" + haxe.CallStack.toString(haxe.CallStack.exceptionStack()));
			mutex.acquire(); active = false; mutex.release();
			throw error;
		}
	}

	static function captureImport(source:String, type:String, scan:ImportScanResult,
		names:Map<String,String>, convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void):SongImportBatchResult {
		var install = FileSystem.fullPath(Sys.getCwd());
		var cache = Path.join([install, CACHE_ROOT]);
		FileSystem.createDirectory(cache);
		var roots:Array<Dynamic> = [];
		var engines:Array<String> = [];
		var normalized = FileSystem.fullPath(source);
		if (scan != null && scan.detectedRoots != null) for (root in scan.detectedRoots) {
			if (root == null || ImportRevision.normalizeEngine(root.engine) == "") continue;
			var relative = relativeTo(root.root, normalized);
			if (relative == null) throw "Import root leaves selected source; select a folder containing all dependencies.";
			var namespace = CompatScriptManifest.namespaceFor(root.root, root.engine);
			roots.push({relative:relative, engine:root.engine, namespace:namespace,
				label:Path.withoutDirectory(Path.normalize(root.root)),
				name:names == null ? null : names.get(ImportPackageNamePrompt.rootKey(root.root))});
			if (engines.indexOf(root.engine) < 0) engines.push(root.engine);
		}
		if (engines.length == 0 && ImportRevision.normalizeEngine(type) != "") {
			engines.push(ImportRevision.normalizeEngine(type));
			roots.push({relative:"",engine:engines[0],namespace:CompatScriptManifest.namespaceFor(source,engines[0]),
				label:Path.withoutDirectory(Path.normalize(source)),name:null});
		}
		if (engines.length == 0) throw "No supported import owner was found in the scan.";
		var keys = [for (root in roots) Std.string(root.engine) + "/" + Std.string(root.namespace)];
		keys.sort(Reflect.compare);
		var id = Sha256.make(haxe.io.Bytes.ofString(keys.join("\n"))).toHex();
		if (!FileSystem.exists(ImportRefreshTransaction.manifestPath(Path.join([cache,"state"]),"retained-import:" + id))) {
			if (scan != null && scan.songs != null) for (song in scan.songs)
				if (Reflect.field(song,"duplicate") == true && Reflect.field(song,"sourceDuplicate") != true)
					throw "An existing song import has no retained-source ownership baseline. Its files were preserved; automatic refresh requires migration.";
			for (root in roots) if (FileSystem.exists(Path.join([install,"assets","imported_mods",Std.string(root.namespace)])))
				throw "This older import has no retained-source ownership baseline. Its files were preserved; automatic refresh requires migration.";
		}
		var snapshot = ImportSourceSnapshot.capture(normalized, Path.join([cache,"sources"]), engines[0],
			EngineBranding.version(), {cancelled:cancel, onProgress:function(p) {
				progress({phase:"retaining-source",current:p.current,completed:p.filesCompleted,total:p.filesTotal});
			}});
		if (snapshot.status == "cancelled") throw "Import cancelled before source retention completed.";
		if (!snapshot.complete) throw "Source retention incomplete: " + snapshot.error + " " + snapshot.incompleteReasons.join(", ");
		var record:Dynamic = {
			schemaVersion:1, id:id, source:Path.join(["sources",snapshot.snapshotId,"content"]),
			snapshotId:snapshot.snapshotId, type:type, engines:engines, roots:roots,
			label:Path.withoutDirectory(Path.normalize(source)), exclusions:snapshot.exclusions,
			dependencyDiagnostics:dependencyDiagnostics(scan),
			revisions:[for (engine in engines) ImportRevision.current(engine,EngineBranding.version())]
		};
		// A pointer is deliberately published before the transaction. If the
		// process exits after commit, its committed manifest remains discoverable.
		var records = Path.join([cache,"records"]);
		FileSystem.createDirectory(records);
		atomicText(Path.join([records,id + ".json"]),Json.stringify({id:id}));
		return regenerate(install,record,convert,cancel,progress);
	}

	public static function refreshNow(install:String, record:Dynamic,
		convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void):SongImportBatchResult {
		return regenerate(install,record,convert,cancel,progress);
	}

	public static function cachedRecords(install:String):Array<Dynamic> {
		var cache = Path.join([install,CACHE_ROOT]);
		var records = Path.join([cache,"records"]);
		var result:Array<Dynamic> = [];
		if (!FileSystem.exists(records)) return result;
		for (name in FileSystem.readDirectory(records)) {
			if (!~/^[a-f0-9]{64}\.json$/.match(name)) continue;
			var id = name.substr(0,64);
			var manifest = committedManifest(Path.join([cache,"state"]),"retained-import:" + id);
			if (manifest == null || manifest.owner != "retained-import:" + id || manifest.revision == null) continue;
			var record:Dynamic = manifest.revision.importRecord;
			if (record != null && record.id == id && record.schemaVersion == 1) result.push(record);
		}
		return result;
	}

	static function regenerate(install:String, record:Dynamic,
		convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void):SongImportBatchResult {
		var cache = Path.join([install,CACHE_ROOT]);
		var owner = "retained-import:" + Std.string(record.id);
		var state = Path.join([cache,"state"]);
		var previous:Dynamic = committedManifest(state,owner);
		var oldMetadata:Dynamic = previous == null ? null : Reflect.field(previous,"revision");
		var masked:Array<String> = [];
		var maskedPaths:Map<String, Bool> = new Map();
		if (previous != null) {
			var files:Array<Dynamic> = cast Reflect.field(previous,"files");
			if (files == null || Reflect.field(previous,"owner") != owner) throw "Invalid import ownership manifest.";
			for (file in files) {
				var path = Std.string(file.path);
				masked.push(path);
				maskedPaths.set(path, true);
			}
		}
		var source = contained(cache,Std.string(record.source));
		if (!FileSystem.exists(source) || !FileSystem.isDirectory(source)) throw "Retained source is missing; import the original package once again.";
		ImportSourceSnapshot.verify(Path.directory(source),Std.string(record.snapshotId),cancel,function(p) {
			progress({phase:"checking-retained-source",current:p.current,completed:p.filesCompleted,total:p.filesTotal});
		});
		var stage = Path.join([cache,"staging",Std.string(record.id) + "-" + Std.string(Date.now().getTime())]);
		FileSystem.createDirectory(stage);
		var io = ImportIO.begin(install,stage,masked,true);
		var retainedEngines:Map<String, String> = new Map();
		for (root in (cast record.roots:Array<Dynamic>))
			retainedEngines.set(Path.join([source,Std.string(root.relative)]),Std.string(root.engine));
		var previousEngines = ImportRootScanner.setRetainedSourceEngines(retainedEngines);
		var ended = false;
		try {
			var registrySeeds:Map<String,String> = new Map();
			var registryRegeneration:Map<String,Bool> = new Map();
			var names:Map<String,String> = new Map();
			for (root in (cast record.roots:Array<Dynamic>)) {
				var path = Path.join([source,Std.string(root.relative)]);
				io.setNamespace(path,Std.string(root.engine),Std.string(root.namespace));
				io.setSourceLabel(path,Std.string(root.label));
				if (root.name != null) names.set(ImportPackageNamePrompt.rootKey(path),Std.string(root.name));
			}
			// Registry baselines describe this import's contribution, not a claim
			// on every entry in a shared registry. Undo that contribution in staging
			// before converting again, then preserve unrelated installed entries.
			var registries:Array<Dynamic> = oldMetadata == null ? [] : cast oldMetadata.registries;
			if (registries == null) registries = [];
			for (registry in registries) {
				var path = Std.string(registry.path);
				var live = Path.join([install,path]);
				if (!FileSystem.exists(live)) throw "Local registry deletion preserved: " + path;
				var prepared = ImportRegistryRefresh.prepare(Std.string(registry.before),Std.string(registry.generated),File.getContent(live));
				if (prepared.conflicts.length > 0) {
					// Calculate fresh output privately before deciding whether these
					// values are already applied or are divergent user edits.
					prepared = ImportRegistryRefresh.regenerationSeed(Std.string(registry.before),
						Std.string(registry.generated),File.getContent(live));
					if (prepared.conflicts.length > 0) throw "Local registry edits preserved: " + path + " " + prepared.conflicts.join(", ");
					registryRegeneration.set(path,true);
				}
				registrySeeds.set(path,prepared.text);
				ImportFile.saveContent(path,prepared.text);
			}
			ImportSongOwnership.invalidateOwnerIdentityIndex();
			progress({phase:"scanning-retained-source", current:source, completed:0, total:0});
			var scan = ImportWorkflow.scanNow(source,Std.string(record.type));
			if (scan == null || scan.rootScanTruncated == true || scan.packageScanTruncated == true)
				throw "Import rescan was incomplete; installed content is unchanged.";
			for (field in ["rootScanDiagnostics","packageScanDiagnostics"]) {
				var diagnostics:Array<Dynamic> = cast Reflect.field(scan,field);
				if (diagnostics != null) for (diagnostic in diagnostics)
					if (Std.string(diagnostic.severity).toLowerCase() == "error")
						throw "Import rescan was incomplete; installed content is unchanged. " + Std.string(diagnostic.message);
			}
			if (previous != null && scan.errors != null && scan.errors.length > 0)
				throw "Import refresh scan needs attention; installed content is unchanged. " + scan.errors.join("\n");
			for (expected in (cast record.roots:Array<Dynamic>)) {
				var expectedPath = Path.normalize(FileSystem.fullPath(Path.join([source,Std.string(expected.relative)])));
				var found = false;
				if (scan.detectedRoots != null) for (root in scan.detectedRoots)
					if (ImportRevision.normalizeEngine(root.engine) == ImportRevision.normalizeEngine(Std.string(expected.engine))
						&& Path.normalize(FileSystem.fullPath(root.root)) == expectedPath) found = true;
				if (!found) throw "Import rescan lost a previously detected source root; installed content is unchanged.";
			}
			if (cancel()) throw "Import cancelled before conversion.";
			var imported = convert(source,scan,names);
			if (imported == null || imported.failed > 0 || cancel())
				throw "Import conversion did not complete; installed content is unchanged. "
					+ (imported == null || imported.errors == null ? "" : imported.errors.join("\n"));
			var outputs:Array<ImportRefreshStagedOutput> = [];
			var baselines:Array<ImportRefreshManifestFile> = [];
			var nextRegistries:Array<Dynamic> = [];
			var written = io.writtenPaths();
			var checkedOutputs = 0;
			progress({phase:"preparing-output", current:"", completed:0, total:written.length});
			for (path in written) {
				if (!StringTools.startsWith(path,"assets/")) continue;
				var staged = Path.join([stage,path]);
				if (!FileSystem.exists(staged) || FileSystem.isDirectory(staged)) continue;
				var before = isRegistry(path) || !maskedPaths.exists(path) ? io.before(path) : null;
				if (isRegistry(path)) {
					var live = Path.join([install,path]);
					var current = FileSystem.exists(live) ? File.getContent(live) : "{}";
					var generated = File.getContent(staged);
					// Staging's registry seed is the base with this import removed.
					var seed = registrySeeds.exists(path) ? registrySeeds.get(path)
						: before == null || before.text == null ? "{}" : before.text;
					var liveBase = current;
					var previousRegistry:Dynamic = null;
					var reconcileGenerated = registryRegeneration.exists(path);
					for (r in registries) if (Std.string(r.path) == path) {
						previousRegistry = r;
						var p = ImportRegistryRefresh.prepare(Std.string(r.before),Std.string(r.generated),current);
						if (p.conflicts.length > 0) {
							reconcileGenerated = true;
							p = ImportRegistryRefresh.regenerationSeed(Std.string(r.before),Std.string(r.generated),current);
							if (p.conflicts.length > 0) throw "Local registry edits preserved: " + path + " " + p.conflicts.join(", ");
						}
						liveBase = p.text;
					}
					var merged = reconcileGenerated && previousRegistry != null
						? ImportRegistryRefresh.merge(Std.string(previousRegistry.generated),generated,current)
						: ImportRegistryRefresh.merge(seed,generated,liveBase);
					if (merged.conflicts.length > 0) throw "Concurrent registry edits preserved: " + path + " " + merged.conflicts.join(", ");
					if (reconcileGenerated) {
						// A merge leaves unchanged fields alone. Also validate all of
						// this owner's regenerated contribution so unchanged importer
						// values cannot silently accept divergent edits or deletions.
						var validated = ImportRegistryRefresh.prepare(seed,generated,merged.text);
						if (validated.conflicts.length > 0) throw "Local registry edits preserved: " + path + " " + validated.conflicts.join(", ");
					}
					File.saveContent(staged,merged.text);
					nextRegistries.push({path:path,before:liveBase,generated:merged.text});
					if (FileSystem.exists(live)) baselines.push({path:path,owner:owner,sha256:Sha256.make(haxe.io.Bytes.ofString(current)).toHex()});
				} else if (before != null && !maskedPaths.exists(path)) {
					// Legacy output has no trusted generated baseline. Do not claim it
					// simply because the user selected the same source folder again.
					throw "Existing untracked import file preserved: " + path;
				}
				outputs.push({path:path,stagedPath:path,sha256:ImportSourceSnapshot.sha256File(staged)});
				progress({phase:"preparing-output", current:path, completed:++checkedOutputs, total:written.length});
			}
			ImportIO.end(); ended = true;
			ImportRootScanner.setRetainedSourceEngines(previousEngines);
			if (scan.detectedEngines != null) for (engine in scan.detectedEngines)
				if (ImportRevision.normalizeEngine(engine) != "" && (cast record.engines:Array<String>).indexOf(engine) < 0)
					(cast record.engines:Array<String>).push(engine);
			record.dependencyDiagnostics = dependencyDiagnostics(scan);
			record.scanDiagnostics = scan.errors;
			record.revisions = [for (engine in (cast record.engines:Array<String>)) ImportRevision.current(engine,EngineBranding.version())];
			var metadata:Dynamic = {importRecord:record,registries:nextRegistries};
			progress({phase:"publishing-import",current:Std.string(record.label),completed:0,total:1});
			var applied = ImportRefreshTransaction.apply(install,stage,state,owner,["assets"],outputs,metadata,cancel,baselines,progress);
			if (applied.status != ImportRefreshTransaction.STATUS_APPLIED)
				throw "Import refresh " + applied.status + ": " + [for (c in applied.conflicts) c.path + " (" + c.reason + ")"].join(", ");
			ImportSongOwnership.invalidateOwnerIdentityIndex();
			// Publication is already committed. A disposable staging cleanup
			// failure must not report that installed import as failed.
			progress({phase:"cleaning-up-import", current:Std.string(record.label), completed:0, total:0});
			try deleteStage(stage) catch (cleanup:Dynamic)
				trace("[import-refresh-cleanup-error] " + Std.string(cleanup));
			return imported;
		} catch (error:Dynamic) {
			trace("[import-refresh-conversion-error] " + Std.string(error) + "\n" + haxe.CallStack.toString(haxe.CallStack.exceptionStack()));
			if (!ended) ImportIO.end();
			ImportRootScanner.setRetainedSourceEngines(previousEngines);
			ImportSongOwnership.invalidateOwnerIdentityIndex();
			try deleteStage(stage) catch (cleanup:Dynamic)
				trace("[import-refresh-cleanup-error] " + Std.string(cleanup));
			throw error;
		}
	}

	/** Only browsing states call this. While refreshing, they gate actions which
	 * could enter gameplay/editors or start a competing importer. */
	public static function browseTick():ImportRefreshBrowseStatus {
		if (!checked) { checked = true; startQueueInspection(); }
		if (!active && queue.length > 0) startNext();
		mutex.acquire();
		var value:ImportRefreshBrowseStatus = {busy:active,label:status.label,fraction:status.fraction,
			complete:status.complete,changed:status.changed,blocked:status.blocked};
		if (measurements != null) {
			var measured = measurements.snapshot(haxe.Timer.stamp(), queue.length);
			for (field in Reflect.fields(measured)) Reflect.setField(value, field, Reflect.field(measured, field));
		}
		var handoff = !active && !handedOff && pendingHandoff;
		var names = handoff ? completedNames.copy() : [];
		if (handoff) { handedOff = true; pendingHandoff = false; completedNames = []; }
		mutex.release();
		if (handoff) { ModuleFunctions.completeImportOnMainThread(names); generation++; }
		return value;
	}

	static function startQueueInspection():Void {
		var install = Sys.getCwd();
		mutex.acquire();
		active = true;
		status.busy = true;
		status.label = "Checking saved imports";
		measurements = new ImportRefreshProgress(haxe.Timer.stamp());
		mutex.release();
		// Receipt parsing and recoverable storage maintenance can inspect many
		// thousands of paths. Never perform it inside a menu's first update.
		Thread.create(function() {
			try loadQueue(install) catch (error:Dynamic) {
				mutex.acquire();
				status.blocked = true;
				status.label = Std.string(error);
				mutex.release();
			}
			mutex.acquire();
			active = false;
			status.busy = false;
			mutex.release();
		});
	}

	static function loadQueue(install:String):Void {
		var cache = Path.join([install,CACHE_ROOT]);
		var records = Path.join([cache,"records"]);
		if (!FileSystem.exists(records)) return;
		var recordNames = [for (name in FileSystem.readDirectory(records))
			if (~/^[a-f0-9]{64}\.json$/.match(name)) name];
		recordNames.sort(Reflect.compare);
		var completed = 0;
		for (name in recordNames) {
			mutex.acquire();
			measurements.update({phase:"checking-import-receipts",current:name,completed:completed,total:recordNames.length},haxe.Timer.stamp());
			mutex.release();
			var id = name.substr(0,64);
			var owner = "retained-import:" + id;
			try {
				var conflicts = ImportRefreshTransaction.recover(install,Path.join([cache,"state"]),owner);
				if (conflicts.length > 0) throw "Interrupted refresh needs attention; installed edits were preserved.";
				var manifest = committedManifest(Path.join([cache,"state"]),owner);
				if (manifest == null || manifest.owner != owner || manifest.revision == null) continue;
				var record:Dynamic = manifest.revision.importRecord;
				if (record == null || record.id != id || record.schemaVersion != 1) continue;
				var stale = false;
				for (stamp in (cast record.revisions:Array<Dynamic>)) {
					var assessment = ImportRevision.assess(stamp,Std.string(stamp.sourceEngine));
					if (assessment.status == ImportRevision.FUTURE || assessment.status == ImportRevision.UNKNOWN)
						throw "Import receipt is newer or unrecognized; its files were preserved.";
					if (assessment.status == ImportRevision.OUTDATED) stale = true;
				}
				if (stale) { mutex.acquire(); queue.push(record); mutex.release(); }
			} catch (error:Dynamic) {
				trace("[import-refresh-error] " + Std.string(error));
				mutex.acquire(); status.blocked = true; status.label = Std.string(error); mutex.release();
			}
			completed++;
		}
		mutex.acquire();
		measurements.update({phase:"checking-import-receipts",current:"",completed:recordNames.length,total:recordNames.length},haxe.Timer.stamp());
		mutex.release();
	}

	static function startNext():Void {
		var record = queue.shift();
		trace("[import-refresh-start] " + Std.string(record.label));
		active = true; handedOff = false;
		status.busy = true; status.complete = false; status.changed = false; status.fraction = 0;
		status.label = "Refreshing import: " + Std.string(record.label);
		measurements = new ImportRefreshProgress(haxe.Timer.stamp());
		var install = Sys.getCwd();
		Thread.create(function() {
			ModuleFunctions.setImportBackgroundMode(true);
			ModuleFunctions.setImportCancelCallback(function() return false);
			var lastDiagnosticPhase = '';
			var lastDiagnosticTime:Float = 0;
			var diagnostics = Sys.getEnv('CAMMIE_IMPORT_REFRESH_TRACE') == '1';
			var onProgress = function(payload:Dynamic) {
				if (diagnostics) {
					var phase = Std.string(payload.phase);
					var now = Sys.time();
					if (phase != lastDiagnosticPhase || now - lastDiagnosticTime >= 2) {
						lastDiagnosticPhase = phase;
						lastDiagnosticTime = now;
						trace('[import-refresh-progress] ' + phase + ' ' + Std.string(payload.completed)
							+ '/' + Std.string(payload.total) + ' ' + Std.string(payload.current));
					}
				}
				mutex.acquire();
				status.label = Std.string(record.label);
				measurements.update(payload, haxe.Timer.stamp());
				status.fraction = measurements.total <= 0 ? 0
					: Math.min(1, measurements.completed / measurements.total);
				mutex.release();
			};
			ModuleFunctions.setImportProgressCallback(onProgress);
			try {
				var result = regenerate(install,record,ImportWorkflow.convertRetainedSource,function() return false,onProgress);
				mutex.acquire();
				if (result.importedSongs != null) for (name in result.importedSongs)
					if (completedNames.indexOf(name) < 0) completedNames.push(name);
				trace("[import-refresh-complete] " + Std.string(record.label));
				pendingHandoff = true; status.changed = true; status.label = "Imports refreshed."; status.fraction = 1;
				mutex.release();
			} catch (error:Dynamic) {
				trace("[import-refresh-error] " + Std.string(record.label) + ": " + Std.string(error));
				mutex.acquire(); status.blocked = true; status.label = Std.string(error); mutex.release();
			}
			ModuleFunctions.setImportProgressCallback(null);
			ModuleFunctions.setImportCancelCallback(null);
			ModuleFunctions.setImportBackgroundMode(false);
			mutex.acquire(); active = false; status.busy = false; status.complete = true; mutex.release();
		});
	}

	static function isRegistry(path:String):Bool return ImportIO.isRegistry(path);

	static function dependencyDiagnostics(scan:ImportScanResult):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (scan != null && scan.songs != null) for (song in scan.songs)
			if (song != null && song.missing != null) for (dependency in song.missing)
				result.push(dependency);
		return result;
	}

	static function committedManifest(state:String,owner:String):Dynamic {
		if (!FileSystem.exists(ImportRefreshTransaction.manifestPath(state,owner))) return null;
		return ImportRefreshTransaction.loadManifest(state,owner);
	}
	static function relativeTo(path:String,root:String):Null<String> {
		if (path == null || root == null) return null;
		var clean = StringTools.replace(Path.normalize(FileSystem.absolutePath(path)),"\\","/");
		var base = StringTools.replace(Path.normalize(FileSystem.absolutePath(root)),"\\","/");
		#if windows
		var comparable = clean.toLowerCase(); var parent = base.toLowerCase();
		#else
		var comparable = clean; var parent = base;
		#end
		return comparable == parent ? "" : (StringTools.startsWith(comparable,parent + "/") ? clean.substr(base.length+1) : null);
	}
	static function contained(root:String,relative:String):String {
		if (relative == null || Path.isAbsolute(relative) || relative.indexOf("\\") >= 0)
			throw "Invalid retained source path.";
		for (component in relative.split("/")) if (component == ".." || component == "." || component == "")
			throw "Invalid retained source path.";
		var candidate = Path.join([root,relative]);
		if (relativeTo(FileSystem.fullPath(candidate),FileSystem.fullPath(root)) == null)
			throw "Retained source leaves the import cache.";
		return candidate;
	}
	static function atomicText(path:String,text:String):Void {
		// These owner pointers are immutable. A failed import can leave one
		// behind; reuse it instead of renaming over it (Windows rejects that).
		if (FileSystem.exists(path)) {
			if (!FileSystem.isDirectory(path) && File.getContent(path) == text) return;
			throw "Retained import pointer conflicts with its owner: " + path;
		}
		var temporary = path + ".tmp";
		File.saveContent(temporary,text);
		FileSystem.rename(temporary,path);
	}
	static function deleteStage(path:String):Void {
		if (!FileSystem.exists(path)) return;
		// Generated staging paths have no donor symlinks; never follow an entry
		// which resolves outside this disposable subtree during cleanup.
		var root = FileSystem.fullPath(path);
		var stack = [path]; var directories:Array<String> = [];
		while (stack.length > 0) {
			var current = stack.pop(); directories.push(current);
			var entries = FileSystem.readDirectory(current);
			if (entries == null) throw "Could not enumerate import staging directory: " + current;
			for (name in entries) {
				var child = Path.join([current,name]);
				if (relativeTo(FileSystem.fullPath(child),root) == null) continue;
				if (FileSystem.isDirectory(child)) stack.push(child); else FileSystem.deleteFile(child);
			}
		}
		directories.reverse(); for (directory in directories) {
			try FileSystem.deleteDirectory(directory) catch (error:Dynamic)
				throw "Could not remove import staging directory " + directory + ": " + Std.string(error);
		}
	}
}
#end
