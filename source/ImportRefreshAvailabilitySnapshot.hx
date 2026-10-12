package;

/** One provisional song discovered by an import or retained-source refresh.
 * `name` is the source identifier/display string, not a registry storage key.
 * The opaque key is stable for this scan from its source path metadata. */
typedef ImportRefreshPendingSong = {
	var key:String;
	var name:String;
	var ownerRoot:String;
	var sourceRoot:String;
	@:optional var sourceFolder:String;
	/** Present only when the scan/converter has supplied the destination folder. */
	@:optional var destinationFolder:String;
}

/** Immutable, revisioned view of owner-scoped importer availability. */
typedef ImportRefreshAvailabilitySnapshot = {
	var revision:Int;
	var inspectionPending:Bool;
	var pendingOwnerRoots:Array<String>;
	var handoffPendingOwnerRoots:Array<String>;
	var committedOwnerRoots:Array<String>;
	var pendingTouchedPaths:Array<String>;
	/** Read-only overlap index shared by copies of this immutable revision. */
	@:optional var pendingPathIndex:ImportRefreshPathIndex;
	var pendingSongs:Array<ImportRefreshPendingSong>;
}

/** A detached, normalized path index. No filesystem queries or process-wide cache.
 * A fresh availability revision owns a fresh index; older views stay unchanged. */
class ImportRefreshPathIndex {
	final paths:Array<String>;

	public function new(touched:Array<String>) {
		var unique:Map<String, Bool> = new Map();
		paths = [];
		var ordered = true;
		if (touched != null) for (path in touched) {
			var normalized = normalizePath(path);
			if (normalized == '' || unique.exists(normalized)) continue;
			unique.set(normalized, true);
			if (paths.length > 0 && Reflect.compare(paths[paths.length - 1], normalized) > 0)
				ordered = false;
			paths.push(normalized);
		}
		// Manager snapshots are already sorted. Normalization can change their
		// order, so verify it before avoiding a second sort of the same paths.
		if (!ordered) paths.sort(Reflect.compare);
	}

	public function touches(scopePath:String):Bool {
		var scope = normalizePath(scopePath);
		if (scope == '') return false;
		var exact = lowerBound(scope);
		if (exact < paths.length && paths[exact] == scope) return true;
		// Searching scope alone is insufficient: a sibling such as song-extra
		// can sort before song/chart.json and must not mask the real descendant.
		var prefix = scope + '/';
		var child = lowerBound(prefix);
		return child < paths.length && StringTools.startsWith(paths[child], prefix);
	}

	function lowerBound(value:String):Int {
		var low = 0;
		var high = paths.length;
		while (low < high) {
			var middle = low + ((high - low) >> 1);
			if (Reflect.compare(paths[middle], value) < 0) low = middle + 1;
			else high = middle;
		}
		return low;
	}

	public static function normalizePath(value:String):String {
		if (value == null)
			return '';
		var path = StringTools.trim(value);
		if (path.indexOf('\\') >= 0) path = StringTools.replace(path, '\\', '/');
		while (path.indexOf('//') >= 0)
			path = StringTools.replace(path, '//', '/');
		while (path.length > 0 && path.charAt(path.length - 1) == '/')
			path = path.substr(0, path.length - 1);
		#if windows
		path = path.toLowerCase();
		#end
		return path;
	}

}
