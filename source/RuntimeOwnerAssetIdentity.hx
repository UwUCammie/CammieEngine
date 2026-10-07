package;

import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

typedef RuntimeOwnerAssetIdentityEntry = {
	var library:String;
	var id:String;
	var type:String;
	var ownerRelative:String;
	var size:Int;
	var sha256:String;
	var candidateOrder:Int;
}

typedef RuntimeOwnerAssetIdentityResult = {
	/** found, missing, type-mismatch, unclaimed, unknown, no-index, invalid. */
	var state:String;
	var owner:String;
	var library:String;
	var id:String;
	var expectedType:Null<String>;
	var entry:Null<RuntimeOwnerAssetIdentityEntry>;
	var path:Null<String>;
}

private typedef RuntimeOwnerAssetIdentityManifestFile = {
	var path:String;
	var sha256:String;
}

/** A small, receipt-bound runtime view of one imported Lime identity catalog.
	The manager supplies the already inspected commit binding; this class reads
	only the small index and checks its entries against that committed file list.
 */
@:keep
class RuntimeOwnerAssetIdentity {
	static inline var MAX_INDEX_BYTES:Int = 16777216;
	static inline var OWNER_PREFIX:String = 'assets/imported_mods/';
	static inline var IDENTITY_DIRECTORY:String = '.cammie-asset-identities';
	static var cache:Map<String, RuntimeOwnerAssetIdentity> = new Map();

	public final owner:String;
	public final engine:String;
	public final scope:String;
	public final generation:Int;
	public final availabilityRevision:Int;
	public final transactionId:String;
	public final bindingSignature:String;
	public final bindingState:String;
	public final complete:Bool;
	public final librariesComplete:Bool;
	public final libraries:Array<String>;
	public final entries:Array<RuntimeOwnerAssetIdentityEntry>;
	final byKey:Map<String, RuntimeOwnerAssetIdentityEntry>;
	final verified:Bool;

	function new(owner:String, engine:String, scope:String, generation:Int, revision:Int,
		transactionId:String, bindingSignature:String, bindingState:String, verified:Bool, complete:Bool,
		librariesComplete:Bool, libraries:Array<String>, entries:Array<RuntimeOwnerAssetIdentityEntry>) {
		this.owner = owner;
		this.engine = engine;
		this.scope = scope;
		this.generation = generation;
		availabilityRevision = revision;
		this.transactionId = transactionId;
		this.bindingSignature = bindingSignature;
		this.bindingState = bindingState;
		this.verified = verified;
		this.complete = complete;
		this.librariesComplete = librariesComplete;
		this.libraries = libraries == null ? [] : libraries.copy();
		this.entries = entries == null ? [] : entries.copy();
		byKey = new Map();
		for (entry in this.entries) byKey.set(key(entry.library, entry.id), entry);
	}

	/** Reuse only while both manager epochs and the committed transaction match. */
	public static function acquire(ownerRoot:String, engineName:String, assetScope:String):RuntimeOwnerAssetIdentity {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		var engine = ImportRevision.normalizeEngine(engineName);
		var scope = canonicalScope(engine, assetScope);
		if (owner == '' || scope == null)
			return empty(owner, engine, assetScope, 'invalid');
		var cacheKey = ownerKey(owner) + '|' + engine + '|' + scope;
		#if sys
		var liveGeneration = ImportRefreshManager.generation;
		var liveRevision = ImportRefreshManager.availabilityRevision();
		var existing = cache.get(cacheKey);
		if (existing != null && existing.generation == liveGeneration
			&& existing.availabilityRevision == liveRevision) return existing;
		var rawBinding:Dynamic = ImportRefreshManager.ownerAssetIndexBinding(owner, engine, scope);
		#else
		var rawBinding:Dynamic = null;
		#end
		if (rawBinding == null) {
			#if sys
			var sidecarRelative = SourceLimeAssetIdentity.sidecarRelativePath(engine, scope);
			var sidecarPath = sidecarRelative == null ? null : owner + '/' + sidecarRelative;
			var state = sidecarPath != null && FileSystem.exists(sidecarPath) ? 'unverified' : 'no-index';
			var unavailable = empty(owner, engine, scope, state, liveGeneration, liveRevision);
			cache.set(cacheKey, unavailable);
			return unavailable;
			#else
			return empty(owner, engine, scope, 'no-index');
			#end
		}

		var generation = intField(rawBinding, 'generation', -1);
		var revision = intField(rawBinding, 'revision', -1);
		var transactionId = stringField(rawBinding, 'transactionId');
		var indexPath = stringField(rawBinding, 'indexPath');
		var indexHash = lower(stringField(rawBinding, 'indexSha256'));
		var signature = generation + '|' + revision + '|' + transactionId + '|'
			+ pathKey(indexPath) + '|' + indexHash;
		var loaded = load(owner, engine, scope, rawBinding, generation, revision,
			transactionId, signature);
		cache.set(cacheKey, loaded);
		return loaded;
	}

	public static function lookup(owner:String, engine:String, scope:String, id:String,
		?expectedType:String):RuntimeOwnerAssetIdentityResult {
		return acquire(owner, engine, scope).resolve(id, expectedType);
	}

	public static function ownerLibraryState(owner:String, engine:String, scope:String,
		library:String):String {
		return acquire(owner, engine, scope).libraryState(library);
	}

	public static function ownerList(owner:String, engine:String, scope:String,
		?library:String, ?expectedType:String):Array<String> {
		return acquire(owner, engine, scope).list(library, expectedType);
	}

	/** Resolve one exact Lime library/id pair. No global fallback decision is
	made here; callers may fall back only for no-index or unclaimed results. */
	public function resolve(idValue:String, expectedType:Null<String>):RuntimeOwnerAssetIdentityResult {
		var parsed:Dynamic = SourceLimeAssetIdentity.parseQualifiedId(idValue);
		if (parsed == null)
			return result('invalid', null, null, expectedType, null, null);
		var library = SourceLimeAssetIdentity.canonicalLibrary(Reflect.field(parsed, 'library'));
		var id = stringField(parsed, 'id');
		if (id == '' || library == '') return result('invalid', library, id, expectedType, null, null);
		if (bindingState == 'no-index') return result('no-index', library, id, expectedType, null, null);
		if (bindingState == 'unverified' || bindingState == 'invalid')
			return result(bindingState, library, id, expectedType, null, null);
		if (!verified) return result('unknown', library, id, expectedType, null, null);

		var entry = byKey.get(key(library, id));
		if (entry != null) {
			if (!SourceLimeAssetIdentity.typeMatches(entry.type, expectedType))
				return result('type-mismatch', library, id, expectedType, entry, null);
			var physical = owner + '/' + entry.ownerRelative;
			#if sys
			physical = FNFAssets.resolveCaseInsensitivePath(physical);
			if (physical == null || !FileSystem.exists(physical) || FileSystem.isDirectory(physical)
				|| !PsychOwnerAssetPath.withinOwner(owner, physical))
				return result('unknown', library, id, expectedType, entry, null);
			#end
			return result('found', library, id, expectedType, entry, physical);
		}

		if (libraries.indexOf(library) >= 0)
			return result(complete ? 'missing' : 'unknown', library, id, expectedType, null, null);
		if (!complete || !librariesComplete) return result('unknown', library, id, expectedType, null, null);
		return result('unclaimed', library, id, expectedType, null, null);
	}

	/** Stable caller-facing name for the per-owner compiled/native asset bridge. */
	public function resolveAssetId(idValue:String, ?expectedType:String):RuntimeOwnerAssetIdentityResult {
		return resolve(idValue, expectedType);
	}

	public function libraryState(libraryValue:String):String {
		var library = SourceLimeAssetIdentity.canonicalLibrary(libraryValue);
		if (bindingState == 'no-index') return 'unclaimed';
		if (!verified) return 'unknown';
		if (libraries.indexOf(library) >= 0) return 'declared';
		return complete && librariesComplete ? 'unclaimed' : 'unknown';
	}

	public function hasLibrary(library:String):Bool return libraryState(library) == 'declared';

	/** Lime lists raw IDs, so identical IDs from distinct owner libraries remain
	separate entries in this list. */
	public function list(?libraryValue:String, ?expectedType:String):Array<String> {
		var output:Array<String> = [];
		if (!verified) return output;
		var library = libraryValue == null ? null : SourceLimeAssetIdentity.canonicalLibrary(libraryValue);
		for (entry in entries) {
			if (library != null && entry.library != library) continue;
			if (!SourceLimeAssetIdentity.typeMatches(entry.type, expectedType)) continue;
			output.push(entry.id);
		}
		return output;
	}

	public function release():Void {
		var prefix = ownerKey(owner) + '|' + engine + '|' + scope;
		cache.remove(prefix);
	}

	/** Drop only bindings for the exact selected owner. */
	public static function releaseOwner(ownerRoot:String):Void {
		var owner = normalizeOwnerKey(ownerRoot);
		if (owner == '') return;
		var prefix = ownerKey(owner) + '|';
		var remove:Array<String> = [];
		for (entryOwner in cache.keys()) if (entryOwner.startsWith(prefix)) remove.push(entryOwner);
		for (entryOwner in remove) cache.remove(entryOwner);
	}

	static function load(owner:String, engine:String, scope:String, binding:Dynamic,
		generation:Int, revision:Int, transactionId:String, signature:String):RuntimeOwnerAssetIdentity {
		var namespace = owner.substr(OWNER_PREFIX.length);
		var boundOwner = stringField(binding, 'owner');
		var boundEngine = stringField(binding, 'engine');
		var boundScope = canonicalScope(boundEngine, stringField(binding, 'scope'));
		if (pathKey(boundOwner) != pathKey(owner) || boundEngine != engine || boundScope != scope
			|| stringField(binding, 'namespace') != namespace || transactionId == '')
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);

		var indexPath = normalizeInstallPath(stringField(binding, 'indexPath'));
		var indexRelative = indexPath == null || !indexPath.startsWith(owner + '/')
			? null : indexPath.substr(owner.length + 1);
		var expectedRelative = SourceLimeAssetIdentity.sidecarRelativePath(engine, scope);
		var expectedPath = expectedRelative == null ? null : owner + '/' + expectedRelative;
		if (indexRelative == null || pathKey(indexPath) != pathKey(expectedPath))
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);

		var indexHash = lower(stringField(binding, 'indexSha256'));
		if (!validHash(indexHash))
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		var committed = committedFiles(binding);
		var committedIndex = committed.get(pathKey(indexPath));
		if (committedIndex == null || lower(committedIndex.sha256) != indexHash)
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		#if sys
		if (!FileSystem.exists(indexPath) || FileSystem.isDirectory(indexPath))
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		var bytes:Bytes;
		try bytes = File.getBytes(indexPath) catch (_:Dynamic)
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		if (bytes.length > MAX_INDEX_BYTES || Sha256.make(bytes).toHex() != indexHash)
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		var indexRaw:Dynamic;
		try indexRaw = haxe.Json.parse(bytes.toString()) catch (_:Dynamic)
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		#else
		var bytes = FNFAssets.getBytes(indexPath);
		if (bytes == null || bytes.length > MAX_INDEX_BYTES || Sha256.make(bytes).toHex() != indexHash)
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		var indexRaw:Dynamic;
		try indexRaw = haxe.Json.parse(bytes.toString()) catch (_:Dynamic)
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		#end

		var index:Dynamic = SourceLimeAssetIdentity.validate(indexRaw, owner, engine, scope, namespace);
		if (index == null || stringField(index, 'snapshotId') != stringField(binding, 'snapshotId')
			|| stringField(index, 'rootRelative') != stringField(binding, 'rootRelative')
			|| lower(stringField(index, 'projectSha256')) != lower(stringField(binding, 'projectSha256')))
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);

		var libraries:Array<String> = [];
		var rawLibraries:Dynamic = Reflect.field(index, 'libraries');
		if (Std.isOfType(rawLibraries, Array)) for (rawLibrary in (cast rawLibraries:Array<Dynamic>)) {
			var name:Dynamic = Std.isOfType(rawLibrary, String) ? rawLibrary : Reflect.field(rawLibrary, 'name');
			var canonical = SourceLimeAssetIdentity.canonicalLibrary(name == null ? '' : Std.string(name));
			if (canonical != '' && libraries.indexOf(canonical) < 0) libraries.push(canonical);
		}
		if (libraries.indexOf('default') < 0 && hasDefaultEntry(Reflect.field(index, 'entries')))
			libraries.push('default');

		var entries:Array<RuntimeOwnerAssetIdentityEntry> = [];
		var seen:Map<String, Bool> = new Map();
		var rawEntries:Dynamic = Reflect.field(index, 'entries');
		if (!Std.isOfType(rawEntries, Array))
			return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
		for (rawEntry in (cast rawEntries:Array<Dynamic>)) {
			var library = SourceLimeAssetIdentity.canonicalLibrary(stringField(rawEntry, 'library'));
			var id = stringField(rawEntry, 'id');
			var relative = safeOwnerRelative(stringField(rawEntry, 'ownerRelative'));
			var hash = lower(stringField(rawEntry, 'sha256'));
			var fullPath = relative == null ? null : normalizeInstallPath(owner + '/' + relative);
			var manifestFile = fullPath == null ? null : committed.get(pathKey(fullPath));
			var entryKey = key(library, id);
			if (library == '' || id == '' || relative == null || !validHash(hash)
				|| manifestFile == null || lower(manifestFile.sha256) != hash || seen.exists(entryKey))
				return empty(owner, engine, scope, 'invalid', generation, revision, transactionId);
			seen.set(entryKey, true);
			entries.push({library:library, id:id, type:upper(stringField(rawEntry, 'type')),
				ownerRelative:relative, size:intField(rawEntry, 'size', -1), sha256:hash,
				candidateOrder:intField(rawEntry, 'candidateOrder', -1)});
		}

		var complete = Reflect.field(index, 'complete') == true;
		var librariesComplete = Reflect.field(index, 'librariesComplete') == true;
		return new RuntimeOwnerAssetIdentity(owner, engine, scope, generation, revision,
			transactionId, signature, 'ready', true, complete, librariesComplete, libraries, entries);
	}

	static function committedFiles(binding:Dynamic):Map<String, RuntimeOwnerAssetIdentityManifestFile> {
		var result:Map<String, RuntimeOwnerAssetIdentityManifestFile> = new Map();
		var rawFiles:Dynamic = Reflect.field(binding, 'files');
		if (!Std.isOfType(rawFiles, Array)) return result;
		for (raw in (cast rawFiles:Array<Dynamic>)) {
			var path = normalizeInstallPath(stringField(raw, 'path'));
			var hash = lower(stringField(raw, 'sha256'));
			if (path == null || !validHash(hash)) continue;
			var key = pathKey(path);
			var prior = result.get(key);
			if (prior != null && lower(prior.sha256) != hash) result.remove(key);
			else if (prior == null) result.set(key, {path:path, sha256:hash});
		}
		return result;
	}

	static function hasDefaultEntry(rawEntries:Dynamic):Bool {
		if (!Std.isOfType(rawEntries, Array)) return false;
		for (entry in (cast rawEntries:Array<Dynamic>))
			if (SourceLimeAssetIdentity.canonicalLibrary(stringField(entry, 'library')) == 'default') return true;
		return false;
	}

	static function safeOwnerRelative(value:String):Null<String> {
		var clean = normalizeInstallPath(value);
		if (clean == null || clean == '' || clean.startsWith(OWNER_PREFIX)
			|| clean.startsWith(IDENTITY_DIRECTORY + '/') || clean == IDENTITY_DIRECTORY) return null;
		return clean;
	}

	static function normalizeInstallPath(value:String):Null<String> {
		if (value == null || value == '' || value.indexOf('\x00') >= 0) return null;
		var clean = value.replace('\\', '/');
		if (clean.startsWith('/') || clean.indexOf(':') >= 0) return null;
		for (part in clean.split('/')) if (part == '' || part == '.' || part == '..') return null;
		clean = Path.normalize(clean).replace('\\', '/');
		return clean == '.' ? null : clean;
	}

	static function canonicalScope(engine:String, scope:String):Null<String> {
		if (engine == 'Psych Engine') return scope == '' || scope == 'package' ? 'package' : null;
		if (engine == 'Nightmare Vision' && (scope == 'package' || scope == 'core')) return scope;
		return null;
	}

	static function empty(owner:String, engine:String, scope:String, state:String,
		generation:Int = -1, revision:Int = -1, transactionId:String = ''):RuntimeOwnerAssetIdentity {
		return new RuntimeOwnerAssetIdentity(owner, engine, scope, generation, revision,
			transactionId, '', state, false, false, false, [], []);
	}

	function result(state:String, library:String, id:String, expectedType:Null<String>,
		entry:RuntimeOwnerAssetIdentityEntry, path:Null<String>):RuntimeOwnerAssetIdentityResult {
		return {state:state, owner:owner, library:library, id:id,
			expectedType:expectedType, entry:entry, path:path};
	}

	static function key(library:String, id:String):String return library + '\x00' + id;
	static function ownerKey(owner:String):String {
		#if windows
		return owner.toLowerCase();
		#else
		return owner;
		#end
	}
	static function normalizeOwnerKey(value:String):String {
		if (value == null) return '';
		var clean = Path.normalize(value.replace('\\', '/')).replace('\\', '/');
		if (!clean.startsWith(OWNER_PREFIX.substr(0, OWNER_PREFIX.length - 1) + '/')) return '';
		return clean;
	}
	static function pathKey(path:String):String {
		var clean = normalizeInstallPath(path);
		if (clean == null) return '';
		return ownerKey(clean);
	}
	static function stringField(value:Dynamic, field:String):String {
		var raw = value == null ? null : Reflect.field(value, field);
		return raw == null ? '' : Std.string(raw);
	}
	static function intField(value:Dynamic, field:String, fallback:Int):Int {
		var raw = value == null ? null : Reflect.field(value, field);
		return Std.isOfType(raw, Int) ? cast raw : fallback;
	}
	static function lower(value:String):String return value == null ? '' : value.toLowerCase();
	static function upper(value:String):String return value == null ? '' : value.toUpperCase();
	static function validHash(value:String):Bool {
		if (value == null || value.length != 64) return false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			if (!((code >= 48 && code <= 57) || (code >= 97 && code <= 102))) return false;
		}
		return true;
	}
}
