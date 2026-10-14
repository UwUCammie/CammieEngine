package;

import haxe.io.Path;
import HxcScriptIdentity.HxcScriptIdentityData;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
using StringTools;

private typedef HxcScriptIdentityCacheEntry = {
	var modifiedAt:Float;
	var size:Int;
	var data:HxcScriptIdentityData;
}

/**
	HXC layout and declared-source discovery. Importers can feed candidate paths
	from any source root; readable files refine character/stage identity without
	executing or modifying donor code, while missing fixture paths retain layout
	matching.
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
	/**
		Source identity is metadata only. Re-read a real HXC file when its size or
		mtime changes; nonexistent test/fixture paths keep their path-only result.
	*/
	static var sourceIdentityCache:Map<String, HxcScriptIdentityCacheEntry> = new Map();
	#end

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
		var entries:Array<NativeDirectoryListing.DirectoryEntry>;
		try {
			entries = NativeDirectoryListing.read(root);
		} catch (_:Dynamic) {
			return budget;
		}
		entries.sort(function(a, b) return Reflect.compare(a.name.toLowerCase(), b.name.toLowerCase()));
		for (entry in entries) {
			if (budget <= 0)
				break;
			var child = Path.join([root, entry.name]);
			if (entry.isDirectory == null ? FileSystem.isDirectory(child) : entry.isDirectory)
				budget = collectRoot(child, output, budget, depth + 1);
			else if (isScriptedClassFile(child)) {
				output.push(FileSystem.fullPath(child));
				budget--;
			}
		}
		return budget;
	}
	#end

	/**
		True for a file the scripted-class runtime may own: any `.hxc`, or a `.hx`
		inside a `scripts/` tree that declares a class with a known scripted base
		(Module, Song, Stage, a character class and so on). Since Funkin 0.8.4
		Polymod reads both extensions. Psych, Nightmare Vision and Codename keep
		classless HScript in `.hx`, so the class test keeps those files out.
		`import.hx` and `import.hxc` only hold package import defaults and are
		never scripts themselves. `source` skips the file read when the caller
		already has the text.
	*/
	public static function isScriptedClassFile(path:String, ?source:String):Bool {
		if (path == null || path == '')
			return false;
		var normalized = path.replace('\\', '/').toLowerCase();
		var slash = normalized.lastIndexOf('/');
		var name = slash < 0 ? normalized : normalized.substr(slash + 1);
		if (name == 'import.hx' || name == 'import.hxc')
			return false;
		if (name.endsWith('.hxc'))
			return true;
		if (!name.endsWith('.hx') || !('/' + normalized).contains('/scripts/'))
			return false;
		var text = source;
		#if sys
		if (text == null) {
			var cached = scriptedHxCache.get(normalized);
			try {
				if (!FileSystem.exists(path))
					return false;
				var stat = FileSystem.stat(path);
				var modifiedAt = stat.mtime == null ? 0 : stat.mtime.getTime();
				if (cached != null && cached.modifiedAt == modifiedAt && cached.size == stat.size)
					return cached.scripted;
				text = File.getContent(path);
				var scripted = declaresScriptedClass(text);
				scriptedHxCache.set(normalized, {modifiedAt: modifiedAt, size: stat.size, scripted: scripted});
				return scripted;
			} catch (_:Dynamic) {
				scriptedHxCache.remove(normalized);
				return false;
			}
		}
		#end
		return text != null && declaresScriptedClass(text);
	}

	static function declaresScriptedClass(source:String):Bool {
		// A class with a scripted base needs both words. Classless HScript, which
		// is most `.hx` under Psych-family scripts trees, skips the tokenizer.
		if (source == null || source.indexOf('class') < 0 || source.indexOf('extends') < 0)
			return false;
		for (declaration in HxcScriptIdentity.classDeclarations(source))
			if (HxcScriptIdentity.familyForBase(declaration.base) != '')
				return true;
		return false;
	}

	#if sys
	static var scriptedHxCache:Map<String, {var modifiedAt:Float; var size:Int; var scripted:Bool;}> = new Map();

	/**
		Package import defaults for one script, the way Polymod applies
		`import.hx` / `import.hxc`: files in the script's own folder and every
		parent folder up to the `scripts` root, outermost first, so a nearer
		file's import of the same name comes later and wins. Each entry is one
		`import ...;` or `using ...;` statement. Only the active `#if` branches
		count, and comments are ignored.
	*/
	public static function importDefaults(scriptPath:String):Array<String> {
		var result:Array<String> = [];
		if (scriptPath == null || scriptPath == '')
			return result;
		var folders:Array<String> = [];
		var folder = Path.directory(Path.normalize(scriptPath.replace('\\', '/')));
		for (_ in 0...16) {
			if (folder == null || folder == '')
				break;
			folders.unshift(folder);
			var base = Path.withoutDirectory(folder).toLowerCase();
			if (base == 'scripts')
				break;
			var parent = Path.directory(folder);
			if (parent == folder)
				break;
			folder = parent;
		}
		// Without a scripts folder above it the file is not in a package tree,
		// so only its own folder can supply defaults.
		if (folders.length > 0 && Path.withoutDirectory(folders[0]).toLowerCase() != 'scripts')
			folders = [folders[folders.length - 1]];
		for (directory in folders)
			for (name in ['import.hx', 'import.hxc']) {
				var file = Path.join([directory, name]);
				if (!FileSystem.exists(file) || FileSystem.isDirectory(file))
					continue;
				try {
					for (statement in importStatements(File.getContent(file)))
						if (result.indexOf(statement) < 0)
							result.push(statement);
				} catch (_:Dynamic) {}
			}
		return result;
	}
	#end

	/** `import` and `using` statements of an import defaults file, normalised to `import a.b.C;`. */
	public static function importStatements(source:String):Array<String> {
		var result:Array<String> = [];
		if (source == null)
			return result;
		var text = stripLineAndBlockComments(HxcPreprocessor.apply(source));
		for (part in text.split(';')) {
			var statement = part.trim();
			var keyword = statement.startsWith('import') ? 'import' : (statement.startsWith('using') ? 'using' : '');
			if (keyword == '' || statement.length <= keyword.length)
				continue;
			var space = statement.charCodeAt(keyword.length);
			if (space != ' '.code && space != '\t'.code && space != '\n'.code && space != '\r'.code)
				continue;
			var body = collapseWhitespace(statement.substr(keyword.length));
			if (body == '' || !isImportBody(body))
				continue;
			var line = keyword + ' ' + body + ';';
			if (result.indexOf(line) < 0)
				result.push(line);
		}
		return result;
	}

	static function stripLineAndBlockComments(source:String):String {
		var output = new StringBuf();
		var index = 0;
		while (index < source.length) {
			var code = source.fastCodeAt(index);
			if (code == '/'.code && index + 1 < source.length && source.fastCodeAt(index + 1) == '/'.code) {
				while (index < source.length && source.fastCodeAt(index) != '\n'.code)
					index++;
				continue;
			}
			if (code == '/'.code && index + 1 < source.length && source.fastCodeAt(index + 1) == '*'.code) {
				var close = source.indexOf('*/', index + 2);
				index = close < 0 ? source.length : close + 2;
				output.addChar(' '.code);
				continue;
			}
			output.addChar(code);
			index++;
		}
		return output.toString();
	}

	static function collapseWhitespace(value:String):String {
		var output = new StringBuf();
		var pendingSpace = false;
		for (index in 0...value.length) {
			var code = value.fastCodeAt(index);
			if (code == ' '.code || code == '\t'.code || code == '\n'.code || code == '\r'.code) {
				pendingSpace = output.length > 0;
				continue;
			}
			if (pendingSpace)
				output.addChar(' '.code);
			pendingSpace = false;
			output.addChar(code);
		}
		return output.toString();
	}

	/** A dotted path with an optional `.*` or ` as Alias` / ` in Alias` tail. */
	static function isImportBody(body:String):Bool {
		var words = body.split(' ');
		if (words.length != 1 && !(words.length == 3 && (words[1] == 'as' || words[1] == 'in')
			&& isIdentifier(words[2])))
			return false;
		var parts = words[0].split('.');
		for (index in 0...parts.length) {
			var part = parts[index];
			if (part == '*' && index == parts.length - 1 && index > 0)
				continue;
			if (!isIdentifier(part))
				return false;
		}
		return true;
	}

	static function isIdentifier(value:String):Bool {
		if (value == null || value == '')
			return false;
		for (index in 0...value.length) {
			var code = value.fastCodeAt(index);
			var letter = (code >= 'a'.code && code <= 'z'.code) || (code >= 'A'.code && code <= 'Z'.code) || code == '_'.code;
			if (!letter && !(index > 0 && code >= '0'.code && code <= '9'.code))
				return false;
		}
		return true;
	}

	/** Map the donor directory layout to a stable importer family name. */
	public static function familyForPath(path:String):String {
		var pathFamily = layoutFamilyForPath(path);
		#if sys
		var metadata = sourceIdentity(path, pathFamily);
		if (metadata != null)
			return metadata.family;
		#end
		return pathFamily;
	}

	/** Return the original path-based family without reading the source file. */
	static function layoutFamilyForPath(path:String):String {
		if (path == null || path == '')
			return 'unknown';
		var normalized = path.replace('\\', '/').toLowerCase();
		// A `.hx` file only counts when it declares a scripted class, and the
		// import defaults files are never scripts.
		if (!normalized.endsWith('.hxc') && !normalized.endsWith('.hx'))
			return 'unknown';
		if (normalized.endsWith('/import.hxc') || normalized.endsWith('/import.hx')
			|| normalized == 'import.hxc' || normalized == 'import.hx')
			return 'unknown';
		if (normalized.endsWith('.hx') && !isScriptedClassFile(path))
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

	#if sys
	static function sourceIdentity(path:String, pathFamily:String):HxcScriptIdentityData {
		var lower = path == null ? '' : path.toLowerCase();
		if (lower == '' || (!lower.endsWith('.hxc') && !lower.endsWith('.hx')))
			return null;
		if (lower.endsWith('.hx') && !isScriptedClassFile(path))
			return null;
		var normalized = Path.normalize(StringTools.replace(path, '\\', '/'));
		var key = normalized + '\u0000' + (pathFamily == null ? '' : pathFamily);
		if (!FileSystem.exists(path)) {
			sourceIdentityCache.remove(key);
			return null;
		}
		try {
			var stat = FileSystem.stat(path);
			var modifiedAt = stat.mtime == null ? 0 : stat.mtime.getTime();
			var cached = sourceIdentityCache.get(key);
			if (cached != null && cached.modifiedAt == modifiedAt && cached.size == stat.size)
				return cached.data;
			// Replace a stale record before parsing so a failed read cannot leave an
			// old valid identity attached to a changed file.
			sourceIdentityCache.remove(key);
			var data = HxcScriptIdentity.inspect(File.getContent(path), pathFamily, stem(path));
			sourceIdentityCache.set(key, {modifiedAt: modifiedAt, size: stat.size, data: data});
			return data;
		} catch (_:Dynamic) {
			sourceIdentityCache.remove(key);
			return null;
		}
	}
	#end

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
		var pathFamily = layoutFamilyForPath(path);
		#if sys
		var metadata = sourceIdentity(path, pathFamily);
		if (metadata != null) {
			if (metadata.family != 'character')
				return '';
			if (metadata.hasCharacterClass) {
				var declaredId = normalizeToken(metadata.characterId);
				if (declaredId != '')
					return declaredId;
				// A selected character file in the canonical character tree may use a
				// non-literal base constructor (for example a CharacterInfo wrapper).
				// Its filename is still the established runtime identity there. Do not
				// guess from a misplaced class file or from an unrelated helper class.
				return pathFamily == 'character' ? normalizeToken(stem(path)) : '';
			}
			// Old classless callback scripts are still selected by their filename.
			return metadata.hasDeclarations ? '' : normalizeToken(stem(path));
		}
		#end
		return normalizeToken(stem(path));
	}

	/** Match a character companion using the shared declared-source identity. */
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

	/** Stable stage id used by runtime routing; declared literal ids win over filenames. */
	public static function stageId(path:String):String {
		var pathFamily = layoutFamilyForPath(path);
		#if sys
		var metadata = sourceIdentity(path, pathFamily);
		if (metadata != null) {
			// A concrete declaration from another family owns this file even when a
			// stale `stages/` path would otherwise suggest a stage companion.
			if (metadata.family != 'stage')
				return '';
			var declaredId = normalizeToken(metadata.stageId);
			if (metadata.hasStageClass && declaredId != '')
				return declaredId;
			// Legacy/classless stage scripts and Stage wrappers with nonliteral
			// constructors retain the established filename identity.
			return normalizeToken(stem(path));
		}
		#end
		return normalizeToken(stem(path));
	}

	/** Match a stage companion by declared constructor id, falling back to its filename. */
	public static function stageMatches(path:String, names:Array<String>):Bool {
		if (familyForPath(path) != 'stage')
			return false;
		var id = stageId(path);
		var filenameId = normalizeToken(stem(path));
		if ((id == '' && filenameId == '') || names == null)
			return false;
		for (name in names)
			if (id == normalizeToken(name) || filenameId == normalizeToken(name))
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
