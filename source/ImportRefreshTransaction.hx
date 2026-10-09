package;

import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.Eof;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import sys.io.FileInput;
import sys.io.FileOutput;
import ImportSourceSnapshot.ImportSnapshotSha256;
import SourceLimeAssetIdentity;

/** A staged file mapped to one relative destination owned by an import. */
typedef ImportRefreshStagedOutput = {
	var path:String;
	var stagedPath:String;
	/** Optional caller digest. When omitted, apply hashes the staged bytes once
	 * and carries that verified value into the manifest and conflict checks. */
	@:optional var sha256:String;
}

/** One file recorded as owned by the previous successful import. */
typedef ImportRefreshManifestFile = {
	var path:String;
	var sha256:String;
	var owner:String;
}

/** A source child authorized as a member of one retained package container. */
typedef ImportRefreshPackageFamilyCatalogEntry = {
	var directory:String;
	var sourceRelative:String;
	/** Required by v2 catalogs, which bind each retained member to an actually
	 * published installed namespace. Older v1 catalogs only grouped source roots. */
	@:optional var namespace:String;
}

/** The authenticated game-root profile which supplies compiled NV core assets
 * to every member of one retained content family. */
typedef ImportRefreshPackageFamilyCoreProvider = {
	var rootRelative:String;
	var namespace:String;
	var projectSha256:String;
}

/** Commit-authenticated description of a bounded, structurally detected family. */
typedef ImportRefreshPackageFamilyCatalog = {
	var version:Int;
	var engine:String;
	var snapshotId:String;
	var containerRelative:String;
	var members:Array<ImportRefreshPackageFamilyCatalogEntry>;
	/** Present only in v3, when the exact retained outer game profile can be
	 * linked to the receiver namespaces below. */
	@:optional var coreProvider:ImportRefreshPackageFamilyCoreProvider;
}

/** Persistent receipt describing the current files owned by one import. */
typedef ImportRefreshManifest = {
	var schemaVersion:Int;
	var owner:String;
	var transactionId:String;
	var ownedRoots:Array<String>;
	var revision:Dynamic;
	var files:Array<ImportRefreshManifestFile>;
	@:optional var packageFamilyCatalog:ImportRefreshPackageFamilyCatalog;
}

typedef ImportRefreshConflict = {
	var path:String;
	var reason:String;
}

typedef ImportRefreshResult = {
	var status:String;
	var conflicts:Array<ImportRefreshConflict>;
	var manifestPath:String;
	var receiptPath:String;
	var transactionPath:String;
}

/**
 * Applies a precomputed import output map as a recoverable file transaction.
 * It does not scan the installation tree: only the supplied destinations and
 * paths in this import's previous manifest are inspected.
 *
 * All destinations must be under one of the caller-provided owned roots. A
 * destination is replaceable/removable only when its previous manifest entry
 * names this owner and the installed bytes still match the recorded SHA-256.
 *
 * Backups and receipts are stored below stateRoot/<sha256(owner)> so multiple
 * imports do not share backup namespaces. The receipt is the commit marker and
 * is written only after every destination and the new manifest are in place.
 */
class ImportRefreshTransaction {
	public static inline var MANIFEST_SCHEMA:Int = 1;
	public static inline var STATUS_APPLIED:String = "applied";
	public static inline var STATUS_CONFLICT:String = "conflict";
	public static inline var STATUS_CANCELLED:String = "cancelled";
	static inline var CANCEL_TOKEN:String = "__IMPORT_REFRESH_CANCELLED__";
	static inline var CHUNK_SIZE:Int = 65536;
	static inline var SETTINGS_PATH:String = "assets/data/options.json";

	/**
	 * Apply stagedOutputs to installRoot. `owner` is a stable identity for one
	 * import (for example an importer name plus package identity). `stagingRoot`
	 * contains each output's `stagedPath`; `stateRoot` stores manifests, journals
	 * and backups. `isCancelled` is checked between file operations.
	 */
	public static function apply(installRoot:String, stagingRoot:String, stateRoot:String, owner:String,
		ownedRoots:Array<String>, stagedOutputs:Array<ImportRefreshStagedOutput>, ?revision:Dynamic,
		?cancelCheck:Void->Bool, ?validatedBaselines:Array<ImportRefreshManifestFile>,
		?progress:Dynamic->Void):ImportRefreshResult {
		try {
			return applyInternal(installRoot, stagingRoot, stateRoot, owner, ownedRoots, stagedOutputs,
				revision, cancelCheck, validatedBaselines, progress);
		} catch (error:Dynamic) {
			if (Std.isOfType(error, ImportWorkCancelled))
				return result(STATUS_CANCELLED, [], manifestPath(stateRoot, owner), "", "");
			throw error;
		}
	}

	static function applyInternal(installRoot:String, stagingRoot:String, stateRoot:String, owner:String,
		ownedRoots:Array<String>, stagedOutputs:Array<ImportRefreshStagedOutput>, ?revision:Dynamic,
		?cancelCheck:Void->Bool, ?validatedBaselines:Array<ImportRefreshManifestFile>,
		?progress:Dynamic->Void):ImportRefreshResult {
		if (installRoot == null || stagingRoot == null || stateRoot == null)
			throw "Import refresh requires install, staging, and state roots.";
		if (owner == null || StringTools.trim(owner) == "")
			throw "Import refresh requires a stable non-empty owner identity.";
		if (ownedRoots == null || ownedRoots.length == 0)
			throw "Import refresh requires at least one owned root.";
		if (stagedOutputs == null)
			throw "Import refresh requires an explicit staged output map.";

		var install = canonicalDirectory(installRoot, false);
		var staging = canonicalDirectory(stagingRoot, false);
		var state = canonicalDirectory(stateRoot, true);
		var scope = Path.join([state, digestText(owner)]);
		var transactionsRoot = Path.join([scope, "transactions"]);
		var manifestPath = safeChild(state, Path.join([digestText(owner), "manifest.json"]), false);
		ensureDirectoryUnder(state, scope);
		ensureDirectoryUnder(state, transactionsRoot);

		var recoveryConflicts = recover(install, state, owner, cancelCheck);
		if (recoveryConflicts.length > 0)
			return result(STATUS_CONFLICT, recoveryConflicts, currentManifestPath(state, owner), "", "");

		var rootList = normalizeOwnedRoots(ownedRoots);
		var outputByPath:Map<String, ImportRefreshStagedOutput> = new Map();
		var caseFolded:Map<String, String> = new Map();
		if (stagedOutputs.length == 0) reportProgress(progress, "checking-output", "", 0, 0);
		var outputsChecked = 0;
		var lastOutputPath = "";
		for (output in stagedOutputs) {
			if (!ImportWorkScheduler.cooperate(function() return checkCancelled(cancelCheck)))
				return result(STATUS_CANCELLED, [], manifestPath, "", "");
			if (output == null) throw "Import refresh output entry cannot be null.";
			var relative = normalizeRelative(output.path);
			reportProgress(progress, "checking-output", relative, outputsChecked, stagedOutputs.length);
			if (!isWithinOwnedRoots(relative, rootList))
				throw 'Output is outside caller-provided owned roots: $relative';
			if (isProtectedSettingsPath(relative))
				throw 'Import refresh cannot target the user settings file: $relative';
			var folded = relative.toLowerCase();
			if (outputByPath.exists(relative) || caseFolded.exists(folded))
				throw 'Duplicate or case-colliding output path: $relative';
			caseFolded.set(folded, relative);
			var expectedOutputHash:Null<String> = output.sha256 == null ? null : output.sha256.toLowerCase();
			if (expectedOutputHash != null)
				validateHash(expectedOutputHash, 'expected output SHA-256 for $relative');
			var sourceRel = normalizeRelative(output.stagedPath);
			var source = safeChild(staging, sourceRel, true);
			if (!isRegularFile(source)) throw 'Staged output is not a regular file: $sourceRel';
			var sourceHash = ImportSourceSnapshot.sha256File(source, CHUNK_SIZE,
				function() return checkCancelled(cancelCheck));
			if (expectedOutputHash != null && sourceHash != expectedOutputHash)
				throw 'Staged output changed or has the wrong SHA-256: $sourceRel';
			outputByPath.set(relative, {
				path: relative,
				stagedPath: sourceRel,
				sha256: sourceHash
			});
			outputsChecked++;
			lastOutputPath = relative;
		}
		if (outputsChecked > 0)
			reportProgress(progress, "checking-output", lastOutputPath, outputsChecked, stagedOutputs.length);

		var baselineByPath:Map<String, ImportRefreshManifestFile> = new Map();
		var baselineCaseFolded:Map<String, String> = new Map();
		if (validatedBaselines != null) {
			for (baseline in validatedBaselines) {
				if (!ImportWorkScheduler.cooperate(function() return checkCancelled(cancelCheck)))
					return result(STATUS_CANCELLED, [], manifestPath, "", "");
				if (baseline == null) throw "Validated import baseline cannot be null.";
				var relative = normalizeRelative(baseline.path);
				if (!isWithinOwnedRoots(relative, rootList))
					throw 'Validated baseline is outside caller-provided owned roots: $relative';
				if (isProtectedSettingsPath(relative))
					throw 'Validated baseline cannot include the user settings file: $relative';
				if (baseline.owner != owner) throw 'Validated baseline owner does not match this import: $relative';
				validateHash(baseline.sha256, 'validated baseline SHA-256 for $relative');
				if (!outputByPath.exists(relative)) throw 'Validated baseline has no staged output: $relative';
				var folded = relative.toLowerCase();
				if (baselineByPath.exists(relative) || baselineCaseFolded.exists(folded))
					throw 'Duplicate or case-colliding validated baseline: $relative';
				baselineCaseFolded.set(folded, relative);
				baselineByPath.set(relative, {path: relative, sha256: baseline.sha256.toLowerCase(), owner: owner});
			}
		}

		checkpointWork(cancelCheck);
		var previous = readCurrentManifest(state, owner, rootList, cancelCheck);
		var previousByPath:Map<String, ImportRefreshManifestFile> = new Map();
		for (entry in previous.files) {
			checkpointWork(cancelCheck);
			previousByPath.set(entry.path, entry);
		}

		var conflicts:Array<ImportRefreshConflict> = [];
		var operations:Array<Dynamic> = [];
		var unchangedTargets:Array<Dynamic> = [];
		var allPaths:Array<String> = [];
		for (path in outputByPath.keys()) {
			checkpointWork(cancelCheck);
			allPaths.push(path);
		}
		for (path in previousByPath.keys()) {
			checkpointWork(cancelCheck);
			if (!outputByPath.exists(path)) allPaths.push(path);
		}
		allPaths.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));

		var transactionId = makeTransactionId();
		var transactionPath = Path.join([transactionsRoot, transactionId]);
		var manifestBeforeExists = FileSystem.exists(manifestPath);
		var manifestBeforeHash = manifestBeforeExists ? ImportSourceSnapshot.sha256File(manifestPath, CHUNK_SIZE,
			function() return checkCancelled(cancelCheck)) : "";
		var manifestAfter = makeManifest(owner, transactionId, rootList, revision, outputByPath, cancelCheck);
		var manifestText = UnicodeSafeJson.stringifyStandard(manifestAfter) + "\n";
		var manifestAfterHash = digestText(manifestText);

		var installedChecked = 0;
		var lastInstalledPath = "";
		if (allPaths.length == 0) reportProgress(progress, "checking-installed", "", 0, 0);
		for (relative in allPaths) {
			if (!ImportWorkScheduler.cooperate(function() return checkCancelled(cancelCheck)))
				return result(STATUS_CANCELLED, [], manifestPath, "", "");
			reportProgress(progress, "checking-installed", relative, installedChecked, allPaths.length);
			if (!isWithinOwnedRoots(relative, rootList)) {
				conflicts.push({path: relative, reason: "The prior manifest target is outside the caller-provided owned roots."});
				installedChecked++;
				lastInstalledPath = relative;
				continue;
			}
			if (isProtectedSettingsPath(relative)) {
				conflicts.push({path: relative, reason: "The user settings file is protected from import refresh."});
				installedChecked++;
				lastInstalledPath = relative;
				continue;
			}
			var prior = previousByPath.get(relative);
			var output = outputByPath.get(relative);
			var baseline = baselineByPath.get(relative);
			var target:String;
			try {
				target = safeChild(install, relative, false);
				assertNotInside(target, scope, relative);
			} catch (error:Dynamic) {
				conflicts.push({path: relative, reason: Std.string(error)});
				installedChecked++;
				lastInstalledPath = relative;
				continue;
			}
			var exists = FileSystem.exists(target);
			if (exists && !isRegularFile(target)) {
				conflicts.push({path: relative, reason: "The destination is not a regular file."});
				installedChecked++;
				lastInstalledPath = relative;
				continue;
			}
			if (output != null) {
				if (exists) {
					if (prior == null && baseline == null) {
						conflicts.push({path: relative, reason: "An unowned or user-added file already exists at this destination."});
						installedChecked++;
						lastInstalledPath = relative;
						continue;
					}
					if (prior != null && prior.owner != owner) {
						conflicts.push({path: relative, reason: "The prior manifest assigns this destination to another owner."});
						installedChecked++;
						lastInstalledPath = relative;
						continue;
					}
					var actual = ImportSourceSnapshot.sha256File(target, CHUNK_SIZE,
						function() return checkCancelled(cancelCheck));
					var matchesPrior = prior != null && actual == prior.sha256.toLowerCase();
					var matchesBaseline = baseline != null && actual == baseline.sha256.toLowerCase();
					var matchesDesired = prior != null && prior.owner == owner && actual == output.sha256;
					if (baseline != null && !matchesBaseline) {
						conflicts.push({path: relative, reason: "The live registry bytes changed after its merge baseline was captured."});
						installedChecked++;
						lastInstalledPath = relative;
						continue;
					}
					if (!matchesPrior && !matchesBaseline && !matchesDesired) {
						conflicts.push({path: relative, reason: "Installed bytes differ from the prior manifest; local edits are preserved."});
						installedChecked++;
						lastInstalledPath = relative;
						continue;
					}
					if (actual == output.sha256) {
						unchangedTargets.push({path: relative, target: target, sha256: actual,
							stagedPath: output.stagedPath, outputSha256: output.sha256});
					} else {
						operations.push(makeOperation(relative, target, true, true, actual, output));
					}
				} else if (prior != null) {
					conflicts.push({path: relative, reason: "A previously owned file is missing; the local deletion is preserved."});
					installedChecked++;
					lastInstalledPath = relative;
					continue;
				} else if (baseline != null) {
					conflicts.push({path: relative, reason: "A validated registry baseline is missing; the local deletion is preserved."});
					installedChecked++;
					lastInstalledPath = relative;
					continue;
				} else {
					operations.push(makeOperation(relative, target, true, false, "", output));
				}
			} else if (prior != null && exists) {
				if (prior.owner != owner) {
					conflicts.push({path: relative, reason: "The prior manifest assigns this destination to another owner."});
					installedChecked++;
					lastInstalledPath = relative;
					continue;
				}
				var actual = ImportSourceSnapshot.sha256File(target, CHUNK_SIZE,
					function() return checkCancelled(cancelCheck));
				if (actual != prior.sha256.toLowerCase()) {
					conflicts.push({path: relative, reason: "Obsolete installed bytes were edited; the local file is preserved."});
					installedChecked++;
					lastInstalledPath = relative;
					continue;
				}
				operations.push(makeOperation(relative, target, false, true, actual, null));
			}
			installedChecked++;
			lastInstalledPath = relative;
		}
		if (installedChecked > 0)
			reportProgress(progress, "checking-installed", lastInstalledPath, installedChecked, allPaths.length);

		if (conflicts.length > 0)
			return result(STATUS_CONFLICT, conflicts, manifestPath, "", "");
		if (checkCancelled(cancelCheck))
			return result(STATUS_CANCELLED, [], manifestPath, "", "");
		if (FileSystem.exists(transactionPath))
			throw 'Import refresh transaction id collision: $transactionId';

		ensureDirectoryUnder(state, transactionPath);
		var backupRoot = Path.join([transactionPath, "backups"]);
		var backupFiles = Path.join([backupRoot, "files"]);
		ensureDirectoryUnder(transactionPath, backupFiles);
		var uninterruptedPublicationToken = 0;
		try {
			var backupTotal = (manifestBeforeExists ? 1 : 0);
			for (operation in operations) {
				if (!ImportWorkScheduler.cooperate(function() return checkCancelled(cancelCheck))) throw CANCEL_TOKEN;
				if (operation.beforeExists) backupTotal++;
			}
			var backupsCompleted = 0;
			var lastBackupPath = "";
			if (backupTotal == 0) reportProgress(progress, "backing-up-import", "", 0, 0);
			var manifestBackup = Path.join([backupFiles, digestText("manifest.json") + ".bak"]);
			if (manifestBeforeExists) {
				reportProgress(progress, "backing-up-import", "manifest.json", backupsCompleted, backupTotal);
				var copiedManifestHash = copyAndHash(manifestPath, manifestBackup, cancelCheck);
				if (copiedManifestHash != manifestBeforeHash)
					throw "The current import manifest changed while its backup was being made.";
				backupsCompleted++;
				lastBackupPath = "manifest.json";
			}
			for (operation in operations) {
				if (operation.beforeExists) {
					reportProgress(progress, "backing-up-import", operation.path, backupsCompleted, backupTotal);
					var backupPath = Path.join([backupFiles, digestText(operation.path) + ".bak"]);
					var copiedHash = copyAndHash(operation.target, backupPath, cancelCheck);
					if (copiedHash != operation.beforeSha256)
						throw 'Installed bytes changed while backing up ${operation.path}.';
					operation.backupPath = relativePathFrom(transactionPath, backupPath);
					backupsCompleted++;
					lastBackupPath = operation.path;
				}
			}
			if (backupsCompleted > 0)
				reportProgress(progress, "backing-up-import", lastBackupPath, backupsCompleted, backupTotal);

			uninterruptedPublicationToken = ImportWorkScheduler.beginUninterruptedPublication(function() {
				return checkCancelled(cancelCheck);
			});
			if (uninterruptedPublicationToken < 0) throw CANCEL_TOKEN;

			var journal:Dynamic = {
				schemaVersion: MANIFEST_SCHEMA,
				owner: owner,
				transactionId: transactionId,
				phase: "prepared",
				installRoot: install,
				ownedRoots: rootList,
				operations: operations,
				manifestPath: "manifest.json",
				manifestBeforeExists: manifestBeforeExists,
				manifestBeforeSha256: manifestBeforeHash,
				manifestAfterSha256: manifestAfterHash,
				manifestBackupPath: manifestBeforeExists ? relativePathFrom(transactionPath, manifestBackup) : "",
				journalSequence: 0
			};
			writeJournal(transactionPath, journal);
			Reflect.setField(journal, "phase", "applying");
			writeJournal(transactionPath, journal);

			// Publication units are destination writes, unchanged-file rechecks,
			// the manifest, and its commit receipt.
			var publishTotal = operations.length + unchangedTargets.length + 2;
			var published = 0;
			var lastPublishedPath = "manifest.json";
			for (operation in operations) {
				if (checkCancelled(cancelCheck)) throw CANCEL_TOKEN;
				reportProgress(progress, "publishing-import", operation.path, published, publishTotal);
				applyOperation(install, staging, transactionPath, transactionId, operation, cancelCheck);
				if (checkCancelled(cancelCheck)) throw CANCEL_TOKEN;
				published++;
				lastPublishedPath = operation.path;
			}
			reportProgress(progress, "publishing-import", lastPublishedPath, published, publishTotal);

			// Unchanged owned files have no journaled write operation, so recheck
			// their bytes after other publication work and immediately before the
			// manifest commit. This retains the old preflight-to-commit protection.
			for (unchanged in unchangedTargets) {
				if (checkCancelled(cancelCheck)) throw CANCEL_TOKEN;
				var unchangedPath = Std.string(Reflect.field(unchanged, "path"));
				reportProgress(progress, "publishing-import", unchangedPath, published, publishTotal);
				var unchangedTarget = safeChild(install, unchangedPath, false);
				var unchangedHash = Std.string(Reflect.field(unchanged, "sha256"));
				if (!FileSystem.exists(unchangedTarget) || !isRegularFile(unchangedTarget)
					|| ImportSourceSnapshot.sha256File(unchangedTarget, CHUNK_SIZE) != unchangedHash)
					throw 'Installed file changed before manifest commit: $unchangedPath';
				var unchangedStageRel = Std.string(Reflect.field(unchanged, "stagedPath"));
				var unchangedStage = safeChild(staging, unchangedStageRel, true);
				var unchangedOutputHash = Std.string(Reflect.field(unchanged, "outputSha256"));
				if (!isRegularFile(unchangedStage)
					|| ImportSourceSnapshot.sha256File(unchangedStage, CHUNK_SIZE) != unchangedOutputHash)
					throw 'Staged output changed before manifest commit: $unchangedStageRel';
				if (checkCancelled(cancelCheck)) throw CANCEL_TOKEN;
				published++;
				lastPublishedPath = unchangedPath;
			}

			var currentManifestHash = FileSystem.exists(manifestPath)
				? ImportSourceSnapshot.sha256File(manifestPath, CHUNK_SIZE) : "";
			if (currentManifestHash != manifestBeforeHash)
				throw "The current import manifest changed during the transaction.";
			reportProgress(progress, "publishing-import", "manifest.json", published, publishTotal);
			atomicReplaceText(manifestPath, manifestText, transactionId + "-manifest");
			published++;
			Reflect.setField(journal, "phase", "receipt-pending");
			writeJournal(transactionPath, journal);

			var receiptPath = Path.join([transactionPath, "receipt.json"]);
			var receipt:Dynamic = {
				schemaVersion: MANIFEST_SCHEMA,
				status: STATUS_APPLIED,
				owner: owner,
				transactionId: transactionId,
				manifestSha256: manifestAfterHash,
				fileCount: Reflect.field(manifestAfter, "files") == null ? 0 : (cast Reflect.field(manifestAfter, "files"):Array<Dynamic>).length
			};
			reportProgress(progress, "publishing-import", "receipt.json", published, publishTotal);
			writeNewText(receiptPath, Json.stringify(receipt) + "\n", transactionId + "-receipt");
			validateReceipt(receiptPath, journal);
			published++;
			reportProgress(progress, "publishing-import", "receipt.json", published, publishTotal);
			ImportWorkScheduler.endUninterruptedPublication(uninterruptedPublicationToken);
			uninterruptedPublicationToken = 0;
			// The receipt makes publication durable. Backup deletion is storage
			// maintenance and can now pause between files without risking rollback.
			cleanupCommittedBackups(transactionPath, journal);
			return result(STATUS_APPLIED, [], manifestPath, receiptPath, transactionPath);
		} catch (error:Dynamic) {
			var rollbackErrors:Array<ImportRefreshConflict> = [];
			try rollbackErrors = rollback(transactionPath, install, state, owner) catch (rollbackError:Dynamic) {
				ImportWorkScheduler.endUninterruptedPublication(uninterruptedPublicationToken);
				throw rollbackError;
			}
			if (rollbackErrors.length > 0) {
				ImportWorkScheduler.endUninterruptedPublication(uninterruptedPublicationToken);
				throw 'Import refresh failed (${Std.string(error)}) and rollback needs recovery: ${rollbackErrors[0].reason}';
			}
			ImportWorkScheduler.endUninterruptedPublication(uninterruptedPublicationToken);
			if (Std.string(error) == CANCEL_TOKEN)
				return result(STATUS_CANCELLED, [], manifestPath, "", transactionPath);
			throw error;
		}
	}

	/** Recover every uncommitted journal for this owner. Safe to call repeatedly. */
	public static function recover(installRoot:String, stateRoot:String, owner:String,
		?cancelCheck:Void->Bool):Array<ImportRefreshConflict> {
		var conflicts:Array<ImportRefreshConflict> = [];
		if (owner == null || StringTools.trim(owner) == "") throw "Recovery requires an owner identity.";
		var install = canonicalDirectory(installRoot, false);
		var state = canonicalDirectory(stateRoot, true);
		var scope = Path.join([state, digestText(owner)]);
		var transactions = Path.join([scope, "transactions"]);
		if (!FileSystem.exists(transactions)) return conflicts;
		if (!FileSystem.isDirectory(transactions))
			return [{path: transactions, reason: "Transaction recovery path is not a directory."}];

		var names = FileSystem.readDirectory(transactions);
		names.sort(Reflect.compare);
		for (name in names) {
			checkpointWork(cancelCheck);
			if (!StringTools.startsWith(name, "txn-") || name.indexOf("/") >= 0 || name.indexOf("\\") >= 0) {
				conflicts.push({path: name, reason: "Unexpected entry in the owner transaction directory."});
				continue;
			}
			var transactionPath:String;
			try transactionPath = safeChild(state, Path.join([digestText(owner), "transactions", name]), true) catch (error:Dynamic) {
				conflicts.push({path: name, reason: Std.string(error)});
				continue;
			}
			if (!FileSystem.isDirectory(transactionPath)) {
				conflicts.push({path: name, reason: "Transaction entry is not a directory."});
				continue;
			}
			var journal = latestJournal(transactionPath, cancelCheck);
			if (journal == null) continue;
			if (Reflect.field(journal, "owner") != owner || Reflect.field(journal, "transactionId") != name) {
				conflicts.push({path: name, reason: "Journal owner or transaction identity does not match its directory."});
				continue;
			}
			var receiptPath = Path.join([transactionPath, "receipt.json"]);
			if (FileSystem.exists(receiptPath)) {
				try {
					validateReceipt(receiptPath, journal);
					cleanupCommittedBackups(transactionPath, journal);
				} catch (error:Dynamic)
					conflicts.push({path: name, reason: Std.string(error)});
				continue;
			}
			var phase = Std.string(Reflect.field(journal, "phase"));
			if (phase == "rolled-back") continue;
			var recordedInstall:Dynamic = Reflect.field(journal, "installRoot");
			if (recordedInstall == null || StringTools.trim(Std.string(recordedInstall)) == ""
				|| !samePath(Path.normalize(Std.string(recordedInstall)), install)) {
				conflicts.push({path: name, reason: "Journal install root differs from the current installation; preserving files for manual recovery."});
				continue;
			}
			// A rollback spans several destination paths and its journal transition.
			// Wait before it starts, then let this one transaction finish or report its
			// conflicts without pausing in a partially restored installation.
			var recoveryToken = ImportWorkScheduler.beginUninterruptedPublication(function() {
				return checkCancelled(cancelCheck);
			});
			if (recoveryToken < 0) throw new ImportWorkCancelled();
			try {
				for (conflict in rollbackFromJournal(transactionPath, install, state, journal))
					conflicts.push(conflict);
			} catch (error:Dynamic) {
				ImportWorkScheduler.endUninterruptedPublication(recoveryToken);
				throw error;
			}
			ImportWorkScheduler.endUninterruptedPublication(recoveryToken);
		}
		return conflicts;
	}

	/** Destination paths from receiptless journals which still need recovery.
	 * This is a bounded metadata read used only after recover() reports conflicts;
	 * it never hashes installed or backup file contents. Paths are returned only
	 * when the journal identity, install root, and owned-root declaration agree. */
	public static function recoveryTargetPaths(installRoot:String, stateRoot:String,
		owner:String):Array<String> {
		if (owner == null || StringTools.trim(owner) == "") return [];
		var install = canonicalDirectory(installRoot, false);
		var state = canonicalDirectory(stateRoot, true);
		var transactions = Path.join([state, digestText(owner), "transactions"]);
		if (!FileSystem.exists(transactions) || !FileSystem.isDirectory(transactions)) return [];
		var names = FileSystem.readDirectory(transactions);
		names.sort(Reflect.compare);
		var result:Array<String> = [];
		for (name in names) {
			ImportWorkScheduler.cooperate();
			if (!StringTools.startsWith(name, "txn-") || name.indexOf("/") >= 0 || name.indexOf("\\") >= 0) continue;
			var transactionPath:String;
			try transactionPath = safeChild(state, Path.join([digestText(owner), "transactions", name]), true)
			catch (_:Dynamic) continue;
			if (!FileSystem.isDirectory(transactionPath)) continue;
			var journal = latestJournal(transactionPath);
			if (journal == null || Reflect.field(journal, "owner") != owner
				|| Reflect.field(journal, "transactionId") != name) continue;
			var recordedInstall:Dynamic = Reflect.field(journal, "installRoot");
			if (recordedInstall == null || !samePath(Path.normalize(Std.string(recordedInstall)), install)) continue;
			if (Std.string(Reflect.field(journal, "phase")) == "rolled-back") continue;
			var receiptPath = Path.join([transactionPath, "receipt.json"]);
			if (FileSystem.exists(receiptPath)) {
				try {
					validateReceipt(receiptPath, journal);
					continue;
				} catch (_:Dynamic) {
					// A mismatched receipt is still unresolved; its journal targets below
					// let the UI hold only songs whose installed paths are known.
				}
			}
			var rawRoots:Dynamic = Reflect.field(journal, "ownedRoots");
			var roots:Array<String>;
			try roots = normalizeOwnedRoots(cast rawRoots) catch (_:Dynamic) continue;
			var operations:Dynamic = Reflect.field(journal, "operations");
			if (!Std.isOfType(operations, Array)) continue;
			for (operation in (cast operations:Array<Dynamic>)) {
				ImportWorkScheduler.cooperate();
				if (operation == null) continue;
				var rawPath:Dynamic = Reflect.field(operation, "path");
				if (rawPath == null) continue;
				var path:String;
				try path = normalizeRelative(Std.string(rawPath)) catch (_:Dynamic) continue;
				if (!isWithinOwnedRoots(path, roots) || isProtectedSettingsPath(path)) continue;
				if (result.indexOf(path) < 0) result.push(path);
			}
		}
		result.sort(Reflect.compare);
		return result;
	}

	/** Read and validate the latest committed manifest for one owner. */
	public static function loadManifest(stateRoot:String, owner:String):ImportRefreshManifest {
		var state = canonicalDirectory(stateRoot, true);
		var manifest = readCurrentManifest(state, owner, null);
		return manifest;
	}

	public static function manifestPath(stateRoot:String, owner:String):String {
		return currentManifestPath(canonicalDirectory(stateRoot, true), owner);
	}

	static function makeOperation(path:String, target:String, afterExists:Bool, beforeExists:Bool,
		beforeSha256:String, output:Null<ImportRefreshStagedOutput>):Dynamic {
		return {
			path: path,
			target: target,
			beforeExists: beforeExists,
			beforeSha256: beforeSha256,
			afterExists: afterExists,
			afterSha256: output == null ? "" : output.sha256,
			stagedPath: output == null ? "" : output.stagedPath,
			backupPath: ""
		};
	}

	static function makeManifest(owner:String, transactionId:String, roots:Array<String>, revision:Dynamic,
		outputs:Map<String, ImportRefreshStagedOutput>, ?cancelCheck:Void->Bool):Dynamic {
		var names:Array<String> = [];
		for (name in outputs.keys()) {
			checkpointWork(cancelCheck);
			names.push(name);
		}
		names.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		var files:Array<Dynamic> = [];
		for (name in names) {
			checkpointWork(cancelCheck);
			var output = outputs.get(name);
			files.push({path: name, sha256: output.sha256, owner: owner});
		}
		var revisionRecord:Dynamic = revision == null ? null : Reflect.field(revision, "importRecord");
		var nestedCatalog:Dynamic = revisionRecord == null ? null : Reflect.field(revisionRecord, "packageFamilyCatalog");
		var catalog = validatePackageFamilyCatalog(nestedCatalog, revisionRecord);
		if (catalog != null && catalog.version >= 2)
			validatePackageFamilyOutputs(catalog, files);
		var manifest:Dynamic = {
			schemaVersion: MANIFEST_SCHEMA,
			owner: owner,
			transactionId: transactionId,
			ownedRoots: roots,
			revision: revision,
			files: files
		};
		if (catalog != null) Reflect.setField(manifest, "packageFamilyCatalog", catalog);
		return manifest;
	}

	static function readCurrentManifest(state:String, owner:String, allowedRoots:Null<Array<String>>,
		?cancelCheck:Void->Bool):ImportRefreshManifest {
		checkpointWork(cancelCheck);
		var path = currentManifestPath(state, owner);
		if (!FileSystem.exists(path)) return {
			schemaVersion: MANIFEST_SCHEMA,
			owner: owner,
			transactionId: "",
			ownedRoots: [],
			revision: null,
			files: []
		};
		path = safeChild(state, Path.join([digestText(owner), "manifest.json"]), true);
		if (!isRegularFile(path)) throw "Current import manifest is not a regular file.";
		var text = File.getContent(path);
		var raw:Dynamic;
		try raw = Json.parse(text) catch (error:Dynamic) throw 'Invalid import manifest: ${Std.string(error)}';
		if (Reflect.field(raw, "schemaVersion") != MANIFEST_SCHEMA || Reflect.field(raw, "owner") != owner)
			throw "Current import manifest schema or owner is invalid.";
		var transactionId = Reflect.field(raw, "transactionId");
		if (transactionId == null || Std.string(transactionId) == "")
			throw "Current import manifest has no committed transaction identity.";
		var safeTransactionId = normalizeRelative(Std.string(transactionId));
		var receiptPath = safeChild(state,
			Path.join([digestText(owner), "transactions", safeTransactionId, "receipt.json"]), true);
		if (!FileSystem.exists(receiptPath)) throw "Current import manifest has no commit receipt.";
		checkpointWork(cancelCheck);
		var receipt:Dynamic = Json.parse(File.getContent(receiptPath));
		if (Reflect.field(receipt, "owner") != owner || Reflect.field(receipt, "transactionId") != transactionId
			|| Reflect.field(receipt, "manifestSha256") != digestText(text))
			throw "Current import manifest does not match its commit receipt.";
		var revision:Dynamic = Reflect.field(raw, "revision");
		var revisionRecord:Dynamic = revision == null ? null : Reflect.field(revision, "importRecord");
		var nestedCatalog:Dynamic = revisionRecord == null ? null : Reflect.field(revisionRecord, "packageFamilyCatalog");
		var topLevelCatalog:Dynamic = Reflect.field(raw, "packageFamilyCatalog");
		var catalog = validatePackageFamilyCatalog(nestedCatalog, revisionRecord);
		if (topLevelCatalog != null) {
			var topCatalog = validatePackageFamilyCatalog(topLevelCatalog, revisionRecord);
			if (catalog == null || Json.stringify(catalog) != Json.stringify(topCatalog))
				throw "Current import package-family catalog does not match its retained record.";
			catalog = topCatalog;
		}
		var rawFiles:Dynamic = Reflect.field(raw, "files");
		var rawRoots:Dynamic = Reflect.field(raw, "ownedRoots");
		if (!Std.isOfType(rawFiles, Array) || !Std.isOfType(rawRoots, Array))
			throw "Current import manifest is missing its file or owned-root list.";
		var roots = normalizeOwnedRoots(cast rawRoots);
		if (allowedRoots != null) {
			for (entry in (cast rawFiles:Array<Dynamic>)) {
				checkpointWork(cancelCheck);
				var entryPath = normalizeRelative(Std.string(Reflect.field(entry, "path")));
				if (!isWithinOwnedRoots(entryPath, allowedRoots))
					throw 'Prior manifest target is outside the caller-provided owned roots: $entryPath';
			}
		}
		var seen:Map<String, Bool> = new Map();
		var files:Array<ImportRefreshManifestFile> = [];
		for (entry in (cast rawFiles:Array<Dynamic>)) {
			checkpointWork(cancelCheck);
			var entryPath = normalizeRelative(Std.string(Reflect.field(entry, "path")));
			var hash = Std.string(Reflect.field(entry, "sha256")).toLowerCase();
			var entryOwner = Std.string(Reflect.field(entry, "owner"));
			validateHash(hash, 'manifest SHA-256 for $entryPath');
			if (entryOwner != owner) throw 'Prior manifest ownership does not match for $entryPath';
			var folded = entryPath.toLowerCase();
			if (seen.exists(folded)) throw 'Duplicate or case-colliding prior manifest target: $entryPath';
			seen.set(folded, true);
			if (!isWithinOwnedRoots(entryPath, roots)) throw 'Prior target is outside its recorded owned roots: $entryPath';
			files.push({path: entryPath, sha256: hash, owner: entryOwner});
		}
		if (catalog != null && catalog.version >= 2)
			validatePackageFamilyOutputs(catalog, files);
		var manifest:ImportRefreshManifest = {
			schemaVersion: MANIFEST_SCHEMA,
			owner: owner,
			transactionId: Std.string(transactionId),
			ownedRoots: roots,
			revision: Reflect.field(raw, "revision"),
			files: files
		};
		if (catalog != null) manifest.packageFamilyCatalog = catalog;
		return manifest;
	}

	/** Validate the optional family catalog against the committed retained import
	 * record. Legacy manifests without a catalog remain valid and resolve as a
	 * singleton until their source snapshot proves a structural family. */
	public static function validatePackageFamilyCatalog(value:Dynamic,
		record:Dynamic):Null<ImportRefreshPackageFamilyCatalog> {
		if (value == null) return null;
		if (record == null || Reflect.field(record, "schemaVersion") != 1)
			throw "Import package-family catalog has no retained import record.";
		var version:Dynamic = Reflect.field(value, "version");
		var engine:Dynamic = Reflect.field(value, "engine");
		var snapshotId:Dynamic = Reflect.field(value, "snapshotId");
		var container:Dynamic = Reflect.field(value, "containerRelative");
		var rawMembers:Dynamic = Reflect.field(value, "members");
		if ((version != 1 && version != 2 && version != 3) || engine != "Nightmare Vision" || !isSha256Text(snapshotId)
			|| (version == 1 && container != "content")
			|| ((version == 2 || version == 3) && container != "content" && container != "")
			|| (version == 3 && container != "content")
			|| !Std.isOfType(rawMembers, Array))
			throw "Import package-family catalog identity or container is invalid.";
		var recordId:Dynamic = Reflect.field(record, "snapshotId");
		var recordSource:Dynamic = Reflect.field(record, "source");
		if (recordId != snapshotId || recordSource != "sources/" + Std.string(snapshotId) + "/content")
			throw "Import package-family catalog does not belong to this retained snapshot.";
		var engines:Dynamic = Reflect.field(record, "engines");
		var hasEngine = false;
		if (Std.isOfType(engines, Array)) for (item in (cast engines:Array<Dynamic>)) {
			ImportWorkScheduler.cooperate();
			if (item == "Nightmare Vision") hasEngine = true;
		}
		if (!hasEngine) throw "Import package-family catalog engine does not match its retained record.";
		var rawRoots:Dynamic = Reflect.field(record, "roots");
		if (!Std.isOfType(rawRoots, Array)) throw "Import package-family catalog record has no roots.";
		var memberValues:Array<Dynamic> = cast rawMembers;
		if (memberValues.length < 2 || memberValues.length > 128)
			throw "Import package-family catalog member count is invalid.";
		var members:Array<ImportRefreshPackageFamilyCatalogEntry> = [];
		var seenDirectories:Map<String, Bool> = new Map();
		var seenPaths:Map<String, Bool> = new Map();
		var seenNamespaces:Map<String, Bool> = new Map();
		for (member in memberValues) {
			ImportWorkScheduler.cooperate();
			var directoryValue:Dynamic = Reflect.field(member, "directory");
			var sourceValue:Dynamic = Reflect.field(member, "sourceRelative");
			if (!Std.isOfType(directoryValue, String) || !Std.isOfType(sourceValue, String))
				throw "Import package-family catalog member fields are invalid.";
			var directory:String = cast directoryValue;
			var sourceRelative:String = cast sourceValue;
			var expectedRelative = version == 1 || container == "content"
				? "content/" + directory : directory;
			if (directory == "" || directory == "." || directory == ".."
				|| directory.indexOf("/") >= 0 || directory.indexOf("\\") >= 0
				|| normalizeRelative(expectedRelative) != expectedRelative
				|| sourceRelative != expectedRelative)
				throw "Import package-family catalog member path is invalid.";
			var folded = directory.toLowerCase();
			if (seenDirectories.exists(folded) || seenPaths.exists(sourceRelative.toLowerCase()))
				throw "Import package-family catalog has an equal-label collision.";
			seenDirectories.set(folded, true);
			seenPaths.set(sourceRelative.toLowerCase(), true);
			var namespace:String = null;
			if (version >= 2) {
				var namespaceValue:Dynamic = Reflect.field(member, "namespace");
				if (!Std.isOfType(namespaceValue, String) || namespaceValue == ""
					|| Std.string(namespaceValue).indexOf("/") >= 0 || Std.string(namespaceValue).indexOf("\\") >= 0)
					throw "Import package-family destination namespace is invalid.";
				namespace = cast namespaceValue;
				var safeNamespace = "assets/imported_mods/" + namespace;
				if (normalizeRelative(safeNamespace) != safeNamespace)
					throw "Import package-family destination namespace is invalid.";
				var namespaceKey = pathTextKey(namespace);
				if (seenNamespaces.exists(namespaceKey))
					throw "Import package-family catalog maps multiple labels to one namespace.";
				seenNamespaces.set(namespaceKey, true);
			}
			members.push({directory: directory, sourceRelative: sourceRelative, namespace: namespace});
		}
		var coreProvider:ImportRefreshPackageFamilyCoreProvider = null;
		if (version == 3) {
			var rawProvider:Dynamic = Reflect.field(value, "coreProvider");
			var providerRelative:Dynamic = rawProvider == null ? null : Reflect.field(rawProvider, "rootRelative");
			var providerNamespace:Dynamic = rawProvider == null ? null : Reflect.field(rawProvider, "namespace");
			var providerProjectSha:Dynamic = rawProvider == null ? null : Reflect.field(rawProvider, "projectSha256");
			if (!Std.isOfType(providerRelative, String) || providerRelative != ""
				|| !Std.isOfType(providerNamespace, String) || providerNamespace == ""
				|| !Std.isOfType(providerProjectSha, String) || !isSha256Text(providerProjectSha)
				|| Std.string(providerProjectSha) != Std.string(providerProjectSha).toLowerCase())
				throw "Import package-family core provider identity is invalid.";
			var safeProviderRoot = normalizeRelative("assets/imported_mods/" + Std.string(providerNamespace));
			if (safeProviderRoot != "assets/imported_mods/" + Std.string(providerNamespace))
				throw "Import package-family core provider namespace is invalid.";
			var providerRootRecorded = false;
			for (root in (cast rawRoots:Array<Dynamic>)) {
				ImportWorkScheduler.cooperate();
				if (root != null && Reflect.field(root, "engine") == "Nightmare Vision"
					&& Reflect.field(root, "relative") == ""
					&& Reflect.field(root, "namespace") == providerNamespace)
					providerRootRecorded = true;
			}
			var profileCatalog:Dynamic = Reflect.field(record, "sourceAssetProfiles");
			var profileRoots:Dynamic = profileCatalog == null ? null : Reflect.field(profileCatalog, "roots");
			var providerProfileFound = false;
			if (Std.isOfType(profileRoots, Array)) for (profileEntry in (cast profileRoots:Array<Dynamic>)) {
				ImportWorkScheduler.cooperate();
				var profile:Dynamic = profileEntry == null ? null : Reflect.field(profileEntry, "profile");
				if (profileEntry != null && Reflect.field(profileEntry, "engine") == "Nightmare Vision"
					&& Reflect.field(profileEntry, "rootRelative") == ""
					&& Reflect.field(profileEntry, "namespace") == providerNamespace
					&& profile != null && Reflect.field(profile, "provenance") == "receipt-bound"
					&& Reflect.field(profile, "snapshotId") == snapshotId
					&& Reflect.field(profile, "sourceEngine") == "Nightmare Vision"
					&& Reflect.field(profile, "rootRelative") == ""
					&& Reflect.field(profile, "namespace") == providerNamespace
					&& Reflect.field(profile, "projectSha256") == providerProjectSha)
					providerProfileFound = true;
			}
			if (!providerRootRecorded || !providerProfileFound)
				throw "Import package-family core provider is not the exact retained root profile.";
			for (member in members) {
				var receiverRootRecorded = false;
				for (root in (cast rawRoots:Array<Dynamic>)) {
					ImportWorkScheduler.cooperate();
					var relative:Dynamic = root == null ? null : Reflect.field(root, "relative");
					if (root != null && Reflect.field(root, "engine") == "Nightmare Vision"
						&& (relative == member.sourceRelative || relative == member.sourceRelative + "/assets")
						&& Reflect.field(root, "namespace") == member.namespace)
						receiverRootRecorded = true;
				}
				if (!receiverRootRecorded)
					throw "Import package-family core receiver is not an exact retained member root.";
			}
			coreProvider = {rootRelative:"", namespace:cast providerNamespace,
				projectSha256:Std.string(providerProjectSha)};
		}
		members.sort(function(a, b) {
			var folded = Reflect.compare(a.sourceRelative.toLowerCase(), b.sourceRelative.toLowerCase());
			return folded != 0 ? folded : Reflect.compare(a.sourceRelative, b.sourceRelative);
		});
		var ownsMember = false;
		var hasFamilyEngine = false;
		for (root in (cast rawRoots:Array<Dynamic>)) {
			ImportWorkScheduler.cooperate();
			if (root == null || Reflect.field(root, "engine") != "Nightmare Vision") continue;
			hasFamilyEngine = true;
			if (version >= 2) continue;
			var relative:Dynamic = Reflect.field(root, "relative");
			var label:Dynamic = Reflect.field(root, "label");
			var namespace:Dynamic = Reflect.field(root, "namespace");
			if (!Std.isOfType(relative, String) || !Std.isOfType(label, String)
				|| !Std.isOfType(namespace, String) || namespace == "") continue;
			var safeNamespace = normalizeRelative("assets/imported_mods/" + Std.string(namespace));
			if (safeNamespace != "assets/imported_mods/" + Std.string(namespace))
				throw "Import package-family destination namespace is invalid.";
			for (member in members) {
				ImportWorkScheduler.cooperate();
				if (relative == member.sourceRelative && label == member.directory) ownsMember = true;
			}
		}
		if (version == 1 && !ownsMember)
			throw "Import package-family catalog does not include an imported source root.";
		if (version >= 2 && !hasFamilyEngine)
			throw "Import package-family catalog has no Nightmare Vision source root.";
		return {
			version: cast version,
			engine: "Nightmare Vision",
			snapshotId: Std.string(snapshotId).toLowerCase(),
			containerRelative: cast container,
			members: members,
			coreProvider: coreProvider
		};
	}

	/** A v2 namespace is authoritative only when this transaction owns the
	 * at least one package runtime file outside the
	 * shared engine-core subtree. */
	static function validatePackageFamilyOutputs(catalog:ImportRefreshPackageFamilyCatalog,
		files:Array<Dynamic>):Void {
		if (catalog == null || catalog.version < 2 || catalog.members == null) return;
		for (member in catalog.members) {
			ImportWorkScheduler.cooperate();
			var prefix = "assets/imported_mods/" + member.namespace + "/";
			var hasRuntime = false;
			for (file in files) {
				ImportWorkScheduler.cooperate();
				var path:String = Std.isOfType(file, String) ? cast file : Std.string(Reflect.field(file, "path"));
				if (ImportPackageRuntimeOwnership.isPayload(path, "assets/imported_mods/" + member.namespace))
					hasRuntime = true;
			}
			if (!hasRuntime)
				throw "Import package-family member lacks transaction-owned runtime files.";
			if (catalog.version >= 3) {
				var coreIndexPath = prefix + SourceLimeAssetIdentity.sidecarRelativePath(
					"Nightmare Vision", "core");
				var hasCoreIndex = false;
				for (file in files) {
					ImportWorkScheduler.cooperate();
					var path:String = Std.isOfType(file, String) ? cast file : Std.string(Reflect.field(file, "path"));
					if (pathTextKey(path) == pathTextKey(coreIndexPath)) hasCoreIndex = true;
				}
			if (!hasCoreIndex)
					throw "Import package-family core handoff lacks a receiver-owned identity index.";
			}
		}
	}

	static function pathTextKey(value:String):String {
		var normalized = value == null ? "" : StringTools.replace(Path.normalize(value), "\\", "/");
		#if windows
		return normalized.toLowerCase();
		#else
		return normalized;
		#end
	}

	static function isSha256Text(value:Dynamic):Bool {
		if (!Std.isOfType(value, String)) return false;
		var text:String = cast value;
		if (text.length != 64) return false;
		for (index in 0...text.length) {
			var code = text.charCodeAt(index);
			if (!((code >= 48 && code <= 57) || (code >= 97 && code <= 102) || (code >= 65 && code <= 70)))
				return false;
		}
		return true;
	}

	static function applyOperation(install:String, staging:String, transactionPath:String, transactionId:String,
		operation:Dynamic, cancelCheck:Null<Void->Bool>):Void {
		var relative = Std.string(Reflect.field(operation, "path"));
		var target = safeChild(install, relative, false);
		var expectedBefore = Std.string(Reflect.field(operation, "beforeSha256"));
		var hadBefore:Bool = Reflect.field(operation, "beforeExists");
		if (hadBefore) {
			if (!FileSystem.exists(target) || !isRegularFile(target)
				|| ImportSourceSnapshot.sha256File(target, CHUNK_SIZE) != expectedBefore)
				throw 'Installed file changed after preflight: $relative';
		} else if (FileSystem.exists(target)) {
			throw 'A destination appeared after preflight: $relative';
		}
		if (!Reflect.field(operation, "afterExists")) {
			if (FileSystem.exists(target)) FileSystem.deleteFile(target);
			return;
		}
		var sourceRel = Std.string(Reflect.field(operation, "stagedPath"));
		var source = safeChild(staging, sourceRel, true);
		var expectedAfter = Std.string(Reflect.field(operation, "afterSha256"));
		var parent = Path.directory(target);
		assertSafeExistingAncestors(install, parent);
		if (!FileSystem.exists(parent)) FileSystem.createDirectory(parent);
		assertSafeExistingAncestors(install, target);
		var tempPath = target + ".codex-import-" + transactionId + "-" + digestText(relative).substr(0, 12) + ".tmp";
		if (FileSystem.exists(tempPath)) throw 'Transaction temporary path already exists: $tempPath';
		var copiedHash = copyAndHash(source, tempPath, cancelCheck);
		if (copiedHash != expectedAfter) throw 'Staged output changed while copying: $sourceRel';
		if (FileSystem.exists(target)) FileSystem.deleteFile(target);
		FileSystem.rename(tempPath, target);
		if (ImportSourceSnapshot.sha256File(target, CHUNK_SIZE) != expectedAfter)
			throw 'Installed output failed post-copy verification: $relative';
	}

	static function rollback(transactionPath:String, install:String, state:String, owner:String):Array<ImportRefreshConflict> {
		var journal = latestJournal(transactionPath);
		if (journal == null) return [];
		return rollbackFromJournal(transactionPath, install, state, journal);
	}

	static function rollbackFromJournal(transactionPath:String, install:String, state:String, journal:Dynamic):Array<ImportRefreshConflict> {
		ImportWorkScheduler.cooperate();
		var conflicts:Array<ImportRefreshConflict> = [];
		var owner = Std.string(Reflect.field(journal, "owner"));
		var roots:Array<String>;
		try roots = normalizeOwnedRoots(cast Reflect.field(journal, "ownedRoots")) catch (error:Dynamic) {
			return [{path: transactionPath, reason: 'Journal owned roots are invalid: ${Std.string(error)}'}];
		}
		var operations:Dynamic = Reflect.field(journal, "operations");
		if (!Std.isOfType(operations, Array))
			return [{path: transactionPath, reason: "Journal operation list is invalid."}];
		var operationList:Array<Dynamic> = cast operations;
		var index = operationList.length - 1;
		while (index >= 0) {
			ImportWorkScheduler.cooperate();
			var operation = operationList[index];
			index--;
			var relative = Std.string(Reflect.field(operation, "path"));
			try {
				if (!isWithinOwnedRoots(relative, roots)) throw "Journal target is outside its owned roots.";
				if (isProtectedSettingsPath(relative)) throw "The user settings file is protected from import refresh.";
				var target = safeChild(install, relative, false);
				var transactionId = Std.string(Reflect.field(journal, "transactionId"));
				var tempPath = target + ".codex-import-" + transactionId + "-" + digestText(relative).substr(0, 12) + ".tmp";
				if (FileSystem.exists(tempPath)) {
					var safeTemp = safeChild(install, relative + ".codex-import-" + transactionId + "-" + digestText(relative).substr(0, 12) + ".tmp", true);
					if (!isRegularFile(safeTemp)) throw "An interrupted transaction temporary is not a regular file.";
					FileSystem.deleteFile(safeTemp);
				}
				var beforeExists:Bool = Reflect.field(operation, "beforeExists");
				var afterExists:Bool = Reflect.field(operation, "afterExists");
				var beforeHash = Std.string(Reflect.field(operation, "beforeSha256"));
				var afterHash = Std.string(Reflect.field(operation, "afterSha256"));
				var exists = FileSystem.exists(target);
				if (!beforeExists) {
					if (exists) {
						if (!isRegularFile(target) || !afterExists || ImportSourceSnapshot.sha256File(target, CHUNK_SIZE) != afterHash)
							throw "A new destination changed after interruption; preserving it.";
						FileSystem.deleteFile(target);
					}
				} else {
					var backupRel = Std.string(Reflect.field(operation, "backupPath"));
					if (backupRel == "") throw "The transaction backup path is missing.";
					var backup = safeChild(transactionPath, backupRel, true);
					if (!isRegularFile(backup) || ImportSourceSnapshot.sha256File(backup, CHUNK_SIZE) != beforeHash)
						throw "The transaction backup is missing or has an invalid hash.";
					if (exists) {
						if (!isRegularFile(target)) throw "The destination is no longer a regular file.";
						var currentHash = ImportSourceSnapshot.sha256File(target, CHUNK_SIZE);
						if (currentHash == beforeHash) continue;
						if (afterExists && currentHash != afterHash)
							throw "The destination was edited after interruption; preserving local bytes.";
					}
					var parent = Path.directory(target);
					assertSafeExistingAncestors(install, parent);
					if (!FileSystem.exists(parent)) FileSystem.createDirectory(parent);
					assertSafeExistingAncestors(install, target);
					var restoreTemp = target + ".codex-import-restore-" + Std.string(Reflect.field(journal, "transactionId"))
						+ "-" + digestText(relative).substr(0, 12) + ".tmp";
					if (FileSystem.exists(restoreTemp)) FileSystem.deleteFile(restoreTemp);
					var restoredHash = copyAndHash(backup, restoreTemp, null);
					if (restoredHash != beforeHash) throw "Restored backup failed hash verification.";
					if (FileSystem.exists(target)) FileSystem.deleteFile(target);
					FileSystem.rename(restoreTemp, target);
				}
			} catch (error:Dynamic) {
				conflicts.push({path: relative, reason: Std.string(error)});
			}
		}

		ImportWorkScheduler.cooperate();
		try {
			var manifestPath = currentManifestPath(state, owner);
			var beforeExists:Bool = Reflect.field(journal, "manifestBeforeExists");
			var beforeHash = Std.string(Reflect.field(journal, "manifestBeforeSha256"));
			var afterHash = Std.string(Reflect.field(journal, "manifestAfterSha256"));
			var exists = FileSystem.exists(manifestPath);
			if (!beforeExists) {
				if (exists) {
					var currentHash = ImportSourceSnapshot.sha256File(manifestPath, CHUNK_SIZE);
					if (currentHash != afterHash) throw "The new manifest changed after interruption; preserving it.";
					FileSystem.deleteFile(manifestPath);
				}
			} else {
				var backupRel = Std.string(Reflect.field(journal, "manifestBackupPath"));
				var backup = safeChild(transactionPath, backupRel, true);
				if (ImportSourceSnapshot.sha256File(backup, CHUNK_SIZE) != beforeHash)
					throw "The previous manifest backup has an invalid hash.";
				if (exists) {
					var currentHash = ImportSourceSnapshot.sha256File(manifestPath, CHUNK_SIZE);
					if (currentHash == beforeHash) {
						// The manifest had not yet been replaced.
					} else if (currentHash != afterHash) {
						throw "The manifest was edited after interruption; preserving it.";
					} else {
						atomicCopyReplace(backup, manifestPath, "restore-manifest-" + Std.string(Reflect.field(journal, "transactionId")), beforeHash);
					}
				} else {
					atomicCopyReplace(backup, manifestPath, "restore-manifest-" + Std.string(Reflect.field(journal, "transactionId")), beforeHash);
				}
			}
			if (conflicts.length == 0) {
				Reflect.setField(journal, "phase", "rolled-back");
				writeJournal(transactionPath, journal);
			}
		} catch (error:Dynamic) {
			conflicts.push({path: "manifest.json", reason: Std.string(error)});
		}
		return conflicts;
	}

	static function atomicCopyReplace(source:String, destination:String, suffix:String, expectedHash:String):Void {
		var temp = destination + ".codex-import-" + suffix + ".tmp";
		if (FileSystem.exists(temp)) FileSystem.deleteFile(temp);
		var copiedHash = copyAndHash(source, temp, null);
		if (copiedHash != expectedHash) throw "Copy for atomic replacement failed hash verification.";
		if (FileSystem.exists(destination)) FileSystem.deleteFile(destination);
		FileSystem.rename(temp, destination);
	}

	static function latestJournal(transactionPath:String, ?cancelCheck:Void->Bool):Dynamic {
		checkpointWork(cancelCheck);
		if (!FileSystem.exists(transactionPath) || !FileSystem.isDirectory(transactionPath)) return null;
		var names = FileSystem.readDirectory(transactionPath);
		var candidates:Array<{path:String, sequence:Int}> = [];
		for (name in names) {
			if (!StringTools.startsWith(name, "journal-") || !StringTools.endsWith(name, ".json")) continue;
			var middle = name.substr(8, name.length - 13);
			var sequence = Std.parseInt(middle);
			if (sequence == null || sequence <= 0) continue;
			candidates.push({path: Path.join([transactionPath, name]), sequence: sequence});
		}
		candidates.sort(function(a, b) return b.sequence - a.sequence);
		for (candidate in candidates) {
			checkpointWork(cancelCheck);
			try {
				var journal:Dynamic = Json.parse(File.getContent(candidate.path));
				if (Reflect.field(journal, "schemaVersion") == MANIFEST_SCHEMA)
					return journal;
			} catch (_:Dynamic) {}
		}
		return null;
	}

	static function writeJournal(transactionPath:String, journal:Dynamic):Void {
		var sequence:Int = Reflect.field(journal, "journalSequence");
		sequence++;
		Reflect.setField(journal, "journalSequence", sequence);
		var name = "journal-" + StringTools.lpad(Std.string(sequence), "0", 8) + ".json";
		var target = Path.join([transactionPath, name]);
		if (FileSystem.exists(target)) throw "Journal sequence path already exists.";
		writeNewText(target, Json.stringify(journal) + "\n", "journal-" + Std.string(sequence));
	}

	static function validateReceipt(receiptPath:String, journal:Dynamic):Void {
		if (!isRegularFile(receiptPath)) throw "Commit receipt is not a regular file.";
		var receipt:Dynamic = Json.parse(File.getContent(receiptPath));
		if (Reflect.field(receipt, "status") != STATUS_APPLIED
			|| Reflect.field(receipt, "owner") != Reflect.field(journal, "owner")
			|| Reflect.field(receipt, "transactionId") != Reflect.field(journal, "transactionId")
			|| Reflect.field(receipt, "manifestSha256") != Reflect.field(journal, "manifestAfterSha256"))
			throw "Commit receipt does not match its transaction journal.";
	}

	/** Rollback copies are required until the commit receipt is valid. After
	 * that point, the current installation and retained source snapshot are the
	 * recoverable state; keeping a full prior copy for every refresh only grows
	 * import-cache indefinitely. Remove only hash-named backups named by this
	 * transaction's journal, leaving its small journal and receipt for audit. */
	static function cleanupCommittedBackups(transactionPath:String, journal:Dynamic):Void {
		try {
			ImportWorkScheduler.cooperate();
			var backupPaths:Array<String> = [];
			if (Reflect.field(journal, "manifestBeforeExists") == true) {
				var expectedManifest = Path.join(["backups", "files", digestText("manifest.json") + ".bak"]);
				var recordedManifest = Std.string(Reflect.field(journal, "manifestBackupPath"));
				if (recordedManifest != expectedManifest) return;
				backupPaths.push(expectedManifest);
			}
			var operations:Dynamic = Reflect.field(journal, "operations");
			if (!Std.isOfType(operations, Array)) return;
			for (operation in (cast operations:Array<Dynamic>)) {
				ImportWorkScheduler.cooperate();
				if (operation == null || Reflect.field(operation, "beforeExists") != true)
					continue;
				var relative = Std.string(Reflect.field(operation, "path"));
				var expected = Path.join(["backups", "files", digestText(relative) + ".bak"]);
				var recorded = Std.string(Reflect.field(operation, "backupPath"));
				if (recorded != expected) return;
				backupPaths.push(expected);
			}

			var resolved:Array<String> = [];
			for (relative in backupPaths) {
				ImportWorkScheduler.cooperate();
				var path = safeChild(transactionPath, relative, false);
				if (FileSystem.exists(path) && !isRegularFile(path)) return;
				resolved.push(path);
			}
			for (path in resolved) {
				ImportWorkScheduler.cooperate();
				if (FileSystem.exists(path)) FileSystem.deleteFile(path);
			}

			for (relative in ["backups/files", "backups"]) {
				ImportWorkScheduler.cooperate();
				var directory = safeChild(transactionPath, relative, false);
				if (FileSystem.exists(directory) && FileSystem.isDirectory(directory)
					&& FileSystem.readDirectory(directory).length == 0)
					FileSystem.deleteDirectory(directory);
			}
		} catch (_:Dynamic) {
			// Cleanup is storage maintenance after a committed import. A locked or
			// unfamiliar backup remains available for diagnosis and must not turn a
			// successful import into a reported failure.
		}
	}

	static function normalizeOwnedRoots(values:Array<String>):Array<String> {
		if (values == null || values.length == 0) throw "At least one owned root is required.";
		var result:Array<String> = [];
		var seen:Map<String, Bool> = new Map();
		for (value in values) {
			var root = normalizeRelative(value);
			var folded = root.toLowerCase();
			if (seen.exists(folded)) throw 'Duplicate or case-colliding owned root: $root';
			seen.set(folded, true);
			result.push(root);
		}
		result.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		return result;
	}

	static function normalizeRelative(value:String):String {
		if (value == null || value == "") throw "Relative path cannot be empty.";
		var normalized = StringTools.replace(value, "\\", "/");
		if (StringTools.startsWith(normalized, "/") || Path.isAbsolute(normalized) || normalized.indexOf(":") >= 0)
			throw 'Absolute or drive-qualified path is not allowed: $value';
		var parts = normalized.split("/");
		if (parts.length == 0) throw 'Invalid relative path: $value';
		for (part in parts) {
			if (part == "" || part == "." || part == "..") throw 'Unsafe path segment in: $value';
			if (part.charCodeAt(part.length - 1) == 32 || part.charCodeAt(part.length - 1) == 46)
				throw 'Windows-ambiguous path segment in: $value';
			for (index in 0...part.length) {
				var code = part.charCodeAt(index);
				if (code < 32 || code == 127 || part.indexOf("<") >= 0 || part.indexOf(">") >= 0
					|| part.indexOf("\"") >= 0 || part.indexOf("|") >= 0 || part.indexOf("?") >= 0 || part.indexOf("*") >= 0)
					throw 'Invalid portable path segment in: $value';
			}
			var basename = part.split(".")[0].toUpperCase();
			if (basename == "CON" || basename == "PRN" || basename == "AUX" || basename == "NUL"
				|| isNumberedDeviceName(basename, "COM") || isNumberedDeviceName(basename, "LPT"))
				throw 'Reserved Windows path segment in: $value';
		}
		return parts.join("/");
	}

	static function isNumberedDeviceName(value:String, prefix:String):Bool {
		if (!StringTools.startsWith(value, prefix) || value.length != prefix.length + 1) return false;
		var digit = value.charCodeAt(prefix.length);
		return digit >= 49 && digit <= 57;
	}

	static function isWithinOwnedRoots(relative:String, roots:Array<String>):Bool {
		for (root in roots) if (relative == root || StringTools.startsWith(relative, root + "/")) return true;
		return false;
	}

	static function isProtectedSettingsPath(relative:String):Bool {
		return relative.toLowerCase() == SETTINGS_PATH;
	}

	static function validateHash(value:String, description:String):Void {
		if (value == null || value.length != 64) throw 'Invalid SHA-256 value for $description.';
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			var hex = (code >= 48 && code <= 57) || (code >= 97 && code <= 102) || (code >= 65 && code <= 70);
			if (!hex) throw 'Invalid SHA-256 value for $description.';
		}
	}

	static function canonicalDirectory(path:String, create:Bool):String {
		if (create && !FileSystem.exists(path)) FileSystem.createDirectory(path);
		if (!FileSystem.exists(path) || !FileSystem.isDirectory(path)) throw 'Not a directory: $path';
		return Path.normalize(FileSystem.fullPath(path));
	}

	static function ensureDirectoryUnder(root:String, path:String):Void {
		if (FileSystem.exists(path)) {
			if (!FileSystem.isDirectory(path)) throw 'Expected a directory: $path';
			var resolved = Path.normalize(FileSystem.fullPath(path));
			if (!samePath(resolved, Path.normalize(path))) throw 'Symlink in transaction state path: $path';
			return;
		}
		var parent = Path.directory(path);
		if (parent != path && !FileSystem.exists(parent)) ensureDirectoryUnder(root, parent);
		FileSystem.createDirectory(path);
		var resolved = Path.normalize(FileSystem.fullPath(path));
		if (!samePath(resolved, Path.normalize(path))) throw 'Transaction state escaped its root: $path';
		assertInside(path, root);
	}

	static function safeChild(root:String, relative:String, requireExists:Bool):String {
		var rel = normalizeRelative(relative);
		var candidate = Path.normalize(Path.join([root, rel]));
		assertInside(candidate, root);
		var current = root;
		for (part in rel.split("/")) {
			current = Path.join([current, part]);
			if (!FileSystem.exists(current)) continue;
			var resolved = Path.normalize(FileSystem.fullPath(current));
			if (!samePath(resolved, Path.normalize(current))) throw 'Symlink in protected path: $relative';
		}
		if (requireExists && !FileSystem.exists(candidate)) throw 'Required file is missing: $relative';
		return candidate;
	}

	static function assertSafeExistingAncestors(root:String, path:String):Void {
		var absolute = Path.normalize(path);
		assertInside(absolute, root);
		var relative = absolute.substr(Path.addTrailingSlash(root).length);
		var current = root;
		var parts = relative.split("/");
		for (part in parts) {
			current = Path.join([current, part]);
			if (!FileSystem.exists(current)) continue;
			if (!samePath(Path.normalize(FileSystem.fullPath(current)), Path.normalize(current)))
				throw 'Symlink in protected path: $path';
		}
	}

	static function assertInside(candidate:String, root:String):Void {
		var base = Path.addTrailingSlash(Path.normalize(root));
		var value = Path.normalize(candidate);
		if (!samePath(value, Path.normalize(root)) && !samePath(value.substr(0, base.length), base))
			throw 'Path escapes protected root: $candidate';
	}

	static function assertNotInside(candidate:String, protectedRoot:String, relative:String):Void {
		if (samePath(candidate, protectedRoot) || samePath(candidate.substr(0, Path.addTrailingSlash(protectedRoot).length), Path.addTrailingSlash(protectedRoot)))
			throw 'Output overlaps transaction state and is protected: $relative';
	}

	static function samePath(a:String, b:String):Bool {
		#if windows
		return a.toLowerCase() == b.toLowerCase();
		#else
		return a == b;
		#end
	}

	static function isRegularFile(path:String):Bool {
		return FileSystem.exists(path) && !FileSystem.isDirectory(path);
	}

	static function currentManifestPath(state:String, owner:String):String {
		return Path.join([state, digestText(owner), "manifest.json"]);
	}

	static function relativePathFrom(root:String, path:String):String {
		var base = Path.addTrailingSlash(Path.normalize(root));
		var value = Path.normalize(path);
		if (!samePath(value.substr(0, base.length), base)) throw 'Path is outside transaction root: $path';
		return value.substr(base.length);
	}

	static function makeTransactionId():String {
		return "txn-" + Std.string(Std.int(Sys.time() * 1000)) + "-" + Std.string(Std.random(0x7fffffff));
	}

	static function result(status:String, conflicts:Array<ImportRefreshConflict>, manifest:String,
		receipt:String, transaction:String):ImportRefreshResult {
		return {status: status, conflicts: conflicts, manifestPath: manifest, receiptPath: receipt, transactionPath: transaction};
	}

	static function checkCancelled(callback:Null<Void->Bool>):Bool {
		return callback != null && callback();
	}

	/** Pause only at a caller-owned safe boundary; cancellation is honored before
	 * the journaled publication window, never between a destination mutation and
	 * the matching manifest or rollback bookkeeping. */
	static function checkpointWork(cancelCheck:Null<Void->Bool>):Void {
		if (checkCancelled(cancelCheck)) throw new ImportWorkCancelled();
		if (!ImportWorkScheduler.cooperate(function() return checkCancelled(cancelCheck)))
			throw new ImportWorkCancelled();
		if (checkCancelled(cancelCheck)) throw new ImportWorkCancelled();
	}

	static function reportProgress(callback:Null<Dynamic->Void>, phase:String, current:String,
		completed:Int, total:Int):Void {
		if (callback == null) return;
		// Progress observers must not change import commit or rollback behavior.
		try callback({phase: phase, current: current, completed: completed, total: total}) catch (_:Dynamic) {}
	}

	static function digestText(value:String):String {
		return Sha256.make(Bytes.ofString(value)).toHex();
	}

	static function copyAndHash(source:String, destination:String, cancelCheck:Null<Void->Bool>):String {
		var input = File.read(source, true);
		var output:FileOutput = null;
		var hash = new ImportSnapshotSha256();
		var buffer = Bytes.alloc(CHUNK_SIZE);
		try {
			output = File.write(destination, true);
			while (true) {
				if (!ImportWorkScheduler.cooperate(function() return checkCancelled(cancelCheck))) throw CANCEL_TOKEN;
				if (checkCancelled(cancelCheck)) throw CANCEL_TOKEN;
				var count:Int;
				try count = input.readBytes(buffer, 0, buffer.length) catch (_:Eof) break;
				if (count <= 0) break;
				hash.update(buffer, 0, count);
				var written = 0;
				while (written < count) {
					var added = output.writeBytes(buffer, written, count - written);
					if (added <= 0) throw "A streamed import file copy stopped making progress.";
					written += added;
				}
			}
			output.close();
			output = null;
			input.close();
			input = null;
			return hash.digestHex();
		} catch (error:Dynamic) {
			if (output != null) try output.close() catch (_:Dynamic) {}
			if (input != null) try input.close() catch (_:Dynamic) {}
			if (FileSystem.exists(destination)) try FileSystem.deleteFile(destination) catch (_:Dynamic) {}
			throw error;
		}
	}

	static function atomicReplaceText(path:String, text:String, suffix:String):Void {
		var temp = path + ".codex-import-" + suffix + ".tmp";
		if (FileSystem.exists(temp)) FileSystem.deleteFile(temp);
		File.saveContent(temp, text);
		if (FileSystem.exists(path)) FileSystem.deleteFile(path);
		FileSystem.rename(temp, path);
	}

	static function writeNewText(path:String, text:String, suffix:String):Void {
		if (FileSystem.exists(path)) throw 'Transaction file already exists: $path';
		var temp = path + ".codex-import-" + suffix + ".tmp";
		if (FileSystem.exists(temp)) throw 'Transaction temporary file already exists: $temp';
		File.saveContent(temp, text);
		FileSystem.rename(temp, path);
	}
}
