package;

using StringTools;

typedef NightmareVisionChartCompatResult = {
	var chart:Dynamic;
	var supported:Bool;
	var diagnostics:Array<String>;
}

/**
	Small chart adapter for the NMV schema documented by its bundled Chart.hx.
	NMV's normalized formats store player/opponent lanes in separate key blocks;
	older unmarked charts are normalized by swapping those blocks on opponent
	sections. This adapter keeps the source engine identity elsewhere in import
	provenance and only translates chart fields the source runtime defines.
*/
class NightmareVisionChartCompat {
	static final NMV_NOTE_TYPES:Array<String> = [
		'', 'Alt Animation', 'Hey!', 'Hurt Note', 'GF Sing', 'No Animation', 'Ghost Note'
	];

	public static function noteTypeName(index:Int):String
		return index >= 0 && index < NMV_NOTE_TYPES.length ? NMV_NOTE_TYPES[index] : '';

	/** Read-only diagnostics for the import/preview path. */
	public static function inspect(chart:Dynamic, ?sourcePath:String):Array<String> {
		return analyze(chart, sourcePath, false).diagnostics;
	}

	/** Convert a parsed JSON chart in memory. Source files are never rewritten. */
	public static function convert(chart:Dynamic, ?sourcePath:String):NightmareVisionChartCompatResult {
		return analyze(chart, sourcePath, true);
	}

	static function analyze(chart:Dynamic, sourcePath:String, apply:Bool):NightmareVisionChartCompatResult {
		var diagnostics:Array<String> = [];
		var supported = true;
		var song:Dynamic = chart == null ? null : Reflect.field(chart, 'song');
		if (song == null || !Std.isOfType(Reflect.field(song, 'notes'), Array)) {
			diagnostics.push(message('nightmare-vision-chart-invalid', sourcePath,
				'expected a song object with a notes array'));
			return {chart:chart, supported:false, diagnostics:diagnostics};
		}

		var rawFormat:Dynamic = Reflect.field(song, 'format');
		var format = rawFormat == null ? '' : StringTools.trim(Std.string(rawFormat)).toLowerCase();
		var exactPsychV1 = format == 'psych_v1';
		var psychV1Family = format.indexOf('psych_v1') >= 0;
		var normalizedLanes = format == 'nmv2' || exactPsychV1;
		// The bundled NMV Chart loader recognizes any `psych_v1` format marker,
		// but only exact `psych_v1` is already lane-normalized. Other members of
		// that family (including psych_v1_convert) follow its legacy lane swap.
		var legacyFormat = format == '' || format == 'psych_1.0'
			|| (psychV1Family && !exactPsychV1);
		if (!normalizedLanes && !legacyFormat) {
			supported = false;
			diagnostics.push(message('nightmare-vision-unsupported-chart-format', sourcePath,
				'format "' + Std.string(rawFormat) + '" is not described by the bundled NMV chart loader; chart fields were retained'));
		}

		var keys = intField(song, 'keys', 4);
		var lanes = intField(song, 'lanes', 2);
		if (keys <= 0) {
			supported = false;
			diagnostics.push(message('nightmare-vision-unsupported-chart-keys', sourcePath,
				'keys must be a positive integer; found ' + keys));
		}
		if (lanes != 2) {
			supported = false;
			diagnostics.push(message('nightmare-vision-unsupported-chart-lanes', sourcePath,
				'the destination supports the two NMV player/opponent fields; found lanes=' + lanes));
		}

		var arrowSkins:Dynamic = Reflect.field(song, 'arrowSkins');
		if (Reflect.field(song, 'trackSwap') == true)
			diagnostics.push(message('nightmare-vision-unsupported-track-swap', sourcePath,
				'NMV trackSwap audio routing is not represented by the destination runtime'));

		var sections:Array<Dynamic> = cast Reflect.field(song, 'notes');
		if (keys > 0 && lanes == 2) {
			for (section in sections) {
				if (section == null)
					continue;
				var beats:Dynamic = Reflect.field(section, 'sectionBeats');
				if (beats != null && !Reflect.hasField(section, 'lengthInSteps') && apply) {
					var beatCount = Std.parseFloat(Std.string(beats));
					if (!Math.isNaN(beatCount) && beatCount > 0)
						Reflect.setField(section, 'lengthInSteps', Std.int(Math.round(beatCount * 4)));
				}
				if (!Reflect.hasField(section, 'lengthInSteps') && apply)
					Reflect.setField(section, 'lengthInSteps', 16);

				var rows:Dynamic = Reflect.field(section, 'sectionNotes');
				if (rows == null || !Std.isOfType(rows, Array))
					continue;
				for (row in (cast rows:Array<Dynamic>)) {
					if (row == null || !Std.isOfType(row, Array))
						continue;
					var values:Array<Dynamic> = cast row;
					if (values.length > 1 && !normalizedLanes && legacyFormat) {
						var lane = Std.parseInt(Std.string(values[1]));
						if (lane != null && lane >= 0 && lane < keys * 2
							&& Reflect.field(section, 'mustHitSection') != true && apply)
							values[1] = (lane + keys) % (keys * 2);
					}
					if (values.length > 3 && values[3] != null && !Std.isOfType(values[3], String)) {
						var typeIndex = Std.parseInt(Std.string(values[3]));
						if (typeIndex != null && typeIndex >= 0 && typeIndex < NMV_NOTE_TYPES.length && apply)
							values[3] = NMV_NOTE_TYPES[typeIndex];
						else if (typeIndex == null || typeIndex < 0 || typeIndex >= NMV_NOTE_TYPES.length)
							diagnostics.push(message('nightmare-vision-unsupported-note-type-index', sourcePath,
								'found note type index ' + Std.string(values[3]) + ' outside the bundled NMV editor table'));
					}
				}
			}
		}

		if (!supported || !apply)
			return {chart:chart, supported:supported, diagnostics:diagnostics};

		// Materialize the source defaults per chart. A selected difficulty that
		// omits them must not inherit a sibling's different key/field count.
		Reflect.setField(song, 'keys', keys);
		Reflect.setField(song, 'lanes', lanes);
		Reflect.setField(song, 'preferredNoteAmount', keys);
		if (arrowSkins == null || (Std.isOfType(arrowSkins, Array)
			&& (cast arrowSkins:Array<Dynamic>).length == 0))
			Reflect.setField(song, 'arrowSkins', [for (_ in 0...lanes) 'default']);
		if (Reflect.field(song, 'trackSwap') == null)
			Reflect.setField(song, 'trackSwap', false);
		if (Reflect.field(song, 'gf') == null || StringTools.trim(Std.string(Reflect.field(song, 'gf'))) == '') {
			var gfVersion:Dynamic = Reflect.field(song, 'gfVersion');
			if (gfVersion == null)
				gfVersion = Reflect.field(song, 'player3');
			if (gfVersion != null)
				Reflect.setField(song, 'gf', gfVersion);
		}
		if (Reflect.field(song, 'needsVoices') == null)
			Reflect.setField(song, 'needsVoices', true);
		if (Reflect.field(song, 'speed') == null)
			Reflect.setField(song, 'speed', 1);
		if (legacyFormat)
			Reflect.setField(song, 'format', 'nmv2');
		return {chart:chart, supported:true, diagnostics:diagnostics};
	}

	static function intField(value:Dynamic, name:String, fallback:Int):Int {
		if (value == null)
			return fallback;
		var parsed = Std.parseInt(Std.string(Reflect.field(value, name)));
		return parsed == null ? fallback : parsed;
	}

	static function message(code:String, sourcePath:String, detail:String):String {
		var result = '[' + code + '] ' + detail;
		if (sourcePath != null && StringTools.trim(sourcePath) != '')
			result += ' (' + sourcePath + ')';
		return result;
	}
}
