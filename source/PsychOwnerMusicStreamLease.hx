package;

import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.Path;
import haxe.Timer;
import ImportSourceSnapshot.ImportSnapshotSha256;
import lime.app.Application;
import lime.media.AudioBuffer;
import lime.media.vorbis.VorbisFile;
import RuntimeOwnerAssetIdentity.RuntimeOwnerAssetIdentityEntry;
import RuntimeOwnerAssetIdentity;
import openfl.media.Sound;
#if sys
import sys.FileSystem;
import sys.io.File;
import sys.io.FileInput;
import sys.io.FileOutput;
#end
#if cpp
import cpp.vm.WeakRef;
#end

using StringTools;

private typedef PsychOwnerMusicStreamLeaseRef = #if cpp WeakRef<AudioBuffer>
	#else AudioBuffer #end;

private typedef PsychOwnerMusicStreamLeaseRecord = {
	var key:String;
	var owner:String;
	var engine:String;
	var scope:String;
	var bindingSignature:String;
	var path:String;
	var refs:Array<PsychOwnerMusicStreamLeaseRef>;
	var retired:Bool;
	var verifiedSize:Int;
	var verifiedMtime:Float;
}

/**
	Streams authenticated owner MUSIC from a private immutable file. Lime's
	VorbisFile.fromFile keeps the file handle open for the lifetime of its audio
	buffer; importing a refreshed owner replaces its managed file on Windows.
	The lease therefore gives each live stream its own content-addressed copy
	without changing Assets.getPath or the selected owner's receipt paths.
*/
@:keep
class PsychOwnerMusicStreamLease {
	static inline var LEASE_DIRECTORY:String = ".cammie-owner-music-leases";
	static var records:Map<String, PsychOwnerMusicStreamLeaseRecord> = new Map();
	static var sessionDirectory:Null<String>;
	static var temporaryCounter:Int = 0;
	static var sweepScheduled:Bool = false;
	static var sweepAgain:Bool = false;
	static var sweepQueue:Array<String> = [];
	static var sweepCursor:Int = 0;
	static var sweepNeedsRetry:Bool = false;
	static var exitHookInstalled:Bool = false;

	/** Return a streaming Sound for one verified Lime MUSIC-compatible entry.
		OpenFL getMusic is path-based and may be given a Lime SOUND ID. A null result
		means the platform has no supported file-backed Vorbis path, allowing the
		caller to use its ordinary Lime/OpenFL fallback. Identity and file errors
		are raised so stale or tampered owner bytes can never be streamed silently.
	*/
	public static function getSound(identity:RuntimeOwnerAssetIdentity,
		entry:RuntimeOwnerAssetIdentityEntry):Null<Sound> {
		#if (cpp && sys && lime_cffi && lime_vorbis && lime > "7.9.0")
		if (identity == null || entry == null) return null;
		var current:RuntimeOwnerAssetIdentity;
		try current = RuntimeOwnerAssetIdentity.acquire(identity.owner, identity.engine, identity.scope)
		catch (error:Dynamic) throw '[psych-assets] Could not revalidate selected-owner music: ' + Std.string(error);
		if (current != identity || current.bindingState != "ready"
			|| current.bindingSignature != identity.bindingSignature)
			throw "[psych-assets] Selected-owner music identity changed before streaming";

		var found = identity.resolve(entry.library + ":" + entry.id, "MUSIC");
		if (found.state != "found" || found.entry == null
			|| found.entry.ownerRelative != entry.ownerRelative
			|| lower(found.entry.sha256) != lower(entry.sha256)
			|| found.entry.size != entry.size)
			throw "[psych-assets] Selected-owner music entry is no longer receipt-verified";

		var key = leaseKey(identity, entry);
		var path = ensureLeaseFile(storageDirectory(), key, found.path, entry.size, entry.sha256);
		var record:PsychOwnerMusicStreamLeaseRecord;
		try record = prepareRecord(identity, key, path) catch (error:Dynamic) {
			if (!records.exists(key)) deleteLease(path);
			throw error;
		}
		var vorbis:VorbisFile = null;
		try vorbis = VorbisFile.fromFile(path) catch (error:Dynamic) {
			record.retired = true;
			scheduleSweep();
			throw error;
		}
		if (vorbis == null) {
			record.retired = true;
			scheduleSweep();
			return null;
		}
		var buffer:AudioBuffer;
		try buffer = AudioBuffer.fromVorbisFile(vorbis) catch (error:Dynamic) {
			vorbis.clear();
			record.retired = true;
			scheduleSweep();
			throw error;
		}
		if (buffer == null) {
			vorbis.clear();
			record.retired = true;
			scheduleSweep();
			return null;
		}
		var sound:Sound;
		try sound = Sound.fromAudioBuffer(buffer) catch (error:Dynamic) {
			vorbis.clear();
			record.retired = true;
			scheduleSweep();
			throw error;
		}
		if (sound == null) {
			vorbis.clear();
			record.retired = true;
			scheduleSweep();
			return null;
		}
		track(identity, key, path, buffer);
		return sound;
		#else
		return null;
		#end
	}

	/** Called when the manager retires this exact owner proof. Existing sounds
		keep their lease until their underlying audio buffers are collected. */
	@:keep public static function releaseIdentity(identity:RuntimeOwnerAssetIdentity):Void {
		if (identity == null) return;
		for (record in records) {
			if (record.owner == identity.owner && record.engine == identity.engine
				&& record.scope == identity.scope
				&& record.bindingSignature == identity.bindingSignature)
				record.retired = true;
		}
		scheduleSweep();
	}

	/** Drop only this owner's lease references; files with live streams remain
		intact until a later sweep observes that the stream buffers are gone. */
	@:keep public static function releaseOwner(ownerRoot:String):Void {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == "") return;
		for (record in records) if (sameOwner(record.owner, owner)) record.retired = true;
		scheduleSweep();
	}

	/** Retry removing files whose last stream buffer has been collected. This
		also cleans files left after a failed native open or a prior refresh. */
	@:keep public static function collectRetired():Void scheduleSweep();

	static function track(identity:RuntimeOwnerAssetIdentity, key:String, path:String,
		buffer:AudioBuffer):Void {
		var record = prepareRecord(identity, key, path);
		record.retired = false;
		#if cpp
		record.refs.push(new WeakRef(buffer));
		#else
		record.refs.push(buffer);
		#end
	}

	static function prepareRecord(identity:RuntimeOwnerAssetIdentity, key:String,
		path:String):PsychOwnerMusicStreamLeaseRecord {
		var record = records.get(key);
		if (record == null) {
			var stat = FileSystem.stat(path);
			record = {key:key, owner:identity.owner, engine:identity.engine,
				scope:identity.scope, bindingSignature:identity.bindingSignature,
				path:path, refs:[], retired:true, verifiedSize:stat.size,
				verifiedMtime:stat.mtime.getTime()};
			records.set(key, record);
		} else if (record.path != path || record.owner != identity.owner
			|| record.engine != identity.engine || record.scope != identity.scope
			|| record.bindingSignature != identity.bindingSignature) {
			throw "[psych-assets] Music lease key collided with another owner identity";
		}
		return record;
	}

	static function scheduleSweep():Void {
		if (sweepScheduled) {
			sweepAgain = true;
			return;
		}
		sweepScheduled = true;
		sweepQueue = [];
		for (key in records.keys()) {
			var record = records.get(key);
			if (record != null && record.retired) sweepQueue.push(key);
		}
		sweepCursor = 0;
		if (sweepQueue.length == 0) {
			sweepScheduled = false;
			if (sweepAgain) {
				sweepAgain = false;
				scheduleSweep();
			} else if (sweepNeedsRetry) {
				sweepNeedsRetry = false;
				Timer.delay(scheduleSweep, 1000);
			}
			return;
		}
		Timer.delay(sweepOne, 0);
	}

	static function sweepOne():Void {
		if (sweepCursor < sweepQueue.length) {
			var key = sweepQueue[sweepCursor++];
			var record = records.get(key);
			if (record != null && record.retired) {
				var live:Array<PsychOwnerMusicStreamLeaseRef> = [];
				for (reference in record.refs) {
					var buffer = #if cpp reference.get() #else reference #end;
					if (buffer != null) live.push(reference);
				}
				record.refs = live;
				if (live.length == 0) {
					if (deleteLease(record.path)) records.remove(key);
					else sweepNeedsRetry = true;
				} else sweepNeedsRetry = true;
			}
		}
		if (sweepCursor < sweepQueue.length) {
			Timer.delay(sweepOne, 16);
			return;
		}
		sweepScheduled = false;
		sweepQueue = [];
		if (sweepAgain) {
			sweepAgain = false;
			scheduleSweep();
		} else if (sweepNeedsRetry) {
			sweepNeedsRetry = false;
			Timer.delay(scheduleSweep, 1000);
		}
	}

	static function deleteLease(path:String):Bool {
		#if sys
		if (path == null || path == "" || !FileSystem.exists(path)) return true;
		try {
			if (FileSystem.isDirectory(path)) return false;
			FileSystem.deleteFile(path);
			return !FileSystem.exists(path);
		} catch (_:Dynamic) return false;
		#else
		return true;
		#end
	}

	static function leaseKey(identity:RuntimeOwnerAssetIdentity,
		entry:RuntimeOwnerAssetIdentityEntry):String {
		var fields = [identity.owner, identity.engine, identity.scope,
			identity.bindingSignature, entry.library, entry.id, entry.ownerRelative,
			lower(entry.sha256)];
		var framed = [for (field in fields) Std.string(field == null ? "" : field).length + ":" + field].join("|");
		return Sha256.make(Bytes.ofString(framed)).toHex().toLowerCase();
	}

	static function storageDirectory():String {
		if (sessionDirectory != null) return sessionDirectory;
		#if (sys && cpp)
		var storage = lime.system.System.applicationStorageDirectory;
		if (storage == null || StringTools.trim(storage) == "")
			throw "[psych-assets] Application storage is unavailable for streaming owner music";
		var base = Path.normalize(storage);
		ensureDirectoryTree(base);
		var parent = Path.normalize(base + "/" + LEASE_DIRECTORY);
		if (!FileSystem.exists(parent)) FileSystem.createDirectory(parent);
		if (!FileSystem.isDirectory(parent))
			throw "[psych-assets] Private owner music lease directory is unavailable";
		var seed = Std.string(Date.now().getTime()) + "|" + Std.string(Sys.time()) + "|" + Std.string(Math.random());
		var session = Sha256.make(Bytes.ofString(seed)).toHex().substr(0, 24).toLowerCase();
		var path = Path.normalize(parent + "/" + session);
		if (!inside(parent, path)) throw "[psych-assets] Owner music lease path escaped application storage";
		if (!FileSystem.exists(path)) FileSystem.createDirectory(path);
		if (!FileSystem.isDirectory(path))
			throw "[psych-assets] Private owner music session directory is unavailable";
		sessionDirectory = path;
		installExitCleanup();
		return path;
		#else
		throw "[psych-assets] File-backed streaming leases require native system storage";
		#end
	}

	static function installExitCleanup():Void {
		#if (cpp && sys)
		if (exitHookInstalled) return;
		var app = Application.current;
		if (app == null) return;
		exitHookInstalled = true;
		app.onExit.add(function(_exitCode) cleanupSessionAtExit());
		#end
	}

	static function cleanupSessionAtExit():Void {
		#if (cpp && sys)
		var paths:Array<String> = [];
		for (record in records) {
			record.retired = true;
			paths.push(record.path);
		}
		for (path in paths) deleteLease(path);
		var directory = sessionDirectory;
		if (directory != null && FileSystem.exists(directory) && FileSystem.isDirectory(directory)) {
			try FileSystem.deleteDirectory(directory) catch (_:Dynamic) {}
		}
		#end
	}

	static function ensureDirectoryTree(path:String):Void {
		#if sys
		if (FileSystem.exists(path)) {
			if (!FileSystem.isDirectory(path))
				throw "[psych-assets] Application storage path is not a directory";
			return;
		}
		var parent = Path.directory(path);
		if (parent == null || parent == "" || parent == path)
			throw "[psych-assets] Could not create application storage directory";
		ensureDirectoryTree(parent);
		FileSystem.createDirectory(path);
		if (!FileSystem.isDirectory(path))
			throw "[psych-assets] Could not create application storage directory";
		#end
	}

	static function ensureLeaseFile(root:String, key:String, sourcePath:String,
		expectedSize:Int, expectedHash:String):String {
		#if sys
		var hash = lower(expectedHash);
		if (root == null || root == "" || !validHash(key) || !validHash(hash)
			|| expectedSize < 0 || sourcePath == null || sourcePath == "")
			throw "[psych-assets] Invalid selected-owner music lease request";
		var directory = Path.normalize(root);
		// leaseKey already commits to owner, proof, asset identity, and content SHA.
		// Avoid repeating the content digest in the filename so native Vorbis can
		// open the private copy even below long user/runtime storage paths.
		var destination = Path.normalize(directory + "/" + key + ".ogg");
		if (!inside(directory, destination)) throw "[psych-assets] Owner music lease destination escaped its private directory";
		var destinationExists = FileSystem.exists(destination);
		if (destinationExists && FileSystem.isDirectory(destination))
			throw "[psych-assets] Immutable owner music lease path is a directory";
		var knownLease = records.get(key);
		var verifiedStat:sys.FileStat = null;
		var destinationAlreadyVerified = false;
		if (destinationExists && knownLease != null && knownLease.path == destination) {
			try verifiedStat = FileSystem.stat(destination) catch (_:Dynamic) verifiedStat = null;
			destinationAlreadyVerified = verifiedStat != null
				&& verifiedStat.size == knownLease.verifiedSize
				&& verifiedStat.mtime.getTime() == knownLease.verifiedMtime;
		}
		if (destinationExists && !destinationAlreadyVerified)
			verifyLeaseFile(destination, expectedSize, hash);
		if (destinationAlreadyVerified) return destination;

		var temporary:String = null;
		if (!destinationExists) {
			var attempts = 0;
			while (attempts < 8) {
				temporaryCounter++;
				var suffix = Sha256.make(Bytes.ofString(key + "|" + Std.string(temporaryCounter)
					+ "|" + Std.string(Math.random()))).toHex().substr(0, 16);
				var candidate = Path.normalize(directory + "/." + key + "-" + suffix + ".part");
				if (!FileSystem.exists(candidate)) {
					temporary = candidate;
					break;
				}
				attempts++;
			}
			if (temporary == null) throw "[psych-assets] Could not allocate a private owner music lease file";
		}
		var before:sys.FileStat;
		try before = FileSystem.stat(sourcePath) catch (error:Dynamic)
			throw '[psych-assets] Could not inspect selected-owner music: ' + Std.string(error);
		if (before.size != expectedSize || FileSystem.isDirectory(sourcePath))
			throw "[psych-assets] Selected-owner music size no longer matches the committed identity";
		var input:FileInput = null;
		var output:FileOutput = null;
		var total = 0;
		var sourceHash = new ImportSnapshotSha256();
		var buffer = Bytes.alloc(65536);
		try {
			input = File.read(sourcePath, true);
			if (temporary != null) output = File.write(temporary, true);
			while (true) {
				var count:Int;
				try count = input.readBytes(buffer, 0, buffer.length) catch (_:haxe.io.Eof) break;
				if (count <= 0) break;
				total += count;
				sourceHash.update(buffer, 0, count);
				if (output != null && output.writeBytes(buffer, 0, count) != count)
					throw "[psych-assets] Short write while creating owner music lease";
			}
		} catch (error:Dynamic) {
			if (input != null) try input.close() catch (_:Dynamic) {}
			if (output != null) try output.close() catch (_:Dynamic) {}
			if (temporary != null && FileSystem.exists(temporary))
				try FileSystem.deleteFile(temporary) catch (_:Dynamic) {}
			throw '[psych-assets] Could not copy selected-owner music: ' + Std.string(error);
		}
		if (input != null) input.close();
		if (output != null) output.close();
		var after:sys.FileStat;
		try after = FileSystem.stat(sourcePath) catch (error:Dynamic) {
			if (temporary != null && FileSystem.exists(temporary)) FileSystem.deleteFile(temporary);
			throw '[psych-assets] Could not verify selected-owner music after copying: ' + Std.string(error);
		}
		if (total != expectedSize || sourceHash.digestHex() != hash
			|| after.size != before.size || after.mtime.getTime() != before.mtime.getTime()) {
			if (temporary != null && FileSystem.exists(temporary)) FileSystem.deleteFile(temporary);
			throw "[psych-assets] Selected-owner music changed while its stream lease was being created";
		}
		if (temporary != null) {
			if (FileSystem.exists(destination)) {
				verifyLeaseFile(destination, expectedSize, hash);
				FileSystem.deleteFile(temporary);
			} else try FileSystem.rename(temporary, destination) catch (error:Dynamic) {
				if (!FileSystem.exists(destination)) {
					if (FileSystem.exists(temporary)) FileSystem.deleteFile(temporary);
					throw error;
				}
				verifyLeaseFile(destination, expectedSize, hash);
				if (FileSystem.exists(temporary)) FileSystem.deleteFile(temporary);
			}
		}
		var finalStat = FileSystem.stat(destination);
		if (finalStat.size != expectedSize)
			throw "[psych-assets] Owner music lease copy has an unexpected size";
		if (knownLease != null) {
			knownLease.verifiedSize = finalStat.size;
			knownLease.verifiedMtime = finalStat.mtime.getTime();
		}
		return destination;
		#else
		throw "[psych-assets] Native filesystem is required for owner music leases";
		#end
	}

	static function verifyLeaseFile(path:String, expectedSize:Int, expectedHash:String):Void {
		#if sys
		if (!FileSystem.exists(path) || FileSystem.isDirectory(path))
			throw "[psych-assets] Immutable owner music lease is missing";
		var input:FileInput = null;
		var size = 0;
		var hash = new ImportSnapshotSha256();
		var buffer = Bytes.alloc(65536);
		try {
			input = File.read(path, true);
			while (true) {
				var count:Int;
				try count = input.readBytes(buffer, 0, buffer.length) catch (_:haxe.io.Eof) break;
				if (count <= 0) break;
				size += count;
				hash.update(buffer, 0, count);
			}
			input.close();
		} catch (_:Dynamic) {
			if (input != null) try input.close() catch (_:Dynamic) {}
			throw "[psych-assets] Could not verify immutable owner music lease";
		}
		if (size != expectedSize || hash.digestHex() != lower(expectedHash))
			throw "[psych-assets] Immutable owner music lease content did not match its receipt hash";
		#end
	}

	static function inside(root:String, path:String):Bool {
		var normalizedRoot = Path.normalize(root);
		var normalizedPath = Path.normalize(path);
		#if windows
		var rootKey = normalizedRoot.toLowerCase();
		var pathKey = normalizedPath.toLowerCase();
		#else
		var rootKey = normalizedRoot;
		var pathKey = normalizedPath;
		#end
		if (pathKey == rootKey) return false;
		if (!rootKey.endsWith("/")) rootKey += "/";
		return pathKey.startsWith(rootKey);
	}

	static function validHash(value:String):Bool {
		if (value == null || value.length != 64) return false;
		for (index in 0...value.length) {
			var char = value.charCodeAt(index);
			if (!((char >= 48 && char <= 57) || (char >= 97 && char <= 102))) return false;
		}
		return true;
	}

	static function lower(value:String):String return value == null ? "" : value.toLowerCase();

	static function sameOwner(left:String, right:String):Bool {
		#if windows
		return left != null && right != null && left.toLowerCase() == right.toLowerCase();
		#else
		return left == right;
		#end
	}
}
