package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

typedef CodenameScriptFile = {
	var path:String;
	var relative:String;
	var family:String;
	@:optional var authoredId:String;
	@:optional var embeddedScript:String;
	@:optional var embeddedSchema:String;
}

typedef CodenameCharacterDiscovery = {
	var files:Array<CodenameScriptFile>;
	var diagnostics:Array<String>;
}

typedef CodenameEventDiscovery = {
	var files:Array<CodenameScriptFile>;
	var diagnostics:Array<String>;
}

typedef CodenameOwnerScriptDiscovery = {
	var files:Array<CodenameScriptFile>;
	var diagnostics:Array<String>;
}

/** Bounded, source-root-local discovery. This does not parse or execute donor Haxe. */
class CodenameScriptDiscovery {
	// Codename EventsData.defaultEventsList. Other event names enter that list
	// only through a nonempty data/events/<name>.json or .pack schema.
	static var builtInEventNames:Array<String> = [
		'HScript Call', 'Camera Movement', 'Camera Position', 'Add Camera Zoom',
		'Camera Bop', 'Camera Zoom', 'Camera Modulo Change', 'Camera Flash',
		'BPM Change', 'Continuous BPM Change', 'Time Signature Change',
		'Scroll Speed Change', 'Alt Animation Toggle', 'Play Animation'
	];

	public static function isBuiltInEvent(name:String):Bool {
		return name != null && builtInEventNames.indexOf(name) >= 0;
	}

	public static function safeName(value:String):Bool {
		if (value == null || value == '' || value == '.' || value == '..'
			|| value.indexOf('/') >= 0 || value.indexOf('\\') >= 0 || value.indexOf(':') >= 0)
			return false;
		return true;
	}

	/** Character IDs may name a file inside nested data/characters folders.
	 * Keep every segment relative and reject Windows/Unix path escapes. */
	public static function safeRelativeName(value:String):Bool {
		if (value == null || value == '' || value.indexOf('\\') >= 0) return false;
		for (part in value.split('/')) if (!safeName(part)) return false;
		return true;
	}

	#if sys
	public static function withinRoot(root:String, path:String):Bool {
		if (root == null || path == null || !FileSystem.exists(root) || !FileSystem.exists(path))
			return false;
		try {
			var base = Path.normalize(FileSystem.fullPath(root));
			var candidate = Path.normalize(FileSystem.fullPath(path));
			return candidate.startsWith(base + '/');
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Exact spelling wins. A single case-insensitive match per path component
	 * is accepted; ambiguous siblings and symlink escapes stay unresolved. */
	public static function scopedResolution(root:String, relative:String):{relative:Null<String>, status:String} {
		return scopedPathResolution(root, relative, false);
	}

	static function scopedDirectoryResolution(root:String, relative:String):{relative:Null<String>, status:String} {
		return scopedPathResolution(root, relative, true);
	}

	static function scopedPathResolution(root:String, relative:String, wantDirectory:Bool):{relative:Null<String>, status:String} {
		if (root == null || !FileSystem.isDirectory(root) || !safeRelativeName(relative))
			return {relative:null, status:'unsafe'};
		var current = root;
		var chosen:Array<String> = [];
		var parts = relative.split('/');
		for (i in 0...parts.length) {
			var part = parts[i];
			var exact = Path.join([current, part]);
			var selected = part;
			if (!FileSystem.exists(exact)) {
				var matches:Array<String> = [];
				try for (entry in FileSystem.readDirectory(current))
					if (safeName(entry) && entry.toLowerCase() == part.toLowerCase()) matches.push(entry)
				catch (_:Dynamic) return {relative:null, status:'missing'};
				if (matches.length != 1)
					return {relative:null, status:matches.length == 0 ? 'missing' : 'ambiguous'};
				selected = matches[0];
			}
			current = Path.join([current, selected]);
			if (!FileSystem.exists(current)) return {relative:null, status:'missing'};
			if (!withinRoot(root, current)) return {relative:null, status:'escape'};
			if (i < parts.length - 1 && !FileSystem.isDirectory(current))
				return {relative:null, status:'missing'};
			chosen.push(selected);
		}
		var isDirectory = FileSystem.isDirectory(current);
		if (isDirectory != wantDirectory) return {relative:null, status:'missing'};
		return {relative:chosen.join('/'), status:'ok'};
	}

	public static function resolveScopedRelative(root:String, relative:String):Null<String> {
		return scopedResolution(root, relative).relative;
	}

	/** Resolve an owner-relative directory using the same case and symlink
		checks as individual scoped files. */
	public static function resolveScopedDirectory(root:String,
		relative:String):{relative:Null<String>, status:String} {
		#if sys
		return scopedDirectoryResolution(root, relative);
		#else
		return {relative:null, status:'unavailable'};
		#end
	}

	/** Script-created Character IDs may be computed from arrays or callbacks,
	 * so chart references alone cannot inventory an owner's character library.
	 * Scan just the flat definition directory and keep the same root boundary. */
	public static function discoverOwnerCharacterIds(root:String):{ids:Array<String>, diagnostics:Array<String>} {
		var result = {ids:[], diagnostics:[]};
		var folder = scopedDirectoryResolution(root, 'data/characters');
		if (folder.relative == null) {
			if (folder.status != 'missing') result.diagnostics.push('Character directory ' + folder.status);
			return result;
		}
		var absolute = Path.join([root, folder.relative]);
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(absolute) catch (_:Dynamic) {
			result.diagnostics.push('Character directory unreadable');
			return result;
		}
		entries.sort(Reflect.compare);
		if (entries.length > 512)
			result.diagnostics.push('Character directory exceeds 512 entry scan limit');
		var examined = 0;
		var seen:Map<String, Bool> = new Map();
		for (entry in entries) {
			if (examined++ >= 512) break;
			if (!safeName(entry)) continue;
			var extension = Path.extension(entry).toLowerCase();
			if (extension != 'xml' && extension != 'hx') continue;
			var id = Path.withoutExtension(entry);
			var key = id.toLowerCase();
			if (!safeName(id) || seen.exists(key)) continue;
			var path = Path.join([absolute, entry]);
			if (FileSystem.isDirectory(path) || !withinRoot(root, path)) continue;
			seen.set(key, true);
			result.ids.push(id);
		}
		return result;
	}

	public static function discoverCharactersDetailed(root:String, ids:Array<String>):CodenameCharacterDiscovery {
		var result:CodenameCharacterDiscovery = {files:[], diagnostics:[]};
		if (root == null || ids == null) return result;
		var seen:Map<String, Bool> = new Map();
		for (id in ids) {
			if (!safeRelativeName(id)) {
				result.diagnostics.push('Unsafe character ID: ' + id);
				continue;
			}
			for (extension in ['.xml', '.hx']) {
				var resolution = scopedResolution(root, 'data/characters/' + id + extension);
				var relative = resolution.relative;
				if (relative == null && (extension == '.xml' || resolution.status != 'missing'))
					result.diagnostics.push('Character ' + id + extension + ' ' + resolution.status);
				var destination = 'data/characters/' + id + extension;
				if (relative == null || seen.exists(destination)) continue;
				seen.set(destination, true);
				result.files.push({path:Path.join([root, relative]), relative:destination,
					family:extension == '.hx' ? 'character' : 'character-xml', authoredId:id});
			}
		}
		return result;
	}

	public static function discoverCharacters(root:String, ids:Array<String>):Array<CodenameScriptFile> {
		return discoverCharactersDetailed(root, ids).files;
	}

	static function addFiles(root:String, relative:String, family:String,
		output:Array<CodenameScriptFile>, maxFiles:Int = 0):Void {
		var folder = Path.join([root, relative]);
		if (!FileSystem.isDirectory(folder)) return;
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(folder) catch (_:Dynamic) return;
		entries.sort(function(a:String, b:String):Int return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		for (entry in entries) {
			if (maxFiles > 0 && output.length >= maxFiles) break;
			if (!safeName(entry) || !entry.toLowerCase().endsWith('.hx')) continue;
			var path = Path.join([folder, entry]);
			if (!FileSystem.isDirectory(path) && withinRoot(root, path))
				output.push({path:path, relative:relative + '/' + entry, family:family});
		}
	}

	static function appendScopedFile(root:String, relative:String, family:String,
		output:Array<CodenameScriptFile>, seen:Map<String, Bool>):Void {
		var resolution = scopedResolution(root, relative);
		if (resolution.relative == null) return;
		var destination = relative.toLowerCase();
		if (seen.exists(destination)) return;
		seen.set(destination, true);
		output.push({path:Path.join([root, resolution.relative]), relative:relative, family:family});
	}

	static function appendScriptTree(root:String, relative:String, family:String,
		output:Array<CodenameScriptFile>, diagnostics:Array<String>, seen:Map<String, Bool>,
		remaining:Array<Int>, depth:Int):Void {
		if (remaining[0] <= 0) return;
		if (depth > 6) {
			diagnostics.push('[codename-owner-script] recursion limit reached under ' + relative);
			return;
		}
		var resolution = scopedDirectoryResolution(root, relative);
		if (resolution.relative == null) return;
		var folder = Path.join([root, resolution.relative]);
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(folder) catch (_:Dynamic) return;
		entries.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (entry in entries) {
			if (remaining[0] <= 0) {
				diagnostics.push('[codename-owner-script] file limit reached under ' + relative);
				return;
			}
			if (!safeName(entry)) continue;
			var child = Path.join([folder, entry]);
			var childRelative = relative + '/' + entry;
			if (FileSystem.isDirectory(child)) {
				if (withinRoot(root, child))
					appendScriptTree(root, childRelative, family, output, diagnostics, seen, remaining, depth + 1);
				continue;
			}
			if (!entry.toLowerCase().endsWith('.hx') || !withinRoot(root, child)) continue;
			var destination = childRelative.toLowerCase();
			if (seen.exists(destination)) continue;
			seen.set(destination, true);
			output.push({path:child, relative:childRelative, family:family});
			remaining[0]--;
		}
	}

	/** Discover package-level HScript modules without scanning asset/media trees.
	 * Every result remains tied to this one owner root; modules and states are
	 * staged verbatim and parsed only when the matching owner is active. */
	public static function discoverOwnerScriptsDetailed(root:String, song:String):CodenameOwnerScriptDiscovery {
		var discovery:CodenameOwnerScriptDiscovery = {files:[], diagnostics:[]};
		if (root == null || !FileSystem.isDirectory(root)) return discovery;
		var seen:Map<String, Bool> = new Map();
		appendScopedFile(root, 'data/global.hx', 'global', discovery.files, seen);
		var remaining = [256];
		appendScriptTree(root, 'data/scripts', 'module', discovery.files,
			discovery.diagnostics, seen, remaining, 0);
		appendScriptTree(root, 'data/states', 'state', discovery.files,
			discovery.diagnostics, seen, remaining, 0);
		// Codename mods can ship Haxe classes alongside their HScript modules.
		// Keep these verbatim and owner-local; the HScript runtime reports class
		// declarations as unsupported until a safe module loader exists.
		appendScriptTree(root, 'source', 'class', discovery.files,
			discovery.diagnostics, seen, remaining, 0);
		// Codename runs .hx files directly below songs/ for every song. Only
		// inspect immediate files; descending into chart/media folders here would
		// be expensive and would select another song's scripts.
		var globalSongs:Array<CodenameScriptFile> = [];
		addFiles(root, 'songs', 'global-song', globalSongs);
		if (globalSongs.length > 256)
			discovery.diagnostics.push('[codename-owner-script] file limit reached under songs');
		for (i in 0...Std.int(Math.min(globalSongs.length, 256))) {
			var file = globalSongs[i];
			var key = file.relative.toLowerCase();
			if (!seen.exists(key)) {
				seen.set(key, true);
				discovery.files.push(file);
			}
		}
		if (safeName(song)) appendScopedFile(root, 'songs/' + song + '/hud.hx', 'hud',
			discovery.files, seen);
		return discovery;
	}

	/** Discover only installation-level scripts shared by Codename mods. State
	 * scripts stay owner-local because they are launch targets, not inherited
	 * package modules. */
	public static function discoverInstallationScriptsDetailed(root:String):CodenameOwnerScriptDiscovery {
		var discovery:CodenameOwnerScriptDiscovery = {files:[], diagnostics:[]};
		if (root == null || !FileSystem.isDirectory(root)) return discovery;
		var seen:Map<String, Bool> = new Map();
		appendScopedFile(root, 'data/global.hx', 'global', discovery.files, seen);
		var remaining = [256];
		appendScriptTree(root, 'data/scripts', 'module', discovery.files,
			discovery.diagnostics, seen, remaining, 0);
		return discovery;
	}

	public static function discoverOwnerScripts(root:String, song:String):Array<CodenameScriptFile>
		return discoverOwnerScriptsDetailed(root, song).files;

	/** Codename loads one script for each selected chart note type. Resolve only
	 * those names in this content root, in the same extension order as
	 * Script.scriptExtensions (excluding Lua, which the source engine rejects).
	 * Compound .pack files are lowered to their HScript payload and staged as
	 * .hx so the host interpreter receives script text rather than pack framing. */
	public static function discoverNoteTypesDetailed(root:String,
		noteTypes:Dynamic):CodenameOwnerScriptDiscovery {
		var result:CodenameOwnerScriptDiscovery = {files:[], diagnostics:[]};
		if (root == null || !FileSystem.isDirectory(root) || !Std.isOfType(noteTypes, Array))
			return result;
		var seen:Map<String, Bool> = new Map();
		var types:Array<Dynamic> = cast noteTypes;
		for (raw in types) {
			if (!Std.isOfType(raw, String)) continue;
			var authored:String = StringTools.trim(cast raw);
			if (authored == '' || authored.toLowerCase() == 'default note') continue;
			if (!safeName(authored)) {
				result.diagnostics.push('Unsafe Codename note type name: ' + authored);
				continue;
			}
			var key = authored.toLowerCase();
			if (seen.exists(key)) continue;
			seen.set(key, true);
			var selected:CodenameScriptFile = null;
			var obstructed = false;
			for (extension in ['hx', 'hscript', 'hsc', 'hxs', 'pack']) {
				var relative = 'data/notes/' + authored + '.' + extension;
				var resolution = scopedResolution(root, relative);
				if (resolution.relative == null) {
					if (resolution.status != 'missing') {
						result.diagnostics.push('Codename note type script ' + relative + ' ' + resolution.status);
						obstructed = true;
						break;
					}
					continue;
				}
				var path = Path.join([root, resolution.relative]);
				if (extension == 'pack') {
					var parts:Array<String> = [];
					try parts = File.getContent(path).split('________PACKSEP________')
					catch (_:Dynamic) {
						result.diagnostics.push('Codename note type script ' + relative + ' unreadable');
						obstructed = true;
						break;
					}
					if (parts.length < 2 || StringTools.trim(parts[1]) == '') {
						result.diagnostics.push('Codename note type script ' + relative + ' invalid pack');
						obstructed = true;
						break;
					}
					selected = {path:path, relative:'data/notes/' + authored + '.hx',
						family:'note-type', authoredId:authored, embeddedScript:parts[1]};
				} else {
					selected = {path:path, relative:resolution.relative,
						family:'note-type', authoredId:authored};
				}
				break;
			}
			if (!obstructed && selected != null) result.files.push(selected);
		}
		return result;
	}

	public static function discoverNoteTypes(root:String, noteTypes:Dynamic):Array<CodenameScriptFile>
		return discoverNoteTypesDetailed(root, noteTypes).files;

	static function nonemptyFile(root:String, relative:String):Bool {
		var resolved = scopedResolution(root, relative).relative;
		if (resolved == null) return false;
		try return sys.io.File.getContent(Path.join([root, resolved])).trim() != ''
		catch (_:Dynamic) return false;
	}

	/** Upstream loads event scripts only when both the authored chart and
	 * EventsData registry name them. Built-ins are pre-registered; custom
	 * names require a nonempty same-owner .json or .pack schema. */
	public static function discoverEvents(root:String, authoredNames:Array<String>):Array<CodenameScriptFile> {
		return discoverEventsDetailed(root, authoredNames).files;
	}

	/** Discover selected-owner event scripts, decoding Codename .pack files into
	 * data records that the importer stages as ordinary scoped .hx files. */
	public static function discoverEventsDetailed(root:String, authoredNames:Array<String>):CodenameEventDiscovery {
		var discovery:CodenameEventDiscovery = {files:[], diagnostics:[]};
		if (root == null || !FileSystem.isDirectory(root) || authoredNames == null) return discovery;
		var names:Array<String> = [];
		for (name in authoredNames)
			if (safeName(name)) {
				var seen = false;
				for (existing in names)
					if (existing.toLowerCase() == name.toLowerCase()) { seen = true; break; }
				if (!seen) names.push(name);
			}
		names.sort(function(a:String, b:String):Int {
			var lower = Reflect.compare(a.toLowerCase(), b.toLowerCase());
			return lower == 0 ? Reflect.compare(a, b) : lower;
		});
		for (name in names) {
			var scriptRelative = 'data/events/' + name + '.hx';
			var resolvedScript = scopedResolution(root, scriptRelative).relative;
			if (resolvedScript != null) {
				if (!isBuiltInEvent(name)
					&& !nonemptyFile(root, 'data/events/' + name + '.json')
					&& !nonemptyFile(root, 'data/events/' + name + '.pack')) continue;
				discovery.files.push({path:Path.join([root, resolvedScript]), relative:scriptRelative, family:'event'});
				continue;
			}

			var packRelative = 'data/events/' + name + '.pack';
			var resolvedPack = scopedResolution(root, packRelative).relative;
			if (resolvedPack == null) continue;
			var packPath = Path.join([root, resolvedPack]);
			var packContent:String;
			try packContent = sys.io.File.getContent(packPath)
			catch (_:Dynamic) {
				discovery.diagnostics.push('[codename-event-pack] ' + packRelative + ' unreadable-pack');
				continue;
			}
			var decoded = CodenameEventPack.decode(packContent, name);
			if (decoded == null || decoded.pack == null) {
				discovery.diagnostics.push('[codename-event-pack] ' + packRelative + ' '
					+ (decoded == null || decoded.error == null ? 'invalid-pack' : decoded.error));
				continue;
			}
			discovery.files.push({path:packPath, relative:scriptRelative, family:'event-pack', authoredId:name,
				embeddedScript:decoded.pack.script, embeddedSchema:decoded.pack.schema});
		}
		return discovery;
	}

	/** Preserve the same schemas that made selected event scripts eligible. */
	public static function discoverEventSchemas(root:String, authoredNames:Array<String>):Array<CodenameScriptFile> {
		var result:Array<CodenameScriptFile> = [];
		for (script in discoverEvents(root, authoredNames)) {
			var name = script.relative.substr('data/events/'.length);
			name = name.substr(0, name.length - '.hx'.length);
			if (script.family == 'event-pack') {
				// Keep the original package (including its parameter schema and
				// optional icon) beside the staged script for owner-scoped recovery.
				result.push({path:script.path, relative:'data/events/' + name + '.pack', family:'event-schema'});
				continue;
			}
			for (extension in ['.json', '.pack']) {
				var relative = 'data/events/' + name + extension;
				var resolved = scopedResolution(root, relative).relative;
				if (resolved != null && nonemptyFile(root, relative))
					result.push({path:Path.join([root, resolved]), relative:relative, family:'event-schema'});
			}
		}
		return result;
	}

	/** Root is one selected Codename content root, never a set of fallback roots.
	 * Immediate scripts are shared by all difficulties; a matching difficulty
	 * subdirectory may add scripts without loading another difficulty's files. */
	public static function discover(root:String, song:String, difficulties:Array<String>, stage:String):Array<CodenameScriptFile> {
		var result:Array<CodenameScriptFile> = [];
		if (root == null || !FileSystem.isDirectory(root)) return result;
		if (safeName(song)) {
			addFiles(root, 'songs', 'global-song', result, 256);
			var hud = scopedResolution(root, 'songs/' + song + '/hud.hx');
			if (hud.relative != null)
				result.push({path:Path.join([root, hud.relative]), relative:hud.relative, family:'hud'});
			var scripts = 'songs/' + song + '/scripts';
			addFiles(root, scripts, 'song', result);
			if (difficulties != null)
				for (difficulty in difficulties)
					if (safeName(difficulty)) addFiles(root, scripts + '/' + difficulty, 'difficulty', result);
		}
		if (safeName(stage)) {
			var relative = 'data/stages/' + stage + '.hx';
			var path = Path.join([root, relative]);
			if (!FileSystem.exists(path)) {
				var folder = Path.join([root, 'data/stages']);
				if (FileSystem.isDirectory(folder)) {
					var matches:Array<String> = [];
					try {
						for (entry in FileSystem.readDirectory(folder))
							if (safeName(entry) && entry.toLowerCase() == (stage + '.hx').toLowerCase())
								matches.push(entry);
					} catch (_:Dynamic) {}
					if (matches.length == 1) {
						relative = 'data/stages/' + matches[0];
						path = Path.join([root, relative]);
					}
				}
			}
			if (FileSystem.exists(path) && !FileSystem.isDirectory(path) && withinRoot(root, path))
				result.push({path:path, relative:relative, family:'stage'});
		}
		return result;
	}
	#end
}
