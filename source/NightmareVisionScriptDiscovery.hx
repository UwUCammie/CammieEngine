package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** A script file selected by the Nightmare Vision source loader. */
typedef NightmareVisionScriptEntry = {
	var scope:String;
	var name:String;
	/** Absolute donor path. This helper never copies or executes the file. */
	var path:String;
	/** Stable path relative to the selected package or its base assets fallback. */
	var relative:String;
}

/** Read-only, per-chart load plan following the supplied Nightmare Vision loader. */
typedef NightmareVisionScriptPlan = {
	var root:String;
	var baseAssetsRoot:String;
	var song:String;
	var stage:String;
	var scripts:Array<NightmareVisionScriptEntry>;
	/** Source scopes whose complete overlay cannot be known without Mods.globalMods. */
	var coverageNotes:Array<String>;
}

typedef NightmareVisionRootSet = {
	var ownerFirst:Array<String>;
	var enumerationOrder:Array<String>;
	var baseAssets:String;
	var contentOverlay:String;
	var hasGlobalModsContext:Bool;
}

/**
	Discovers supported `.hx`, `.hxs`, and `.hscript` files selected by the
	Nightmare Vision/FunkinScript source loader. It does not interpret Haxe imports
	or execute scripts. Gameplay and persistent plugin scopes have separate plans.
	Dynamic loads, imports, and menu scripts remain explicit inventory gaps.
*/
class NightmareVisionScriptDiscovery {
	static var scriptExtensions:Array<String> = ['.hx', '.hxs', '.hscript'];

	/** Plugins have a package lifetime, separate from the per-chart main group.
	 * Preserve the source's core-before-content enumeration and duplicate names. */
	public static function discoverPlugins(sourceRoot:String):Array<NightmareVisionScriptEntry> {
		var entries:Array<NightmareVisionScriptEntry> = [];
		#if sys
		var roots = resolveRoots(sourceRoot);
		collectImmediateLayers(roots.enumerationOrder, 'scripts/plugins', 'plugin', '', entries, new Map());
		var core = normalize(FileSystem.absolutePath(Path.join([normalize(sourceRoot), '__nmv_core'])));
		for (entry in entries) if (entry.path.startsWith(core + '/'))
			entry.relative = '__nmv_core/' + entry.path.substr(core.length + 1);
		#end
		return entries;
	}

	/**
		Build a read-only source load plan for one chart. `sourceRoot` is the
		selected content package root (or an ordinary game/assets root). The
		optional sidecar can be supplied by a caller; otherwise the selected
		song's `songs/<song>/charts/events.json` is read, with an explicitly
		diagnosed release-layout fallback to `data/events.json`.
	*/
	public static function discover(sourceRoot:String, songName:String, chart:Dynamic,
		?companionEvents:Dynamic, ?parseJson:String->Dynamic):NightmareVisionScriptPlan {
		if (parseJson == null) parseJson = haxe.Json.parse;
		#if sys
		var roots = resolveRoots(sourceRoot);
		#else
		var roots:NightmareVisionRootSet = {ownerFirst:[], enumerationOrder:[], baseAssets:'', contentOverlay:'', hasGlobalModsContext:false};
		#end
		var root = normalize(sourceRoot);
		var plan:NightmareVisionScriptPlan = {
			root:root,
			baseAssetsRoot:roots.baseAssets,
			song:cleanName(songName),
			stage:'',
			scripts:[],
			coverageNotes:[]
		};
		#if sys
		var songData = chartSongData(chart);
		var chartSong = sanitizeSong(stringField(songData, 'song'));
		if (chartSong != '') plan.song = chartSong;
		plan.stage = stringField(songData, 'stage');
		if (plan.stage == '') plan.stage = 'stage';
		if (roots.hasGlobalModsContext == false)
			plan.coverageNotes.push('Paths.listAllFilesInDirectory may include runtime Mods.globalMods layers that are not represented by sourceRoot.');

		var seenPaths:Map<String, Bool> = new Map();
		var entries:Array<NightmareVisionScriptEntry> = [];

		// Stage.runScript runs first and selects the first candidate below.
		var stagePath = resolveFirst(roots.ownerFirst, [
			'data/stages/' + plan.stage + '/script',
			'data/stages/' + plan.stage,
			'stages/' + plan.stage + '/script',
			'stages/' + plan.stage,
			'data/stages/stage'
		]);
		if (stagePath != null)
			addEntry(entries, seenPaths, 'stage', plan.stage, stagePath.path, stagePath.relative);

		// Paths.listAllFilesInDirectory is non-recursive and layers core/base
		// assets before the active content package.
		collectImmediateLayers(roots.enumerationOrder, 'scripts', 'global', '', entries, seenPaths);

		// PlayState creates GF, opponent, then player and loads each character's
		// data/characters/<id> before characters/<id>.
		var girlfriend = stringField(songData, 'gfVersion');
		if (girlfriend == '') girlfriend = stringField(songData, 'player3');
		if (girlfriend == '') girlfriend = 'gf';
		var characterNames = [stringField(songData, 'player2'), stringField(songData, 'player1')];
		if (!stageHidesGirlfriend(roots.ownerFirst, plan.stage, parseJson, plan.coverageNotes)) characterNames.insert(0, girlfriend);
		var seenCharacters:Map<String, Bool> = new Map();
		for (character in characterNames) {
			var name = cleanRelative(character);
			if (name == '' || seenCharacters.exists(name.toLowerCase())) continue;
			seenCharacters.set(name.toLowerCase(), true);
			var selected = resolveFirst(roots.ownerFirst, ['data/characters/' + name, 'characters/' + name]);
			if (selected != null)
				addEntry(entries, seenPaths, 'character', name, selected.path, selected.relative);
		}

		// Source loads immediate song files, then immediate files in its scripts
		// subdirectory. Base assets layer before the active package in both passes.
		if (plan.song != '') {
			var songFolder = plan.song;
			collectImmediateLayers(roots.enumerationOrder, 'songs/' + songFolder, 'song', plan.song,
				entries, seenPaths);
			collectImmediateLayers(roots.enumerationOrder, 'songs/' + songFolder + '/scripts', 'song', plan.song,
				entries, seenPaths);
		}

		// NMV note type scripts are selected only for types used by chart notes.
		var sidecar = companionEvents;
		if (sidecar == null) sidecar = readEventsSidecar(roots, plan.song, plan.coverageNotes, parseJson);
		var references = SourceChartReferences.collect(songData, sidecar, NightmareVisionChartCompat.noteTypeName,
			legacyEventRow, cleanRelative);
		for (noteType in references.noteTypes) {
			var selected = resolveFirst(roots.ownerFirst,
				['data/notetypes/' + noteType, 'notetypes/' + noteType]);
			if (selected != null)
				addEntry(entries, seenPaths, 'notetype', noteType, selected.path, selected.relative);
		}

		for (eventName in references.events) {
			var selected = resolveFirst(roots.ownerFirst,
				['data/events/' + eventName, 'events/' + eventName]);
			if (selected != null)
				addEntry(entries, seenPaths, 'event', eventName, selected.path, selected.relative);
		}
		for (payload in [songData, sidecar])
			for (event in SourceChartReferences.eventRows(payload, legacyEventRow)) {
				if (event.length < 3 || event[0] != 'Change Character' || !Std.isOfType(event[2], String)) continue;
				var name = cleanRelative(cast event[2]);
				if (name == '') continue;
				var selected = resolveFirst(roots.ownerFirst, ['data/characters/' + name, 'characters/' + name]);
				if (selected != null)
					addEntry(entries, seenPaths, 'character_event', name, selected.path, selected.relative);
			}

		// Installed core scripts keep a distinct identity from same-named owner
		// globals. Both layers execute in source enumeration order.
		var installedCore = normalize(FileSystem.absolutePath(Path.join([root, '__nmv_core'])));
		for (entry in entries) if (entry.path.startsWith(installedCore + '/'))
			entry.relative = '__nmv_core/' + entry.path.substr(installedCore.length + 1);
		plan.scripts = entries;
		plan.coverageNotes.push('Runtime initScript calls, imported modules, and contextual menu scripts require separate discovery; persistent plugins use discoverPlugins rather than this per-chart plan.');
		#end
		return plan;
	}

	/** Stable unsupported-script diagnostics for the importer to persist. */
	public static function unsupportedDiagnostics(plan:NightmareVisionScriptPlan):Array<String> {
		var result:Array<String> = [];
		if (plan == null) return result;
		var seen:Map<String, Bool> = new Map();
		if (plan.scripts != null) for (entry in plan.scripts) {
			if (entry == null || entry.relative == null || entry.relative == '') continue;
			appendDiagnostic(result, seen, entry.scope, entry.relative);
		}
		for (note in plan.coverageNotes)
			result.push('[nightmare-vision-script-inventory-incomplete] ' + note);
		return result;
	}

	static function appendDiagnostic(result:Array<String>, seen:Map<String, Bool>, scope:String, relative:String):Void {
		var clean = relative.replace('\\', '/');
		var key = scope + '|' + clean;
		if (seen.exists(key)) return;
		seen.set(key, true);
		result.push('[nightmare-vision-unsupported-script] scope=' + scope + ' path=' + clean);
	}

	#if sys
	static function resolveRoots(sourceRoot:String):NightmareVisionRootSet {
		var owner = normalize(sourceRoot);
		var baseAssets = '';
		var contentOverlay = '';
		if (FileSystem.exists(Path.join([owner, 'assets'])) && FileSystem.isDirectory(Path.join([owner, 'assets'])))
			owner = normalize(Path.join([owner, 'assets']));
		var parts = owner.split('/');
		var installedCore = Path.join([owner, '__nmv_core']);
		if (FileSystem.isDirectory(installedCore) && withinRoot(owner, installedCore)) {
			baseAssets = normalize(installedCore);
		} else if (parts.length >= 3 && parts[parts.length - 2].toLowerCase() == 'content') {
			var gameRoot = parts.slice(0, parts.length - 2).join('/');
			var candidate = Path.join([gameRoot, 'assets']);
			if (FileSystem.isDirectory(candidate)) baseAssets = normalize(candidate);
			var overlay = Path.join([gameRoot, 'content']);
			if (FileSystem.isDirectory(overlay) && normalize(overlay) != owner)
				contentOverlay = normalize(overlay);
		} else if (Path.withoutDirectory(owner).toLowerCase() == 'assets') {
			baseAssets = owner;
			var content = Path.join([Path.directory(owner), 'content']);
			if (FileSystem.isDirectory(content)) contentOverlay = normalize(content);
		}
		var ownerFirst:Array<String> = [];
		var enumerationOrder:Array<String> = [];
		if (owner != '' && FileSystem.isDirectory(owner) && owner != baseAssets) ownerFirst.push(owner);
		if (contentOverlay != '') ownerFirst.push(contentOverlay);
		if (baseAssets != '') {
			ownerFirst.push(baseAssets);
			enumerationOrder.push(baseAssets);
		}
		if (contentOverlay != '') enumerationOrder.push(contentOverlay);
		if (owner != '' && FileSystem.isDirectory(owner) && owner != baseAssets) enumerationOrder.push(owner);
		return {ownerFirst:ownerFirst, enumerationOrder:enumerationOrder, baseAssets:baseAssets,
			contentOverlay:contentOverlay, hasGlobalModsContext:false};
	}

	static function collectImmediateLayers(layers:Array<String>, relativeDirectory:String, scope:String, name:String,
		entries:Array<NightmareVisionScriptEntry>, seen:Map<String, Bool>):Void {
		for (layer in layers) {
			var directory = resolveDirectory(layer, relativeDirectory);
			if (directory == null) continue;
			var files:Array<String>;
			try files = FileSystem.readDirectory(directory) catch (_:Dynamic) continue;
			for (file in files) {
				if (!safeSegment(file) || !isScriptFile(file)) continue;
				var path = Path.join([directory, file]);
				if (FileSystem.isDirectory(path) || !withinRoot(layer, path)) continue;
				var logical = relativeDirectory + '/' + file;
				addEntry(entries, seen, scope, name == '' ? stripExtension(file) : name, path, logical);
			}
		}
	}

	static function addEntry(entries:Array<NightmareVisionScriptEntry>, seen:Map<String, Bool>, scope:String, name:String,
		path:String, relative:String):Void {
		if (path == null || !FileSystem.exists(path) || FileSystem.isDirectory(path)) return;
		var key = canonical(path);
		if (key == '' || seen.exists(key)) return;
		seen.set(key, true);
		entries.push({scope:scope, name:name == null ? '' : name,
			path:normalize(FileSystem.absolutePath(path)), relative:relative.replace('\\', '/')});
	}

	static function resolveFirst(roots:Array<String>, candidates:Array<String>):Null<{path:String, relative:String}> {
		for (candidate in candidates) {
			for (extension in scriptExtensions) {
				for (root in roots) {
					var relative = candidate + extension;
					var path = resolveFile(root, relative);
					if (path != null) return {path:path, relative:relative};
				}
			}
		}
		return null;
	}

	static function resolveFile(root:String, relative:String):Null<String> {
		var path = resolvePath(root, relative, false);
		if (path != null && isScriptFile(path)) return path;
		return null;
	}

	static function resolveDirectory(root:String, relative:String):Null<String> {
		return resolvePath(root, relative, true);
	}

	// The case-insensitive owner walk and the physical containment check are
	// shared with the character and stage loaders.
	static function resolvePath(root:String, relative:String, wantDirectory:Bool):Null<String> {
		return wantDirectory ? SourceOwnerFiles.resolveDirectory(root, relative) : SourceOwnerFiles.resolveFile(root, relative);
	}

	static function withinRoot(root:String, path:String):Bool {
		return SourceOwnerFiles.within(root, path);
	}

	static function canonical(path:String):String {
		return normalize(FileSystem.fullPath(path));
	}

	static function readEventsSidecar(roots:NightmareVisionRootSet, song:String, coverageNotes:Array<String>, parseJson:String->Dynamic):Dynamic {
		if (song == '') return null;
		// Current source code uses charts/events.json. The mounted release bundle
		// also contains data/events.json; keep it as a release-layout fallback.
		for (relative in ['songs/' + song + '/charts/events.json', 'songs/' + song + '/data/events.json']) {
			for (root in roots.ownerFirst) {
				var path = resolvePath(root, relative, false);
				if (path == null) continue;
				if (relative.endsWith('/data/events.json'))
					coverageNotes.push('Release-layout sidecar ' + relative + ' differs from the supplied source charts/events.json lookup.');
				try return parseJson(File.getContent(path)) catch (_:Dynamic) {
					coverageNotes.push('Unable to parse event sidecar ' + relative + ': ' + Std.string(_));
					return null;
				}
			}
		}
		return null;
	}

	static function chartSongData(chart:Dynamic):Dynamic
		return SourceChartReferences.songData(chart);

	static function chartSongName(chart:Dynamic):String {
		return stringField(chartSongData(chart), 'song');
	}

	static function stringField(value:Dynamic, field:String):String {
		if (value == null) return '';
		var result:Dynamic = Reflect.field(value, field);
		if (!Std.isOfType(result, String)) return '';
		return field == 'song' ? cleanName(cast result) : cleanRelative((cast result:String).trim());
	}

	/** Chart.correctFormat pulls old in-section event rows out only when the
	 * chart has no events list; with one, such a row stays a note. */
	static function legacyEventRow(values:Array<Dynamic>, hasEvents:Bool):Bool
		return !hasEvents && values[1] < 0;

	static function isScriptFile(path:String):Bool
		return SourceChartReferences.isScriptFile(path, scriptExtensions);

	static function stripExtension(path:String):String
		return SourceChartReferences.stripScriptExtension(path, scriptExtensions);

	static function safeSegment(value:String):Bool {
		return value != null && value != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0;
	}

	static function cleanRelative(value:String):String {
		var clean = SourceOwnerFiles.cleanRelative(value);
		return clean == null ? '' : clean;
	}

	#end

	static function cleanName(value:String):String {
		if (value == null) return '';
		var cleaned = value.trim();
		if (cleaned == '' || cleaned == '.' || cleaned == '..' || cleaned.indexOf('/') >= 0
			|| cleaned.indexOf('\\') >= 0 || cleaned.indexOf(':') >= 0) return '';
		return cleaned;
	}

	#if sys
	static function stageHidesGirlfriend(roots:Array<String>, stage:String, parseJson:String->Dynamic, coverageNotes:Array<String>):Bool {
		var candidates = ['data/stages/' + stage + '/data.json', 'data/stages/' + stage + '.json',
			'stages/' + stage + '/data.json', 'stages/' + stage + '.json'];
		for (candidate in candidates) {
			for (root in roots) {
				var path = resolvePath(root, candidate, false);
				if (path == null) continue;
				try {
					var data:Dynamic = parseJson(File.getContent(path));
					return Reflect.field(data, 'hide_girlfriend') == true;
				} catch (_:Dynamic) {
					coverageNotes.push('Unable to parse stage metadata ' + candidate + '; girlfriend script selection remains unverified.');
					return false;
				}
			}
		}
		return false;
	}

	#end

	static function sanitizeSong(value:String):String {
		return cleanName(value).toLowerCase().replace(' ', '-');
	}

	static function normalize(value:String):String {
		if (value == null || value == '') return '';
		#if sys
		try return Path.normalize(FileSystem.absolutePath(value)).replace('\\', '/') catch (_:Dynamic) {}
		#end
		return Path.normalize(value).replace('\\', '/');
	}
}
