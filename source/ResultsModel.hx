package;

/** One player's line on the results screen; the local player in solo play, everyone in a lobby. */
typedef ResultsPlayer = {
	var id:String;
	var name:String;
	var score:Int;
	/** 0 to 1. */
	var accuracy:Float;
	var maxCombo:Int;
	var rank:String;
	var sicks:Int;
	var goods:Int;
	var bads:Int;
	var shits:Int;
	var misses:Int;
	var modifiers:Array<String>;
	var failed:Bool;
	var quit:Bool;
}

/** Everything the results screen shows, gathered once when the song ends. */
typedef ResultsData = {
	var title:String;
	var difficulty:String;
	/** The local player's result. */
	var player:ResultsPlayer;
	/** Judgeable objects in the chart (the full combo). */
	var judgeable:Int;
	var multiplier:Float;
	var unranked:Bool;
	/** Best score saved before this play, -1 when there was none. */
	var previousBest:Int;
	var previousRank:String;
	/** Signed hit offsets in ms of judged note heads; positive is late. */
	var hitOffsets:Array<Float>;
	var storyMode:Bool;
	/** Every player of a multiplayer match, server-ordered or not; null in solo play. */
	var ?players:Array<ResultsPlayer>;
	/** Shown under the title in multiplayer, e.g. "Unranked: timelines differed". */
	var ?note:String;
}

typedef HitErrorStats = {
	var count:Int;
	/** Mean signed offset in ms; positive means late on average. */
	var mean:Float;
	/** osu! unstable rate: ten times the standard deviation in ms. */
	var unstableRate:Float;
}

/** The results screen as plain values: formatting, ordering, timing statistics
 * and the accuracy ring's segments. No display objects, so it is tested alone. */
class ResultsModel {
	/** Ring segments, lowest first: [start accuracy, end accuracy, rank]. */
	public static final SEGMENTS:Array<Array<Dynamic>> = [
		[0.0, 0.7, 'D'], [0.7, 0.8, 'C'], [0.8, 0.9, 'B'], [0.9, 0.95, 'A'], [0.95, 1.0, 'S'], [1.0, 1.0, 'SS']
	];

	/** 1234567 as "1,234,567". */
	public static function formatScore(score:Int):String {
		var negative = score < 0;
		var digits = Std.string(negative ? -score : score);
		var out = '';
		var count = 0;
		var index = digits.length - 1;
		while (index >= 0) {
			out = digits.charAt(index) + out;
			count++;
			if (count % 3 == 0 && index > 0)
				out = ',' + out;
			index--;
		}
		return (negative ? '-' : '') + out;
	}

	/** 0.98364 as "98.36%". Truncated, never rounded up, so 99.999% never shows as 100.00%. */
	public static function formatAccuracy(accuracy:Float):String {
		if (!Math.isFinite(accuracy) || accuracy < 0)
			accuracy = 0;
		var hundredths = Math.floor(accuracy * 10000 + 1e-7);
		var whole = Std.int(hundredths / 100);
		var fraction = Std.int(hundredths % 100);
		return whole + '.' + (fraction < 10 ? '0' : '') + fraction + '%';
	}

	/** Rank colour: the ring's segment colours, gold for S and pale for SS. */
	public static function rankColor(rank:String):Int {
		return switch (rank) {
			case 'SS' | 'SSH': 0xFFF3F0FF;
			case 'S' | 'SH': 0xFFFFD166;
			case 'A': 0xFF7BE07B;
			case 'B': 0xFF66B8FF;
			case 'C': 0xFFC08CFF;
			case 'D': 0xFFFF6B6B;
			case 'F': 0xFF9DB2CC;
			default: 0xFF9DB2CC;
		};
	}

	/** Higher score first, then higher accuracy, then the earlier entry. Quitters sink. */
	public static function ordered(players:Array<ResultsPlayer>):Array<ResultsPlayer> {
		var indexed = [for (index in 0...players.length) {player: players[index], index: index}];
		indexed.sort(function(a, b) {
			if (a.player.quit != b.player.quit)
				return a.player.quit ? 1 : -1;
			if (a.player.score != b.player.score)
				return a.player.score > b.player.score ? -1 : 1;
			if (a.player.accuracy != b.player.accuracy)
				return a.player.accuracy > b.player.accuracy ? -1 : 1;
			return a.index - b.index;
		});
		return [for (entry in indexed) entry.player];
	}

	public static function hitErrors(offsets:Array<Float>):HitErrorStats {
		var count = offsets == null ? 0 : offsets.length;
		if (count == 0)
			return {count: 0, mean: 0, unstableRate: 0};
		var sum = 0.0;
		for (value in offsets)
			sum += value;
		var mean = sum / count;
		var squares = 0.0;
		for (value in offsets)
			squares += (value - mean) * (value - mean);
		return {count: count, mean: mean, unstableRate: Math.sqrt(squares / count) * 10};
	}

	/** Counts of offsets in `bins` equal buckets across [-range, range]; outliers land in the edge buckets. */
	public static function histogram(offsets:Array<Float>, bins:Int, range:Float):Array<Int> {
		var counts = [for (_ in 0...bins) 0];
		if (offsets == null || bins <= 0 || range <= 0)
			return counts;
		for (value in offsets) {
			var bucket = Std.int(Math.floor((value + range) / (2 * range) * bins));
			if (bucket < 0)
				bucket = 0;
			if (bucket >= bins)
				bucket = bins - 1;
			counts[bucket]++;
		}
		return counts;
	}

	/** "3.2 ms late", "1.0 ms early" or "on time". */
	public static function meanLabel(mean:Float):String {
		var tenths = Math.round(Math.abs(mean) * 10) / 10;
		if (tenths == 0)
			return 'on time';
		var text = Std.string(tenths);
		if (text.indexOf('.') < 0)
			text += '.0';
		return text + ' ms ' + (mean > 0 ? 'late' : 'early');
	}

	/** lazer's accuracy fill easing (OutPow10, shortened): fast at first, settling at the end. */
	public static function fillEase(t:Float):Float {
		if (t <= 0)
			return 0;
		if (t >= 1)
			return 1;
		return 1 - Math.pow(1 - t, 10);
	}

	/** Result music, as the old victory screen chose it. */
	public static function musicFor(accuracy:Float):String
		return accuracy >= 0.65 ? 'goodScore' : (accuracy >= 0.5 ? 'mehScore' : 'badScore');

	/** The modifier names shown under the score, in the menu's order. */
	public static function modifierNames(ids:Array<String>, names:Map<String, String>):String {
		var shown = [for (id in ids) names.exists(id) ? names.get(id) : id];
		return shown.length == 0 ? 'No modifiers' : shown.join(', ');
	}
}
