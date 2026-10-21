package multiplayer;

import haxe.Json;
#if sys
import sys.FileSystem;
#end

typedef MpPackageFile = {
	var path:String;
	var size:Int;
	var sha256:String;
}

typedef MpPackageManifest = {
	var files:Array<MpPackageFile>;
	var total:Int;
	var id:String;
}

/** What a song is sent as: the runtime files it needs, by path, size and content hash.
 * The rules match the server (cammie_mp.check_manifest) exactly. */
class MpPackage {
	public static inline var MAX_TOTAL:Int = 250 * 1024 * 1024;
	public static inline var MAX_FILES:Int = 4096;
	static final EXTENSIONS:Array<String> = ['json', 'jsonc', 'txt', 'xml', 'png', 'ogg', 'wav', 'mp3', 'mp4', 'webm', 'ttf', 'otf',
		'frag', 'vert', 'hx', 'hxs', 'hscript', 'lua', 'fnt'];
	static final RESERVED:Array<String> = ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7',
		'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'];

	public static function validPath(path:String):Bool {
		if (path == null || path.length == 0 || path.length > 240 || !StringTools.startsWith(path, 'assets/'))
			return false;
		if (path.indexOf('\\') >= 0 || path.indexOf(':') >= 0 || StringTools.startsWith(path, '/'))
			return false;
		for (i in 0...path.length) {
			var code = path.charCodeAt(i);
			if (code < 32 || code == 127)
				return false;
		}
		for (part in path.split('/')) {
			if (part == '' || part == '.' || part == '..')
				return false;
			if (StringTools.endsWith(part, ' ') || StringTools.endsWith(part, '.'))
				return false;
			if (RESERVED.indexOf(part.split('.')[0].toLowerCase()) >= 0)
				return false;
		}
		var name = path.substr(path.lastIndexOf('/') + 1);
		var dot = name.lastIndexOf('.');
		return dot > 0 && EXTENSIONS.indexOf(name.substr(dot + 1).toLowerCase()) >= 0;
	}

	/** Canonical JSON of the file list, the text its id hashes. */
	public static function canonical(files:Array<MpPackageFile>):String {
		var parts = [for (file in files) '{"path":' + Json.stringify(file.path) + ',"size":' + file.size + ',"sha256":"' + file.sha256 + '"}'];
		return '[' + parts.join(',') + ']';
	}

	public static function make(files:Array<MpPackageFile>):MpPackageManifest {
		var sorted = files.copy();
		sorted.sort(function(a, b) return a.path < b.path ? -1 : (a.path > b.path ? 1 : 0));
		var unique = new Map<String, Int>();
		for (file in sorted)
			unique.set(file.sha256, file.size);
		var total = 0;
		for (size in unique)
			total += size;
		return {files: sorted, total: total, id: haxe.crypto.Sha256.make(haxe.io.Bytes.ofString(canonical(sorted))).toHex()};
	}

	/** Why a received manifest is unacceptable, or null when it is fine. */
	public static function problem(manifest:Dynamic):Null<String> {
		if (manifest == null || !Std.isOfType(manifest.files, Array))
			return 'bad manifest';
		var files:Array<Dynamic> = manifest.files;
		if (files.length == 0 || files.length > MAX_FILES)
			return 'too many files';
		var seen = new Map<String, Bool>();
		var list:Array<MpPackageFile> = [];
		var previous = '';
		for (entry in files) {
			if (entry == null || !Std.isOfType(entry.path, String) || !validPath(entry.path))
				return 'unsafe path';
			var lower = (entry.path:String).toLowerCase();
			if (seen.exists(lower) || entry.path <= previous && list.length > 0)
				return 'unsorted or duplicate path';
			if (!Std.isOfType(entry.size, Int) || entry.size < 0 || entry.size > MAX_TOTAL || !MpCache.isHash(entry.sha256))
				return 'bad file entry';
			seen.set(lower, true);
			previous = entry.path;
			list.push({path: entry.path, size: entry.size, sha256: entry.sha256});
		}
		var made = make(list);
		if (made.total > MAX_TOTAL || manifest.total != made.total)
			return 'too large';
		if (manifest.id != made.id)
			return 'id mismatch';
		return null;
	}

	#if sys
	/** The files a song needs, for a host to send. `folders` are the chart's data folder and the
	 * song's storage folder (its audio), which differ when the chart names another song.
	 * Worker threads only (it hashes files). */
	public static function build(folders:Array<String>, chartPath:String):{manifest:MpPackageManifest, chartSha:String, scripted:Bool} {
		var paths = new Map<String, String>();
		for (songFolder in folders) {
			var folder = songFolder.toLowerCase();
			for (root in ['assets/data/' + folder, 'assets/songs/' + songFolder, 'assets/songs/' + folder])
				collect(root, paths);
			for (path in MpCache.songFiles(songFolder))
				paths.set(path.toLowerCase(), path);
		}
		paths.set(chartPath.toLowerCase(), chartPath);
		var files:Array<MpPackageFile> = [];
		var scripted = false;
		for (path in paths) {
			if (!validPath(path) || !FileSystem.exists(path) || FileSystem.isDirectory(path))
				continue;
			var size = Std.int(FileSystem.stat(path).size);
			if (size > MAX_TOTAL)
				continue;
			var lower = path.toLowerCase();
			if (StringTools.endsWith(lower, '.hscript') || StringTools.endsWith(lower, '.hx') || StringTools.endsWith(lower, '.hxs')
				|| StringTools.endsWith(lower, '.lua'))
				scripted = true;
			files.push({path: path, size: size, sha256: MpCache.hashOf(path)});
			if (files.length > MAX_FILES)
				throw 'This song has too many files to share.';
		}
		MpCache.flush();
		var manifest = make(files);
		if (manifest.total > MAX_TOTAL)
			throw 'This song is too large to share (over 250 MB).';
		return {manifest: manifest, chartSha: MpCache.hashOf(chartPath), scripted: scripted};
	}

	static function collect(root:String, into:Map<String, String>):Void {
		if (!FileSystem.exists(root) || !FileSystem.isDirectory(root))
			return;
		for (name in FileSystem.readDirectory(root)) {
			var path = root + '/' + name;
			if (FileSystem.isDirectory(path))
				collect(path, into);
			else
				into.set(path.toLowerCase(), path);
		}
	}
	#end
}
