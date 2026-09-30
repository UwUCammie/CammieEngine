package;

import haxe.io.Path;
using StringTools;

/** Owner-scoped resolver for media passed to an HXC in-stage video sprite. */
class HxcOwnedVideoPath {
	/**
		Return `{path, error}` where `error` is `rejected` for an invalid/out-of-owner
		key and `missing` for a valid key with no file. Native videos are accepted
		only from `assets/videos`; imported videos must remain under `ownerRoot`.
	*/
	public static function resolve(ownerRoot:String, source:String):Dynamic {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '' || source == null)
			return {path: null, error: 'rejected', detail: 'missing selected media owner or path'};

		var root = StringTools.replace(StringTools.trim(ownerRoot), '\\', '/');
		while (root.endsWith('/')) root = root.substr(0, root.length - 1);
		var key = StringTools.replace(StringTools.trim(source), '\\', '/');
		while (key.startsWith('./')) key = key.substr(2);
		var exactAbsoluteOwner = key == root || key.startsWith(root + '/');
		if (!exactAbsoluteOwner && (key.startsWith('/') || (key.length > 1 && key.charAt(1) == ':'))) {
			var marker = key.lastIndexOf('/assets/videos/');
			if (marker < 0)
				marker = key.lastIndexOf('/assets/imported_mods/');
			if (marker < 0)
				return {path: null, error: 'rejected', detail: 'absolute video path is outside allowed roots: ' + key};
			key = key.substr(marker + 1);
		}
		if (root == '' || key == ''
			|| key.indexOf(String.fromCharCode(0)) >= 0)
			return {path: null, error: 'rejected', detail: 'empty or invalid path ' + key};

		if (key.startsWith('assets/videos/')) {
			var videoKey = key.substr('assets/videos/'.length);
			for (prefix in ['videos/', 'videos/videos/', 'assets/videos/']) {
				var owned = resolveWithin(root, prefix + videoKey, key);
				if (Reflect.field(owned, 'path') != null || Reflect.field(owned, 'error') == 'rejected')
					return owned;
			}
			return resolveWithin('assets/videos', videoKey, key);
		}
		if (key.startsWith('assets/imported_mods/') && key != root && !key.startsWith(root + '/'))
			return {path: null, error: 'rejected', detail: 'video belongs to another import: ' + key};
		if (key.startsWith('assets/') && key != root && !key.startsWith(root + '/'))
			return {path: null, error: 'rejected', detail: 'video path is outside allowed roots: ' + key};

		var relative:String;
		if (key == root)
			relative = '';
		else if (key.startsWith(root + '/'))
			relative = key.substr(root.length + 1);
		else if (key.startsWith('videos/'))
			relative = key;
		else if (key.startsWith('assets/'))
			return {path: null, error: 'rejected', detail: 'video path is outside selected import: ' + key};
		else
			relative = 'videos/' + key;

		if (relative == '')
			return {path: null, error: 'rejected', detail: 'video path names the import root'};
		var owned = resolveWithin(root, relative, key);
		if (Reflect.field(owned, 'path') != null || Reflect.field(owned, 'error') == 'rejected')
			return owned;
		if (relative.startsWith('videos/')) {
			var nested = resolveWithin(root, 'videos/' + relative, key);
			if (Reflect.field(nested, 'path') != null || Reflect.field(nested, 'error') == 'rejected')
				return nested;
		}
		return owned;
	}

	static function resolveWithin(root:String, relative:String, source:String):Dynamic {
		var extension = Path.extension(relative).toLowerCase();
		if (extension == '')
			relative += '.mp4';
		else if (extension != 'mp4' && extension != 'webm' && extension != 'ogv')
			return {path: null, error: 'rejected', detail: 'unsupported video format: ' + source};
		var candidate = HxcOwnedPath.candidate(root, relative);
		if (candidate == null)
			return {path: null, error: 'rejected', detail: 'unsafe video path: ' + source};
		var existing = HxcOwnedPath.existing(root, relative);
		if (existing == null)
			return {path: null, error: 'missing', detail: source};
		return {path: existing, error: null, detail: source};
	}
}
