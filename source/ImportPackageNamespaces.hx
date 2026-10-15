package;

#if sys
import haxe.io.Path;
import sys.FileSystem;

typedef ImportPackageNamespaceEntry = {
	var relative:String;
	var engine:String;
	var namespace:String;
}

/**
	Keeps the namespace of each Nightmare Vision content package (a folder in
	`<game>/content`) the same across re-imports.

	A package that is not itself a recorded import root got its namespace from a
	hash of its path inside the retained source snapshot. Every re-import that
	captured a new snapshot therefore moved the package to a new namespace,
	which dropped its saves and left the old namespace behind as empty folders.
	The namespaces that packages actually used are now stored in the import
	record and bound again before the next conversion.
*/
class ImportPackageNamespaces {
	public static inline var FIELD:String = "packageNamespaces";
	static inline var ENGINE:String = "Nightmare Vision";
	static inline var MAX_PACKAGES:Int = 256;
	static inline var MAX_EMPTY_WALK:Int = 100000;
	static inline var HASH_LENGTH:Int = 10;

	/** Source-relative content package folders of the record's Nightmare Vision
	 * roots, plus their `assets` folders, which some packages use as their root. */
	public static function packageRoots(source:String, record:Dynamic):Array<String> {
		var result:Array<String> = [];
		var roots:Dynamic = record == null ? null : Reflect.field(record, "roots");
		if (source == null || !Std.isOfType(roots, Array)) return result;
		var recorded:Map<String, Bool> = new Map();
		for (root in (cast roots:Array<Dynamic>)) {
			var relative:Dynamic = root == null ? null : Reflect.field(root, "relative");
			if (Std.isOfType(relative, String)) recorded.set(Std.string(relative).toLowerCase(), true);
		}
		var seen:Map<String, Bool> = new Map();
		for (root in (cast roots:Array<Dynamic>)) {
			if (root == null || ImportRevision.normalizeEngine(Std.string(Reflect.field(root, "engine"))) != ENGINE)
				continue;
			var relative:Dynamic = Reflect.field(root, "relative");
			if (!Std.isOfType(relative, String) || !safeRelative(Std.string(relative), true)) continue;
			var container = relative == "" ? "content" : Std.string(relative) + "/content";
			var containerPath = Path.join([source, container]);
			if (!FileSystem.exists(containerPath) || !FileSystem.isDirectory(containerPath)) continue;
			var names = FileSystem.readDirectory(containerPath);
			names.sort(Reflect.compare);
			for (name in names) {
				ImportWorkScheduler.cooperate();
				if (!safeRelative(name, false) || name.indexOf("/") >= 0) continue;
				var packageRelative = container + "/" + name;
				if (!FileSystem.isDirectory(Path.join([source, packageRelative]))) continue;
				for (candidate in [packageRelative, packageRelative + "/assets"]) {
					var key = candidate.toLowerCase();
					if (seen.exists(key) || recorded.exists(key)) continue;
					if (candidate != packageRelative && !FileSystem.isDirectory(Path.join([source, candidate]))) continue;
					seen.set(key, true);
					result.push(candidate);
					if (result.length >= MAX_PACKAGES) return result;
				}
			}
		}
		return result;
	}

	/** Bind every content package to the namespace it used last time. Call after
	 * the record roots and family members are bound and before conversion. */
	public static function retain(io:ImportIO, source:String, record:Dynamic, previous:Dynamic):Void {
		if (io == null || source == null || record == null) return;
		var claimed = recordNamespaces(record);
		var bound:Map<String, Bool> = new Map();
		var persisted = entries(record);
		for (entry in persisted) {
			var path = Path.join([source, entry.relative]);
			if (!FileSystem.exists(path) || !FileSystem.isDirectory(path)) continue;
			if (claimed.exists(entry.namespace) || io.namespace(path, entry.engine) != null) continue;
			io.setNamespace(path, entry.engine, entry.namespace);
			claimed.set(entry.namespace, true);
			bound.set(entry.relative.toLowerCase(), true);
		}
		if (persisted.length > 0 || previous == null) return;
		// Receipts written before this field existed only list the files. A package
		// keeps its old namespace when exactly one earlier namespace carries its
		// readable label and no other package shares that label.
		var owned:Map<String, Bool> = new Map();
		for (namespace in manifestNamespaces(previous).keys())
			if (!claimed.exists(namespace)) owned.set(namespace, true);
		var byLabel:Map<String, Array<String>> = new Map();
		for (relative in packageRoots(source, record)) {
			if (bound.exists(relative.toLowerCase()) || StringTools.endsWith(relative.toLowerCase(), "/assets")) continue;
			var path = Path.join([source, relative]);
			if (io.namespace(path, ENGINE) != null) continue;
			var label = CompatScriptManifest.namespaceLabel(path, ENGINE);
			var group = byLabel.get(label);
			if (group == null) byLabel.set(label, group = []);
			group.push(relative);
		}
		for (label in byLabel.keys()) {
			var group = byLabel.get(label);
			if (group.length != 1) continue;
			var matches = [for (namespace in owned.keys()) if (labelOf(namespace) == label) namespace];
			if (matches.length != 1) continue;
			io.setNamespace(Path.join([source, group[0]]), ENGINE, matches[0]);
			owned.remove(matches[0]);
		}
	}

	/** Store the namespaces content packages used in this conversion. Only
	 * namespaces with staged outputs are kept, so a package that produced nothing
	 * does not reserve a name. */
	public static function capture(io:ImportIO, source:String, record:Dynamic):Void {
		if (io == null || source == null || record == null) return;
		var withOutputs:Map<String, Bool> = new Map();
		for (path in io.writtenPaths()) {
			var namespace = namespaceOfPath(path);
			if (namespace != null) withOutputs.set(namespace, true);
		}
		var roots = recordNamespaces(record);
		var result:Array<ImportPackageNamespaceEntry> = [];
		for (relative in packageRoots(source, record)) {
			var namespace = io.resolvedNamespace(Path.join([source, relative]), ENGINE);
			if (namespace == null || !validNamespace(namespace) || !withOutputs.exists(namespace) || roots.exists(namespace))
				continue;
			result.push({relative:relative, engine:ENGINE, namespace:namespace});
		}
		if (result.length > 0) Reflect.setField(record, FIELD, result);
		else Reflect.deleteField(record, FIELD);
	}

	/** Remove namespace folders that hold no files at all: ones this import owned
	 * before and no longer writes, and same-label leftovers of a package whose
	 * namespace moved in an earlier re-import. Folders with any file are kept. */
	public static function pruneEmptyNamespaces(install:String, previous:Dynamic, committed:Dynamic):Int {
		if (install == null || committed == null) return 0;
		var current = manifestNamespaces(committed);
		var candidates:Map<String, Bool> = new Map();
		if (previous != null)
			for (namespace in manifestNamespaces(previous).keys())
				if (!current.exists(namespace)) candidates.set(namespace, true);
		var labels:Map<String, Bool> = new Map();
		for (namespace in current.keys()) {
			var label = labelOf(namespace);
			if (label != null) labels.set(label, true);
		}
		var parent = Path.join([install, CompatScriptManifest.ROOT_PREFIX]);
		if (!FileSystem.exists(parent) || !FileSystem.isDirectory(parent)) return 0;
		for (name in FileSystem.readDirectory(parent)) {
			var namespace = name.toLowerCase();
			if (current.exists(namespace)) continue;
			var label = labelOf(namespace);
			if (label != null && labels.exists(label)) candidates.set(namespace, true);
		}
		var removed = 0;
		for (namespace in candidates.keys()) {
			ImportWorkScheduler.cooperate();
			if (!validNamespace(namespace)) continue;
			var folder = Path.join([parent, namespace]);
			if (!FileSystem.exists(folder) || !FileSystem.isDirectory(folder)) continue;
			var budget = [MAX_EMPTY_WALK];
			if (!holdsNoFiles(folder, budget, 0)) continue;
			if (deleteEmptyTree(folder)) removed++;
		}
		return removed;
	}

	static function entries(record:Dynamic):Array<ImportPackageNamespaceEntry> {
		var result:Array<ImportPackageNamespaceEntry> = [];
		var raw:Dynamic = Reflect.field(record, FIELD);
		if (!Std.isOfType(raw, Array)) return result;
		for (value in (cast raw:Array<Dynamic>)) {
			if (value == null) continue;
			var relative:Dynamic = Reflect.field(value, "relative");
			var engine:Dynamic = Reflect.field(value, "engine");
			var namespace:Dynamic = Reflect.field(value, "namespace");
			if (!Std.isOfType(relative, String) || !Std.isOfType(engine, String) || !Std.isOfType(namespace, String))
				continue;
			if (!safeRelative(relative, false) || !validNamespace(namespace)
				|| ImportRevision.normalizeEngine(engine) != ENGINE) continue;
			result.push({relative:relative, engine:ENGINE, namespace:namespace});
		}
		return result;
	}

	static function recordNamespaces(record:Dynamic):Map<String, Bool> {
		var result:Map<String, Bool> = new Map();
		var roots:Dynamic = Reflect.field(record, "roots");
		if (Std.isOfType(roots, Array)) for (root in (cast roots:Array<Dynamic>)) {
			var namespace:Dynamic = root == null ? null : Reflect.field(root, "namespace");
			if (Std.isOfType(namespace, String)) result.set(Std.string(namespace).toLowerCase(), true);
		}
		var catalog:Dynamic = Reflect.field(record, "packageFamilyCatalog");
		var members:Dynamic = catalog == null ? null : Reflect.field(catalog, "members");
		if (Std.isOfType(members, Array)) for (member in (cast members:Array<Dynamic>)) {
			var namespace:Dynamic = member == null ? null : Reflect.field(member, "namespace");
			if (Std.isOfType(namespace, String)) result.set(Std.string(namespace).toLowerCase(), true);
		}
		return result;
	}

	static function manifestNamespaces(manifest:Dynamic):Map<String, Bool> {
		var result:Map<String, Bool> = new Map();
		var files:Dynamic = manifest == null ? null : Reflect.field(manifest, "files");
		if (!Std.isOfType(files, Array)) return result;
		for (file in (cast files:Array<Dynamic>)) {
			var path:Dynamic = file == null ? null : Reflect.field(file, "path");
			var namespace = Std.isOfType(path, String) ? namespaceOfPath(path) : null;
			if (namespace != null) result.set(namespace, true);
		}
		return result;
	}

	static function namespaceOfPath(path:String):Null<String> {
		var prefix = CompatScriptManifest.ROOT_PREFIX + "/";
		if (path == null || !StringTools.startsWith(path.toLowerCase(), prefix)) return null;
		var rest = path.substr(prefix.length);
		var slash = rest.indexOf("/");
		if (slash <= 0) return null;
		var namespace = rest.substr(0, slash).toLowerCase();
		return validNamespace(namespace) ? namespace : null;
	}

	/** `<label>` of a `<label>-<ten hex digits>` namespace, or null. */
	static function labelOf(namespace:String):Null<String> {
		if (namespace == null || namespace.length <= HASH_LENGTH + 1) return null;
		var dash = namespace.length - HASH_LENGTH - 1;
		if (namespace.charAt(dash) != "-") return null;
		for (index in dash + 1...namespace.length) {
			var code = namespace.charCodeAt(index);
			if (!((code >= 48 && code <= 57) || (code >= 97 && code <= 102))) return null;
		}
		return namespace.substr(0, dash);
	}

	static function validNamespace(value:String):Bool {
		if (value == null || value == "" || value.length > 200) return false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			if (!((code >= 97 && code <= 122) || (code >= 48 && code <= 57) || code == 45)) return false;
		}
		return value.charAt(0) != "-";
	}

	static function safeRelative(value:String, allowEmpty:Bool):Bool {
		if (value == null) return false;
		if (value == "") return allowEmpty;
		if (Path.isAbsolute(value) || value.indexOf("\\") >= 0 || value.indexOf(":") >= 0) return false;
		for (part in value.split("/")) if (part == "" || part == "." || part == "..") return false;
		return true;
	}

	static function holdsNoFiles(folder:String, budget:Array<Int>, depth:Int):Bool {
		if (depth > 64) return false;
		for (name in FileSystem.readDirectory(folder)) {
			if (--budget[0] < 0) return false;
			var child = Path.join([folder, name]);
			if (!FileSystem.isDirectory(child) || !holdsNoFiles(child, budget, depth + 1)) return false;
		}
		return true;
	}

	static function deleteEmptyTree(folder:String):Bool {
		try {
			for (name in FileSystem.readDirectory(folder)) {
				var child = Path.join([folder, name]);
				if (!FileSystem.isDirectory(child) || !deleteEmptyTree(child)) return false;
			}
			// deleteDirectory refuses a folder that still has entries, so a file
			// written meanwhile is never removed.
			FileSystem.deleteDirectory(folder);
			return true;
		} catch (_:Dynamic) return false;
	}
}
#end
