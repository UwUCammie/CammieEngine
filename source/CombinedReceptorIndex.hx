package;

/**
	Index maths for scripts that address every receptor through one combined
	list, opponent lanes first and player lanes after. The game keeps two
	strumlines, so this only turns a combined index into a side and a lane.
*/
class CombinedReceptorIndex {
	public static inline var OPPONENT:Int = 0;
	public static inline var PLAYER:Int = 1;

	public static function count(opponentCount:Int, playerCount:Int):Int {
		return (opponentCount < 0 ? 0 : opponentCount) + (playerCount < 0 ? 0 : playerCount);
	}

	/**
		Returns [side, lane], or null when the index points at nothing.
		`wrap` is the note tween rule (index modulo the combined length); group
		reads leave it off so a loop that runs past the end sees nothing.
	*/
	public static function resolve(index:Int, opponentCount:Int, playerCount:Int, wrap:Bool = false):Null<Array<Int>> {
		if (opponentCount < 0) opponentCount = 0;
		if (playerCount < 0) playerCount = 0;
		var total = opponentCount + playerCount;
		// A negative index stays negative after the modulo in the source engines
		// too, and reads an empty slot there.
		if (total == 0 || index < 0) return null;
		if (wrap) index = index % total;
		else if (index >= total) return null;
		return index < opponentCount ? [OPPONENT, index] : [PLAYER, index - opponentCount];
	}
}
