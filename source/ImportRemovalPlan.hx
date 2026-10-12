package;

import ImportRefreshTransaction.ImportRefreshManifest;
import ImportRefreshTransaction.ImportRefreshManifestFile;

private typedef RemovalRecord = {
	var manifest:ImportRefreshManifest;
	var roots:Array<String>;
	var dependencies:Array<String>;
	var snapshot:String;
	var selected:Bool;
}
private typedef RemovalClaim = {
	var path:String;
	var hash:String;
	var disagree:Bool;
	var selected:Array<String>;
	var retained:Array<String>;
}
typedef ImportRemovalFile = {
	var path:String;
	var sha256:String;
	var transactions:Array<String>;
}
typedef ImportRemovalSharedFile = {
	var path:String;
	var retainedBy:Array<String>;
}

/** Read-only ownership assessment, not authorization to delete files.
 * Supply the complete receipt-validated inventory. A future executor must
 * reserve owners, revalidate this inventory and current bytes, reconcile registry
 * contributions, archive identities, then journal publication and cleanup.
 * No source, save, registry, receipt or live asset is mutated here. */
class ImportRemovalPlan {
	public var selectedOwners(default, null):Array<String> = [];
	public var affectedOwners(default, null):Array<String> = [];
	public var transactionOwners(default, null):Array<String> = [];
	public var candidateFiles(default, null):Array<ImportRemovalFile> = [];
	public var sharedFiles(default, null):Array<ImportRemovalSharedFile> = [];
	public var registryPaths(default, null):Array<String> = [];
	public var candidateSnapshots(default, null):Array<String> = [];
	public var sharedSnapshots(default, null):Array<String> = [];
	public var dependents(default, null):Array<String> = [];
	public var blockers(default, null):Array<String> = [];
	public var transactionVersions(default, null):Map<String,String> = new Map();
	public var inventoryComplete(default, null):Bool = false;
	static inline var MAX_RECORDS:Int = 8192;
	static inline var MAX_FILES:Int = 1000000;
	function new() {}

	public static function assess(selected:Array<String>, manifests:Array<ImportRefreshManifest>,
		complete:Bool, ?activeOwners:Array<String>, ?checkpoint:Void->Void):ImportRemovalPlan {
		var plan = new ImportRemovalPlan();
		var work = checkpoint == null ? function() {} : checkpoint;
		try {
			if (!complete) throw 'The installed ownership inventory is incomplete.';
			if (manifests == null || manifests.length > MAX_RECORDS) throw 'Ownership inventory limit exceeded or missing.';
			var wanted:Map<String,Bool> = new Map();
			if (selected != null) for (root in selected) wanted.set(owner(root), true);
			plan.selectedOwners = sortedKeys(wanted);
			if (plan.selectedOwners.length == 0) throw 'Select at least one imported package.';
			var byRoot:Map<String,String> = new Map();
			var affected:Map<String,Bool> = new Map();
			var records:Array<RemovalRecord> = [];
			var fileCount = 0;
			for (manifest in manifests) {
				work();
				if (manifest == null || manifest.schemaVersion != 1 || manifest.transactionId == null
					|| manifest.transactionId == '' || manifest.files == null) throw 'Missing committed ownership metadata.';
				var record:Dynamic = manifest.revision == null ? null : Reflect.field(manifest.revision, 'importRecord');
				var id = text(record, 'id');
				if (record == null || Reflect.field(record, 'schemaVersion') != 1 || !~/^[a-f0-9]{64}$/.match(id)
					|| manifest.owner != 'retained-import:' + id) throw 'Invalid retained import identity.';
				if (plan.transactionVersions.exists(manifest.owner)) throw 'Duplicate transaction owner in inventory.';
				plan.transactionVersions.set(manifest.owner, manifest.transactionId);
				var roots:Map<String,Bool> = new Map();
				var rawRoots = array(record, 'roots');
				for (root in rawRoots) roots.set(owner('assets/imported_mods/' + text(root, 'namespace')), true);
				var family = ImportRefreshTransaction.validatePackageFamilyCatalog(
					Reflect.field(record, 'packageFamilyCatalog'), record);
				if (family != null && family.version >= 2) for (member in family.members)
					roots.set(owner('assets/imported_mods/' + member.namespace), true);
				if (roots.keys().hasNext() == false) throw 'Retained import has no package roots.';
				var chosen = false;
				for (root in roots.keys()) {
					if (byRoot.exists(root)) throw 'Package has ambiguous transaction ownership: ' + root;
					byRoot.set(root, manifest.owner);
					if (wanted.exists(root)) chosen = true;
				}
				var dependencies:Array<String> = [];
				// Older receipts may omit dependencies. They cannot prove a deletion safe.
				if (!Reflect.hasField(record, 'runtimeDependencyOwners'))
					plan.blockers.push('Dependency metadata is missing for ' + manifest.owner + '.');
				else for (dependency in array(record, 'runtimeDependencyOwners')) {
					if (!Std.isOfType(dependency, String)) throw 'Invalid dependency owner.';
					var root = owner(cast dependency);
					if (dependencies.indexOf(root) < 0) dependencies.push(root);
				}
				var snapshot = text(record, 'snapshotId');
				if (!~/^[a-f0-9]{64}$/.match(snapshot) || text(record, 'source') != 'sources/' + snapshot + '/content')
					throw 'Invalid managed snapshot identity.';
				fileCount += manifest.files.length;
				if (fileCount > MAX_FILES) throw 'Ownership file inventory limit exceeded.';
				var entry:RemovalRecord = {manifest:manifest, roots:sortedKeys(roots), dependencies:dependencies,
					snapshot:snapshot, selected:chosen};
				records.push(entry);
				if (chosen) {
					plan.transactionOwners.push(manifest.owner);
					for (root in entry.roots) {
						affected.set(root, true);
						if (!wanted.exists(root)) plan.blockers.push('This import also owns ' + root
							+ '. Per-package transaction splitting is required.');
					}
				}
			}
			for (root in wanted.keys()) if (!byRoot.exists(root)) plan.blockers.push('No committed ownership for ' + root + '.');
			plan.affectedOwners = sortedKeys(affected);
			if (activeOwners != null) for (root in activeOwners) if (affected.exists(owner(root)))
				plan.blockers.push('Package is active or reserved: ' + root);
			var claims:Map<String,RemovalClaim> = new Map();
			var snapshots:Map<String,Array<Bool>> = new Map();
			var dependentRoots:Map<String,Bool> = new Map();
			var registrySet:Map<String,String> = new Map();
			var registrySpellings:Map<String,String> = new Map();
			for (entry in records) {
				work();
				if (!snapshots.exists(entry.snapshot)) snapshots.set(entry.snapshot, [false, false]);
				snapshots.get(entry.snapshot)[entry.selected ? 0 : 1] = true;
				if (!entry.selected) for (dependency in entry.dependencies) if (affected.exists(dependency))
					for (root in entry.roots) dependentRoots.set(root, true);
				var registryBaselines:Map<String,Bool> = new Map();
				if (entry.selected) {
					var values:Dynamic = Reflect.field(entry.manifest.revision, 'registries');
					if (Std.isOfType(values, Array)) for (value in (cast values:Array<Dynamic>)) {
						var path = ImportRefreshTransaction.managedAssetPath(text(value, 'path')).toLowerCase();
						if (!ImportIO.isRegistry(path) || !Std.isOfType(Reflect.field(value, 'before'), String)
							|| !Std.isOfType(Reflect.field(value, 'generated'), String) || registryBaselines.exists(path))
							throw 'Invalid registry contribution baseline.';
						registryBaselines.set(path, true);
					}
				}
				var seen:Map<String,Bool> = new Map();
				var index = 0;
				for (file in entry.manifest.files) {
					if ((index++ & 1023) == 0) work();
					if (file == null || file.owner != entry.manifest.owner || file.sha256 == null
						|| !~/^[a-fA-F0-9]{64}$/.match(file.sha256)) throw 'Invalid manifest file claim.';
					var path = ImportRefreshTransaction.managedAssetPath(file.path);
					var key = path.toLowerCase();
					if (seen.exists(key)) throw 'Duplicate or case-colliding manifest file claim.';
					seen.set(key, true);
					if (ImportIO.isRegistry(key)) {
						if (registrySpellings.exists(key) && registrySpellings.get(key) != path)
							plan.blockers.push('Registry path casing differs across owners: ' + path);
						registrySpellings.set(key, path);
						if (entry.selected) {
							registrySet.set(key, path);
							if (!registryBaselines.exists(key)) plan.blockers.push('No registry contribution baseline for ' + path);
						}
						continue;
					}
					var claim = claims.get(key);
					if (claim == null) {
						claim = {path:path, hash:file.sha256.toLowerCase(), disagree:false, selected:[], retained:[]};
						claims.set(key, claim);
					}
					if (claim.hash != file.sha256.toLowerCase()) claim.disagree = true;
					if (claim.path != path) plan.blockers.push('File path casing differs across owners: ' + path);
					(entry.selected ? claim.selected : claim.retained).push(entry.manifest.owner);
				}
			}
			for (key in sortedKeys(claims)) {
				var claim = claims.get(key);
				if (claim.selected.length == 0) continue;
				claim.selected.sort(Reflect.compare); claim.retained.sort(Reflect.compare);
				if (claim.retained.length > 0) plan.sharedFiles.push({path:claim.path, retainedBy:claim.retained});
				else if (claim.disagree) plan.blockers.push('Selected owners disagree on the generated file digest: ' + claim.path);
				else plan.candidateFiles.push({path:claim.path, sha256:claim.hash, transactions:claim.selected});
			}
			for (snapshot in sortedKeys(snapshots)) {
				var refs = snapshots.get(snapshot);
				if (refs[0]) (refs[1] ? plan.sharedSnapshots : plan.candidateSnapshots).push(snapshot);
			}
			plan.dependents = sortedKeys(dependentRoots);
			for (root in plan.dependents) plan.blockers.push('Surviving package depends on this selection: ' + root);
			plan.registryPaths = [for (key in sortedKeys(registrySet)) registrySet.get(key)];
			plan.transactionOwners.sort(Reflect.compare);
			plan.inventoryComplete = true;
		} catch (error:Dynamic) {
			plan.blockers.push(Std.string(error));
			// Never expose partial candidates from an invalid or cancelled inventory.
			plan.candidateFiles = []; plan.candidateSnapshots = [];
		}
		return plan;
	}

	static function owner(value:String):String {
		var path = ImportRefreshTransaction.managedAssetPath(value);
		var parts = path.split('/');
		if (parts.length != 3 || parts[0].toLowerCase() != 'assets' || parts[1].toLowerCase() != 'imported_mods')
			throw 'Invalid imported package root.';
		return path.toLowerCase();
	}
	static function text(value:Dynamic, key:String):String {
		var field:Dynamic = value == null ? null : Reflect.field(value, key);
		return Std.isOfType(field, String) ? cast field : '';
	}
	static function array(value:Dynamic, key:String):Array<Dynamic> {
		var field:Dynamic = value == null ? null : Reflect.field(value, key);
		if (!Std.isOfType(field, Array)) throw 'Missing ownership list: ' + key;
		return cast field;
	}
	static function sortedKeys<T>(map:Map<String,T>):Array<String> {
		var result = [for (key in map.keys()) key]; result.sort(Reflect.compare); return result;
	}
}
