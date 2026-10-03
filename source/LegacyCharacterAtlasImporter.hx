package;

import haxe.io.Path;
#if sys
import haxe.io.Bytes;
import ImportFileSystem as FileSystem;
import ImportFile as File;
#end
using StringTools;

/** One Sparrow atlas pair which can be used as a native character source. */
typedef LegacyCharacterAtlasCandidate = {
	var png:String;
	var xml:String;
	var score:Int;
	var idlePrefix:String;
	var singUpPrefix:String;
	var singDownPrefix:String;
	var singLeftPrefix:String;
	var singRightPrefix:String;
	var frameNames:Array<String>;
	var relative:String;
}

/** Read-only result for one chart character reference. */
typedef LegacyCharacterAtlasResult = {
	var reference:String;
	var nativeName:String;
	var recoverable:Bool;
	var candidate:LegacyCharacterAtlasCandidate;
	var candidates:Array<LegacyCharacterAtlasCandidate>;
	var diagnostics:Array<String>;
	var searched:Array<String>;
	var hscript:String;
	var registryEntry:Dynamic;
}

/** Cached, reference-independent atlas metadata for one owner-root set. */
typedef LegacyCharacterAtlasPair = {
	var png:String;
	var xml:String;
	var names:Array<String>;
	var relative:String;
}

typedef LegacyCharacterAtlasIndex = {
	var pairs:Array<LegacyCharacterAtlasPair>;
	var incomplete:Array<LegacyCharacterAtlasPair>;
}

/**
	Adapter for old Kade/FPS/legacy packs whose character definitions lived in
	compiled code.  Those packs often still ship a conventional Sparrow PNG/XML
	pair in an engine/library folder.  Discovery is deliberately independent of
	PlayState and the HXC/Lua compatibility layers: it only reads the XML names,
	then emits ordinary native custom-character assets and a tiny HScript module.

	The adapter is intentionally conservative.  A pair must be inside one of the
	owner roots supplied by the caller, the XML must name at least one idle frame
	(and all four sing directions for player/opponent roles), and a single
	highest-scoring atlas must be identifiable.  Ties and partial atlases stay
	diagnostics rather than guesses.
*/
class LegacyCharacterAtlasImporter {
	public static inline var MAX_DEPTH:Int = 12;
	public static inline var MAX_DIRECTORIES:Int = 8192;
	public static inline var MAX_XML_FILES:Int = 4096;
	public static inline var RECOVERABLE_SCORE:Int = 500;
	#if sys
	static var indexCache:Map<String, LegacyCharacterAtlasIndex> = new Map<String, LegacyCharacterAtlasIndex>();
	#end

	/**
		Discard directory indexes at a new scan/import boundary.  The cache is
		process-local for speed, but donor folders can be edited between two user
		operations; callers must not observe an old atlas after that boundary.
	*/
	public static function clearCache():Void {
		#if sys
		indexCache = new Map<String, LegacyCharacterAtlasIndex>();
		#end
	}

	/** Inspect a single owner root.  This is the common Auto/import entrypoint. */
	public static function inspect(ownerRoot:String, reference:String, ?role:String):LegacyCharacterAtlasResult {
		return inspectRoots(ownerRoot == null ? [] : [ownerRoot], reference, role);
	}

	/** Inspect a bounded set of equivalent owner roots (for example root + assets). */
	public static function inspectRoots(ownerRoots:Array<String>, reference:String, ?role:String):LegacyCharacterAtlasResult {
		var result:LegacyCharacterAtlasResult = emptyResult(reference);
		var atlasRole = normalizedRole(role);
		#if sys
		var roots:Array<String> = uniqueRoots(ownerRoots);
		if (roots.length == 0) {
			result.diagnostics.push('[incomplete-character-atlas] No readable owner root for "'
				+ result.reference + '".');
			return result;
		}
		var index = indexedAtlases(roots);
		var all:Array<LegacyCharacterAtlasCandidate> = [];
		var incomplete:Array<String> = [];
		for (pair in index.incomplete) {
			var missingAssociation = associationScore(result.reference, pair.xml, pair.names);
			if (missingAssociation.score > 0)
				incomplete.push(pair.xml + ' (missing paired PNG)');
		}
		for (pair in index.pairs) {
			var association = associationScore(result.reference, pair.xml, pair.names);
			if (association.score <= 0)
				continue;
			var prefixes = inferPrefixes(pair.names);
			var complete = atlasComplete(prefixes, atlasRole);
			var quality = complete ? 200 : 0;
			var candidate:LegacyCharacterAtlasCandidate = {
				png: pair.png,
				xml: pair.xml,
				score: association.score + quality,
				idlePrefix: prefixes.idle,
				singUpPrefix: prefixes.up,
				singDownPrefix: prefixes.down,
				singLeftPrefix: prefixes.left,
				singRightPrefix: prefixes.right,
				frameNames: pair.names.copy(),
				relative: pair.relative
			};
			all.push(candidate);
		}
		result.candidates = dedupeCandidates(all);
		for (candidate in result.candidates)
			result.searched.push(candidate.xml + ' + ' + candidate.png);
		for (missing in incomplete)
			result.searched.push(missing);
		result.candidates.sort(function(a:LegacyCharacterAtlasCandidate, b:LegacyCharacterAtlasCandidate):Int {
			if (a.score != b.score)
				return b.score - a.score;
			return a.relative.toLowerCase() < b.relative.toLowerCase() ? -1 : 1;
		});
		if (result.candidates.length == 0) {
			if (incomplete.length > 0)
				result.diagnostics.push('[incomplete-character-atlas] Atlas XML candidates for "'
					+ result.reference + '" are missing their paired PNG or required animation prefixes.');
			return result;
		}
		var best = result.candidates[0];
		var ties:Array<LegacyCharacterAtlasCandidate> = [];
		for (candidate in result.candidates)
			if (candidate.score == best.score)
				ties.push(candidate);
		if (ties.length > 1) {
			result.diagnostics.push('[ambiguous-character-atlas] Multiple equally suitable Sparrow atlases match "'
				+ result.reference + '": ' + joinCandidates(ties) + '.');
			return result;
		}
		if (!atlasComplete(best, atlasRole)) {
			result.diagnostics.push('[incomplete-character-atlas] Sparrow atlas for "' + result.reference
				+ '" is missing the animation prefixes required for role ' + atlasRole + ': '
				+ missingPrefixes(best, atlasRole) + '.');
			return result;
		}
		if (best.score < RECOVERABLE_SCORE) {
			result.diagnostics.push('[ambiguous-character-atlas] No strongly associated Sparrow atlas was found for "'
				+ result.reference + '".');
			return result;
		}
		result.candidate = best;
		result.nativeName = nativeName(result.reference);
		if (result.nativeName == '') {
			result.diagnostics.push('[incomplete-character-atlas] Character reference "' + result.reference
				+ '" cannot be represented as a safe native character name.');
			return result;
		}
		result.recoverable = true;
		result.hscript = generateHScript(best, result.nativeName);
		result.registryEntry = {
			like: result.nativeName,
			icons: [0, 0, 0, 0],
			colors: ['#FFFFFF'],
			legacyAtlas: true
		};
		result.diagnostics.push('[recoverable-character-atlas] Inferred native animations for "'
			+ result.reference + '" from ' + best.relative + '.');
		#end
		return result;
	}

	/** Alias used by importer/tests which call the adapter a detector. */
	public static function detect(ownerRoot:String, reference:String, ?role:String):LegacyCharacterAtlasResult {
		return inspect(ownerRoot, reference, role);
	}

	/** Convert a donor chart id into a path-safe native registry id. */
	public static function nativeName(reference:String):String {
		if (reference == null)
			return '';
		var value = StringTools.trim(reference);
		if (value == '' || value == '.' || value == '..')
			return '';
		value = StringTools.replace(value, '\\', '-');
		value = StringTools.replace(value, '/', '-');
		value = StringTools.replace(value, ':', '-');
		value = StringTools.replace(value, '\u0000', '-');
		while (value.indexOf('--') >= 0)
			value = value.replace('--', '-');
		return StringTools.trim(value);
	}

	static function emptyResult(reference:String):LegacyCharacterAtlasResult {
		return {
			reference: StringTools.trim(reference == null ? '' : reference),
			nativeName: '', recoverable: false, candidate: null, candidates: [],
			diagnostics: [], searched: [], hscript: '', registryEntry: null
		};
	}

	static function normalizedRole(role:String):String {
		if (role == null || StringTools.trim(role) == '')
			return 'opponent';
		var value = StringTools.trim(role).toLowerCase();
		if (value == 'gf' || value == 'girlfriend' || value == 'player3' || value == 'special'
			|| value == 'background' || value == 'event' || value == 'nonstandard')
			return 'special';
		return value;
	}

	static function atlasComplete(prefixes:Dynamic, role:String):Bool {
		if (prefixes == null)
			return false;
		var idle = Reflect.hasField(prefixes, 'idle') ? Std.string(Reflect.field(prefixes, 'idle')) : Std.string(Reflect.field(prefixes, 'idlePrefix'));
		var up = Reflect.hasField(prefixes, 'up') ? Std.string(Reflect.field(prefixes, 'up')) : Std.string(Reflect.field(prefixes, 'singUpPrefix'));
		var down = Reflect.hasField(prefixes, 'down') ? Std.string(Reflect.field(prefixes, 'down')) : Std.string(Reflect.field(prefixes, 'singDownPrefix'));
		var left = Reflect.hasField(prefixes, 'left') ? Std.string(Reflect.field(prefixes, 'left')) : Std.string(Reflect.field(prefixes, 'singLeftPrefix'));
		var right = Reflect.hasField(prefixes, 'right') ? Std.string(Reflect.field(prefixes, 'right')) : Std.string(Reflect.field(prefixes, 'singRightPrefix'));
		if (idle == null || idle == '' || idle == 'null')
			return false;
		// Girlfriend and special/event actors are often authored with only a
		// dance/idle animation.  Requiring the four standard sing prefixes here
		// made valid legacy atlases look missing even though their chart never
		// asks them to sing.
		if (role == 'special')
			return true;
		return up != null && up != '' && up != 'null' && down != null && down != '' && down != 'null'
			&& left != null && left != '' && left != 'null' && right != null && right != '' && right != 'null';
	}

	#if sys
	/** Copy one inferred definition into the destination without overwriting. */
	public static function materialize(definition:LegacyCharacterAtlasResult,
		destinationRoot:String):LegacyCharacterAtlasMaterializeResult {
		var result:LegacyCharacterAtlasMaterializeResult = {copied:0, skipped:0, failed:0, errors:[]};
		if (definition == null || !definition.recoverable || definition.candidate == null)
			return result;
		var name = nativeName(definition.nativeName);
		if (name == '') {
			result.failed++;
			result.errors.push('Invalid inferred native character name.');
			return result;
		}
		var folder = Path.join([destinationRoot, 'images', 'custom_chars', name]);
		if (FileSystem.exists(folder) && !FileSystem.isDirectory(folder)) {
			result.failed++;
			result.errors.push('Destination character path is not a directory: ' + folder);
			return result;
		}
		ensureDirectory(folder);
		copyNonOverwriting(definition.candidate.png, Path.join([folder, 'char.png']), result);
		copyNonOverwriting(definition.candidate.xml, Path.join([folder, 'char.xml']), result);
		copyTextNonOverwriting(definition.hscript,
			Path.join([destinationRoot, 'images', 'custom_chars', name + '.hscript']), result);
		return result;
	}
	#end

	#if sys
	static function uniqueRoots(ownerRoots:Array<String>):Array<String> {
		var result:Array<String> = [];
		if (ownerRoots == null)
			return result;
		for (root in ownerRoots) {
			var path = canonical(root);
			if (path == '' || !FileSystem.exists(path) || !FileSystem.isDirectory(path))
				continue;
			var key = path.toLowerCase();
			if (result.indexOf(path) < 0) {
				var duplicate = false;
				for (existing in result)
					if (existing.toLowerCase() == key)
						duplicate = true;
				if (!duplicate)
					result.push(path);
			}
		}
		return result;
	}

	/**
		Build the expensive directory/XML index once per owner-root set.  A chart
		scan can inspect the same donor root hundreds of times (and once per
		character slot); caching the reference-independent pairs keeps Auto
		discovery bounded without weakening the per-reference association check.
	*/
	static function indexedAtlases(roots:Array<String>):LegacyCharacterAtlasIndex {
		var cacheRoots = roots.copy();
		cacheRoots.sort(function(a:String, b:String):Int {
			var al = a.toLowerCase();
			var bl = b.toLowerCase();
			return al < bl ? -1 : (al > bl ? 1 : Reflect.compare(a, b));
		});
		var cacheKey = cacheRoots.join('\u0001');
		var cached = indexCache.get(cacheKey);
		if (cached != null)
			return cached;
		var pairs:Array<LegacyCharacterAtlasPair> = [];
		var incomplete:Array<LegacyCharacterAtlasPair> = [];
		var visited:Map<String, Bool> = new Map<String, Bool>();
		var directories = 0;
		var xmlFiles = 0;
		for (root in roots) {
			if (directories >= MAX_DIRECTORIES || xmlFiles >= MAX_XML_FILES)
				break;
			var queue:Array<{path:String, depth:Int}> = [{path:root, depth:0}];
			var cursor = 0;
			while (cursor < queue.length && directories < MAX_DIRECTORIES && xmlFiles < MAX_XML_FILES) {
				var item = queue[cursor++];
				var current = canonical(item.path);
				var key = current.toLowerCase();
				if (current == '' || visited.exists(key) || !FileSystem.isDirectory(current))
					continue;
				visited.set(key, true);
				directories++;
				var entries:Array<String>;
				try {
					entries = FileSystem.readDirectory(current);
				} catch (_:Dynamic) {
					continue;
				}
				entries.sort(function(a:String, b:String):Int {
					var al = a.toLowerCase();
					var bl = b.toLowerCase();
					return al < bl ? -1 : (al > bl ? 1 : Reflect.compare(a, b));
				});
				var pngByStem:Map<String, String> = new Map<String, String>();
				var xmlPaths:Array<String> = [];
				for (entry in entries) {
					if (!validEntry(entry))
						continue;
					var path = Path.join([current, entry]);
					try {
						if (FileSystem.isDirectory(path)) {
							if (item.depth < MAX_DEPTH && !skipDirectory(entry))
								queue.push({path:path, depth:item.depth + 1});
							continue;
						}
					} catch (_:Dynamic) {
						continue;
					}
					var lower = entry.toLowerCase();
					if (lower.endsWith('.png')) {
						pngByStem.set(stemKey(entry), path);
					} else if (lower.endsWith('.xml')) {
						xmlPaths.push(path);
						xmlFiles++;
					}
				}
				for (xmlPath in xmlPaths) {
					var parsed = parseAtlas(xmlPath, pngByStem);
					if (parsed == null)
						continue;
					if (parsed.png == null || !FileSystem.exists(parsed.png)) {
						incomplete.push({png:parsed.png, xml:xmlPath, names:parsed.names.copy(),
							relative:relativeToRoots(xmlPath, roots)});
						continue;
					}
					pairs.push({png:parsed.png, xml:xmlPath, names:parsed.names.copy(),
						relative:relativeToRoots(xmlPath, roots)});
				}
			}
		}
		var deduped:Array<LegacyCharacterAtlasPair> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (pair in pairs) {
			var pairKey = canonical(pair.xml).toLowerCase();
			if (seen.exists(pairKey))
				continue;
			seen.set(pairKey, true);
			deduped.push(pair);
		}
		var index:LegacyCharacterAtlasIndex = {pairs:deduped, incomplete:incomplete};
		indexCache.set(cacheKey, index);
		return index;
	}

	static function canonical(path:String):String {
		if (path == null || StringTools.trim(path) == '')
			return '';
		var value = StringTools.replace(StringTools.trim(path), '\\', '/');
		try {
			value = FileSystem.fullPath(value);
		} catch (_:Dynamic) {}
		return Path.normalize(value);
	}

	static function validEntry(name:String):Bool {
		return name != null && name != '' && name != '.' && name != '..'
			&& name.indexOf('/') < 0 && name.indexOf('\\') < 0 && name.indexOf(':') < 0
			&& name.indexOf('\u0000') < 0;
	}

	static function skipDirectory(name:String):Bool {
		var lower = name.toLowerCase();
		// Media libraries can be enormous.  Character atlases are normally below
		// images/characters/library/shared; skip unrelated bulk trees while still
		// descending into every plausible engine/library container.
		return lower == '.git' || lower == '.tools' || lower == '.haxelib'
			|| lower == 'export' || lower == 'build' || lower == 'dist' || lower == 'bin'
			|| lower == 'songs' || lower == 'music' || lower == 'sounds' || lower == 'videos'
			|| lower == 'replays' || lower == 'cache' || lower == 'node_modules';
	}

	static function stemKey(name:String):String {
		var stem = Path.withoutExtension(Path.withoutDirectory(StringTools.replace(name, '\\', '/')));
		return stem.toLowerCase();
	}

	static function parseAtlas(xmlPath:String, pngByStem:Map<String, String>):Dynamic {
		var text:String;
		try {
			// Do not ask the runtime to UTF-8 decode arbitrary legacy XML first:
			// some old exports contain a bad comment byte.  Animation names and
			// imagePath are ASCII in Sparrow XML, so a byte-preserving sanitization
			// keeps the useful attributes while making malformed comments harmless.
			var bytes:Bytes = File.getBytes(xmlPath);
			var safe = new StringBuf();
			for (index in 0...bytes.length) {
				var code = bytes.get(index);
				safe.addChar(code < 128 && (code >= 32 || code == 9 || code == 10 || code == 13) ? code : 32);
			}
			text = safe.toString();
		} catch (_:Dynamic) {
			return null;
		}
		if (text == null)
			return null;
		text = text.charCodeAt(0) == 0xFEFF ? text.substr(1) : text;
		var xml:Xml;
		try {
			xml = Xml.parse(text).firstElement();
		} catch (_:Dynamic) {
			// A few old Animate/Kade exports contain one malformed UTF-8 comment
			// even though their TextureAtlas/SubTexture tags are perfectly usable.
			// Keep the importer read-only and fall back to the small attribute subset
			// needed for inference instead of rejecting the whole atlas.
			return parseAtlasFallback(xmlPath, text, pngByStem);
		}
		if (xml == null || xml.nodeName.toLowerCase() != 'textureatlas')
			return null;
		var names:Array<String> = [];
		for (node in xml.elements()) {
			if (node.nodeName.toLowerCase() != 'subtexture')
				continue;
			var name = StringTools.trim(node.get('name'));
			if (name != '')
				names.push(name);
		}
		if (names.length == 0)
			return null;
		var rawImagePath:Dynamic = xml.get('imagePath');
		var imagePath = rawImagePath == null ? '' : StringTools.trim(Std.string(rawImagePath));
		var dir = Path.directory(xmlPath);
		var png:String = null;
		if (imagePath != '') {
			imagePath = StringTools.replace(imagePath, '\\', '/');
			var clean = Path.normalize(Path.join([dir, imagePath]));
			if (isWithin(clean, dir) && FileSystem.exists(clean) && !FileSystem.isDirectory(clean)
				&& clean.toLowerCase().endsWith('.png'))
				png = clean;
			if (png == null)
				png = pngByStem.get(stemKey(imagePath));
		}
		if (png == null)
			png = pngByStem.get(stemKey(xmlPath));
		return {png:png, names:names};
	}

	static function parseAtlasFallback(xmlPath:String, text:String,
		pngByStem:Map<String, String>):Dynamic {
		var atlasTag = new EReg('<TextureAtlas[^>]*>', 'i');
		if (!atlasTag.match(text))
			return null;
		var imagePath = '';
		var imageAttribute = new EReg('imagePath\\s*=\\s*[\"\']([^\"\']+)[\"\']', 'i');
		if (imageAttribute.match(atlasTag.matched(0)))
			imagePath = StringTools.trim(imageAttribute.matched(1));
		var names:Array<String> = [];
		var subTexture = new EReg('<SubTexture[^>]*name\\s*=\\s*[\"\']([^\"\']+)[\"\']', 'ig');
		var remaining = text;
		while (subTexture.match(remaining)) {
			var name = StringTools.trim(subTexture.matched(1));
			if (name != '')
				names.push(name);
			remaining = subTexture.matchedRight();
		}
		if (names.length == 0)
			return null;
		var dir = Path.directory(xmlPath);
		var png:String = null;
		if (imagePath != '')
			png = pngByStem.get(stemKey(imagePath));
		if (png == null)
			png = pngByStem.get(stemKey(xmlPath));
		return {png:png, names:names};
	}

	static function isWithin(path:String, parent:String):Bool {
		var child = canonical(path).toLowerCase();
		var base = canonical(parent).toLowerCase();
		return child == base || child.startsWith(base + '/');
	}

	static function associationScore(reference:String, xmlPath:String, names:Array<String>):{score:Int} {
		var wanted = compact(reference);
		if (wanted == '')
			return {score:0};
		var stem = compact(Path.withoutExtension(Path.withoutDirectory(xmlPath)));
		var score = 0;
		if (stem == wanted)
			score = 1000;
		else if (stem.startsWith(wanted))
			score = 760 - Std.int(Math.min(120, stem.length - wanted.length));
		else if (wanted.startsWith(stem) && stem.length >= 3)
			score = 680 - Std.int(Math.min(120, wanted.length - stem.length));
		else if (stem.indexOf(wanted) >= 0 || wanted.indexOf(stem) >= 0)
			score = 560;
		var pathParts = StringTools.replace(Path.normalize(xmlPath), '\\', '/').split('/');
		for (part in pathParts) {
			var partKey = compact(part);
			if (partKey == wanted)
				score = Std.int(Math.max(score, 880));
		}
		if (score == 0 && names != null)
			for (name in names)
				if (compact(name).indexOf(wanted) >= 0)
					score = 420;
		// Character atlases conventionally use char.xml/char.png, while portrait
		// atlases can live beside them and contain similarly named frames. Keep
		// portraits as a fallback but prefer the character atlas when both exist.
		// Apply the preference only after association: a generic `char.xml` in an
		// unrelated folder must not become a candidate for every missing id.
		if (score > 0) {
			var xmlStem = Path.withoutExtension(Path.withoutDirectory(StringTools.replace(xmlPath, '\\', '/'))).toLowerCase();
			if (xmlStem == 'char')
				score += 260;
			else if (xmlStem == 'portrait')
				score -= 160;
		}
		return {score:score};
	}

	static function compact(value:String):String {
		if (value == null)
			return '';
		var lower = value.toLowerCase();
		var output = new StringBuf();
		for (index in 0...lower.length) {
			var code = lower.charCodeAt(index);
			if ((code >= 48 && code <= 57) || (code >= 97 && code <= 122))
				output.addChar(code);
		}
		return output.toString();
	}

	static function stripFrameNumber(name:String):String {
		if (name == null)
			return '';
		var end = name.length;
		while (end > 0) {
			var code = name.charCodeAt(end - 1);
			if (code >= 48 && code <= 57)
				end--;
			else
				break;
		}
		return StringTools.trim(name.substr(0, end));
	}

	static function inferPrefixes(names:Array<String>):Dynamic {
		var counts:Map<String, Int> = new Map<String, Int>();
		var originals:Map<String, String> = new Map<String, String>();
		for (name in names) {
			var prefix = stripFrameNumber(name);
			if (prefix == '')
				continue;
			var key = prefix.toLowerCase();
			counts.set(key, (counts.exists(key) ? counts.get(key) : 0) + 1);
			if (!originals.exists(key))
				originals.set(key, prefix);
		}
		return {
			idle: choosePrefix(counts, originals, 'idle'),
			up: choosePrefix(counts, originals, 'up'),
			down: choosePrefix(counts, originals, 'down'),
			left: choosePrefix(counts, originals, 'left'),
			right: choosePrefix(counts, originals, 'right')
		};
	}

	static function choosePrefix(counts:Map<String, Int>, originals:Map<String, String>, role:String):String {
		var best:String = '';
		var bestRank = -1;
		var bestCount = -1;
		for (key in counts.keys()) {
			var lower = key.toLowerCase();
			var matches = role == 'idle'
				? (lower.indexOf('idle') >= 0 || lower.indexOf('danc') >= 0 || lower.indexOf('neutral') >= 0)
				: (lower.indexOf(role) >= 0
					&& (lower.indexOf('sing') >= 0 || lower.indexOf('note') >= 0
						|| lower.indexOf('anim') >= 0));
			if (!matches)
				continue;
			// Normal sing prefixes outrank miss/hold variants.  Idle outranks
			// dance/neutral aliases, and exact direction names are preferred.
			var rank = 0;
			if (role == 'idle' && lower.indexOf('idle') >= 0) rank += 30;
			if (role != 'idle' && lower.indexOf('sing') >= 0) rank += 20;
			if (role != 'idle' && lower.indexOf('note') >= 0) rank += 16;
			if (lower.indexOf(role) >= 0) rank += 10;
			if (lower.indexOf('miss') >= 0) rank -= 8;
			if (lower.indexOf('hold') >= 0) rank -= 4;
			var count = counts.get(key);
			var original = originals.get(key);
			if (rank > bestRank || (rank == bestRank && count > bestCount)
				|| (rank == bestRank && count == bestCount
					&& (best == '' || original.toLowerCase() < best.toLowerCase()))) {
				best = original;
				bestRank = rank;
				bestCount = count;
			}
		}
		return best;
	}

	static function dedupeCandidates(items:Array<LegacyCharacterAtlasCandidate>):Array<LegacyCharacterAtlasCandidate> {
		var result:Array<LegacyCharacterAtlasCandidate> = [];
		var seen:Map<String, Bool> = new Map<String, Bool>();
		for (item in items) {
			var key = canonical(item.xml).toLowerCase();
			if (seen.exists(key))
				continue;
			seen.set(key, true);
			result.push(item);
		}
		return result;
	}

	static function relativeToRoots(path:String, roots:Array<String>):String {
		var normalized = canonical(path);
		for (root in roots) {
			var base = canonical(root);
			if (isWithin(normalized, base)) {
				var value = normalized.substr(base.length);
				while (value.startsWith('/')) value = value.substr(1);
				return value == '' ? Path.withoutDirectory(normalized) : value;
			}
		}
		return Path.withoutDirectory(normalized);
	}

	static function joinCandidates(items:Array<LegacyCharacterAtlasCandidate>):String {
		var names:Array<String> = [];
		for (item in items)
			names.push(item.relative);
		return names.join(', ');
	}

	static function missingPrefixes(candidate:LegacyCharacterAtlasCandidate, ?role:String):String {
		var atlasRole = normalizedRole(role);
		var missing:Array<String> = [];
		if (candidate.idlePrefix == '') missing.push('idle');
		if (atlasRole == 'special')
			return missing.join(', ');
		if (candidate.singUpPrefix == '') missing.push('singUP');
		if (candidate.singDownPrefix == '') missing.push('singDOWN');
		if (candidate.singLeftPrefix == '') missing.push('singLEFT');
		if (candidate.singRightPrefix == '') missing.push('singRIGHT');
		return missing.join(', ');
	}

	static function quote(value:String):String {
		return "'" + StringTools.replace(StringTools.replace(StringTools.replace(value, '\\', '\\\\'), "'", "\\'"), '\n', '\\n') + "'";
	}

	static function generateHScript(candidate:LegacyCharacterAtlasCandidate, characterName:String):String {
		var lines:Array<String> = [
			'// Generated by LegacyCharacterAtlasImporter; source definition was compiled into the donor.',
			'function init(char) {',
			"    char.frames = FlxAtlasFrames.fromSparrow(hscriptPath + 'char.png', hscriptPath + 'char.xml');",
			"    char.like = " + quote(characterName) + ';'
		];
		var addAnimation = function(nativeName:String, prefix:String):Void {
			if (prefix == null || prefix == '')
				return;
			lines.push("    char.animation.addByPrefix('" + nativeName + "', " + quote(prefix) + ', 24, false);');
			lines.push("    char.addOffset('" + nativeName + "');");
		};
		addAnimation('idle', candidate.idlePrefix);
		addAnimation('singUP', candidate.singUpPrefix);
		addAnimation('singDOWN', candidate.singDownPrefix);
		addAnimation('singLEFT', candidate.singLeftPrefix);
		addAnimation('singRIGHT', candidate.singRightPrefix);
		lines = lines.concat([
			"    char.playAnim('idle');",
			'    char.flipX = false;',
			'}',
			'portraitOffset = [0, 0];',
			'dadVar = 4.0;',
			'isPixel = false;',
			'function sing(direction, miss, alt, char) {}',
			'function update(elapsed, char) {}',
			'function dance(char) { char.playAnim(\'idle\'); }',
			''
		]);
		return lines.join('\n');
	}

	static function ensureDirectory(path:String):Void {
		if (path == null || StringTools.trim(path) == '' || FileSystem.exists(path))
			return;
		var parent = Path.directory(path);
		if (parent != null && parent != '' && parent != path)
			ensureDirectory(parent);
		try FileSystem.createDirectory(path) catch (_:Dynamic) {}
	}

	static function copyNonOverwriting(source:String, destination:String,
		result:LegacyCharacterAtlasMaterializeResult):Void {
		if (source == null || !FileSystem.exists(source)) {
			result.failed++;
			result.errors.push('Missing atlas source: ' + source);
			return;
		}
		if (FileSystem.exists(destination)) {
			result.skipped++;
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			File.copy(source, destination);
			result.copied++;
		} catch (error:Dynamic) {
			result.failed++;
			result.errors.push('Could not copy atlas source: ' + Std.string(error));
		}
	}

	static function copyTextNonOverwriting(text:String, destination:String,
		result:LegacyCharacterAtlasMaterializeResult):Void {
		if (text == null || StringTools.trim(text) == '') {
			result.failed++;
			result.errors.push('Generated character script is empty.');
			return;
		}
		if (FileSystem.exists(destination)) {
			result.skipped++;
			return;
		}
		try {
			ensureDirectory(Path.directory(destination));
			File.saveContent(destination, text);
			result.copied++;
		} catch (error:Dynamic) {
			result.failed++;
			result.errors.push('Could not write generated character script: ' + Std.string(error));
		}
	}
	#end
}

typedef LegacyCharacterAtlasMaterializeResult = {
	var copied:Int;
	var skipped:Int;
	var failed:Int;
	var errors:Array<String>;
}
