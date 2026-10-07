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
	static var dependentRootsByOwner:Map<String, Array<String>> = new Map();
	static var familyOwnerRootCache:Map<String, Array<String>> = new Map();
	static var unresolvedRecovery:Bool = false;
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
			committedPathsByOwner.set(root, []);
		}
		for (entry in (cast files:Array<Dynamic>)) {
			var path:Dynamic = Reflect.field(entry, "path");
			if (path == null) continue;
			var relative = normalizeInstallRelative(Std.string(path));
			if (relative == "" || isRegistry(relative)) continue;
			var key = ownerPathKey(relative);
			var known = committedPathOwners.get(key);
			if (known == null) known = [];
			for (root in ownerRoots) {
				if (known.indexOf(root) < 0) known.push(root);
				var paths = committedPathsByOwner.get(root);
				if (paths == null) paths = [];
				if (paths.indexOf(relative) < 0) paths.push(relative);
				committedPathsByOwner.set(root, paths);
			}
			known.sort(Reflect.compare);
			committedPathOwners.set(key, known);
		}
		mutex.release();
	}

	static function addRecordDependencyEdges(record:Dynamic, ownerRoots:Array<String>, ?dependencyOwners:Array<String>):Void {
		var raw:Dynamic = dependencyOwners == null
			? (record == null ? null : Reflect.field(record, "runtimeDependencyOwners")) : dependencyOwners;
		if (raw == null || !Std.isOfType(raw, Array) || ownerRoots == null) return;
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
		var rawDependencies:Dynamic = Reflect.field(record, "runtimeDependencyOwners");
		if (rawDependencies != null) {
			var complete = Std.isOfType(rawDependencies, Array);
			if (complete) for (raw in (cast rawDependencies:Array<Dynamic>)) {
				var normalized = raw == null ? "" : normalizeOwnerRoot(Std.string(raw));
				if (normalized == "") complete = false;
				else if (owners.indexOf(normalized) < 0) owners.push(normalized);
			}
			owners.sort(Reflect.compare);
			return {owners:owners, complete:complete};
		}

		var complete = true;
		var fileCount = 0;
		var byteCount = 0;
		var rawFiles:Dynamic = manifest == null ? null : Reflect.field(manifest, "files");
		if (rawFiles == null || !Std.isOfType(rawFiles, Array))
			return {owners:owners, complete:false};
		for (entry in (cast rawFiles:Array<Dynamic>)) {
			var pathValue:Dynamic = entry == null ? null : Reflect.field(entry, "path");
			var path = pathValue == null ? "" : normalizeInstallRelative(Std.string(pathValue));
			if (!isSongCompatManifestPath(path)) continue;
			fileCount++;
			if (fileCount > MAX_COMPAT_MANIFESTS_PER_RECORD) {
				complete = false;
				break;
			}
			try {
				var absolute = Path.join([install, path]);
				if (!FileSystem.exists(absolute) || FileSystem.isDirectory(absolute)) {
					complete = false;
					continue;
				}
				var resolvedInstall = StringTools.replace(Path.normalize(FileSystem.fullPath(install)), "\\", "/");
				var resolvedFile = StringTools.replace(Path.normalize(FileSystem.fullPath(absolute)), "\\", "/");
				var resolvedRelative = relativeTo(resolvedFile, resolvedInstall);
				if (resolvedRelative == null || ownerPathKey(resolvedRelative) != ownerPathKey(path)) {
					complete = false;
					continue;
				}
				var stat = FileSystem.stat(absolute);
				if (stat.size < 0 || stat.size > MAX_COMPAT_MANIFEST_BYTES
					|| byteCount + stat.size > MAX_COMPAT_METADATA_BYTES_PER_RECORD) {
					complete = false;
					continue;
				}
				var bytes = File.getBytes(absolute);
				if (bytes.length != stat.size) {
					complete = false;
					continue;
				}
				byteCount += bytes.length;
				var expectedHash:Dynamic = Reflect.field(entry, "sha256");
				if (expectedHash == null || Sha256.make(bytes).toHex() != Std.string(expectedHash).toLowerCase()) {
					complete = false;
					continue;
				}
				var data = CompatScriptManifest.parse(bytes.toString());
				var selectedOwner = normalizeOwnerRoot(CompatScriptManifest.selectedRoot(data));
				if (selectedOwner == "" || ownerRoots.indexOf(selectedOwner) < 0) {
					complete = false;
					continue;
				}
				if (data.roots != null) for (root in data.roots) {
					if (root == null || root.dependency != true) continue;
					var dependency = normalizeOwnerRoot(root.path);
					if (dependency == "") {
						complete = false;
						continue;
					}
					if (owners.indexOf(dependency) < 0) owners.push(dependency);
				}
			} catch (_:Dynamic) {
				complete = false;
			}
		}
		owners.sort(Reflect.compare);
		return {owners:owners, complete:complete};
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
			var normalized = normalizeOwnerRoot(root);
			if (normalized != "" && result.indexOf(normalized) < 0) result.push(normalized);
		}
		var index = 0;
		var overflow = result.length > 512;
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
			unresolvedRecovery = true;
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
			var rawDependencies:Dynamic = Reflect.field(song, "dependencies");
			if (rawDependencies == null || !Std.isOfType(rawDependencies, Array)) continue;
			for (dependency in (cast rawDependencies:Array<Dynamic>)) {
				if (Reflect.field(dependency, "found") != true) continue;
				var searched:Dynamic = Reflect.field(dependency, "searched");
				if (searched == null || !Std.isOfType(searched, Array)) continue;
				for (candidate in (cast searched:Array<Dynamic>)) {
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
			"CodenameImportedModsState", "CategoryState", "RuntimeImportSmokeState"])
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
		var shouldStart = checked && inspectionPending && !inspectionRunning && !active;
		if (shouldStart) {
			inspectionRunning = true;
			active = true;
			status.busy = true;
			status.label = "Checking saved imports";
			measurements = new ImportRefreshProgress(haxe.Timer.stamp());
		}
		mutex.release();
		if (!shouldStart) return;
		var install = Sys.getCwd();
		Thread.create(function() {
			var stagedCommittedRoots:Array<String> = [];
			var inspectionSucceeded = false;
			try {
				stagedCommittedRoots = loadQueue(install);
				inspectionSucceeded = true;
			} catch (error:Dynamic) {
				mutex.acquire();
				recordDiagnosticLocked(Std.string(error));
				mutex.release();
			}
			finishQueueInspection(stagedCommittedRoots, inspectionSucceeded);
		});
	}

	/** Publish receipt-backed owners atomically with the end of the initial
	 * receipt/recovery pass. A failed pass must not expose a partial inventory. */
	static function finishQueueInspection(stagedCommittedRoots:Array<String>, succeeded:Bool):Void {
		mutex.acquire();
		if (succeeded) {
			setCommittedRootsLocked(stagedCommittedRoots);
		} else {
			unresolvedRecovery = true;
			recordDiagnosticLocked("Retained import receipt inspection did not complete; package readiness remains unresolved.");
			bumpAvailabilityLocked();
		}
		inspectionRunning = false;
		inspectionPending = false;
		active = false;
		status.busy = false;
		bumpAvailabilityLocked();
		mutex.release();
	}

	/** Called by the existing native import worker. Its renderer stays on the
 	 * installed tree; only that worker receives the filesystem staging context. */
	public static function importOnce(source:String, type:String, scan:ImportScanResult,
		names:Map<String,String>, convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void):SongImportBatchResult {
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
		measurements = new ImportRefreshProgress(haxe.Timer.stamp());
		mutex.release();
		var sharedProgress = function(payload:Dynamic):Void {
			mutex.acquire();
			status.busy = true;
			status.complete = false;
			status.label = "Importing: " + Path.withoutDirectory(Path.normalize(source));
			measurements.update(payload, haxe.Timer.stamp());
			status.fraction = measurements.total <= 0 ? 0
				: Math.min(1, measurements.completed / measurements.total);
			mutex.release();
			if (progress != null) progress(payload);
		};
		try {
			var result = captureImport(source,type,scan,names,convert,cancel,sharedProgress,token);
			mutex.acquire();
			active = false;
			status.busy = false;
			status.complete = true;
			status.changed = true;
			status.fraction = 1;
			status.label = "Import committed; updating the song list";
			var reservation = reservations.get(token);
			if (reservation != null) queueHandoffLocked(token, result.importedSongs);
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
		cancel:Void->Bool, progress:Dynamic->Void, reservationToken:String):SongImportBatchResult {
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
		var rootOwners = expandDependentOwnerRoots([for (root in roots) ownerRootForNamespace(Std.string(root.namespace))]);
		var dependencyOwners = dependencyOwnerRootsForScan(scan, install, rootOwners);
		setReservationCandidates(reservationToken, "", rootOwners,
			candidatesForScan(scan, sourceRootDescriptors(normalized, roots)));
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
			runtimeDependencyOwners:dependencyOwners,
			revisions:[for (engine in engines) ImportRevision.current(engine,EngineBranding.version())]
		};
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

	public static function refreshNow(install:String, record:Dynamic,
		convert:(String,ImportScanResult,Map<String,String>)->SongImportBatchResult,
		cancel:Void->Bool, progress:Dynamic->Void):SongImportBatchResult {
		var token:String;
		var owner = "retained-import:" + Std.string(record.id);
		var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
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
		var reusableFamilyNamespaces = ImportPackageFamilyCatalog.reusableNamespaces(install, previous, Path.directory(source), record);
		for (sourceRelative in reusableFamilyNamespaces.keys())
			io.setNamespace(Path.join([source, sourceRelative]), ImportEngine.NIGHTMARE_VISION,
				reusableFamilyNamespaces.get(sourceRelative));
		var priorCatalogValue:Dynamic = Reflect.field(record, "packageFamilyCatalog");
		if (priorCatalogValue != null) {
			var priorCatalog = ImportRefreshTransaction.validatePackageFamilyCatalog(priorCatalogValue, record);
			if (priorCatalog != null && priorCatalog.version >= 2)
				for (member in priorCatalog.members)
					io.setNamespace(Path.join([source, member.sourceRelative]),
						ImportEngine.NIGHTMARE_VISION, member.namespace);
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
			var runtimeOwnerRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
			var runtimeDependencies = dependencyOwnerRootsForScan(scan, install, runtimeOwnerRoots);
			record.runtimeDependencyOwners = runtimeDependencies;
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
				var familyPublication = ModuleFunctions.publishNightmareVisionFamilyMemberRoots(familySourceRoots);
				if (familyPublication.failed > 0 || cancel())
					throw "Nightmare Vision package-family publication did not complete; installed content is unchanged. "
						+ (familyPublication.errors == null ? "" : familyPublication.errors.join("\n"));
			}
			var familyCatalog = ImportPackageFamilyCatalog.capturePublished(Path.directory(source), record, io);
			if (familyCatalog != null) Reflect.setField(record, "packageFamilyCatalog", familyCatalog);
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
				// The transaction hashes the generated bytes during its output
				// validation pass. Avoid reading every staged asset a second time here.
				outputs.push({path:path,stagedPath:path});
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
			var publishedPaths = masked.copy();
			for (output in outputs) if (publishedPaths.indexOf(output.path) < 0) publishedPaths.push(output.path);
			setReservationPaths(reservationToken, publishedPaths);
			var applied = ImportRefreshTransaction.apply(install,stage,state,owner,["assets"],outputs,metadata,cancel,baselines,progress);
			if (applied.status != ImportRefreshTransaction.STATUS_APPLIED)
				throw "Import refresh " + applied.status + ": " + [for (c in applied.conflicts) c.path + " (" + c.reason + ")"].join(", ");
			var committed = committedManifest(state, owner);
			var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
			addCommittedPathOwners(committed, committedRoots);
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
			var measured = measurements.snapshot(haxe.Timer.stamp(), queue.length);
			for (field in Reflect.fields(measured)) Reflect.setField(value, field, Reflect.field(measured, field));
		}
		mutex.release();
		return value;
	}

	static function loadQueue(install:String):Array<String> {
		var cache = Path.join([install,CACHE_ROOT]);
		var records = Path.join([cache,"records"]);
		if (!FileSystem.exists(records)) return [];
		var recordNames = [for (name in FileSystem.readDirectory(records))
			if (~/^[a-f0-9]{64}\.json$/.match(name)) name];
		recordNames.sort(Reflect.compare);
		var completed = 0;
		var protectedRecords:Map<String,Dynamic> = new Map();
		var dependencyOwnersByToken:Map<String,Array<String>> = new Map();
		var unavailableOwners:Map<String,Bool> = new Map();
		var unknownRecoveryTokens:Array<String> = [];
		var stagedCommittedRoots:Map<String,Bool> = new Map();
		for (name in recordNames) {
			mutex.acquire();
			measurements.update({phase:"checking-import-receipts",current:name,completed:completed,total:recordNames.length},haxe.Timer.stamp());
			mutex.release();
			var id = name.substr(0,64);
			var owner = "retained-import:" + id;
			var priorManifest:Dynamic = null;
			var priorRecord:Dynamic = null;
			var recoveryPaths:Array<String> = [];
			try {
				priorManifest = committedManifest(Path.join([cache,"state"]),owner);
				if (priorManifest != null && priorManifest.owner == owner && priorManifest.revision != null) {
					priorRecord = Reflect.field(priorManifest.revision,"importRecord");
				}
				var conflicts = ImportRefreshTransaction.recover(install,Path.join([cache,"state"]),owner);
				if (conflicts.length > 0) {
					recoveryPaths = ImportRefreshTransaction.recoveryTargetPaths(install,Path.join([cache,"state"]),owner);
					if (priorRecord != null && priorRecord.id == id && priorRecord.schemaVersion == 1) {
						var recoveryRoots = familyOwnerRootsForRecord(priorRecord, ownerRootsForRecord(priorRecord));
						var recoveryDependencies = runtimeDependencyMetadata(install, priorManifest, priorRecord, recoveryRoots);
						dependencyOwnersByToken.set("refresh:" + id, recoveryDependencies.owners);
						addRecordDependencyEdges(priorRecord, recoveryRoots, recoveryDependencies.owners);
						if (!recoveryDependencies.complete) for (root in recoveryRoots) unavailableOwners.set(root, true);
						reserveRecoveryBlock("refresh:" + id, owner, priorRecord, priorManifest,
							recoveryPaths, stagedCommittedRoots);
						protectedRecords.set("refresh:" + id, priorRecord);
					} else {
						reserveUnknownRecoveryBlock("refresh:" + id, owner, recoveryPaths);
						if (unknownRecoveryTokens.indexOf("refresh:" + id) < 0) unknownRecoveryTokens.push("refresh:" + id);
					}
					throw "Interrupted refresh needs attention; installed edits were preserved.";
				}
				var manifest = committedManifest(Path.join([cache,"state"]),owner);
				if (manifest == null || manifest.owner != owner || manifest.revision == null) continue;
				var record:Dynamic = manifest.revision.importRecord;
				if (record == null || record.id != id || record.schemaVersion != 1) continue;
				priorRecord = record;
				var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
				var dependencyMetadata = runtimeDependencyMetadata(install, manifest, record, committedRoots);
				dependencyOwnersByToken.set("refresh:" + id, dependencyMetadata.owners);
				addRecordDependencyEdges(record, committedRoots, dependencyMetadata.owners);
				if (!dependencyMetadata.complete) {
					for (root in committedRoots) unavailableOwners.set(root, true);
					mutex.acquire();
					unresolvedRecovery = true;
					recordDiagnosticLocked("A retained import has invalid or incomplete song provenance; its package remains unavailable until it is reimported.");
					bumpAvailabilityLocked();
					mutex.release();
				}
				stageCommittedRoots(stagedCommittedRoots, committedRoots);
				addCommittedPathOwners(manifest, committedRoots);
				var stale = false;
				for (stamp in (cast record.revisions:Array<Dynamic>)) {
					var assessment = ImportRevision.assess(stamp,Std.string(stamp.sourceEngine));
					if (assessment.status == ImportRevision.FUTURE || assessment.status == ImportRevision.UNKNOWN)
						throw "Import receipt is newer or unrecognized; its files were preserved.";
					if (assessment.status == ImportRevision.OUTDATED) stale = true;
				}
				if (stale) {
					protectedRecords.set("refresh:" + id, record);
					mutex.acquire();
				var reservation = reserveLocked("refresh:" + id, owner, committedRoots, null, false);
				setReservationCommittedRootsLocked(reservation, committedRoots);
				setReservationDependenciesLocked(reservation, dependencyMetadata.owners);
				queue.push(record);
				bumpAvailabilityLocked();
				mutex.release();
				}
			} catch (error:Dynamic) {
				trace("[import-refresh-error] " + Std.string(error));
				if (priorRecord != null && priorRecord.id == id && priorRecord.schemaVersion == 1) {
					if (recoveryPaths.length == 0) try
						recoveryPaths = ImportRefreshTransaction.recoveryTargetPaths(install,Path.join([cache,"state"]),owner)
					catch (_:Dynamic) {}
					if (!dependencyOwnersByToken.exists("refresh:" + id)) {
						var recoveryRoots = familyOwnerRootsForRecord(priorRecord, ownerRootsForRecord(priorRecord));
						var recoveryDependencies = runtimeDependencyMetadata(install, priorManifest, priorRecord, recoveryRoots);
						dependencyOwnersByToken.set("refresh:" + id, recoveryDependencies.owners);
						addRecordDependencyEdges(priorRecord, recoveryRoots, recoveryDependencies.owners);
						if (!recoveryDependencies.complete) for (root in recoveryRoots) unavailableOwners.set(root, true);
					}
					reserveRecoveryBlock("refresh:" + id, owner, priorRecord, priorManifest,
						recoveryPaths, stagedCommittedRoots);
					protectedRecords.set("refresh:" + id, priorRecord);
				} else {
					if (recoveryPaths.length == 0) try
						recoveryPaths = ImportRefreshTransaction.recoveryTargetPaths(install,Path.join([cache,"state"]),owner)
					catch (_:Dynamic) {}
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
			var record = protectedRecords.get(token);
			if (record == null) continue;
			var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
			stageCommittedRoots(stagedCommittedRoots, committedRoots);
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
		measurements.update({phase:"checking-import-receipts",current:"",completed:recordNames.length,total:recordNames.length},haxe.Timer.stamp());
		mutex.release();
		for (root in unavailableOwners.keys()) stagedCommittedRoots.remove(root);
		var confirmedRoots = [for (root in stagedCommittedRoots.keys()) root];
		confirmedRoots.sort(Reflect.compare);
		return confirmedRoots;
	}

	static function stageCommittedRoots(staged:Map<String,Bool>, roots:Array<String>):Void {
		if (staged == null || roots == null) return;
		for (root in roots) {
			var normalized = normalizeOwnerRoot(root);
			if (normalized != "") staged.set(normalized, true);
		}
	}

	static function reserveRecoveryBlock(token:String, owner:String, record:Dynamic, manifest:Dynamic,
		recoveryPaths:Array<String>, stagedCommittedRoots:Map<String,Bool>):Void {
		var committedRoots = familyOwnerRootsForRecord(record, ownerRootsForRecord(record));
		stageCommittedRoots(stagedCommittedRoots, committedRoots);
		mutex.acquire();
		var reservation = reserveLocked(token, owner, committedRoots, null, false);
		setReservationCommittedRootsLocked(reservation, committedRoots);
		reservation.recoveryBlocked = true;
		var files:Dynamic = manifest == null ? null : Reflect.field(manifest,"files");
		var paths:Array<String> = [];
		if (files != null && Std.isOfType(files,Array)) for (file in (cast files:Array<Dynamic>)) {
			var path:Dynamic = file == null ? null : Reflect.field(file,"path");
			var normalized = path == null ? "" : normalizeInstallRelative(Std.string(path));
			if (normalized != "" && paths.indexOf(normalized) < 0) paths.push(normalized);
		}
		if (recoveryPaths != null) for (rawPath in recoveryPaths) {
			var normalized = normalizeInstallRelative(rawPath);
			if (normalized != "" && paths.indexOf(normalized) < 0) paths.push(normalized);
			var pathOwner = ownerRootFromInstalledPath(normalized);
			if (pathOwner != "" && reservation.roots.indexOf(pathOwner) < 0) {
				reservation.roots.push(pathOwner);
				reservation.roots.sort(Reflect.compare);
			}
		}
		paths.sort(Reflect.compare);
		if (reservation.touchedPaths.join("\n") != paths.join("\n")) {
			reservation.touchedPaths = paths;
			bumpAvailabilityLocked();
		}
		if (reservation.roots.length == 0 && !unresolvedRecovery) {
			unresolvedRecovery = true;
			bumpAvailabilityLocked();
		}
		mutex.release();
	}

	static function reserveUnknownRecoveryBlock(token:String, owner:String, recoveryPaths:Array<String>):Void {
		var roots:Array<String> = [];
		var paths:Array<String> = [];
		if (recoveryPaths != null) for (rawPath in recoveryPaths) {
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
		if (roots.length == 0) unresolvedRecovery = true;
		bumpAvailabilityLocked();
		mutex.release();
	}

	static function markUnresolvedRecovery(message:String):Void {
		mutex.acquire();
		unresolvedRecovery = true;
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
		measurements = new ImportRefreshProgress(haxe.Timer.stamp());
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
				measurements.update(payload, haxe.Timer.stamp());
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
