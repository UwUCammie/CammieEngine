package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end

using StringTools;

typedef PsychOwnerAssetPathResult = {
	var path:String;
	var owned:Bool;
	var blocked:Bool;
	var unavailable:Bool;
}

/** Shared selected-owner path validation for Psych source asset facades. */
class PsychOwnerAssetPath {
	public static function normalizeOwner(value:String):String {
		if (value == null) return '';
		var owner = Path.normalize(StringTools.replace(StringTools.trim(value), '\\', '/'));
		if (!owner.startsWith(CompatScriptManifest.ROOT_PREFIX + '/'))
			return '';
		#if sys
		if (!FileSystem.isDirectory(owner)) return '';
		#end
		return owner;
	}

	/** Release the small identity-index cache when this selected owner retires. */
	public static function releaseOwner(owner:String):Void {
		RuntimeOwnerAssetIdentity.releaseOwner(owner);
	}

	/** Locate only owner media. Native fallback remains the caller's decision. */
	public static function resolve(owner:String, id:String):PsychOwnerAssetPathResult {
		return resolveInScope(owner, id, owner, '');
	}

	/** Resolve an owner file through an explicit authenticated subtree.
		`pathRoot` must be the owner itself or a descendant. A package can also
		exclude a reserved subtree such as Nightmare Vision's `__nmv_core`. */
	public static function resolveInScope(owner:String, id:String, pathRoot:String,
		excludedSubtree:String = ''):PsychOwnerAssetPathResult {
		var clean = cleanId(id);
		if (clean == null) return result(null, false, true, false);
		var normalizedOwner = normalizeOwner(owner);
		if (normalizedOwner == '') return result(null, false, true, false);
		var normalizedRoot = Path.normalize(StringTools.replace(pathRoot == null || pathRoot == ''
			? normalizedOwner : pathRoot, '\\', '/'));
		if (!pathIsWithin(normalizedOwner, normalizedRoot)) return result(null, false, true, false);
		var rootKey = normalizedOwner.toLowerCase();
		var lower = clean.toLowerCase();
		if (lower.startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/')) {
			if (rootKey == '' || (lower != rootKey && !lower.startsWith(rootKey + '/')))
				return result(null, false, true, false);
			var ownPath = FNFAssets.resolveCaseInsensitivePath(clean);
			var requestedPath = Path.normalize(clean);
			if (!pathIsWithin(normalizedRoot, requestedPath)
				|| isExcludedPath(normalizedOwner, requestedPath, excludedSubtree))
				return result(null, false, true, false);
			if (ownPath == null) return result(clean, false, false, true);
			if (!withinOwner(normalizedOwner, ownPath) || !withinOwner(normalizedRoot, ownPath)
				|| isExcludedPath(normalizedOwner, ownPath, excludedSubtree))
				return result(null, false, true, false);
			return result(ownPath, true, false, false);
		}

		var relative = lower.startsWith('assets/') ? clean.substr('assets/'.length) : clean;
		var ownerPrefix = normalizedOwner + '/';
		var rootRelative = normalizedRoot == normalizedOwner ? '' : normalizedRoot.substr(ownerPrefix.length);
		if (rootRelative != '' && (relative.toLowerCase() == rootRelative.toLowerCase()
			|| relative.toLowerCase().startsWith(rootRelative.toLowerCase() + '/')))
			relative = relative.length == rootRelative.length ? '' : relative.substr(rootRelative.length + 1);
		var candidate = Path.normalize(Path.join([normalizedRoot, relative]));
		if (candidate == normalizedRoot || !pathIsWithin(normalizedRoot, candidate)
			|| isExcludedPath(normalizedOwner, candidate, excludedSubtree))
			return result(null, false, true, false);
		var ownerPath = FNFAssets.resolveCaseInsensitivePath(candidate);
		if (ownerPath != null) {
			if (!withinOwner(normalizedOwner, ownerPath) || !withinOwner(normalizedRoot, ownerPath)
				|| isExcludedPath(normalizedOwner, ownerPath, excludedSubtree))
				return result(null, false, true, false);
			return result(ownerPath, true, false, false);
		}
		return result(null, false, false, false);
	}

	/** Confirm that a receipt-indexed physical path belongs to the same
		package/core scope as the source Assets facade. */
	public static function pathInScope(owner:String, path:String, pathRoot:String,
		excludedSubtree:String = ''):Bool {
		var normalizedOwner = normalizeOwner(owner);
		if (normalizedOwner == '' || path == null || path == '') return false;
		var normalizedRoot = Path.normalize(StringTools.replace(pathRoot == null || pathRoot == ''
			? normalizedOwner : pathRoot, '\\', '/'));
		if (!pathIsWithin(normalizedOwner, normalizedRoot) || !pathIsWithin(normalizedOwner, path)) return false;
		if (isExcludedPath(normalizedOwner, path, excludedSubtree)) return false;
		#if sys
		return withinOwner(normalizedOwner, path) && withinOwner(normalizedRoot, path);
		#else
		return true;
		#end
	}

	/** Guard legacy/native fallback paths for owner-bound scripts. Relative
	 * Psych asset ids remain eligible for ordinary shared fallback; an explicit
	 * imported namespace path must resolve to a real file inside this owner. */
	public static function ownerReferenceAllowed(owner:String, reference:String):Bool {
		var clean = cleanId(reference);
		if (clean == null) return false;
		if (!clean.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/'))
			return true;
		var resolved = resolve(owner, clean);
		return resolved != null && resolved.owned && !resolved.blocked && !resolved.unavailable;
	}

	public static function cleanId(value:String):String {
		if (value == null) return null;
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		while (clean.startsWith('./')) clean = clean.substr(2);
		if (clean == '' || clean.indexOf(String.fromCharCode(0)) >= 0 || clean.indexOf(':') >= 0
			|| clean.startsWith('/') || clean.split('/').indexOf('..') >= 0)
			return null;
		return clean;
	}

	public static function withinOwner(owner:String, path:String):Bool {
		#if sys
		if (owner == null || path == null || !FileSystem.exists(owner) || !FileSystem.exists(path))
			return false;
		try {
			var base = Path.normalize(FileSystem.fullPath(owner));
			var candidate = Path.normalize(FileSystem.fullPath(path));
			return candidate.startsWith(base + '/');
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return owner != null && path != null && Path.normalize(path).startsWith(Path.normalize(owner) + '/');
		#end
	}

	static function pathIsWithin(root:String, path:String):Bool {
		if (root == null || root == '' || path == null || path == '') return false;
		var normalizedRoot = Path.normalize(root);
		var normalizedPath = Path.normalize(path);
		var rootKey = normalizedRoot.toLowerCase();
		var pathKey = normalizedPath.toLowerCase();
		return pathKey == rootKey || pathKey.startsWith(rootKey.endsWith('/') ? rootKey : rootKey + '/');
	}

	static function isExcludedPath(owner:String, path:String, excludedSubtree:String):Bool {
		if (excludedSubtree == null || excludedSubtree == '') return false;
		var excluded = Path.normalize(Path.join([owner, excludedSubtree]));
		return pathIsWithin(excluded, path);
	}

	static function result(path:String, owned:Bool, blocked:Bool, unavailable:Bool):PsychOwnerAssetPathResult {
		return {path:path, owned:owned, blocked:blocked, unavailable:unavailable};
	}
}
