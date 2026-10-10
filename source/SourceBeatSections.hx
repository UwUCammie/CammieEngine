package;

/** Common Psych/NV section cursor; callbacks observe each intermediate section. */
class SourceBeatSections {
	public static function advance(state:Dynamic, beats:Void->Float, hit:Void->Void):Void {
		if (state.stepsToDo < 1) state.stepsToDo = Math.round(beats() * 4);
		while (state.curStep >= state.stepsToDo) {
			state.curSection++;
			state.stepsToDo += Math.round(beats() * 4);
			hit();
		}
	}
	public static function rollback(state:Dynamic, count:Void->Int, exists:Int->Bool,
		beats:Void->Float, hit:Void->Void):Void {
		if (state.curStep < 0) return;
		var lastSection:Int = state.curSection;
		state.curSection = 0;
		state.stepsToDo = 0;
		var length = count();
		for (index in 0...length) {
			if (!exists(index)) continue;
			state.stepsToDo += Math.round(beats() * 4);
			if (state.stepsToDo > state.curStep) break;
			state.curSection++;
		}
		if (state.curSection > lastSection) hit();
	}
}
