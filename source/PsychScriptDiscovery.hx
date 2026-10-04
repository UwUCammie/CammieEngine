package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
using StringTools;

/** One source script selected for a Psych/Kade compatibility load. */
typedef PsychScriptPlanEntry = {
	/** global, song, stage, custom_event, or custom_notetype */
	var scope:String;
	/** The chart/event/note-type name which caused the entry to be selected. */
	var name:String;
	/** The original donor path. Discovery never writes this file. */
	var path:String;
}

/** Read-only script load plan for one Psych/Kade chart. */
typedef PsychScriptPlan = {
	var root:String;
	var song:String;
	var stage:String;
	var scripts:Array<PsychScriptPlanEntry>;
}

/**
	Discover the script scopes which belong to one Psych/Kade chart.

	Psych's normal layout has global `scripts/`, song-local `data/<song>/`,
	`stages/`, `custom_events/`, and `custom_notetypes/` directories. Some
	Psych-family packages place the song folder below `data/songData/<song>`;
	Kade also keeps song scripts in the same data tree below `assets/`. The importer
	can pass the scanner's `contentRoot` (either a game root or its `assets`
	directory); this class resolves both spellings case-insensitively.

	Only files which are directly usable by the selected chart are returned:
	global and song folders are inspected at their immediate level, while a
	nested custom event/note-type path is visited only when that exact name is
	referenced by the chart. Disabled/unused directories are therefore not
	loaded accidentally. Returned paths are donor paths and are never edited.
*/
class PsychScriptDiscovery {
	public static inline var GLOBAL:String = 'global';
	public static inline var SONG:String = 'song';
	public static inline var STAGE:String = 'stage';
	public static inline var CUSTOM_EVENT:String = 'custom_event';
	public static inline var CUSTOM_NOTE_TYPE:String = 'custom_notetype';

	// Psych mods use `.hx` for both plain HScript callbacks and compiled Haxe
	// sources. Discovery selects both; PsychHscriptCompat classifies `.hx` before
	// the runtime decides whether it can be executed as a callback.
	static var scriptExtensions:Array<String> = ['.hscript', '.lua', '.hx'];

	/** Build a deterministic read-only plan for one chart.  `companionEvents`
	 * accepts a Psych/FPS `events.json` payload because many donor charts keep
	 * custom-event references outside the chart envelope. */
	public static function discover(root:String, songName:String, ?chart:Dynamic,
		?companionEvents:Dynamic, ?diagnosticSource:String):PsychScriptPlan {
		var plan:PsychScriptPlan = {
			root:normalizePath(root),
			song:cleanName(songName),
			stage:'',
			scripts:[]
		};
		#if sys
		var contentRoots = resolveContentRoots(root);
		if (plan.song == '')
			plan.song = chartSongName(chart);
		var chartData = chartSongData(chart);
		if (chartData != null) {
			var chartStage = stringField(chartData, 'stage');
			if (chartStage != '')
				plan.stage = chartStage;
		}

		var seen:Map<String, Bool> = new Map<String, Bool>();
		var entries:Array<PsychScriptPlanEntry> = [];
		for (contentRoot in contentRoots) {
			collectGlobalScripts(contentRoot, entries, seen);
			collectSongScripts(contentRoot, plan.song, entries, seen);
			if (plan.stage != '')
				collectStageScripts(contentRoot, plan.stage, entries, seen);
		}

		var eventNames:Array<String> = [];
		var noteTypeNames:Array<String> = [];
		// This opt-in forensic path records chart and row coordinates before
		// touching nested section-note arrays. Keep the ordinary walk unchanged
		// so mounted scans pay no per-row diagnostic branch or output cost.
		if (Sys.getEnv('DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE') == '1')
			collectChartReferencesTraced(chartData, eventNames, noteTypeNames,
				diagnosticSource, root, plan.song);
		else
			collectChartReferences(chartData, eventNames, noteTypeNames);
		collectEvents(companionEvents, eventNames);
		for (contentRoot in contentRoots) {
			collectReferencedScripts(contentRoot, 'custom_events', eventNames, CUSTOM_EVENT, entries, seen);
			collectReferencedScripts(contentRoot, 'custom_notetypes', noteTypeNames, CUSTOM_NOTE_TYPE, entries, seen);
		}
		entries.sort(compareEntries);
		plan.scripts = entries;
		#end
		return plan;
	}

	/** Convenience overload when the song name should come from chart.song. */
	public static function discoverChart(root:String, chart:Dynamic):PsychScriptPlan {
		return discover(root, chartSongName(chart), chart);
	}

	/** Return only paths, useful for a runtime loader which already has its own
		ordering/ownership structure. */
	public static function paths(plan:PsychScriptPlan):Array<String> {
		var result:Array<String> = [];
		if (plan == null || plan.scripts == null)
			return result;
		for (entry in plan.scripts)
			if (entry != null && entry.path != null)
				result.push(entry.path);
		return result;
	}

	#if sys
	static function collectGlobalScripts(contentRoot:String, entries:Array<PsychScriptPlanEntry>,
		seen:Map<String, Bool>):Void {
		var scriptsRoot = findDirectory(contentRoot, 'scripts');
		collectImmediateScripts(scriptsRoot, GLOBAL, '', entries, seen);
	}

	static function collectSongScripts(contentRoot:String, songName:String, entries:Array<PsychScriptPlanEntry>,
		seen:Map<String, Bool>):Void {
		if (songName == null || songName == '')
			return;
		var dataRoot = findDirectory(contentRoot, 'data');
		if (dataRoot == null)
			return;
		var songRoot = findDirectory(dataRoot, songName);
		if (songRoot == null) {
			// A few Kade/FPS packages put charts below data/songs/<song>.
			var nested = findDirectory(dataRoot, 'songs');
			if (nested != null)
				songRoot = findDirectory(nested, songName);
		}
		if (songRoot == null) {
			// Psych-family game packages may use data/songData/<song> while keeping
			// their songs/<song> audio and the rest of the engine's usual asset tree.
			var nested = findDirectory(dataRoot, 'songData');
			if (nested != null)
				songRoot = findDirectory(nested, songName);
		}
		collectImmediateScripts(songRoot, SONG, songName, entries, seen);
	}

	static function collectStageScripts(contentRoot:String, stageName:String, entries:Array<PsychScriptPlanEntry>,
		seen:Map<String, Bool>):Void {
		var stagesRoot = findDirectory(contentRoot, 'stages');
		if (stagesRoot == null)
			return;
		var cleanStage = stripScriptExtension(stageName);
		for (path in resolveReferencedFiles(stagesRoot, cleanStage))
			addEntry(entries, seen, STAGE, stageName, path);
	}

	static function collectReferencedScripts(contentRoot:String, directory:String, names:Array<String>, scope:String,
		entries:Array<PsychScriptPlanEntry>, seen:Map<String, Bool>):Void {
		if (names == null || names.length == 0)
			return;
		var scriptsRoot = findDirectory(contentRoot, directory);
		if (scriptsRoot == null)
			return;
		var unique:Map<String, Bool> = new Map<String, Bool>();
		for (name in names) {
			var cleaned = cleanReference(name);
			if (cleaned == '')
				continue;
			var key = cleaned.toLowerCase();
			if (unique.exists(key))
				continue;
			unique.set(key, true);
			for (path in resolveReferencedFiles(scriptsRoot, cleaned))
				addEntry(entries, seen, scope, name, path);
		}
	}

	static function collectImmediateScripts(directory:String, scope:String, name:String,
		entries:Array<PsychScriptPlanEntry>, seen:Map<String, Bool>):Void {
		if (directory == null || !FileSystem.isDirectory(directory))
			return;
		var files = readDirectory(directory);
		for (entry in files) {
			var path = Path.join([directory, entry]);
			if (FileSystem.isDirectory(path) || !isScriptFile(entry))
				continue;
			addEntry(entries, seen, scope, name == '' ? stripScriptExtension(entry) : name, path);
		}
	}

	static function addEntry(entries:Array<PsychScriptPlanEntry>, seen:Map<String, Bool>, scope:String,
		name:String, path:String):Void {
		if (path == null || !FileSystem.exists(path) || FileSystem.isDirectory(path))
			return;
		var canonical = normalizePath(FileSystem.fullPath(path));
		var key = canonical.toLowerCase();
		if (key == '' || seen.exists(key))
			return;
		seen.set(key, true);
		// Canonical paths identify duplicate files, but the caller's mounted
		// path is the runtime asset address. Resolving a symlink here can turn
		// an in-scope asset into an out-of-scope donor path in a runtime overlay.
		entries.push({scope:scope, name:name == null ? '' : name,
			path:normalizePath(FileSystem.absolutePath(path))});
	}

	static function resolveReferencedFiles(directory:String, reference:String):Array<String> {
		var result:Array<String> = [];
		if (directory == null || reference == null || reference == '')
			return result;
		var clean = cleanReference(reference);
		if (clean == '')
			return result;
		var explicitExtension = isScriptFile(clean);
		var parent = directory;
		var stem = clean;
		if (clean.indexOf('/') >= 0) {
			var parts = clean.split('/');
			stem = parts.pop();
			for (part in parts) {
				parent = findDirectory(parent, part);
				if (parent == null)
					return result;
			}
		}
		if (explicitExtension) {
			var exact = findFile(parent, stem);
			if (exact != null && isScriptFile(exact))
				result.push(exact);
			return result;
		}
		var files = readDirectory(parent);
		for (entry in files) {
			var lower = entry.toLowerCase();
			var candidateStem = stripScriptExtension(entry);
			if (candidateStem.toLowerCase() == stem.toLowerCase() && isScriptFile(entry))
				result.push(Path.join([parent, entry]));
		}
		return result;
	}

	static function resolveContentRoots(root:String):Array<String> {
		var result:Array<String> = [];
		var normalized = normalizePath(root);
		if (normalized == '' || !FileSystem.isDirectory(normalized))
			return result;
		var content = normalized;
		var assets = findDirectory(normalized, 'assets');
		if (assets != null && findDirectory(normalized, 'data') == null)
			content = assets;
		addUniqueDirectory(result, content);
		var shared = findDirectory(content, 'shared');
		if (shared != null)
			addUniqueDirectory(result, shared);
		return result;
	}

	static function addUniqueDirectory(result:Array<String>, path:String):Void {
		if (path == null || !FileSystem.isDirectory(path))
			return;
		var key = normalizePath(FileSystem.fullPath(path)).toLowerCase();
		for (existing in result)
			if (normalizePath(FileSystem.fullPath(existing)).toLowerCase() == key)
				return;
		result.push(normalizePath(FileSystem.absolutePath(path)));
	}

	static function findDirectory(parent:String, wanted:String):String {
		if (parent == null || wanted == null || !FileSystem.isDirectory(parent))
			return null;
		var exact = Path.join([parent, wanted]);
		if (FileSystem.isDirectory(exact))
			return normalizePath(exact);
		for (entry in readDirectory(parent)) {
			if (entry.toLowerCase() != wanted.toLowerCase())
				continue;
			var candidate = Path.join([parent, entry]);
			if (FileSystem.isDirectory(candidate))
				return normalizePath(candidate);
		}
		return null;
	}

	static function findFile(parent:String, wanted:String):String {
		if (parent == null || wanted == null || !FileSystem.isDirectory(parent))
			return null;
		for (entry in readDirectory(parent))
			if (entry.toLowerCase() == wanted.toLowerCase())
				return Path.join([parent, entry]);
		return null;
	}

	static function readDirectory(path:String):Array<String> {
		var entries:Array<String> = [];
		try {
			entries = FileSystem.readDirectory(path);
		} catch (_:Dynamic) {
			return entries;
		}
		entries.sort(function(a:String, b:String):Int {
			var lowerA = a.toLowerCase();
			var lowerB = b.toLowerCase();
			if (lowerA < lowerB)
				return -1;
			if (lowerA > lowerB)
				return 1;
			return a < b ? -1 : (a > b ? 1 : 0);
		});
		return entries;
	}

	static function compareEntries(a:PsychScriptPlanEntry, b:PsychScriptPlanEntry):Int {
		var scopeA = scopeOrder(a.scope);
		var scopeB = scopeOrder(b.scope);
		if (scopeA != scopeB)
			return scopeA - scopeB;
		var nameA = (a.name == null ? '' : a.name).toLowerCase();
		var nameB = (b.name == null ? '' : b.name).toLowerCase();
		if (nameA < nameB)
			return -1;
		if (nameA > nameB)
			return 1;
		var pathA = a.path.toLowerCase();
		var pathB = b.path.toLowerCase();
		if (pathA < pathB)
			return -1;
		if (pathA > pathB)
			return 1;
		return a.path < b.path ? -1 : (a.path > b.path ? 1 : 0);
	}

	static function scopeOrder(scope:String):Int {
		return switch (scope) {
			case GLOBAL: 0;
			case SONG: 1;
			case STAGE: 2;
			case CUSTOM_EVENT: 3;
			case CUSTOM_NOTE_TYPE: 4;
			default: 5;
		};
	}

	static function collectChartReferences(chartData:Dynamic, eventNames:Array<String>, noteTypeNames:Array<String>):Void {
		if (chartData == null)
			return;
		collectEvents(field(chartData, 'events'), eventNames);
		var notes:Dynamic = field(chartData, 'notes');
		if (!Std.isOfType(notes, Array))
			return;
		for (section in (cast notes:Array<Dynamic>)) {
			var rows:Dynamic = field(section, 'sectionNotes');
			if (!Std.isOfType(rows, Array))
				continue;
			for (row in (cast rows:Array<Dynamic>)) {
				if (!Std.isOfType(row, Array))
					continue;
				var values:Array<Dynamic> = cast row;
				if (values.length >= 2 && numericInt(values[1]) == -1 && values.length >= 3)
					addReference(eventNames, values[2]);
				if (values.length >= 4 && Std.isOfType(values[3], String))
					addNoteType(noteTypeNames, values[3]);
			}
		}
	}

	/** Same chart walk as collectChartReferences with opt-in provenance markers
	 * for the native mounted-corpus scanner. The separate method leaves the
	 * default hot path without per-row trace checks. */
	static function collectChartReferencesTraced(chartData:Dynamic, eventNames:Array<String>,
		noteTypeNames:Array<String>, diagnosticSource:String, root:String, song:String):Void {
		// Emit the expensive source identity once. Subsequent coordinates belong
		// to this chart until the next chart header in this synchronous traversal.
		traceChartReference('chart', diagnosticSource, root, song, -1, -1, 'begin');
		if (chartData == null)
			return;
		collectEvents(field(chartData, 'events'), eventNames);
		var notes:Dynamic = field(chartData, 'notes');
		if (!Std.isOfType(notes, Array))
			return;
		var sectionIndex = 0;
		for (section in (cast notes:Array<Dynamic>)) {
			traceChartReference('section', null, null, null, sectionIndex, -1, 'begin');
			var rows:Dynamic = field(section, 'sectionNotes');
			if (!Std.isOfType(rows, Array)) {
				sectionIndex++;
				continue;
			}
			var rowIndex = 0;
			for (row in (cast rows:Array<Dynamic>)) {
				// Flush before any row dereference so a native fault retains its
				// coordinates. Per-index markers altered scan cost substantially.
				traceChartReference('row', null, null, null, sectionIndex, rowIndex++,
					'before-typecheck');
				if (!Std.isOfType(row, Array))
					continue;
				var values:Array<Dynamic> = cast row;
				if (values.length >= 2 && numericInt(values[1]) == -1 && values.length >= 3)
					addReference(eventNames, values[2]);
				if (values.length >= 4 && Std.isOfType(values[3], String))
					addNoteType(noteTypeNames, values[3]);
			}
			sectionIndex++;
		}
	}

	static function traceChartReference(phase:String, diagnosticSource:String, root:String, song:String,
		sectionIndex:Int, rowIndex:Int, detail:String):Void {
		var output = Sys.stderr();
		var identity = phase == 'chart' ? '|chart=' + diagnosticField(diagnosticSource)
			+ '|root=' + diagnosticField(root) + '|song=' + diagnosticField(song) : '';
		output.writeString('PSYCH_SCRIPT_DISCOVERY|phase=' + diagnosticField(phase) + identity
			+ '|section=' + sectionIndex + '|row=' + rowIndex
			+ '|detail=' + diagnosticField(detail) + '\n');
		output.flush();
	}

	static function diagnosticField(value:String):String {
		if (value == null)
			return '';
		return StringTools.replace(StringTools.replace(StringTools.replace(value, '\\', '\\\\'),
			'|', '\\|'), '\n', '\\n');
	}

	static function collectEvents(value:Dynamic, names:Array<String>):Void {
		if (value == null)
			return;
		if (Std.isOfType(value, Array)) {
			for (item in (cast value:Array<Dynamic>)) {
				if (Std.isOfType(item, Array)) {
					var row:Array<Dynamic> = cast item;
					if (row.length >= 2 && Std.isOfType(row[1], Array)) {
						for (event in (cast row[1]:Array<Dynamic>))
							addEventRecord(names, event);
					} else if (row.length >= 3 && numericInt(row[1]) == -1) {
						addReference(names, row[2]);
					} else
						addEventRecord(names, row);
				} else if (Std.isOfType(item, String))
					addReference(names, item);
				else
					addEventRecord(names, item);
			}
		} else if (Reflect.hasField(value, 'events'))
			collectEvents(Reflect.field(value, 'events'), names);
		else
			addEventRecord(names, value);
	}

	static function addEventRecord(names:Array<String>, record:Dynamic):Void {
		if (record == null)
			return;
		if (Std.isOfType(record, String)) {
			addReference(names, record);
			return;
		}
		if (Std.isOfType(record, Array)) {
			var values:Array<Dynamic> = cast record;
			if (values.length > 0)
				addReference(names, values[0]);
			return;
		}
		// Modern Psych chart records use the compact `e` key (with `t` for
		// time and `v` for values).  Older wrappers use the more descriptive
		// names below.  The discovery plan only needs the event name, but it must
		// recognize both spellings so the corresponding custom_event Lua module
		// is loaded before the first event fires.
		for (fieldName in ['e', 'name', 'event', 'eventName', 'type']) {
			var value:Dynamic = Reflect.field(record, fieldName);
			if (value != null) {
				addReference(names, value);
				return;
			}
		}
	}

	static function addReference(names:Array<String>, value:Dynamic):Void {
		if (value == null)
			return;
		var text = cleanReference(Std.string(value));
		if (text != '' && names.indexOf(text) < 0)
			names.push(text);
	}

	static function addNoteType(names:Array<String>, value:Dynamic):Void {
		var text = cleanReference(Std.string(value));
		if (text == '')
			return;
		var lower = text.toLowerCase();
		if (lower == 'normal' || lower == 'default' || lower == 'alt' || lower == 'alt animation'
			|| lower == 'gf sing' || lower == 'hurt note' || lower == "can't hit" || lower == 'no animation')
			return;
		if (names.indexOf(text) < 0)
			names.push(text);
	}
	#end

	static function chartSongData(chart:Dynamic):Dynamic {
		if (chart == null)
			return null;
		var nested = field(chart, 'song');
		if (nested != null && !Std.isOfType(nested, String))
			return nested;
		return chart;
	}

	static function chartSongName(chart:Dynamic):String {
		var data = chartSongData(chart);
		return data == null ? '' : stringField(data, 'song');
	}

	static function field(value:Dynamic, name:String):Dynamic {
		return value == null ? null : Reflect.field(value, name);
	}

	static function stringField(value:Dynamic, name:String):String {
		var fieldValue = field(value, name);
		return fieldValue == null ? '' : cleanName(Std.string(fieldValue));
	}

	static function numericInt(value:Dynamic):Int {
		if (value == null)
			return 0;
		var parsed = Std.parseInt(Std.string(value));
		return parsed == null ? 0 : parsed;
	}

	static function cleanName(value:String):String {
		return value == null ? '' : StringTools.trim(value);
	}

	static function cleanReference(value:String):String {
		if (value == null)
			return '';
		var result = StringTools.trim(StringTools.replace(value, '\\', '/'));
		while (result.startsWith('./'))
			result = result.substr(2);
		if (result == '' || result.startsWith('/') || result.indexOf(':') == 1)
			return '';
		for (part in result.split('/'))
			if (part == '' || part == '.' || part == '..')
				return '';
		return result;
	}

	static function stripScriptExtension(value:String):String {
		if (value == null)
			return '';
		var lower = value.toLowerCase();
		for (extension in scriptExtensions)
			if (lower.endsWith(extension))
				return value.substr(0, value.length - extension.length);
		return value;
	}

	static function isScriptFile(value:String):Bool {
		if (value == null)
			return false;
		var lower = value.toLowerCase();
		for (extension in scriptExtensions)
			if (lower.endsWith(extension))
				return true;
		return false;
	}

	static function normalizePath(value:String):String {
		if (value == null || StringTools.trim(value) == '')
			return '';
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		return Path.normalize(clean);
	}
}
