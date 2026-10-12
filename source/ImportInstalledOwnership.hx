package;

import haxe.Json;
import haxe.io.Path;
import ImportRefreshTransaction.ImportRefreshManifest;

/** Detached, receipt-backed chart identity for a later history archive. */
typedef InstalledLibraryIdentity = {
	var folder:String;
	var ownerRoot:String;
	var sourceFolder:String;
	var engine:String;
	var sourceIdentity:String;
	var sourceFingerprint:String;
}

/** Read-only join of live ownership markers and a strict retained inventory.
 * Unknown installed owners block assessment; they are never silently adopted. */
class ImportInstalledOwnership {
	public var complete(default, null):Bool = false;
	public var blockers(default, null):Array<String> = [];
	public var charts(default, null):Array<InstalledLibraryIdentity> = [];
	public var owners(default, null):Array<String> = [];
	function new() {}

	public static function inspect(install:String, manifests:Array<ImportRefreshManifest>,
		protectedRoots:Array<String>, ?cancel:Void->Bool):ImportInstalledOwnership {
		var result = new ImportInstalledOwnership();
		try {
			var view = new ImportMetadataInspection(install, cancel);
			var protectedOwners:Map<String,Bool> = new Map();
			if (protectedRoots != null) for (root in protectedRoots) protectedOwners.set(ImportRemovalPlan.ownerRoot(root), true);
			var transactions:Map<String,ImportRefreshManifest> = new Map();
			var engines:Map<String,String> = new Map();
			var claims:Map<String,Array<{owner:String, hash:String}>> = new Map();
			var installed:Map<String,Bool> = new Map();
			if (manifests == null || manifests.length > 8192) throw 'Incomplete retained inventory.';
			var fileCount = 0;
			for (manifest in manifests) {
				view.check();
				var rootEngines = ImportRemovalPlan.manifestRootEngines(manifest);
				for (root in rootEngines.keys()) {
					if (protectedOwners.exists(root)) throw 'Retained import claims host-owned content: ' + root;
					if (transactions.exists(root)) throw 'Ambiguous installed ownership: ' + root;
					transactions.set(root, manifest); engines.set(root, rootEngines.get(root));
				}
				if (manifest.files == null) throw 'Missing retained output claims.';
				for (file in manifest.files) {
					view.check();
					if (++fileCount > 1000000) throw 'Installed ownership file limit exceeded.';
					var path = ImportRefreshTransaction.managedAssetPath(file.path).toLowerCase();
					if (file.owner != manifest.owner || file.sha256 == null || !~/^[a-fA-F0-9]{64}$/.match(file.sha256))
						throw 'Invalid retained output claim: ' + path;
					if (!claims.exists(path)) claims.set(path, []);
					claims.get(path).push({owner:manifest.owner, hash:file.sha256.toLowerCase()});
				}
			}
			function known(root:String):Void {
				if (!transactions.exists(root) && !protectedOwners.exists(root)) throw 'Installed package has no retained ownership: ' + root;
				installed.set(root, true);
			}
			function claimed(relative:String, root:String):Void {
				var entries = claims.get(relative.toLowerCase());
				var transaction = transactions.get(root);
				if (transaction == null || entries == null) throw 'Installed metadata has no matching retained claim: ' + relative;
				var matched = false;
				for (entry in entries) if (entry.owner == transaction.owner
					&& entry.hash == view.digest(Path.join([view.root, relative]))) matched = true;
				if (!matched) throw 'Installed metadata differs from its retained ownership receipt: ' + relative;
			}
			var data = Path.join([view.root, 'assets/data']);
			var folders = view.optionalDirectory(data);
			if (folders.length > 8192) throw 'Installed chart inventory limit exceeded.';
			var chartFolders:Map<String,Bool> = new Map();
			for (folder in folders) {
				view.check(); var directory = Path.join([data, folder]);
				if (!view.isDirectory(directory)) continue;
				var provenance = Path.join([directory, 'importProvenance.json']);
				var compat = Path.join([directory, CompatScriptManifest.FILE_NAME]);
				var hasProvenance = view.exists(provenance); var hasCompat = view.exists(compat);
				if (!hasProvenance && !hasCompat) continue;
				if (!hasCompat && claims.exists(('assets/data/' + folder + '/' + CompatScriptManifest.FILE_NAME).toLowerCase()))
					throw 'Claimed compatibility metadata is missing: ' + folder;
				if (!hasProvenance) throw 'Compatibility chart has no import provenance: ' + folder;
				var record = view.metadata(provenance, 131072);
				if (Reflect.field(record, 'version') != 1 || text(record, 'destinationFolder') != folder)
					throw 'Invalid installed chart provenance: ' + folder;
				var root = ImportRemovalPlan.ownerRoot(text(record, 'sourceOwner')); known(root);
				var engine = ImportEngine.normalize(text(record, 'sourceEngine'));
				if (engine == ImportEngine.AUTO || engine != engines.get(root)) throw 'Chart source engine disagrees with retained ownership: ' + folder;
				var source = text(record, 'sourceFolder');
				if (source == '' || source.length > 256 || ~/[\x00-\x1F\x7F]/.match(source)) throw 'Missing or invalid source chart identity: ' + folder;
				var relative = 'assets/data/' + folder + '/importProvenance.json'; claimed(relative, root);
				chartFolders.set(folder.toLowerCase(), true);
				if (hasCompat) {
					var raw = view.metadata(compat, 131072);
					var roots:Dynamic = Reflect.field(raw, 'roots');
					if (Reflect.field(raw, 'version') != CompatScriptManifest.VERSION || !Std.isOfType(roots, Array)
						|| (cast roots:Array<Dynamic>).length == 0) throw 'Invalid compatibility ownership: ' + folder;
					var normalized = CompatScriptManifest.normalize(raw);
					if (ImportRemovalPlan.ownerRoot(CompatScriptManifest.selectedRoot(normalized)) != root)
						throw 'Chart provenance and compatibility owner disagree: ' + folder;
					var selected = text(raw, 'selectedRoot');
					if (selected != '' && ImportRemovalPlan.ownerRoot(selected) != root)
						throw 'Explicit compatibility owner disagrees with provenance: ' + folder;
					var transaction = transactions.get(root);
					var dependencies:Dynamic = Reflect.field(transaction.revision.importRecord, 'runtimeDependencyOwners');
					if (!Std.isOfType(dependencies, Array)) throw 'Missing retained dependency metadata: ' + root;
					var declared = [for (dependency in (cast dependencies:Array<Dynamic>)) ImportRemovalPlan.ownerRoot(Std.string(dependency))];
					for (entry in (cast roots:Array<Dynamic>)) {
						var provider = ImportRemovalPlan.ownerRoot(text(entry, 'path')); known(provider);
						if (ImportEngine.normalize(text(entry, 'engine')) == ImportEngine.AUTO
							|| (!protectedOwners.exists(provider) && ImportEngine.normalize(text(entry, 'engine')) != engines.get(provider)))
							throw 'Invalid compatibility provider engine: ' + folder;
						if (provider != root && !protectedOwners.exists(provider)
							&& transactions.get(provider).owner != transaction.owner && declared.indexOf(provider) < 0)
							throw 'Live compatibility dependency is absent from its retained receipt: ' + provider;
					}
					claimed('assets/data/' + folder + '/' + CompatScriptManifest.FILE_NAME, root);
				}
				result.charts.push({folder:folder, ownerRoot:root, sourceFolder:source, engine:engine,
					sourceIdentity:text(record, 'sourceIdentity'), sourceFingerprint:text(record, 'sourceFingerprint')});
			}
			// A deleted provenance file must not turn an imported chart into a base song.
			for (path in claims.keys()) if (StringTools.startsWith(path, 'assets/data/')) {
				var parts = path.split('/');
				if (parts.length == 4 && (parts[3] == 'importprovenance.json' || parts[3] == 'compatscripts.json')
					&& !chartFolders.exists(parts[2])) throw 'Claimed chart ownership metadata is missing: ' + path;
			}
			var mods = Path.join([view.root, 'assets/imported_mods']);
			for (name in view.optionalDirectory(mods)) {
				view.check(); var path = Path.join([mods, name]);
				if (!view.isDirectory(path)) {
					if (!ImportIO.isRegistry('assets/imported_mods/' + name)) throw 'Unclaimed package metadata: ' + name;
					continue;
				}
				var root = ImportRemovalPlan.ownerRoot('assets/imported_mods/' + name);
				if (protectedOwners.exists(root)) continue;
				known(root);
				var marker = Path.join([path, '.cammie-owner.json']);
				if (view.exists(marker)) {
					var record = view.metadata(marker, 131072);
					if (Reflect.field(record, 'version') != 1 || ImportEngine.normalize(text(record, 'engine')) == ImportEngine.AUTO
						|| ImportEngine.normalize(text(record, 'engine')) != engines.get(root))
						throw 'Invalid installed package marker: ' + root;
					claimed('assets/imported_mods/' + name + '/.cammie-owner.json', root);
				}
			}
			var catalog = Path.join([data, 'codenameMods.json']);
			if (view.exists(catalog)) {
				var raw = view.metadata(catalog); var entries:Dynamic = Reflect.field(raw, 'entries');
				if (!Std.isOfType(entries, Array)) throw 'Invalid imported menu catalog.';
				for (entry in (cast entries:Array<Dynamic>)) known(ImportRemovalPlan.ownerRoot(text(entry, 'root')));
			}
			var providerConfig = Path.join([mods, 'globalResultsProvider.json']);
			if (view.exists(providerConfig)) {
				var raw = view.metadata(providerConfig, 131072);
				if (Reflect.field(raw, 'version') != 1) throw 'Invalid global provider selector.';
				known(ImportRemovalPlan.ownerRoot(text(raw, 'defaultOwner')));
			}
			view.verify();
			result.owners = [for (root in installed.keys()) root]; result.owners.sort(Reflect.compare);
			result.charts.sort(function(a,b) return Reflect.compare(a.folder, b.folder));
			result.complete = true;
		} catch (error:Dynamic) {
			result.charts = []; result.owners = []; result.blockers.push(Std.string(error));
		}
		return result;
	}
	static function text(value:Dynamic, key:String):String {
		var field:Dynamic = value == null ? null : Reflect.field(value, key);
		return Std.isOfType(field, String) ? cast field : '';
	}
}
