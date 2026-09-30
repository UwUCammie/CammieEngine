package;

import haxe.Json;
import haxe.io.Bytes;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

using StringTools;

/** A diagnostic emitted while planning a donor Polymod-style overlay. */
typedef ImportOverlayDiagnostic = {
	var severity:String;
	var code:String;
	var path:String;
	var message:String;
	@:optional var mod:String;
	@:optional var operation:String;
}

/** One validated JSON Patch operation from a `_merge` file. */
typedef ImportOverlayPatch = {
	var op:String;
	var path:String;
	@:optional var value:Dynamic;
}

/** One file discovered below a supported overlay operation directory. */
typedef ImportOverlayEntry = {
	var mod:String;
	var operation:String;
	var kind:String;
	var relativePath:String;
	var sourcePath:String;
	var provenance:String;
	var sourceBytes:Bytes;
	@:optional var patches:Array<ImportOverlayPatch>;
}

/** The deterministic in-memory result of planning one donor root. */
typedef ImportOverlayPlan = {
	var root:String;
	var activeMods:Array<String>;
	var entries:Array<ImportOverlayEntry>;
	var diagnostics:Array<ImportOverlayDiagnostic>;
}

typedef ImportOverlayModList = {
	var activeMods:Array<String>;
	var diagnostics:Array<ImportOverlayDiagnostic>;
}

typedef ImportOverlayApplyResult = {
	var ok:Bool;
	var value:Dynamic;
	var diagnostics:Array<ImportOverlayDiagnostic>;
}

/** One detected engine root and the planner result retained for the import
	transaction.  Keeping this in memory lets scan/import reuse one plan without
	rescanning donor mod lists or persisting donor paths. */
typedef ImportOverlayMount = {
	var root:String;
	var contentRoot:String;
	var engine:String;
	var plan:ImportOverlayPlan;
}

/** A validated overlay which could not be materialized yet.  This is safe to
	serialize into the destination-only compatibility manifest: it contains no
	donor filesystem path. */
typedef ImportOverlayRetention = {
	var engine:String;
	var mod:String;
	var operation:String;
	var kind:String;
	/** Stable traversal ordinal assigned by the destination transaction. */
	@:optional var order:Int;
	var relativePath:String;
	var targetPath:String;
	var provenance:String;
	var reason:String;
	var payload:String;
}

typedef ImportOverlaySummary = {
	var planned:Int;
	var applied:Int;
	var retained:Int;
	var skipped:Int;
	var diagnostics:Array<String>;
	var provenance:Array<String>;
	var retainedPatches:Array<ImportOverlayRetention>;
}

typedef ImportOverlayDiscoveredFile = {
	var path:String;
	var relativePath:String;
}

/**
	Plans the small, evidence-backed subset of Polymod overlays found in the
	mounted donor corpus.

	This class is deliberately an in-memory boundary.  It never writes donor
	files and it never evaluates donor scripts.  `_append` and `_replace` carry
	exact source bytes for a later importer transaction; `_merge` carries a
	validated JSON Patch list and the original patch bytes.  Callers can retain
	`sourcePath`, `mod`, `operation`, `relativePath`, and `provenance` as import
	provenance without making a donor path part of runtime script discovery.
*/
class ImportOverlayPlanner {
	public static inline var MOD_LIST_FILE:String = 'mods/modList.txt';
	public static inline var APPEND:String = '_append';
	public static inline var REPLACE:String = '_replace';
	public static inline var MERGE:String = '_merge';
	public static inline var KIND_TEXT_APPEND:String = 'textAppend';
	public static inline var KIND_REPLACE:String = 'replace';
	public static inline var KIND_JSON_PATCH:String = 'jsonPatch';

	/**
		Plan active overlays below `root/mods`.  A missing modList is a valid
		no-op: roots without the optional legacy overlay layer remain ordinary
		asset roots.
	*/
	public static function plan(root:String):ImportOverlayPlan {
		var cleanRoot = canonicalPath(root);
		var result:ImportOverlayPlan = {
			root: cleanRoot,
			activeMods: [],
			entries: [],
			diagnostics: []
		};

		if (root == null || StringTools.trim(root) == '') {
			result.diagnostics.push(diagnostic('error', 'invalid-root', '', 'Overlay root is empty.'));
			return result;
		}

		var modListPath = Path.join([cleanRoot, MOD_LIST_FILE]);
		if (!FileSystem.exists(modListPath)) {
			// Root-level Polymod operation trees do not require a named-mod list.
			discoverRootOperations(cleanRoot, result);
			sortEntries(result);
			return result;
		}

		var raw:String;
		try {
			raw = File.getContent(modListPath);
		} catch (error:Dynamic) {
			result.diagnostics.push(diagnostic('error', 'mod-list-read-failed', modListPath,
				'Could not read the active mod list: ' + Std.string(error)));
			return result;
		}

		var parsed = parseModList(raw, modListPath);
		result.activeMods = parsed.activeMods.copy();
		for (finding in parsed.diagnostics)
			result.diagnostics.push(finding);

		// V-Slice/Polymod packages can put an operation tree at the package
		// root, as in DDTO++'s `_merge/data/players/pico.json`.  Keep that
		// overlay distinct from active named mods while applying the same safe
		// discovery and validation rules.
		discoverRootOperations(cleanRoot, result);

		var modsRoot = Path.join([cleanRoot, 'mods']);
		for (mod in result.activeMods) {
			var modPath = Path.join([modsRoot, mod]);
			if (!withinRoot(cleanRoot, modPath)) {
				result.diagnostics.push(diagnostic('error', 'unsafe-mod-path', modPath,
					'Active mod path escapes the donor root.', mod));
				continue;
			}
			if (!FileSystem.exists(modPath)) {
				result.diagnostics.push(diagnostic('error', 'missing-mod', modPath,
					'Active mod directory does not exist.', mod));
				continue;
			}
			if (!FileSystem.isDirectory(modPath)) {
				result.diagnostics.push(diagnostic('error', 'mod-not-directory', modPath,
					'Active mod entry is not a directory.', mod));
				continue;
			}
			discoverMod(cleanRoot, modPath, mod, result);
		}

		sortEntries(result);
		return result;
	}

	// Filesystem enumeration order is not portable.  Preserve modList order,
	// then use a stable operation/path order inside each active mod.  Root-level
	// operation trees use the same operation precedence with a synthetic empty
	// mod name, so a root without modList.txt remains deterministic too.
	static function sortEntries(result:ImportOverlayPlan):Void {
		result.entries.sort(function(a:ImportOverlayEntry, b:ImportOverlayEntry):Int {
			var modOrder = result.activeMods.indexOf(a.mod) - result.activeMods.indexOf(b.mod);
			if (modOrder != 0)
				return modOrder;
			var operationOrder = operationRank(a.operation) - operationRank(b.operation);
			if (operationOrder != 0)
				return operationOrder;
			return Reflect.compare(a.relativePath, b.relativePath);
		});
	}

	/** Parse a modList without touching the filesystem. */
	public static function parseModList(raw:String, ?sourcePath:String):ImportOverlayModList {
		var result:ImportOverlayModList = {activeMods: [], diagnostics: []};
		var path = sourcePath == null ? MOD_LIST_FILE : sourcePath;
		if (raw == null) {
			result.diagnostics.push(diagnostic('error', 'mod-list-null', path,
				'Active mod list was null.'));
			return result;
		}

		var seen:Map<String, Bool> = new Map<String, Bool>();
		var lines = raw.split('\n');
		for (index in 0...lines.length) {
			var line = StringTools.trim(StringTools.replace(lines[index], '\r', ''));
			if (line == '' || line.startsWith('#') || line.startsWith('//'))
				continue;
			if (!isSafeModName(line)) {
				result.diagnostics.push(diagnostic('error', 'unsafe-mod-name', path,
					'Active mod name is not a safe single directory name on line ' + (index + 1) + ': ' + line));
				continue;
			}
			if (seen.exists(line)) {
				result.diagnostics.push(diagnostic('warning', 'duplicate-mod', path,
					'Duplicate active mod name was ignored: ' + line, line));
				continue;
			}
			seen.set(line, true);
			result.activeMods.push(line);
		}
		return result;
	}

	/** Return the canonical safe spelling of a relative overlay target, or null. */
	public static function validateRelativePath(value:String):String {
		return safeRelativePath(value);
	}

	/** Validate a single active mod directory name without touching the filesystem. */
	public static function validateModName(value:String):Bool {
		return isSafeModName(value);
	}

	/** Concatenate validated text-append payloads without rewriting their bytes. */
	public static function applyTextAppend(base:Bytes, entries:Array<ImportOverlayEntry>):Bytes {
		var baseBytes = base == null ? Bytes.alloc(0) : base;
		var total = baseBytes.length;
		var accepted:Array<ImportOverlayEntry> = [];
		if (entries != null)
			for (entry in entries)
				if (entry != null && entry.kind == KIND_TEXT_APPEND && entry.sourceBytes != null) {
					accepted.push(entry);
					total += entry.sourceBytes.length;
				}

		var output = Bytes.alloc(total);
		var offset = 0;
		output.blit(offset, baseBytes, 0, baseBytes.length);
		offset += baseBytes.length;
		for (entry in accepted) {
			output.blit(offset, entry.sourceBytes, 0, entry.sourceBytes.length);
			offset += entry.sourceBytes.length;
		}
		return output;
	}

	/**
		Apply validated JSON Patch operations to a JSON document in memory.  The
		document is cloned first, so a failed operation never partially mutates
		the caller's value.
	*/
	public static function applyJsonPatch(document:Dynamic, patches:Array<ImportOverlayPatch>):ImportOverlayApplyResult {
		var result:ImportOverlayApplyResult = {ok: false, value: null, diagnostics: []};
		var working:Dynamic;
		try {
			working = Json.parse(Json.stringify(document));
		} catch (error:Dynamic) {
			result.diagnostics.push(diagnostic('error', 'document-not-json', '',
				'JSON Patch target could not be cloned: ' + Std.string(error)));
			return result;
		}
		if (patches == null) {
			result.diagnostics.push(diagnostic('error', 'patch-list-null', '', 'JSON Patch list was null.'));
			return result;
		}

		for (index in 0...patches.length) {
			var patch = patches[index];
			var pointer = decodePointer(patch == null ? null : patch.path);
			if (patch == null || pointer == null) {
				result.diagnostics.push(diagnostic('error', 'invalid-json-pointer',
					patch == null ? ('#' + index) : patch.path,
					'JSON Patch path is malformed at operation ' + index + '.'));
				return result;
			}

			var applied = applyOnePatch(working, patch, pointer, index);
			for (finding in applied.diagnostics)
				result.diagnostics.push(finding);
			if (!applied.ok)
				return result;
			working = applied.value;
		}
		result.ok = true;
		result.value = working;
		return result;
	}

	static function discoverMod(root:String, modPath:String, mod:String, result:ImportOverlayPlan):Void {
		var children = readDirectorySorted(modPath, result, mod, '');
		for (name in children) {
			var childPath = Path.join([modPath, name]);
			if (!FileSystem.isDirectory(childPath))
				continue;
			if (name == APPEND || name == REPLACE || name == MERGE) {
				discoverOperation(root, childPath, mod, name, result);
			} else if (name.startsWith('_')) {
				result.diagnostics.push(diagnostic('error', 'unsupported-overlay-operation', childPath,
					'Overlay operation directory is unsupported: ' + name, mod, name));
			}
		}
	}

	static function discoverRootOperations(root:String, result:ImportOverlayPlan):Void {
		var children = readDirectorySorted(root, result, '', '');
		for (name in children) {
			var childPath = Path.join([root, name]);
			if (!FileSystem.isDirectory(childPath))
				continue;
			if (name == APPEND || name == REPLACE || name == MERGE) {
				discoverOperation(root, childPath, '', name, result);
			} else if (name.startsWith('_')) {
				result.diagnostics.push(diagnostic('error', 'unsupported-overlay-operation', childPath,
					'Overlay operation directory is unsupported: ' + name, null, name));
			}
		}
	}

	static function discoverOperation(root:String, operationPath:String, mod:String,
		operation:String, result:ImportOverlayPlan):Void {
		var files:Array<ImportOverlayDiscoveredFile> = [];
		collectFiles(operationPath, '', files, result, mod, operation);
		for (file in files) {
			var relative = safeRelativePath(file.relativePath);
			if (relative == null) {
				result.diagnostics.push(diagnostic('error', 'unsafe-overlay-path', file.relativePath,
					'Overlay target path contains an absolute, empty, or traversal component.', mod, operation));
				continue;
			}
			var bytes:Bytes;
			try {
				bytes = File.getBytes(file.path);
			} catch (error:Dynamic) {
				result.diagnostics.push(diagnostic('error', 'overlay-read-failed', file.path,
					'Could not read overlay source bytes: ' + Std.string(error), mod, operation));
				continue;
			}

			if (operation == APPEND) {
				if (!isTextBytes(bytes)) {
					result.diagnostics.push(diagnostic('error', 'unsupported-append-type', file.path,
						'_append only supports text payloads.', mod, operation));
					continue;
				}
				result.entries.push(entry(mod, operation, KIND_TEXT_APPEND, relative, file.path, bytes));
			} else if (operation == REPLACE) {
				result.entries.push(entry(mod, operation, KIND_REPLACE, relative, file.path, bytes));
			} else {
				var patches = parsePatch(bytes.toString(), file.path, mod, operation, result);
				if (patches != null)
					result.entries.push({
						mod: mod,
						operation: operation,
						kind: KIND_JSON_PATCH,
						relativePath: relative,
						sourcePath: file.path,
						provenance: provenance(mod, operation, relative),
						sourceBytes: bytes,
						patches: patches
					});
			}
		}
	}

	static function collectFiles(current:String, prefix:String, output:Array<ImportOverlayDiscoveredFile>,
		result:ImportOverlayPlan, mod:String, operation:String):Void {
		var names = readDirectorySorted(current, result, mod, operation);
		for (name in names) {
			var childPath = Path.join([current, name]);
			var relative = prefix == '' ? name : prefix + '/' + name;
			if (safeRelativePath(relative) == null) {
				result.diagnostics.push(diagnostic('error', 'unsafe-overlay-path', relative,
					'Overlay source path contains an absolute, empty, or traversal component.', mod, operation));
				continue;
			}
			if (FileSystem.isDirectory(childPath))
				collectFiles(childPath, relative, output, result, mod, operation);
			else if (FileSystem.exists(childPath))
				output.push({path: childPath, relativePath: relative});
		}
	}

	static function readDirectorySorted(path:String, result:ImportOverlayPlan, mod:String,
		operation:String):Array<String> {
		try {
			var names = FileSystem.readDirectory(path);
			names.sort(Reflect.compare);
			return names;
		} catch (error:Dynamic) {
			result.diagnostics.push(diagnostic('error', 'overlay-directory-read-failed', path,
				'Could not enumerate overlay directory: ' + Std.string(error), mod == '' ? null : mod,
				operation == '' ? null : operation));
			return [];
		}
	}

	static function parsePatch(raw:String, path:String, mod:String, operation:String,
		result:ImportOverlayPlan):Array<ImportOverlayPatch> {
		var parsed:Dynamic;
		try {
			parsed = Json.parse(raw);
		} catch (error:Dynamic) {
			result.diagnostics.push(diagnostic('error', 'malformed-json-patch', path,
				'JSON Patch source is not valid JSON: ' + Std.string(error), mod, operation));
			return null;
		}
		if (!Std.isOfType(parsed, Array)) {
			result.diagnostics.push(diagnostic('error', 'json-patch-not-array', path,
				'JSON Patch source must be an array of operations.', mod, operation));
			return null;
		}

		var patches:Array<ImportOverlayPatch> = [];
		var rawPatches:Array<Dynamic> = cast parsed;
		for (index in 0...rawPatches.length) {
			var rawPatch:Dynamic = rawPatches[index];
			if (rawPatch == null || Std.isOfType(rawPatch, Array) || !hasField(rawPatch, 'op')) {
				result.diagnostics.push(diagnostic('error', 'json-patch-entry-type', path,
					'JSON Patch operation ' + index + ' must be an object.', mod, operation));
				return null;
			}
			var opValue:Dynamic = Reflect.field(rawPatch, 'op');
			if (!Std.isOfType(opValue, String)) {
				result.diagnostics.push(diagnostic('error', 'json-patch-op-type', path,
					'JSON Patch operation ' + index + ' has a non-string op.', mod, operation));
				return null;
			}
			var op:String = cast opValue;
			if (op != 'add' && op != 'replace' && op != 'remove') {
				result.diagnostics.push(diagnostic('error', 'unsupported-json-patch-op', path,
					'Unsupported JSON Patch operation at index ' + index + ': ' + op, mod, operation));
				return null;
			}
			if (!hasField(rawPatch, 'path') || !Std.isOfType(Reflect.field(rawPatch, 'path'), String)) {
				result.diagnostics.push(diagnostic('error', 'json-patch-path-type', path,
					'JSON Patch operation ' + index + ' has a non-string path.', mod, operation));
				return null;
			}
			var patchPath:String = cast Reflect.field(rawPatch, 'path');
			if (decodePointer(patchPath) == null) {
				result.diagnostics.push(diagnostic('error', 'invalid-json-pointer', path,
					'JSON Patch operation ' + index + ' has an invalid JSON Pointer.', mod, operation));
				return null;
			}
			if ((op == 'add' || op == 'replace') && !hasField(rawPatch, 'value')) {
				result.diagnostics.push(diagnostic('error', 'json-patch-value-missing', path,
					'JSON Patch ' + op + ' operation ' + index + ' has no value.', mod, operation));
				return null;
			}
			var patch:ImportOverlayPatch = {op: op, path: patchPath};
			if (hasField(rawPatch, 'value'))
				patch.value = Reflect.field(rawPatch, 'value');
			patches.push(patch);
		}
		return patches;
	}

	static function applyOnePatch(document:Dynamic, patch:ImportOverlayPatch, pointer:Array<String>,
		index:Int):ImportOverlayApplyResult {
		var result:ImportOverlayApplyResult = {ok: false, value: document, diagnostics: []};
		if (patch.op != 'add' && patch.op != 'replace' && patch.op != 'remove') {
			result.diagnostics.push(diagnostic('error', 'unsupported-json-patch-op', patch.path,
				'Unsupported JSON Patch operation at index ' + index + ': ' + patch.op));
			return result;
		}
		if (pointer.length == 0) {
			if (patch.op == 'remove')
				result.value = null;
			else
				result.value = patch.value;
			result.ok = true;
			return result;
		}

		var parent:Dynamic = document;
		for (segmentIndex in 0...(pointer.length - 1)) {
			var segment = pointer[segmentIndex];
			var child = readChild(parent, segment);
			if (!child.found) {
				result.diagnostics.push(diagnostic('error', 'json-patch-parent-missing', patch.path,
					'JSON Patch parent path is missing at operation ' + index + '.'));
				return result;
			}
			parent = child.value;
		}

		var leaf = pointer[pointer.length - 1];
		if (Std.isOfType(parent, Array)) {
			var array:Array<Dynamic> = cast parent;
			if (patch.op == 'add' && leaf == '-') {
				array.push(patch.value);
				result.ok = true;
				return result;
			}
			var allowEnd = patch.op == 'add';
			var arrayIndex = parseArrayIndex(leaf, array.length, allowEnd);
			if (arrayIndex < 0) {
				result.diagnostics.push(diagnostic('error', 'json-patch-array-index', patch.path,
					'JSON Patch array index is invalid at operation ' + index + '.'));
				return result;
			}
			if (patch.op == 'add') {
				if (arrayIndex == array.length)
					array.push(patch.value);
				else
					array.insert(arrayIndex, patch.value);
			} else if (patch.op == 'replace') {
				array[arrayIndex] = patch.value;
			} else {
				array.splice(arrayIndex, 1);
			}
			result.ok = true;
			return result;
		}

		if (parent == null || Std.isOfType(parent, String) || Std.isOfType(parent, Int)
			|| Std.isOfType(parent, Float) || Std.isOfType(parent, Bool)) {
			result.diagnostics.push(diagnostic('error', 'json-patch-parent-type', patch.path,
				'JSON Patch parent is not an object or array at operation ' + index + '.'));
			return result;
		}
		var exists = hasField(parent, leaf);
		if (patch.op == 'add') {
			Reflect.setField(parent, leaf, patch.value);
		} else if (patch.op == 'replace') {
			if (!exists) {
				result.diagnostics.push(diagnostic('error', 'json-patch-target-missing', patch.path,
					'JSON Patch replace target is missing at operation ' + index + '.'));
				return result;
			}
			Reflect.setField(parent, leaf, patch.value);
		} else {
			if (!exists) {
				result.diagnostics.push(diagnostic('error', 'json-patch-target-missing', patch.path,
					'JSON Patch remove target is missing at operation ' + index + '.'));
				return result;
			}
			Reflect.deleteField(parent, leaf);
		}
		result.ok = true;
		return result;
	}

	static function readChild(parent:Dynamic, segment:String):{found:Bool, value:Dynamic} {
		if (Std.isOfType(parent, Array)) {
			var array:Array<Dynamic> = cast parent;
			var index = parseArrayIndex(segment, array.length, false);
			return index < 0 ? {found:false, value:null} : {found:true, value:array[index]};
		}
		if (parent == null || Std.isOfType(parent, String) || Std.isOfType(parent, Int)
			|| Std.isOfType(parent, Float) || Std.isOfType(parent, Bool)
			|| !hasField(parent, segment))
			return {found:false, value:null};
		return {found:true, value:Reflect.field(parent, segment)};
	}

	static function parseArrayIndex(value:String, length:Int, allowEnd:Bool):Int {
		if (value == null || value == '' || (value.length > 1 && value.charAt(0) == '0'))
			return -1;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			if (code < 48 || code > 57)
				return -1;
		}
		var parsed:Null<Int> = Std.parseInt(value);
		if (parsed == null || parsed < 0 || parsed > length || (!allowEnd && parsed >= length))
			return -1;
		return parsed;
	}

	static function decodePointer(path:String):Array<String> {
		if (path == null || (path != '' && !path.startsWith('/')))
			return null;
		if (path == '')
			return [];
		var result:Array<String> = [];
		var tokens = path.substr(1).split('/');
		for (token in tokens) {
			var decoded = new StringBuf();
			var index = 0;
			while (index < token.length) {
				var character = token.charAt(index);
				if (character == '~') {
					if (index + 1 >= token.length)
						return null;
					var escaped = token.charAt(index + 1);
					if (escaped != '0' && escaped != '1')
						return null;
					decoded.add(escaped == '0' ? '~' : '/');
					index += 2;
				} else {
					decoded.add(character);
					index++;
				}
			}
			result.push(decoded.toString());
		}
		for (index in 0...result.length)
			if (result[index] == '-' && index != result.length - 1)
				return null;
		return result;
	}

	static function isSafeModName(value:String):Bool {
		if (value == null || value == '' || value == '.' || value == '..')
			return false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			var alpha = (code >= 65 && code <= 90) || (code >= 97 && code <= 122);
			var digit = code >= 48 && code <= 57;
			if (!alpha && !digit && code != 45 && code != 46 && code != 95)
				return false;
		}
		return true;
	}

	static function safeRelativePath(value:String):String {
		if (value == null)
			return null;
		var clean = StringTools.replace(value, '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0)
			return null;
		var parts = clean.split('/');
		for (part in parts)
			if (part == '' || part == '.' || part == '..')
				return null;
		return parts.join('/');
	}

	static function isTextBytes(bytes:Bytes):Bool {
		if (bytes == null)
			return false;
		for (index in 0...bytes.length)
			if (bytes.get(index) == 0)
				return false;
		return true;
	}

	static function hasField(value:Dynamic, field:String):Bool {
		if (value == null)
			return false;
		try {
			return Reflect.hasField(value, field);
		} catch (_:Dynamic) {
			return false;
		}
	}

	static function entry(mod:String, operation:String, kind:String, relative:String,
		sourcePath:String, sourceBytes:Bytes):ImportOverlayEntry {
		return {
			mod: mod,
			operation: operation,
			kind: kind,
			relativePath: relative,
			sourcePath: sourcePath,
			provenance: provenance(mod, operation, relative),
			sourceBytes: sourceBytes
		};
	}

	static function provenance(mod:String, operation:String, relative:String):String {
		return (mod == null || mod == '' ? operation : mod + '/' + operation) + '/' + relative;
	}

	static function operationRank(operation:String):Int {
		return operation == APPEND ? 0 : operation == REPLACE ? 1 : operation == MERGE ? 2 : 3;
	}

	static function diagnostic(severity:String, code:String, path:String, message:String,
		?mod:String, ?operation:String):ImportOverlayDiagnostic {
		var result:ImportOverlayDiagnostic = {severity:severity, code:code, path:path, message:message};
		if (mod != null)
			result.mod = mod;
		if (operation != null)
			result.operation = operation;
		return result;
	}

	static function canonicalPath(value:String):String {
		return ImportOverlayPath.canonicalPath(value);
	}

	static function withinRoot(root:String, child:String):Bool {
		return ImportOverlayPath.withinRoot(root, child);
	}
}
