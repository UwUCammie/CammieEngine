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

	/** Locate only owner media. Native fallback remains the caller's decision. */
	public static function resolve(owner:String, id:String):PsychOwnerAssetPathResult {
		var clean = cleanId(id);
		if (clean == null) return result(null, false, true, false);
		var rootKey = owner.toLowerCase();
		var lower = clean.toLowerCase();
		if (lower.startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/')) {
			if (rootKey == '' || (lower != rootKey && !lower.startsWith(rootKey + '/')))
				return result(null, false, true, false);
			var ownPath = FNFAssets.resolveCaseInsensitivePath(clean);
			if (ownPath == null) return result(clean, false, false, true);
			if (!withinOwner(owner, ownPath)) return result(null, false, true, false);
			return result(ownPath, true, false, false);
		}
		if (owner != '') {
			var relative = lower.startsWith('assets/') ? clean.substr('assets/'.length) : clean;
			var candidate = Path.normalize(Path.join([owner, relative]));
			if (candidate != owner && candidate.startsWith(owner + '/')) {
				var ownerPath = FNFAssets.resolveCaseInsensitivePath(candidate);
				if (ownerPath != null) {
					if (!withinOwner(owner, ownerPath)) return result(null, false, true, false);
					return result(ownerPath, true, false, false);
				}
			}
		}
		return result(null, false, false, false);
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

	static function result(path:String, owned:Bool, blocked:Bool, unavailable:Bool):PsychOwnerAssetPathResult {
		return {path:path, owned:owned, blocked:blocked, unavailable:unavailable};
	}
}
