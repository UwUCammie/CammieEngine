package;

/** Owner-scoped implementation of Codename's static Chart.parse API.
 * Imported source chart files are parsed in place when present. This importer
 * stores converted gameplay charts plus authored metadata sidecars, so the
 * fallback keeps those exact metadata values and labels converted chart data
 * explicitly rather than presenting it as original Codename strumlines.
 */
class CodenameChartCompat {
	public static function facade(paths:CodenamePaths):Dynamic {
		if (paths == null) throw '[codename-chart] Missing selected-owner Paths context';
		return {
			parse:function(songName:String, ?difficulty:String, ?variant:String):Dynamic
				return parse(paths, songName, difficulty, variant)
		};
	}

	static function safeName(value:String):Bool {
		return value != null && StringTools.trim(value) != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0
			&& value.indexOf('\u0000') < 0;
	}

	static function read(paths:CodenamePaths, relative:String):Null<String> {
		try return FNFAssets.getText(paths.file(relative)) catch (_:Dynamic) return null;
	}

	static function parse(paths:CodenamePaths, songName:String,
		difficulty:String, variant:String):Dynamic {
		var song = songName == null ? '' : StringTools.trim(songName);
		var diff = difficulty == null || StringTools.trim(difficulty) == ''
			? configuredDefaultDifficulty(paths) : StringTools.trim(difficulty);
		var cleanVariant = variant == null || StringTools.trim(variant) == '' ? null : StringTools.trim(variant);
		if (!safeName(song) || !safeName(diff) || (cleanVariant != null && !safeName(cleanVariant)))
			throw '[codename-chart] Song, difficulty, and variant must be safe owner-relative names';

		var sourcePaths = chartPaths(song, diff, cleanVariant);
		for (relative in sourcePaths) {
			var contents = read(paths, relative);
			if (contents == null) continue;
			var source:Dynamic;
			try source = haxe.Json.parse(contents) catch (error:Dynamic)
				throw '[codename-chart] Could not parse selected-owner chart ' + relative + ': ' + Std.string(error);
			var meta = loadMeta(paths, song, diff, cleanVariant);
			var chart = CodenameChartDataCompat.fromSource(song, diff, cleanVariant, source, meta,
				loadConfigDefaults(paths));
			normalizeLegacyEvents(chart);
			mergeGlobalEvents(paths, song, cleanVariant, chart);
			return chart;
		}

		if (cleanVariant != null)
			throw '[codename-chart] Variant chart was not imported or retained for ' + song + ' (' + cleanVariant + ')';
		return parseConvertedChart(paths, song, diff);
	}

	static function chartPaths(song:String, difficulty:String, variant:String):Array<String> {
		var roots = ['songs/' + song, 'assets/songs/' + song];
		var result:Array<String> = [];
		for (root in roots) {
			result.push(root + '/charts/' + (variant == null ? '' : variant + '/') + difficulty + '.json');
		}
		return result;
	}

	static function configuredDefaultDifficulty(paths:CodenamePaths):String {
		var configured:Dynamic = Reflect.field(loadConfigDefaults(paths), 'difficulty');
		return configured != null && safeName(Std.string(configured))
			? Std.string(configured) : 'normal';
	}

	static function loadMeta(paths:CodenamePaths, song:String, difficulty:String,
		variant:String):Dynamic {
		if (variant == null) {
			var resolvedPath = CodenameSongMetadata.resolvedPath(paths.root, song);
			var resolvedText = resolvedPath == '' ? null : read(paths,
				'songs/' + song + '/' + CodenameSongMetadata.RESOLVED_FILE_NAME);
			if (resolvedText != null) try {
				var resolved = CodenameSongMetadata.parseResolved(resolvedText, song);
				var selected = CodenameSongMetadata.selectedResolved(resolved, difficulty);
				if (selected != null) return selected;
		} catch (error:Dynamic) {
			throw '[codename-chart] Invalid resolved metadata for ' + song + ' (' + difficulty + '): '
				+ Std.string(error);
			}
		}

		var candidates:Array<String> = [];
		if (variant != null) {
			candidates.push('songs/' + song + '/meta-' + variant + '-' + difficulty + '.json');
			candidates.push('songs/' + song + '/meta-' + variant + '.json');
		}
		candidates.push('songs/' + song + '/meta-' + difficulty + '.json');
		candidates.push('songs/' + song + '/meta.json');
		var fileMeta:Dynamic = null;
		for (relative in candidates) {
			var contents = read(paths, relative);
			if (contents == null) continue;
			try {
				fileMeta = haxe.Json.parse(contents);
				break;
			} catch (error:Dynamic) {
				throw '[codename-chart] Could not parse metadata ' + relative + ': ' + Std.string(error);
			}
		}
		if (fileMeta == null) {
			var compatPath = CodenameSongMetadata.path(paths.root, song);
			var compatText = compatPath == '' ? null : read(paths,
				'songs/' + song + '/' + CodenameSongMetadata.FILE_NAME);
			if (compatText != null) try fileMeta = CodenameSongMetadata.parse(compatText, song).meta
			catch (error:Dynamic) throw '[codename-chart] Invalid authored metadata for ' + song + ': ' + Std.string(error);
		}
		if (fileMeta == null) fileMeta = {};
		var difficulties:Array<String> = [difficulty];
		var listed:Dynamic = Reflect.field(fileMeta, 'difficulties');
		if (Std.isOfType(listed, Array)) {
			var names:Array<String> = [];
			for (item in (cast listed:Array<Dynamic>))
				if (item != null && safeName(Std.string(item))) names.push(Std.string(item));
			if (names.length > 0) difficulties = names;
		}
		var config = loadConfigDefaults(paths);
		return CodenameSongMetadata.resolve(song, fileMeta, null, difficulties, config);
	}

	static function loadConfigDefaults(paths:CodenamePaths):Dynamic {
		for (relative in ['config/engineConfig.ini', 'data/engineConfig.ini', 'engineConfig.ini']) {
			var contents = read(paths, relative);
			if (contents != null) return CodenameSongMetadata.configDefaults(contents);
		}
		return {};
	}

	static function mergeGlobalEvents(paths:CodenamePaths, song:String, variant:String,
		chart:Dynamic):Void {
		var suffix = variant == null ? '' : '-' + variant;
		var contents = read(paths, 'songs/' + song + '/events' + suffix + '.json');
		if (contents == null) return;
		try {
			var raw:Dynamic = haxe.Json.parse(contents);
			var events:Dynamic = Reflect.field(raw, 'events');
			if (!Std.isOfType(events, Array)) return;
			var destination:Array<Dynamic> = cast Reflect.field(chart, 'events');
			for (event in (cast events:Array<Dynamic>)) {
				if (event == null) continue;
				Reflect.setField(event, 'global', true);
				destination.push(event);
			}
		} catch (error:Dynamic) {
			throw '[codename-chart] Could not parse global events for ' + song + ': ' + Std.string(error);
		}
	}

	static function normalizeLegacyEvents(chart:Dynamic):Void {
		var events:Dynamic = Reflect.field(chart, 'events');
		if (!Std.isOfType(events, Array)) return;
		var eventNames:Map<Int, String> = [
			-1 => 'HScript Call', 0 => 'Unknown', 1 => 'Camera Movement',
			2 => 'BPM Change', 3 => 'Alt Animation Toggle'
		];
		for (event in (cast events:Array<Dynamic>)) {
			if (event == null || !Reflect.hasField(event, 'type')) continue;
			var eventType:Dynamic = Reflect.field(event, 'type');
			if (eventType == null) continue;
			if (Std.isOfType(eventType, Int))
				Reflect.setField(event, 'name', eventNames.exists(cast eventType)
					? eventNames.get(cast eventType) : 'Unknown');
			Reflect.deleteField(event, 'type');
		}
	}

	static function parseConvertedChart(paths:CodenamePaths, song:String, difficulty:String):Dynamic {
		var storageFolder = CodenameSongLaunch.resolveStorageFolder(song, paths.root);
		var nativeFileName = difficulty.toLowerCase() == 'normal'
			? storageFolder.toLowerCase() : storageFolder.toLowerCase() + '-' + difficulty.toLowerCase();
		var nativeChart:Dynamic;
		try nativeChart = Song.loadFromJson(nativeFileName, storageFolder) catch (error:Dynamic)
			throw '[codename-chart] No selected-owner source chart or imported gameplay chart for '
				+ song + ' (' + difficulty + '): ' + Std.string(error);
		return CodenameChartDataCompat.fromNative(song, difficulty, null, nativeChart,
			loadMeta(paths, song, difficulty, null));
	}
}
