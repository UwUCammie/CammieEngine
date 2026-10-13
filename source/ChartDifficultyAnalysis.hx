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
	var activeSeconds:Float;
	var lethalDangerNotes:Int;
	var missRiskNotes:Int;
	var chordNotes:Int;
	var chordStrain:Float;
	var sustainTapNotes:Int;
	var sustainTapStrain:Float;
	/** Notes whose script takes the player's input away when hit. */
	var mechanicNotes:Int;
	/** Scripted playfield movement estimate, see ChartMechanicScan.modchart. */
	var modchart:Float;
}

/** Pure analysis of normalized charts. Heads count once; sustains keep activity open.
	* Two-second burst windows and active ten-second windows separate bursts from consistency.
	* Never executes donor scripts or guesses their effects from mod/chart names.
	* An optional context carries what a static read of those scripts found. */
class ChartDifficultyAnalysis {
	public static inline var VERSION:Int = 8;
	public static inline var FAST_NPS:Float = 6;
	public static inline var SHADOW_DIFFICULTY:Float = 17;
	public static function number(value:Dynamic, fallback:Float = 0):Float {
		return (Std.isOfType(value, Int) || Std.isOfType(value, Float)) && Math.isFinite(value) ? value : fallback;
	}
	public static function analyze(chart:Dynamic, definitions:Array<Dynamic>, nightmare:Bool = false, ?context:ChartMechanicScan.ChartAnalysisContext):Null<ChartDensity> {
		if (chart == null) return null;
		var song:Dynamic = Reflect.field(chart, 'song');
		if (song == null || !Reflect.isObject(song)) song = chart;
		var sections:Dynamic = Reflect.field(song, 'notes');
		if (!Std.isOfType(sections, Array)) return null;
		var columns = Std.int(number(Reflect.field(song, 'preferredNoteAmount'), 0));
		if (columns <= 0) columns = switch (Reflect.field(song, 'mania')) { case 1: 6; case 2: 9; default: 4; };
		var format:String = Reflect.field(song, 'format');
		var hits:Array<Float> = []; var dangers:Array<Float> = []; var unknown = 0; var end:Float = 0;
		var heads:Array<Dynamic> = []; var activity:Array<Dynamic> = []; var lethal = 0; var dangerWeight:Float = 0; var missRisk = 0; var missWeight:Float = 0;
		var mechanics = 0; var readOnly = 0; var hazardIndex = context == null ? null : context.noteHazards;
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
				var scripted = definition != null && (Reflect.field(definition,'noteHit') != null || Reflect.field(definition,'noteMiss') != null);
				// A statically read note script settles what metadata leaves unknown.
				var hazard:Null<ChartMechanicScan.NoteScriptHazard> = hazardIndex == null || kind == '' ? null : hazardIndex.get(kind.toLowerCase());
				var trap = hazard != null && hazard.avoid && (hazard.inputLock || hazard.damage || hazard.lethal);
				if (danger || trap) {
					if (hazard == null && (scripted || (kind != '' && kind != 'Hurt Note'))) unknown++;
					dangers.push(time); activity.push({start:time-1000, end:time+1000});
					var damage = !danger ? 0.04 : definition == null ? (bank == 3 ? 69 : bank == 1 ? 0.45 : 0.04) : Math.max(Math.max(0,-number(Reflect.field(definition,'damageAmount'),-0.04*number(Reflect.field(definition,'damageMultiplier'),1))), number(Reflect.field(definition,'missHealth')));
					var kills = damage >= 2 || (hazard != null && hazard.lethal);
					if (kills) lethal++;
					var locks = hazard != null && hazard.inputLock;
					if (locks) mechanics++;
					// Losing input costs every note until recovery: between ordinary and lethal damage.
					dangerWeight += kills ? 4 : locks ? 3 : 1 + Math.min(2, damage);
					if (!danger) {
						// A scripted trap still has to be read and steered around, often beside a
						// real note, so it keeps its place in the pattern as well as its hazard.
						var duration = Math.max(0,number(row.length > 2 ? row[2] : null));
						hits.push(time); heads.push({time:time,end:time+duration,lane:Std.int(lane)%columns}); readOnly++;
					}
					continue;
				}
				// Skippable with no consequence: neither a required head nor a hazard.
				if (hazard != null && hazard.avoid) continue;
				if (kind == "Can't Hit" || (definition != null && Reflect.field(definition, 'dontCountNote') == true)) continue;
				if (hazard == null && (scripted || (kind != '' && ['Normal','Alt Animation','GF Sing','No Animation'].indexOf(kind) < 0))) unknown++;
				if (hazard != null && (hazard.inputLock || hazard.lethal || hazard.damage)) {
					// Required, and its script punishes the player around it.
					if (hazard.inputLock) mechanics++;
					missRisk++; missWeight += hazard.lethal ? 4 : hazard.inputLock ? 2 : 1;
				}
				if (definition != null) {
					var missDamage = Math.max(0,number(Reflect.field(definition,'missHealth'),0.04*number(Reflect.field(definition,'damageMultiplier'),1)));
					if (missDamage > 0.1) {missRisk++;missWeight += Math.min(4,missDamage);}
				}
				hits.push(time);
				var duration = Math.max(0,number(row.length > 2 ? row[2] : null));
				heads.push({time:time,end:time+duration,lane:Std.int(lane)%columns});
				activity.push({start:time-1000,end:time+Math.max(1000,duration)});
			}
		}
		hits.sort(Reflect.compare); dangers.sort(Reflect.compare);
		heads.sort(function(a,b) return Reflect.compare(a.time,b.time));
		activity.sort(function(a,b) return Reflect.compare(a.start,b.start));
		// Merge playable intervals. Gaps over two seconds contain no playable activity;
		// holds remain active, and isolated heads retain a two-second denominator.
		var merged:Array<Dynamic> = [];
		for (span in activity) {
			if (merged.length == 0 || span.start > merged[merged.length-1].end) merged.push({start:span.start,end:span.end});
			else merged[merged.length-1].end = Math.max(merged[merged.length-1].end,span.end);
		}
		var active:Float = 0;
		for (span in merged) active += (span.end-span.start)/1000;
		active = Math.max(2,active);
		var seconds = Math.max(2,end/1000); var peak:Float = 0; var left = 0;
		for (right in 0...hits.length) {
			while (hits[right] - hits[left] >= 2000) left++;
			peak = Math.max(peak,(right-left+1)/2);
		}
		var nps = hits.length/active; var hazardRate = dangers.length/active;
		var fastDangers = 0; var right = 0; left = 0;
		for (time in dangers) {
			while (left < hits.length && hits[left] < time-1000) left++;
			if (right < left) right = left;
			while (right < hits.length && hits[right] < time+1000) right++;
			if ((right-left)/2 >= FAST_NPS) fastDangers++;
		}
		// Consistency is measured within active spans, never across removed breaks.
		var sustained:Float = 0; var weighted:Float = 0; var weight:Float = 0;
		left = 0; right = 0;
		for (span in merged) {
			var spanSeconds = Math.max(2,(span.end-span.start)/1000);
			var window = Math.min(10,spanSeconds); var start:Float = span.start;
			while (start < span.end) {
				while (left < hits.length && hits[left] < start) left++;
				if (right < left) right = left;
				while (right < hits.length && hits[right] < Math.min(span.end,start+window*1000)) right++;
				var duration = Math.max(2,Math.min(window,(span.end-start)/1000));
				var rate = (right-left)/duration;
				weighted += rate*rate*duration; weight += duration; start += window*1000;
			}
		}
		sustained = weight == 0 ? 0 : Math.sqrt(weighted/weight);
		var chordNotes = 0; var chordStrain:Float = 0; var tapNotes = 0; var tapStrain:Float = 0;
		var held:Map<Int,Float> = []; var i = 0; left = 0; right = 0;
		while (i < heads.length) {
			var time:Float = heads[i].time; var j = i+1;
			while (j < heads.length && heads[j].time-time <= 1) j++;
			while (left < hits.length && hits[left] < time-1000) left++;
			if (right < left) right = left;
			while (right < hits.length && hits[right] < time+1000) right++;
			var local = (right-left)/2;
			for (lane in held.keys()) if (held.get(lane) <= time) held.remove(lane);
			var lanes:Map<Int,Bool> = []; var longest:Float = 0;
			for (k in i...j) {
				var h = heads[k]; lanes.set(h.lane,true); longest = Math.max(longest,h.end-time);
				for (lane in held.keys()) if (lane != h.lane) {tapNotes++;tapStrain += 1+local/Math.max(1,nps);break;}
			}
			var size = 0; for (_ in lanes.keys()) size++;
			if (size > 1) {
				chordNotes += size;
				chordStrain += (size-1)*size*(1+local/Math.max(1,nps))*(1+Math.min(4,longest/1000)*0.25);
			}
			for (k in i...j) if (heads[k].end > time) {
				var h = heads[k]; held.set(h.lane,Math.max(held.exists(h.lane)?held.get(h.lane):time,h.end));
			}
			i = j;
		}
		chordStrain /= active; tapStrain /= active;
		// Independent pressures compound; scroll speed is deliberately absent.
		var speed = nps*0.65 + sustained*0.25 + Math.sqrt(peak)*0.4;
		var hazards = (dangerWeight+missWeight)/active + fastDangers/active;
		var complexity = Math.sqrt(chordStrain)*0.9 + Math.sqrt(tapStrain)*0.9;
		var pressure = speed*(1+Math.min(0.5,complexity*0.08+hazards*0.06))+complexity+hazards;
		// Convex strain scale: preserve introductory charts, then increase the
		// marginal rating per unit of compound pressure. There is no upper cap.
		var rating = hits.length+dangers.length == 0 ? 0 : Math.max(1, pressure*(1+Math.max(0,pressure-3)/8));
		// Moving, hidden or reversed lanes make every note harder to read. Applied after
		// the convex scale and bounded, because the scripts are read rather than run.
		var modchart = context == null ? 0.0 : Math.max(0, number(context.modchart));
		rating *= 1+Math.min(0.3,modchart*0.075);
		return {version:VERSION, playerNotes:hits.length-readOnly, dangerNotes:dangers.length, unknownKinds:unknown,
			seconds:seconds, activeSeconds:active,nps:nps,peakNps:peak,sustainedNps:sustained,
			dangerPerSecond:hazardRate,dangersInFastSections:fastDangers,lethalDangerNotes:lethal,missRiskNotes:missRisk,
			chordNotes:chordNotes,chordStrain:chordStrain,sustainTapNotes:tapNotes,sustainTapStrain:tapStrain,
			mechanicNotes:mechanics,modchart:rating == 0 ? 0 : modchart,difficulty:rating};
	}

	public static function read(raw:Dynamic):Null<ChartDensity> {
		if (raw == null || Reflect.field(raw, 'version') != VERSION) return null;
		for (field in ['playerNotes','dangerNotes','unknownKinds','seconds','nps','peakNps','sustainedNps','dangerPerSecond','dangersInFastSections','difficulty','activeSeconds','lethalDangerNotes','missRiskNotes','chordNotes','chordStrain','sustainTapNotes','sustainTapStrain','mechanicNotes','modchart']) {
			var value = number(Reflect.field(raw,field), -1);
			if (value < 0) return null;
		}
		return cast raw;
	}
	/** Screenshot-inspired continuous scale: blue, cyan, green, yellow, red, violet, navy, black. */
	public static function color(density:Null<ChartDensity>):Int
		return density == null ? 0xFF8997AD : ratingColor(density.difficulty);
	/** Star colour of a Difficulty Rating; the scale ends at 20. */
	public static function ratingColor(difficulty:Float):Int {
		var stops = [0xFF4290FB,0xFF4BC3F5,0xFF4CFF86,0xFFF5F05D,0xFFFF7468,0xFFF44791,0xFFAE4DC3,0xFF5148CB,0xFF151071,0xFF05020C];
		var position = !Math.isFinite(difficulty) ? 0 : Math.max(0, Math.min(9, difficulty / 20 * 9));
		var i = Std.int(position); if (i == 9) return stops[9];
		var weight = position - i; var a = stops[i]; var b = stops[i+1];
		var r = Std.int(((a >> 16) & 255) * (1-weight) + ((b >> 16) & 255) * weight);
		var g = Std.int(((a >> 8) & 255) * (1-weight) + ((b >> 8) & 255) * weight);
		var blue = Std.int((a & 255) * (1-weight) + (b & 255) * weight);
		return 0xFF000000 | (r << 16) | (g << 8) | blue;
	}
	public static function shadow(density:Null<ChartDensity>):Bool return density != null && density.difficulty >= SHADOW_DIFFICULTY;
	public static function twoDecimals(value:Float):String {
		if (!Math.isFinite(value) || value < 0) return '?';
		// Keep the whole part as Float: uncapped ratings can exceed Int range.
		var whole = Math.ffloor(value); var cents = Std.int(Math.ffloor((value-whole)*100+0.5));
		if (cents == 100) { whole += 1; cents = 0; }
		var text = Std.string(whole); var exponent = text.indexOf('e');
		if (exponent >= 0) return twoDecimals(Std.parseFloat(text.substr(0,exponent)))+text.substr(exponent);
		return text + '.' + StringTools.lpad(Std.string(cents), '0', 2);
	}
	public static function describe(density:Null<ChartDensity>):String {
		if (density == null) return 'Difficulty Rating: awaiting analysis';
		return 'Difficulty Rating ' + twoDecimals(density.difficulty) + '\nNPS ' + twoDecimals(density.nps) + ' / peak ' + twoDecimals(density.peakNps)
			+ ' / consistent ' + twoDecimals(density.sustainedNps)
			+ '\nDanger notes: ' + density.dangerNotes + ' (' + twoDecimals(density.dangerPerSecond) + '/s)'
			+ ' / lethal: ' + density.lethalDangerNotes + '\nChords: ' + density.chordNotes + ' / taps during holds: ' + density.sustainTapNotes
			+ '\nIn fast sections: ' + density.dangersInFastSections
			+ (density.mechanicNotes > 0 ? '\nInput-lock notes: ' + density.mechanicNotes : '')
			+ (density.modchart > 0 ? '\nModchart: ' + ChartMechanicScan.modchartLabel(density.modchart) + ' (' + twoDecimals(density.modchart) + ')' : '')
			+ (density.unknownKinds > 0 ? '\nScripted note behavior: estimated' : '');
	}
}
