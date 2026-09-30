package;

import haxe.io.Path;

using StringTools;

typedef CodenameModStateResolution = {
	var path:String;
	var ambiguous:Bool;
}

/** Resolve a bare imported state constructor within one owner's catalog.
	The owner boundary is supplied by the caller; this helper prefers the
	current script's sibling directory and refuses ambiguous owner-wide names.
*/
class CodenameModStateResolver {
	public static function resolve(statePaths:Array<String>, name:String,
		sourcePath:String):CodenameModStateResolution {
		var result:CodenameModStateResolution = {path:'', ambiguous:false};
		if (statePaths == null || name == null) return result;
		var requested = StringTools.trim(StringTools.replace(name, '\\', '/'));
		if (requested == '') return result;
		var hasExtension = requested.toLowerCase().endsWith('.hx');
		var hasPath = requested.indexOf('/') >= 0 || hasExtension;
		if (hasPath) {
			var explicit = matchingPath(statePaths, requested);
			if (explicit.length == 1) {
				result.path = explicit[0];
				return result;
			}
			if (explicit.length > 1) result.ambiguous = true;
			// A path-qualified request must never silently degrade to a basename
			// match elsewhere in the owner.
			return result;
		}

		if (requested.indexOf('.') >= 0) {
			var qualified = StringTools.replace(requested, '.', '/');
			if (StringTools.startsWith(qualified.toLowerCase(), 'data/states/'))
				qualified = qualified.substr('data/states/'.length);
			var qualifiedMatches:Array<String> = [];
			for (path in statePaths) {
				if (path == null || path == '') continue;
				var relative = normalizeRelative(path);
				var statePrefix = 'data/states/';
				if (StringTools.startsWith(relative, statePrefix)) relative = relative.substr(statePrefix.length);
				if (relative == normalizeRelative(qualified) && qualifiedMatches.indexOf(path) < 0)
					qualifiedMatches.push(path);
			}
			if (qualifiedMatches.length == 1) result.path = qualifiedMatches[0];
			else if (qualifiedMatches.length > 1) result.ambiguous = true;
			return result;
		}

		var basename = requested;
		var dot = basename.lastIndexOf('.');
		if (dot > 0) basename = basename.substr(0, dot);

		var matches:Array<String> = [];
		for (path in statePaths) {
			if (path == null || path == '') continue;
			if (Path.withoutExtension(Path.withoutDirectory(path)).toLowerCase() == basename.toLowerCase())
				if (matches.indexOf(path) < 0) matches.push(path);
		}
		if (matches.length == 0) return result;
		if (matches.length == 1) {
			result.path = matches[0];
			return result;
		}

		var source = normalizeRelative(sourcePath == null ? '' : sourcePath);
		var sourceDirectory = source == '' ? '' : Path.directory(source);
		if (sourceDirectory != null && sourceDirectory != '') {
			var siblings:Array<String> = [];
			for (path in matches)
				if (Path.directory(normalizeRelative(path)) == sourceDirectory) siblings.push(path);
			if (siblings.length == 1) {
				result.path = siblings[0];
				return result;
			}
			if (siblings.length > 1) {
				result.ambiguous = true;
				return result;
			}
		}
		result.ambiguous = true;
		return result;
	}

	static function matchingPath(statePaths:Array<String>, requested:String):Array<String> {
		var result:Array<String> = [];
		var wanted = normalizeRelative(requested);
		var withoutStateRoot = wanted;
		if (StringTools.startsWith(withoutStateRoot, 'data/states/'))
			withoutStateRoot = withoutStateRoot.substr('data/states/'.length);
		for (path in statePaths) {
			if (path == null || path == '') continue;
			var normalized = normalizeRelative(path);
			var relative = normalized;
			if (StringTools.startsWith(relative, 'data/states/'))
				relative = relative.substr('data/states/'.length);
			if ((normalized == wanted || relative == withoutStateRoot)
				&& result.indexOf(path) < 0) result.push(path);
		}
		return result;
	}

	static function normalizeRelative(value:String):String {
		if (value == null) return '';
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		while (StringTools.startsWith(clean, './')) clean = clean.substr(2);
		if (clean.toLowerCase().endsWith('.hx')) clean = clean.substr(0, clean.length - 3);
		return clean.toLowerCase();
	}
}
