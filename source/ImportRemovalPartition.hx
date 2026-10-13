package;

import haxe.Json;
import haxe.io.Path;
import sys.io.File;
import ImportRefreshTransaction.ImportRefreshManifest;
import ImportInstalledOwnership.InstalledLibraryIdentity;

typedef ImportRemovalPartitionResult = {
	var revisions:Map<String,Dynamic>;
	var retainedFiles:Map<String,Array<String>>;
	var registryGenerated:Map<String,Map<String,String>>;
}

/** Partition only receipt-backed chart roots and direct namespace outputs.
 * Unattributed common outputs stay with the surviving transaction. */
class ImportRemovalPartition {
	public static function prepare(install:String,plan:ImportRemovalPlan,manifests:Array<ImportRefreshManifest>,
		charts:Array<InstalledLibraryIdentity>,?cancel:Void->Bool):ImportRemovalPartitionResult {
		var result:ImportRemovalPartitionResult = {revisions:new Map(),retainedFiles:new Map(),registryGenerated:new Map()};
		var wanted = plan.selectedOwners;
		var selectedFolders:Array<String> = []; var retainedFolders:Array<String> = [];
		for (chart in charts) (wanted.indexOf(chart.ownerRoot) >= 0 ? selectedFolders : retainedFolders).push(chart.folder.toLowerCase());
		var selectedPaths:Map<String,Bool> = new Map();
		var partial:Array<String> = [];
		for (manifest in manifests) {
			ImportRefreshTransaction.checkpointWork(cancel);
			var roots = ImportRemovalPlan.manifestRoots(manifest);
			var chosen = [for (root in roots) if (wanted.indexOf(root) >= 0) root];
			var retained = [for (root in roots) if (wanted.indexOf(root) < 0) root];
			if (chosen.length == 0 || retained.length == 0) continue;
			var record:Dynamic = manifest.revision.importRecord;
			var family = ImportRefreshTransaction.validatePackageFamilyCatalog(Reflect.field(record,'packageFamilyCatalog'),record);
			if (family != null && family.version < 2) throw 'This older family catalog cannot prove independent destination ownership.';
			if (family != null && family.coreProvider != null
				&& wanted.indexOf(ImportRemovalPlan.ownerRoot('assets/imported_mods/' + family.coreProvider.namespace)) >= 0)
				throw 'The shared engine core is required by surviving family members.';
			var copy:Dynamic = Json.parse(Json.stringify(manifest.revision)); var next:Dynamic = copy.importRecord;
			var removed:Array<Dynamic> = [];
			var keepRoots:Array<Dynamic> = [];
			for (root in (cast next.roots:Array<Dynamic>)) {
				var owner = ImportRemovalPlan.ownerRoot('assets/imported_mods/' + Std.string(root.namespace));
				if (wanted.indexOf(owner) >= 0) {
					var relative:Dynamic = Reflect.field(root,'relative');
					if (!Std.isOfType(relative,String) || Std.string(relative) == '' || Std.string(relative).indexOf('..') >= 0
						|| Path.isAbsolute(Std.string(relative))) throw 'Aggregate source root cannot be independently excluded.';
					removed.push({relative:relative,engine:root.engine,namespace:root.namespace});
				} else keepRoots.push(root);
			}
			if (family != null) {
				var keepMembers:Array<Dynamic> = [];
				for (member in family.members) {
					if (wanted.indexOf(ImportRemovalPlan.ownerRoot('assets/imported_mods/' + member.namespace)) >= 0) {
						var present = false;
						for (entry in removed) if (entry.namespace == member.namespace) present = true;
						if (!present) removed.push({relative:member.sourceRelative,engine:family.engine,namespace:member.namespace});
					} else keepMembers.push(member);
				}
				if (keepMembers.length == 0) Reflect.deleteField(next,'packageFamilyCatalog');
				else next.packageFamilyCatalog.members = keepMembers;
			}
			if (keepRoots.length == 0 || removed.length != chosen.length) throw 'Aggregate package ownership is ambiguous.';
			next.roots = keepRoots;
			var prior:Array<Dynamic> = cast Reflect.field(next,'removedSourceRoots');
			next.removedSourceRoots = (prior == null ? [] : prior).concat(removed);
			for (field in ['sourceBuildContexts','sourceAssetProfiles']) {
				var catalog:Dynamic = Reflect.field(next,field);
				if (catalog != null && Std.isOfType(Reflect.field(catalog,'roots'),Array)) {
					var values:Array<Dynamic> = cast catalog.roots;
					catalog.roots = [for (value in values) if (!excludedProfile(value,removed)) value];
				}
			}
			var retainedPaths:Array<String> = [];
			for (file in manifest.files) {
				var selected = selectedFile(file.path,chosen,selectedFolders);
				if (selected && !ImportIO.isRegistry(file.path)) selectedPaths.set(file.path.toLowerCase(),true);
				else retainedPaths.push(file.path);
			}
			var generated:Map<String,String> = new Map();
			var registries:Array<Dynamic> = cast Reflect.field(copy,'registries');
			if (registries != null) for (registry in registries) {
				var before:Dynamic = tjson.TJSON.parse(registry.before);
				var previous:Dynamic = tjson.TJSON.parse(registry.generated);
				var filtered = filter(before,previous,chosen,retained,selectedFolders,retainedFolders);
				registry.generated = UnicodeSafeJson.stringify(filtered.value);
				generated.set(registry.path,registry.generated);
			}
			// Survivor chart providers cannot point at a package being removed.
			for (chart in charts) if (retained.indexOf(chart.ownerRoot) >= 0) {
				var path = ImportRefreshTransaction.safeChild(install,'assets/data/' + chart.folder + '/compatScripts.json',false);
				if (sys.FileSystem.exists(path)) {
					var compat:Dynamic = Json.parse(File.getContent(path));
					for (provider in (cast compat.roots:Array<Dynamic>)) if (wanted.indexOf(ImportRemovalPlan.ownerRoot(provider.path)) >= 0)
						throw 'Surviving aggregate chart depends on the selected package: ' + chart.folder;
				}
			}
			result.revisions.set(manifest.owner,copy); result.retainedFiles.set(manifest.owner,retainedPaths);
			result.registryGenerated.set(manifest.owner,generated); partial.push(manifest.owner);
		}
		if (partial.length == 0) return result;
		plan.blockers = [for (blocker in plan.blockers) if (blocker.indexOf('Per-package transaction splitting is required.') < 0) blocker];
		plan.affectedOwners = wanted.copy();
		var candidates = [];
		for (file in plan.candidateFiles) {
			if (selectedCandidate(file.path,file.transactions,partial,selectedPaths,result.retainedFiles)) candidates.push(file);
			else plan.sharedFiles.push({path:file.path,retainedBy:file.transactions});
		}
		plan.candidateFiles = candidates;
		// A partially retained transaction still references its full source snapshot.
		for (manifest in manifests) if (partial.indexOf(manifest.owner) >= 0) {
			var references:Array<String> = [manifest.revision.importRecord.snapshotId];
			var extra:Dynamic = Reflect.field(manifest.revision.importRecord,'sourceSnapshots');
			if (Std.isOfType(extra,Array)) for (reference in (cast extra:Array<Dynamic>))
				references.push(Std.isOfType(reference,String) ? Std.string(reference) : reference.snapshotId);
			for (snapshot in references) {
				plan.candidateSnapshots.remove(snapshot);
				if (plan.sharedSnapshots.indexOf(snapshot) < 0) plan.sharedSnapshots.push(snapshot);
			}
		}
		return result;
	}
	static function excludedProfile(value:Dynamic,removed:Array<Dynamic>):Bool {
		for (entry in removed) if (Reflect.field(value,'namespace') == entry.namespace
			|| Reflect.field(value,'rootRelative') == entry.relative || Reflect.field(value,'relative') == entry.relative) return true;
		return false;
	}
	static function selectedCandidate(path:String,owners:Array<String>,partial:Array<String>,selected:Map<String,Bool>,retained:Map<String,Array<String>>):Bool {
		for (owner in owners) if (retained.exists(owner) && retained.get(owner).indexOf(path) >= 0) return false;
		for (owner in owners) if (partial.indexOf(owner) < 0) return true;
		return selected.exists(path.toLowerCase());
	}
	static function selectedFile(path:String,roots:Array<String>,folders:Array<String>):Bool {
		path = path.toLowerCase();
		for (root in roots) if (StringTools.startsWith(path,root + '/')) return true;
		for (folder in folders) for (base in ['assets/data/','assets/songs/']) if (StringTools.startsWith(path,base + folder + '/')) return true;
		return false;
	}
	static function references(value:Dynamic,roots:Array<String>,folders:Array<String>):Bool {
		if (Std.isOfType(value,String)) {
			var text = Std.string(value).toLowerCase();
			if (folders.indexOf(text) >= 0) return true;
			for (root in roots) if (text == root || StringTools.startsWith(text,root + '/')) return true;
			return false;
		}
		return false;
	}
	static function direct(value:Dynamic,roots:Array<String>,folders:Array<String>):Bool {
		if (Std.isOfType(value,String)) return false;
		if (value != null && !Std.isOfType(value,Array) && !Std.isOfType(value,String)) {
			// Freeplay category names are presentation, even when they equal a
			// chart folder. Only a song entry or an explicit owner/path is a claim.
			if (Std.isOfType(Reflect.field(value,'songs'),Array)) return false;
			for (field in ['owner','root','path','sourceOwner']) if (references(Reflect.field(value,field),roots,[])) return true;
			if (Reflect.hasField(value,'character') || Reflect.hasField(value,'week'))
				if (references(Reflect.field(value,'name'),roots,folders)) return true;
		}
		return false;
	}
	static function identity(value:Dynamic):String {
		if (Std.isOfType(value,String)) return 'string:' + value;
		if (value != null) for (field in ['name','id','root','owner','path']) {
			var text:Dynamic = Reflect.field(value,field); if (Std.isOfType(text,String)) return field + ':' + text;
		}
		return '';
	}
	static function filter(before:Dynamic,value:Dynamic,selected:Array<String>,retained:Array<String>,
		folders:Array<String>,otherFolders:Array<String>):{exists:Bool,value:Dynamic} {
		if (direct(value,selected,folders)) {
			if (direct(value,retained,otherFolders)) throw 'Registry entry mixes selected and surviving owners.';
			return {exists:before != null,value:before};
		}
		if (Std.isOfType(value,Array)) {
			var baseline:Array<Dynamic> = Std.isOfType(before,Array) ? cast before : [];
			var output:Array<Dynamic> = [];
			for (item in (cast value:Array<Dynamic>)) {
				var original:Dynamic = null; var id = identity(item);
				if (id != '') for (old in baseline) if (identity(old) == id) original = old;
				var filtered = Std.isOfType(item,String) && references(item,selected,folders)
					? {exists:original != null,value:original} : filter(original,item,selected,retained,folders,otherFolders);
				if (filtered.exists) output.push(filtered.value);
			}
			return {exists:true,value:output};
		}
		if (value != null && !Std.isOfType(value,String) && !Std.isOfType(value,Bool) && !Std.isOfType(value,Float)) {
			var output:Dynamic = {};
			for (field in Reflect.fields(value)) {
				var original = before == null ? null : Reflect.field(before,field);
				var child = Reflect.field(value,field);
				var filtered = filter(original,child,selected,retained,folders,otherFolders);
				if (filtered.exists) Reflect.setField(output,field,filtered.value);
			}
			return {exists:true,value:output};
		}
		return {exists:true,value:value};
	}
}
