package;

import haxe.Json;
import haxe.crypto.Base64;
import haxe.crypto.Md5;
import haxe.io.Bytes;
import haxe.io.Path;
import ImportFileSystem as FileSystem;
import ImportFile as File;
import ImportOverlayPlanner.ImportOverlayEntry;
import ImportOverlayPlanner.ImportOverlayMount;
import ImportOverlayPlanner.ImportOverlayPlan;
import ImportOverlayPlanner.ImportOverlaySummary;
import ImportOverlayPlanner.ImportOverlayRetention;

using StringTools;

/** One destination write staged before the overlay transaction commits. */
typedef ImportOverlayPendingWrite = {
	var path:String;
	var relativePath:String;
	var bytes:Bytes;
	var entries:Array<ImportOverlayPendingEntry>;
}

typedef ImportOverlayPendingEntry = {
	var mount:ImportOverlayMount;
	var entry:ImportOverlayEntry;
	var order:Int;
}

/**
	Destination-side transaction for the bounded overlay planner.

	The planner is intentionally read-only.  This companion stages only safe
	`data/...` targets below the native `assets` tree, commits new files through
	sibling temporary files, and removes every file created by a failed commit.
	Existing destination files are protected rather than overwritten; a valid
	overlay which cannot safely apply is retained as destination-only provenance
	for ImportOverlayResolver's read-only virtual asset layer.
*/
class ImportOverlayRuntime {
	public static inline var DESTINATION_ROOT:String = 'assets';

	/** Build one reusable mount plan for a detected engine root. */
	public static function mount(root:String, contentRoot:String, engine:String,
		?plan:ImportOverlayPlan):ImportOverlayMount {
		var cleanRoot = canonicalPath(root);
		var cleanContent = canonicalPath(contentRoot == null || StringTools.trim(contentRoot) == ''
			? root : contentRoot);
		return {
			root: cleanRoot,
			contentRoot: cleanContent,
			engine: engine == null ? '' : engine,
			plan: plan == null ? ImportOverlayPlanner.plan(cleanRoot) : plan
		};
	}

	/** Deterministically sort roots before either reporting or applying them. */
	public static function sortMounts(mounts:Array<ImportOverlayMount>):Array<ImportOverlayMount> {
		var result = mounts == null ? [] : mounts.copy();
		result.sort(function(a:ImportOverlayMount, b:ImportOverlayMount):Int {
			var left = a == null || a.root == null ? '' : a.root;
			var right = b == null || b.root == null ? '' : b.root;
			var compared = Reflect.compare(left, right);
			if (compared != 0)
				return compared;
			left = a == null || a.contentRoot == null ? '' : a.contentRoot;
			right = b == null || b.contentRoot == null ? '' : b.contentRoot;
			compared = Reflect.compare(left, right);
			if (compared != 0)
				return compared;
			return Reflect.compare(a == null || a.engine == null ? '' : a.engine,
				b == null || b.engine == null ? '' : b.engine);
		});
		return result;
	}

	/** Summarize plans without writing any destination files. */
	public static function summarize(mounts:Array<ImportOverlayMount>):ImportOverlaySummary {
		var result = emptySummary();
		for (mount in sortMounts(mounts)) {
			if (mount == null || mount.plan == null)
				continue;
			appendPlanSummary(result, mount.plan);
		}
		return result;
	}

	/** Apply all mounts as one deterministic, rollback-safe destination transaction. */
	public static function apply(mounts:Array<ImportOverlayMount>,
		?destinationRoot:String):ImportOverlaySummary {
		var result = emptySummary();
		var destination = canonicalPath(destinationRoot == null || StringTools.trim(destinationRoot) == ''
			? DESTINATION_ROOT : destinationRoot);
		if (!safeDestinationRoot(destination)) {
			result.diagnostics.push('[overlay-invalid-destination] Refused overlay destination: ' + destination);
			return result;
		}

		var pendingByPath:Map<String, ImportOverlayPendingWrite> = new Map<String, ImportOverlayPendingWrite>();
		var traversalOrder = 0;
		for (mount in sortMounts(mounts)) {
			if (mount == null || mount.plan == null)
				continue;
			appendPlanSummary(result, mount.plan);
			for (entry in mount.plan.entries) {
				var entryOrder = traversalOrder++;
				if (entry == null)
					continue;
				var relative = ImportOverlayPlanner.validateRelativePath(entry.relativePath);
				if (!safeOverlayTarget(relative)) {
					result.skipped++;
					result.diagnostics.push('[overlay-unsupported-target] ' + provenance(entry)
						+ ': only safe data/... targets are materialized.');
					continue;
				}
				var target = Path.join([destination, relative]);
				if (!withinRoot(destination, target)) {
					result.skipped++;
					result.diagnostics.push('[overlay-target-escape] ' + provenance(entry)
						+ ': destination path escaped assets/.');
					continue;
				}
				var key = pathKey(target);
				var pending = pendingByPath.get(key);
				if (pending == null) {
					pending = {
						path: target,
						relativePath: relative,
						bytes: null,
						entries: []
					};
					pendingByPath.set(key, pending);
				}
				pending.entries.push({mount:mount, entry:entry, order:entryOrder});
				var accepted = stageEntry(result, pending, mount, entry, relative, target, entryOrder);
				if (!accepted)
					pending.entries.pop();
				if (pending.entries.length == 0)
					pendingByPath.remove(key);
			}
		}

		var pendingWrites:Array<ImportOverlayPendingWrite> = [];
		for (key in pendingByPath.keys()) {
			var pending = pendingByPath.get(key);
			if (pending != null && pending.bytes != null)
				pendingWrites.push(pending);
		}
		pendingWrites.sort(function(a:ImportOverlayPendingWrite, b:ImportOverlayPendingWrite):Int {
			return Reflect.compare(a.path, b.path);
		});
		commit(pendingWrites, result);
		return result;
	}

	static function emptySummary():ImportOverlaySummary {
		return {
			planned: 0,
			applied: 0,
			retained: 0,
			skipped: 0,
			diagnostics: [],
			provenance: [],
			retainedPatches: []
		};
	}

	static function appendPlanSummary(result:ImportOverlaySummary, plan:ImportOverlayPlan):Void {
		if (plan == null)
			return;
		if (plan.diagnostics != null)
			for (finding in plan.diagnostics)
				if (finding != null) {
					var prefix = finding.code == null || finding.code == '' ? 'overlay-diagnostic' : finding.code;
					var path = finding.path == null || finding.path == '' ? '' : ' [' + finding.path + ']';
					result.diagnostics.push('[' + prefix + ']' + path + ' ' + finding.message);
				}
		if (plan.entries == null)
			return;
		result.planned += plan.entries.length;
		for (entry in plan.entries)
			if (entry != null && entry.provenance != null && result.provenance.indexOf(entry.provenance) < 0)
				result.provenance.push(entry.provenance);
	}

	static function stageEntry(result:ImportOverlaySummary, pending:ImportOverlayPendingWrite,
		mount:ImportOverlayMount, entry:ImportOverlayEntry, relative:String, target:String,
		order:Int):Bool {
		var base:{found:Bool, bytes:Bytes, protectedTarget:Bool, reason:String};
		if (pending.bytes != null) {
			base = {found:true, bytes:pending.bytes, protectedTarget:false, reason:''};
		} else if (FileSystem.exists(target)) {
			base = {
				found:false,
				bytes:null,
				protectedTarget:true,
				reason:FileSystem.isDirectory(target) ? 'destination-is-directory' : 'destination-exists'
			};
		} else {
			base = readDonorBase(mount, entry, relative);
		}

		switch (entry.operation) {
			case ImportOverlayPlanner.REPLACE:
				if (entry.sourceBytes == null) {
					retain(result, mount, entry, relative, 'replace-source-missing', order);
					return false;
				}
				if (base.protectedTarget) {
					retain(result, mount, entry, relative, base.reason, order);
					return false;
				}
				pending.bytes = entry.sourceBytes;
				return true;
			case ImportOverlayPlanner.APPEND:
				if (entry.sourceBytes == null || !base.found) {
					retain(result, mount, entry, relative,
						base.protectedTarget ? base.reason : 'missing-append-base', order);
					return false;
				}
				pending.bytes = append(base.bytes, entry.sourceBytes);
				return true;
			case ImportOverlayPlanner.MERGE:
				if (!base.found) {
					retain(result, mount, entry, relative,
						base.protectedTarget ? base.reason : 'missing-merge-base', order);
					return false;
				}
				if (entry.patches == null) {
					retain(result, mount, entry, relative, 'merge-patches-missing', order);
					return false;
				}
				var parsed:Dynamic;
				try {
					parsed = Json.parse(base.bytes.toString());
				} catch (error:Dynamic) {
					retain(result, mount, entry, relative, 'merge-base-malformed-json', order);
					result.diagnostics.push('[overlay-merge-base-invalid] ' + provenance(entry)
						+ ': ' + Std.string(error));
					return false;
				}
				var applied = ImportOverlayPlanner.applyJsonPatch(parsed, cast entry.patches);
				if (!applied.ok) {
					retain(result, mount, entry, relative, 'merge-apply-failed', order);
					for (finding in applied.diagnostics)
						if (finding != null)
							result.diagnostics.push('[overlay-merge-apply] ' + provenance(entry) + ': ' + finding.message);
					return false;
				}
				pending.bytes = Bytes.ofString(Json.stringify(applied.value));
				return true;
			default:
				retain(result, mount, entry, relative, 'unsupported-operation', order);
				return false;
		}
	}

	static function readDonorBase(mount:ImportOverlayMount, entry:ImportOverlayEntry,
		relative:String):{found:Bool, bytes:Bytes, protectedTarget:Bool, reason:String} {
		if (mount == null)
			return {found:false, bytes:null, protectedTarget:false, reason:'missing-overlay-mount'};
		var baseRoot = entry.mod == null || entry.mod == '' ? mount.root : mount.contentRoot;
		if (baseRoot == null || StringTools.trim(baseRoot) == '')
			return {found:false, bytes:null, protectedTarget:false, reason:'missing-overlay-root'};
		var candidate = Path.join([baseRoot, relative]);
		if (!withinRoot(baseRoot, candidate) || !FileSystem.exists(candidate) || FileSystem.isDirectory(candidate))
			return {found:false, bytes:null, protectedTarget:false, reason:'missing-overlay-base'};
		try {
			return {found:true, bytes:File.getBytes(candidate), protectedTarget:false, reason:''};
		} catch (_:Dynamic) {
			return {found:false, bytes:null, protectedTarget:false, reason:'overlay-base-read-failed'};
		}
	}

	static function retain(result:ImportOverlaySummary, mount:ImportOverlayMount,
		entry:ImportOverlayEntry, relative:String, reason:String, order:Int):Void {
		result.retained++;
		result.diagnostics.push('[overlay-retained] ' + provenance(entry) + ': ' + reason);
		var payload = '';
		if (entry.sourceBytes != null) {
			// Replacement payloads may be arbitrary binary data.  Keep text append
			// and JSON Patch records human-readable for existing manifests, but use
			// an explicit marker for binary-safe replacement retention.
			payload = entry.kind == ImportOverlayPlanner.KIND_REPLACE
				? 'base64:' + Base64.encode(entry.sourceBytes)
				: entry.sourceBytes.toString();
		}
		result.retainedPatches.push({
			engine: mount == null || mount.engine == null ? '' : mount.engine,
			mod: entry.mod == null ? '' : entry.mod,
			operation: entry.operation,
			kind: entry.kind,
			order: order,
			relativePath: relative,
			targetPath: relative,
			provenance: provenance(entry),
			reason: reason,
			payload: payload
		});
	}

	static function commit(writes:Array<ImportOverlayPendingWrite>, result:ImportOverlaySummary):Void {
		if (writes == null || writes.length == 0)
			return;
		var committed:Array<ImportOverlayPendingWrite> = [];
		var temporary:Array<String> = [];
		try {
			for (pending in writes) {
				if (pending == null || pending.bytes == null)
					continue;
				if (FileSystem.exists(pending.path))
					throw 'destination appeared before overlay commit: ' + pending.path;
				ensureDirectory(Path.directory(pending.path));
				var temporaryPath = pending.path + '.overlay-' + Md5.encode(pending.path).substr(0, 12) + '.tmp';
				if (FileSystem.exists(temporaryPath))
					throw 'overlay temporary path already exists: ' + temporaryPath;
				temporary.push(temporaryPath);
				File.saveBytes(temporaryPath, pending.bytes);
				FileSystem.rename(temporaryPath, pending.path);
				committed.push(pending);
			}
			for (pending in committed) {
				for (item in pending.entries) {
					result.applied++;
					if (item != null && item.entry != null && item.entry.provenance != null
						&& result.provenance.indexOf(item.entry.provenance) < 0)
						result.provenance.push(item.entry.provenance);
				}
			}
		} catch (error:Dynamic) {
			for (temporaryPath in temporary)
				if (FileSystem.exists(temporaryPath))
					try FileSystem.deleteFile(temporaryPath) catch (_:Dynamic) {}
			for (pending in committed)
				if (pending != null && FileSystem.exists(pending.path))
					try FileSystem.deleteFile(pending.path) catch (_:Dynamic) {}
			result.diagnostics.push('[overlay-transaction-rollback] ' + Std.string(error));
			var rolledBackEntries = 0;
			for (pending in writes)
				if (pending != null && pending.entries != null)
					rolledBackEntries += pending.entries.length;
			result.retained += rolledBackEntries;
			for (pending in writes)
				if (pending != null)
					for (item in pending.entries)
						if (item != null && item.entry != null)
							result.retainedPatches.push({
								engine: item.mount == null || item.mount.engine == null ? '' : item.mount.engine,
								mod: item.entry.mod == null ? '' : item.entry.mod,
								operation: item.entry.operation,
								kind: item.entry.kind,
								order: item.order,
								relativePath: pending.relativePath,
								targetPath: pending.relativePath,
								provenance: provenance(item.entry),
								reason: 'overlay-transaction-rollback',
								payload: item.entry.sourceBytes == null ? ''
									: item.entry.kind == ImportOverlayPlanner.KIND_REPLACE
										? 'base64:' + Base64.encode(item.entry.sourceBytes)
										: item.entry.sourceBytes.toString()
							});
		}
	}

	static function append(first:Bytes, second:Bytes):Bytes {
		var left = first == null ? Bytes.alloc(0) : first;
		var right = second == null ? Bytes.alloc(0) : second;
		var result = Bytes.alloc(left.length + right.length);
		result.blit(0, left, 0, left.length);
		result.blit(left.length, right, 0, right.length);
		return result;
	}

	static function provenance(entry:ImportOverlayEntry):String {
		return entry == null || entry.provenance == null ? 'overlay' : entry.provenance;
	}

	static function safeOverlayTarget(relative:String):Bool {
		return relative != null && (relative == 'data' || relative.startsWith('data/'));
	}

	static function safeDestinationRoot(path:String):Bool {
		var clean = canonicalPath(path);
		var assets = canonicalPath(DESTINATION_ROOT);
		return clean == assets || withinRoot(assets, clean);
	}

	static function pathKey(path:String):String {
		var clean = canonicalPath(path);
		#if windows
		return clean.toLowerCase();
		#else
		return clean;
		#end
	}

	static function ensureDirectory(path:String):Void {
		if (path == null || StringTools.trim(path) == '' || FileSystem.exists(path))
			return;
		var parent = Path.directory(path);
		if (parent != null && parent != '' && parent != path)
			ensureDirectory(parent);
		FileSystem.createDirectory(path);
	}

	static function canonicalPath(value:String):String {
		return ImportOverlayPath.canonicalPath(value);
	}

	static function withinRoot(root:String, child:String):Bool {
		return ImportOverlayPath.withinRoot(root, child);
	}
}
