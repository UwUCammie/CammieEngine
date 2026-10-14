package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

/**
 * Owner roots and owner-relative files for imported Psych and Nightmare Vision
 * packages. The rules used to be copied into each data loader with small
 * differences; this is the one copy.
 *
 * Containment is checked on the physical path (CompatCanonicalPath), because
 * FileSystem.fullPath is only lexical on Windows and would let a junction
 * inside an owner point anywhere.
 */
class SourceOwnerFiles {
	public static inline var PREFIX:String = 'assets/imported_mods';

	/** Clean an owner root (slashes, trailing slash) or return null when it is
	 * not an installed owner under imported mods. A ':' or NUL is never part of
	 * an installed folder name, so those are refused too. */
	public static function normalizeRoot(value:String):Null<String> {
		if (value == null || value.indexOf(':') >= 0 || value.indexOf(String.fromCharCode(0)) >= 0) return null;
		var path = value.replace('\\', '/');
		while (path.indexOf('//') >= 0) path = path.replace('//', '/');
		while (path.length > PREFIX.length + 1 && path.endsWith('/'))
			path = path.substr(0, path.length - 1);
		if (!path.startsWith(PREFIX + '/') || path.length <= PREFIX.length + 1
			|| path.indexOf('/../') >= 0 || path.endsWith('/..')
			|| path.indexOf('/./') >= 0 || path.endsWith('/.'))
			return null;
		return path;
	}

	/** An owner root read from saved or imported data (score receipts, handoff
	 * keys): surrounding spaces are dropped, then it must pass normalizeRoot.
	 * Anything that is not text is refused. */
	public static function ownerFromData(value:Dynamic):Null<String> {
		if (!Std.isOfType(value, String)) return null;
		return normalizeRoot(StringTools.trim(cast value));
	}

	/** A path relative to an owner, or null when it could leave it: no leading
	 * slash, no backslash, no ':' or NUL, no empty, '.' or '..' segment. */
	public static function cleanRelative(value:String):Null<String> {
		if (value == null || value == '' || value.startsWith('/') || value.indexOf('\\') >= 0
			|| value.indexOf(String.fromCharCode(0)) >= 0)
			return null;
		var parts = value.split('/');
		for (part in parts)
			if (part == '' || part == '.' || part == '..' || part.indexOf(':') >= 0)
				return null;
		return value;
	}

	#if sys
	static var canonicalRoots:Map<String, String> = new Map();
	// Asset lookups ask about the same files again and again; a physical
	// resolve opens a handle on Windows, so answers are remembered. The cap
	// keeps a long session from growing it without bound.
	static var canonicalPaths:Map<String, String> = new Map();
	static var canonicalPathCount:Int = 0;
	static inline var CANONICAL_PATH_CAP:Int = 4096;
	// Import workers run script discovery off the main thread while gameplay
	// resolves assets, so the remembered answers are shared under a lock.
	static final cacheLock:sys.thread.Mutex = new sys.thread.Mutex();

	/** True when `path` exists and physically lies in `root` (or is it, unless
	 * `allowRoot` is false). */
	public static function within(root:String, path:String, allowRoot:Bool = true):Bool {
		if (root == null || path == null || root == '' || path == '') return false;
		try {
			if (!FileSystem.exists(root) || !FileSystem.exists(path)) return false;
			var base = canonicalRoot(root);
			var candidate = canonicalPath(path);
			if (base == null || candidate == null) return false;
			if (candidate == base) return allowRoot;
			return candidate.startsWith(base.endsWith('/') ? base : base + '/');
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Owner roots are checked on every lookup; their physical target is
	 * remembered so each check costs one resolve instead of two. */
	static function canonicalRoot(root:String):Null<String> {
		cacheLock.acquire();
		var known = canonicalRoots.get(root);
		cacheLock.release();
		if (known != null) return known;
		var resolved = CompatCanonicalPath.resolve(root);
		if (resolved != null) {
			cacheLock.acquire();
			canonicalRoots.set(root, resolved);
			cacheLock.release();
		}
		return resolved;
	}

	static function canonicalPath(path:String):Null<String> {
		cacheLock.acquire();
		var known = canonicalPaths.get(path);
		cacheLock.release();
		if (known != null) return known;
		var resolved = CompatCanonicalPath.resolve(path);
		if (resolved == null) return null;
		cacheLock.acquire();
		if (canonicalPathCount >= CANONICAL_PATH_CAP) {
			canonicalPaths.clear();
			canonicalPathCount = 0;
		}
		if (!canonicalPaths.exists(path)) canonicalPathCount++;
		canonicalPaths.set(path, resolved);
		cacheLock.release();
		return resolved;
	}

	/** Forget remembered physical paths, for when files under an owner were
	 * replaced (a re-import) and a junction may now point elsewhere. */
	public static function forgetResolvedPaths():Void {
		cacheLock.acquire();
		canonicalRoots.clear();
		canonicalPaths.clear();
		canonicalPathCount = 0;
		cacheLock.release();
	}

	/** A file under `root`, spelled as it is on disk. */
	public static function resolveFile(root:String, relative:String):Null<String> {
		return resolveEntry(root, relative, false);
	}

	/** A directory under `root`, spelled as it is on disk. */
	public static function resolveDirectory(root:String, relative:String):Null<String> {
		return resolveEntry(root, relative, true);
	}

	/**
	 * Walk `relative` one segment at a time from `root`. An exact name wins;
	 * otherwise a single case-insensitive match is used, so a package made on
	 * Windows still loads where file names are case sensitive. Two names that
	 * only differ by case are ambiguous and resolve to nothing. The result keeps
	 * `root` as given, followed by the on-disk spelling.
	 */
	static function resolveEntry(root:String, relative:String, wantDirectory:Bool):Null<String> {
		var clean = cleanRelative(relative);
		if (clean == null || root == null || root.trim() == '') return null;
		try {
			if (!FileSystem.isDirectory(root)) return null;
			var current = root;
			var parts = clean.split('/');
			for (i in 0...parts.length) {
				var part = parts[i];
				var selected = Path.join([current, part]);
				if (!FileSystem.exists(selected)) {
					var wanted = part.toLowerCase();
					var match:String = null;
					for (entry in FileSystem.readDirectory(current)) {
						if (entry.toLowerCase() != wanted) continue;
						if (match != null) return null;
						match = entry;
					}
					if (match == null) return null;
					selected = Path.join([current, match]);
				}
				if (i < parts.length - 1 && !FileSystem.isDirectory(selected)) return null;
				current = selected;
			}
			if (FileSystem.isDirectory(current) != wantDirectory) return null;
			if (!within(root, current, false)) return null;
			return Path.normalize(current);
		} catch (_:Dynamic) {
			return null;
		}
	}
	#end
}
