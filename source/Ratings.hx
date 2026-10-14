import Highscore.FCLevel;
import haxe.display.Display.Package;
import flixel.FlxG;

class Ratings
{
	public static function GenerateLetterRank(accuracy:Float) // generate a letter ranking
	{
		var ranking:String = "N/A";
		if (FlxG.save.data.botplay)
			ranking = "BotPlay";
		switch (CalculateFCRating()) {
			case Sick:
				ranking = "(MFC)";
			case Good:
				ranking = "(GFC)";
			case Bad:
				ranking = "(FC)";
			case Sdcb:
				ranking = "(SDCB)";
			default:
				ranking = "(Clear)";
		}

		// WIFE TIME :)))) (based on Wife3)
		ranking += wifeLetter(accuracy);

		if (accuracy == 0)
			ranking = "N/A";
		else if (FlxG.save.data.botplay)
			ranking = "BotPlay";

		return ranking;
	}

	/**
		The Wife3 letter for an accuracy, with its leading space. The first
		threshold that matches wins. This runs for the score line, so it checks
		the thresholds in order instead of building a table on every call. NaN
		matches none of them and adds nothing, as the table did.
	**/
	static function wifeLetter(accuracy:Float):String
	{
		if (accuracy >= 99.9935) return " AAAAA";
		if (accuracy >= 99.980) return " AAAA:";
		if (accuracy >= 99.970) return " AAAA.";
		if (accuracy >= 99.955) return " AAAA";
		if (accuracy >= 99.90) return " AAA:";
		if (accuracy >= 99.80) return " AAA.";
		if (accuracy >= 99.70) return " AAA";
		if (accuracy >= 99) return " AA:";
		if (accuracy >= 96.50) return " AA.";
		if (accuracy >= 93) return " AA";
		if (accuracy >= 90) return " A:";
		if (accuracy >= 85) return " A.";
		if (accuracy >= 80) return " A";
		if (accuracy >= 70) return " B";
		if (accuracy >= 60) return " C";
		if (accuracy < 60) return " D";
		return "";
	}

	public static function CalculateRating(noteDiff:Float, ?customSafeZone:Float):String // Generate a judgement through some timing shit
	{
		var customTimeScale = Conductor.safeZoneOffset / 166;


		// trace(customTimeScale + ' vs ' + Conductor.timeScale);

		// I HATE THIS IF CONDITION
		// IF LEMON SEES THIS I'M SORRY :(

		// trace('Hit Info\nDifference: ' + noteDiff + '\nZone: ' + Conductor.safeZoneOffset * 1.5 + "\nTS: " + customTimeScale + "\nLate: " + 155 * customTimeScale);
		// I assume these are in milliseconds? lmao
		if (ModifierState.namedModifiers.demo.value)
			return "good"; // FUNNY
		// ok these are actually in milliseconds
		if (noteDiff > Judge.wayoffJudge) // so god damn early its a miss
			return "miss";
		if (noteDiff > Judge.shitJudge ) 
			if (OptionsHandler.options.ignoreVile)
				return "miss"
			else 
				return "wayoff";
		if (noteDiff > Judge.badJudge) // way early
			return "shit";
		else if (noteDiff > Judge.goodJudge) // early
			return "bad";
		else if (noteDiff > Judge.sickJudge) // your kinda there
			return "good";
		else if (noteDiff < -1 * Judge.sickJudge) // little late
			return "good";
		else if (noteDiff < -1 * Judge.goodJudge) // late
			return "bad";
		else if (noteDiff < -1 * Judge.badJudge) // late as fuck
			return "shit";
		else if (noteDiff < -1 * Judge .shitJudge) // :grief:
			if (OptionsHandler.options.ignoreVile)
				return "miss"
			else
				return "wayoff";
		else if (noteDiff < -1 * Judge.wayoffJudge) // so god damn late its a miss
			return "miss";
		return "sick";
	}
	public static function CalculateFullCombo(level:FCLevel):Bool {
		return switch (level) {
			case Sick:
				(PlayState.misses == 0 && PlayState.bads == 0 && PlayState.shits == 0 && PlayState.goods == 0);
			case Good:
				PlayState.misses == 0 && PlayState.bads == 0 && PlayState.shits == 0;
			case Bad:
				PlayState.misses == 0 && PlayState.shits == 0;
			case Sdcb:
				PlayState.misses < 10;
			case Clear:
				PlayState.misses >= 10;
			default:
				false;
		}
	}
	public static function CalculateFCRating():FCLevel {
		if (CalculateFullCombo(Sick))
			return Sick;
		if (CalculateFullCombo(Good))
			return Good;
		if (CalculateFullCombo(Bad))
			return Bad;
		if (CalculateFullCombo(Sdcb))
			return Sdcb;
		if (CalculateFullCombo(Clear))
			return Clear;
		return None;
	}
	// The score line is asked for every frame, but what it shows only changes
	// on a hit, a miss or an option toggle. Keep the last line with everything
	// it was built from, so an unchanged frame gets it back without building a
	// dozen strings.
	static var rankingLine:String = null;
	static var rankingScore:Int = 0;
	static var rankingScoreDef:Int = 0;
	static var rankingNps:Int = 0;
	static var rankingAccuracy:Float = 0;
	static var rankingMisses:Int = 0;
	static var rankingGoods:Int = 0;
	static var rankingBads:Int = 0;
	static var rankingShits:Int = 0;
	static var rankingSafeFrames:Int = 0;
	static var rankingNpsDisplay:Bool = false;
	static var rankingBotplay:Bool = false;

	/** CalculateRanking, reusing the last line while none of its inputs changed. */
	public static function CalculateRankingCached(score:Int, scoreDef:Int, nps:Int, accuracy:Float):String
	{
		var npsDisplay:Bool = FlxG.save.data.npsDisplay ? true : false;
		var botplay:Bool = FlxG.save.data.botplay ? true : false;
		if (rankingLine != null && rankingScore == score && rankingScoreDef == scoreDef
			&& rankingNps == nps && rankingAccuracy == accuracy && rankingMisses == PlayState.misses
			&& rankingGoods == PlayState.goods && rankingBads == PlayState.bads
			&& rankingShits == PlayState.shits && rankingSafeFrames == Conductor.safeFrames
			&& rankingNpsDisplay == npsDisplay && rankingBotplay == botplay)
			return rankingLine;
		rankingScore = score;
		rankingScoreDef = scoreDef;
		rankingNps = nps;
		rankingAccuracy = accuracy;
		rankingMisses = PlayState.misses;
		rankingGoods = PlayState.goods;
		rankingBads = PlayState.bads;
		rankingShits = PlayState.shits;
		rankingSafeFrames = Conductor.safeFrames;
		rankingNpsDisplay = npsDisplay;
		rankingBotplay = botplay;
		return rankingLine = CalculateRanking(score, scoreDef, nps, accuracy);
	}

	public static function CalculateRanking(score:Int, scoreDef:Int, nps:Int, accuracy:Float):String
	{
		return (FlxG.save.data.npsDisplay ? "NPS: " + nps + (!FlxG.save.data.botplay ? " | " : "") : "") + (!FlxG.save.data.botplay ? // NPS Toggle
			"Score:"
			+ (Conductor.safeFrames != 10 ? score + " (" + scoreDef + ")" : "" + score)
			+ // Score
			" | Misses:"
			+ PlayState.misses
			+ // Misses/Combo Breaks
			" | Accuracy:"
			+ (FlxG.save.data.botplay ? "N/A" : HelperFunctions.truncateFloat(accuracy, 2) + "%")
			+ // Accuracy
			" | "
			+ GenerateLetterRank(accuracy) : ""); // Letter Rank
	}
}