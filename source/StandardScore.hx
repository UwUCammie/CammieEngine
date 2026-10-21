package;

/**
	Standardised scoring, modelled on osu!lazer's mania ruleset.

	This module is pure on purpose: it imports nothing, touches no save, no
	option and no engine state, so PlayState, the regression tests and a later
	server-side re-judge (a Python port that has to agree to the last point) all
	run the very same arithmetic. Keep it that way. Anything that needs the game
	(reading a Note, a modifier menu, the save file) belongs to the caller.

	THE FORMULA
	-----------
	total = 150000 * comboProgress + 850000 * accuracy^(2 + 2 * accuracy) * accuracyProgress
	final = round(total * modifierMultiplier)

	A 100% accuracy full combo of the whole chart is exactly 1,000,000 before
	modifier multipliers. `round` is round-half-up (floor(x + 0.5)), not
	banker's rounding. `^` is IEEE pow. log4(x) is ln(x) / ln(4) in doubles.

	Judgement base values: sick 300, good 200, bad 100, shit 50, miss 0. This
	engine has no tier above sick (lazer has a separate 305 Perfect), so 100%
	accuracy means every judged object was a sick.

	accuracy         = sum(base value of judged objects) / (300 * judged objects),
	                   1.0 while nothing is judged yet (lazer's starting value)
	accuracyProgress = judged objects / judgeable objects in the chart (max 1)
	comboProgress    = comboPortion / maximumComboPortion (max 1)
	comboPortion     = sum over judgements of base * min(max(0.5, log4(combo)), log4(400)),
	                   `combo` being the combo right after that judgement
	maximumComboPortion = what an all-sick full combo of the chart yields,
	                   sum for i in 1..N of 300 * min(max(0.5, log4(i)), log4(400))

	Only a miss resets the combo (lazer rule). A shit still extends it, even
	though the on-screen combo counter of this engine resets on a shit.

	WHAT IS JUDGEABLE
	-----------------
	The judgeable total is known before the song starts, from the loaded chart
	plus the note type rules, and is the `total` handed to the Tracker.
	One judgement is owed for each of these objects:

	1. Every authored note head the player is responsible for (a lift note is a
	   head too). Generated hold pieces are not heads.
	2. One hold end per hold: the last generated piece of an authored hold whose
	   head is itself judgeable. It is judged sick when that last piece is carried
	   through, and miss as soon as any piece of the hold is missed or dropped
	   (once per hold, however many pieces follow the first drop). A head missed
	   outright therefore costs two misses (head and hold end), as in lazer.

	An object is NOT judgeable when:
	- the player is not responsible for it: opponent notes in a normal run, every
	  autoplayed note (demo or botplay lanes, Codename cpu lines, Nightmare Vision
	  autoplayed fields). Opponent notes of Solo mode become the player's, and in
	  Duo mode both sides are played, so they count there (those modes are
	  unranked anyway);
	- it is a mine or nuke note, a hurt note (hitCausesMiss), a canMiss note, a
	  note a script or note type marks ignored, or a custom noteInfo.json type
	  with dontCountNote (dontCountNote is also forced on for negative healAmount
	  and for mines and nukes). Hazards never feed the tracker, so touching one
	  costs health but never score.

	Things that are deliberately not judgements: an empty key press (ghost miss)
	and a hazard hit. They change health and the on-screen miss counter but not
	the standardised score, the way pressing an empty lane does nothing in
	lazer mania.

	PlayState describes each chart object with a JudgeableObject and asks
	isJudgeable; a Python port only has to rebuild those descriptors from the
	chart and noteInfo.json.

	RANKS
	-----
	SS when accuracy == 1 (every judged object a sick, zero misses), S >= 95%,
	A >= 90%, B >= 80%, C >= 70%, D below, F for a failed run. Silver variants
	SSH and SH (lazer XH and SH) when a hidden style modifier (Vanish or
	Invisible notes) was active. A, B, C, D have no silver form.

	MODIFIERS
	---------
	The final score is multiplied by the product of the per-modifier values in
	MULTIPLIERS, applied in the fixed order of MULTIPLIER_ORDER (so doubles
	round identically everywhere), with 0.5 applied once for the whole health
	group (Health Loss, Health Gain, Sup. Love, Poison Fright) when any of them
	is set away from its default. Practice, Demo, Solo, Duo and Oppnt. Play make
	a run unranked.

	SCORING_VERSION is stored in the save so saved scores can be migrated once.
**/

/** One chart object, reduced to the facts the judgeable rules need. */
typedef JudgeableObject = {
	/** An authored note head (including lift notes), not a generated hold piece. */
	var isHead:Bool;
	/** The last generated piece of an authored hold. Carries its head's flags. */
	var isHoldEnd:Bool;
	/** The player, not autoplay, is responsible for this object. */
	var played:Bool;
	/** noteInfo.json dontCountNote, or forced by mine, nuke and negative heal. */
	var dontCount:Bool;
	/** ignoreNote: a note the player must not hit. */
	var ignored:Bool;
	var hitCausesMiss:Bool;
	var canMiss:Bool;
	var mine:Bool;
	var nuke:Bool;
}

/** What a save keeps about one scored play (also built by the migration). */
typedef ScoreDetail = {
	/** SCORING_VERSION that produced it. */
	var version:Int;
	/** True when the entry was converted from a pre-standardised save. */
	var migrated:Bool;
	var rank:String;
	/** Judgement counts, -1 when unknown (migrated entries). */
	var sicks:Int;
	var goods:Int;
	var bads:Int;
	var shits:Int;
	var misses:Int;
	var maxCombo:Int;
	/** Judgeable objects in the chart, -1 when unknown. */
	var judgeable:Int;
	/** Product of the modifier multipliers that were applied. */
	var multiplier:Float;
	/** Internal names of the modifiers that were on. */
	var modifiers:Array<String>;
}

class StandardScore {
	public static inline var SCORING_VERSION:Int = 1;
	public static inline var MAX_SCORE:Int = 1000000;
	public static inline var COMBO_WEIGHT:Float = 150000;
	public static inline var ACCURACY_WEIGHT:Float = 850000;
	public static inline var MAX_COMBO_FACTOR:Float = 400;

	public static inline var MISS:Int = 0;
	public static inline var SHIT:Int = 1;
	public static inline var BAD:Int = 2;
	public static inline var GOOD:Int = 3;
	public static inline var SICK:Int = 4;

	/** Highscore.FCLevel.Bad: the lowest level that means "no combo break". */
	public static inline var FC_LEVEL_BAD:Int = 3;
	/** Highscore.FCLevel.Sick. */
	public static inline var FC_LEVEL_SICK:Int = 5;

	static inline var MAX_BASE:Int = 300;

	/** 0.5 for the whole health group, applied once. */
	public static inline var HEALTH_GROUP_MULTIPLIER:Float = 0.5;
	public static final HEALTH_GROUP:Array<String> = ['healthloss', 'healthgain', 'regen', 'degen'];

	/** Order the per-modifier values are multiplied in. */
	public static final MULTIPLIER_ORDER:Array<String> = [
		'mfc', 'gfc', 'fc', 'poison', 'loop', 'flipped', 'snake', 'drunk', 'slow', 'fast', 'accel', 'vanish', 'invis'
	];
	static final MULTIPLIER_VALUES:Array<Float> = [
		1.0, 1.0, 1.0, 1.0, 1.0, 1.02, 1.02, 1.02, 1.0, 1.0, 1.0, 1.04, 1.06
	];
	/** Modifiers that make a run unranked: nothing is saved, results say Unranked. */
	public static final UNRANKED:Array<String> = ['practice', 'demo', 'nos', 'duo', 'oppnt'];
	/** Hidden style modifiers: the silver ranks. */
	public static final HIDDEN:Array<String> = ['vanish', 'invis'];

	static final LOG4:Float = Math.log(4.0);
	static final LOG4_CAP:Float = Math.log(MAX_COMBO_FACTOR) / Math.log(4.0);

	// ------------------------------------------------------------------ judgements

	public static function baseValue(judgement:Int):Int {
		return switch (judgement) {
			case SICK: 300;
			case GOOD: 200;
			case BAD: 100;
			case SHIT: 50;
			default: 0;
		};
	}

	/**
		Map an engine or donor rating name to a judgement. `weight` is the donor's
		accuracy weight (Psych ratingMod, Codename accuracy) used only for names
		that are not the standard five; pass -1 when there is none.
	**/
	public static function judgementFromName(name:String, weight:Float = -1):Int {
		switch (name == null ? '' : name.toLowerCase()) {
			case 'sick' | 'epic' | 'perfect' | 'marvelous':
				return SICK;
			case 'good':
				return GOOD;
			case 'bad':
				return BAD;
			case 'shit' | 'wayoff':
				return SHIT;
			case 'miss':
				return MISS;
			default:
		}
		if (weight < 0)
			return GOOD;
		if (weight >= 0.99)
			return SICK;
		if (weight >= 0.6)
			return GOOD;
		if (weight >= 0.3)
			return BAD;
		if (weight > 0)
			return SHIT;
		return MISS;
	}

	// ------------------------------------------------------------------ combo math

	/** min(max(0.5, log4(combo)), log4(400)) */
	public static function comboFactor(combo:Int):Float {
		if (combo <= 1)
			return 0.5;
		var value = Math.log(combo) / LOG4;
		if (value < 0.5)
			value = 0.5;
		return value > LOG4_CAP ? LOG4_CAP : value;
	}

	/** The combo portion an all-sick full combo of `count` objects earns. */
	public static function maxComboPortion(count:Int):Float {
		var portion:Float = 0;
		for (i in 1...count + 1)
			portion += MAX_BASE * comboFactor(i);
		return portion;
	}

	/** accuracy^(2 + 2 * accuracy) */
	public static function accuracyCurve(accuracy:Float):Float {
		if (accuracy <= 0)
			return 0;
		if (accuracy >= 1)
			return 1;
		return Math.pow(accuracy, 2 + 2 * accuracy);
	}

	public static function roundHalfUp(value:Float):Int {
		return Std.int(Math.floor(value + 0.5));
	}

	/** The unrounded total before the modifier multiplier. */
	public static function totalPoints(accuracy:Float, comboProgress:Float, accuracyProgress:Float):Float {
		var combo = comboProgress < 0 ? 0 : (comboProgress > 1 ? 1 : comboProgress);
		var progress = accuracyProgress < 0 ? 0 : (accuracyProgress > 1 ? 1 : accuracyProgress);
		return COMBO_WEIGHT * combo + ACCURACY_WEIGHT * accuracyCurve(accuracy) * progress;
	}

	public static function finalScore(accuracy:Float, comboProgress:Float, accuracyProgress:Float, multiplier:Float):Int {
		return roundHalfUp(totalPoints(accuracy, comboProgress, accuracyProgress) * multiplier);
	}

	/**
		The score a list of judgements earns in a chart of `total` judgeable
		objects. The reference replay: a server re-judging inputs ends up here.
	**/
	public static function scoreForJudgements(judgements:Array<Int>, total:Int, multiplier:Float = 1.0):Int {
		var tracker = new StandardTracker(total);
		for (judgement in judgements)
			tracker.judge(judgement);
		return tracker.score(multiplier);
	}

	// ------------------------------------------------------------------ judgeable objects

	public static function isJudgeable(o:JudgeableObject):Bool {
		if (!o.isHead && !o.isHoldEnd)
			return false;
		return o.played && !o.dontCount && !o.ignored && !o.hitCausesMiss && !o.canMiss && !o.mine && !o.nuke;
	}

	public static function countJudgeables(objects:Array<JudgeableObject>):Int {
		var count = 0;
		for (o in objects)
			if (isJudgeable(o))
				count++;
		return count;
	}

	// ------------------------------------------------------------------ ranks

	/** Rank from exact integer sums: base total and 300 * judged. */
	public static function rankFromSums(baseSum:Int, maxSum:Int, hidden:Bool = false, failed:Bool = false):String {
		if (failed)
			return 'F';
		if (maxSum <= 0)
			return 'N/A';
		var rank:String;
		if (baseSum >= maxSum)
			rank = 'SS';
		else if (baseSum * 100 >= 95 * maxSum)
			rank = 'S';
		else if (baseSum * 100 >= 90 * maxSum)
			rank = 'A';
		else if (baseSum * 100 >= 80 * maxSum)
			rank = 'B';
		else if (baseSum * 100 >= 70 * maxSum)
			rank = 'C';
		else
			rank = 'D';
		return hidden && (rank == 'SS' || rank == 'S') ? rank + 'H' : rank;
	}

	/**
		Rank from an accuracy percentage (0 to 100). Values are compared at 1e-8
		of a percent so a quotient such as 95 / 100 that lands one ulp short
		still reads as the threshold it is.
	**/
	public static function rankFromPercent(percent:Float, hidden:Bool = false, failed:Bool = false):String {
		if (failed)
			return 'F';
		var scaled = Math.round(percent * 1000000);
		var rank:String;
		if (scaled >= 100000000)
			rank = 'SS';
		else if (scaled >= 95000000)
			rank = 'S';
		else if (scaled >= 90000000)
			rank = 'A';
		else if (scaled >= 80000000)
			rank = 'B';
		else if (scaled >= 70000000)
			rank = 'C';
		else
			rank = 'D';
		return hidden && (rank == 'SS' || rank == 'S') ? rank + 'H' : rank;
	}

	// ------------------------------------------------------------------ modifiers

	/** One modifier's own value (the health group members show 0.5 each). */
	public static function multiplierOf(id:String):Float {
		if (HEALTH_GROUP.indexOf(id) >= 0)
			return HEALTH_GROUP_MULTIPLIER;
		var index = MULTIPLIER_ORDER.indexOf(id);
		return index < 0 ? 1.0 : MULTIPLIER_VALUES[index];
	}

	/** Product of the multipliers of every id in `active`, in canonical order. */
	public static function multiplierFor(active:Array<String>):Float {
		var product:Float = 1.0;
		if (active == null)
			return product;
		for (id in HEALTH_GROUP)
			if (active.indexOf(id) >= 0) {
				product *= HEALTH_GROUP_MULTIPLIER;
				break;
			}
		for (index in 0...MULTIPLIER_ORDER.length)
			if (active.indexOf(MULTIPLIER_ORDER[index]) >= 0)
				product *= MULTIPLIER_VALUES[index];
		return product;
	}

	public static function isUnranked(active:Array<String>):Bool {
		if (active == null)
			return false;
		for (id in UNRANKED)
			if (active.indexOf(id) >= 0)
				return true;
		return false;
	}

	public static function hasHiddenModifier(active:Array<String>):Bool {
		if (active == null)
			return false;
		for (id in HIDDEN)
			if (active.indexOf(id) >= 0)
				return true;
		return false;
	}

	// ------------------------------------------------------------------ migration helpers

	/**
		Score a pre-standardised result is converted to. Only the accuracy and a
		combo proportion are known for an old entry, so the run is treated as
		complete (accuracyProgress 1).
	**/
	public static function migratedScore(accuracy:Float, comboProportion:Float, multiplier:Float):Int {
		var clamped = accuracy < 0 ? 0 : (accuracy > 1 ? 1 : accuracy);
		return finalScore(clamped, comboProportion, 1.0, multiplier);
	}

	/**
		Estimated comboProgress of an old entry that was not a full combo, from
		what PlayPerformance recorded (player notes, misses, longest combo).
		The longest combo is kept as one run and the remaining notes are spread
		evenly over the other `misses` runs. Even spreading is the least a given
		longest combo can have earned, so the estimate stays conservative.
		Returns -1 when the record cannot support an estimate.
	**/
	public static function estimateComboProportion(totalNotes:Int, misses:Int, maxCombo:Int):Float {
		if (totalNotes <= 0 || misses < 0 || maxCombo < 0)
			return -1;
		var longest = maxCombo > totalNotes ? totalNotes : maxCombo;
		var full = maxComboPortion(totalNotes);
		if (full <= 0)
			return -1;
		if (misses == 0)
			return 1.0;
		var rest = totalNotes - longest - misses;
		if (rest < 0)
			rest = 0;
		var portion = maxComboPortion(longest);
		var base = Std.int(rest / misses);
		var extra = rest - base * misses;
		for (run in 0...misses)
			portion += maxComboPortion(base + (run < extra ? 1 : 0));
		var ratio = portion / full;
		return ratio > 1 ? 1 : ratio;
	}

	/** Rank of a migrated entry. Only a recorded top FC level may keep SS. */
	public static function migratedRank(accuracy:Float, fcLevel:Int, hidden:Bool):String {
		var rank = rankFromPercent(accuracy * 100, hidden, false);
		if (fcLevel < FC_LEVEL_SICK) {
			if (rank == 'SS')
				return 'S';
			if (rank == 'SSH')
				return 'SH';
		}
		return rank;
	}
}

/**
	Live scoring state of one play. Feed it one judgement per judgeable object
	and read the score back at any time; it grows during play and reaches its
	full value once every judgeable object has been judged.
**/
class StandardTracker {
	public var total(default, null):Int;
	public var judged(default, null):Int = 0;
	public var sicks(default, null):Int = 0;
	public var goods(default, null):Int = 0;
	public var bads(default, null):Int = 0;
	public var shits(default, null):Int = 0;
	public var misses(default, null):Int = 0;
	public var combo(default, null):Int = 0;
	public var maxCombo(default, null):Int = 0;
	public var baseSum(default, null):Int = 0;
	var comboPortion:Float = 0;
	var maximumPortion:Float;

	public function new(total:Int) {
		this.total = total < 0 ? 0 : total;
		maximumPortion = StandardScore.maxComboPortion(this.total);
	}

	public function judge(judgement:Int):Void {
		judged++;
		var base = StandardScore.baseValue(judgement);
		baseSum += base;
		switch (judgement) {
			case StandardScore.SICK:
				sicks++;
			case StandardScore.GOOD:
				goods++;
			case StandardScore.BAD:
				bads++;
			case StandardScore.SHIT:
				shits++;
			default:
				misses++;
		}
		if (judgement == StandardScore.MISS) {
			combo = 0;
			return;
		}
		combo++;
		if (combo > maxCombo)
			maxCombo = combo;
		comboPortion += base * StandardScore.comboFactor(combo);
	}

	public function accuracy():Float {
		return judged == 0 ? 1.0 : baseSum / (300.0 * judged);
	}

	public function comboProgress():Float {
		if (maximumPortion <= 0)
			return 0;
		var progress = comboPortion / maximumPortion;
		return progress > 1 ? 1 : progress;
	}

	public function accuracyProgress():Float {
		if (total <= 0)
			return 0;
		return judged >= total ? 1.0 : judged / total;
	}

	/** The score so far, with the modifier multiplier applied. */
	public function score(multiplier:Float = 1.0):Int {
		return StandardScore.finalScore(accuracy(), comboProgress(), accuracyProgress(), multiplier);
	}

	/** Rank so far from exact integer sums; 'N/A' until something is judged. */
	public function rank(hidden:Bool = false, failed:Bool = false):String {
		return StandardScore.rankFromSums(baseSum, 300 * judged, hidden, failed);
	}
}
