package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
using StringTools;

/** Relative file keys used by an imported HXC Paths proxy. */
class HxcOwnedPath {
	/** Map V-Slice's `songs/<id>/<file>` text keys to the imported owner tree.
		Paths.txt appends `.txt` when the authored key has no extension. */
	public static function songDataRelative(key:String):String {
		if (key == null)
			return null;
		var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		if (clean.startsWith('/') || clean.indexOf(':') >= 0 || clean.indexOf(String.fromCharCode(0)) >= 0)
			return null;
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean.toLowerCase().startsWith('data/'))
			clean = clean.substr('data/'.length);
		if (!clean.toLowerCase().startsWith('songs/'))
			return null;
		var parts = clean.split('/');
		if (parts.length < 3)
			return null;
		for (part in parts)
			if (part == '' || part == '.' || part == '..')
				return null;
		if (haxe.io.Path.extension(parts[parts.length - 1]) == '')
			parts[parts.length - 1] += '.txt';
		return 'data/' + parts.join('/');
	}

	/** Resolve a V-Slice song-data key only within its selected imported owner. */
	public static function existingSongDataFile(root:String, key:String):String {
		var relative = songDataRelative(key);
		return relative == null ? null : existing(root, relative);
	}

	public static function candidate(root:String, key:String):String {
		if (root == null || StringTools.trim(root) == '' || key == null) return null;
		var clean = StringTools.replace(StringTools.trim(key), '\\', '/');
		if (clean.startsWith('/') || clean.indexOf(':') >= 0 || clean.indexOf(String.fromCharCode(0)) >= 0)
			return null;
		while (clean.startsWith('./')) clean = clean.substr(2);
		if (clean.toLowerCase().startsWith('assets/')) clean = clean.substr('assets/'.length);
		if (clean == '') return null;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..') return null;
		var base = Path.normalize(root);
		var path = Path.normalize(Path.join([base, clean]));
		return path.startsWith(base + '/') ? path : null;
	}

	public static function existing(root:String, key:String):String {
		#if sys
		var path = candidate(root, key);
		if (path == null || !FileSystem.exists(path) || FileSystem.isDirectory(path)) return null;
		try {
			var base = Path.normalize(FileSystem.fullPath(root));
			var full = Path.normalize(FileSystem.fullPath(path));
			return full.startsWith(base + '/') ? path : null;
		} catch (_:Dynamic) {
			return null;
		}
		#else
		return null;
		#end
	}

	/** Resolve one file inside the selected owner, retaining its safe candidate
		when it is missing so callers can report the source dependency. An
		existing symlink or directory that fails the owner check is rejected. */
	public static function scoped(root:String, key:String):String {
		var path = candidate(root, key);
		if (path == null)
			return null;
		var found = existing(root, key);
		if (found != null)
			return found;
		#if sys
		if (FileSystem.exists(path))
			return null;
		#end
		return path;
	}
}
