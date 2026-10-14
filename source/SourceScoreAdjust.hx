package;

/** Arithmetic behind script score edits, kept apart from the live state so
 * every script layer adjusts the counters the same way. */
class SourceScoreAdjust {
	/** The counter after an edit: `relative` adds to it, otherwise it is replaced. */
	public static function apply(current:Int, value:Int, relative:Bool):Int
		return relative ? current + value : value;

	/** Hits as scripts read them when the judgement counters own the total. */
	public static function hitTotal(judged:Int, adjustment:Int):Int return judged + adjustment;

	/** The judgement counters can't be rewritten, so a hits edit is stored as
	 * the difference that makes the read-back come out at `target`. */
	public static function hitAdjustment(target:Int, judged:Int):Int return target - judged;
}
