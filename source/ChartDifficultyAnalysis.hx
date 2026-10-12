package;

typedef ChartDensity = {
	var version:Int;
	var playerNotes:Int;
	var dangerNotes:Int;
	var unknownKinds:Int;
	var seconds:Float;
	var nps:Float;
	var peakNps:Float;
	var sustainedNps:Float;
	var dangerPerSecond:Float;
	var dangersInFastSections:Int;
	var difficulty:Float;
}

/** Pure analysis of normalized charts. Heads count once; sustains extend duration.
	* Two-second density windows avoid treating a single chord as sustained speed.
	* Never executes donor scripts or guesses their effects from mod/chart names. */
class ChartDifficultyAnalysis {
	public static inline var VERSION:Int = ImportRevision.COMMON_REVISION;
	public static inline var FAST_NPS:Float = 6;
	public static inline var SHADOW_DIFFICULTY:Float = 8;
	public static function number(value:Dynamic, fallback:Float = 0):Float {
		return (Std.isOfType(value, Int) || Std.isOfType(value, Float)) && Math.isFinite(value) ? value : fallback;
	}
	public static function analyze(chart:Dynamic, definitions:Array<Dynamic>, nightmare:Bool = false):Null<ChartDensity> {
		if (chart == null) return null;
		var song:Dynamic = Reflect.field(chart, 'song');
		if (song == null || !Reflect.isObject(song)) song = chart;
		var sections:Dynamic = Reflect.field(song, 'notes');
		if (!Std.isOfType(sections, Array)) return null;
		var columns = Std.int(number(Reflect.field(song, 'preferredNoteAmount'), 0));
		if (columns <= 0) columns = switch (Reflect.field(song, 'mania')) { case 1: 6; case 2: 9; default: 4; };
		var format:String = Reflect.field(song, 'format');
		var hits:Array<Float> = []; var dangers:Array<Float> = []; var unknown = 0; var end:Float = 0;
		var definitionIndex:Map<String, Dynamic> = [];
		if (definitions != null) for (definition in definitions) if (definition != null) {
			var kind = NoteTypeCompat.canonical(Reflect.field(definition, 'sourceNoteType'));
			if (kind != '') definitionIndex.set(kind.toLowerCase(), definition);
		}
		for (section in (cast sections:Array<Dynamic>)) {
			if (section == null) continue;
			var rows:Dynamic = Reflect.field(section, 'sectionNotes');
			if (!Std.isOfType(rows, Array)) continue;
			for (raw in (cast rows:Array<Dynamic>)) {
				if (!Std.isOfType(raw, Array)) continue;
				var row:Array<Dynamic> = cast raw;
				if (row.length < 2) continue;
				var time = number(row[0], -1); var lane = number(row[1], -1);
				if (time < 0 || lane < 0 || lane != Math.floor(lane)) continue;
				end = Math.max(end, time + Math.max(0, number(row.length > 2 ? row[2] : null)));
				var address = nightmare ? ChartNoteOwnership.nightmareVisionAddress(format, Std.int(lane), Reflect.field(section, 'mustHitSection') == true, columns)
					: ChartNoteOwnership.address(format, Std.int(lane), Reflect.field(section, 'mustHitSection') == true, columns);
				if (!address.playerControlled || address.autoPlay) continue;
				var kind = row.length > 3 && NoteTypeCompat.isStringType(row[3]) ? NoteTypeCompat.canonical(row[3]) : '';
				var definition:Dynamic = definitionIndex.get(kind.toLowerCase());
				var bank = Std.int(lane / (columns * 2));
				if (!nightmare && kind == '' && bank >= 5 && definitions != null && bank - 5 < definitions.length) definition = definitions[bank - 5];
				var danger = kind == 'Hurt Note' || (!nightmare && kind == '' && (bank == 1 || bank == 3));
				if (definition != null) danger = danger || Reflect.field(definition, 'hitCausesMiss') == true
					|| Reflect.field(definition, 'avoidAutoHit') == true || number(Reflect.field(definition, 'damageAmount')) < 0;
				if (danger) { dangers.push(time); continue; }
				if (kind == "Can't Hit" || (definition != null && Reflect.field(definition, 'dontCountNote') == true)) continue;
				if (kind != '' && ['Normal','Alt Animation','GF Sing','No Animation'].indexOf(kind) < 0) unknown++;
				hits.push(time);
			}
		}
		hits.sort(Reflect.compare); dangers.sort(Reflect.compare);
		var seconds = Math.max(2, end / 1000); var peak:Float = 0; var left = 0;
		for (right in 0...hits.length) {
			while (hits[right] - hits[left] >= 2000) left++;
			peak = Math.max(peak, (right - left + 1) / 2);
		}
		var fastDangers = 0; left = 0; var right = 0;
		for (time in dangers) {
			while (left < hits.length && hits[left] < time - 1000) left++;
			if (right < left) right = left;
			while (right < hits.length && hits[right] < time + 1000) right++;
			if ((right - left) / 2 >= FAST_NPS) fastDangers++;
		}
		var nps = hits.length / seconds; var hazardRate = dangers.length / seconds;
		// Time-weighted ten-second windows: short bursts remain visible as peak NPS,
		// while sustained speed contributes to the displayed difficulty rating.
		var window = Math.min(10, seconds); var rates:Array<Float> = [];
		var step = Math.max(1, seconds / 4096); var start:Float = 0; left = 0; right = 0;
		while (start <= seconds - window) {
			while (left < hits.length && hits[left] < start * 1000) left++;
			if (right < left) right = left;
			while (right < hits.length && hits[right] <= (start + window) * 1000) right++;
			rates.push((right - left) / window); start += step;
		}
		rates.sort(Reflect.compare);
		var sustained = rates.length == 0 ? nps : rates[Std.int(Math.max(0, Math.ceil(rates.length * 0.9) - 1))];
		return {version:VERSION, playerNotes:hits.length, dangerNotes:dangers.length, unknownKinds:unknown,
			seconds:seconds, nps:nps, peakNps:peak, sustainedNps:sustained, dangerPerSecond:hazardRate, dangersInFastSections:fastDangers,
			difficulty:(nps * 0.7 + sustained * 0.3 + Math.min(2, hazardRate + fastDangers / seconds * 2)) / 2};
	}
	public static function read(raw:Dynamic):Null<ChartDensity> {
		if (raw == null || Reflect.field(raw, 'version') != VERSION) return null;
		for (field in ['playerNotes','dangerNotes','unknownKinds','seconds','nps','peakNps','sustainedNps','dangerPerSecond','dangersInFastSections','difficulty']) {
			var value = number(Reflect.field(raw,field), -1);
			if (value < 0) return null;
		}
		return cast raw;
	}
	/** Screenshot-inspired continuous scale: blue, cyan, green, yellow, red, violet, navy, black. */
	public static function color(density:Null<ChartDensity>):Int {
		if (density == null) return 0xFF8997AD;
		var stops = [0xFF4290FB,0xFF4BC3F5,0xFF4CFF86,0xFFF5F05D,0xFFFF7468,0xFFF44791,0xFFAE4DC3,0xFF5148CB,0xFF151071,0xFF05020C];
		var position = Math.max(0, Math.min(9, density.difficulty));
		var i = Std.int(position); if (i == 9) return stops[9];
		var weight = position - i; var a = stops[i]; var b = stops[i+1];
		var r = Std.int(((a >> 16) & 255) * (1-weight) + ((b >> 16) & 255) * weight);
		var g = Std.int(((a >> 8) & 255) * (1-weight) + ((b >> 8) & 255) * weight);
		var blue = Std.int((a & 255) * (1-weight) + (b & 255) * weight);
		return 0xFF000000 | (r << 16) | (g << 8) | blue;
	}
	public static function shadow(density:Null<ChartDensity>):Bool return density != null && density.difficulty >= SHADOW_DIFFICULTY;
	public static function twoDecimals(value:Float):String {
		var rounded = Math.round(value * 100); var whole = Std.int(rounded / 100);
		return whole + '.' + StringTools.lpad(Std.string(rounded % 100), '0', 2);
	}
	public static function describe(density:Null<ChartDensity>):String {
		if (density == null) return 'Density: awaiting analysis';
		return 'NPS ' + twoDecimals(density.nps) + ' / peak ' + twoDecimals(density.peakNps)
			+ '\nDanger notes: ' + density.dangerNotes + ' (' + twoDecimals(density.dangerPerSecond) + '/s)'
			+ '\nIn fast sections: ' + density.dangersInFastSections + (density.unknownKinds > 0 ? '\nScripted note behavior: estimated' : '');
	}
}
