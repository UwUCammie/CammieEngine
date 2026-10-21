package multiplayer;

import haxe.io.Bytes;
import multiplayer.MpPackage.MpPackageManifest;
#if sys
import sys.FileSystem;
import sys.io.File;
import sys.thread.Deque;
import sys.thread.Mutex;
import sys.thread.Thread;
#end

/**
	Moving a lobby's song from the host to the players who lack it (protocol section 5).

	The host side answers `want` with each file as `chunk_begin` and 256 KiB binary frames,
	read and sent on a worker thread that waits while more than 4 MiB is queued, so a large
	song never sits in memory. The joiner side decides what it lacks (its own library, then
	the multiplayer cache), asks for it, and writes what arrives on a worker thread, which
	checks every file's sha256 before it enters the cache.
**/
class MpTransfer {
	public static inline var CHUNK:Int = 256 * 1024;
	static inline var QUEUE_LIMIT:Float = 4 * 1024 * 1024;

	/** The chart file of a selection: the package's data file with the chart's hash. */
	public static function chartPathOf(selection:Dynamic):Null<String> {
		if (selection == null || selection.chart_sha256 == null || Reflect.field(selection, 'package') == null)
			return null;
		var files:Array<Dynamic> = Reflect.field(selection, 'package').files;
		for (file in files)
			if (file.sha256 == selection.chart_sha256 && StringTools.startsWith(file.path, 'assets/data/')
				&& StringTools.endsWith(file.path.toLowerCase(), '.json') && file.path.split('/').length == 4)
				return file.path;
		return null;
	}

	// ------------------------------------------------------------------ host

	static var shared:Null<{id:String, paths:Map<String, String>, sizes:Map<String, Int>}> = null;
	#if sys
	static var sendQueue:Deque<{sha:String, generation:Int}> = new Deque();
	static var senderGeneration:Int = -1;
	static var sendGeneration:Int = 0;
	#end

	/** Build the package of a song on a worker thread and hand back its selection
	 * ({title, difficulty, package, chart_sha256, judge, scripted}). */
	public static function share(chartPath:String, title:String, difficulty:String, judge:String,
			done:Dynamic->Void, failed:String->Void):Void {
		var parts = chartPath.split('/');
		var folder = parts.length > 2 ? parts[2] : '';
		MpTasks.run(function() return MpPackage.build(songFolders(folder, chartPath), chartPath), function(built) {
			var paths = new Map<String, String>();
			var sizes = new Map<String, Int>();
			for (file in built.manifest.files) {
				if (!paths.exists(file.sha256))
					paths.set(file.sha256, file.path);
				sizes.set(file.sha256, file.size);
			}
			stopSending();
			shared = {id: built.manifest.id, paths: paths, sizes: sizes};
			done({title: title, difficulty: difficulty, "package": built.manifest, chart_sha256: built.chartSha, judge: judge,
				scripted: built.scripted});
		}, failed);
	}

	/** The chart's data folder and, when the chart names another song, that song's storage folder. */
	static function songFolders(folder:String, chartPath:String):Array<String> {
		var folders = [folder];
		#if sys
		var storage = '';
		try {
			var raw = StringTools.trim(File.getContent(chartPath));
			// Charts can carry trailing junk after the object, as Song.readChart allows.
			raw = raw.substr(0, raw.lastIndexOf('}') + 1);
			var json:Dynamic = haxe.Json.parse(raw);
			var inner:Dynamic = Reflect.field(json, 'song');
			storage = Song.storageFolder(Reflect.isObject(inner) && !Std.isOfType(inner, String) ? inner : json);
		} catch (error:Dynamic) {
			trace('[multiplayer] could not read ' + chartPath + ' for its song folder: ' + error);
		}
		if (storage != '' && folders.indexOf(storage) < 0)
			folders.push(storage);
		#end
		return folders;
	}

	/** The server passed on what players lack; queue those files. */
	public static function answerWant(packageId:String, hashes:Array<String>):Void {
		#if sys
		if (shared == null || shared.id != packageId)
			return;
		var socket = MpClient.get().transferSocket();
		if (socket == null)
			return;
		for (sha in hashes)
			if (shared.paths.exists(sha))
				sendQueue.add({sha: sha, generation: sendGeneration});
		// One sender per shared song; an older one stops at its next item.
		if (senderGeneration != sendGeneration) {
			senderGeneration = sendGeneration;
			var generation = sendGeneration;
			var files = shared;
			Thread.create(function() sendLoop(socket, files, generation));
		}
		#end
	}

	public static function stopSending():Void {
		#if sys
		shared = null;
		sendGeneration++;
		// Wakes a sender waiting for work, so it sees it is no longer current.
		sendQueue.add({sha: '', generation: -1});
		#end
	}

	#if sys
	static function sendLoop(socket:MpSocket, files:{id:String, paths:Map<String, String>, sizes:Map<String, Int>}, generation:Int):Void {
		var buffer = Bytes.alloc(CHUNK);
		while (generation == sendGeneration && !socket.isClosing()) {
			var item = sendQueue.pop(true);
			if (generation != sendGeneration)
				break;
			if (item.generation != generation)
				continue;
			var sha = item.sha;
			var path = files.paths.get(sha);
			var size = files.sizes.get(sha);
			try {
				if (!FileSystem.exists(path) || Std.int(FileSystem.stat(path).size) != size)
					continue;
				socket.sendText(haxe.Json.stringify({t: 'chunk_begin', sha256: sha, size: size}));
				var input = File.read(path, true);
				var offset = 0;
				var digest = Bytes.ofHex(sha);
				while (offset < size && generation == sendGeneration && !socket.isClosing()) {
					var length = input.readBytes(buffer, 0, size - offset < CHUNK ? size - offset : CHUNK);
					if (length <= 0)
						break;
					var frame = Bytes.alloc(40 + length);
					frame.blit(0, digest, 0, 32);
					// Offsets stay under 250 MiB, so the high half of the 8-byte offset is 0.
					frame.setInt32(32, 0);
					frame.set(36, (offset >>> 24) & 255);
					frame.set(37, (offset >>> 16) & 255);
					frame.set(38, (offset >>> 8) & 255);
					frame.set(39, offset & 255);
					frame.blit(40, buffer, 0, length);
					while (socket.queuedBytes() > QUEUE_LIMIT && generation == sendGeneration && !socket.isClosing())
						Sys.sleep(0.01);
					socket.sendBinary(frame);
					offset += length;
				}
				input.close();
			} catch (error:Dynamic) {
				trace('[multiplayer] could not send ' + path + ': ' + error);
			}
		}
	}
	#end

	// ------------------------------------------------------------------ joiner

	/** The song this player is getting, or has, for the current lobby. */
	public static var fetch(default, null):Null<MpFetch> = null;

	/** Start getting a selection's files, unless that package is already being handled. */
	public static function receive(selection:Dynamic):MpFetch {
		var manifest:MpPackageManifest = Reflect.field(selection, 'package');
		if (fetch != null && fetch.manifest.id == manifest.id)
			return fetch;
		if (fetch != null)
			fetch.cancel();
		fetch = new MpFetch(manifest, selection);
		fetch.start();
		return fetch;
	}

	public static function forget():Void {
		if (fetch != null)
			fetch.cancel();
		fetch = null;
	}
}

private enum MpFetchItem {
	Begin(sha:String, size:Int);
	Chunk(frame:Bytes);
	Stop;
}

/** One player's copy of a lobby song: which files come from where, and the download. */
class MpFetch {
	public var manifest(default, null):MpPackageManifest;
	public var selection(default, null):Dynamic;
	/** checking, downloading, ready or failed. */
	public var state(default, null):String = 'checking';
	public var error(default, null):String = '';
	/** Package paths that play from the multiplayer cache, to their cache file. */
	public var mounts(default, null):Map<String, String> = new Map();

	var missing:Map<String, Int> = new Map();
	var retried:Map<String, Bool> = new Map();
	var received:Float = 0;
	var reportedAt:Float = 0;
	var reported:Float = -1;
	var cancelled:Bool = false;
	#if sys
	var items:Deque<MpFetchItem> = new Deque();
	var finished:Deque<{sha:String, ok:Bool, error:String}> = new Deque();
	var progressLock:Mutex = new Mutex();
	/** Bytes of the file being written, kept by the writer thread. */
	var partial:Float = 0;
	#end

	public function new(manifest:MpPackageManifest, selection:Dynamic) {
		this.manifest = manifest;
		this.selection = selection;
	}

	public function needsSandbox():Bool
		return mounts.keys().hasNext();

	public function start():Void {
		var problem = MpPackage.problem(manifest);
		if (problem != null) {
			fail('The song from the host was refused: ' + problem);
			return;
		}
		var files = manifest.files;
		MpTasks.run(function() {
			// For every file: the player's own copy if it is identical, else the cache, else it is missing.
			var mounts = new Map<String, String>();
			var missing = new Map<String, Int>();
			for (file in files) {
				var local = false;
				try local = FileSystem.exists(file.path) && !FileSystem.isDirectory(file.path)
					&& Std.int(FileSystem.stat(file.path).size) == file.size && MpCache.hashOf(file.path) == file.sha256
				catch (_:Dynamic) {}
				if (local)
					continue;
				mounts.set(file.path, absolute(MpCache.filePath(file.sha256)));
				if (!MpCache.has(file.sha256))
					missing.set(file.sha256, file.size);
			}
			MpCache.flush();
			return {mounts: mounts, missing: missing};
		}, function(found) {
			if (cancelled)
				return;
			mounts = found.mounts;
			missing = found.missing;
			var lacking = 0.0;
			for (size in missing)
				lacking += size;
			received = manifest.total - lacking;
			var wanted = [for (sha in missing.keys()) sha];
			if (wanted.length == 0) {
				complete();
				return;
			}
			state = 'downloading';
			MpCache.evict(MpCache.limit() - lacking, [for (file in manifest.files) file.sha256]);
			#if sys
			Thread.create(writeLoop);
			#end
			MpClient.get().send({t: 'want', package_id: manifest.id, sha256: wanted});
			report(true);
		}, function(error) fail('Could not check the song files: ' + error));
	}

	static function absolute(path:String):String {
		#if sys
		return haxe.io.Path.normalize(Sys.getCwd() + '/' + path);
		#else
		return path;
		#end
	}

	public function onChunkBegin(sha:String, size:Int):Void {
		#if sys
		if (state == 'downloading' && missing.exists(sha))
			items.add(Begin(sha, size));
		#end
	}

	public function onBinary(frame:Bytes):Void {
		#if sys
		if (state == 'downloading' && frame.length > 40)
			items.add(Chunk(frame));
		#end
	}

	#if sys
	function writeLoop():Void {
		var current = '';
		while (true) {
			var item = items.pop(true);
			switch (item) {
				case Stop:
					if (current != '')
						MpCache.abort(current);
					return;
				case Begin(sha, size):
					setPartial(0, false);
					try {
						MpCache.begin(sha, size);
						current = sha;
						if (size == 0 && MpCache.write(sha, 0, Bytes.alloc(0), 0, 0)) {
							current = '';
							finished.add({sha: sha, ok: true, error: ''});
						}
					} catch (error:Dynamic) {
						finished.add({sha: sha, ok: false, error: Std.string(error)});
					}
				case Chunk(frame):
					var sha = frame.sub(0, 32).toHex();
					// Big-endian offset; the high half is always 0 under the 250 MiB limit.
					var offset = (frame.get(36) << 24) | (frame.get(37) << 16) | (frame.get(38) << 8) | frame.get(39);
					var length = frame.length - 40;
					try {
						if (MpCache.write(sha, offset, frame, 40, length)) {
							current = '';
							setPartial(0, false);
							finished.add({sha: sha, ok: true, error: ''});
						} else
							setPartial(length, true);
					} catch (error:Dynamic) {
						MpCache.abort(sha);
						current = '';
						setPartial(0, false);
						finished.add({sha: sha, ok: false, error: Std.string(error)});
					}
			}
		}
	}

	function setPartial(value:Float, add:Bool):Void {
		progressLock.acquire();
		partial = add ? partial + value : value;
		progressLock.release();
	}
	#end

	/** Main thread, every frame: settle finished files and report progress. */
	public function update():Void {
		#if sys
		if (state != 'downloading')
			return;
		while (true) {
			var done = finished.pop(false);
			if (done == null)
				break;
			var size = missing.get(done.sha);
			if (size == null)
				continue;
			if (done.ok) {
				missing.remove(done.sha);
				received += size;
			} else if (!retried.exists(done.sha)) {
				// One more try, then the song is unavailable.
				retried.set(done.sha, true);
				MpClient.get().send({t: 'want', package_id: manifest.id, sha256: [done.sha]});
			} else {
				fail('A song file from the host did not arrive intact.');
				MpClient.get().send({t: 'progress', received: Std.int(received), total: manifest.total, complete: false});
				return;
			}
		}
		if (!missing.keys().hasNext()) {
			complete();
			return;
		}
		report(false);
		#end
	}

	/** Bytes the player has of the package, counting the file being written. */
	public function have():Float {
		#if sys
		progressLock.acquire();
		var extra = partial;
		progressLock.release();
		return Math.min(manifest.total, received + Math.max(0, extra));
		#else
		return received;
		#end
	}

	function report(force:Bool):Void {
		var now = haxe.Timer.stamp();
		var value = have();
		if (!force && (now - reportedAt < 0.5 || value == reported))
			return;
		reportedAt = now;
		reported = value;
		MpClient.get().send({t: 'progress', received: Std.int(value), total: manifest.total, complete: false});
	}

	function complete():Void {
		state = 'ready';
		received = manifest.total;
		#if sys
		items.add(Stop);
		#end
		MpCache.touch([for (file in manifest.files) file.sha256]);
		MpCache.flush();
		MpClient.get().send({t: 'progress', received: manifest.total, total: manifest.total, complete: true});
	}

	function fail(message:String):Void {
		state = 'failed';
		error = message;
		#if sys
		items.add(Stop);
		#end
	}

	public function cancel():Void {
		cancelled = true;
		if (state == 'downloading') {
			#if sys
			items.add(Stop);
			#end
		}
		state = 'failed';
	}
}
