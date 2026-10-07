package;

import haxe.io.Bytes;
import haxe.io.Path;
import ImportSourceSnapshot.ImportSnapshotSha256;
import sys.FileSystem as RawFileSystem;
import sys.io.File as RawFile;
import sys.io.FileInput;
import sys.io.FileOutput;
using StringTools;

typedef ImportIOBaseline = {
	var sha256:String;
	var text:Null<String>;
}

private typedef ImportIOPath = {
	var relative:Null<String>;
	var external:String;
	var stageAbsolute:Bool;
}

/**
	Per-thread virtual filesystem used while an import is being regenerated.

	Importer reads see staged output first and then the installed tree. Previous
	owned output paths can be masked so a stale installed copy cannot satisfy a
	new import. Writes are always redirected into stageRoot.
*/
class ImportIO {
	#if target.threaded
	static var threadContext:sys.thread.Tls<ImportIO> = new sys.thread.Tls();
	#else
	static var fallbackContext:ImportIO;
	#end

	public var installRoot(default, null):String;
	public var stageRoot(default, null):String;
	var parent:ImportIO;
	var masks:Map<String, Bool> = new Map();
	var ownedAncestors:Map<String, Bool> = new Map();
	var deferOwnedBaselines:Bool;
	var touched:Map<String, Bool> = new Map();
	var removed:Map<String, Bool> = new Map();
	var baselineCache:Map<String, ImportIOBaseline> = new Map();
	var baselineChecked:Map<String, Bool> = new Map();
	var namespaces:Map<String, String> = new Map();
	var resolvedNamespaces:Map<String, String> = new Map();
	var sourceLabels:Map<String, String> = new Map();

	public function new(installRoot:String, stageRoot:String, ?masked:Array<String>, deferOwnedBaselines:Bool = false) {
		this.deferOwnedBaselines = deferOwnedBaselines;
		if (installRoot == null || StringTools.trim(installRoot) == "")
			throw "Import staging requires an install root.";
		if (stageRoot == null || StringTools.trim(stageRoot) == "")
			throw "Import staging requires a stage root.";
		var lexicalInstall = absoluteNormalized(installRoot);
		this.installRoot = canonicalRoot(installRoot);
		if (!RawFileSystem.exists(this.installRoot) || !RawFileSystem.isDirectory(this.installRoot))
			throw "Import install root must be an existing directory.";
		var lexicalStage = absoluteNormalized(stageRoot);
		var stageRelative = relativeWithin(lexicalStage, lexicalInstall);
		if (stageRelative == null)
			throw "Import stage root must be under installRoot/import-cache/staging.";
		var expectedStage = absoluteNormalized(Path.join([this.installRoot, stageRelative]));
		var resolvedStage = resolveThroughExistingAncestor(lexicalStage);
		if (!samePath(resolvedStage, expectedStage))
			throw "Import stage root cannot traverse symbolic links.";
		this.stageRoot = expectedStage;
		stageRelative = relativeWithin(this.stageRoot, this.installRoot);
		if (stageRelative == "") throw "Import stage root cannot equal the install root.";
		if (stageRelative != null && (!StringTools.startsWith(stageRelative, "import-cache/staging/")
			|| StringTools.startsWith(stageRelative, "assets/")))
			throw "An in-install import stage must be under import-cache/staging and outside assets/.";
		if (masked != null)
			for (path in masked) {
				var relative = outputRelative(path);
				if (relative != null) {
					masks.set(relative, true);
					var ancestor = Path.directory(relative);
					while (ancestor != null && ancestor != "" && ancestor != ".") {
						if (ownedAncestors.exists(ancestor)) break;
						ownedAncestors.set(ancestor, true);
						ancestor = Path.directory(ancestor);
					}
				}
			}
	}

	/** Start a virtual filesystem scope on this thread. Scopes may nest. */
	public static function begin(installRoot:String, stageRoot:String, ?masked:Array<String>, deferOwnedBaselines:Bool = false):ImportIO {
		var context = new ImportIO(installRoot, stageRoot, masked, deferOwnedBaselines);
		context.parent = current();
		setCurrent(context);
		return context;
	}

	/** Restore the scope which was active before the most recent begin(). */
	public static function end():Void {
		var context = current();
		if (context == null)
			throw "ImportIO.end() called without an active import scope.";
		setCurrent(context.parent);
		context.parent = null;
	}

	public static function current():Null<ImportIO> {
		#if target.threaded
		return threadContext.value;
		#else
		return fallbackContext;
		#end
	}

	static function setCurrent(context:ImportIO):Void {
		#if target.threaded
		threadContext.value = context;
		#else
		fallbackContext = context;
		#end
	}

	/** Resolve a read to the newest staged file, or to the installed fallback. */
	public function readPath(path:String):String {
		var routed = route(path);
		if (routed.relative == null)
			return routed.external;
		var staged = stagePath(routed.relative);
		if (RawFileSystem.exists(staged)) ensureSafeStagePath(staged);
		if (RawFileSystem.exists(staged) && !RawFileSystem.isDirectory(staged))
			return staged;
		if (isHidden(routed.relative))
			return staged;
		return installPath(routed.relative);
	}

	/** Resolve an output and record its prewrite state before the first write. */
	public function writePath(path:String):String {
		var routed = route(path);
		if (routed.relative == null)
			throw "Writes outside the import stage are forbidden: " + path;
		validateOutputRelative(routed.relative, path);
		markTouched(routed.relative);
		var target = stagePath(routed.relative);
		ensureSafeStagePath(target);
		ensureParent(target);
		clearDeletedAncestors(routed.relative);
		return target;
	}

	/** Prepare a staged append, copying the visible installed version if needed. */
	public function appendPath(path:String):String {
		var routed = route(path);
		if (routed.relative == null)
			throw "Writes outside the import stage are forbidden: " + path;
		validateOutputRelative(routed.relative, path);
		var target = stagePath(routed.relative);
		ensureSafeStagePath(target);
		if (!RawFileSystem.exists(target) && !isHidden(routed.relative)) {
			var installed = installPath(routed.relative);
			if (RawFileSystem.exists(installed) && !RawFileSystem.isDirectory(installed)) {
				ensureParent(target);
				copyStreaming(installed, target);
			}
		}
		markTouched(routed.relative);
		ensureParent(target);
		clearDeletedAncestors(routed.relative);
		return target;
	}

	public function copy(source:String, destination:String):Void {
		copyStreaming(readPath(source), writePath(destination));
	}

	/** All asset outputs touched in this scope, sorted for stable manifests. */
	public function writtenPaths():Array<String> {
		var result:Array<String> = [];
		for (path in touched.keys())
			if (isTrackedOutput(path)) result.push(path);
		result.sort(Reflect.compare);
		return result;
	}

	/** Touched files deleted from the virtual output tree. */
	public function deletedPaths():Array<String> {
		var result:Array<String> = [];
		for (path in removed.keys())
			if (isTrackedOutput(path)) result.push(path);
		result.sort(Reflect.compare);
		return result;
	}

	/** Hash the prewrite installed file; retain text only for shared registries. */
	public function before(path:String):Null<ImportIOBaseline> {
		var relative = outputRelative(path);
		if (relative == null || !isTrackedOutput(relative)) return null;
		if (baselineChecked.exists(relative)) return baselineCache.get(relative);
		baselineChecked.set(relative, true);
		var live = installPath(relative);
		if (!RawFileSystem.exists(live) || RawFileSystem.isDirectory(live)) return null;
		var input:FileInput = null;
		try {
			input = RawFile.read(live, true);
			var hash = new ImportSnapshotSha256();
			var buffer = Bytes.alloc(65536);
			while (true) {
				var count:Int;
				try count = input.readBytes(buffer, 0, buffer.length) catch (_:haxe.io.Eof) break;
				if (count <= 0) break;
				hash.update(buffer, 0, count);
			}
			input.close();
			input = null;
			var text:Null<String> = null;
			if (ImportIO.isRegistry(relative)) text = RawFile.getContent(live);
			var result:ImportIOBaseline = {sha256: hash.digestHex(), text: text};
			baselineCache.set(relative, result);
			return result;
		} catch (error:Dynamic) {
			if (input != null) try input.close() catch (_:Dynamic) {}
			throw "Could not capture prewrite import baseline for " + relative + ": " + Std.string(error);
		}
	}

	/** Whether a path overlaps a prior owned output path. */
	public function hasOwnedPath(path:String):Bool {
		var relative = outputRelative(path);
		if (relative == null) return false;
		// The retained manifest can contain thousands of paths. Index their
		// ancestors once instead of walking every mask for each asset lookup.
		return ownedAncestors.exists(relative) || isMasked(relative);
	}

	public function setNamespace(sourceRoot:String, engine:String, namespace:String):Void {
		var key = sourceEngineKey(sourceRoot, engine);
		if (key != "") namespaces.set(key, namespace);
	}

	public function namespace(sourceRoot:String, engine:String):Null<String> {
		var key = sourceEngineKey(sourceRoot, engine);
		return key == "" ? null : namespaces.get(key);
	}

	/** Record the namespace actually selected by CompatScriptManifest for this
	 * source root. The importer uses this exact result when publishing retained
	 * package-family provenance; it never reconstructs a namespace from labels. */
	public function recordResolvedNamespace(sourceRoot:String, engine:String, namespace:String):Void {
		var key = sourceEngineKey(sourceRoot, engine);
		if (key == "" || namespace == null || StringTools.trim(namespace) == "") return;
		var prior = resolvedNamespaces.get(key);
		if (prior != null && prior != namespace)
			throw "An import source root resolved to multiple destination namespaces.";
		resolvedNamespaces.set(key, namespace);
	}

	public function resolvedNamespace(sourceRoot:String, engine:String):Null<String> {
		var key = sourceEngineKey(sourceRoot, engine);
		return key == "" ? null : resolvedNamespaces.get(key);
	}

	public function setSourceLabel(sourceRoot:String, label:String):Void {
		var key = sourceRootKey(sourceRoot);
		if (key != "") sourceLabels.set(key, label);
	}

	public function sourceLabel(sourceRoot:String):Null<String> {
		var key = sourceRootKey(sourceRoot);
		return key == "" ? null : sourceLabels.get(key);
	}

	public function exists(path:String):Bool {
		var routed = route(path);
		if (routed.relative == null) return RawFileSystem.exists(routed.external);
		var staged = stagePath(routed.relative);
		if (RawFileSystem.exists(staged)) { ensureSafeStagePath(staged); return true; }
		if (isHidden(routed.relative)) return false;
		return RawFileSystem.exists(installPath(routed.relative));
	}

	public function stat(path:String):sys.FileStat {
		var routed = route(path);
		if (routed.relative == null) return RawFileSystem.stat(routed.external);
		var staged = stagePath(routed.relative);
		if (RawFileSystem.exists(staged)) { ensureSafeStagePath(staged); return RawFileSystem.stat(staged); }
		if (isHidden(routed.relative)) throw "Path does not exist in the import view: " + path;
		return RawFileSystem.stat(installPath(routed.relative));
	}

	public function isDirectory(path:String):Bool {
		var routed = route(path);
		if (routed.relative == null) return RawFileSystem.isDirectory(routed.external);
		var staged = stagePath(routed.relative);
		if (RawFileSystem.exists(staged)) { ensureSafeStagePath(staged); return RawFileSystem.isDirectory(staged); }
		if (isHidden(routed.relative)) throw "Path does not exist in the import view: " + path;
		return RawFileSystem.isDirectory(installPath(routed.relative));
	}

	public function readDirectory(path:String):Array<String> {
		var routed = route(path);
		if (routed.relative == null) return RawFileSystem.readDirectory(routed.external);
		if (!exists(path) || !isDirectory(path)) throw "Path is not a directory in the import view: " + path;
		var names:Map<String, Bool> = new Map();
		var stage = stagePath(routed.relative);
		var live = installPath(routed.relative);
		if (RawFileSystem.exists(live) && RawFileSystem.isDirectory(live))
			for (name in RawFileSystem.readDirectory(live)) names.set(name, true);
		if (RawFileSystem.exists(stage)) ensureSafeStagePath(stage);
		if (RawFileSystem.exists(stage) && RawFileSystem.isDirectory(stage))
			for (name in RawFileSystem.readDirectory(stage)) names.set(name, true);
		var output:Array<String> = [];
		for (name in names.keys()) {
			var child = joinRelative(routed.relative, name);
			var stageChild = stagePath(child);
			if (isRemoved(child)) continue;
			if (!RawFileSystem.exists(stageChild) && isMasked(child)) continue;
			if (!RawFileSystem.exists(stageChild) && !RawFileSystem.exists(installPath(child))) continue;
			output.push(name);
		}
		output.sort(Reflect.compare);
		return output;
	}

	public function createDirectory(path:String):Void {
		var routed = route(path);
		if (routed.relative == null) throw "Writes outside the import stage are forbidden: " + path;
		validateOutputRelative(routed.relative, path);
		var target = stagePath(routed.relative);
		ensureSafeStagePath(target);
		ensureParent(target);
		if (!RawFileSystem.exists(target)) RawFileSystem.createDirectory(target);
		clearDeletedAncestors(routed.relative);
	}

	public function deleteFile(path:String):Void {
		var routed = route(path);
		if (routed.relative == null) throw "Writes outside the import stage are forbidden: " + path;
		validateOutputRelative(routed.relative, path);
		markTouched(routed.relative);
		var target = stagePath(routed.relative);
		ensureSafeStagePath(target);
		if (RawFileSystem.exists(target)) {
			if (RawFileSystem.isDirectory(target)) throw "Cannot delete a directory as a file: " + path;
			RawFileSystem.deleteFile(target);
		}
		removed.set(routed.relative, true);
	}

	public function deleteDirectory(path:String):Void {
		var routed = route(path);
		if (routed.relative == null) throw "Writes outside the import stage are forbidden: " + path;
		validateOutputRelative(routed.relative, path);
		if (readDirectory(path).length > 0) throw "Directory is not empty in the import view: " + path;
		var target = stagePath(routed.relative);
		ensureSafeStagePath(target);
		if (RawFileSystem.exists(target) && RawFileSystem.isDirectory(target)) RawFileSystem.deleteDirectory(target);
		removed.set(routed.relative, true);
	}

	public function rename(path:String, newPath:String):Void {
		var source = route(path);
		var destination = route(newPath);
		if (source.relative == null || destination.relative == null)
			throw "Renames outside the import stage are forbidden.";
		validateOutputRelative(source.relative, path);
		validateOutputRelative(destination.relative, newPath);
		if (source.relative == destination.relative) return;
		if (!exists(path)) throw "Rename source does not exist in the import view: " + path;
		if (exists(newPath)) throw "Rename destination already exists in the import view: " + newPath;
		var sourceIsDirectory = isDirectory(path);
		var target = stagePath(destination.relative);
		ensureSafeStagePath(target);
		ensureParent(target);
		if (sourceIsDirectory) {
			RawFileSystem.createDirectory(target);
			for (name in readDirectory(path))
				rename(joinFs(path, name), joinFs(newPath, name));
			deleteDirectory(path);
		} else {
			var sourcePath = readPath(path);
			markTouched(destination.relative);
			copyStreaming(sourcePath, target);
		}
		if (!sourceIsDirectory) deleteFile(path);
	}

	/** Logical absolute path: staging never changes importer path identity. */
	public function absolutePath(path:String):String {
		var routed = route(path);
		if (routed.relative == null) return RawFileSystem.absolutePath(routed.external);
		if (routed.stageAbsolute) return stagePath(routed.relative);
		return installPath(routed.relative);
	}

	public function fullPath(path:String):String {
		var routed = route(path);
		if (routed.relative == null) return RawFileSystem.fullPath(routed.external);
		if (routed.stageAbsolute) return stagePath(routed.relative);
		return installPath(routed.relative);
	}

	function route(path:String):ImportIOPath {
		if (path == null || path == "") throw "ImportIO path cannot be empty.";
		var value = slash(path);
		if (Path.isAbsolute(path)) {
			var absolute = absoluteNormalized(path);
			var stageRelative = relativeWithin(absolute, stageRoot);
			if (stageRelative != null)
				return {relative: stageRelative, external: absolute, stageAbsolute: true};
			var installRelative = relativeWithin(absolute, installRoot);
			if (installRelative != null && isInstallOutput(installRelative))
				return {relative: installRelative, external: absolute, stageAbsolute: false};
			return {relative: null, external: path, stageAbsolute: false};
		}
		if (hasDotDot(value)) throw "Traversal is forbidden in importer paths: " + path;
		var normalized = Path.normalize(value);
		normalized = slash(normalized);
		if (isInstallOutput(normalized))
			return {relative: trimLeading(normalized), external: installPath(trimLeading(normalized)), stageAbsolute: false};
		return {relative: null, external: path, stageAbsolute: false};
	}

	function markTouched(relative:String):Void {
		if (isTrackedOutput(relative) && !touched.exists(relative)) {
			// The refresh transaction verifies owned files against the committed
			// manifest itself. Its caller can avoid a redundant prewrite media hash;
			// shared registry merge baselines and unowned paths still require one.
			if (!deferOwnedBaselines || !masks.exists(relative) || isRegistry(relative)) before(relative);
			touched.set(relative, true);
		}
	}

	function isHidden(relative:String):Bool {
		return isRemoved(relative) || isMasked(relative);
	}

	function isRemoved(relative:String):Bool {
		var current = relative;
		while (current != "") {
			if (removed.exists(current)) return true;
			var parentPath = Path.directory(current);
			if (parentPath == null || parentPath == "." || parentPath == current) break;
			current = slash(parentPath);
		}
		return false;
	}

	function isMasked(relative:String):Bool {
		var current = relative;
		while (current != "") {
			if (masks.exists(current)) return true;
			var parentPath = Path.directory(current);
			if (parentPath == null || parentPath == "." || parentPath == current) break;
			current = slash(parentPath);
		}
		return false;
	}

	function clearDeletedAncestors(relative:String):Void {
		var current = relative;
		while (current != "") {
			removed.remove(current);
			var parentPath = Path.directory(current);
			if (parentPath == null || parentPath == "." || parentPath == current) break;
			current = slash(parentPath);
		}
	}

	function validateOutputRelative(relative:String, original:String):Void {
		if (relative == null || hasDotDot(slash(original)) || !isInstallOutput(relative))
			throw "Importer writes must stay under staged assets/ or tmp/: " + original;
	}

	function isTrackedOutput(relative:String):Bool {
		return StringTools.startsWith(relative, "assets/")
			&& relative != "assets/module/import/import-report.txt";
	}

	function outputRelative(path:String):Null<String> {
		if (path == null || path == "") return null;
		var routed:ImportIOPath;
		try routed = route(path) catch (_:Dynamic) return null;
		return routed.relative;
	}

	public static function isRegistry(path:String):Bool {
		return path == "assets/data/freeplaySongJson.jsonc"
			|| path == "assets/data/freeplaySongJson.json"
			|| path == "assets/images/freeplaySongJson.jsonc"
			|| path == "assets/images/freeplaySongJson.json"
			|| path == "assets/data/storySonglist.json"
			|| path == "assets/data/codenameMods.json"
			|| path == "assets/imported_mods/compatOverlays.json"
			|| path == "assets/imported_mods/globalResultsProvider.json"
			|| path == "assets/images/custom_chars/custom_chars.jsonc"
			|| path == "assets/images/custom_chars/icon_only_chars.json"
			|| path == "assets/images/custom_stages/custom_stages.json"
			|| path == "assets/images/custom_cutscenes/cutscenes.json"
			|| path == "assets/images/custom_difficulties/difficulties.json"
			|| path == "assets/images/custom_ui/ui_packs/ui.json";
	}

	function sourceEngineKey(sourceRoot:String, engine:String):String {
		var root = sourceRootKey(sourceRoot);
		if (root == "" || engine == null || StringTools.trim(engine) == "") return "";
		return root + "\n" + StringTools.trim(engine).toLowerCase();
	}

	function sourceRootKey(path:String):String {
		if (path == null || StringTools.trim(path) == "") return "";
		var value = Path.normalize(slash(path));
		if (!Path.isAbsolute(path)) value = RawFileSystem.absolutePath(value);
		if (RawFileSystem.exists(value)) try value = RawFileSystem.fullPath(value) catch (_:Dynamic) {}
		value = slash(value);
		while (StringTools.endsWith(value, "/") && value.length > 1
			&& !(value.length == 3 && value.charAt(1) == ":"))
			value = value.substr(0, value.length - 1);
		#if windows
		value = value.toLowerCase();
		#end
		return value;
	}

	function installPath(relative:String):String return Path.join([installRoot, relative]);
	function stagePath(relative:String):String return Path.join([stageRoot, relative]);

	static function ensureParent(path:String):Void {
		var parentPath = Path.directory(path);
		if (parentPath != null && parentPath != "" && parentPath != path && !RawFileSystem.exists(parentPath))
			RawFileSystem.createDirectory(parentPath);
	}

	function ensureSafeStagePath(path:String):Void {
		var absolute = absoluteNormalized(path);
		if (!sameOrWithin(absolute, stageRoot))
			throw "Import staging path escaped the stage root: " + path;
		var current = absolute;
		while (sameOrWithin(current, stageRoot)) {
			if (RawFileSystem.exists(current)) {
				var resolved = absoluteNormalized(RawFileSystem.fullPath(current));
				if (!samePath(resolved, current))
					throw "Import staging cannot follow symbolic links: " + current;
			}
			if (samePath(current, stageRoot)) break;
			var parentPath = Path.directory(current);
			if (parentPath == null || parentPath == current || !sameOrWithin(parentPath, stageRoot)) break;
			current = parentPath;
		}
	}

	static function copyStreaming(source:String, destination:String):Void {
		ensureParent(destination);
		var input:FileInput = null;
		var output:FileOutput = null;
		var buffer = Bytes.alloc(65536);
		try {
			input = RawFile.read(source, true);
			output = RawFile.write(destination, true);
			while (true) {
				var count:Int;
				try count = input.readBytes(buffer, 0, buffer.length) catch (_:haxe.io.Eof) break;
				if (count <= 0) break;
				output.writeBytes(buffer, 0, count);
			}
			input.close();
			input = null;
			output.close();
			output = null;
		} catch (error:Dynamic) {
			if (input != null) try input.close() catch (_:Dynamic) {}
			if (output != null) try output.close() catch (_:Dynamic) {}
			throw error;
		}
	}

	static function isInstallOutput(relative:String):Bool {
		return relative == "assets" || StringTools.startsWith(relative, "assets/")
			|| relative == "tmp" || StringTools.startsWith(relative, "tmp/");
	}

	static function joinRelative(parentPath:String, child:String):String {
		return parentPath == "" || parentPath == "." ? child : parentPath + "/" + child;
	}

	static function joinFs(path:String, child:String):String return Path.join([path, child]);

	static function hasDotDot(path:String):Bool {
		for (part in slash(path).split("/")) if (part == "..") return true;
		return false;
	}

	static function trimLeading(path:String):String {
		while (StringTools.startsWith(path, "/")) path = path.substr(1);
		return path;
	}

	static function slash(path:String):String {
		#if windows
		return StringTools.replace(path, "\\", "/");
		#else
		return path;
		#end
	}

	static function absoluteNormalized(path:String):String {
		return slash(Path.normalize(RawFileSystem.absolutePath(path)));
	}

	static function canonicalRoot(path:String):String {
		var absolute = absoluteNormalized(path);
		if (RawFileSystem.exists(absolute))
			return absoluteNormalized(RawFileSystem.fullPath(absolute));
		return absolute;
	}

	static function resolveThroughExistingAncestor(path:String):String {
		var absolute = absoluteNormalized(path);
		var cursor = absolute;
		var suffix:Array<String> = [];
		while (!RawFileSystem.exists(cursor)) {
			var parentPath = Path.directory(cursor);
			var name = Path.withoutDirectory(cursor);
			if (parentPath == null || parentPath == "" || parentPath == cursor || name == "")
				throw "Cannot resolve import stage root.";
			suffix.unshift(name);
			cursor = parentPath;
		}
		var resolved = absoluteNormalized(RawFileSystem.fullPath(cursor));
		for (part in suffix) resolved = Path.join([resolved, part]);
		return absoluteNormalized(resolved);
	}

	static function relativeWithin(path:String, root:String):Null<String> {
		var child = slash(path);
		var base = slash(root);
		#if windows
		child = child.toLowerCase();
		base = base.toLowerCase();
		#end
		if (child == base) return "";
		var prefix = StringTools.endsWith(base, "/") ? base : base + "/";
		if (!StringTools.startsWith(child, prefix)) return null;
		return path.substr(prefix.length);
	}

	static function sameOrWithin(path:String, root:String):Bool {
		var child = path;
		var base = root;
		#if windows
		child = child.toLowerCase();
		base = base.toLowerCase();
		#end
		return child == base || StringTools.startsWith(child, StringTools.endsWith(base, "/") ? base : base + "/");
	}

	static function samePath(left:String, right:String):Bool {
		#if windows
		return left.toLowerCase() == right.toLowerCase();
		#else
		return left == right;
		#end
	}
}
