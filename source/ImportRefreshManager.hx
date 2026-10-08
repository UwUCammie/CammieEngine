package;

#if sys
import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import sys.thread.Mutex;
import sys.thread.Thread;
import flixel.FlxG;
import ImportWorkflow.ImportScanResult;
import ImportWorkflow.ImportScanSong;
import ModuleFunctions.SongImportBatchResult;
import ImportRefreshAvailabilitySnapshot.ImportRefreshAvailabilitySnapshot;
import ImportRefreshAvailabilitySnapshot.ImportRefreshPendingSong;
import ImportRefreshTransaction.ImportRefreshStagedOutput;
import ImportRefreshTransaction.ImportRefreshManifestFile;
import ImportRefreshTransaction.ImportRefreshPackageFamilyCatalog;
import ImportSourceSnapshot.ImportSourceSnapshotResult;
import PsychAssetProfile.PsychAssetProfileBuild;

typedef ImportRefreshBrowseStatus = {
	var busy:Bool;
	@:optional var backgroundBusy:Bool;
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

typedef ImportSourceBuildContext = {
	/** Exact selected source root path from the caller, never inferred from host settings. */
	var sourceRoot:String;
	var engine:String;
	var build:PsychAssetProfileBuild;
}

private typedef ImportSourceBuildContextRecord = {
	var rootRelative:String;
	var engine:String;
	var build:PsychAssetProfileBuild;
}

private typedef ImportRefreshAvailabilityReservation = {
	var token:String;
	var transactionOwner:String;
	var roots:Array<String>;
	var committedRoots:Array<String>;
	var waitForOwnerRoots:Array<String>;
	var songs:Array<ImportRefreshPendingSong>;
	var touchedPaths:Array<String>;
	var committed:Bool;
	var handoffPending:Bool;
	var handoffNames:Array<String>;
	var manual:Bool;
	var recoveryBlocked:Bool;
}

private typedef ImportRefreshRuntimeDependencyMetadata = {
	var owners:Array<String>;
	var complete:Bool;
	var touchedPaths:Array<String>;
}

private typedef ImportRefreshQueueInspectionResult = {
	var committedRoots:Array<String>;
	var unavailableOwners:Array<Dynamic>;
	var unresolvedRecovery:Bool;
}

/** Retained source -> private conversion -> owned, recoverable publication.
 * Only metadata is inspected on a normal launch. Source bytes are read again
 * when importer revisions change, never merely because the app version changes. */
class ImportRefreshManager {
	public static inline var CACHE_ROOT:String = "import-cache";
	static inline var MAX_COMPAT_MANIFESTS_PER_RECORD:Int = 4096;
	static inline var MAX_COMPAT_MANIFEST_BYTES:Int = 65536;
	static inline var MAX_COMPAT_METADATA_BYTES_PER_RECORD:Int = 16777216;
	static var mutex:Mutex = new Mutex();
	static var checked:Bool = false;
	static var inspectionPending:Bool = false;
	static var inspectionRunning:Bool = false;
	static var active:Bool = false;
	static var status:ImportRefreshBrowseStatus = {
		busy:false, label:"", fraction:0, complete:false, changed:false, blocked:false
	};
	static var diagnosticMessages:Array<String> = [];
	static var queue:Array<Dynamic> = [];
	static var reservations:Map<String, ImportRefreshAvailabilityReservation> = new Map();
	static var pendingHandoffs:Array<String> = [];
	static var handoffInProgress:Map<String, Bool> = new Map();
	static var committedOwnerRoots:Map<String, Bool> = new Map();
	static var committedPathOwners:Map<String, Array<String>> = new Map();
	static var committedPathsByOwner:Map<String, Array<String>> = new Map();
	static var committedAssetIndexBindings:Map<String, Dynamic> = new Map();
	static var dependentRootsByOwner:Map<String, Array<String>> = new Map();
	static var familyOwnerRootCache:Map<String, Array<String>> = new Map();
	static var unresolvedRecovery:Bool = false;
	static var inspectionSawUnresolvedRecovery:Bool = false;
	static var availabilityRecheckRequested:Bool = false;
	static var scopedUnavailableOwnersByToken:Map<String,Array<String>> = new Map();
	static var scopedUnavailablePathsByToken:Map<String,Array<String>> = new Map();
	static var availabilityEpoch:Int = 1;
	static var availabilityCache:Null<ImportRefreshAvailabilitySnapshot> = null;
	static var reservationSerial:Int = 0;
	static var measurements:ImportRefreshProgress;
	public static var generation(default,null):Int = 0;

	/** Cheap epoch check for high-frequency menu updates. */
	public static function availabilityRevision():Int {
		mutex.acquire();
		var revision = availabilityEpoch;
		mutex.release();
		return revision;
	}

	/** Immutable cached view; path and receipt inspection always runs outside this lock. */
	public static function availabilitySnapshot():ImportRefreshAvailabilitySnapshot {
		ensureQueueInspection();
		mutex.acquire();
		if (availabilityCache == null || availabilityCache.revision != availabilityEpoch) {
			var pending:Map<String, Bool> = new Map();
			var handoff:Map<String, Bool> = new Map();
			var touched:Map<String, Bool> = new Map();
			var songs:Map<String, ImportRefreshPendingSong> = new Map();
			for (reservation in reservations) {
				for (root in reservation.roots) pending.set(root, true);
				if (reservation.handoffPending)
					for (root in reservation.roots) handoff.set(root, true);
				for (path in reservation.touchedPaths) touched.set(path, true);
				for (song in reservation.songs) songs.set(song.key, song);
			}
			for (roots in scopedUnavailableOwnersByToken) for (root in roots)
				if (root != null && root != "") pending.set(root, true);
			for (paths in scopedUnavailablePathsByToken) for (path in paths)
				if (path != null && path != "") touched.set(path, true);
			var pendingRoots = [for (root in pending.keys()) root]; pendingRoots.sort(Reflect.compare);
			var handoffRoots = [for (root in handoff.keys()) root]; handoffRoots.sort(Reflect.compare);
			var committedRoots = [for (root in committedOwnerRoots.keys()) root]; committedRoots.sort(Reflect.compare);
			var touchedPaths = [for (path in touched.keys()) path]; touchedPaths.sort(Reflect.compare);
			var pendingSongs = [for (song in songs) song];
			pendingSongs.sort(function(a, b) return Reflect.compare(a.key, b.key));
			availabilityCache = {
				revision:availabilityEpoch,
				inspectionPending:inspectionPending || unresolvedRecovery,
				pendingOwnerRoots:pendingRoots,
				handoffPendingOwnerRoots:handoffRoots,
				committedOwnerRoots:committedRoots,
				pendingTouchedPaths:touchedPaths,
				pendingSongs:pendingSongs
			};
		}
		var cached = availabilityCache;
		var snapshot:ImportRefreshAvailabilitySnapshot = {
			revision:cached.revision,
			inspectionPending:cached.inspectionPending,
			pendingOwnerRoots:cached.pendingOwnerRoots.copy(),
			handoffPendingOwnerRoots:cached.handoffPendingOwnerRoots.copy(),
			committedOwnerRoots:cached.committedOwnerRoots.copy(),
			pendingTouchedPaths:cached.pendingTouchedPaths.copy(),
			pendingSongs:[for (song in cached.pendingSongs) clonePendingSong(song)]
		};
		mutex.release();
		return snapshot;
	}

	static function clonePendingSong(song:ImportRefreshPendingSong):ImportRefreshPendingSong {
		var copy:ImportRefreshPendingSong = {
			key:song.key, name:song.name, ownerRoot:song.ownerRoot, sourceRoot:song.sourceRoot
		};
		if (song.sourceFolder != null) copy.sourceFolder = song.sourceFolder;
		if (song.destinationFolder != null) copy.destinationFolder = song.destinationFolder;
		return copy;
	}

	static function bumpAvailabilityLocked():Void {
		availabilityEpoch++;
		availabilityCache = null;
	}

	/** Preserve the live gate while recording whether a fresh receipt pass still
	 * found an ownerless recovery condition. A successful pass replaces the old
	 * result; a failed pass remains conservative. */
	static function flagUnresolvedRecoveryLocked():Void {
		unresolvedRecovery = true;
		if (inspectionRunning) inspectionSawUnresolvedRecovery = true;
	}

	static function inspectionUnresolvedRecoveryFound(includePrior:Bool = false):Bool {
		mutex.acquire();
		var result = inspectionSawUnresolvedRecovery || (includePrior && unresolvedRecovery);
		mutex.release();
		return result;
	}

	/** Full warnings stay available in Import Settings after the progress UI retires. */
	public static function diagnostics():Array<String> {
		mutex.acquire();
		var result = diagnosticMessages.copy();
		mutex.release();
		return result;
	}
	public static function diagnosticCount():Int {
		mutex.acquire();
		var result = diagnosticMessages.length;
		mutex.release();
		return result;
	}
	public static function reportFailure(message:String):Void {
		trace("[import-refresh-error] " + message);
		mutex.acquire(); recordDiagnosticLocked(message); mutex.release();
	}
	static function recordDiagnosticLocked(message:String):Void {
		status.blocked = true;
		status.label = message;
		if (diagnosticMessages.indexOf(message) < 0) diagnosticMessages.push(message);
	}

	static function nextReservationTokenLocked(prefix:String):String {
		reservationSerial++;
		return prefix + ":" + Std.string(reservationSerial);
	}

	static function reserveLocked(token:String, transactionOwner:String, roots:Array<String>,
		songs:Array<ImportRefreshPendingSong>, manual:Bool):ImportRefreshAvailabilityReservation {
		var reservation = reservations.get(token);
		if (reservation == null) {
			reservation = {token:token, transactionOwner:transactionOwner == null ? "" : transactionOwner,
				roots:[], committedRoots:[], waitForOwnerRoots:[], songs:[], touchedPaths:[], committed:false, handoffPending:false,
				handoffNames:[], manual:manual, recoveryBlocked:false};
			reservations.set(token, reservation);
		}
		var changed = false;
		if (transactionOwner != null && transactionOwner != "" && reservation.transactionOwner != transactionOwner) {
			reservation.transactionOwner = transactionOwner;
			changed = true;
		}
		if (manual && !reservation.manual) { reservation.manual = true; changed = true; }
		if (roots != null) for (root in roots) {
			var normalized = normalizeOwnerRoot(root);
			if (normalized != "" && reservation.roots.indexOf(normalized) < 0) {
				reservation.roots.push(normalized);
				reservation.roots.sort(Reflect.compare);
				changed = true;
			}
		}
		if (songs != null) {
			var next:Map<String, ImportRefreshPendingSong> = new Map();
			for (song in songs) if (song != null && song.key != null && song.key != "")
				next.set(song.key, clonePendingSong(song));
			var oldKeys = [for (song in reservation.songs) song.key];
			var newKeys = [for (key in next.keys()) key];
			oldKeys.sort(Reflect.compare); newKeys.sort(Reflect.compare);
			if (oldKeys.join("\n") != newKeys.join("\n")) changed = true;
			else for (song in reservation.songs) if (!pendingSongEqual(song, next.get(song.key))) changed = true;
			reservation.songs = [for (song in next) song];
			reservation.songs.sort(function(a, b) return Reflect.compare(a.key, b.key));
		}
		if (changed) bumpAvailabilityLocked();
		return reservation;
	}

	static function pendingSongEqual(left:ImportRefreshPendingSong, right:ImportRefreshPendingSong):Bool {
		return left != null && right != null && left.key == right.key && left.name == right.name
			&& left.ownerRoot == right.ownerRoot && left.sourceRoot == right.sourceRoot
			&& left.sourceFolder == right.sourceFolder && left.destinationFolder == right.destinationFolder;
	}

	static function setReservationDependenciesLocked(reservation:ImportRefreshAvailabilityReservation,
		dependencies:Array<String>):Void {
		var next:Array<String> = [];
		if (dependencies != null) for (value in dependencies) {
			var root = normalizeOwnerRoot(value);
			if (root != "" && next.indexOf(root) < 0) next.push(root);
		}
		next.sort(Reflect.compare);
		if (reservation.waitForOwnerRoots.join("\n") != next.join("\n")) {
			reservation.waitForOwnerRoots = next;
			bumpAvailabilityLocked();
		}
	}

	static function setReservationCommittedRootsLocked(reservation:ImportRefreshAvailabilityReservation,
		roots:Array<String>):Void {
		var next:Array<String> = [];
		if (roots != null) for (value in roots) {
			var root = normalizeOwnerRoot(value);
			if (root != "" && next.indexOf(root) < 0) next.push(root);
		}
		next.sort(Reflect.compare);
		if (reservation.committedRoots.join("\n") != next.join("\n")) {
			reservation.committedRoots = next;
			bumpAvailabilityLocked();
		}
	}

	static function setReservationCandidates(token:String, transactionOwner:String,
		roots:Array<String>, songs:Array<ImportRefreshPendingSong>):Void {
		mutex.acquire();
		var reservation = reserveLocked(token, transactionOwner, roots, null, false);
		var next:Map<String, ImportRefreshPendingSong> = new Map();
		if (songs != null) for (song in songs) if (song != null && song.key != null && song.key != "")
			next.set(song.key, clonePendingSong(song));
		var oldKeys = [for (song in reservation.songs) song.key];
		var newKeys = [for (key in next.keys()) key];
		oldKeys.sort(Reflect.compare); newKeys.sort(Reflect.compare);
		var metadataChanged = oldKeys.join("\n") != newKeys.join("\n");
		if (!metadataChanged) for (song in reservation.songs)
			if (!pendingSongEqual(song, next.get(song.key))) metadataChanged = true;
		if (metadataChanged) {
			reservation.songs = [for (song in next) song];
			reservation.songs.sort(function(a, b) return Reflect.compare(a.key, b.key));
			bumpAvailabilityLocked();
		}
		mutex.release();
	}

	static function setReservationPaths(token:String, paths:Array<String>):Void {
		var normalized:Array<String> = [];
		var outputOwners:Array<String> = [];
		if (paths != null) for (path in paths) {
			var clean = normalizeInstallRelative(path);
			if (clean != "") {
				if (normalized.indexOf(clean) < 0) normalized.push(clean);
				var outputOwner = ownerRootFromInstalledPath(clean);
				if (outputOwner != "" && outputOwners.indexOf(outputOwner) < 0) outputOwners.push(outputOwner);
			}
		}
		normalized.sort(Reflect.compare);
		var expandedOutputOwners = expandDependentOwnerRoots(outputOwners);
		mutex.acquire();
		var reservation = reservations.get(token);
		if (reservation != null) {
			var changed = reservation.touchedPaths.join("\n") != normalized.join("\n");
			if (changed) reservation.touchedPaths = normalized;
			for (root in expandedOutputOwners) if (reservation.roots.indexOf(root) < 0) {
				reservation.roots.push(root);
				reservation.roots.sort(Reflect.compare);
				changed = true;
			}
			if (changed) bumpAvailabilityLocked();
		}
		mutex.release();
	}

	static function setCommittedRootsLocked(roots:Array<String>):Void {
		var changed = false;
		if (roots != null) for (root in roots) {
			var normalized = normalizeOwnerRoot(root);
			if (normalized != "" && !committedOwnerRoots.exists(normalized)) {
				committedOwnerRoots.set(normalized, true);
				changed = true;
			}
		}
		if (changed) bumpAvailabilityLocked();
	}

	static function queueHandoffLocked(token:String, names:Array<String>):Void {
		var reservation = reservations.get(token);
		if (reservation == null) return;
		reservation.committed = true;
		reservation.handoffPending = true;
		reservation.handoffNames = names == null ? [] : names.copy();
		setCommittedRootsLocked(reservation.committedRoots);
		if (pendingHandoffs.indexOf(token) < 0) pendingHandoffs.push(token);
		bumpAvailabilityLocked();
	}

	static function removeToken(values:Array<String>, token:String):Array<String> {
		var result:Array<String> = [];
		for (value in values) if (value != token) result.push(value);
		return result;
	}

	/** Ask for another receipt/recovery pass after the user returns to Freeplay.
	 * Only stale inspection knowledge is retried; active work and live handoffs
	 * keep their reservations until the owning transaction completes. */
	public static function requestAvailabilityRecheck():Bool {
		mutex.acquire();
		var hasScopedBlock = scopedUnavailableOwnersByToken.keys().hasNext()
			|| scopedUnavailablePathsByToken.keys().hasNext();
		var hasRecoveryReservation = false;
		var onlyRecoveryReservations = true;
		for (reservation in reservations) {
			if (reservation == null) continue;
			if (!reservation.recoveryBlocked || reservation.handoffPending
				|| handoffInProgress.exists(reservation.token))
				onlyRecoveryReservations = false;
			else hasRecoveryReservation = true;
		}
		var needsRecheck = unresolvedRecovery || hasScopedBlock || hasRecoveryReservation;
		if (!needsRecheck || active || inspectionRunning || queue.length > 0
			|| pendingHandoffs.length > 0 || !onlyRecoveryReservations) {
			mutex.release();
			return false;
		}
		if (unresolvedRecovery)
			inspectionPending = true;
		else
			availabilityRecheckRequested = true;
		bumpAvailabilityLocked();
		mutex.release();
		ensureQueueInspection();
		return true;
	}

	static function releaseReservationLocked(token:String):Void {
		if (reservations.remove(token)) {
			pendingHandoffs = removeToken(pendingHandoffs, token);
			handoffInProgress.remove(token);
			bumpAvailabilityLocked();
		}
	}

	static function normalizeOwnerRoot(value:String):String {
		if (value == null) return "";
		var root = StringTools.replace(StringTools.trim(value), "\\", "/");
		while (StringTools.startsWith(root, "./")) root = root.substr(2);
		var parts = root.split("/");
		if (parts.length != 3 || parts[0] != "assets" || parts[1] != "imported_mods"
			|| !~/^[A-Za-z0-9._-]+$/.match(parts[2]) || parts[2] == "." || parts[2] == "..") return "";
		return root;
	}

	static function ownerRootForNamespace(namespace:String):String {
		if (namespace == null || !~/^[A-Za-z0-9._-]+$/.match(namespace)
			|| namespace == "." || namespace == "..") return "";
		return normalizeOwnerRoot("assets/imported_mods/" + namespace);
	}

	static function ownerRootsForRecord(record:Dynamic):Array<String> {
		var roots:Array<String> = [];
		var raw:Dynamic = record == null ? null : Reflect.field(record, "roots");
		if (raw != null && Std.isOfType(raw, Array)) for (entry in (cast raw:Array<Dynamic>)) {
			if (entry == null) continue;
			var owner = ownerRootForNamespace(Reflect.field(entry, "namespace") == null
				? null : Std.string(Reflect.field(entry, "namespace")));
			if (owner != "" && roots.indexOf(owner) < 0) roots.push(owner);
		}
		roots.sort(Reflect.compare);
		return roots;
	}

	/** Family membership is backed by committed source snapshots and manifests.
	 * Resolve it only while inspecting or reserving a job, never in a frame read. */
	static function familyOwnerRootsForRecord(record:Dynamic, roots:Array<String>):Array<String> {
		var result:Array<String> = roots == null ? [] : roots.copy();
		if (!recordUsesNightmareVision(record)) return result;
		for (root in (roots == null ? [] : roots)) {
			var cached = familyOwnerRootCache.get(root);
			if (cached == null) {
				var expanded:Array<String> = [root];
				try for (member in ImportPackageFamilyCatalog.forOwner(root)) {
					var normalized = normalizeOwnerRoot(member.root);
					if (normalized != "" && expanded.indexOf(normalized) < 0) expanded.push(normalized);
				} catch (_:Dynamic) {}
				expanded.sort(Reflect.compare);
				for (memberRoot in expanded) familyOwnerRootCache.set(memberRoot, expanded.copy());
				cached = expanded;
			}
			for (memberRoot in cached) if (result.indexOf(memberRoot) < 0) result.push(memberRoot);
		}
	result.sort(Reflect.compare);
	return result;
	}

	static function recordUsesNightmareVision(record:Dynamic):Bool {
		if (record == null) return false;
		var engines:Dynamic = Reflect.field(record, "engines");
		if (engines != null && Std.isOfType(engines, Array))
			for (engine in (cast engines:Array<Dynamic>)) if (engine == "Nightmare Vision") return true;
		var roots:Dynamic = Reflect.field(record, "roots");
		if (roots != null && Std.isOfType(roots, Array))
			for (root in (cast roots:Array<Dynamic>)) if (Reflect.field(root, "engine") == "Nightmare Vision") return true;
		return false;
	}

	static function addCommittedPathOwners(manifest:Dynamic, ownerRoots:Array<String>):Void {
		if (manifest == null || ownerRoots == null || ownerRoots.length == 0) return;
		var files:Dynamic = Reflect.field(manifest, "files");
		if (files == null || !Std.isOfType(files, Array)) return;
		// These maps are read from gameplay and owner asset lookup. Check before
		// taking their mutex so a worker never waits for gameplay while holding it.
		ImportWorkScheduler.cooperate();
		var nextPathsByRoot:Map<String, Array<String>> = new Map();
		var nextOwnersByPath:Map<String, Array<String>> = new Map();
		for (root in ownerRoots) {
			ImportWorkScheduler.cooperate();
			nextPathsByRoot.set(root, []);
		}
		for (entry in (cast files:Array<Dynamic>)) {
			ImportWorkScheduler.cooperate();
			var path:Dynamic = Reflect.field(entry, "path");
			if (path == null) continue;
			var relative = normalizeInstallRelative(Std.string(path));
			if (relative == "" || isRegistry(relative)) continue;
			var key = ownerPathKey(relative);
			var newOwners = nextOwnersByPath.get(key);
			if (newOwners == null) newOwners = [];
			for (root in ownerRoots) {
				if (newOwners.indexOf(root) < 0) newOwners.push(root);
				var paths = nextPathsByRoot.get(root);
				if (paths != null && paths.indexOf(relative) < 0) paths.push(relative);
			}
			newOwners.sort(Reflect.compare);
			nextOwnersByPath.set(key, newOwners);
		}
		for (root in ownerRoots) {
			var paths = nextPathsByRoot.get(root);
			if (paths != null) paths.sort(Reflect.compare);
		}
		var nextAssetBindings = buildAssetIndexBindings(manifest, ownerRoots);
		mutex.acquire();
		for (root in ownerRoots) {
			var oldPaths = committedPathsByOwner.get(root);
			if (oldPaths != null) for (oldPath in oldPaths) {
				var oldKey = ownerPathKey(oldPath);
				var oldOwners = committedPathOwners.get(oldKey);
				if (oldOwners == null) continue;
				oldOwners = oldOwners.filter(function(value) return value != root);
				if (oldOwners.length == 0) committedPathOwners.remove(oldKey);
				else committedPathOwners.set(oldKey, oldOwners);
			}
			var nextPaths = nextPathsByRoot.get(root);
			committedPathsByOwner.set(root, nextPaths == null ? [] : nextPaths.copy());
		}
		for (key in nextOwnersByPath.keys()) {
			var known = committedPathOwners.get(key);
			if (known == null) known = [];
			var newOwners = nextOwnersByPath.get(key);
			if (newOwners != null) for (root in newOwners) {
				if (known.indexOf(root) < 0) known.push(root);
			}
			known.sort(Reflect.compare);
			committedPathOwners.set(key, known);
		}
		updateAssetIndexBindingsLocked(ownerRoots, nextAssetBindings);
		mutex.release();
	}

	/** Build detached index proofs before taking the manager lock. Manifest file
	 * lists can be large, so gameplay getters should only see the final swap. */
	static function buildAssetIndexBindings(manifest:Dynamic, roots:Array<String>):Map<String, Dynamic> {
		var result:Map<String, Dynamic> = new Map();
		var files:Dynamic = Reflect.field(manifest, "files");
		var record:Dynamic = manifest.revision == null ? null : Reflect.field(manifest.revision, "importRecord");
		if (record == null || record.schemaVersion != 1 || record.snapshotId == null
			|| !~/^[a-f0-9]{64}$/.match(Std.string(record.snapshotId))) return result;
		var catalog:Dynamic = Reflect.field(record, "sourceAssetProfiles");
		var profiles:Dynamic = catalog == null ? null : Reflect.field(catalog, "roots");
		if (profiles == null || !Std.isOfType(profiles, Array)
			|| files == null || !Std.isOfType(files, Array)) return result;
		var rawFamily:Dynamic = Reflect.field(record, "packageFamilyCatalog");
		var rawFamilyVersion:Dynamic = rawFamily == null ? null : Reflect.field(rawFamily, "version");
		var hasV3Family = rawFamilyVersion == 3;
		var family:ImportRefreshPackageFamilyCatalog = null;
		if (rawFamily != null) try family = ImportRefreshTransaction.validatePackageFamilyCatalog(rawFamily, record)
			catch (_:Dynamic) family = null;
		if (hasV3Family && family == null) return result;
		for (root in roots) {
			ImportWorkScheduler.cooperate();
			var namespace = root.substr("assets/imported_mods/".length);
			var owned:Array<Dynamic> = [];
			var sidecars:Map<String, Dynamic> = new Map();
			for (entry in (cast files:Array<Dynamic>)) {
				ImportWorkScheduler.cooperate();
				if (entry == null || entry.owner != manifest.owner || entry.path == null
					|| entry.sha256 == null || !~/^[a-f0-9]{64}$/.match(Std.string(entry.sha256))) continue;
				var path = normalizeInstallRelative(Std.string(entry.path));
				if (path == null || !StringTools.startsWith(path, root + "/")) continue;
				owned.push({path:path, sha256:Std.string(entry.sha256)});
				var relative = path.substr(root.length + 1);
				if (StringTools.startsWith(relative, SourceLimeAssetIdentity.SIDECAR_DIR + "/"))
					sidecars.set(relative, entry);
			}
			for (engine in ["Psych Engine", "Nightmare Vision"]) {
				ImportWorkScheduler.cooperate();
				for (scope in (engine == "Psych Engine" ? ["package"] : ["package", "core"])) {
					ImportWorkScheduler.cooperate();
					var selected:Dynamic = null;
					var handoff:Dynamic = null;
					var ambiguous = false;
					var selectedMember:Dynamic = null;
					if (engine == "Nightmare Vision" && scope == "core" && family != null && family.version >= 3) {
						for (member in family.members)
							if (member != null && member.namespace == namespace) selectedMember = member;
					}
					// A family receiver borrows the authenticated provider profile.
					// The selected outer provider keeps its ordinary own-scope index.
					if (selectedMember != null && family.coreProvider != null) {
						var provider = family.coreProvider;
						for (item in (cast profiles:Array<Dynamic>)) {
							ImportWorkScheduler.cooperate();
							if (item == null || item.namespace != provider.namespace
								|| item.rootRelative != provider.rootRelative
								|| ImportRevision.normalizeEngine(Std.string(item.engine)) != engine) continue;
							var profile:Dynamic = item.profile;
							if (profile == null || profile.provenance != "receipt-bound"
								|| profile.snapshotId != record.snapshotId || profile.namespace != provider.namespace
								|| profile.rootRelative != item.rootRelative || profile.sourceEngine != engine
								|| profile.projectSha256 != provider.projectSha256
								|| !~/^[a-f0-9]{64}$/.match(Std.string(profile.projectSha256))) continue;
							if (selected != null) ambiguous = true;
							selected = profile;
						}
						if (selected != null && !ambiguous) handoff = {
							version:1, providerNamespace:provider.namespace,
							providerRootRelative:provider.rootRelative,
							providerProjectSha256:provider.projectSha256,
							receiverRootRelative:selectedMember.sourceRelative,
							receiverNamespace:namespace, catalogVersion:3
						};
					} else {
						for (item in (cast profiles:Array<Dynamic>)) {
							ImportWorkScheduler.cooperate();
							if (item == null || item.namespace != namespace
								|| ImportRevision.normalizeEngine(Std.string(item.engine)) != engine) continue;
							var profile:Dynamic = item.profile;
							if (profile == null || profile.provenance != "receipt-bound"
								|| profile.snapshotId != record.snapshotId || profile.namespace != namespace
								|| profile.rootRelative != item.rootRelative || profile.sourceEngine != engine
								|| profile.projectSha256 == null
								|| !~/^[a-f0-9]{64}$/.match(Std.string(profile.projectSha256))) continue;
							if (selected != null) ambiguous = true;
							selected = profile;
						}
					}
					if (selected == null || ambiguous) continue;
					var sidecar = sidecars.get(SourceLimeAssetIdentity.sidecarRelativePath(engine, scope));
					if (sidecar == null) continue;
					result.set(root + "/" + engine + "/" + scope, {
						owner:root, engine:engine, scope:scope, namespace:namespace,
						snapshotId:record.snapshotId, rootRelative:selected.rootRelative,
						projectSha256:selected.projectSha256, handoff:handoff,
						transactionId:manifest.transactionId,
						indexPath:Std.string(sidecar.path), indexSha256:Std.string(sidecar.sha256),
						indexSize:null, files:owned
					});
				}
			}
		}
		return result;
	}

	/** Replace the small set of verified bindings under the manager lock. */
	static function updateAssetIndexBindingsLocked(roots:Array<String>, next:Map<String, Dynamic>):Void {
		for (root in roots) {
			for (suffix in ["Psych Engine/package", "Nightmare Vision/package", "Nightmare Vision/core"])
				committedAssetIndexBindings.remove(root + "/" + suffix);
		}
		if (next != null) for (key in next.keys()) committedAssetIndexBindings.set(key, next.get(key));
	}

	/** Exact committed owner binding for a shared source asset identity index.
	 * Return a detached view so source callers cannot mutate manager metadata. */
	public static function ownerAssetIndexBinding(owner:String, engine:String, scope:String):Null<Dynamic> {
		ensureQueueInspection();
		var root = normalizeOwnerRoot(owner);
		var normalizedEngine = ImportRevision.normalizeEngine(engine);
		if (normalizedEngine == "Psych Engine") scope = "package";
		if (root == "" || (normalizedEngine != "Psych Engine" && normalizedEngine != "Nightmare Vision")
			|| (normalizedEngine == "Nightmare Vision" && scope != "package" && scope != "core")) return null;
		mutex.acquire();
		var binding = committedAssetIndexBindings.get(root + "/" + normalizedEngine + "/" + scope);
		var bindingGeneration = generation;
		var bindingRevision = availabilityEpoch;
		mutex.release();
		if (binding == null) return null;
		var files:Array<Dynamic> = [];
		for (entry in (cast binding.files:Array<Dynamic>)) {
			ImportWorkScheduler.cooperate();
			files.push({path:entry.path, sha256:entry.sha256});
		}
		return {generation:bindingGeneration, revision:bindingRevision,
			owner:binding.owner, engine:binding.engine, scope:binding.scope,
			namespace:binding.namespace, snapshotId:binding.snapshotId,
			rootRelative:binding.rootRelative, projectSha256:binding.projectSha256,
			handoff:binding.handoff == null ? null : {
				version:binding.handoff.version,
				providerNamespace:binding.handoff.providerNamespace,
				providerRootRelative:binding.handoff.providerRootRelative,
				providerProjectSha256:binding.handoff.providerProjectSha256,
				receiverRootRelative:binding.handoff.receiverRootRelative,
				receiverNamespace:binding.handoff.receiverNamespace,
				catalogVersion:binding.handoff.catalogVersion
			},
			transactionId:binding.transactionId, indexPath:binding.indexPath,
			indexSha256:binding.indexSha256, indexSize:null, files:files};
	}

	static function addRecordDependencyEdges(record:Dynamic, ownerRoots:Array<String>, ?dependencyOwners:Array<String>):Void {
		var raw:Dynamic = dependencyOwners == null
			? (record == null ? null : Reflect.field(record, "runtimeDependencyOwners")) : dependencyOwners;
		if (raw == null || !Std.isOfType(raw, Array) || ownerRoots == null) return;
		ImportWorkScheduler.cooperate();
		mutex.acquire();
		var oldDependencies = [for (dependency in dependentRootsByOwner.keys()) dependency];
		for (dependency in oldDependencies) {
			var dependents = dependentRootsByOwner.get(dependency);
			if (dependents == null) continue;
			dependents = dependents.filter(function(root) return ownerRoots.indexOf(root) < 0);
			if (dependents.length == 0) dependentRootsByOwner.remove(dependency);
			else dependentRootsByOwner.set(dependency, dependents);
		}
		for (value in (cast raw:Array<Dynamic>)) {
			var dependency = normalizeOwnerRoot(Std.string(value));
			if (dependency == "") continue;
			var dependents = dependentRootsByOwner.get(dependency);
			if (dependents == null) dependents = [];
			for (root in ownerRoots) if (root != dependency && dependents.indexOf(root) < 0) dependents.push(root);
			dependents.sort(Reflect.compare);
			dependentRootsByOwner.set(dependency, dependents);
		}
		mutex.release();
	}

	/** Older receipts predate the cached runtimeDependencyOwners field. Recover
	 * only explicit dependency roots from receipt-listed per-song provenance. */
	static function runtimeDependencyMetadata(install:String, manifest:Dynamic, record:Dynamic,
		ownerRoots:Array<String>):ImportRefreshRuntimeDependencyMetadata {
		var owners:Array<String> = [];
		var touchedPaths:Array<String> = [];
		var rawDependencies:Dynamic = Reflect.field(record, "runtimeDependencyOwners");
		if (rawDependencies != null) {
			var complete = Std.isOfType(rawDependencies, Array);
			if (complete) for (raw in (cast rawDependencies:Array<Dynamic>)) {
				ImportWorkScheduler.cooperate();
				var normalized = raw == null ? "" : normalizeOwnerRoot(Std.string(raw));
				if (normalized == "") complete = false;
				else if (owners.indexOf(normalized) < 0) owners.push(normalized);
			}
			owners.sort(Reflect.compare);
			return {owners:owners, complete:complete, touchedPaths:touchedPaths};
		}

		var complete = true;
		var fileCount = 0;
		var byteCount = 0;
		var rawFiles:Dynamic = manifest == null ? null : Reflect.field(manifest, "files");
		if (rawFiles == null || !Std.isOfType(rawFiles, Array))
			return {owners:owners, complete:false, touchedPaths:touchedPaths};
		for (entry in (cast rawFiles:Array<Dynamic>)) {
			ImportWorkScheduler.cooperate();
			var pathValue:Dynamic = entry == null ? null : Reflect.field(entry, "path");
			var path = pathValue == null ? "" : normalizeInstallRelative(Std.string(pathValue));
			if (!isSongCompatManifestPath(path)) continue;
			fileCount++;
			if (fileCount > MAX_COMPAT_MANIFESTS_PER_RECORD) {
				complete = false;
				break;
			}
			var pathComplete = true;
			try {
				var absolute = Path.join([install, path]);
				if (!FileSystem.exists(absolute) || FileSystem.isDirectory(absolute)) {
					pathComplete = false;
				} else {
					var resolvedInstall = StringTools.replace(Path.normalize(FileSystem.fullPath(install)), "\\", "/");
					var resolvedFile = StringTools.replace(Path.normalize(FileSystem.fullPath(absolute)), "\\", "/");
					var resolvedRelative = relativeTo(resolvedFile, resolvedInstall);
					if (resolvedRelative == null || ownerPathKey(resolvedRelative) != ownerPathKey(path))
						pathComplete = false;
					var stat = FileSystem.stat(absolute);
					if (stat.size < 0 || stat.size > MAX_COMPAT_MANIFEST_BYTES
						|| byteCount + stat.size > MAX_COMPAT_METADATA_BYTES_PER_RECORD)
						pathComplete = false;
					if (pathComplete) {
						var bytes = File.getBytes(absolute);
						if (bytes.length != stat.size)
							pathComplete = false;
						else {
							byteCount += bytes.length;
							var expectedHash:Dynamic = Reflect.field(entry, "sha256");
							if (expectedHash == null || Sha256.make(bytes).toHex() != Std.string(expectedHash).toLowerCase())
								pathComplete = false;
							else {
								var data = CompatScriptManifest.parse(bytes.toString());
								var selectedOwner = normalizeOwnerRoot(CompatScriptManifest.selectedRoot(data));
								if (selectedOwner == "" || ownerRoots.indexOf(selectedOwner) < 0)
									pathComplete = false;
								if (pathComplete && data.roots != null) for (root in data.roots) {
									ImportWorkScheduler.cooperate();
									if (root == null || root.dependency != true) continue;
									var dependency = normalizeOwnerRoot(root.path);
									if (dependency == "") pathComplete = false;
									else if (owners.indexOf(dependency) < 0) owners.push(dependency);
								}
							}
						}
					}
				}
			} catch (_:Dynamic) {
				pathComplete = false;
			}
			if (!pathComplete) {
				complete = false;
				if (path != "" && touchedPaths.indexOf(path) < 0) touchedPaths.push(path);
			}
		}
		owners.sort(Reflect.compare);
		touchedPaths.sort(Reflect.compare);
		return {owners:owners, complete:complete, touchedPaths:touchedPaths};
	}

	static function isSongCompatManifestPath(path:String):Bool {
		if (path == null) return false;
		var parts = path.split("/");
		return parts.length == 4 && parts[0].toLowerCase() == "assets"
			&& parts[1].toLowerCase() == "data" && parts[2] != ""
			&& parts[3].toLowerCase() == CompatScriptManifest.FILE_NAME.toLowerCase();
	}

	static function expandDependentOwnerRoots(roots:Array<String>):Array<String> {
		var result:Array<String> = [];
		if (roots != null) for (root in roots) {
			ImportWorkScheduler.cooperate();
			var normalized = normalizeOwnerRoot(root);
			if (normalized != "" && result.indexOf(normalized) < 0) result.push(normalized);
		}
		var index = 0;
		var overflow = result.length > 512;
		ImportWorkScheduler.cooperate();
		mutex.acquire();
		while (index < result.length && !overflow) {
			var dependents = dependentRootsByOwner.get(result[index]);
			index++;
			if (dependents != null) for (dependent in dependents) if (result.indexOf(dependent) < 0) {
				if (result.length >= 512) { overflow = true; break; }
				result.push(dependent);
			}
		}
		if (overflow) {
			flagUnresolvedRecoveryLocked();
			recordDiagnosticLocked("Import dependency ownership exceeded the safe reservation limit; package availability remains unresolved.");
			bumpAvailabilityLocked();
		}
		mutex.release();
	result.sort(Reflect.compare);
	return result;
	}

	static function dependencyOwnerRootsForScan(scan:ImportScanResult, install:String,
		ownRoots:Array<String>):Array<String> {
		var result:Array<String> = [];
		if (scan == null || scan.songs == null) return result;
		for (song in scan.songs) {
			ImportWorkScheduler.cooperate();
			var rawDependencies:Dynamic = Reflect.field(song, "dependencies");
			if (rawDependencies == null || !Std.isOfType(rawDependencies, Array)) continue;
			for (dependency in (cast rawDependencies:Array<Dynamic>)) {
				ImportWorkScheduler.cooperate();
				if (Reflect.field(dependency, "found") != true) continue;
				var searched:Dynamic = Reflect.field(dependency, "searched");
				if (searched == null || !Std.isOfType(searched, Array)) continue;
				for (candidate in (cast searched:Array<Dynamic>)) {
					ImportWorkScheduler.cooperate();
					if (candidate == null) continue;
					var relative = installRelativeCandidate(Std.string(candidate), install);
					if (relative == "") continue;
					var explicitOwner = ownerRootFromInstalledPath(relative);
					if (explicitOwner != "" && (ownRoots == null || ownRoots.indexOf(explicitOwner) < 0)
						&& result.indexOf(explicitOwner) < 0) result.push(explicitOwner);
					mutex.acquire();
					var providers = committedPathOwners.get(ownerPathKey(relative));
					if (providers != null) for (provider in providers)
						if ((ownRoots == null || ownRoots.indexOf(provider) < 0) && result.indexOf(provider) < 0)
							result.push(provider);
					mutex.release();
				}
			}
		}
	result.sort(Reflect.compare);
	return result;
	}

	static function ownerPathKey(path:String):String {
		#if windows
		return path.toLowerCase();
		#else
		return path;
		#end
	}

	static function installRelativeCandidate(path:String, install:String):String {
		if (path == null || StringTools.trim(path) == "") return "";
		var direct = normalizeInstallRelative(path);
		if (direct != "" && StringTools.startsWith(direct, "assets/")) return direct;
		var relative = relativeTo(path, install);
		return normalizeInstallRelative(relative == null ? "" : relative);
	}

	static function ownerRootFromInstalledPath(path:String):String {
		var parts = path == null ? [] : path.split("/");
		if (parts.length < 3 || parts[0] != "assets" || parts[1] != "imported_mods") return "";
		return ownerRootForNamespace(parts[2]);
	}

	static function sourceRootDescriptors(source:String, roots:Array<Dynamic>):Array<Dynamic> {
		var result:Array<Dynamic> = [];
		if (source == null || roots == null) return result;
		for (entry in roots) {
			if (entry == null) continue;
			var relative:Dynamic = Reflect.field(entry, "relative");
			var namespace:Dynamic = Reflect.field(entry, "namespace");
			var engine:Dynamic = Reflect.field(entry, "engine");
			if (relative == null || namespace == null || engine == null) continue;
			result.push({root:Path.join([source, Std.string(relative)]),
				namespace:Std.string(namespace), engine:Std.string(engine)});
		}
		return result;
	}

	static function validateSourceBuildContexts(contexts:Array<ImportSourceBuildContext>, source:String,
		roots:Array<Dynamic>):Array<ImportSourceBuildContextRecord> {
		var result:Array<ImportSourceBuildContextRecord> = [];
		if (contexts == null || contexts.length == 0) return result;
		if (contexts.length > 4096 || roots == null)
			throw "Source build contexts exceed the retained import limit.";
		var selected:Array<Dynamic> = [];
		for (root in roots) {
			var relative = normalizeSourceRootRelative(Reflect.field(root, "relative"));
			var engine = ImportRevision.normalizeEngine(Std.string(Reflect.field(root, "engine")));
			if (relative == null || engine == "") continue;
			selected.push({relative:relative, engine:engine,
				path:canonicalSourceRoot(Path.join([source, relative]))});
		}
		var seen:Map<String, Bool> = new Map();
		var totalFlags = 0;
		var totalValues = 0;
		var totalBuildText = 0;
		for (context in contexts) {
			if (context == null) throw "A source build context is missing its selected source root.";
			var requestedRoot = canonicalSourceRoot(context.sourceRoot);
			var requestedEngine = ImportRevision.normalizeEngine(context.engine);
			if (requestedRoot == "" || requestedEngine == "")
				throw "A source build context must name an exact selected root and supported engine.";
			var match:Dynamic = null;
			for (root in selected)
				if (sameCanonicalSourceRoot(requestedRoot, Std.string(root.path))
					&& requestedEngine == Std.string(root.engine)) {
					match = root;
					break;
				}
			if (match == null)
				throw "A source build context does not match an exact selected root and engine.";
			var relative = Std.string(match.relative);
			var key = relative + "\n" + requestedEngine;
			if (seen.exists(key)) throw "A selected source root has duplicate build contexts.";
			seen.set(key, true);
			var build = normalizeSourceBuild(Reflect.field(context, "build"));
			totalFlags += build.flags == null ? 0 : build.flags.length;
			if (totalFlags > 16384) throw "Source build contexts contain too many flags.";
			totalValues += build.values == null ? 0 : build.values.length;
			if (totalValues > 16384) throw "Source build contexts contain too many values.";
			totalBuildText += sourceBuildTextLength(build);
			if (totalBuildText > 4 * 1024 * 1024)
				throw "Source build contexts exceed the aggregate text limit.";
			result.push({rootRelative:relative, engine:requestedEngine, build:build});
		}
		result.sort(function(a, b) {
			var compared = Reflect.compare(a.rootRelative, b.rootRelative);
			return compared != 0 ? compared : Reflect.compare(a.engine, b.engine);
		});
		return result;
	}

	static function normalizeSourceBuild(raw:Dynamic):PsychAssetProfileBuild {
		if (raw == null || !Reflect.isObject(raw) || Std.isOfType(raw, Array))
			throw "A source build context must provide an explicit build object.";
		var flagsComplete = false;
		if (Reflect.hasField(raw, "flagsComplete")) {
			var rawFlagsComplete:Dynamic = Reflect.field(raw, "flagsComplete");
			if (!Std.isOfType(rawFlagsComplete, Bool))
				throw "Source build flagsComplete must be a boolean.";
			flagsComplete = cast rawFlagsComplete;
		}
		var hasCommand = Reflect.hasField(raw, "command");
		var command:Null<String> = null;
		if (hasCommand)
			command = checkedBuildContextText(Reflect.field(raw, "command"), "command", 128, true, true);
		var targetValue:Dynamic = Reflect.field(raw, "target");
		var target:Null<String> = null;
		if (targetValue != null) {
			target = checkedBuildContextText(targetValue, "target", 128, true, true);
			if (target == "") target = null;
		}
		var rawFlags:Dynamic = Reflect.field(raw, "flags");
		if (Reflect.hasField(raw, "flags") && rawFlags == null)
			throw "Source build flags must be an array when present.";
		if (rawFlags != null && !Std.isOfType(rawFlags, Array))
			throw "Source build flags must be an array.";
		var flags:Array<PsychAssetProfile.PsychAssetProfileFlag> = [];
		var flagStates:Map<String, String> = new Map();
		var seen:Map<String, Bool> = new Map();
		if (rawFlags != null) {
			var values:Array<Dynamic> = cast rawFlags;
			if (values.length > 16384) throw "Source build context has too many flags.";
			for (value in values) {
				if (value == null || !Reflect.isObject(value))
					throw "A source build flag must be an object.";
				var name = checkedBuildContextText(Reflect.field(value, "name"), "flag name", 128, false, true);
				if (!~/^[A-Za-z_][A-Za-z0-9_.-]*$/.match(name))
					throw "Source build flag names must be Lime define identifiers.";
				var key = name;
				if (seen.exists(key)) throw "A source build context contains duplicate flags.";
				seen.set(key, true);
				var rawState = checkedBuildContextText(Reflect.field(value, "state"), "flag state", 32, false).toLowerCase();
				if (rawState != "enabled" && rawState != "disabled" && rawState != "unresolved")
					throw "A source build flag state must be enabled, disabled, or unresolved.";
				var provenance = sourceBuildProvenance(value, "flag provenance");
				flags.push({name:name, state:rawState, provenance:provenance});
				flagStates.set(name, rawState);
			}
		}
		flags.sort(function(a, b) return Reflect.compare(a.name, b.name));
		var rawValues:Dynamic = Reflect.field(raw, "values");
		if (Reflect.hasField(raw, "values") && rawValues == null)
			throw "Source build values must be an array when present.";
		if (rawValues != null && !Std.isOfType(rawValues, Array))
			throw "Source build values must be an array.";
		var values:Array<PsychAssetProfile.PsychAssetProfileValue> = [];
		var seenValues:Map<String, Bool> = new Map();
		if (rawValues != null) {
			var entries:Array<Dynamic> = cast rawValues;
			if (entries.length > 16384) throw "Source build context has too many values.";
			for (entry in entries) {
				if (entry == null || !Reflect.isObject(entry) || Std.isOfType(entry, Array))
					throw "A source build value must be an object.";
				var name = checkedBuildContextText(Reflect.field(entry, "name"), "value name", 128, false, true);
				if (!~/^[A-Za-z_][A-Za-z0-9_.-]*$/.match(name))
					throw "Source build value names must be Lime define identifiers.";
				if (seenValues.exists(name)) throw "A source build context contains duplicate values.";
				seenValues.set(name, true);
				var value = checkedBuildContextText(Reflect.field(entry, "value"), "value", 4096, true, true);
				var provenance = sourceBuildProvenance(entry, "value provenance");
				var state = flagStates.get(name);
				if (state != null && state != "enabled")
					throw "A known source build value conflicts with a disabled or unresolved flag.";
				values.push({name:name, value:value, provenance:provenance});
			}
		}
		values.sort(function(a, b) return Reflect.compare(a.name, b.name));
		var normalized:Dynamic = {target:target, flags:flags, values:values, flagsComplete:flagsComplete};
		if (hasCommand) Reflect.setField(normalized, "command", command);
		return cast normalized;
	}

	static function sourceBuildProvenance(entry:Dynamic, label:String):String {
		if (!Reflect.hasField(entry, "provenance")) return "caller-supplied";
		return checkedBuildContextText(Reflect.field(entry, "provenance"), label, 128, false, true);
	}

	static function sourceBuildTextLength(build:PsychAssetProfileBuild):Int {
		if (build == null) return 0;
		var total = build.target == null ? 0 : build.target.length;
		if (Reflect.hasField(build, "command") && Reflect.field(build, "command") != null)
			total += Std.string(Reflect.field(build, "command")).length;
		if (build.flags != null) for (flag in build.flags) if (flag != null)
			total += (flag.name == null ? 0 : flag.name.length)
				+ (flag.state == null ? 0 : flag.state.length)
				+ (flag.provenance == null ? 0 : flag.provenance.length);
		if (build.values != null) for (value in build.values) if (value != null)
			total += (value.name == null ? 0 : value.name.length)
				+ (value.value == null ? 0 : value.value.length)
				+ (value.provenance == null ? 0 : value.provenance.length);
		return total;
	}

	static function checkedBuildContextText(value:Dynamic, label:String, maximum:Int, allowEmpty:Bool,
		preserveWhitespace:Bool = false):String {
		if (!Std.isOfType(value, String)) throw "Source build context " + label + " must be text.";
		var raw:String = cast value;
		var text = preserveWhitespace ? raw : StringTools.trim(raw);
		if ((!allowEmpty && StringTools.trim(text) == "") || text.length > maximum)
			throw "Source build context " + label + " has an invalid length.";
		for (index in 0...text.length) {
			var code = text.charCodeAt(index);
			if (code < 0x20 || code == 0x7f)
				throw "Source build context " + label + " contains a control character.";
		}
		return text;
	}

	static function normalizeSourceRootRelative(value:Dynamic):Null<String> {
		if (value == null || !Std.isOfType(value, String)) return null;
		var raw = StringTools.replace(StringTools.trim(cast value), "\\", "/");
		if (raw == "") return "";
		if (Path.isAbsolute(raw) || raw.indexOf(":") >= 0 || raw.indexOf("\u0000") >= 0
			|| StringTools.startsWith(raw, "~")) return null;
		var parts:Array<String> = [];
		for (part in raw.split("/")) {
			if (part == "" || part == ".") continue;
			if (part == "..") return null;
			parts.push(part);
		}
		return parts.join("/");
	}

	static function canonicalSourceRoot(path:String):String {
		if (path == null || StringTools.trim(path) == "") return "";
		try {
			var full = Path.normalize(FileSystem.fullPath(path));
			return StringTools.replace(full, "\\", "/");
		} catch (_:Dynamic) return "";
	}

	static function sameCanonicalSourceRoot(left:String, right:String):Bool {
		#if windows
		return left.toLowerCase() == right.toLowerCase();
		#else
		return left == right;
		#end
	}

	static function recordedSourceBuildContexts(record:Dynamic):Array<ImportSourceBuildContextRecord> {
		var raw:Dynamic = Reflect.field(record, "sourceBuildContexts");
		var empty:Array<ImportSourceBuildContextRecord> = [];
		if (raw == null) return empty;
		var snapshotId = Std.string(Reflect.field(record, "snapshotId"));
		var values:Dynamic = Reflect.field(raw, "roots");
		var recordedRoots:Dynamic = Reflect.field(record, "roots");
		var valid = Reflect.field(raw, "version") == 1
			&& Reflect.field(raw, "snapshotId") == snapshotId
			&& Std.isOfType(values, Array) && Std.isOfType(recordedRoots, Array)
			&& (cast values:Array<Dynamic>).length <= 4096;
		if (!valid) {
			Reflect.deleteField(record, "sourceBuildContexts");
			return empty;
		}
		var available:Array<Dynamic> = cast recordedRoots;
		var result:Array<ImportSourceBuildContextRecord> = [];
		var seen:Map<String, Bool> = new Map();
		var totalFlags = 0;
		var totalValues = 0;
		var totalBuildText = 0;
		try {
			for (entry in (cast values:Array<Dynamic>)) {
				if (entry == null) throw "bad build context record";
				var relative = normalizeSourceRootRelative(Reflect.field(entry, "rootRelative"));
				var engine = ImportRevision.normalizeEngine(Std.string(Reflect.field(entry, "engine")));
				if (relative == null || engine == "") throw "bad build context identity";
				var found = false;
				for (root in available) {
					var recordedRelative = normalizeSourceRootRelative(Reflect.field(root, "relative"));
					var recordedEngine = ImportRevision.normalizeEngine(Std.string(Reflect.field(root, "engine")));
					if (recordedRelative == relative && recordedEngine == engine) found = true;
				}
				if (!found) throw "unmatched build context root";
				var key = relative + "\n" + engine;
				if (seen.exists(key)) throw "duplicate build context root";
				seen.set(key, true);
				var build = normalizeSourceBuild(Reflect.field(entry, "build"));
				Reflect.setField(entry, "build", build);
				totalFlags += build.flags == null ? 0 : build.flags.length;
				totalValues += build.values == null ? 0 : build.values.length;
				totalBuildText += sourceBuildTextLength(build);
				if (totalFlags > 16384 || totalValues > 16384 || totalBuildText > 4 * 1024 * 1024)
					throw "retained build context aggregate limit";
				result.push({rootRelative:relative, engine:engine, build:build});
			}
		} catch (_:Dynamic) {
			Reflect.deleteField(record, "sourceBuildContexts");
			return empty;
		}
		result.sort(function(a, b) {
			var compared = Reflect.compare(a.rootRelative, b.rootRelative);
			return compared != 0 ? compared : Reflect.compare(a.engine, b.engine);
		});
		return result;
	}

	static function buildForSourceRoot(contexts:Array<ImportSourceBuildContextRecord>,
		rootRelative:String, engine:String):Null<PsychAssetProfileBuild> {
		if (contexts != null) for (context in contexts)
			if (context.rootRelative == rootRelative && context.engine == engine) return context.build;
		return null;
	}

	static function resolveSourceAssetProfiles(contentRoot:String, record:Dynamic, io:ImportIO,
		buildContexts:Array<ImportSourceBuildContextRecord>, cancelled:Void->Bool):Dynamic {
		var snapshotId = Std.string(Reflect.field(record, "snapshotId"));
		var roots:Array<Dynamic> = cast Reflect.field(record, "roots");
		var profiles:Array<Dynamic> = [];
		if (roots != null) for (root in roots) {
			var engineLabel = Std.string(Reflect.field(root, "engine"));
			var engine = ImportRevision.normalizeEngine(engineLabel);
			if (engine != "Psych Engine" && engine != "Nightmare Vision") continue;
			var relative = normalizeSourceRootRelative(Reflect.field(root, "relative"));
			var namespace:Dynamic = Reflect.field(root, "namespace");
			if (relative == null || namespace == null || StringTools.trim(Std.string(namespace)) == "")
				throw "Source profile could not be bound because a retained source root identity is incomplete.";
			var profile:Dynamic = null;
			try {
				profile = PsychAssetProfile.resolveRetained(contentRoot, snapshotId, relative,
					engine, Std.string(namespace), buildForSourceRoot(buildContexts, relative, engine), cancelled);
			} catch (error:Dynamic) {
				if (Std.isOfType(error, ImportWorkCancelled)) throw error;
				profile = {version:1, provenance:"invalid", complete:false, snapshotId:snapshotId,
					rootRelative:relative, sourceEngine:engine, namespace:Std.string(namespace),
					flags:[], candidates:[], opaqueBuildInputs:[],
					diagnostics:["profile-resolution-failed: " + Std.string(error)]};
			}
			if (profile == null) profile = {version:1, provenance:"invalid", complete:false,
				snapshotId:snapshotId, rootRelative:relative, sourceEngine:engine,
				namespace:Std.string(namespace), flags:[], candidates:[], opaqueBuildInputs:[],
				diagnostics:["profile-resolution-returned-null"]};
			if (Reflect.field(profile, "provenance") == "receipt-bound") {
				var sourceRoot = Path.join([contentRoot, relative]);
				if (io == null)
					throw "Source profile could not be bound because the retained ImportIO scope is missing.";
				try io.setAssetProfile(sourceRoot, contentRoot, snapshotId, relative, engineLabel,
					Std.string(namespace), profile) catch (error:Dynamic)
					throw "Source profile binding failed for " + engineLabel + " root " + relative + ": " + Std.string(error);
				var binding = io.assetProfile(sourceRoot, engineLabel);
				if (binding == null || binding.profile == null
					|| !sameCanonicalSourceRoot(canonicalSourceRoot(binding.contentRoot), canonicalSourceRoot(contentRoot))
					|| Reflect.field(binding.profile, "snapshotId") != snapshotId
					|| Reflect.field(binding.profile, "rootRelative") != relative
					|| Reflect.field(binding.profile, "namespace") != Std.string(namespace)
					|| Reflect.field(binding.profile, "provenance") != "receipt-bound")
					throw "Source profile binding could not be verified for " + engineLabel + " root " + relative + ".";
			} else if (!sourceProfileIsOnlyMissingProject(profile)) {
				var diagnostics = sourceProfileDiagnostics(profile);
				throw "Source profile validation failed for " + engineLabel + " root " + relative + ": " + diagnostics;
			}
			profiles.push({rootRelative:relative, engine:engine, namespace:Std.string(namespace), profile:profile});
		}
		return {version:1, snapshotId:snapshotId, roots:profiles};
	}

	static function sourceProfileIsOnlyMissingProject(profile:Dynamic):Bool {
		if (profile == null || Reflect.field(profile, "provenance") != "invalid") return false;
		var diagnostics:Dynamic = profile == null ? null : Reflect.field(profile, "diagnostics");
		if (!Std.isOfType(diagnostics, Array) || (cast diagnostics:Array<Dynamic>).length != 1) return false;
		var raw:Dynamic = (cast diagnostics:Array<Dynamic>)[0];
		return raw != null && StringTools.startsWith(Std.string(raw), "project-xml-missing:");
	}

	static function sourceProfileDiagnostics(profile:Dynamic):String {
		var diagnostics:Dynamic = profile == null ? null : Reflect.field(profile, "diagnostics");
		if (Std.isOfType(diagnostics, Array)) {
			var messages:Array<String> = [];
			for (raw in (cast diagnostics:Array<Dynamic>)) if (raw != null) messages.push(Std.string(raw));
			if (messages.length > 0) return messages.join("; ");
		}
		return "no diagnostic was supplied";
	}

	static function ownerRootsForScan(scan:ImportScanResult, source:String, type:String):Array<String> {
		var roots:Array<String> = [];
		if (scan != null && scan.detectedRoots != null) for (root in scan.detectedRoots) {
			if (root == null || ImportRevision.normalizeEngine(Reflect.field(root, "engine") == null
				? "" : Std.string(Reflect.field(root, "engine"))) == "") continue;
			var namespace:Dynamic = Reflect.field(root, "namespace");
			var owner = ownerRootForNamespace(namespace == null
				? CompatScriptManifest.namespaceFor(Std.string(Reflect.field(root, "root")), Std.string(Reflect.field(root, "engine")))
				: Std.string(namespace));
			if (owner != "" && roots.indexOf(owner) < 0) roots.push(owner);
		}
		if (roots.length == 0 && ImportRevision.normalizeEngine(type) != "") {
			var owner = ownerRootForNamespace(CompatScriptManifest.namespaceFor(source, type));
			if (owner != "") roots.push(owner);
		}
		roots.sort(Reflect.compare);
		return roots;
	}

	static function candidatesForScan(scan:ImportScanResult, roots:Array<Dynamic>):Array<ImportRefreshPendingSong> {
		var candidates:Array<ImportRefreshPendingSong> = [];
		if (scan == null || scan.songs == null) return candidates;
		for (song in scan.songs) {
			if (song == null || Reflect.field(song, "willImport") != true) continue;
			var rawSourceRoot:Dynamic = Reflect.field(song, "source");
			var sourceRoot = rawSourceRoot == null ? "" : normalizeSourceIdentity(Std.string(rawSourceRoot));
			var selectedRoot:Dynamic = null;
			var selectedLength = -1;
			if (roots != null) for (root in roots) {
				if (root == null) continue;
				var rawPath:Dynamic = Reflect.field(root, "root");
				var rawNamespace:Dynamic = Reflect.field(root, "namespace");
				if (rawPath == null || rawNamespace == null) continue;
				var candidatePath = normalizeSourceIdentity(Std.string(rawPath));
				if (sourceRoot == candidatePath || relativeTo(sourceRoot, candidatePath) != null) {
					if (candidatePath.length > selectedLength) {
						selectedRoot = root;
						selectedLength = candidatePath.length;
					}
				}
			}
			if (selectedRoot == null) continue;
			var owner = ownerRootForNamespace(Std.string(Reflect.field(selectedRoot, "namespace")));
			if (owner == "") continue;
			var rawName:Dynamic = Reflect.field(song, "name");
			var name = rawName == null ? "" : Std.string(rawName);
			if (name == "") continue;
			var folderValue:Dynamic = Reflect.field(song, "sourceFolder");
			var sourceFolder = folderValue == null ? "" : StringTools.trim(Std.string(folderValue));
			var destinationValue:Dynamic = Reflect.field(song, "destinationFolder");
			var destinationFolder = destinationValue == null ? "" : cleanSingleFolder(Std.string(destinationValue));
			var rawCharts:Dynamic = Reflect.field(song, "charts");
			var chartIdentity:Array<String> = rawCharts != null && Std.isOfType(rawCharts, Array)
				? (cast rawCharts:Array<String>).copy() : [];
			for (i in 0...chartIdentity.length) chartIdentity[i] = normalizeSourceIdentity(chartIdentity[i]);
			chartIdentity.sort(Reflect.compare);
			var identity = owner + "\n" + sourceRoot + "\n" + sourceFolder + "\n" + name + "\n" + chartIdentity.join("\n");
			var candidate:ImportRefreshPendingSong = {
				key:"pending:" + Sha256.make(Bytes.ofString(identity)).toHex(),
				name:name,
				ownerRoot:owner,
				sourceRoot:sourceRoot
			};
			if (sourceFolder != "") candidate.sourceFolder = sourceFolder;
			if (destinationFolder != "") candidate.destinationFolder = destinationFolder;
			candidates.push(candidate);
		}
		candidates.sort(function(a, b) return Reflect.compare(a.key, b.key));
		return candidates;
	}

	static function normalizeSourceIdentity(path:String):String {
		if (path == null || StringTools.trim(path) == "") return "";
		var normalized:String;
		try normalized = StringTools.replace(Path.normalize(FileSystem.absolutePath(path)), "\\", "/")
		catch (_:Dynamic) normalized = StringTools.replace(Path.normalize(path), "\\", "/");
		while (normalized.length > 3 && StringTools.endsWith(normalized, "/"))
			normalized = normalized.substr(0, normalized.length - 1);
		return normalized;
	}

	static function cleanSingleFolder(value:String):String {
		if (value == null) return "";
		var folder = StringTools.trim(value);
		return folder != "" && folder != "." && folder != ".." && folder.indexOf("/") < 0
			&& folder.indexOf("\\") < 0 && folder.indexOf(":") < 0 ? folder : "";
	}

	static function normalizeInstallRelative(value:String):String {
		if (value == null || StringTools.trim(value) == "") return "";
		var path = StringTools.replace(Path.normalize(StringTools.trim(value)), "\\", "/");
		while (StringTools.startsWith(path, "./")) path = path.substr(2);
		if (Path.isAbsolute(path) || path.indexOf(":") >= 0) return "";
		for (part in path.split("/")) if (part == "" || part == "." || part == "..") return "";
		return path;
	}

	static function canHandoffOnCurrentState():Bool {
		var state:Dynamic = FlxG.state;
		if (state == null) return true;
		var className = Type.getClassName(Type.getClass(state));
		if (className == null) return false;
		for (safeName in ["MainMenuState", "FreeplayState", "SaveDataState", "ImportSettingsState",
			"CodenameImportedModsState", "RuntimeImportSmokeState"])
			if (className == safeName || StringTools.endsWith(className, "." + safeName)) return true;
		return false;
	}

	static function tryHandoff(token:String):Bool {
		if (!canHandoffOnCurrentState()) return false;
		mutex.acquire();
		var reservation = reservations.get(token);
		if (reservation == null || !reservation.handoffPending || handoffInProgress.exists(token)) {
			mutex.release();
			return reservation == null;
		}
		for (otherToken in reservations.keys()) if (otherToken != token) {
			var other = reservations.get(otherToken);
			if (other == null) continue;
			for (dependency in reservation.waitForOwnerRoots)
				if (other.roots.indexOf(dependency) >= 0 && (!other.committed || other.recoveryBlocked)) {
					mutex.release();
					return false;
				}
		}
		handoffInProgress.set(token, true);
		var names = reservation.handoffNames.copy();
		mutex.release();
		try {
			ModuleFunctions.completeImportOnMainThread(names);
			ImportSongOwnership.invalidateOwnerIdentityIndex();
			mutex.acquire();
			var current = reservations.get(token);
			if (current != null) {
				setCommittedRootsLocked(current.committedRoots);
				releaseReservationLocked(token);
			}
			generation++;
			status.changed = true;
			if (!active && queue.length == 0 && pendingHandoffs.length == 0) {
				status.complete = true;
				status.fraction = 1;
				status.busy = false;
			}
			mutex.release();
			return true;
		} catch (error:Dynamic) {
			mutex.acquire();
			handoffInProgress.remove(token);
			recordDiagnosticLocked(Std.string(error));
			mutex.release();
			throw error;
		}
	}

	static function performPendingHandoffs():Void {
		if (!canHandoffOnCurrentState()) return;
		mutex.acquire();
		var tokens = pendingHandoffs.copy();
		mutex.release();
		for (token in tokens) try tryHandoff(token) catch (error:Dynamic)
			trace("[import-refresh-handoff-error] " + Std.string(error));
	}

	/** Main-thread bridge for the initial worker. The reservation remains held
	 * until the queued cache/registry handoff succeeds in a safe menu state. */
	public static function completeInitialImportHandoff(importedNames:Array<String>):Bool {
		mutex.acquire();
		var selected:String = null;
		for (token in pendingHandoffs) {
			var reservation = reservations.get(token);
			if (reservation != null && reservation.manual) { selected = token; break; }
		}
		if (selected == null) {
			// A browsing progress poll may already have completed the same handoff.
			mutex.release();
			return true;
		}
		var reservation = reservations.get(selected);
		if (reservation != null && importedNames != null)
			reservation.handoffNames = importedNames.copy();
		bumpAvailabilityLocked();
		mutex.release();
		try return tryHandoff(selected) catch (error:Dynamic) {
			trace("[import-refresh-handoff-error] " + Std.string(error));
			return false;
		}
	}

	static function ensureQueueInspection():Void {
		mutex.acquire();
		if (!checked) {
			checked = true;
			inspectionPending = true;
			bumpAvailabilityLocked();
		}
		var shouldStart = checked && (inspectionPending || availabilityRecheckRequested)
			&& !inspectionRunning && !active;
		if (shouldStart) {
			inspectionRunning = true;
			active = true;
			availabilityRecheckRequested = false;
			inspectionSawUnresolvedRecovery = false;
			status.busy = true;
			status.label = "Checking saved imports";
			measurements = new ImportRefreshProgress(ImportWorkScheduler.workStamp());
		}
		mutex.release();
		if (!shouldStart) return;
		var install = Sys.getCwd();
		Thread.create(function() {
			var inspection:ImportRefreshQueueInspectionResult = null;
			var inspectionSucceeded = false;
			try {
				inspection = loadQueue(install);
				inspectionSucceeded = true;
			} catch (error:Dynamic) {
				mutex.acquire();
				recordDiagnosticLocked(Std.string(error));
				mutex.release();
			}
			finishQueueInspection(inspection == null ? [] : inspection.committedRoots,
				inspectionSucceeded,
				inspection == null ? [] : inspection.unavailableOwners,
				inspection != null && inspection.unresolvedRecovery);
		});
	}

	/** Publish receipt-backed owners atomically with the end of the initial
	 * receipt/recovery pass. A failed pass must not expose a partial inventory. */
	static function finishQueueInspection(stagedCommittedRoots:Array<String>, succeeded:Bool,
		unavailableOwnerRecords:Array<Dynamic> = null,
		ownerlessRecoveryFound:Bool = false):Void {
		mutex.acquire();
		if (succeeded) {
			committedOwnerRoots = new Map();
			setCommittedRootsLocked(stagedCommittedRoots);
			scopedUnavailableOwnersByToken = new Map();
			scopedUnavailablePathsByToken = new Map();
			if (unavailableOwnerRecords != null) for (entry in unavailableOwnerRecords) {
				var tokenValue:Dynamic = entry == null ? null : Reflect.field(entry, "token");
				var token = tokenValue == null ? "" : Std.string(tokenValue);
				if (token == "") continue;
				var rootsValue:Dynamic = Reflect.field(entry, "roots");
				var roots:Array<String> = [];
				if (Std.isOfType(rootsValue, Array)) for (rawRoot in (cast rootsValue:Array<Dynamic>)) {
					var root = rawRoot == null ? "" : normalizeOwnerRoot(Std.string(rawRoot));
					if (root != "" && roots.indexOf(root) < 0) roots.push(root);
				}
				roots.sort(Reflect.compare);
				if (roots.length > 0) scopedUnavailableOwnersByToken.set(token, roots);
				var pathsValue:Dynamic = Reflect.field(entry, "paths");
				var paths:Array<String> = [];
				if (Std.isOfType(pathsValue, Array)) for (rawPath in (cast pathsValue:Array<Dynamic>)) {
					var path = rawPath == null ? "" : normalizeInstallRelative(Std.string(rawPath));
					if (path != "" && paths.indexOf(path) < 0) paths.push(path);
				}
				paths.sort(Reflect.compare);
				if (paths.length > 0) scopedUnavailablePathsByToken.set(token, paths);
			}
			unresolvedRecovery = ownerlessRecoveryFound || inspectionSawUnresolvedRecovery;
		} else {
			unresolvedRecovery = true;
			recordDiagnosticLocked("Retained import receipt inspection did not complete; package readiness remains unresolved.");
			bumpAvailabilityLocked();
		}
		inspectionRunning = false;
		inspectionPending = false;
		availabilityRecheckRequested = false;
		active = false;
		status.busy = false;
		bumpAvailabilityLocked();
		mutex.release();
	}

	/** Called by the existing native import worker. Its renderer stays on the
 	 * installed tree; only that worker receives the filesystem staging context. */
	public static function importOnce(source:String, type:String, scan:ImportScanResult,
		names:Map<String,String>, convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void,
		?sourceBuildContexts:Array<ImportSourceBuildContext>):SongImportBatchResult {
		ensureQueueInspection();
		var importCommittedRoots = ownerRootsForScan(scan, source, type);
		var importRoots = expandDependentOwnerRoots(importCommittedRoots);
		var dependencyOwners = dependencyOwnerRootsForScan(scan, Sys.getCwd(), importRoots);
		mutex.acquire();
		if (active || queue.length > 0 || inspectionPending || inspectionRunning || unresolvedRecovery) {
			mutex.release();
			throw "Another import refresh is already running.";
		}
		var token = nextReservationTokenLocked("initial-import");
		var reservation = reserveLocked(token, "", importRoots,
			candidatesForScan(scan, scan == null ? null : scan.detectedRoots), true);
		setReservationCommittedRootsLocked(reservation, importCommittedRoots);
		setReservationDependenciesLocked(reservation, dependencyOwners);
		active = true;
		status.busy = true;
		status.complete = false;
		status.changed = false;
		status.fraction = 0;
		status.label = "Importing content";
		measurements = new ImportRefreshProgress(ImportWorkScheduler.workStamp());
		mutex.release();
		var sharedProgress = function(payload:Dynamic):Void {
			mutex.acquire();
			status.busy = true;
			status.complete = false;
			status.label = "Importing: " + Path.withoutDirectory(Path.normalize(source));
			measurements.update(payload, ImportWorkScheduler.workStamp());
			status.fraction = measurements.total <= 0 ? 0
				: Math.min(1, measurements.completed / measurements.total);
			mutex.release();
			if (progress != null) progress(payload);
		};
		try {
			var result = captureImport(source,type,scan,names,convert,cancel,sharedProgress,token,sourceBuildContexts);
			mutex.acquire();
			active = false;
			status.busy = false;
			status.complete = true;
			var noChanges = Reflect.field(result, "noChanges") == true;
			status.changed = !noChanges;
			status.fraction = 1;
			status.label = noChanges ? "Selected source roots are already imported" : "Import committed; updating the song list";
			var reservation = reservations.get(token);
			if (!noChanges && reservation != null) queueHandoffLocked(token, result.importedSongs);
			mutex.release();
			return result;
		} catch (error:Dynamic) {
			trace("[import-refresh-error] " + Std.string(error) + "\n" + haxe.CallStack.toString(haxe.CallStack.exceptionStack()));
			settleFailedReservation(token, Sys.getCwd());
			mutex.acquire();
			active = false;
			status.busy = false;
			status.complete = true;
			recordDiagnosticLocked(Std.string(error));
			mutex.release();
			throw error;
		}
	}

	static function captureImport(source:String, type:String, scan:ImportScanResult,
		names:Map<String,String>, convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void, reservationToken:String,
		sourceBuildContexts:Array<ImportSourceBuildContext>):SongImportBatchResult {
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
				evidence:root.evidence == null ? [] : root.evidence.copy(),
				name:names == null ? null : names.get(ImportPackageNamePrompt.rootKey(root.root))});
			if (engines.indexOf(root.engine) < 0) engines.push(root.engine);
		}
		if (engines.length == 0 && ImportRevision.normalizeEngine(type) != "") {
			engines.push(ImportRevision.normalizeEngine(type));
			roots.push({relative:"",engine:engines[0],namespace:CompatScriptManifest.namespaceFor(source,engines[0]),
				label:Path.withoutDirectory(Path.normalize(source)),name:null});
		}
		if (engines.length == 0) throw "No supported import owner was found in the scan.";
		var normalizedBuildContexts = validateSourceBuildContexts(sourceBuildContexts, normalized, roots);
		var initialId = retainedImportId(roots);
		var stateRoot = Path.join([cache, "state"]);
		var initialOwner = "retained-import:" + initialId;
		var hasInitialOwner = FileSystem.exists(ImportRefreshTransaction.manifestPath(stateRoot, initialOwner));
		var snapshot = ImportSourceSnapshot.capture(normalized, Path.join([cache,"sources"]), engines[0],
			EngineBranding.version(), {cancelled:cancel, onProgress:function(p) {
				progress({phase:"retaining-source",current:p.current,completed:p.filesCompleted,total:p.filesTotal});
			}});
		if (snapshot.status == "cancelled") throw "Import cancelled before source retention completed.";
		if (!snapshot.complete) throw "Source retention incomplete: " + snapshot.error + " " + snapshot.incompleteReasons.join(", ");
		var effectiveScan = scan;
		var excludedRootPaths:Map<String, Bool> = new Map();
		// A parent selection may contain roots already imported through independent
		// retained owners. Exclude only roots whose receipt-backed subtree is byte-
		// identical to a committed owner root; never merge those owners' baselines.
		// An existing aggregate owner keeps its full selected root set for refresh.
		if (!hasInitialOwner) {
			var previouslyOwned = authenticatedPreviouslyOwnedRoots(install, cache, normalized,
				snapshot, roots, cancel, progress);
			if (previouslyOwned.length > 0) {
				var remainingRoots:Array<Dynamic> = [];
				for (root in roots) {
					cooperateImportWork(cancel);
					var rootPath = Path.join([normalized, Std.string(root.relative)]);
					var key = sourceRootIdentityKey(rootPath, Std.string(root.engine));
					if (previouslyOwned.indexOf(key) >= 0) excludedRootPaths.set(key, true);
					else remainingRoots.push(root);
				}
				if (remainingRoots.length == 0) {
					if (scanHasUnclaimedImportWork(scan))
						throw "Every selected source root already has a verified retained import, but the scan still reports new or unresolved work. No existing owner was changed.";
					cooperateImportWork(cancel);
					mutex.acquire();
					releaseReservationLocked(reservationToken);
					mutex.release();
					return alreadyImportedNoOpResult(scan);
				}
				roots = remainingRoots;
				engines = uniqueRootEngines(roots);
				effectiveScan = scanWithoutPreviouslyOwnedRoots(scan, excludedRootPaths);
			}
		}
		if (engines.length == 0) throw "No supported import owner remains after retained-root reconciliation.";
		normalizedBuildContexts = buildContextsWithoutExcludedRoots(normalizedBuildContexts,
			normalized, excludedRootPaths);
		var id = retainedImportId(roots);
		var owner = "retained-import:" + id;
		var hasOwner = FileSystem.exists(ImportRefreshTransaction.manifestPath(stateRoot, owner));
		var rootOwners = expandDependentOwnerRoots([for (root in roots) ownerRootForNamespace(Std.string(root.namespace))]);
		var dependencyOwners = dependencyOwnerRootsForScan(effectiveScan, install, rootOwners);
		setReservationCandidates(reservationToken, "", rootOwners,
			candidatesForScan(effectiveScan, sourceRootDescriptors(normalized, roots)));
		if (!hasOwner) {
			if (effectiveScan != null && effectiveScan.songs != null) for (song in effectiveScan.songs)
				if (Reflect.field(song,"duplicate") == true && Reflect.field(song,"sourceDuplicate") != true)
					throw "An existing song import has no retained-source ownership baseline. Its files were preserved; automatic refresh requires migration.";
			for (root in roots) if (FileSystem.exists(Path.join([install,"assets","imported_mods",Std.string(root.namespace)])))
				throw "This older import has no retained-source ownership baseline. Its files were preserved; automatic refresh requires migration.";
		}
		var record:Dynamic = {
			schemaVersion:1, id:id, source:Path.join(["sources",snapshot.snapshotId,"content"]),
			snapshotId:snapshot.snapshotId, type:type, engines:engines, roots:roots,
			label:Path.withoutDirectory(Path.normalize(source)), exclusions:snapshot.exclusions,
			dependencyDiagnostics:dependencyDiagnostics(effectiveScan),
			runtimeDependencyOwners:dependencyOwners,
			revisions:[for (engine in engines) ImportRevision.current(engine,EngineBranding.version())]
		};
		if (normalizedBuildContexts.length > 0)
			Reflect.setField(record, "sourceBuildContexts", {
				version:1, snapshotId:snapshot.snapshotId, roots:normalizedBuildContexts
			});
		mutex.acquire();
		var importReservation = reservations.get(reservationToken);
		if (importReservation != null) setReservationDependenciesLocked(importReservation, dependencyOwners);
		mutex.release();
		// A pointer is deliberately published before the transaction. If the
		// process exits after commit, its committed manifest remains discoverable.
		var records = Path.join([cache,"records"]);
		FileSystem.createDirectory(records);
		mutex.acquire();
		var reservation = reservations.get(reservationToken);
		if (reservation != null) reservation.transactionOwner = "retained-import:" + id;
		bumpAvailabilityLocked();
		mutex.release();
		atomicText(Path.join([records,id + ".json"]),Json.stringify({id:id}));
		return regenerate(install,record,convert,cancel,progress,reservationToken);
	}

	static function retainedImportId(roots:Array<Dynamic>):String {
		var keys = [for (root in roots) Std.string(root.engine) + "/" + Std.string(root.namespace)];
		keys.sort(Reflect.compare);
		return Sha256.make(Bytes.ofString(keys.join("\n"))).toHex();
	}

	static function scanHasUnclaimedImportWork(scan:Dynamic):Bool {
		if (scan == null) return true;
		for (field in ["songsToImport", "assetsToImport", "globalPacksToImport", "overlayPlanned"]) {
			var value:Dynamic = Reflect.field(scan, field);
			if (!Std.isOfType(value, Int) && !Std.isOfType(value, Float)) return true;
			if ((cast value:Float) > 0) return true;
		}
		var songs:Dynamic = Reflect.field(scan, "songs");
		if (!Std.isOfType(songs, Array)) return true;
		for (song in (cast songs:Array<Dynamic>)) {
			if (song == null) return true;
			var willImport:Dynamic = Reflect.field(song, "willImport");
			if (willImport == true || (willImport != false && Reflect.field(song, "duplicate") != true)) return true;
		}
		var assets:Dynamic = Reflect.field(scan, "assets");
		if (!Std.isOfType(assets, Array)) return true;
		for (asset in (cast assets:Array<Dynamic>)) {
			if (asset == null || Reflect.field(asset, "duplicate") != true) return true;
		}
		return false;
	}

	static function alreadyImportedNoOpResult(scan:Dynamic):SongImportBatchResult {
		var found:Dynamic = Reflect.field(scan, "songsFound");
		var duplicateSongs:Dynamic = Reflect.field(scan, "duplicateSongs");
		var duplicateAssets:Dynamic = Reflect.field(scan, "duplicateAssets");
		var songs:Dynamic = Reflect.field(scan, "songs");
		if ((!Std.isOfType(found, Int) && !Std.isOfType(found, Float)) && Std.isOfType(songs, Array))
			found = (cast songs:Array<Dynamic>).length;
		if (!Std.isOfType(found, Int) && !Std.isOfType(found, Float)) found = 0;
		if (!Std.isOfType(duplicateSongs, Int) && !Std.isOfType(duplicateSongs, Float)) {
			var count = 0;
			if (Std.isOfType(songs, Array)) for (song in (cast songs:Array<Dynamic>))
				if (song != null && Reflect.field(song, "duplicate") == true) count++;
			duplicateSongs = count;
		}
		if (!Std.isOfType(duplicateAssets, Int) && !Std.isOfType(duplicateAssets, Float)) duplicateAssets = 0;
		var result:SongImportBatchResult = {
			found:Std.int(found), imported:0, importedSongs:[], skipped:Std.int(duplicateSongs), failed:0,
			copiedAssets:0, skippedAssets:Std.int(duplicateAssets), errors:[]
		};
		Reflect.setField(result, "noChanges", true);
		return result;
	}

	static function uniqueRootEngines(roots:Array<Dynamic>):Array<String> {
		var result:Array<String> = [];
		if (roots != null) for (root in roots) {
			if (root == null) continue;
			var engine:Dynamic = Reflect.field(root, "engine");
			if (engine != null && ImportRevision.normalizeEngine(Std.string(engine)) != ""
				&& result.indexOf(Std.string(engine)) < 0) result.push(Std.string(engine));
		}
		return result;
	}

	/** Return exact roots already covered by committed retained-source owners.
	 * Namespace and engine select possible owners; complete verified snapshot
	 * subtrees prove identity. A matching folder name or song duplicate is never
	 * enough to suppress a root. */
	static function authenticatedPreviouslyOwnedRoots(install:String, cache:String, selectedSource:String,
		snapshot:ImportSourceSnapshotResult, roots:Array<Dynamic>, cancel:Void->Bool,
		progress:Dynamic->Void):Array<String> {
		var matched:Array<String> = [];
		if (roots == null || roots.length == 0) return matched;
		var records = cachedRecords(install);
		var state = Path.join([cache, "state"]);
		var possible = false;
		for (root in roots) {
			cooperateImportWork(cancel);
			var engine = ImportRevision.normalizeEngine(Std.string(root.engine));
			var namespace = Std.string(root.namespace);
			for (record in records) {
				var oldRoots:Dynamic = Reflect.field(record, "roots");
				if (oldRoots == null || !Std.isOfType(oldRoots, Array)) continue;
				for (oldRoot in (cast oldRoots:Array<Dynamic>)) {
					cooperateImportWork(cancel);
					if (oldRoot != null
						&& ImportRevision.normalizeEngine(Std.string(Reflect.field(oldRoot, "engine"))) == engine
						&& Reflect.field(oldRoot, "namespace") == namespace) {
						possible = true;
						break;
					}
				}
				if (possible) break;
			}
			if (possible) break;
		}
		if (!possible) return matched;

		// The just-captured tree may have reused a cache entry. Verify its bytes
		// before using its receipt table as comparison evidence.
		try {
			ImportSourceSnapshot.verify(snapshot.snapshotRoot, snapshot.snapshotId, cancel, function(p) {
				if (progress != null) progress({phase:"verifying-selected-root-baseline", current:p.current,
					completed:p.filesCompleted, total:p.filesTotal});
			});
		} catch (error:Dynamic) {
			if (cancel != null && cancel()) throw error;
			throw "The captured source snapshot could not be verified for retained-root migration: " + Std.string(error);
		}
		var newReceipt:Dynamic = readSnapshotReceiptForRootComparison(snapshot.snapshotRoot);
		var verifiedSnapshots:Map<String, String> = new Map();
		var receipts:Map<String, Dynamic> = new Map();
		for (root in roots) {
			cooperateImportWork(cancel);
			var engine = ImportRevision.normalizeEngine(Std.string(root.engine));
			var namespace = Std.string(root.namespace);
			var currentRelative = normalizeSourceRootRelative(Reflect.field(root, "relative"));
			if (currentRelative == null) continue;
			var currentSignature = snapshotSubtreeSignature(newReceipt, currentRelative);
			if (currentSignature == null) continue;
			var currentRootPath = currentRelative == "" ? selectedSource : Path.join([selectedSource, currentRelative]);
			for (record in records) {
				cooperateImportWork(cancel);
				var recordId = Std.string(Reflect.field(record, "id"));
				var oldRoots:Dynamic = Reflect.field(record, "roots");
				if (oldRoots == null || !Std.isOfType(oldRoots, Array)) continue;
				for (oldRoot in (cast oldRoots:Array<Dynamic>)) {
					cooperateImportWork(cancel);
					if (oldRoot == null
						|| ImportRevision.normalizeEngine(Std.string(Reflect.field(oldRoot, "engine"))) != engine
						|| Reflect.field(oldRoot, "namespace") != namespace) continue;
					var oldRelative = normalizeSourceRootRelative(Reflect.field(oldRoot, "relative"));
					if (oldRelative == null) continue;
					var owner = "retained-import:" + recordId;
					var manifest:Dynamic = null;
					try manifest = committedManifest(state, owner) catch (_:Dynamic) continue;
					var namespaceRoot = ownerRootForNamespace(namespace);
					if (!manifestAuthenticatesOwnerRecord(manifest, owner, namespaceRoot)) continue;
					var oldSnapshotId = Std.string(Reflect.field(record, "snapshotId"));
					if (oldSnapshotId == "") continue;
					var snapshotState = verifiedSnapshots.get(oldSnapshotId);
					if (snapshotState == null) {
						var oldSource = Std.string(Reflect.field(record, "source"));
						var oldContent = "";
						try oldContent = contained(cache, oldSource) catch (_:Dynamic) {}
						if (oldContent == "" || Path.withoutDirectory(Path.directory(oldContent)) != oldSnapshotId) {
							verifiedSnapshots.set(oldSnapshotId, "invalid");
						} else {
						var oldSnapshotRoot = Path.directory(oldContent);
						try {
							ImportSourceSnapshot.verify(oldSnapshotRoot, oldSnapshotId, cancel, function(p) {
								if (progress != null) progress({phase:"verifying-existing-root-baseline",
									current:p.current, completed:p.filesCompleted, total:p.filesTotal});
							});
							receipts.set(oldSnapshotId, readSnapshotReceiptForRootComparison(oldSnapshotRoot));
							verifiedSnapshots.set(oldSnapshotId, "valid");
						} catch (error:Dynamic) {
							if (cancel != null && cancel()) throw error;
							verifiedSnapshots.set(oldSnapshotId, "invalid");
						}
					}
					snapshotState = verifiedSnapshots.get(oldSnapshotId);
				}
				if (snapshotState != "valid") continue;
				var oldReceipt = receipts.get(oldSnapshotId);
				if (oldReceipt == null) continue;
				var oldSignature = snapshotSubtreeSignature(oldReceipt, oldRelative);
				if (oldSignature == null || oldSignature != currentSignature) continue;
				var matchKey = sourceRootIdentityKey(currentRootPath, engine);
				if (matched.indexOf(matchKey) < 0) matched.push(matchKey);
				break;
			}
		}
		}
		matched.sort(Reflect.compare);
		return matched;
	}

	static function manifestAuthenticatesOwnerRecord(manifest:Dynamic, owner:String, ownerRoot:String):Bool {
		if (manifest == null || ownerRoot == "" || Reflect.field(manifest, "owner") != owner) return false;
		var roots:Dynamic = Reflect.field(manifest, "ownedRoots");
		if (roots == null || !Std.isOfType(roots, Array)
			|| (cast roots:Array<Dynamic>).indexOf("assets") < 0) return false;
		var files:Dynamic = Reflect.field(manifest, "files");
		if (files == null || !Std.isOfType(files, Array) || (cast files:Array<Dynamic>).length == 0) return false;
		for (file in (cast files:Array<Dynamic>))
			if (file == null || Reflect.field(file, "owner") != owner
				|| !StringTools.startsWith(Std.string(Reflect.field(file, "path")), "assets/")) return false;
		var revision:Dynamic = Reflect.field(manifest, "revision");
		var record:Dynamic = revision == null ? null : Reflect.field(revision, "importRecord");
		if (record == null || Reflect.field(record, "id") != owner.substr("retained-import:".length)) return false;
		var recordRoots:Dynamic = Reflect.field(record, "roots");
		if (recordRoots == null || !Std.isOfType(recordRoots, Array)) return false;
		var namespace = ownerRoot.substr("assets/imported_mods/".length);
		for (root in (cast recordRoots:Array<Dynamic>))
			if (root != null && Reflect.field(root, "namespace") == namespace) return true;
		return false;
	}

	static function readSnapshotReceiptForRootComparison(snapshotRoot:String):Dynamic {
		var path = Path.join([snapshotRoot, "receipt.json"]);
		if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) return null;
		var size = FileSystem.stat(path).size;
		if (size < 0 || size > PsychAssetProfile.MAX_RECEIPT_BYTES) return null;
		return Json.parse(File.getContent(path));
	}

	static function snapshotSubtreeSignature(receipt:Dynamic, rootRelative:String):Null<String> {
		if (receipt == null) return null;
		var root = normalizeSourceRootRelative(rootRelative);
		if (root == null) return null;
		var incomplete:Dynamic = Reflect.field(receipt, "incompleteReasons");
		if (!Std.isOfType(incomplete, Array) || (cast incomplete:Array<Dynamic>).length != 0) return null;
		var directoryValues:Dynamic = Reflect.field(receipt, "directories");
		var fileValues:Dynamic = Reflect.field(receipt, "files");
		var exclusionValues:Dynamic = Reflect.field(receipt, "exclusions");
		var omissionValues:Dynamic = Reflect.field(receipt, "omissions");
		if (!Std.isOfType(directoryValues, Array) || !Std.isOfType(fileValues, Array)
			|| !Std.isOfType(exclusionValues, Array) || !Std.isOfType(omissionValues, Array)) return null;
		var directories:Array<String> = [];
		for (value in (cast directoryValues:Array<Dynamic>)) {
			var relative = snapshotPathWithinRoot(Std.string(value), root);
			if (relative != null && relative != "" && directories.indexOf(relative) < 0)
				directories.push(relative);
		}
		directories.sort(Reflect.compare);
		var files:Array<Array<Dynamic>> = [];
		for (entry in (cast fileValues:Array<Dynamic>)) {
			if (entry == null) return null;
			var path:Dynamic = Reflect.field(entry, "path");
			var relative = path == null ? null : snapshotPathWithinRoot(Std.string(path), root);
			if (relative == null) continue;
			files.push([relative, Reflect.field(entry, "size"), Std.string(Reflect.field(entry, "sha256")).toLowerCase()]);
		}
		files.sort(function(a, b) return Reflect.compare(Std.string(a[0]), Std.string(b[0])));
		var exclusions:Array<Array<Dynamic>> = [];
		for (entry in (cast exclusionValues:Array<Dynamic>)) {
			if (entry == null) return null;
			var path:Dynamic = Reflect.field(entry, "path");
			var relative = path == null ? null : snapshotPathWithinRoot(Std.string(path), root);
			if (relative == null) continue;
			exclusions.push([relative, Reflect.field(entry, "size"), Reflect.field(entry, "reason"),
				Reflect.field(entry, "detectedHeader")]);
		}
		exclusions.sort(function(a, b) return Reflect.compare(Std.string(a[0]), Std.string(b[0])));
		var omissions:Array<Array<Dynamic>> = [];
		for (entry in (cast omissionValues:Array<Dynamic>)) {
			if (entry == null) return null;
			var path:Dynamic = Reflect.field(entry, "path");
			if (path == null) return null;
			var rawPath = Std.string(path);
			// A root-relative empty omission cannot be attributed to one child root.
			if (rawPath == "" && root != "") return null;
			var relative = snapshotPathWithinRoot(rawPath, root);
			if (relative == null) continue;
			omissions.push([relative, Reflect.field(entry, "reason"), Reflect.field(entry, "detail")]);
		}
		if (omissions.length > 0) return null;
		return Json.stringify([directories, files, exclusions]);
	}

	static function snapshotPathWithinRoot(path:String, root:String):Null<String> {
		var normalized = StringTools.replace(path == null ? "" : path, "\\", "/");
		if (normalized == "") return root == "" ? "" : null;
		if (root == "") return normalized;
		if (normalized == root) return "";
		return StringTools.startsWith(normalized, root + "/")
			? normalized.substr(root.length + 1) : null;
	}

	static function sourceRootIdentityKey(path:String, engine:String):String {
		var normalizedPath = canonicalSourceRoot(path);
		#if windows
		normalizedPath = normalizedPath.toLowerCase();
		#end
		return normalizedPath + "\n" + ImportRevision.normalizeEngine(engine);
	}

	static function buildContextsWithoutExcludedRoots(contexts:Array<ImportSourceBuildContextRecord>,
		source:String, excluded:Map<String, Bool>):Array<ImportSourceBuildContextRecord> {
		if (contexts == null || contexts.length == 0 || excluded == null || !hasMapEntries(excluded))
			return contexts;
		var result:Array<ImportSourceBuildContextRecord> = [];
		for (context in contexts) {
			if (context == null) { result.push(context); continue; }
			var rootPath = context.rootRelative == "" ? source : Path.join([source, context.rootRelative]);
			var key = sourceRootIdentityKey(rootPath, context.engine);
			if (!excluded.exists(key)) result.push(context);
		}
		return result;
	}

	static function scanWithoutPreviouslyOwnedRoots(scan:ImportScanResult,
		excluded:Map<String, Bool>):ImportScanResult {
		if (scan == null || excluded == null || !hasMapEntries(excluded)) return scan;
		var result:ImportScanResult = cast Reflect.copy(scan);
		if (scan.detectedRoots != null) {
			var roots:Array<Dynamic> = [];
			var engines:Map<String, Bool> = new Map();
			for (root in scan.detectedRoots) {
				if (root == null) continue;
				var key = sourceRootIdentityKey(Std.string(Reflect.field(root, "root")),
					Std.string(Reflect.field(root, "engine")));
				if (excluded.exists(key)) continue;
				roots.push(root);
				var engine = Std.string(Reflect.field(root, "engine"));
				if (engine != "" && !engines.exists(engine)) engines.set(engine, true);
			}
			result.detectedRoots = cast roots;
			result.detectedEngines = [for (engine in engines.keys()) engine];
			result.detectedEngines.sort(Reflect.compare);
		}
		if (scan.songs != null) {
			var songs:Array<ImportScanSong> = [];
			for (song in scan.songs) {
				if (song == null) continue;
				var sourcePath:Dynamic = Reflect.field(song, "sourceRoot");
				if (sourcePath == null || StringTools.trim(Std.string(sourcePath)) == "")
					sourcePath = Reflect.field(song, "source");
				if (sourcePath != null && StringTools.trim(Std.string(sourcePath)) != "") {
					var pathKey = canonicalSourceRoot(Std.string(sourcePath));
					#if windows
					pathKey = pathKey.toLowerCase();
					#end
					var engine = Reflect.field(song, "engine");
					for (key in excluded.keys()) {
						var split = key.lastIndexOf("\n");
						var excludedPath = key.substr(0, split);
						var excludedEngine = key.substr(split + 1);
						if (pathKey == excludedPath && (engine == null
							|| ImportRevision.normalizeEngine(Std.string(engine)) == excludedEngine)) {
							pathKey = "";
							break;
						}
					}
					if (pathKey == "") continue;
				}
				songs.push(song);
			}
			result.songs = songs;
		}
		return result;
	}

	static function hasMapEntries(values:Map<String, Bool>):Bool {
		if (values == null) return false;
		for (_ in values.keys()) return true;
		return false;
	}

	public static function refreshNow(install:String, record:Dynamic,
		convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void):SongImportBatchResult {
		var token:String;
		var owner = "retained-import:" + Std.string(record.id);
		ImportWorkScheduler.cooperate();
		var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
		ImportWorkScheduler.cooperate();
		var roots = expandDependentOwnerRoots(committedRoots);
		mutex.acquire();
		token = nextReservationTokenLocked("refresh-now");
		var reservation = reserveLocked(token, owner, roots, null, false);
		setReservationCommittedRootsLocked(reservation, committedRoots);
		var dependencies:Dynamic = Reflect.field(record, "runtimeDependencyOwners");
		if (dependencies != null && Std.isOfType(dependencies, Array))
			setReservationDependenciesLocked(reservation, cast dependencies);
		setCommittedRootsLocked(roots);
		mutex.release();
		try {
			var result = regenerate(install,record,convert,cancel,progress,token);
			mutex.acquire();
			queueHandoffLocked(token, result.importedSongs);
			mutex.release();
			return result;
		} catch (error:Dynamic) {
			settleFailedReservation(token, install);
			mutex.acquire(); recordDiagnosticLocked(Std.string(error)); mutex.release();
			throw error;
		}
	}

	public static function cachedRecords(install:String):Array<Dynamic> {
		var cache = Path.join([install,CACHE_ROOT]);
		var records = Path.join([cache,"records"]);
		var result:Array<Dynamic> = [];
		if (!FileSystem.exists(records)) return result;
		for (name in FileSystem.readDirectory(records)) {
			ImportWorkScheduler.cooperate();
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
		cancel:Void->Bool, progress:Dynamic->Void, reservationToken:String):SongImportBatchResult {
		var cache = Path.join([install,CACHE_ROOT]);
		var owner = "retained-import:" + Std.string(record.id);
		var state = Path.join([cache,"state"]);
		cooperateImportWork(cancel);
		var previous:Dynamic = committedManifest(state,owner);
		var oldMetadata:Dynamic = previous == null ? null : Reflect.field(previous,"revision");
		var masked:Array<String> = [];
		var maskedPaths:Map<String, Bool> = new Map();
		if (previous != null) {
			var files:Array<Dynamic> = cast Reflect.field(previous,"files");
			if (files == null || Reflect.field(previous,"owner") != owner) throw "Invalid import ownership manifest.";
			for (file in files) {
				cooperateImportWork(cancel);
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
		var io = ImportIO.begin(install,stage,masked,true,cancel);
		var retainedEngines:Map<String, String> = new Map();
		var retainedRoots:Map<String, String> = new Map();
		for (root in (cast record.roots:Array<Dynamic>)) {
			ImportWorkScheduler.cooperate();
			var rootPath = Std.string(root.relative) == "" ? source : Path.join([source,Std.string(root.relative)]);
			retainedEngines.set(rootPath,Std.string(root.engine));
			retainedRoots.set(rootPath,Std.string(root.engine));
		}
		var previousEngines = ImportRootScanner.setRetainedSourceEngines(retainedEngines);
		var previousRoots = ImportRootScanner.setRetainedSourceRoots(retainedRoots);
		var ended = false;
		try {
			var registrySeeds:Map<String,String> = new Map();
			var registryRegeneration:Map<String,Bool> = new Map();
			var names:Map<String,String> = new Map();
		for (root in (cast record.roots:Array<Dynamic>)) {
			cooperateImportWork(cancel);
			var path = Path.join([source,Std.string(root.relative)]);
			io.setNamespace(path,Std.string(root.engine),Std.string(root.namespace));
			io.setSourceLabel(path,Std.string(root.label));
			if (root.name != null) names.set(ImportPackageNamePrompt.rootKey(path),Std.string(root.name));
		}
		cooperateImportWork(cancel);
		var reusableFamilyNamespaces = ImportPackageFamilyCatalog.reusableNamespaces(install, previous, Path.directory(source), record);
		for (sourceRelative in reusableFamilyNamespaces.keys()) {
			cooperateImportWork(cancel);
			io.setNamespace(Path.join([source, sourceRelative]), ImportEngine.NIGHTMARE_VISION,
				reusableFamilyNamespaces.get(sourceRelative));
		}
		var priorCatalogValue:Dynamic = Reflect.field(record, "packageFamilyCatalog");
		if (priorCatalogValue != null) {
			cooperateImportWork(cancel);
			var priorCatalog = ImportRefreshTransaction.validatePackageFamilyCatalog(priorCatalogValue, record);
			if (priorCatalog != null && priorCatalog.version >= 2)
				for (member in priorCatalog.members) {
					cooperateImportWork(cancel);
					io.setNamespace(Path.join([source, member.sourceRelative]),
						ImportEngine.NIGHTMARE_VISION, member.namespace);
				}
		}
			// Registry baselines describe this import's contribution, not a claim
			// on every entry in a shared registry. Undo that contribution in staging
			// before converting again, then preserve unrelated installed entries.
			var registries:Array<Dynamic> = oldMetadata == null ? [] : cast oldMetadata.registries;
			if (registries == null) registries = [];
			var registryIndex = 0;
			for (registry in registries) {
				progress({phase:"reconciling-import-registries", current:Std.string(registry.path),
					completed:registryIndex, total:registries.length});
				cooperateImportWork(cancel);
				var path = Std.string(registry.path);
				var live = Path.join([install,path]);
				if (!FileSystem.exists(live)) throw "Local registry deletion preserved: " + path;
				cooperateImportWork(cancel);
				var current = File.getContent(live);
				cooperateImportWork(cancel);
				var prepared = ImportRegistryRefresh.prepare(Std.string(registry.before),Std.string(registry.generated),current);
				if (prepared.conflicts.length > 0) {
					// Calculate fresh output privately before deciding whether these
					// values are already applied or are divergent user edits.
					cooperateImportWork(cancel);
					prepared = ImportRegistryRefresh.regenerationSeed(Std.string(registry.before),
						Std.string(registry.generated),current);
					if (prepared.conflicts.length > 0) throw "Local registry edits preserved: " + path + " " + prepared.conflicts.join(", ");
					registryRegeneration.set(path,true);
				}
				registrySeeds.set(path,prepared.text);
				ImportFile.saveContent(path,prepared.text);
				registryIndex++;
			}
			ImportSongOwnership.invalidateOwnerIdentityIndex();
			progress({phase:"scanning-retained-source", current:source, completed:0, total:0});
			cooperateImportWork(cancel);
			var scan = ImportWorkflow.scanNow(source,Std.string(record.type));
			if (scan == null || scan.rootScanTruncated == true || scan.packageScanTruncated == true)
				throw "Import rescan was incomplete; installed content is unchanged.";
			for (field in ["rootScanDiagnostics","packageScanDiagnostics"]) {
				cooperateImportWork(cancel);
				var diagnostics:Array<Dynamic> = cast Reflect.field(scan,field);
				if (diagnostics != null) for (diagnostic in diagnostics) {
					cooperateImportWork(cancel);
					if (Std.string(diagnostic.severity).toLowerCase() == "error")
						throw "Import rescan was incomplete; installed content is unchanged. " + Std.string(diagnostic.message);
				}
			}
			if (previous != null && scan.errors != null && scan.errors.length > 0)
				throw "Import refresh scan needs attention; installed content is unchanged. " + scan.errors.join("\n");
			for (expected in (cast record.roots:Array<Dynamic>)) {
				cooperateImportWork(cancel);
				var expectedPath = Path.normalize(FileSystem.fullPath(Path.join([source,Std.string(expected.relative)])));
				var found = false;
				if (scan.detectedRoots != null) for (root in scan.detectedRoots) {
					cooperateImportWork(cancel);
					if (ImportRevision.normalizeEngine(root.engine) == ImportRevision.normalizeEngine(Std.string(expected.engine))
						&& Path.normalize(FileSystem.fullPath(root.root)) == expectedPath) found = true;
				}
				if (!found) throw "Import rescan lost a previously detected source root; installed content is unchanged.";
			}
			cooperateImportWork(cancel);
			var buildContexts = recordedSourceBuildContexts(record);
			Reflect.setField(record, "sourceAssetProfiles",
				resolveSourceAssetProfiles(source, record, io, buildContexts, cancel));
			cooperateImportWork(cancel);
			var runtimeOwnerRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
			var runtimeDependencies = dependencyOwnerRootsForScan(scan, install, runtimeOwnerRoots);
			record.runtimeDependencyOwners = runtimeDependencies;
			cooperateImportWork(cancel);
			mutex.acquire();
			var dependencyReservation = reservations.get(reservationToken);
			if (dependencyReservation != null)
				setReservationDependenciesLocked(dependencyReservation, runtimeDependencies);
			mutex.release();
			setReservationCandidates(reservationToken, owner, ownerRootsForRecord(record),
				candidatesForScan(scan, sourceRootDescriptors(source, cast record.roots)));
			if (cancel()) throw "Import cancelled before conversion.";
			progress({phase:"converting-import", current:Std.string(record.label), completed:0, total:0});
			var imported = convert(source,scan,names);
			if (imported == null || imported.failed > 0 || cancel())
				throw "Import conversion did not complete; installed content is unchanged. "
					+ (imported == null || imported.errors == null ? "" : imported.errors.join("\n"));
			var familySourceRoots = ImportPackageFamilyCatalog.sourceRoots(Path.directory(source), record);
			if (familySourceRoots.length > 0) {
				cooperateImportWork(cancel);
				var familyPublication = ModuleFunctions.publishNightmareVisionFamilyMemberRoots(
					familySourceRoots, Path.directory(source), record);
				if (familyPublication.failed > 0 || cancel())
					throw "Nightmare Vision package-family publication did not complete; installed content is unchanged. "
						+ (familyPublication.errors == null ? "" : familyPublication.errors.join("\n"));
			}
			cooperateImportWork(cancel);
			var familyCatalog = ImportPackageFamilyCatalog.capturePublished(Path.directory(source), record, io);
			if (familyCatalog != null) Reflect.setField(record, "packageFamilyCatalog", familyCatalog);
			var outputs:Array<ImportRefreshStagedOutput> = [];
			var baselines:Array<ImportRefreshManifestFile> = [];
			var nextRegistries:Array<Dynamic> = [];
			var written = io.writtenPaths();
			var checkedOutputs = 0;
			progress({phase:"preparing-output", current:"", completed:0, total:written.length});
			for (path in written) {
				cooperateImportWork(cancel);
				if (!StringTools.startsWith(path,"assets/")) continue;
				var staged = Path.join([stage,path]);
				if (!FileSystem.exists(staged) || FileSystem.isDirectory(staged)) continue;
				cooperateImportWork(cancel);
				var before = isRegistry(path) || !maskedPaths.exists(path) ? io.before(path) : null;
				if (isRegistry(path)) {
					var live = Path.join([install,path]);
					cooperateImportWork(cancel);
					var current = FileSystem.exists(live) ? File.getContent(live) : "{}";
					cooperateImportWork(cancel);
					var generated = File.getContent(staged);
					// Staging's registry seed is the base with this import removed.
					var seed = registrySeeds.exists(path) ? registrySeeds.get(path)
						: before == null || before.text == null ? "{}" : before.text;
					var liveBase = current;
					var previousRegistry:Dynamic = null;
					var reconcileGenerated = registryRegeneration.exists(path);
					for (r in registries) {
						cooperateImportWork(cancel);
						if (Std.string(r.path) != path) continue;
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
				// The transaction hashes the generated bytes during its output
				// validation pass. Avoid reading every staged asset a second time here.
				outputs.push({path:path,stagedPath:path});
				progress({phase:"preparing-output", current:path, completed:++checkedOutputs, total:written.length});
			}
			ImportIO.end(); ended = true;
			ImportRootScanner.setRetainedSourceEngines(previousEngines);
			ImportRootScanner.setRetainedSourceRoots(previousRoots);
				if (scan.detectedEngines != null) for (engine in scan.detectedEngines)
					if (ImportRevision.normalizeEngine(engine) != "" && (cast record.engines:Array<String>).indexOf(engine) < 0) {
						ImportWorkScheduler.cooperate();
						(cast record.engines:Array<String>).push(engine);
					}
			record.dependencyDiagnostics = dependencyDiagnostics(scan);
			record.scanDiagnostics = scan.errors;
			var nextRevisions:Array<Dynamic> = [];
			for (engine in (cast record.engines:Array<String>)) {
				ImportWorkScheduler.cooperate();
				nextRevisions.push(ImportRevision.current(engine,EngineBranding.version()));
			}
			record.revisions = nextRevisions;
			var metadata:Dynamic = {importRecord:record,registries:nextRegistries};
			progress({phase:"publishing-import",current:Std.string(record.label),completed:0,total:1});
			var publishedPaths = masked.copy();
			for (output in outputs) {
				cooperateImportWork(cancel);
				if (publishedPaths.indexOf(output.path) < 0) publishedPaths.push(output.path);
			}
			setReservationPaths(reservationToken, publishedPaths);
			var applied = ImportRefreshTransaction.apply(install,stage,state,owner,["assets"],outputs,metadata,cancel,baselines,progress);
			if (applied.status != ImportRefreshTransaction.STATUS_APPLIED)
				throw "Import refresh " + applied.status + ": " + [for (c in applied.conflicts) c.path + " (" + c.reason + ")"].join(", ");
			ImportWorkScheduler.cooperate();
			var committed = committedManifest(state, owner);
			var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
			addCommittedPathOwners(committed, committedRoots);
			ImportWorkScheduler.cooperate();
			addRecordDependencyEdges(record, committedRoots);
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
			ImportRootScanner.setRetainedSourceRoots(previousRoots);
			ImportSongOwnership.invalidateOwnerIdentityIndex();
			try deleteStage(stage) catch (cleanup:Dynamic)
				trace("[import-refresh-cleanup-error] " + Std.string(cleanup));
			throw error;
		}
	}

	/** Only browsing states call this. While refreshing, they gate actions which
	 * could enter gameplay/editors or start a competing importer. */
	public static function browseTick():ImportRefreshBrowseStatus {
		ensureQueueInspection();
		mutex.acquire();
		var shouldStart = !active && !inspectionPending && queue.length > 0;
		mutex.release();
		if (shouldStart) startNext();
		performPendingHandoffs();
		mutex.acquire();
		var handoffWaiting = pendingHandoffs.length > 0;
		var queueWaiting = queue.length > 0;
		var value:ImportRefreshBrowseStatus = {busy:active || queueWaiting || handoffWaiting,
			backgroundBusy:status.busy || queueWaiting || handoffWaiting,label:status.label,fraction:status.fraction,
			complete:status.complete,changed:status.changed,blocked:status.blocked};
		if (measurements != null) {
			var measured = measurements.snapshot(ImportWorkScheduler.workStamp(), queue.length);
			for (field in Reflect.fields(measured)) Reflect.setField(value, field, Reflect.field(measured, field));
		}
		mutex.release();
		return value;
	}

	static function markUnavailableOwnerRecord(records:Map<String,Dynamic>, token:String,
		roots:Array<String>, paths:Array<String>):Void {
		if (records == null || token == null || token == "") return;
		var current:Dynamic = records.get(token);
		var nextRoots:Array<String> = current == null ? [] : cast Reflect.field(current, "roots");
		var nextPaths:Array<String> = current == null ? [] : cast Reflect.field(current, "paths");
		if (nextRoots == null) nextRoots = [];
		if (nextPaths == null) nextPaths = [];
		if (roots != null) for (value in roots) {
			var root = normalizeOwnerRoot(value);
			if (root != "" && nextRoots.indexOf(root) < 0) nextRoots.push(root);
		}
		if (paths != null) for (value in paths) {
			var path = normalizeInstallRelative(value);
			if (path != "" && nextPaths.indexOf(path) < 0) nextPaths.push(path);
		}
		nextRoots.sort(Reflect.compare);
		nextPaths.sort(Reflect.compare);
		records.set(token, {token:token, roots:nextRoots, paths:nextPaths});
	}

	/** A recheck may discover that a recovery journal is now resolved. Retire
	 * only reservations for that exact transaction; an outdated record keeps a
	 * normal owner reservation while its queued regeneration runs. */
	static function clearResolvedRecoveryReservations(transactionOwner:String, refreshToken:String,
		roots:Array<String>, committedRoots:Array<String>, dependencies:Array<String>,
		keepRefreshReservation:Bool):Void {
		mutex.acquire();
		var tokens = [for (token in reservations.keys()) token];
		for (token in tokens) {
			var reservation = reservations.get(token);
			if (reservation == null || !reservation.recoveryBlocked
				|| reservation.transactionOwner != transactionOwner) continue;
			if (keepRefreshReservation && token == refreshToken) {
				reservation.roots = roots == null ? [] : roots.copy();
				reservation.roots.sort(Reflect.compare);
				setReservationCommittedRootsLocked(reservation, committedRoots);
				setReservationDependenciesLocked(reservation, dependencies);
				reservation.touchedPaths = [];
				reservation.recoveryBlocked = false;
				reservation.committed = false;
				reservation.handoffPending = false;
				reservation.handoffNames = [];
				bumpAvailabilityLocked();
			} else {
				releaseReservationLocked(token);
			}
		}
		mutex.release();
	}

	/** An absent or empty receipt directory cannot prove that a prior package's
	 * owner-scoped uncertainty was repaired. Keep the last authoritative view
	 * until a non-empty receipt pass can replace it. */
	static function preservedQueueInspection():ImportRefreshQueueInspectionResult {
		ImportWorkScheduler.cooperate();
		mutex.acquire();
		var roots = [for (root in committedOwnerRoots.keys()) root];
		roots.sort(Reflect.compare);
		var tokens:Map<String,Bool> = new Map();
		for (token in scopedUnavailableOwnersByToken.keys()) tokens.set(token, true);
		for (token in scopedUnavailablePathsByToken.keys()) tokens.set(token, true);
		var tokenNames = [for (token in tokens.keys()) token];
		tokenNames.sort(Reflect.compare);
		var unavailable:Array<Dynamic> = [];
		for (token in tokenNames) {
			var ownerRoots = scopedUnavailableOwnersByToken.get(token);
			var paths = scopedUnavailablePathsByToken.get(token);
			unavailable.push({token:token,
				roots:ownerRoots == null ? [] : ownerRoots.copy(),
				paths:paths == null ? [] : paths.copy()});
		}
		var unresolved = unresolvedRecovery || inspectionSawUnresolvedRecovery;
		mutex.release();
		return {committedRoots:roots, unavailableOwners:unavailable,
			unresolvedRecovery:unresolved};
	}

	static function loadQueue(install:String):ImportRefreshQueueInspectionResult {
		ImportWorkScheduler.cooperate();
		var cache = Path.join([install,CACHE_ROOT]);
		var records = Path.join([cache,"records"]);
		if (!FileSystem.exists(records))
			return preservedQueueInspection();
		var recordNames:Array<String> = [];
		for (name in FileSystem.readDirectory(records)) {
			ImportWorkScheduler.cooperate();
			if (~/^[a-f0-9]{64}\.json$/.match(name)) recordNames.push(name);
		}
		recordNames.sort(Reflect.compare);
		// An empty receipt directory cannot prove that any prior owner-scoped or
		// ownerless uncertainty was repaired. It is not an authoritative pass.
		if (recordNames.length == 0)
			return preservedQueueInspection();
		var completed = 0;
		var protectedRecords:Map<String,Dynamic> = new Map();
		var dependencyOwnersByToken:Map<String,Array<String>> = new Map();
		var unavailableOwners:Map<String,Bool> = new Map();
		var unavailableOwnersByToken:Map<String,Dynamic> = new Map();
		var unknownRecoveryTokens:Array<String> = [];
		var stagedCommittedRoots:Map<String,Bool> = new Map();
		for (name in recordNames) {
			ImportWorkScheduler.cooperate();
			mutex.acquire();
			measurements.update({phase:"checking-import-receipts",current:name,completed:completed,total:recordNames.length},ImportWorkScheduler.workStamp());
			mutex.release();
			var id = name.substr(0,64);
			var owner = "retained-import:" + id;
			var priorManifest:Dynamic = null;
			var priorRecord:Dynamic = null;
			var recoveryPaths:Array<String> = [];
			try {
				ImportWorkScheduler.cooperate();
				priorManifest = committedManifest(Path.join([cache,"state"]),owner);
				if (priorManifest != null && priorManifest.owner == owner && priorManifest.revision != null) {
					priorRecord = Reflect.field(priorManifest.revision,"importRecord");
				}
				ImportWorkScheduler.cooperate();
				var conflicts = ImportRefreshTransaction.recover(install,Path.join([cache,"state"]),owner);
				if (conflicts.length > 0) {
					ImportWorkScheduler.cooperate();
					recoveryPaths = ImportRefreshTransaction.recoveryTargetPaths(install,Path.join([cache,"state"]),owner);
					if (priorRecord != null && priorRecord.id == id && priorRecord.schemaVersion == 1) {
						var recoveryRoots = familyOwnerRootsForRecord(priorRecord, ownerRootsForRecord(priorRecord));
						ImportWorkScheduler.cooperate();
						var recoveryDependencies = runtimeDependencyMetadata(install, priorManifest, priorRecord, recoveryRoots);
						dependencyOwnersByToken.set("refresh:" + id, recoveryDependencies.owners);
						addRecordDependencyEdges(priorRecord, recoveryRoots, recoveryDependencies.owners);
						if (!recoveryDependencies.complete) {
							for (root in recoveryRoots) unavailableOwners.set(root, true);
							markUnavailableOwnerRecord(unavailableOwnersByToken,
								"refresh:" + id, recoveryRoots, recoveryDependencies.touchedPaths);
						}
						reserveRecoveryBlock("refresh:" + id, owner, priorRecord, priorManifest,
							recoveryPaths, stagedCommittedRoots);
						protectedRecords.set("refresh:" + id, priorRecord);
					} else {
						reserveUnknownRecoveryBlock("refresh:" + id, owner, recoveryPaths);
						if (unknownRecoveryTokens.indexOf("refresh:" + id) < 0) unknownRecoveryTokens.push("refresh:" + id);
					}
					throw "Interrupted refresh needs attention; installed edits were preserved.";
				}
				ImportWorkScheduler.cooperate();
				var manifest = committedManifest(Path.join([cache,"state"]),owner);
				if (manifest == null || manifest.owner != owner || manifest.revision == null) continue;
				var record:Dynamic = manifest.revision.importRecord;
				if (record == null || record.id != id || record.schemaVersion != 1) continue;
				priorRecord = record;
				var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
				ImportWorkScheduler.cooperate();
				var dependencyMetadata = runtimeDependencyMetadata(install, manifest, record, committedRoots);
				dependencyOwnersByToken.set("refresh:" + id, dependencyMetadata.owners);
				addRecordDependencyEdges(record, committedRoots, dependencyMetadata.owners);
				if (!dependencyMetadata.complete) {
					for (root in committedRoots) unavailableOwners.set(root, true);
					markUnavailableOwnerRecord(unavailableOwnersByToken,
						"refresh:" + id, committedRoots, dependencyMetadata.touchedPaths);
					mutex.acquire();
					recordDiagnosticLocked("A retained import has invalid or incomplete song provenance; its package remains unavailable until it is reimported.");
					mutex.release();
				}
				stageCommittedRoots(stagedCommittedRoots, committedRoots);
				addCommittedPathOwners(manifest, committedRoots);
				var stale = false;
				for (stamp in (cast record.revisions:Array<Dynamic>)) {
					ImportWorkScheduler.cooperate();
					var assessment = ImportRevision.assess(stamp,Std.string(stamp.sourceEngine));
					if (assessment.status == ImportRevision.FUTURE || assessment.status == ImportRevision.UNKNOWN)
						throw "Import receipt is newer or unrecognized; its files were preserved.";
					if (assessment.status == ImportRevision.OUTDATED) stale = true;
				}
				var refreshToken = "refresh:" + id;
				ImportWorkScheduler.cooperate();
				var refreshRoots = expandDependentOwnerRoots(committedRoots);
				ImportWorkScheduler.cooperate();
				clearResolvedRecoveryReservations(owner, refreshToken, refreshRoots,
					committedRoots, dependencyMetadata.owners, stale);
				if (stale) {
					protectedRecords.set("refresh:" + id, record);
					mutex.acquire();
				var reservation = reserveLocked(refreshToken, owner, refreshRoots, null, false);
				setReservationCommittedRootsLocked(reservation, committedRoots);
				setReservationDependenciesLocked(reservation, dependencyMetadata.owners);
				queue.push(record);
				bumpAvailabilityLocked();
				mutex.release();
				}
			} catch (error:Dynamic) {
				trace("[import-refresh-error] " + Std.string(error));
				if (priorRecord != null && priorRecord.id == id && priorRecord.schemaVersion == 1) {
					if (recoveryPaths.length == 0) try {
						ImportWorkScheduler.cooperate();
						recoveryPaths = ImportRefreshTransaction.recoveryTargetPaths(install,Path.join([cache,"state"]),owner);
					} catch (_:Dynamic) {}
					if (!dependencyOwnersByToken.exists("refresh:" + id)) {
						var recoveryRoots = familyOwnerRootsForRecord(priorRecord, ownerRootsForRecord(priorRecord));
						ImportWorkScheduler.cooperate();
						var recoveryDependencies = runtimeDependencyMetadata(install, priorManifest, priorRecord, recoveryRoots);
						dependencyOwnersByToken.set("refresh:" + id, recoveryDependencies.owners);
						addRecordDependencyEdges(priorRecord, recoveryRoots, recoveryDependencies.owners);
						if (!recoveryDependencies.complete) {
							for (root in recoveryRoots) unavailableOwners.set(root, true);
							markUnavailableOwnerRecord(unavailableOwnersByToken,
								"refresh:" + id, recoveryRoots, recoveryDependencies.touchedPaths);
						}
					}
					reserveRecoveryBlock("refresh:" + id, owner, priorRecord, priorManifest,
						recoveryPaths, stagedCommittedRoots);
					protectedRecords.set("refresh:" + id, priorRecord);
				} else {
					if (recoveryPaths.length == 0) try {
						ImportWorkScheduler.cooperate();
						recoveryPaths = ImportRefreshTransaction.recoveryTargetPaths(install,Path.join([cache,"state"]),owner);
					} catch (_:Dynamic) {}
					if (recoveryPaths.length > 0) {
						reserveUnknownRecoveryBlock("refresh:" + id, owner, recoveryPaths);
						if (unknownRecoveryTokens.indexOf("refresh:" + id) < 0) unknownRecoveryTokens.push("refresh:" + id);
					}
					else markUnresolvedRecovery("Import receipt or recovery metadata could not identify a safe owner.");
				}
				mutex.acquire(); recordDiagnosticLocked(Std.string(error)); mutex.release();
			}
			completed++;
		}
		// All provider-to-dependent edges are known now. Reserve complete closures
		// before startup inspection finishes or any queued refresh can be selected.
		var protectedTokens = [for (token in protectedRecords.keys()) token];
		protectedTokens.sort(Reflect.compare);
		for (token in protectedTokens) {
			ImportWorkScheduler.cooperate();
			var record = protectedRecords.get(token);
			if (record == null) continue;
			var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
			stageCommittedRoots(stagedCommittedRoots, committedRoots);
			ImportWorkScheduler.cooperate();
			var roots = expandDependentOwnerRoots(committedRoots);
			var dependencies = dependencyOwnersByToken.get(token);
			mutex.acquire();
			var reservation = reserveLocked(token, "retained-import:" + Std.string(record.id), roots, null, false);
			setReservationCommittedRootsLocked(reservation, committedRoots);
			if (dependencies != null) setReservationDependenciesLocked(reservation,dependencies);
			bumpAvailabilityLocked();
			mutex.release();
		}
		unknownRecoveryTokens.sort(Reflect.compare);
		for (token in unknownRecoveryTokens) {
			ImportWorkScheduler.cooperate();
			mutex.acquire();
			var reservation = reservations.get(token);
			var seeds = reservation == null ? [] : reservation.roots.copy();
			var transactionOwner = reservation == null ? "" : reservation.transactionOwner;
			mutex.release();
			if (reservation == null || seeds.length == 0) continue;
			var roots = expandDependentOwnerRoots(seeds);
			mutex.acquire();
			reserveLocked(token, transactionOwner, roots, null, false);
			mutex.release();
		}
		mutex.acquire();
		measurements.update({phase:"checking-import-receipts",current:"",completed:recordNames.length,total:recordNames.length},ImportWorkScheduler.workStamp());
		mutex.release();
		for (root in unavailableOwners.keys()) stagedCommittedRoots.remove(root);
		var confirmedRoots = [for (root in stagedCommittedRoots.keys()) root];
		confirmedRoots.sort(Reflect.compare);
		var unavailableTokens = [for (token in unavailableOwnersByToken.keys()) token];
		unavailableTokens.sort(Reflect.compare);
		var unavailableRecords:Array<Dynamic> = [];
		for (token in unavailableTokens) {
			ImportWorkScheduler.cooperate();
			var value:Dynamic = unavailableOwnersByToken.get(token);
			if (value != null) unavailableRecords.push(value);
		}
		return {committedRoots:confirmedRoots, unavailableOwners:unavailableRecords,
			unresolvedRecovery:inspectionUnresolvedRecoveryFound()};
	}

	static function stageCommittedRoots(staged:Map<String,Bool>, roots:Array<String>):Void {
		if (staged == null || roots == null) return;
		for (root in roots) {
			ImportWorkScheduler.cooperate();
			var normalized = normalizeOwnerRoot(root);
			if (normalized != "") staged.set(normalized, true);
		}
	}

	static function reserveRecoveryBlock(token:String, owner:String, record:Dynamic, manifest:Dynamic,
		recoveryPaths:Array<String>, stagedCommittedRoots:Map<String,Bool>):Void {
		ImportWorkScheduler.cooperate();
		var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
		stageCommittedRoots(stagedCommittedRoots, committedRoots);
		var files:Dynamic = manifest == null ? null : Reflect.field(manifest,"files");
		var paths:Array<String> = [];
		if (files != null && Std.isOfType(files,Array)) for (file in (cast files:Array<Dynamic>)) {
			ImportWorkScheduler.cooperate();
			var path:Dynamic = file == null ? null : Reflect.field(file,"path");
			var normalized = path == null ? "" : normalizeInstallRelative(Std.string(path));
			if (normalized != "" && paths.indexOf(normalized) < 0) paths.push(normalized);
		}
		var extraRoots:Array<String> = [];
		if (recoveryPaths != null) for (rawPath in recoveryPaths) {
			ImportWorkScheduler.cooperate();
			var normalized = normalizeInstallRelative(rawPath);
			if (normalized != "" && paths.indexOf(normalized) < 0) paths.push(normalized);
			var pathOwner = ownerRootFromInstalledPath(normalized);
			if (pathOwner != "" && extraRoots.indexOf(pathOwner) < 0) extraRoots.push(pathOwner);
		}
		paths.sort(Reflect.compare);
		extraRoots.sort(Reflect.compare);
		mutex.acquire();
		var reservation = reserveLocked(token, owner, committedRoots, null, false);
		setReservationCommittedRootsLocked(reservation, committedRoots);
		reservation.recoveryBlocked = true;
		for (pathOwner in extraRoots) if (reservation.roots.indexOf(pathOwner) < 0) {
			reservation.roots.push(pathOwner);
			reservation.roots.sort(Reflect.compare);
		}
		if (reservation.touchedPaths.join("\n") != paths.join("\n")) {
			reservation.touchedPaths = paths;
			bumpAvailabilityLocked();
		}
		if (reservation.roots.length == 0) {
			var wasUnresolved = unresolvedRecovery;
			flagUnresolvedRecoveryLocked();
			if (!wasUnresolved) bumpAvailabilityLocked();
		}
		mutex.release();
	}

	static function reserveUnknownRecoveryBlock(token:String, owner:String, recoveryPaths:Array<String>):Void {
		var roots:Array<String> = [];
		var paths:Array<String> = [];
		if (recoveryPaths != null) for (rawPath in recoveryPaths) {
			ImportWorkScheduler.cooperate();
			var path = normalizeInstallRelative(rawPath);
			if (path == "") continue;
			if (paths.indexOf(path) < 0) paths.push(path);
			var pathOwner = ownerRootFromInstalledPath(path);
			if (pathOwner != "" && roots.indexOf(pathOwner) < 0) roots.push(pathOwner);
		}
		roots.sort(Reflect.compare); paths.sort(Reflect.compare);
		mutex.acquire();
		var reservation = reserveLocked(token, owner, roots, null, false);
		reservation.recoveryBlocked = true;
		reservation.touchedPaths = paths;
		if (roots.length == 0) flagUnresolvedRecoveryLocked();
		bumpAvailabilityLocked();
		mutex.release();
	}

	static function markUnresolvedRecovery(message:String):Void {
		mutex.acquire();
		flagUnresolvedRecoveryLocked();
		recordDiagnosticLocked(message);
		bumpAvailabilityLocked();
		mutex.release();
	}

	static function settleFailedReservation(token:String, install:String):Void {
		mutex.acquire();
		var reservation = reservations.get(token);
		var owner = reservation == null ? "" : reservation.transactionOwner;
		mutex.release();
		var conflicts:Array<Dynamic> = [];
		if (owner != "") try conflicts = ImportRefreshTransaction.recover(install,
			Path.join([install,CACHE_ROOT,"state"]),owner) catch (error:Dynamic) {
			conflicts = [{path:owner,reason:Std.string(error)}];
		}
		mutex.acquire();
		reservation = reservations.get(token);
		if (reservation != null) {
			if (conflicts.length > 0) {
				reservation.recoveryBlocked = true;
				var paths:Array<String> = [];
				for (conflict in conflicts) {
					var path:Dynamic = Reflect.field(conflict,"path");
					var normalized = path == null ? "" : normalizeInstallRelative(Std.string(path));
					if (normalized != "" && paths.indexOf(normalized) < 0) paths.push(normalized);
				}
				paths.sort(Reflect.compare);
				reservation.touchedPaths = paths;
				bumpAvailabilityLocked();
			} else releaseReservationLocked(token);
		}
		mutex.release();
	}

	static function startNext():Void {
		mutex.acquire();
		if (active || inspectionPending || queue.length == 0) { mutex.release(); return; }
		var record = queue.shift();
		var token = "refresh:" + Std.string(record.id);
		var owner = "retained-import:" + Std.string(record.id);
		reserveLocked(token, owner, ownerRootsForRecord(record), null, false);
		trace("[import-refresh-start] " + Std.string(record.label));
		active = true;
		status.busy = true; status.complete = false; status.changed = false; status.fraction = 0;
		status.label = "Refreshing import: " + Std.string(record.label);
		measurements = new ImportRefreshProgress(ImportWorkScheduler.workStamp());
		var install = Sys.getCwd();
		mutex.release();
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
				measurements.update(payload, ImportWorkScheduler.workStamp());
				status.fraction = measurements.total <= 0 ? 0
					: Math.min(1, measurements.completed / measurements.total);
				mutex.release();
			};
			ModuleFunctions.setImportProgressCallback(onProgress);
			try {
				var result = regenerate(install,record,ImportWorkflow.convertRetainedSource,function() return false,onProgress,token);
				mutex.acquire();
				queueHandoffLocked(token, result.importedSongs);
				trace("[import-refresh-complete] " + Std.string(record.label));
				status.changed = true; status.label = "Imports refreshed."; status.fraction = 1; status.complete = true;
				mutex.release();
			} catch (error:Dynamic) {
				trace("[import-refresh-error] " + Std.string(record.label) + ": " + Std.string(error));
				settleFailedReservation(token, install);
				mutex.acquire(); recordDiagnosticLocked(Std.string(error)); mutex.release();
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
		ImportWorkScheduler.cooperate();
		if (!FileSystem.exists(ImportRefreshTransaction.manifestPath(state,owner))) return null;
		return ImportRefreshTransaction.loadManifest(state,owner);
	}

	static function cooperateImportWork(cancel:Null<Void->Bool>):Void {
		if (cancel != null && cancel()) throw "Import cancelled at a safe work checkpoint.";
		if (!ImportWorkScheduler.cooperate(function() return cancel != null && cancel()))
			throw "Import cancelled at a safe work checkpoint.";
		if (cancel != null && cancel()) throw "Import cancelled at a safe work checkpoint.";
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
			// Cleanup is required once publication has committed, so this checkpoint
			// deliberately has no cancellation callback. Import workers wait here
			// during gameplay; the foreground caller never blocks in cooperate().
			ImportWorkScheduler.cooperate();
			var current = stack.pop(); directories.push(current);
			var entries = FileSystem.readDirectory(current);
			if (entries == null) throw "Could not enumerate import staging directory: " + current;
			for (name in entries) {
				ImportWorkScheduler.cooperate();
				var child = Path.join([current,name]);
				if (relativeTo(FileSystem.fullPath(child),root) == null) continue;
				if (FileSystem.isDirectory(child)) stack.push(child); else {
					ImportWorkScheduler.cooperate();
					FileSystem.deleteFile(child);
				}
			}
		}
		directories.reverse(); for (directory in directories) {
			ImportWorkScheduler.cooperate();
			try FileSystem.deleteDirectory(directory) catch (error:Dynamic)
				throw "Could not remove import staging directory " + directory + ": " + Std.string(error);
		}
	}
}
#end
