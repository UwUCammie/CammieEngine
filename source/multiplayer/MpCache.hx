package multiplayer;

import haxe.io.Bytes;
import haxe.Json;
#if sys
import sys.FileSystem;
import sys.io.File;
import sys.io.FileOutput;
import sys.thread.Mutex;
#end

/** One cached file as the index remembers it. */
typedef MpCachedFile = {
	var size:Float;
	var used:Float;
}

/**
	The multiplayer cache, kept apart from the library: mpcache/files/<aa>/<sha256> holds
	files received from other players, named by their content, so a file shared by many
	songs is stored once. A size limit (option) evicts the least recently used files.

	It also remembers the hash of local runtime files by size and modification time, so a
	file is only read in full when it changed, and the list of files each song read the
	last time it was played (mpcache/songs), which a host's package is built from.
**/
class MpCache {
	public static inline var ROOT:String = 'mpcache';
	public static inline var DEFAULT_LIMIT:Float = 2.0 * 1024 * 1024 * 1024;
	static inline var CHUNK:Int = 1024 * 1024;

	/** The size limit in bytes; the options screen sets it. */
	public static var limitBytes:Float = DEFAULT_LIMIT;

	public static function limit():Float
		return limitBytes;

	#if sys
	static var lock:Mutex = new Mutex();
	#end
	static var loaded:Bool = false;
	static var files:Map<String, MpCachedFile> = new Map();
	static var hashes:Map<String, {size:Float, mtime:Float, sha:String}> = new Map();
	static var incoming:Map<String, {output:FileOutput, size:Int, written:Int}> = new Map();

	public static function isHash(value:String):Bool
		return value != null && ~/^[0-9a-f]{64}$/.match(value);

	public static function filePath(sha:String):String {
		if (!isHash(sha))
			throw 'not a sha256: ' + sha;
		return ROOT + '/files/' + sha.substr(0, 2) + '/' + sha;
	}

	static function load():Void {
		if (loaded)
			return;
		loaded = true;
		#if sys
		var path = ROOT + '/index.json';
		if (!FileSystem.exists(path))
			return;
		var data:Dynamic = null;
		try data = Json.parse(File.getContent(path)) catch (_:Dynamic) {}
		if (data == null)
			return;
		if (data.files != null)
			for (sha in Reflect.fields(data.files))
				if (isHash(sha))
					files.set(sha, Reflect.field(data.files, sha));
		if (data.hashes != null)
			for (relative in Reflect.fields(data.hashes))
				hashes.set(relative, Reflect.field(data.hashes, relative));
		#end
	}

	static function save():Void {
		#if sys
		FileSystem.createDirectory(ROOT);
		var fileData:Dynamic = {};
		for (sha in files.keys())
			Reflect.setField(fileData, sha, files.get(sha));
		var hashData:Dynamic = {};
		for (relative in hashes.keys())
			Reflect.setField(hashData, relative, hashes.get(relative));
		var temp = ROOT + '/index.json.tmp';
		File.saveContent(temp, Json.stringify({files: fileData, hashes: hashData}));
		if (FileSystem.exists(ROOT + '/index.json'))
			FileSystem.deleteFile(ROOT + '/index.json');
		FileSystem.rename(temp, ROOT + '/index.json');
		#end
	}

	public static function has(sha:String):Bool {
		#if sys
		lock.acquire();
		load();
		var known = files.exists(sha) && FileSystem.exists(filePath(sha));
		lock.release();
		return known;
		#else
		return false;
		#end
	}

	/** sha256 of a runtime file, read again only when its size or time changed. Worker threads only. */
	public static function hashOf(relative:String):String {
		#if sys
		var stat = FileSystem.stat(relative);
		var size = stat.size * 1.0;
		var mtime = stat.mtime.getTime();
		lock.acquire();
		load();
		var known = hashes.get(relative);
		lock.release();
		if (known != null && known.size == size && known.mtime == mtime)
			return known.sha;
		var sha = sha256File(relative);
		lock.acquire();
		hashes.set(relative, {size: size, mtime: mtime, sha: sha});
		lock.release();
		return sha;
		#else
		throw 'unsupported';
		#end
	}

	/** Stream a file through SHA-256 without holding all of it. */
	public static function sha256File(path:String):String {
		#if sys
		var input = File.read(path, true);
		var hasher = new MpSha256();
		var buffer = Bytes.alloc(CHUNK);
		try {
			while (true) {
				var read = input.readBytes(buffer, 0, CHUNK);
				if (read <= 0)
					break;
				hasher.update(buffer, 0, read);
			}
		} catch (_:haxe.io.Eof) {}
		input.close();
		return hasher.digestHex();
		#else
		throw 'unsupported';
		#end
	}

	public static function flush():Void {
		#if sys
		lock.acquire();
		load();
		save();
		lock.release();
		#end
	}

	// ------------------------------------------------------------------ receiving

	public static function begin(sha:String, size:Int):Void {
		#if sys
		abort(sha);
		var path = filePath(sha);
		FileSystem.createDirectory(haxe.io.Path.directory(path));
		incoming.set(sha, {output: File.write(path + '.part', true), size: size, written: 0});
		#end
	}

	/** Append a chunk at `offset`; returns true once the whole file has arrived and checked out. */
	public static function write(sha:String, offset:Int, payload:Bytes, start:Int, length:Int):Bool {
		#if sys
		var entry = incoming.get(sha);
		if (entry == null || offset != entry.written || entry.written + length > entry.size)
			throw 'unexpected chunk for ' + sha;
		entry.output.writeBytes(payload, start, length);
		entry.written += length;
		if (entry.written < entry.size)
			return false;
		entry.output.close();
		incoming.remove(sha);
		var path = filePath(sha);
		if (sha256File(path + '.part') != sha) {
			FileSystem.deleteFile(path + '.part');
			throw 'hash mismatch for ' + sha;
		}
		if (FileSystem.exists(path))
			FileSystem.deleteFile(path);
		FileSystem.rename(path + '.part', path);
		lock.acquire();
		load();
		files.set(sha, {size: entry.size, used: Date.now().getTime()});
		lock.release();
		return true;
		#else
		return false;
		#end
	}

	public static function abort(sha:String):Void {
		#if sys
		var entry = incoming.get(sha);
		if (entry == null)
			return;
		entry.output.close();
		incoming.remove(sha);
		var part = filePath(sha) + '.part';
		if (FileSystem.exists(part))
			FileSystem.deleteFile(part);
		#end
	}

	public static function touch(shas:Array<String>):Void {
		#if sys
		lock.acquire();
		load();
		var now = Date.now().getTime();
		for (sha in shas) {
			var entry = files.get(sha);
			if (entry != null)
				entry.used = now;
		}
		lock.release();
		#end
	}

	/** Drop least recently used files until the cache fits `limit` bytes, keeping `keep`. */
	public static function evict(limit:Float, ?keep:Array<String>):Void {
		#if sys
		lock.acquire();
		load();
		var total = 0.0;
		for (entry in files)
			total += entry.size;
		var order = [for (sha in files.keys()) sha];
		order.sort(function(a, b) return files.get(a).used < files.get(b).used ? -1 : 1);
		for (sha in order) {
			if (total <= limit)
				break;
			if (keep != null && keep.indexOf(sha) >= 0)
				continue;
			var path = filePath(sha);
			if (FileSystem.exists(path))
				FileSystem.deleteFile(path);
			total -= files.get(sha).size;
			files.remove(sha);
		}
		save();
		lock.release();
		#end
	}

	// ------------------------------------------------------------------ what songs read

	static function songKey(folder:String):String
		return ROOT + '/songs/' + haxe.crypto.Sha256.make(Bytes.ofString(folder.toLowerCase())).toHex().substr(0, 32) + '.json';

	public static function rememberSongFiles(folder:String, paths:Array<String>):Void {
		#if sys
		FileSystem.createDirectory(ROOT + '/songs');
		File.saveContent(songKey(folder), Json.stringify({folder: folder, paths: paths}));
		#end
	}

	public static function songFiles(folder:String):Array<String> {
		#if sys
		var path = songKey(folder);
		if (!FileSystem.exists(path))
			return [];
		try {
			var data:Dynamic = Json.parse(File.getContent(path));
			var paths:Array<String> = data.paths;
			return paths == null ? [] : paths;
		} catch (_:Dynamic) {
			return [];
		}
		#else
		return [];
		#end
	}
}
