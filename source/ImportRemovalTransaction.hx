package;

import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import ImportRefreshTransaction.ImportRefreshManifest;

typedef ImportRemovalResult = {
	var status:String;
	var blockers:Array<String>;
	var affectedOwners:Array<String>;
	var transactionId:String;
}

/** Worker-only removal executor. The caller holds the importer and runtime owner
 * reservations from confirmation through publication and its main-thread handoff.
 * Every live mutation has a durable journal and a verified rollback copy. */
class ImportRemovalTransaction {
	public static inline var STATE:String = 'import-cache/removal-state';
	static inline var OWNER:String = 'managed-import-removal';
	static inline var CANCEL:String = '__REMOVAL_CANCELLED__';

	public static function preview(install:String, selected:Array<String>, protectedRoots:Array<String>,
		?activeOwners:Array<String>, ?cancel:Void->Bool):ImportRemovalPlan {
		var manifests = inventory(install,cancel);
		var audit = ImportInstalledOwnership.inspect(install,manifests,protectedRoots,cancel,true);
		var chosen = selected == null ? [] : selected.copy();
		var plan:ImportRemovalPlan = null;
		var rounds = 0;
		// A package can be tied to others: one import may have installed several and
		// be unable to give up just one, and other imports may load content from it.
		// Rather than refuse, grow the request until nothing left behind needs what
		// goes. The caller sees the additions in linkedOwners and confirms them.
		while (true) {
			plan = ImportRemovalPlan.assess(chosen,manifests,true,activeOwners,function() check(cancel));
			if (!audit.complete || !plan.inventoryComplete) break;
			var whole = plan.affectedOwners.copy();
			var more:Array<String> = [];
			try ImportRemovalPartition.prepare(install,plan,manifests,audit.charts,cancel) catch (error:Dynamic) {
				if (cancel != null && cancel()) throw error;
				// This import cannot be split, so it goes as a whole or not at all.
				more = [for (root in whole) if (plan.selectedOwners.indexOf(root) < 0) root];
				if (more.length == 0) throw error;
			}
			if (more.length == 0) more = plan.relink();
			if (more.length == 0 || ++rounds > 64) break;
			for (root in more) if (chosen.indexOf(root) < 0) chosen.push(root);
		}
		if (selected != null && audit.complete && plan.inventoryComplete) plan.markLinked(selected);
		if (audit.complete) {
			var claims:Map<String,Bool> = new Map();
			for (manifest in manifests) for (file in manifest.files) claims.set(file.path.toLowerCase(),true);
			var directories = plan.selectedOwners.copy();
			for (chart in audit.charts) if (plan.selectedOwners.indexOf(chart.ownerRoot) >= 0) {
				directories.push('assets/data/' + chart.folder); directories.push('assets/songs/' + chart.folder);
			}
			for (directory in directories) inspectUnclaimed(install,directory,claims,plan.blockers,cancel);
		}
		if (protectedRoots != null) for (root in protectedRoots) if (plan.selectedOwners.indexOf(ImportRemovalPlan.ownerRoot(root)) >= 0) plan.blockers.push("Bundled engine content cannot be removed.");
		if (!audit.complete) {
			for (blocker in audit.blockers) plan.blockers.push(blocker);
			plan.blockers.push("Reimport this package to create committed ownership before removal.");
		}
		return plan;
	}

	static function inspectUnclaimed(install:String,relative:String,claims:Map<String,Bool>,blockers:Array<String>,cancel:Void->Bool):Void {
		var stack = [relative]; var count = 0;
		while (stack.length > 0) {
			check(cancel); var path = stack.pop(); var target = safe(install,path);
			if (!FileSystem.exists(target)) continue;
			if (FileSystem.isDirectory(target)) {
				for (name in FileSystem.readDirectory(target)) stack.push(path + '/' + name);
			} else if (!claims.exists(path.toLowerCase())) {
				blockers.push('Unowned local file preserved. Move it outside this package before removal: ' + path);
			}
			if (++count + stack.length > 1000000) throw 'Package file inventory limit exceeded.';
		}
	}
	static function inventory(install:String, cancel:Void->Bool):Array<ImportRefreshManifest>
		return ImportRefreshTransaction.inspectRetainedManifests(install,Path.join([install,'import-cache/state']),
			Path.join([install,'import-cache/records']),cancel);
	static function check(cancel:Void->Bool):Void {
		ImportRefreshTransaction.checkpointWork(cancel);
		if (cancel != null && cancel()) throw CANCEL;
	}
	static function digest(path:String):String return ImportSourceSnapshot.sha256File(path,65536);
	/** A staged text file still holds what its journal recorded. Journals from before
	 * the byte-exact hash recorded Sha256.encode of the text, which is wrong for
	 * non-ASCII text; accepting that value too lets those interrupted removals finish
	 * cleaning up instead of staying locked forever. */
	static function stagedTextMatches(path:String, expected:String):Bool {
		if (digest(path) == expected) return true;
		try return Sha256.encode(File.getContent(path)) == expected catch (_:Dynamic) return false;
	}
	// UTF-8 bytes, the same digest as the files these texts are written to and as
	// ImportRefreshTransaction.digestText. Sha256.encode counts characters, not bytes,
	// so any manifest, registry or path with non-ASCII text never matched its file
	// and every such removal rolled back. ASCII text hashes exactly as before.
	static function key(text:String):String return Sha256.make(haxe.io.Bytes.ofString(text)).toHex();
	static function safe(root:String,path:String,exists:Bool = false):String
		return ImportRefreshTransaction.safeChild(root,path,exists);

	public static function apply(install:String, reviewed:ImportRemovalPlan, protectedRoots:Array<String>,
		?cancel:Void->Bool, ?progress:Dynamic->Void):ImportRemovalResult {
		install = ImportRefreshTransaction.canonicalDirectory(install,false);
		var id = ''; var txn = ''; var journal:Dynamic = null;
		var operations:Array<Dynamic> = [];
		var state = Path.join([install,STATE]); var token = 0;
		try {
			var recovery = recover(install);
			if (recovery.length > 0) throw recovery.join('; ');
			check(cancel);
			if (reviewed == null || reviewed.blockers.length > 0 || !reviewed.inventoryComplete)
				throw 'The removal preview has unresolved blockers.';
			var current = preview(install,reviewed.selectedOwners,protectedRoots,[],cancel);
			if (current.blockers.length > 0) throw current.blockers.join('; ');
			if (fingerprint(current) != fingerprint(reviewed)) throw 'Installed ownership changed. Review the removal again.';
			var manifests = inventory(install,cancel);
			var audit = ImportInstalledOwnership.inspect(install,manifests,protectedRoots,cancel,true);
			var partition = ImportRemovalPartition.prepare(install,current,manifests,audit.charts,cancel);
			// Persist identity history before any installed file is changed. Saves,
			// favorites, categories, difficulty preferences and settings are retained.
			LibraryIdentityArchive.prepare(install,current.affectedOwners,protectedRoots,cancel);
			check(cancel);
			id = ImportRefreshTransaction.makeTransactionId();
			var scope = safe(install,STATE);
			ImportRefreshTransaction.ensureDirectoryUnder(install,scope + '/transactions');
			txn = safe(install,STATE + '/transactions/' + id);
			ImportRefreshTransaction.ensureDirectoryUnder(install,txn + '/backups/files');
			ImportRefreshTransaction.ensureDirectoryUnder(install,txn + '/staging');
			var scopes:Array<Dynamic> = [];
			var registries:Map<String,String> = new Map();
			for (file in current.candidateFiles) addOperation(install,txn,operations,file.path,file.sha256,null,cancel);
			for (manifest in manifests) if (current.transactionOwners.indexOf(manifest.owner) >= 0) {
				var record:Dynamic = Reflect.field(manifest.revision,'importRecord');
				var pointer = 'import-cache/records/' + Std.string(Reflect.field(record,'id')) + '.json';
				// An import whose index pointer was lost is still removable; there is just no
				// pointer file to retire with it.
				if (!partition.revisions.exists(manifest.owner) && FileSystem.exists(safe(install,pointer)))
					addOperation(install,txn,operations,pointer,digest(safe(install,pointer,true)),null,cancel);
				var path = 'import-cache/state/' + key(manifest.owner);
				scopes.push({path:path,backupPath:'retired/owner-' + scopes.length,inventory:tree(install,path,cancel),owner:manifest.owner,originalManifestText:File.getContent(safe(install,path + '/manifest.json',true)),
					replacement:partition.revisions.exists(manifest.owner) ? replacementFiles(install,manifest,partition.revisions.get(manifest.owner),partition.retainedFiles.get(manifest.owner),id) : null});
				var values:Array<Dynamic> = cast Reflect.field(manifest.revision,'registries');
				if (values != null) for (value in values) {
					var path:String = value.path;
					var live = registries.exists(path) ? registries.get(path) : File.getContent(safe(install,path,true));
					var prepared = partition.registryGenerated.exists(manifest.owner)
						? ImportRegistryRefresh.merge(value.generated,partition.registryGenerated.get(manifest.owner).get(path),live)
						: ImportRegistryRefresh.prepare(value.before,value.generated,live);
					if (prepared.conflicts.length > 0) throw 'Registry edits preserved: ' + path + ': ' + prepared.conflicts.join('; ');
					registries.set(path,prepared.text);
				}
			}
			for (snapshot in current.candidateSnapshots) {
				var path = 'import-cache/sources/' + snapshot;
				if (FileSystem.exists(safe(install,path))) {
					ImportSourceSnapshot.verify(safe(install,path,true),snapshot,cancel);
					scopes.push({path:path,backupPath:'retired/source-' + scopes.length,inventory:tree(install,path,cancel)});
				}
			}
			for (path in registries.keys()) addOperation(install,txn,operations,path,digest(safe(install,path,true)),registries.get(path),cancel);
			for (entry in scopes) prepareReplacement(entry,registries,install);
			var marker = Json.stringify({schemaVersion:1,owner:OWNER,transactionId:id,removed:current.affectedOwners});
			var markerPath = ImportRefreshTransaction.manifestPath(state,OWNER);
			ImportRefreshTransaction.ensureDirectoryUnder(install,Path.directory(markerPath));
			var markerExists = FileSystem.exists(markerPath);
			var markerHash = markerExists ? digest(markerPath) : '';

			journal = {schemaVersion:1,owner:OWNER,transactionId:id,phase:'preparing',installRoot:install,
				ownedRoots:['assets','import-cache/records'],operations:operations,retiredScopes:scopes,
				manifestBeforeExists:markerExists,manifestBeforeSha256:markerHash,manifestAfterSha256:key(marker),
				manifestBackupPath:markerExists ? 'backups/files/' + key('manifest.json') + '.bak' : '',
				manifestPath:'manifest.json',journalSequence:0,selectedOwners:current.affectedOwners};
			ImportRefreshTransaction.ensureDirectoryUnder(install,txn + '/retired');
			ImportRefreshTransaction.writeJournal(txn,journal);
			for (operation in operations) {
				check(cancel);
				if (progress != null) progress({phase:'backing-up-removal',current:operation.path});
				if (ImportRefreshTransaction.copyAndHash(safe(install,operation.path,true),safe(txn,operation.backupPath),cancel) != operation.beforeSha256)
					throw 'File changed during removal backup: ' + operation.path;
			}
			if (markerExists && ImportRefreshTransaction.copyAndHash(markerPath,txn + '/backups/files/' + key('manifest.json') + '.bak',cancel) != markerHash)
				throw 'Removal marker changed during backup.';
			check(cancel);
			token = ImportWorkScheduler.beginUninterruptedPublication(function() return cancel != null && cancel());
			if (token < 0) throw CANCEL;
			journal.phase = 'prepared';
			ImportRefreshTransaction.writeJournal(txn,journal);
			if (progress != null) progress({phase:"removal-journal-prepared",current:""});
			for (operation in operations) {
				check(cancel);
				if (progress != null) progress({phase:'removing-import',current:operation.path});
				ImportRefreshTransaction.applyOperation(install,txn + '/staging',txn,id,operation,cancel);
				if (progress != null) progress({phase:"removal-file-applied",current:operation.path});
			}
			for (entry in scopes) {
				check(cancel);
				if (Json.stringify(tree(install,entry.path,cancel)) != Json.stringify(entry.inventory)) throw 'Ownership metadata changed before removal.';
				FileSystem.rename(safe(install,entry.path,true),safe(txn,entry.backupPath));
				if (progress != null) progress({phase:"removal-scope-retired",current:entry.path});
				if (entry.replacement != null) publishReplacement(install,entry,registries);
				if (progress != null) progress({phase:"removal-scope-published",current:entry.path});
			}
			check(cancel);
			// Revalidate shared files and all survivors immediately before commit.
			for (manifest in manifests)
				for (file in manifest.files) if (!ImportIO.isRegistry(file.path)
					&& (current.transactionOwners.indexOf(manifest.owner) < 0 || (partition.retainedFiles.exists(manifest.owner)
					&& partition.retainedFiles.get(manifest.owner).indexOf(file.path) >= 0))) {
					check(cancel);
					if (digest(safe(install,file.path,true)) != file.sha256) throw 'Surviving asset changed before removal commit: ' + file.path;
				}
			ImportRefreshTransaction.atomicReplaceText(markerPath,marker,id + '-manifest');
			if (progress != null) progress({phase:'removal-marker-published',current:''});
			journal.phase = 'receipt-pending'; ImportRefreshTransaction.writeJournal(txn,journal);
			ImportRefreshTransaction.writeNewText(txn + '/receipt.json',Json.stringify({schemaVersion:1,status:'applied',owner:OWNER,
				transactionId:id,manifestSha256:key(marker),fileCount:0,removalJournalSha256:journalDigest(txn,journal)}),id + '-receipt');
			validateRemovalReceipt(txn,journal);
			if (progress != null) progress({phase:'removal-committed',current:''});
			ImportWorkScheduler.endUninterruptedPublication(token); token = 0;
			var pending = cleanup(install,txn,journal);
			return {status:pending.length == 0 ? 'applied' : 'cleanup-pending',blockers:pending,affectedOwners:current.affectedOwners,transactionId:id};
		} catch (error:Dynamic) {
			ImportWorkScheduler.endUninterruptedPublication(token);
			if (journal != null && FileSystem.exists(txn + '/receipt.json')) {
				try {
					validateRemovalReceipt(txn,journal);
					return {status:'cleanup-pending',blockers:[Std.string(error)],affectedOwners:cast journal.selectedOwners,transactionId:id};
				} catch (receiptError:Dynamic) {
					return {status:'conflict',blockers:[Std.string(error),Std.string(receiptError)],affectedOwners:cast journal.selectedOwners,transactionId:id};
				}
			}
			if (journal != null && !FileSystem.exists(txn + '/receipt.json')) {
				var failures = journal.phase == 'preparing' ? finishPreparationCleanup(install,txn,journal) : rollback(install,state,txn,journal);
				if (failures.length > 0) return {status:'conflict',blockers:[Std.string(error)].concat(failures),affectedOwners:reviewed.affectedOwners,transactionId:id};
			}
			return {status:Std.string(error) == CANCEL || Std.string(error) == ImportRefreshTransaction.CANCEL_TOKEN || Std.isOfType(error,ImportWorkCancelled) ? 'cancelled' : 'conflict',
				blockers:[Std.string(error)],affectedOwners:reviewed == null ? [] : reviewed.affectedOwners,transactionId:id};
		}
	}
	static function replacementFiles(install:String,manifest:ImportRefreshManifest,revision:Dynamic,retained:Array<String>,id:String):Dynamic {
		var files:Array<Dynamic> = [for (file in manifest.files) if (retained.indexOf(file.path) >= 0)
			{path:file.path,sha256:file.sha256,owner:file.owner}];
		// Registry hashes are calculated from the final globally merged values
		// during preparation, before the parent publication journal is written.
		return {owner:manifest.owner,id:id,roots:manifest.ownedRoots,revision:revision,files:files,metadata:null};
	}
	static function prepareReplacement(entry:Dynamic,registries:Map<String,String>,install:String):Void {
		var replacement:Dynamic = entry.replacement;
		if (replacement == null) return;
		for (file in (cast replacement.files:Array<Dynamic>)) if (registries.exists(file.path)) file.sha256 = key(registries.get(file.path));
		var manifest = Json.stringify({schemaVersion:1,owner:replacement.owner,transactionId:replacement.id,
			ownedRoots:replacement.roots,revision:replacement.revision,files:replacement.files}) + '
';
		var journal = Json.stringify({schemaVersion:1,owner:replacement.owner,transactionId:replacement.id,
			phase:'receipt-pending',installRoot:install,ownedRoots:replacement.roots,operations:[],manifestPath:'manifest.json',
			manifestBeforeExists:false,manifestBeforeSha256:'',manifestAfterSha256:key(manifest),manifestBackupPath:'',journalSequence:1}) + '
';
		var receipt = Json.stringify({schemaVersion:1,status:'applied',owner:replacement.owner,transactionId:replacement.id,
			manifestSha256:key(manifest),fileCount:(cast replacement.files:Array<Dynamic>).length}) + '
';
		replacement.metadata = [{path:'transactions/' + replacement.id + '/journal-00000001.json',text:journal},
			{path:'manifest.json',text:manifest},{path:'transactions/' + replacement.id + '/receipt.json',text:receipt}];
	}
	static function publishReplacement(install:String,entry:Dynamic,registries:Map<String,String>):Void {
		for (file in (cast entry.replacement.files:Array<Dynamic>)) if (digest(safe(install,file.path,true)) != file.sha256)
			throw 'Surviving aggregate file changed: ' + file.path;
		for (file in (cast entry.replacement.metadata:Array<Dynamic>)) {
			var path = safe(install,entry.path + '/' + file.path);
			ImportRefreshTransaction.ensureDirectoryUnder(install,Path.directory(path));
			File.saveContent(path,file.text);
		}
	}
	static function removeReplacement(install:String,entry:Dynamic):Void {
		var expected:Map<String,String> = new Map();
		for (file in (cast entry.replacement.metadata:Array<Dynamic>)) expected.set('/' + file.path,key(file.text));
		var actual = tree(install,entry.path,null);
		for (item in actual) if ((!item.directory && expected.get(item.path) != item.sha256)
			|| (item.directory && item.path != '' && item.path != '/transactions'
				&& item.path != '/transactions/' + entry.replacement.id))
			throw 'Replacement ownership metadata changed; preserving both scopes.';
		actual.sort(function(a,b) return Std.string(b.path).length - Std.string(a.path).length);
		for (item in actual) {
			var path = safe(install,entry.path + item.path,true);
			if (item.directory) FileSystem.deleteDirectory(path); else FileSystem.deleteFile(path);
		}
	}
	static function fingerprint(plan:ImportRemovalPlan):String {
		var versions = [for (owner in plan.transactionVersions.keys()) owner + ':' + plan.transactionVersions.get(owner)]; versions.sort(Reflect.compare);
		return key(Json.stringify([plan.selectedOwners,plan.affectedOwners,plan.candidateFiles,plan.sharedFiles,plan.registryPaths,plan.candidateSnapshots,plan.sharedSnapshots,versions]));
	}
	static function addOperation(install:String,txn:String,operations:Array<Dynamic>,path:String,hash:String,
		after:Null<String>,cancel:Void->Bool):Void {
		check(cancel);
		var target = safe(install,path,true);
		if (!ImportRefreshTransaction.isRegularFile(target) || digest(target) != hash) throw 'Local file edit preserved: ' + path;
		var stage = key(path);
		var output = after == null ? null : {path:path,stagedPath:stage,sha256:key(after)};
		if (after != null) File.saveBytes(safe(txn,'staging/' + stage),haxe.io.Bytes.ofString(after));
		var operation = ImportRefreshTransaction.makeOperation(path,target,after != null,true,hash,output);
		operation.backupPath = 'backups/files/' + key(path) + '.bak';
		operations.push(operation);
	}

	/** Bounded exact inventory also rejects links, reparse points and unfamiliar
	 * files through the same safe-path validator used by import publication. */
	static function tree(root:String,relative:String,cancel:Void->Bool):Array<Dynamic> {
		var result:Array<Dynamic> = []; var stack = [relative];
		while (stack.length > 0) {
			check(cancel); var rel = stack.pop(); var path = safe(root,rel,true);
			if (FileSystem.isDirectory(path)) {
				result.push({path:rel.substr(relative.length),directory:true});
				var names = FileSystem.readDirectory(path); names.sort(Reflect.compare);
				for (name in names) stack.push(rel + '/' + name);
			} else {
				if (!ImportRefreshTransaction.isRegularFile(path)) throw 'Unsafe managed cleanup entry: ' + rel;
				result.push({path:rel.substr(relative.length),directory:false,sha256:digest(path)});
			}
			if (result.length + stack.length > 262144) throw 'Managed cleanup entry limit exceeded.';
		}
		result.sort(function(a,b) return Reflect.compare(a.path,b.path)); return result;
	}
	static function finishPreparationCleanup(install:String,txn:String,journal:Dynamic):Array<String> {
		var failures = cleanup(install,txn,journal);
		if (failures.length == 0) { journal.phase = 'rolled-back'; ImportRefreshTransaction.writeJournal(txn,journal); }
		return failures;
	}
	static function rollback(install:String,state:String,txn:String,journal:Dynamic):Array<String> {
		var failures:Array<String> = [];
		for (entry in (cast journal.retiredScopes:Array<Dynamic>)) try {
			var original = safe(install,entry.path); var backup = safe(txn,entry.backupPath);
			if (FileSystem.exists(backup)) {
				if (FileSystem.exists(original)) {
					if (entry.replacement == null) throw 'Retired owner destination appeared; preserving both copies.';
					removeReplacement(install,entry);
				}
				if (Json.stringify(tree(txn,entry.backupPath,null)) != Json.stringify(entry.inventory)) throw 'Retired owner backup changed.';
				FileSystem.rename(backup,original);
			}
		} catch (error:Dynamic) failures.push(Std.string(error));
		if (failures.length == 0) {
			for (failure in ImportRefreshTransaction.rollbackFromJournal(txn,install,state,journal)) failures.push(failure.reason);
			if (failures.length == 0) failures = failures.concat(cleanup(install,txn,journal));
		}
		return failures;
	}
	static function cleanup(install:String,txn:String,journal:Dynamic):Array<String> {
		var failures:Array<String> = [];
		for (entry in (cast journal.retiredScopes:Array<Dynamic>)) try {
			var path = safe(txn,entry.backupPath);
			if (!FileSystem.exists(path)) continue;
			var actual = tree(txn,entry.backupPath,null);
			// After a cleanup interruption, remaining entries must be a subset of
			// the original authenticated inventory with identical bytes.
			var known:Map<String,String> = new Map();
			for (item in (cast entry.inventory:Array<Dynamic>)) known.set(item.path,Json.stringify(item));
			for (item in actual) if (known.get(item.path) != Json.stringify(item)) throw 'Cleanup bytes changed; preserving quarantine.';
			actual.sort(function(a,b) return Std.string(b.path).length - Std.string(a.path).length);
			for (item in actual) {
				var child = safe(txn,entry.backupPath + item.path,true);
				if (item.directory) FileSystem.deleteDirectory(child);
				else {
					if (digest(child) != item.sha256) throw 'Cleanup file changed; preserving quarantine.';
					FileSystem.deleteFile(child);
				}
			}
		} catch (error:Dynamic) failures.push(Std.string(error));
		ImportRefreshTransaction.cleanupCommittedBackups(txn,journal);
		if (FileSystem.exists(safe(txn,'backups'))) failures.push('Removal backup cleanup is pending.');
		for (operation in (cast journal.operations:Array<Dynamic>)) if (operation.afterExists) try {
			var staged = safe(txn,'staging/' + operation.stagedPath);
			if (FileSystem.exists(staged)) {
				if (!ImportRefreshTransaction.isRegularFile(staged) || !stagedTextMatches(staged, operation.afterSha256))
					throw 'Removal staged cleanup bytes changed; preserving them.';
				FileSystem.deleteFile(staged);
			}
		} catch (error:Dynamic) failures.push(Std.string(error));
		for (relative in ['staging','retired']) try {
			var directory = safe(txn,relative);
			if (FileSystem.exists(directory) && FileSystem.isDirectory(directory) && FileSystem.readDirectory(directory).length == 0)
				FileSystem.deleteDirectory(directory);
		} catch (error:Dynamic) failures.push(Std.string(error));
		// Remove only empty managed directories on paths already authorized by
		// the journal. Unowned/local files keep their enclosing folder intact.
		var parents:Map<String,Bool> = new Map();
		for (operation in (cast journal.operations:Array<Dynamic>)) if (!operation.afterExists) {
			var parent = Path.directory(operation.path);
			while (parent != 'assets' && parent != 'assets/data' && parent != 'assets/songs'
				&& parent != 'assets/images' && parent != 'assets/music' && parent != 'assets/imported_mods'
				&& StringTools.startsWith(parent,'assets/')) { parents.set(parent,true); parent = Path.directory(parent); }
		}
		var directories = [for (parent in parents.keys()) parent];
		directories.sort(function(a,b) return b.length-a.length);
		for (relative in directories) try {
			var path = safe(install,relative);
			if (FileSystem.exists(path) && FileSystem.isDirectory(path) && FileSystem.readDirectory(path).length == 0) FileSystem.deleteDirectory(path);
		} catch (error:Dynamic) failures.push(Std.string(error));
		return failures;
	}
	static function journalDigest(txn:String,journal:Dynamic):String
		return digest(safe(txn,'journal-' + StringTools.lpad(Std.string(journal.journalSequence),'0',8) + '.json',true));
	static function validateRemovalReceipt(txn:String,journal:Dynamic):Void {
		ImportRefreshTransaction.validateReceipt(txn + '/receipt.json',journal);
		var receipt:Dynamic = Json.parse(File.getContent(safe(txn,'receipt.json',true)));
		if (receipt.removalJournalSha256 != journalDigest(txn,journal)) throw 'Removal journal differs from its committed receipt.';
	}
	/** `sameFolder` is waived only for a removal that cannot write into the old
	 * folder any more: a committed one, or one that was already rolled back. */
	static function validateJournalIdentity(install:String,journal:Dynamic,id:String,sameFolder:Bool = true):Void {
		if (journal.schemaVersion != 1 || journal.owner != OWNER || journal.transactionId != id) throw 'Removal recovery identity mismatch.';
		if (sameFolder && !ImportRefreshTransaction.samePath(journal.installRoot,install))
			throw 'Unfinished removal was started in a different install folder; its files were preserved for manual recovery.';
	}
	static function validateJournal(install:String,txn:String,journal:Dynamic,id:String,sameFolder:Bool = true):Void {
		validateJournalIdentity(install,journal,id,sameFolder);
		if (Json.stringify(journal.ownedRoots) != Json.stringify(['assets','import-cache/records'])
			|| !Std.isOfType(journal.operations,Array) || !Std.isOfType(journal.retiredScopes,Array)
			|| !Std.isOfType(journal.selectedOwners,Array)) throw 'Removal recovery identity mismatch.';
		var selected:Array<String> = cast journal.selectedOwners;
		for (owner in selected) if (ImportRemovalPlan.ownerRoot(owner) != owner || owner == 'assets/imported_mods/bundled-vslice-results') throw 'Invalid selected removal owner.';
		var seen:Map<String,Bool> = new Map(); var backups:Map<String,Bool> = new Map();
		var claims:Map<String,String> = new Map(); var snapshots:Map<String,Bool> = new Map();
		for (entry in (cast journal.retiredScopes:Array<Dynamic>)) {
			var path:String = entry.path; var backup:String = entry.backupPath;
			var stateMatch = ~/^import-cache\/state\/([a-f0-9]{64})$/;
			var sourceMatch = ~/^import-cache\/sources\/([a-f0-9]{64})$/;
			if (stateMatch.match(path)) {
				if (!Std.isOfType(entry.originalManifestText,String)) throw 'Missing original committed metadata.';
				var original:ImportRefreshManifest = Json.parse(entry.originalManifestText);
				var claimedManifest = false;
				for (item in (cast entry.inventory:Array<Dynamic>)) if (item.path == '/manifest.json' && !item.directory
					&& item.sha256 == key(entry.originalManifestText)) claimedManifest = true;
				if (!claimedManifest) throw 'Original manifest differs from its retired inventory.';
				// Before commit, verify the original metadata still exists at one
				// of its authorized locations. A receipt-bound committed journal
				// remains verifiable after quarantine cleanup has removed it.
				if (!FileSystem.exists(safe(txn,'receipt.json'))) {
					var origin = FileSystem.exists(safe(txn,backup)) ? safe(txn,backup) : safe(install,path,true);
					if (File.getContent(safe(origin,'manifest.json',true)) != entry.originalManifestText)
						throw 'Original ownership metadata changed after interruption.';
					var receipt:Dynamic = Json.parse(File.getContent(safe(origin,'transactions/' + original.transactionId + '/receipt.json',true)));
					if (receipt.owner != original.owner || receipt.transactionId != original.transactionId
						|| receipt.manifestSha256 != key(entry.originalManifestText)) throw 'Original ownership receipt mismatch.';
				}
				if (original == null || original.schemaVersion != 1 || original.owner != entry.owner
					|| key(original.owner) != stateMatch.matched(1)) throw 'Retired state owner mismatch.';
				var chosen = false;
				for (owner in ImportRemovalPlan.manifestRoots(original)) if (selected.indexOf(owner) >= 0) chosen = true;
				if (!chosen) throw 'Retired scope does not own a selected package.';
				for (file in original.files) claims.set(file.path,file.sha256);
				var record:Dynamic = original.revision.importRecord;
				claims.set('import-cache/records/' + record.id + '.json','pointer');
				snapshots.set(record.snapshotId,true);
				var refs:Dynamic = Reflect.field(record,'sourceSnapshots');
				if (Std.isOfType(refs,Array)) for (ref in (cast refs:Array<Dynamic>)) snapshots.set(Std.isOfType(ref,String) ? Std.string(ref) : ref.snapshotId,true);
				if (!~/^retired\/owner-[0-9]+$/.match(backup)) throw 'Invalid retired owner backup.';
			} else if (sourceMatch.match(path)) {
				if (!~/^retired\/source-[0-9]+$/.match(backup)) throw 'Invalid retired snapshot backup.';
			} else throw 'Removal recovery scope is outside managed metadata.';
			if (seen.exists(path) || backups.exists(backup) || !Std.isOfType(entry.inventory,Array)) throw 'Invalid retired scope inventory.';
			seen.set(path,true); backups.set(backup,true); safe(install,path); safe(txn,backup);
			if (entry.replacement != null) {
				var replacement:Dynamic = entry.replacement;
				if (replacement.id != id || key(replacement.owner) != path.substr('import-cache/state/'.length)
					|| !Std.isOfType(replacement.metadata,Array) || (cast replacement.metadata:Array<Dynamic>).length != 3)
					throw 'Invalid surviving ownership publication.';
				var expected = ['transactions/' + id + '/journal-00000001.json','manifest.json','transactions/' + id + '/receipt.json'];
				var index = 0;
				for (metadata in (cast replacement.metadata:Array<Dynamic>)) {
					if (metadata.path != expected[index++] || !Std.isOfType(metadata.text,String)
						|| Std.string(metadata.text).length > 134217728) throw 'Invalid replacement metadata path.';
					var raw:Dynamic = Json.parse(metadata.text);
					if (raw.schemaVersion != 1 || raw.owner != replacement.owner || raw.transactionId != id)
						throw 'Replacement metadata identity mismatch.';
				}
			}
			for (item in (cast entry.inventory:Array<Dynamic>)) {
				var child:String = item.path;
				if (child != '' && !StringTools.startsWith(child,'/')) throw 'Invalid retired child path.';
				safe(txn,backup + child);
				if (!item.directory && !~/^[a-f0-9]{64}$/.match(item.sha256)) throw 'Invalid retired file digest.';
			}
		}
		for (entry in (cast journal.retiredScopes:Array<Dynamic>)) if (StringTools.startsWith(entry.path,'import-cache/sources/') && !snapshots.exists(Std.string(entry.path).substr('import-cache/sources/'.length))) throw 'Retired snapshot has no selected committed reference.';
		for (operation in (cast journal.operations:Array<Dynamic>)) {
			var path:String = operation.path;
			if (!claims.exists(path) || (!ImportIO.isRegistry(path) && claims.get(path) != 'pointer' && claims.get(path) != operation.beforeSha256)) throw 'Removal operation has no selected committed claim.';
			if (StringTools.startsWith(path,'assets/')) ImportRefreshTransaction.managedAssetPath(path);
			else if (!~/^import-cache\/records\/[a-f0-9]{64}\.json$/.match(path)) throw 'Removal operation targets unmanaged metadata.';
			if (!operation.beforeExists || !~/^[a-f0-9]{64}$/.match(operation.beforeSha256)
				|| operation.backupPath != 'backups/files/' + key(path) + '.bak') throw 'Invalid removal operation backup.';
			safe(install,path); safe(txn,operation.backupPath);
		}
	}
	/** Remove a finished transaction folder. Only plain files and folders inside it
	 * are deleted; anything that is not one stops the delete and is kept. */
	static function deleteFinishedTransaction(directory:String,name:String):Void {
		var root = safe(directory,name,true);
		var stack = [root]; var order:Array<String> = [];
		while (stack.length > 0) {
			var path = stack.pop(); order.push(path);
			if (FileSystem.isDirectory(path)) for (child in FileSystem.readDirectory(path)) stack.push(path + '/' + child);
			else if (!ImportRefreshTransaction.isRegularFile(path)) throw 'Unsafe entry in finished removal transaction: ' + path;
			if (order.length > 262144) throw 'Finished removal transaction is too large to clear.';
		}
		order.sort(function(a,b) return b.length - a.length);
		for (path in order) if (FileSystem.isDirectory(path)) FileSystem.deleteDirectory(path); else FileSystem.deleteFile(path);
	}
	public static function recover(install:String):Array<String> {
		install = ImportRefreshTransaction.canonicalDirectory(install,false);
		var state = Path.join([install,STATE]); var directory = safe(install,STATE + '/transactions');
		if (!FileSystem.exists(directory)) return [];
		var failures:Array<String> = [];
		for (name in FileSystem.readDirectory(directory)) try {
			if (!StringTools.startsWith(name,'txn-') || name.indexOf('/') >= 0 || name.indexOf('\\') >= 0) throw 'Unexpected removal transaction directory.';
			var txn = safe(directory,name,true); var journal = ImportRefreshTransaction.latestJournal(txn);
			if (journal == null) continue;
			var committed = FileSystem.exists(txn + '/receipt.json');
			if (journal.phase == 'rolled-back' && !committed) {
				// A rolled-back removal already put every installed file back; what is
				// left in its folder is only its own copies. Checking it against the
				// original ownership metadata is wrong once a later removal of the same
				// package succeeded (that metadata is gone by design), and it locked the
				// whole library on every launch. Delete the finished folder instead.
				validateJournalIdentity(install,journal,name,false);
				deleteFinishedTransaction(directory,name);
				continue;
			}
			// A committed removal has nothing left to restore, so it stays valid after
			// the install folder was moved or renamed. Its receipt binds the exact
			// journal, which is checked before the folder rule is waived.
			if (committed) validateRemovalReceipt(txn,journal);
			validateJournal(install,txn,journal,name,!committed);
			if (committed) {
				failures = failures.concat(cleanup(install,txn,journal));
			} else if (journal.phase == 'preparing') failures = failures.concat(finishPreparationCleanup(install,txn,journal));
			else if (journal.phase != 'rolled-back') failures = failures.concat(rollback(install,state,txn,journal));
			else failures = failures.concat(cleanup(install,txn,journal));
		} catch (error:Dynamic) failures.push(Std.string(error));
		return failures;
	}
}
