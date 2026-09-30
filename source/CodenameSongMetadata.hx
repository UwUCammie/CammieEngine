package;

import haxe.Json;
import haxe.io.Path;

typedef CodenameSongMetadataData = {
	var version:Int;
	var song:String;
	/** Complete parsed donor meta.json object, including custom fields. */
	var meta:Dynamic;
}

/** Data-only, selected-owner Codename ChartData.meta provenance. */
class CodenameSongMetadata {
	public static inline var FILE_NAME = '__cammie_compat_song_meta.json';
	public static inline var RESOLVED_FILE_NAME = '__cammie_compat_song_meta_resolved.json';
	public static inline var VERSION = 1;

	public static function path(root:String, song:String):String {
		if (root == null || root == '' || !CodenameScriptDiscovery.safeName(song)
			|| StringTools.trim(song) == '') return '';
		return Path.join([root, 'songs', song, FILE_NAME]);
	}

	public static function resolvedPath(root:String, song:String):String {
		if (root == null || root == '' || !CodenameScriptDiscovery.safeName(song)
			|| StringTools.trim(song) == '') return '';
		return Path.join([root, 'songs', song, RESOLVED_FILE_NAME]);
	}

	static function isObject(value:Dynamic):Bool return value != null && Type.typeof(value) == TObject;

	static function validateValue(value:Dynamic):Void {
		if (value == null || Std.isOfType(value, String) || Std.isOfType(value, Bool)) return;
		if (Std.isOfType(value, Int)) return;
		if (Std.isOfType(value, Float)) {
			if (!Math.isFinite(value)) throw 'Invalid Codename song meta number';
			return;
		}
		if (Std.isOfType(value, Array)) {
			for (item in (cast value:Array<Dynamic>)) validateValue(item);
			return;
		}
		if (isObject(value)) {
			for (key in Reflect.fields(value)) validateValue(Reflect.field(value, key));
			return;
		}
		throw 'Invalid Codename song meta value';
	}

	public static function create(song:String, originalMeta:Dynamic):CodenameSongMetadataData {
		if (!CodenameScriptDiscovery.safeName(song) || StringTools.trim(song) == ''
			|| !isObject(originalMeta)) throw 'Invalid Codename song metadata';
		validateValue(originalMeta);
		var authoredName:Dynamic = Reflect.field(originalMeta, 'name');
		// Upstream may use meta.name as a song-path identity distinct from the
		// discovered source folder. The sidecar.song field, not this authored
		// value, binds the record to its selected owner.
		if (authoredName != null && (!Std.isOfType(authoredName, String)
			|| !CodenameScriptDiscovery.safeName(cast authoredName)
			|| StringTools.trim(cast authoredName) == ''))
			throw 'Invalid Codename authored meta name';
		// Clone through JSON so the sidecar never holds a mutable importer object.
		return {version:VERSION, song:song, meta:Json.parse(Json.stringify(originalMeta))};
	}

	public static function stringify(record:CodenameSongMetadataData):String
		return Json.stringify(create(record.song, record.meta));

	public static function parse(raw:String, expectedSong:String):CodenameSongMetadataData {
		if (raw == null || StringTools.trim(raw) == '') throw 'Missing Codename song metadata';
		var decoded:Dynamic = Json.parse(raw);
		if (!isObject(decoded) || !Std.isOfType(Reflect.field(decoded, 'version'), Int)
			|| Reflect.field(decoded, 'version') != VERSION)
			throw 'Invalid Codename song metadata version';
		var record = create(Reflect.field(decoded, 'song'), Reflect.field(decoded, 'meta'));
		if (record.song != expectedSong) throw 'Codename song metadata owner mismatch';
		return record;
	}

	static function fill(value:Dynamic, name:String, fallback:Dynamic):Void {
		if (Reflect.field(value, name) == null) Reflect.setField(value, name, fallback);
	}

	/** Chart defaults from Codename's [Flags] section. Other flags control
	 * engine systems and are intentionally left to their respective adapters. */
	public static function configDefaults(contents:String):Dynamic {
		var defaults:Dynamic = {};
		if (contents == null) return defaults;
		var section = '';
		for (line in contents.split('\n')) {
			line = StringTools.trim(line);
			if (StringTools.startsWith(line, '[') && StringTools.endsWith(line, ']')) {
				section = line.substr(1, line.length - 2);
				continue;
			}
			if (section != 'Flags' || line == '' || StringTools.startsWith(line, '#')
				|| StringTools.startsWith(line, ';')) continue;
			var equals = line.indexOf('=');
			if (equals < 0) continue;
			var key = StringTools.trim(line.substr(0, equals));
			var raw = StringTools.trim(line.substr(equals + 1));
			if (raw.length >= 2 && ((StringTools.startsWith(raw, '"') && StringTools.endsWith(raw, '"'))
				|| (StringTools.startsWith(raw, "'") && StringTools.endsWith(raw, "'"))))
				raw = raw.substr(1, raw.length - 2);
			switch (key) {
				case 'DEFAULT_BPM':
					var value = Std.parseFloat(raw);
					if (Math.isFinite(value)) Reflect.setField(defaults, 'bpm', value);
				case 'DEFAULT_DIFFICULTY': Reflect.setField(defaults, 'difficulty', raw);
				case 'DEFAULT_SCROLL_SPEED':
					var value = Std.parseFloat(raw);
					if (Math.isFinite(value)) Reflect.setField(defaults, 'scrollSpeed', value);
				case 'DEFAULT_STAGE': Reflect.setField(defaults, 'stage', raw);
				case 'DEFAULT_BEATS_PER_MEASURE':
					var value = Std.parseInt(raw);
					if (value != null) Reflect.setField(defaults, 'beatsPerMeasure', value);
				case 'DEFAULT_STEPS_PER_BEAT':
					var value = Std.parseInt(raw);
					if (value != null) Reflect.setField(defaults, 'stepsPerBeat', value);
				case 'DEFAULT_CHARACTER': Reflect.setField(defaults, 'characterFallback', raw);
				case 'DEFAULT_HEALTH_ICON': Reflect.setField(defaults, 'icon', raw);
				case 'DEFAULT_COOP_ALLOWED': Reflect.setField(defaults, 'coopAllowed', raw.toLowerCase() == 'true');
				case 'DEFAULT_OPPONENT_MODE_ALLOWED': Reflect.setField(defaults, 'opponentModeAllowed', raw.toLowerCase() == 'true');
				case 'DEFAULT_COLOR':
					var value = Std.parseInt(raw);
					if (value != null) Reflect.setField(defaults, 'color', value);
				default:
			}
		}
		return defaults;
	}

	static function color(value:Dynamic):Int {
		if (Std.isOfType(value, Int)) return cast value;
		if (Std.isOfType(value, String)) {
			// FlxColor.fromString trims and accepts #/0x RGB or ARGB and
			// its built-in named colors. Keep this pure for metadata validation.
			var literal = StringTools.trim(cast value);
			var digits = StringTools.startsWith(literal, '#') ? literal.substr(1) : literal.substr(2);
			if (~/^(0x|#)[0-9A-Fa-f]{6}$/.match(literal))
				return Std.parseInt('0xFF' + digits);
			if (~/^(0x|#)[0-9A-Fa-f]{8}$/.match(literal))
				return Std.parseInt('0x' + digits);
			switch (literal.toUpperCase()) {
				case 'TRANSPARENT': return 0x00000000;
				case 'WHITE': return 0xFFFFFFFF;
				case 'GRAY': return 0xFF808080;
				case 'BLACK': return 0xFF000000;
				case 'GREEN': return 0xFF008000;
				case 'LIME': return 0xFF00FF00;
				case 'YELLOW': return 0xFFFFFF00;
				case 'ORANGE': return 0xFFFFA500;
				case 'RED': return 0xFFFF0000;
				case 'PURPLE': return 0xFF800080;
				case 'BLUE': return 0xFF0000FF;
				case 'BROWN': return 0xFF8B4513;
				case 'PINK': return 0xFFFFC0CB;
				case 'MAGENTA': return 0xFFFF00FF;
				case 'CYAN': return 0xFF00FFFF;
				default:
			}
		}
		return 0xFF9271FD;
	}

	/** Pinned Codename Chart.loadChartMeta defaults followed by its non-null
	 * chart.meta field overlay. Variant files remain a separate selection. */
	public static function resolve(song:String, fileMeta:Dynamic, inlineMeta:Dynamic,
		chartDifficulties:Array<String>, ?config:Dynamic):Dynamic {
		if (!CodenameScriptDiscovery.safeName(song) || StringTools.trim(song) == ''
			|| !isObject(fileMeta) || (inlineMeta != null && !isObject(inlineMeta))
			|| chartDifficulties == null) throw 'Invalid Codename resolved song metadata';
		validateValue(fileMeta);
		if (inlineMeta != null) validateValue(inlineMeta);
		if (config != null) validateValue(config);
		var meta:Dynamic = Json.parse(Json.stringify(fileMeta));
		var fallback = function(name:String, value:Dynamic):Dynamic {
			var configured = config == null ? null : Reflect.field(config, name);
			return configured == null ? value : configured;
		};
		// Chart.loadChartMeta unconditionally sets name to its songName argument.
		Reflect.setField(meta, 'name', song);
		var authoredColor = Reflect.field(meta, 'color');
		Reflect.setField(meta, 'color', color(authoredColor == null ? fallback('color', null) : authoredColor));
		fill(meta, 'displayName', song);
		fill(meta, 'bpm', fallback('bpm', 100.0));
		fill(meta, 'beatsPerMeasure', fallback('beatsPerMeasure', 4));
		fill(meta, 'stepsPerBeat', fallback('stepsPerBeat', 4));
		fill(meta, 'icon', fallback('icon', 'face'));
		fill(meta, 'coopAllowed', fallback('coopAllowed', false));
		fill(meta, 'opponentModeAllowed', fallback('opponentModeAllowed', false));
		fill(meta, 'instSuffix', '');
		fill(meta, 'vocalsSuffix', '');
		fill(meta, 'needsVoices', true);
		fill(meta, 'variants', []);
		fill(meta, 'metas', {});
		Reflect.setField(meta, 'variant', null);
		var listed:Dynamic = Reflect.field(meta, 'difficulties');
		if (!Std.isOfType(listed, Array) || (cast listed:Array<Dynamic>).length == 0) {
			var names = chartDifficulties.copy();
			if (names.length == 3) {
				var ordered:Array<String> = [];
				for (kind in ['easy', 'normal', 'hard'])
					for (name in names) if (name.toLowerCase() == kind) ordered.push(name);
				if (ordered.length == 3) names = ordered;
			}
			Reflect.setField(meta, 'difficulties', names);
		}
		if (inlineMeta != null)
			for (field in Reflect.fields(inlineMeta)) {
				var value = Reflect.field(inlineMeta, field);
				if (value != null) Reflect.setField(meta, field, Json.parse(Json.stringify(value)));
			}
		return meta;
	}

	static function canonical(value:Dynamic):String {
		if (value == null || !isObject(value) && !Std.isOfType(value, Array)) return Json.stringify(value);
		if (Std.isOfType(value, Array))
			return '[' + [for (item in (cast value:Array<Dynamic>)) canonical(item)].join(',') + ']';
		var keys = Reflect.fields(value);
		keys.sort(Reflect.compare);
		return '{' + [for (key in keys) Json.stringify(key) + ':' + canonical(Reflect.field(value, key))].join(',') + '}';
	}

	/** Additive sibling plan. `selectedFile` is a relative basename only; the
	 * original file and inline chart meta remain available for provenance. */
	static function buildResolved(song:String, chartDifficulties:Array<String>, entries:Dynamic,
		verifyDerived:Bool):Dynamic {
		if (!CodenameScriptDiscovery.safeName(song) || StringTools.trim(song) == ''
			|| chartDifficulties == null || !isObject(entries))
			throw 'Invalid Codename resolved metadata plan';
		var seen:Map<String, Bool> = new Map<String, Bool>();
		var safeNames:Array<String> = [];
		var safeEntries:Dynamic = {};
		for (difficulty in chartDifficulties) {
			if (!CodenameScriptDiscovery.safeName(difficulty) || StringTools.trim(difficulty) == ''
				|| seen.exists(difficulty)) throw 'Invalid Codename metadata difficulty';
			seen.set(difficulty, true);
			safeNames.push(difficulty);
		}
		for (difficulty in safeNames) {
			var entry = Reflect.field(entries, difficulty);
			if (entry == null) continue; // A source chart may fail conversion.
			if (!isObject(entry)) throw 'Invalid Codename metadata difficulty entry';
			var selectedFile:Dynamic = Reflect.field(entry, 'selectedFile');
			if (selectedFile != 'meta.json' && selectedFile != 'meta-' + difficulty + '.json')
				throw 'Invalid Codename metadata source file';
			var fileMeta = Reflect.field(entry, 'fileMeta');
			var inlineMeta = Reflect.field(entry, 'inlineMeta');
			var config = Reflect.field(entry, 'configDefaults');
			var resolved = resolve(song, fileMeta, inlineMeta, safeNames, config);
			var encoded:Dynamic = Reflect.field(entry, 'resolved');
			if (verifyDerived && encoded != null && canonical(encoded) != canonical(resolved))
				throw 'Codename resolved metadata differs from source fields';
			Reflect.setField(safeEntries, difficulty, {selectedFile:selectedFile,
				fileMeta:Json.parse(Json.stringify(fileMeta)),
				inlineMeta:inlineMeta == null ? null : Json.parse(Json.stringify(inlineMeta)),
				configDefaults:config == null ? null : Json.parse(Json.stringify(config)),
				resolved:resolved});
		}
		for (difficulty in Reflect.fields(entries)) if (!seen.exists(difficulty))
			throw 'Unexpected Codename metadata difficulty';
		return {version:VERSION, song:song, chartDifficulties:safeNames, difficulties:safeEntries};
	}

	/** Build importer output and reject a stale derived metadata cache. */
	public static function createResolved(song:String, chartDifficulties:Array<String>, entries:Dynamic):Dynamic
		return buildResolved(song, chartDifficulties, entries, true);

	public static function stringifyResolved(plan:Dynamic):String
		return Json.stringify(createResolved(Reflect.field(plan, 'song'),
			Reflect.field(plan, 'chartDifficulties'), Reflect.field(plan, 'difficulties')));

	public static function parseResolved(raw:String, expectedSong:String):Dynamic {
		if (raw == null || StringTools.trim(raw) == '') throw 'Missing Codename resolved metadata';
		var parsed:Dynamic = Json.parse(raw);
		if (!isObject(parsed) || !Std.isOfType(Reflect.field(parsed, 'version'), Int)
			|| Reflect.field(parsed, 'version') != VERSION)
			throw 'Invalid Codename resolved metadata version';
		// `resolved` is only a derived cache. Recompute it from the retained
		// source metadata when loading so changes to the compatibility defaults
		// cannot make valid imported metadata disappear at runtime.
		var data = buildResolved(Reflect.field(parsed, 'song'),
			Reflect.field(parsed, 'chartDifficulties'), Reflect.field(parsed, 'difficulties'), false);
		if (Reflect.field(data, 'song') != expectedSong)
			throw 'Codename resolved metadata owner mismatch';
		return data;
	}

	/** Caller selects the exact/unique-case difficulty first. */
	public static function selectedResolved(data:Dynamic, difficulty:String):Dynamic {
		if (data == null || !CodenameScriptDiscovery.safeName(difficulty)) return null;
		var entry = Reflect.field(Reflect.field(data, 'difficulties'), difficulty);
		return entry == null ? null : Reflect.field(entry, 'resolved');
	}
}
