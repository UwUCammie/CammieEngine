package multiplayer;

/**
	A read-only view of another player's song files on top of the runtime folder, active
	only while that multiplayer song plays.

	`files` maps a runtime-relative path such as "assets/songs/x/Inst.ogg" to the cached
	file that holds it (mpcache/files/aa/<sha256>). Every read in the engine resolves through
	here first (FNFAssets.resolveDiskPath and the native sys.FileSystem / sys.io.File in
	source-native), so charts, audio, images, registries and scripts all come from the
	package, and nothing is ever written into the player's library. When the overlay is off
	the cost is one boolean test per file access.

	The same hook records which files a song reads on the host, which is what its package
	is built from (see MpPackage).
**/
class MpOverlay {
	public static var active(default, null):Bool = false;
	public static var recording(default, null):Bool = false;
	static var root:String = '';
	static var files:Map<String, String> = new Map();
	/** Directory (lowercase relative) -> child names in their original spelling. */
	static var folders:Map<String, Map<String, String>> = new Map();
	static var recorded:Map<String, String> = new Map();

	/** Mount `entries` (relative path -> absolute cached file) over the runtime folder `runtimeRoot`. */
	public static function mount(runtimeRoot:String, entries:Map<String, String>):Void {
		root = ScriptSandbox.normalize(runtimeRoot);
		files = new Map();
		folders = new Map();
		for (path in entries.keys()) {
			var parts = ScriptSandbox.tidy(path).split('/');
			files.set(parts.join('/').toLowerCase(), entries.get(path));
			// Every folder on the way holds the next part: "" holds "assets", "assets" holds "songs", ...
			for (depth in 0...parts.length) {
				var parent = parts.slice(0, depth).join('/').toLowerCase();
				var children = folders.get(parent);
				if (children == null) {
					children = new Map();
					folders.set(parent, children);
				}
				children.set(parts[depth].toLowerCase(), parts[depth]);
			}
		}
		active = true;
	}

	public static function unmount():Void {
		active = false;
		files = new Map();
		folders = new Map();
	}

	/** Remember every runtime file read until stopRecording(). */
	public static function startRecording(runtimeRoot:String):Void {
		root = ScriptSandbox.normalize(runtimeRoot);
		recorded = new Map();
		recording = true;
	}

	/** The relative paths (original spelling) read since startRecording(), sorted. */
	public static function stopRecording():Array<String> {
		recording = false;
		var paths = [for (path in recorded) path];
		paths.sort(function(a, b) return a < b ? -1 : (a > b ? 1 : 0));
		return paths;
	}

	/** Called on every read: notes it while recording, and returns the cached file when mounted. */
	public static function read(path:String):String {
		if (!active && !recording)
			return path;
		var relative = relativeOf(path);
		if (relative == null)
			return path;
		if (recording && StringTools.startsWith(relative.toLowerCase(), 'assets/'))
			recorded.set(relative.toLowerCase(), relative);
		if (!active)
			return path;
		var cached = files.get(relative.toLowerCase());
		return cached == null ? path : cached;
	}

	/** Whether a path is a mounted file or a folder that holds mounted files. */
	public static function provides(path:String):Bool {
		if (!active)
			return false;
		var relative = relativeOf(path);
		if (relative == null)
			return false;
		var lower = relative.toLowerCase();
		return files.exists(lower) || folders.exists(lower);
	}

	public static function isFolder(path:String):Bool {
		if (!active)
			return false;
		var relative = relativeOf(path);
		return relative != null && folders.exists(relative.toLowerCase());
	}

	/** Mounted children of a folder, merged with what is really there. */
	public static function children(path:String, real:Null<Array<String>>):Array<String> {
		var result = real == null ? [] : real.copy();
		if (!active)
			return result;
		var relative = relativeOf(path);
		var mounted = relative == null ? null : folders.get(relative.toLowerCase());
		if (mounted == null)
			return result;
		var seen = new Map<String, Bool>();
		for (name in result)
			seen.set(name.toLowerCase(), true);
		for (lower in mounted.keys())
			if (!seen.exists(lower))
				result.push(mounted.get(lower));
		return result;
	}

	/** A path relative to the runtime folder in forward slashes, or null when outside it. */
	public static function relativeOf(path:String):Null<String> {
		if (path == null || path == '')
			return null;
		var clean = ScriptSandbox.tidy(path);
		var absolute = StringTools.startsWith(clean, '/') || (clean.length > 1 && clean.charAt(1) == ':');
		if (!absolute)
			return clean == '..' || StringTools.startsWith(clean, '../') ? null : clean;
		var lower = ScriptSandbox.normalize(clean);
		if (!StringTools.startsWith(lower, root + '/'))
			return null;
		return clean.substr(root.length + 1);
	}
}
