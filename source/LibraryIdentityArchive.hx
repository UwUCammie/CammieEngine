package;

import haxe.Json;
import haxe.io.Path;
import ImportInstalledOwnership.InstalledLibraryIdentity;
import sys.FileSystem;
import sys.io.File;

/** Durable identity reservations. User favorites/scores stay in their existing saves;
 * retaining both owner/source and destination keys makes them reachable on reinstall. */
class LibraryIdentityArchive {
	public static inline var DATA:String = 'import-cache/library-history/data/identities.json';
	static inline var STATE:String = 'import-cache/library-history/state';
	static inline var OWNER:String = 'library-history-identities';
	static inline var MAX_BYTES:Int = 8388608;
	static inline var MAX_RECORDS:Int = 32768;
	#if target.threaded
	static var mutex = new sys.thread.Mutex();
	#end
	var entries:Array<InstalledLibraryIdentity>;
	public var records(get, never):Array<InstalledLibraryIdentity>;
	function get_records():Array<InstalledLibraryIdentity> return [for (entry in entries) validate(entry)];
	public function new(?records:Array<InstalledLibraryIdentity>) {
		entries = [];
		if (records != null) {
			if (records.length > MAX_RECORDS) throw 'Library identity archive record limit exceeded.';
			var seen:Map<String,Bool> = []; var bindings:Map<String,String> = [];
			for (record in records) {
				var entry = validate(record); var key = Json.stringify(entry);
				var folder = entry.folder.toLowerCase();
				var binding = Json.stringify([entry.ownerRoot,entry.sourceFolder.toLowerCase(),entry.engine]);
				if (bindings.exists(folder) && bindings.get(folder) != binding)
					throw 'Conflicting archived chart destination: ' + entry.folder;
				bindings.set(folder,binding);
				if (!seen.exists(key)) { entries.push(entry); seen.set(key,true); }
			}
		}
		entries.sort(function(a,b) return Reflect.compare(Json.stringify(a),Json.stringify(b)));
	}
	public static function lookupKey(engine:String, identity:String, fingerprint:String):String {
		if (ImportEngine.normalize(engine) == ImportEngine.AUTO || identity == null || identity == '' || identity.length > 4096 || ~/[\x00-\x1F\x7F]/.match(identity)) return '';
		var parts = identity.split('|');
		if (parts.length < 3 || parts[0] != engine.toLowerCase() || parts[2] == '') return '';
		if (parts[1] == 'id') return identity;
		if (['package-name','user-name','inner-package-name','package-title'].indexOf(parts[1]) < 0) return '';
		if (fingerprint == null || !~/^[a-f0-9]{32}$/.match(fingerprint)) return '';
		return identity + '|' + fingerprint;
	}
	static function folder(value:String):String {
		if (value == null || value == '' || value.length > 256 || value.indexOf('/') >= 0 || value.indexOf('\\') >= 0)
			throw 'Invalid archived chart folder.';
		var path = ImportRefreshTransaction.managedAssetPath('assets/data/' + value);
		if (path != 'assets/data/' + value) throw 'Invalid archived chart folder.';
		return value;
	}
	static function text(record:Dynamic, name:String, limit:Int, empty:Bool = false):String {
		var value:Dynamic = record == null ? null : Reflect.field(record,name);
		if (!Std.isOfType(value,String)) throw 'Invalid archived identity field: ' + name;
		var result:String = cast value;
		if ((!empty && result == '') || result.length > limit || ~/[\x00-\x1F\x7F]/.match(result))
			throw 'Invalid archived identity field: ' + name;
		return result;
	}
	static function validate(record:Dynamic):InstalledLibraryIdentity {
		var engine = text(record,'engine',80);
		if (ImportEngine.normalize(engine) == ImportEngine.AUTO) throw 'Invalid archived source engine.';
		var owner = ImportRemovalPlan.ownerRoot(text(record,'ownerRoot',512));
		var identity = text(record,'sourceIdentity',4096,true);
		var fingerprint = text(record,'sourceFingerprint',32,true);
		if (fingerprint != '' && !~/^[a-f0-9]{32}$/.match(fingerprint)) throw 'Invalid archived source fingerprint.';
		if (identity != '' && lookupKey(engine,identity,'00000000000000000000000000000000') == '')
			throw 'Invalid archived source identity.';
		return {folder:folder(text(record,'folder',256)), ownerRoot:owner,
			sourceFolder:text(record,'sourceFolder',256), engine:engine, sourceIdentity:identity, sourceFingerprint:fingerprint};
	}
	public function encode():String return Json.stringify({version:1,records:entries});
	public static function decode(text:String):LibraryIdentityArchive {
		if (text == null || haxe.io.Bytes.ofString(text).length > MAX_BYTES) throw 'Library identity archive byte limit exceeded.';
		var raw:Dynamic = Json.parse(text);
		if (raw == null || raw.version != 1 || !Std.isOfType(raw.records,Array)) throw 'Invalid library identity archive.';
		return new LibraryIdentityArchive(cast raw.records);
	}
	/** No match remains unknown. Multiple owners or destinations must never be guessed. */
	public function ownerFor(engine:String, identity:String, fingerprint:String):Null<String> {
		var key = lookupKey(engine,identity,fingerprint); if (key == '') return null;
		var owner:String = null;
		for (entry in entries) if (lookupKey(entry.engine,entry.sourceIdentity,entry.sourceFingerprint) == key) {
			if (owner != null && owner != entry.ownerRoot) throw 'Archived package identity is ambiguous.';
			owner = entry.ownerRoot;
		}
		return owner;
	}
	/** `plannedFolder` is the folder the importer is about to use. One source folder can
	 * legitimately own several destinations (a V-Slice song and its erect variation both
	 * come from one source folder), so it tells them apart; without it, or when it names
	 * none of them, several destinations stay ambiguous and are never guessed. */
	public function destinationFor(engine:String, identity:String, fingerprint:String, sourceFolder:String, ?plannedFolder:String):Null<String> {
		var owner = ownerFor(engine,identity,fingerprint); if (owner == null || sourceFolder == null) return null;
		var key = lookupKey(engine,identity,fingerprint); var destinations:Array<String> = [];
		for (entry in entries) if (entry.ownerRoot == owner && entry.sourceFolder.toLowerCase() == sourceFolder.toLowerCase()
			&& lookupKey(entry.engine,entry.sourceIdentity,entry.sourceFingerprint) == key
			&& destinations.indexOf(entry.folder) < 0) destinations.push(entry.folder);
		if (destinations.length <= 1) return destinations.length == 0 ? null : destinations[0];
		if (plannedFolder != null && plannedFolder != '') {
			var wanted = plannedFolder.toLowerCase();
			var exact = [for (folder in destinations) if (folder.toLowerCase() == wanted) folder];
			// An owner-qualified destination is the planned folder followed by "--" and the owner tag.
			var qualified = [for (folder in destinations) if (StringTools.startsWith(folder.toLowerCase(), wanted + '--')) folder];
			var chosen = exact.length > 0 ? exact : qualified;
			if (chosen.length == 1) return chosen[0];
		}
		throw 'Archived chart identity is ambiguous.';
	}
	public static function load(install:String, ?cancel:Void->Bool):LibraryIdentityArchive {
		var view = new ImportMetadataInspection(install,cancel);
		var path = Path.join([view.root,DATA]); var state = Path.join([view.root,STATE]);
		var manifest = ImportRefreshTransaction.inspectCommittedManifest(view.root,state,OWNER,['import-cache/library-history/data'],cancel);
		if (manifest == null) {
			if (view.exists(path)) throw 'Library history has no committed ownership receipt.';
			view.verify(); return new LibraryIdentityArchive();
		}
		var result = decode(view.text(path,MAX_BYTES));
		if (manifest.files.length != 1 || manifest.files[0].path != DATA || manifest.files[0].sha256 != view.digest(path)
			|| manifest.ownedRoots.length != 1 || manifest.ownedRoots[0] != 'import-cache/library-history/data'
			|| manifest.revision == null || Reflect.field(manifest.revision,'schemaVersion') != 1)
			throw 'Library identity archive differs from its transaction manifest.';
		view.verify();
		var current = ImportRefreshTransaction.inspectCommittedManifest(view.root,state,OWNER,['import-cache/library-history/data'],cancel);
		if (current == null || current.transactionId != manifest.transactionId) throw 'Library identity archive changed during inspection.';
		return result;
	}
	/** Prepare history before removal. This does not remove a package or alter saves.
	 * A future executor must reserve owners and revalidate before its deletion commit. */
	public static function prepare(install:String, selected:Array<String>, protectedRoots:Array<String>, ?cancel:Void->Bool):LibraryIdentityArchive {
		#if target.threaded
		mutex.acquire();
		#end
		try {
			var result = prepareLocked(install,selected,protectedRoots,cancel);
			#if target.threaded
			mutex.release();
			#end
			return result;
		} catch (error:Dynamic) {
			#if target.threaded
			mutex.release();
			#end
			throw error;
		}
	}
	static function prepareLocked(install:String, selected:Array<String>, protectedRoots:Array<String>, cancel:Void->Bool):LibraryIdentityArchive {
		install = ImportRefreshTransaction.canonicalDirectory(install,false);
		if (selected == null || selected.length == 0) throw 'Select a package to archive.';
		var owners = [for (owner in selected) ImportRemovalPlan.ownerRoot(owner)];
		var manifests = ImportRefreshTransaction.inspectRetainedManifests(install,Path.join([install,'import-cache/state']),Path.join([install,'import-cache/records']),cancel);
		var audit = ImportInstalledOwnership.inspect(install,manifests,protectedRoots,cancel,true);
		if (!audit.complete) throw audit.blockers.join('; ');
		var committedOwners:Map<String,Bool> = new Map();
		for (manifest in manifests) for (owner in ImportRemovalPlan.manifestRoots(manifest)) committedOwners.set(owner,true);
		// A shared core provider may be a receipt-authenticated logical root
		// without a materialized namespace. It has no chart history to archive.
		for (owner in owners) if (!committedOwners.exists(owner)) throw 'Selected package has no committed ownership: ' + owner;
		var archive = load(install,cancel);
		var original = archive.encode();
		var merged = archive.records;
		for (record in audit.charts) if (owners.indexOf(record.ownerRoot) >= 0) merged.push(record);
		archive = new LibraryIdentityArchive(merged);
		var encoded = archive.encode();
		if (haxe.io.Bytes.ofString(encoded).length > MAX_BYTES) throw 'Library identity archive byte limit exceeded.';
		if (encoded == original) return archive;
		ImportRefreshTransaction.checkpointWork(cancel);
		var stage = ImportRefreshTransaction.safeChild(install,'import-cache/library-history/staging',false);
		ImportRefreshTransaction.ensureDirectoryUnder(install,stage);
		var staged = ImportRefreshTransaction.safeChild(stage,'identities.json',false);
		File.saveContent(staged,encoded);
		var result = ImportRefreshTransaction.apply(install,stage,Path.join([install,STATE]),OWNER,
			['import-cache/library-history/data'],[{path:DATA,stagedPath:'identities.json'}],{schemaVersion:1},cancel);
		if (result.status != ImportRefreshTransaction.STATUS_APPLIED) throw 'Library history archive was not committed: ' + result.status;
		ImportSongOwnership.invalidateOwnerIdentityIndex();
		return load(install,cancel);
	}
}
