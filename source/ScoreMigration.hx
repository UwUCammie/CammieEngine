package;

import StandardScore.ScoreDetail;

/** The score maps of Highscore that the one-time scoring migration reads. */
typedef ScoreMigrationInput = {
	var scores:Map<String, Int>;
	var accuracy:Map<String, Float>;
	var fcLevels:Map<String, Int>;
	var performance:Map<String, PlayPerformance.PlayPerformanceRecord>;
	var modifiers:Map<String, Dynamic>;
	/** Raw scores of entries that were already converted. */
	var legacy:Map<String, Int>;
	var details:Map<String, ScoreDetail>;
}

/** New maps. The input maps are never touched, so a failure leaves the save as it was. */
typedef ScoreMigrationResult = {
	var scores:Map<String, Int>;
	var legacy:Map<String, Int>;
	var details:Map<String, ScoreDetail>;
	/** Entries converted by this call. */
	var migrated:Int;
}

/**
	One-time conversion of saved scores from the old scoring to StandardScore.

	Each entry is converted from what the old save recorded about it: its
	accuracy (a fraction for songs, a percentage for weeks), its FC level, and
	the PlayPerformance record when it has one.

	  comboProportion  1 for any full-combo level (Bad, Good or Sick). Otherwise
	                   estimated from PlayPerformance (longest combo, misses and
	                   player notes, see StandardScore.estimateComboProportion).
	                   Entries without a usable record, and weeks, use 0.5.
	  new score        round((150000 * comboProportion + 850000 * acc^(2 + 2 * acc))
	                   * multiplier), multiplier being the product of the NEW
	                   modifier values for the modifier set the entry recorded
	                   (1.0 when none was recorded), completion assumed.

	The old raw score is kept in `legacy`. An entry that has a legacy value is
	never converted again, so running this twice (or after an interrupted run
	that never stamped the scoring version) converts each entry exactly once.
	Entries that were never played (zero score, accuracy, FC level) stay 0.
**/
class ScoreMigration {
	static inline var UNKNOWN_COMBO:Float = 0.5;
	static final BEST_SCORE_SUFFIX:String = '-best-score';
	static final WEEK_PREFIX:String = 'week-';
	static final CATEGORY_SUFFIXES:Array<String> = ['-best-score', '-recent', '-best-accuracy', '-best-fullcombo'];

	public static function migrate(input:ScoreMigrationInput):ScoreMigrationResult {
		var scores = new Map<String, Int>();
		var legacy = new Map<String, Int>();
		var details = new Map<String, ScoreDetail>();
		for (key in input.scores.keys())
			scores.set(key, input.scores.get(key));
		if (input.legacy != null)
			for (key in input.legacy.keys())
				legacy.set(key, input.legacy.get(key));
		if (input.details != null)
			for (key in input.details.keys())
				details.set(key, input.details.get(key));

		var migrated = 0;
		var convertedHere = new Map<String, Bool>();
		for (key in input.scores.keys()) {
			if (legacy.exists(key) || details.exists(key))
				continue;
			var raw = input.scores.get(key);
			var accuracy = input.accuracy.exists(key) ? input.accuracy.get(key) : 0.0;
			var fcLevel = input.fcLevels.exists(key) ? input.fcLevels.get(key) : 0;
			legacy.set(key, raw);
			if (raw == 0 && accuracy <= 0 && fcLevel <= 0)
				continue;
			var detail = convert(key, raw, accuracy, fcLevel, input);
			scores.set(key, detail.score);
			if (detail.detail != null)
				details.set(key, detail.detail);
			convertedHere.set(key, true);
			migrated++;
		}

		// "best" has no category suffix and always mirrors its own best-score entry.
		for (key in convertedHere.keys()) {
			if (isCategory(key) || isWeek(key))
				continue;
			var sibling = key + BEST_SCORE_SUFFIX;
			if (!convertedHere.exists(sibling) || input.scores.get(sibling) != input.scores.get(key))
				continue;
			scores.set(key, scores.get(sibling));
			if (details.exists(sibling))
				details.set(key, details.get(sibling));
		}
		return {scores: scores, legacy: legacy, details: details, migrated: migrated};
	}

	static function convert(key:String, raw:Int, accuracy:Float, fcLevel:Int,
			input:ScoreMigrationInput):{score:Int, detail:Null<ScoreDetail>} {
		if (isWeek(key)) {
			// Week accuracy was stored as a percentage.
			var fraction = accuracy / 100;
			return {score: StandardScore.migratedScore(fraction, UNKNOWN_COMBO, 1.0), detail: null};
		}
		var performance = PlayPerformance.read(input.performance == null ? null : input.performance.get(key));
		var modifiers = activeModifiers(input.modifiers == null ? null : input.modifiers.get(key));
		var proportion = UNKNOWN_COMBO;
		if (fcLevel >= StandardScore.FC_LEVEL_BAD)
			proportion = 1.0;
		else if (performance != null) {
			var estimate = StandardScore.estimateComboProportion(performance.totalPlayerNotes, performance.misses,
				performance.maxCombo);
			if (estimate >= 0)
				proportion = estimate;
		}
		var multiplier = StandardScore.multiplierFor(modifiers);
		var score = StandardScore.migratedScore(accuracy, proportion, multiplier);
		return {
			score: score,
			detail: {
				version: StandardScore.SCORING_VERSION,
				migrated: true,
				rank: StandardScore.migratedRank(accuracy, fcLevel, StandardScore.hasHiddenModifier(modifiers)),
				sicks: -1,
				goods: -1,
				bads: -1,
				shits: -1,
				misses: performance == null ? -1 : performance.misses,
				maxCombo: performance == null ? -1 : performance.maxCombo,
				judgeable: performance == null ? -1 : performance.totalPlayerNotes,
				multiplier: multiplier,
				modifiers: modifiers
			}
		};
	}

	/** Names of the modifiers a saved modifier object had switched on. */
	public static function activeModifiers(saved:Dynamic):Array<String> {
		var ids:Array<String> = [];
		if (saved == null || !Reflect.isObject(saved))
			return ids;
		for (id in Reflect.fields(saved)) {
			var modifier:Dynamic = Reflect.field(saved, id);
			if (modifier != null && Reflect.isObject(modifier) && Reflect.field(modifier, 'value') == true)
				ids.push(id);
		}
		ids.sort(function(a:String, b:String):Int return a < b ? -1 : (a > b ? 1 : 0));
		return ids;
	}

	static function isWeek(key:String):Bool
		return StringTools.startsWith(key, WEEK_PREFIX);

	static function isCategory(key:String):Bool {
		for (suffix in CATEGORY_SUFFIXES)
			if (StringTools.endsWith(key, suffix))
				return true;
		return false;
	}
}
