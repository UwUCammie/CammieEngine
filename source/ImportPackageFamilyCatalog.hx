package;

#if sys
import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import ImportRefreshTransaction.ImportRefreshManifest;
import ImportRefreshTransaction.ImportRefreshPackageFamilyCatalog;
import ImportRefreshTransaction.ImportRefreshPackageFamilyCatalogEntry;
import NightmareVisionModFamilyMember;

private typedef ImportPackageFamilyCommittedImport = {
	var manifest:ImportRefreshManifest;
	var record:Dynamic;
	var catalog:ImportRefreshPackageFamilyCatalog;
}

private typedef ImportPackageFamilySourceMember = {
	var directory:String;
	var sourceRelative:String;
	var sourceRoot:String;
}

private typedef ImportPackageFamilySourceStructure = {
	var snapshotId:String;
	var containerRelative:String;
	var members:Array<ImportPackageFamilySourceMember>;
}

/**
	Enrollment for sibling roots from one retained Nightmare Vision content
	container. Package labels only come from direct content/<package> directory
	entries that the importer recorded in the same committed source snapshot.
*/
class ImportPackageFamilyCatalog {
	public static inline var MAX_RECORDS:Int = 256;
	public static inline var MAX_FAMILY_DIRECTORIES:Int = 128;
	static inline var FAMILY_EVIDENCE:String = "Nested content package inherits Nightmare Vision identity from its parent game root";

	/** Build an optional catalog while a newly captured snapshot is already in
	 * hand. Failure to prove a family never blocks an ordinary import. */
	public static function capture(snapshotRoot:String, record:Dynamic):Null<ImportRefreshPackageFamilyCatalog> {
		try {
			var catalog = discover(snapshotRoot, record);
			return catalog == null ? null : ImportRefreshTransaction.validatePackageFamilyCatalog(catalog, record);
		} catch (_:Dynamic) return null;
	}

	/** Direct source roots which were proved to belong to one retained NMV
	 * content container. Callers may materialize their package runtime files, but
	 * must still require transaction-owned config and runtime outputs before
	 * publishing a v2 mapping. */
	public static function sourceRoots(snapshotRoot:String, record:Dynamic):Array<String> {
		try {
			var structure = discoverStructure(snapshotRoot, record);
			return structure == null ? [] : [for (member in structure.members) member.sourceRoot];
		} catch (_:Dynamic) return [];
	}

	/** The scanner's accepted outer NMV identities are the authority for a
	 * content package. Keep this proof shared with path canonicalization so an
	 * executable-only distribution remains equivalent to a source checkout. */
	public static function isAuthenticatedNightmareVisionContainer(rootPath:String):Bool {
		try {
			var root = ImportRootScanner.inspectRoot(rootPath, ImportEngine.AUTO);
			return root != null && root.engine == ImportEngine.NIGHTMARE_VISION
				&& hasNmvContainerProof(root.evidence);
		} catch (_:Dynamic) return false;
	}

	/** Build a v2 catalog only from namespaces resolved by CompatScriptManifest
	 * during the same ImportIO staging scope, and only when the staged transaction
	 * owns the package config plus non-core runtime content. */
	public static function capturePublished(snapshotRoot:String, record:Dynamic, io:ImportIO):Null<ImportRefreshPackageFamilyCatalog> {
		if (io == null) return null;
		try {
			var structure = discoverStructure(snapshotRoot, record);
			if (structure == null) return null;
			var written = io.writtenPaths();
			var members:Array<ImportRefreshPackageFamilyCatalogEntry> = [];
			for (sourceMember in structure.members) {
				var namespace = io.resolvedNamespace(sourceMember.sourceRoot, "Nightmare Vision");
				if (namespace == null || !hasStagedMemberOutputs(namespace, written)) continue;
				members.push({directory:sourceMember.directory,
					sourceRelative:sourceMember.sourceRelative, namespace:namespace});
			}
			if (members.length < 2) return null;
			var catalog:ImportRefreshPackageFamilyCatalog = {
				version:2, engine:"Nightmare Vision", snapshotId:structure.snapshotId,
				containerRelative:structure.containerRelative, members:members
			};
			return ImportRefreshTransaction.validatePackageFamilyCatalog(catalog, record);
		} catch (_:Dynamic) return null;
	}

	/** Carry verified per-package namespaces forward when an import recaptures
	 * changed source bytes into a new immutable snapshot. The prior mapping must
	 * still be backed by its own authenticated snapshot and committed output
	 * manifest; a current source member is matched only by its exact relative
	 * path and directory label within the same retained-import identity. */
	public static function reusableNamespaces(install:String, previous:ImportRefreshManifest,
		snapshotRoot:String, record:Dynamic):Map<String, String> {
		var result:Map<String, String> = new Map();
		try {
			if (install == null || previous == null || record == null || previous.revision == null) return result;
			var id:Dynamic = Reflect.field(record, "id");
			var oldRecord:Dynamic = Reflect.field(previous.revision, "importRecord");
			if (!Std.isOfType(id, String) || previous.owner != "retained-import:" + Std.string(id)
				|| oldRecord == null || Reflect.field(oldRecord, "id") != id
				|| Reflect.field(oldRecord, "schemaVersion") != 1) return result;
			var oldCatalog = ImportRefreshTransaction.validatePackageFamilyCatalog(previous.packageFamilyCatalog,
				oldRecord);
			if (oldCatalog == null || oldCatalog.version != 2) return result;
			var oldSnapshot = safeChild(Path.join([install, "import-cache"]),
				"sources/" + Std.string(Reflect.field(oldRecord, "snapshotId")));
			if (oldSnapshot == null || !safeExistingDirectory(install, oldSnapshot)
				|| !sameSourceStructure(oldCatalog, discoverStructure(oldSnapshot, oldRecord))) return result;
			var currentStructure = discoverStructure(snapshotRoot, record);
			if (currentStructure == null || currentStructure.containerRelative != oldCatalog.containerRelative)
				return result;
			var currentMembers:Map<String, ImportPackageFamilySourceMember> = new Map();
			for (member in currentStructure.members)
				currentMembers.set(member.sourceRelative, member);
			for (member in oldCatalog.members) {
				var current = currentMembers.get(member.sourceRelative);
				if (current == null || current.directory != member.directory) continue;
				if (installedMappingV2(install, previous, member) == null) continue;
				result.set(member.sourceRelative, member.namespace);
			}
		} catch (_:Dynamic) {
			return new Map();
		}
		return result;
	}

	/** Resolve only installed family roots whose source relationship is covered
	 * by committed retained-import manifests. Invalid or legacy-singleton state
	 * returns an empty list for the caller's existing owner-only path. */
	public static function forOwner(ownerRoot:String):Array<NightmareVisionModFamilyMember> {
		var empty:Array<NightmareVisionModFamilyMember> = [];
		try {
			if (ownerRoot == null || StringTools.trim(ownerRoot) == "") return empty;
			var install = canonicalDirectory(Sys.getCwd());
			var ownerPath = Path.isAbsolute(ownerRoot) ? ownerRoot : Path.join([install, ownerRoot]);
			var normalizedOwner = canonicalDirectory(ownerPath);
			if (!isWithin(normalizedOwner, install)) return empty;
			var expectedPrefix = Path.normalize(Path.join([install, "assets", "imported_mods"]));
			if (!isWithin(normalizedOwner, expectedPrefix) || samePath(normalizedOwner, expectedPrefix)) return empty;
			var cache = Path.join([install, "import-cache"]);
			var committed = loadCommittedImports(install, cache);
			var selectedSnapshot:String = "";
			var selectedCatalog:ImportRefreshPackageFamilyCatalog = null;
			var selectedDirectory:String = "";
			var selectedFound = false;
			for (entry in committed) {
				for (mapping in installedMappings(install, entry.manifest, entry.record, entry.catalog)) {
					if (mapping != null && samePath(canonicalDirectory(Path.join([install, mapping.root])), normalizedOwner)) {
						if (selectedFound && (selectedSnapshot != entry.catalog.snapshotId
							|| !sameCatalog(selectedCatalog, entry.catalog) || selectedDirectory != mapping.directory))
							return empty;
						selectedSnapshot = entry.catalog.snapshotId;
						selectedCatalog = entry.catalog;
						selectedDirectory = mapping.directory;
						selectedFound = true;
					}
				}
			}
			if (!selectedFound || selectedCatalog == null) return empty;

			var byDirectory:Map<String, NightmareVisionModFamilyMember> = new Map();
			var byRoot:Map<String, String> = new Map();
			for (entry in committed) {
				if (entry.catalog.snapshotId != selectedSnapshot || !sameCatalog(entry.catalog, selectedCatalog)) continue;
				for (mapping in installedMappings(install, entry.manifest, entry.record, selectedCatalog)) {
					if (mapping == null) continue;
					var directoryKey = mapping.directory.toLowerCase();
					var rootKey = pathKey(canonicalDirectory(Path.join([install, mapping.root])));
					var priorDirectory = byDirectory.get(directoryKey);
					var priorLabel = byRoot.get(rootKey);
					if ((priorDirectory != null && !samePath(priorDirectory.root, mapping.root))
						|| (priorLabel != null && priorLabel != mapping.directory))
						return empty;
					if (priorDirectory == null) byDirectory.set(directoryKey, mapping);
					byRoot.set(rootKey, mapping.directory);
				}
			}
			var result:Array<NightmareVisionModFamilyMember> = [];
			for (member in byDirectory) result.push(member);
			result.sort(function(a, b) {
				var folded = Reflect.compare(a.directory.toLowerCase(), b.directory.toLowerCase());
				return folded != 0 ? folded : Reflect.compare(a.directory, b.directory);
			});
			for (member in result)
				if (samePath(canonicalDirectory(Path.join([install, member.root])), normalizedOwner)) return result;
			return empty;
		} catch (_:Dynamic) return empty;
	}

	static function loadCommittedImports(install:String, cache:String):Array<ImportPackageFamilyCommittedImport> {
		var result:Array<ImportPackageFamilyCommittedImport> = [];
		var recordsRoot = Path.join([cache, "records"]);
		var stateRoot = Path.join([cache, "state"]);
		if (!safeExistingDirectory(install, cache) || !safeExistingDirectory(install, recordsRoot)
			|| !safeExistingDirectory(install, stateRoot)) return result;
		var names = FileSystem.readDirectory(recordsRoot);
		if (names.length > MAX_RECORDS) return result;
		names.sort(Reflect.compare);
		var probeCache:Map<String, Null<ImportRefreshPackageFamilyCatalog>> = new Map();
		for (name in names) {
			if (!~/^[a-f0-9]{64}\.json$/.match(name)) continue;
			var id = name.substr(0, 64);
			var pointer = safeChild(recordsRoot, name);
			if (pointer == null || !isRegularFile(pointer)) continue;
			try {
				var pointerValue:Dynamic = Json.parse(File.getContent(pointer));
				if (Reflect.field(pointerValue, "id") != id) continue;
			} catch (_:Dynamic) continue;
			var owner = "retained-import:" + id;
			var manifest:ImportRefreshManifest;
			try manifest = ImportRefreshTransaction.loadManifest(stateRoot, owner) catch (_:Dynamic) continue;
			if (manifest == null || manifest.owner != owner || manifest.revision == null) continue;
			var record:Dynamic = Reflect.field(manifest.revision, "importRecord");
			if (!validRecordIdentity(record, id)) continue;
			var snapshotRoot = safeChild(cache, "sources/" + record.snapshotId);
			if (snapshotRoot == null || !safeExistingDirectory(install, snapshotRoot)) continue;
			var catalog:Null<ImportRefreshPackageFamilyCatalog> = null;
			var persisted:Dynamic = Reflect.field(manifest, "packageFamilyCatalog");
			if (persisted != null && Reflect.field(persisted, "version") == 2) {
				var structure:Null<ImportPackageFamilySourceStructure> = null;
				try {
					catalog = ImportRefreshTransaction.validatePackageFamilyCatalog(persisted, record);
					structure = discoverStructure(snapshotRoot, record);
				} catch (_:Dynamic) catalog = null;
				if (!sameSourceStructure(catalog, structure)) catalog = null;
			} else {
				var key = Std.string(record.snapshotId);
				if (probeCache.exists(key)) catalog = probeCache.get(key);
				else {
					try catalog = discover(snapshotRoot, record) catch (_:Dynamic) catalog = null;
					probeCache.set(key, catalog);
				}
				if (persisted != null && catalog != null) {
					try {
						if (!sameCatalog(ImportRefreshTransaction.validatePackageFamilyCatalog(persisted, record), catalog))
							catalog = null;
					} catch (_:Dynamic) catalog = null;
				}
			}
			if (catalog == null) continue;
			result.push({manifest:manifest, record:record, catalog:catalog});
		}
		return result;
	}

	/** Revalidate the retained source layout independently of installed labels.
	 * Full-root captures prove the outer NMV installation from retained source
	 * files. Captures beginning at content/ require persisted scanner evidence
	 * from the original scan or direct NMV chart structure in the retained tree. */
	static function discoverStructure(snapshotRoot:String, record:Dynamic):Null<ImportPackageFamilySourceStructure> {
		if (record == null || !Std.isOfType(Reflect.field(record, "snapshotId"), String)
			|| Reflect.field(record, "source") != "sources/" + Std.string(record.snapshotId) + "/content") return null;
		var snapshotId = Std.string(record.snapshotId).toLowerCase();
		if (!~/^[a-f0-9]{64}$/.match(snapshotId)
			|| Path.withoutDirectory(Path.normalize(snapshotRoot)).toLowerCase() != snapshotId) return null;
		var normalizedSnapshot = canonicalDirectory(snapshotRoot);
		var receiptPath = safeChild(normalizedSnapshot, "receipt.json");
		if (receiptPath == null || !isRegularFile(receiptPath)) return null;
		var receipt:Dynamic = Json.parse(File.getContent(receiptPath));
		if (Reflect.field(receipt, "snapshotSchemaVersion") != ImportSourceSnapshot.RECEIPT_SCHEMA_VERSION
			|| Reflect.field(receipt, "snapshotId") != snapshotId || Reflect.field(receipt, "contentRoot") != "content") return null;
		var revision:Dynamic = Reflect.field(receipt, "importRevision");
		var incomplete:Dynamic = Reflect.field(receipt, "incompleteReasons");
		var rawDirectories:Dynamic = Reflect.field(receipt, "directories");
		var sourceEngines:Dynamic = Reflect.field(record, "engines");
		var hasNightmareVision = false;
		var receiptEngineMatches = false;
		if (Std.isOfType(sourceEngines, Array)) for (engine in (cast sourceEngines:Array<Dynamic>)) {
			if (engine == "Nightmare Vision") hasNightmareVision = true;
			if (revision != null && engine == Reflect.field(revision, "sourceEngine")) receiptEngineMatches = true;
		}
		if (revision == null || !hasNightmareVision || !receiptEngineMatches
			|| !Std.isOfType(incomplete, Array) || (cast incomplete:Array<Dynamic>).length != 0
			|| !Std.isOfType(rawDirectories, Array)) return null;
		var recordedDirectories:Map<String, Bool> = new Map();
		for (value in (cast rawDirectories:Array<Dynamic>))
			if (Std.isOfType(value, String)) recordedDirectories.set(Std.string(value).toLowerCase(), true);
		var sourceRoot = safeChild(normalizedSnapshot, "content");
		if (sourceRoot == null || !safeExistingDirectory(normalizedSnapshot, sourceRoot)) return null;
		var rawRoots:Dynamic = Reflect.field(record, "roots");
		if (!Std.isOfType(rawRoots, Array)) return null;
		var retained:Map<String, String> = new Map();
		var recordedAssetMembers:Map<String, String> = new Map();
		var fullRootProvenance = false;
		var containerRootCount = 0;
		var containerEvidence:Map<String, Bool> = new Map();
		for (root in (cast rawRoots:Array<Dynamic>)) {
			if (root == null || Reflect.field(root, "engine") != "Nightmare Vision") continue;
			var relativeValue:Dynamic = Reflect.field(root, "relative");
			if (!Std.isOfType(relativeValue, String)) return null;
			var relative:String = cast relativeValue;
			var path = relative == "" ? sourceRoot : safeChild(sourceRoot, relative);
			if (path == null || !FileSystem.isDirectory(path)) return null;
			retained.set(path, "Nightmare Vision");
			if (relative == "") fullRootProvenance = true;
			var parts = relative.split("/");
			if (parts.length == 3 && parts[0].toLowerCase() == "content"
				&& parts[1] != "" && parts[1] != "." && parts[1] != ".."
				&& parts[1].indexOf("\\") < 0 && parts[2].toLowerCase() == "assets")
				recordedAssetMembers.set(parts[1].toLowerCase(), relative);
			if (relative != "" && relative.indexOf("/") < 0 && relative.indexOf("\\") < 0) {
				containerRootCount++;
				var evidence:Dynamic = Reflect.field(root, "evidence");
				if (Std.isOfType(evidence, Array) && evidenceContains(cast evidence, FAMILY_EVIDENCE))
					containerEvidence.set(relative.toLowerCase(), true);
			}
		}
		var previousEngines = ImportRootScanner.setRetainedSourceEngines(retained);
		var structure:Null<ImportPackageFamilySourceStructure> = null;
		try {
			var containerRelative:String = null;
			var container:String = null;
			var parentProven = false;
			if (fullRootProvenance && recordedDirectories.exists("content")) {
				container = safeChild(sourceRoot, "content");
				if (container != null && safeExistingDirectory(normalizedSnapshot, container)) {
					parentProven = isAuthenticatedNightmareVisionContainer(sourceRoot);
					if (parentProven) containerRelative = "content";
				}
			}
			if (containerRelative == null && containerRootCount >= 2) {
				container = sourceRoot;
				containerRelative = "";
			}
			if (containerRelative != null && container != null) {
				var packageNames = FileSystem.readDirectory(container);
				if (packageNames.length <= MAX_FAMILY_DIRECTORIES) {
					packageNames.sort(Reflect.compare);
					var members:Array<ImportPackageFamilySourceMember> = [];
					var seen:Map<String, Bool> = new Map();
					var invalidDirectory = false;
					for (name in packageNames) {
						if (name == "" || name == "." || name == ".." || name.indexOf("/") >= 0 || name.indexOf("\\") >= 0) {
							invalidDirectory = true;
							break;
						}
						var folded = name.toLowerCase();
						if (seen.exists(folded)) {
							invalidDirectory = true;
							break;
						}
						seen.set(folded, true);
						var relative = containerRelative == "" ? name : containerRelative + "/" + name;
						if (!recordedDirectories.exists(relative.toLowerCase())) continue;
						var child = safeChild(container, name);
						if (child == null || !FileSystem.isDirectory(child)) continue;
						var inspected = ImportRootScanner.inspectRoot(child, ImportEngine.AUTO);
						if (inspected != null && inspected.engine != "Nightmare Vision") continue;
						var sourceProven = inspected != null && parentProven
							&& evidenceContains(inspected.evidence, FAMILY_EVIDENCE);
						if (containerRelative == "")
							sourceProven = inspected != null && (containerEvidence.exists(name.toLowerCase())
								|| hasNmvContainerProof(inspected.evidence));
						// Native NMV game roots commonly record their content packages at
						// content/<name>/assets. The outer scanner proof authenticates the
						// container; the exact recorded assets root and direct package
						// metadata bind the member without guessing from chart names.
						var assetRelative = recordedAssetMembers.get(name.toLowerCase());
						var packageMetadata = safeChild(child, "meta.json");
						var canonicalAssetsMember = parentProven && assetRelative != null
							&& recordedDirectories.exists(relative.toLowerCase())
							&& recordedDirectories.exists(assetRelative.toLowerCase())
							&& packageMetadata != null && isRegularFile(packageMetadata);
						if (containerRelative == "content" && canonicalAssetsMember)
							sourceProven = true;
						if (!sourceProven) continue;
						members.push({directory:name, sourceRelative:relative, sourceRoot:child});
					}
					if (!invalidDirectory && members.length >= 2) {
						members.sort(function(a, b) {
							var folded = Reflect.compare(a.sourceRelative.toLowerCase(), b.sourceRelative.toLowerCase());
							return folded != 0 ? folded : Reflect.compare(a.sourceRelative, b.sourceRelative);
						});
						structure = {snapshotId:snapshotId, containerRelative:containerRelative, members:members};
					}
				}
			}
		} catch (_:Dynamic) {}
		ImportRootScanner.setRetainedSourceEngines(previousEngines);
		return structure;
	}

	static function hasNmvContainerProof(evidence:Array<String>):Bool {
		if (evidence == null) return false;
		for (item in evidence) if (item != null
			&& (StringTools.startsWith(item, "Nightmare Vision executable package marker:")
				|| StringTools.startsWith(item, "Nightmare Vision Haxe project package:")
				|| StringTools.startsWith(item, "Nightmare Vision chart metadata: format=nmv2"))) return true;
		return false;
	}

	static function evidenceContains(evidence:Array<String>, expected:String):Bool {
		if (evidence == null || expected == null) return false;
		for (item in evidence) if (item == expected) return true;
		return false;
	}

	static function sameSourceStructure(catalog:ImportRefreshPackageFamilyCatalog,
		structure:Null<ImportPackageFamilySourceStructure>):Bool {
		if (catalog == null || structure == null || catalog.version != 2
			|| catalog.snapshotId != structure.snapshotId || catalog.containerRelative != structure.containerRelative
			|| catalog.members == null || catalog.members.length < 2
			|| catalog.members.length > structure.members.length) return false;
		for (member in catalog.members) {
			var matched = false;
			for (sourceMember in structure.members)
				if (member.directory == sourceMember.directory && member.sourceRelative == sourceMember.sourceRelative)
					matched = true;
			if (!matched) return false;
		}
		return true;
	}

	static function hasStagedMemberOutputs(namespace:String, written:Array<String>):Bool {
		if (namespace == null || written == null) return false;
		var prefix = "assets/imported_mods/" + namespace + "/";
		var configPath = prefix + "meta.json";
		var hasConfig = false;
		var hasRuntime = false;
		for (path in written) {
			var key = pathKey(path);
			if (key == pathKey(configPath)) hasConfig = true;
			if (StringTools.startsWith(key, pathKey(prefix)) && key != pathKey(configPath)
				&& !StringTools.startsWith(key, pathKey(prefix + "__nmv_core/"))) hasRuntime = true;
		}
		return hasConfig && hasRuntime;
	}

	static function discover(snapshotRoot:String, record:Dynamic):Null<ImportRefreshPackageFamilyCatalog> {
		if (record == null || !Std.isOfType(Reflect.field(record, "snapshotId"), String)
			|| !Std.isOfType(Reflect.field(record, "source"), String)) return null;
		var snapshotId = Std.string(record.snapshotId).toLowerCase();
		if (!~/^[a-f0-9]{64}$/.match(snapshotId)
			|| Reflect.field(record, "source") != "sources/" + snapshotId + "/content") return null;
		if (Path.withoutDirectory(Path.normalize(snapshotRoot)).toLowerCase() != snapshotId) return null;
		var normalizedSnapshot = canonicalDirectory(snapshotRoot);
		var receiptPath = safeChild(normalizedSnapshot, "receipt.json");
		if (receiptPath == null || !isRegularFile(receiptPath)) return null;
		var receipt:Dynamic = Json.parse(File.getContent(receiptPath));
		if (Reflect.field(receipt, "snapshotSchemaVersion") != ImportSourceSnapshot.RECEIPT_SCHEMA_VERSION
			|| Reflect.field(receipt, "snapshotId") != snapshotId || Reflect.field(receipt, "contentRoot") != "content") return null;
		var revision:Dynamic = Reflect.field(receipt, "importRevision");
		if (revision == null || Reflect.field(revision, "sourceEngine") != "Nightmare Vision") return null;
		var incomplete:Dynamic = Reflect.field(receipt, "incompleteReasons");
		var rawDirectories:Dynamic = Reflect.field(receipt, "directories");
		if (!Std.isOfType(incomplete, Array) || (cast incomplete:Array<Dynamic>).length != 0
			|| !Std.isOfType(rawDirectories, Array)) return null;
		var recordedDirectories:Map<String, Bool> = new Map();
		for (value in (cast rawDirectories:Array<Dynamic>))
			if (Std.isOfType(value, String)) recordedDirectories.set(Std.string(value).toLowerCase(), true);
		var sourceRoot = safeChild(normalizedSnapshot, "content");
		if (sourceRoot == null || !safeExistingDirectory(normalizedSnapshot, sourceRoot)) return null;
		var containerRelative = "content";
		var container = safeChild(sourceRoot, containerRelative);
		if (container == null || !safeExistingDirectory(normalizedSnapshot, container)
			|| !recordedDirectories.exists(containerRelative)) return null;
		var packageNames = FileSystem.readDirectory(container);
		if (packageNames.length > MAX_FAMILY_DIRECTORIES) return null;
		packageNames.sort(Reflect.compare);
		var retained:Map<String, String> = new Map();
		for (root in (cast record.roots:Array<Dynamic>)) {
			if (root == null || !Std.isOfType(Reflect.field(root, "relative"), String)
				|| !Std.isOfType(Reflect.field(root, "engine"), String)) continue;
			var relative:String = cast Reflect.field(root, "relative");
			var engine:String = cast Reflect.field(root, "engine");
			if (engine == "Nightmare Vision") {
				var retainedRoot = relative == "" ? sourceRoot : safeChild(sourceRoot, relative);
				if (retainedRoot == null) return null;
				retained.set(Path.normalize(retainedRoot), engine);
			}
		}
		var previousEngines = ImportRootScanner.setRetainedSourceEngines(retained);
		var members:Array<ImportRefreshPackageFamilyCatalogEntry> = [];
		var seen:Map<String, Bool> = new Map();
		var invalidDirectory = false;
		try {
			for (name in packageNames) {
				if (name == "" || name == "." || name == ".." || name.indexOf("/") >= 0 || name.indexOf("\\") >= 0) {
					invalidDirectory = true;
					break;
				}
				var folded = name.toLowerCase();
				if (seen.exists(folded)) {
					invalidDirectory = true;
					break;
				}
				seen.set(folded, true);
				var child = safeChild(container, name);
				if (child == null || !FileSystem.exists(child) || !FileSystem.isDirectory(child)
					|| !recordedDirectories.exists((containerRelative + "/" + name).toLowerCase())) continue;
				var childRoot = ImportRootScanner.inspectRoot(child, ImportEngine.AUTO);
				if (childRoot == null || childRoot.engine != "Nightmare Vision"
					|| childRoot.evidence == null || childRoot.evidence.indexOf(FAMILY_EVIDENCE) < 0) continue;
				members.push({directory:name, sourceRelative:containerRelative + "/" + name});
			}
		} catch (_:Dynamic) {
			invalidDirectory = true;
		}
		ImportRootScanner.setRetainedSourceEngines(previousEngines);
		if (invalidDirectory) return null;
		if (members.length < 2) return null;
		members.sort(function(a, b) {
			var folded = Reflect.compare(a.sourceRelative.toLowerCase(), b.sourceRelative.toLowerCase());
			return folded != 0 ? folded : Reflect.compare(a.sourceRelative, b.sourceRelative);
		});
		var catalog:ImportRefreshPackageFamilyCatalog = {
			version:1, engine:"Nightmare Vision", snapshotId:snapshotId,
			containerRelative:containerRelative, members:members
		};
		var validationRoots:Array<Dynamic> = [for (member in members) {
			relative:member.sourceRelative,
			label:member.directory,
			engine:"Nightmare Vision",
			namespace:"catalog-validation"
		}];
		return ImportRefreshTransaction.validatePackageFamilyCatalog(catalog, {
			schemaVersion:1,
			snapshotId:snapshotId,
			source:"sources/" + snapshotId + "/content",
			engines:["Nightmare Vision"],
			roots:validationRoots
		});
	}

	static function installedMapping(install:String, manifest:ImportRefreshManifest,
		root:Dynamic, catalog:ImportRefreshPackageFamilyCatalog):Null<NightmareVisionModFamilyMember> {
		if (root == null || Reflect.field(root, "engine") != "Nightmare Vision") return null;
		var relative:Dynamic = Reflect.field(root, "relative");
		var label:Dynamic = Reflect.field(root, "label");
		var namespace:Dynamic = Reflect.field(root, "namespace");
		if (!Std.isOfType(relative, String) || !Std.isOfType(label, String)
			|| !Std.isOfType(namespace, String) || namespace == "") return null;
		var sourceRelative:String = cast relative;
		var directory:String = cast label;
		var matched = false;
		for (member in catalog.members)
			if (member.sourceRelative == sourceRelative && member.directory == directory) matched = true;
		if (!matched) return null;
		var destination = "assets/imported_mods/" + Std.string(namespace);
		try if (normalizeRelative(destination) != destination) return null catch (_:Dynamic) return null;
		var owned = false;
		for (rootValue in manifest.ownedRoots)
			if (destination == rootValue || StringTools.startsWith(destination, rootValue + "/")) owned = true;
		if (!owned) return null;
		if (!manifestHasMemberConfigAndRuntime(install, manifest, destination)) return null;
		return {directory:directory, root:destination};
	}

	static function installedMappings(install:String, manifest:ImportRefreshManifest,
		record:Dynamic, catalog:ImportRefreshPackageFamilyCatalog):Array<NightmareVisionModFamilyMember> {
		var result:Array<NightmareVisionModFamilyMember> = [];
		if (catalog == null || manifest == null) return result;
		if (catalog.version == 2) {
			if (catalog.members == null) return result;
			for (member in catalog.members) {
				var mapping = installedMappingV2(install, manifest, member);
				if (mapping != null) result.push(mapping);
			}
			return result;
		}
		if (record == null || !Std.isOfType(Reflect.field(record, "roots"), Array)) return result;
		for (root in (cast record.roots:Array<Dynamic>)) {
			var mapping = installedMapping(install, manifest, root, catalog);
			if (mapping != null) result.push(mapping);
		}
		return result;
	}

	static function installedMappingV2(install:String, manifest:ImportRefreshManifest,
		member:ImportRefreshPackageFamilyCatalogEntry):Null<NightmareVisionModFamilyMember> {
		if (member == null || member.namespace == null || member.namespace == "") return null;
		var destination = "assets/imported_mods/" + member.namespace;
		try if (normalizeRelative(destination) != destination) return null catch (_:Dynamic) return null;
		var ownedRoot = false;
		for (root in manifest.ownedRoots)
			if (destination == root || StringTools.startsWith(destination, root + "/")) ownedRoot = true;
		if (!ownedRoot) return null;
		if (!manifestHasMemberConfigAndRuntime(install, manifest, destination)) return null;
		return {directory:member.directory, root:destination};
	}

	static function manifestHasMemberConfigAndRuntime(install:String, manifest:ImportRefreshManifest,
		destination:String):Bool {
		var hasConfig = false;
		var hasRuntime = false;
		for (file in manifest.files) {
			var live = safeChild(install, file.path);
			if (live == null || !isRegularFile(live)) continue;
			if (pathKey(file.path) == pathKey(destination + "/meta.json")) hasConfig = true;
			if (StringTools.startsWith(pathKey(file.path), pathKey(destination + "/"))
				&& pathKey(file.path) != pathKey(destination + "/meta.json")
				&& !StringTools.startsWith(pathKey(file.path), pathKey(destination + "/__nmv_core/"))) hasRuntime = true;
		}
		var absolute = safeChild(install, destination);
		return hasConfig && hasRuntime && absolute != null && safeExistingDirectory(install, absolute);
	}

	static function sameCatalog(left:ImportRefreshPackageFamilyCatalog,
		right:ImportRefreshPackageFamilyCatalog):Bool {
		if (left == null || right == null || left.version != right.version || left.engine != right.engine
			|| left.snapshotId != right.snapshotId || left.containerRelative != right.containerRelative
			|| left.members == null || right.members == null || left.members.length != right.members.length) return false;
		for (index in 0...left.members.length)
			if (left.members[index].directory != right.members[index].directory
				|| left.members[index].sourceRelative != right.members[index].sourceRelative
				|| left.members[index].namespace != right.members[index].namespace) return false;
		return true;
	}

	static function validRecordIdentity(record:Dynamic, id:String):Bool {
		if (record == null || id == null || !~/^[a-f0-9]{64}$/.match(id)
			|| Reflect.field(record, "schemaVersion") != 1 || Reflect.field(record, "id") != id) return false;
		var snapshotId:Dynamic = Reflect.field(record, "snapshotId");
		var source:Dynamic = Reflect.field(record, "source");
		if (!Std.isOfType(snapshotId, String) || !~/^[a-f0-9]{64}$/.match(Std.string(snapshotId))
			|| source != "sources/" + Std.string(snapshotId) + "/content") return false;
		var roots:Dynamic = Reflect.field(record, "roots");
		var engines:Dynamic = Reflect.field(record, "engines");
		if (!Std.isOfType(roots, Array) || !Std.isOfType(engines, Array)) return false;
		var hasNightmareVision = false;
		for (engine in (cast engines:Array<Dynamic>)) if (engine == "Nightmare Vision") hasNightmareVision = true;
		if (!hasNightmareVision) return false;
		var matchingRoot = false;
		for (root in (cast roots:Array<Dynamic>)) {
			if (root == null || Reflect.field(root, "engine") != "Nightmare Vision") continue;
			var relative:Dynamic = Reflect.field(root, "relative");
			var label:Dynamic = Reflect.field(root, "label");
			var namespace:Dynamic = Reflect.field(root, "namespace");
			if (!Std.isOfType(relative, String) || !Std.isOfType(label, String)
				|| !Std.isOfType(namespace, String) || namespace == "") return false;
			if (relative != "" && normalizeRelative(Std.string(relative)) != Std.string(relative)) return false;
			if (normalizeRelative("assets/imported_mods/" + Std.string(namespace))
				!= "assets/imported_mods/" + Std.string(namespace)) return false;
			matchingRoot = true;
		}
		return matchingRoot;
	}

	static function canonicalDirectory(path:String):String {
		if (path == null || !FileSystem.exists(path) || !FileSystem.isDirectory(path)) throw "Expected directory.";
		var normalized = Path.normalize(FileSystem.fullPath(path));
		if (!samePath(normalized, Path.normalize(path))) throw "Protected directory is a symlink.";
		return normalized;
	}

	static function safeChild(root:String, relative:String):Null<String> {
		if (root == null || relative == null || relative == "" || Path.isAbsolute(relative)
			|| relative.indexOf(":") >= 0 || relative.indexOf("\\") >= 0) return null;
		var parts = relative.split("/");
		for (part in parts) if (part == "" || part == "." || part == "..") return null;
		var candidate = Path.normalize(Path.join([root, relative]));
		if (!isWithin(candidate, root)) return null;
		var current = root;
		for (part in parts) {
			current = Path.join([current, part]);
			if (!FileSystem.exists(current)) continue;
			var resolved = Path.normalize(FileSystem.fullPath(current));
			if (!samePath(resolved, Path.normalize(current))) return null;
		}
		return candidate;
	}

	static function safeExistingDirectory(root:String, path:String):Bool {
		try return FileSystem.exists(path) && FileSystem.isDirectory(path)
			&& isWithin(canonicalDirectory(path), canonicalDirectory(root)) catch (_:Dynamic) return false;
	}

	static function isRegularFile(path:String):Bool {
		try return FileSystem.exists(path) && !FileSystem.isDirectory(path) catch (_:Dynamic) return false;
	}

	static function normalizeRelative(value:String):String {
		if (value == null || value == "" || Path.isAbsolute(value) || value.indexOf(":") >= 0)
			throw "Unsafe relative path.";
		var parts = StringTools.replace(value, "\\", "/").split("/");
		for (part in parts) if (part == "" || part == "." || part == "..") throw "Unsafe relative path.";
		return parts.join("/");
	}

	static function isWithin(candidate:String, root:String):Bool {
		var base = Path.addTrailingSlash(Path.normalize(root));
		var path = Path.normalize(candidate);
		return samePath(path, Path.normalize(root)) || samePath(path.substr(0, base.length), base);
	}

	static function pathKey(path:String):String {
		#if windows
		return Path.normalize(path).toLowerCase();
		#else
		return Path.normalize(path);
		#end
	}

	static function samePath(left:String, right:String):Bool {
		#if windows
		return left.toLowerCase() == right.toLowerCase();
		#else
		return left == right;
		#end
	}
}
#else
import NightmareVisionModFamilyMember;
import ImportRefreshTransaction.ImportRefreshPackageFamilyCatalog;

class ImportPackageFamilyCatalog {
	public static function capture(snapshotRoot:String, record:Dynamic):Null<ImportRefreshPackageFamilyCatalog> return null;
	public static function forOwner(ownerRoot:String):Array<NightmareVisionModFamilyMember> return [];
}
#end
