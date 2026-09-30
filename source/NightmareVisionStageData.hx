package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** Owner-scoped StageData lookup used by Nightmare Vision gameplay. */
class NightmareVisionStageData {
	/**
		Load the selected stage JSON from its retained owner package. The lookup
		order matches Nightmare Vision's StageData.getStageFile(): data/stages
		before stages, and each directory form before its flat JSON form.
	*/
	public static function load(ownerRoot:String, stageId:String):Dynamic {
		return getStageFile(ownerRoot, stageId);
	}

	/** Return the authored stage object, or null when no owner-local file exists. */
	public static function getStageFile(ownerRoot:String, stageId:String,
		?parseJson:String->Dynamic):Dynamic {
		var stage = normalizeStageId(stageId);
		if (stage == '') return null;
		var path = getStageFromDir(ownerRoot, 'data/stages', stage);
		if (path == null) path = getStageFromDir(ownerRoot, 'stages', stage);
		if (path == null) return null;
		if (parseJson == null) parseJson = CoolUtil.parseJson;
		#if sys
		return parseJson(File.getContent(path));
		#else
		return null;
		#end
	}

	/**
		Resolve one source StageData directory using its two candidate forms:
		`<dir>/<stage>/data.json`, followed by `<dir>/<stage>.json`.
		The returned path is absolute and must resolve inside ownerRoot.
	*/
	public static function getStageFromDir(ownerRoot:String, directory:String,
		stageId:String):Null<String> {
		var stage = normalizeStageId(stageId);
		var base = normalizeRelative(directory);
		if (stage == '' || base == '') return null;
		var path = resolveWithCore(ownerRoot, base + '/' + stage + '/data.json');
		if (path != null) return path;
		return resolveWithCore(ownerRoot, base + '/' + stage + '.json');
	}

	static function resolveWithCore(ownerRoot:String, relative:String):Null<String> {
		var path = resolveExactFile(ownerRoot, relative);
		// Paths.getPath checks the owner then its core dependency for each
		// candidate, before StageData tries the next candidate spelling.
		return path != null ? path : resolveExactFile(ownerRoot, '__nmv_core/' + relative);
	}

	/** Nightmare Vision's exact StageData template, kept separate from authored data. */
	public static function getTemplateStageFile():Dynamic {
		return {
			defaultZoom: 0.8,
			boyfriend: [500, 100],
			girlfriend: [0, 100],
			opponent: [-500, 100],
			hide_girlfriend: false,
			camera_boyfriend: [0, 0],
			camera_opponent: [0, 0],
			camera_girlfriend: [0, 0],
			camera_speed: 1
		};
	}

	/** Keep source spelling and nesting; reject paths that can leave the owner. */
	public static function normalizeStageId(stageId:String):String {
		return normalizeRelative(stageId == null ? '' : stageId.trim());
	}

	static function normalizeRelative(value:String):String {
		if (value == null || value == '' || value.startsWith('/') || value.indexOf('\\') >= 0)
			return '';
		var parts = value.split('/');
		for (part in parts)
			if (part == '' || part == '.' || part == '..' || part.indexOf(':') >= 0)
				return '';
		return parts.join('/');
	}

	static function resolveExactFile(ownerRoot:String, relative:String):Null<String> {
		#if sys
		var clean = normalizeRelative(relative);
		if (clean == '' || ownerRoot == null || ownerRoot.trim() == '') return null;
		try {
			var root = Path.normalize(FileSystem.fullPath(ownerRoot));
			if (!FileSystem.isDirectory(root)) return null;
			var current = root;
			var parts = clean.split('/');
			for (i in 0...parts.length) {
				current = Path.join([current, parts[i]]);
				if (!FileSystem.exists(current) || !withinRoot(root, current)) return null;
				if (i < parts.length - 1 && !FileSystem.isDirectory(current)) return null;
				if (i == parts.length - 1 && FileSystem.isDirectory(current)) return null;
			}
			return current;
		} catch (_:Dynamic) {
			return null;
		}
		#else
		return null;
		#end
	}

	#if sys
	static function withinRoot(root:String, path:String):Bool {
		try {
			var base = Path.normalize(FileSystem.fullPath(root));
			var candidate = Path.normalize(FileSystem.fullPath(path));
			var prefix = base.endsWith('/') ? base : base + '/';
			return candidate == base || candidate.startsWith(prefix);
		} catch (_:Dynamic) {
			return false;
		}
	}
	#end
}
