package;

import haxe.io.Path;
import sys.FileSystem;

using StringTools;

/** Path canonicalization shared by the overlay planner, transaction, and resolver. */
class ImportOverlayPath {
	/**
		Return a normalized absolute path even when its final components do not
		exist. Hxcpp's FileSystem.fullPath returns null for missing paths, so first
		resolve the longest existing prefix and append the remaining components.
		Trying each original prefix before normalizing preserves symlink/`..`
		semantics and keeps containment checks aware of symlink ancestors.
	*/
	public static function canonicalPath(value:String):String {
		if (value == null || StringTools.trim(value) == '')
			return '';

		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		var absolute:String;
		try {
			if (Path.isAbsolute(clean)) {
				absolute = clean;
			} else {
				var cwd = StringTools.replace(FileSystem.fullPath(Sys.getCwd()), '\\', '/');
				absolute = (cwd.endsWith('/') ? cwd : cwd + '/') + clean;
			}
		} catch (_:Dynamic) {
			absolute = clean;
		}
		if (absolute == null || absolute == '')
			return '';

		var candidate = absolute;
		var missing:Array<String> = [];
		while (candidate != null && candidate != '') {
			var resolved:String = null;
			try {
				resolved = FileSystem.fullPath(candidate);
			} catch (_:Dynamic) {}
			if (resolved != null && resolved != '') {
				resolved = StringTools.replace(resolved, '\\', '/');
				if (missing.length > 0)
					resolved = Path.join([resolved, missing.join('/')]);
				return Path.normalize(resolved);
			}

			var parent = Path.directory(candidate);
			var name = Path.withoutDirectory(candidate);
			if (name == null || name == '') {
				var trimmed = Path.removeTrailingSlashes(candidate);
				if (trimmed == candidate || trimmed == '')
					break;
				candidate = trimmed;
				continue;
			}
			if (parent == null || parent == '' || parent == candidate)
				break;
			missing.unshift(name);
			candidate = parent;
		}

		return Path.normalize(absolute);
	}

	/** Check containment after resolving every existing ancestor on both paths. */
	public static function withinRoot(root:String, child:String):Bool {
		var rootPath = canonicalPath(root);
		var childPath = canonicalPath(child);
		if (rootPath == '' || childPath == '')
			return false;
		if (rootPath == childPath)
			return true;
		var prefix = rootPath.endsWith('/') ? rootPath : rootPath + '/';
		return childPath.startsWith(prefix);
	}
}
