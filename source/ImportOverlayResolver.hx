package;

import haxe.Json;
import haxe.crypto.Base64;
import haxe.io.Bytes;
import haxe.io.Path;
import CompatScriptManifest.CompatOverlayRecord;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/**
	Read-only virtual view of retained Polymod overlay operations.

	The importer deliberately leaves an existing destination file alone.  When
	that happens, ImportOverlayRuntime writes a destination-only record to
	compatOverlays.json.  This resolver applies those records to bytes after the
	native file/asset has been read, so `_append`, `_replace`, and `_merge` still
	behave like the donor without overwriting a user's file.

	Only safe `assets/data/...` targets are accepted.  The manifest is never
	loaded through FNFAssets, which avoids recursion when the resolver itself is
	asked to read an asset.  Non-native targets compile to no-op helpers.
*/
class ImportOverlayResolver {
	#if sys
	static var cachedManifestPath:String = '';
	static var cachedManifestStamp:String = '';
	static var cachedRecords:Array<CompatOverlayRecord> = null;
	static var diagnosticBuffer:Array<String> = [];
	#end

	/** Drop the cached manifest after an import writes a new retention record. */
	public static function invalidate():Void {
		#if sys
		cachedManifestPath = '';
		cachedManifestStamp = '';
		cachedRecords = null;
		diagnosticBuffer = [];
		#end
	}

	/** Return diagnostics from the last native manifest/payload read. */
	public static function getDiagnostics():Array<String> {
		#if sys
		return diagnosticBuffer == null ? [] : diagnosticBuffer.copy();
		#else
		return [];
		#end
	}

	/** Apply retained operations to an already-read byte buffer. */
	public static function applyBytes(id:String, base:Bytes):Bytes {
		#if sys
		if (base == null)
			return base;
		var relative = targetRelative(id);
		if (relative == '')
			return base;
		var records = recordsFor(relative);
		if (records.length == 0)
			return base;
		var result = base;
		for (record in records) {
			if (record == null || !sameTarget(record, relative))
				continue;
			// CompatScriptManifest.normalize removes duplicate persisted records at
			// manifest identity.  Do not dedupe by payload here: two different mods
			// may intentionally append the same bytes, and Polymod applies both.
			result = applyRecord(result, record);
		}
		return result;
		#else
		return base;
		#end
	}

	/** Apply retained operations to text while preserving the native fallback. */
	public static function applyText(id:String, base:String):String {
		#if sys
		if (base == null)
			return base;
		try {
			return applyBytes(id, Bytes.ofString(base)).toString();
		} catch (error:Dynamic) {
			recordDiagnostic('text-overlay-read-failed [' + id + ']: ' + Std.string(error));
			return base;
		}
		#else
		return base;
		#end
	}

	#if sys
	static function recordsFor(relative:String):Array<CompatOverlayRecord> {
		var records = loadRecords();
		var result:Array<CompatOverlayRecord> = [];
		for (record in records)
			if (record != null && sameTarget(record, relative))
				result.push(record);
		return result;
	}

	static function loadRecords():Array<CompatOverlayRecord> {
		var path = Path.normalize(CompatScriptManifest.overlayManifestPath());
		var stamp = manifestStamp(path);
		if (cachedRecords != null && cachedManifestPath == path && cachedManifestStamp == stamp)
			return cachedRecords;

		cachedManifestPath = path;
		cachedManifestStamp = stamp;
		cachedRecords = [];
		diagnosticBuffer = [];
		if (stamp == '')
			return cachedRecords;

		try {
			var raw = File.getContent(path);
			var parsed:Dynamic = Json.parse(raw);
			var normalized = CompatScriptManifest.normalize(parsed);
			if (normalized.overlays != null)
				cachedRecords = normalized.overlays.copy();
		} catch (error:Dynamic) {
			recordDiagnostic('overlay-manifest-invalid [' + path + ']: ' + Std.string(error));
			cachedRecords = [];
		}
		cachedRecords.sort(compareRecords);
		return cachedRecords;
	}

	static function manifestStamp(path:String):String {
		if (path == null || StringTools.trim(path) == '' || !FileSystem.exists(path)
			|| FileSystem.isDirectory(path))
			return '';
		try {
			var stat = FileSystem.stat(path);
			return Std.string(stat.size) + ':' + Std.string(stat.mtime.getTime());
		} catch (error:Dynamic) {
			recordDiagnostic('overlay-manifest-stat-failed [' + path + ']: ' + Std.string(error));
			return '';
		}
	}

	static function sameTarget(record:CompatOverlayRecord, relative:String):Bool {
		if (record == null || relative == null)
			return false;
		var target = safeRelative(record.targetPath);
		if (target == '')
			target = safeRelative(record.relativePath);
		return target != '' && targetKey(target) == targetKey(relative);
	}

	static function applyRecord(base:Bytes, record:CompatOverlayRecord):Bytes {
		var operation = record.operation == null ? '' : record.operation;
		var payload = decodePayload(record.payload, operation, record.provenance);
		if (payload == null)
			return base;
		switch (operation) {
			case '_append':
				return append(base, payload);
			case '_replace':
				return payload;
			case '_merge':
				return applyMerge(base, payload, record);
			default:
				recordDiagnostic('overlay-operation-unsupported [' + record.provenance + ']: ' + operation);
				return base;
		}
	}

	static function applyMerge(base:Bytes, payload:Bytes, record:CompatOverlayRecord):Bytes {
		try {
			var document:Dynamic = Json.parse(base.toString());
			var rawPatches:Dynamic = Json.parse(payload.toString());
			if (!Std.isOfType(rawPatches, Array)) {
				recordDiagnostic('overlay-merge-payload-not-array [' + record.provenance + ']');
				return base;
			}
			var result = ImportOverlayPlanner.applyJsonPatch(document, cast rawPatches);
			if (!result.ok) {
				for (finding in result.diagnostics)
					if (finding != null)
						recordDiagnostic('overlay-merge-apply [' + record.provenance + ']: ' + finding.message);
				return base;
			}
			return Bytes.ofString(Json.stringify(result.value));
		} catch (error:Dynamic) {
			recordDiagnostic('overlay-merge-invalid [' + record.provenance + ']: ' + Std.string(error));
			return base;
		}
	}

	static function decodePayload(raw:String, operation:String, provenance:String):Bytes {
		if (raw == null) {
			recordDiagnostic('overlay-payload-missing [' + provenance + ']');
			return null;
		}
		// Replacements are binary-safe by construction.  Refuse old empty/raw
		// replacement records rather than turning a missing payload into a blank
		// asset.  Append and merge records retain their historical UTF-8 payload
		// form, but accept the same marker for future binary-safe manifests.
		if (raw.startsWith('base64:'))
			return decodeBase64(raw.substr('base64:'.length), provenance);
		if (operation == '_replace') {
			recordDiagnostic('overlay-replace-payload-unencoded [' + provenance + ']');
			return null;
		}
		return Bytes.ofString(raw);
	}

	static function decodeBase64(value:String, provenance:String):Bytes {
		if (value == null || value.length % 4 != 0) {
			recordDiagnostic('overlay-payload-base64-invalid [' + provenance + ']');
			return null;
		}
		var padding = false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			var valid = (code >= 65 && code <= 90) || (code >= 97 && code <= 122)
				|| (code >= 48 && code <= 57) || code == 43 || code == 47;
			if (code == 61) {
				padding = true;
				if (index < value.length - 2)
					return invalidBase64(provenance);
			} else if (!valid || padding) {
				return invalidBase64(provenance);
			}
		}
		try {
			return Base64.decode(value);
		} catch (error:Dynamic) {
			return invalidBase64(provenance + ': ' + Std.string(error));
		}
	}

	static function invalidBase64(provenance:String):Bytes {
		recordDiagnostic('overlay-payload-base64-invalid [' + provenance + ']');
		return null;
	}

	static function append(first:Bytes, second:Bytes):Bytes {
		var left = first == null ? Bytes.alloc(0) : first;
		var right = second == null ? Bytes.alloc(0) : second;
		var result = Bytes.alloc(left.length + right.length);
		result.blit(0, left, 0, left.length);
		result.blit(left.length, right, 0, right.length);
		return result;
	}

	static function compareRecords(left:CompatOverlayRecord, right:CompatOverlayRecord):Int {
		var leftOrder = left == null || left.order == null ? -1 : left.order;
		var rightOrder = right == null || right.order == null ? -1 : right.order;
		// New manifests carry the transaction's planner traversal ordinal.  It is
		// the semantic order for non-commutative overlays; provenance sorting is
		// only the compatibility fallback for old manifests that predate it.
		if (leftOrder >= 0 && rightOrder >= 0) {
			var ordered = leftOrder - rightOrder;
			if (ordered != 0)
				return ordered;
		} else if (leftOrder != rightOrder) {
			return leftOrder >= 0 ? -1 : 1;
		}
		var compared = Reflect.compare(safeRelative(left == null ? '' : left.targetPath),
			safeRelative(right == null ? '' : right.targetPath));
		if (compared != 0)
			return compared;
		compared = operationRank(left == null ? '' : left.operation)
			- operationRank(right == null ? '' : right.operation);
		if (compared != 0)
			return compared;
		compared = Reflect.compare(left == null ? '' : left.provenance,
			right == null ? '' : right.provenance);
		if (compared != 0)
			return compared;
		return Reflect.compare(left == null ? '' : left.payload, right == null ? '' : right.payload);
	}

	static function operationRank(operation:String):Int {
		return operation == '_replace' ? 0 : operation == '_append' ? 1 : operation == '_merge' ? 2 : 3;
	}

	static function safeRelative(value:String):String {
		if (value == null)
			return '';
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0)
			return '';
		var parts = clean.split('/');
		for (part in parts)
			if (part == '' || part == '.' || part == '..')
				return '';
		var normalized = parts.join('/');
		return normalized == 'data' || normalized.startsWith('data/') ? normalized : '';
	}

	static function targetKey(value:String):String {
		#if windows
		return value == null ? '' : value.toLowerCase();
		#else
		return value == null ? '' : value;
		#end
	}

	static function targetRelative(id:String):String {
		if (id == null)
			return '';
		var clean = StringTools.replace(StringTools.trim(id), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean == 'assets')
			return '';
		if (clean.startsWith('assets/'))
			return safeRelative(clean.substr('assets/'.length));
		var assetsRoot = ImportOverlayPath.canonicalPath('assets');
		var absolute = ImportOverlayPath.canonicalPath(clean);
		if (assetsRoot == '' || absolute == '')
			return '';
		var prefix = assetsRoot.endsWith('/') ? assetsRoot : assetsRoot + '/';
		return absolute.startsWith(prefix) ? safeRelative(absolute.substr(prefix.length)) : '';
	}

	static function recordDiagnostic(message:String):Void {
		if (diagnosticBuffer == null)
			diagnosticBuffer = [];
		if (diagnosticBuffer.indexOf(message) < 0)
			diagnosticBuffer.push(message);
	}
	#end
}
