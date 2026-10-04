package;

/** Pure source score deltas and snapshots for Psych and Nightmare Vision.

	The caller applies these deltas to the host's existing score fields. This
	helper deliberately owns no counters and does not change native scoring.
*/
class SourceScoreLedger {
	static final defaultPsychRatings:Array<Dynamic> = [
		['You Suck!', 0.2], ['Shit', 0.4], ['Bad', 0.5], ['Bruh', 0.6],
		['Meh', 0.69], ['Nice', 0.7], ['Good', 0.8], ['Great', 0.9],
		['Sick!', 1.0], ['Perfect!!', 1.0]
	];

	static function numberField(value:Dynamic, name:String):Float {
		if (value == null) return 0;
		var field:Dynamic = Reflect.field(value, name);
		return field == null ? 0 : cast field;
	}

	static function counterName(rating:Dynamic):String {
		if (rating == null) return '';
		var counter:Dynamic = Reflect.field(rating, 'counter');
		if (counter != null) return Std.string(counter);
		var name:Dynamic = Reflect.field(rating, 'name');
		return name == null ? '' : Std.string(name) + 's';
	}

	/** Return the effects of one accepted, scored head hit. */
	public static function hit(rating:Dynamic, ratingDisabled:Bool = false, cpu:Bool = false,
		nightmare:Bool = false, practice:Bool = false, fieldAuto:Bool = false,
		defaultScoreAddition:Bool = true):Dynamic {
		var sourceAllowsScore:Bool = nightmare ? (!practice && !cpu && !fieldAuto) : !cpu;
		var scoreAllowed:Bool = sourceAllowsScore && (!nightmare || defaultScoreAddition);
		var countersAllowed:Bool = sourceAllowsScore && !ratingDisabled;
		return {
			weight: numberField(rating, 'ratingMod'),
			ratedCounter: ratingDisabled ? 0 : 1,
			counterName: counterName(rating),
			score: scoreAllowed ? Std.int(numberField(rating, 'score')) : 0,
			hits: countersAllowed ? 1 : 0,
			played: countersAllowed ? 1 : 0,
			recalculate: countersAllowed
		};
	}

	/** Return the effects of one committed miss or non-ghost empty press. */
	public static function miss(nightmare:Bool = false, practice:Bool = false,
		ending:Bool = false):Dynamic {
		return {
			score: nightmare && practice ? 0 : -10,
			missDelta: nightmare || !ending ? 1 : 0,
			played: 1,
			recalculate: true
		};
	}

	static function isNightmareRatings(ratingStuff:Array<Dynamic>):Bool {
		if (ratingStuff == null || ratingStuff.length == 0) return false;
		var first = ratingStuff[0];
		return first != null && Reflect.hasField(first, 'name') && Reflect.hasField(first, 'percent');
	}

	static function entryName(entry:Dynamic, nightmare:Bool):String {
		if (nightmare) return Std.string(Reflect.field(entry, 'name'));
		var row:Array<Dynamic> = cast entry;
		return row == null || row.length == 0 ? '' : Std.string(row[0]);
	}

	static function entryThreshold(entry:Dynamic, nightmare:Bool):Float {
		if (nightmare) {
			var value:Dynamic = Reflect.field(entry, 'percent');
			return value == null ? 0 : cast value;
		}
		var row:Array<Dynamic> = cast entry;
		return row == null || row.length < 2 || row[1] == null ? 0 : cast row[1];
	}

	static function ratingName(rating:Float, totalPlayed:Int,
		ratingStuff:Array<Dynamic>, nightmare:Bool):String {
		if (totalPlayed < 1) return '?';
		var last = ratingStuff[ratingStuff.length - 1];
		var result = entryName(last, nightmare);
		if (rating < 1) {
			for (index in 0...ratingStuff.length - 1) {
				if (rating < entryThreshold(ratingStuff[index], nightmare)) {
					result = entryName(ratingStuff[index], nightmare);
					break;
				}
			}
		}
		return result;
	}

	public static function fullCombo(misses:Int, sicks:Int, goods:Int, bads:Int,
		shits:Int, epics:Int, nightmare:Bool):String {
		if (nightmare) {
			var result = '';
			if (epics > 0) result = 'KFC';
			if (sicks > 0) result = 'SFC';
			if (goods > 0) result = 'GFC';
			if (bads > 0 || shits > 0) result = 'FC';
			if (misses > 0 && misses < 10) result = 'SDCB';
			else if (misses >= 10) result = 'Clear';
			return result;
		}

		if (misses == 0) {
			if (bads > 0 || shits > 0) return 'FC';
			if (goods > 0) return 'GFC';
			if (sicks > 0) return 'SFC';
			return '';
		}
		return misses < 10 ? 'SDCB' : 'Clear';
	}

	/** Build the source-facing score/rating fields from current host counters. */
	public static function snapshot(score:Int, misses:Int, hits:Int, totalPlayed:Int,
		totalNotesHit:Float, sicks:Int, goods:Int, bads:Int, shits:Int,
		epics:Int = 0, ?ratingStuff:Array<Dynamic>):Dynamic {
		var nightmare = isNightmareRatings(ratingStuff);
		var tiers = ratingStuff == null ? defaultPsychRatings : ratingStuff;
		var rating = totalPlayed < 1 ? 0.0
			: Math.min(1, Math.max(0, totalNotesHit / totalPlayed));
		return {
			score: score,
			misses: misses,
			hits: hits,
			totalPlayed: totalPlayed,
			totalNotesHit: totalNotesHit,
			sicks: sicks,
			goods: goods,
			bads: bads,
			shits: shits,
			epics: epics,
			rating: rating,
			ratingPercent: rating,
			ratingName: ratingName(rating, totalPlayed, tiers, nightmare),
			ratingFC: fullCombo(misses, sicks, goods, bads, shits, epics, nightmare)
		};
	}
}
