package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
using StringTools;

/**
	Filesystem-independent HXC layout discovery.  Importers can feed this helper
	a list of candidate paths from any source root and keep chart-local scripts
	separate from global modules/events without opening or modifying donor files.
*/
typedef HxcScriptDiscoveryResult = {
	var all:Array<String>;
	var chart:Array<String>;
	var otherSongs:Array<String>;
	var global:Array<String>;
	var unknown:Array<String>;
	var families:Map<String, Array<String>>;
}

class HxcScriptDiscovery {
	#if sys
	/** Enumerate a copied donor scripts tree with bounded recursion. */
	public static function discoverRoot(root:String, ?songId:String, maxFiles:Int = 4096):HxcScriptDiscoveryResult {
		var paths:Array<String> = [];
		var budget = maxFiles < 1 ? 1 : maxFiles;
		collectRoot(root, paths, budget, 0);
		paths.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		return discover(paths, songId);
	}

	/**
		For one global family, keep the first manifest-owner copy of an identical
		relative path. Distinct paths and other families are retained. Roots must be
		provided in owner-precedence order (native fallback first, then manifest
		roots from highest to lowest priority).
	*/
	public static function preferFamilyPaths(paths:Array<String>, roots:Array<String>, family:String):Array<String> {
		var result:Array<String> = [];
		if (paths == null)
			return result;
		var bestByIdentity:Map<String, {var index:Int; var rootIndex:Int; var path:String;}> = new Map();
		for (path in paths) {
			if (path == null || path == '')
				continue;
			if (familyForPath(path) != family) {
				result.push(path);
				continue;
			}
			var relative = relativePathForRoots(path, roots);
			if (relative == '') {
				result.push(path);
				continue;
			}
			var identity = Path.normalize(relative).replace('\\', '/').toLowerCase();
			var rootIndex = familyRootIndexForPath(path, roots);
			var previous = bestByIdentity.get(identity);
			if (previous == null) {
				bestByIdentity.set(identity, {index: result.length, rootIndex: rootIndex, path: path});
				result.push(path);
			} else if (rootIndex >= 0 && (previous.rootIndex < 0 || rootIndex < previous.rootIndex)) {
				result[previous.index] = path;
				bestByIdentity.set(identity, {index: previous.index, rootIndex: rootIndex, path: path});
			}
		}
		return result;
	}

	static function relativePathForRoots(path:String, roots:Array<String>):String {
		var rootIndex = familyRootIndexForPath(path, roots);
		if (rootIndex < 0 || roots == null || roots[rootIndex] == null)
			return '';
		var fullPath = StringTools.replace(FileSystem.fullPath(path), '\\', '/');
		var fullRoot = StringTools.replace(FileSystem.fullPath(roots[rootIndex]), '\\', '/');
		while (fullRoot.endsWith('/'))
			fullRoot = fullRoot.substr(0, fullRoot.length - 1);
		return fullPath.startsWith(fullRoot + '/') ? fullPath.substr(fullRoot.length + 1) : '';
	}

	static function familyRootIndexForPath(path:String, roots:Array<String>):Int {
		if (path == null || roots == null)
			return -1;
		var fullPath = StringTools.replace(FileSystem.fullPath(path), '\\', '/');
		var bestIndex = -1;
		var bestLength = -1;
		for (index in 0...roots.length) {
			var root = roots[index];
			if (root == null || root == '')
				continue;
			var fullRoot = StringTools.replace(FileSystem.fullPath(root), '\\', '/');
			while (fullRoot.endsWith('/'))
				fullRoot = fullRoot.substr(0, fullRoot.length - 1);
			if (fullPath.startsWith(fullRoot + '/') && fullRoot.length > bestLength) {
				bestIndex = index;
				bestLength = fullRoot.length;
			}
		}
		return bestIndex;
	}

	static function collectRoot(root:String, output:Array<String>, budget:Int, depth:Int):Int {
		if (root == null || root == '' || budget <= 0 || depth > 12 || !FileSystem.isDirectory(root))
			return budget;
		var entries:Array<String>;
		try {
			entries = FileSystem.readDirectory(root);
		} catch (_:Dynamic) {
			return budget;
		}
		entries.sort(function(a, b) return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		for (entry in entries) {
			if (budget <= 0)
				break;
			var child = Path.join([root, entry]);
			if (FileSystem.isDirectory(child))
				budget = collectRoot(child, output, budget, depth + 1);
			else if (entry.toLowerCase().endsWith('.hxc')) {
				output.push(FileSystem.fullPath(child));
				budget--;
			}
		}
		return budget;
	}
	#end

	/** Map the donor directory layout to a stable importer family name. */
	public static function familyForPath(path:String):String {
		if (path == null || path == '')
			return 'unknown';
		var normalized = path.replace('\\', '/').toLowerCase();
		if (!normalized.endsWith('.hxc'))
			return 'unknown';
		var parts = normalized.split('/');
		for (index in 0...parts.length) {
			var part = parts[index];
			switch (part) {
				case 'shaders' | 'shader': return 'shader';
				case 'songs' | 'song-scripts': return 'song';
				case 'stages': return 'stage';
				case 'characters' | 'character': return 'character';
				case 'modules' | 'module': return 'module';
				case 'events' | 'event': return 'event';
				case 'notes' | 'note' | 'notekinds': return 'note';
				case 'states' | 'state': return 'state';
				case 'substates' | 'substate': return 'substate';
				case 'ui': return 'ui';
				case 'cutscenes' | 'cutscene': return 'cutscene';
				default:
			}
		}
		return 'unknown';
	}

	/**
		Partition candidate paths.  Only `scripts/songs/<song>.hxc` is chart-local
		by filename; stages, characters, modules, events, notes, states, UI and
		cutscenes are global donor families selected by their owning runtime.
		State/substate factories inspect the bounded manifest root on demand.
		Non-selected song scripts are kept in `otherSongs`
		instead of being accidentally treated as global.  An empty song id
		intentionally selects every song script, useful for a freeplay/library scan.
	*/
	public static function discover(paths:Array<String>, ?songId:String):HxcScriptDiscoveryResult {
		var all:Array<String> = [];
		var chart:Array<String> = [];
		var otherSongs:Array<String> = [];
		var global:Array<String> = [];
		var unknown:Array<String> = [];
		var families:Map<String, Array<String>> = new Map<String, Array<String>>();
		var chartKey = normalizeToken(songId);
		if (paths != null)
			for (path in paths) {
				if (path == null || path == '' || all.indexOf(path) >= 0)
					continue;
				all.push(path);
				var family = familyForPath(path);
				var familyPaths = families.get(family);
				if (familyPaths == null) {
					familyPaths = [];
					families.set(family, familyPaths);
				}
				familyPaths.push(path);
				if (family == 'song' && (chartKey == '' || normalizeToken(stem(path)) == chartKey))
					chart.push(path);
				else if (family == 'song')
					otherSongs.push(path);
				else if (family == 'unknown')
					unknown.push(path);
				else
					global.push(path);
			}
		return {
			all: all,
			chart: chart,
			otherSongs: otherSongs,
			global: global,
			unknown: unknown,
			families: families
		};
	}

	/** Return the filename without its final extension. */
	public static function stem(path:String):String {
		if (path == null || path == '')
			return '';
		var normalized = path.replace('\\', '/');
		var slash = normalized.lastIndexOf('/');
		var name = slash < 0 ? normalized : normalized.substr(slash + 1);
		var dot = name.lastIndexOf('.');
		return dot <= 0 ? name : name.substr(0, dot);
	}

	/** Stable character id used by runtime routing and imported manifests. */
	public static function characterId(path:String):String {
		return normalizeToken(stem(path));
	}

	/** Match a character companion by its filename, without opening the donor. */
	public static function characterMatches(path:String, names:Array<String>):Bool {
		if (familyForPath(path) != 'character')
			return false;
		var id = characterId(path);
		if (id == '' || names == null)
			return false;
		for (name in names)
			if (id == normalizeToken(name))
				return true;
		return false;
	}

	/**
		Select at most one companion for each character id.

		`roots` is an ordered runtime search list.  A manifest's selected owner
		wins among foreign roots, while the native `assets/scripts` root (when it
		is present in the list) remains the native engine's first precedence.  If
		the owner does not
		provide a requested id, the remaining roots may provide that id, but a
		duplicate id can never be loaded from more than one root.  Paths inside a
		single root use a stable lexical tie-break so shared/ and direct layouts do
		not depend on filesystem enumeration order.
	*/
	public static function selectCharacterPaths(paths:Array<String>, names:Array<String>,
		?roots:Array<String>, ?selectedRoot:String):Array<String> {
		var wanted:Map<String, Bool> = new Map<String, Bool>();
		if (names != null)
			for (name in names) {
				var normalized = normalizeToken(name);
				if (normalized != '')
					wanted.set(normalized, true);
			}
		if (wanted.keys().hasNext() == false || paths == null || paths.length == 0)
			return [];

		var candidates:Map<String, String> = new Map<String, String>();
		var candidateRanks:Map<String, Int> = new Map<String, Int>();
		for (path in paths) {
			if (path == null || path == '' || familyForPath(path) != 'character')
				continue;
			var id = characterId(path);
			if (id == '' || !wanted.exists(id))
				continue;
			var rank = characterPathRank(path, roots, selectedRoot);
			var current = candidates.get(id);
			if (current == null || rank < candidateRanks.get(id)
				|| (rank == candidateRanks.get(id)
					&& pathKey(path) < pathKey(current))) {
				candidates.set(id, path);
				candidateRanks.set(id, rank);
			}
		}

		var result:Array<String> = [];
		for (path in candidates)
			result.push(path);
		result.sort(function(a, b):Int {
			var rankA = characterPathRank(a, roots, selectedRoot);
			var rankB = characterPathRank(b, roots, selectedRoot);
			if (rankA != rankB)
				return rankA < rankB ? -1 : 1;
			var keyA = pathKey(a);
			var keyB = pathKey(b);
			return keyA < keyB ? -1 : (keyA > keyB ? 1 : 0);
		});
		return result;
	}

	/** Stable root/path precedence used by selectCharacterPaths. */
	static function characterPathRank(path:String, roots:Array<String>, selectedRoot:String):Int {
		var rootIndex = rootIndexForPath(path, roots);
		var nativeRoot = rootIndex == 0 && roots != null && roots.length > 0
			&& pathWithin(path, roots[0])
			&& Path.normalize(StringTools.replace(roots[0], '\\', '/')).toLowerCase() == 'assets/scripts';
		var owner = selectedRoot == null ? '' : StringTools.trim(selectedRoot);
		if (nativeRoot)
			return 0;
		if (owner != '' && pathWithin(path, owner))
			return 1;
		return rootIndex < 0 ? (roots == null ? 2 : roots.length + 2) : rootIndex + 2;
	}

	static function rootIndexForPath(path:String, roots:Array<String>):Int {
		if (roots == null)
			return -1;
		for (index in 0...roots.length)
			if (pathWithin(path, roots[index]))
				return index;
		return -1;
	}

	static function pathWithin(path:String, root:String):Bool {
		if (path == null || root == null || StringTools.trim(path) == '' || StringTools.trim(root) == '')
			return false;
		var cleanPath = Path.normalize(StringTools.replace(path, '\\', '/'));
		var cleanRoot = Path.normalize(StringTools.replace(root, '\\', '/'));
		if (cleanPath == cleanRoot || cleanPath.startsWith(cleanRoot + '/'))
			return true;
		#if sys
		// discoverRoot returns full paths while manifests intentionally store
		// destination-relative roots. Compare both forms so precedence remains
		// tied to the manifest rather than to the process working directory.
		var marker = '/' + cleanRoot + '/';
		if (cleanPath.indexOf(marker) >= 0 || cleanPath.endsWith('/' + cleanRoot))
			return true;
		try {
			var fullPath = Path.normalize(StringTools.replace(FileSystem.fullPath(cleanPath), '\\', '/'));
			var fullRoot = Path.normalize(StringTools.replace(FileSystem.fullPath(cleanRoot), '\\', '/'));
			return fullPath == fullRoot || fullPath.startsWith(fullRoot + '/');
		} catch (_:Dynamic) {
			return false;
		}
		#else
		return false;
		#end
	}

	static function pathKey(path:String):String {
		var normalized = Path.normalize(StringTools.replace(path == null ? '' : path, '\\', '/'));
		// Keep the case-folded key for the usual cross-platform ordering, then
		// retain the normalized spelling as a final tie-break for Linux case
		// variants.  A comparator which returns equality here would leak the
		// donor filesystem's directory enumeration order.
		return normalized.toLowerCase() + '\u0000' + normalized;
	}

	/** Normalize chart ids without changing the donor path itself. */
	public static function normalizeToken(value:String):String {
		if (value == null || value == '')
			return '';
		var output = new StringBuf();
		for (index in 0...value.length) {
			var character = value.charAt(index).toLowerCase();
			var code = character.charCodeAt(0);
			if ((code >= 97 && code <= 122) || (code >= 48 && code <= 57))
				output.add(character);
		}
		return output.toString();
	}
}
